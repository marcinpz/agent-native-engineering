# Contributing

Read AGENTS.md, docs/IMPLEMENTATION_PLAN.md and docs/adr/0001-mvp-stack-and-contract.md.
Use a feature branch and small commits; link your pull request to its issue.
Architectural and declared-requirement changes need human approval.

Install Python 3.12+ and uv, then run:

```sh
uv sync --locked --python 3.12
uv run ruff format .
uv run ruff check .
uv run pytest
uv run lsm validate examples/shop.json --json
uv build
```

Add tests for changed behavior. Do not label documentation or claims verified
without supporting evidence. Schema changes must discuss compatibility and
migration; the current implementation only accepts schema version 1.0.

Contributions are under Apache-2.0; do not include secrets or proprietary data.
