"""Explicit evidence evaluation is never a verification gate."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from lsm.cli import main
from lsm.evidence import evaluate_junit
from lsm.junit import import_junit
from lsm.storage import load_model

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40


@pytest.fixture
def inputs(tmp_path):
    path = tmp_path / "report.xml"
    path.write_text(
        '<testsuite name="password=private-value">'
        '<testcase name="same"/><testcase name="same"><failure>RAW_FAILURE_SECRET</failure>'
        '</testcase><testcase name="error"><error/></testcase>'
        '<testcase name="skip"><skipped/></testcase></testsuite>'
    )
    report = import_junit(path, repository="repo.backend", commit=COMMIT)
    model = load_model(ROOT / "examples/shop.json")
    mapping = {
        "schema_version": "1.0",
        "report_id": report["data"]["id"],
        "mappings": [
            {
                "case_id": report["data"]["cases"][0]["id"],
                "test_id": "test.notes",
                "requirement_ids": ["requirement.notes"],
            }
        ],
    }
    return path, model, mapping, report


def evaluate(inputs, expected_commit=COMMIT):
    path, model, mapping, _ = inputs
    return evaluate_junit(
        path,
        model=model,
        mapping=mapping,
        repository="repo.backend",
        commit=COMMIT,
        expected_commit=expected_commit,
    )


@pytest.mark.parametrize(
    "index,outcome", [(0, "passed"), (1, "failed"), (2, "error"), (3, "skipped"), (None, "missing")]
)
def test_outcomes_no_promotion(inputs, index, outcome):
    path, model, mapping, report = inputs
    mapping["mappings"][0]["case_id"] = (
        report["data"]["cases"][index]["id"] if index is not None else None
    )
    before = copy.deepcopy((model, mapping)), path.read_bytes()
    result = evaluate(inputs)
    assert result["status"] == "succeeded"
    data = result["data"]
    assert data["tests"][0]["outcome"] == outcome
    requirement = next(
        row for row in data["requirements"] if row["requirement_id"] == "requirement.notes"
    )
    assert requirement["mapped_test_outcome"] == outcome
    assert requirement["coverage"] == "unknown"
    assert requirement["verification"] == data["verification"] == "unverified"
    assert result["permissions"] == {"source_access": "read", "writes_performed": False}
    assert before == ((model, mapping), path.read_bytes())
    assert "RAW_FAILURE_SECRET" not in json.dumps(result)
    assert "private-value" not in json.dumps(result)
    assert data["unmapped_case_count"] == (4 if index is None else 3)


def test_stale_and_identity(inputs):
    current, stale = evaluate(inputs), evaluate(inputs, "b" * 40)
    assert current["data"]["freshness"] == "current"
    assert stale["data"]["freshness"] == "stale"
    assert current["data"]["tests"] == stale["data"]["tests"]
    path, _, _, original = inputs
    assert original["data"] == import_junit(path, repository="repo.backend", commit=COMMIT)["data"]
    assert original["data"]["cases"][0]["id"] != original["data"]["cases"][1]["id"]
    path.write_bytes(path.read_bytes() + b"\n")
    assert evaluate(inputs)["status"] == "failed"


@pytest.mark.parametrize(
    "bad",
    [
        "report",
        "extra",
        "test",
        "requirement",
        "case",
        "duplicate",
        "wrong_test",
        "wrong_requirement",
        "empty",
        "requirements",
        "entry_extra",
        "repository",
        "model",
        "expected",
        "case_list",
    ],
)
def test_bad_mapping(inputs, bad):
    _, model, mapping, _ = inputs
    entry = mapping["mappings"][0]
    if bad == "report":
        mapping["report_id"] = "bad"
    elif bad == "extra":
        mapping["verify"] = True
    elif bad == "test":
        entry["test_id"] = "missing"
    elif bad == "requirement":
        entry["requirement_ids"] = ["missing"]
    elif bad == "case":
        entry["case_id"] = "missing"
    elif bad == "duplicate":
        mapping["mappings"].append(copy.deepcopy(entry))
    elif bad == "wrong_test":
        entry["test_id"] = "requirement.notes"
    elif bad == "wrong_requirement":
        entry["requirement_ids"] = ["test.notes"]
    elif bad == "empty":
        mapping["mappings"] = []
    elif bad == "requirements":
        entry["requirement_ids"] = "requirement.notes"
    elif bad == "entry_extra":
        entry["password"] = "private-value"
    elif bad == "repository":
        next(n for n in model["nodes"] if n["id"] == "repo.backend")["type"] = "component"
    elif bad == "model":
        model["nodes"].append(copy.deepcopy(model["nodes"][0]))
    elif bad == "case_list":
        entry["case_id"] = []
    result = evaluate(inputs, "bad" if bad == "expected" else COMMIT)
    assert result["status"] == "failed"
    assert result["data"] is None
    assert result["errors"][0]["code"] == "invalid_mapping"
    assert "private-value" not in json.dumps(result)


def test_failure_impact(inputs):
    _, _, mapping, report = inputs
    mapping["mappings"][0]["requirement_ids"].append("requirement.notes-old")
    mapping["mappings"].append(
        {
            "case_id": report["data"]["cases"][1]["id"],
            "test_id": "test.notes",
            "requirement_ids": ["requirement.notes", "requirement.notes-old"],
        }
    )
    result = evaluate(inputs)
    assert {r["mapped_test_outcome"] for r in result["data"]["requirements"]} == {"failed"}
    assert {c["outcome"] for c in result["data"]["tests"][0]["cases"]} == {"passed", "failed"}


def test_existing_trust_not_inherited_and_unmapped_requirement(inputs):
    _, model, _, _ = inputs
    node = next(node for node in model["nodes"] if node["id"] == "requirement.notes")
    node["approval"] = "approved"
    node["provenance"]["verification"] = "verified"
    node["evidence"] = ["evidence.test-description"]
    before = copy.deepcopy(model)
    result = evaluate(inputs)
    assert result["status"] == "succeeded"
    assert all(row["verification"] == "unverified" for row in result["data"]["requirements"])
    unmapped = next(
        row
        for row in result["data"]["requirements"]
        if row["requirement_id"] == "requirement.notes-old"
    )
    assert unmapped["mapped_test_outcome"] == "missing"
    assert unmapped["test_ids"] == []
    assert model == before


def test_shared_redaction_of_reference_metadata(inputs):
    _, model, mapping, _ = inputs
    old, new = "test.notes", "test.ghp_abcdefghijklmno"
    for node in model["nodes"]:
        if node["id"] == old:
            node["id"] = new
    for edge in model["edges"]:
        for key in ("source", "target"):
            if edge[key] == old:
                edge[key] = new
    mapping["mappings"][0]["test_id"] = new
    result = evaluate(inputs)
    assert result["status"] == "succeeded"
    assert "ghp_abcdefghijklmno" not in json.dumps(result)


def test_cli_compatibility(inputs, tmp_path, capsys):
    path, model, mapping, _ = inputs
    model_path, mapping_path = tmp_path / "model.json", tmp_path / "mapping.json"
    model_path.write_text(json.dumps(model))
    mapping_path.write_text(json.dumps(mapping))
    before = {p: p.read_bytes() for p in (path, model_path, mapping_path)}
    args = [str(path), "--repository", "repo.backend", "--commit", COMMIT]
    assert main(["import-junit", *args]) == 0
    assert json.loads(capsys.readouterr().out)["capability"] == "import_test_report"
    assert (
        main(
            [
                "evaluate-junit",
                *args,
                "--model",
                str(model_path),
                "--mapping",
                str(mapping_path),
                "--expected-commit",
                COMMIT,
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["data"]["requirements"][0]["coverage"] == "unknown"
    assert before == {p: p.read_bytes() for p in before}


def test_no_execution_invalid_report(inputs, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("evaluation must not execute commands")

    monkeypatch.setattr("subprocess.run", forbidden)
    assert evaluate(inputs)["status"] == "succeeded"
    inputs[0].write_text("<!DOCTYPE bad><testsuite/>")
    result = evaluate(inputs)
    assert result["status"] == "failed"
    assert result["errors"][0]["code"] == "invalid_report"


def test_executable_demo():
    process = subprocess.run(
        [sys.executable, str(ROOT / "scripts/evidence_demo.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(process.stdout)
    assert result["data"]["freshness"] == "stale"
    assert result["data"]["tests"][0]["outcome"] == "failed"
