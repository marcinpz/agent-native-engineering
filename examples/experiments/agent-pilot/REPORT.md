# Actual matched local agent pilot — #8 / #23

## Outcome

All four first-attempt implementations passed independent acceptance and the
unchanged original regression test. Baseline 2/2, ANE 2/2; no observed quality
difference on these two tasks. ANE increased cumulative input exposure in both
pairs. This is exploratory n=2, not evidence of general quality or cost gains.
No coordinator repair, additional agent attempt, exclusion, or merge occurred.

Preregistration is immutable commit `31377df` (base `3b211f7`). Tasks are local
stdlib Python multi-module changes: idempotent cancellation/refund and owned
cursor pagination. Both arms had identical source, requirements/docs and public
tests; ANE additionally received compiled cited context. Original fixture git
commits and SHA-256 hashes are in preparation.json. `results/summary.json`
verifies final TASK.md, README.md, test_public.py and ANE context unchanged;
both external held-out definitions still match preregistered hashes exactly.

## Independent verification

| Run | Original public | Held-out | Agent-added tests | All agent tests |
| --- | ---: | ---: | ---: | ---: |
| cancel-baseline | 1/1 | 10/10 | 9 | 10/10 |
| cancel-ane | 1/1 | 10/10 | 11 | 12/12 |
| pagination-baseline | 1/1 | 15/15 | 16 | 17/17 |
| pagination-ane | 1/1 | 15/15 | 21 | 22/22 |

Thus 50 held-out cases and 4 original public cases pass across four runs. These
are repeated task cases across arms, not 54 independent tasks. Agent-authored
tests are additional self-verification, not independent success criteria. Before
trials, all four original public suites passed; all 10 cancellation and all 15
pagination held-out cases failed per arm on missing APIs (pretrial/).

Coordinator ran the frozen evaluator after all four completed; its command,
stdout/stderr, zero exit statuses and JUnit are archived per run under
`results/NAME/evaluation/{public,heldout}/`. Command pattern:

```sh
/tmp/opencode/ane-agent-pilot/.venv/bin/python \
  /tmp/opencode/ane-pilot-evaluator/evaluate.py \
  /tmp/opencode/ane-pilot-runs/NAME TASK \
  /tmp/opencode/ane-pilot-evaluator/results/NAME
```

TASK is cancel or pagination. The report integration additionally executed real
pytest against each entire final trial directory, without editing it; the exact
commands, outputs and JUnit are in `results/NAME/all-agent-tests/` (all exit 0).
`snapshot.json` stores every final source/doc/test file, including untracked
feature tests, excluding only .git and runtime caches. Extract its path-to-text
mapping into a fresh directory to reproduce; held-out tests remain external.
Final source hashes and added-file lists are in results/summary.json. No raw
system prompt or full transcript is published.

Report integration verification: `uv run pytest -q
--junitxml=examples/experiments/agent-pilot/results/integration-junit.xml` exited 0,
770 passed in 54.98 s; `uv run ruff check .` and `uv run ruff format --check .`
both exited 0 (98 Python files formatted). Archived trial sources are JSON text
bundles, so agent-authored tests do not affect project pytest collection.

## Actual session telemetry

Every session resolves to `openai/gpt-6.1-sol`, variant `low`. Raw metrics retain
session IDs, timestamps, message/tool counts, errors, and audit shell commands.
Each has 5 assistant messages, 4 tool calls for cancellation and pagination-ANE,
10 for pagination-baseline, and no reported tool errors. Session outcome alone
is not the acceptance score; JUnit above is the independent check.

| Run | Input | Cache read | Cache write | Cumulative input exposure | Output | Reasoning | Session seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cancel-baseline | 1,955 | 27,776 | 0 | 29,731 | 1,380 | 0 | 40.997 |
| cancel-ane | 3,144 | 30,592 | 0 | 33,736 | 1,414 | 21 | 40.485 |
| pagination-baseline | 5,491 | 26,240 | 0 | 31,731 | 1,679 | 0 | 45.306 |
| pagination-ane | 3,574 | 30,848 | 0 | 34,422 | 1,510 | 0 | 43.336 |

Cumulative input exposure is explicitly input + cache.read, summed over session
calls, **not unique context size**. Output and reasoning are separately reported
harness categories; do not assume reasoning should be added to output. Baseline
input exposure totals 61,462 versus ANE 68,158 (+6,696, about 10.9%); output totals
3,059 versus 2,924. Pair exposure increases: +4,005 cancellation, +2,691 pagination.
No inference about cost follows: the harness reported zero but had no pricing
catalog; actual USD is null for every run. Cache pricing is unavailable.

