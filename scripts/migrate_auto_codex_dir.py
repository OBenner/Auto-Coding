#!/usr/bin/env python3
"""Migrate ``.auto-Codex/`` runtime artifacts to ``.auto-claude/runtime/``.

The Codex-agent PR series (PRs #250 - #263) wrote provider-smoke history
and related runtime artifacts under ``.auto-Codex/``. The canonical
location is now ``.auto-claude/runtime/``. Reads remain tolerant of the
legacy directory for one migration window; this script moves the files
in-place so future writes do not orphan the old data.

Usage::

    python scripts/migrate_auto_codex_dir.py              # dry run
    python scripts/migrate_auto_codex_dir.py --apply      # perform move
    python scripts/migrate_auto_codex_dir.py --apply \\
        --project-dir /path/to/project --delete-empty-source

The script is safe to run repeatedly; it is a no-op when ``.auto-Codex/``
is absent.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

LEGACY_DIR_NAME = ".auto-Codex"
NEW_DIR_PARTS = (".auto-claude", "runtime")


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def _safely_remove_empty_tree(root: Path) -> None:
    """Remove ``root`` and any empty subdirectories underneath it.

    ``Path.rmdir()`` only works on truly empty directories; the legacy
    ``.auto-Codex`` tree may contain orphan subdirectories left over
    after the migration. Bottom-up removal handles both cases without
    raising ``OSError: Directory not empty``.
    """
    if not root.exists():
        return
    for dirpath in sorted(
        (p for p in root.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        try:
            dirpath.rmdir()
        except OSError:
            # Still has non-empty contents (e.g. a skipped file remains).
            # Leave the rest in place so the operator can inspect.
            print(
                f"[warn] {dirpath} is not empty, leaving in place"
            )
            return
    try:
        root.rmdir()
    except OSError as exc:
        print(f"[warn] could not remove {root}: {exc}")
    else:
        print(f"[ok] removed empty {root}")


def migrate(
    project_dir: Path,
    *,
    apply: bool,
    delete_empty_source: bool,
) -> int:
    legacy_dir = project_dir / LEGACY_DIR_NAME
    new_dir = project_dir.joinpath(*NEW_DIR_PARTS)

    if not legacy_dir.exists():
        print(f"[ok] {legacy_dir} does not exist; nothing to migrate.")
        return 0
    if not legacy_dir.is_dir():
        print(
            f"[error] {legacy_dir} is not a directory; refusing to migrate.",
            file=sys.stderr,
        )
        return 2

    actions: list[tuple[Path, Path, str]] = []
    skipped: list[tuple[Path, str]] = []
    for source in _iter_files(legacy_dir):
        relative = source.relative_to(legacy_dir)
        target = new_dir / relative
        if target.exists():
            skipped.append((source, "target already exists"))
            continue
        actions.append((source, target, "move"))

    verb = "Would move" if not apply else "Moving"
    for source, target, _ in actions:
        print(f"[{verb.lower()}] {source} -> {target}")
    for source, reason in skipped:
        print(f"[skip] {source}: {reason}")

    if not actions and not skipped:
        print(f"[ok] {legacy_dir} is empty; nothing to migrate.")
        if apply and delete_empty_source:
            _safely_remove_empty_tree(legacy_dir)
        return 0

    if not apply:
        print(
            f"\n[dry-run] {len(actions)} files would be moved, "
            f"{len(skipped)} would be skipped. Re-run with --apply to perform "
            "the migration.",
        )
        return 0

    for source, target, _ in actions:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))

    print(
        f"\n[ok] migrated {len(actions)} files into {new_dir} "
        f"({len(skipped)} skipped)."
    )

    if delete_empty_source and not any(_iter_files(legacy_dir)):
        _safely_remove_empty_tree(legacy_dir)
    elif delete_empty_source:
        print(
            f"[warn] {legacy_dir} still contains files (skipped above); "
            "not removing."
        )
    else:
        print(
            f"[info] {legacy_dir} kept in place; pass --delete-empty-source "
            "to remove it once empty."
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project root (defaults to current working directory).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually move files. Without this flag the script only prints a plan.",
    )
    parser.add_argument(
        "--delete-empty-source",
        action="store_true",
        help="Remove the legacy .auto-Codex directory if it is empty afterwards.",
    )
    args = parser.parse_args(argv)

    project_dir = args.project_dir.resolve()
    if not project_dir.is_dir():
        print(f"[error] project-dir {project_dir} is not a directory.", file=sys.stderr)
        return 2

    return migrate(
        project_dir,
        apply=args.apply,
        delete_empty_source=args.delete_empty_source,
    )


if __name__ == "__main__":
    raise SystemExit(main())
