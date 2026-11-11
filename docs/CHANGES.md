# Semantic changes and conservative impact (#5)

`semantic_diff(before, after)` compares entities by stable ID, ignoring ordering
of node/edge arrays and object keys. Content arrays (including criteria) retain
their order. Summaries are redacted; they are not executable patches. Model
digests use canonical raw content and bind exact inputs without disclosing them.

`analyze_impact(model, seed_ids)` conservatively traverses relations in both
directions and supplies an edge-ID path for each affected entity. This may
overestimate impact; missing model edges and unknown external behavior mean
`unknown_impact` is always true. Reported confidence is a model declaration, not
measured impact accuracy. Disconnected entities are not assumed affected.

`create_proposal(before, after)` combines impact from both graphs, including
deleted edges/entities, so removal cannot hide affected clients/tests. Metadata
changes conservatively seed all nodes. Results include semantic diff, input
digests, assumptions, risks and explicit proposed/approved state. Human review is
required before implementation. Approving uses policy `approve_changes`; agent
actors are denied. Approval binds the proposal content digest; editing approved
content invalidates it. Local names/digests are attestations, not signatures or
authentication. Nothing executes, approves requirements or modifies repositories.

```sh
uv run lsm change propose examples/changes/before.json examples/changes/offline-sync.json proposal.json
uv run lsm change validate proposal.json
uv run lsm change approve proposal.json approved-change.json --policy examples/governance/policy.json --actor demo-owner
```

The approval command is an explicit human action, not authorization for an agent
to impersonate the named owner. Offline-sync fixtures are illustrative intent;
impact links include mobile, backend, storage and tests but prove no implementation.
