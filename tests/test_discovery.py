"""Discovery fixtures are created locally; no nested Git metadata is checked in."""

import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from lsm.discovery import discover
from lsm.validation import validate_model


def git(root, *args):
    env = {
        "PATH": os.environ["PATH"],
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Discovery fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Discovery fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()


@pytest.fixture
def manifest(tmp_path):
    root = tmp_path / "backend"
    root.mkdir()
    git(root, "init")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "--allow-empty", "-m", "Fixture")
    # These files must never be opened, executed, or imported into the model.
    (root / ".env").write_text("DO_NOT_READ=secret", encoding="utf-8")
    (root / "malicious.sh").write_text("touch EXECUTED", encoding="utf-8")
    return {
        "schema_version": "1.0",
        "model": {"id": "system.demo", "title": "Demo"},
        "repositories": [
            {
                "id": "repo.backend",
                "title": "Backend",
                "path": "backend",
                "components": [
                    {
                        "id": "component.backend",
                        "title": "Backend",
                        "interfaces": [{"id": "interface.api", "title": "API"}],
                    }
                ],
            }
        ],
        "dependencies": [
            {"id": "dependency.api", "source": "component.backend", "target": "interface.api"}
        ],
    }


def snapshot(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def test_discover_idempotence_provenance_and_immutability(manifest, tmp_path):
    original = deepcopy(manifest)
    before = snapshot(tmp_path)
    result = discover(manifest, tmp_path)
    assert validate_model(result) == []
    assert manifest == original
    assert snapshot(tmp_path) == before
    assert len(result["nodes"]) == 3
    assert [edge["type"] for edge in result["edges"]] == [
        "belongs_to",
        "belongs_to",
        "exposes",
        "depends_on",
    ]
    repository = result["nodes"][0]
    assert repository["provenance"]["origin"] == "observed"
    assert git(tmp_path / "backend", "rev-parse", "HEAD") in repository["provenance"]["source"]
    assert "commit" not in repository
    assert all(
        item["provenance"]["origin"] == "declared" for item in result["nodes"][1:] + result["edges"]
    )
    assert all(
        item["provenance"]["verification"] == "unverified"
        for item in result["nodes"] + result["edges"]
    )
    existing = deepcopy(result)
    assert discover(manifest, tmp_path, result) == result
    assert result == existing
    assert discover(manifest, tmp_path) == result
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/etc",
        "../backend",
        "a/../backend",
        "./backend",
        "backend/.",
        "a//b",
        "backend/",
        "C:/repo",
        "C:\\repo",
        "a\\b",
        "a\x00b",
        "a\nb",
    ],
)
def test_reject_malformed_paths(manifest, tmp_path, path):
    manifest["repositories"][0]["path"] = path
    with pytest.raises(ValueError, match="manifest"):
        discover(manifest, tmp_path)


@pytest.mark.parametrize("location", ["root", "parent", "metadata", "head"])
def test_reject_symlinks(manifest, tmp_path, location):
    root = tmp_path / "backend"
    if location == "root":
        (tmp_path / "link").symlink_to(root, target_is_directory=True)
        manifest["repositories"][0]["path"] = "link"
    elif location == "parent":
        (tmp_path / "link").symlink_to(tmp_path, target_is_directory=True)
        manifest["repositories"][0]["path"] = "link/backend"
    elif location == "metadata":
        (root / ".git").rename(root / "metadata")
        (root / ".git").symlink_to(root / "metadata", target_is_directory=True)
    else:
        head = root / ".git" / "HEAD"
        head.rename(root / ".git" / "saved-head")
        head.symlink_to(root / ".git" / "saved-head")
    with pytest.raises(ValueError, match="Symlink"):
        discover(manifest, tmp_path)


