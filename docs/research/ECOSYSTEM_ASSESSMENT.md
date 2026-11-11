# Ecosystem assessment: requirements-preserving evolution

**Initial substantive milestone for [#21](https://github.com/marcinpz/agent-native-engineering/issues/21), checked 2026-11-11. Not completed research.**
Decision state: **PROPOSED**, awaiting human review of
[ADR 0004](../adr/0004-integration-shortlist.md). This does not supersede the
accepted [integration-first direction](../INTEGRATION_FIRST_ARCHITECTURE.md).
No application source, provider configuration, service or deployment was changed.

## Design and acceptance criteria for this milestone

Keep the research outside production schemas and adapters. Deliver a primary-source
inventory, three alternative stacks, a build/integrate/defer/reject proposal, a
portable System Contract example, three read-only reference evaluations, and an
executable **structural** consistency check. Build on #19's native CLI/model
integration evidence and coordinate proposed provider boundaries with #22, rather
than inventing another engine. At least 12 tools must cover agents, specifications,
AST/LSP, verification, modernization, diagrams and SCM/CI. Every selected tool needs
an observed revision/date, license evidence and explicit caveats. Versions not
observed are **unknown**, not guessed. Consequential recommendations must go to a
human before adoption or implementation.

**Acceptance left open:** real-provider PoC, actual Spring fixture assessment,
full agent-only comparison, budget-approved model runs, artifact-level licensing
review and architecture approval. The coordinator's limited native-tool plumbing
PoC is available as separately reported evidence below; it does not satisfy these
application/provider gates. Reading `gh issue view` and primary GitHub APIs is
research collection, not the proposed end-to-end provider PoC.

## Evidence method and limits

- **Observed documentation:** official repository/API/license text or official
  documentation was read. It establishes what the source says, not that software
  works as described. GitHub license contents were decoded, not inferred from
  stars, badges alone or search snippets. Root license exceptions are called out.
- **Inferred:** all maturity, fit, complexity, security/lock-in judgments below.
  These are screening assessments, not benchmarks or legal opinions.
- **Proposed:** every ANE integration, contract field and stack in this document.
  None is made deployed merely because the upstream has a CLI/API/MCP server.
- **Unknown:** unavailable versions, actual application dependencies, exhaustive
  behavior, target-host capabilities and empirical benefit remain unresolved.

[ecosystem-sources.json](ecosystem-sources.json) records full observed commit SHAs,
license blob refs, feature and maintenance evidence URLs, check statuses, failed
lookups and pending gates. Repository metadata, current commit, README and license
were separate API reads, not an atomic release snapshot. Commit dates are latest
**observed default-branch commits**, not release dates or promises of support.
Mutable documentation has a checked date, not an invented release/ref. A source
SHA is not a safe binary pin until its artifact, dependencies and security status
have been reviewed. Offline tests validate these artifacts' structure and links
to each other; **they do not prove claims or live documentation correctness**.
The [independent review record](ECOSYSTEM_REVIEW.md) documents targeted primary-source
checks, sampled license/maintenance refs and corrected proposal findings. It does
not certify all matrix capabilities, application behavior or legal suitability.

### Existing limited native-tool plumbing baseline

The coordinator's [integration gate report](../verification/INTEGRATION_GATE.md)
was read in the separate integration worktree on 2026-11-11; it is to be integrated
by the coordinator, not copied/modified here. It records real native **Git + LSM
CLI + unittest** composition: **573 full tests**, a **25-step** joined source CLI
walkthrough and the same **25-step installed-wheel** flow, including source-byte
and model-trust preservation checks. Reported environment: Git 2.53.0, CPython
3.12.9, uv 0.6.7; baseline `06f3e5338afcaec0e827b72619df4d1279e69876` plus gate
changes. It links [CI run 43053661730](https://github.com/marcinpz/agent-native-engineering/actions/runs/43053661730)
for gate commit `57aae63`. Retained local artifacts are reported at
`/tmp/opencode/ane-integration-gate-19-20261111` (not a portable published artifact).
This milestone inspected the report, **did not independently rerun that gate** or
audit its retained artifacts/CI. This is useful existing plumbing evidence, **not**
a Spring Boot/Maven/OpenRewrite/OpenCode execution, real-provider acceptance,
paid agent experiment or agent-only benefit comparison. Final integrated commit
and CI linkage remain the coordinator's responsibility.

## Capability / license / maintenance matrix

All rows checked **2026-11-11**. Short SHAs below resolve to full SHAs and exact
maintenance timestamps in the source registry. `L` links to actual license evidence;
tool links provide primary feature evidence. Unlisted release versions are unknown.
Interfaces are **documented upstream**, not deployed ANE adapters. Standard rows
describe interoperability specifications, not installed tools.

| ID | Tool / observed capability | License and scope | Observed revision / maintenance signal | Documented interface and deployment |
| --- | --- | --- | --- | --- |
| `opencode` | [OpenCode V2](https://opencode.ai/docs/): coding agent, [automation CLI](https://opencode.ai/docs/cli), [HTTP API](https://opencode.ai/docs/api) | MIT [L](https://api.github.com/repos/anomalyco/opencode/license); model/hosted services separate | `aa08bb2e347e`, 2026-11-11; dev commit **not mapped to a V2 installed binary** | Local CLI/shared background service; experimental HTTP API. No SDK invocation or config changes in this milestone. |
| `aider` | [Aider scripting](https://aider.chat/docs/scripting.html): one-shot editing with `--message` | Apache-2.0 [L](https://api.github.com/repos/Aider-AI/aider/license); model terms separate | `5dc9490bb35f`, 2026-05-22 | Local CLI; Python scripting API explicitly unsupported/stability not guaranteed. Defaults may auto-commit; never invoke casually for read-only import. |
| `openspec` | [OpenSpec README](https://api.github.com/repos/Fission-AI/OpenSpec/readme): spec/change proposal and archive workflow | MIT [L](https://api.github.com/repos/Fission-AI/OpenSpec/license); assistants/community bundles separate | `a959be77cf04`, 2026-11-10 | CLI, Git files, assistant commands; no generic ANE MCP/API capability assumed. Initialization writes guidance. |
| `spec-kit` | [Spec Kit README](https://api.github.com/repos/github/spec-kit/readme): specification, plan, implementation workflows; extensions/presets | MIT [L](https://api.github.com/repos/github/spec-kit/license); catalogs not endorsed/audited | `40dd00f39763`, 2026-11-11 | Specify CLI, templates/scripts/commands and Git artifacts. Extensions can execute work; not a behavioral proof system. |
| `rmf` | [Eclipse RMF/ProR](https://projects.eclipse.org/projects/modeling.mdt.rmf): ReqIF reference implementation/GUI | EPL-1.0 [actual bundled text](https://raw.githubusercontent.com/eclipse-rmf/org.eclipse.rmf/b711d21a259d78b93ce76ccaa3a0d73ac446fcd6/org.eclipse.rmf.releng.product/epl-v10.html); per-file/NOTICE exceptions | Mirror `b711d21a259d`, 2015-09-16; Eclipse page lists 0.14.0 on 2016-03-01. Current distribution activity unknown | Eclipse application/library and ReqIF files. Not a headless connector demonstrated here. |
| `oslc` | [OSLC repository](https://api.github.com/repos/oslc-op/oslc-specs/readme): Core 3.0/RM 2.1 listed; lifecycle resource linking | Apache-2.0 code, CC-BY-4.0 documentation + OASIS covenant [L](https://raw.githubusercontent.com/oslc-op/oslc-admin/master/LICENSE.md) | `829005202d92`, 2026-06-02; individual normative publication status unresolved | HTTP-based resource interfaces; server implementation and authentication are separate choices. Repository includes work in progress. |
| `tree-sitter` | [Tree-sitter README](https://api.github.com/repos/tree-sitter/tree-sitter/readme): incremental **concrete syntax trees**, not whole-program semantics | MIT [L](https://api.github.com/repos/tree-sitter/tree-sitter/license); grammar licenses separate | `8a476cb87443`, 2026-11-11 | CLI / parsing library; local, per-language grammar. No ANE parser to build. |
| `jdtls` | [JDT LS README](https://api.github.com/repos/eclipse-jdtls/eclipse.jdt.ls/readme): Java LSP server | EPL-2.0 [L](https://api.github.com/repos/eclipse-jdtls/eclipse.jdt.ls/license); bundle review required | `9c3e7936390d`, 2026-11-09 | LSP through standard streams, sockets or pipes; JVM/workspace. Read observed runtime prerequisites before installation; do not conflate server Java with app Java. |
| `pact` | [Pact introduction](https://docs.pact.io/), [JVM implementation](https://api.github.com/repos/pact-foundation/pact-jvm/readme): HTTP/message consumer/provider contract tests | Apache-2.0 JVM [L](https://api.github.com/repos/pact-foundation/pact-jvm/license); PactFlow/Broker/plugin terms separate | `1928f22476f1`, 2026-11-03; intro updated 2026-08-25 | Test libraries/build integration and pact artifacts; optional broker service. Executed examples, not universal equivalence. |
| `openapi-diff` | [OpenAPI Diff README](https://api.github.com/repos/OpenAPITools/openapi-diff/readme): OpenAPI 3.x differences, JSON reports, fail-on-incompatible | Apache-2.0 [L](https://api.github.com/repos/OpenAPITools/openapi-diff/license) | `63850d807445`, 2026-08-05 | CLI, Maven plugin/library; local files or URLs. Actual spec dialect compatibility needs fixture tests. |
| `openrewrite` | [OpenRewrite README](https://api.github.com/repos/openrewrite/rewrite/readme): type-aware recipe engine; Maven/Gradle integration | Apache-2.0 core [L](https://api.github.com/repos/openrewrite/rewrite/license), **mixed newer modules/recipes** per [official licensing](https://docs.openrewrite.org/licensing/openrewrite-licensing) | `a40dbb5fd671`, 2026-11-11 | Local engine/plugins; no proprietary platform requirement for Apache core. Module selection is a license gate. |
| `rewrite-spring` | [Pinned Boot 4 recipe source](https://raw.githubusercontent.com/openrewrite/rewrite-spring/9fd585b4d33b36a224dc0263fdcb71d10742c3b9/src/main/resources/META-INF/rewrite/spring-boot-40.yml) contains `UpgradeSpringBoot_4_0` | **Moderne Source Available License**, not Apache/OSI OSS [actual L](https://api.github.com/repos/openrewrite/rewrite-spring/contents/LICENSE/moderne-source-available-license.md?ref=9fd585b4d33b36a224dc0263fdcb71d10742c3b9) | `9fd585b4d33b3`, 2026-11-10 | Recipe module consumed by engine/plugin; source observed, never executed. Internal use vs offering functionality to third parties is consequential. |
| `renovate` | [Renovate README](https://api.github.com/repos/renovatebot/renovate/readme): dependency update CLI | AGPL-3.0-only (README qualification; API says AGPL-3.0) [L](https://api.github.com/repos/renovatebot/renovate/license); hosted Mend terms separate | `2c8893a9921b`, 2026-11-11 | Self-hosted CLI/container or hosted offering; repository writes/credentials subject to operator policy. |
| `dependabot` | [Dependabot core README](https://api.github.com/repos/dependabot/dependabot-core/readme): updater libraries; recommends separate CLI for standalone use | MIT core [L](https://api.github.com/repos/dependabot/dependabot-core/license), not blanket GitHub service/CLI terms | `4d12fc64248f`, 2026-11-11 | Libraries; standalone CLI is separately packaged; hosted GitHub integration. Do not claim core itself is a complete deployed bot. |
| `structurizr` | [Consolidated Structurizr commands](https://docs.structurizr.com/commands): local/export/validate/inspect, DSL workspace | Apache-2.0 repo [L](https://api.github.com/repos/structurizr/structurizr/license); **server/closed extensions separately licensed** | `ad34036c5a12`, 2026-11-07; docs advertise binaries v2026.09.19, not installed | Local commands, DSL/JSON; server API optional. Existing C4 concepts reusable without adopting hosted server. |
| `structurizr-cli-legacy` | [Old CLI README](https://api.github.com/repos/structurizr/cli/readme) says migrate; no further updates | Apache-2.0 [L](https://api.github.com/repos/structurizr/cli/license) | `64464b193376`, 2026-02-01; GitHub `archived=true` | Legacy CLI; reject as new dependency, not the C4 approach itself. |
| `mermaid` | [Mermaid README](https://api.github.com/repos/mermaid-js/mermaid/readme): text diagrams, separate CLI linked | MIT core [L](https://api.github.com/repos/mermaid-js/mermaid/license); CLI/browser dependencies separate | `49429b28c7fe`, 2026-11-11 | Text and JS renderer; CLI separate. Keep generated diagrams as views, not verified architecture facts. |
| `github-cli` | [GitHub CLI README](https://api.github.com/repos/cli/cli/readme): issues, PRs, repository concepts | MIT client [L](https://api.github.com/repos/cli/cli/license); hosting service separate | `233b470d3a18`, 2026-11-11 | Local authenticated CLI/API access. Research used read calls only; no PR/issue writes. |
| `actions` | [Actions runner](https://github.com/actions/runner), [security reference](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions): delegate CI execution | MIT runner [L](https://api.github.com/repos/actions/runner/license), not service/actions licenses | `8cfa1049f867`, 2026-11-11 | Hosted or self-hosted runners, workflow artifacts/API; untrusted build code is an execution boundary. |
| `wasmtime` | [Wasmtime book](https://docs.wasmtime.dev/), [WASIp2 example](https://docs.wasmtime.dev/examples-wasip2.html): WASM/WASI/Component Model runtime | **Apache-2.0 WITH LLVM-exception**, actual [L](https://raw.githubusercontent.com/bytecodealliance/wasmtime/1d10469d7a95857ffe241cfe74583c656a7b5d35/LICENSE); API detection omitted exception | `1d10469d7a95`, 2026-11-11; example references `wasi:cli/run@0.2.0`, not a latest-version claim | CLI/embedding APIs and explicitly linked host interfaces; not a Spring compiler or cloud deployment platform. |
| `kantra` | [Kantra README](https://api.github.com/repos/konveyor/kantra/readme): Konveyor analysis/transformation CLI, containerless/hybrid modes | Apache-2.0 [L](https://api.github.com/repos/konveyor/kantra/license); bundled rules/server/assets separately review | `d05ca62ef7ab`, 2026-11-04 | CLI plus rules/JDT/report assets; container runtime needed for some modes. Optional modernization evidence provider. |
| `kai` | [Konveyor AI README](https://api.github.com/repos/konveyor/kai/readme): analysis-informed AI modernization | Apache-2.0 [L](https://api.github.com/repos/konveyor/kai/license); models/providers separate | `1a47a4d52931`, 2026-11-06 | IDE-oriented integration; README identifies MCP solution server and analysis RPC. Does not establish universal transformation support. |
| `backstage` | [Backstage README](https://api.github.com/repos/backstage/backstage/readme): developer portal/software catalog | Apache-2.0 [L](https://api.github.com/repos/backstage/backstage/license); plugins/distributions separate | `da0d8f70995b`, 2026-11-11 | Service/plugin framework with catalog artifacts. Not an ANE requirement or a behavior verifier. |
| `capra` | [Eclipse Capra README](https://api.github.com/repos/eclipse-capra/capra/readme): trace links, matrices and impact visualizations | EPL-2.0 [L](https://api.github.com/repos/eclipse-capra/capra/license) | Mirror `e22b69938209`, 2021-05-05; current canonical activity unresolved | Eclipse extension architecture; persistence/metamodel customization. No headless ANE API claimed. |

**ReqIF standard separately:** [OMG ReqIF 1.2](https://www.omg.org/spec/ReqIF/1.2/About-ReqIF)
is a formal requirements interchange specification (July 2016, formal/16-07-01),
with linked XML schemas and RF-Limited IPR mode. That is **not** an SPDX software
license for RMF or any other implementation. Reuse IDs, typed attributes and links
through an eventual import/export mapping; do not make XML the universal internal
model. Rich text, attachments, round-trip identity and tool extensions need tests.
OSLC is resource-oriented lifecycle interoperability, not a replacement for ReqIF's
exchange files. No OSLC server or ReqIF adapter is implemented by this research.

**LSP separately:** the [3.17 specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)
documents JSON-RPC and negotiated capabilities; its navigation now labels 3.18
current and 3.19 upcoming. Do not blindly use a memorized "latest 3.17" or assume
every server supports call hierarchy/references. Record negotiated capabilities,
encoding, project configuration and server version in evidence.

## Screening: maturity, evidence, security, lock-in and integration cost

All cells in this table are **inferences**, not measured performance or security
certifications. Complexity is relative thin-adapter effort: low = files/one-shot
CLI; medium = process lifecycle/version mapping; high = service, identity and data
model integration. All ANE bindings remain proposed. Upstream documented interfaces
above are not proof of a deployed capability in this repository.

| ID | Maturity / suitability inference | Evidence quality limit | Security and lock-in boundary | Proposed ANE complexity / fit |
| --- | --- | --- | --- | --- |
| `opencode` | Strong first-agent fit with active repository; experimental API implies churn | Agent conclusions remain hypotheses until checked against refs/tests | Prompts/source may leave host; tools can execute/write; permissions are not OS isolation; provider terms | Medium; proposed #22 capability boundary and external process/service, never bake agent state into LSM |
| `aider` | Useful interchangeable CLI baseline; observed commit age warrants refresh | Patch/log alone not conformance evidence | Auto-commit/edit defaults and model egress; unsupported Python API creates lock-in | Low CLI / medium safe execution; alternative, not parallel mandatory runtime |
| `openspec` | Lightweight change-intent workflow; overlap worth testing before new spec UX | Written scenarios are declared intent, not passing tests | Init modifies guidance; README reports command/version telemetry; inspect policy/disable when needed | Low file import; medium lossless mapping; candidate over mandatory adoption |
| `spec-kit` | Broader workflow/templates; useful alternative, more overlapping orchestration | Plan completion is not requirement verification | Community extensions/scripts are executable dependencies; pin/review | Medium; compare against OpenSpec rather than force both |
| `rmf` | Established interchange implementation, old observed mirror raises maintenance questions | Typed exchange cannot authenticate approval or truth | Eclipse/bundle dependencies; rich text and attachments untrusted | High for headless adaptation; defer absent concrete regulated-import need |
| `oslc` | Standard vocabulary/resource approach fits enterprise links | Provider URI must identify configuration/version, not merely latest resource | Authentication, linked resources and network trust; provider dialect lock-in possible | High; defer server, retain URI/version mappings |
| `tree-sitter` | Useful small syntax provider, inadequate alone for semantics | Syntax location is an observation; cannot prove runtime calls or intent | Untrusted grammar/native code and huge inputs; pin grammar separately | Low/medium; only add for gaps in existing manifests/providers |
| `jdtls` | Strong Java semantic-navigation candidate, heavier than file discovery | Missing classpath/generated code/reflection constrain results | Build import/plugins may execute or resolve dependencies; isolated writable cache, read-only source mount | Medium/high; optional provider, not a new ANE Java analyzer |
| `pact` | Good cross-repo integration evidence where consumers are known | Only covered examples/interactions; no full functional/security/SLO proof | Test code executes, pact payloads may contain secrets/PII; optional broker adds service trust | Medium; consume existing reports before introducing broker/test infrastructure |
| `openapi-diff` | Narrow deterministic compatibility gate | Declaration compatibility != deployed response compatibility | Remote spec URLs risk SSRF; use confined local sanitized files | Low; first candidate verification artifact alongside native tests |
| `openrewrite` | Mature mechanical-transformation building block, not orchestration substitute | Recipes can miss context; compilation/tests needed after changes | Maven/Gradle execute code/download artifacts; root license insufficient for module set | Medium; approved Apache components, isolated subprocess only |
| `rewrite-spring` | Relevant recipe source exists, **not cleared** for default distribution | Composite recipe source != tested artifact/coverage | MSAL third-party functionality restriction; transitive recipe terms unresolved | High legal gate; defer bundling/service use pending license review, never reimplement recipes to evade terms |
| `renovate` | Broad dependency-workflow candidate, unnecessary to recreate | Updated versions/PRs do not prove application compatibility | Repository write token, package registries, scripts and AGPL obligations | Medium self-hosting; ingest existing bot PRs first |
| `dependabot` | Low adoption cost on existing GitHub projects; core standalone is more work | Alert/update != migration success | Separate GitHub trust/quotas; updater resolves untrusted dependency data | Low hosted-result import / medium standalone; interchangeable dependency provider |
| `structurizr` | Good C4/DSL projection candidate; consolidated tool transition needs pinning | Diagrams represent model declarations/inferences, not runtime topology proof | Includes/scripts/plugins can cross boundaries; local export preferred; commercial server optional | Medium; defer extra renderer unless Mermaid insufficient |
| `structurizr-cli-legacy` | Archived, unsuitable for new integration | Historical behavior not current support | Stale tooling/dependency risk | Reject new use; migrate any proposed design to current tooling |
| `mermaid` | Smallest diagram-view fit for existing Markdown workflow | Layout success does not validate architecture | Untrusted diagram links/rendering; avoid publishing raw source/secrets | Low text generation; prefer existing exporter, don't rebuild renderer |
| `github-cli` | Strong first SCM transport fit, replaceable at boundary | API results must retain repository/commit/check IDs and pagination scope | Scoped credentials, redact outputs; hosting-specific concepts should not leak into contract | Low; existing CLI/API, read first, explicit approval for writes |
| `actions` | Useful existing CI execution/evidence provider | A green run only covers that workflow/ref; logs can be forged/incomplete | No secrets for untrusted PR builds; isolated runners, dependency lockfiles or verified SHA pins | Low artifact import / medium trusted triggering; not an ANE CI engine |
| `wasmtime` | Plausible sandbox/runtime experiment, **not a default target** | Successful Rust example says nothing about JVM/Spring conversion | Explicit host capabilities, network/filesystem grants; sandbox != platform-feature parity | High for migration; defer until target host/ABI/language compatibility established |
| `kantra` | Useful modernization/discovery alternative to source-only extraction | Rules/findings suggest risks, not approved requirements or complete dependency graph | Containers, rule packs, build/classpath import; isolated execution and pinned assets | Medium; compare as optional read-only evidence provider |
| `kai` | Close modernization competitor/composable provider; avoid duplicate agent loops | AI changes need independent verification and review | Models/source egress and solution memory; MCP does not grant trust | High if embedding whole workflow; consider thin findings/artifact boundary instead |
| `backstage` | Strong adjacent catalog/portal, too heavy for offline MVP | Catalog ownership/topology declarations can drift | Service/plugins/identity lifecycle and operational footprint | High; defer UI/portal, possible catalog import later |
| `capra` | Relevant traceability counterexample, not greenfield invention space | Trace links do not prove behavioral preservation | Eclipse metamodel/tool lock-in; current distribution maintenance unclear | High; learn from mappings, defer runtime dependency |

### Landscape: products versus composable blocks

No conclusion of "nothing comparable exists" is justified by this sample.

- [Konveyor](https://konveyor.io/) Hub + Kantra + AI is the closest open-source
  modernization **suite** in this pass: portfolio assessment, static analysis and
  AI transformation are existing product capabilities, not opportunities to
  rebuild. Its Kubernetes/cloud-native focus is not evidence of universal platform
  preservation. ANE should first test importing its findings, not build a rival
  analyzer. Compare operational burden and supported task coverage directly.
- OpenSpec and Spec Kit compete with portions of requirement/change workflow;
  Capra overlaps traceability/impact; Structurizr overlaps architecture/ADRs;
  Backstage overlaps catalog/continuous documentation surfaces. These are adjacent
  products, not a single proof that one suite satisfies all ANE requirements.
- Tree-sitter/JDT LS, Pact/OpenAPI Diff, native build/test runners and SCM clients
  are composable **building blocks**. Composition still requires governance,
  versioned evidence, cross-repo identity, partial failure and refresh semantics.
- **Commercial context, separately licensed:** [Moderne's official ecosystem
  description](https://api.github.com/repos/openrewrite/rewrite/readme) describes
  multi-repo LST analysis/recipes and agent tools; its [licensing
  page](https://docs.openrewrite.org/licensing/openrewrite-licensing) distinguishes
  Apache, MSAL and proprietary recipes. [AWS Transform](https://aws.amazon.com/transform/)
  advertises portfolio modernization, source-to-target traceability and
  human review, with agentic IDE/MCP access. These vendor descriptions are observed
  **claims**, not independently measured quality/speed/cost. No commercial trial,
  price comparison, contract audit or deployment was performed. Their hosted
  terms are not OSS licenses and are not cleared for incorporation. They are
  credible buy/partner comparators; reject a mandatory vendor dependency, not the
  possibility that an existing commercial product is better for a user's job.

**Potential differentiation, inference only:** a portable, human-governed System
Contract spanning requirements and platform constraints, with honest evidence
coverage across tools/repositories. If this is only another agent prompt wrapper
or makes review harder, choose native workflows instead. Continuous documentation
alone is not sufficient differentiation. Optional REA/binary analysis stays deferred
until source is unavailable or a concrete black-box question justifies selecting
and licensing a specialized provider. No bespoke reverse-engineering subsystem.

## Three candidate stacks (all proposed)

| Stack | Composition | Tradeoff and first test |
| --- | --- | --- |
| A — minimal native evidence | Existing ANE Git JSON/YAML + manifests/Git refs + existing Maven/test reports + local OpenAPI Diff when useful + GitHub CLI/CI artifacts + existing Markdown/Mermaid views. OpenCode V2 optional after approval; import OpenSpec artifacts if present. | **Recommended minimal experiment.** Low service footprint and portable artifacts. Manual mapping initially; test whether scoped context/approval traceability adds measurable value over agent + exactly the same native tools. No default Spring recipe bundle. |
| B — modernization-provider rich | A + Kantra findings/JDT LS when needed + license-cleared OpenRewrite components; Spring recipes only after explicit artifact/license review; Renovate or Dependabot results + Pact interactions. Agent selectable OpenCode/Aider. | More grounded dependency/impact evidence, but caches, language servers, recipes and execution boundaries add cost. Test one approved Java migration, not a new migration engine. |
| C — enterprise interoperability | A/B evidence boundary + ReqIF exchange/OSLC resource mappings + Backstage catalog import + consolidated Structurizr C4 views; compare against Konveyor suite or commercial procurement. | Highest identity, service, round-trip and licensing burden. Appropriate only with actual enterprise traceability/import needs; not MVP architecture. |

### Proposed build / integrate / defer / reject decision table

| Action | Scope | Reason / gate |
| --- | --- | --- |
| **Build narrowly** | Stable IDs, provenance/uncertainty, human approval, normalized evidence references, constraint-conflict records, model reconciliation and bounded context | ANE's existing mission. Extend existing model/native boundaries only after review; coordinate provider contracts with #22 rather than create competing research schemas. |
| **Integrate first** | Existing manifests/Git/SCM, native tests/CI evidence, optional schema compatibility reports and existing diagram renderer | Thin read-only boundary, measurable vertical slice; repository code is not automatically trusted to execute. |
| **Integrate conditionally** | OpenCode V2/Aider; optional OpenSpec/Spec Kit imports; Kantra/JDT LS; Apache OpenRewrite components | Capability/version discovery, sandbox and human authorization first; avoid imposing spec or agent format on core LSM. |
| **Defer** | `rewrite-spring` distribution/service execution, broker services, OSLC server, full ReqIF round trip, portal/UI, advanced graph/IR, WASI migration, optional REA | Artifact/license review or empirical use-case need missing. Do not substitute a custom engine for a licensing gap. |
| **Reject** | Archived Structurizr CLI as new dependency; mandatory proprietary runtime/vendor; auto-approval/merge/deploy; blanket semantic equivalence claims | Maintenance, portability and trust constraints; keeps accepted architecture intact. |

## System Contract proposal (not a production schema)

See [system-contract-proposal.json](../../examples/research/system-contract-proposal.json).
It is a standalone **synthetic, unapproved research example**, not an LSM document
accepted by `lsm validate`. It proposes a mapping to existing nodes/edges/evidence,
not a new compiler, semantic IR or executable logic language. No schema migration
is adopted here.

Minimum concepts:

1. **Requirements:** stable IDs, statement, owner, approval/version, acceptance
   criteria and explicitly approved exceptions. Importing code does not create
   approved intent. Keep observed behavior, hypotheses and unknowns separate.
2. **Observable behaviors:** actor/preconditions, stimulus, visible response,
   externally visible state/side effects, failure behavior and acceptance examples.
   Hidden implementation choices do not define the behavior. Characterization
   tests describe current behavior, including possible bugs, not desired policy.
3. **Interfaces:** protocol/data contracts, consumer/provider identities, direction,
   schema/source ref, compatibility policy and observed vs declared status. Reuse
   OpenAPI/Pact/ReqIF/OSLC artifacts via links, not embedded vendor-specific state.
4. **Constraints:** required capability + scope + severity, target profile's offered
   capability + evidence, and assessment `satisfied/conflict/unknown`. Keep portable
   requirements separate from implementation/deployment observations. Missing
   information is not support. Conflict references requirements, evidence and
   mitigation/exception approval; an approved exception is versioned, not silent.
5. **Evidence:** provider/artifact URI, immutable source/run ref or explicit missing
   ref, method, timestamp, scope/coverage/exclusions and independent provenance
   origin/verification. Documentation evidence supports only what was documented,
   not verified application behavior. No blanket semantic-
   equivalence guarantee; even verified executions are bounded to tested inputs,
   environments, dependency versions and assertions.
6. **Unknowns/decisions:** owner/question, blocking scope, required next evidence,
   proposal/approval state and supersession. Preserve unresolved/partial failures.

### Mapping to existing LSM provenance: independent axes

The proposal reuses existing LSM provenance for claims whose origin is known:
`provenance: {origin: declared|inferred|observed, source: <nonempty string>,
verification: unverified|verified}`. **Origin and verification are independent**;
there is no mixed claim-kind enum. Synthetic intent is declared/unverified; the
actual reading of Cloud Run documentation is observed/unverified and scoped only
to that documentation. Interpretations (such as a hypothesized network dependency
or migration hold recommendation) remain inferred/unverified with their own source.

Observed behavior can be **unverified** and can contradict approved intent.
Verification never changes origin or implies approval: a later check of an
observation does not turn it into declared intent, and a declared requirement can
have a separate verification state without becoming human-approved. The proposal's
behaviors are declared representational examples, **not performed application
observations**; all application checks remain not-executed and approvals pending.
There is no verified provenance in this research example.

Unavailable application/target facts use explicit `status: unknown`,
`provenance: null` and a nonempty `unknown_reason`. **Unknown is a status, not a new
origin**; do not fabricate observed or inferred provenance for missing facts.
This nullable research representation is not itself a production LSM schema change
or a claim that a production entity can omit required provenance. A future import
must retain unresolved questions and map known claims to existing contracts only
after review. Structural tests exercise the existing provenance definition and
representational combinations; they do not perform observations or verification.

Refresh design: commit/webhook/poll or explicit refresh discovers changed source
refs, invalidates dependent evidence freshness, proposes a model diff, retains
declared requirements until human approval, and regenerates cited views only from
the reviewed model. Deleted/renamed entities need explicit identity reconciliation;
never silently repoint old evidence to a new file. This mechanism is proposed,
not an implemented drift detector.

### What verification can establish

| Existing technique to delegate to | Evidence it can contribute | What stays unproven |
| --- | --- | --- |
| Native regression/characterization/golden-master tests | Captured outputs, error cases and state transitions for fixed fixtures; review any nondeterminism normalization | Unseen inputs; captured bug vs approved requirement; concurrency and side effects omitted from snapshots |
| Pact provider/consumer checks | Specific HTTP/message examples and matchers for identified participants | Every API behavior, business invariant, auth policy, integration failure or SLO |
| OpenAPI/schema diff | Declared structural compatibility under selected rules/spec dialect | Actual runtime serialization/errors and compatibility of undocumented clients |
| Differential testing of old/new implementations | Matched observations for the same isolated/replayed cases and data | Behavior outside samples; environment/time effects; correctness of both implementations |
| Property-based/metamorphic testing with existing ecosystem tools | Sampled invariants, shrunk counterexamples, expected relations between transformed inputs | Universal proof, completeness of properties or equivalence of all stateful traces |
| Existing integration/security/load tests + SLO telemetry | Environment-bound integration outcomes, workload/latency/error measurements | Future load, all threats, other regions/configuration; telemetry is observation, not approved intent |

Test-generation tools remain unselected; generated tests require oracle review and
independent assertions. No new test engine or formal prover is proposed. A truly
formal proof would require a specified semantics/model and explicit assumptions;
this milestone provides neither. Passing tests **does not prove full semantic
equivalence** or authorize a changed requirement.

## Read-only reference evaluations

These are **desk evaluations of synthetic scenarios**, not inspections of a real
application, executions, migrations or provider PoCs. Application versions, source
refs and measurements are unknown. Output should eventually live in an external
orchestration workspace or approved `.ane/workflows/`, not require source edits.

### A. Spring Boot dependency upgrade, 3 → 4

**Observed official guidance:** the [current 4.0 migration
guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
displayed edited Jun 28 2026 with 68 revisions when checked. It says move first to
the latest available **3.5.x**, review removed deprecations and unmanaged
dependencies, then a maintenance release of 4.0. It states Java **17+**, Kotlin
**2.2+** if used, GraalVM native-image **25+** if used, Jakarta EE **11** / Servlet
**6.1**, and Spring Framework **7.x**. These are observed guide requirements, not
assumed installed versions or a claim about every later Boot release.

Concrete assessment issues from that guide:

- Undertow support removed because the stated Servlet baseline was not met.
- Modularized main/test starters and package moves can require explicit starter
  changes; inventory actual use, including Flyway/Liquibase/security tests.
- Jackson **3** is preferred, with group/package changes and a temporary deprecated
  Jackson 2 module; serialization snapshots/API compatibility must be checked.
- Native image requirements are not WASM support. Spring Cloud and unmanaged
  libraries need their own compatibility evidence, not just a Boot parent bump.
- Removed/renamed properties and changed operational/data behavior matter: e.g.
  Spring Batch's non-JDBC default can change persistence of job metadata. This is
  a requirement risk, not cosmetic modernization.

**Proposed inventory:** request immutable source commit; read POM/Gradle/wrapper,
lock/dependency reports if already available, JDK/container manifest, third-party
starter/native/JNI use, tests, API specs, Cloud Run configuration and rollback
assumptions. Do not execute an unreviewed Maven wrapper/build during read-only
discovery. Dependency resolution and build plugins can execute code or contact
registries; require a separate sandbox/network authorization for analysis.

**Provider selection:** existing dependency reports/optional Kantra or JDT LS can
supply findings. The [pinned Spring recipe
source](https://raw.githubusercontent.com/openrewrite/rewrite-spring/9fd585b4d33b36a224dc0263fdcb71d10742c3b9/src/main/resources/META-INF/rewrite/spring-boot-40.yml)
contains `org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0` and composite
version selectors such as `4.0.x`; this is evidence a source recipe exists, not
that an approved published artifact resolves/runs or preserves behavior. Its
[actual MSAL text](https://api.github.com/repos/openrewrite/rewrite-spring/contents/LICENSE/moderne-source-available-license.md?ref=9fd585b4d33b36a224dc0263fdcb71d10742c3b9)
allows internal use subject to conditions and restricts making functionality
available to third parties. Official summary prose is less precise than this text;
use the actual artifact license and legal review before distribution/service use.
Do not quietly call all OpenRewrite Spring migration recipes Apache-2.0.

**Go/no-go now:** **hold migration approval**. No actual inventory, exact target
maintenance version, artifact pin, recipe license clearance, dependency matrix or
test baseline is available. Hard no-go for an unmitigated incompatible required
container/library, changed approved behavior, failing acceptance tests or recipe
use outside allowed terms. A human may approve a documented replacement/exception,
never the orchestrator silently weakening the contract.

**Acceptance plan after approval:** build/native tests, Jackson/API snapshots,
consumer/provider interactions, auth/error handling, database/batch migration,
startup/shutdown and workload/SLO checks in isolated fixtures. Compare old/new
observations using existing test infrastructure. Retain input refs, tool versions,
recipe configuration, dependency/artifact hashes, reports and uncovered cases.
Rollback must include data/schema reversibility, not only reverting a JAR. This
research authorizes no source edits, recipe runs, cloud credentials or deployment.

### B. New feature across backend, web, mobile and storage

**Synthetic request:** allow an authenticated customer to cancel an order before
dispatch, without duplicate refunds. Existing business policy and APIs are unknown.
Do not infer permission, refund timing or offline-mobile semantics from code alone.

Proposed read-only evaluation:

1. Record unapproved requirement, actors, allowed order states, concurrency,
   retry/idempotency behavior, fraud/privacy constraints and unresolved refund
   ownership. Require a human to approve scope and acceptance examples.
2. Link backend order/refund operations, external payment interface, storage state,
   web/mobile clients and notification consumers to immutable evidence. Import
   existing spec artifacts if present; AST/LSP only supplies candidate references,
   not an authoritative business impact graph.
3. Produce proposed API/message additions and compatibility rules. OpenAPI Diff
   checks structural changes; Pact checks identified consumer examples. Native
   regression/property tests should cover concurrent dispatch/cancel and repeated
   requests; differential checks apply only to **unchanged** behavior. A feature
   deliberately changes behavior; whole-program equivalence is the wrong objective.
4. Plan cross-repo PR dependency order and feature rollout/rollback; keep partial
   merges/failing checks explicit. Coordinate #5 impact, #6 context, #7 multi-repo
   review and #22/#23 providers/workflow instead of creating another task engine.

**Decision now:** feasible to *plan*, not approved to implement. No-go if refund
exactly-once policy, consumer compatibility, access control or required data
retention cannot be specified/verified. Unknown consumers and mobile offline races
remain blockers where they affect approved requirements. No tests were generated
or run against such an application in this milestone.

### C. Cloud Run → WASM/WASI feasibility

First disambiguate the goal: replace Cloud Run hosting with a named WASI host, or
run a WASM component **inside a Linux container still hosted on Cloud Run**? Those
are different migrations. No target host/ABI or application inventory is supplied.

**Observed:** [Cloud Run's container runtime
contract](https://cloud.google.com/run/docs/container-contract) requires Linux
x86_64 executables (`linux/amd64` in a multi-architecture manifest) and describes
ephemeral writable filesystem semantics and lifecycle/resource/security limits.
For a **Cloud Run HTTP service specifically**, ingress must listen on
`0.0.0.0:$PORT`, TLS terminates at the platform (h2c where configured), and responses
must meet the configured request timeout including startup time. These are **not
universal Cloud Run jobs or worker-pool requirements**. Jobs should terminate upon
completion, not listen on a port or start a web server; other resource types have
their own lifecycle/network constraints. This reference ingress scenario is an
HTTP service; retain general architecture/filesystem constraints where applicable
and compare each resource's actual contract. A bare `.wasm` is not a Linux
executable satisfying that contract; a native
runtime in a compliant container is a different option, not a completed platform
migration. [Wasmtime](https://docs.wasmtime.dev/) provides CLI/embedding and WASI
host-mediated capabilities; its [WASIp2 Rust
example](https://docs.wasmtime.dev/examples-wasip2.html) explicitly links imports and
uses `wasi:cli/run@0.2.0`. Neither source establishes Java/Spring compatibility or
the latest supported WASI profile of an unspecified hosting platform.

| Constraint to evaluate | Evidence to request / conflict rule |
| --- | --- |
| Language/runtime/reflection | Exact JVM/compiler target, Spring reflection/class loading/proxy use and supported compilation path. **No-go** for required JVM/reflection features without demonstrated target support; GraalVM native Linux output is not evidence of WASI compilation. |
| Networking/protocols | Required incoming HTTP/gRPC, outbound TLS/TCP/DNS, private DB connectivity and target's exact WASI interfaces/host grants. **No-go** if any required protocol, private connectivity or security policy lacks an approved implementation. |
| Threads/processes/native libraries | Inventory JNI, JDBC native/TLS drivers, thread pools, subprocesses and signal needs; compare exact target guarantees. **No-go** on unported required native code or unsupported process/concurrency semantics. Do not assert that all WASI hosts lack networking or threads. |
| Filesystem/data | Required durable state/transactions and path permissions vs explicit host filesystem/storage capabilities. Cloud Run local filesystem is already ephemeral; that does not establish target durable storage or transaction compatibility. |
| Identity/secrets/security | Replace Cloud Run metadata/service identity/IAM assumptions with documented target identity, secret delivery and least-privilege capability grants. Missing identity equivalent is a **no-go**, not permission to weaken auth. |
| Deployment/operations | Concrete host ABI/interface versions, CPU/memory limits, cold start, concurrency, timeout/shutdown, region, observability, SLO and rollback. Missing mandatory operational guarantee is a conflict or blocking unknown. |

**Decision now:** **no-go for authorizing a Java/Spring platform migration on this
evidence**; target capabilities and compilation feasibility are unknown. This is
not a theorem that every Java→WASM path is impossible. Keep the container platform
unless a specific, requirement-compatible target and existing supported toolchain
are demonstrated. A later optional experiment may isolate a small pure function
in a supported language, but that does **not** establish whole-application migration
feasibility and may require a separately approved architecture change. Kubernetes
likewise is not a runtime-equivalence guarantee; select node/runtime, services,
network/storage/identity policies explicitly before comparing capabilities.

## Safe reproducible PoC and baseline plan — not executed here

1. **Human gate:** present ADR/stack A and exact task, provider, fixture license,
   budget, allowable file/network paths and stop conditions. No paid run without
   separate approval (#8). Preserve #19 implementation boundary; coordinator PoC
   evidence is separately linked above within its native-plumbing scope.
2. **Fixture:** choose/create an approved synthetic Spring Boot + sanitized Cloud
   Run-descriptor fixture in a separate sandbox; no real application credentials,
   proprietary source or deployed resource. Pin fixture commit and expected
   intentional incompatibilities. Pin initial and target Boot/JDK/build versions
   from actual observed official releases and compatible dependency metadata.
   Their exact versions/hashes are **pending**, not populated with fake numbers.
3. **Tool lock manifest:** record executable `--version`, binary/package SHA-256,
   source commit, OS/architecture, tool/dependency lockfiles, container image
   digest, recipe artifact coordinates/configuration and licenses. Repository
   revisions in `ecosystem-sources.json` are research references, **not install
   instructions**. Verify provenance/checksums/security advisories, resolve release
   tags to immutable commits, then get approval; no `curl | sh`, `@latest`, dynamic
   recipe selectors or automatic installer execution. Hash pins themselves do not
   prove safety. Review full transitive recipe/module set before running anything.
4. **Read-only native vertical slice:** discover manifests/source refs without
   executing the fixture; import pre-existing test/API reports through the accepted
   future approved #22 provider boundary, reusing existing CLI/model contracts.
   Under separate execution approval, run the existing build,
   compatibility and test tools in a disposable sandbox with read-only source,
   writable cache/output outside it and allowlisted/no network as appropriate.
   Assert deterministic normalized refs, visible missing evidence, nonzero errors,
   bounded/redacted output, denied writes and no approval promotion.
5. **Agent slice separately:** only with authorization, give a read-only assessment
   task through a pinned OpenCode V2 CLI/API surface confirmed against installed
   version/OpenAPI. No SDK/configuration changes required by this research.
   Capture structured usage if available, otherwise mark tokens/cost unknown.
   Aider alternative uses reviewed no-auto-commit/read-only controls; no blind
   execution of the editing examples in its docs. Fail closed on capability mismatch.
6. **After a second approval only:** approved tools may edit disposable fixture
   copies and produce reviewable patches; never real source, auto-merge or deploy.
   Compare baseline and ANE treatments on the same task/ref, tools, model/version,
   budget and time cap, with fresh isolated contexts and randomized run order.
   Repeat tasks/seeds rather than claim success from one cherry-picked run.
7. **Blinded scoring and evidence:** maintain held-out expected incompatibilities,
   positive/negative acceptance cases and independent reviewer rubric. Report
   missed/false impact findings, task correctness, interface/behavior coverage,
   preserved requirements/explicit exceptions, install/onboarding minutes, elapsed
   time (including LSM setup/refresh), loops, actual input/output/cache tokens,
   invoiced/provider usage cost, reviewer minutes and model-drift correction effort.
   Byte proxies are not provider tokens. Include failures, missing measurements,
   uncertainty and provider/version limitations, not fabricated speedups.

| Comparison metric | Agent + native tools baseline | ANE + same agent/native tools |
| --- | --- | --- |
| Onboarding and setup/refresh effort | Pending measurement | Pending measurement; must include modeling overhead |
| Correctness, impact precision/recall and held-out acceptance coverage | Pending | Pending |
| Latency, repair loops, tokens and actual cost | Pending; no paid run | Pending; no paid run |
| Human review burden and requirement/evidence traceability | Pending | Pending; no assumed improvement |

**Success criterion proposed, not established:** ANE must add inspectable
cross-repo requirement/constraint traceability without hiding failures or weakening
correctness, and justify its total setup/maintenance/review cost. Agree numerical
thresholds and sufficient repetition with the human before the trial; do not
retrofit thresholds to observed results. Simplify/drop adapters when native tools
alone perform as well with less overhead.

## Open questions and suggested follow-ups

- #21/#22: artifact-level license clearance for actual recipe/transitive modules,
  binary provenance and permissive alternatives; are user-local invocations legally
  suitable for ANE's intended distribution/service model? Human/legal decision.
- #21/#20: which exact Spring fixture, Boot maintenance targets, JDK/build plugins,
  third-party dependencies and recipe artifacts are available and reproducible?
- #19/#22: how should source/run identity, capability mismatch, partial output,
  pagination, nonzero exits and stale evidence map from existing CLI/model artifacts
  into proposed provider contracts? #19 plumbing evidence does not deploy #22 adapters.
- #5/#6/#7: how much impact/trace coverage can be recovered without new tests or
  speculative agent inference, and how does context help across independent PRs?
- #21/#24/#25: choose an actual WASI host/interface profile and investigate required
  Java/native/identity constraints only if the user wants that target; no mandatory
  WASM backend or blanket semantic preservation claim.
- #21: compare canonical current Capra/RMF distributions and real OSLC/ReqIF
  exporters before any adoption; observed mirrors are inadequate support evidence.
- #21/#8: human-approved baseline rubric, task sample size, run budget and actual
  reviewer/token measurements. Test only on synthetic/sanitized data.
- #22/#23: scoped credentials, prompt injection/tool-output trust, isolation,
  redaction/retention and requirement approval authenticity. MCP is transport,
  not authorization; local actor names are not authenticated human approval.
- Future research: GitLab-specific interfaces/service licenses, observability
  providers, test generation and optional REA. They are not assessed simply by
  naming them; keep capability gaps explicit rather than adding assumed adapters.

## Local verification of this milestone

Initial milestone results, **before independent-review corrections**, executed in
the separate `research/21-ecosystem-assessment` worktree on 2026-11-11 with CPython
3.12.9, locked pytest 8.4.2 and Ruff 0.17.4:

| Command | Actual result |
| --- | --- |
| `uv sync --locked --python 3.12` | Passed; isolated worktree virtual environment created |
| `uv run ruff format tests/test_ecosystem_assessment.py` | Formatted the new test file |
| `uv run ruff format --check .` | Passed; 69 files already formatted |
| `uv run ruff check .` | Passed |
| `uv run pytest` | **601 passed** in 30.65 s on final run (local observation, not a benchmark); includes **34 research structural checks** |
| `git diff --check` | Passed for tracked changes; all five new research files separately checked for trailing whitespace and final newline |

Review correction verification in the same worktree: after separating LSM origin
and verification axes, retaining unknown facts without fabricated provenance, and
scoping Cloud Run ingress/TLS/request-timeout statements to HTTP services,
`uv run pytest tests/test_ecosystem_assessment.py` passed **46 structural checks**
in 0.22 s. `uv run ruff check .` passed and `uv run ruff format --check .` passed
(73 files already formatted). At that initial correction check the full suite had
not yet been rerun; the 601-test result above is historical, not a claim about
current merged main.
No production schema, adapter, application, configuration or deployment changed.

After integrating the accepted #19 gate, the coordinator reran the complete suite:
**619 passed** in 32.47 s (local observation), including all 46 research checks.
Ruff lint, formatting (73 files) and source/wheel build passed. Independent review
reran the 46 checks and found no remaining publication blockers in the corrected
provenance axes and HTTP-service qualification. See [review scope](ECOSYSTEM_REVIEW.md).
Research branch/main CI links will be recorded on issue #21 after publication;
no successful research CI run is predicted by these local results.

These results are distinct from the 573-test integration-only gate. No packaged
or released provider PoC, issue auto-close, architecture adoption, real-provider
completion, behavioral verification or economic benefit is claimed by this milestone.
