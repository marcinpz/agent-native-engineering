"""Fresh-directory integration through the actual public CLI, without skipped coverage."""

import html
import json
import subprocess
import sys
from pathlib import Path


def test_complete_cli_walkthrough(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "walkthrough"
    result = subprocess.run(
        [sys.executable, str(root / "scripts/roadmap_smoke.py"), "--output-dir", str(output)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["ok"] is True
    assert summary["retained"] is True
    assert summary["github_pr"] is None
    assert summary["agent_experiments"] == "pending"
    steps = json.loads((output / "steps.json").read_text())
    assert summary["cli_steps"] == len(steps)
    assert all(step["exit_code"] == 0 for step in steps)
    assert {step["command"][3] for step in steps} >= {
        "migrate",
        "discover",
        "validate",
        "inspect",
        "export",
        "requirement",
        "change",
        "context",
        "context-compare",
        "workflow",
        "benchmark",
    }
    record = json.loads((output / "execution.json").read_text())
    assert len(record["repositories"]) == 4
    assert record["reconciliation"]["verified"] is True
    assert json.loads((output / "questions.json").read_text())["state"] == "questions"
    comparison = json.loads((output / "repository-comparison.json").read_text())
    assert comparison["baseline"]["utf8_bytes"] == len(
        (output / "whole-repository-baseline.txt").read_bytes()
    )
    assert comparison["agent_outcome_measured"] is False
    requirement = json.loads((output / "inspected-requirement.json").read_text())
    assert requirement["approval"] == "pending"
    assert requirement["provenance"]["origin"] == "declared"
    implementation = json.loads((output / "inspected-implementation.json").read_text())
    assert implementation["provenance"]["origin"] == "inferred"
    assert implementation["provenance"]["verification"] == "unverified"
    trace = html.unescape((output / "docs" / "traceability.md").read_text())
    assert "implementation.demo-sync" in trace
    assert "test.demo-sync" in trace
