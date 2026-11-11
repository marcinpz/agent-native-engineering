# ADR 0003: Evaluate a bounded semantic IR hypothesis

Status: PROPOSED

## Context

Issue #9 and accepted ADR 0002 authorize research/prototype proposals only, not a
compiler. The implementation plan explicitly excludes a new language/compiler
from the MVP and makes typed semantic IR a later evidence-dependent option.
The LSM links intent and evidence; it is not currently an executable specification.

## Proposed decision (not adopted architecture)

Review the [research design](../research/SEMANTIC_IR.md) and its versioned
[experiment proposal](../../examples/research/semantic-ir-proposal.json).
Hypothesis: **untested** — a tiny pure typed-operation subset might reduce
maintenance across targets without losing the explicitly bounded semantics.

Compare existing source with traceability links against a typed-operation
interpreter, source emitters (Python and TypeScript assessed separately), and
optional WASM. No runtime, vendor, WASM, compiler framework or implementation
language is mandated. Existing source remains a valid outcome and the default.

Require human approval before implementing even the bounded experiment. A full
compiler, language or new executable architecture needs a separate approved ADR;
successful finite-suite evaluation would not grant that approval automatically.

## Alternatives and consequences

- Existing source avoids a new dialect and preserves native framework behavior,
  but cross-target duplication and drift remain possible.
- An interpreter makes bounded operation contracts inspectable, but adds a
  runtime and risks dialect/extension lock-in and shared oracle bugs.
- Source emitters preserve target integration and inspectability, but introduce
  generated-code churn, numeric/error adaptations and toolchain dependence.
- Optional WASM may offer another pure-operation target, but needs an error ABI,
  explicit overflow handling and host integration; it is not application portability.

All candidates leave domain meaning, network effects, concurrency, persistent
state, host error translation and security unsupported by the proposed portable
mapping. Open formats do not remove semantic, ABI or ecosystem lock-in. These
gaps and per-candidate risks are mandatory parts of the proposal, not footnotes
to a claim of universal compilation.

## Evaluation and acceptance

Before trials, review 20 paired tasks × three repetitions per candidate target
and baseline; fix 1,000 oracle cases per operation and rejection cases for all six
gaps. Proposed gates: 100% bounded oracle agreement, zero silent unsupported
acceptance, at least 90% task pass@1, at least 20% median maintenance reduction
(paired 95% interval excluding zero), at most 2× latency and memory, and at most
one semantic workaround per operation per target. Publish failures and raw
measurements; missing data and inconclusive comparisons cannot justify adoption.
Full methodology and limits are in the research design.

## Evidence and unresolved questions

No trials have run and no success or feasibility claim is made. Proposal tests
check structure and consistency only, not executable semantics. Results remain
null. Oracle ownership, representative tasks, migration costs, host boundaries
and the value over source-plus-LSM remain unresolved. This ADR does not change
the model schema, CLI, accepted architecture or implementation roadmap.
