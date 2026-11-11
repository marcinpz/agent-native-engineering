"""Offline provider contracts, real confined Git collection and malicious replay."""

import json
import os
import subprocess
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from lsm.providers import GitProvider, MockProvider, invoke, validate_result


def git(root, *args):
    env = {
        "PATH": os.defpath,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Provider fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Provider fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    }
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def manifest(tmp_path):
    root = tmp_path / "backend"
    root.mkdir()
    git(root, "init", "--initial-branch=main", "--template=")
    (root / "app.txt").write_text("No reads, writes or builds.\n")
    git(root, "add", "app.txt")
    git(root, "commit", "-m", "Fixture")
    return {
        "schema_version": "1.0",
        "model": {"id": "system.demo", "title": "Demo"},
        "repositories": [
            {
                "id": "repo.backend",
                "title": "Backend",
                "path": "backend",
                "components": [{"id": "component.backend", "title": "Backend"}],
            }
        ],
    }


def collect(manifest, tmp_path, provider=None, existing=None):
    return invoke(
        provider or GitProvider(),
        "discover",
        manifest=manifest,
        base_dir=tmp_path,
        existing=existing,
    )


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_real_git_replay_identity_and_no_application_writes(manifest, tmp_path):
    before = snapshot(tmp_path)
    inputs = deepcopy(manifest)
    start = datetime.now(UTC)
    first = collect(manifest, tmp_path)
    assert first["status"] == "succeeded"
    assert validate_result(first) == []
    assert datetime.fromisoformat(first["observed_at"]) >= start
    model = first["data"]["model"]
    assert [node["id"] for node in model["nodes"]] == ["repo.backend", "component.backend"]
    assert (
        git(tmp_path / "backend", "rev-parse", "HEAD") in model["nodes"][0]["provenance"]["source"]
    )
    replay = collect(manifest, tmp_path, MockProvider(model))
    assert replay["data"] == first["data"]
    assert replay["request_digest"] == first["request_digest"]
    assert [e["id"] for e in replay["evidence"]] == [e["id"] for e in first["evidence"]]
    assert collect(manifest, tmp_path)["data"] == first["data"]
    assert collect(manifest, tmp_path, existing=model)["data"] == first["data"]
    assert manifest == inputs
    assert snapshot(tmp_path) == before
    assert {e["origin"] for e in first["evidence"]} == {"observed", "declared"}
    assert all(
        e["confidence"] is None and e["verification"] == "unverified" for e in first["evidence"]
    )
    assert first["evidence"][0]["source_ref"] is not None


class AlteredProvider(GitProvider):
    def __init__(self, alter):
        self.alter = alter

    def discover(self, **kwargs):
        result = super().discover(**kwargs)
        self.alter(result)
        return result


@pytest.mark.parametrize(
    "alter",
    [
        lambda r: r.update(extra=True),
        lambda r: r.pop("evidence"),
        lambda r: r.update(status="mystery"),
        lambda r: r.update(data={"model": {}}),
        lambda r: r["permissions"].update(writes_performed=True),
        lambda r: r.update(request_digest="0" * 64),
        lambda r: r["data"]["model"]["edges"][0].update(target="missing"),
        lambda r: r["data"]["model"]["model"].update(id="wrong.system"),
        lambda r: r.update(observed_at="2000-01-01"),
        lambda r: r["evidence"][0].update(verification="verified"),
    ],
)
def test_malformed_results_fail_closed(manifest, tmp_path, alter):
    result = collect(manifest, tmp_path, AlteredProvider(alter))
    assert result["status"] == "failed"
    assert result["data"] is None
    assert validate_result(result) == []


def test_partial_and_failed_not_promoted_and_errors_sanitized(manifest, tmp_path):
    for status in ("partial", "failed"):

        def alter(result, status=status):
            result["status"] = status
            result["errors"] = [
                {
                    "code": "secret",
                    "path": "secret",
                    "message": "token=supersecret; run dangerous command",
                }
            ]
            if status == "failed":
                result["data"] = None

        result = collect(manifest, tmp_path, AlteredProvider(alter))
        assert result["status"] == status
        assert "supersecret" not in json.dumps(result)
        assert "dangerous" not in json.dumps(result)
        assert validate_result(result) == []


