"""Confined, offline-only workflow demonstration, not a general code executor.

The marker and records are local integrity attestations, not cryptographic trust
anchors. Concurrent filesystem mutation by another process is outside this demo's
threat model; untrusted source trees must never be used as demo roots.
"""

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from lsm.demo_models import demo_models
from lsm.security import redact, require_authorization

COMPONENTS = ("backend", "web", "mobile", "store")
MARKER = ".lsm-demo.json"
BRANCH = "demo/offline-sync-v2"
_CONFIG = (
    "[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n"
    "\tbare = false\n\tlogallrefupdates = true\n"
    "[user]\n\tname = LSM Local Demo\n\temail = demo@localhost\n"
)
_GIT = [
    "git",
    "--no-optional-locks",
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "commit.gpgSign=false",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "init.templateDir=",
]
_TEST = [sys.executable, "-I", "-m", "unittest", "discover", "-s", ".", "-v"]


def _json(value):
    return json.dumps(value, sort_keys=True, indent=2) + "\n"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _write(path, text):
    path.write_text(text, encoding="utf-8")


def _root(root):
    root = Path(os.path.abspath(root))
    # resolve() alone would hide a symlink in a parent or the selected root.
    for path in (root, *root.parents):
        if path.is_symlink():
            raise ValueError("Demo root and its parents must not be symlinks")
    return root


def _snapshot(root):
    result = {}
    for base, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories + files):
            path = Path(base) / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError("Demo contains a symlink or special file")
            if stat.S_ISREG(mode) and path.stat().st_nlink != 1:
                raise ValueError("Demo files must not be hard linked")
            relative = path.relative_to(root).as_posix()
            if relative == MARKER:
                continue
            result[relative] = {
                "sha256": _sha(path.read_bytes()) if path.is_file() else None,
                "mode": stat.S_IMODE(mode),
            }
    return result


def _environment():
    # No inherited Git config, Python startup configuration, credentials or shell.
    return {
        "PATH": os.defpath,
        "HOME": "/nonexistent",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ATTR_NOSYSTEM": "1",
    }


