# Joined discovery / requirements / documentation fixture

`seed-model.json` is illustrative declared intent and an explicitly **inferred**
implementation hypothesis. The evidence points here to a scenario description,
not a test execution. A queued edit should remain visible while disconnected;
conflict policy remains an unresolved question. Requirement approval is pending.
Neither a `satisfies` nor `verified_by` relation establishes implemented behavior.

The backend node matches the explicit `examples/discovery/manifest.json` entry so
read-only discovery can merge it idempotently into one model with the generated
repositories. A conflicting declaration must fail rather than overwrite it.
The synthetic `password=ane-integration-probe-only` string is a fake redaction
probe; it must remain absent from publication outputs, not from raw local models.

`scripts/roadmap_smoke.py` generates new demo repositories and runs the complete
CLI flow. It inspects requirement/provenance, checks schema migration preservation,
exports deterministic docs/Mermaid twice, verifies explicit requirement-to-test
links, and confirms source file bytes remain unchanged before executing the
separate fixed local workflow demo. No real application migration is performed.
