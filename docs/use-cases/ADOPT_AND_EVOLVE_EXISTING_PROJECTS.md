# Reference use cases: adopt and evolve existing software

Status: product scenarios; **not yet fully implemented**. A bounded UC-01 read-only
manifest/Git adoption experiment is available through #24; see
[workspace usage](../WORKSPACE.md) and [measured scope](../verification/ADOPTION_EXPERIMENT.md).
It does not provide automatic application analysis, build/migration or agent execution.
See [integration-first direction](../INTEGRATION_FIRST_ARCHITECTURE.md).

## UC-01 — Adopt an existing application with minimal friction

**Persona:** maintainer of a Java/Spring Boot service deployed to Google Cloud Run, or any other supported stack.

**Trigger:** connect a Git repository and request `ane init` / `ane import` (illustrative command names).

**Expected flow:**
1. Detect project boundaries and existing tools without changing application code.
2. Import verifiable evidence from source manifests, Maven/Gradle, deployment descriptors, APIs, tests, Git history and approved providers.
3. Propose a small, Git-friendly `.ane/` workspace with model, references, decisions, documentation and workflows. Do not duplicate source trees, secrets or generated caches.
4. Produce a human-readable overview and an agent-consumable scoped context, with evidence references and uncertainty.
5. Allow opt-in refresh and detect drift between model and implementation.

**Candidate layout (design proposal, not frozen schema):**
```text
my-service/
  src/
  pom.xml
  Dockerfile
  .ane/
    project.yaml
    model/
    knowledge/
    requirements/
    docs/
    workflows/
```
For multi-repository systems, allow the workspace in a **separate orchestration repository** instead of requiring changes to every source repo.

**Acceptance criteria:** fresh-clone onboarding is documented; no mandatory agent/LLM/cloud credentials for offline read-only import; generated docs cite sources; unknowns are visible; idempotent refresh has reviewable diffs; source code remains untouched. No vendor-specific format in the core LSM.

## UC-02 — Understand and document an unfamiliar application

**Persona:** new engineer, architect, support engineer or agent.

**Questions:** What does the service do? Which APIs and external services does it use? How does auth work? How is it deployed to Cloud Run? What happens on external API failure?

**Expected flow:** query Living System Model, inspect cited evidence, navigate components/requirements/diagrams, distinguish observed behavior from inferred assumptions and unresolved questions. Generate deterministic Markdown/Mermaid views using existing documentation tools where suitable.

**Acceptance criteria:** each significant claim links to source or is explicitly unverified; onboarding works without custom UI; changes to source can trigger proposed documentation refresh.

## UC-03 — Evaluate Spring Boot 4 migration before modifying code

**Persona:** maintainer planning Spring Boot 3 → 4 upgrade.

**Expected flow:**
1. Inventory actual Java/Spring Boot versions, Maven dependencies, plugins, tests, APIs, Cloud Run deployment and runtime constraints.
2. Use current official compatibility/migration guidance and existing analyzers; report unsupported or uncertain dependencies.
3. Produce a reviewable migration proposal: scope, impact graph, risks, options, acceptance criteria, test plan and rollback considerations.
4. Obtain human approval before edits. Evaluation itself must be read-only.

**Acceptance criteria:** grounded compatibility report with versions and citations; clear go/no-go and unknowns; zero source edits during evaluation; reproducible report artifact under `.ane/workflows/` or an external workspace.

## UC-04 — Execute migration with existing tools and reconcile

**Expected flow:** on approval, delegate mechanical Java refactors to **OpenRewrite** recipes where applicable, contextual changes to **OpenCode** or interchangeable agent provider, verification to Maven/test/CI and optional isolated Cloud Run validation. Open a reviewable PR; never auto-merge or deploy by default. Reconcile LSM, decisions and docs from verified results.

**Acceptance criteria:** no custom Spring Boot migration engine; documented tool versions and recipe selection; failing tests block completion; all code changes visible in PR; model changes reference implementation/test evidence; human approval for consequential actions.

## UC-05 — Extend a heterogeneous multi-repository system

**Persona:** team managing backend, frontend, mobile and infrastructure repos.

**Expected flow:** attach multiple repositories, map cross-repo interfaces and requirements, propose a feature, calculate impacted components, delegate scoped tasks to agents, coordinate PRs and tests, reconcile shared LSM. Workspace may live in a dedicated system repo.

**Acceptance criteria:** stable cross-repo IDs and references; no assumptions about one language or hosting provider; partial failures and unresolved changes remain explicit.

## Product guardrails and evaluation

ANE **coordinates** existing tools; it does not implement reverse engineering, a Java parser, Spring migration recipes, a new coding agent or a CI server. REA is optional when binary/black-box analysis is needed. Provider results retain provenance, trust level and approval boundaries.

Compare the same tasks with and without ANE: onboarding time, migration assessment accuracy, agent context/token cost, PR correctness, test coverage, documentation freshness and human review effort. If ANE adds overhead without measurable benefit, simplify it.

Related: Epic #13, #19 integration gate, #20 end-to-end pilot, #21 tool assessment, #22 adapters, #23 orchestrated workflow, #5 impact, #6 context, #7 multi-repo.
