"""Standalone lifecycle contracts and local authorization boundaries."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from lsm.requirements import (
    create_requirement,
    refine_requirement,
    transition_requirement,
    validate_requirement,
)

POLICY = {
    "version": "1.0",
    "humans": ["owner"],
    "permissions": {"approve_requirements": ["owner"]},
}


def proposed():
    record = create_requirement("requirement.offline-sync", "Support offline sync")
    record["acceptance_criteria"] = ["Changes converge after a successful reconnection."]
    return transition_requirement(record, "proposed")


def approved():
    return transition_requirement(proposed(), "approved", POLICY, "owner")


def test_create_and_schema():
    record = create_requirement("requirement.sync", "Sync offline changes")
    assert record["version"] == 1
    assert record["state"] == "draft"
    assert record["history"] == []
    assert validate_requirement(record) == []
    schema = json.loads(Path("src/lsm/schemas/requirement.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(record)


@pytest.mark.parametrize("identifier,intent", [("", "ok"), ("bad id", "ok"), ("r", " ")])
def test_invalid_create(identifier, intent):
    with pytest.raises(ValueError):
        create_requirement(identifier, intent)


def test_refinement_is_deterministic_idempotent_and_nonmutating():
    record = create_requirement("r", "Offline sync token=super-secret-value")
    original = copy.deepcopy(record)
    refined = refine_requirement(record)
    assert record == original
    assert refined == refine_requirement(record)
    assert refine_requirement(refined) == refined
    assert refined["state"] == "questions"
    assert refined["version"] == 2
    assert len(refined["questions"]) == 5
    prompts = " ".join(refined["questions"]).lower()
    for word in ("owns", "conflicts", "connectivity", "consistency"):
        assert word in prompts
    assert "super-secret-value" not in prompts
    assert refined["assumptions"] == refined["acceptance_criteria"] == []
    assert refined["history"][0]["prior_snapshot"]["intent"] == record["intent"]
    refined["history"][0]["prior_snapshot"]["questions"].append("Independent")
    assert record == original


def test_generic_refinement_and_proposed_reopening():
    record = create_requirement("r", "Improve navigation")
    assert len(refine_requirement(record)["questions"]) == 1
    result = refine_requirement(proposed())
    assert result["state"] == "questions"
    assert result["version"] == 3
    assert validate_requirement(result) == []


def test_answered_questions_can_be_proposed_without_inferred_answers():
    record = refine_requirement(create_requirement("r", "Offline sync"))
    record["questions"] = []
    record["assumptions"] = ["Owner supplied a single-user scope."]
    record["acceptance_criteria"] = ["A queued edit survives restart."]
    result = transition_requirement(record, "proposed", actor="owner")
    assert result["version"] == 3
    assert validate_requirement(result) == []
    assert result["history"][-1]["prior_snapshot"]["assumptions"] == record["assumptions"]


@pytest.mark.parametrize("source", ["draft", "questions", "proposed", "approved", "superseded"])
@pytest.mark.parametrize(
    "target", ["draft", "questions", "proposed", "approved", "superseded", "bad"]
)
def test_transition_matrix(source, target):
    draft = create_requirement("r", "Intent")
    draft["acceptance_criteria"] = ["Explicit result"]
    records = {"draft": draft}
    records["questions"] = transition_requirement(draft, "questions")
    records["proposed"] = transition_requirement(draft, "proposed")
    records["approved"] = transition_requirement(records["proposed"], "approved", POLICY, "owner")
    records["superseded"] = transition_requirement(
        records["approved"], "superseded", POLICY, "owner"
    )
    legal = {
        ("draft", "questions"),
        ("draft", "proposed"),
        ("questions", "proposed"),
        ("proposed", "questions"),
        ("proposed", "approved"),
        ("approved", "superseded"),
    }
    before = copy.deepcopy(records[source])
    if (source, target) in legal:
        result = transition_requirement(before, target, POLICY, "owner")
        assert result["version"] == before["version"] + 1
        assert validate_requirement(result) == []
    else:
        with pytest.raises(ValueError):
            transition_requirement(before, target, POLICY, "owner")
    assert before == records[source]


@pytest.mark.parametrize("target", ["approved", "superseded"])
@pytest.mark.parametrize(
    "policy,actor,kind",
    [
        (None, "owner", "human"),
        (POLICY, None, "human"),
        (POLICY, "other", "human"),
        (POLICY, "owner", "agent"),
        ({"version": "1.0", "humans": ["owner"], "permissions": {}}, "owner", "human"),
    ],
)
def test_consequential_transitions_default_deny(target, policy, actor, kind):
    record = proposed() if target == "approved" else approved()
    with pytest.raises(ValueError):
        transition_requirement(record, target, policy, actor, kind)


def test_approval_requires_criteria_and_resolved_questions():
    record = transition_requirement(create_requirement("r", "Intent"), "proposed")
    with pytest.raises(ValueError, match="criteria"):
        transition_requirement(record, "approved", POLICY, "owner")
    record["acceptance_criteria"] = ["Explicit outcome"]
    record["questions"] = ["Who owns data?"]
    with pytest.raises(ValueError, match="questions"):
        transition_requirement(record, "approved", POLICY, "owner")


def test_approval_version_and_actor_are_retained():
    before = proposed()
    original = copy.deepcopy(before)
    result = transition_requirement(before, "approved", POLICY, "owner")
    assert before == original
    assert result["version"] == 3
    assert result["history"][-1] == {
        "from_state": "proposed",
        "to_state": "approved",
        "from_version": 2,
        "to_version": 3,
        "actor": "owner",
        "actor_kind": "human",
        "prior_snapshot": {key: value for key, value in before.items() if key != "history"},
    }
    assert validate_requirement(result) == []


@pytest.mark.parametrize("state", ["approved", "superseded"])
def test_final_records_cannot_be_refined(state):
    record = approved()
    if state == "superseded":
        record = transition_requirement(record, state, POLICY, "owner")
    with pytest.raises(ValueError):
        refine_requirement(record)


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(version=99),
        lambda r: r.update(requirement_id="different"),
        lambda r: r.update(state="draft"),
        lambda r: r["history"][0].update(to_version=99),
        lambda r: r["history"][0].update(to_state="superseded"),
        lambda r: r["history"][-1].update(actor_kind="agent"),
        lambda r: r["history"][-1].update(actor=None),
        lambda r: r["history"][0]["prior_snapshot"].update(version=0),
        lambda r: r["acceptance_criteria"].append("Silently altered"),
        lambda r: r.update(schema_version="2.0"),
        lambda r: r.update(extra="forbidden"),
    ],
)
def test_invalid_records_and_history_rejected(change):
    record = approved()
    change(record)
    errors = validate_requirement(record)
    assert errors
    assert all(set(error) == {"code", "path", "message"} for error in errors)
    with pytest.raises(ValueError):
        transition_requirement(record, "superseded", POLICY, "owner")


@pytest.mark.parametrize("record", [None, [], {}, {"state": []}, {"history": [None]}])
def test_malformed_inputs_return_diagnostics(record):
    assert validate_requirement(record)


def test_schema_diagnostics_do_not_echo_secret_values():
    record = create_requirement("r", "Intent")
    record["state"] = "token=super-secret"
    assert "super-secret" not in json.dumps(validate_requirement(record))


def test_examples_validate():
    for path in Path("examples/requirements").glob("*.json"):
        assert validate_requirement(json.loads(path.read_text())) == [], path
