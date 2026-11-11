# Integration-first, agent-agnostic architecture

Status: **Accepted product direction** (2026-11-11). This is a guiding principle, not a claim that every adapter already exists.

## Mission

Agent Native Engineering (ANE) is a **high-level semantic and orchestration layer over existing software systems and tools**. It helps humans and agents understand, govern and evolve systems across repositories and technology stacks.

ANE must **integrate mature existing tools rather than rebuild their capabilities**. Reverse engineering, decompilation, static analysis, code generation, CI execution and hosting are provider capabilities, not ANE product pillars.

## ANE owns

- A versioned **Living System Model** connecting intent, requirements, domain/behavior, architecture, components, interfaces, decisions, evidence and tests.
- Provenance, uncertainty, traceability, human approvals and change governance.
- Tool-neutral provider capability discovery, normalized results and evidence links.
- Change planning, dependency/impact analysis and task-scoped context assembly.
- Workflow coordination across agents, repositories, tests and PRs; reconciliation of observed implementation with the model.

## ANE delegates

- Coding agents: OpenCode first, other agents through interchangeable providers.
- Source/binary understanding: existing AST/LSP, REA or other specialized analyzers when relevant.
- Source control and reviews: GitHub/GitLab.
- Specifications and documentation: integrate existing standards and generators when appropriate.
- CI/CD, deployment, infrastructure and runtime observability: existing providers.

No mandatory reverse-engineering engine, compiler, LLM vendor, graph database or execution runtime. MCP, CLI and APIs are possible transport mechanisms, not a single mandatory protocol.

## Integration contract principles

1. **Capability-oriented:** providers advertise operations and constraints; orchestration depends on capabilities, not brands.
2. **Explicit trust:** record source, timestamp, evidence, confidence and whether information is declared, inferred or verified; never promote inferred claims automatically.
3. **Safe by default:** read-only discovery first; writes, PR creation, merges and deployments require appropriate authorization and approval.
4. **Portable:** model and workflows stay usable if an agent or provider is replaced.
5. **Thin adapters:** reuse native tools; do not duplicate parsers, decompilers, agent runtimes or CI engines.
6. **Reconciliation:** changes made inside or outside ANE can be detected and reflected as proposed model updates.
7. **Measurable value:** evaluate integration cost, correctness, human review load, agent context efficiency and maintainability.

## Target workflow

Connect existing system(s) and providers → discover/import evidence → build/refine Living System Model → human states goal or requirement → impact analysis and plan → compile task-scoped context → delegate to agent(s) and tools → verify with existing test/CI infrastructure → review PRs → reconcile model and regenerate documentation.

## Roadmap implications

Before implementing new analysis or orchestration engines, inventory existing open-source tools and document build-vs-integrate decisions. Implement provider contracts and one end-to-end vertical slice using existing tools. Reverse engineering is an **optional provider integration**, not a standalone ANE workstream. Treat advanced semantic IR as optional research, not an MVP prerequisite.

See Epic #13 and issues #5, #6, #7, #19 and #20.
