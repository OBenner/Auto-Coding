"""
Workspace and membership models for cloud-hosted Auto Code (team mode).

A Workspace is the tenant boundary that owns specs, runs, and repositories.
In single-user mode one "Personal" workspace is bootstrapped; in team mode there
are many, each with role-based members (see WorkspaceUser). Roles are checked in
core/permissions.py.
"""

from datetime import UTC, datetime
from typing import Literal

from core.database import Base
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship


class Workspace(Base):
    """A tenant boundary owning specs/runs/repositories, with role-based members."""

    __tablename__ = "workspaces"
    __table_args__ = (
        # At most one "Personal" workspace per owner (partial unique index) — this
        # makes get_or_create_personal_workspace race-safe under concurrent
        # register/login. Other workspace names are unconstrained.
        Index(
            "uq_personal_workspace_per_owner",
            "owner_id",
            unique=True,
            sqlite_where=text("name = 'Personal'"),
            postgresql_where=text("name = 'Personal'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    # RESTRICT, not CASCADE: deleting a user must not silently destroy a whole
    # workspace (and its specs/runs). Ownership transfer/deletion is explicit
    # application logic (Track C).
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    owner = relationship("User")
    members = relationship(
        "WorkspaceUser", back_populates="workspace", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Workspace(id={self.id}, name={self.name!r}, owner_id={self.owner_id})>"


class WorkspaceUser(Base):
    """Membership linking a user to a workspace with a role (owner/editor/viewer)."""

    __tablename__ = "workspace_users"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
        # Mirror the WorkspaceRole closed set (core/permissions.py) at the DB level.
        CheckConstraint(
            "role IN ('owner', 'editor', 'viewer')", name="ck_workspace_user_role"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(20), nullable=False, default="viewer")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<WorkspaceUser(workspace_id={self.workspace_id}, "
            f"user_id={self.user_id}, role={self.role!r})>"
        )


# Closed sets for invitations; the DB CHECK constraints are derived from them.
INVITATION_ROLES = ("owner", "editor", "viewer")
INVITATION_STATUSES = ("pending", "accepted", "revoked")
_INVITATION_ROLES_SQL = ", ".join(f"'{r}'" for r in INVITATION_ROLES)
_INVITATION_STATUSES_SQL = ", ".join(f"'{s}'" for s in INVITATION_STATUSES)


class WorkspaceInvitation(Base):
    """An email invitation into a workspace (C7 — team onboarding).

    Inviting an existing user adds the membership immediately and records the
    invitation as ``accepted`` (audit of who invited whom); inviting an unknown
    email stays ``pending`` until that email registers, at which point pending
    invitations convert into memberships. Emails are stored lowercased.
    """

    __tablename__ = "workspace_invitations"
    __table_args__ = (
        CheckConstraint(
            f"role IN ({_INVITATION_ROLES_SQL})",
            name="ck_workspace_invitation_role",
        ),
        CheckConstraint(
            f"status IN ({_INVITATION_STATUSES_SQL})",
            name="ck_workspace_invitation_status",
        ),
        # At most one *pending* invitation per (workspace, email); accepted or
        # revoked history rows are unconstrained.
        Index(
            "uq_pending_invitation_per_email",
            "workspace_id",
            "email",
            unique=True,
            sqlite_where=text("status = 'pending'"),
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="viewer")
    status = Column(String(20), nullable=False, default="pending")
    # SET NULL: the invitation audit survives the inviter's deletion.
    invited_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    responded_at = Column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace")

    def __repr__(self) -> str:
        return (
            f"<WorkspaceInvitation(id={self.id}, workspace_id={self.workspace_id}, "
            f"status={self.status!r})>"
        )


# Pydantic models for API requests and responses


class WorkspaceCreateRequest(BaseModel):
    """Request model for creating a workspace (team mode)."""

    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")


class WorkspaceResponse(BaseModel):
    """Response model for a workspace, including the caller's role in it."""

    id: int = Field(..., description="Workspace ID")
    name: str = Field(..., description="Workspace name")
    role: str = Field(..., description="Caller's role: owner/editor/viewer")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class WorkspaceListResponse(BaseModel):
    """Response model for the list of workspaces the caller can access."""

    workspaces: list[WorkspaceResponse] = Field(
        default_factory=list, description="Accessible workspaces"
    )
    cloud_mode: str = Field(..., description="Deployment mode: single or team")


class WorkspaceMemberAddRequest(BaseModel):
    """Request model for adding a member to a workspace."""

    user_id: int = Field(..., description="Id of the user to add")
    role: Literal["owner", "editor", "viewer"] = Field(
        "viewer", description="Role to grant"
    )


class WorkspaceMemberUpdateRequest(BaseModel):
    """Request model for changing a member's role."""

    role: Literal["owner", "editor", "viewer"] = Field(..., description="New role")


class WorkspaceMemberResponse(BaseModel):
    """Response model for a single workspace member."""

    user_id: int = Field(..., description="Member user id")
    email: str = Field(..., description="Member email")
    role: str = Field(..., description="Member role: owner/editor/viewer")


class WorkspaceMemberListResponse(BaseModel):
    """Response model for the members of a workspace."""

    members: list[WorkspaceMemberResponse] = Field(
        default_factory=list, description="Workspace members (owner first)"
    )


class InvitationCreateRequest(BaseModel):
    """Request model for inviting someone into a workspace by email."""

    email: EmailStr = Field(..., description="Email address to invite")
    role: Literal["owner", "editor", "viewer"] = Field(
        "viewer", description="Role to grant on acceptance"
    )


class InvitationResponse(BaseModel):
    """Response model for one invitation (pending/accepted/revoked)."""

    id: int = Field(..., description="Invitation ID")
    workspace_id: int = Field(..., description="Workspace invited into")
    email: str = Field(..., description="Invited email (lowercased)")
    role: str = Field(..., description="Role granted on acceptance")
    status: str = Field(..., description="pending/accepted/revoked")
    invited_by: int | None = Field(None, description="User who sent the invitation")
    created_at: datetime = Field(..., description="When the invitation was created")
    responded_at: datetime | None = Field(
        None, description="When it was accepted/revoked"
    )

    model_config = ConfigDict(from_attributes=True)


class InvitationListResponse(BaseModel):
    """Response model for a workspace's invitations (newest first)."""

    invitations: list[InvitationResponse] = Field(
        default_factory=list, description="Invitations, newest first"
    )
