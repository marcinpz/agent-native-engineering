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
