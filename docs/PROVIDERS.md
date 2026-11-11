# Read-only provider experiment (#22)

## Design and acceptance

This bounded Stack A slice wraps existing manifest/Git discovery and an offline
model replay with one closed JSON envelope. Native and mock collection must retain
identical LSM identity, provenance and trust; repeated semantic inputs have a stable
request digest. Invalid descriptors/results, graph errors, unsafe manifest paths,
unsupported capabilities and unauthorized trust changes fail closed. Tests use
actual committed temporary repositories without inherited Git configuration/hooks.

```python
from lsm.providers import GitProvider, MockProvider, invoke, validate_result

result = invoke(GitProvider(), "discover", manifest=manifest, base_dir=source_base)
assert validate_result(result) == []
if result["status"] == "succeeded":
    model = result["data"]["model"]
    replay = invoke(MockProvider(model), "discover", manifest=manifest, base_dir=source_base)
    assert replay["data"]["model"] == model
```

`existing=None` optionally supplies the current model. `describe()` returns
`schema_version`, `id`, `version`, and `capabilities: [{name: "discover",
read_only: true}]`. Adapter `discover(*, manifest, base_dir, existing=None)` returns
the envelope, not a bare model. Callers use `invoke`, never bypass its transition
gate. Providers are trusted in-process Python objects, not sandboxed plugins;
configuration cannot dynamically import providers or run commands.

## Contract

`src/lsm/schemas/provider.schema.json` closes envelope, identity, evidence,
permissions and error shapes. `validate_result(result)` returns structured
`code/path/message` diagnostics and additionally validates the complete LSM graph.
Validation is not authentication or behavior verification.

- `schema_version: "1.0"`, `provider: {id, version}`, `capability`.
- `status`: `succeeded`, `partial`, or `failed`. Success requires a model and no
  errors; failure requires errors and null data. Partial remains partial and must
  not be used as a successful discovery by workspace orchestration.
- `data`: null or `{model}`. Provider-specific metadata never enters the LSM.
- `evidence`: stable source/entity-derived IDs, entity IDs, source URIs, immutable
  Git source refs where available (otherwise null), independent origins,
  `verification: "unverified"`, unknown `confidence: null`, UTC `collected_at`.
  Git collection is an observation, not proof that source behavior is correct.
- `errors`: diagnostics only; invocation substitutes fixed safe messages rather
  than publishing arbitrary adapter errors/exceptions or executable remediation.
- `permissions: {source_access: "read", writes_performed: false}`.
- `request_digest`: SHA-256 of canonical capability/manifest/existing JSON, excluding
  provider identity and machine-specific source base. Same inputs give the same
  digest; models and evidence IDs are stable while timestamps may differ.
  Consumers can use `request_digest(capability, manifest, existing=None)` to check
  persisted request binding without invoking a provider or reading source files.
- `observed_at`: actual UTC collection timestamp. Workspace refresh may preserve
  the first unchanged envelope rather than treating time alone as model drift.

Before returning any model (also partial models), invocation compares it with the
existing model, or an empty model of the same identity, using `check_transition`
with `actor_kind="agent"` and no policy. Newly approved requirements or verified
claims, and edits/removals/downgrades of protected entities, are denied. Unchanged
previously protected claims may be replayed without authenticating their history.
Caller inputs are deep-copied before adapter execution.

## Explicit limits

Only read-only `discover` is implemented. Evidence collection, planning, code
changes, tests, PRs, deployment and reconciliation remain unsupported capability
catalog entries, not adapters. Even approval cannot enable them: this API has no
policy argument or write executor. No parser, source scan, build, migration, agent,
service, network operation or application-file write is introduced. Git collection
delegates to `lsm.discovery.discover`, including its confined metadata checks.
Mock replay validates manifests and rejects symlink paths without reading source
files; it does not establish that its supplied model reflects live repositories.

This experiment does not close #22's future real provider capabilities or establish
semantic equivalence, application compatibility, cost improvements or authenticity
of imported evidence. Consequential future integrations need separate approval.

## Local verification (2026-11-11)

- `uv sync --locked`: passed.
- `uv run pytest tests/test_providers.py tests/test_discovery.py`: **105 passed**
  (60 provider-contract cases and 45 existing discovery cases).
- Ruff format/check on `src/lsm/providers.py` and `tests/test_providers.py`: passed.

These results cover local native Git/replay plumbing and negative trust/path/shape
cases, not an external provider, live application build or agent execution.
