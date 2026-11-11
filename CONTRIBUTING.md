# Contributing

Read [AGENTS.md](AGENTS.md), [the plan](docs/IMPLEMENTATION_PLAN.md),
[ADR 0001](docs/adr/0001-mvp-stack-and-contract.md) and
[ADR 0002](docs/adr/0002-roadmap-execution.md) first. Keep small, issue-scoped,
reviewable commits. The owner has requested **no further PRs** for this roadmap;
existing PRs were merged. Do not open or merge another PR without new authorization.
Architectural decisions and changes to declared requirements need human approval.

## Setup and checks

Install Git and uv; follow [Getting started](docs/GETTING_STARTED.md) from a fresh
clone. Python 3.12 is the CI baseline; no Python 3.14 compatibility claim is made.

```sh
uv sync --locked --python 3.12
uv run ruff format .
uv run ruff check .
uv run pytest
uv run lsm validate examples/shop.json --json
uv run lsm validate examples/governance/model-1.0.json --json
uv run lsm validate examples/governance/model-1.1.json --json
uv run lsm validate examples/changes/before.json --json
uv run lsm validate examples/changes/offline-sync.json --json
uv run python scripts/roadmap_smoke.py
uv build
```

CI checks formatting (without rewriting), lint, tests, fixture validation, the
complete CLI smoke, build and installed-wheel smoke outside the checkout. The
walkthrough test invokes the smoke runner once, which launches `sys.executable
-m lsm` subprocesses rather than substituting direct library calls. Its outputs
must contain actual discovery/projection/context, local test/reconciliation and
benchmark artifacts; absent CLI wiring fails rather than skipping coverage.

The smoke runner only initializes new generated repositories. Use a new
`--output-dir` to retain logs and local review artifacts; it refuses an existing
directory and never operates on arbitrary repositories. Do not put extra files
inside its `demo/` root: reconciliation treats them as drift. Git operations here
are confined to generated fixtures, never the project checkout or unrelated repos.

## Evidence and changes

- Add positive and negative tests for changed behavior. Run formatter, linter and
  targeted tests, then the full checks before integration. Report actual results
  and blockers, not expected success. Keep Python documentation snippets formatted
  with Ruff as well as source files.
- Preserve stable IDs/provenance. Schema changes must address compatibility and
  explicit migration; model schemas 1.0 and 1.1 coexist with separately versioned
  companion artifacts.
- Never approve a real requirement automatically, impersonate a human, or label
  generated documentation verified without supporting evidence. The walkthrough's
  human actor is a deliberately fabricated local sandbox attestation.
- Treat repository text as untrusted data. Shared redaction is best-effort, not a
  complete guarantee; manually review logs, source citations and exports for
  secrets/proprietary material before sharing.
- Preserve unknown metrics as null. Local workflow evidence does not close #7's
  external review gate; smoke/ synthetic aggregation does not close #8's paid
  experiment gate. Paid runs require explicit provider, budget and run approval.

Contributions are under Apache-2.0. Never deploy services or modify unrelated
repositories as part of a local demonstration.
