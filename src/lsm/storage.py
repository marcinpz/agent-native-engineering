"""Strict, portable JSON/YAML persistence for Living System Models."""

import json
import math
import os
import re
import tempfile
from pathlib import Path

import yaml


class ModelIOError(Exception):
    """A model could not be read or written safely."""


class _ModelLoader(yaml.SafeLoader):
    """Use JSON-like scalars, not YAML 1.1 dates, octal or yes/no booleans."""

    def construct_object(self, node, deep=False):
        try:
            return super().construct_object(node, deep=deep)
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise yaml.constructor.ConstructorError(
                None, None, f"Invalid value for YAML tag {node.tag}: {exc}", node.start_mark
            ) from exc


_ModelLoader.yaml_implicit_resolvers = {
    key: [
        (tag, pattern)
        for tag, pattern in resolvers
        if tag
        not in {
            "tag:yaml.org,2002:bool",
            "tag:yaml.org,2002:timestamp",
            "tag:yaml.org,2002:int",
            "tag:yaml.org,2002:float",
        }
    ]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_ModelLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$"), list("tf")
)
_ModelLoader.add_implicit_resolver(
    "tag:yaml.org,2002:int", re.compile(r"^-?(?:0|[1-9][0-9]*)$"), list("-0123456789")
)
_ModelLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+(?:[eE][+-]?[0-9]+)?|[eE][+-]?[0-9]+)$"),
    list("-0123456789"),
)
_ModelLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(r"^[+-]?\.(?:inf|Inf|INF|nan|NaN|NAN)$"),
    list("+-."),
)


class _ModelDumper(yaml.SafeDumper):
    """Quote strings using the same scalar semantics as the model loader."""


_ModelDumper.yaml_implicit_resolvers = {
    key: list(resolvers) for key, resolvers in _ModelLoader.yaml_implicit_resolvers.items()
}


def _yaml_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ModelIOError("YAML mapping keys must be strings")
        if key in result:
            raise ModelIOError(f"Duplicate mapping key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_ModelLoader.add_constructor("tag:yaml.org,2002:map", _yaml_mapping)


def _json_mapping(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ModelIOError(f"Duplicate mapping key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ModelIOError(f"Non-finite number is not JSON-compatible: {value}")


def _check_json_tree(value, path="", ancestors=None):
    """Reject lossy encodings, non-finite floats, and recursive aliases."""
    if ancestors is None:
        ancestors = set()
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ModelIOError(f"Non-finite number at {path or '/'}")
        return
    if type(value) not in (dict, list):
        raise ModelIOError(f"Non-JSON value ({type(value).__name__}) at {path or '/'}")
    if id(value) in ancestors:
        raise ModelIOError(f"Recursive alias or container at {path or '/'}")
    ancestors.add(id(value))
    try:
        entries = value.items() if isinstance(value, dict) else enumerate(value)
        for key, child in entries:
            if isinstance(value, dict) and not isinstance(key, str):
                raise ModelIOError(f"Mapping keys must be strings at {path or '/'}")
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            _check_json_tree(child, f"{path}/{escaped}", ancestors)
    finally:
        ancestors.remove(id(value))


def _format(path):
    suffix = path.suffix.lower()
    if suffix not in {".json", ".yaml", ".yml"}:
        raise ModelIOError(f"Unsupported model format {suffix!r}; use .json, .yaml or .yml")
    return suffix


def load_model(path) -> dict:
    """Load a model without interpreting or changing its declared claims."""
    path = Path(path)
    suffix = _format(path)
    try:
        text = path.read_text(encoding="utf-8")
        if suffix == ".json":
            model = json.loads(
                text, object_pairs_hook=_json_mapping, parse_constant=_reject_constant
            )
        else:
            model = yaml.load(text, Loader=_ModelLoader)
        _check_json_tree(model)
        if not isinstance(model, dict):
            raise ModelIOError("The model document must be an object/mapping")
        return model
    except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError, ModelIOError) as exc:
        raise ModelIOError(f"Cannot load model {path}: {exc}") from exc


def save_model(model, path) -> None:
    """Write deterministic output atomically, without mutating the model."""
    path = Path(path)
    suffix = _format(path)
    temporary = None
    try:
        _check_json_tree(model)
        if not isinstance(model, dict):
            raise ModelIOError("The model document must be an object/mapping")
        if suffix == ".json":
            text = json.dumps(model, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
            text += "\n"
        else:
            text = yaml.dump(
                model,
                Dumper=_ModelDumper,
                sort_keys=True,
                allow_unicode=True,
                default_flow_style=False,
            )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError, ModelIOError) as exc:
        raise ModelIOError(f"Cannot save model {path}: {exc}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                # Do not hide an actionable write error if best-effort cleanup fails.
                pass
