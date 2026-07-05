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
from datetime import UTC, datetime

from api.models.user import User
from api.models.workspace import Workspace, WorkspaceInvitation, WorkspaceUser
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)

# Name of the auto-created single-user workspace.
PERSONAL_WORKSPACE_NAME = "Personal"


class InvitationInvalid(Exception):
    """The invitation request itself is invalid (routes map this to 400)."""


class InvitationConflict(Exception):
    """The invitee already has access or a pending invite (routes map to 409)."""


def _find_personal_workspace(db: Session, user_id: int) -> Workspace | None:
    """Return the user's oldest workspace named PERSONAL_WORKSPACE_NAME, or None."""
    return (
        db.query(Workspace)
        .filter(
            Workspace.owner_id == user_id,
            Workspace.name == PERSONAL_WORKSPACE_NAME,
        )
        .order_by(Workspace.id.asc())
        .first()
    )


def get_or_create_personal_workspace(db: Session, user_id: int) -> Workspace:
    """Return the user's Personal workspace, creating it if absent (idempotent).

    This is the single-mode default workspace. A partial unique index
    (``uq_personal_workspace_per_owner``) guarantees one per owner, so concurrent
    register/login calls cannot create duplicates: the loser of the race catches
    the IntegrityError and reuses the winner's workspace.
    """
    existing = _find_personal_workspace(db, user_id)
    if existing is not None:
        return existing

    workspace = Workspace(name=PERSONAL_WORKSPACE_NAME, owner_id=user_id)
    db.add(workspace)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = _find_personal_workspace(db, user_id)
        if winner is None:  # pragma: no cover - the unique index guarantees one
            raise
        return winner
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
    # No info log here: user_id/role/workspace_id are request-derived (CodeQL
    # log-injection). Membership changes belong in the audit story (C3/C7).
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


# ---------------------------------------------------------------------------
# Invitations (C7) — email onboarding into workspaces
# ---------------------------------------------------------------------------


def _find_user_by_email(db: Session, email: str) -> User | None:
    """Case-insensitive user lookup by email."""
    return db.query(User).filter(func.lower(User.email) == email).first()


def invite_member(
    db: Session,
    workspace: Workspace,
    email: str,
    role: str,
    invited_by: int | None,
) -> WorkspaceInvitation:
    """Invite ``email`` into the workspace with ``role``.

    If a user with that email already exists, the membership is added
    immediately and the invitation is recorded as ``accepted`` (audit of who
    invited whom). Unknown emails get a ``pending`` invitation that converts on
    registration (see ``accept_pending_invitations``).

    Raises InvitationInvalid for the workspace owner, InvitationConflict for
    existing members and duplicate pending invitations (race-safe via the
    partial unique index).
    """
    normalized = email.strip().lower()
    now = datetime.now(UTC)
    user = _find_user_by_email(db, normalized)

    if user is not None:
        if user.id == workspace.owner_id:
            raise InvitationInvalid("The workspace owner already has access")
        if get_membership(db, workspace.id, user.id) is not None:
            raise InvitationConflict("User is already a member")

        invitation = WorkspaceInvitation(
            workspace_id=workspace.id,
            email=normalized,
            role=role,
            status="accepted",
            invited_by=invited_by,
            responded_at=now,
        )
        db.add(invitation)
        db.add(
            WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role=role)
        )
        try:
            db.commit()
        except IntegrityError:
            # Lost a race against a concurrent add (uq_workspace_user).
            db.rollback()
            raise InvitationConflict("User is already a member") from None
        db.refresh(invitation)
        return invitation

    invitation = WorkspaceInvitation(
        workspace_id=workspace.id,
        email=normalized,
        role=role,
        status="pending",
        invited_by=invited_by,
    )
    db.add(invitation)
    try:
        db.commit()
    except IntegrityError:
        # Partial unique index: one pending invitation per (workspace, email).
        db.rollback()
        raise InvitationConflict(
            "A pending invitation for this email already exists"
        ) from None
    db.refresh(invitation)
    return invitation


def list_invitations(db: Session, workspace_id: int) -> list[WorkspaceInvitation]:
    """A workspace's invitations, newest first."""
    return (
        db.query(WorkspaceInvitation)
        .filter(WorkspaceInvitation.workspace_id == workspace_id)
        .order_by(WorkspaceInvitation.id.desc())
        .all()
    )


def revoke_invitation(
    db: Session, workspace_id: int, invitation_id: int
) -> WorkspaceInvitation | None:
    """Revoke a pending invitation.

    Returns None when no such invitation exists in the workspace; raises
    InvitationConflict when it exists but is no longer pending.
    """
    invitation = (
        db.query(WorkspaceInvitation)
        .filter(
            WorkspaceInvitation.id == invitation_id,
            WorkspaceInvitation.workspace_id == workspace_id,
        )
        .first()
    )
    if invitation is None:
        return None
    if invitation.status != "pending":
        raise InvitationConflict("Only pending invitations can be revoked")
    invitation.status = "revoked"
    invitation.responded_at = datetime.now(UTC)
    db.commit()
    db.refresh(invitation)
    return invitation


def accept_pending_invitations(db: Session, user: User) -> int:
    """Convert the user's pending invitations into memberships (on registration).

    Returns the number of invitations accepted. Best-effort per invitation: a
    membership that already exists (or a lost insert race) still marks the
    invitation accepted rather than failing registration.
    """
    normalized = (user.email or "").strip().lower()
    if not normalized:
        return 0
    pending = (
        db.query(WorkspaceInvitation)
        .filter(
            WorkspaceInvitation.email == normalized,
            WorkspaceInvitation.status == "pending",
        )
        .all()
    )
    accepted = 0
    now = datetime.now(UTC)
    for invitation in pending:
        workspace = db.query(Workspace).filter(
            Workspace.id == invitation.workspace_id
        ).first()
        is_owner = workspace is not None and workspace.owner_id == user.id
        has_membership = (
            get_membership(db, invitation.workspace_id, user.id) is not None
        )
        if not is_owner and not has_membership:
            db.add(
                WorkspaceUser(
                    workspace_id=invitation.workspace_id,
                    user_id=user.id,
                    role=invitation.role,
                )
            )
        invitation.status = "accepted"
        invitation.responded_at = now
        try:
            db.commit()
        except IntegrityError:
            # Lost an insert race; the membership exists — mark accepted only.
            db.rollback()
            invitation.status = "accepted"
            invitation.responded_at = now
            db.commit()
        accepted += 1
    if accepted:
        logger.info(
            "Accepted %s pending invitation(s) for user_id=%s", accepted, user.id
        )
    return accepted
