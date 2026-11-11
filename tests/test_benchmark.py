"""Aggregation numbers below are SYNTHETIC fixtures, not experimental results."""

import copy
import json
from pathlib import Path

import pytest

from lsm.benchmark import run_smoke, summarize_trials

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def trials():
    records = []
    for pair in range(2):
        for arm in ("baseline", "lsm"):
            for attempt in (1, 2):
                records.append(
                    {
                        "kind": "agent_trial",
                        "run_id": f"synthetic-{pair}-{arm}-{attempt}",
                        "pair_id": f"synthetic-{pair}",
                        "arm": arm,
                        "task": "Synthetic maintenance task",
                        "model_revision": "synthetic-revision",
                        "budget": 8192,
                        "seed": pair,
                        "attempt": attempt,
                        "success": arm == "lsm" or attempt == 2,
                        "verification_ref": "fixture://not-real-evidence",
                        "tokens_input": 100,
                        "tokens_output": None,
                        "cost_usd": None if pair == 1 and attempt == 2 else 0.1,
                        "latency_seconds": 2.0,
                        "repair_iterations": attempt - 1,
                        "impact_recall": 0.5,
                    }
                )
    return {
        "schema_version": "1.0",
        "kind": "agent_trials",
        "data_origin": "synthetic_fixture",
        "trials": records,
    }


def test_synthetic_summary(trials):
    before = copy.deepcopy(trials)
    summary = summarize_trials(trials)
    assert trials == before
    assert summary["data_origin"] == "synthetic_fixture"
    assert summary["pair_count"] == 2
    assert summary["arms"]["baseline"]["pass_at_1"] == 0
    assert summary["arms"]["lsm"]["pass_at_1"] == 1
    for arm in summary["arms"].values():
        assert arm["attempt_count"] == 4
        assert arm["first_attempt_count"] == 2
        assert arm["metrics"]["tokens_input"] == {
            "known_count": 4,
            "unknown_count": 0,
            "mean": 100.0,
            "sum": 400.0,
        }
        assert arm["metrics"]["tokens_output"]["mean"] is None
        assert arm["metrics"]["onboarding_accuracy"]["unknown_count"] == 4
        assert arm["verified_cost_accounting"] == {
            "included_pair_count": 1,
            "excluded_unknown_cost_pair_count": 1,
            "verified_success_count": 1,
            "known_total_cost_usd": 0.2,
            "cost_per_verified_success_usd": 0.2,
        }
    trials["trials"].reverse()
    assert summarize_trials(trials) == summary


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cost_usd", -1),
        ("cost_usd", float("nan")),
        ("latency_seconds", float("inf")),
        ("tokens_input", -1),
        ("tokens_output", 1.5),
        ("repair_iterations", True),
        ("impact_recall", 1.1),
        ("onboarding_accuracy", -0.1),
        ("success", "yes"),
        ("attempt", 0),
        ("budget", False),
        ("seed", -1),
        ("task", " "),
        ("kind", "deterministic_smoke"),
    ],
)
def test_malformed_metrics_rejected(trials, field, value):
    trials["trials"][0][field] = value
    with pytest.raises(ValueError):
        summarize_trials(trials)


@pytest.mark.parametrize("field", ["task", "model_revision", "budget", "seed"])
def test_unmatched_metadata_rejected(trials, field):
    trials["trials"][2][field] = 123 if field in ("budget", "seed") else "different"
    with pytest.raises(ValueError, match="must match"):
        summarize_trials(trials)


def test_duplicate_and_missing_arms_attempts(trials):
    duplicate = copy.deepcopy(trials)
    duplicate["trials"][1]["run_id"] = duplicate["trials"][0]["run_id"]
    with pytest.raises(ValueError, match="Duplicate run ID"):
        summarize_trials(duplicate)
    missing = copy.deepcopy(trials)
    missing["trials"] = missing["trials"][:2]
    with pytest.raises(ValueError, match="requires baseline"):
        summarize_trials(missing)
    missing["trials"] = trials["trials"][:-1]
    with pytest.raises(ValueError, match="matching attempt sets"):
        summarize_trials(missing)
    trials["trials"][1]["attempt"] = 1
    with pytest.raises(ValueError, match="unique and contiguous"):
        summarize_trials(trials)


@pytest.mark.parametrize("reference", [None, "", "   "])
def test_success_requires_independent_verification_reference(trials, reference):
    trials["trials"][1]["verification_ref"] = reference
    with pytest.raises(ValueError):
        summarize_trials(trials)


