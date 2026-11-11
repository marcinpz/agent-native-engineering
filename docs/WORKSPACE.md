# Read-only adoption workspace (bounded #24 experiment)

## Design and acceptance

An opt-in `.ane` directory holds one current LSM and existing documentation/context
projections, not a second application source tree. Discovery is the existing
explicit-manifest/Git metadata operation behind a replaceable read-only provider.
Acceptance: source-byte preservation, stable IDs, content-based node versions,
byte-identical no-op refreshes, preview-first changes, and fail-closed ownership,
placement, provider-result and cleanup checks. Schema 1.0 only: no autodowngrade.

## Placement and use

Use a **new** explicit `.ane` directly inside a repository named by the manifest,
or outside **all** named repositories (for example, an orchestration repository).
Its parent must exist. Nested application-source paths, symlink ancestors, existing
targets and traversal are rejected. Pass the explicit source base on every refresh;
the stored config alone never authorizes source access.
Any `.git` ancestor is forbidden, including outside the named source repositories.
Workspace and source-base bindings are absolute and local-only. Copying or moving a
workspace invalidates its location binding; explicitly initialize new metadata at
the new location instead. The workspace bundle is not a cross-machine portable
configuration (the LSM itself remains a portable artifact).

```sh
uv run lsm workspace init manifest.json /ABS/orchestration/.ane --base-dir /ABS/sources
uv run lsm workspace status /ABS/orchestration/.ane
uv run lsm workspace refresh /ABS/orchestration/.ane --base-dir /ABS/sources
uv run lsm workspace refresh /ABS/orchestration/.ane --base-dir /ABS/sources --apply
uv run lsm workspace clean /ABS/orchestration/.ane
uv run lsm workspace clean /ABS/orchestration/.ane --apply
```

`project.json` binds workspace location, source base, explicit manifest, provider
identity and context settings (`task`, explicit/default repository seed IDs, byte
budget). `model.json` is the sole current model. `evidence.json` retains the normalized
provider collection envelope; `context.json` and `docs/{index.md,context.mmd,
components.mmd,traceability.md,onboarding.md}` reuse existing projectors. `state.json`
contains fixed managed-artifact hashes, not executable deletion instructions.

Initialization writes only new metadata. Refresh defaults to a semantic diff;
`--apply` updates only managed metadata. A HEAD change updates repository provenance
and increments that node's version; unchanged content keeps its version. Timestamp
or provider-envelope-only differences do not rewrite anything, including the first
collection timestamp. Replacing Git with `MockProvider(model)` does not create new
trust. Failed/partial collections are never persisted.
Reordering node/edge arrays alone is also a no-op. `context.json` uses the exact
compact context serialization, without a trailing newline: its UTF-8 file size
equals the self-inclusive accounting byte count and stays within the budget.

## Ownership, cleanup and recovery

Do not edit the managed model, configuration or generated projections in place.
Drift, missing/unknown files, symlinks, hardlinks and special files block refresh and
cleanup **before discovery**. Status checks local metadata integrity only, not fresh
source refs or behavior. Hashes detect accidental drift; they are not authenticated
signatures against an attacker rewriting the whole bundle.

Cleanup first lists constant managed paths. Explicit apply removes those unchanged
files and then empty directories, never a recursive tree. Preserve user work outside
the bundle. Unknown entries must be reviewed and moved manually, never auto-deleted.
Cleanup I/O errors propagate; deletion is not atomic and an interrupted cleanup may
leave an incomplete bundle requiring manual review.

Refresh stages each replacement in the metadata directory and writes state last.
Before replacing anything, it exclusively creates `.ane/recovery.json`, a labeled
base64 backup of the original fixed metadata files. Ordinary write errors trigger
rollback; successful rollback removes the backup and raises an error honestly.
Incomplete rollback retains the backup and reports its location. A crash may also
leave recovery/staging files. These block status/refresh/cleanup until human review.
For manual recovery, review the original base64 bytes in `recovery.json`, restore
**only the documented fixed paths** (never execute or trust arbitrary paths from a
backup), then remove the recovery file after confirming restoration. Do not rerun
init over an existing directory. Multi-file writes are **not crash-atomic**.

## Trust limits

No source scan, source execution, build, tests, migration recipe, remote access,
environment/URI resolution, service or agent execution is added. Manifest framework
names are declarations; Git refs are observations. Docs/context remain cited,
unverified projections, not proof of application compatibility or behavior. No
approvals, evidence authentication, or measured cost/quality benefits are inferred.
Concurrent writers are unsupported; this is not an OS sandbox against an adversary
mutating the filesystem during operations.
