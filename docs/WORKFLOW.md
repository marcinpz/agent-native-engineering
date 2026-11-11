# Local-only approved workflow prototype (#7)

## Design and acceptance

The prototype creates four **new generated repositories** (backend, web, mobile,
store), implements a tiny offline-sync contract v1 → v2 on feature branches,
executes actual Python unittest fixtures and leaves local review bundles. It is
not an executor for arbitrary repositories or model-supplied commands. Approval
must be valid and content-bound through `lsm.changes.validate_proposal`; an
explicit named human grant for `approve_changes` is also required. Local approval
is an attestation, **not authentication or a cryptographic signature**.

Before any run writes, the approved proposal's model digests, complete semantic
diff and impact must **exactly match** `create_proposal(*demo_models())`.
`lsm.workflow.demo_models()` returns fresh package-owned canonical before/after
models, mirrored by `examples/changes/{before,offline-sync}.json`. Installed
packages do not read repository examples. Only proposal ID, assumptions and risks
may vary; approval still binds all submitted content. Merely reusing supported
IDs is insufficient: reverse, contradictory, additional or otherwise different
changes are rejected before writes. A content-bound execution plan is saved at
`reviews/execution-plan.json`.

The canonical requirement describes only the fixed pure Python function:
v1 returns `{'version': 1, 'accepted': 0, 'offline': False}`; v2 returns
`{'version': 2, 'accepted': len(queued), 'offline': True}` for a sized queue.
There is **no persistence, networking, retry or conflict-resolution behavior**
and no application-level offline-sync fulfillment claim. Canonical model
provenance remains unverified; actual fixture execution evidence is separate.

Acceptance: all four fixed fixture tests execute; unauthorized actors and agents
are rejected before writes; a failed fixture produces a failed record, never a
test-pass claim; root/path/marker/symlink tampering and subsequent tracked,
untracked or Git metadata drift prevent verification. The generated Python
fixtures are illustrative contracts, not backend/web/mobile/store applications.

## Library API

```python
from pathlib import Path
from lsm.changes import approve_proposal, create_proposal
from lsm.workflow import demo_models, init_demo, run_demo, reconcile_demo

init_demo(Path("fresh-demo"))  # refuses ANY existing directory, including empty
# policy: explicit named human approve_changes grant, as in the sample policy
proposal = approve_proposal(create_proposal(*demo_models()), policy, "owner")
record = run_demo(Path("fresh-demo"), proposal, policy, actor="owner")
result = reconcile_demo(Path("fresh-demo"), record)
```

Keep the returned record outside the demo root. Any extra file inside the root
(including an execution record) deliberately counts as drift. Each root supports
one run; start with another new directory for a repeat. For a failure-aware demo,
pass `fail_component="mobile"` to `run_demo`. Other components still execute;
the failed component's commit is retained for local review, not merged.

Process timeouts, missing executables and Git errors instead stop further work
and return a partial failed record. Components are explicitly `succeeded`,
`failed` or `unattempted`, with the last attempted stage, actual command evidence
and nullable test/after-commit/diff fields. No observed commit, test or diff is
invented. Timeouts retain redacted partial stdout/stderr and exit code 124;
missing processes use 127. Other process-launch errors use 126; ordinary Git/test
exits retain their actual codes. Such records can never verify successfully.
Failures after mutation retain in-memory evidence even if storage errors prevent
writing some review artifacts; the record then reports incomplete evidence.

The CLI integration surface is owned by the coordinator. Intended commands:

```sh
lsm workflow init fresh-demo
lsm workflow run fresh-demo approved-proposal.json --policy examples/workflow/policy.json --actor owner --output execution.json
lsm workflow reconcile fresh-demo execution.json
```

These command forms are the eventual CLI contract, not a claim that this module
alone installs CLI wiring. See `examples/workflow/README.md` for fixture details.

## Evidence and boundaries

Execution records use schema version `1.0`, state `succeeded` or `failed`, per-repo
before/after commits, fixed command arguments, exit codes, redacted stdout/stderr,
SHA256 content evidence, branch and local review/diff artifact paths. Review
bundles contain `REVIEW.md`, `commands.json` and `test.json` under
`reviews/COMPONENT/`; `change.diff` exists only when actually produced. Failed or
unattempted components also have `failure.json` (best effort if storage fails).
GitHub PR
fields are always `null`: **no remote PR was created**. There are no remote calls,
merges, deployments or arbitrary model-provided commands.

Reconciliation checks root identity, marker bytes, a full file/directory/mode
snapshot (including Git metadata and unknown files), HEAD/branch, clean status,
content hashes and recorded command/test/failure artifacts. Completed successful
repositories must have matching HEAD/branch and clean status. Partial failures
use the full recorded snapshot, including known dirty files/index/HEAD, without
running Git in incomplete repositories. `matched` only means the local bytes
still match; failed or unattempted work remains unverified even when bytes match.
`verified` is scoped to these generated fixtures and the recorded test exits,
not to requirement fulfillment, evidence authenticity or real system behavior.

Roots, ancestors and generated contents must not be symlinks; hard-linked files
and special files are rejected. A copied root fails identity checks. Before
source execution the executor checks the entire initial snapshot and exact
generated source content; additional executable tests are forbidden. Git uses a
controlled environment without inherited `GIT_*` settings, ignores global/system
configuration and disables hooks, signing and fsmonitor. Tests run using
`sys.executable -I -m unittest discover -s . -v` and a minimal environment, only
within the fixed generated repositories. No shell is invoked.

This is not an OS sandbox. Root markers and execution records are local mutable
attestations, not tamper-proof credentials; an attacker rewriting the entire
history and evidence is not authenticated by hashing. Concurrent mutation during
a run is outside the prototype threat model. Never point it at untrusted source,
nor use it to verify an adversarial filesystem. A failed initialization or
interrupted run may leave a partial directory; inspect it and select a new root.

**External deferred gate:** a real multi-repository demo with remotely linked PRs
and human review remains outstanding. This local prototype does not close that
acceptance criterion or claim external PR closure.
