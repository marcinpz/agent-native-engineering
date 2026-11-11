"""Read existing JUnit bytes only; source binding is an unauthenticated attestation."""

import hashlib
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException

from lsm.providers import _diagnostic, _digest, _now
from lsm.security import redact

MAX_BYTES = 2 * 1024 * 1024
MAX_ELEMENTS = 20000
MAX_DEPTH = 32


def import_junit(path, *, repository, commit):
    """Return a safe companion result, never execute tests or modify an LSM."""
    result = {
        "schema_version": "1.0",
        "provider": {"id": "junit", "version": "1.0"},
        "capability": "import_test_report",
        "status": "failed",
        "data": None,
        "errors": [],
        "permissions": {"source_access": "read", "writes_performed": False},
        "observed_at": _now(),
    }
    try:
        if not isinstance(repository, str) or not re.fullmatch(
            r"[a-z][a-z0-9_.:-]{0,199}", repository
        ):
            raise ValueError
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
            raise ValueError
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError
        # Only UTF-8 XML. Parser callbacks reject DTDs/entities/external refs;
        # comments and CDATA are ordinary XML, not declaration heuristics.
        text = raw.decode("utf-8-sig")
        if "\x00" in text:
            raise ValueError
        declaration = re.match(r"\s*<\?xml\s+([^?]*)\?>", text)
        if declaration and re.search(r"encoding\s*=\s*['\"](?!utf-8['\"])", declaration[1], re.I):
            raise ValueError
        root = SafeET.fromstring(text, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        if root.tag not in {"testsuite", "testsuites"}:
            raise ValueError
        artifact = hashlib.sha256(raw).hexdigest()
        binding = {"repository": repository, "commit": commit, "kind": "user_attestation"}
        identity = _digest({"artifact": artifact, "binding": binding})
        suites = []
        cases = []
        count = 0

        def visit(element, depth):
            nonlocal count
            count += 1
            if count > MAX_ELEMENTS or depth > MAX_DEPTH:
                raise ValueError
            for child in element:
                visit(child, depth + 1)

        visit(root, 0)

        def suite(element, location):
            start = len(cases)
            for index, child in enumerate(element):
                position = (*location, index)
                if child.tag in {"testsuite", "testsuites"}:
                    suite(child, position)
                elif child.tag == "testcase":
                    if element.tag != "testsuite" or not child.get("name", "").strip():
                        raise ValueError
                    # Dialect-specific status/result flags cannot silently turn
                    # unexecuted cases into passing cases.
                    if child.get("status", "run") != "run" or "result" in child.attrib:
                        raise ValueError
                    outcomes = [c.tag for c in child if c.tag in {"failure", "error", "skipped"}]
                    if len(outcomes) > 1:
                        raise ValueError
                    if any(
                        c.tag
                        not in {
                            "failure",
                            "error",
                            "skipped",
                            "system-out",
                            "system-err",
                            "properties",
                        }
                        for c in child
                    ):
                        raise ValueError
                    cases.append(
                        {
                            "id": "junit-case:"
                            + _digest({"report": identity, "position": position}),
                            "name": redact(child.get("name")[:500]),
                            "classname": redact(child.get("classname", "")[:500]),
                            "outcome": outcomes[0] if outcomes else "passed",
                        }
                    )
                elif child.tag not in {"properties", "system-out", "system-err"}:
                    raise ValueError
            subset = cases[start:]
            totals = {"tests": len(subset), "failures": 0, "errors": 0, "skipped": 0}
            for case in subset:
                key = {"failure": "failures", "error": "errors", "skipped": "skipped"}.get(
                    case["outcome"]
                )
                if key:
                    totals[key] += 1
            for key, value in totals.items():
                if key in element.attrib and (
                    not re.fullmatch(r"[0-9]+", element.attrib[key])
                    or int(element.attrib[key]) != value
                ):
                    raise ValueError
            suites.append(
                {
                    "position": list(location),
                    "name": redact(element.get("name", "")[:500]),
                    "outcome": (
                        "error"
                        if totals["errors"]
                        else "failure"
                        if totals["failures"]
                        else "empty"
                        if not subset
                        else "skipped"
                        if totals["skipped"] == len(subset)
                        else "passed"
                    ),
                    **totals,
                }
            )

        suite(root, ())
        if not cases:
            raise ValueError
        result["status"] = "succeeded"
        result["data"] = {
            "id": "junit-report:" + identity,
            "artifact_sha256": artifact,
            "source_ref": "sha256:" + artifact,
            "binding": binding,
            "origin": "observed",
            "verification": "unverified",
            "confidence": None,
            "suites": suites,
            "cases": cases,
        }
    except (OSError, ValueError, ET.ParseError, DefusedXmlException, RecursionError):
        result["errors"] = [_diagnostic("invalid_report", "", "JUnit report or binding rejected")]
    return result
