import json

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
