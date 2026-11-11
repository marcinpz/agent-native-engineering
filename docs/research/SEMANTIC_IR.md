# Semantic IR research — issue #9

**Hypothesis: untested.** This is an experiment design, not adopted architecture,
an executable compiler, or evidence of semantic equivalence. ADR
[0003](../adr/0003-semantic-ir-research.md) is PROPOSED. ADR 0002 limits this work
to research; the Phase 0–1 model and CLI remain unchanged.

## Design and acceptance criteria

Investigate whether a small, typed description of pure operations can reduce
cross-language maintenance without hiding meaningful differences. Compare against
maintaining existing source plus LSM links, rather than assuming a new IR wins.
The proposed artifact must have a version, stable IDs, explicit types, candidate
mappings, unsupported semantics and risks. Tests check only proposal consistency.
They do not execute operations, validate generated source, or measure portability.

The companion [JSON proposal](../../examples/research/semantic-ir-proposal.json)
is a standalone research document, **not an LSM schema extension** and not input
to `lsm validate`. Its `proposal_version` describes this research format, not a
language compatibility promise. Unknown versions must be rejected by any future
consumer; migration would need explicit review. There is no executable consumer.

## Narrow proposed semantics

Three operation descriptions sketch a deliberately small pure subset:

| ID | Inputs → output | Proposed meaning |
| --- | --- | --- |
| `op.add-checked` | two signed i32 → result(i32, overflow) | mathematical sum; overflow is an explicit error, never wrap |
| `op.equal` | two signed i32 → bool | exact integer equality |
| `op.choose` | bool and two i32 → i32 | select an already supplied value; no lazy or effectful branches |

These are requirements for a possible experiment, not implemented behavior.
Operation order, syntax, serialization of executable programs, parsing, lowering,
optimization and host bindings are intentionally absent. No arbitrary source
reverse engineering or full application representation is proposed.

## Alternatives and candidate mappings

1. **Existing source + LSM links (baseline):** leave execution in each project's
   language and link requirements/tests to it. Lowest migration cost and preserves
   framework behavior, but duplicates implementations and can allow drift. An
   annotation that points at a function is not a verified semantic mapping.
2. **Typed operations + interpreter:** explicit checked arithmetic and tagged
   outcomes could make a small reference semantics inspectable. Interpreter bugs,
   host numeric behavior and custom operation extensions create a new lock-in
   boundary. A reference interpreter would not itself prove other backends correct.
3. **Source emitters:** independently assess Python and TypeScript output, not a
   mandatory pair of runtimes. Source remains inspectable and integrates with
   existing builds, but generated diffs, runtime checks, numeric conversions,
   exception conventions and source maps add maintenance. Available host integers
   or numbers must not silently replace checked i32 semantics.
4. **Optional WASM backend:** only a candidate for the pure subset. It would need
   explicit overflow checking and an error ABI. A binary target does not settle
   host imports, authorization, networking, scheduling or durable state. Neither
   WASM nor any vendor, runtime, language or compiler framework is required.

The JSON keeps Python and TypeScript as one candidate family with explicit
targets; evaluation must report each target separately. All advertised mappings
are `proposed`, with unsupported-case references and risks. An operation mapping
does not imply support for surrounding application semantics.

## Semantic gaps (unsupported in every candidate mapping)

| Gap ID | Boundary and unresolved question |
| --- | --- |
| `gap.domain` | Money, units, calendars, Unicode and domain invariants: who defines equivalence and validates constraints? |
| `gap.network` | Protocols, partial failures, retries, ordering and idempotency: what observable effects count as equivalent? |
| `gap.concurrency` | Threads, async scheduling, cancellation and memory models: which interleavings are permitted? |
| `gap.state` | Persistence, transactions, migrations and offline conflict resolution: where is the consistency boundary? |
| `gap.errors` | Host exceptions, stack traces, cancellation and cross-boundary error translation; only the proposed local overflow tag is described. |
| `gap.security` | Identity, authorization, capabilities, secrets, injection and side channels: which threat model and trust boundary apply? |

Exclusions do not mean these concerns are absent from existing source systems;
they mean this research proposal makes no portable mapping claim about them.
Future experiments must reject such inputs explicitly, never erase effects or
silently lower them to approximate operations. Source and repository metadata
remain untrusted data, not instructions to execute. Any future projection must
follow ADR 0002's redaction boundary; this proposal reads no repositories or secrets.

## Portability versus locking

An open JSON representation makes inspection and replacement possible, but is not
semantic portability. Versioned operation contracts, error layouts and host APIs
can lock users into this project's dialect just as a runtime can. Adding escape
hatches improves integration but reduces equivalence and moves lock-in to plugins.
Existing-source links retain language/framework dependence without inventing a
second implementation language. Source emission retains target-toolchain costs;
an interpreter adds deployment costs; WASM adds host/ABI integration costs.
Measure all these costs before preferring any backend. Keep exportable artifacts,
explicit versions and the option to retain hand-written source.

## Pre-registered evaluation plan (not results)

First seek human approval of a bounded experiment, scope, budget and threat model.
No interpreter, emitter, WASM backend or full compiler is authorized by this ADR.
Implementation of a full compiler requires a separate consequential architecture
decision even if a small experiment passes.

The JSON records proposed quantitative gates. Use 20 predeclared paired pure-subset
change tasks, three repetitions each per candidate target and baseline, with the
same requirements, fixtures, machines and budgets. Publish task IDs, revisions,
toolchain versions, seeds, raw outputs and failures. Use an independent expected
outcome oracle with boundary cases (i32 minima/maxima and overflow); agreement
between two backends alone is not correctness. Fix a deterministic suite of 1,000
cases per operation and target before running. Add one explicit rejection case
per gap per target. No production inputs or paid agents are needed by default;
any external paid trial requires its own approval and budget.

Proposed gates, subject to human review before trials:

- 100% oracle agreement on the bounded suite, with zero silently accepted
  unsupported cases. This is finite-suite evidence, not proof of equivalence.
- At least 90% of paired change tasks pass their independent acceptance tests
  without repair; publish counts, pass@1 and uncertainty intervals.
- At least 20% lower median maintenance minutes than the existing-source baseline;
  report paired differences and a bootstrap 95% interval. If it includes zero,
  record the maintenance hypothesis as inconclusive, not established.
- Median execution latency ratio at most 2.0 and peak-memory ratio at most 2.0
  versus equivalent baseline implementations; report hardware and dispersion.
- At most one backend-specific semantic workaround per operation per target,
  counted from reviewed changes (formatting/build glue excluded).

Record implementation effort, changed lines, repair loops, dependencies and all
unsupported requests separately. Include build/host setup in maintenance cost;
report cold setup and warm execution separately. Missing measurements are null,
not zero. Analyze Python and TypeScript separately; never pool away a failing
target. A failed safety/correctness gate stops that candidate. Missing data,
unreliable baselines or inconclusive intervals mean no adoption recommendation.
Passing every gate would justify review of a next experiment, not automatic
adoption or generalization to the six excluded semantic areas.

## Evidence and open questions

No benchmark or execution has been performed. `results` is null; candidate
feasibility and benefits remain unverified. Local proposal tests establish only
that IDs, references, exclusions, gates and research-only labels stay consistent.
Open questions include oracle ownership, realistic task selection, long-term
version migration, acceptable escape hatches, target availability and whether
LSM traceability alone provides most of the value. Prefer the baseline unless
evidence warrants greater complexity.
