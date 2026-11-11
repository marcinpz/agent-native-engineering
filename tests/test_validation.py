import copy

import pytest

from lsm.validation import validate_model


def provenance(verification="unverified"):
    return {"origin": "declared", "source": "test fixture", "verification": verification}


def node(identifier, kind="component", **extra):
    value = {
        "id": identifier,
        "type": kind,
        "title": identifier,
        "version": 1,
        "provenance": provenance(),
    }
    if kind == "requirement":
        value.update(acceptance_criteria=["The acceptance criterion holds"], approval="pending")
    if kind == "evidence":
        value["uri"] = "https://example.org/evidence"
    value.update(extra)
    return value


def edge(identifier, kind, source, target, **extra):
    return {
        "id": identifier,
        "type": kind,
        "source": source,
        "target": target,
        "provenance": provenance(),
        **extra,
    }


def model(nodes=None, edges=None):
    return {
        "schema_version": "1.0",
        "model": {"id": "fixture", "title": "Fixture"},
        "nodes": nodes or [],
        "edges": edges or [],
    }


def codes(value):
    return {error["code"] for error in validate_model(value)}


def test_empty_model_is_valid_and_not_mutated():
    value = model()
    before = copy.deepcopy(value)
    assert validate_model(value) == []
    assert value == before


@pytest.mark.parametrize(
    "kind",
    [
        "requirement",
        "domain_concept",
        "behavior",
        "component",
        "interface",
        "repository",
        "decision",
        "implementation",
        "test",
        "evidence",
    ],
)
def test_all_node_types(kind):
    assert validate_model(model([node("a", kind)])) == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(unexpected=True),
        lambda value: value["nodes"][0].update(unexpected=True),
        lambda value: value["nodes"][0].update(id="BAD ID"),
        lambda value: value["nodes"][0].update(version=0),
        lambda value: value["nodes"][0].update(version=True),
        lambda value: value["nodes"][0].update(timestamp="not-a-timestamp"),
        lambda value: value["nodes"][0].update(confidence=1.1),
        lambda value: value["nodes"][0].update(type="unknown"),
        lambda value: value["nodes"][0]["provenance"].update(origin="imagined"),
    ],
)
def test_schema_rejections(mutate):
    value = model([node("a")])
    mutate(value)
    assert "schema_error" in codes(value)


def test_requirement_requires_criteria_and_approval():
    value = model([node("a", "requirement")])
    del value["nodes"][0]["acceptance_criteria"]
    del value["nodes"][0]["approval"]
    assert "schema_error" in codes(value)


def test_timestamp_format_and_evidence_uri():
    assert not validate_model(model([node("a", "evidence", timestamp="2026-11-11T12:00:00Z")]))
    value = model([node("a", "evidence")])
    del value["nodes"][0]["uri"]
    assert "schema_error" in codes(value)


def test_unsupported_version_has_explicit_diagnostic():
    value = model()
    value["schema_version"] = "2.0"
    assert any(
        error["code"] == "unsupported_schema_version" and error["path"] == "/schema_version"
        for error in validate_model(value)
    )


def test_node_and_edge_ids_share_namespace():
    value = model([node("a"), node("a")], [edge("a", "depends_on", "a", "a")])
    duplicates = [error for error in validate_model(value) if error["code"] == "duplicate_id"]
    assert {error["path"] for error in duplicates} == {"/nodes/1/id", "/edges/0/id"}


def test_duplicate_edge_ids():
    value = model(
        [node("a")],
        [
            edge("e", "depends_on", "a", "a"),
            edge("e", "depends_on", "a", "a"),
        ],
    )
    assert "duplicate_id" in codes(value)


def test_missing_endpoints_and_edge_is_not_node():
    value = model([], [edge("e", "depends_on", "missing", "e")])
    errors = [error for error in validate_model(value) if error["code"] == "missing_endpoint"]
    assert {error["path"] for error in errors} == {"/edges/0/source", "/edges/0/target"}


@pytest.mark.parametrize(
    "kind,source_type,target_type",
    [
        ("satisfies", "behavior", "requirement"),
        ("depends_on", "repository", "interface"),
        ("implemented_by", "requirement", "component"),
        ("verified_by", "implementation", "test"),
        ("verified_by", "requirement", "evidence"),
        ("supersedes", "domain_concept", "domain_concept"),
        ("exposes", "component", "interface"),
        ("decided_by", "test", "decision"),
        ("belongs_to", "test", "repository"),
    ],
)
def test_allowed_relation_endpoints(kind, source_type, target_type):
    value = model([node("a", source_type), node("b", target_type)], [edge("e", kind, "a", "b")])
    assert validate_model(value) == []


