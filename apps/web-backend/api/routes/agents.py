"""
Agent Execution API routes

Provides endpoints for starting and managing agent execution.
"""

import logging
from typing import Annotated, Literal

from core.config import settings
from core.database import get_db
from core.permissions import WorkspaceRole, check_workspace_access
from core.security import require_auth
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from services.agent_runner import (
    cancel_task,
    cleanup_completed_tasks,
    get_task_status,
    start_agent_task,
)
from services.execution_log import create_execution, mark_execution_finished
from services.workspace_service import get_or_create_personal_workspace
from sqlalchemy.orm import Session

from api.models.agent_execution import AgentExecution
from api.routes.shared import get_project_dir, sanitize_log

logger = logging.getLogger(__name__)


# Create router for agent endpoints
router = APIRouter(prefix="/api/agents", tags=["agents"])


def _resolve_execution_context(
    request: "AgentRunRequest", auth: dict, db: Session
) -> tuple[int | None, int | None]:
    """Resolve (workspace_id, user_id) for the run's audit record.

    Tokens whose ``sub`` is not a numeric user id (legacy/service tokens) get
    (None, None): the run proceeds without a persisted record. Real tokens are
    always numeric (users.py mints sub=str(user.id)). Single mode attributes the
    run to the caller's Personal workspace; team mode requires ``workspace_id``
    in the request body and >= editor access.
    """
    sub = auth.get("sub")
    if sub is None or not str(sub).isdigit():
        return None, None
    user_id = int(sub)

    if settings.CLOUD_MODE == "single":
        workspace = get_or_create_personal_workspace(db, user_id)
        return workspace.id, user_id

    if request.workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is required in team mode",
        )
    if not check_workspace_access(
        db, user_id, request.workspace_id, WorkspaceRole.EDITOR
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient workspace permissions",
        )
    return request.workspace_id, user_id


def _mark_failed_start(
    db: Session, execution: "AgentExecution | None", error: str
) -> None:
    """Best-effort: finish the run record as failed when the task never started."""
    if execution is None:
        return
    try:
        mark_execution_finished(db, execution, "failed", error)
    except Exception:
        logger.warning(
            "Failed to mark execution %s as failed", execution.id, exc_info=True
        )


class AgentRunRequest(BaseModel):
    """Request to run an agent"""

    spec_id: str = Field(..., description="Spec ID (e.g., '001' or '001-feature-name')")
    agent_type: Literal["planner", "coder", "qa_reviewer", "qa_fixer"] = Field(
        ..., description="Type of agent to run"
    )
    model: str = Field(
        default="claude-sonnet-4-5-20250929", description="Claude model to use"
    )
    verbose: bool = Field(default=False, description="Enable verbose output")
    workspace_id: int | None = Field(
        default=None,
        description="Workspace to attribute the run to (required in team mode; "
        "ignored in single mode, where the Personal workspace is used)",
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
    result: dict | None = Field(None, description="Task result (if completed)")
    error: str | None = Field(None, description="Error message (if failed)")


class AgentCancelResponse(BaseModel):
    """Response from cancelling an agent"""

    task_id: str = Field(..., description="Task ID")
    cancelled: bool = Field(..., description="Whether task was cancelled")
    message: str = Field(..., description="Human-readable message")


@router.post(
    "/run", response_model=AgentRunResponse, status_code=status.HTTP_202_ACCEPTED
)
async def run_agent(
    request: AgentRunRequest,
    auth: Annotated[dict, Depends(require_auth)],
    db: Annotated[Session, Depends(get_db)],
):
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
    logger.info(
        f"Agent run request: spec_id={sanitize_log(request.spec_id)}, "
        f"agent_type={sanitize_log(request.agent_type)}, model={sanitize_log(request.model)}"
    )

    # Resolve audit context first (may raise 400/403 in team mode) and create
    # the durable run record (C3) before the task starts.
    workspace_id, user_id = _resolve_execution_context(request, auth, db)
    execution = None
    if workspace_id is not None:
        execution = create_execution(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            spec_id=request.spec_id,
            agent_type=request.agent_type,
            model=request.model,
        )

    try:
        # Start the agent task
        project_dir = get_project_dir()

        task_id = start_agent_task(
            spec_id=request.spec_id,
            agent_type=request.agent_type,
            project_dir=project_dir,
            model=request.model,
            verbose=request.verbose,
            execution_id=execution.id if execution is not None else None,
        )

        # Clean up completed tasks
        cleanup_completed_tasks()

        return AgentRunResponse(
            task_id=task_id,
            spec_id=request.spec_id,
            agent_type=request.agent_type,
            status="started",
            message=f"Agent task started: {request.agent_type} for spec {request.spec_id}",
        )

    except FileNotFoundError as e:
        logger.warning(f"Spec not found: {e}")
        _mark_failed_start(db, execution, str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.warning(f"Task already running: {e}")
        _mark_failed_start(db, execution, str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        _mark_failed_start(db, execution, str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # Log full exception details internally; do not expose raw error to clients
        logger.error(f"Error starting agent: {e}", exc_info=True)
        _mark_failed_start(db, execution, "Internal error while starting the task")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start agent task due to an internal error",
        )


@router.get(
    "/status/{task_id}",
    response_model=AgentStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_agent_status(task_id: str, auth: Annotated[dict, Depends(require_auth)]):
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
            detail="Failed to get task status",
        )


@router.post(
    "/cancel/{task_id}",
    response_model=AgentCancelResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_agent(task_id: str, auth: Annotated[dict, Depends(require_auth)]):
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
                task_id=task_id, cancelled=True, message=f"Task cancelled: {task_id}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found or already completed: {task_id}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel task",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def agents_health():
    """
    Health check for agents API.

    Returns basic status information about the agents API endpoint.

    Returns:
        Dictionary with status and configuration info
    """
    return {
        "status": "ok",
        "endpoint": "agents",
    }
