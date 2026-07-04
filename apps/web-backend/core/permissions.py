"""
Workspace-scoped role checks for cloud-hosted Auto Code (team mode).

Roles are hierarchical: owner > editor > viewer. ``check_workspace_access`` is
the pure, unit-testable core; ``require_workspace_access`` wraps it as a FastAPI
dependency for routes that carry a ``workspace_id``. In single-user mode the lone
"Personal" workspace owner satisfies every check.
"""

from enum import Enum

from api.models.workspace import Workspace, WorkspaceUser
from fastapi import Depends, HTTPException, status
from services.workspace_service import get_or_create_personal_workspace
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.security import require_auth


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


# Higher rank = more privilege.
_ROLE_RANK: dict[WorkspaceRole, int] = {
    WorkspaceRole.VIEWER: 0,
    WorkspaceRole.EDITOR: 1,
    WorkspaceRole.OWNER: 2,
}

# Reused 403 detail for workspace permission failures (avoid a duplicated literal).
_INSUFFICIENT_PERMISSIONS = "Insufficient workspace permissions"


def role_satisfies(actual: "WorkspaceRole | str", required: "WorkspaceRole | str") -> bool:
    """True when ``actual`` grants at least the privilege of ``required``."""
    try:
        return _ROLE_RANK[WorkspaceRole(actual)] >= _ROLE_RANK[WorkspaceRole(required)]
    except (ValueError, KeyError):
        return False


def user_role_in_workspace(
    db: Session, user_id: int, workspace_id: int
) -> WorkspaceRole | None:
    """Return the user's effective role in the workspace, or None if no access.

    The workspace owner (``Workspace.owner_id``) always has owner-level access,
    even without an explicit membership row — this is what makes the single-user
    "Personal" workspace owner satisfy every check. Everyone else gets the role
    from their ``WorkspaceUser`` membership.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if workspace is not None and workspace.owner_id == user_id:
        return WorkspaceRole.OWNER

    membership = (
        db.query(WorkspaceUser)
        .filter(
            WorkspaceUser.workspace_id == workspace_id,
            WorkspaceUser.user_id == user_id,
        )
        .first()
    )
    if membership is None:
        return None
    try:
        return WorkspaceRole(membership.role)
    except ValueError:
        return None


def check_workspace_access(
    db: Session,
    user_id: int,
    workspace_id: int,
    required_role: WorkspaceRole = WorkspaceRole.VIEWER,
) -> bool:
    """True when the user has at least ``required_role`` (owner or membership)."""
    role = user_role_in_workspace(db, user_id, workspace_id)
    return role is not None and role_satisfies(role, required_role)


def current_user_id(auth: dict) -> int | None:
    """Extract the integer user id from JWT claims (``sub`` is ``str(user.id)``).

    Returns None for legacy/service tokens whose ``sub`` is not numeric — the
    single place that encodes this rule; routes must reuse it, not re-parse.
    """
    sub = auth.get("sub")
    return int(sub) if sub is not None and str(sub).isdigit() else None


def require_workspace_access(required_role: WorkspaceRole = WorkspaceRole.VIEWER):
    """FastAPI dependency factory.

    Returns a dependency that raises 403 unless the authenticated user has at
    least ``required_role`` in the route's ``workspace_id`` path/query param.
    On success it returns the resolved WorkspaceRole.
    """

    def dependency(
        workspace_id: int,
        auth: dict = Depends(require_auth),
        db: Session = Depends(get_db),
    ) -> WorkspaceRole:
        user_id = current_user_id(auth)
        role = (
            user_role_in_workspace(db, user_id, workspace_id)
            if user_id is not None
            else None
        )
        if role is None or not role_satisfies(role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_INSUFFICIENT_PERMISSIONS,
            )
        return role

    return dependency


def get_current_workspace(
    workspace_id: int | None = None,
    auth: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Workspace:
    """Resolve the workspace for the current request.

    - **single mode** (``CLOUD_MODE=single``): the caller's auto-created
      "Personal" workspace (``workspace_id`` is ignored). Created on first use.
    - **team mode**: the workspace named by the ``workspace_id`` query parameter,
      which the caller must be able to access (>= viewer) — else 400/403.

    Returns the resolved ``Workspace`` ORM object.
    """
    user_id = current_user_id(auth)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No authenticated user in token",
        )

    if settings.CLOUD_MODE == "single":
        return get_or_create_personal_workspace(db, user_id)

    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is required in team mode",
        )
    # Check access first; only fetch the workspace row once access is granted.
    if not check_workspace_access(db, user_id, workspace_id, WorkspaceRole.VIEWER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_INSUFFICIENT_PERMISSIONS,
        )
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if workspace is None:  # pragma: no cover - access check already proved existence
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_INSUFFICIENT_PERMISSIONS,
        )
    return workspace
