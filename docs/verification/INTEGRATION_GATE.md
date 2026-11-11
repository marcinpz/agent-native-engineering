# Integration gate #19

## Design and acceptance

Verify the integrated main baseline, not just isolated library functions. Use only
new generated repositories and explicitly illustrative intent/evidence. Discovery
merges a valid declared requirement and inferred implementation fixture into the
same model as the imported repository/component inventory. The joined CLI flow
must validate, inspect claim states, migrate without trust changes, export cited
docs twice without diff, and preserve source files. No approvals are inferred.

Acceptance:
- Fresh locked setup, full formatting/lint/tests and schema fixture validation.
- One subprocess walkthrough connecting discovery, requirements/provenance and
  documentation in one model, including explicit implementation/test trace links.
- Deterministic rediscovery/export and schema 1.0 -> 1.1 preservation checks.
- Recognizable synthetic secrets absent from inspect/docs/context projections.
- Negative trust transitions fail; declared/inferred/observed are not conflated
  with pending approval or verified behavior.
- Build and installed-wheel walkthrough outside checkout pass; actual commands,
  environment, revision and CI links recorded below and on issue #19.

## Boundaries

This gate does not authenticate actors/evidence, establish behavioral equivalence,
execute real application migrations or close #7/#8/#20/#23 external acceptance.
Fixture tests and documentation remain evidence only for their explicit scope.
Discovery currently accepts schema 1.0 existing models; schema 1.1 is an explicit
downstream migration, not a silently accepted discovery input.

## Results

Executed 2026-11-11 in isolated worktree `integration-gate-19`, branch
`verify/19-main-gate`. Baseline: `06f3e5338afcaec0e827b72619df4d1279e69876`
(main at start), plus this gate's fixture/walkthrough/tests. The tests execute real
CLI subprocesses, not mocked success responses.

Environment: Linux, CPython 3.12.9, uv 0.6.7, Git 2.53.0, locked project dependencies
(pytest 8.4.2, Ruff 0.17.4). No LLM/provider credentials, real application access,
remote demo PRs, source migrations or deployment were used.

| Command/check | Actual result |
| --- | --- |
| `uv sync --locked --python 3.12` in new worktree/venv | Passed |
| `uv run ruff format --check .` | Passed, 69 files formatted |
| `uv run ruff check .` | Passed |
| `uv run pytest` | **573 passed**, 34.74 s local observation |
| CLI validate all 7 model fixtures | All valid: shop, context, integration seed, governance 1.0/1.1, changes before/after |
| `uv run python scripts/roadmap_smoke.py --output-dir /tmp/opencode/ane-integration-gate-19-20261111` | **25 CLI steps passed**; artifacts retained locally |
| `uv build` | Source distribution and wheel built |
| Isolated installed-wheel walkthrough outside checkout | **25 CLI steps passed** |
| Independent read-only review | 7 joined-flow tests passed; no code/safety blockers within scope |

Installed-wheel command (run from outside checkout; use absolute paths to your
checkout's wheel and script):

```sh
uv run --isolated --no-project --refresh-package agent-native-engineering --python 3.12 --with /ABS/CHECKOUT/dist/agent_native_engineering-0.1.0-py3-none-any.whl python /ABS/CHECKOUT/scripts/roadmap_smoke.py
```

The retained directory includes `steps.json`, inspected requirement/implementation,
joined 1.0 and 1.1 models, repeated docs, context, explicit repository-source size
comparison, and scoped local workflow/benchmark evidence. Raw model files contain
only an intentional synthetic credential probe; inspect/docs/context outputs do
not expose that probe. The ambiguous requirement stays pending, the hypothetical
implementation inferred/unverified, and test-plan evidence is not execution proof.
All source bytes are checked unchanged before the separately approved fixed demo.

No new product failures were found, so no separate bug was filed. The documented
1.0-only discovery-input boundary remains visible and tested; this gate does not
silently broaden supported inputs or alter trust semantics.

CI evidence: pending the gate commit's branch run. Final acceptance and issue
closure require a successful linked run; local results above are already executed,
not a prediction of CI success. Timing is one local observation, not a benchmark.
