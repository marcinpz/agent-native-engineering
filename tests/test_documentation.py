"""Documentation projections are cited data, not independently verified claims."""

import copy
import json
import random
import re
from pathlib import Path

import pytest

from lsm.documentation import render_docs

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).parent / "golden" / "docs"
FILENAMES = {"index.md", "context.mmd", "components.mmd", "traceability.md", "onboarding.md"}


@pytest.fixture
def shop():
    return json.loads((ROOT / "examples" / "shop.json").read_text(encoding="utf-8"))


def test_shop_golden(shop):
    rendered = render_docs(shop)
    assert set(rendered) == FILENAMES
    assert {path.name for path in GOLDEN.iterdir()} == FILENAMES
    for filename, text in rendered.items():
        assert text == (GOLDEN / filename).read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert "not independently verified" in text


def test_reordered_nodes_edges_are_identical_without_mutation(shop):
    original = copy.deepcopy(shop)
    expected = render_docs(shop)
    for seed in range(5):
        shuffled = copy.deepcopy(shop)
        random.Random(seed).shuffle(shuffled["nodes"])
        random.Random(seed + 10).shuffle(shuffled["edges"])
        assert render_docs(shuffled) == expected
    assert shop == original


@pytest.mark.parametrize("model", [{}, None, {"schema_version": "99"}])
def test_invalid_models_fail(model):
    with pytest.raises(ValueError, match="invalid model"):
        render_docs(model)


def test_validate_before_redact_does_not_disclose_diagnostics(shop, monkeypatch):
    shop["nodes"][0]["secret"] = "must-not-appear"

    def forbidden(_):
        pytest.fail("Redaction must not run before validation rejects raw input")

    monkeypatch.setattr("lsm.documentation.redact", forbidden)
    with pytest.raises(ValueError) as error:
        render_docs(shop)
    assert "must-not-appear" not in str(error.value)


def test_entire_model_passes_redaction_boundary(shop, monkeypatch):
    seen = []

    def redact_all(model):
        seen.append(copy.deepcopy(model))
        clean = copy.deepcopy(model)
        clean["model"]["title"] = "REDACTED MODEL"
        clean["nodes"][0]["title"] = "REDACTED NODE"
        clean["edges"][0]["provenance"]["source"] = "REDACTED SOURCE"
        return clean

    monkeypatch.setattr("lsm.documentation.redact", redact_all)
    output = render_docs(shop)
    assert seen == [shop]
    assert "REDACTED MODEL" in output["index.md"]
    assert "REDACTED NODE" in output["index.md"]
    assert "REDACTED SOURCE" in output["index.md"]


def test_secrets_in_titles_sources_and_uris_are_not_output(shop):
    token = "ghp_" + "A" * 36
    shop["model"]["title"] = "Shop " + token
    for node in shop["nodes"]:
        node["title"] += " " + token
        node["provenance"]["source"] = "https://example.invalid/?token=" + token
        if "uri" in node:
            node["uri"] = "https://example.invalid/?token=" + token
    for edge in shop["edges"]:
        edge["provenance"]["source"] = "token=" + token
        edge["provenance"]["rationale"] = token
    rendered = render_docs(shop)
    for text in rendered.values():
        assert token not in text
        assert "A" * 36 not in text


