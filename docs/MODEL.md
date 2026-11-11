# Living System Model 1.0

The public contract is `src/lsm/schemas/model.schema.json` (JSON Schema Draft
2020-12), shipped as a normal package resource. `examples/shop.json` is a complete
illustrative model. It describes logical backend, web, mobile, and store repositories;
it does not create or scan those repositories.

## Document and identity

A document contains exactly `schema_version`, `model`, `nodes`, and `edges`.
`schema_version` must be `"1.0"`; `model` contains `id` and `title`. Empty node and
edge lists are valid. Objects reject unknown fields, including `status`: version
1.0 represents claim state through provenance and requirement approval instead.

IDs match `^[a-z][a-z0-9_.:-]*$`. Node and edge IDs share a unique namespace.
IDs are stable identities, not regenerated from titles or paths. Renaming a node
does not change its ID. Every node has a positive integer `version`, incremented
when its modeled content changes. Schema versions and node versions are distinct;
there are no automatic schema migrations yet.

Nodes require `id`, `type`, `title`, `version`, and `provenance`. Types are
`requirement`, `domain_concept`, `behavior`, `component`, `interface`, `repository`,
`decision`, `implementation`, `test`, and `evidence`. Optional fields and their
precise constraints are defined by the schema. Requirements additionally require
nonempty `acceptance_criteria` and `approval`; evidence requires a nonempty `uri`.
URIs may be repository-relative artifact paths; they are not restricted to HTTP.

## Claim states and evidence

Every node and edge has provenance with a nonempty `source`, an `origin`, and a
`verification` state; `rationale` is optional.

- `declared`: authored intent or an explicit design statement, not observed behavior.
- `inferred`: an interpretation that has not been established as fact.
- `observed`: a recorded observation, not automatically verified or intended behavior.
- `unverified`: no claim of verification.
- `verified`: at least one evidence-node ID must appear in the claim's `evidence` list.

Evidence nodes themselves require supporting evidence to be marked verified.
Validation checks structure and references, not authenticity or truth. Neither a
`verified_by` edge nor an evidence node means a test passed. Approval
(`pending`, `approved`, `rejected`) is separate from verification; commands do not
approve requirements or enforce approver identity. Optional `confidence` is a
number from 0 to 1, not a replacement for verification. Optional `timestamp` must
be an RFC 3339 date-time; static artifacts need not invent an observation time.

The fixture deliberately keeps every claim unverified. Its requirement is pending
approval, implementation mapping is inferred, and test evidence is explicitly an
illustrative description, not an execution record.

## Directed relations

Edges require `id`, `type`, `source`, `target`, and `provenance`, with optional
`evidence`. Directions and endpoint types are normative:

| Relation | Source type | Target type |
| --- | --- | --- |
| `satisfies` | behavior, component, interface, implementation | requirement |
| `depends_on` | component, interface, repository, implementation | component, interface, repository, implementation |
| `implemented_by` | requirement, behavior, interface, component | implementation, component |
| `verified_by` | requirement, behavior, interface, component, implementation | test, evidence |
| `supersedes` | any | same type as source |
| `exposes` | component | interface |
| `decided_by` | any except evidence | decision |
| `belongs_to` | component, interface, implementation, test | repository |

For example, a newer requirement `supersedes` an older requirement, not the
reverse. Only `supersedes` must be acyclic. Other relation cycles are permitted.
The JSON Schema validates local structure; the graph validator checks unique IDs,
references, evidence-node types, endpoint compatibility, and supersedes cycles.

## Storage and limits

Store the whole model in one Git-friendly JSON or YAML document. Both formats
have the same schema and semantics. Serialization uses stable sorted keys, safe
YAML, rejects duplicate mapping keys, and does not preserve comments or original
formatting. Saving does not implicitly mutate the model.

This milestone does not enforce evidence authenticity, URI existence, approval
identity, or actual system behavior. It provides no repository scanner, graph
database, migrations, per-entity storage, extension relation types, or generated
Markdown/Mermaid views. Human review remains necessary for requirements and
consequential architecture decisions.
