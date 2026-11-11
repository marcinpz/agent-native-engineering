"""Explicit local authorization and best-effort projection redaction.

Actor names are local attestations, not authenticated remote identities. Redaction
is defense in depth, not a secret scanner or a sandbox for untrusted programs.
"""

import copy
import re

_SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|secret|token|api[_-]?key|authorization|credential|private[_-]?key)",
    re.IGNORECASE,
)
_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{8,}|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{8,})\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"(?i)(?:password|passwd|secret|token|api[_-]?key|credential)\s*[=:]\s*[^\s&;,]+"),
    re.compile(r"(?i)https?://[^\s/@]+:[^\s/@]+@"),
]
_ACTIONS = {"approve_requirements", "approve_changes", "verify"}


def redact(value):
    """Return a copy with sensitive keys and recognizable secret strings removed."""
    if isinstance(value, dict):
        return {
            _redact_string(str(key)): "[REDACTED]"
            if _SENSITIVE_KEY.search(str(key))
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _redact_string(value):
    for pattern in _PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value


def require_authorization(policy, actor, action, actor_kind="human"):
    """Deny by default; explicit named human grants are required for transitions."""
    if not isinstance(policy, dict) or set(policy) != {"version", "humans", "permissions"}:
        raise ValueError("Policy requires only version, humans and permissions")
    humans, permissions = policy["humans"], policy["permissions"]
    if (
        policy["version"] != "1.0"
        or not isinstance(humans, list)
        or not all(isinstance(item, str) and item.strip() for item in humans)
        or len(humans) != len(set(humans))
        or not isinstance(permissions, dict)
        or not set(permissions) <= _ACTIONS
    ):
        raise ValueError("Malformed authorization policy")
    for grants in permissions.values():
        if (
            not isinstance(grants, list)
            or not all(isinstance(item, str) and item in humans for item in grants)
            or len(grants) != len(set(grants))
        ):
            raise ValueError("Policy grants must name unique declared human actors")
    if (
        actor_kind != "human"
        or not isinstance(actor, str)
        or actor not in humans
        or action not in _ACTIONS
        or actor not in permissions.get(action, [])
    ):
        raise ValueError(
            f"Authorization denied for action {action!r}; explicit human grant required"
        )


def check_transition(before, after, policy, actor, actor_kind="human"):
    """Authorize promotions and edits of previously approved/verified entities.

    Imported files remain untrusted declarations. This gate applies to changes
    performed through platform transition APIs, not arbitrary filesystem writes.
    """
    from lsm.validation import validate_model

    for model in (before, after):
        if validate_model(model):
            raise ValueError("Trust transition requires valid before and after models")
    if before["model"]["id"] != after["model"]["id"]:
        raise ValueError("Trust transition cannot change model identity")
    old = {item["id"]: item for item in before["nodes"] + before["edges"]}
    new = {item["id"]: item for item in after["nodes"] + after["edges"]}
    required = set()
    for identifier in old.keys() | new.keys():
        previous, current = old.get(identifier, {}), new.get(identifier, {})
        if previous == current:
            continue
        if any(
            item.get("provenance", {}).get("verification") == "verified"
            for item in (previous, current)
        ):
            required.add("verify")
        if any(
            item.get("type") == "requirement" and item.get("approval") == "approved"
            for item in (previous, current)
        ):
            required.add("approve_requirements")
    for action in sorted(required):
        require_authorization(policy, actor, action, actor_kind)
    return copy.deepcopy(after)
