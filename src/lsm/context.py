"""Offline, deterministic context projection. Model text is untrusted data."""

import heapq
import json
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft202012Validator

from lsm.security import redact
from lsm.validation import validate_model

_PRIORITY = {
    name: index
    for index, name in enumerate(
        ("requirement", "decision", "component", "interface", "test", "evidence", "repository")
    )
}
_TEXT_FIELDS = ("description", "owner", "approval", "commit", "timestamp")
_LIST_FIELDS = ("acceptance_criteria", "open_questions", "constraints")


def serialize_context(pack: dict) -> str:
    """Canonical compact JSON; transport newlines are not part of the pack."""
    return json.dumps(
        pack, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def estimate_context(value: dict) -> int:
    """UTF-8 byte count, used as a conservative proxy, NOT provider token usage."""
    return len(serialize_context(value).encode("utf-8"))


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads(files("lsm").joinpath("schemas/context.schema.json").read_text())
    return Draft202012Validator(schema)


def validate_context(pack: dict) -> list[dict]:
    """Return schema diagnostics plus endpoint/accounting consistency diagnostics."""
    errors = [
        {"path": "/" + "/".join(map(str, error.absolute_path)), "message": error.message}
        for error in _validator().iter_errors(pack)
    ]
    if errors:
        return sorted(errors, key=lambda item: (item["path"], item["message"]))
    identifiers = {node["id"] for node in pack["nodes"]}
    if not set(pack["seed_ids"]) <= identifiers:
        errors.append({"path": "/seed_ids", "message": "Seeds must be included"})
    entities = pack["nodes"] + pack["edges"]
    if len({entity["id"] for entity in entities}) != len(entities):
        errors.append({"path": "/nodes", "message": "Entity IDs must be unique"})
    for index, edge in enumerate(pack["edges"]):
        if not {edge["source"], edge["target"]} <= identifiers:
            errors.append({"path": f"/edges/{index}", "message": "Missing endpoint"})
    for entity in entities:
        if not set(entity.get("evidence", [])) <= {
            node["id"] for node in pack["nodes"] if node["type"] == "evidence"
        }:
            errors.append({"path": "/nodes", "message": "Missing or mistyped evidence"})
    for selection in pack["selection"]:
        if (
            selection["id"] not in identifiers
            or not set(selection["path"]) <= identifiers
            or selection["path"][-1] != selection["id"]
            or selection["path"][0] not in pack["seed_ids"]
        ):
            errors.append({"path": "/selection", "message": "Invalid selection path"})
    if {citation["id"] for citation in pack["citations"]} != {entity["id"] for entity in entities}:
        errors.append({"path": "/citations", "message": "Citations must cover included entities"})
    size = estimate_context(pack)
    if size != pack["accounting"]["estimated_tokens"] or size > pack["accounting"]["budget"]:
        errors.append({"path": "/accounting", "message": "Incorrect or exceeded byte budget"})
    return errors


def _project(entity):
    """Bound textual detail; never copy arbitrary metadata or omitted entity content."""
    truncated = 0

    def text(value, limit=256):
        nonlocal truncated
        if len(value) > limit:
            truncated += 1
            return value[:limit] + "…"
        return value

    result = {key: entity[key] for key in ("id", "type")}
    if "title" in entity:
        result["title"] = text(entity["title"], 160)
        result["version"] = entity["version"]
    else:
        result.update({key: entity[key] for key in ("source", "target")})
    provenance = entity["provenance"]
    result["provenance"] = {
        "origin": provenance["origin"],
        "verification": provenance["verification"],
    }
    if "rationale" in provenance:
        result["provenance"]["rationale"] = text(provenance["rationale"])
    for key in _TEXT_FIELDS:
        if key in entity:
            result[key] = text(entity[key], 512 if key == "description" else 256)
    for key in _LIST_FIELDS:
        if key in entity:
            values = entity[key]
            truncated += max(0, len(values) - 8)
            result[key] = [text(value) for value in values[:8]]
    if "confidence" in entity:
        result["confidence"] = entity["confidence"]
    citation = {"id": entity["id"], "source": text(provenance["source"])}
    if "uri" in entity:
        citation["uri"] = text(entity["uri"])
    return result, citation, truncated


def compile_context(model: dict, task: str, seed_ids: list[str], budget: int = 8192) -> dict:
    """Compile a bounded pack, raising ValueError on invalid input or impossible seeds.

    Explicit graph/evidence references only: no semantic task search, source reads,
    environment access, URI resolution, approval, or evidence authentication.
    """
    if validate_model(model):
        raise ValueError("Context requires a valid model")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("Context requires a nonempty task")
    if (
        not isinstance(seed_ids, list)
        or not seed_ids
        or not all(isinstance(value, str) and value for value in seed_ids)
    ):
        raise ValueError("Context requires nonempty explicit seed IDs")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        raise ValueError("Budget must be a positive integer")
    originals = {node["id"] for node in model["nodes"]}
    if not set(seed_ids) <= originals:
        raise ValueError("Unknown seed ID")
    safe = redact(model)
    # Redaction must not silently merge identities or invalidate traceability.
    if [item["id"] for item in safe["nodes"] + safe["edges"]] != [
        item["id"] for item in model["nodes"] + model["edges"]
    ]:
        raise ValueError("Redaction changed an entity ID; context cannot preserve identity")
    nodes = {node["id"]: node for node in safe["nodes"]}
    edges = {edge["id"]: edge for edge in safe["edges"]}
    seeds = sorted(set(seed_ids))
    adjacency = {identifier: [] for identifier in nodes}
    for edge in edges.values():
        source, target = edge["source"], edge["target"]
        adjacency[source].append((target, edge["id"]))
        adjacency[target].append((source, edge["id"]))
        for reference in edge.get("evidence", []):
            # Evidence on a relation is reachable from either endpoint.
            for endpoint in (source, target):
                adjacency[endpoint].append((reference, "evidence:" + edge["id"]))
                adjacency[reference].append((endpoint, "evidence:" + edge["id"]))
    for node in nodes.values():
        for reference in node.get("evidence", []):
            adjacency[node["id"]].append((reference, "evidence:" + node["id"]))
            adjacency[reference].append((node["id"], "evidence:" + node["id"]))

    projected = {key: _project(value) for key, value in (nodes | edges).items()}
    whole_bytes = estimate_context(safe)
    selected = set(seeds)
    chosen_edges = set()
    reasons = {
        identifier: {"id": identifier, "reason": "explicit_seed", "path": [identifier], "via": ""}
        for identifier in seeds
    }

    def build():
        entity_ids = sorted(selected) + sorted(chosen_edges)
        uncertainties = []
        projections = {}
        for identifier in entity_ids:
            entity = nodes.get(identifier, edges.get(identifier))
            projections[identifier] = dict(projected[identifier][0])
            if "evidence" in entity:
                projections[identifier]["evidence"] = sorted(set(entity["evidence"]) & selected)
            flags = []
            if entity["provenance"]["origin"] == "inferred":
                flags.append("inferred")
            if entity["provenance"]["verification"] != "verified":
                flags.append("unverified")
            if entity.get("open_questions"):
                flags.append("open_questions")
            missing = len(set(entity.get("evidence", [])) - selected)
            if missing:
                flags.append("omitted_evidence")
            if flags:
                uncertainties.append(
                    {"id": identifier, "flags": flags, "omitted_evidence": missing}
                )
        pack = {
            "schema_version": "1.0",
            "model_id": safe["model"]["id"],
            "task": redact(task),
            "trust": "untrusted_data_no_implicit_approval",
            "seed_ids": seeds,
            "nodes": [projections[key] for key in sorted(selected)],
            "edges": [projections[key] for key in sorted(chosen_edges)],
            "citations": [projected[key][1] for key in entity_ids],
            "selection": [reasons[key] for key in sorted(selected)],
            "uncertainties": uncertainties,
            "omitted": {
                "nodes": len(nodes) - len(selected),
                "edges": len(edges) - len(chosen_edges),
                "truncated_values": sum(projected[key][2] for key in entity_ids),
            },
            "accounting": {
                "method": "canonical_json_utf8_bytes",
                "budget": budget,
                "estimated_tokens": 0,
                "provider_overhead_included": False,
                "naive_whole_model_estimated_tokens": whole_bytes,
            },
        }
        # Self-inclusive accounting reaches a fixed point when digit width stabilizes.
        while True:
            size = estimate_context(pack)
            if pack["accounting"]["estimated_tokens"] == size:
                return pack
            pack["accounting"]["estimated_tokens"] = size

    pack = build()
    if estimate_context(pack) > budget:
        raise ValueError("Budget cannot fit explicit seeds and context metadata")
    frontier = []

    def expand(identifier):
        for neighbor, via in adjacency[identifier]:
            if neighbor not in selected:
                path = reasons[identifier]["path"] + [neighbor]
                heapq.heappush(
                    frontier,
                    (len(path), _PRIORITY.get(nodes[neighbor]["type"], 7), neighbor, path, via),
                )

    for seed in seeds:
        expand(seed)
    attempted = set()
    while frontier:
        _, _, identifier, path, via = heapq.heappop(frontier)
        if identifier in selected or identifier in attempted:
            continue
        attempted.add(identifier)
        selected.add(identifier)
        reasons[identifier] = {
            "id": identifier,
            "reason": "graph_neighbor",
            "path": path,
            "via": via,
        }
        added_edge = via in edges and via not in chosen_edges
        if added_edge:
            chosen_edges.add(via)
        candidate = build()
        if estimate_context(candidate) <= budget:
            pack = candidate
            expand(identifier)
        else:
            selected.remove(identifier)
            del reasons[identifier]
            if added_edge:
                chosen_edges.remove(via)
    # Additional relations are lower priority than reachable nodes, never dangling.
    for identifier, edge in sorted(edges.items()):
        if identifier in chosen_edges or not {edge["source"], edge["target"]} <= selected:
            continue
        chosen_edges.add(identifier)
        candidate = build()
        if estimate_context(candidate) <= budget:
            pack = candidate
        else:
            chosen_edges.remove(identifier)
    errors = validate_context(pack)
    if errors:
        raise ValueError("Invalid compiled context: " + errors[0]["message"])
    return pack
