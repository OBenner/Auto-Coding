"""
Spec Management API routes

Provides endpoints for listing and managing specs.
Specs and tasks are synonymous in Auto Claude - this is an alias endpoint.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status

from api.models.spec import (
    SpecDetail,
    SpecListResponse,
    SpecProgressDetail,
    SpecSummary,
)
from core.config import settings
from core.security import require_auth

logger = logging.getLogger(__name__)

# Create router for spec endpoints
router = APIRouter(prefix="/api/specs", tags=["specs"])


def _get_project_dir() -> Path:
    """Get the project directory from settings."""
    # Use configured project directory or fall back to parent of backend
    if hasattr(settings, "PROJECT_DIR") and settings.PROJECT_DIR:
        return Path(settings.PROJECT_DIR)

    # Default: parent of web-backend directory (../../ from api/routes/)
    return Path(__file__).parent.parent.parent.parent.parent


def _get_specs_dir() -> Path:
    """Get the specs directory."""
    project_dir = _get_project_dir()
    return project_dir / ".auto-claude" / "specs"


def _count_subtasks(spec_dir: Path) -> Tuple[int, int]:
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


def _count_subtasks_detailed(spec_dir: Path) -> dict:
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
                status = subtask.get("status", "pending")
                if status in result:
                    result[status] += 1
                else:
                    result["pending"] += 1

        return result
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return result


def _get_progress_percentage(spec_dir: Path) -> float:
    """
    Get the progress as a percentage.

    Args:
        spec_dir: Directory containing implementation_plan.json

    Returns:
        Percentage of subtasks completed (0-100)
    """
    completed, total = _count_subtasks(spec_dir)
    if total == 0:
        return 0.0
    return (completed / total) * 100


def _list_specs() -> List[dict]:
    """
    List all specs in the project.

    Returns:
        List of spec info dicts with keys: number, name, folder, status, progress, has_build
    """
    specs_dir = _get_specs_dir()
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
            completed, total = _count_subtasks(spec_folder)
            if total > 0:
                if completed == total:
                    status = "complete"
                else:
                    status = "in_progress"
                progress = f"{completed}/{total}"
            else:
                status = "initialized"
                progress = "0/0"
        else:
            status = "pending"
            progress = "-"

        # Add build indicator
        if has_build:
            status = f"{status} (has build)"

        specs.append(
            {
                "number": number,
                "name": name,
                "folder": folder_name,
                "status": status,
                "progress": progress,
                "has_build": has_build,
            }
        )

    return specs


def _get_spec_dir(spec_id: str) -> Optional[Path]:
    """
    Get spec directory for a given spec ID.

    Args:
        spec_id: Spec number (e.g., "001") or full folder name

    Returns:
        Path to spec directory, or None if not found
    """
    specs_dir = _get_specs_dir()

    if not specs_dir.exists():
        return None

    # Spec ID can be either the number (e.g., "001") or full folder name (e.g., "001-feature")
    # Try to find matching spec directory
    for spec_folder in specs_dir.iterdir():
        if spec_folder.is_dir():
            folder_name = spec_folder.name
            # Check if it starts with the spec ID or matches exactly
            if folder_name.startswith(f"{spec_id}-") or folder_name == spec_id:
                return spec_folder

    return None


@router.get("", response_model=SpecListResponse, status_code=status.HTTP_200_OK)
async def list_specs(auth: dict = Depends(require_auth)):
    """
    List all specs in the project.

    Returns a list of all specs with their current status and progress.

    Returns:
        SpecListResponse with list of specs and total count

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/specs \
             -H "Authorization: Bearer <token>" \
             -H "Content-Type: application/json"
        # Returns: {"specs": [...], "total": 5}
        ```
    """
    try:
        logger.info(f"Listing specs from project directory: {_get_project_dir()}")

        # Get specs
        specs = _list_specs()

        # Convert to API response format
        spec_list = [
            SpecSummary(
                number=spec["number"],
                name=spec["name"],
                folder=spec["folder"],
                status=spec["status"],
                progress=spec["progress"],
                has_build=spec.get("has_build", False),
            )
            for spec in specs
        ]

        return SpecListResponse(specs=spec_list, total=len(spec_list))

    except Exception as e:
        logger.error(f"Error listing specs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list specs: {str(e)}",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def specs_health():
    """
    Health check for specs API.

    Returns basic status information about the specs API endpoint.

    Returns:
        Dictionary with status and configuration info
    """
    project_dir = _get_project_dir()
    specs_dir = _get_specs_dir()

    return {
        "status": "ok",
        "endpoint": "specs",
        "project_dir": str(project_dir),
        "specs_dir_exists": specs_dir.exists(),
    }


@router.get("/{spec_id}", response_model=SpecDetail, status_code=status.HTTP_200_OK)
async def get_spec_detail(spec_id: str, auth: dict = Depends(require_auth)):
    """
    Get detailed information for a specific spec.

    Args:
        spec_id: Spec number (e.g., "001") or full folder name (e.g., "001-feature")

    Returns:
        SpecDetail with complete spec information including spec content

    Raises:
        HTTPException: 404 if spec not found, 500 for other errors

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/specs/001 \
             -H "Authorization: Bearer <token>" \
             -H "Content-Type: application/json"
        # Returns: {"number": "001", "name": "feature", ...}
        ```
    """
    try:
        spec_dir = _get_spec_dir(spec_id)

        # Check if spec exists
        if spec_dir is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec {spec_id} not found",
            )

        spec_file = spec_dir / "spec.md"
        if not spec_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec {spec_id} not found",
            )

        # Get spec content
        try:
            spec_content = spec_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read spec content: {e}")
            spec_content = None

        # Parse folder name to get number and name
        folder_name = spec_dir.name
        parts = folder_name.split("-", 1)
        number = parts[0] if len(parts) > 0 else spec_id
        name = parts[1] if len(parts) > 1 else "unknown"

        # Get progress details
        progress_detail = _count_subtasks_detailed(spec_dir)
        percentage = _get_progress_percentage(spec_dir)

        # Determine status
        if progress_detail["total"] == 0:
            spec_status = "pending"
        elif progress_detail["completed"] == progress_detail["total"]:
            spec_status = "complete"
        elif progress_detail["in_progress"] > 0 or progress_detail["completed"] > 0:
            spec_status = "in_progress"
        else:
            spec_status = "initialized"

        # Check for active build
        has_build = (spec_dir / "implementation_plan.json").exists()

        return SpecDetail(
            number=number,
            name=name,
            folder=folder_name,
            status=spec_status,
            progress=SpecProgressDetail(
                completed=progress_detail["completed"],
                in_progress=progress_detail["in_progress"],
                pending=progress_detail["pending"],
                failed=progress_detail["failed"],
                total=progress_detail["total"],
                percentage=percentage,
            ),
            has_build=has_build,
            spec_content=spec_content,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spec detail for {spec_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get spec detail: {str(e)}",
        )
