"""
Workspace and membership models for cloud-hosted Auto Code (team mode).

A Workspace is the tenant boundary that owns specs, runs, and repositories.
In single-user mode one "Personal" workspace is bootstrapped; in team mode there
are many, each with role-based members (see WorkspaceUser). Roles are checked in
core/permissions.py.
"""

from datetime import UTC, datetime

from core.database import Base
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship


class Workspace(Base):
    """A tenant boundary owning specs/runs/repositories, with role-based members."""

    __tablename__ = "workspaces"

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
