"""Tiny generated local repositories; no application builds or source execution."""

import hashlib
import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from lsm import workspace


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
    ).stdout.strip()


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "tiny-python"
    root.mkdir()
    (root / "app.py").write_text("# Declaration fixture; never executed\nVALUE = 1\n")
    git(root, "init", "-q")
    git(root, "add", "app.py")
    git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "commit",
        "-qm",
        "fixture",
    )
    manifest = {
        "schema_version": "1.0",
        "model": {"id": "system:tiny", "title": "Tiny"},
        "repositories": [
            {
                "id": "repo:tiny",
                "title": "Tiny Python",
                "path": root.name,
                "components": [{"id": "component:app", "title": "App"}],
            }
        ],
    }
    return tmp_path, root, manifest


def snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def advance(root):
    git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "commit",
        "--allow-empty",
        "-qm",
        "new HEAD only",
    )


@pytest.mark.parametrize("internal", [True, False])
def test_git_init_status_noop_cleanup(source, internal):
    base, root, manifest = source
    target = (root if internal else base) / ".ane"
    original, head = (root / "app.py").read_bytes(), git(root, "rev-parse", "HEAD")
    result = workspace.init_workspace(manifest, base, target)
    assert result == {
        "workspace": str(target),
        "changed": True,
        "mode": "in-repo" if internal else "external",
    }
    assert workspace.workspace_status(target)["valid"]
    assert not workspace.workspace_status(target)["source_verified"]
    before = snapshot(target)
    assert set(before) == set(workspace.MANAGED)
    assert not workspace.refresh_workspace(target, base)["changed"]
    assert not workspace.refresh_workspace(target, base, apply=True)["changed"]
    assert snapshot(target) == before
    assert not workspace.cleanup_workspace(target)["applied"]
    assert snapshot(target) == before
    assert workspace.cleanup_workspace(target, apply=True)["applied"]
    assert not target.exists()
    assert (root / "app.py").read_bytes() == original
    assert git(root, "rev-parse", "HEAD") == head


def test_head_diff_preview_apply_versions(source):
    base, root, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    before = snapshot(target)
    advance(root)
    preview = workspace.refresh_workspace(target, base)
    assert preview["changed"] and not preview["applied"]
    assert snapshot(target) == before
    modified = preview["diff"]["nodes"]["modified"]
    assert [node["id"] for node in modified] == ["repo:tiny"]
    assert modified[0]["after"]["version"] == 2
    assert modified[0]["after"]["provenance"]["verification"] == "unverified"
    assert workspace.refresh_workspace(target, base, apply=True)["applied"]
    assert workspace.workspace_status(target)["valid"]
    applied = snapshot(target)
    assert not workspace.refresh_workspace(target, base, apply=True)["changed"]
    assert snapshot(target) == applied
    advance(root)
    workspace.refresh_workspace(target, base, apply=True)
    model = json.loads((target / "model.json").read_bytes())
    assert {node["id"]: node["version"] for node in model["nodes"]} == {
        "repo:tiny": 3,
        "component:app": 1,
    }


def test_mock_replacement_preserves_entire_bundle(source):
    from lsm.providers import MockProvider

    base, _, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    before = snapshot(target)
    model = json.loads(before["model.json"])
    assert not workspace.refresh_workspace(target, base, provider=MockProvider(model), apply=True)[
        "changed"
    ]
    assert snapshot(target) == before
    workspace.cleanup_workspace(target, apply=True)
    workspace.init_workspace(manifest, base, target, provider=MockProvider(model))
    assert workspace.workspace_status(target)["valid"]
    assert json.loads((target / "model.json").read_bytes()) == model


