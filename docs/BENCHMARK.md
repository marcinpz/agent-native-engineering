# Benchmark harness and experiment protocol

## Status and scope (#8)

**Limited local agent pilot available; broader empirical gates remain pending.**
The [actual n=2 matched pilot](../examples/experiments/agent-pilot/REPORT.md)
records four first-attempt passes, equal acceptance and increased cumulative
input exposure with ANE; unknown USD, concurrent timing and unspecified effective
budgets preclude cost/speed claims. It is not the 30-pair gate or remote
multi-repository acceptance. Historical preparation scope follows.

Owner approval covers this offline harness,
methodology and local preparation smoke only. Paid agent experiments require an
explicit user-approved provider/model, monetary ceiling, token budget and run
count. No agent is invoked by these APIs. Synthetic tests are not actual results.

`examples/benchmark/smoke-result.json` records one real local execution, when the
context compiler is available. It measures redacted whole-model JSON preparation
versus redacted compiled-context JSON preparation with `perf_counter`, including
serialization. Module import and initial harness model validation are outside the
timed intervals; compiler validation is included. Order is baseline then LSM.
No timing ratio or scientific speedup claim follows from this small sample.

The whole-model baseline is untruncated, unlike the budgeted compiler. Thus this
is a plumbing check, **not a fair equal-budget agent comparison**. Output bytes
are UTF-8 compact sorted JSON; `token_proxy_bytes_div_4` is ceil(bytes / 4), not a
tokenizer measurement or billable usage. All agent-outcome metrics remain null,
including pass@1, input/output tokens, cost, agent latency, repair iterations,
impact recall and onboarding accuracy. Only preparation seconds and sizes are
measured. Timings are machine/cache dependent; nontiming fields are deterministic
for identical input and implementation.

The committed sample was generated locally from `examples/shop.json` with task
`Inspect backend dependencies`, seed `component.backend` and budget 8192. It
contains baseline 8469 bytes / 2118 proxy units / 0.002923958 seconds and LSM
8045 bytes / 2012 proxy units / 0.027808275 seconds. These are **one local smoke
observation**, not agent results or a stable performance estimate. The current
compiler's budget is conservative canonical JSON **bytes**, not provider tokens;
the smoke's byte/4 proxy is a separate reporting convention.

To regenerate the actual artifact explicitly (overwrites that file):

```python
import json
from pathlib import Path
from lsm.benchmark import run_smoke

model = json.loads(Path("examples/shop.json").read_text())
result = run_smoke(model, "Inspect backend dependencies", ["component.backend"], 8192)
Path("examples/benchmark").mkdir(parents=True, exist_ok=True)
Path("examples/benchmark/smoke-result.json").write_text(
    json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
)
```

Use `uv run python` with the locked project environment. Keep timing results with
the machine/Python/dependency metadata for any larger study; this tiny artifact
is not a portable machine performance baseline.

## APIs and CLI integration contract

```python
from lsm.benchmark import run_smoke, summarize_trials

smoke = run_smoke(model, "Inspect backend dependencies", ["component.backend"], 8192)
summary = summarize_trials(document)
```

Both APIs return JSON-compatible dictionaries and do not write files. Smoke uses
`lsm.context.compile_context` lazily. Summary is pure and never fetches references,
executes tests, invokes agents or authenticates evidence.

Coordinator-owned CLI integration uses compact JSON:

```sh
lsm benchmark smoke examples/shop.json --task 'Inspect backend dependencies' \
  --seed component.backend --budget 8192 --output examples/benchmark/smoke-result.json
lsm benchmark summarize trials.json
```

## Supplied trial contract (schema 1.0)

`src/lsm/schemas/benchmark.schema.json` describes an object with
`schema_version: "1.0"`, `kind: "agent_trials"`, `data_origin` equal to
`supplied_experiment` or `synthetic_fixture`, and a nonempty `trials` array.
Each record has:

| Field | Contract |
| --- | --- |
| `kind` | `agent_trial`, never `deterministic_smoke` |
| `run_id`, `pair_id` | Nonblank identifiers; run IDs globally unique |
| `arm` | `baseline` or `lsm` |
| `task`, `model_revision` | Nonblank, matched within a pair |
| `budget`, `seed` | Positive integer budget; nonnegative integer random seed, matched |
| `attempt` | Positive integer, contiguous from 1 per arm |
| `success` | Boolean; true requires nonblank `verification_ref` |
| `verification_ref` | Independent reviewer/test artifact reference, or null for failure |
| `tokens_input`, `tokens_output`, `repair_iterations` | Nonnegative integers or null |
| `cost_usd`, `latency_seconds` | Finite nonnegative numbers or null |
| `impact_recall`, `onboarding_accuracy` | Optional fractions in [0, 1], or null |

