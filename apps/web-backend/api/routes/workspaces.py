"""
Workspace management API (Track C — cloud multitenancy).

Lets the frontend list the workspaces a user can access, resolve the current one
(the workspace switcher), and create workspaces in team mode. Access is enforced
via core/permissions.py; the single-mode "Personal" workspace is auto-created.
"""

import logging

from core.config import settings
from core.database import get_db
from core.permissions import (
    WorkspaceRole,
    get_current_workspace,
    user_role_in_workspace,
)
from core.security import require_auth
from fastapi import APIRouter, Depends, HTTPException, status
from services.workspace_service import create_workspace, list_accessible_workspaces
from sqlalchemy.orm import Session

from api.models.workspace import (
    Workspace,
    WorkspaceCreateRequest,
    WorkspaceListResponse,
    WorkspaceResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def _require_user_id(auth: dict) -> int:
    """Return the integer user id from the token claims, or raise 403."""
    sub = auth.get("sub")
    if sub is None or not str(sub).isdigit():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No authenticated user in token",
        )
    return int(sub)


def _to_response(workspace: Workspace, role: WorkspaceRole) -> WorkspaceResponse:
    """Build a WorkspaceResponse including the caller's role string."""
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        role=role.value,
        created_at=workspace.created_at,
    )


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    auth: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> WorkspaceListResponse:
    """List every workspace the caller can access, with their role in each."""
    user_id = _require_user_id(auth)
    items: list[WorkspaceResponse] = []
    for ws in list_accessible_workspaces(db, user_id):
        role = user_role_in_workspace(db, user_id, ws.id) or WorkspaceRole.VIEWER
        items.append(_to_response(ws, role))
    return WorkspaceListResponse(workspaces=items, cloud_mode=settings.CLOUD_MODE)


@router.get("/current", response_model=WorkspaceResponse)
async def current_workspace(
    workspace: Workspace = Depends(get_current_workspace),
    auth: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    """Resolve the current workspace (Personal in single mode; ?workspace_id in team)."""
    user_id = _require_user_id(auth)
    role = user_role_in_workspace(db, user_id, workspace.id) or WorkspaceRole.VIEWER
    return _to_response(workspace, role)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace_endpoint(
    request: WorkspaceCreateRequest,
    auth: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    """Create a workspace owned by the caller (used in team mode)."""
    user_id = _require_user_id(auth)
    workspace = create_workspace(db, owner_id=user_id, name=request.name)
    return _to_response(workspace, WorkspaceRole.OWNER)
