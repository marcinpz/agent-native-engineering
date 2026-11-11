# Bounded evidence traceability (#22)

Design: import existing JUnit bytes and join an explicit report-bound mapping to a
validated LSM. Emit a standalone companion, not changes to the locked `.ane` file
set. No workspace, graph, approval or provenance mutations. Exact case IDs bind
artifact bytes, repository, commit and position, never ambiguous display names.

Acceptance: failures/errors affect explicitly mapped requirements; skipped,
missing and stale remain visible. Passing subsets never establish requirement
coverage or verification. Invalid/extra keys, duplicate case assignments, dangling
or wrong-type references and mismatched report identities fail closed. Existing
import/discovery/workspace behavior remains compatible. Tests/demo may execute a
fixture; the evaluator never executes anything.

## API and CLI

```python
from lsm.junit import import_junit
from lsm.evidence import evaluate_junit

report = import_junit(report_path, repository="repo.backend", commit="a" * 40)
mapping = {
    "schema_version": "1.0",
    "report_id": report["data"]["id"],
    "mappings": [
        {
            "case_id": report["data"]["cases"][0]["id"],
            "test_id": "test.notes",
            "requirement_ids": ["requirement.notes"],
        },
    ],
}
result = evaluate_junit(
    report_path,
    model=model,
    mapping=mapping,
    repository="repo.backend",
    commit="a" * 40,
    expected_commit="b" * 40,
)
```

Mapping has only the illustrated keys. `case_id: null` explicitly declares a
missing expected test; unknown non-null IDs are errors. Multiple distinct cases
may map to one test; each case may occur only once. Requirements are explicit
mapping assertions, not inferred graph relations or acceptance-criterion coverage.

```sh
uv run lsm evaluate-junit report.xml --model model.json --mapping mapping.json \
  --repository repo.backend --commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --expected-commit bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb > evaluation.json
uv run python scripts/evidence_demo.py
```

Keep mapping and evaluation **outside** `.ane`; unknown files block workspace
operations. Reading `--model .ane/model.json` does not import into the workspace.
Retain original report bytes separately. No portable evaluation schema or workspace
persistence is claimed by this slice.

Exit 0 means valid evaluation, not passing tests. `tests[].outcome` and
`requirements[].mapped_test_outcome` prioritize error > failed > missing > skipped >
passed; detailed rows preserve mixed outcomes. Unmapped requirements have missing
mapped-test outcome. `coverage` is always unknown, `verification` unverified.
`freshness` current/stale compares only explicit commit attestations, not Git HEAD
or working-tree state. Stale results retain reported outcomes, not current proof.
Model/mapping digests and source ref bind inputs, not execution authenticity.
Model trust is neither changed nor copied into new evaluations. No automatic
approval/verification. Output omits names, raw failure text and model descriptions,
and uses shared best-effort redaction; review before publishing.

## Local acceptance results (2026-11-11)

`uv run pytest`: **797 passed**, including 27 traceability tests and the executable
demo's real pytest fixture (one pass, one failure, one skip). The harness's failure
exit is expected; evaluation succeeds with failed mapped-test outcome and stale
binding. Tests cover missing/skipped/error, failure impact, partial coverage,
invalid/wrong-type/dangling/duplicate mapping, artifact mismatch, existing protected
trust, no execution, redaction, CLI and unchanged input bytes. Existing JUnit,
provider and workspace suites remain passing. Ruff check and format check pass.
These are local fixture results, not real-application acceptance or authenticated
execution evidence.
