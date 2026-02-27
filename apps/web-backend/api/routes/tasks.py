"""
Task Management API routes

Provides endpoints for listing and managing tasks (specs).
Tasks and specs are synonymous in Auto Code.
"""

import logging
from typing import Annotated

from core.security import require_auth
from fastapi import APIRouter, Depends, HTTPException, status

from api.models.task import (
    TaskDetail,
    TaskListResponse,
    TaskProgressDetail,
    TaskSummary,
)
from api.routes.shared import (
    count_subtasks_detailed,
    find_spec_dir,
    get_progress_percentage,
    list_specs,
    sanitize_log,
)

logger = logging.getLogger(__name__)


# Create router for task endpoints
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse, status_code=status.HTTP_200_OK)
async def list_tasks(auth: Annotated[dict, Depends(require_auth)]):
    """
    List all tasks (specs) in the project.

    Returns a list of all specs with their current status and progress.
    Tasks and specs are synonymous - each spec represents a task to be implemented.

    Args:
        auth: Authentication token claims (required)

    Returns:
        TaskListResponse with list of tasks and total count

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/tasks \
             -H "Authorization: Bearer <token>" \
             -H "Content-Type: application/json"
        # Returns: {"tasks": [...], "total": 5}
        ```
    """
    try:
        # Get specs
        specs = list_specs()

        # Convert to API response format
        tasks = [
            TaskSummary(
                number=spec["number"],
                name=spec["name"],
                folder=spec["folder"],
                status=spec["status"],
                progress=spec["progress"],
                has_build=spec.get("has_build", False),
            )
            for spec in specs
        ]

        return TaskListResponse(tasks=tasks, total=len(tasks))

    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tasks",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def tasks_health():
    """
    Health check for tasks API.

    Returns basic status information about the tasks API endpoint.

    Returns:
        Dictionary with status and configuration info
    """
    return {
        "status": "ok",
        "endpoint": "tasks",
    }


@router.get("/{task_id}", response_model=TaskDetail, status_code=status.HTTP_200_OK)
async def get_task_detail(task_id: str, auth: Annotated[dict, Depends(require_auth)]):
    """
    Get detailed information for a specific task.

    Args:
        task_id: Task number (e.g., "001") or full folder name (e.g., "001-feature")
        auth: Authentication token claims (required)

    Returns:
        TaskDetail with complete task information including spec content

    Raises:
        HTTPException: 404 if task not found, 500 for other errors

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/tasks/001 \
             -H "Authorization: Bearer <token>" \
             -H "Content-Type: application/json"
        # Returns: {"number": "001", "name": "feature", ...}
        ```
    """
    try:
        spec_dir = find_spec_dir(task_id)

        # Check if spec exists
        if spec_dir is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        spec_file = spec_dir / "spec.md"
        if not spec_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
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
        number = parts[0] if len(parts) > 0 else task_id
        name = parts[1] if len(parts) > 1 else "unknown"

        # Get progress details
        progress_detail = count_subtasks_detailed(spec_dir)
        percentage = get_progress_percentage(spec_dir)

        # Determine status
        if progress_detail["total"] == 0:
            task_status = "pending"
        elif progress_detail["completed"] == progress_detail["total"]:
            task_status = "complete"
        elif progress_detail["in_progress"] > 0 or progress_detail["completed"] > 0:
            task_status = "in_progress"
        else:
            task_status = "initialized"

        # Check for active build
        has_build = (spec_dir / "implementation_plan.json").exists()

        return TaskDetail(
            number=number,
            name=name,
            folder=folder_name,
            status=task_status,
            progress=TaskProgressDetail(
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
        logger.error(
            f"Error getting task detail for {sanitize_log(task_id)}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task detail",
        )
