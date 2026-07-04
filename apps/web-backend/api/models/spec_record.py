"""
Spec index + audit trail for cloud-hosted Auto Code (Track C — C4).

The filesystem stays the source of truth for specs (`.auto-claude/specs/`);
these tables are a workspace-scoped **cache/audit layer** on top of it:
``SpecRecord`` mirrors what the FS listing last showed, and every observed
change (created / updated / deleted) is appended to ``SpecAuditEntry`` so spec
edits are auditable per workspace (UC-T, compliance). Rows are written by
services/spec_index.py during listing sync — never edited by hand.
"""

from datetime import UTC, datetime

from core.database import Base
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

# Closed set; the DB CHECK constraint below is derived from it (no drift).
AUDIT_ACTIONS = ("created", "updated", "deleted")
_AUDIT_ACTIONS_SQL = ", ".join(f"'{action}'" for action in AUDIT_ACTIONS)


class SpecRecord(Base):
    """Last-known FS state of one spec, scoped to a workspace."""

    __tablename__ = "spec_records"
    __table_args__ = (
        UniqueConstraint("workspace_id", "folder", name="uq_spec_record_folder"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Canonical spec directory name, e.g. "001-user-auth".
    folder = Column(String(255), nullable=False, index=True)
    number = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)

    status = Column(String(50), nullable=False)
    progress = Column(String(20), nullable=False, default="")
    has_build = Column(Boolean, nullable=False, default=False)

    # Set when the folder disappears from the FS; cleared if it reappears.
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_synced_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    workspace = relationship("Workspace")
    audit_entries = relationship(
        "SpecAuditEntry",
        back_populates="spec_record",
        cascade="all, delete-orphan",
        order_by="SpecAuditEntry.id",
    )

    def __repr__(self) -> str:
        return (
            f"<SpecRecord(id={self.id}, workspace_id={self.workspace_id}, "
            f"folder={self.folder!r}, status={self.status!r})>"
        )


class SpecAuditEntry(Base):
    """One observed spec change: created / updated / deleted, with a detail line."""

    __tablename__ = "spec_audit_entries"
    __table_args__ = (
        CheckConstraint(
            f"action IN ({_AUDIT_ACTIONS_SQL})",
            name="ck_spec_audit_action",
        ),
        # Composite index: the audit API reads WHERE spec_record_id=? ORDER BY
        # id DESC — this serves both the filter and the newest-first order.
        Index("ix_spec_audit_record_newest", "spec_record_id", "id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    spec_record_id = Column(
        Integer,
        ForeignKey("spec_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    action = Column(String(20), nullable=False)
    # Human-readable change summary, e.g. "status: in_progress -> complete".
    detail = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    spec_record = relationship("SpecRecord", back_populates="audit_entries")

    def __repr__(self) -> str:
        return (
            f"<SpecAuditEntry(spec_record_id={self.spec_record_id}, "
            f"action={self.action!r})>"
        )


# Pydantic models for API responses


class SpecAuditEntryResponse(BaseModel):
    """Response model for one audit entry."""

    id: int = Field(..., description="Audit entry ID")
    action: str = Field(..., description="created/updated/deleted")
    detail: str | None = Field(None, description="Change summary")
    created_at: datetime = Field(..., description="When the change was observed")

    model_config = ConfigDict(from_attributes=True)


class SpecAuditResponse(BaseModel):
    """Response model for a spec's audit trail (newest first)."""

    folder: str = Field(..., description="Spec directory name")
    workspace_id: int = Field(..., description="Workspace the record belongs to")
    entries: list[SpecAuditEntryResponse] = Field(
        default_factory=list, description="Audit entries, newest first"
    )