def test_unknown_costs_and_no_success(trials):
    for trial in trials["trials"]:
        trial["success"] = False
        trial["verification_ref"] = None
        trial["cost_usd"] = None
    for arm in summarize_trials(trials)["arms"].values():
        assert arm["pass_at_1"] == 0
        assert arm["verified_cost_accounting"]["included_pair_count"] == 0
        assert arm["verified_cost_accounting"]["known_total_cost_usd"] is None
        assert arm["verified_cost_accounting"]["cost_per_verified_success_usd"] is None


def test_accounting_overflow_rejected(trials):
    for trial in trials["trials"]:
        trial["cost_usd"] = 1e308
    with pytest.raises(ValueError, match="finite accounting range"):
        summarize_trials(trials)


def test_unknown_and_boolean_metrics_rejected(trials):
    trials["trials"][0]["unexpected"] = 1
    with pytest.raises(ValueError):
        summarize_trials(trials)
    del trials["trials"][0]["unexpected"]
    trials["trials"][0]["cost_usd"] = True
    with pytest.raises(ValueError):
        summarize_trials(trials)


def test_summary_never_publishes_raw_metadata(trials):
    secret = "ghp_" + "A" * 36
    for trial in trials["trials"]:
        trial["task"] = "password=example " + secret
        trial["verification_ref"] = "https://user:password@example.invalid/" + secret
    assert secret not in json.dumps(summarize_trials(trials))
    assert "password=example" not in json.dumps(summarize_trials(trials))


def test_actual_local_smoke():
    shop = json.loads((ROOT / "examples/shop.json").read_text())
    before = copy.deepcopy(shop)
    result = run_smoke(shop, "Inspect backend dependencies", ["component.backend"])
    assert shop == before
    assert result["kind"] == "deterministic_smoke"
    assert result["agent_outcome_measured"] is False
    assert result["budget"] == 8192
    for arm in result["arms"].values():
        assert arm["context_bytes"] > 0
        assert arm["token_proxy_bytes_div_4"] == (arm["context_bytes"] + 3) // 4
        assert arm["preparation_seconds"] >= 0
        for field in (
            "pass_at_1",
            "tokens_input",
            "tokens_output",
            "cost_usd",
            "repair_iterations",
            "impact_recall",
            "onboarding_accuracy",
        ):
            assert arm[field] is None
    with pytest.raises(ValueError, match="smoke records"):
        summarize_trials(result)


def test_smoke_redaction_and_deterministic_nontiming_fields():
    shop = json.loads((ROOT / "examples/shop.json").read_text())
    secret = "ghp_" + "A" * 36
    task = "password=example " + secret
    results = [run_smoke(shop, task, ["component.backend"]) for _ in range(2)]
    for result in results:
        assert secret not in json.dumps(result)
        assert "password=example" not in json.dumps(result)
        for arm in result["arms"].values():
            arm.pop("preparation_seconds")
    assert results[0] == results[1]


def test_smoke_measures_real_preparation_and_serialization(monkeypatch):
    from lsm.benchmark import _json
    from lsm.context import compile_context
    from lsm.security import redact

    shop = json.loads((ROOT / "examples/shop.json").read_text())
    clock = iter([1.0, 1.25, 2.0, 2.5])
    monkeypatch.setattr("lsm.benchmark.perf_counter", lambda: next(clock))
    result = run_smoke(shop, "Inspect backend", ["component.backend"])
    expected_baseline = redact(
        {"model": shop, "task": "Inspect backend", "seed_ids": ["component.backend"]}
    )
    expected_compiled = compile_context(shop, "Inspect backend", ["component.backend"], 8192)
    assert result["arms"]["baseline"]["context_bytes"] == len(
        _json(expected_baseline).encode("utf-8")
    )
    assert result["arms"]["lsm"]["context_bytes"] == len(_json(expected_compiled).encode("utf-8"))
    assert result["arms"]["baseline"]["preparation_seconds"] == 0.25
    assert result["arms"]["lsm"]["preparation_seconds"] == 0.5


@pytest.mark.parametrize(
    ("task", "seeds", "budget"),
    [
        ("", ["component.backend"], 8192),
        ("task", [], 8192),
        ("task", ["missing"], 8192),
        ("task", ["component.backend"], 0),
        ("task", ["component.backend"], True),
        ("task", ["component.backend", "component.backend"], 8192),
    ],
)
def test_invalid_smoke_arguments(task, seeds, budget):
    shop = json.loads((ROOT / "examples/shop.json").read_text())
    with pytest.raises(ValueError):
        run_smoke(shop, task, seeds, budget)


@pytest.mark.parametrize("document", [None, {}, [], {"kind": "deterministic_smoke"}])
def test_invalid_trial_documents(document):
    with pytest.raises(ValueError):
        summarize_trials(document)


def test_invalid_smoke_model():
    with pytest.raises(ValueError, match="valid model"):
        run_smoke({}, "task", ["component.backend"])