@pytest.mark.parametrize("field,value", [("capability", "deploy"), ("request_digest", "0" * 64)])
def test_evidence_is_bound_to_actual_discovery_request(source, monkeypatch, field, value):
    base, _, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    evidence_path = target / "evidence.json"
    evidence = json.loads(evidence_path.read_bytes())
    evidence[field] = value
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    state_path = target / "state.json"
    state = json.loads(state_path.read_bytes())
    state["hashes"]["evidence.json"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    before = snapshot(target)
    assert workspace.workspace_status(target)["valid"] is False

    def forbidden(*args, **kwargs):
        raise AssertionError("Inconsistent saved evidence must fail before provider invocation")

    monkeypatch.setattr("lsm.providers.invoke", forbidden)
    with pytest.raises(ValueError, match="request binding"):
        workspace.refresh_workspace(target, base, apply=True)
    with pytest.raises(ValueError, match="request binding"):
        workspace.cleanup_workspace(target, apply=True)
    assert snapshot(target) == before


@pytest.mark.parametrize(
    "placement", ["nested", "wrong-name", "existing", "symlink-parent", "traversal"]
)
def test_reject_unsafe_placement_before_provider(source, monkeypatch, placement):
    base, root, manifest = source
    target = base / ".ane"
    if placement == "nested":
        (root / "src").mkdir()
        target = root / "src" / ".ane"
    elif placement == "wrong-name":
        target = base / "metadata"
    elif placement == "existing":
        target.mkdir()
    elif placement == "symlink-parent":
        (base / "linked").symlink_to(root, target_is_directory=True)
        target = base / "linked" / ".ane"
    else:
        target = root / ".." / ".ane"
    monkeypatch.setattr(workspace, "_provider", lambda _: pytest.fail("must not discover"))
    with pytest.raises(ValueError):
        workspace.init_workspace(manifest, base, target)


@pytest.mark.parametrize(
    "tamper",
    [
        "model",
        "config",
        "hash",
        "unknown",
        "symlink",
        "hardlink",
        "fifo",
        "missing",
        "state-path",
        "version",
    ],
)
def test_drift_fails_before_discovery_and_cleanup(source, monkeypatch, tamper):
    base, _, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    if tamper in {"model", "config"}:
        name = "model.json" if tamper == "model" else "project.json"
        (target / name).write_bytes((target / name).read_bytes() + b" ")
    elif tamper in {"hash", "state-path", "version"}:
        state = json.loads((target / "state.json").read_bytes())
        if tamper == "hash":
            state["hashes"]["model.json"] = "0" * 64
        elif tamper == "state-path":
            state["hashes"]["../app.py"] = "0" * 64
        else:
            state["workspace_version"] = "2.0"
        (target / "state.json").write_text(json.dumps(state))
    elif tamper == "unknown":
        (target / "notes.txt").write_text("user work")
    elif tamper == "missing":
        (target / "context.json").unlink()
    else:
        path = target / "context.json"
        path.unlink()
        if tamper == "symlink":
            path.symlink_to(target / "model.json")
        elif tamper == "hardlink":
            os.link(target / "model.json", path)
        else:
            os.mkfifo(path)
    monkeypatch.setattr(workspace, "_provider", lambda _: pytest.fail("must not discover"))
    assert not workspace.workspace_status(target)["valid"]
    with pytest.raises(ValueError):
        workspace.refresh_workspace(target, base, apply=True)
    with pytest.raises(ValueError):
        workspace.cleanup_workspace(target, apply=True)
    assert target.exists()


def test_explicit_base_binding(source, monkeypatch):
    base, root, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    monkeypatch.setattr(workspace, "_provider", lambda _: pytest.fail("must not discover"))
    with pytest.raises(ValueError, match="binding"):
        workspace.refresh_workspace(target, root, apply=True)


@pytest.mark.parametrize("status", ["partial", "failed"])
def test_incomplete_provider_never_persists(source, monkeypatch, status):
    import lsm.providers

    base, _, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    before = snapshot(target)
    envelope = json.loads(before["evidence.json"])
    envelope["status"] = status
    monkeypatch.setattr(lsm.providers, "invoke", lambda *a, **kw: deepcopy(envelope))
    with pytest.raises(ValueError, match="completely"):
        workspace.refresh_workspace(target, base, apply=True)
    assert snapshot(target) == before
    workspace.cleanup_workspace(target, apply=True)
    with pytest.raises(ValueError):
        workspace.init_workspace(manifest, base, target)
    assert not target.exists()


def test_refresh_write_failure_rolls_back(source, monkeypatch):
    base, root, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    before = snapshot(target)
    advance(root)
    original = workspace._replace
    calls = 0

    def fail_once(path, content):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("fixture write failure")
        return original(path, content)

    monkeypatch.setattr(workspace, "_replace", fail_once)
    with pytest.raises(OSError, match="original metadata restored"):
        workspace.refresh_workspace(target, base, apply=True)
    assert snapshot(target) == before
    assert workspace.workspace_status(target)["valid"]


def test_failed_rollback_retains_recovery_and_blocks_cleanup(source, monkeypatch):
    base, root, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    before = snapshot(target)
    advance(root)
    original = workspace._replace
    calls = 0

    def fail_after_one(path, content):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise OSError("fixture persistent write failure")
        return original(path, content)

    monkeypatch.setattr(workspace, "_replace", fail_after_one)
    with pytest.raises(OSError, match="rollback incomplete; recovery:"):
        workspace.refresh_workspace(target, base, apply=True)
    import base64

    recovery = json.loads((target / "recovery.json").read_bytes())
    assert {
        name: base64.b64decode(content) for name, content in recovery["files_base64"].items()
    } == before
    assert not workspace.workspace_status(target)["valid"]
    with pytest.raises(ValueError):
        workspace.cleanup_workspace(target, apply=True)


def test_unsupported_model_version_never_creates_workspace(source):
    from lsm.providers import MockProvider

    base, _, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    model = json.loads((target / "model.json").read_bytes())
    workspace.cleanup_workspace(target, apply=True)
    model["schema_version"] = "1.1"
    with pytest.raises(ValueError):
        workspace.init_workspace(manifest, base, target, provider=MockProvider(model))
    assert not target.exists()


def test_recomputed_hash_does_not_hide_inconsistent_projection(source):
    base, _, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    content = b"user projection change\n"
    (target / "docs/index.md").write_bytes(content)
    state = json.loads((target / "state.json").read_bytes())
    state["hashes"]["docs/index.md"] = workspace._hash(content)
    (target / "state.json").write_bytes(workspace._json(state))
    assert not workspace.workspace_status(target)["valid"]
    with pytest.raises(ValueError, match="inconsistent"):
        workspace.cleanup_workspace(target, apply=True)


def test_drift_during_discovery_is_not_overwritten(source, monkeypatch):
    base, root, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    advance(root)
    original = workspace._discover

    def modify_while_discovering(*args):
        result = original(*args)
        (target / "docs/index.md").write_bytes(b"user edit during collection\n")
        return result

    monkeypatch.setattr(workspace, "_discover", modify_while_discovering)
    with pytest.raises(ValueError, match="drift"):
        workspace.refresh_workspace(target, base, apply=True)
    assert (target / "docs/index.md").read_bytes() == b"user edit during collection\n"
    assert not (target / "recovery.json").exists()


def test_init_write_failure_never_touches_source(source, monkeypatch):
    base, root, manifest = source
    target = root / ".ane"
    source_bytes = (root / "app.py").read_bytes()
    original = Path.open

    def fail_model_write(path, mode="r", *args, **kwargs):
        if path == target / "model.json" and mode == "xb":
            raise OSError("fixture init write failure")
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_model_write)
    with pytest.raises(OSError, match="fixture init"):
        workspace.init_workspace(manifest, base, target)
    assert not target.exists()
    assert (root / "app.py").read_bytes() == source_bytes


