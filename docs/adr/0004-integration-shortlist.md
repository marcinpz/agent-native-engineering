# ADR 0004 — Proposed integration shortlist and System Contract boundary

- **Status: PROPOSED — not adopted**
- Date: 2026-11-11
- Issue: [#21](https://github.com/marcinpz/agent-native-engineering/issues/21)
- Human architecture approval: **pending**
- Empirical provider/baseline acceptance: **pending**

## Context

The accepted [integration-first direction](../INTEGRATION_FIRST_ARCHITECTURE.md)
requires ANE to own model/governance/provenance, not analyzers, migration engines,
agents, CI or deployment runtimes. [The ecosystem
assessment](../research/ECOSYSTEM_ASSESSMENT.md) and its [source
registry](../research/ecosystem-sources.json) document primary evidence checked
2026-11-11. Suitability and cost remain inferences, not demonstrated gains.

Important constraints discovered: `rewrite-spring` at the observed revision uses
the Moderne Source Available License and is not cleared for redistribution or
managed service use. Root Apache licensing of OpenRewrite does not cover all
modules/recipes. The old Structurizr CLI is archived; consolidated tooling is the
current candidate. V2 OpenCode API documentation labels its surface experimental;
observed repository SHA is not an installed V2 binary pin.

## Proposal for human review

Prefer **stack A: minimal native evidence**, initially read-only: existing ANE
Git JSON/YAML, stable source refs/manifests, native test/build artifacts, optional
local OpenAPI compatibility reports, GitHub CLI/CI evidence and existing
Markdown/Mermaid views. OpenCode V2 is the first optional agent boundary, not a
core model dependency. Keep provider replacement possible. Reuse existing
CLI/model contracts exercised by #19 and coordinate proposed provider contracts
with #22; no competing adapter schema or SDK embedded by this ADR.

Propose a technology-independent System Contract as linked requirements,
observable behaviors, interfaces, capability constraints, evidence, unknowns and
approved exceptions. The [synthetic research
example](../../examples/research/system-contract-proposal.json) is **not** an
adopted production schema. Passing tests supplies bounded evidence, never a
blanket semantic-equivalence guarantee. Human approval is required to alter
requirements, accept exceptions or adopt consequential architecture.

Known claims reuse LSM's independent provenance origin, source and verification
axes; observed does not mean verified or approved. Missing application/target
facts stay unknown with null provenance and an explicit reason in the research
example, not a new provenance origin. This proposes no production schema change.

| Proposed action | Scope | Approval / evidence gate |
| --- | --- | --- |
| Build narrowly | Stable identity, provenance/uncertainty, approval, model reconciliation, constraint-conflict records and scoped context | Reuse/extend existing contracts only after human review |
| Integrate | Native manifests/tests/SCM/CI reports and existing renderer | Confined read-only inputs; provenance, errors and coverage retained |
| Integrate conditionally | OpenCode/Aider, OpenSpec or Spec Kit artifacts, Kantra/JDT LS, explicitly Apache-licensed OpenRewrite modules | Pin actual artifacts, review license/security, sandbox execution and approve task |
| Defer | Spring recipe bundle/service integration, full ReqIF/OSLC, broker, portal, advanced IR, WASI migration and optional REA | Legal/artifact review or actual use-case evidence missing |
| Reject | Archived Structurizr CLI as new dependency, bespoke analyzer/migration engine, mandatory proprietary dependency, auto-merge/deploy and automatic approval | Conflicts with direction or trust/maintenance constraints |

## Alternatives

1. **Stack B, modernization-rich:** Kantra/JDT findings, license-cleared recipes,
   dependency bots and Pact may improve coverage. Defer extra lifecycle/legal
   burden until A identifies a measured gap. Do not rebuild recipes to avoid terms.
2. **Stack C, enterprise interoperability:** ReqIF/OSLC, catalog and C4 integration
   may fit an existing enterprise toolchain. Service/identity/round-trip complexity
   is unjustified as the default offline MVP.
3. **Native tools/agent alone or buy an existing suite:** Konveyor, Moderne and AWS
   Transform are meaningful modernization comparators; Capra/Backstage/spec tools
   overlap parts of the product. Commercial terms are separate from OSS building
   blocks. No assumption ANE outperforms them; choose this alternative if ANE's
   governance/context value does not outweigh onboarding and maintenance cost.

## Consequences if approved later

Smaller operational footprint, explicit unknowns and replaceable integrations;
initial mapping may remain manual and incomplete. No language-independent
reverse engineering, full runtime semantics, authenticated approvals or platform
equivalence is implied. Per-component licensing and provider API changes require
maintenance. Application source remains untouched during evaluation.

## Validation and unresolved decisions

The milestone tests only source-registry/contract/document structural consistency;
they do not validate factual claims or upstream runtime behavior. Follow the
assessment's safe pinning/sandbox PoC plan and same-tools agent-only comparison.
The coordinator's [integration gate report](../verification/INTEGRATION_GATE.md)
has been inspected and records limited native Git + LSM CLI + unittest plumbing
(573 tests; 25-step source and installed-wheel flows), not Spring Boot or agent
provider execution. It was not independently rerun here; integration/CI linkage
remain coordinator-owned. Paid model runs require budget approval. Exact
fixture/tool artifacts/hashes, numerical
success thresholds, recipe legal clearance and target-host capabilities remain
pending. This ADR neither authorizes execution/deployment nor closes #21.
