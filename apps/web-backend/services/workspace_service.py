"""
Workspace bootstrap and listing helpers (Track C — cloud multitenancy).

In single-user mode every user gets one auto-created "Personal" workspace that
owns their specs/runs/repos; in team mode users own and join many. These are the
deterministic, unit-testable helpers used by the workspace routes and the
``get_current_workspace`` dependency in ``core/permissions.py``.

Owner access derives from ``Workspace.owner_id`` (see core/permissions.py), so a
Personal workspace needs no membership row — listing unions owned workspaces with
``WorkspaceUser`` memberships rather than relying on a redundant owner row.
"""

import logging

from api.models.workspace import Workspace, WorkspaceUser
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)

# Name of the auto-created single-user workspace.
PERSONAL_WORKSPACE_NAME = "Personal"


def get_or_create_personal_workspace(db: Session, user_id: int) -> Workspace:
    """Return the user's Personal workspace, creating it if absent (idempotent).

    This is the single-mode default workspace. If the user already owns one named
    ``PERSONAL_WORKSPACE_NAME`` the oldest such workspace is reused, so repeated
    calls (e.g. on every login) never create duplicates.
    """
    existing = (
        db.query(Workspace)
        .filter(
            Workspace.owner_id == user_id,
            Workspace.name == PERSONAL_WORKSPACE_NAME,
        )
        .order_by(Workspace.id.asc())
        .first()
    )
    if existing is not None:
        return existing

    workspace = Workspace(name=PERSONAL_WORKSPACE_NAME, owner_id=user_id)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    logger.info(
        "Bootstrapped Personal workspace id=%s for user_id=%s", workspace.id, user_id
    )
    return workspace


def list_accessible_workspaces(db: Session, user_id: int) -> list[Workspace]:
    """Workspaces the user can access: those they own plus those they're a member of."""
    member_ids = db.query(WorkspaceUser.workspace_id).filter(
        WorkspaceUser.user_id == user_id
    )
    return (
        db.query(Workspace)
        .filter(
            or_(
                Workspace.owner_id == user_id,
                Workspace.id.in_(member_ids),
            )
        )
        .order_by(Workspace.id.asc())
        .all()
    )


def create_workspace(db: Session, owner_id: int, name: str) -> Workspace:
    """Create a workspace owned by ``owner_id`` (team mode). Owner access is implicit."""
    workspace = Workspace(name=name, owner_id=owner_id)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    # Do not log the user-supplied name (log-injection); id + owner suffice.
    logger.info("Created workspace id=%s owner_id=%s", workspace.id, owner_id)
    return workspace


def list_workspace_members(db: Session, workspace_id: int) -> list[WorkspaceUser]:
    """Return the explicit membership rows for a workspace (excludes the owner).

    Eager-loads the related user so callers can read ``wu.user`` without an N+1.
    """
    return (
        db.query(WorkspaceUser)
        .options(joinedload(WorkspaceUser.user))
        .filter(WorkspaceUser.workspace_id == workspace_id)
        .order_by(WorkspaceUser.id.asc())
        .all()
    )


def get_membership(
    db: Session, workspace_id: int, user_id: int
) -> WorkspaceUser | None:
    """Return the user's membership row in the workspace, or None."""
    return (
        db.query(WorkspaceUser)
        .filter(
            WorkspaceUser.workspace_id == workspace_id,
            WorkspaceUser.user_id == user_id,
        )
        .first()
    )


def add_member(
    db: Session, workspace_id: int, user_id: int, role: str
) -> WorkspaceUser:
    """Insert a membership row (callers validate uniqueness/owner/user first)."""
    membership = WorkspaceUser(
        workspace_id=workspace_id, user_id=user_id, role=role
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    logger.info(
        "Added member user_id=%s role=%s to workspace_id=%s",
        user_id,
        role,
        workspace_id,
    )
    return membership


def update_member_role(
    db: Session, membership: WorkspaceUser, role: str
) -> WorkspaceUser:
    """Update a membership's role in place."""
    membership.role = role
    db.commit()
    db.refresh(membership)
    return membership


def remove_member(db: Session, membership: WorkspaceUser) -> None:
    """Delete a membership row."""
    db.delete(membership)
    db.commit()
