"""Read-only discovery from explicit manifests, never from application sources."""

import json
import os
import re
import shutil
import subprocess
from copy import deepcopy
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator

from lsm.validation import validate_model


def _check_model(model, label):
    errors = validate_model(model)
    if errors:
        raise ValueError(
            f"Invalid {label}: "
            + "; ".join(f"{error['path']}: {error['message']}" for error in errors)
        )


def _confined(path, base):
    """Reject symlinks, including intermediate directories, before opening metadata."""
    path = Path(path)
    if not path.is_relative_to(base):
        raise ValueError(f"Repository metadata/path escapes base_dir: {path}")
    current = base
    for part in path.relative_to(base).parts:
        current = current.parent if part == ".." else current / part
        if not current.is_relative_to(base):
            raise ValueError(f"Repository metadata/path escapes base_dir: {path}")
        if current.is_symlink():
            raise ValueError(f"Symlink repository metadata/path is forbidden: {current}")
    return current


def _metadata_tree(path, base):
    _confined(path, base)
    if not path.is_dir():
        raise ValueError(f"Git metadata directory does not exist: {path}")
    for directory, dirs, names in os.walk(path, followlinks=False):
        for name in dirs + names:
            _confined(Path(directory) / name, base)
        for name in ("config", "config.worktree"):
            config = Path(directory) / name
            if config.is_file() and re.search(
                r"^\s*\[\s*include(?:if)?\b", config.read_text(encoding="utf-8"), re.I | re.M
            ):
                raise ValueError(f"External Git configuration includes are forbidden: {config}")


def _head(root, base):
    marker = _confined(root / ".git", base)
    gitdir = marker
    if marker.is_file():
        text = marker.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir: ") or "\n" in text:
            raise ValueError(f"Invalid Git metadata pointer: {marker}")
        gitdir = _confined(root / text[len("gitdir: ") :], base)
    _metadata_tree(gitdir, base)
    common = gitdir / "commondir"
    if common.is_file():
        common_path = common.read_text(encoding="utf-8").strip()
        if not common_path or "\n" in common_path:
            raise ValueError(f"Invalid Git common directory pointer: {common}")
        _metadata_tree(_confined(gitdir / common_path, base), base)
    git = shutil.which("git")
    if git is None:
        raise ValueError("Git is required for discovery; install git and retry")
    # Do not inherit GIT_DIR, GIT_WORK_TREE, injected config, or user configuration.
    env = {
        "PATH": os.defpath,
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
    }

    def rev_parse(*args):
        result = subprocess.run(
            [git, "--no-optional-locks", "-C", str(root), "rev-parse", *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode:
            raise ValueError(f"Not a usable Git repository with a committed HEAD: {root}")
        return result.stdout.strip()

    if Path(rev_parse("--show-toplevel")) != root:
        raise ValueError(f"Path must be an actual Git repository root: {root}")
    commit = rev_parse("--verify", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise ValueError(f"Invalid Git HEAD metadata: {root}")
    return commit


def discover(manifest: dict, base_dir: Path, existing: dict | None = None) -> dict:
    """Return a validated model 1.0, preserving identical IDs and rejecting conflicts.

    Only Git metadata is inspected. No files are written and inputs are not mutated.
    Manifest nesting explicitly declares containment/exposure; no source is scanned.
    """
    schema = json.loads(
        files("lsm").joinpath("schemas/discovery.schema.json").read_text(encoding="utf-8")
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda error: str(list(error.absolute_path)),
    )
    if errors:
        raise ValueError(
            "Invalid discovery manifest: "
            + "; ".join(
                f"/{'/'.join(map(str, error.absolute_path))}: {error.message}" for error in errors
            )
        )
    if existing is not None:
        _check_model(existing, "existing model")
        if existing["schema_version"] != "1.0":
            raise ValueError("Discovery requires existing model schema_version 1.0")
        if existing["model"] != manifest["model"]:
            raise ValueError("Manifest model identity/title conflicts with existing model")
    model = {
        "schema_version": "1.0",
        "model": deepcopy(manifest["model"]),
        "nodes": [],
        "edges": [],
    }
    seen = set()

    def provenance(source, origin="declared"):
        return {"origin": origin, "source": source, "verification": "unverified"}

    def add(collection, entity):
        if entity["id"] in seen:
            raise ValueError(f"Duplicate/conflicting discovery ID: {entity['id']}")
        seen.add(entity["id"])
        model[collection].append(entity)

    def node(item, kind, source, origin="declared"):
        add(
            "nodes",
            {
                "id": item["id"],
                "title": item["title"],
                "type": kind,
                "version": 1,
                "provenance": provenance(source, origin),
            },
        )

    def edge(kind, source, target, citation, identifier=None):
        # Length-prefix endpoints to avoid ambiguous concatenation of explicit IDs.
        identifier = identifier or f"discovery:{kind}:{len(source)}:{source}:{target}"
        add(
            "edges",
            {
                "id": identifier,
                "type": kind,
                "source": source,
                "target": target,
                "provenance": provenance(citation),
            },
        )

    try:
        base = Path(base_dir).absolute()
        if base.is_symlink() or base.resolve() != base or not base.is_dir():
            raise ValueError("base_dir must be an existing directory without symlink ancestors")
        roots = set()
        for index, repo in enumerate(manifest["repositories"]):
            citation = f"manifest:/repositories/{index}"
            root = _confined(base / repo["path"], base)
            if root in roots:
                raise ValueError(f"Duplicate repository path: {repo['path']}")
            roots.add(root)
            commit = _head(root, base)
            node(repo, "repository", f"{citation}; git:{repo['path']}@{commit}", "observed")
            for comp_index, component in enumerate(repo["components"]):
                comp_citation = f"{citation}/components/{comp_index}"
                node(component, component.get("type", "component"), comp_citation)
                edge("belongs_to", component["id"], repo["id"], comp_citation)
                for iface_index, interface in enumerate(component.get("interfaces", [])):
                    iface_citation = f"{comp_citation}/interfaces/{iface_index}"
                    node(interface, "interface", iface_citation)
                    edge("belongs_to", interface["id"], repo["id"], iface_citation)
                    edge("exposes", component["id"], interface["id"], iface_citation)
        for index, dependency in enumerate(manifest.get("dependencies", [])):
            edge(
                "depends_on",
                dependency["source"],
                dependency["target"],
                f"manifest:/dependencies/{index}",
                dependency["id"],
            )
    except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
        raise ValueError(f"Cannot inspect discovery repository metadata: {exc}") from exc
    # References may point at pre-existing nodes, but never silently replace them.
    if existing is not None:
        merged = deepcopy(existing)
        entities = {entity["id"]: entity for key in ("nodes", "edges") for entity in merged[key]}
        for key in ("nodes", "edges"):
            for entity in model[key]:
                previous = entities.get(entity["id"])
                if previous is not None and previous != entity:
                    raise ValueError(f"Conflicting existing entity ID: {entity['id']}")
                if previous is None:
                    merged[key].append(entity)
                    entities[entity["id"]] = entity
        model = merged
    _check_model(model, "discovered model")
    return model
