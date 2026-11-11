"""Archive completed local synthetic trials; never execute an agent or alter a trial."""

import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALUATOR = Path("/tmp/opencode/ane-pilot-evaluator")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def counts(path):
    root = ET.parse(path).getroot()
    return {
        key: sum(int(s.get(key, 0)) for s in root.iter("testsuite"))
        for key in ("tests", "failures", "errors", "skipped")
    }


def main():
    output = HERE / "results"
    output.mkdir(exist_ok=False)
    prep = json.loads((HERE / "preparation.json").read_text())
    summary = []
    for name, expected in prep["heldout_sha256"].items():
        assert sha((EVALUATOR / name).read_bytes()) == expected
        assert sha((HERE / name).read_bytes()) == expected
    for trial in prep["trials"]:
        repo = Path(trial["directory"])
        name = repo.name
        dest = output / name
        dest.mkdir()
        for filename in ("TASK.md", "README.md", "test_public.py"):
            assert sha((repo / filename).read_bytes()) == trial["hashes"][filename]
        if "CONTEXT.json" in trial["hashes"]:
            assert sha((repo / "CONTEXT.json").read_bytes()) == trial["hashes"]["CONTEXT.json"]
        files = {
            p.relative_to(repo).as_posix(): p.read_text()
            for p in sorted(repo.rglob("*"))
            if p.is_file()
            and not any(
                x in p.relative_to(repo).parts for x in (".git", "__pycache__", ".pytest_cache")
            )
        }
        (dest / "snapshot.json").write_text(json.dumps(files, indent=2) + "\n")
        metrics = json.loads((EVALUATOR / f"{name}-metrics.json").read_text())
        assert metrics["model"] == dict(id="gpt-6.1-sol", providerID="openai", variant="low")
        (dest / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
        shutil.copytree(EVALUATOR / "results" / name, dest / "evaluation")
        checks = {}
        for suite in ("public", "heldout"):
            folder = dest / "evaluation" / suite
            command = json.loads((folder / "command.json").read_text())
            assert command["returncode"] == 0
            checks[suite] = counts(folder / "junit.xml")
            assert checks[suite]["failures"] == checks[suite]["errors"] == 0
        tokens = metrics["tokens_reported_by_harness"]
        summary.append(
            dict(
                run=name,
                checks=checks,
                original_inputs_unchanged=True,
                file_sha256={n: sha(v.encode()) for n, v in files.items()},
                added_files=sorted(set(files) - set(trial["hashes"])),
                cumulative_input_exposure=tokens["input"] + tokens["cache"]["read"],
                output=tokens["output"],
                actual_cost_usd=None,
            )
        )
    shutil.copyfile(
        "/tmp/opencode/ane-pilot-preparation-session.json", output / "preparation-session.json"
    )
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
