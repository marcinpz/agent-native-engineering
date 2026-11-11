"""Actual Git/fixture execution with real proposal approval and digest validation."""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lsm import workflow
from lsm.changes import approve_proposal, create_proposal
from lsm.workflow import COMPONENTS, MARKER, demo_models, init_demo, reconcile_demo, run_demo


@pytest.fixture
def policy():
    return {
        "version": "1.0",
        "humans": ["owner"],
        "permissions": {"approve_changes": ["owner"]},
    }


@pytest.fixture
def proposal(policy):
    return approve_proposal(create_proposal(*demo_models()), policy, "owner")


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "demo"
    init_demo(path)
    return path


def tree(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and not p.is_symlink()
    }


def test_success_all_four_actual_tests_and_local_evidence(root, proposal, policy):
    record = run_demo(root, proposal, policy, "owner")
    assert record["schema_version"] == "1.0"
    assert record["state"] == "succeeded"
    assert record["github_pr"] is None
    assert record["reconciliation"]["verified"] is True
    assert [r["component"] for r in record["repositories"]] == list(COMPONENTS)
    for repo in record["repositories"]:
        assert repo["before_commit"] != repo["after_commit"]
        assert repo["test"]["exit_code"] == 0
        assert "Ran 1 test" in repo["test"]["stderr"]
        assert "OK" in repo["test"]["stderr"]
        assert repo["test"]["command"][:2] == [sys.executable, "-I"]
        assert (root / repo["diff_artifact"]).is_file()
        assert "not created" in (root / repo["review_bundle"] / "REVIEW.md").read_text()
        assert repo["github_pr"] is None
        for name, digest in repo["content_evidence"].items():
            assert hashlib.sha256((root / repo["path"] / name).read_bytes()).hexdigest() == digest
    assert reconcile_demo(root, json.loads(json.dumps(record)))["verified"] is True
    with pytest.raises(ValueError, match="changed or dirty"):
        run_demo(root, proposal, policy, "owner")


def test_package_canonical_models_match_examples_and_are_fresh():
    before, after = demo_models()
    assert before == json.loads(Path("examples/changes/before.json").read_text())
    assert after == json.loads(Path("examples/changes/offline-sync.json").read_text())
    before["nodes"][0]["title"] = "mutated"
    assert demo_models()[0]["nodes"][0]["title"] != "mutated"
    assert after["nodes"][0]["title"] != "mutated"


def test_demo_does_not_require_repository_examples(root, proposal, policy, monkeypatch, tmp_path):
    elsewhere = tmp_path / "without-examples"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    record = run_demo(root, proposal, policy, "owner")
    assert record["state"] == "succeeded"
    assert record["reconciliation"]["verified"] is True


@pytest.mark.parametrize("mutation", ["reverse", "contradictory", "forged-summary", "wrong-digest"])
def test_exact_supported_behavior_binding_before_writes(root, proposal, policy, mutation):
    before_model, after_model = demo_models()
    if mutation == "reverse":
        candidate = create_proposal(after_model, before_model)
    elif mutation == "contradictory":
        after_model["nodes"][0]["acceptance_criteria"] = [
            "Disable offline operation; never accept queued items."
        ]
        candidate = create_proposal(before_model, after_model)
    else:
        candidate = copy.deepcopy(proposal)
        candidate["state"], candidate["approval"] = "proposed", None
        if mutation == "forged-summary":
            candidate["diff"]["nodes"]["modified"][0]["after"]["acceptance_criteria"] = [
                "Disable offline operation; never accept queued items."
            ]
        else:
            candidate["before_digest"] = "a" * 64
    approved = approve_proposal(candidate, policy, "owner")
    before = tree(root)
    with pytest.raises(ValueError, match="exactly match the canonical"):
        run_demo(root, approved, policy, "owner")
    assert tree(root) == before


