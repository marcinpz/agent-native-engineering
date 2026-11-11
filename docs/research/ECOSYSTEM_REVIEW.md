# Independent review of the initial ecosystem assessment

Checked: 2026-11-11. Scope: initial research milestone for #21, not approval of
architecture, licensing for a distribution, application compatibility or benefit.
This review used primary documentation and read-only HTTP requests. No application,
provider configuration or deployment was changed; no paid agent experiment ran.

## Source checks performed

The independent reviewer fetched the high-risk sources below. Their statements
were supported within the qualifications recorded in the assessment. This is not
verification of every feature in all 24 landscape rows.

| Claim checked | Primary evidence and conclusion |
| --- | --- |
| OpenRewrite versus Spring module licensing | [Official licensing](https://docs.openrewrite.org/licensing/openrewrite-licensing) and [pinned MSAL text](https://raw.githubusercontent.com/openrewrite/rewrite-spring/9fd585b4d33b36a224dc0263fdcb71d10742c3b9/LICENSE/moderne-source-available-license.md): Apache core does not clear every recipe/module; third-party distribution/service restrictions require review. |
| Boot 4 recipe existence | [Pinned recipe source](https://raw.githubusercontent.com/openrewrite/rewrite-spring/9fd585b4d33b36a224dc0263fdcb71d10742c3b9/src/main/resources/META-INF/rewrite/spring-boot-40.yml) contains `UpgradeSpringBoot_4_0` and dynamic selectors. Source existence is not artifact resolution, successful execution or behavioral preservation. |
| Wasmtime license exception | [Pinned LICENSE](https://raw.githubusercontent.com/bytecodealliance/wasmtime/1d10469d7a95857ffe241cfe74583c656a7b5d35/LICENSE) contains Apache 2.0 plus LLVM Exceptions; metadata detecting only Apache is incomplete. |
| Structurizr maintenance boundary | [Legacy repository](https://api.github.com/repos/structurizr/cli), [pinned README](https://raw.githubusercontent.com/structurizr/cli/64464b193376e8f902383204c96c2ea53bb618b4/README.md) and [current commands](https://docs.structurizr.com/commands) support rejecting the archived CLI as a new dependency, not rejecting C4/current tooling. |
| OpenCode V2 interface scope | [Official introduction](https://opencode.ai/docs/), [CLI](https://opencode.ai/docs/cli) and [API](https://opencode.ai/docs/api) document automation, shared background service and experimental HTTP API. Repository SHA is not an installed-binary pin. |
| Spring Boot 4 migration prerequisites | [Official migration guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide) supports the recorded Java/framework/Servlet/optional native-image prerequisites and migration risks; application compatibility remains unknown. |
| Cloud Run and WASI scope | [Container contract](https://cloud.google.com/run/docs/container-contract) and [Wasmtime WASIp2 example](https://docs.wasmtime.dev/examples-wasip2.html) do not establish Java/Spring-to-WASI feasibility. HTTP service ingress rules must not be generalized to jobs or worker pools. |

Additional reference checks: **23 commit-specific maintenance URLs** resolved with
the recorded SHAs/timestamps. **Six sampled license blobs** (OpenCode, Aider,
OpenRewrite, Renovate, Structurizr, Capra) matched the recorded Git blob hashes.
These checks substantiate the sampled references, not release currency, binary
provenance, all capabilities or legal permission for the intended ANE use.

## Required corrections

1. Keep origin, verification and human approval orthogonal in the proposed System
   Contract, matching the existing LSM. Observed-yet-unverified behavior must be
   representable without promoting it to verified or changing its origin. Missing
   information stays unknown, not an invented observation.
2. Scope `0.0.0.0:$PORT`, ingress TLS and request-response timeouts to **Cloud Run
   HTTP services**. Jobs should terminate rather than start a web server. This
   qualification does not change the migration-hold recommendation.

Correction verification: both findings were closed in a read-only follow-up
review of the corrected example, mapping text and HTTP-service scope. The reviewer
executed **46 structural checks**, all passed (0.21 s local observation). Unknown
facts retain explicit reasons without fabricated provenance. No production schema
or trust semantics changed. Structural tests are not independent factual proof.

## Remaining gates

Actual Spring inventory/build/recipe execution, transitive artifact licensing,
real provider acceptance, concrete WASI target support, paid matched-agent
comparison and architecture approval remain pending. Structural unit tests check
artifact consistency, not factual source correctness or universal equivalence.
Keep issue #21 open and recommendations **PROPOSED**.
