# Deterministic documentation

`lsm.documentation.render_docs(model: dict) -> dict[str, str]` returns `index.md`,
`context.mmd`, `components.mmd`, `traceability.md` and `onboarding.md`. It does not
write files, fetch sources, scan repositories or execute tests. Invalid models
raise `ValueError` before rendering. The caller owns output-directory handling.

The raw model is validated before the entire model passes through the shared
`lsm.security.redact` boundary. Input is not mutated. Nodes and edges are ordered
by stable ID; reordering those arrays produces identical output. No timestamps
are invented. Criteria and question order is preserved.

Every projected node and relation includes its origin, source, verification
declaration and evidence references. Details inherit and repeat the node citation.
Source references and URIs are escaped non-clickable text, not links. Only fixed
internal output filenames are linked. Markdown punctuation is entity-escaped;
Mermaid uses generated node identifiers and textual Unicode code-point escapes
for unsafe label characters. Neither projection permits model-controlled HTML,
Mermaid statements, directives, clickable links or Markdown fences.

The context diagram shows components, repositories and their explicit relations;
the component diagram also includes interfaces and implementations. These are
graph projections, not authenticated C4 architecture or verified diagrams.

Requirement traces follow inverse `satisfies` and forward `implemented_by` edges,
then show `verified_by` links on reachable nodes. Each displayed path cites its
edges. Dependencies, supersession and decisions are not treated as implementation
proof. Cycles are bounded by visited IDs. Missing implementation/test links are
reported as **model gaps**, never proof of missing behavior. Linked test or
evidence nodes do not establish execution, passing results or authenticity.

The inventory retains declared questions, criteria, constraints and approval
metadata. Onboarding includes repository boundaries, dependencies and decision
overviews. A `verified` label is explicitly a model declaration, not renderer
authentication. Human review and supporting evidence remain necessary.

## Regression checks

```sh
uv run pytest tests/test_documentation.py
uv run ruff check src/lsm/documentation.py tests/test_documentation.py
uv run ruff format --check src/lsm/documentation.py tests/test_documentation.py
```

`tests/golden/docs/` contains reviewed projections of `examples/shop.json`, whose
repository, implementation and test artifacts remain illustrative.
