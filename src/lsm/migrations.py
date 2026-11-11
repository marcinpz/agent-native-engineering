"""Explicit, lossless model upgrades. Never infer approval or verification."""

import copy

from lsm.validation import validate_model


def migrate_model(model, target="1.1"):
    if validate_model(model):
        raise ValueError("Cannot migrate invalid model")
    source = model["schema_version"]
    if target not in {"1.0", "1.1"}:
        raise ValueError(f"Unsupported target schema version: {target!r}")
    if source == "1.1" and target == "1.0":
        raise ValueError("Downgrades are not supported; governance metadata could be lost")
    result = copy.deepcopy(model)
    result["schema_version"] = target
    if validate_model(result):
        raise ValueError("Migrated model failed target validation")
    return result