Both ANE sessions' audit commands explicitly read CONTEXT.json along with the
same TASK/README/source/public tests. Baseline cancellation read the same files
without context; pagination baseline used individual read calls and had no
CONTEXT.json. This establishes context retrieval, not cognitive use or causality.
The collector is archived as collect_metrics.py; it reads completed session API
metadata/messages and emits selected telemetry, not raw prompts. Archived data
is synthetic fixture activity with local paths/session identifiers, no secrets.

## Preparation overhead (separate from trials)

| Item | Measurement |
| --- | --- |
| Fixture setup + compilation + baseline checks | 6.114348 s |
| Cancellation context API + canonical serialization | 0.011128 s; 5,790 bytes |
| Pagination context API + canonical serialization | 0.013202 s; 6,205 bytes |
| Preparation authoring session | 416.700 s; input 17,195; cache.read 722,816; cache.write 0; output 10,193; reasoning 268 |

Authoring-session cumulative input exposure is 740,011. That session designed
fixtures, docs, evaluator, protocol **and** models; it cannot all be allocated
to ANE. It is observed session telemetry, not a measurement of human authoring
effort. Human review burden and later report-integration cost are unmeasured.
Shared authoring remains unallocated; no end-to-end cost saving is claimed.
Setup excludes interpreter startup/dependency installation. Compilation excludes
model construction/initial validation, includes compiler validation/serialization.
Offline compilation itself invoked no model; that does not make agent use free.
The actual LSMs are archived in results/*-model.json and context in snapshots.

## Deviations and limitations

- Fixed counterbalanced launch order: cancel-baseline, cancel-ane,
  pagination-ane, pagination-baseline. Not randomized; executions overlapped.
  Session wall times are exploratory and resource-confounded, not a speedup.
- Protocol requested a 20-minute ceiling, but launch tooling had no timeout:
  **not technically enforced**. All observed sessions completed below a minute.
- Equal harness defaults/model variant were used; effective context/output
  numeric limits were unspecified, not frozen known budgets. Provider seed
  unavailable. Exact system-prompt equality was not independently audited.
- One attempt each, ordinary self-tests allowed; no coordinator repair help.
  Coordinator attests completion before grading; this archive does not provide
  cryptographic isolation or prove absence of every possible external read.
- Small hand-designed tasks and finite assertions can miss defects; automated
  grading is not arm-blind human review. No measured human review burden.
- Local multi-module experiment only; no remote multi-repository acceptance,
  broad #8/#23/#20 completion, statistical significance, or general benefit claim.

## Recommendation

Keep context compilation as an optional, traceable aid. These tasks show working
plumbing and equal acceptance, with greater input exposure, not demonstrated
economic benefit. Before broader claims, use harder independently curated tasks,
known equal budgets, enforceable limits, reliable billing, randomized scheduling,
and measured review effort; retain failures as well as successes. The benchmark's
30-pair minimum remains unmet. Coordinator independently reviews this integration.

## Appendix: post-trial evidence reconciliation (separate integration)

After trials the coordinator executed the archived `results/traceability/runner.py.txt`
using the evaluator API from [PR #31](https://github.com/marcinpz/agent-native-engineering/pull/31),
revision `0b49761`, not this branch's main-based API. Reproduction must use that
revision/environment; it has not been cherry-picked or merged here.

The completed cancel-ANE source was copied into a separate frozen clean git
snapshot, commit `718108c08e720bb15a85a25281acf0783ae06ec3`. The same 10 held-out
tests were actually rerun there: 10 passed, exit 0, with a pytest cache permission
warning from `-c /dev/null`. The snapshot remained git-clean. Its source is already
represented by the cancel-ANE snapshot archive; no duplicate .git/cache is stored.

The coordinator explicitly mapped 10 test IDs to `requirement.feature` and called
`evaluate_junit`. Archived model.json, mapping.json, evaluation.json, execution.json
and junit.xml show freshness=current and mapped_test_outcome=passed, but
coverage=unknown and verification=unverified. Mapping was **not automatic**;
the commit binding is a user attestation, not authenticated execution provenance.

stale-demonstration.json deliberately sets expected_commit to forty zeroes and
returns stale. This is a **synthetic mismatch check**, not a second actual code
revision or observed stale production evidence. This appendix adds an integration
observation only: it does not change the four trial scores, attempts or timings.
