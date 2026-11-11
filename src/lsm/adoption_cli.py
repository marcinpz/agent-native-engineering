"""Explicit read-only provider calls and opt-in ANE metadata operations."""

import json
from pathlib import Path

from lsm.security import redact
from lsm.storage import ModelIOError, load_model, save_model


def configure(commands):
    providers = commands.add_parser(
        "provider", help="inspect or invoke read-only provider capabilities"
    )
    providers.set_defaults(json_output=True)
    operations = providers.add_subparsers(dest="provider_command", required=True)
    operations.add_parser("capabilities")
    discover = operations.add_parser("discover")
    discover.add_argument("manifest", type=Path)
    discover.add_argument("--base-dir", type=Path, required=True)
    discover.add_argument(
        "--replay", type=Path, help="replace native Git with a validated mock model"
    )
    discover.add_argument("--output", type=Path, help="save raw local result; stdout is redacted")

    workspaces = commands.add_parser("workspace", help="manage only opt-in .ane metadata")
    workspaces.set_defaults(json_output=True)
    actions = workspaces.add_subparsers(dest="workspace_command", required=True)
    init = actions.add_parser("init")
    init.add_argument("manifest", type=Path)
    init.add_argument("directory", type=Path)
    init.add_argument("--base-dir", type=Path, required=True)
    init.add_argument("--task", default="Onboard system")
    init.add_argument("--seed", action="append", dest="seed_ids")
    init.add_argument("--budget", type=int, default=8192)
    refresh = actions.add_parser("refresh")
    refresh.add_argument("directory", type=Path)
    refresh.add_argument("--base-dir", type=Path, required=True)
    refresh.add_argument(
        "--apply", action="store_true", help="update managed metadata after reviewing diff"
    )
    status = actions.add_parser("status")
    status.add_argument("directory", type=Path)
    clean = actions.add_parser("clean")
    clean.add_argument("directory", type=Path)
    clean.add_argument(
        "--apply", action="store_true", help="delete only unchanged ANE-owned metadata"
    )


def _display(value):
    print(json.dumps(redact(value), sort_keys=True, ensure_ascii=False))


def dispatch(args):
    if args.command == "provider":
        from lsm.providers import GitProvider, MockProvider, invoke

        if args.provider_command == "capabilities":
            _display(GitProvider().describe())
            return 0
        provider = MockProvider(load_model(args.replay)) if args.replay else GitProvider()
        result = invoke(
            provider, "discover", manifest=load_model(args.manifest), base_dir=args.base_dir
        )
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise ModelIOError("Provider result destination already exists")
            save_model(result, args.output)
        _display(result)
        return int(result["status"] != "succeeded")
    if args.command == "workspace":
        from lsm.workspace import (
            cleanup_workspace,
            init_workspace,
            refresh_workspace,
            workspace_status,
        )

        if args.workspace_command == "init":
            result = init_workspace(
                load_model(args.manifest),
                args.base_dir,
                args.directory,
                task=args.task,
                seed_ids=args.seed_ids,
                budget=args.budget,
            )
        elif args.workspace_command == "refresh":
            result = refresh_workspace(args.directory, args.base_dir, apply=args.apply)
        elif args.workspace_command == "clean":
            result = cleanup_workspace(args.directory, apply=args.apply)
        else:
            result = workspace_status(args.directory)
        _display(result)
        return int(result.get("valid") is False)
    return None
