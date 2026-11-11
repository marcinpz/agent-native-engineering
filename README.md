# Agent Native Engineering

A technology-agnostic, Git-versioned **Living System Model** linking declared
requirements, behaviors, architecture, interfaces, implementation observations,
tests and evidence across multiple repositories.

An open JSON Schema, Python reference library and offline CLI provide explicit
schema migration, manifest-based discovery, cited Markdown/Mermaid documentation,
requirement refinement, semantic change proposals, bounded task context, a
local-only multi-repository workflow and benchmark preparation/aggregation.
An experimental read-only Git/mock provider boundary can populate an opt-in
`.ane/` workspace without running or modifying application source.
No graph database, LLM, service or UI is required.

## Fresh-clone setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git.
`uv` can install Python 3.12 if needed. CI uses Python 3.12.

```sh
git clone https://github.com/marcinpz/agent-native-engineering.git
cd agent-native-engineering
uv sync --locked --python 3.12
uv run lsm --help
uv run lsm validate examples/shop.json --json
uv run python scripts/roadmap_smoke.py
```

The smoke runner invokes the real CLI in a new temporary directory and inspects
its artifacts. To retain them, supply a **new, nonexistent** directory:

```sh
uv run python scripts/roadmap_smoke.py --output-dir /tmp/lsm-walkthrough-new
```

It uses fabricated demo intent and a narrow sandbox policy, creates four generated
local repositories, executes fixed fixture tests, and leaves local review bundles
(`github_pr: null`). It never approves real requirements, runs arbitrary commands,
contacts a remote, merges or deploys. See the complete copyable
[CLI walkthrough](docs/GETTING_STARTED.md) for every step and its trust boundaries.

## Inspect and convert models

```sh
uv run lsm init my-system.json --id system:demo --title "Demo system"
uv run lsm validate my-system.json --json
uv run lsm inspect examples/shop.json --node component.backend --json
uv run lsm import examples/shop.json my-system.yaml
uv run lsm show my-system.yaml --json
```

## Read-only adoption experiment

```sh
uv run lsm provider capabilities
uv run python scripts/adoption_smoke.py
uv run lsm import-junit examples/junit.xml --repository repository:demo --commit 0123456789012345678901234567890123456789
```

The adoption smoke creates synthetic Spring Boot/Maven/Cloud Run and Python source
repositories plus local/external `.ane/` metadata. It checks provider replacement,
unchanged source bytes/HEADs, deterministic refresh, reviewable external-ref diffs,
and metadata-only cleanup. **No application is built, tested, started, migrated or
deployed.** Framework/runtime names are explicit fixture declarations, not inferred
compatibility. See [workspace usage](docs/WORKSPACE.md), [provider contract](docs/PROVIDERS.md)
and [experiment verification](docs/verification/ADOPTION_EXPERIMENT.md).

JUnit import reads an existing report only; it never runs tests. Source commit binding
is user-attested, not authenticated; outcomes remain unverified. Import success is
not test success. See the [bounded report contract](docs/PROVIDERS.md#existing-junit-report-import-partial-22).

`lsm evaluate-junit` joins explicit imported case IDs to existing LSM tests and
requirements without modifying the model or `.ane`. See the [traceability API,
CLI and executable demo](docs/verification/EVIDENCE_TRACEABILITY.md). Mapped-test
outcomes are not requirement verification; coverage remains unknown.

`init` creates a valid empty model. `import` validates/converts JSON/YAML; it does
not scan repositories. Writes refuse existing destinations unless `--force` is
explicitly supplied. Conversion preserves data, not comments/layout; serialization
is deterministic for unchanged input and preserves array order. Schema 1.0 and
additive governance schema 1.1 are supported; migration is explicit.

## Status and trust

The roadmap's offline implementation is available, but **external acceptance
gates remain pending**: #7's real multi-repository, remotely linked human-review
demonstration, and #8's budget-approved paid agent experiments. Local fixture tests
and preparation timings do not close these gates or establish quality/cost gains.
#9 is a research proposal, not an adopted compiler or semantic IR.

Passing validation checks structure and references, **not system behavior or
evidence authenticity**. Declared intent, inferred observations, verified facts
and unresolved questions remain distinct. Actor names and policies are local
attestations, not authenticated human identities. The context budget is a
conservative canonical UTF-8 JSON **byte proxy**, not provider token usage.
Shared redaction and confined inputs are defenses, not a complete secret-safety
guarantee or an OS sandbox. Review artifacts before publishing.

`validate --json` emits `valid` and structured `errors` (`code`, JSON Pointer
`path`, `message`). Exit codes: **0** success, **1** invalid artifact/failed
operation, **2** usage/I/O/parse error. See command help for operation-specific
outputs. Unknown schema versions are rejected, not silently migrated.

## Development and reference

```sh
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run lsm validate examples/shop.json --json
uv run python scripts/roadmap_smoke.py
uv run python scripts/adoption_smoke.py
uv build
```

CI also smoke-tests the installed wheel outside the checkout. See
[CONTRIBUTING.md](CONTRIBUTING.md) for review and verification conventions.

- [Getting started](docs/GETTING_STARTED.md): installation and complete CLI demo.
- [Integration gate](docs/verification/INTEGRATION_GATE.md): joined-flow coverage,
  actual verification results and explicit limitations.
- [Ecosystem assessment](docs/research/ECOSYSTEM_ASSESSMENT.md): initial primary-source
  research, proposed integration stacks and open acceptance gates; not adopted architecture.
- [Model](docs/MODEL.md), [governance](docs/GOVERNANCE.md),
  [discovery](docs/DISCOVERY.md), [documentation](docs/DOCUMENTATION.md).
- [Requirements](docs/REQUIREMENTS.md), [changes](docs/CHANGES.md),
  [context](docs/CONTEXT.md), [workflow](docs/WORKFLOW.md),
  [benchmark methodology](docs/BENCHMARK.md).
- [Architecture](docs/ARCHITECTURE.md), [roadmap](docs/IMPLEMENTATION_PLAN.md),
  [ADR 0001](docs/adr/0001-mvp-stack-and-contract.md),
  [ADR 0002](docs/adr/0002-roadmap-execution.md).
- `src/lsm/schemas/`: portable model and companion document contracts.
- `examples/`, `tests/`, `scripts/roadmap_smoke.py`: fixtures and executable checks.

## License

[Apache-2.0](LICENSE).