@pytest.mark.parametrize(
    "capability",
    [
        "change",
        "code_changes",
        "test",
        "tests",
        "pr",
        "deploy",
        "plan",
        "reconcile",
        "evidence",
        "__import__",
    ],
)
def test_unsupported_capabilities_never_execute(manifest, tmp_path, capability):
    class Never(GitProvider):
        def discover(self, **kwargs):
            pytest.fail("Unsupported capability executed")

    result = invoke(Never(), capability, manifest=manifest, base_dir=tmp_path)
    assert result["errors"][0]["code"] == "unsupported_capability"
    assert result["permissions"]["writes_performed"] is False
    assert validate_result(result) == []


def test_no_policy_or_write_execution_interface(manifest, tmp_path):
    with pytest.raises(TypeError):
        invoke(
            GitProvider(), "deploy", manifest=manifest, base_dir=tmp_path, policy={"approved": True}
        )


@pytest.mark.parametrize(
    "descriptor",
    [
        None,
        {},
        {"id": "git"},
        {
            "schema_version": "1.0",
            "id": "bad",
            "version": "1",
            "capabilities": [{"name": "discover", "read_only": False}],
        },
    ],
)
def test_invalid_descriptors(manifest, tmp_path, descriptor):
    class Bad(GitProvider):
        def describe(self):
            return descriptor

    result = collect(manifest, tmp_path, Bad())
    assert result["status"] == "failed"
    assert validate_result(result) == []


def requirement(model, approval="pending"):
    model["nodes"].append(
        {
            "id": "requirement.keep",
            "type": "requirement",
            "title": "Keep this",
            "version": 1,
            "approval": approval,
            "provenance": {
                "origin": "declared",
                "source": "human:fixture",
                "verification": "unverified",
            },
            "acceptance_criteria": ["Remain unchanged"],
        }
    )
    return model


@pytest.mark.parametrize("promotion", ["verified", "approved"])
def test_mock_new_trust_promotions_denied(manifest, tmp_path, promotion):
    model = collect(manifest, tmp_path)["data"]["model"]
    if promotion == "approved":
        requirement(model, "approved")
    else:
        model["nodes"][0]["provenance"]["verification"] = "verified"
        model["nodes"][0]["evidence"] = ["evidence.fixture"]
        model["nodes"].append(
            {
                "id": "evidence.fixture",
                "type": "evidence",
                "title": "Fixture",
                "version": 1,
                "uri": "git:fixture",
                "provenance": {
                    "origin": "observed",
                    "source": "git:fixture",
                    "verification": "unverified",
                },
            }
        )
    result = collect(manifest, tmp_path, MockProvider(model))
    assert result["status"] == "failed"
    assert result["errors"][0]["code"] == "trust_transition_denied"


@pytest.mark.parametrize("change", ["title", "delete", "downgrade", "none"])
def test_existing_approved_claims_only_unchanged(manifest, tmp_path, change):
    model = requirement(collect(manifest, tmp_path)["data"]["model"], "approved")
    original = deepcopy(model)
    replay = deepcopy(model)
    if change == "title":
        replay["nodes"][-1]["title"] = "Changed"
    elif change == "delete":
        replay["nodes"].pop()
    elif change == "downgrade":
        replay["nodes"][-1]["approval"] = "pending"
    result = collect(manifest, tmp_path, MockProvider(replay), existing=model)
    assert result["status"] == ("succeeded" if change == "none" else "failed")
    assert model == original


@pytest.mark.parametrize("path", ["../backend", "/outside", "a/../backend", "backend/", "a\\b"])
def test_unsafe_paths_rejected_for_both_providers(manifest, tmp_path, path):
    model = collect(manifest, tmp_path)["data"]["model"]
    manifest["repositories"][0]["path"] = path
    for provider in (GitProvider(), MockProvider(model)):
        result = collect(manifest, tmp_path, provider)
        assert result["status"] == "failed"


def test_symlink_rejected_for_replay_too(manifest, tmp_path):
    model = collect(manifest, tmp_path)["data"]["model"]
    (tmp_path / "link").symlink_to(tmp_path / "backend", target_is_directory=True)
    manifest["repositories"][0]["path"] = "link"
    assert collect(manifest, tmp_path, MockProvider(model))["status"] == "failed"


