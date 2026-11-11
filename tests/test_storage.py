import copy
import json

import pytest
import yaml

from lsm.storage import ModelIOError, load_model, save_model
from lsm.validation import validate_model


def model():
    return {
        "schema_version": "1.0",
        "model": {"id": "sample", "title": "Sample café"},
        "nodes": [],
        "edges": [],
    }


@pytest.mark.parametrize("suffix", [".json", ".yaml", ".yml", ".JSON"])
def test_round_trip_is_stable_and_does_not_mutate(tmp_path, suffix):
    original = model()
    snapshot = copy.deepcopy(original)
    path = tmp_path / f"model{suffix}"
    save_model(original, path)
    first = path.read_bytes()
    loaded = load_model(path)
    assert loaded == original == snapshot
    save_model(loaded, path)
    assert path.read_bytes() == first
    assert first.endswith(b"\n")


@pytest.mark.parametrize("suffix", ["json", "yaml"])
def test_sorted_keys_independent_of_insertion_order(tmp_path, suffix):
    first, second = tmp_path / f"a.{suffix}", tmp_path / f"b.{suffix}"
    save_model({"z": {"y": 1, "a": 2}, "a": []}, first)
    save_model({"a": [], "z": {"a": 2, "y": 1}}, second)
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize("text", ["1e3", "1E3", "-1e-3", "1.2e3", "0e+3"])
def test_yaml_exponent_looking_string_keys_and_values_round_trip(tmp_path, text):
    path = tmp_path / "strings.yaml"
    original = {text: text, "nested": {text: [text]}}
    save_model(original, path)
    assert load_model(path) == original


def test_yaml_whole_valid_model_round_trip_with_exponent_looking_strings(tmp_path):
    original = model()
    original["model"]["title"] = "1e3"
    original["nodes"] = [
        {
            "id": "component",
            "type": "component",
            "title": "-1e-3",
            "version": 1,
            "description": "1.2e3",
            "provenance": {"origin": "declared", "source": "1E3", "verification": "unverified"},
        }
    ]
    assert validate_model(original) == []
    path = tmp_path / "model.yaml"
    save_model(original, path)
    loaded = load_model(path)
    assert loaded == original
    assert validate_model(loaded) == []


def test_model_yaml_resolvers_do_not_change_global_pyyaml_behavior(tmp_path):
    original = {"title": "1e3"}
    expected_dump = yaml.safe_dump(original)
    expected_load = yaml.safe_load("title: 1e3\nflag: yes\n")
    path = tmp_path / "model.yaml"
    save_model(original, path)
    assert load_model(path) == original
    assert yaml.safe_dump(original) == expected_dump
    assert yaml.safe_load("title: 1e3\nflag: yes\n") == expected_load
    assert expected_load == {"title": "1e3", "flag": True}


@pytest.mark.parametrize("scalar", ["!!bool garbage", '!!float ""', '!!int ""'])
def test_malformed_tagged_yaml_scalars_raise_actionable_model_io_error(tmp_path, scalar):
    path = tmp_path / "invalid.yaml"
    path.write_text(f"a: {scalar}\n", encoding="utf-8")
    with pytest.raises(ModelIOError, match="Cannot load model.*Invalid value for YAML tag"):
        load_model(path)


