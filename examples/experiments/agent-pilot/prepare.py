"""Prepare pinned isolated repositories, compile context, and check baselines."""

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from lsm.context import compile_context, serialize_context, validate_context
from lsm.validation import validate_model

HERE = Path(__file__).resolve().parent
RUNS = Path("/tmp/opencode/ane-pilot-runs")
EVALUATOR = Path("/tmp/opencode/ane-pilot-evaluator")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    setup_start = time.perf_counter()
    if RUNS.exists() or EVALUATOR.exists():
        raise SystemExit("Refusing existing run/evaluator directories")
    EVALUATOR.mkdir()
    for name in ("evaluate.py", "accept_cancel.py", "accept_pagination.py"):
        shutil.copyfile(HERE / name, EVALUATOR / name)
    from evaluate import run

    fixtures = json.loads((HERE / "fixtures.json").read_text())
    record = {
        "python": sys.version,
        "platform": platform.platform(),
        "trials": [],
        "heldout_sha256": {p.name: digest(p.read_bytes()) for p in EVALUATOR.glob("accept_*.py")},
        "model_cost_usd": 0,
        "agent_results": None,
    }
    for task, fixture in fixtures.items():
        modules = {
            "domain": "domain.py defines dataclasses and response serialization.",
            "store": (
                "store.py owns mutable in-memory records; shared Store instances retain state."
            ),
            "api": "api.py exposes status/body tuples and ownership policy.",
            "client": "client.py binds owner and raises ValueError(status) on errors.",
        }
        readme = "# Offline fixture\n\n## Architecture\n" + "\n".join(modules.values())
        readme += "\n\n## Requirements\n" + fixture["requirements"]
        readme += (
            "\n\n## Verification\nRun python -m pytest. "
            "Existing public tests cover legacy behavior; "
            "add feature tests. Python stdlib application, pytest runner only.\n"
        )
        provenance = {
            "origin": "declared",
            "source": "README.md#requirements",
            "verification": "unverified",
        }
        nodes = [
            {
                "id": "requirement.feature",
                "type": "requirement",
                "title": task,
                "version": 1,
                "approval": "pending",
                "description": fixture["requirements"],
                "acceptance_criteria": fixture["requirements"].split(". "),
                "provenance": provenance,
            }
        ]
        edges = []
        for name, description in modules.items():
            nodes.append(
                {
                    "id": "component." + name,
                    "type": "component",
                    "title": name,
                    "version": 1,
                    "description": description,
                    "provenance": dict(provenance, source="README.md#architecture"),
                }
            )
            edges.append(
                {
                    "id": "edge." + name,
                    "type": "implemented_by",
                    "source": "requirement.feature",
                    "target": "component." + name,
                    "provenance": provenance,
                }
            )
        model = {
            "schema_version": "1.0",
            "model": {"id": "model." + task, "title": task},
            "nodes": nodes,
            "edges": edges,
        }
        assert not validate_model(model), validate_model(model)
        start = time.perf_counter()
        pack = compile_context(model, fixture["requirements"], ["requirement.feature"], 24000)
        context = serialize_context(pack)
        elapsed = time.perf_counter() - start
        assert not validate_context(pack)
        (EVALUATOR / (task + "-model.json")).write_text(json.dumps(model, indent=2) + "\n")
        for arm in ("baseline", "ane"):
            repo = RUNS / f"{task}-{arm}"
            repo.mkdir(parents=True)
            files = dict(
                fixture["files"],
                **{
                    "README.md": readme,
                    "TASK.md": fixture["requirements"] + "\n",
                    ".gitignore": "__pycache__/\n.pytest_cache/\n",
                },
            )
            if arm == "ane":
                files["CONTEXT.json"] = context + "\n"
            for name, content in files.items():
                (repo / name).write_text(content)
            env = dict(
                __import__("os").environ,
                GIT_AUTHOR_DATE="2026-11-11T00:00:00Z",
                GIT_COMMITTER_DATE="2026-11-11T00:00:00Z",
            )
            for args in (
                ["init", "-b", "main"],
                ["add", "."],
                [
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "-m",
                    "Pinned initial fixture",
                ],
            ):
                subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            output = EVALUATOR / "pretrial" / repo.name
            public = run(repo, repo / "test_public.py", output / "public")
            hidden = run(repo, EVALUATOR / f"accept_{task}.py", output / "heldout")
            assert public == 0 and hidden == 1, (repo, public, hidden)
            record["trials"].append(
                dict(
                    directory=str(repo),
                    commit=commit,
                    hashes={n: digest(v.encode()) for n, v in files.items()},
                    public_exit=public,
                    heldout_exit=hidden,
                    context_seconds=elapsed if arm == "ane" else None,
                    context_bytes=len(context.encode()) if arm == "ane" else 0,
                )
            )
    record["setup_seconds_including_compile_and_checks"] = time.perf_counter() - setup_start
    (EVALUATOR / "preparation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
