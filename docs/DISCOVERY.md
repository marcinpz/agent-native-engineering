# Explicit, read-only discovery

```python
from pathlib import Path
from lsm.discovery import discover

model = discover(manifest, Path("local-repositories"), existing=None)
```

`discover(manifest: dict, base_dir: Path, existing: dict | None = None) -> dict`
returns a validated model **1.0** without changing its inputs or writing files.
Invalid manifests, models, references, conflicts, or inaccessible repositories
raise actionable `ValueError` diagnostics. The CLI is a separate integration.

## Manifest contract

The closed Draft 2020-12 schema is
`src/lsm/schemas/discovery.schema.json`. Required fields:

- `schema_version: "1.0"` and `model: {id, title}`.
- `repositories: [{id, title, path, components: [{id, title}]}]`.
- Entries under `components` default to `type: "component"`. Explicit types may
  also be `interface`, `implementation` or `test` (the model's repository-owned
  types). Only component entries may declare `interfaces: [{id, title}]`.
- Optional `dependencies: [{id, source, target}]` explicitly declares `depends_on`.

IDs follow the model ID syntax and share the node/edge namespace. They are never
derived from titles or paths. Nested components/interfaces explicitly declare
`belongs_to` repository links and component `exposes` interface links. These edges
receive deterministic IDs of the form
`discovery:<relation>:<source-ID-length>:<source-ID>:<target-ID>`; collisions with
explicit IDs are rejected. No dependencies or other relationships are inferred.

Paths use forward slashes, are nonempty relative roots under `base_dir`, and may
not contain empty, `.` or `..` segments, backslashes, control characters, or drive
prefixes. Duplicate roots, absolute paths and symlinks (including intermediate
directories and metadata symlinks) are rejected. The base must already exist and
have no symlink ancestors. Roots must have Git metadata and a committed HEAD;
plain directories, bare repositories and unborn repositories are not supported.
Gitdir/commondir pointers must stay inside the base; Git configuration includes
are rejected to avoid reading external configuration.

## Provenance and merging

Repository nodes are `observed` / `unverified`: provenance source includes the
manifest JSON Pointer, relative root and observed Git HEAD hash. Titles and IDs
remain manifest labels, not independently verified facts. Components, interfaces
and edges are `declared` / `unverified`, citing manifest JSON Pointers. No timestamps,
evidence, approvals or verified claims are invented; no extra model fields are added.

Existing models are validated before use and must be schema 1.0 with identical
model identity/title. Equal entities are retained; new IDs are appended in manifest
order. Conflicting IDs raise errors rather than updating titles, provenance,
versions or commits silently. Dependencies may reference existing nodes. Output
is validated with `validate_model`. Re-importing the same manifest at unchanged
HEADs into its result yields exact dictionary equality. A changed HEAD intentionally
causes a conflict requiring explicit reconciliation. List order is preserved;
reordering a manifest changes JSON Pointer citations and may cause conflicts.

## Safety boundary and limitations

Discovery inspects only explicitly listed roots and their Git metadata (including
checking metadata paths for symlinks); it never opens application sources, `.env`
files or scripts. It invokes only controlled, shell-free `git -C ... rev-parse`
commands with timeouts, optional locks disabled and an isolated Git environment.
It does not run hooks, source parsers, network commands, commits or checkouts.
Repository contents must not be concurrently modified during discovery: filesystem
checks are not a sandbox against an adversary swapping paths between checks.

See [the runnable local fixture](../examples/discovery/README.md). Tests create
temporary repositories with explicit commit identities; passing validation proves
model structure, not implementation correctness or authenticity of Git metadata.
