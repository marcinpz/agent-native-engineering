"""Research-artifact checks only; no compiler execution or portability evidence."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "examples/research/semantic-ir-proposal.json"
GAPS = {
    f"gap.{name}" for name in ("domain", "network", "concurrency", "state", "errors", "security")
}


def check_proposal(proposal):
    """Local test contract, deliberately not a public IR schema or consumer."""
    assert proposal["proposal_version"] == "0.1"
    assert proposal["id"] == "research.semantic-ir"
    assert proposal["issue"] == 9
    assert proposal["status"] == "proposed"
    assert proposal["hypothesis_status"] == "untested"
    assert proposal["artifact_kind"] == "experiment-proposal"
    assert proposal["executable"] is False
    assert proposal["architecture_adopted"] is False
    assert proposal["implementation_approval"] == "required"
    assert proposal["full_compiler_approval"] == "separate-approved-adr-required"
    assert proposal["required_runtime"] is None
    assert proposal["required_vendor"] is None
    assert proposal["results"] is None
    collections = ("operations", "unsupported_semantics", "candidate_backends")
    for collection in collections:
        ids = [item["id"] for item in proposal[collection]]
        assert ids and len(ids) == len(set(ids))
    operations = {item["id"] for item in proposal["operations"]}
    assert operations == {"op.add-checked", "op.equal", "op.choose"}
    types = {"i32", "bool", "result<i32,overflow>"}
    for operation in proposal["operations"]:
        assert operation["inputs"] and set(operation["inputs"]) <= types
        assert operation["output"] in types
        assert operation["semantics"].strip()
    assert {gap["id"] for gap in proposal["unsupported_semantics"]} == GAPS
    for gap in proposal["unsupported_semantics"]:
        assert gap["cases"] and all(case.strip() for case in gap["cases"])
    backends = proposal["candidate_backends"]
    assert {backend["id"] for backend in backends} == {
        "backend.existing-source",
        "backend.interpreter",
        "backend.source-emitters",
        "backend.wasm",
    }
    assert sum(backend["role"] == "baseline" for backend in backends) == 1
    for backend in backends:
        assert backend["role"] in {"baseline", "candidate"}
        assert backend["targets"] and all(target.strip() for target in backend["targets"])
        assert backend["optional"] is True
        mapping = backend["mapping"]
        assert mapping["status"] == "proposed"
        assert set(mapping["operation_ids"]) == operations
        assert len(mapping["operation_ids"]) == len(operations)
        assert set(mapping["unsupported_case_ids"]) == GAPS
        assert len(mapping["unsupported_case_ids"]) == len(GAPS)
        assert mapping["approach"].strip()
        assert mapping["risks"] and all(risk.strip() for risk in mapping["risks"])
    evaluation = proposal["evaluation"]
    assert evaluation["status"] == "planned-not-run"
    assert evaluation["paired_tasks"] == 20
    assert evaluation["repetitions_per_target"] == 3
    assert evaluation["oracle_cases_per_operation_per_target"] == 1000
    assert evaluation["rejection_cases_per_gap_per_target"] >= 1
    assert evaluation["missing_measurements"] is None
    assert evaluation["adoption_on_pass"] is False
    assert evaluation["thresholds"] == {
        "oracle_agreement_min": 1.0,
        "silent_unsupported_acceptance_max": 0,
        "task_pass_at_1_min": 0.9,
        "median_maintenance_reduction_min": 0.2,
        "paired_interval_confidence": 0.95,
        "maintenance_interval_must_exclude_zero": True,
        "median_latency_ratio_max": 2.0,
        "peak_memory_ratio_max": 2.0,
        "semantic_workarounds_per_operation_per_target_max": 1,
    }


@pytest.fixture
def proposal():
    return json.loads(PROPOSAL.read_text())


def test_proposal_is_consistent_and_unexecuted(proposal):
    check_proposal(proposal)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("proposal_version", "9.0"),
        ("status", "successful"),
        ("hypothesis_status", "verified"),
        ("executable", True),
        ("architecture_adopted", True),
        ("results", {"success": True}),
        ("required_runtime", "wasm"),
        ("required_vendor", "any-vendor"),
        ("implementation_approval", "granted"),
    ],
)
def test_rejects_success_or_requirement_claims(proposal, field, value):
    proposal[field] = value
    with pytest.raises(AssertionError):
        check_proposal(proposal)


@pytest.mark.parametrize("backend_index", range(4))
@pytest.mark.parametrize("defect", ["no-gaps", "missing-gap", "no-risks", "unknown-op", "success"])
def test_every_mapping_requires_exclusions_risks_and_no_success(proposal, backend_index, defect):
    mapping = proposal["candidate_backends"][backend_index]["mapping"]
    if defect == "no-gaps":
        mapping["unsupported_case_ids"] = []
    elif defect == "missing-gap":
        mapping["unsupported_case_ids"].pop()
    elif defect == "no-risks":
        mapping["risks"] = []
    elif defect == "unknown-op":
        mapping["operation_ids"].append("op.unknown")
    else:
        mapping["status"] = "verified"
    with pytest.raises(AssertionError):
        check_proposal(proposal)


def test_duplicate_ids_and_automatic_adoption_rejected(proposal):
    duplicate = deepcopy(proposal)
    duplicate["operations"].append(deepcopy(duplicate["operations"][0]))
    with pytest.raises(AssertionError):
        check_proposal(duplicate)
    proposal["evaluation"]["adoption_on_pass"] = True
    with pytest.raises(AssertionError):
        check_proposal(proposal)


def test_docs_preserve_proposed_and_untested_boundary():
    adr = (ROOT / "docs/adr/0003-semantic-ir-research.md").read_text()
    research = (ROOT / "docs/research/SEMANTIC_IR.md").read_text()
    assert "Status: PROPOSED" in adr
    assert "not adopted architecture" in adr
    assert "Hypothesis: untested" in research
    assert "No benchmark or execution has been performed" in research
    for gap in GAPS:
        assert gap in research
    assert "semantic-ir-proposal.json" in adr and "semantic-ir-proposal.json" in research