@pytest.mark.parametrize(
    "kind,source_type,target_type",
    [
        ("satisfies", "requirement", "component"),
        ("depends_on", "evidence", "component"),
        ("implemented_by", "evidence", "implementation"),
        ("verified_by", "component", "implementation"),
        ("supersedes", "component", "interface"),
        ("exposes", "interface", "component"),
        ("decided_by", "evidence", "decision"),
        ("decided_by", "component", "test"),
        ("belongs_to", "repository", "component"),
    ],
)
def test_disallowed_relation_endpoints(kind, source_type, target_type):
    value = model([node("a", source_type), node("b", target_type)], [edge("e", kind, "a", "b")])
    assert "invalid_relation_endpoints" in codes(value)


@pytest.mark.parametrize("relation,forbidden", [("depends_on", False), ("supersedes", True)])
@pytest.mark.parametrize("self_loop", [False, True])
def test_only_supersedes_cycles_are_forbidden(relation, forbidden, self_loop):
    edges = [edge("e1", relation, "a", "a" if self_loop else "b")]
    if not self_loop:
        edges.append(edge("e2", relation, "b", "a"))
    value = model([node("a"), node("b")], edges)
    assert ("supersedes_cycle" in codes(value)) is forbidden
    if not forbidden:
        assert validate_model(value) == []


def test_long_supersedes_chain_is_not_recursive():
    value = model(
        [node(f"n{i}") for i in range(1100)],
        [edge(f"e{i}", "supersedes", f"n{i}", f"n{i + 1}") for i in range(1099)],
    )
    assert validate_model(value) == []


@pytest.mark.parametrize("entity_kind", ["node", "edge"])
def test_verified_claims_require_evidence(entity_kind):
    value = model([node("a"), node("proof", "evidence")], [edge("e", "depends_on", "a", "a")])
    entity = value["nodes"][0] if entity_kind == "node" else value["edges"][0]
    entity["provenance"] = provenance("verified")
    assert "evidence_required" in codes(value)
    entity["evidence"] = []
    assert "evidence_required" in codes(value)
    entity["evidence"] = ["proof"]
    assert validate_model(value) == []


def test_evidence_itself_cannot_claim_verified_without_evidence():
    value = model([node("proof", "evidence", provenance=provenance("verified"))])
    assert "evidence_required" in codes(value)


@pytest.mark.parametrize("entity_kind", ["node", "edge"])
def test_evidence_references_must_exist_and_be_evidence_nodes(entity_kind):
    value = model([node("a")], [edge("e", "depends_on", "a", "a")])
    entity = value["nodes"][0] if entity_kind == "node" else value["edges"][0]
    entity["evidence"] = ["missing", "a", "e"]
    assert {"missing_evidence", "invalid_evidence_type"} <= codes(value)


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        [],
        "model",
        7,
        {},
        {"nodes": {}, "edges": "edges"},
        {"nodes": [None, 1, [], {"id": []}, {"id": {}}], "edges": [None, False, []]},
        {
            "nodes": [{"id": "a", "type": [], "provenance": [], "evidence": {}}],
            "edges": [{"source": [], "target": {}, "type": []}],
        },
        {
            "nodes": [{"id": "a", "type": {}}, {"id": "b", "type": []}],
            "edges": [{"source": "a", "target": "b", "type": {}}],
        },
        {"nodes": [{"id": "a", "provenance": {"verification": "verified"}, "evidence": [[], {}]}]},
    ],
)
def test_invalid_shapes_return_diagnostics_without_crashing(invalid):
    assert validate_model(invalid)


def test_diagnostics_are_structured_deterministic_and_sorted():
    value = model([node("a", evidence=["missing"]), node("a")], [edge("e", "exposes", "x", "a")])
    errors = validate_model(value)
    assert errors == validate_model(copy.deepcopy(value))
    assert errors == sorted(errors, key=lambda item: (item["path"], item["code"], item["message"]))
    assert all(set(error) == {"code", "path", "message"} for error in errors)
    assert all(error["path"] == "" or error["path"].startswith("/") for error in errors)


def test_schema_diagnostic_path_uses_json_pointer_escaping():
    value = model([node("a")])
    value["nodes"][0]["provenance"]["source"] = 42
    assert any(error["path"] == "/nodes/0/provenance/source" for error in validate_model(value))
