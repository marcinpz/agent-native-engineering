"""Explainable conservative graph impact and human-approved change proposals."""

import copy
import hashlib
import json
from collections import deque
from importlib.resources import files

from jsonschema import Draft202012Validator

from lsm.security import redact, require_authorization
from lsm.validation import validate_model


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def model_digest(model):
    canonical = copy.deepcopy(model)
    for key in ("nodes", "edges"):
        canonical[key] = sorted(canonical[key], key=lambda entity: entity["id"])
    return hashlib.sha256(_canonical(canonical).encode()).hexdigest()


def _require_model(model):
    if validate_model(model):
        raise ValueError("Change analysis requires a valid model")
    identifiers = [model["model"]["id"]] + [item["id"] for item in model["nodes"] + model["edges"]]
    if any(redact(identifier) != identifier for identifier in identifiers):
        raise ValueError("Change projection identifiers must remain stable after redaction")


def semantic_diff(before, after):
    """Return redacted semantic summaries, not an executable source/model patch."""
    _require_model(before)
    _require_model(after)
    if before["model"]["id"] != after["model"]["id"]:
        raise ValueError("Cannot compare models with different identities")
    result = {}
    for collection in ("nodes", "edges"):
        left = {item["id"]: item for item in before[collection]}
        right = {item["id"]: item for item in after[collection]}
        result[collection] = {
            "added": [right[key] for key in sorted(right.keys() - left.keys())],
            "removed": [left[key] for key in sorted(left.keys() - right.keys())],
            "modified": [
                {
                    "id": key,
                    "before": left[key],
                    "after": right[key],
                    "fields": sorted(
                        field
                        for field in left[key].keys() | right[key].keys()
                        if left[key].get(field) != right[key].get(field)
                    ),
                }
                for key in sorted(left.keys() & right.keys())
                if left[key] != right[key]
            ],
        }
    result["metadata_changed"] = any(
        before.get(key) != after.get(key)
        for key in before.keys() | after.keys()
        if key not in {"nodes", "edges"}
    )
    return redact(result)


def analyze_impact(model, seed_ids):
    """Traverse relations/evidence; via contains edge IDs or evidence: JSON tokens."""
    _require_model(model)
    nodes = {node["id"]: node for node in model["nodes"]}
    if not isinstance(seed_ids, list) or not all(isinstance(item, str) for item in seed_ids):
        raise ValueError("Impact seeds must be a list of node IDs")
    seeds = sorted(set(seed_ids))
    if any(seed not in nodes for seed in seeds):
        raise ValueError("Unknown impact seed ID")
    adjacency = {identifier: [] for identifier in nodes}
    for edge in sorted(model["edges"], key=lambda item: item["id"]):
        adjacency[edge["source"]].append((edge["target"], edge["id"]))
        adjacency[edge["target"]].append((edge["source"], edge["id"]))
    # Keep via string-compatible, but distinguish references from real edge IDs.
    # An edge's supporting evidence can affect either endpoint, in either direction.
    for kind, owners in (("node", model["nodes"]), ("edge", model["edges"])):
        for owner in owners:
            endpoints = [owner["id"]] if kind == "node" else [owner["source"], owner["target"]]
            for evidence_id in owner.get("evidence", []):
                step = "evidence:" + _canonical([kind, owner["id"], evidence_id])
                for endpoint in endpoints:
                    adjacency[evidence_id].append((endpoint, step))
                    adjacency[endpoint].append((evidence_id, step))
    paths = {seed: [] for seed in seeds}
    queue = deque(seeds)
    while queue:
        current = queue.popleft()
        for neighbor, edge_id in sorted(adjacency[current]):
            if neighbor not in paths:
                paths[neighbor] = paths[current] + [edge_id]
                queue.append(neighbor)
    impacted = []
    for identifier in sorted(paths):
        node = nodes[identifier]
        impacted.append(
            {
                "id": identifier,
                "type": node["type"],
                "via": paths[identifier],
                "origin": node["provenance"]["origin"],
                "verification": node["provenance"]["verification"],
                "confidence": node.get("confidence"),
            }
        )
    return redact(
        {
            "seeds": seeds,
            "impacted": impacted,
            "repositories": sorted(item["id"] for item in impacted if item["type"] == "repository"),
            "unknown_impact": True,
            "limitations": [
                "Conservative undirected graph reachability can overestimate impact.",
                "Missing relationships and behavior outside this model remain unknown.",
                "Confidence and verification are model declarations, not measured impact accuracy.",
            ],
        }
    )


