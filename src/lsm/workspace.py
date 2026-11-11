"""Opt-in read-only adoption bundles; never execute or write application sources."""

import base64
import hashlib
import json
import os
import stat
import tempfile
from copy import deepcopy
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator

from lsm.changes import semantic_diff
from lsm.context import compile_context, serialize_context
from lsm.documentation import render_docs
from lsm.validation import validate_model

DOCUMENTS = ("index.md", "context.mmd", "components.mmd", "traceability.md", "onboarding.md")
ARTIFACTS = ("project.json", "model.json", "evidence.json", "context.json") + tuple(
    "docs/" + name for name in DOCUMENTS
)
MANAGED = ARTIFACTS + ("state.json",)


def _json(value):
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode()


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _schema(name, value):
    schema = json.loads(files("lsm").joinpath(f"schemas/{name}.schema.json").read_text())
    if list(Draft202012Validator(schema).iter_errors(value)):
        raise ValueError(f"Invalid {name} configuration")


def _path(value):
    path = Path(value).absolute()
    if ".." in path.parts or path.resolve() != path:
        raise ValueError("Paths must not contain traversal or symlink ancestors")
    return path


def _placement(directory, base, manifest):
    _schema("discovery", manifest)
    if directory.name != ".ane":
        raise ValueError("Workspace must be named .ane")
    mode = "external"
    for repo in manifest["repositories"]:
        root = base / repo["path"]
        if directory.is_relative_to(root):
            if directory.parent != root:
                raise ValueError("Workspace must be a direct child of a named repository")
            mode = "in-repo"
    return mode


def _provider(provider):
    from lsm.providers import GitProvider

    return GitProvider() if provider is None else provider


def _discover(provider, manifest, base):
    from lsm.providers import invoke

    result = invoke(provider, "discover", manifest=deepcopy(manifest), base_dir=base, existing=None)
    if result["status"] != "succeeded" or result["errors"] or result["data"] is None:
        raise ValueError("Discovery did not succeed completely; workspace unchanged")
    model = result["data"]["model"]
    if validate_model(model) or model["schema_version"] != "1.0":
        raise ValueError("Workspace requires a valid schema 1.0 discovery model")
    return deepcopy(result), deepcopy(model)


def _versions(model, before):
    model = deepcopy(model)
    previous = {node["id"]: node for node in before["nodes"]}
    for node in model["nodes"]:
        old = previous.get(node["id"])
        if old is not None:
            changed = {k: v for k, v in old.items() if k != "version"} != {
                k: v for k, v in node.items() if k != "version"
            }
            node["version"] = old["version"] + int(changed)
    return model


def _bundle(project, model, evidence):
    data = {
        "project.json": _json(project),
        "model.json": _json(model),
        "evidence.json": _json(evidence),
        "context.json": (
            serialize_context(compile_context(model, **project["context"])) + "\n"
        ).encode(),
    }
    documents = render_docs(model)
    if set(documents) != set(DOCUMENTS):
        raise ValueError("Unexpected documentation projection layout")
    data.update({"docs/" + name: documents[name].encode() for name in DOCUMENTS})
    data["state.json"] = _json(
        {"workspace_version": "1.0", "hashes": {name: _hash(data[name]) for name in ARTIFACTS}}
    )
    return data


def _read(directory):
    directory = _path(directory)
    if directory.name != ".ane" or not directory.is_dir():
        raise ValueError("Expected an existing .ane directory")
    expected = set(MANAGED) | {"docs"}
    found = set()
    for parent, dirs, names in os.walk(directory, followlinks=False):
        for name in dirs + names:
            path = Path(parent) / name
            relative = path.relative_to(directory).as_posix()
            found.add(relative)
            info = path.lstat()
            if relative not in expected or stat.S_ISLNK(info.st_mode):
                raise ValueError("Unknown entry or symlink in workspace")
            if relative == "docs":
                if not stat.S_ISDIR(info.st_mode):
                    raise ValueError("Workspace docs must be a directory")
            elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("Workspace requires regular, non-hardlinked files")
    if found != expected:
        raise ValueError("Incomplete workspace")
    data = {name: (directory / name).read_bytes() for name in MANAGED}
    try:
        state = json.loads(data["state.json"])
        if set(state) != {"workspace_version", "hashes"} or state["workspace_version"] != "1.0":
            raise ValueError("Unsupported workspace state")
        if set(state["hashes"]) != set(ARTIFACTS):
            raise ValueError("Invalid managed hash paths")
        if state["hashes"] != {name: _hash(data[name]) for name in ARTIFACTS}:
            raise ValueError("Workspace drift: managed bytes were modified")
        project = json.loads(data["project.json"])
        _schema("workspace", project)
        base = _path(project["base_dir"])
        if str(base) != project["base_dir"]:
            raise ValueError("Source base binding must be absolute")
        if project["workspace"] != str(directory):
            raise ValueError("Workspace location binding mismatch")
        if _placement(directory, base, project["manifest"]) != project["mode"]:
            raise ValueError("Workspace placement binding mismatch")
        model = json.loads(data["model.json"])
        if validate_model(model) or model["schema_version"] != "1.0":
            raise ValueError("Invalid workspace model")
        evidence = json.loads(data["evidence.json"])
        from lsm.providers import validate_result

        if validate_result(evidence):
            raise ValueError("Invalid workspace provider evidence")
        if evidence["status"] != "succeeded" or evidence["errors"]:
            raise ValueError("Incomplete workspace provider evidence")
        if project["provider"] != evidence["provider"]:
            raise ValueError("Workspace provider binding mismatch")
        if model["model"] != project["manifest"]["model"]:
            raise ValueError("Workspace manifest/model binding mismatch")
        if _versions(evidence["data"]["model"], model) != model:
            raise ValueError("Workspace model/evidence mismatch")
        if _bundle(project, model, evidence) != data:
            raise ValueError("Workspace projections or state are inconsistent")
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed workspace metadata") from exc
    return directory, data, project, model


