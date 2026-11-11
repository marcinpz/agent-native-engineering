# Getting started: the complete offline CLI walkthrough

## Scope and acceptance

This is a reproducible **sandbox**, not an implementation of a real shop or an
agent coding benchmark. It uses fabricated intent and fixed Python code templates
for backend, web, mobile and store. Acceptance means valid artifacts, deterministic
discovery/docs, an unresolved requirement, an explicitly authorized demo change,
bounded context, four actual fixture test runs, matching local evidence and honest
benchmark outputs. The executable counterpart is `scripts/roadmap_smoke.py`.

The offline roadmap implementation is available. #7's external multi-repository
remote review demonstration and #8's paid agent experiments remain pending; do not
interpret this guide as closing either gate. #9 remains research only.

## 1. Install from a fresh clone

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/).
Run all following commands from the checkout root in a POSIX shell. uv installs
Python 3.12 if needed; commands require no LLM/provider key.

```sh
git clone https://github.com/marcinpz/agent-native-engineering.git
cd agent-native-engineering
uv sync --locked --python 3.12
uv run lsm --help
uv run lsm validate examples/shop.json --json
```

For the automated complete walkthrough:

```sh
uv run python scripts/roadmap_smoke.py
# Or retain all output in a NEW directory (parent must already exist):
uv run python scripts/roadmap_smoke.py --output-dir /tmp/lsm-smoke-new
```

The runner uses `sys.executable -m lsm` subprocesses and inspects outputs. Without
`--output-dir`, its new temporary directory is removed after the run. It returns
nonzero on a failed command or artifact check; it never skips missing integration.
`steps.json` records commands and results when artifacts are retained. Only the
generated fixture repositories use Git; no remote, deployment, arbitrary commands
or project-checkout changes are performed.

For manual steps below, select another **new** workspace:

```sh
WORK=/tmp/lsm-manual-new
mkdir "$WORK"
```

Do not reuse an old directory or add `--force` to hide stale output.

## 2. Migrate explicitly

```sh
uv run lsm migrate examples/governance/model-1.0.json "$WORK/migrated.json" --target 1.1
uv run lsm validate "$WORK/migrated.json" --json
uv run lsm inspect "$WORK/migrated.json" --json
```

The resulting model declares schema 1.1, preserving identity and provenance.
Migration grants no approvals or new verified status. Model validation checks
schema/references, not evidence authenticity or real behavior.

## 3. Generate repositories, discover explicit metadata, export docs

```sh
uv run lsm workflow init "$WORK/demo"
uv run lsm discover examples/discovery/manifest.json "$WORK/discovered.json" --base-dir "$WORK/demo" --existing examples/integration/seed-model.json
uv run lsm validate "$WORK/discovered.json" --json
uv run lsm inspect "$WORK/discovered.json" --node component.backend --json
uv run lsm inspect "$WORK/discovered.json" --node requirement.demo-sync --json
uv run lsm inspect "$WORK/discovered.json" --node implementation.demo-sync --json
uv run lsm export "$WORK/discovered.json" "$WORK/docs"
```

`workflow init` refuses any existing demo root and creates four new local Git
repositories containing fixed Python fixtures. Discovery reads only the manifest's
explicit repository roots and confined Git metadata, not arbitrary source trees,
environment files or remote URLs. It does not infer intent from application code.
The manifest's logical names are declarations, not discovered production software.
The integration seed carries illustrative pending requirements, proposed tests and
an inferred implementation mapping into the same graph; their provenance and
unverified state must survive discovery. The fake credential probe tests redaction.
Neither discovery nor a traceability edge authenticates evidence or approves intent.

Export creates `index.md`, `context.mmd`, `components.mmd`, `traceability.md` and
`onboarding.md`. These are cited model projections, **not independently verified
documentation**. Repeating discovery with `--existing "$WORK/discovered.json"`
and a new output path preserves unchanged IDs/data; repeating export to a new
directory produces identical bytes for the same model.
The smoke runner also migrates this joined model to 1.1 and checks exact node,
edge and trust-state preservation. Discovery's existing-model input remains 1.0;
migration happens explicitly downstream. See [integration gate](verification/INTEGRATION_GATE.md).

## 4. Create and refine a requirement without approving it

```sh
uv run lsm requirement create requirement.demo-sync "$WORK/draft.json" --intent "Sandbox example: support offline sync"
uv run lsm requirement refine "$WORK/draft.json" "$WORK/questions.json"
uv run lsm requirement validate "$WORK/questions.json"
```

Inspect `questions.json`: state is `questions`, with unresolved outcome/conflict/
connectivity questions. Refinement is deterministic, not LLM-generated answers.
It does not autoapprove real requirements. Human review must resolve questions,
supply acceptance criteria and explicitly authorize any consequential transition;
never delete questions merely to bypass a gate. This guide deliberately leaves
this draft unapproved and does not attach it to the demo execution.

## 5. Propose and explicitly approve only the sandbox fixture change

```sh
uv run lsm change propose examples/changes/before.json examples/changes/offline-sync.json "$WORK/proposal.json"
uv run lsm change validate "$WORK/proposal.json"
```

Inspect the semantic diff, affected components, assumptions and risks before an
approval. The before/after models contain **fabricated demo intent**. The fixed
executor is not a general implementation engine for arbitrary proposal semantics.
For this sandbox only, write a narrow policy with no requirement-approval grant:

