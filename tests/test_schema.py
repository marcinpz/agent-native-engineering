"""Exercise the portable schema directly, independently of graph validation."""

import json
from copy import deepcopy
from importlib.resources import files
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(files("lsm").joinpath("schemas/model.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


@pytest.fixture
def model():
    return json.loads((ROOT / "examples/shop.json").read_text())


def node(model, kind):
    return next(item for item in model["nodes"] if item["type"] == kind)


def test_schema_and_fixture(model):
    Draft202012Validator.check_schema(SCHEMA)
    VALIDATOR.validate(model)
    assert {item["type"] for item in model["nodes"]} == set(
        SCHEMA["$defs"]["node"]["properties"]["type"]["enum"]
    )
    assert {item["type"] for item in model["edges"]} == set(
        SCHEMA["$defs"]["edge"]["properties"]["type"]["enum"]
    )
    assert all(
        item["provenance"]["verification"] == "unverified"
        for item in model["nodes"] + model["edges"]
    )
    artifact = ROOT / node(model, "evidence")["uri"]
    assert "not an execution record" in artifact.read_text()
    assert node(model, "implementation")["provenance"]["origin"] == "inferred"


def test_empty_model_is_valid():
    VALIDATOR.validate(
        {
            "schema_version": "1.0",
            "model": {"id": "empty", "title": "Empty"},
            "nodes": [],
            "edges": [],
        }
    )


@pytest.mark.parametrize("field", ["schema_version", "model", "nodes", "edges"])
def test_document_fields_required(model, field):
    del model[field]
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize("field", ["id", "type", "title", "version", "provenance"])
def test_node_fields_required(model, field):
    del model["nodes"][0][field]
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize("field", ["id", "type", "source", "target", "provenance"])
def test_edge_fields_required(model, field):
    del model["edges"][0][field]
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize("field", ["origin", "source", "verification"])
def test_provenance_fields_required(model, field):
    del model["nodes"][0]["provenance"][field]
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize("location", ["document", "model", "node", "edge", "provenance"])
def test_objects_are_closed(model, location):
    objects = {
        "document": model,
        "model": model["model"],
        "node": model["nodes"][0],
        "edge": model["edges"][0],
        "provenance": model["nodes"][0]["provenance"],
    }
    objects[location]["unexpected"] = True
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", ""),
        ("id", "Uppercase"),
        ("id", "has spaces"),
        ("id", "1number"),
        ("id", 1),
        ("type", "unknown"),
        ("title", ""),
        ("version", 0),
        ("version", -1),
        ("version", 1.5),
        ("version", True),
        ("description", 3),
        ("owner", ""),
        ("approval", "automatic"),
        ("uri", ""),
        ("commit", ""),
        ("timestamp", "yesterday"),
        ("confidence", -0.1),
        ("confidence", 1.1),
        ("confidence", True),
        ("confidence", "0.5"),
        ("evidence", ["Bad ID"]),
        ("evidence", "evidence.test-description"),
        ("constraints", [""]),
        ("open_questions", [1]),
        ("acceptance_criteria", [""]),
    ],
)
def test_invalid_node_values(model, field, value):
    model["nodes"][0][field] = value
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("origin", "generated"),
        ("source", ""),
        ("source", 1),
        ("verification", "probably"),
        ("rationale", ""),
    ],
)
def test_invalid_provenance(model, field, value):
    model["nodes"][0]["provenance"][field] = value
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize("field", ["approval", "acceptance_criteria"])
def test_requirement_additional_fields_required(model, field):
    del node(model, "requirement")[field]
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize("criteria", [[], [""], [1], "one criterion"])
def test_requirement_criteria_constraints(model, criteria):
    node(model, "requirement")["acceptance_criteria"] = criteria
    assert not VALIDATOR.is_valid(model)


def test_evidence_requires_uri(model):
    del node(model, "evidence")["uri"]
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize("collection", ["nodes", "edges"])
@pytest.mark.parametrize("evidence", [None, []])
def test_verified_claim_requires_evidence(model, collection, evidence):
    claim = model[collection][0]
    claim["provenance"]["verification"] = "verified"
    if evidence is not None:
        claim["evidence"] = evidence
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize("kind", ["repository", "evidence", "edge"])
def test_verified_claim_with_reference_is_structurally_valid(model, kind):
    claim = model["edges"][0] if kind == "edge" else node(model, kind)
    claim["provenance"]["verification"] = "verified"
    # A distinct supporting evidence node; schema alone does not establish its truth.
    support = deepcopy(node(model, "evidence"))
    support["id"] = "evidence.support"
    support["provenance"]["verification"] = "unverified"
    model["nodes"].append(support)
    claim["evidence"] = [support["id"]]
    VALIDATOR.validate(model)


@pytest.mark.parametrize("version", ["2.0", 1, ""])
def test_unknown_schema_version_rejected(model, version):
    model["schema_version"] = version
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize(
    ("field", "value"),
    [("type", "calls"), ("source", "Bad ID"), ("target", ""), ("evidence", [5])],
)
def test_invalid_edge_values(model, field, value):
    model["edges"][0][field] = value
    assert not VALIDATOR.is_valid(model)


@pytest.mark.parametrize("confidence", [0, 0.5, 1])
def test_optional_metadata_and_confidence_bounds(model, confidence):
    model["nodes"][0].update(
        confidence=confidence, timestamp="2026-11-11T12:00:00Z", commit="example-revision"
    )
    VALIDATOR.validate(model)
