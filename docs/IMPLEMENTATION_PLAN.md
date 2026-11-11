# Implementation plan — Agent Native Engineering

## Vision
A Living System Model (LSM) is a versioned, machine-readable graph connecting requirements, behaviors, architecture, domain concepts, APIs, components, repositories, decisions, implementation evidence and tests. Humans specify intent and approve changes; agents propose and execute verified changes. Code and docs are projections/evidence, not automatically guaranteed faithful to intent.

## Non-goals for MVP
- A new programming language or compiler.
- Mandatory WASM, MLIR or specific runtime.
- Autonomous production deployment.
- Perfect reverse engineering of arbitrary codebases.
- Building a large graphical editor before proving the model.

## Core concepts
Node: stable ID, type, title, description, status, provenance, evidence, version.
Edge: typed relation (satisfies, depends_on, implemented_by, verified_by, supersedes, exposes, decided_by) with provenance.
Requirement: intent, acceptance criteria, open questions, constraints, owner/approval.
Evidence: source URI/ref, commit hash, test output, timestamp, confidence and verification state.
Change proposal: before/after semantic diff, impact, assumptions, risks, affected components, tests, approval state.
Views: architecture C4, requirements traceability, behavioral flows, onboarding documentation.

## Phases

### Phase 0 — Foundation
- Establish repo structure, licensing decision, contribution conventions, ADR template.
- Select a minimal language/toolchain based on maintainability; document choice in ADR.
- CI for lint, unit tests and schema validation.
- Acceptance: fresh clone can run documented commands and CI checks.

### Phase 1 — Living System Model
- Versioned JSON Schema for nodes, edges, requirements, decisions and evidence.
- Storage in Git-friendly JSON/YAML; stable IDs and schema migrations.
- Graph validation (missing nodes, invalid relation types, duplicate IDs, cycles only where forbidden).
- CLI: init, validate, inspect, export.
- Example system: backend API, web UI, mobile app and database across logical repo boundaries.
- Acceptance: model loads, invalid references fail, round-trip serialization is stable, tests pass.

### Phase 2 — Discovery and documentation
- Import repository metadata and explicit manifests; use parsers selectively.
- Mark inferred relations as unverified until confirmed.
- Generate Mermaid/C4-style diagrams, Markdown docs, onboarding summaries, traceability matrix.
- Acceptance: docs regenerate deterministically from the same model; every claim has source/provenance.

### Phase 3 — Requirements and change management
- Interactive requirement refinement; unresolved questions and explicit approval gates.
- Semantic diff, impact analysis across repositories, change proposals.
- Acceptance: offline-sync example shows affected mobile, backend, storage, API and tests; ambiguous requirements remain open rather than silently assumed.

### Phase 4 — Agent integration
- OpenCode-facing CLI/tools and task-specific context compiler.
- Generate scoped context packages with token budget, links and evidence.
- Agent workflow: propose, validate, implement in PR, test, update model, human review.
- Acceptance: agent completes one end-to-end change in a demo multi-repo system and leaves traceable evidence.

### Phase 5 — Research
- Benchmark baseline repo+docs vs LSM+context compiler.
- Metrics: task success, pass@1, token cost, repair loops, latency, correctness of impact analysis, onboarding accuracy.
- Optional typed semantic IR and alternative execution backends only after evidence warrants them.

## First ten work items
1. ADR for MVP stack and storage.
2. Project layout and CI.
3. Schema for model nodes.
4. Schema for typed edges.
5. Provenance/evidence and verification states.
6. Model validation library.
7. CLI init/validate/inspect.
8. Sample multi-component system model.
9. Deterministic Markdown + Mermaid export.
10. Integration tests and onboarding guide.

## Guardrails
Use stable identifiers; make uncertainty explicit. Require approvals before changing declared requirements. Avoid conflating observed code with intended behavior. Keep a human-readable export and Git review workflow. Prefer portable open formats.
