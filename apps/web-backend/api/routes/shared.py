"""
Shared utilities for API routes.

Common helper functions used across specs, tasks, and agents routes.
Centralised here to avoid code duplication.
"""

import json
import logging
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)


def sanitize_log(value: str) -> str:
    """Sanitize value for safe logging (prevent log injection)."""
    return str(value).replace("\n", "\\n").replace("\r", "\\r")


def get_project_dir() -> Path:
    """Get the project directory from settings."""
    if hasattr(settings, "PROJECT_DIR") and settings.PROJECT_DIR:
        return Path(settings.PROJECT_DIR)

    # Default: parent of web-backend directory (../../ from api/routes/)
    return Path(__file__).parent.parent.parent.parent.parent


def get_specs_dir() -> Path:
    """Get the specs directory."""
    project_dir = get_project_dir()
    return project_dir / ".auto-claude" / "specs"


def _parse_plan_subtask_statuses(spec_dir: Path) -> list[str]:
    """
    Read implementation_plan.json and return a flat list of subtask statuses.

    Returns an empty list if the file doesn't exist or can't be parsed.
    """
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return []
    try:
        data = json.loads(plan_file.read_text(encoding="utf-8"))
        return [
            subtask.get("status", "pending")
            for phase in data.get("phases", [])
            for subtask in phase.get("subtasks", [])
        ]
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def count_subtasks(spec_dir: Path) -> tuple[int, int]:
    """Count completed and total subtasks. Returns (completed, total)."""
    statuses = _parse_plan_subtask_statuses(spec_dir)
    return sum(1 for s in statuses if s == "completed"), len(statuses)


def count_subtasks_detailed(spec_dir: Path) -> dict:
    """Count subtasks grouped by status."""
    statuses = _parse_plan_subtask_statuses(spec_dir)
    result = {
        "completed": 0,
        "in_progress": 0,
        "pending": 0,
        "failed": 0,
        "total": len(statuses),
    }
    for s in statuses:
        key = s if s in result else "pending"
        result[key] += 1
    return result


def get_progress_percentage(spec_dir: Path) -> float:
    """Get progress as a percentage (0-100)."""
    completed, total = count_subtasks(spec_dir)
    return (completed / total * 100) if total else 0.0


def list_specs() -> list[dict]:
    """
    List all specs in the project.

    Returns:
        List of spec info dicts with keys: number, name, folder, status, progress, has_build
    """
    specs_dir = get_specs_dir()
    specs = []

    if not specs_dir.exists():
        return specs

    for spec_folder in sorted(specs_dir.iterdir()):
        if not spec_folder.is_dir():
            continue

        # Parse folder name (e.g., "001-initial-app")
        folder_name = spec_folder.name
        parts = folder_name.split("-", 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue

        number = parts[0]
        name = parts[1]

        # Check for spec.md
        spec_file = spec_folder / "spec.md"
        if not spec_file.exists():
            continue

        # Check for existing build (simplified - checking for implementation plan)
        has_build = (spec_folder / "implementation_plan.json").exists()

        # Check progress via implementation_plan.json
        plan_file = spec_folder / "implementation_plan.json"
        if plan_file.exists():
            completed, total = count_subtasks(spec_folder)
            if total > 0:
                if completed == total:
                    spec_status = "complete"
                else:
                    spec_status = "in_progress"
                progress = f"{completed}/{total}"
            else:
                spec_status = "initialized"
                progress = "0/0"
        else:
            spec_status = "pending"
            progress = "-"

        # Add build indicator
        if has_build:
            spec_status = f"{spec_status} (has build)"

        specs.append(
            {
                "number": number,
                "name": name,
                "folder": folder_name,
                "status": spec_status,
                "progress": progress,
                "has_build": has_build,
            }
        )

    return specs


def build_item_detail(item_id: str, not_found_label: str) -> dict:
    """
    Build a detailed information dict for a spec/task item.

    Encapsulates the common logic shared by get_spec_detail and get_task_detail.

    Args:
        item_id: Spec/task number (e.g., "001") or full folder name
        not_found_label: Label used in 404 messages (e.g., "Spec" or "Task")

    Returns:
        Dict with keys: number, name, folder, status, has_build, spec_content,
        and a nested 'progress' dict with completed/in_progress/pending/failed/total/percentage.

    Raises:
        HTTPException: 404 if the item directory or spec.md is not found
    """
    # Local import to avoid circular dependency (fastapi imports app, app imports routes)
    from fastapi import HTTPException
    from fastapi import status as http_status

    spec_dir = find_spec_dir(item_id)
    if spec_dir is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"{not_found_label} {item_id} not found",
        )

    spec_file = spec_dir / "spec.md"
    if not spec_file.exists():
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"{not_found_label} {item_id} not found",
        )

    try:
        spec_content = spec_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read spec content: %s", e)
        spec_content = None

    folder_name = spec_dir.name
    parts = folder_name.split("-", 1)
    number = parts[0] if len(parts) > 0 else item_id
    name = parts[1] if len(parts) > 1 else "unknown"

    progress_detail = count_subtasks_detailed(spec_dir)
    percentage = get_progress_percentage(spec_dir)

    if progress_detail["total"] == 0:
        item_status = "pending"
    elif progress_detail["completed"] == progress_detail["total"]:
        item_status = "complete"
    elif progress_detail["in_progress"] > 0 or progress_detail["completed"] > 0:
        item_status = "in_progress"
    else:
        item_status = "initialized"

    has_build = (spec_dir / "implementation_plan.json").exists()

    return {
        "number": number,
        "name": name,
        "folder": folder_name,
        "status": item_status,
        "has_build": has_build,
        "spec_content": spec_content,
        "progress": {
            "completed": progress_detail["completed"],
            "in_progress": progress_detail["in_progress"],
            "pending": progress_detail["pending"],
            "failed": progress_detail["failed"],
            "total": progress_detail["total"],
            "percentage": percentage,
        },
    }


def find_spec_dir(spec_id: str) -> Path | None:
    """
    Get spec directory for a given spec/task ID.

    Args:
        spec_id: Spec number (e.g., "001") or full folder name

    Returns:
        Path to spec directory, or None if not found
    """
    specs_dir = get_specs_dir()

    if not specs_dir.exists():
        return None

    for spec_folder in specs_dir.iterdir():
        if spec_folder.is_dir():
            folder_name = spec_folder.name
            if folder_name.startswith(f"{spec_id}-") or folder_name == spec_id:
                return spec_folder

    return None
