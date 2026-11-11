"""Shared display redaction must not change locally persisted artifacts."""

import copy
import json

import pytest

from lsm.changes import create_proposal
from lsm.cli import main
from lsm.context import compile_context, serialize_context
from lsm.documentation import render_docs
from lsm.security import redact


@pytest.fixture
def model():
    return {
        "schema_version": "1.0",
        "model": {"id": "model.test", "title": "Review model"},
        "nodes": [
            {
                "id": "component.test",
                "type": "component",
                "title": "Review component",
                "version": 1,
                "provenance": {
                    "origin": "declared",
                    "source": "fixture",
                    "verification": "unverified",
                },
            }
        ],
        "edges": [],
    }


@pytest.mark.parametrize(
    "prose",
    [
        'Credentials: {"password": "ReviewOnlySecret with spaces"}',
        "'api_key': 'ReviewOnlySecret with spaces'",
        '"password": ReviewOnlySecret',
        "password='ReviewOnlySecret with spaces'",
        r'password="ReviewOnlySecret \"quoted\" trailing words"',
        r"password='ReviewOnlySecret \'quoted\' trailing words'",
        "password='ReviewOnlySecret ''quoted'' trailing words'",
        'password="ReviewOnlySecret unterminated value',
        '"authorization": "ReviewOnlySecret with spaces"',
        '"private_key": "ReviewOnlySecret with spaces"',
        "postgres://reviewuser:ReviewOnlySecret@localhost/db",
        "redis+tls://reviewuser:ReviewOnlySecret@localhost/db",
        "redis://:ReviewOnlySecret@localhost/db",
        "authorization: Bearer ReviewOnlySecret",
    ],
)
def test_quoted_credentials_redacted_in_every_projection(model, prose):
    model["nodes"][0]["description"] = prose
    original = copy.deepcopy(model)
    after = copy.deepcopy(model)
    after["nodes"][0]["title"] = "Changed"
    outputs = [
        redact(prose),
        *render_docs(model).values(),
        serialize_context(compile_context(model, "Explain", ["component.test"])),
        json.dumps(create_proposal(model, after)),
    ]
    for output in outputs:
        assert "ReviewOnlySecret" not in output
        assert "trailing words" not in output
    assert "[REDACTED]" in outputs[0]
    assert model == original


def test_quoted_json_prose_preserves_structure_and_json_transport():
    prose = r'{"password": "ReviewOnlySecret \"with quotes\"", "other": "Keep me"}'
    clean = redact(prose)
    assert json.loads(clean) == {"password": "[REDACTED]", "other": "Keep me"}
    assert json.loads(json.dumps({"description": clean}))["description"] == clean
    assert redact(clean) == clean


@pytest.mark.parametrize("command", ["inspect", "show"])
def test_inspect_node_redacted_without_changing_persistence(model, tmp_path, capsys, command):
    model["nodes"][0]["description"] = (
        'password=ReviewOnlySecret ghp_reviewonlysecret {"password": "QuotedSecret words"}'
    )
    source = tmp_path / "model.json"
    source.write_text(json.dumps(model))
    original = source.read_bytes()
    assert main([command, str(source), "--node", "component.test", "--json"]) == 0
    result = capsys.readouterr()
    assert not result.err
    node = json.loads(result.out)
    for secret in ("ReviewOnlySecret", "ghp_reviewonlysecret", "QuotedSecret"):
        assert secret not in node["description"]
    assert source.read_bytes() == original
    destination = tmp_path / "copy.json"
    assert main(["import", str(source), str(destination)]) == 0
    capsys.readouterr()
    assert json.loads(destination.read_text()) == model


@pytest.mark.parametrize("json_output", [False, True])
def test_summary_and_missing_node_redacted(model, tmp_path, capsys, json_output):
    model["model"]["title"] = 'Title {"password": "ReviewOnlySecret words"}'
    source = tmp_path / "model.json"
    source.write_text(json.dumps(model))
    flags = ["--json"] if json_output else []
    assert main(["inspect", str(source), *flags]) == 0
    output = capsys.readouterr()
    assert "ReviewOnlySecret" not in output.out + output.err
    if json_output:
        assert json.loads(output.out)["model"]["title"].endswith('"[REDACTED]"}')
    assert main(["inspect", str(source), "--node", "ghp_reviewonlysecret", *flags]) == 1
    output = capsys.readouterr()
    assert "ghp_reviewonlysecret" not in output.out + output.err


@pytest.mark.parametrize("json_output", [False, True])
def test_validation_diagnostics_do_not_echo_invalid_values(model, tmp_path, capsys, json_output):
    # Neither recognizable secrets nor arbitrary invalid values belong in schema diagnostics.
    model["nodes"][0]["version"] = 'UnrecognizedSecret {"password": "ReviewOnlySecret words"}'
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps(model))
    flags = ["--json"] if json_output else []
    assert main(["validate", str(source), *flags]) == 1
    output = capsys.readouterr()
    assert "UnrecognizedSecret" not in output.out + output.err
    assert "ReviewOnlySecret" not in output.out + output.err
    if json_output:
        error = json.loads(output.out)["errors"][0]
        assert error["code"] == "schema_error"
        assert error["path"] == "/nodes/0/version"


def test_graph_diagnostic_redaction(model, tmp_path, capsys):
    model["nodes"].append(copy.deepcopy(model["nodes"][0]))
    for node in model["nodes"]:
        node["id"] = "ghp_reviewonlysecret"
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps(model))
    assert main(["validate", str(source), "--json"]) == 1
    output = capsys.readouterr()
    assert "ghp_reviewonlysecret" not in output.out + output.err
    assert any(e["code"] == "duplicate_id" for e in json.loads(output.out)["errors"])


@pytest.mark.parametrize("json_output", [False, True])
def test_parse_diagnostics_do_not_echo_source_lines(tmp_path, capsys, json_output):
    source = tmp_path / "broken.yaml"
    source.write_text("nodes: [UnrecognizedSecret, password='ReviewOnlySecret words'\n")
    flags = ["--json"] if json_output else []
    assert main(["validate", str(source), *flags]) == 2
    output = capsys.readouterr()
    assert "UnrecognizedSecret" not in output.out + output.err
    assert "ReviewOnlySecret" not in output.out + output.err
    assert "Traceback" not in output.out + output.err
    if json_output:
        assert json.loads(output.out)["errors"][0]["code"] == "io_error"


@pytest.mark.parametrize("json_output", [False, True])
def test_operation_oserror_is_a_redacted_io_failure(monkeypatch, capsys, tmp_path, json_output):
    def unavailable_parent(args):
        raise OSError("Cannot create root parent: password='ReviewOnlySecret with spaces'")

    monkeypatch.setattr("lsm.cli.dispatch", unavailable_parent)
    # Simulate an operation's mkdir/init failure without relying on OS privileges.
    flags = ["--json"] if json_output else []
    assert main(["validate", str(tmp_path / "unavailable" / "model.json"), *flags]) == 2
    output = capsys.readouterr()
    assert "ReviewOnlySecret" not in output.out + output.err
    assert "Traceback" not in output.out + output.err
    assert "Cannot create root parent" in output.out + output.err
    if json_output:
        assert json.loads(output.out)["errors"][0]["code"] == "io_error"


def test_usage_error_redaction(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["ghp_reviewonlysecret"])
    assert exc.value.code == 2
    assert "ghp_reviewonlysecret" not in capsys.readouterr().err
