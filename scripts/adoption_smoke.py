"""Run a read-only adoption experiment on new, synthetic source repositories."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from lsm.changes import model_digest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = {
    "spring-service": (
        "pom.xml",
        "Dockerfile",
        "cloudrun.yaml",
        "src/main/java/example/synthetic/Application.java",
    ),
    "python-service": ("pyproject.toml", "app.py"),
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo, *args):
    git = shutil.which("git")
    if git is None:
        raise ValueError("Git must be installed for the native-provider experiment")
    command = [
        git,
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "commit.gpgSign=false",
        "-c",
        "user.name=Synthetic ANE fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "-C",
        str(repo),
        *args,
    ]
    result = subprocess.run(
        command,
        env={
            "PATH": os.defpath,
            "HOME": "/nonexistent",
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ATTR_NOSYSTEM": "1",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    _require(result.returncode == 0, f"Synthetic fixture Git command failed: {result.stderr}")
    return result.stdout.strip()


def _source_snapshot(root):
    # The harness inspects only newly generated synthetic trees. Track unexpected
    # files/directories too, not just edits to known files. Providers themselves
    # read neither these sources nor the .env canary, and never execute them.
    snapshot = {}
    for name in SOURCE_FILES:
        repo = root / name
        for parent, dirs, names in os.walk(repo, followlinks=False):
            if Path(parent) == repo:
                dirs[:] = [entry for entry in dirs if entry not in {".git", ".ane"}]
            for entry in dirs + names:
                path = Path(parent) / entry
                _require(not path.is_symlink(), "Unexpected symlink in synthetic source tree")
                relative = f"{name}/{path.relative_to(repo).as_posix()}"
                snapshot[relative] = (
                    "directory" if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest()
                )
                snapshot[relative] += f":mode={path.stat().st_mode & 0o777:o}"
    return snapshot


def _metadata_snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def walkthrough(output):
    preparation_started = time.perf_counter()
    steps = []

    def cli(*arguments):
        command = [sys.executable, "-m", "lsm", *map(str, arguments)]
        started = time.perf_counter()
        result = subprocess.run(
            command, cwd=output, capture_output=True, text=True, timeout=120, check=False
        )
        steps.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
        _save(output / "steps.json", steps)
        _require(
            result.returncode == 0,
            f"CLI failed: {' '.join(command)}\n{result.stdout}\n{result.stderr}",
        )
        return json.loads(result.stdout)

    fixture = ROOT / "examples" / "adoption"
    source_base = output / "sources"
    source_base.mkdir()
    for name, paths in SOURCE_FILES.items():
        repo = source_base / name
        repo.mkdir()
        for relative in paths:
            destination = repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(fixture / name / relative, destination)
        _git(repo, "init")
        _git(repo, "add", "--all")
        _git(repo, "commit", "-m", "Create synthetic read-only adoption fixture")
        # A fake, untracked canary: do not import source/env files or publish it.
        (repo / ".env").write_text("API_TOKEN=adoption-probe-not-a-real-secret\n", encoding="utf-8")
    original_sources = _source_snapshot(source_base)
    original_heads = {name: _git(source_base / name, "rev-parse", "HEAD") for name in SOURCE_FILES}

    descriptor = cli("provider", "capabilities")
    _save(output / "provider-capabilities.json", descriptor)
    results = {}
    for language, repo_name in (("spring", "spring-service"), ("python", "python-service")):
        workspace = source_base / repo_name / ".ane"
        manifest = fixture / f"{language}-manifest.json"
        created = cli("workspace", "init", manifest, workspace, "--base-dir", source_base)
        _require(created["mode"] == "in-repo", "Expected an explicitly opted-in local workspace")
        _require(cli("workspace", "status", workspace)["valid"], "Workspace failed validation")
        baseline = _metadata_snapshot(workspace)
        preview = cli("workspace", "refresh", workspace, "--base-dir", source_base)
        _require(not preview["changed"], "Unchanged source must not produce a refresh change")
        _require(_metadata_snapshot(workspace) == baseline, "Preview refresh wrote metadata")
        applied = cli("workspace", "refresh", workspace, "--base-dir", source_base, "--apply")
        _require(not applied["changed"], "Reapplying unchanged data must be idempotent")
        _require(_metadata_snapshot(workspace) == baseline, "Clock-only refresh rewrote metadata")

        native = cli("provider", "discover", manifest, "--base-dir", source_base)
        replay = cli(
            "provider",
            "discover",
            manifest,
            "--base-dir",
            source_base,
            "--replay",
            workspace / "model.json",
        )
        _require(native["status"] == replay["status"] == "succeeded", "Provider discovery failed")
        _require(
            model_digest(native["data"]["model"])
            == model_digest(replay["data"]["model"])
            == model_digest(_json(workspace / "model.json")),
            "Replacing Git with mock changed LSM semantics",
        )
        for node in native["data"]["model"]["nodes"]:
            _require(
                node["provenance"]["verification"] == "unverified",
                "Read-only import promoted trust",
            )
        _require((workspace / "docs" / "index.md").is_file(), "Missing generated human entrypoint")
        _require((workspace / "context.json").is_file(), "Missing generated agent entrypoint")
        context = _json(workspace / "context.json")
        _require(
            len((workspace / "context.json").read_bytes())
            == context["accounting"]["estimated_tokens"]
            <= 8192,
            "Workspace context file violates compact byte-budget accounting",
        )
        public = (workspace / "context.json").read_text() + "".join(
            path.read_text() for path in (workspace / "docs").iterdir() if path.is_file()
        )
        _require(
            "adoption-probe-not-a-real-secret" not in public, "Source credential canary leaked"
        )
        results[language] = {
            "mode": created["mode"],
            "provider_model_equivalent": True,
            "idempotent": True,
            "workspace": str(workspace),
        }

    # Separate orchestration repository; no metadata is required in source repos.
    orchestrator = output / "orchestration"
    orchestrator.mkdir()
    (orchestrator / "README.md").write_text("Synthetic orchestration repository.\n")
    _git(orchestrator, "init")
    _git(orchestrator, "add", "--all")
    _git(orchestrator, "commit", "-m", "Create synthetic orchestration repository")
    orchestration_head = _git(orchestrator, "rev-parse", "HEAD")
    external = orchestrator / ".ane"
    created = cli(
        "workspace", "init", fixture / "multi-manifest.json", external, "--base-dir", source_base
    )
    _require(created["mode"] == "external", "Expected external workspace placement")
    baseline = _metadata_snapshot(external)
    unchanged = cli("workspace", "refresh", external, "--base-dir", source_base)
    _require(
        not unchanged["changed"] and baseline == _metadata_snapshot(external),
        "External workspace is not deterministic",
    )
    _require(
        _source_snapshot(source_base) == original_sources, "Adoption changed application sources"
    )
    _require(
        all(
            _git(source_base / name, "rev-parse", "HEAD") == head
            for name, head in original_heads.items()
        ),
        "Adoption changed source Git HEADs",
    )

    # Simulate a change made OUTSIDE ANE, in this disposable fixture only. No
    # application source bytes are changed; metadata refresh must expose the ref.
    _git(
        source_base / "spring-service",
        "commit",
        "--allow-empty",
        "-m",
        "Simulated external revision",
    )
    revised_head = _git(source_base / "spring-service", "rev-parse", "HEAD")
    changed = cli("workspace", "refresh", external, "--base-dir", source_base)
    _require(changed["changed"], "A new external Git revision must produce a reviewable diff")
    _require(baseline == _metadata_snapshot(external), "Change preview wrote metadata")
    _save(output / "refresh-preview.json", changed)
    applied = cli("workspace", "refresh", external, "--base-dir", source_base, "--apply")
    _require(applied["changed"], "Explicit refresh did not apply the accepted metadata change")
    _require(cli("workspace", "status", external)["valid"], "Refreshed workspace is invalid")
    _require(
        not cli("workspace", "refresh", external, "--base-dir", source_base)["changed"],
        "Refresh after apply is not idempotent",
    )
    repositories = [
        node for node in _json(external / "model.json")["nodes"] if node["type"] == "repository"
    ]
    spring_repo = next(node for node in repositories if node["id"] == "repo.synthetic-spring")
    _require(
        revised_head in spring_repo["provenance"]["source"] and spring_repo["version"] >= 2,
        "Observed ref refresh lost provenance or entity version",
    )

    python_workspace = source_base / "python-service" / ".ane"
    baseline = _metadata_snapshot(python_workspace)
    planned = cli("workspace", "clean", python_workspace)
    _require(
        not planned["applied"] and _metadata_snapshot(python_workspace) == baseline,
        "Cleanup plan must not delete metadata",
    )
    _require(
        cli("workspace", "clean", python_workspace, "--apply")["applied"], "Cleanup was not applied"
    )
    _require(not python_workspace.exists(), "Cleanup left an unexpected metadata directory")
    _require(
        _source_snapshot(source_base) == original_sources,
        "Refresh/cleanup changed application bytes",
    )
    _require(
        _git(source_base / "spring-service", "rev-parse", "HEAD") == revised_head,
        "ANE changed the operator-simulated source revision",
    )
    _require(
        _git(source_base / "python-service", "rev-parse", "HEAD")
        == original_heads["python-service"],
        "ANE changed the Python source revision",
    )
    _require(
        _git(orchestrator, "rev-parse", "HEAD") == orchestration_head,
        "Workspace wrote an orchestration commit",
    )
    summary = {
        "ok": True,
        "cli_steps": len(steps),
        "fixtures": results,
        "external_workspace": str(external),
        "source_bytes_unchanged": True,
        "git_heads_unchanged_by_ane": True,
        "external_revision_simulated": True,
        "application_builds_executed": False,
        "application_tests_executed": False,
        "migration_executed": False,
        "cloud_accessed": False,
        "output_dir": str(output),
        "preparation_seconds": time.perf_counter() - preparation_started,
        "cli_seconds": sum(step["elapsed_seconds"] for step in steps),
        "agent_model_invocations": 0,
        "provider_tokens": None,
        "cost_usd": None,
    }
    _save(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, help="NEW directory for retained synthetic artifacts"
    )
    args = parser.parse_args()
    try:
        if args.output_dir:
            output = args.output_dir.absolute()
            _require(
                not any(path.is_symlink() for path in (output, *output.parents)),
                "Symlink output is forbidden",
            )
            output.mkdir(exist_ok=False)
            result = walkthrough(output)
            result["retained"] = True
        else:
            preferred = Path("/tmp/opencode")
            with tempfile.TemporaryDirectory(
                prefix="ane-adoption-", dir=preferred if preferred.is_dir() else None
            ) as directory:
                result = walkthrough(Path(directory))
            result["retained"] = False
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Adoption experiment failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