def test_markdown_and_mermaid_injection_is_inert(shop):
    attack = (
        '"]\nclick n0001 "javascript:alert(1)"\n'
        '%%{init: {"securityLevel":"loose"}}%%\n'
        "<script>alert(1)</script><img src=x onerror=alert(1)>"
        "[link](javascript:alert(1)) ` ``` &quot; &#34; \u202e"
    )
    shop["model"]["title"] = attack
    for node in shop["nodes"]:
        node["title"] = attack
        node["description"] = attack
        node["provenance"]["source"] = attack
        node["provenance"]["rationale"] = attack
        if "uri" in node:
            node["uri"] = "data:text/html," + attack
    for edge in shop["edges"]:
        edge["provenance"]["source"] = attack
    output = render_docs(shop)
    for filename, text in output.items():
        assert "<script>" not in text
        assert "<img" not in text
        assert "```" not in text
        assert "\u202e" not in text
        assert "%%{init" not in text
        assert "\nclick " not in text
        if filename.endswith(".md"):
            assert "[link](javascript:" not in text
            assert "data:text/html" not in text
            links = re.findall(r"\]\(([^)]+)\)", text)
            assert set(links) <= FILENAMES
        else:
            assert "&quot;" not in text
            assert "&#34;" not in text
            for line in text.splitlines()[2:]:
                if "[" in line:
                    assert re.match(r'^  n\d{4}\["[^"\n]*"\]$', line)
                else:
                    assert re.match(r'^  n\d{4} -->\|"[^"\n]*"\| n\d{4}$', line)


def test_explicit_trace_and_model_gaps(shop):
    trace = render_docs(shop)["traceability.md"]
    # Stable IDs are escaped text, not raw Markdown or generated node IDs.
    assert "implementation&#46;notes" in trace
    assert "edge&#46;satisfies" in trace
    assert "edge&#46;implemented&#45;by" in trace
    assert "test&#46;notes" in trace
    assert "Gap: no implementation node" in trace  # superseded draft
    assert "Gap: no verified_by" in trace
    assert "Should mobile support offline edits" in trace
    assert "not proof of execution" in trace


def test_missing_implementation_is_not_inferred_from_dependencies(shop):
    shop["edges"] = [edge for edge in shop["edges"] if edge["type"] != "implemented_by"]
    trace = render_docs(shop)["traceability.md"]
    assert "implementation&#46;notes" not in trace
    assert trace.count("Gap: no implementation node") == 2


def test_verified_is_only_a_model_declaration(shop):
    node = next(node for node in shop["nodes"] if node["id"] == "implementation.notes")
    node["provenance"]["verification"] = "verified"
    output = render_docs(shop)
    assert "verification&#61;verified &#40;model declaration&#41;" in output["index.md"]
    assert "does not authenticate" in output["traceability.md"]


def test_invalid_graph_reference_is_rejected(shop):
    shop["edges"][0]["target"] = "requirement.missing"
    with pytest.raises(ValueError, match="invalid model"):
        render_docs(shop)


def test_redacted_identifiers_do_not_break_graph_lookups(shop):
    old = "component.backend"
    identifier = "component.sk-abcdefghijklmnop"
    for node in shop["nodes"]:
        if node["id"] == old:
            node["id"] = identifier
    for edge in shop["edges"]:
        for endpoint in ("source", "target"):
            if edge[endpoint] == old:
                edge[endpoint] = identifier
    output = render_docs(shop)
    for text in output.values():
        assert "abcdefghijklmnop" not in text
    shop["nodes"].reverse()
    shop["edges"].reverse()
    assert render_docs(shop) == output


def test_trace_cycles_are_bounded(shop):
    provenance = {"origin": "declared", "source": "cycle fixture", "verification": "unverified"}
    shop["edges"].extend(
        [
            {
                "id": "edge.cycle-out",
                "type": "implemented_by",
                "source": "requirement.notes",
                "target": "component.backend",
                "provenance": provenance,
            },
            {
                "id": "edge.cycle-self",
                "type": "implemented_by",
                "source": "component.backend",
                "target": "component.backend",
                "provenance": provenance,
            },
        ]
    )
    assert "implementation&#46;notes" in render_docs(shop)["traceability.md"]


def test_empty_model_has_honest_unknowns():
    output = render_docs(
        {
            "schema_version": "1.0",
            "model": {"id": "model.empty", "title": "Empty"},
            "nodes": [],
            "edges": [],
        }
    )
    assert "coverage are unknown" in output["traceability.md"]
    assert "None recorded" in output["onboarding.md"]
    assert "No matching nodes recorded" in output["context.mmd"]
