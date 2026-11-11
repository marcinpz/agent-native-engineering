from lsm.cli import main


def test_change_cli_requires_explicit_human_approval(tmp_path):
    proposal, approved = tmp_path / "proposal.json", tmp_path / "approved.json"
    assert (
        main(
            [
                "change",
                "propose",
                "examples/changes/before.json",
                "examples/changes/offline-sync.json",
                str(proposal),
            ]
        )
        == 0
    )
    assert main(["change", "validate", str(proposal)]) == 0
    assert (
        main(
            [
                "change",
                "approve",
                str(proposal),
                str(approved),
                "--policy",
                "examples/governance/policy.json",
                "--actor",
                "demo-owner",
                "--actor-kind",
                "agent",
            ]
        )
        == 1
    )
    assert not approved.exists()
    assert (
        main(
            [
                "change",
                "approve",
                str(proposal),
                str(approved),
                "--policy",
                "examples/governance/policy.json",
                "--actor",
                "demo-owner",
            ]
        )
        == 0
    )
    assert main(["change", "validate", str(approved)]) == 0
