# Tiny context fixture

`model.json` contains a pending requirement, inferred component, illustrative
evidence and disconnected component. It describes a proposed scenario: save a
note, then retrieve it as the same user. Nothing here records an executed test.
The `verified_by` relation is unverified, not proof that the scenario works.

Use `compile_context` from `lsm.context` with task `Plan note saving`, seed
`requirement.save` and budget `8192`. The disconnected billing component must
stay excluded. See [the library API and CLI integration contract](../../docs/CONTEXT.md).
No golden pack is hand-authored: generate output with `serialize_context` so
its self-inclusive byte accounting matches the actual serialization.