def test_canonical_proposal_allows_review_metadata_variation(root, policy):
    candidate = create_proposal(*demo_models(), identifier="change:reviewed-fixture")
    candidate["risks"] = ["This is only a generated function demonstration."]
    candidate["assumptions"] = ["No application fulfillment is asserted."]
    record = run_demo(root, approve_proposal(candidate, policy, "owner"), policy, "owner")
    assert record["state"] == "succeeded"
    assert record["reconciliation"]["verified"] is True


@pytest.mark.parametrize("failure", ["timeout", "missing-process"])
def test_process_exception_returns_partial_failure_evidence(
    root, proposal, policy, monkeypatch, failure
):
    original = workflow.subprocess.run

    def injected(args, **kwargs):
        if kwargs["cwd"] == root / "web" and args[0] == sys.executable:
            if failure == "timeout":
                raise subprocess.TimeoutExpired(
                    args, 30, output=b"partial output token=very-secret", stderr=b"still waiting"
                )
            raise FileNotFoundError("test interpreter unavailable")
        return original(args, **kwargs)

    monkeypatch.setattr(workflow.subprocess, "run", injected)
    record = run_demo(root, proposal, policy, "owner")
    assert record["state"] == "failed"
    assert [item["state"] for item in record["repositories"]] == [
        "succeeded",
        "failed",
        "unattempted",
        "unattempted",
    ]
    web = record["repositories"][1]
    assert web["stage"] == "test"
    assert web["after_commit"] is None
    assert web["diff_artifact"] is None
    assert web["test"]["exit_code"] == (124 if failure == "timeout" else 127)
    if failure == "timeout":
        assert "partial output" in web["test"]["stdout"]
        assert "very-secret" not in json.dumps(record)
        assert web["test"]["stderr"] == "still waiting"
    assert (root / web["failure_artifact"]).is_file()
    assert record["reconciliation"]["state"] == "matched"
    assert record["reconciliation"]["verified"] is False
    for item in record["repositories"][2:]:
        assert item["commands"] == []
        assert item["test"] is None
        assert item["after_commit"] is None
        assert (root / item["failure_artifact"]).is_file()
    assert reconcile_demo(root, record)["verified"] is False
    record["state"] = "succeeded"
    for item in record["repositories"]:
        item["state"] = "succeeded"
    assert reconcile_demo(root, record)["verified"] is False


@pytest.mark.parametrize("stage", ["switch", "add", "commit", "head", "diff"])
@pytest.mark.parametrize("failure", ["missing-process", "nonzero-exit"])
def test_git_operational_failure_preserves_stage_and_partial_evidence(
    root, proposal, policy, monkeypatch, stage, failure
):
    original = workflow.subprocess.run
    operation = "rev-parse" if stage == "head" else stage

    def injected(args, **kwargs):
        if kwargs["cwd"] == root / "web" and operation in args and (root / "reviews").exists():
            if failure == "missing-process":
                raise FileNotFoundError("git unavailable")
            return subprocess.CompletedProcess(args, 128, "partial git output", "git failed")
        return original(args, **kwargs)

    monkeypatch.setattr(workflow.subprocess, "run", injected)
    record = run_demo(root, proposal, policy, "owner")
    assert record["state"] == "failed"
    assert [item["state"] for item in record["repositories"]] == [
        "succeeded",
        "failed",
        "unattempted",
        "unattempted",
    ]
    web = record["repositories"][1]
    assert web["stage"] == stage
    assert web["commands"][-1]["exit_code"] == (127 if failure == "missing-process" else 128)
    assert (root / web["failure_artifact"]).is_file()
    if stage == "diff":
        assert web["after_commit"] is not None
    else:
        assert web["after_commit"] is None
    assert record["reconciliation"]["verified"] is False
    assert record["reconciliation"]["state"] == "matched"


