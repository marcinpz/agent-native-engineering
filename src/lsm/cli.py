"""Small offline CLI for importing and inspecting Living System Models."""

import argparse
import json
import sys
from pathlib import Path

from lsm.operations_cli import configure, dispatch
from lsm.storage import ModelIOError, load_model, save_model
from lsm.validation import validate_model


def _parser():
    parser = argparse.ArgumentParser(prog="lsm", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create an empty, valid model")
    init.add_argument("path", type=Path)
    init.add_argument("--id", default="system:example")
    init.add_argument("--title", default="New system")
    init.add_argument("--force", action="store_true")
    importer = commands.add_parser("import", help="validate and copy a JSON/YAML model")
    importer.add_argument("source", type=Path)
    importer.add_argument("destination", type=Path)
    importer.add_argument("--force", action="store_true")
    validator = commands.add_parser("validate", help="validate structure and graph links")
    validator.add_argument("path", type=Path)
    validator.add_argument("--json", action="store_true", dest="json_output")
    inspector = commands.add_parser("inspect", aliases=["show"], help="summarize or show a node")
    inspector.add_argument("path", type=Path)
    inspector.add_argument("--node", help="stable node ID")
    inspector.add_argument("--json", action="store_true", dest="json_output")
    configure(commands)
    return parser


def _emit_errors(errors, json_output=False):
    if json_output:
        print(json.dumps({"valid": False, "errors": errors}, sort_keys=True))
    else:
        for error in errors:
            print(f"{error['code']} at {error['path'] or '/'}: {error['message']}", file=sys.stderr)


def _write(model, path, force):
    if path.exists() and not force:
        raise ModelIOError(f"Destination exists: {path}; use --force to overwrite")
    errors = validate_model(model)
    if errors:
        _emit_errors(errors)
        return 1
    save_model(model, path)
    print(f"Saved {path}")
    return 0


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        result = dispatch(args)
        if result is not None:
            return result
        if args.command == "init":
            model = {
                "schema_version": "1.0",
                "model": {"id": args.id, "title": args.title},
                "nodes": [],
                "edges": [],
            }
            return _write(model, args.path, args.force)
        if args.command == "import":
            return _write(load_model(args.source), args.destination, args.force)
        model = load_model(args.path)
        errors = validate_model(model)
        if errors:
            _emit_errors(errors, args.json_output)
            return 1
        if args.command == "validate":
            if args.json_output:
                print(json.dumps({"valid": True, "errors": []}))
            else:
                print("Valid model (structure and references only; evidence not authenticated).")
            return 0
        if args.node:
            node = next((node for node in model["nodes"] if node["id"] == args.node), None)
            if node is None:
                _emit_errors(
                    [{"code": "node_not_found", "path": "/nodes", "message": args.node}],
                    args.json_output,
                )
                return 1
            print(json.dumps(node, indent=2, sort_keys=True))
        else:
            summary = {
                "schema_version": model["schema_version"],
                "model": model["model"],
                "nodes": len(model["nodes"]),
                "edges": len(model["edges"]),
                "node_types": {
                    kind: sum(node["type"] == kind for node in model["nodes"])
                    for kind in sorted({node["type"] for node in model["nodes"]})
                },
            }
            if args.json_output:
                print(json.dumps(summary, indent=2, sort_keys=True))
            else:
                print(f"{summary['model']['title']} ({summary['model']['id']})")
                print(
                    f"Schema {summary['schema_version']}; {summary['nodes']} nodes; "
                    f"{summary['edges']} edges"
                )
                for kind, count in summary["node_types"].items():
                    print(f"  {kind}: {count}")
        return 0
    except ModelIOError as exc:
        if getattr(args, "json_output", False):
            _emit_errors([{"code": "io_error", "path": "", "message": str(exc)}], True)
        else:
            print(f"I/O error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        from lsm.security import redact

        _emit_errors(
            [{"code": "operation_error", "path": "", "message": redact(str(exc))}],
            getattr(args, "json_output", False),
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
