import copy
import json
import os
import subprocess

from lsm.cli import main
from lsm.storage import load_model, save_model


def _source_repo(tmp_path):
    repo = tmp_path / "spring-service"
    repo.mkdir()
    (repo / "source.txt").write_text("Unchanged synthetic source.\n")
    environment = {
        "PATH": os.defpath,
        "HOME": "/nonexistent",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }

    def git(*args):
        subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgSign=false",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "-C",
                str(repo),
                *args,
            ],
            env=environment,
            check=True,
            capture_output=True,
        )

    git("init")
    git("add", "--all")
    git("commit", "-m", "Synthetic source baseline")
    return repo


def test_provider_capabilities_cli(capsys):
    assert main(["provider", "capabilities"]) == 0
    descriptor = json.loads(capsys.readouterr().out)
    assert descriptor["capabilities"] == [{"name": "discover", "read_only": True}]


def test_provider_cli_replay_and_safe_failures(tmp_path, capsys):
    _source_repo(tmp_path)
    manifest = "examples/adoption/spring-manifest.json"
    assert main(["provider", "discover", manifest, "--base-dir", str(tmp_path)]) == 0
    native = json.loads(capsys.readouterr().out)
    model_path = tmp_path / "replay.json"
    save_model(native["data"]["model"], model_path)
    assert (
        main(
            [
                "provider",
                "discover",
                manifest,
                "--base-dir",
                str(tmp_path),
                "--replay",
                str(model_path),
            ]
        )
        == 0
    )
    replay = json.loads(capsys.readouterr().out)
    assert replay["data"] == native["data"]
    bad = copy.deepcopy(load_model(manifest))
    bad["repositories"][0]["path"] = "../escape"
    path = tmp_path / "invalid.json"
    save_model(bad, path)
    assert main(["provider", "discover", str(path), "--base-dir", str(tmp_path)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "failed"


def test_provider_output_does_not_overwrite(tmp_path, capsys):
    _source_repo(tmp_path)
    path = tmp_path / "keep.json"
    path.write_text("Original local artifact")
    assert (
        main(
            [
                "provider",
                "discover",
                "examples/adoption/spring-manifest.json",
                "--base-dir",
                str(tmp_path),
                "--output",
                str(path),
            ]
        )
        == 2
    )
    assert path.read_text() == "Original local artifact"
    result = json.loads(capsys.readouterr().out)
    assert result["errors"][0]["code"] == "io_error"


def test_provider_cli_parse_error_is_structured_and_redacted(tmp_path, capsys):
    path = tmp_path / "malformed.json"
    path.write_text('{"password": "adoption-cli-fake-secret",')
    assert main(["provider", "discover", str(path), "--base-dir", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out)["errors"][0]["code"] == "io_error"
    assert "adoption-cli-fake-secret" not in captured.out + captured.err
    assert "Traceback" not in captured.out + captured.err


def test_workspace_cli_defaults_do_not_write_existing_metadata(tmp_path, capsys):
    repo = _source_repo(tmp_path)
    target = repo / ".ane"
    assert (
        main(
            [
                "workspace",
                "init",
                "examples/adoption/spring-manifest.json",
                str(target),
                "--base-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["workspace", "status", str(target)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True
    before = {path: path.read_bytes() for path in target.rglob("*") if path.is_file()}
    assert main(["workspace", "refresh", str(target), "--base-dir", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is False
    assert all(path.read_bytes() == content for path, content in before.items())
    assert main(["workspace", "clean", str(target)]) == 0
    assert json.loads(capsys.readouterr().out)["applied"] is False
    assert all(path.read_bytes() == content for path, content in before.items())
    assert main(["workspace", "clean", str(target), "--apply"]) == 0
    assert not target.exists()
    assert (repo / "source.txt").read_text() == "Unchanged synthetic source.\n"
