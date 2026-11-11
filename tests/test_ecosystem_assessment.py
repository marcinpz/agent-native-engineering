"""Offline research-artifact consistency, not factual or live-doc verification."""

import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "docs/research/ecosystem-sources.json"
CONTRACT_PATH = ROOT / "examples/research/system-contract-proposal.json"
ASSESSMENT_PATH = ROOT / "docs/research/ECOSYSTEM_ASSESSMENT.md"
ADR_PATH = ROOT / "docs/adr/0004-integration-shortlist.md"
SOURCES = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
MODEL_SCHEMA = json.loads((ROOT / "src/lsm/schemas/model.schema.json").read_text(encoding="utf-8"))
PROVENANCE_VALIDATOR = Draft202012Validator(
    {"$ref": "#/$defs/provenance", "$defs": MODEL_SCHEMA["$defs"]}
)
TOOLS = SOURCES["tools"]
ENTITY_COLLECTIONS = (
    "requirements",
    "behaviors",
    "interfaces",
    "components",
    "constraints",
    "deployment_observations",
    "target_profiles",
    "constraint_assessments",
    "evidence",
    "unknowns",
    "decisions",
)


def test_registry_scope_and_pending_acceptance() -> None:
    assert SOURCES["status"] == "initial-milestone"
    date.fromisoformat(SOURCES["checked_on"])
    assert SOURCES["gates"]["architecture_approval"] == "pending"
    assert SOURCES["gates"]["real_provider_poc"] == "pending"
    assert SOURCES["gates"]["baseline_experiment"] == "pending"
    assert SOURCES["gates"]["application_evaluation"] == "not-executed"
    assert SOURCES["gates"]["paid_model_experiment"] == "not-executed"
    assert "structural" in SOURCES["claim_policy"]["tests"].lower()


def test_inventory_has_unique_ids_and_required_tracks() -> None:
    ids = [tool["id"] for tool in TOOLS]
    assert len(ids) >= 12
    assert len(ids) == len(set(ids))
    assert {"coding-agent", "specification", "static-analysis", "behavioral-verification"} <= {
        tool["category"] for tool in TOOLS
    }
    assert {"modernization", "diagram", "scm", "ci"} <= {tool["category"] for tool in TOOLS}
    assert {"openspec", "spec-kit", "rmf", "oslc", "rewrite-spring"} <= set(ids)


@pytest.mark.parametrize("tool", TOOLS, ids=lambda tool: tool["id"])
def test_tool_has_observation_and_license_provenance(tool: dict) -> None:
    date.fromisoformat(tool["checked_on"])
    assert tool["checked_on"] == SOURCES["checked_on"]
    assert re.fullmatch(r"[a-f0-9]{40}", tool["revision"])
    assert "version" in tool  # null is honest unknown, not an invented version.
    assert tool["license"] and tool["license_caveat"]
    assert tool["classification"] in {
        "building-block",
        "source-available-building-block",
        "adjacent-product",
        "standard",
    }
    assert {"license", "feature", "maintenance"} <= tool["evidence"].keys()
    for evidence in tool["evidence"].values():
        assert urlparse(evidence["url"]).scheme == "https"
        assert urlparse(evidence["url"]).netloc
        assert evidence["ref"]
        assert evidence["check_status"] == "observed_documentation"


def test_standards_landscape_and_failures_are_explicit() -> None:
    references = SOURCES["reference_sources"]
    ids = [source["id"] for source in references]
    assert len(ids) == len(set(ids))
    assert {"reqif-1.2", "spring-boot-4-guide", "cloud-run-contract", "lsp-3.17"} <= set(ids)
    assert {"moderne-landscape", "aws-transform-landscape", "konveyor-landscape"} <= set(ids)
    for source in references:
        date.fromisoformat(source["checked_on"])
        assert source["ref"]
        assert source["check_status"] == "observed_documentation"
        assert urlparse(source["url"]).scheme == "https"
    assert SOURCES["failed_lookups"]
    for failure in SOURCES["failed_lookups"]:
        assert failure["check_status"] == "http-404"
        assert failure["resolution"]
        date.fromisoformat(failure["checked_on"])

    # Separately reported integration evidence must not close the research gates.
    reports = SOURCES["related_execution_reports"]
    assert reports
    for report in reports:
        assert report["check_status"] == "reported_execution"
        assert report["repository_path"] == "docs/verification/INTEGRATION_GATE.md"
        assert report["exclusions"]
        assert urlparse(report["reported_ci_url"]).scheme == "https"
        date.fromisoformat(report["checked_on"])