def test_reject_external_gitdir_and_common_dir(manifest, tmp_path):
    root = tmp_path / "backend"
    (root / ".git").rename(tmp_path / "metadata")
    (root / ".git").write_text("gitdir: /outside/base\n", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes base_dir"):
        discover(manifest, tmp_path)
    (root / ".git").write_text("gitdir: ../metadata\n", encoding="utf-8")
    (tmp_path / "metadata" / "commondir").write_text("../../outside\n", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes base_dir"):
        discover(manifest, tmp_path)


def test_reject_external_config_include(manifest, tmp_path):
    config = tmp_path / "backend" / ".git" / "config"
    with config.open("a", encoding="utf-8") as stream:
        stream.write("\n[include]\n path = /outside/secret\n")
    with pytest.raises(ValueError, match="configuration includes"):
        discover(manifest, tmp_path)


def test_real_git_roots_and_committed_head_required(manifest, tmp_path):
    root = tmp_path / "plain"
    root.mkdir()
    manifest["repositories"][0]["path"] = "plain"
    with pytest.raises(ValueError, match="metadata directory"):
        discover(manifest, tmp_path)
    git(root, "init")
    with pytest.raises(ValueError, match="committed HEAD"):
        discover(manifest, tmp_path)


@pytest.mark.parametrize("field", ["id", "source", "target"])
def test_duplicate_ids_and_wrong_refs(manifest, tmp_path, field):
    manifest["dependencies"][0][field] = "repo.backend" if field == "id" else "missing.node"
    before = snapshot(tmp_path)
    original = deepcopy(manifest)
    with pytest.raises(ValueError, match="ID|does not exist"):
        discover(manifest, tmp_path)
    assert snapshot(tmp_path) == before
    assert manifest == original


def test_duplicates_across_repositories_and_generated_edges(manifest, tmp_path):
    manifest["repositories"][0]["components"].append({"id": "interface.api", "title": "Duplicate"})
    with pytest.raises(ValueError, match="Duplicate/conflicting"):
        discover(manifest, tmp_path)
    manifest["repositories"][0]["components"].pop()
    manifest["dependencies"][0]["id"] = "discovery:belongs_to:17:component.backend:repo.backend"
    with pytest.raises(ValueError, match="Duplicate/conflicting"):
        discover(manifest, tmp_path)


def test_existing_conflict_and_invalid_model(manifest, tmp_path):
    existing = discover(manifest, tmp_path)
    existing["nodes"][0]["title"] = "Do not overwrite"
    original = deepcopy(existing)
    with pytest.raises(ValueError, match="Conflicting existing entity ID"):
        discover(manifest, tmp_path, existing)
    assert existing == original
    with pytest.raises(ValueError, match="existing model"):
        discover(manifest, tmp_path, {"nodes": []})
    existing["model"]["title"] = "Different model"
    with pytest.raises(ValueError, match="identity/title"):
        discover(manifest, tmp_path, existing)


def test_dependencies_can_reference_existing_nodes(manifest, tmp_path):
    existing = discover(manifest, tmp_path)
    minimal = {key: deepcopy(value) for key, value in manifest.items() if key != "dependencies"}
    minimal["repositories"] = []
    minimal["dependencies"] = [
        {"id": "edge.additional", "source": "repo.backend", "target": "interface.api"}
    ]
    result = discover(minimal, tmp_path, existing)
    assert len(result["edges"]) == len(existing["edges"]) + 1
    assert validate_model(result) == []


@pytest.mark.parametrize("change", ["version", "unknown", "type", "shape", "duplicate_path"])
def test_manifest_rejects_malformed_input(manifest, tmp_path, change):
    if change == "version":
        manifest["schema_version"] = "9.0"
    elif change == "unknown":
        manifest["repositories"][0]["secrets"] = True
    elif change == "type":
        manifest["repositories"][0]["components"][0]["type"] = "evidence"
    elif change == "shape":
        manifest["repositories"] = None
    else:
        manifest["repositories"].append(deepcopy(manifest["repositories"][0]))
    with pytest.raises(ValueError):
        discover(manifest, tmp_path)


def test_git_environment_not_inherited(manifest, tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_DIR", "/nonexistent")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.bare")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    assert validate_model(discover(manifest, tmp_path)) == []


@pytest.mark.parametrize("kind", ["component", "interface", "implementation", "test"])
def test_explicit_repository_owned_types(manifest, tmp_path, kind):
    manifest["repositories"][0]["components"] = [
        {"id": "node.explicit", "title": "Explicit type", "type": kind}
    ]
    manifest["dependencies"] = []
    result = discover(manifest, tmp_path)
    assert result["nodes"][1]["type"] == kind
    assert result["edges"][0]["type"] == "belongs_to"
    if kind != "component":
        manifest["repositories"][0]["components"][0]["interfaces"] = []
        with pytest.raises(ValueError, match="manifest"):
            discover(manifest, tmp_path)


def test_internal_gitdir_pointer(manifest, tmp_path):
    root = tmp_path / "backend"
    (root / ".git").rename(tmp_path / "metadata")
    (root / ".git").write_text("gitdir: ../metadata\n", encoding="utf-8")
    assert validate_model(discover(manifest, tmp_path)) == []


def test_never_open_application_files(manifest, tmp_path, monkeypatch):
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path.is_relative_to(tmp_path / "backend") and ".git" not in path.parts:
            pytest.fail(f"Discovery tried opening application data: {path}")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    assert validate_model(discover(manifest, tmp_path)) == []


@pytest.mark.parametrize("manifest", [None, [], {}, {"schema_version": "1.0"}])
def test_invalid_manifest_shapes(manifest, tmp_path):
    with pytest.raises(ValueError, match="manifest"):
        discover(manifest, tmp_path)


def test_missing_git_actionable_error(manifest, tmp_path, monkeypatch):
    monkeypatch.setattr("lsm.discovery.shutil.which", lambda _: None)
    with pytest.raises(ValueError, match="Git is required"):
        discover(manifest, tmp_path)


def test_sample_manifest_schema_and_discovery(tmp_path):
    schema = json.loads(Path("src/lsm/schemas/discovery.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    sample = json.loads(Path("examples/discovery/manifest.json").read_text())
    assert list(Draft202012Validator(schema).iter_errors(sample)) == []
    for repo in sample["repositories"]:
        root = tmp_path / repo["path"]
        root.mkdir(parents=True)
        git(root, "init")
        git(root, "-c", "core.hooksPath=/dev/null", "commit", "--allow-empty", "-m", "Fixture")
    result = discover(sample, tmp_path)
    assert validate_model(result) == []
    assert len([node for node in result["nodes"] if node["type"] == "repository"]) == 4
    assert discover(sample, tmp_path, result) == result
