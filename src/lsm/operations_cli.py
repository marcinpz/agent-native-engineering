"""Roadmap commands, isolated from the original minimal model CLI."""

from pathlib import Path

from lsm.storage import ModelIOError, load_model, save_model


def configure(commands):
    migration = commands.add_parser("migrate", help="explicitly upgrade a model schema")
    migration.add_argument("source", type=Path)
    migration.add_argument("destination", type=Path)
    migration.add_argument("--target", choices=["1.0", "1.1"], default="1.1")
    migration.add_argument("--force", action="store_true")
    exporter = commands.add_parser("export", help="generate cited Markdown and Mermaid views")
    exporter.add_argument("path", type=Path)
    exporter.add_argument("destination", type=Path)
    exporter.add_argument("--force", action="store_true")
    discovery = commands.add_parser("discover", help="import explicit local repository manifests")
    discovery.add_argument("manifest", type=Path)
    discovery.add_argument("destination", type=Path)
    discovery.add_argument("--base-dir", type=Path, required=True)
    discovery.add_argument("--existing", type=Path)
    discovery.add_argument("--force", action="store_true")
    requirements = commands.add_parser("requirement", help="refine and transition requirements")
    lifecycle = requirements.add_subparsers(dest="requirement_command", required=True)
    create = lifecycle.add_parser("create")
    create.add_argument("requirement_id")
    create.add_argument("destination", type=Path)
    create.add_argument("--intent", required=True)
    create.add_argument("--force", action="store_true")
    for name in ("refine", "transition", "validate"):
        operation = lifecycle.add_parser(name)
        operation.add_argument("source", type=Path)
        if name != "validate":
            operation.add_argument("destination", type=Path)
            operation.add_argument("--force", action="store_true")
        if name == "transition":
            operation.add_argument("--state", required=True)
            operation.add_argument("--policy", type=Path)
            operation.add_argument("--actor")
            operation.add_argument("--actor-kind", choices=["human", "agent"], default="human")
    changes = commands.add_parser("change", help="semantic diff, impact and proposal approval")
    actions = changes.add_subparsers(dest="change_command", required=True)
    propose = actions.add_parser("propose")
    propose.add_argument("before", type=Path)
    propose.add_argument("after", type=Path)
    propose.add_argument("destination", type=Path)
    propose.add_argument("--id", default="change:offline-sync")
    propose.add_argument("--force", action="store_true")
    approve = actions.add_parser("approve")
    approve.add_argument("source", type=Path)
    approve.add_argument("destination", type=Path)
    approve.add_argument("--policy", required=True, type=Path)
    approve.add_argument("--actor", required=True)
    approve.add_argument("--actor-kind", choices=["human", "agent"], default="human")
    approve.add_argument("--force", action="store_true")
    check = actions.add_parser("validate")
    check.add_argument("source", type=Path)


def write_document(document, destination, force=False):
    if destination.exists() and not force:
        raise ModelIOError(f"Destination exists: {destination}; use --force to overwrite")
    save_model(document, destination)


def write_projection(files, destination, force=False):
    if destination.is_symlink():
        raise ModelIOError("Projection destination must not be a symlink")
    for name in files:
        relative = Path(name)
        if relative.is_absolute() or len(relative.parts) != 1 or name in {".", ".."}:
            raise ValueError("Projection filenames must be plain relative filenames")
        path = destination / name
        if path.is_symlink() or (path.exists() and not force):
            raise ModelIOError("Projection file exists or is a symlink; choose a new directory")
    try:
        destination.mkdir(parents=True, exist_ok=True)
        for name, text in sorted(files.items()):
            (destination / name).write_text(text, encoding="utf-8")
    except OSError as exc:
        raise ModelIOError(f"Cannot write projection: {exc}") from exc


def dispatch(args):
    if args.command == "change":
        from lsm.changes import approve_proposal, create_proposal, validate_proposal

        if args.change_command == "propose":
            record = create_proposal(load_model(args.before), load_model(args.after), args.id)
        else:
            record = load_model(args.source)
            if args.change_command == "validate":
                import json

                errors = validate_proposal(record)
                print(json.dumps({"valid": not errors, "errors": errors}, sort_keys=True))
                return int(bool(errors))
            record = approve_proposal(record, load_model(args.policy), args.actor, args.actor_kind)
        write_document(record, args.destination, args.force)
        print(f"Saved {args.destination}")
        return 0
    if args.command == "requirement":
        from lsm.requirements import (
            create_requirement,
            refine_requirement,
            transition_requirement,
            validate_requirement,
        )

        if args.requirement_command == "create":
            record = create_requirement(args.requirement_id, args.intent)
        else:
            record = load_model(args.source)
            if args.requirement_command == "validate":
                import json

                from lsm.security import redact

                errors = validate_requirement(record)
                print(json.dumps(redact({"valid": not errors, "errors": errors}), sort_keys=True))
                return int(bool(errors))
            if args.requirement_command == "refine":
                record = refine_requirement(record)
            else:
                record = transition_requirement(
                    record,
                    args.state,
                    load_model(args.policy) if args.policy else None,
                    args.actor,
                    args.actor_kind,
                )
        write_document(record, args.destination, args.force)
        print(f"Saved {args.destination}")
        return 0
    if args.command == "migrate":
        from lsm.migrations import migrate_model

        write_document(
            migrate_model(load_model(args.source), args.target), args.destination, args.force
        )
        print(f"Saved {args.destination}")
        return 0
    if args.command == "export":
        from lsm.documentation import render_docs

        write_projection(render_docs(load_model(args.path)), args.destination, args.force)
        print(f"Generated documentation in {args.destination}")
        return 0
    if args.command == "discover":
        from lsm.discovery import discover

        model = discover(
            load_model(args.manifest),
            args.base_dir,
            load_model(args.existing) if args.existing else None,
        )
        write_document(model, args.destination, args.force)
        print(f"Saved {args.destination}")
        return 0
    return None
