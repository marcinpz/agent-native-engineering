import json

import pytest

from lsm.cli import main
from lsm.comparison import compare_repository_context
from lsm.storage import load_model


def test_curated_whole_repo_size_comparison_and_no_mutation():
    model = load_model("examples/shop.json")
    baseline = "# complete tiny repo\nprint('hello')\n"
    result = compare_repository_context(model, "Inspect", ["component.backend"], baseline)
    assert result["baseline"]["utf8_bytes"] == len(baseline.encode())
    assert result["compiled_context"]["utf8_bytes"] <= 8192
    assert result["byte_difference"] < 0  # Do not assume the model context is smaller.
    assert result["agent_outcome_measured"] is False
    assert result["provider_tokens"] is None
    assert "print('hello')" not in json.dumps(result)


def test_baseline_secret_redaction_and_invalid_input():
    model = load_model("examples/shop.json")
    result = compare_repository_context(
        model, "Inspect", ["component.backend"], 'password="do not publish this value"'
    )
    assert "do not publish" not in str(result)
    assert result["baseline"]["utf8_bytes"] == len('password="[REDACTED]"')
    with pytest.raises(ValueError):
        compare_repository_context(model, "Inspect", ["component.backend"], "")


def test_comparison_cli(tmp_path, capsys):
    baseline = tmp_path / "sources.txt"
    baseline.write_text("print('tiny repository')\n")
    assert (
        main(
            [
                "context-compare",
                "examples/shop.json",
                "--task",
                "Inspect",
                "--seed",
                "component.backend",
                "--baseline",
                str(baseline),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["baseline"]["utf8_bytes"] == len(baseline.read_bytes())
    assert (
        main(
            [
                "context-compare",
                "examples/shop.json",
                "--task",
                "Inspect",
                "--seed",
                "component.backend",
                "--baseline",
                str(tmp_path / "missing.txt"),
            ]
        )
        == 2
    )
