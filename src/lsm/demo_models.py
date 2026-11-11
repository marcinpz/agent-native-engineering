"""Fresh canonical models for the one supported generated fixture transition.

These declarations describe a pure function demo, not application-level offline
sync, persistence, retries or conflict resolution. No repository examples are
read at runtime, so installed packages have the same execution contract.
"""

import copy


def demo_models() -> tuple[dict, dict]:
    def provenance(source="demo manifest"):
        return {"origin": "declared", "source": source, "verification": "unverified"}

    before = {
        "schema_version": "1.0",
        "model": {"id": "system.offline-demo", "title": "Offline sync demo"},
        "nodes": [
            {
                "id": "requirement.offline-sync",
                "type": "requirement",
                "title": "Generated synchronize contract v1",
                "version": 1,
                "acceptance_criteria": [
                    "In each generated Python fixture, synchronize(queued) returns exactly "
                    "{'version': 1, 'accepted': 0, 'offline': False} for a sized queue.",
                    "This pure function demo performs no persistence, networking, retries "
                    "or conflict resolution and makes no application fulfillment claim.",
                ],
                "approval": "pending",
                "provenance": provenance("examples/changes/before.json"),
            }
        ],
        "edges": [],
    }
    names = ("backend", "web", "mobile", "store")
    titles = ("Backend API", "Web client", "Mobile client", "Data store")
    for name, title in zip(names, titles, strict=True):
        before["nodes"].append(
            {
                "id": f"component.{name}",
                "type": "component",
                "title": title,
                "version": 1,
                "provenance": provenance(),
            }
        )
    before["nodes"].append(
        {
            "id": "test.offline-sync",
            "type": "test",
            "title": "Generated synchronize(['pending']) contract",
            "version": 1,
            "description": "Planned fixed fixture assertion, not an execution record.",
            "provenance": provenance(),
        }
    )
    for name in names:
        before["nodes"].append(
            {
                "id": f"repo.{name}",
                "type": "repository",
                "title": name.capitalize(),
                "version": 1,
                "provenance": provenance(),
            }
        )
    edges = [
        ("edge.satisfies", "satisfies", "component.backend", "requirement.offline-sync"),
        ("edge.web-backend", "depends_on", "component.web", "component.backend"),
        ("edge.mobile-backend", "depends_on", "component.mobile", "component.backend"),
        ("edge.backend-store", "depends_on", "component.backend", "component.store"),
        ("edge.test", "verified_by", "requirement.offline-sync", "test.offline-sync"),
        *[
            (f"edge.repo-{name}", "belongs_to", f"component.{name}", f"repo.{name}")
            for name in names
        ],
    ]
    before["edges"] = [
        {
            "id": identifier,
            "type": kind,
            "source": source,
            "target": target,
            "provenance": provenance(),
        }
        for identifier, kind, source, target in edges
    ]
    after = copy.deepcopy(before)
    after["nodes"][0] = {
        "id": "requirement.offline-sync",
        "type": "requirement",
        "title": "Generated synchronize contract v2",
        "version": 2,
        "acceptance_criteria": [
            "In each generated Python fixture, synchronize(queued) returns exactly "
            "{'version': 2, 'accepted': len(queued), 'offline': True} for a sized queue.",
            "This pure function demo performs no persistence, networking, retries "
            "or conflict resolution and makes no application fulfillment claim.",
        ],
        "approval": "pending",
        "provenance": provenance("examples/changes/offline-sync.json"),
    }
    return before, after
