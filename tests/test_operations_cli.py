import json
import subprocess

from lsm.cli import main


def test_migrate_cli(tmp_path):
    path = tmp_path / "upgraded.yaml"
    assert main(["migrate", "examples/shop.json", str(path)]) == 0
    assert main(["validate", str(path)]) == 0
    assert main(["migrate", "examples/shop.json", str(path)]) == 2


def test_export_cli(tmp_path):
    output = tmp_path / "docs"
    assert main(["export", "examples/shop.json", str(output)]) == 0
    assert {path.name for path in output.iterdir()} == {
        "index.md",
        "context.mmd",
        "components.mmd",
        "traceability.md",
        "onboarding.md",
    }
    snapshot = {path.name: path.read_bytes() for path in output.iterdir()}
    assert main(["export", "examples/shop.json", str(output)]) == 2
    assert main(["export", "examples/shop.json", str(output), "--force"]) == 0
    assert snapshot == {path.name: path.read_bytes() for path in output.iterdir()}


def test_invalid_export_does_not_write(tmp_path):
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps({"schema_version": "unknown"}))
    output = tmp_path / "docs"
    assert main(["export", str(source), str(output)]) == 1
    assert not output.exists()


def test_discover_cli_and_idempotent_import(tmp_path):
    repository = tmp_path / "backend"
    repository.mkdir()
    subprocess.run(["git", "init", str(repository)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=Demo",
            "-c",
            "user.email=demo@example.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "Initial",
        ],
        check=True,
        capture_output=True,
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "model": {"id": "system:test", "title": "Demo"},
                "repositories": [
                    {
                        "id": "repo:backend",
                        "title": "Backend",
                        "path": "backend",
                        "components": [{"id": "component:backend", "title": "API"}],
                    }
                ],
            }
        )
    )
    destination = tmp_path / "discovered.json"
    assert main(["discover", str(manifest), str(destination), "--base-dir", str(tmp_path)]) == 0
    assert main(["validate", str(destination)]) == 0
    second = tmp_path / "second.yaml"
    assert (
        main(
            [
                "discover",
                str(manifest),
                str(second),
                "--base-dir",
                str(tmp_path),
                "--existing",
                str(destination),
            ]
        )
        == 0
    )
    from lsm.storage import load_model

    assert load_model(destination) == load_model(second)
