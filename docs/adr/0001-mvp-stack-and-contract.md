# ADR 0001: Portable model and Python reference implementation

Status: accepted by project owner for issue #1.

## Decision

Use Python 3.12+, uv, pytest, Ruff, argparse, jsonschema and PyYAML. The public
contract is JSON Schema Draft 2020-12, not Python classes. Store a whole model in
one JSON or YAML document. License the project under Apache-2.0.

TypeScript would also support a portable CLI but introduces a Node toolchain;
Pydantic would couple schema evolution to Python definitions. A graph database,
workflow engine, UI and repository scanner are outside this milestone.

## Shared implementation contract

Package: `lsm`, command: `lsm`, schema resource: `lsm/schemas/model.schema.json`.
Document: `schema_version: "1.0"`, `model: {id, title}`, `nodes: []`, `edges: []`.
Unknown fields are rejected. IDs are nonempty stable strings matching
`^[a-z][a-z0-9_.:-]*$`; node and edge IDs share a namespace. Do not derive IDs
from titles or paths. Node version is a positive integer.

Node required fields: `id`, `type`, `title`, `version`, `provenance`.
Optional: `description`, `evidence` (list of evidence-node IDs), `acceptance_criteria`
(list of nonempty strings), `open_questions` (list of nonempty strings),
`constraints` (list of nonempty strings), `owner`, `approval` (pending/approved/rejected),
`uri`, `commit`, `timestamp`, `confidence` (0..1).
Requirement nodes additionally require nonempty acceptance_criteria and approval.
Evidence nodes additionally require uri. `timestamp` uses date-time format;
it is optional because static example artifacts need not invent observation times.

Node types: requirement, domain_concept, behavior, component, interface,
repository, decision, implementation, test, evidence.

Provenance required fields: `origin` (declared/inferred/observed), `source`
(nonempty string), `verification` (unverified/verified); optional `rationale`.
Verified claims require at least one evidence reference. This is structural
traceability, NOT independent verification of evidence contents or truth.
Evidence nodes themselves remain unverified unless supported by other evidence.
Approval is independent of verification; no command approves requirements.

Edge required fields: `id`, `type`, `source`, `target`, `provenance`;
optional `evidence` (evidence-node IDs).
Allowed source -> target types:

| Relation | Source | Target |
|---|---|---|
| satisfies | behavior, component, interface, implementation | requirement |
| depends_on | component, interface, repository, implementation | component, interface, repository, implementation |
| implemented_by | requirement, behavior, interface, component | implementation, component |
| verified_by | requirement, behavior, interface, component, implementation | test, evidence |
| supersedes | any | same type as source |
| exposes | component | interface |
| decided_by | any except evidence | decision |
| belongs_to | component, interface, implementation, test | repository |

Only supersedes must be acyclic. Other cycles are not automatically invalid.
Schema version 1.0 only; reject unknown versions. No automatic migrations yet.

Library API:
- `load_model(path) -> dict`, `save_model(model, path) -> None` in `lsm.storage`.
  JSON/YAML only, safe YAML, duplicate mapping keys rejected, stable sorted keys,
  no implicit model mutation; serialization need not preserve comments/formatting.
- `validate_model(model) -> list[dict]` in `lsm.validation`.
  Diagnostics contain `code`, `path` (JSON Pointer), `message`; deterministic order.
- `ModelIOError` in `lsm.storage` for actionable parse/format/write errors.

## Vertical slice and acceptance

CLI init/import/validate/inspect (show alias), optional machine-readable JSON
output, no overwrite without --force. Validate before import/write. Invalid
models return exit 1, I/O/usage errors exit 2; successful commands return 0.
Empty init model is valid. Inspection supports summary and node lookup.

Tests cover schema errors, duplicate IDs, missing references, typed relations,
supersedes cycles, evidence requirements, JSON/YAML round trips, unsafe/ambiguous
input, CLI success/failure and a backend/web/mobile/store multi-repo fixture.
CI runs formatting, lint, tests and fixture validation from a fresh checkout.

## Limitations and open questions

Logical repository boundaries in the fixture do not create or scan repositories.
Evidence authenticity, approval identity enforcement, migrations, richer criteria
objects, per-entity files and relation extensions need future decisions. Do not
interpret passing validation as system correctness or evidence verification.
Markdown/Mermaid generation belongs to Phase 2 and is deliberately excluded.