def test_review_storage_error_returns_in_memory_partial_evidence(
    root, proposal, policy, monkeypatch
):
    original = workflow._write

    def injected(path, text):
        if path == root / "reviews" / "web" / "test.json":
            raise OSError("review storage unavailable")
        return original(path, text)

    monkeypatch.setattr(workflow, "_write", injected)
    record = run_demo(root, proposal, policy, "owner")
    assert record["state"] == "failed"
    assert [item["state"] for item in record["repositories"]] == [
        "succeeded",
        "failed",
        "unattempted",
        "unattempted",
    ]
    assert record["repositories"][1]["stage"] == "review_artifacts"
    assert record["repositories"][1]["commands"]
    assert record["errors"]
    assert record["reconciliation"]["verified"] is False


@pytest.mark.parametrize(
    ("actor", "kind"), [("intruder", "human"), ("owner", "agent"), ("owner", "service")]
)
def test_denied_before_any_writes(root, proposal, policy, actor, kind):
    before = tree(root)
    with pytest.raises(ValueError, match="Authorization denied"):
        run_demo(root, proposal, policy, actor, actor_kind=kind)
    assert tree(root) == before


def test_deny_missing_policy_before_root_creation(tmp_path, proposal):
    root = tmp_path / "never-created"
    with pytest.raises(ValueError):
        run_demo(root, proposal, {}, "owner")
    assert not root.exists()


@pytest.mark.parametrize("field", ["state", "diff", "approval"])
def test_invalid_or_tampered_approval_before_writes(root, proposal, policy, field):
    before = tree(root)
    proposal[field] = None
    with pytest.raises(ValueError, match="valid, content-bound"):
        run_demo(root, proposal, policy, "owner")
    assert tree(root) == before


def test_run_actor_must_match_approval(root, proposal, policy):
    policy["humans"].append("other-owner")
    policy["permissions"]["approve_changes"].append("other-owner")
    before = tree(root)
    with pytest.raises(ValueError, match="match"):
        run_demo(root, proposal, policy, "other-owner")
    assert tree(root) == before


@pytest.mark.parametrize("mutation", ["missing-component", "extra-component", "unrelated", "empty"])
def test_reject_valid_approved_unrelated_or_unsupported_proposal(root, proposal, policy, mutation):
    candidate = copy.deepcopy(proposal)
    candidate["state"], candidate["approval"] = "proposed", None
    if mutation == "missing-component":
        candidate["impact"]["impacted"].pop()
    elif mutation == "extra-component":
        item = copy.deepcopy(candidate["impact"]["impacted"][0])
        item["id"] = "component.unrelated"
        candidate["impact"]["impacted"].append(item)
    elif mutation == "unrelated":
        item = candidate["diff"]["nodes"]["modified"][0]
        item["id"] = item["before"]["id"] = item["after"]["id"] = "requirement.unrelated"
    else:
        candidate["diff"]["nodes"]["modified"] = []
    candidate = approve_proposal(candidate, policy, "owner")
    before = tree(root)
    with pytest.raises(ValueError, match="offline-sync"):
        run_demo(root, candidate, policy, "owner")
    assert tree(root) == before


def test_intentional_failure_never_claims_pass(root, proposal, policy):
    record = run_demo(root, proposal, policy, "owner", fail_component="mobile")
    assert record["state"] == "failed"
    assert record["reconciliation"]["state"] == "matched"
    assert record["reconciliation"]["verified"] is False
    mobile = next(r for r in record["repositories"] if r["component"] == "mobile")
    assert mobile["state"] == "failed"
    assert mobile["test"]["exit_code"] != 0
    assert "Intentional demo failure" in mobile["test"]["stderr"]
    assert sum(r["state"] == "succeeded" for r in record["repositories"]) == 3
    # Editing only a failure report must not promote it to verified.
    record["state"] = "succeeded"
    mobile["state"] = "succeeded"
    mobile["test"]["exit_code"] = 0
    assert reconcile_demo(root, record)["verified"] is False


