"""Exercise the public CLI using only new local demo directories and fixed fixtures."""

import argparse
import html
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = {"backend", "web", "mobile", "store"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def walkthrough(output):
    """Run real subprocesses; a zero exit alone is not evidence of correct output."""
    steps = []

    def cli(*arguments, capture=None):
        command = [sys.executable, "-m", "lsm", *map(str, arguments)]
        result = subprocess.run(
            command, cwd=output, capture_output=True, text=True, timeout=120, check=False
        )
        steps.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        write_json(output / "steps.json", steps)
        require(
            result.returncode == 0,
            f"CLI failed ({result.returncode}): {' '.join(command)}\n{result.stderr}",
        )
        if capture:
            document = json.loads(result.stdout)
            if arguments[0] == "context":
                compact = json.dumps(
                    document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                )
                require(result.stdout.rstrip("\n") == compact, "Context CLI must emit compact JSON")
                require(
                    len(compact.encode("utf-8")) == document["accounting"]["estimated_tokens"],
                    "Context byte accounting differs from its emitted compact JSON",
                )
            write_json(output / capture, document)
            return document
        return result.stdout

    examples = ROOT / "examples"
    migrated = output / "migrated.json"
    cli("migrate", examples / "governance/model-1.0.json", migrated)
    require(read_json(migrated)["schema_version"] == "1.1", "Migration did not select 1.1")
    require(
        cli("validate", migrated, "--json", capture="migration-validation.json")["valid"],
        "Migrated model is invalid",
    )

    demo = output / "demo"
    cli("workflow", "init", demo)
    require(
        all((demo / name / ".git").is_dir() for name in COMPONENTS),
        "Missing generated demo repositories",
    )
    model = output / "discovered.json"
    source_files = (".gitignore", "contract.py", "test_contract.py")
    source_before = {
        (component, name): (demo / component / name).read_bytes()
        for component in COMPONENTS
        for name in source_files
    }
    cli(
        "discover",
        examples / "discovery/manifest.json",
        model,
        "--base-dir",
        demo,
        "--existing",
        examples / "integration/seed-model.json",
    )
    require(
        cli("validate", model, "--json", capture="discovery-validation.json")["valid"],
        "Discovered model is invalid",
    )
    discovered = read_json(model)
    intent = cli(
        "inspect",
        model,
        "--node",
        "requirement.demo-sync",
        "--json",
        capture="inspected-requirement.json",
    )
    observation = cli(
        "inspect",
        model,
        "--node",
        "implementation.demo-sync",
        "--json",
        capture="inspected-implementation.json",
    )
    require(
        intent["approval"] == "pending"
        and intent["provenance"]
        == {
            "origin": "declared",
            "source": "examples/integration/README.md",
            "verification": "unverified",
        }
        and observation["provenance"]["origin"] == "inferred"
        and observation["provenance"]["verification"] == "unverified",
        "Discovery/inspection must not promote inferred observations or approve intent",
    )
    require(
        "ane-integration-probe-only" not in json.dumps(intent), "Inspect leaked synthetic secret"
    )
    migrated_joined = output / "discovered-1.1.json"
    cli("migrate", model, migrated_joined)
    cli("validate", migrated_joined, "--json", capture="joined-migration-validation.json")
    upgraded = read_json(migrated_joined)
    require(
        upgraded["schema_version"] == "1.1"
        and upgraded["nodes"] == discovered["nodes"]
        and upgraded["edges"] == discovered["edges"],
        "Migration must preserve identities, provenance and trust states exactly",
    )
    require(
        {f"component.{name}" for name in COMPONENTS}
        <= {node["id"] for node in discovered["nodes"]},
        "Missing discovered components",
    )
    repeated = output / "rediscovered.json"
    cli(
        "discover",
        examples / "discovery/manifest.json",
        repeated,
        "--base-dir",
        demo,
        "--existing",
        model,
    )
    require(read_json(repeated) == discovered, "Discovery is not idempotent")
    cli("export", model, output / "docs")
    cli("export", model, output / "docs-repeat")
    for name in ("index.md", "context.mmd", "components.mmd", "traceability.md", "onboarding.md"):
        text = (output / "docs" / name).read_bytes()
        require(
            bool(text) and text == (output / "docs-repeat" / name).read_bytes(),
            f"Missing or nondeterministic projection: {name}",
        )
        require(
            "ane-integration-probe-only" not in html.unescape(text.decode("utf-8")),
            "Documentation leaked synthetic secret",
        )
    trace = html.unescape((output / "docs" / "traceability.md").read_text(encoding="utf-8"))
    require(
        all(
            identifier in trace
            for identifier in (
                "requirement.demo-sync",
                "implementation.demo-sync",
                "test.demo-sync",
            )
        ),
        "Joined discovery model lost requirement/implementation/test traceability",
    )
    require(
        source_before
        == {
            (component, name): (demo / component / name).read_bytes()
            for component in COMPONENTS
            for name in source_files
        },
        "Read-only discovery/docs altered generated repository sources",
    )

    draft, questions = output / "draft.json", output / "questions.json"
    cli(
        "requirement",
        "create",
        "requirement.demo-sync",
        draft,
        "--intent",
        "Sandbox example: support offline sync",
    )
    cli("requirement", "refine", draft, questions)
    require(
        cli("requirement", "validate", questions, capture="requirement-validation.json")["valid"],
        "Requirement is invalid",
    )
    requirement = read_json(questions)
    require(
        requirement["state"] == "questions" and bool(requirement["questions"]),
        "Ambiguous requirement must remain unapproved with open questions",
    )

    policy = output / "demo-policy.json"
    write_json(
        policy,
        {
            "version": "1.0",
            "humans": ["demo-owner"],
            "permissions": {"approve_changes": ["demo-owner"]},
        },
    )
    proposal, approved = output / "proposal.json", output / "approved.json"
    cli(
        "change",
        "propose",
        examples / "changes/before.json",
        examples / "changes/offline-sync.json",
        proposal,
    )
    require(
        cli("change", "validate", proposal, capture="proposal-validation.json")["valid"],
        "Sandbox proposal is invalid",
    )
    # Explicit synthetic sandbox attestation, never approval of real user requirements.
    cli(
        "change",
        "approve",
        proposal,
        approved,
        "--policy",
        policy,
        "--actor",
        "demo-owner",
        "--actor-kind",
        "human",
    )
    require(
        cli("change", "validate", approved, capture="approval-validation.json")["valid"],
        "Approved sandbox proposal is invalid",
    )

    task = "Inspect backend dependencies"
    pack = cli(
        "context",
        model,
        "--task",
        task,
        "--seed",
        "component.backend",
        "--budget",
        "8192",
        capture="context.json",
    )
    require(pack["seed_ids"] == ["component.backend"], "Context lost its explicit seed")
    require(
        pack["accounting"]["method"] == "canonical_json_utf8_bytes"
        and pack["accounting"]["estimated_tokens"] <= 8192,
        "Context exceeded its byte proxy budget",
    )
    require(bool(pack["citations"]), "Context omitted citations")
    require("ane-integration-probe-only" not in json.dumps(pack), "Context leaked synthetic secret")

    # Every tracked source file in all four generated fixture repositories is
    # explicitly enumerated. No scanning, Git metadata, secrets or outside paths.
    baseline = output / "whole-repository-baseline.txt"
    baseline.write_text(
        "\n".join(
            f"# {component}/{name}\n" + (demo / component / name).read_text(encoding="utf-8")
            for component in sorted(COMPONENTS)
            for name in source_files
        ),
        encoding="utf-8",
    )
    comparison = cli(
        "context-compare",
        model,
        "--task",
        task,
        "--seed",
        "component.backend",
        "--budget",
        "8192",
        "--baseline",
        baseline,
        capture="repository-comparison.json",
    )
    require(
        comparison["baseline"]["utf8_bytes"] == len(baseline.read_bytes())
        and comparison["compiled_context"]["utf8_bytes"] == pack["accounting"]["estimated_tokens"]
        and comparison["agent_outcome_measured"] is False,
        "Repository baseline comparison must measure actual bytes, not agent performance",
    )

    execution = output / "execution.json"  # Outside demo: extra files there count as drift.
    cli(
        "workflow",
        "run",
        demo,
        approved,
        "--policy",
        policy,
        "--actor",
        "demo-owner",
        "--output",
        execution,
    )
    record = read_json(execution)
    require(
        record["state"] == "succeeded" and record["github_pr"] is None,
        "Demo must succeed locally without claiming a remote PR",
    )
    require(
        {item["component"] for item in record["repositories"]} == COMPONENTS,
        "Execution did not cover all generated components",
    )
    for item in record["repositories"]:
        require(
            item["test"]["exit_code"] == 0 and item["github_pr"] is None,
            "Missing successful fixture test or unexpected PR claim",
        )
        require((demo / item["diff_artifact"]).is_file(), "Missing local diff artifact")
        require((demo / item["review_bundle"] / "test.json").is_file(), "Missing test artifact")
    reconciled = cli("workflow", "reconcile", demo, execution, capture="reconciliation.json")
    require(
        reconciled["state"] == "matched" and reconciled["verified"] is True,
        "Generated fixture evidence did not reconcile",
    )

    benchmark = output / "benchmark.json"
    cli(
        "benchmark",
        "smoke",
        model,
        "--task",
        task,
        "--seed",
        "component.backend",
        "--budget",
        "8192",
        "--output",
        benchmark,
    )
    measured = read_json(benchmark)
    require(
        measured["kind"] == "deterministic_smoke" and measured["agent_outcome_measured"] is False,
        "Smoke mislabeled as an agent experiment",
    )
    for arm in measured["arms"].values():
        require(
            arm["context_bytes"] > 0 and arm["preparation_seconds"] >= 0,
            "Missing local preparation measurements",
        )
        require(
            arm["cost_usd"] is None and arm["pass_at_1"] is None,
            "Smoke must not fabricate cost or quality",
        )

    # Fabricated paired failures test aggregation, not agent performance.
    trials = {
        "schema_version": "1.0",
        "kind": "agent_trials",
        "data_origin": "synthetic_fixture",
        "trials": [
            {
                "kind": "agent_trial",
                "run_id": f"synthetic-{arm}",
                "pair_id": "synthetic-pair",
                "arm": arm,
                "task": "Fabricated aggregation fixture",
                "model_revision": "demo-v1",
                "budget": 8192,
                "seed": 0,
                "attempt": 1,
                "success": False,
                "verification_ref": None,
                "tokens_input": None,
                "tokens_output": None,
                "repair_iterations": None,
                "cost_usd": None,
                "latency_seconds": None,
            }
            for arm in ("baseline", "lsm")
        ],
    }
    write_json(output / "trials.json", trials)
    summary = cli("benchmark", "summarize", output / "trials.json", capture="summary.json")
    require(
        summary["data_origin"] == "synthetic_fixture" and summary["pair_count"] == 1,
        "Aggregation lost its synthetic origin or pair",
    )
    require(
        all(arm["metrics"]["cost_usd"]["mean"] is None for arm in summary["arms"].values()),
        "Unknown costs must remain null",
    )
    return {
        "ok": True,
        "cli_steps": len(steps),
        "github_pr": None,
        "agent_experiments": "pending",
        "output_dir": str(output),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="NEW directory to retain local artifacts")
    args = parser.parse_args()
    try:
        if args.output_dir is not None:
            output = args.output_dir.absolute()
            require(
                not any(path.is_symlink() for path in (output, *output.parents)),
                "Output directory and ancestors must not be symlinks",
            )
            output.mkdir(exist_ok=False)
            result = walkthrough(output)
            result["retained"] = True
        else:
            preferred = Path("/tmp/opencode")
            with tempfile.TemporaryDirectory(
                prefix="lsm-roadmap-", dir=preferred if preferred.is_dir() else None
            ) as directory:
                result = walkthrough(Path(directory))
            result["retained"] = False
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Walkthrough failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
