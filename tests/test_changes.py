import copy

import pytest

from lsm.changes import (
    analyze_impact,
    approve_proposal,
    create_proposal,
    model_digest,
    semantic_diff,
    validate_proposal,
)
from lsm.storage import load_model


def inputs():
    return load_model("examples/changes/before.json"), load_model(
        "examples/changes/offline-sync.json"
    )


def test_offline_sync_impact_is_explained_and_cross_repository():
    before, after = inputs()
    proposal = create_proposal(before, after)
    assert validate_proposal(proposal) == []
    impact = proposal["impact"]
    assert {"component.mobile", "component.backend", "component.store", "test.offline-sync"} <= {
        item["id"] for item in impact["impacted"]
    }
    assert len(impact["repositories"]) == 4
    assert impact["unknown_impact"] is True
    assert all(
        item["via"] for item in impact["impacted"] if item["id"] != "requirement.offline-sync"
    )
    assert proposal["state"] == "proposed"
    assert len(proposal["diff"]["nodes"]["modified"]) == 1


def test_semantic_order_and_repeat_invariance():
    before, after = inputs()
    reversed_model = copy.deepcopy(before)
    reversed_model["nodes"].reverse()
    reversed_model["edges"].reverse()
    assert semantic_diff(before, reversed_model)["nodes"]["modified"] == []
    assert model_digest(before) == model_digest(reversed_model)
    assert create_proposal(before, after) == create_proposal(reversed_model, after)


def test_removed_edge_still_impacts_old_endpoints():
    before, after = inputs()
    after = copy.deepcopy(before)
    after["edges"] = [edge for edge in after["edges"] if edge["id"] != "edge.mobile-backend"]
    proposal = create_proposal(before, after)
    assert "component.mobile" in proposal["impact"]["seeds"]
    assert "component.backend" in proposal["impact"]["seeds"]


def test_approval_is_human_and_bound_to_content():
    proposal = create_proposal(*inputs())
    policy = load_model("examples/governance/policy.json")
    with pytest.raises(ValueError, match="denied"):
        approve_proposal(proposal, policy, "demo-owner", "agent")
    approved = approve_proposal(proposal, policy, "demo-owner")
    assert validate_proposal(approved) == []
    assert proposal["state"] == "proposed"
    approved["risks"].append("Another risk")
    assert validate_proposal(approved)[0]["code"] == "approval_mismatch"


def test_unrelated_nodes_not_affected_and_unknown_seed_fails():
    before, _ = inputs()
    unrelated = copy.deepcopy(before["nodes"][1])
    unrelated["id"] = "component.unrelated"
    before["nodes"].append(unrelated)
    impact = analyze_impact(before, ["component.mobile"])
    assert "component.unrelated" not in {node["id"] for node in impact["impacted"]}
    with pytest.raises(ValueError, match="Unknown"):
        analyze_impact(before, ["missing"])
    with pytest.raises(ValueError):
        create_proposal({}, {})


def test_secret_redaction_and_malformed_approval():
    before, after = inputs()
    after["nodes"][0]["description"] = "token=hidden-value"
    proposal = create_proposal(before, after)
    assert "hidden-value" not in str(proposal)
    proposal["state"] = "approved"
    assert validate_proposal(proposal)
    assert validate_proposal([])


def test_no_changes_and_metadata_changes():
    before, _ = inputs()
    assert create_proposal(before, before)["impact"]["impacted"] == []
    after = copy.deepcopy(before)
    after["model"]["title"] = "Renamed"
    assert len(create_proposal(before, after)["impact"]["impacted"]) == len(before["nodes"])
