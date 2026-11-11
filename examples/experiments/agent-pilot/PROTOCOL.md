# Matched agent pilot #8/#23 — preregistration

Prepared before any trials. Design: two matched maintenance tasks, four fresh
`openai/gpt-6.1-sol#low` sessions, one attempt each; exploratory n=2 only, not the
30-pair benchmark gate. No improvement or empirical completion claim is allowed.

Design acceptance: stdlib applications, four modules each, no services/network;
identical source, docs, public tests and task prompt within each pair. Only ANE
gets `CONTEXT.json`, compiled by the current `lsm.context.compile_context` from
declared, unverified requirements and module descriptions quoted from the same
README. No solution or evaluator content enters the model. Full README remains
available in both arms; no truncation. Generated LSM is coordinator-side only.

Exact prompt (substitute task directory only):

> Work only in TRIAL_DIRECTORY. Implement TASK.md using README.md and existing
> source. If CONTEXT.json exists, it is supplemental cited context, not authority
> over the README. Preserve existing behavior except explicit requested changes.
> Run public tests with python -m pytest. Do not read outside your assigned trial
> directory except executing the shared Python/pytest binary and its runtime.
> Do not use network services or other agents. Make one
> implementation attempt; ordinary self-testing within that attempt is allowed.
> Finish with a concise summary and tests run. Do not change TASK.md or README.md.

TASK.md is exactly the task-specific Requirements section in README.md, generated
from the checked-in fixture definition. Hashes in preparation.json freeze both.

Launch order: cancel-baseline, cancel-ane, pagination-ane, pagination-baseline;
counterbalanced fixed order (no claim of randomized scheduling). Runs may execute
concurrently: wall-time comparisons are exploratory and resource-confounded. Four fresh
sessions, no prior conversation/solution transfer, no coordinator repair advice.
Use identical harness permissions and 20-minute/one-response completion ceiling,
same available context/output limits for all runs; record effective limits and
model resolution before launch. No extra attempts after timeout or failed grading.
Provider seed is unavailable; do not invent one. Collect actual session API
input, output, reasoning, cache.read and cache.write token categories separately,
resolved model/variant, session duration, message/tool counts when available.
If derived, input + cache.read is cumulative input exposure, not unique context
size. Empty pricing catalog and reported zero cost do not establish free usage:
actual USD stays null. Missing telemetry remains null. Coordinator collector is
external to trial repos. No paid-budget approval is implied by this file;
the coordinator must confirm applicable authorization before launching.

Scoring: after all four completions, coordinator runs evaluate.py, which invokes
real pytest subprocesses with independent held-out tests outside trial trees,
plus public regression tests. Success requires both exit codes zero. Keep stdout,
stderr, command, exit status and JUnit. Do not repair after grading. Grade coded
task IDs without using arm in assertions; automated evaluator is not human-blind.
Report every run including failures; no exclusions except unusable infrastructure,
which must be disclosed, not replaced silently. No impact/onboarding score.

Preparation records compilation wall time, bytes, zero model invocation cost for
offline compilation only (not zero agent cost),
Python/platform, initial commits and content hashes. Compilation cost is separate
from trial telemetry; shared fixture authoring effort is unmeasured. The evaluator
source is committed here for reproducibility but copied to coordinator-only
/tmp/opencode/ane-pilot-evaluator; agents must not access this benchmark checkout.
This is an instruction boundary, not an OS sandbox. This local multi-module
experiment does not establish remote multi-repository acceptance. Report fixture
setup and context construction measurements separately; authoring is unmeasured.
No results yet. No PR yet.
