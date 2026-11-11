"""Small offline CLI for importing and inspecting Living System Models."""

import argparse
import json
import sys
from pathlib import Path

from lsm.operations_cli import configure, dispatch
from lsm.security import redact
from lsm.storage import ModelIOError, load_model, save_model
from lsm.validation import validate_model


class _RedactingParser(argparse.ArgumentParser):
    def error(self, message):
        super().error(redact(message))


def _parser():
    parser = _RedactingParser(prog="lsm", description=__doc__)
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
    junit = commands.add_parser(
        "import-junit", help="read an existing JUnit report; never run tests"
    )
    junit.add_argument("path", type=Path)
    junit.add_argument("--repository", required=True, help="explicit repository model ID")
    junit.add_argument("--commit", required=True, help="user-attested full source commit hash")
    evaluation = commands.add_parser("evaluate-junit", help="read-only explicit evidence mapping")
    evaluation.add_argument("path", type=Path)
    evaluation.add_argument("--model", required=True, type=Path)
    evaluation.add_argument("--mapping", required=True, type=Path)
    evaluation.add_argument("--repository", required=True)
    evaluation.add_argument("--commit", required=True)
    evaluation.add_argument("--expected-commit", required=True)
    return parser


def _emit_errors(errors, json_output=False):
    # Schema messages can contain reprs of entire invalid, secret-bearing values.
    # Retain diagnostic locations/codes without projecting those raw values.
    errors = redact(
        [
            {**error, "message": "Model schema constraint failed"}
            if error["code"] == "schema_error"
            else error
            for error in errors
        ]
    )
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
    print(redact(f"Saved {path}"))
    return 0


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "evaluate-junit":
            from lsm.evidence import evaluate_junit

            result = evaluate_junit(
                args.path,
                model=load_model(args.model),
                mapping=load_model(args.mapping),
                repository=args.repository,
                commit=args.commit,
                expected_commit=args.expected_commit,
            )
            print(json.dumps(result, sort_keys=True))
            return 0 if result["status"] == "succeeded" else 1
        if args.command == "import-junit":
            from lsm.junit import import_junit

            result = import_junit(args.path, repository=args.repository, commit=args.commit)
            print(json.dumps(result, sort_keys=True))
            return 0 if result["status"] == "succeeded" else 1
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
            print(json.dumps(redact(node), indent=2, sort_keys=True))
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
            summary = redact(summary)
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
    except (ModelIOError, OSError) as exc:
        # Parser/loader diagnostics may quote arbitrary source lines, not merely
        # recognizable credentials. Filesystem failures remain actionable.
        message = (
            "Cannot read or write model; check document syntax, encoding and content"
            if exc.__cause__ is not None and not isinstance(exc.__cause__, OSError)
            else redact(str(exc))
        )
        if getattr(args, "json_output", False):
            _emit_errors([{"code": "io_error", "path": "", "message": message}], True)
        else:
            print(f"I/O error: {message}", file=sys.stderr)
        return 2
    except ValueError as exc:
        _emit_errors(
            [{"code": "operation_error", "path": "", "message": redact(str(exc))}],
            getattr(args, "json_output", False),
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
