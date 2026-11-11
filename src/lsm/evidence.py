"""Read-only explicit JUnit-to-LSM evaluation; never a trust transition."""

import re

from lsm.junit import import_junit
from lsm.providers import _diagnostic, _digest
from lsm.security import redact
from lsm.validation import validate_model


def _outcome(values):
    return next(
        (v for v in ("error", "failed", "missing", "skipped", "passed") if v in values),
        "missing",
    )


def evaluate_junit(path, *, model, mapping, repository, commit, expected_commit):
    """Import existing bytes and join explicit case/test/requirement identities.

    Success means valid evaluation, not passing tests. Bindings are attestations.
    No input mutation, execution, approval or verification is performed.
    """
    result = import_junit(path, repository=repository, commit=commit)
    result["capability"] = "evaluate_test_evidence"
    if result["status"] != "succeeded":
        return result
    report = result["data"]
    result["status"] = "failed"
    result["data"] = None
    try:
        if not isinstance(expected_commit, str) or not re.fullmatch(
            r"[0-9a-f]{40}|[0-9a-f]{64}", expected_commit
        ):
            raise ValueError
        if validate_model(model):
            raise ValueError
        nodes = {node["id"]: node for node in model["nodes"]}
        if nodes.get(repository, {}).get("type") != "repository":
            raise ValueError
        if not isinstance(mapping, dict) or set(mapping) != {
            "schema_version",
            "report_id",
            "mappings",
        }:
            raise ValueError
        if mapping["schema_version"] != "1.0" or mapping["report_id"] != report["id"]:
            raise ValueError
        if not isinstance(mapping["mappings"], list) or not mapping["mappings"]:
            raise ValueError
        cases = {case["id"]: case for case in report["cases"]}
        seen = set()
        tests = {}
        for entry in mapping["mappings"]:
            if not isinstance(entry, dict) or set(entry) != {
                "case_id",
                "test_id",
                "requirement_ids",
            }:
                raise ValueError
            case_id, test_id, requirements = (
                entry["case_id"],
                entry["test_id"],
                entry["requirement_ids"],
            )
            if not isinstance(test_id, str) or nodes.get(test_id, {}).get("type") != "test":
                raise ValueError
            if (
                not isinstance(requirements, list)
                or not requirements
                or any(not isinstance(item, str) for item in requirements)
                or len(set(requirements)) != len(requirements)
                or any(nodes.get(item, {}).get("type") != "requirement" for item in requirements)
            ):
                raise ValueError
            if case_id is not None and (
                not isinstance(case_id, str) or case_id not in cases or case_id in seen
            ):
                raise ValueError
            if case_id is not None:
                seen.add(case_id)
            test = tests.setdefault(test_id, {"cases": [], "requirements": set()})
            test["requirements"].update(requirements)
            outcome = cases[case_id]["outcome"] if case_id is not None else "missing"
            test["cases"].append(
                {"case_id": case_id, "outcome": "failed" if outcome == "failure" else outcome}
            )
        test_rows = [
            {
                "test_id": test_id,
                "requirement_ids": sorted(test["requirements"]),
                "cases": test["cases"],
                "outcome": _outcome([case["outcome"] for case in test["cases"]]),
            }
            for test_id, test in sorted(tests.items())
        ]
        requirements = []
        for node_id, node in sorted(nodes.items()):
            if node["type"] != "requirement":
                continue
            linked = [test for test in test_rows if node_id in test["requirement_ids"]]
            requirements.append(
                {
                    "requirement_id": node_id,
                    "test_ids": [test["test_id"] for test in linked],
                    "mapped_test_outcome": _outcome([test["outcome"] for test in linked]),
                    "coverage": "unknown",
                    "verification": "unverified",
                }
            )
        result["data"] = redact(
            {
                "report_id": report["id"],
                "source_ref": report["source_ref"],
                "binding": report["binding"],
                "expected_commit": expected_commit,
                "freshness": "current" if commit == expected_commit else "stale",
                "model_digest": _digest(model),
                "mapping_digest": _digest(mapping),
                "origin": "observed",
                "verification": "unverified",
                "confidence": None,
                "tests": test_rows,
                "requirements": requirements,
                "unmapped_case_count": len(cases) - len(seen),
            }
        )
        result["status"] = "succeeded"
    except (ValueError, TypeError, KeyError):
        result["errors"] = [
            _diagnostic("invalid_mapping", "", "Model, mapping or expected commit rejected")
        ]
    return result
