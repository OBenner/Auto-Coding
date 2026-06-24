"""Out-of-scope edit detection for the Trust Layer verification report (P1.T2).

Compares the files a build actually changed against the files the plan declared
it would touch (``files_to_modify`` + ``files_to_create`` per subtask) and flags
the difference, so the verification report can surface edits the agent made
outside its plan.

Pure logic (stdlib only): the plan dict and the changed-file list are passed in,
so this is unit-testable without git or the QA package's runtime dependencies.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

# Framework bookkeeping (specs, artifacts, memory) lives under .auto-claude/ and
# is never a user-facing source edit, so it must not be flagged as out of scope.
_IGNORED_PREFIXES = (".auto-claude/", ".auto-claude-")


def _normalize_path(path: str) -> str:
    """Normalize a repo-relative path for comparison (slashes, leading ./)."""
    normalized = (path or "").strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def get_planned_files(plan: dict[str, Any] | None) -> set[str]:
    """Collect the files the plan declared it would touch.

    Unions ``files_to_modify`` + ``files_to_create`` across every subtask of
    every phase, supporting both the ``subtasks`` and legacy ``chunks`` keys.
    Returns normalized paths.
    """
    planned: set[str] = set()
    if not plan:
        return planned

    for phase in plan.get("phases", []) or []:
        if not isinstance(phase, dict):
            continue
        subtasks = phase.get("subtasks") or phase.get("chunks") or []
        for subtask in subtasks:
            if not isinstance(subtask, dict):
                continue
            for key in ("files_to_modify", "files_to_create"):
                for file_path in subtask.get(key, []) or []:
                    normalized = _normalize_path(file_path)
                    if normalized:
                        planned.add(normalized)
    return planned


def detect_out_of_scope_edits(
    planned_files: Iterable[str],
    changed_files: Iterable[str],
) -> list[dict[str, str]]:
    """Return changed files that the plan did not declare.

    Paths under framework bookkeeping (``.auto-claude/``) are ignored. The
    result is de-duplicated and stable-sorted for deterministic reports.
    """
    planned = {_normalize_path(f) for f in planned_files}
    out_of_scope: list[dict[str, str]] = []
    seen: set[str] = set()

    for raw in changed_files:
        normalized = _normalize_path(raw)
        if not normalized or normalized in seen:
            continue
        if any(normalized.startswith(prefix) for prefix in _IGNORED_PREFIXES):
            continue
        if normalized in planned:
            continue
        seen.add(normalized)
        out_of_scope.append(
            {
                "file": normalized,
                "reason": "edited outside the plan's files_to_modify/files_to_create",
            }
        )

    return sorted(out_of_scope, key=lambda item: item["file"])