def test_material_license_and_maintenance_caveats_are_not_lost() -> None:
    tools = {tool["id"]: tool for tool in TOOLS}
    assert "Source Available" in tools["rewrite-spring"]["license"]
    assert "LLVM-exception" in tools["wasmtime"]["license"]
    assert "mixed" in tools["openrewrite"]["license"]
    assert (
        "separate" in tools["actions"]["license_caveat"]
        or "not hosted" in tools["actions"]["license_caveat"]
    )
    assert "archived=true" in tools["structurizr-cli-legacy"]["evidence"]["maintenance"]["ref"]


def test_document_tables_cover_registry_ids() -> None:
    text = ASSESSMENT_PATH.read_text(encoding="utf-8")
    assert "Mapping to existing LSM provenance: independent axes" in text
    assert "Observed behavior can be **unverified**" in text
    assert "Verification never changes origin or implies approval" in text
    assert "Unknown is a status, not a new" in text
    rows = re.findall(r"^\| `([^`]+)` \|", text, flags=re.MULTILINE)
    for tool in TOOLS:
        assert rows.count(tool["id"]) == 2, tool["id"]
    assert "observed_documentation" in SOURCES["claim_policy"]
    for path in (ASSESSMENT_PATH, ADR_PATH):
        content = path.read_text(encoding="utf-8")
        assert "PROPOSED" in content
        assert "semantic" in content
        assert "pending" in content.lower()
        assert "ecosystem-sources.json" in content
        assert "system-contract-proposal.json" in content


def test_contract_is_research_only_without_fake_approval_or_execution() -> None:
    assert CONTRACT["status"] == "proposed"
    assert CONTRACT["synthetic"] is True
    assert CONTRACT["production_schema"] is False
    assert CONTRACT["architecture_approval"] == "pending"
    assert CONTRACT["semantic_equivalence_guarantee"] is False
    assert CONTRACT["source_registry"] == str(SOURCES_PATH.relative_to(ROOT))
    assert CONTRACT["approved_exceptions"] == []
    summary = CONTRACT["verification_summary"]
    assert summary["status"] == "not-executed"
    assert summary["executed_application_checks"] == []
    assert summary["approved_requirements"] == []
    for requirement in CONTRACT["requirements"]:
        assert requirement["approval"] == {
            "status": "pending",
            "actor": None,
            "approved_revision": None,
        }
    for behavior in CONTRACT["behaviors"]:
        assert behavior["verification"]["status"] == "not-executed"
        assert behavior["verification"]["execution_evidence_ids"] == []


def test_contract_ids_and_independent_provenance_axes() -> None:
    entities = [entity for key in ENTITY_COLLECTIONS for entity in CONTRACT[key]]
    ids = [entity["id"] for entity in entities]
    assert len(ids) == len(set(ids))
    assert set(CONTRACT["provenance_axes"]["origin"]) == {"declared", "inferred", "observed"}
    assert set(CONTRACT["provenance_axes"]["verification"]) == {"unverified", "verified"}
    assert "claim_kinds" not in CONTRACT
    assert '"claim_kind"' not in CONTRACT_PATH.read_text(encoding="utf-8")
    for entity in entities:
        provenance = entity["provenance"]
        if provenance is None:
            assert entity["status"] == "unknown"
            assert entity["unknown_reason"].strip()
        else:
            PROVENANCE_VALIDATOR.validate(provenance)
            assert provenance["source"].strip()
            # Real documentation reads exist, but this sample has no verified claims.
            assert provenance["verification"] == "unverified"


@pytest.mark.parametrize("origin", ["declared", "inferred", "observed"])
@pytest.mark.parametrize("verification", ["unverified", "verified"])
def test_lsm_provenance_axes_allow_independent_representations(
    origin: str, verification: str
) -> None:
    # Pure representation/schema exercise: this is NOT performed app verification.
    representation = deepcopy(CONTRACT["requirements"][0])
    representation["provenance"] = {
        "origin": origin,
        "source": "urn:ane:test:representation-not-an-application-observation",
        "verification": "unverified",
    }
    approval_before = deepcopy(representation["approval"])
    representation["provenance"]["verification"] = verification
    PROVENANCE_VALIDATOR.validate(representation["provenance"])
    assert representation["provenance"]["origin"] == origin
    assert representation["approval"] == approval_before
    assert representation["approval"]["status"] == "pending"
    assert CONTRACT["verification_summary"]["status"] == "not-executed"


@pytest.mark.parametrize(
    "invalid_provenance",
    [
        {"origin": "unknown", "source": "urn:ane:test:unknown", "verification": "unverified"},
        {"origin": "verified", "source": "urn:ane:test:mixed-axis", "verification": "verified"},
        {"origin": "observed", "source": "", "verification": "unverified"},
    ],
)
def test_unknown_is_not_an_origin_and_known_origins_need_source(invalid_provenance: dict) -> None:
    with pytest.raises(ValidationError):
        PROVENANCE_VALIDATOR.validate(invalid_provenance)


