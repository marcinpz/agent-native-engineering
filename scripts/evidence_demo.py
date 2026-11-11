"""Run a fixed fixture in the demo harness, then read/evaluate its report."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from lsm.evidence import evaluate_junit
from lsm.junit import import_junit
from lsm.storage import load_model


def main():
    model = load_model(Path(__file__).resolve().parents[1] / "examples/shop.json")
    with tempfile.TemporaryDirectory(prefix="lsm-evidence-") as directory:
        root = Path(directory)
        fixture = root / "test_fixture.py"
        fixture.write_text(
            "import pytest\ndef test_pass(): assert True\ndef test_fail(): assert False\n"
            "@pytest.mark.skip(reason='fixture')\ndef test_skip(): pass\n"
        )
        path = root / "report.xml"
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-c",
                "/dev/null",
                str(fixture),
                f"--junitxml={path}",
            ],
            cwd=root,
            capture_output=True,
            check=False,
        )
        assert process.returncode == 1
        before = (fixture.read_bytes(), path.read_bytes())
        report = import_junit(path, repository="repo.backend", commit="a" * 40)
        assert report["status"] == "succeeded"
        mapping = {
            "schema_version": "1.0",
            "report_id": report["data"]["id"],
            "mappings": [
                {
                    "case_id": case["id"],
                    "test_id": "test.notes",
                    "requirement_ids": ["requirement.notes"],
                }
                for case in report["data"]["cases"]
            ],
        }
        result = evaluate_junit(
            path,
            model=model,
            mapping=mapping,
            repository="repo.backend",
            commit="a" * 40,
            expected_commit="b" * 40,
        )
        assert result["status"] == "succeeded"
        assert result["data"]["freshness"] == "stale"
        assert result["data"]["tests"][0]["outcome"] == "failed"
        assert {case["outcome"] for case in result["data"]["tests"][0]["cases"]} == {
            "passed",
            "failed",
            "skipped",
        }
        assert before == (fixture.read_bytes(), path.read_bytes())
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
