"""
Agent Execution API routes

Provides endpoints for starting and managing agent execution.
"""

import logging
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.config import settings
from services.agent_runner import (
    cancel_task,
    cleanup_completed_tasks,
    get_task_status,
    start_agent_task,
)

logger = logging.getLogger(__name__)


def _sanitize_log(value: str) -> str:
    """Sanitize value for safe logging (prevent log injection)."""
    return str(value).replace("\n", "\\n").replace("\r", "\\r")


# Create router for agent endpoints
router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    """Request to run an agent"""

    spec_id: str = Field(..., description="Spec ID (e.g., '001' or '001-feature-name')")
    agent_type: Literal["planner", "coder", "qa_reviewer", "qa_fixer"] = Field(
        ..., description="Type of agent to run"
    )
    model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model to use"
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output"
    )


class AgentRunResponse(BaseModel):
    """Response from starting an agent"""

    task_id: str = Field(..., description="Task ID for tracking execution")
    spec_id: str = Field(..., description="Spec ID")
    agent_type: str = Field(..., description="Agent type")
    status: Literal["started", "error"] = Field(..., description="Initial status")
    message: str = Field(..., description="Human-readable message")


class AgentStatusResponse(BaseModel):
    """Response with agent task status"""

    task_id: str = Field(..., description="Task ID")
    status: Literal["running", "completed", "failed", "not_found"] = Field(
        ..., description="Current task status"
    )
    result: Optional[dict] = Field(None, description="Task result (if completed)")
    error: Optional[str] = Field(None, description="Error message (if failed)")


class AgentCancelResponse(BaseModel):
    """Response from cancelling an agent"""

    task_id: str = Field(..., description="Task ID")
    cancelled: bool = Field(..., description="Whether task was cancelled")
    message: str = Field(..., description="Human-readable message")


def _get_project_dir() -> Path:
    """Get the project directory from settings."""
    # Use configured project directory or fall back to parent of backend
    if hasattr(settings, "PROJECT_DIR") and settings.PROJECT_DIR:
        return Path(settings.PROJECT_DIR)

    # Default: parent of web-backend directory (../../ from api/routes/)
    return Path(__file__).parent.parent.parent.parent.parent


@router.post("/run", response_model=AgentRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_agent(request: AgentRunRequest):
    """
    Start an agent execution task.

    This endpoint starts an agent task in the background and returns immediately.
    Use the returned task_id to check status via GET /api/agents/status/{task_id}.

    The agent will run asynchronously and emit progress events via WebSocket.

    Args:
        request: Agent run request with spec_id, agent_type, model, and verbose

    Returns:
        AgentRunResponse with task_id for tracking

    Raises:
        HTTPException: 400 if spec not found or task already running, 500 for other errors

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/agents/run \\
             -H "Content-Type: application/json" \\
             -d '{"spec_id": "001", "agent_type": "planner"}'
        # Returns: {"task_id": "001:planner", "status": "started", ...}
        ```
    """
    try:
        logger.info(
            f"Agent run request: spec_id={_sanitize_log(request.spec_id)}, "
            f"agent_type={_sanitize_log(request.agent_type)}, model={_sanitize_log(request.model)}"
        )

        # Start the agent task
        project_dir = _get_project_dir()

        task_id = start_agent_task(
            spec_id=request.spec_id,
            agent_type=request.agent_type,
            project_dir=project_dir,
            model=request.model,
            verbose=request.verbose,
        )

        # Clean up completed tasks
        cleanup_completed_tasks()

        return AgentRunResponse(
            task_id=task_id,
            spec_id=request.spec_id,
            agent_type=request.agent_type,
            status="started",
            message=f"Agent task started: {request.agent_type} for spec {request.spec_id}"
        )

    except FileNotFoundError as e:
        logger.warning(f"Spec not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.warning(f"Task already running: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error starting agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start agent: {str(e)}",
        )


@router.get("/status/{task_id}", response_model=AgentStatusResponse, status_code=status.HTTP_200_OK)
async def get_agent_status(task_id: str):
    """
    Get the status of a running agent task.

    Args:
        task_id: Task ID returned by POST /api/agents/run

    Returns:
        AgentStatusResponse with current status and result (if completed)

    Raises:
        HTTPException: 404 if task not found

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/agents/status/001:planner \\
             -H "Content-Type: application/json"
        # Returns: {"task_id": "001:planner", "status": "running", ...}
        ```
    """
    try:
        task_status = get_task_status(task_id)

        if task_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found: {task_id}",
            )

        return AgentStatusResponse(
            task_id=task_id,
            status=task_status["status"],
            result=task_status.get("result"),
            error=task_status.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )


@router.post("/cancel/{task_id}", response_model=AgentCancelResponse, status_code=status.HTTP_200_OK)
async def cancel_agent(task_id: str):
    """
    Cancel a running agent task.

    Args:
        task_id: Task ID to cancel

    Returns:
        AgentCancelResponse with cancellation status

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/agents/cancel/001:planner \\
             -H "Content-Type: application/json"
        # Returns: {"task_id": "001:planner", "cancelled": true, ...}
        ```
    """
    try:
        cancelled = cancel_task(task_id)

        if cancelled:
            return AgentCancelResponse(
                task_id=task_id,
                cancelled=True,
                message=f"Task cancelled: {task_id}"
            )
        else:
            return AgentCancelResponse(
                task_id=task_id,
                cancelled=False,
                message=f"Task not found or already completed: {task_id}"
            )

    except Exception as e:
        logger.error(f"Error cancelling task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def agents_health():
    """
    Health check for agents API.

    Returns basic status information about the agents API endpoint.

    Returns:
        Dictionary with status and configuration info
    """
    project_dir = _get_project_dir()

    return {
        "status": "ok",
        "endpoint": "agents",
        "project_dir": str(project_dir),
    }
