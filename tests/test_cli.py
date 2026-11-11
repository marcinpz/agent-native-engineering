import json
import subprocess
import sys

import pytest

from lsm.cli import main


def test_init_validate_inspect_import(tmp_path, capsys):
    source = tmp_path / "model.json"
    destination = tmp_path / "model.yaml"
    assert main(["init", str(source), "--id", "system:test", "--title", "Test"]) == 0
    assert main(["validate", str(source), "--json"]) == 0
    assert '"valid": true' in capsys.readouterr().out
    assert main(["import", str(source), str(destination)]) == 0
    capsys.readouterr()
    assert main(["inspect", str(destination), "--json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["nodes"] == 0
    assert summary["model"]["id"] == "system:test"
    assert main(["show", str(source)]) == 0
    assert main(["inspect", str(source), "--node", "missing"]) == 1


def test_no_overwrite_without_force(tmp_path):
    path = tmp_path / "model.json"
    assert main(["init", str(path)]) == 0
    original = path.read_bytes()
    assert main(["init", str(path), "--title", "Replacement"]) == 2
    assert path.read_bytes() == original
    assert main(["init", str(path), "--title", "Replacement", "--force"]) == 0
    assert json.loads(path.read_text())["model"]["title"] == "Replacement"


def test_structured_failure_and_invalid_import(tmp_path, capsys):
    path = tmp_path / "invalid.json"
    path.write_text('{"schema_version":"99"}')
    assert main(["validate", str(path), "--json"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] is False
    assert all({"code", "path", "message"} <= error.keys() for error in result["errors"])
    destination = tmp_path / "not-created.yaml"
    assert main(["import", str(path), str(destination)]) == 1
    assert not destination.exists()


def test_io_and_invalid_init(tmp_path, capsys):
    assert main(["validate", str(tmp_path / "missing.json"), "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["errors"][0]["code"] == "io_error"
    assert main(["init", str(tmp_path / "bad.json"), "--id", "INVALID ID"]) == 1
    assert not (tmp_path / "bad.json").exists()


def test_module_entry_point():
    result = subprocess.run([sys.executable, "-m", "lsm", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "validate" in result.stdout


def test_example_end_to_end(tmp_path, capsys):
    source = "examples/shop.json"
    assert main(["validate", source]) == 0
    destination = tmp_path / "shop.yaml"
    assert main(["import", source, str(destination)]) == 0
    capsys.readouterr()
    assert main(["inspect", str(destination), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["nodes"] >= 10


def test_example_node_lookup(capsys):
    assert main(["show", "examples/shop.json", "--node", "component.backend", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == "component.backend"


def test_invalid_model_subprocess_exit(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text(
        '{"schema_version":"1.0","model":{"id":"system:test","title":"T"},'
        '"nodes":[],"edges":[{"id":"edge:missing","type":"depends_on",'
        '"source":"component:a","target":"component:b","provenance":'
        '{"origin":"declared","source":"test","verification":"unverified"}}]}'
    )
    result = subprocess.run(
        [sys.executable, "-m", "lsm", "validate", str(path), "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["errors"]
    assert not result.stderr


def test_parse_failure_does_not_write(tmp_path):
    source = tmp_path / "bad.yaml"
    source.write_text("nodes: [")
    destination = tmp_path / "output.json"
    assert main(["import", str(source), str(destination)]) == 2
    assert not destination.exists()


def test_invalid_import_preserves_destination_with_force(tmp_path):
    source = tmp_path / "invalid.json"
    source.write_text("{}")
    destination = tmp_path / "existing.json"
    destination.write_text("original content")
    assert main(["import", str(source), str(destination), "--force"]) == 1
    assert destination.read_text() == "original content"


def test_usage_and_console_entry_point():
    result = subprocess.run(["lsm", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    result = subprocess.run(
        [sys.executable, "-m", "lsm", "validate"], capture_output=True, text=True
    )
    assert result.returncode == 2


@pytest.mark.parametrize("tagged", ["!!bool garbage", '!!float ""', '!!int ""'])
def test_malformed_tagged_yaml_has_structured_io_error(tmp_path, tagged):
    path = tmp_path / "bad.yaml"
    path.write_text(f"a: {tagged}\n")
    result = subprocess.run(
        [sys.executable, "-m", "lsm", "validate", str(path), "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["errors"][0]["code"] == "io_error"
    assert "Traceback" not in result.stderr


def test_import_preserves_exponent_string_title(tmp_path, capsys):
    source, destination = tmp_path / "model.json", tmp_path / "model.yaml"
    assert main(["init", str(source), "--title", "1e3"]) == 0
    assert main(["import", str(source), str(destination)]) == 0
    capsys.readouterr()
    assert main(["inspect", str(destination), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["model"]["title"] == "1e3"
