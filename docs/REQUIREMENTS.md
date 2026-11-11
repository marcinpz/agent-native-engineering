# Requirement lifecycle (companion schema 1.0)

`src/lsm/schemas/requirement.schema.json` is a standalone closed JSON Schema.
It does not extend or change Living System Model schema 1.0. `requirement_id`
is stable across revisions and can use the corresponding model requirement ID;
the library does not resolve model references.

## Python API

```python
from lsm.requirements import (
    create_requirement,
    refine_requirement,
    transition_requirement,
    validate_requirement,
)

draft = create_requirement("requirement.offline-sync", "Support offline sync")
questions = refine_requirement(draft)
assert validate_requirement(questions) == []
```

Creation returns version 1, state `draft`, and empty questions, assumptions,
acceptance criteria and history. Refinement is deterministic, rule-based and
idempotent on unchanged input. It asks a general measurable-outcome question;
offline/sync intents also get data ownership, conflict resolution, connectivity
and consistency questions. Prompts are fixed strings, never interpolated source
text. No LLM, answer inference, assumption generation or automatic approval occurs.
Refinement moves editable records to `questions`; approved/superseded records
cannot be refined.

Questions are unresolved strings. To answer them, explicitly prepare an editable
copy, remove resolved questions, and supply human-authored assumptions and
acceptance criteria. Preserve answers in those fields or external review evidence.
Do not remove questions just to pass an approval gate. The API cannot determine
whether a human's answer is correct or sufficient.

```python
from copy import deepcopy

answered = deepcopy(questions)
answered["questions"] = []  # Only after explicit resolution in human review.
answered["assumptions"] = ["Single-owner records; server revisions are authoritative."]
answered["acceptance_criteria"] = [
    "A queued edit survives an offline restart without loss.",
    "Reconnection retries queued edits without duplicate application.",
    "Conflicting revisions remain visible for explicit user resolution.",
]
proposal = transition_requirement(answered, "proposed", actor="owner")
policy = {
    "version": "1.0",
    "humans": ["owner"],
    "permissions": {"approve_requirements": ["owner"]},
}
approved = transition_requirement(proposal, "approved", policy, "owner")
```

Allowed explicit transitions:

| From | To |
| --- | --- |
| draft | questions, proposed |
| questions | proposed |
| proposed | questions, approved |
| approved | superseded |
| superseded | none |

Same-state explicit transitions and unknown states are rejected. Approval requires
nonempty acceptance criteria, no unresolved questions, and
`security.require_authorization(policy, actor, "approve_requirements", actor_kind)`.
Superseding also requires this authorization. An agent is denied even if it uses
the name of a policy-authorized human. Superseding retires the record; it does not
edit approved content or create/link a replacement automatically.

All operations return independent copies; input records are not mutated. Every
API content/state change increments the positive integer version and appends a
history entry with from/to states and versions, actor/kind, and a prior-content
snapshot (excluding history). An idempotent refinement does not add a version.
Direct edits to editable JSON are external proposal preparation, **not tracked API
mutations**: the next operation snapshots the submitted content. This is not a
general editing API or a complete audit of filesystem changes. Approved content
must remain identical to the snapshot submitted for approval.

`validate_requirement(record)` returns deterministic `code`, JSON Pointer `path`,
and `message` diagnostics. It checks closed schema shape, version/state/identity
history continuity, transition legality, named-human consequential entries,
approval completeness, and approved-content preservation. Mutating helpers raise
`ValueError` on invalid input, illegal states or denied authorization.

## Trust boundaries and limitations

Records, actor names, policies and history are **local attestations**, not
authenticated identities or cryptographic approvals. Structural history checks
catch accidental/inconsistent edits, not coherent rewriting of an entire record.
Validation does not reauthorize historical actors against a policy, prove behavior,
execute acceptance tests, or authenticate review evidence. Policy integrity and
human authentication belong to the caller/review environment. Do not present
passing validation as authenticated approval.

Original intent and history snapshots retain caller-supplied data and may contain
secrets. Generated question text does not copy that data. Apply the shared
`security.redact` projection boundary before displaying or exporting records and
diagnostics; redaction is best-effort, not a secret scanner. Treat all source text
as untrusted data, never executable instructions.

Fixtures: `examples/requirements/offline-sync-ambiguous.json` contains open
questions; `offline-sync-proposed.json` contains illustrative explicitly supplied
criteria and assumptions. Neither is approved or evidence of working sync.

Run library checks with `uv run pytest tests/test_requirements.py` and
`uv run ruff check src/lsm/requirements.py tests/test_requirements.py`.
CLI usage:

```sh
uv run lsm requirement create requirement:offline draft.json --intent "Support offline sync"
uv run lsm requirement refine draft.json questions.json
uv run lsm requirement validate questions.json
uv run lsm requirement transition examples/requirements/offline-sync-proposed.json approved.json --state approved --policy examples/governance/policy.json --actor demo-owner
```

The last command is an explicit local human approval attestation, not something an
agent may silently perform on behalf of the user. No requirements are approved
automatically by discovery, refinement, migration or documentation generation.
