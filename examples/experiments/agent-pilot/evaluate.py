"""Coordinator-only grading; never copy into trial repositories."""

import json
import os
import subprocess
import sys
from pathlib import Path


def run(repo, tests, output):
    output.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        str(tests),
        "--junitxml=" + str(output / "junit.xml"),
    ]
    env = dict(os.environ, PYTHONPATH=str(repo), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(command, cwd=repo, env=env, capture_output=True, text=True)
    record = dict(
        command=command,
        cwd=str(repo),
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
    (output / "command.json").write_text(json.dumps(record, indent=2) + "\n")
    return result.returncode


if __name__ == "__main__":
    repo = Path(sys.argv[1]).resolve()
    task = sys.argv[2]
    output = Path(sys.argv[3]).resolve()
    public = run(repo, repo / "test_public.py", output / "public")
    heldout = run(repo, Path(__file__).parent / f"accept_{task}.py", output / "heldout")
    print(json.dumps(dict(public=public, heldout=heldout)))
    sys.exit(bool(public or heldout))