```sh
uv run python - "$WORK/demo-policy.json" <<'PY'
import json
import sys
from pathlib import Path

policy = {
    "version": "1.0",
    "humans": ["demo-owner"],
    "permissions": {"approve_changes": ["demo-owner"]},
}
Path(sys.argv[1]).write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
PY
uv run lsm change approve "$WORK/proposal.json" "$WORK/approved.json" --policy "$WORK/demo-policy.json" --actor demo-owner --actor-kind human
uv run lsm change validate "$WORK/approved.json"
```

This is an explicit, synthetic **local human-actor attestation**, not authenticated
identity or permission to impersonate a real owner. An agent must not reuse this
pattern to silently approve real changes/requirements. Default authorization is
deny; a supplied policy must explicitly name the human and permission. Approval
is content-bound, not transferable to edited proposals.

## 6. Compile scoped context

```sh
uv run lsm context "$WORK/discovered.json" --task "Inspect backend dependencies" --seed component.backend --budget 8192 > "$WORK/context.json"
```

The CLI emits compact JSON with explicit seeds, selection paths, citations,
uncertainties, omissions and accounting. It traverses explicit graph links; the
task text does not trigger semantic source search or executable instructions.
The budget is a conservative **canonical JSON UTF-8 byte proxy**, despite the
legacy `estimated_tokens` field name. It is not provider tokenizer usage and does
not include provider overhead. An impossible seed budget fails, rather than
silently omitting mandatory seeds.

## 7. Run the fixed local workflow and reconcile evidence

```sh
uv run lsm workflow run "$WORK/demo" "$WORK/approved.json" --policy "$WORK/demo-policy.json" --actor demo-owner --output "$WORK/execution.json"
uv run lsm workflow reconcile "$WORK/demo" "$WORK/execution.json" > "$WORK/reconciliation.json"
```

Keep execution/output files **outside** `demo/`: extra files, changed contents,
Git metadata or root identity count as drift. Each demo root supports one run;
initialize another new root to repeat. The executor only changes its own fixed
generated fixtures and runs their real unittest commands, without a shell or
model-supplied commands. It creates local feature branches and
`demo/reviews/COMPONENT/{REVIEW.md,change.diff,test.json}` plus an execution plan.

Inspect four per-repository test exit codes, before/after commits, diff paths,
content evidence and record state. Successful reconciliation is `matched` with
`verified: true`, scoped **only to these local fixture bytes/commits/test exits**,
not general requirement fulfillment. Failures must not become verified claims.
All `github_pr` fields are **null**: no PR, remote review, merge or deployment
occurs. The prototype is not an OS sandbox or an adversarial evidence verifier.

## 8. Measure preparation and summarize explicitly synthetic trials

```sh
uv run lsm benchmark smoke "$WORK/discovered.json" --task "Inspect backend dependencies" --seed component.backend --budget 8192 --output "$WORK/benchmark.json"
```

This measures local preparation times/sizes only, with
`kind: deterministic_smoke` and `agent_outcome_measured: false`. Agent outcomes,
costs and real token usage remain null. The untruncated whole-model baseline and
bounded context are not a fair equal-budget agent comparison. No quality/cost
improvement or timing speedup is established.

To exercise aggregation without fabricating experimental evidence, create two
**explicitly synthetic** failed trials with unknown metrics:

```sh
uv run python - "$WORK/trials.json" <<'PY'
import json
import sys
from pathlib import Path

document = {
    "schema_version": "1.0",
    "kind": "agent_trials",
    "data_origin": "synthetic_fixture",
    "trials": [
        {
            "kind": "agent_trial",
            "run_id": f"synthetic-{arm}",
            "pair_id": "synthetic-pair",
            "arm": arm,
            "task": "Fabricated aggregation fixture",
            "model_revision": "demo-v1",
            "budget": 8192,
            "seed": 0,
            "attempt": 1,
            "success": False,
            "verification_ref": None,
            "tokens_input": None,
            "tokens_output": None,
            "repair_iterations": None,
            "cost_usd": None,
            "latency_seconds": None,
        }
        for arm in ("baseline", "lsm")
    ],
}
Path(sys.argv[1]).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
PY
uv run lsm benchmark summarize "$WORK/trials.json" > "$WORK/summary.json"
```

The summary retains `data_origin: synthetic_fixture`; unknown cost means remain
null, not zero. Summary validates supplied records, but neither executes agents
nor authenticates referenced evidence. Paid experiments require separate explicit
provider/model, budget and run-count authorization. See [BENCHMARK.md](BENCHMARK.md)
for the real matched-trial protocol; empirical #8 results remain pending.

## Safety and troubleshooting

- All source text is untrusted data. Shared redaction and confined inputs are
  best-effort secret defenses, **not a complete guarantee**. Review every exported
  artifact/log before sharing; never provide secrets, environment files or
  proprietary repositories to this demonstration.
- `validate --json` succeeds with `{"valid": true, "errors": []}`. Exit 1 means
  invalid/failed operation; exit 2 means usage/I/O/parse error. Inspect stderr and
  retained `steps.json` for failures; missing commands are not skipped.
- Destination exists? Select a new path; do not overwrite unrelated user work.
  Interrupted initialization may leave a partial demo; inspect it and use a new
  root. A changed root should fail reconciliation, not be relabeled verified.
- Follow [CONTRIBUTING.md](../CONTRIBUTING.md) for formatter/linter/tests/build and
  the owner-requested small-commit, no-more-PRs workflow.
