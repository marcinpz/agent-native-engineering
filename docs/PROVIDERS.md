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

The discovery envelope implements only read-only `discover`. Dedicated evidence retrieval, planning, code
changes, tests, PRs, deployment and reconciliation remain unsupported capability
catalog entries, not adapters. Even approval cannot enable them: this API has no
policy argument or write executor. No parser, source scan, build, migration, agent,
service, network operation or application-file write is introduced. Git collection
delegates to `lsm.discovery.discover`, including its confined metadata checks.
Mock replay validates manifests and rejects symlink paths without reading source
files; it does not establish that its supplied model reflects live repositories.
Native collection observes committed HEAD metadata and explicit manifest declarations,
not uncommitted working-tree changes, dependency resolution or application behavior.
A stable HEAD does not prove a clean or unchanged working tree.

This experiment does not close #22's future real provider capabilities or establish
semantic equivalence, application compatibility, cost improvements or authenticity
of imported evidence. Consequential future integrations need separate approval.

## Existing JUnit report import (partial #22)

Design/acceptance: import existing bytes without commands, model mutations or trust
promotion; bind deterministic identities to artifact SHA-256 plus explicit repository
ID and full commit; reject malformed/contradictory reports and suppress raw output.
The standalone `lsm.junit.import_junit(path, repository=..., commit=...)` and CLI
return a companion result, **not** the discovery `{model}` contract. They reuse
provider identity/status, diagnostics, observation time and read-only permissions;
`invoke`, Git/mock discovery and workspace refresh are unchanged. This avoids
pretending report outcomes are discovery nodes or widening every existing caller.

```sh
uv run lsm import-junit examples/junit.xml \
  --repository repository:demo \
  --commit 0123456789012345678901234567890123456789 > report-evidence.json
```

Exit 0/status `succeeded` means import succeeded, **not tests passed**. Inspect
`data.cases[].outcome` (`passed`, `failure`, `error`, `skipped`) and per-suite
aggregate counts. Invalid input yields exit 1/status `failed`, null data and fixed
diagnostics. The illustrative fixture intentionally contains a failure and skip.

`data.binding` is a **user attestation**, not proof the report was produced from
that repository/commit. No Git existence/cleanliness, execution, authenticity,
measured verification or approval is established. Every report stays observed,
unverified, confidence unknown; no model is read or modified. `source_ref` is a
content-addressed `sha256:` reference to the exact input bytes, not a retrieval
service; retain the original artifact separately. IDs also include binding and
case positions (reordering/changing the report intentionally changes identities).
Only `observed_at` varies across identical imports.

The bounded dialect accepts UTF-8 `testsuite`/`testsuites` nesting with named cases,
at most 2 MiB, 20,000 XML elements and depth 32. Optional declared aggregate counts
must match descendant cases; multiple outcome markers, empty reports and unsupported
structural elements fail closed. Standard XML comments and CDATA text are accepted;
comments are discarded and CDATA failure/output text is not projected. Parsing uses
`defusedxml` with `forbid_dtd`, `forbid_entities` and `forbid_external` explicitly
enabled: DTDs (including external subsets) and entity declarations/references are
rejected by parser callbacks, not a blanket `<!` text heuristic. Predefined XML
escapes such as `&amp;` remain valid. No external resolver, network, XInclude or
execution is supported. This intentionally rejects some JUnit dialects.
Failure/error/skip text and attributes, stdout/stderr and properties are never
projected. Names/classnames are bounded and use shared redaction, which is not a
complete secret detector: review metadata before publication. Suite counts describe
the report's claims, not independently verified execution. There is no requirement
mapping, workspace integration, automatic claim promotion or general test executor.

Suite outcomes prioritize error, failure, empty, all-skipped, then passed (counts
still disclose mixed skips). Unsupported testcase `status` values other than `run`
and dialect-specific `result` flags are rejected rather than guessed as passing.
The companion JSON shape is documented here, not accepted by discovery-specific
`validate_result`/schema; no portable evidence validation API or persisted
workspace import is claimed by this slice.

Local slice verification (2026-11-11): focused JUnit/provider/discovery tests
**142 passed** (31 JUnit cases); full `uv run pytest` **770 passed**;
`uv run ruff format --check .` and `uv run ruff check .` passed.
The documented fixture import and `uv run python scripts/adoption_smoke.py`
passed; adoption still reported unchanged source bytes/HEADs and no application
builds/tests. These checks do not authenticate any imported report.

Review follow-up acceptance: comments and failure/error/skip/output CDATA import
without exposing their text; hostile DTD/internal/external/parameter entity cases
fail closed. A new interoperability test invokes installed pytest with `--junitxml`
in a generated temporary fixture directory (one pass, one fail, one skip), then
imports the real report and checks outcomes, attested binding, digest, unverified
trust, no raw failure text, unchanged fixture/report bytes and no importer subprocess.
Only the test harness runs pytest; the importer still never runs a test/build.

## Local verification (2026-11-11)

- `uv sync --locked`: passed.
- `uv run pytest tests/test_providers.py tests/test_discovery.py`: **105 passed**
  (60 provider-contract cases and 45 existing discovery cases).
- Ruff format/check on `src/lsm/providers.py` and `tests/test_providers.py`: passed.

These results cover local native Git/replay plumbing and negative trust/path/shape
cases, not an external provider, live application build or agent execution.
