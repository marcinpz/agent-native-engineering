"""Fresh-directory integration through the actual public CLI, without skipped coverage."""

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
        "export",
        "requirement",
        "change",
        "context",
        "workflow",
        "benchmark",
    }
    record = json.loads((output / "execution.json").read_text())
    assert len(record["repositories"]) == 4
    assert record["reconciliation"]["verified"] is True
    assert json.loads((output / "questions.json").read_text())["state"] == "questions"