def proposal_content_digest(proposal):
    content = {key: value for key, value in proposal.items() if key not in {"state", "approval"}}
    return hashlib.sha256(_canonical(content).encode()).hexdigest()


def validate_proposal(proposal):
    schema = json.loads(files("lsm").joinpath("schemas/change.schema.json").read_text())
    errors = [
        {
            "code": "schema_error",
            "path": "/" + "/".join(map(str, error.absolute_path)),
            "message": error.message,
        }
        for error in Draft202012Validator(schema).iter_errors(proposal)
    ]
    if errors:
        return sorted(redact(errors), key=lambda error: (error["path"], error["message"]))
    if proposal["state"] == "approved":
        approval = proposal["approval"]
        if approval is None or approval["content_digest"] != proposal_content_digest(proposal):
            errors.append(
                {
                    "code": "approval_mismatch",
                    "path": "/approval",
                    "message": "Approval must bind the exact proposal content",
                }
            )
    elif proposal["approval"] is not None:
        errors.append(
            {
                "code": "unexpected_approval",
                "path": "/approval",
                "message": "Proposed changes cannot carry approval",
            }
        )
    return errors


def create_proposal(before, after, identifier="change:offline-sync"):
    diff = semantic_diff(before, after)
    # Compute seeds on raw identities, not on redacted summaries.
    left = {item["id"]: item for item in before["nodes"]}
    right = {item["id"]: item for item in after["nodes"]}
    seeds = {key for key in left.keys() | right.keys() if left.get(key) != right.get(key)}
    old_edges = {item["id"]: item for item in before["edges"]}
    new_edges = {item["id"]: item for item in after["edges"]}
    for key in old_edges.keys() | new_edges.keys():
        if old_edges.get(key) != new_edges.get(key):
            for edge in (old_edges.get(key), new_edges.get(key)):
                if edge:
                    seeds.update((edge["source"], edge["target"]))
    if diff["metadata_changed"]:
        seeds.update(left.keys() | right.keys())
    impacts = [
        analyze_impact(model, sorted(seeds & ids.keys()))
        for model, ids in ((before, left), (after, right))
    ]
    combined = {}
    for impact in impacts:
        for item in impact["impacted"]:
            if item["id"] not in combined or len(item["via"]) < len(combined[item["id"]]["via"]):
                combined[item["id"]] = item
    impact = impacts[1]
    impact["seeds"] = sorted(set(impacts[0]["seeds"]) | set(impacts[1]["seeds"]))
    impact["impacted"] = [combined[key] for key in sorted(combined)]
    impact["repositories"] = sorted(
        item["id"] for item in combined.values() if item["type"] == "repository"
    )
    result = {
        "schema_version": "1.0",
        "id": identifier,
        "state": "proposed",
        "before_digest": model_digest(before),
        "after_digest": model_digest(after),
        "diff": diff,
        "impact": impact,
        "assumptions": [],
        "risks": ["Model completeness and actual source impact require human review."],
        "approval": None,
    }
    if validate_proposal(result):
        raise ValueError("Generated proposal failed schema validation")
    return result


def approve_proposal(proposal, policy, actor, actor_kind="human"):
    if validate_proposal(proposal) or proposal["state"] != "proposed":
        raise ValueError("Only a valid proposed change can be approved")
    require_authorization(policy, actor, "approve_changes", actor_kind)
    result = copy.deepcopy(proposal)
    result["state"] = "approved"
    result["approval"] = {
        "actor": actor,
        "actor_kind": actor_kind,
        "content_digest": proposal_content_digest(result),
    }
    return result
