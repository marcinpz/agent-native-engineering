# Disposable offline-sync fixtures

Use the local-only API/CLI contract in [WORKFLOW.md](../../docs/WORKFLOW.md).
`policy.json` grants a sample local human named `owner` permission to approve
changes; it is not an authenticated identity or a production policy.

`init_demo` generates backend, web, mobile and store repositories under a **new**
selected directory. Each has a Python `contract.py`, `test_contract.py` and
`.gitignore`, committed on `main`. No source repository is imported or executed.
The initial contract returns version 1, accepts zero pending items and declares
offline mode false. The fixed feature-branch change returns version 2, accepts
the queued item count and declares offline mode true; corresponding real
unittest assertions are updated and executed. This intentionally tiny fixture is
not a working distributed synchronization implementation.

Construct the exact supported proposal with
`lsm.changes.create_proposal(*lsm.workflow.demo_models())`, then use
`lsm.changes.approve_proposal(proposal, policy, "owner")` before `run_demo`.
The canonical models mirror `examples/changes/before.json` and `offline-sync.json`
but live inside the package; no examples paths are read at runtime. Model digests,
diff and impact must exactly match the canonical forward transition, not just
its IDs. Reverse, contradictory and arbitrary approved proposals are rejected
before writes. ID, assumptions and risks may vary as review metadata. The fixed
pure function performs no persistence, retries, networking or conflict resolution
and does not fulfill application-level offline-sync requirements.

Inspect `reviews/COMPONENT/REVIEW.md`, `change.diff` and `test.json` alongside the
execution record. `commands.json` records commands; `failure.json` describes any
failed/unattempted component. Operational process/Git failures preserve partial
evidence and stop remaining components; missing results stay `null`, never pass.
`fail_component="mobile"` intentionally adds a failing assertion while still
running all four fixtures. Store records **outside** the generated root;
repeat runs require new roots. No remote, linked GitHub PR, merge or deployment
is performed. Remote-linked PR acceptance remains deferred, not simulated.
