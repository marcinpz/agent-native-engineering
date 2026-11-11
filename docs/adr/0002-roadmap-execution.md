# ADR 0002: Incremental roadmap execution

Status: accepted. Project owner authorized issues #2–#11 and the boundaries below.

## Design and boundaries

Keep the Python library/CLI, portable JSON/YAML artifacts and Git workflow. No
service, graph database, LLM dependency or agent orchestration framework is added.
Preserve schema 1.0; introduce additive model schema 1.1 only for explicit
governance metadata. Migration is explicit, validates both ends and preserves IDs
and provenance. Lifecycle, proposals, context packs and execution records are
versioned companion documents, not silently appended unknown model fields.

All projections must apply a shared redaction boundary. Untrusted repository
data is data, never executable instructions. Discovery reads only explicitly
listed roots/manifests, not arbitrary source trees or environment files.
Local approval records are explicit attestations, not authenticated identities.
Only human actors explicitly authorized by a supplied policy may authorize
consequential state transitions; default is deny. Existing verified claims cannot
be promoted or approval granted by inference or migration.

Each child issue gets its own commit/branch/PR. Dependent PRs are stacked on the
previous branch until human review/merge. Do not merge automatically.

## Order and contracts

1. #10 governance: schema selection/migration, policy and redaction primitives.
2. #2 read-only manifest discovery; #3 deterministic, cited Markdown/Mermaid.
3. #4 requirement lifecycle; #5 semantic diff and explainable graph impact.
4. #6 bounded task context exposed through the existing offline CLI.
5. #7 local-only multi-repository demo with approval, tests, reconciliation records.
6. #8 benchmark harness, methodology and honestly labeled smoke measurements.
7. #9 research ADR/prototype proposal only; no compiler.
8. #11 documented end-to-end workflow, install and CI smoke gates.

Core functions consume/return JSON-compatible dictionaries and do not write unless
explicitly asked. Commands validate input before processing. Main CLI integration
is owned by the coordinator; subagents have disjoint paths. Results distinguish
invalid artifacts from filesystem/usage failures using existing exit codes.

## Acceptance and verification

Every workstream includes positive/negative automated tests and documented CLI
examples. Preserve previous tests. Run Ruff, pytest, wheel/source build and an
installed-package smoke test, plus GitHub CI. Demonstrate discovery idempotence,
deterministic docs/context, denied unauthorized transitions, offline-sync impact,
failure-aware local workflow and benchmark aggregation. Record actual commands
and outputs in PRs, not speculative success claims.

## Explicit limitations

No changes to unrelated repositories, production deployment or automatic merges.
Demo repositories live only under an explicitly selected new demo directory.
Benchmark smoke trials are not real agent quality/cost comparisons. Paid agent
experiments require a separate budget; unknown costs/tokens remain null. Research
#9 ends with a proposed experiment and decision criteria, not adopted semantic IR.
The epic cannot be considered empirically complete before these external trials.
