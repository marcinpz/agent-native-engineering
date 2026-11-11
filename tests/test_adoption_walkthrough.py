"""Actual CLI proof on synthetic Java and non-Java projects, not app execution."""

import json
import subprocess
import sys
from pathlib import Path


def test_read_only_adoption_walkthrough(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "adoption"
    result = subprocess.run(
        [sys.executable, str(root / "scripts/adoption_smoke.py"), "--output-dir", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["ok"] and summary["source_bytes_unchanged"]
    assert summary["git_heads_unchanged_by_ane"] and summary["retained"]
    assert set(summary["fixtures"]) == {"spring", "python"}
    assert summary["application_builds_executed"] is False
    assert summary["application_tests_executed"] is False
    assert summary["migration_executed"] is False and summary["cloud_accessed"] is False
    assert summary["preparation_seconds"] >= summary["cli_seconds"] > 0
    assert summary["agent_model_invocations"] == 0
    assert summary["provider_tokens"] is None and summary["cost_usd"] is None
    steps = json.loads((output / "steps.json").read_text())
    assert summary["cli_steps"] == len(steps)
    assert all(step["exit_code"] == 0 for step in steps)
    assert {step["command"][3] for step in steps} == {"provider", "workspace"}
    assert not (output / "sources/python-service/.ane").exists()
    model = json.loads((output / "orchestration/.ane/model.json").read_text())
    assert all(node["provenance"]["verification"] == "unverified" for node in model["nodes"])
    assert (output / "orchestration/.ane/docs/index.md").exists()
    assert (output / "orchestration/.ane/context.json").exists()
    assert (
        "adoption-probe-not-a-real-secret"
        not in (output / "orchestration/.ane/context.json").read_text()
    )
