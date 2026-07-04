"""Create agent_executions table (run history / audit)

Revision ID: 005
Revises: 004
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
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create agent_executions: workspace-scoped, user-attributed run records."""
    op.create_table(
        "agent_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("spec_id", sa.String(length=255), nullable=False),
        sa.Column("agent_type", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="running"
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        # SET NULL: audit records survive user deletion.
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "agent_type IN ('planner', 'coder', 'qa_reviewer', 'qa_fixer')",
            name="ck_agent_execution_type",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled')",
            name="ck_agent_execution_status",
        ),
    )
    op.create_index(
        op.f("ix_agent_executions_workspace_id"),
        "agent_executions",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_executions_user_id"),
        "agent_executions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_executions_spec_id"),
        "agent_executions",
        ["spec_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop agent_executions."""
    op.drop_index(op.f("ix_agent_executions_spec_id"), table_name="agent_executions")
    op.drop_index(op.f("ix_agent_executions_user_id"), table_name="agent_executions")
    op.drop_index(
        op.f("ix_agent_executions_workspace_id"), table_name="agent_executions"
    )
    op.drop_table("agent_executions")