def test_documentation_observations_and_interpretations_remain_scoped() -> None:
    source = "https://cloud.google.com/run/docs/container-contract"
    docs = CONTRACT["deployment_observations"][0]
    evidence = next(
        item for item in CONTRACT["evidence"] if item["id"] == "evidence.cloud-run-docs"
    )
    for item in (docs, evidence):
        assert item["provenance"] == {
            "origin": "observed",
            "source": source,
            "verification": "unverified",
        }
    assert docs["scope"] == "documentation-only; no actual deployment"
    assert "Actual deployment" in evidence["exclusions"]
    assert evidence["execution_status"] == "not-executed"
    for requirement in CONTRACT["requirements"]:
        assert requirement["provenance"]["origin"] == "declared"
        assert requirement["provenance"]["verification"] == "unverified"
    interpretation = next(
        item for item in CONTRACT["constraints"] if item["id"] == "constraint.required-network"
    )
    assert interpretation["provenance"]["origin"] == "inferred"
    assert interpretation["provenance"]["verification"] == "unverified"
    assert interpretation["provenance"]["source"].strip()


def test_missing_application_and_target_facts_have_no_fabricated_provenance() -> None:
    missing = [
        *CONTRACT["components"],
        *CONTRACT["target_profiles"],
        *CONTRACT["constraint_assessments"],
        *CONTRACT["unknowns"],
        next(item for item in CONTRACT["interfaces"] if item["id"] == "interface.payment"),
    ]
    for item in missing:
        assert item["status"] == "unknown"
        assert item["provenance"] is None
        assert item["unknown_reason"].strip()


def test_cloud_run_ingress_constraints_are_scoped_to_http_service() -> None:
    docs = CONTRACT["deployment_observations"][0]
    assert docs["resource_scope"] == "Cloud Run HTTP service"
    assert "Linux x86_64 executable container" in docs["general_container_constraints"]
    assert "ephemeral writable local filesystem" in docs["general_container_constraints"]
    assert docs["documented_constraints"]
    assert all(item.startswith("HTTP service ") for item in docs["documented_constraints"])
    assert any("0.0.0.0" in item and "PORT" in item for item in docs["documented_constraints"])
    assert any("TLS" in item for item in docs["documented_constraints"])
    assert any("request timeout" in item for item in docs["documented_constraints"])
    assert "jobs should exit upon completion" in docs["jobs_note"]
    assert "not listen on a port or start a web server" in docs["jobs_note"]


def test_contract_references_resolve_without_promoting_unknowns() -> None:
    ids_by_collection = {
        key: {entity["id"] for entity in CONTRACT[key]} for key in ENTITY_COLLECTIONS
    }
    references = {
        "requirement_ids": "requirements",
        "behavior_ids": "behaviors",
        "interface_ids": "interfaces",
        "evidence_ids": "evidence",
        "unknown_ids": "unknowns",
        "consumer_ids": "components",
    }
    for collection in ENTITY_COLLECTIONS:
        for entity in CONTRACT[collection]:
            for field, target in references.items():
                assert set(entity.get(field, [])) <= ids_by_collection[target]
            if "provider_id" in entity and entity["provider_id"] is not None:
                assert entity["provider_id"] in ids_by_collection["components"]
    for assessment in CONTRACT["constraint_assessments"]:
        assert assessment["constraint_id"] in ids_by_collection["constraints"]
        assert assessment["target_id"] in ids_by_collection["target_profiles"]
        assert assessment["status"] == "unknown"
        assert assessment["exception_id"] is None
        assert assessment["unknown_ids"]
    assert set(CONTRACT["conflict_representation"]["assessment_statuses"]) == {
        "satisfied",
        "conflict",
        "unknown",
    }
    for target in CONTRACT["target_profiles"]:
        assert target["runtime_version"] is None
        assert target["interface_profile"] is None
        assert target["offered_capabilities"] == []


def test_contract_evidence_points_to_registry_and_retains_limits() -> None:
    source_ids = {source["id"] for source in SOURCES["reference_sources"]}
    for evidence in CONTRACT["evidence"]:
        date.fromisoformat(evidence["recorded_on"])
        assert urlparse(evidence["artifact_uri"]).scheme in {"https", "urn"}
        assert evidence["method"] and evidence["coverage"] and evidence["exclusions"]
        assert evidence["execution_status"] == "not-executed"
        assert evidence["artifact_ref"] is None  # No fictitious app/run/hash refs.
        if evidence["source_id"] is not None:
            assert evidence["source_id"] in source_ids
    for unknown in CONTRACT["unknowns"]:
        assert unknown["question"] and unknown["owner"] and unknown["required_evidence"]
        assert unknown["blocking"] is True


def test_adr_does_not_approve_itself() -> None:
    text = ADR_PATH.read_text(encoding="utf-8")
    assert "PROPOSED — not adopted" in text
    assert "Human architecture approval: **pending**" in text
    assert "neither authorizes" in text
    assert "closes #21" in text