def test_context_file_matches_self_inclusive_budget(source):
    base, root, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)

    def check_size():
        content = (target / "context.json").read_bytes()
        accounting = json.loads(content)["accounting"]
        assert len(content) == accounting["estimated_tokens"] <= accounting["budget"]
        assert not content.endswith(b"\n")

    check_size()
    advance(root)
    workspace.refresh_workspace(target, base, apply=True)
    check_size()


@pytest.mark.parametrize("internal", [True, False])
def test_git_metadata_placement_rejected_before_discovery(source, monkeypatch, internal):
    base, root, manifest = source
    parent = root / ".git" if internal else base / "orchestration" / ".git"
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / ".ane"
    monkeypatch.setattr(workspace, "_provider", lambda _: pytest.fail("must not discover"))
    with pytest.raises(ValueError, match="Git metadata"):
        workspace.init_workspace(manifest, base, target)
    assert not target.exists()


def test_reordered_mock_is_noop_preserving_bytes_and_timestamps(source):
    from lsm.providers import MockProvider

    base, root, manifest = source
    manifest["repositories"][0]["components"].append({"id": "component:other", "title": "Other"})
    target = root / ".ane"
    workspace.init_workspace(manifest, base, target)
    before = snapshot(target)
    timestamps = {name: (target / name).stat().st_mtime_ns for name in workspace.MANAGED}
    model = json.loads(before["model.json"])
    assert len(model["nodes"]) > 1 and len(model["edges"]) > 1
    model["nodes"].reverse()
    model["edges"].reverse()
    for apply in (False, True):
        result = workspace.refresh_workspace(
            target, base, provider=MockProvider(model), apply=apply
        )
        assert not result["changed"] and not result["applied"]
        assert result["diff"] == {
            "nodes": {"added": [], "removed": [], "modified": []},
            "edges": {"added": [], "removed": [], "modified": []},
            "metadata_changed": False,
        }
        assert snapshot(target) == before
        assert {
            name: (target / name).stat().st_mtime_ns for name in workspace.MANAGED
        } == timestamps


def test_moved_workspace_fails_local_binding(source):
    base, _, manifest = source
    target = base / ".ane"
    workspace.init_workspace(manifest, base, target)
    destination = base / "elsewhere"
    destination.mkdir()
    moved = destination / ".ane"
    target.rename(moved)
    assert not workspace.workspace_status(moved)["valid"]
    with pytest.raises(ValueError, match="location binding"):
        workspace.refresh_workspace(moved, base, apply=True)
