"""Bounded, read-only provider boundary; no dynamic loading or write executor."""

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from lsm.discovery import discover
from lsm.security import check_transition
from lsm.validation import validate_model


def _schema():
    return json.loads(files("lsm").joinpath("schemas/provider.schema.json").read_text())


def _diagnostic(code, path, message):
    return {"code": code, "path": path, "message": message}


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _request(capability, manifest, existing):
    # Provider identity and machine-specific base paths are not semantic inputs.
    return _digest({"capability": capability, "manifest": manifest, "existing": existing})


def _now():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _evidence_identity(identifier, source):
    # Discovery already supplies immutable Git refs; do not inspect Git here.
    return {
        "id": "provider-evidence:" + _digest({"id": identifier, "source": source}),
        "source_ref": source.split("; git:", 1)[1] if "; git:" in source else None,
    }


def _result(descriptor, capability, digest, model=None, error=None):
    timestamp = _now()
    evidence = []
    if model is not None:
        for entity in model["nodes"] + model["edges"]:
            provenance = entity["provenance"]
            source = provenance["source"]
            evidence.append(
                {
                    **_evidence_identity(entity["id"], source),
                    "entity_id": entity["id"],
                    "source_uri": source,
                    "origin": provenance["origin"],
                    "verification": "unverified",
                    "confidence": None,
                    "collected_at": timestamp,
                }
            )
    return {
        "schema_version": "1.0",
        "provider": {key: descriptor[key] for key in ("id", "version")},
        "capability": capability,
        "status": "failed" if error else "succeeded",
        "data": None if model is None else {"model": deepcopy(model)},
        "evidence": evidence,
        "errors": [] if error is None else [_diagnostic(error, "", "Provider request rejected")],
        "permissions": {"source_access": "read", "writes_performed": False},
        "request_digest": digest,
        "observed_at": timestamp,
    }


def validate_result(result) -> list[dict]:
    """Validate closed result shape and graph; does not authenticate evidence."""
    try:
        json.dumps(result, allow_nan=False)
    except (ValueError, TypeError, RecursionError):
        return [_diagnostic("provider_schema_error", "", "Result must be JSON-compatible")]
    validator = Draft202012Validator(_schema(), format_checker=FormatChecker())
    errors = [
        _diagnostic(
            "provider_schema_error",
            "".join(
                "/" + str(part).replace("~", "~0").replace("/", "~1")
                for part in error.absolute_path
            ),
            "Invalid provider result field",
        )
        for error in validator.iter_errors(result)
    ]
    if errors:
        return sorted(errors, key=lambda item: (item["path"], item["code"]))
    data = result["data"]
    if data is not None:
        errors.extend(
            _diagnostic(item["code"], "/data/model" + item["path"], "Invalid provider model")
            for item in validate_model(data["model"])
        )
        if not errors:
            entities = {
                item["id"]: item for key in ("nodes", "edges") for item in data["model"][key]
            }
            cited = set()
            for item in result["evidence"]:
                entity = entities.get(item["entity_id"])
                if (
                    entity is None
                    or item["source_uri"] != entity["provenance"]["source"]
                    or item["origin"] != entity["provenance"]["origin"]
                ):
                    errors.append(
                        _diagnostic(
                            "invalid_evidence",
                            "/evidence",
                            "Evidence must preserve model provenance",
                        )
                    )
                cited.add(item["entity_id"])
            if cited != set(entities):
                errors.append(
                    _diagnostic(
                        "invalid_evidence", "/evidence", "Evidence must cover model entities"
                    )
                )
    for index, item in enumerate(result["evidence"]):
        expected = _evidence_identity(item["entity_id"], item["source_uri"])
        for field, value in expected.items():
            if item[field] != value:
                errors.append(
                    _diagnostic(
                        "invalid_evidence",
                        f"/evidence/{index}/{field}",
                        "Evidence identity and immutable ref must match its source",
                    )
                )
    identifiers = [item["id"] for item in result["evidence"]]
    if len(set(identifiers)) != len(identifiers):
        errors.append(_diagnostic("duplicate_evidence", "/evidence", "Duplicate evidence ID"))
    return errors