Every pair must contain both arms and identical attempt sets. Unknown properties,
negative/nonfinite metrics, missing required fields and duplicate IDs are rejected.
Semantic matching and uniqueness checks supplement JSON Schema. A nonblank
verification reference is a supplied attestation, not proof of authenticity.

Summary fields: `schema_version`, `kind: agent_trial_summary`, `data_origin`,
`pair_count`, `arms`, `verification`, `claims`. Each arm reports `attempt_count`,
`first_attempt_count`, `first_attempt_successes`, `pass_at_1`, `metrics` and
`verified_cost_accounting`. Pass@1 uses only attempt 1, never repaired successes.
Each metric reports known/unknown counts, mean and sum (null when all unknown).
Fractions' sums are bookkeeping only, not a quality score.

Cost accounting excludes an entire arm's pair if **any** attempt cost is unknown.
`included_pair_count` and `excluded_unknown_cost_pair_count` expose that selection.
`known_total_cost_usd` includes failed attempts in complete-cost pairs;
`verified_success_count` counts pairs with at least one independently referenced
success. Their quotient is `cost_per_verified_success_usd`, null with no successes.
This is descriptive accounting of supplied evidence, not authenticated billing.
Per-arm complete-cost subsets can differ: do not compare them as matched causal
estimates. Never interpret null as zero.

## Reproducible real-experiment protocol (not yet executed)

1. Pre-register task descriptions, acceptance tests, independent grading rubric,
   exclusions, stopping rules and analysis before running agents. Include both
   reproducibility tasks (fresh setup, reproduce an existing test/failure) and
   maintenance tasks (behavior change, cross-component offline sync, regression
   repair), plus impact-analysis and onboarding questions with held-out answers.
2. Use at least **30 independent matched task/seed pairs** across at least three
   task classes as a pilot minimum, not a claim of statistical power. Plan power
   and confidence intervals before any confirmatory claims; report failures,
   uncertainty, exclusions and per-task results, not just favorable averages.
3. Freeze repository/model revisions, agent provider/model version, system prompt,
   tool permissions, environment, dependency locks, timeout, output allowance,
   context budget and random seeds. Both arms use identical tasks, models,
   resources and budgets. Baseline uses repo+docs; LSM adds scoped model context.
   Count all supplied context against the same tokenizer-based budget and apply
   a preregistered baseline truncation policy. Record exact prompts privately.
4. Randomize arm order using a recorded scheduler seed; counterbalance baseline
   first and LSM first equally. Reset worktrees, conversational state and caches
   consistently. Avoid leaking a previous arm's solution into the next run.
   Record scheduling/environment metadata in a companion experiment manifest.
5. Grade with independent tests/reviewer blinded to arm, not agent self-reports.
   Retain test logs and reviewer rubric artifacts under `verification_ref`.
   Failed verification means `success: false`; unavailable outcomes must not be
   silently dropped or recorded as successes. Capture every attempt, including
   repairs, and use identical maximum attempts/stopping policy in both arms.
6. Record real input/output tokenizer usage and provider billing in USD, including
   repair attempts and cache pricing. Missing telemetry stays null. Distinguish
   agent end-to-end latency from local context preparation. Label any shared or
   amortized setup costs and include them using a preregistered allocation rule.
7. Define impact recall against independently curated affected-entity sets and
   onboarding accuracy against blinded rubric answers; retain denominators and
   grading artifacts in the manifest. Optional fractions alone do not prove
   correctness. Report paired confidence intervals and task-stratified outcomes;
   this simple summary does not implement inferential statistics.
8. Publish anonymized, reviewed artifacts: replace personal identifiers and
   proprietary task/code text with stable pseudonyms, preserve pair identity,
   and scan prompts, tasks, seed IDs, URLs, verification refs and logs for secrets.
   Shared redaction removes common recognizable secrets, not arbitrary sensitive
   business data. Summary intentionally omits raw tasks, seeds and references.
   Keep restricted originals separately; never publish credentials or environment
   files. Document withheld artifacts and limitations to reproducibility.

The harness APIs alone do not establish paid usage, agent task success, quality
improvement, cost reduction or completion of the roadmap's empirical research
phase. The separately archived local pilot above records actual task outcomes,
but does not establish broader gains or close that phase.
