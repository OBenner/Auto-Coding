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


def count_subtasks(spec_dir: Path) -> tuple[int, int]:
    """
    Count completed and total subtasks in implementation_plan.json.

    Args:
        spec_dir: Directory containing implementation_plan.json

    Returns:
        (completed_count, total_count)
    """
    plan_file = spec_dir / "implementation_plan.json"

    if not plan_file.exists():
        return 0, 0

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        total = 0
        completed = 0

        for phase in plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                total += 1
                if subtask.get("status") == "completed":
                    completed += 1

        return completed, total
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return 0, 0


def count_subtasks_detailed(spec_dir: Path) -> dict:
    """
    Count subtasks by status.

    Returns:
        Dict with completed, in_progress, pending, failed counts
    """
    plan_file = spec_dir / "implementation_plan.json"

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
                    result["pending"] += 1

        return result
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return result


def get_progress_percentage(spec_dir: Path) -> float:
    """
    Get the progress as a percentage.

    Args:
        spec_dir: Directory containing implementation_plan.json

    Returns:
        Percentage of subtasks completed (0-100)
    """
    completed, total = count_subtasks(spec_dir)
    if total == 0:
        return 0.0
    return (completed / total) * 100


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