def test_init_refuses_existing_even_empty(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        init_demo(existing)
    assert list(existing.iterdir()) == []


@pytest.mark.parametrize("target", ["test_contract.py", ".git/config", "untracked.txt"])
def test_refuse_drift_before_executing_mutated_source(root, proposal, policy, target, tmp_path):
    sentinel = tmp_path / "must-not-execute"
    (root / "backend" / target).write_text(
        f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\n"
    )
    before = tree(root)
    with pytest.raises(ValueError, match="changed or dirty"):
        run_demo(root, proposal, policy, "owner")
    assert not sentinel.exists()
    assert tree(root) == before


@pytest.mark.parametrize("target", ["backend", "backend/test_contract.py", MARKER])
def test_symlink_tampering_refused(root, proposal, policy, tmp_path, target):
    victim = root / target
    outside = tmp_path / "outside"
    victim.rename(outside)
    victim.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(ValueError, match="symlink|unsafe"):
        run_demo(root, proposal, policy, "owner")


def test_init_refuses_symlink_parent(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / "link"
    link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        init_demo(link / "demo")
    assert not (actual / "demo").exists()


def test_copied_root_and_changed_marker_refused(root, proposal, policy, tmp_path):
    copied = tmp_path / "copied"
    shutil.copytree(root, copied)
    with pytest.raises(ValueError, match="marker"):
        run_demo(copied, proposal, policy, "owner")
    path = root / MARKER
    marker = json.loads(path.read_text())
    marker["heads"]["backend"] = "0" * 40
    path.write_text(json.dumps(marker))
    with pytest.raises(ValueError, match="marker"):
        run_demo(root, proposal, policy, "owner")


@pytest.mark.parametrize("target", ["test_evil.py", "test_contract.py", ".git/config"])
def test_rehashed_marker_does_not_authorize_mutated_executable(
    root, proposal, policy, target, tmp_path
):
    sentinel = tmp_path / "never"
    (root / "backend" / target).write_text(
        f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\n"
    )
    marker = json.loads((root / MARKER).read_text())
    marker.pop("content_digest")
    marker["initial_files"] = workflow._snapshot(root)
    marker["content_digest"] = hashlib.sha256(workflow._json(marker).encode()).hexdigest()
    (root / MARKER).write_text(workflow._json(marker))
    with pytest.raises(ValueError, match="fixed|fixtures|configuration"):
        run_demo(root, proposal, policy, "owner")
    assert not sentinel.exists()


def test_marker_non_object_refused(root, proposal, policy):
    (root / MARKER).write_text("[]")
    with pytest.raises(ValueError, match="marker"):
        run_demo(root, proposal, policy, "owner")


@pytest.mark.parametrize(
    "target", ["backend/contract.py", "backend/new.txt", "reviews/backend/test.json", MARKER]
)
def test_reconcile_drift(root, proposal, policy, target):
    record = run_demo(root, proposal, policy, "owner")
    (root / target).write_text("tampered\n")
    result = reconcile_demo(root, record)
    assert result["state"] == "drifted"
    assert result["verified"] is False
    assert result["errors"]


def test_reconcile_head_change(root, proposal, policy):
    record = run_demo(root, proposal, policy, "owner")
    (root / "backend" / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    assert reconcile_demo(root, record)["state"] == "drifted"


def test_reconcile_symlink_and_record_path_tamper(root, proposal, policy, tmp_path):
    record = run_demo(root, proposal, policy, "owner")
    record["repositories"][0]["path"] = "../outside"
    assert reconcile_demo(root, record)["verified"] is False
    record["repositories"][0]["path"] = "backend"
    outside = tmp_path / "outside"
    outside.write_text("unchanged")
    (root / "backend" / "extra").symlink_to(outside)
    assert reconcile_demo(root, record)["verified"] is False
    assert outside.read_text() == "unchanged"


def test_git_environment_ignores_overrides(root, proposal, policy, monkeypatch, tmp_path):
    fake_git = tmp_path / "unrelated"
    fake_git.mkdir()
    monkeypatch.setenv("GIT_DIR", str(fake_git))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.worktree")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(tmp_path))
    record = run_demo(root, proposal, policy, "owner")
    assert record["state"] == "succeeded"
    assert list(fake_git.iterdir()) == []
