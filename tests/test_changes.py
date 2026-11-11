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


def test_redacted_identity_collision_is_rejected_not_silently_merged():
    before, after = inputs()
    for identifier in ("ghp_abcdefghijk", "ghp_lmnopqrstuv"):
        node = copy.deepcopy(before["nodes"][1])
        node["id"] = identifier
        before["nodes"].append(node)
        modified = copy.deepcopy(node)
        modified["title"] = "Modified"
        after["nodes"].append(modified)
    with pytest.raises(ValueError, match="identifiers must remain stable"):
        create_proposal(before, after)


def evidence_model(edge=False):
    model, _ = inputs()
    component = copy.deepcopy(model["nodes"][1])
    component.update(id="c", evidence=["e"], confidence=0.7)
    component["provenance"]["verification"] = "verified"
    evidence = {
        "id": "e",
        "type": "evidence",
        "title": "Test evidence",
        "version": 1,
        "uri": "file:test",
        "provenance": {"origin": "declared", "source": "fixture", "verification": "unverified"},
    }
    model["nodes"] = [component, evidence]
    model["edges"] = []
    if edge:
        component.pop("evidence")
        component["provenance"]["verification"] = "unverified"
        other = copy.deepcopy(component)
        other["id"] = "d"
        model["nodes"].append(other)
        model["edges"] = [
            {
                "id": "edge.cd",
                "type": "depends_on",
                "source": "c",
                "target": "d",
                "evidence": ["e"],
                "provenance": copy.deepcopy(evidence["provenance"]),
            }
        ]
    return model


@pytest.mark.parametrize("edge", [False, True])
def test_evidence_impact_paths_and_trust(edge):
    model = evidence_model(edge)
    original = copy.deepcopy(model)
    impact = analyze_impact(model, ["e"])
    impacted = {item["id"]: item for item in impact["impacted"]}
    token = 'evidence:["edge","edge.cd","e"]' if edge else 'evidence:["node","c","e"]'
    assert impacted["c"]["via"] == [token]
    if edge:
        assert impacted["d"]["via"] == [token]
        assert analyze_impact(model, ["c"])["impacted"][1]["via"] == ["edge.cd"]
    assert impacted["e"]["verification"] == "unverified"
    assert impacted["c"]["verification"] == ("unverified" if edge else "verified")
    assert impacted["c"]["confidence"] == 0.7
    assert impacted["c"]["origin"] == "declared"
    assert model == original
    reverse = {item["id"]: item for item in analyze_impact(model, ["c"])["impacted"]}
    assert reverse["e"]["via"] == [token]


def test_shared_cyclic_evidence_is_deterministic():
    model = evidence_model()
    other = copy.deepcopy(model["nodes"][1])
    other.update(id="f", evidence=["e"])
    model["nodes"][1]["evidence"] = ["f"]
    model["nodes"][0]["evidence"].append("f")
    model["nodes"].append(other)
    impact = analyze_impact(model, ["e", "e"])
    assert len(impact["impacted"]) == 3
    assert impact["impacted"][0]["via"] == ['evidence:["node","c","e"]']
    model["nodes"].reverse()
    for node in model["nodes"]:
        node.get("evidence", []).reverse()
    assert analyze_impact(model, ["e"]) == impact


@pytest.mark.parametrize("edge", [False, True])
@pytest.mark.parametrize("operation", ["modified", "removed", "added"])
def test_proposal_evidence_changes_use_both_snapshots(edge, operation):
    before = evidence_model(edge)
    after = copy.deepcopy(before)
    if operation == "modified":
        after["nodes"][1]["uri"] = "file:changed"
    else:
        after["nodes"].pop(1)
        if edge:
            after["edges"][0].pop("evidence")
        else:
            after["nodes"][0].pop("evidence")
            after["nodes"][0]["provenance"]["verification"] = "unverified"
        if operation == "added":
            before, after = after, before
    proposal = create_proposal(before, after)
    assert validate_proposal(proposal) == []
    impacted = {item["id"]: item for item in proposal["impact"]["impacted"]}
    assert {"c", "e"} <= impacted.keys()
    if edge:
        assert "d" in impacted
    if operation == "modified":
        assert impacted["c"]["via"]
    assert proposal["state"] == "proposed"
    assert proposal["approval"] is None
    assert proposal["impact"]["unknown_impact"] is True
