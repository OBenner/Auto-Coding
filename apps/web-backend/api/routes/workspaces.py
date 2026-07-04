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
    require_workspace_access,
    user_role_in_workspace,
)
from core.security import require_auth
from fastapi import APIRouter, Depends, HTTPException, status
from services.workspace_service import (
    add_member,
    create_workspace,
    get_membership,
    list_accessible_workspaces,
    list_workspace_members,
    remove_member,
    update_member_role,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.workspace import (
    Workspace,
    WorkspaceCreateRequest,
    WorkspaceListResponse,
    WorkspaceMemberAddRequest,
    WorkspaceMemberListResponse,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdateRequest,
    WorkspaceResponse,
    WorkspaceUser,
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


def require_team_mode() -> None:
    """Reject management requests in single mode (one auto-Personal workspace).

    Creating extra workspaces and managing members are team-mode features; in
    single mode the lone Personal workspace is auto-created and not shared.
    """
    if settings.CLOUD_MODE != "team":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace management is only available in team mode",
        )


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
):
    """List every workspace the caller can access, with their role in each."""
    user_id = _require_user_id(auth)
    workspaces = list_accessible_workspaces(db, user_id)
    # Resolve roles with a single membership query (avoids an N+1 over
    # user_role_in_workspace): owners are detected from owner_id directly.
    member_roles = {
        wu.workspace_id: wu.role
        for wu in db.query(WorkspaceUser).filter(WorkspaceUser.user_id == user_id)
    }
    items: list[WorkspaceResponse] = []
    for ws in workspaces:
        role = (
            WorkspaceRole.OWNER
            if ws.owner_id == user_id
            else WorkspaceRole(member_roles.get(ws.id, WorkspaceRole.VIEWER.value))
        )
        items.append(_to_response(ws, role))
    return WorkspaceListResponse(workspaces=items, cloud_mode=settings.CLOUD_MODE)


@router.get("/current", response_model=WorkspaceResponse)
async def current_workspace(
    workspace: Workspace = Depends(get_current_workspace),
    auth: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Resolve the current workspace (Personal in single mode; ?workspace_id in team)."""
    user_id = _require_user_id(auth)
    role = user_role_in_workspace(db, user_id, workspace.id) or WorkspaceRole.VIEWER
    return _to_response(workspace, role)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace_endpoint(
    request: WorkspaceCreateRequest,
    _team: None = Depends(require_team_mode),
    auth: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a workspace owned by the caller (team mode only)."""
    user_id = _require_user_id(auth)
    workspace = create_workspace(db, owner_id=user_id, name=request.name)
    return _to_response(workspace, WorkspaceRole.OWNER)


# ---------------------------------------------------------------------------
# Member management (team mode) — the first real consumer of
# require_workspace_access: listing needs >= viewer, mutations need owner.
# ---------------------------------------------------------------------------


def _member_response(user_id: int, email: str, role: str) -> WorkspaceMemberResponse:
    return WorkspaceMemberResponse(user_id=user_id, email=email, role=role)


@router.get("/{workspace_id}/members", response_model=WorkspaceMemberListResponse)
async def list_members(
    workspace_id: int,
    _team: None = Depends(require_team_mode),
    _role: WorkspaceRole = Depends(require_workspace_access(WorkspaceRole.VIEWER)),
    db: Session = Depends(get_db),
):
    """List a workspace's members (owner first). Team mode; requires >= viewer."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )
    members = [_member_response(workspace.owner_id, workspace.owner.email, "owner")]
    members.extend(
        _member_response(wu.user_id, wu.user.email, wu.role)
        for wu in list_workspace_members(db, workspace_id)
    )
    return WorkspaceMemberListResponse(members=members)


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_workspace_member(
    workspace_id: int,
    request: WorkspaceMemberAddRequest,
    _team: None = Depends(require_team_mode),
    _role: WorkspaceRole = Depends(require_workspace_access(WorkspaceRole.OWNER)),
    db: Session = Depends(get_db),
):
    """Add a member to a workspace. Team mode; requires owner access."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )
    if request.user_id == workspace.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The workspace owner already has access",
        )
    user = db.query(User).filter(User.id == request.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if get_membership(db, workspace_id, request.user_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User is already a member"
        )
    try:
        membership = add_member(db, workspace_id, request.user_id, request.role)
    except IntegrityError:
        # Lost a race against a concurrent add (uq_workspace_user); return 409.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User is already a member"
        ) from None
    return _member_response(membership.user_id, user.email, membership.role)


@router.patch(
    "/{workspace_id}/members/{user_id}", response_model=WorkspaceMemberResponse
)
async def update_workspace_member(
    workspace_id: int,
    user_id: int,
    request: WorkspaceMemberUpdateRequest,
    _team: None = Depends(require_team_mode),
    _role: WorkspaceRole = Depends(require_workspace_access(WorkspaceRole.OWNER)),
    db: Session = Depends(get_db),
):
    """Change a member's role. Team mode; requires owner access."""
    membership = get_membership(db, workspace_id, user_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found"
        )
    membership = update_member_role(db, membership, request.role)
    return _member_response(membership.user_id, membership.user.email, membership.role)


@router.delete(
    "/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_workspace_member(
    workspace_id: int,
    user_id: int,
    _team: None = Depends(require_team_mode),
    _role: WorkspaceRole = Depends(require_workspace_access(WorkspaceRole.OWNER)),
    db: Session = Depends(get_db),
):
    """Remove a member from a workspace. Requires owner access."""
    membership = get_membership(db, workspace_id, user_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found"
        )
    remove_member(db, membership)
