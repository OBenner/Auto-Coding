"""Enforce one Personal workspace per owner (partial unique index)

Revision ID: 004
Revises: 003
Create Date: 2026-06-25 00:00:00.000000

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
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAME = "uq_personal_workspace_per_owner"


def upgrade() -> None:
    """Add a partial unique index: at most one 'Personal' workspace per owner."""
    # Pre-clean any pre-existing duplicate Personal workspaces (created before
    # this constraint, e.g. by a racy bootstrap) so the unique index can build.
    # Keep the oldest (lowest id) per owner — matching get_or_create's behaviour.
    op.execute(
        sa.text(
            "DELETE FROM workspaces WHERE name = 'Personal' AND id NOT IN ("
            "  SELECT MIN(id) FROM workspaces WHERE name = 'Personal' "
            "  GROUP BY owner_id"
            ")"
        )
    )
    op.create_index(
        _INDEX_NAME,
        "workspaces",
        ["owner_id"],
        unique=True,
        sqlite_where=sa.text("name = 'Personal'"),
        postgresql_where=sa.text("name = 'Personal'"),
    )


def downgrade() -> None:
    """Drop the partial unique index."""
    op.drop_index(_INDEX_NAME, table_name="workspaces")
