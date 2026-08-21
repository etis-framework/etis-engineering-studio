"""add repository onboarding authority state

Revision ID: c8c7d5f44e31
Revises: a02a1e010b45
Create Date: 2026-08-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8c7d5f44e31"
down_revision: Union[str, Sequence[str], None] = "a02a1e010b45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Persist candidate ownership and authorization state."""
    with op.batch_alter_table("repository_connections") as batch_op:
        batch_op.add_column(
            sa.Column("owner_type", sa.String(length=20), nullable=True)
        )
        batch_op.add_column(
            sa.Column("owner_login", sa.String(length=120), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "owner_github_account_id",
                sa.String(length=80),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "authorization_requested_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

    # Legacy pre-verification rows were mirrored into teams.repo_full_name by
    # the old onboarding flow. Clear that authoritative evidence pointer before
    # converting those rows to candidates. Verified rows remain untouched.
    op.execute(
        sa.text(
            "UPDATE teams SET repo_full_name = '' "
            "WHERE id IN ("
            "SELECT team_id FROM repository_connections "
            "WHERE status IN ('identified', 'awaiting_access')"
            ")"
        )
    )

    op.execute(
        sa.text(
            "UPDATE repository_connections "
            "SET status = 'candidate' "
            "WHERE status IN ('identified', 'awaiting_access')"
        )
    )

    op.execute(
        sa.text(
            "UPDATE repository_connections "
            "SET status = 'verified' "
            "WHERE status = 'connected'"
        )
    )


def downgrade() -> None:
    """Remove repository onboarding authority state."""
    op.execute(
        sa.text(
            "UPDATE repository_connections "
            "SET status = 'awaiting_access' "
            "WHERE status IN ('candidate', 'owner_authorization_required')"
        )
    )

    with op.batch_alter_table("repository_connections") as batch_op:
        batch_op.drop_column("authorization_requested_at")
        batch_op.drop_column("owner_github_account_id")
        batch_op.drop_column("owner_login")
        batch_op.drop_column("owner_type")
