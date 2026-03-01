"""
Shared utilities for spec/task management.

Specs and tasks are synonymous in Auto Claude. These helpers are used by
both the /api/specs and /api/tasks route modules to avoid code duplication.

All functions that scan the filesystem take an explicit ``specs_dir`` parameter
so that callers can redirect them to a temporary directory during testing (by
patching the ``_get_specs_dir`` helper that lives in each route module).
"""

import json
import logging
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)

# Name of the implementation plan file inside each spec directory
PLAN_FILE = "implementation_plan.json"


def get_specs_dir() -> Path:
    """Return the canonical specs directory derived from settings."""
    if hasattr(settings, "PROJECT_DIR") and settings.PROJECT_DIR:
        project_dir = Path(settings.PROJECT_DIR)
    else:
        # Default: five levels up from this file
        # api/utils/spec_utils.py → api/utils → api → web-backend → apps → project
        project_dir = Path(__file__).parent.parent.parent.parent.parent
        logger.warning(
            "PROJECT_DIR not configured; falling back to relative path: %s",
            project_dir,
        )
    return project_dir / ".auto-claude" / "specs"


# ---------------------------------------------------------------------------
# Pure computation helpers (no filesystem discovery)
# ---------------------------------------------------------------------------


def count_subtasks(spec_dir: Path) -> tuple[int, int]:
    """
    Count completed and total subtasks in implementation_plan.json.

    Returns:
        (completed_count, total_count)
    """
    result = count_subtasks_detailed(spec_dir)
    return result["completed"], result["total"]


def count_subtasks_detailed(spec_dir: Path) -> dict:
    """
    Count subtasks by status.

    Returns:
        Dict with completed, in_progress, pending, failed, total counts
    """
    plan_file = spec_dir / PLAN_FILE
    result = {
        "completed": 0,
        "in_progress": 0,
        "pending": 0,
        "failed": 0,
        "total": 0,
    }

    if not plan_file.exists():
        return result

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        for phase in plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                result["total"] += 1
                subtask_status = subtask.get("status", "pending")
                if subtask_status in result:
                    result[subtask_status] += 1
                else:
                    logger.warning(
                        "Unknown subtask status %r; skipping count", subtask_status
                    )

        return result
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return result


def get_progress_percentage(spec_dir: Path) -> float:
    """Return completion percentage (0-100) based on subtask counts."""
    completed, total = count_subtasks(spec_dir)
    if total == 0:
        return 0.0
    return (completed / total) * 100


# ---------------------------------------------------------------------------
# Directory-scanning helpers (take explicit specs_dir)
# ---------------------------------------------------------------------------


def _spec_status_and_progress(spec_folder: Path) -> tuple[str, str]:
    """Return (status, progress) for a spec folder that already has a build."""
    completed, total = count_subtasks(spec_folder)
    if total > 0:
        raw = "complete" if completed == total else "in_progress"
        return f"{raw} (has build)", f"{completed}/{total}"
    return "initialized (has build)", "0/0"


def list_specs_in(specs_dir: Path) -> list[dict]:
    """
    List all specs found inside *specs_dir*.

    Returns:
        List of spec dicts with keys: number, name, folder, status, progress, has_build
    """
    specs: list[dict] = []

    if not specs_dir.exists():
        return specs

    for spec_folder in sorted(specs_dir.iterdir()):
        if not spec_folder.is_dir():
            continue

        folder_name = spec_folder.name
        parts = folder_name.split("-", 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue

        if not (spec_folder / "spec.md").exists():
            continue

        has_build = (spec_folder / PLAN_FILE).exists()
        if has_build:
            spec_status, progress = _spec_status_and_progress(spec_folder)
        else:
            spec_status, progress = "pending", "-"

        specs.append(
            {
                "number": parts[0],
                "name": parts[1],
                "folder": folder_name,
                "status": spec_status,
                "progress": progress,
                "has_build": has_build,
            }
        )

    return specs


def find_spec_in(specs_dir: Path, spec_id: str) -> Path | None:
    """
    Find the spec directory for *spec_id* inside *specs_dir*.

    Args:
        specs_dir: Root directory that contains spec subdirectories.
        spec_id: Spec number (e.g., "001") or full folder name (e.g., "001-feature").

    Returns:
        Path to the matching spec directory, or None if not found.
    """
    if not specs_dir.exists():
        return None

    for spec_folder in specs_dir.iterdir():
        if spec_folder.is_dir():
            folder_name = spec_folder.name
            if folder_name.startswith(f"{spec_id}-") or folder_name == spec_id:
                return spec_folder

    return None
