"""Add workspace_id to repositories (workspace-scoped repo links)

Revision ID: 007
Revises: 006
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
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FK_NAME = "fk_repositories_workspace_id"
_IX_NAME = "ix_repositories_workspace_id"


def upgrade() -> None:
    """Scope repository links by workspace (nullable for migration safety).

    batch_alter_table keeps this portable: plain ALTERs on Postgres, a table
    rebuild on SQLite (which cannot add an FK column in place).
    """
    with op.batch_alter_table("repositories") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            _FK_NAME, "workspaces", ["workspace_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_index(_IX_NAME, ["workspace_id"], unique=False)

    # Defensive backfill: no code path ever wrote to this table before C6, but
    # if rows exist (manual/out-of-band inserts), attach them to their owner's
    # Personal workspace so they stay visible through the workspace-scoped API.
    # Rows whose owner has no Personal workspace keep NULL (same visibility as
    # before this migration: none — there was no listing endpoint).
    op.execute(
        sa.text(
            "UPDATE repositories SET workspace_id = ("
            "  SELECT w.id FROM workspaces w"
            "  WHERE w.owner_id = repositories.user_id AND w.name = 'Personal'"
            ") WHERE workspace_id IS NULL"
        )
    )


def downgrade() -> None:
    """Drop the workspace scoping column."""
    with op.batch_alter_table("repositories") as batch_op:
        batch_op.drop_index(_IX_NAME)
        batch_op.drop_constraint(_FK_NAME, type_="foreignkey")
        batch_op.drop_column("workspace_id")
