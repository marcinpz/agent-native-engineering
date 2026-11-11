"""Offline smoke measurements and pure aggregation of supplied paired trials.

No agents, subprocesses, network calls or paid experiments are invoked here.
"""

import json
import math
from collections import defaultdict
from importlib.resources import files
from time import perf_counter

from jsonschema import Draft202012Validator

from lsm.security import redact
from lsm.validation import validate_model


def _json(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nonfinite numbers are not permitted")
    if isinstance(value, dict):
        for item in value.values():
            _finite(item)
    elif isinstance(value, list):
        for item in value:
            _finite(item)


def _sum(values):
    try:
        result = math.fsum(values)
    except (OverflowError, ValueError):
        raise ValueError("Metrics exceed finite accounting range") from None
    if not math.isfinite(result):
        raise ValueError("Metrics exceed finite accounting range")
    return result


def _public(value):
    # Redact strings individually: shared redact treats metric names such as
    # tokens_input as sensitive keys, but these numeric measurements are public.
    if isinstance(value, dict):
        return {redact(key): _public(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_public(item) for item in value]
    return redact(value) if isinstance(value, str) else value


def run_smoke(model: dict, task: str, seed_ids: list[str], budget: int = 8192) -> dict:
    """Measure one local preparation per arm, not agent performance or real tokens."""
    _finite(model)
    if validate_model(model):
        raise ValueError("Smoke requires a valid model")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("Task must be a nonempty string")
    if (
        not isinstance(seed_ids, list)
        or not seed_ids
        or any(not isinstance(seed, str) or not seed.strip() for seed in seed_ids)
        or len(seed_ids) != len(set(seed_ids))
        or not set(seed_ids) <= {node["id"] for node in model["nodes"]}
    ):
        raise ValueError("Seeds must be unique existing node IDs")
    if type(budget) is not int or budget <= 0:
        raise ValueError("Budget must be a positive integer")

    # Import outside the timed interval: measure preparation, not module loading.
    from lsm.context import compile_context

    start = perf_counter()
    baseline = _json(redact({"model": model, "task": task, "seed_ids": seed_ids}))
    baseline_seconds = perf_counter() - start
    start = perf_counter()
    compiled = _json(_public(compile_context(model, task, seed_ids, budget)))
    compiled_seconds = perf_counter() - start

    def measurement(text, seconds):
        size = len(text.encode("utf-8"))
        return {
            "context_bytes": size,
            "token_proxy_bytes_div_4": (size + 3) // 4,
            "preparation_seconds": seconds,
            "pass_at_1": None,
            "tokens_input": None,
            "tokens_output": None,
            "cost_usd": None,
            "agent_latency_seconds": None,
            "repair_iterations": None,
            "impact_recall": None,
            "onboarding_accuracy": None,
        }

    return _public(
        {
            "schema_version": "1.0",
            "kind": "deterministic_smoke",
            "agent_outcome_measured": False,
            "task": task,
            "seed_ids": seed_ids,
            "budget": budget,
            "model_id": model["model"]["id"],
            "measurement_order": ["baseline", "lsm"],
            "arms": {
                "baseline": measurement(baseline, baseline_seconds),
                "lsm": measurement(compiled, compiled_seconds),
            },
            "limitations": [
                "One local preparation per arm; timing varies with machine and cache state.",
                "Whole-model baseline is not truncated to the compiler budget.",
                "Byte/4 proxy is not tokenizer usage; no agent outcome measured.",
                "No scientific comparison, speedup or paid-agent result is claimed.",
            ],
        }
    )


def summarize_trials(document: dict) -> dict:
    """Validate and summarize supplied agent records; never execute or verify them."""
    _finite(document)
    schema = json.loads(files("lsm").joinpath("schemas/benchmark.schema.json").read_text())
    if not Draft202012Validator(schema).is_valid(document):
        raise ValueError("Invalid agent trial document (smoke records are not agent trials)")
    seen = set()
    pairs = defaultdict(lambda: defaultdict(list))
    for trial in document["trials"]:
        if trial["run_id"] in seen:
            raise ValueError("Duplicate run ID")
        seen.add(trial["run_id"])
        pairs[trial["pair_id"]][trial["arm"]].append(trial)
    matched_fields = ("task", "model_revision", "budget", "seed")
    for arms in pairs.values():
        if set(arms) != {"baseline", "lsm"}:
            raise ValueError("Every pair requires baseline and lsm arms")
        reference = arms["baseline"][0]
        for records in arms.values():
            records.sort(key=lambda record: record["attempt"])
            if [record["attempt"] for record in records] != list(range(1, len(records) + 1)):
                raise ValueError("Attempts must be unique and contiguous starting at one")
            for record in records:
                if any(record[field] != reference[field] for field in matched_fields):
                    raise ValueError("Paired task, model revision, budget and seed must match")
        if len(arms["baseline"]) != len(arms["lsm"]):
            raise ValueError("Paired arms require matching attempt sets")

    summary = {}
    for arm in ("baseline", "lsm"):
        groups = [arms[arm] for _, arms in sorted(pairs.items())]
        records = [record for group in groups for record in group]
        complete = [group for group in groups if all(r["cost_usd"] is not None for r in group)]
        successful_groups = sum(any(r["success"] for r in group) for group in complete)
        total_cost = _sum(r["cost_usd"] for group in complete for r in group)
        metrics = {}
        for field in (
            "tokens_input",
            "tokens_output",
            "cost_usd",
            "latency_seconds",
            "repair_iterations",
            "impact_recall",
            "onboarding_accuracy",
        ):
            known = [record[field] for record in records if record.get(field) is not None]
            total = _sum(known)
            metrics[field] = {
                "known_count": len(known),
                "unknown_count": len(records) - len(known),
                "mean": total / len(known) if known else None,
                "sum": total if known else None,
            }
        summary[arm] = {
            "attempt_count": len(records),
            "first_attempt_count": len(groups),
            "first_attempt_successes": sum(group[0]["success"] for group in groups),
            "pass_at_1": sum(group[0]["success"] for group in groups) / len(groups),
            "metrics": metrics,
            "verified_cost_accounting": {
                "included_pair_count": len(complete),
                "excluded_unknown_cost_pair_count": len(groups) - len(complete),
                "verified_success_count": successful_groups,
                "known_total_cost_usd": total_cost if complete else None,
                "cost_per_verified_success_usd": (
                    total_cost / successful_groups if successful_groups else None
                ),
            },
        }
    result = {
        "schema_version": "1.0",
        "kind": "agent_trial_summary",
        "data_origin": document["data_origin"],
        "pair_count": len(pairs),
        "arms": summary,
        "verification": (
            "Supplied independent verification references; not authenticated or executed."
        ),
        "claims": "Descriptive aggregation only; no causal or statistical significance claim.",
    }
    _finite(result)
    return _public(result)
