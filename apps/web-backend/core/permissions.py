"""
Workspace-scoped role checks for cloud-hosted Auto Code (team mode).

Roles are hierarchical: owner > editor > viewer. ``check_workspace_access`` is
the pure, unit-testable core; ``require_workspace_access`` wraps it as a FastAPI
dependency for routes that carry a ``workspace_id``. In single-user mode the lone
"Personal" workspace owner satisfies every check.
"""

from enum import Enum

from api.models.workspace import WorkspaceUser
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

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


def role_satisfies(actual: "WorkspaceRole | str", required: "WorkspaceRole | str") -> bool:
    """True when ``actual`` grants at least the privilege of ``required``."""
    try:
        return _ROLE_RANK[WorkspaceRole(actual)] >= _ROLE_RANK[WorkspaceRole(required)]
    except (ValueError, KeyError):
        return False


def user_role_in_workspace(
    db: Session, user_id: int, workspace_id: int
) -> WorkspaceRole | None:
    """Return the user's role in the workspace, or None if they are not a member."""
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
    """True when the user is a member of the workspace with at least ``required_role``."""
    role = user_role_in_workspace(db, user_id, workspace_id)
    return role is not None and role_satisfies(role, required_role)


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
        sub = auth.get("sub")
        user_id = int(sub) if sub is not None and str(sub).isdigit() else None
        role = (
            user_role_in_workspace(db, user_id, workspace_id)
            if user_id is not None
            else None
        )
        if role is None or not role_satisfies(role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient workspace permissions",
            )
        return role

    return dependency