def _replace(path, content):
    """Stage one file in its own directory; caller owns multi-file rollback."""
    fd, temporary = tempfile.mkstemp(prefix=".ane-stage-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _apply(directory, before, after):
    # Rollback, NOT a filesystem transaction or crash-atomic operation.
    _read(directory)  # Recheck drift after discovery and before writes.
    recovery = directory / "recovery.json"
    recovery_bytes = _json(
        {
            "purpose": "Original metadata for manual recovery; not a second editable model",
            "files_base64": {
                name: base64.b64encode(before[name]).decode("ascii") for name in MANAGED
            },
        }
    )
    with recovery.open("xb") as stream:
        stream.write(recovery_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    preserve = False
    try:
        written = []
        try:
            for name in MANAGED:  # state is deliberately last
                if before[name] != after[name]:
                    _replace(directory / name, after[name])
                    written.append(name)
        except OSError as exc:
            failed = []
            for name in reversed(written):
                try:
                    _replace(directory / name, before[name])
                except OSError:
                    failed.append(name)
            if failed:
                preserve = True
                raise OSError(
                    f"Non-atomic refresh failed; rollback incomplete; recovery: {recovery}"
                ) from exc
            raise OSError("Non-atomic refresh failed; original metadata restored") from exc
    finally:
        if not preserve and recovery.read_bytes() == recovery_bytes:
            recovery.unlink()


def init_workspace(
    manifest,
    base_dir,
    directory,
    *,
    provider=None,
    task="Onboard system",
    seed_ids=None,
    budget=8192,
):
    """Create a NEW explicit .ane target; no source files are written."""
    directory, base = _path(directory), _path(base_dir)
    mode = _placement(directory, base, manifest)
    if directory.exists() or not directory.parent.is_dir() or not base.is_dir():
        raise ValueError("Workspace must be new with existing parent and source base")
    evidence, model = _discover(_provider(provider), manifest, base)
    project = {
        "workspace_version": "1.0",
        "workspace": str(directory),
        "base_dir": str(base),
        "mode": mode,
        "manifest": deepcopy(manifest),
        "provider": evidence["provider"],
        "context": {
            "task": task,
            "seed_ids": seed_ids
            if seed_ids is not None
            else [repo["id"] for repo in manifest["repositories"]],
            "budget": budget,
        },
    }
    _schema("workspace", project)
    data = _bundle(project, model, evidence)
    directory.mkdir()
    created = []
    try:
        (directory / "docs").mkdir()
        for name in MANAGED:
            with (directory / name).open("xb") as stream:
                created.append(name)
                stream.write(data[name])
    except OSError:
        for name in reversed(created):
            path = directory / name
            if path.is_file() and not path.is_symlink() and path.read_bytes() == data[name]:
                path.unlink()
        for path in (directory / "docs", directory):
            try:
                path.rmdir()
            except OSError:
                pass
        raise
    return {"workspace": str(directory), "changed": True, "mode": mode}


def refresh_workspace(directory, base_dir, *, provider=None, apply=False):
    """Preview by default. Explicit apply changes only hash-checked metadata."""
    directory, before, project, model = _read(directory)
    base = _path(base_dir)
    if str(base) != project["base_dir"]:
        raise ValueError("Explicit source base does not match workspace binding")
    evidence, discovered = _discover(_provider(provider), project["manifest"], base)
    updated = _versions(discovered, model)
    diff = semantic_diff(model, updated)
    changed = updated != model
    if changed and apply:
        project = deepcopy(project)
        project["provider"] = evidence["provider"]
        _apply(directory, before, _bundle(project, updated, evidence))
    return {
        "workspace": str(directory),
        "changed": changed,
        "diff": diff,
        "applied": bool(apply and changed),
    }


def workspace_status(directory):
    """Local bundle integrity only; never claim fresh source verification."""
    try:
        directory, _, project, _ = _read(directory)
    except (ValueError, OSError) as exc:
        return {"workspace": str(directory), "valid": False, "errors": [str(exc)]}
    return {
        "workspace": str(directory),
        "valid": True,
        "mode": project["mode"],
        "source_verified": False,
    }


def cleanup_workspace(directory, *, apply=False):
    """Plan or delete ONLY fixed known files, then empty directories."""
    directory, _, _, _ = _read(directory)
    paths = [str(directory / name) for name in MANAGED] + [str(directory / "docs"), str(directory)]
    if apply:
        for name in MANAGED:
            (directory / name).unlink()
        (directory / "docs").rmdir()
        directory.rmdir()
    return {"workspace": str(directory), "paths": paths, "applied": bool(apply)}
