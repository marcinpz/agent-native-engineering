import json
import subprocess
import sys

from lsm.cli import main


def test_context_stdout_accounting_and_budget_errors(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "lsm",
            "context",
            "examples/shop.json",
            "--task",
            "Inspect",
            "--seed",
            "component.backend",
            "--budget",
            "8192",
        ],
        capture_output=True,
        check=True,
    )
    pack = json.loads(result.stdout)
    assert pack["accounting"]["estimated_tokens"] == len(result.stdout) <= 8192
    assert not result.stderr
    assert (
        main(
            [
                "context",
                "examples/shop.json",
                "--task",
                "Inspect",
                "--seed",
                "component.backend",
                "--budget",
                "10",
            ]
        )
        == 1
    )


def test_benchmark_smoke_cli(tmp_path):
    output = tmp_path / "smoke.json"
    assert (
        main(
            [
                "benchmark",
                "smoke",
                "examples/shop.json",
                "--task",
                "Inspect",
                "--seed",
                "component.backend",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    smoke = json.loads(output.read_text())
    assert smoke["kind"] == "deterministic_smoke"
    assert main(["benchmark", "summarize", str(output)]) == 1


def test_workflow_cli_and_failure_exit(tmp_path):
    from lsm.changes import approve_proposal, create_proposal
    from lsm.storage import load_model, save_model

    proposal = approve_proposal(
        create_proposal(
            load_model("examples/changes/before.json"),
            load_model("examples/changes/offline-sync.json"),
        ),
        load_model("examples/governance/policy.json"),
        "demo-owner",
    )
    proposal_path = tmp_path / "approved.json"
    save_model(proposal, proposal_path)
    for fail in (False, True):
        root = tmp_path / ("failed" if fail else "successful")
        record = tmp_path / ("failed-record.json" if fail else "record.json")
        assert main(["workflow", "init", str(root)]) == 0
        args = [
            "workflow",
            "run",
            str(root),
            str(proposal_path),
            "--policy",
            "examples/governance/policy.json",
            "--actor",
            "demo-owner",
            "--output",
            str(record),
        ]
        assert main(args + (["--fail-component", "mobile"] if fail else [])) == int(fail)
        assert json.loads(record.read_text())["state"] == ("failed" if fail else "succeeded")
        assert main(["workflow", "reconcile", str(root), str(record)]) == int(fail)


def test_workflow_missing_output_parent_fails_before_mutation(tmp_path):
    root = tmp_path / "demo"
    assert main(["workflow", "init", str(root)]) == 0
    assert (
        main(
            [
                "workflow",
                "run",
                str(root),
                str(tmp_path / "unused.json"),
                "--policy",
                "examples/governance/policy.json",
                "--actor",
                "demo-owner",
                "--output",
                str(tmp_path / "missing" / "record.json"),
            ]
        )
        == 2
    )
    assert not (root / "reviews").exists()


def test_workflow_record_save_failure_preserves_evidence_on_stdout(tmp_path, monkeypatch, capsys):
    from lsm.changes import approve_proposal, create_proposal
    from lsm.storage import ModelIOError, load_model, save_model

    proposal = approve_proposal(
        create_proposal(
            load_model("examples/changes/before.json"),
            load_model("examples/changes/offline-sync.json"),
        ),
        load_model("examples/governance/policy.json"),
        "demo-owner",
    )
    path = tmp_path / "proposal.json"
    save_model(proposal, path)
    root = tmp_path / "demo"
    assert main(["workflow", "init", str(root)]) == 0
    capsys.readouterr()

    def fail_write(*args, **kwargs):
        raise ModelIOError("simulated full disk")

    monkeypatch.setattr("lsm.operations_cli.write_document", fail_write)
    assert (
        main(
            [
                "workflow",
                "run",
                str(root),
                str(path),
                "--policy",
                "examples/governance/policy.json",
                "--actor",
                "demo-owner",
                "--output",
                str(tmp_path / "record.json"),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["state"] == "succeeded"
    assert "simulated full disk" in captured.err
