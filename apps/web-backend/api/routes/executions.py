"""
Agent execution history API (Track C — C3).

Read-only, workspace-scoped run history: the sessions/audit view (UC-S2/S3)
lists past runs and inspects a single record. Rows are written by
api/routes/agents.py (start) and services/agent_runner.py (finish).
"""

import logging

from core.database import get_db
from core.permissions import (
    WorkspaceRole,
    check_workspace_access,
    get_current_workspace,
)
from core.security import require_auth
from fastapi import APIRouter, Depends, HTTPException, Query, status
from services.execution_log import get_execution, list_executions
from sqlalchemy.orm import Session

from api.models.agent_execution import ExecutionListResponse, ExecutionResponse
from api.models.workspace import Workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/executions", tags=["executions"])


@router.get("", response_model=ExecutionListResponse)
async def list_workspace_executions(
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
):
    """List the current workspace's run history, newest first."""
    executions, total = list_executions(db, workspace.id, limit=limit)
    return ExecutionListResponse(
        executions=[ExecutionResponse.model_validate(e) for e in executions],
        total=total,
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_workspace_execution(
    execution_id: int,
    auth: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Fetch one run record; the caller needs >= viewer access to its workspace."""
    execution = get_execution(db, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found"
        )
    sub = auth.get("sub")
    user_id = int(sub) if sub is not None and str(sub).isdigit() else None
    if user_id is None or not check_workspace_access(
        db, user_id, execution.workspace_id, WorkspaceRole.VIEWER
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient workspace permissions",
        )
    return ExecutionResponse.model_validate(execution)
