# Instructions for OpenCode agents

Read README.md and docs/IMPLEMENTATION_PLAN.md before making changes.

## Mission
Build an open-source, technology-agnostic agent-native software engineering platform. The primary artifact is a versioned Living System Model linking user intent, requirements, domain concepts, behaviors, architecture, interfaces, implementation evidence, tests and decisions. Support multiple repositories and heterogeneous systems (backend, web, mobile, infrastructure).

## Principles
- Human approval for consequential architectural decisions and changes to requirements.
- Never claim generated documentation is verified without supporting evidence.
- Distinguish declared intent, inferred observations, verified facts and unresolved questions.
- Stable IDs and traceable links for all model entities.
- Small, reviewable PRs with tests; keep implementation language and runtime replaceable.
- No WASM requirement, no proprietary vendor lock-in, no premature compiler or full UI.
- Never silently modify unrelated repositories or deploy services.

## Workflow
1. Read implementation plan and existing code.
2. Write a short design and acceptance criteria for the current task.
3. Implement the smallest vertical slice with tests and sample data.
4. Run formatter, linter and tests; report actual results.
5. Update docs and model schemas; summarize decisions and unresolved questions.
6. Open a PR referencing the issue; stop before unrelated phases.

## First assignment
Implement Phase 0 then the minimal Phase 1: schema for entities/relations with provenance, JSON/YAML persistence, validator, CLI import/validate/show, and a tiny multi-component example. Avoid building a full graph DB or UI.
