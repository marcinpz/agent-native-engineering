"""Joined-model trust/compatibility regressions, not tests of real app behavior."""

import copy
import html
import json

import pytest

from lsm.cli import main
from lsm.context import compile_context, serialize_context
from lsm.discovery import discover
from lsm.documentation import render_docs
from lsm.migrations import migrate_model
from lsm.security import check_transition
from lsm.storage import load_model, save_model
from lsm.validation import validate_model
from lsm.workflow import init_demo


@pytest.fixture
def joined(tmp_path):
    root = tmp_path / "generated"
    init_demo(root)
    seed = load_model("examples/integration/seed-model.json")
    manifest = load_model("examples/discovery/manifest.json")
    return root, seed, manifest, discover(manifest, root, seed)


@pytest.mark.parametrize("version", ["1.0", "1.1"])
def test_one_model_retains_intent_inference_citations_and_redaction(
    joined, tmp_path, capsys, version
):
    root, seed, manifest, imported = joined
    model = migrate_model(imported, version)
    assert validate_model(model) == []
    assert model["nodes"] == imported["nodes"]
    assert model["edges"] == imported["edges"]
    if version == "1.0":
        assert discover(manifest, root, model) == model
    assert seed == load_model("examples/integration/seed-model.json")
    path = tmp_path / "joined.json"
    save_model(model, path)
    assert main(["inspect", str(path), "--node", "requirement.demo-sync", "--json"]) == 0
    displayed = json.loads(capsys.readouterr().out)
    assert displayed["approval"] == "pending"
    assert displayed["provenance"]["origin"] == "declared"
    assert "ane-integration-probe-only" not in json.dumps(displayed)
    inferred = next(node for node in model["nodes"] if node["id"] == "implementation.demo-sync")
    assert inferred["provenance"]["origin"] == "inferred"
    assert inferred["provenance"]["verification"] == "unverified"
    docs = render_docs(model)
    text = html.unescape(docs["traceability.md"])
    assert all(
        identifier in text
        for identifier in ("requirement.demo-sync", "implementation.demo-sync", "test.demo-sync")
    )
    assert "pending" in text and "inferred" in text and "unverified" in text
    assert "examples/integration/README.md" in text
    assert "ane-integration-probe-only" not in html.unescape("".join(docs.values()))
    pack = compile_context(model, "Inspect queued edits", ["requirement.demo-sync"], 8192)
    assert "ane-integration-probe-only" not in serialize_context(pack)
    reordered = copy.deepcopy(model)
    reordered["nodes"].reverse()
    reordered["edges"].reverse()
    assert render_docs(reordered) == docs


@pytest.mark.parametrize("promotion", ["approval", "verification"])
def test_joined_model_cannot_promote_trust_as_an_agent(joined, promotion):
    _, _, _, before = joined
    after = copy.deepcopy(before)
    if promotion == "approval":
        node = next(node for node in after["nodes"] if node["type"] == "requirement")
        node["approval"] = "approved"
    else:
        node = next(node for node in after["nodes"] if node["type"] == "implementation")
        node["provenance"]["verification"] = "verified"
    assert validate_model(after) == []  # Structural declarations are not authorization.
    policy = load_model("examples/governance/policy.json")
    with pytest.raises(ValueError, match="denied"):
        check_transition(before, after, policy, "demo-owner", "agent")
    assert all(node.get("approval") != "approved" for node in before["nodes"])


def test_conflicting_discovery_fails_without_rewriting_declared_intent(joined):
    root, _, manifest, model = joined
    original = copy.deepcopy(model)
    conflicting = copy.deepcopy(manifest)
    conflicting["repositories"][0]["components"][0]["title"] = "Contradictory backend title"
    before = {
        path: path.read_bytes()
        for name in ("backend", "web", "mobile", "store")
        for path in (root / name).iterdir()
        if path.is_file()
    }
    with pytest.raises(ValueError, match="Conflicting"):
        discover(conflicting, root, model)
    assert model == original
    assert all(path.read_bytes() == content for path, content in before.items())


def test_discovery_1_1_input_is_an_explicit_known_boundary(joined):
    root, _, manifest, model = joined
    upgraded = migrate_model(model)
    with pytest.raises(ValueError, match="schema_version 1.0"):
        discover(manifest, root, upgraded)
    assert validate_model(upgraded) == []
