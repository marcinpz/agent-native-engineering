# ADR 0005: Read-only provider and workspace experiment

Status: accepted **for this bounded experiment only**, by the project owner.
Related: #21, #22, #24. ADR 0004 remains proposed for broader architecture adoption.

## Design

Exercise Stack A with a native Git provider and a replay/mock replacement, using
the existing manifest discovery, LSM validation, documentation and context code.
No parser, analyzer, migration recipe, agent runtime, service, Maven build or
deployment engine is introduced. Application sources are never written. Explicit
workspace initialization/apply/cleanup may write only ANE-owned metadata.

### Shared provider contract

`lsm.providers` exposes `GitProvider`, `MockProvider`, `invoke` and `validate_result`.
`invoke(provider, "discover", *, manifest, base_dir, existing=None)` returns a
versioned JSON-compatible result. `provider.describe()` advertises its versioned
supported capabilities. Only read-only `discover` is implemented here; evidence,
plan, change, test, PR and reconciliation capabilities are catalogued, not invented
as working adapters. Write/code/test/PR requests fail closed even if a caller
supplies an approval: this experiment has no write executor.

Result required fields: `schema_version: "1.0"`, `provider: {id, version}`,
`capability`, `status: succeeded|failed|partial`, `data` (null or `{model}`),
`evidence`, `errors`, `permissions: {source_access: "read", writes_performed: false}`,
`request_digest`, `observed_at` (actual UTC date-time). Evidence includes stable
ID/source URI, immutable source ref where available, independent origin and
verification, unknown confidence as null and collection timestamp. Errors are
structured/redacted, never executable instructions. Invalid provider responses or
trust promotions are rejected. The real adapter delegates to `lsm.discovery`,
not another Git/source-analysis implementation. Mock replay cannot promote trust.

`MockProvider(model)` replays a model using the same semantic validation boundary.
Same model from either provider must retain identical LSM IDs/provenance/trust.
Provider-specific collection metadata remains outside the LSM.

### Workspace API and ownership

`lsm.workspace` exposes:
- `init_workspace(manifest, base_dir, directory, *, provider=None, task="Onboard system", seed_ids=None, budget=8192)`
- `refresh_workspace(directory, base_dir, *, provider=None, apply=False)`
- `workspace_status(directory)`
- `cleanup_workspace(directory, *, apply=False)`

`directory` must be a new `.ane` metadata directory: either directly inside an
explicit source repository (opt-in) or outside all source repositories, such as
an existing orchestration repository. No source copies or secrets are imported.
Every read/refresh requires an explicit source base, not a config-driven arbitrary
filesystem scan. Config/manifest paths and metadata ownership are validated.

Minimal layout: `project.json` (version/config + explicit manifest), `model.json`
(the sole current LSM), `evidence.json` (provider envelope), `context.json`,
`docs/` (five existing projections), `state.json` (managed artifact hashes).
Historical rollback data, if needed, is explicitly labeled, never a second editable
source of truth. Do not silently overwrite user-modified model/config/projections.
Reject symlinks, hardlinks, unknown managed paths and unsupported versions.

Refresh defaults to a non-writing diff. `apply=True` explicitly writes only
validated managed metadata; unchanged inputs preserve exact bytes, including the
original evidence timestamp. A new collection timestamp alone is not a semantic
change. Changed refs produce a reviewable semantic diff; never approve requirements
or authenticate evidence. Cleanup defaults to a plan, deletes only known unchanged
metadata when explicitly applied, and refuses unknown files/drift. No broad recursive
delete. If a multi-file write fails, preserve/report recovery evidence and never
claim success or atomicity that is not implemented.

## Acceptance

- Offline provider contract tests and actual local Git + mock model equivalence.
- Unsupported capabilities, malformed/partial responses and trust promotions fail.
- Source-byte/HEAD preservation on Spring Boot/Maven/Cloud Run and non-Java fixtures.
- Local and external workspace placement; deterministic repeat refresh and diff.
- Cited docs/context generated using existing APIs; no provider/LLM/cloud key.
- Tampering/path/symlink/cleanup/failure regressions and explicit rollback docs.
- CLI smoke from source and installed wheel, full Ruff/tests/build and CI.

## Limits

This is not Spring compatibility analysis, a successful build/migration, a real
agent execution, or evidence of lower cost/semantic equivalence. Framework/runtime
names in fixtures are declarations. #22 remains partial for other real provider
capabilities; #21 keeps application/provider/baseline/license gates explicit.
No new PRs per owner instruction; use small commits, review and green CI before
main integration. Consequential future provider writes require separate approval.
