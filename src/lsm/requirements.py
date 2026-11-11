"""Offline requirement lifecycle; local attestations, not authenticated approvals."""

import copy
import json
import re
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft202012Validator

from lsm.security import require_authorization

_TRANSITIONS = {
    "draft": {"questions", "proposed"},
    "questions": {"proposed"},
    "proposed": {"questions", "approved"},
    "approved": {"superseded"},
    "superseded": set(),
}
_PROMPTS = (
    "Which user-visible outcomes and measurable acceptance criteria define success?",
    "Who owns offline data and is authorized to create, change, or delete it?",
    "How are concurrent offline and server changes detected and conflicts resolved?",
    "What works without connectivity, and when and how is synchronization retried?",
    "What consistency guarantees apply during disconnection and after reconnection?",
)


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads(files("lsm").joinpath("schemas/requirement.schema.json").read_text())
    return Draft202012Validator(schema)


def _snapshot(record):
    return copy.deepcopy({key: value for key, value in record.items() if key != "history"})


def validate_requirement(record) -> list[dict]:
    """Check shape and history continuity, not actor identity or policy authenticity."""
    errors = []

    def report(code, path, message):
        errors.append({"code": code, "path": path, "message": message})

    for error in _validator().iter_errors(record):
        path = "".join(
            "/" + str(p).replace("~", "~0").replace("/", "~1") for p in error.absolute_path
        )
        # Do not echo untrusted content (including secrets) in diagnostics.
        report("schema_error", path, f"Requirement schema constraint failed: {error.validator}")
    if errors:
        return sorted(errors, key=lambda item: (item["path"], item["message"]))

    history = record["history"]
    if record["version"] != len(history) + 1:
        report("invalid_history", "/version", "Version must equal history length plus one")
    previous_state = "draft"
    for index, entry in enumerate(history):
        path = f"/history/{index}"
        prior = entry["prior_snapshot"]
        if (
            entry["from_version"] != index + 1
            or entry["to_version"] != index + 2
            or prior["version"] != entry["from_version"]
            or prior["requirement_id"] != record["requirement_id"]
            or prior["state"] != entry["from_state"]
            or entry["from_state"] != previous_state
        ):
            report("invalid_history", path, "History identity, state or version chain is broken")
        source, target = entry["from_state"], entry["to_state"]
        if target not in _TRANSITIONS[source] and not (
            source == target and source in {"draft", "questions", "proposed"}
        ):
            report("invalid_transition", path, "History contains an illegal transition")
        if target in {"approved", "superseded"} and (
            entry["actor_kind"] != "human" or not entry["actor"]
        ):
            report("human_required", path, "Consequential transitions require a named human")
        if (source in {"approved", "superseded"} or target == "approved") and (
            prior["questions"] or not prior["acceptance_criteria"]
        ):
            report("approval_incomplete", path, "Approved snapshots require resolved criteria")
        # Once approved, content cannot be edited even when superseding it.
        if source == "approved" or target == "approved":
            after = history[index + 1]["prior_snapshot"] if index + 1 < len(history) else record
            fields = ("intent", "questions", "assumptions", "acceptance_criteria")
            if any(prior[field] != after[field] for field in fields):
                report("approved_content_changed", path, "Approved content is immutable")
        previous_state = target
    if record["state"] != previous_state:
        report("invalid_history", "/state", "Current state does not match history")
    if record["state"] in {"approved", "superseded"} and (
        record["questions"] or not record["acceptance_criteria"]
    ):
        report("approval_incomplete", "/state", "Approval requires criteria and no open questions")
    return sorted(errors, key=lambda item: (item["path"], item["code"], item["message"]))


def _require_valid(record):
    if validate_requirement(record):
        raise ValueError("Invalid requirement record; use validate_requirement for diagnostics")


def create_requirement(requirement_id: str, intent: str) -> dict:
    """Create an unapproved version-one draft without inferred answers."""
    record = {
        "schema_version": "1.0",
        "requirement_id": requirement_id,
        "version": 1,
        "intent": intent,
        "state": "draft",
        "questions": [],
        "assumptions": [],
        "acceptance_criteria": [],
        "history": [],
    }
    _require_valid(record)
    return record


def _change(record, updated, actor, actor_kind):
    if record == updated:
        return copy.deepcopy(record)
    updated["version"] = record["version"] + 1
    updated["history"].append(
        {
            "from_state": record["state"],
            "to_state": updated["state"],
            "from_version": record["version"],
            "to_version": updated["version"],
            "actor": actor,
            "actor_kind": actor_kind,
            "prior_snapshot": _snapshot(record),
        }
    )
    _require_valid(updated)
    return updated


def refine_requirement(record: dict) -> dict:
    """Add fixed clarification prompts; never infer answers or approve intent."""
    _require_valid(record)
    if record["state"] in {"approved", "superseded"}:
        raise ValueError("Approved or superseded requirements cannot be refined")
    updated = copy.deepcopy(record)
    # Only inspect intent for topic selection; never interpolate it into prompts.
    offline = re.search(r"\boffline\b|\bsync(?:hroni[sz](?:ation|e))?\b", record["intent"], re.I)
    prompts = _PROMPTS if offline else _PROMPTS[:1]
    for prompt in prompts:
        if prompt not in updated["questions"]:
            updated["questions"].append(prompt)
    if updated["questions"]:
        updated["state"] = "questions"
    return _change(record, updated, "rule-based-refiner", "agent")


def transition_requirement(
    record: dict,
    state: str,
    policy: dict | None = None,
    actor: str | None = None,
    actor_kind="human",
) -> dict:
    """Apply a legal transition; approval and supersession default to deny."""
    _require_valid(record)
    if not isinstance(state, str) or state not in _TRANSITIONS[record["state"]]:
        raise ValueError("Illegal requirement state transition")
    if state in {"approved", "superseded"}:
        require_authorization(policy, actor, "approve_requirements", actor_kind)
    if state == "approved" and (record["questions"] or not record["acceptance_criteria"]):
        raise ValueError("Approval requires nonempty acceptance criteria and no open questions")
    updated = copy.deepcopy(record)
    updated["state"] = state
    return _change(record, updated, actor, actor_kind)
