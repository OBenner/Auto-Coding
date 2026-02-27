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
    build_item_detail,
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
        data = build_item_detail(task_id, "Task")
        progress_data = data.pop("progress")
        return TaskDetail(progress=TaskProgressDetail(**progress_data), **data)
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