class GitProvider:
    """Delegate native metadata collection to the existing confined discovery API."""

    def describe(self):
        return {
            "schema_version": "1.0",
            "id": "git",
            "version": "1.0",
            "capabilities": [{"name": "discover", "read_only": True}],
        }

    def discover(self, *, manifest, base_dir, existing=None):
        model = discover(manifest, base_dir, existing)
        return _result(self.describe(), "discover", _request("discover", manifest, existing), model)


class MockProvider:
    """Replay an independent copy of a model, without provider-specific LSM data."""

    def __init__(self, model):
        self._model = deepcopy(model)

    def describe(self):
        return {
            "schema_version": "1.0",
            "id": "mock",
            "version": "1.0",
            "capabilities": [{"name": "discover", "read_only": True}],
        }

    def discover(self, *, manifest, base_dir, existing=None):
        # Validation precedes evidence extraction, including for malicious replay input.
        if validate_model(self._model):
            raise ValueError("Invalid replay model")
        return _result(
            self.describe(), "discover", _request("discover", manifest, existing), self._model
        )


def invoke(provider, capability, *, manifest, base_dir, existing=None) -> dict:
    """Fail closed on unsupported operations, invalid responses and trust promotions.

    Provider objects are trusted in-process code, not sandboxed plugins. Configuration
    never loads Python or supplies executable commands. All adapter inputs are copies.
    """
    fallback = {"id": "unknown", "version": "unknown"}
    digest = "0" * 64
    if not isinstance(capability, str) or not capability:
        return _result(fallback, "unsupported", digest, error="unsupported_capability")
    try:
        digest = _request(capability, manifest, existing)
        descriptor = deepcopy(provider.describe())
        descriptor_schema = _schema()["$defs"]["descriptor"]
        if list(Draft202012Validator(descriptor_schema).iter_errors(descriptor)):
            return _result(fallback, capability, digest, error="invalid_descriptor")
        fallback = descriptor
        if capability != "discover":
            return _result(fallback, capability, digest, error="unsupported_capability")
        # Validate manifests even for replay, without executing native discovery.
        manifest_schema = json.loads(
            files("lsm").joinpath("schemas/discovery.schema.json").read_text()
        )
        if list(Draft202012Validator(manifest_schema).iter_errors(manifest)):
            return _result(fallback, capability, digest, error="invalid_request")
        base = Path(base_dir).absolute()
        if not base.is_dir() or base.resolve() != base:
            return _result(fallback, capability, digest, error="invalid_request")
        for repository in manifest["repositories"]:
            current = base
            for part in Path(repository["path"]).parts:
                current = current / part
                if current.is_symlink():
                    return _result(fallback, capability, digest, error="invalid_request")
        if existing is not None and validate_model(existing):
            return _result(fallback, capability, digest, error="invalid_request")
        response = deepcopy(
            provider.discover(
                manifest=deepcopy(manifest), base_dir=base_dir, existing=deepcopy(existing)
            )
        )
        if validate_result(response):
            return _result(fallback, capability, digest, error="invalid_response")
        if (
            response["provider"] != {key: descriptor[key] for key in ("id", "version")}
            or response["capability"] != capability
            or response["request_digest"] != digest
        ):
            return _result(fallback, capability, digest, error="invalid_response")
        if response["data"] is not None:
            model = response["data"]["model"]
            if model["model"] != manifest["model"]:
                return _result(fallback, capability, digest, error="invalid_response")
            before = (
                existing
                if existing is not None
                else {
                    "schema_version": model["schema_version"],
                    "model": deepcopy(model["model"]),
                    "nodes": [],
                    "edges": [],
                }
            )
            try:
                check_transition(before, model, policy=None, actor="provider", actor_kind="agent")
            except ValueError:
                return _result(fallback, capability, digest, error="trust_transition_denied")
        # Do not publish untrusted adapter error strings (secrets or instructions).
        response["errors"] = [
            _diagnostic("provider_error", "", "Provider reported an incomplete request")
            for _ in response["errors"]
        ]
        return response
    except Exception:
        # Never leak exception text, paths, credentials or executable remediation.
        return _result(fallback, capability, digest, error="provider_failure")
