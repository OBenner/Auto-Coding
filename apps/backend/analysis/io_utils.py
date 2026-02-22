"""
Analysis I/O Utilities
======================

Shared utilities for the analysis module: atomic file writes,
severity helpers, and common constants.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

# Directories commonly skipped during source analysis
SKIP_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
    }
)

SEVERITY_ORDER: list[str] = ["critical", "high", "medium", "low", "info"]


def atomic_json_write(
    data: Any,
    output_file: Path,
    *,
    dir: Path | None = None,
    prefix: str = "analysis_",
) -> None:
    """Write *data* as JSON to *output_file* atomically.

    A temporary file is created in *dir* (defaults to ``output_file.parent``),
    the JSON payload is written there, and the temp file is atomically renamed
    to *output_file*.  On failure the temp file is cleaned up.
    """
    target_dir = str(dir or output_file.parent)
    fd, tmp_path = tempfile.mkstemp(dir=target_dir, suffix=".tmp", prefix=prefix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, str(output_file))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # Best-effort cleanup; temp file may already be removed
        raise


def group_by_severity(items: list, *, attr: str = "severity") -> dict[str, list]:
    """Group *items* by their severity attribute.

    Returns a dict keyed by severity level (critical → info) with lists of
    matching items.  Unknown severities are silently skipped.
    """
    groups: dict[str, list] = {s: [] for s in SEVERITY_ORDER}
    for item in items:
        sev = getattr(item, attr, None)
        if sev in groups:
            groups[sev].append(item)
    return groups


def count_by_severity(items: list, *, attr: str = "severity") -> dict[str, int]:
    """Return ``{severity: count}`` for *items*."""
    groups = group_by_severity(items, attr=attr)
    return {k: len(v) for k, v in groups.items()}


def should_skip_path(path: Path, skip_dirs: frozenset[str] = SKIP_DIRS) -> bool:
    """Return True if *path* contains any of the *skip_dirs* components."""
    return any(part in skip_dirs for part in path.parts)