def _command(repo, args):
    def text(value):
        return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""

    try:
        completed = subprocess.run(
            args,
            cwd=repo,
            env=_environment(),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        result = {
            "command": args,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as error:
        result = {
            "command": args,
            "exit_code": 124,
            "stdout": text(error.stdout),
            "stderr": text(error.stderr),
            "operational_error": {"kind": "timeout", "message": str(error)},
        }
    except (OSError, subprocess.SubprocessError) as error:
        result = {
            "command": args,
            "exit_code": 127 if isinstance(error, FileNotFoundError) else 126,
            "stdout": text(getattr(error, "stdout", "")),
            "stderr": text(getattr(error, "stderr", "")),
            "operational_error": {"kind": "process_error", "message": str(error)},
        }
    return redact(result)


class _CommandFailure(ValueError):
    def __init__(self, result):
        super().__init__(f"Generated repository command failed with exit {result['exit_code']}")
        self.result = result


def _git(repo, *args):
    result = _command(repo, [*_GIT, *args])
    if result["exit_code"]:
        raise _CommandFailure(result)
    return result


def _fixture(component, version, fail=False):
    contract = f'COMPONENT = "{component}"\nVERSION = {version}\n\ndef synchronize(queued):\n' + (
        '    return {"version": VERSION, "accepted": len(queued), "offline": True}\n'
        if version == 2
        else '    return {"version": VERSION, "accepted": 0, "offline": False}\n'
    )
    test = (
        "import unittest\n"
        "from contract import VERSION, synchronize\n\n\n"
        "class OfflineSyncContract(unittest.TestCase):\n"
        "    def test_contract(self):\n"
        f"        self.assertEqual(VERSION, {version})\n"
        f"        self.assertEqual(synchronize(['pending']), "
        f"{{'version': {version}, 'accepted': {1 if version == 2 else 0}, "
        f"'offline': {version == 2}}})\n"
        + ("        self.fail('Intentional demo failure')\n" if fail else "")
    )
    return {"contract.py": contract, "test_contract.py": test, ".gitignore": "__pycache__/\n"}


def _identity(root):
    info = root.stat()
    return {"path": str(root), "device": info.st_dev, "inode": info.st_ino}


def init_demo(root: Path) -> dict:
    """Create only a NEW root, with four generated, initially clean repositories."""
    root = _root(root)
    # mkdir(exist_ok=False) is the no-clobber boundary, including empty directories.
    root.mkdir(exist_ok=False)
    heads = {}
    for component in COMPONENTS:
        repo = root / component
        repo.mkdir()
        for name, text in _fixture(component, 1).items():
            _write(repo / name, text)
        _git(repo, "init", "--initial-branch=main")
        _write(repo / ".git" / "config", _CONFIG)
        _git(repo, "add", "--", ".gitignore", "contract.py", "test_contract.py")
        _git(repo, "commit", "-m", "Generated offline-sync contract v1")
        heads[component] = _git(repo, "rev-parse", "HEAD")["stdout"].strip()
    marker = {
        "schema_version": "1.0",
        "kind": "lsm-generated-local-demo",
        "root": _identity(root),
        "heads": heads,
        "initial_files": _snapshot(root),
    }
    marker["content_digest"] = _sha(_json(marker).encode())
    _write(root / MARKER, _json(marker))
    return {
        "schema_version": "1.0",
        "root": str(root),
        "repositories": list(COMPONENTS),
        "marker": str(root / MARKER),
        "github_pr": None,
    }


def _marker(root):
    path = root / MARKER
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError("Missing or unsafe generated demo marker")
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            raise ValueError("Invalid generated demo marker")
        digest = marker.pop("content_digest")
        if (
            set(marker) != {"schema_version", "kind", "root", "heads", "initial_files"}
            or marker["schema_version"] != "1.0"
            or marker["kind"] != "lsm-generated-local-demo"
            or marker["root"] != _identity(root)
            or not isinstance(marker["heads"], dict)
            or not isinstance(marker["initial_files"], dict)
            or set(marker["heads"]) != set(COMPONENTS)
            or digest != _sha(_json(marker).encode())
        ):
            raise ValueError("Invalid or changed generated demo marker")
        return marker
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid generated demo marker") from error


def _safe_repository(repo):
    if not (repo / ".git").is_dir():
        raise ValueError("Demo repositories must have local Git directories")
    if (repo / ".git" / "config").read_text(encoding="utf-8") != _CONFIG:
        raise ValueError("Demo Git configuration changed")
    for name in ("commondir", "gitdir", "objects/info/alternates", "objects/info/http-alternates"):
        if (repo / ".git" / name).exists():
            raise ValueError("Demo Git storage must be confined to the generated repository")


def _check_initial(root):
    marker = _marker(root)
    snapshot = _snapshot(root)
    if snapshot != marker["initial_files"]:
        raise ValueError("Demo root changed or dirty; initialize a new demo")
    allowed = {component for component in COMPONENTS}
    allowed.update(
        f"{component}/{name}" for component in COMPONENTS for name in _fixture(component, 1)
    )
    if any(
        path not in allowed
        and not any(path == f"{c}/.git" or path.startswith(f"{c}/.git/") for c in COMPONENTS)
        for path in snapshot
    ):
        raise ValueError("Demo contains files outside the fixed generated fixture")
    for component in COMPONENTS:
        repo = root / component
        for name, text in _fixture(component, 1).items():
            if (repo / name).read_text(encoding="utf-8") != text:
                raise ValueError("Only the fixed generated fixtures may be executed")
        _safe_repository(repo)
        if _git(repo, "rev-parse", "HEAD")["stdout"].strip() != marker["heads"][component]:
            raise ValueError("Initial repository HEAD changed")
        if _git(repo, "status", "--porcelain", "--untracked-files=all")["stdout"]:
            raise ValueError("Demo repository is dirty")
    return marker


def _execution_plan(proposal):
    """Bind approval to exact canonical intent, direction, models, diff and impact."""
    from lsm.changes import create_proposal, proposal_content_digest

    canonical = create_proposal(*demo_models())
    # Only review metadata may vary. IDs alone cannot authorize a different or
    # reverse behavior, even when the forged summaries have a valid approval.
    for key in ("schema_version", "before_digest", "after_digest", "diff", "impact"):
        if proposal[key] != canonical[key]:
            raise ValueError("Proposal must exactly match the canonical offline-sync v1-to-v2 demo")

    return {
        "scenario": "fixed-generated-offline-sync-v1-to-v2",
        "proposal_content_digest": proposal_content_digest(proposal),
        "components": sorted(f"component.{name}" for name in COMPONENTS),
        "changed_model_ids": ["requirement.offline-sync"],
        "before_digest": canonical["before_digest"],
        "after_digest": canonical["after_digest"],
        "implementation_scope": "Generated contract fixtures only, not arbitrary proposed behavior",
    }


def _repository_record(component, marker):
    return {
        "component": component,
        "path": component,
        "branch": BRANCH,
        "before_commit": marker["heads"][component],
        "after_commit": None,
        "state": "unattempted",
        "stage": "not_started",
        "commands": [],
        "test": None,
        "error": None,
        "before_content_evidence": {
            name: _sha(text.encode()) for name, text in _fixture(component, 1).items()
        },
        "content_evidence": {},
        "review_bundle": f"reviews/{component}",
        "diff_artifact": None,
        "failure_artifact": None,
        "github_pr": None,
    }


def _run_repository(root, item, fail):
    repo = root / item["component"]

    def git(stage, *args):
        item["stage"] = stage
        try:
            result = _git(repo, *args)
        except _CommandFailure as error:
            item["commands"].append(error.result)
            raise
        item["commands"].append(result)
        return result

    try:
        item["state"] = "failed"  # Never optimistic success during partial execution.
        git("switch", "switch", "-c", BRANCH)
        item["stage"] = "write_fixture"
        for name, text in _fixture(item["component"], 2, fail).items():
            _write(repo / name, text)
        item["stage"] = "test"
        result = _command(repo, _TEST)
        item["test"] = result
        item["commands"].append(result)
        if result.get("operational_error"):
            raise _CommandFailure(result)
        item["stage"] = "cleanup"
        # Only bytecode produced by our fixed tests; never clean arbitrary roots.
        cache = repo / "__pycache__"
        if cache.exists():
            for path in cache.iterdir():
                path.unlink()
            cache.rmdir()
        git("add", "add", "--", "contract.py", "test_contract.py")
        git("commit", "commit", "-m", "Demonstrate offline-sync contract v2")
        item["after_commit"] = git("head", "rev-parse", "HEAD")["stdout"].strip()
        diff = git(
            "diff",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            item["before_commit"],
            item["after_commit"],
        )["stdout"]
        item["stage"] = "write_diff"
        _write(root / item["review_bundle"] / "change.diff", diff)
        item["diff_artifact"] = f"{item['review_bundle']}/change.diff"
        item["stage"] = "completed"
        item["state"] = "succeeded" if result["exit_code"] == 0 else "failed"
        if result["exit_code"]:
            item["error"] = {"kind": "test_failure", "message": "Fixed fixture test failed"}
        return False  # Test assertion failures still allow the other fixtures to run.
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        item["error"] = redact(
            {
                "kind": "operational_failure",
                "stage": item["stage"],
                "message": str(error),
                "command": error.result if isinstance(error, _CommandFailure) else None,
            }
        )
        return True  # Operational failure: stop and mark remaining repositories unattempted.


def _review_artifacts(root, item):
    bundle = root / item["review_bundle"]
    _write(bundle / "test.json", _json(item["test"]))
    _write(bundle / "commands.json", _json(item["commands"]))
    if item["state"] != "succeeded":
        item["failure_artifact"] = f"{item['review_bundle']}/failure.json"
        _write(
            bundle / "failure.json",
            _json(
                {
                    "state": item["state"],
                    "stage": item["stage"],
                    "error": item["error"],
                }
            ),
        )
    _write(
        bundle / "REVIEW.md",
        f"# {item['component']}: local review only\n\n"
        f"State: {item['state']}; stage: {item['stage']}\n\n"
        f"Intended branch: `{BRANCH}`\n\nBefore: `{item['before_commit']}`\n\n"
        f"After (only if observed): `{item['after_commit']}`\n\n"
        f"Diff artifact (only if produced): `{item['diff_artifact']}`\n\n"
        "See commands.json, test.json and failure.json if present. "
        "GitHub PR: not created. No merge or deployment.\n",
    )


def run_demo(
    root: Path,
    proposal: dict,
    policy: dict,
    actor: str,
    actor_kind="human",
    fail_component: str | None = None,
) -> dict:
    """Run one approved fixed v1 -> v2 change, recording actual local evidence."""
    require_authorization(policy, actor, "approve_changes", actor_kind)
    from lsm.changes import validate_proposal

    errors = validate_proposal(proposal)
    if errors or proposal.get("state") != "approved":
        raise ValueError("Workflow requires a valid, content-bound approved proposal")
    approval = proposal.get("approval") or {}
    if approval.get("actor") != actor or approval.get("actor_kind") != actor_kind:
        raise ValueError("Run actor must match the approved proposal's human actor")
    if fail_component is not None and fail_component not in COMPONENTS:
        raise ValueError("Unknown intentional failure component")
    plan = _execution_plan(proposal)
    root = _root(root)
    marker = _check_initial(root)
    reviews = root / "reviews"
    repositories = [_repository_record(component, marker) for component in COMPONENTS]
    errors = []
    active, stage = None, "prepare_reviews"
    try:
        reviews.mkdir()
        _write(reviews / "execution-plan.json", _json(plan))
        stopped = False
        for item in repositories:
            active, stage = item, "prepare_review_bundle"
            (root / item["review_bundle"]).mkdir()
            if stopped:
                item["error"] = {"kind": "unattempted", "message": "Earlier operational failure"}
            else:
                stopped = _run_repository(root, item, item["component"] == fail_component)
            stage = "content_evidence"
            item["content_evidence"] = {
                name: _sha((root / item["component"] / name).read_bytes())
                for name in _fixture(item["component"], 1)
            }
            stage = "review_artifacts"
            _review_artifacts(root, item)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # Storage failures may prevent local artifacts, but must not discard the
        # in-memory partial command evidence returned to the caller.
        failure = redact({"kind": "evidence_failure", "stage": stage, "message": str(error)})
        errors.append(failure)
        active = active or repositories[0]
        active.update(state="failed", stage=stage, error=failure)
        for item in repositories:
            if item["state"] == "unattempted":
                item["error"] = {"kind": "unattempted", "message": "Earlier evidence failure"}
            try:
                (root / item["review_bundle"]).mkdir(exist_ok=True)
                _review_artifacts(root, item)
            except (OSError, ValueError) as artifact_error:
                errors.append(
                    redact({"kind": "artifact_unavailable", "message": str(artifact_error)})
                )
    try:
        evidence = {"files": _snapshot(root), "marker_sha256": _sha((root / MARKER).read_bytes())}
    except (OSError, ValueError) as error:
        evidence = {"files": None, "marker_sha256": None}
        errors.append(redact({"kind": "snapshot_unavailable", "message": str(error)}))
    record = {
        "schema_version": "1.0",
        "state": "succeeded"
        if not errors and all(r["state"] == "succeeded" for r in repositories)
        else "failed",
        "root": _identity(root),
        "proposal": redact(proposal),
        "proposal_id": proposal["id"],
        "execution_plan": plan,
        "repositories": repositories,
        "evidence": evidence,
        "errors": errors,
        "github_pr": None,
        "limitations": [
            "Local human attestation, not authenticated identity",
            "Fixed generated fixtures only; not real applications",
            "Remote linked PR demonstration remains an external deferred acceptance gate",
        ],
    }
    record["reconciliation"] = reconcile_demo(root, record)
    return record


def reconcile_demo(root: Path, record: dict) -> dict:
    """Compare local bytes and HEADs; never execute repository source during reconciliation."""
    errors = []
    try:
        root = _root(root)
        _marker(root)
        if record.get("schema_version") != "1.0" or record.get("root") != _identity(root):
            raise ValueError("Record root identity or version mismatch")
        if record.get("errors"):
            raise ValueError("Execution evidence is incomplete")
        plan = _execution_plan(record["proposal"])
        if any(
            record["execution_plan"].get(key) != value
            for key, value in plan.items()
            if key != "proposal_content_digest"
        ):
            raise ValueError("Execution plan differs from the canonical scenario")
        evidence = record["evidence"]
        if evidence["marker_sha256"] != _sha((root / MARKER).read_bytes()):
            raise ValueError("Demo marker changed")
        actual = _snapshot(root)
        expected = evidence["files"]
        if not isinstance(expected, dict):
            raise ValueError("Invalid recorded file evidence")
        changed = sorted(
            key for key in actual.keys() | expected.keys() if actual.get(key) != expected.get(key)
        )
        if changed:
            errors.append({"code": "drift", "paths": changed})
        # Never invoke even Git on a modified tree/configuration.
        if not errors:
            repos = record["repositories"]
            if [item["component"] for item in repos] != list(COMPONENTS):
                raise ValueError("Record repository set changed")
            for item in repos:
                component = item["component"]
                if item["path"] != component or item["branch"] != BRANCH:
                    raise ValueError("Record repository path or branch mismatch")
                if item["state"] not in {"succeeded", "failed", "unattempted"}:
                    raise ValueError("Unknown repository execution state")
                repo = root / component
                _safe_repository(repo)
                if set(item["content_evidence"]) != set(_fixture(component, 2)):
                    raise ValueError("Incomplete content evidence")
                if item["before_content_evidence"] != {
                    name: _sha(text.encode()) for name, text in _fixture(component, 1).items()
                }:
                    raise ValueError("Initial content evidence mismatch")
                for name, digest in item["content_evidence"].items():
                    if name not in _fixture(component, 2):
                        raise ValueError("Unknown content evidence path")
                    if _sha((repo / name).read_bytes()) != digest:
                        raise ValueError("Content evidence differs from recorded files")
                bundle = root / "reviews" / component
                if (
                    item["review_bundle"] != f"reviews/{component}"
                    or item["diff_artifact"] not in (None, f"reviews/{component}/change.diff")
                    or json.loads((bundle / "test.json").read_text()) != item["test"]
                    or json.loads((bundle / "commands.json").read_text()) != item["commands"]
                ):
                    raise ValueError("Recorded test result or review bundle mismatch")
                if item["state"] != "succeeded":
                    if item[
                        "failure_artifact"
                    ] != f"reviews/{component}/failure.json" or json.loads(
                        (bundle / "failure.json").read_text()
                    ) != {"state": item["state"], "stage": item["stage"], "error": item["error"]}:
                        raise ValueError("Recorded partial failure artifact mismatch")
                    # The full snapshot includes any known dirty files/index and
                    # HEAD for partial runs. Do not run Git on incomplete work.
                    continue
                if (
                    item["stage"] != "completed"
                    or item["error"] is not None
                    or item["diff_artifact"] is None
                    or not item["after_commit"]
                    or not isinstance(item["test"], dict)
                    or item["test"].get("exit_code") != 0
                    or not item["commands"]
                    or any(command["exit_code"] != 0 for command in item["commands"])
                ):
                    raise ValueError("Incomplete or failed execution cannot be successful")
                if _git(repo, "rev-parse", "HEAD")["stdout"].strip() != item["after_commit"]:
                    raise ValueError("Repository HEAD differs from execution record")
                if _git(repo, "symbolic-ref", "--short", "HEAD")["stdout"].strip() != BRANCH:
                    raise ValueError("Repository branch differs from execution record")
                if _git(repo, "status", "--porcelain", "--untracked-files=all")["stdout"]:
                    raise ValueError("Repository has unknown modifications")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        errors.append({"code": "integrity", "message": str(error)})
    repos = record.get("repositories", [])
    tests_passed = (
        isinstance(repos, list)
        and len(repos) == len(COMPONENTS)
        and all(
            isinstance(item, dict)
            and item.get("state") == "succeeded"
            and isinstance(item.get("test"), dict)
            and item["test"].get("exit_code") == 0
            for item in repos
        )
    )
    return {
        "schema_version": "1.0",
        "state": "drifted" if errors else "matched",
        "verified": not errors and tests_passed and record.get("state") == "succeeded",
        "scope": "Local recorded fixture bytes, commits and test exits only; not authenticity",
        "errors": redact(errors),
        "github_pr": None,
    }
