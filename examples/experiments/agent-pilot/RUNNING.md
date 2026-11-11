# Coordinator handoff (not supplied to agents)

Protocol: PROTOCOL.md. Definitions: fixtures.json, accept_cancel.py,
accept_pagination.py. No trials have been executed by the preparer.

The host shell does not have `python` on PATH. For every agent supply the same
runtime instruction: `Use /tmp/opencode/ane-agent-pilot/.venv/bin/python as the
shared Python binary when running python -m pytest; do not read its checkout.`
Runtime imports from the installed shared environment are permitted, not browsing
the benchmark checkout. This same exception applies to all four sessions.

Substitute each exact directory in the protocol's exact prompt, without other
task-specific coaching:

1. /tmp/opencode/ane-pilot-runs/cancel-baseline
2. /tmp/opencode/ane-pilot-runs/cancel-ane
3. /tmp/opencode/ane-pilot-runs/pagination-ane
4. /tmp/opencode/ane-pilot-runs/pagination-baseline

After completion, per directory use (replace NAME and TASK):

```sh
/tmp/opencode/ane-agent-pilot/.venv/bin/python \
  /tmp/opencode/ane-pilot-evaluator/evaluate.py \
  /tmp/opencode/ane-pilot-runs/NAME TASK \
  /tmp/opencode/ane-pilot-evaluator/results/NAME
```

TASK is cancel or pagination. Keep all results; exit 0 alone is success. Session
telemetry collector `/tmp/opencode/ane-collect-trial-metrics.py` is coordinator
owned, not invoked here. Do not give agents this document or evaluator paths.

Reprepare on a fresh environment with `uv run python
examples/experiments/agent-pilot/prepare.py`; refuses existing destination roots.
Pretrial commands/stdout/JUnit and hashes are committed alongside this document.
One schema-validation preparation failure (missing requirement approval field)
was corrected before any trial. Superseded pre-format/failed preparation artifacts
were preserved outside final roots, not used as trial inputs. Setup measurements
exclude interpreter startup, dependency installation and unmeasured authoring.
Compilation timings include API call and canonical serialization, exclude model
construction/initial validation; setup total includes compilation and all checks.
