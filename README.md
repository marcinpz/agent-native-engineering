# Agent Native Engineering

A technology-agnostic, Git-versioned **Living System Model** linking declared
requirements, behaviors, architecture, interfaces, implementation observations,
tests and evidence across multiple repositories.

This Phase 0–1 MVP provides an open JSON Schema, Python reference library and
offline CLI. No graph database, LLM, service or UI is required.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git.
`uv` can install Python 3.12 if it is not already available.

```sh
git clone https://github.com/marcinpz/agent-native-engineering.git
cd agent-native-engineering
uv sync --locked --python 3.12
uv run lsm --help
```

## Try the model

```sh
uv run lsm init my-system.json --id system:demo --title "Demo system"
uv run lsm validate my-system.json --json
uv run lsm validate examples/shop.json
uv run lsm inspect examples/shop.json
uv run lsm inspect examples/shop.json --node component.backend --json
uv run lsm import examples/shop.json my-system.yaml
uv run lsm show my-system.yaml --json
```

`init` creates a valid empty model. `import` validates and converts an existing
model document; it does not scan source repositories. `inspect` / `show` validate
before displaying a summary or a node. Writes refuse existing destinations unless
`--force` is supplied. JSON/YAML conversion preserves data, not comments or layout.
Serialization is deterministic for an unchanged model; array order is preserved.

The shop fixture describes logical backend, web, mobile and data-store components
and repository boundaries; it does not implement or create those applications.
Its test/evidence artifacts are illustrative, not proof of working shop software.

### Errors and trust

`validate --json` returns `{"valid": true, "errors": []}` on success or structured
errors with `code`, JSON Pointer `path` and `message` on failure. Exit codes:
**0** success, **1** invalid model or missing node, **2** usage/I/O/parse error.

Validation checks schema, references, duplicate IDs, allowed relation endpoints,
evidence references and forbidden `supersedes` cycles. Other dependency cycles
are allowed. Unknown schema versions are rejected, not automatically migrated.

**Passing validation does not prove system behavior or authenticate evidence.**
Declared/inferred/observed origins and unverified/verified states are separate.
Verified claims must link to evidence, but this CLI does not execute tests, inspect
external URIs, approve requirements or verify evidence authenticity.

## Development

```sh
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run lsm validate examples/shop.json --json
uv build
```

CI runs these checks. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Layout and decisions

- `src/lsm/schemas/model.schema.json`: language-independent schema, version 1.0.
- `src/lsm/`: storage, graph validation and CLI reference implementation.
- `examples/`: small multi-component system and illustrative evidence.
- `tests/`: schema, graph, persistence and CLI tests.
- [Model reference](docs/MODEL.md): types, relations and provenance.
- [ADR 0001](docs/adr/0001-mvp-stack-and-contract.md): stack, contract and limitations.
- [Architecture](docs/ARCHITECTURE.md) and [roadmap](docs/IMPLEMENTATION_PLAN.md).

Next phases may add repository discovery, deterministic Markdown/Mermaid views,
requirement refinement, semantic diff, impact analysis and scoped agent context.
They are intentionally not implemented here. Open questions include evidence
authenticity, approval enforcement, migrations and splitting large model files.

## License

[Apache-2.0](LICENSE).