@pytest.mark.parametrize(
    "suffix,text",
    [
        ("json", '{"nodes": [], "nodes": []}'),
        ("json", '{"model": {"id": "a", "id": "b"}}'),
        ("yaml", "nodes: []\nnodes: []\n"),
        ("yaml", "model:\n  id: a\n  id: b\n"),
        ("yaml", "true: value\n"),
        ("yaml", "1: value\n"),
        ("yaml", "? [a, b]\n: value\n"),
        ("yaml", "value: !!python/object/apply:os.system ['touch unsafe']\n"),
        ("yaml", "value: !!binary SGVsbG8=\n"),
        ("yaml", "value: !!set {a: null}\n"),
        ("yaml", "value: !!timestamp 2026-01-01\n"),
        ("yaml", "value: &cycle [*cycle]\n"),
        ("yaml", "value: &cycle {child: *cycle}\n"),
        ("yaml", "---\na: 1\n---\na: 2\n"),
        ("json", '{"value": NaN}'),
        ("json", '{"value": Infinity}'),
        ("json", '{"value": 1e999}'),
        ("yaml", "value: 1e999\n"),
        ("yaml", "value: !!float .nan\n"),
        ("yaml", "value: .nan\n"),
        ("yaml", "value: -.inf\n"),
        ("yaml", "value: +.Inf\n"),
        ("json", "[]"),
        ("yaml", ""),
        ("json", "{broken"),
        ("yaml", "value: [\n"),
    ],
)
def test_rejects_unsafe_or_ambiguous_documents(tmp_path, suffix, text):
    path = tmp_path / f"bad.{suffix}"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ModelIOError, match="Cannot load model"):
        load_model(path)


def test_yaml_json_scalar_semantics_and_timestamp_preservation(tmp_path):
    path = tmp_path / "model.yaml"
    path.write_text(
        "timestamp: 2026-11-11T12:00:00Z\ndate: 2026-11-11\n"
        "yes: no\non: off\nleading: 012\nexponent: 1e3\nflag: true\n",
        encoding="utf-8",
    )
    assert load_model(path) == {
        "timestamp": "2026-11-11T12:00:00Z",
        "date": "2026-11-11",
        "yes": "no",
        "on": "off",
        "leading": "012",
        "exponent": 1000.0,
        "flag": True,
    }


def test_shared_nonrecursive_yaml_alias_is_allowed(tmp_path):
    path = tmp_path / "model.yaml"
    path.write_text("one: &shared {value: 1}\ntwo: *shared\n", encoding="utf-8")
    assert load_model(path) == {"one": {"value": 1}, "two": {"value": 1}}


@pytest.mark.parametrize(
    "bad",
    [
        {1: "key"},
        {"bad": {1, 2}},
        {"bad": (1, 2)},
        {"bad": object()},
        {"bad": float("nan")},
        {"bad": float("inf")},
        [],
    ],
)
@pytest.mark.parametrize("suffix", ["json", "yaml"])
def test_invalid_serialization_preserves_existing_destination(tmp_path, bad, suffix):
    path = tmp_path / f"model.{suffix}"
    path.write_text("original", encoding="utf-8")
    with pytest.raises(ModelIOError):
        save_model(bad, path)
    assert path.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.iterdir()) == [path]


def test_recursive_serialization_rejected(tmp_path):
    recursive = {}
    recursive["child"] = recursive
    with pytest.raises(ModelIOError, match="Recursive"):
        save_model(recursive, tmp_path / "model.json")


def test_unknown_formats_and_missing_files(tmp_path):
    with pytest.raises(ModelIOError, match="Unsupported model format"):
        save_model(model(), tmp_path / "model.txt")
    with pytest.raises(ModelIOError, match="Unsupported model format"):
        load_model(tmp_path / "model.txt")
    with pytest.raises(ModelIOError, match="Cannot load model"):
        load_model(tmp_path / "missing.json")
    with pytest.raises(ModelIOError, match="Cannot save model"):
        save_model(model(), tmp_path / "missing" / "model.json")


def test_invalid_utf8_is_actionable(tmp_path):
    path = tmp_path / "model.json"
    path.write_bytes(b"\xff")
    with pytest.raises(ModelIOError, match="Cannot load model"):
        load_model(path)


def test_failed_atomic_replace_preserves_destination_and_cleans_temp(tmp_path, monkeypatch):
    path = tmp_path / "model.json"
    path.write_text("original", encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr("lsm.storage.os.replace", fail_replace)
    with pytest.raises(ModelIOError, match="simulated replacement failure"):
        save_model(model(), path)
    assert path.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.iterdir()) == [path]


def test_json_output_has_sorted_keys(tmp_path):
    path = tmp_path / "model.json"
    save_model(model(), path)
    assert list(json.loads(path.read_text())) == ["edges", "model", "nodes", "schema_version"]
