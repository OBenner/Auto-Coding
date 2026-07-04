"""Create spec_records + spec_audit_entries (FS-backed spec index/audit)

Revision ID: 006
Revises: 005
Create Date: 2026-07-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Alembic requires these module-level identifiers
__all__ = [
    "revision",
    "down_revision",
    "branch_labels",
    "depends_on",
    "upgrade",
    "downgrade",
]

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the spec index (cache of FS state) and its audit trail."""
    op.create_table(
        "spec_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("folder", sa.String(length=255), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "progress", sa.String(length=20), nullable=False, server_default=""
        ),
        sa.Column(
            "has_build", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("workspace_id", "folder", name="uq_spec_record_folder"),
    )
    op.create_index(
        op.f("ix_spec_records_workspace_id"),
        "spec_records",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_spec_records_folder"), "spec_records", ["folder"], unique=False
    )

    op.create_table(
        "spec_audit_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("spec_record_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["spec_record_id"], ["spec_records.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "action IN ('created', 'updated', 'deleted')",
            name="ck_spec_audit_action",
        ),
    )
    # Composite: serves both the spec filter and the newest-first (id DESC) order.
    op.create_index(
        "ix_spec_audit_record_newest",
        "spec_audit_entries",
        ["spec_record_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop spec_audit_entries and spec_records."""
    op.drop_index(
        "ix_spec_audit_record_newest",
        table_name="spec_audit_entries",
    )
    op.drop_table("spec_audit_entries")
    op.drop_index(op.f("ix_spec_records_folder"), table_name="spec_records")
    op.drop_index(op.f("ix_spec_records_workspace_id"), table_name="spec_records")
    op.drop_table("spec_records")
