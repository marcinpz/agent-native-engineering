import hashlib
import json

import pytest

from lsm.cli import main
from lsm.junit import MAX_BYTES, import_junit

COMMIT = "a" * 40


def collect(tmp_path, xml, **kwargs):
    path = tmp_path / "report.xml"
    path.write_bytes(xml.encode())
    before = path.read_bytes()
    result = import_junit(path, repository="repository:demo", commit=COMMIT, **kwargs)
    assert path.read_bytes() == before
    return result


@pytest.mark.parametrize("outcome", ["passed", "failure", "error", "skipped"])
def test_outcomes(tmp_path, outcome):
    marker = "" if outcome == "passed" else f"<{outcome}>SECRET OUTPUT</{outcome}>"
    result = collect(tmp_path, f'<testsuite><testcase name="case">{marker}</testcase></testsuite>')
    assert result["status"] == "succeeded"
    data = result["data"]
    assert data["cases"][0]["outcome"] == outcome
    assert data["verification"] == "unverified"
    assert data["confidence"] is None
    assert "SECRET OUTPUT" not in json.dumps(result)
    assert "approved" not in json.dumps(result)


@pytest.mark.parametrize(
    "xml",
    [
        "not XML",
        "<testsuite/>",
        '<testsuite tests="0"><testcase name="x"/></testsuite>',
        '<testsuite failures="1"><testcase name="x"/></testsuite>',
        '<testsuite><testcase name="x"><failure/><skipped/></testcase></testsuite>',
        "<testsuite><testcase/></testsuite>",
        '<!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]><testsuite/>',
        "<testsuite><failure>SECRET</failure></testsuite>",
        '<testsuites><testcase name="x"/></testsuites>',
        '<testsuite><testcase name="x"><unknown/></testcase></testsuite>',
        "<testsuite>" * 40 + "</testsuite>" * 40,
        " " * (MAX_BYTES + 1),
    ],
)
def test_reject(tmp_path, xml):
    result = collect(tmp_path, xml)
    assert result["status"] == "failed"
    assert result["data"] is None
    assert result["errors"][0]["message"] == "JUnit report or binding rejected"


def test_binding_identity_nesting(tmp_path):
    xml = (
        '<testsuites tests="1"><testsuite><testsuite>'
        '<testcase name="x"/></testsuite></testsuite></testsuites>'
    )
    first = collect(tmp_path, xml)
    second = collect(tmp_path, xml)
    assert first["data"] == second["data"]
    data = first["data"]
    assert len(data["suites"]) == 3
    assert data["artifact_sha256"] == hashlib.sha256(xml.encode()).hexdigest()
    assert data["source_ref"] == "sha256:" + data["artifact_sha256"]
    path = tmp_path / "report.xml"
    for repository, commit in [("repository:other", COMMIT), ("repository:demo", "b" * 40)]:
        changed = import_junit(path, repository=repository, commit=commit)
        assert changed["data"]["id"] != data["id"]
        assert changed["data"]["cases"][0]["id"] != data["cases"][0]["id"]
    assert import_junit(path, repository="repository:demo", commit="HEAD")["status"] == "failed"
    assert import_junit(path, repository="https://secret@host", commit=COMMIT)["status"] == "failed"


@pytest.mark.parametrize("attributes", ['status="notrun"', 'result="skipped"'])
def test_unsupported_status_is_not_pass(tmp_path, attributes):
    result = collect(tmp_path, f'<testsuite><testcase name="x" {attributes}/></testsuite>')
    assert result["status"] == "failed"


def test_element_bound_and_invalid_encoding(tmp_path):
    result = collect(tmp_path, "<testsuite>" + '<testcase name="x"/>' * 20000 + "</testsuite>")
    assert result["status"] == "failed"
    path = tmp_path / "report.xml"
    path.write_bytes(b"\xffSECRET")
    assert import_junit(path, repository="repository:demo", commit=COMMIT)["status"] == "failed"
    assert (
        import_junit(tmp_path / "missing", repository="repository:demo", commit=COMMIT)["status"]
        == "failed"
    )


def test_cli(tmp_path, capsys):
    path = tmp_path / "report.xml"
    path.write_text(
        '<testsuite><testcase name="x"><failure>SECRET</failure></testcase></testsuite>'
    )
    assert (
        main(["import-junit", str(path), "--repository", "repository:demo", "--commit", COMMIT])
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["cases"][0]["outcome"] == "failure"
    assert "SECRET" not in json.dumps(result)
    assert (
        main(["import-junit", str(path), "--repository", "repository:demo", "--commit", "HEAD"])
        == 1
    )
