import copy

import pytest

from lsm.migrations import migrate_model
from lsm.security import check_transition, redact, require_authorization
from lsm.storage import load_model, save_model
from lsm.validation import validate_model


def test_migration_fixture_and_no_mutation():
    original = load_model("examples/governance/model-1.0.json")
    snapshot = copy.deepcopy(original)
    upgraded = migrate_model(original)
    assert upgraded == load_model("examples/governance/model-1.1.json")
    assert original == snapshot
    assert migrate_model(upgraded) == upgraded
    with pytest.raises(ValueError, match="Downgrades"):
        migrate_model(upgraded, "1.0")
    with pytest.raises(ValueError):
        migrate_model(original, "2.0")
    with pytest.raises(ValueError):
        migrate_model({})


def test_migration_preserves_ids_provenance_and_roundtrip(tmp_path):
    original = load_model("examples/shop.json")
    upgraded = migrate_model(original)
    assert upgraded["nodes"] == original["nodes"]
    assert upgraded["edges"] == original["edges"]
    upgraded["governance"] = {"owners": ["demo-owner"], "policy_uri": "policy.json"}
    assert validate_model(upgraded) == []
    for suffix in ("json", "yaml"):
        path = tmp_path / f"model.{suffix}"
        save_model(upgraded, path)
        assert load_model(path) == upgraded
    upgraded["governance"]["owners"] = []
    assert validate_model(upgraded)


def test_redaction_recursive_and_nonmutating():
    raw = {
        "api_key": "hidden",
        "nested": ["ghp_abcdefghijklmnop", "Bearer abcdef.123", "password=hello"],
        "uri": "https://alice:password@example.com/path?token=abc",
        "key": "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----",
        "okay": "requirement.notes",
    }
    result = redact(raw)
    assert result["api_key"] == "[REDACTED]"
    assert all(item == "[REDACTED]" for item in result["nested"])
    assert "password" not in result["uri"]
    assert "secret" not in result["key"]
    assert result["okay"] == "requirement.notes"
    assert raw["api_key"] == "hidden"


@pytest.mark.parametrize("kind,actor", [("agent", "demo-owner"), ("human", "unknown")])
def test_policy_default_deny(kind, actor):
    policy = load_model("examples/governance/policy.json")
    with pytest.raises(ValueError, match="denied"):
        require_authorization(policy, actor, "approve_changes", kind)
    require_authorization(policy, "demo-owner", "approve_changes")


def test_trust_promotions_edits_and_removals_require_authorization():
    original = load_model("examples/shop.json")
    modified = copy.deepcopy(original)
    requirement = next(node for node in modified["nodes"] if node["type"] == "requirement")
    requirement["approval"] = "approved"
    policy = load_model("examples/governance/policy.json")
    with pytest.raises(ValueError, match="denied"):
        check_transition(original, modified, policy, "agent", "agent")
    assert check_transition(original, modified, policy, "demo-owner") == modified
    edited = copy.deepcopy(modified)
    next(node for node in edited["nodes"] if node["id"] == requirement["id"])["title"] = "Changed"
    with pytest.raises(ValueError, match="denied"):
        check_transition(modified, edited, policy, "unknown")
    evidence = next(node for node in edited["nodes"] if node["type"] == "evidence")
    component = next(node for node in edited["nodes"] if node["type"] == "component")
    component["provenance"]["verification"] = "verified"
    component["evidence"] = [evidence["id"]]
    with pytest.raises(ValueError, match="denied"):
        check_transition(original, edited, policy, "demo-owner", "agent")
    assert check_transition(original, edited, policy, "demo-owner") == edited


@pytest.mark.parametrize(
    "policy", [{}, {"version": "1.0", "humans": [], "permissions": {"all": []}}]
)
def test_malformed_policy_denied(policy):
    with pytest.raises(ValueError):
        require_authorization(policy, "any", "approve_changes")
