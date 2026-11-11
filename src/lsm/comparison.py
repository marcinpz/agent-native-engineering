"""Measure task context against an explicitly supplied, curated repository baseline."""

from lsm.context import compile_context, serialize_context
from lsm.security import redact


def compare_repository_context(model, task, seed_ids, baseline_text, budget=8192):
    """Compare bytes only; a caller supplies/attests baseline completeness.

    This API never opens source files, scans a repository or invokes an agent.
    A full-repository baseline is deliberately not truncated to the pack budget;
    this is not a fair equal-budget agent-quality or billed-token experiment.
    """
    if not isinstance(baseline_text, str) or not baseline_text.strip():
        raise ValueError("Repository comparison requires nonempty curated baseline text")
    pack = compile_context(model, task, seed_ids, budget)
    naive_bytes = len(redact(baseline_text).encode("utf-8"))
    pack_bytes = len(serialize_context(pack).encode("utf-8"))
    return {
        "schema_version": "1.0",
        "kind": "repository_context_size_comparison",
        "baseline": {
            "scope": "caller_supplied_repository_sources",
            "utf8_bytes": naive_bytes,
            "completeness": "caller_attestation_not_verified",
        },
        "compiled_context": {"utf8_bytes": pack_bytes, "budget_proxy_bytes": budget},
        "byte_difference": naive_bytes - pack_bytes,
        "agent_outcome_measured": False,
        "provider_tokens": None,
        "cost_usd": None,
        "limitations": [
            "Baseline completeness and curation are the caller's responsibility.",
            "Full-source baseline and bounded context are not an equal-budget quality experiment.",
            "A cited context pack may be larger than a tiny repository; no improvement is assumed.",
        ],
    }
