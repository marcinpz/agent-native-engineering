"""Schema and graph validation; passing is not evidence authenticity verification."""

import json
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft202012Validator, FormatChecker

_IMPLEMENTABLE = {"component", "interface", "repository", "implementation"}
_RELATIONS = {
    "satisfies": ({"behavior", "component", "interface", "implementation"}, {"requirement"}),
    "depends_on": (_IMPLEMENTABLE, _IMPLEMENTABLE),
    "implemented_by": (
        {"requirement", "behavior", "interface", "component"},
        {"implementation", "component"},
    ),
    "verified_by": (
        {"requirement", "behavior", "interface", "component", "implementation"},
        {"test", "evidence"},
    ),
    "exposes": ({"component"}, {"interface"}),
    "belongs_to": ({"component", "interface", "implementation", "test"}, {"repository"}),
}


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads(
        files("lsm").joinpath("schemas/model.schema.json").read_text(encoding="utf-8")
    )
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _pointer(parts):
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def validate_model(model) -> list[dict]:
    """Return deterministic JSON Pointer diagnostics, even for invalid graph shapes."""
    errors = []

    def report(code, path, message):
        errors.append({"code": code, "path": path, "message": message})

    for error in _validator().iter_errors(model):
        report("schema_error", _pointer(error.absolute_path), error.message)
    if not isinstance(model, dict):
        return sorted(errors, key=lambda error: (error["path"], error["code"], error["message"]))
    if "schema_version" in model and model["schema_version"] != "1.0":
        report(
            "unsupported_schema_version",
            "/schema_version",
            "Only schema version '1.0' is supported",
        )

    collections = {}
    seen = {}
    nodes = {}
    for collection in ("nodes", "edges"):
        values = model.get(collection)
        collections[collection] = values if isinstance(values, list) else []
        for index, entity in enumerate(collections[collection]):
            if not isinstance(entity, dict):
                continue
            identifier = entity.get("id")
            if not isinstance(identifier, str):
                continue
            path = f"/{collection}/{index}/id"
            if identifier in seen:
                report(
                    "duplicate_id", path, f"ID {identifier!r} is already used at {seen[identifier]}"
                )
            else:
                seen[identifier] = path
            if collection == "nodes":
                nodes.setdefault(identifier, entity)

    for collection, entities in collections.items():
        for index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                continue
            path = f"/{collection}/{index}"
            evidence = entity.get("evidence")
            provenance = entity.get("provenance")
            if (
                isinstance(provenance, dict)
                and provenance.get("verification") == "verified"
                and (not isinstance(evidence, list) or not evidence)
            ):
                report("evidence_required", f"{path}/evidence", "Verified claims require evidence")
            if isinstance(evidence, list):
                for ref_index, reference in enumerate(evidence):
                    if not isinstance(reference, str):
                        continue
                    ref_path = f"{path}/evidence/{ref_index}"
                    if reference not in nodes:
                        report(
                            "missing_evidence",
                            ref_path,
                            f"Evidence node {reference!r} does not exist",
                        )
                    elif nodes[reference].get("type") != "evidence":
                        report(
                            "invalid_evidence_type", ref_path, f"Node {reference!r} is not evidence"
                        )
                    elif (
                        collection == "nodes"
                        and entity.get("type") == "evidence"
                        and reference == entity.get("id")
                    ):
                        report(
                            "self_supporting_evidence",
                            ref_path,
                            "Evidence nodes must reference other evidence, not themselves",
                        )

    supersedes = {}
    for index, edge in enumerate(collections["edges"]):
        if not isinstance(edge, dict):
            continue
        path = f"/edges/{index}"
        endpoints = []
        for field in ("source", "target"):
            reference = edge.get(field)
            node = nodes.get(reference) if isinstance(reference, str) else None
            endpoints.append(node)
            if isinstance(reference, str) and node is None:
                report("missing_endpoint", f"{path}/{field}", f"Node {reference!r} does not exist")
        source, target = endpoints
        if source is None or target is None:
            continue
        relation = edge.get("type")
        source_type, target_type = source.get("type"), target.get("type")
        if not isinstance(source_type, str) or not isinstance(target_type, str):
            continue
        valid = True
        if relation == "supersedes":
            valid = source_type == target_type
            supersedes.setdefault(edge["source"], []).append((edge["target"], index))
        elif relation == "decided_by":
            valid = source_type != "evidence" and target_type == "decision"
        elif isinstance(relation, str) and relation in _RELATIONS:
            source_types, target_types = _RELATIONS[relation]
            valid = source_type in source_types and target_type in target_types
        if not valid:
            report(
                "invalid_relation_endpoints",
                path,
                f"Relation {relation!r} does not allow {source_type!r} -> {target_type!r}",
            )

    # Iterative DFS avoids the Python recursion limit on large, valid chains.
    state = {}
    for start in sorted(supersedes):
        if state.get(start):
            continue
        state[start] = 1
        stack = [(start, iter(supersedes.get(start, [])))]
        while stack:
            node, outgoing = stack[-1]
            item = next(outgoing, None)
            if item is None:
                state[node] = 2
                stack.pop()
                continue
            target, index = item
            if state.get(target) == 1:
                report(
                    "supersedes_cycle", f"/edges/{index}", "The supersedes relation must be acyclic"
                )
            elif not state.get(target):
                state[target] = 1
                stack.append((target, iter(supersedes.get(target, []))))

    return sorted(errors, key=lambda error: (error["path"], error["code"], error["message"]))