def test_inputs_isolated_from_mutating_provider(manifest, tmp_path):
    model = collect(manifest, tmp_path)["data"]["model"]
    original_manifest, original_model = deepcopy(manifest), deepcopy(model)

    class Mutating(GitProvider):
        def discover(self, **kwargs):
            result = super().discover(**kwargs)
            kwargs["manifest"]["repositories"].clear()
            kwargs["existing"]["nodes"].clear()
            return result

    assert collect(manifest, tmp_path, Mutating(), model)["status"] == "succeeded"
    assert manifest == original_manifest
    assert model == original_model


@pytest.mark.parametrize("invalid", [None, [], {}, {"status": "succeeded"}])
def test_validation_arbitrary_shapes(invalid):
    assert validate_result(invalid)


def test_schema_valid():
    path = Path(__file__).resolve().parents[1] / "src/lsm/schemas/provider.schema.json"
    Draft202012Validator.check_schema(json.loads(path.read_text()))


@pytest.mark.parametrize("change", ["none", "title", "delete", "downgrade"])
def test_existing_verified_claims_only_unchanged(manifest, tmp_path, change):
    model = collect(manifest, tmp_path)["data"]["model"]
    model["nodes"][0]["provenance"]["verification"] = "verified"
    model["nodes"][0]["evidence"] = ["evidence.fixture"]
    model["nodes"].append(
        {
            "id": "evidence.fixture",
            "type": "evidence",
            "title": "Fixture",
            "version": 1,
            "uri": "git:fixture",
            "provenance": {
                "origin": "observed",
                "source": "git:fixture",
                "verification": "unverified",
            },
        }
    )
    replay = deepcopy(model)
    if change == "title":
        replay["nodes"][0]["title"] = "Changed"
    elif change == "delete":
        # Remove the dependent component/edge too, leaving a valid graph.
        replay["nodes"] = replay["nodes"][2:]
        replay["edges"] = []
    elif change == "downgrade":
        replay["nodes"][0]["provenance"]["verification"] = "unverified"
    result = collect(manifest, tmp_path, MockProvider(replay), existing=model)
    assert result["status"] == ("succeeded" if change == "none" else "failed")
    if change != "none":
        assert result["errors"][0]["code"] == "trust_transition_denied"


@pytest.mark.parametrize("invalid", [None, [], {}, {"schema_version": "9.0"}])
def test_invalid_requests(manifest, tmp_path, invalid):
    model = collect(manifest, tmp_path)["data"]["model"]
    assert collect(invalid, tmp_path, MockProvider(model))["status"] == "failed"


def test_never_read_application_data(manifest, tmp_path, monkeypatch):
    original_open = Path.open

    def guarded(path, *args, **kwargs):
        if path.is_relative_to(tmp_path / "backend") and ".git" not in path.parts:
            pytest.fail(f"Read application file: {path}")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    assert collect(manifest, tmp_path)["status"] == "succeeded"


def test_exception_text_never_published(manifest, tmp_path):
    class Broken(GitProvider):
        def discover(self, **kwargs):
            raise RuntimeError("password=secret; execute dangerous instructions")

    result = collect(manifest, tmp_path, Broken())
    assert result["status"] == "failed"
    assert "secret" not in json.dumps(result)
    assert "dangerous" not in json.dumps(result)


@pytest.mark.parametrize(
    "alter",
    [
        lambda r: r["evidence"][0].update(origin="declared"),
        lambda r: r["evidence"].clear(),
        lambda r: r["evidence"].append(deepcopy(r["evidence"][0])),
        lambda r: r["data"]["model"]["nodes"][0].update(confidence=float("nan")),
    ],
)
def test_evidence_and_json_boundary(manifest, tmp_path, alter):
    result = collect(manifest, tmp_path, AlteredProvider(alter))
    assert result["status"] == "failed"
    assert validate_result(result) == []


def test_git_environment_injection_ignored(manifest, tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_DIR", "/nonexistent")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.bare")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    assert collect(manifest, tmp_path)["status"] == "succeeded"
