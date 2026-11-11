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
    context = commands.add_parser("context", help="compile bounded, cited task context")
    context.add_argument("path", type=Path)
    context.add_argument("--task", required=True)
    context.add_argument("--seed", action="append", required=True, dest="seed_ids")
    context.add_argument("--budget", type=int, default=8192)
    benchmark = commands.add_parser("benchmark", help="offline smoke or supplied-trial summary")
    experiments = benchmark.add_subparsers(dest="benchmark_command", required=True)
    smoke = experiments.add_parser("smoke")
    smoke.add_argument("path", type=Path)
    smoke.add_argument("--task", required=True)
    smoke.add_argument("--seed", action="append", required=True, dest="seed_ids")
    smoke.add_argument("--budget", type=int, default=8192)
    smoke.add_argument("--output", type=Path)
    smoke.add_argument("--force", action="store_true")
    summarize = experiments.add_parser("summarize")
    summarize.add_argument("source", type=Path)
    workflow = commands.add_parser("workflow", help="operate only newly generated local demo repos")
    steps = workflow.add_subparsers(dest="workflow_command", required=True)
    initializer = steps.add_parser("init")
    initializer.add_argument("root", type=Path)
    runner = steps.add_parser("run")
    runner.add_argument("root", type=Path)
    runner.add_argument("proposal", type=Path)
    runner.add_argument("--policy", required=True, type=Path)
    runner.add_argument("--actor", required=True)
    runner.add_argument("--actor-kind", choices=["human", "agent"], default="human")
    runner.add_argument("--output", required=True, type=Path)
    runner.add_argument("--fail-component", choices=["backend", "web", "mobile", "store"])
    reconcile = steps.add_parser("reconcile")
    reconcile.add_argument("root", type=Path)
    reconcile.add_argument("record", type=Path)


def write_document(document, destination, force=False):
    if destination.is_symlink() or (destination.exists() and not force):
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
    if args.command == "context":
        import sys

        from lsm.context import compile_context, serialize_context

        pack = compile_context(load_model(args.path), args.task, args.seed_ids, args.budget)
        sys.stdout.write(serialize_context(pack))
        return 0
    if args.command == "benchmark":
        import json

        from lsm.benchmark import run_smoke, summarize_trials

        if args.benchmark_command == "smoke":
            record = run_smoke(load_model(args.path), args.task, args.seed_ids, args.budget)
            if args.output:
                write_document(record, args.output, args.force)
                print(f"Saved {args.output}")
                return 0
        else:
            record = summarize_trials(load_model(args.source))
        print(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        return 0
    if args.command == "workflow":
        import json

        from lsm.workflow import init_demo, reconcile_demo, run_demo

        if args.workflow_command == "init":
            record = init_demo(args.root)
        elif args.workflow_command == "run":
            if args.output.exists() or args.output.is_symlink():
                raise ModelIOError("Execution record destination already exists")
            if not args.output.parent.is_dir():
                raise ModelIOError("Execution record destination parent must already exist")
            root = args.root.resolve()
            if args.output.resolve().is_relative_to(root):
                raise ValueError("Execution records must be outside the demo root")
            record = run_demo(
                args.root,
                load_model(args.proposal),
                load_model(args.policy),
                args.actor,
                args.actor_kind,
                args.fail_component,
            )
            try:
                write_document(record, args.output)
            except (ModelIOError, OSError):
                # Preserve actual execution evidence even if the requested disk
                # destination fails after the demo repositories were changed.
                print(json.dumps(record, sort_keys=True, separators=(",", ":")))
                raise
            print(f"Saved {args.output}")
            return int(record["state"] != "succeeded")
        else:
            record = reconcile_demo(args.root, load_model(args.record))
            print(json.dumps(record, sort_keys=True, separators=(",", ":")))
            return int(not record.get("verified", False))
        print(json.dumps(record, sort_keys=True, separators=(",", ":")))
        return 0
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
