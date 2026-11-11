# Model governance and trust boundaries (#10)

Schema 1.0 is frozen and supported. Schema 1.1 adds optional `governance` metadata
with nonempty `owners` and optional `policy_uri`. These values describe ownership;
they do not grant filesystem or platform permissions. Both schemas are bundled,
resolved offline. Unknown versions fail. The only upgrade is 1.0 -> 1.1; it changes
only `schema_version`, preserves IDs/order/provenance, and validates both ends.
Downgrades are rejected to avoid metadata loss. Same-version migrations are
idempotent copies. See `examples/governance/model-1.*.json`.

`lsm migrate INPUT OUTPUT --target 1.1` writes explicitly, never overwrites without
`--force`. It cannot promote trust or approve requirements. Confidence remains a
declared number in [0,1]; confidence 1 does not constitute verification.

Authorization policy: `version: "1.0"`, `humans: [actor IDs]`, `permissions` mapping
`approve_requirements`, `approve_changes`, `verify` to explicitly granted humans.
Missing grant or an actor classified as agent is denied. Transition APIs require
authorization to add/edit/delete approved requirements or verified entities.
Requirement lifecycle and change proposal commands use the same policy boundary.

**Local actor names and policies are attestations, not authenticated identity.**
Trusted operators must protect policy/model files and CLI invocation using OS/Git
permissions and review. An agent with unrestricted write access could bypass any
local record; this tool does not claim to be an authentication service. Importing
a model containing `approved`/`verified` only imports untrusted declarations, not
newly certified facts. URI existence, external evidence and actual behavior are
not authenticated by graph validation.

Documentation/context/benchmark projections apply shared redaction to sensitive
keys, common tokens, credentials, private keys and URL passwords before output.
Never load `.env`, secrets or arbitrary source files for context. Redaction is
best-effort defense in depth: arbitrary prose can contain unknown secrets, so
operators must curate inputs and review artifacts before publishing. Structured
error messages for projections must not echo secret-bearing artifact contents.
Raw `inspect`, import and persistence are local model editing tools, not safe
publication endpoints; do not expose them to untrusted callers.
