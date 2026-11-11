"""Roadmap commands, isolated from the original minimal model CLI."""

from pathlib import Path

from lsm.storage import ModelIOError, load_model, save_model


def configure(commands):
    migration = commands.add_parser("migrate", help="explicitly upgrade a model schema")
    migration.add_argument("source", type=Path)
    migration.add_argument("destination", type=Path)
    migration.add_argument("--target", choices=["1.0", "1.1"], default="1.1")
    migration.add_argument("--force", action="store_true")


def write_document(document, destination, force=False):
    if destination.exists() and not force:
        raise ModelIOError(f"Destination exists: {destination}; use --force to overwrite")
    save_model(document, destination)


def dispatch(args):
    if args.command == "migrate":
        from lsm.migrations import migrate_model

        write_document(
            migrate_model(load_model(args.source), args.target), args.destination, args.force
        )
        print(f"Saved {args.destination}")
        return 0
    return None
