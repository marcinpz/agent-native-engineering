# Read-only adoption experiment (#22 / #24)

## Approved design and acceptance

[ADR 0005](../adr/0005-readonly-adoption-experiment.md) approves only the bounded
Stack A experiment, not all recommendations in ADR 0004. Reuse the existing Git
manifest discovery, LSM, docs and context APIs. One real native Git provider and a
mock replay share a closed read-only envelope; no application code is executed.

The acceptance walkthrough creates new sanitized Spring Boot/Maven/Cloud Run
HTTP-service and Python repositories, then proves:
- Native Git and mock replay retain the same canonical LSM semantics.
- Opt-in `.ane/` works inside a named source repo and an external orchestration repo.
- Source bytes and Git HEADs do not change **because of ANE operations**.
- Repeat refresh preserves every managed byte, including first collection timestamps.
- Preview exposes an intentionally simulated external Git revision without writing;
  explicit apply updates only managed metadata and node versions.
- Human docs/context are cited, unverified projections; exact compact context bytes
  match their declared byte-budget proxy.
- Cleanup defaults to a plan; explicit apply removes only unchanged known metadata.
- Malformed, partial, unsafe-path, drift and trust-promotion cases fail closed.

The fixture harness deliberately creates an empty commit outside ANE to simulate
an external revision. This changes no application source bytes and must not be
confused with an ANE commit/source-edit operation. Java/runtime/config versions are
explicit declarations, **not detected compatibility or successful build evidence**.

## Reproduce

```sh
uv sync --locked --python 3.12
uv run lsm provider capabilities
uv run python scripts/adoption_smoke.py
uv run python scripts/adoption_smoke.py --output-dir /tmp/opencode/ane-adoption-new
```

Use a new nonexistent output directory. Retained artifacts include `steps.json`,
`refresh-preview.json`, a summary and remaining local/external metadata. The Python
workspace is intentionally cleaned to exercise rollback of adoption; all synthetic
source files remain. `.env` contains only an untracked fake canary, never imported
by the provider or published in docs/context. No genuine secrets or cloud resources.

`preparation_seconds` measures one whole fixture walkthrough (including repository
setup and the simulated external revision). `cli_seconds` sums measured CLI process
times. These are local observations, not a fair agent-only performance comparison.
There are zero agent-model invocations; provider tokens and monetary cost remain
null rather than fabricated estimates.

## Ownership, cleanup and rollback

`model.json` is the sole current LSM; other files are config, evidence, projections
or integrity bookkeeping. Do not edit managed files in place. Unknown files,
symlinks, hardlinks, mismatched request identity and metadata drift block operations.
See [workspace documentation](../WORKSPACE.md) for constant-path cleanup and recovery.

To roll back adoption itself, preview and then explicitly apply `workspace clean`:
only ANE metadata disappears; application sources require no rollback. Successful
refreshes do not retain an unlimited history. If you need a post-success metadata
rollback, retain a reviewed backup or Git revision **outside** the managed bundle
before applying. Restore only the documented fixed metadata paths to their original
location; never follow arbitrary backup paths. Status checks local integrity, not
fresh source truth, so restored old evidence still requires a refresh preview.

Refresh has staged per-file replacements and a labeled recovery backup, but is
**not crash-atomic**. Incomplete rollback retains recovery evidence and fails.
Concurrent writers are unsupported. Workspace/source bindings are absolute and
local-only: copied/moved bundles require a new explicit initialization, not silent
re-binding. The portable manifest and LSM can be reused independently.

## Explicit remaining gates

Only `discover` is implemented. Other real provider capabilities, code/test/PR
execution, authentic human identity, Spring inventory/build/migration, agent-only
comparison and cloud deployment are not delivered by this experiment. These remain
in #21/#22/#23/#25/#8. No proprietary recipes or new engines were bundled.

## Actual verification

Executed 2026-11-11 in isolated `adoption-slice-24`, based on main `e5e59cb`, with
CPython 3.12.9, uv 0.6.7, native Git 2.53.0 and locked dependencies. Fixture Git
commands ignore inherited Git configuration/hooks/signing; no application tooling
or model credentials were installed or executed.

| Check | Actual result |
| --- | --- |
| `uv sync --locked --python 3.12` | Passed in a new worktree/venv |
| `uv run pytest` | **726 passed**, 43.23 s local observation |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed, 87 files formatted |
| Provider/workspace/CLI/adoption regressions | **107 passed**; independently rerun during read-only review |
| `uv build` | ANE source distribution and wheel built; application fixtures were not built |
| Source adoption walkthrough | **21 CLI steps passed**, source bytes/directory entries/modes preserved |
| Installed-wheel adoption walkthrough outside checkout | **21 CLI steps passed** |

Source-run artifacts are retained locally at
`/tmp/opencode/ane-adoption-22-24-20261111`, including the changed-ref preview and
remaining Java/external workspaces. That run measured 6.266 s whole fixture
preparation and 6.169 s summed CLI time. One installed-wheel run measured 6.153 s
preparation and 6.065 s CLI time. These are rounded **single local observations**,
not performance estimates or evidence of advantage over another workflow.
Both report zero agent-model invocations and null token/monetary-cost metrics.

Read-only review findings were fixed before publication: evidence IDs/immutable
refs match their derivation; saved evidence is bound to the discovery request;
CLI I/O errors are structured/redacted; context bytes exactly match accounting;
`.git` placement is forbidden; reordered model arrays are semantic no-ops.
Negative path/drift/partial-result/rollback/cleanup checks passed. Review found no
remaining blockers within these bounds. No new application failure or successful
application test, migration, cloud operation or authenticity claim is implied.

CI evidence and the integrated commit are posted on #22/#24 after execution, not
predicted here. The prototype delivers #24's fixture adoption/cleanup flow; #22
remains partial for other real capabilities. #21's broader PoC/baseline gates are
not closed by this native metadata experiment.
