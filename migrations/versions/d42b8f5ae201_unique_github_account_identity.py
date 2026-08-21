"""enforce unique immutable GitHub account identity

Revision ID: d42b8f5ae201
Revises: c8c7d5f44e31
Create Date: 2026-08-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d42b8f5ae201"
down_revision: Union[str, Sequence[str], None] = "c8c7d5f44e31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind=op.get_bind()

    duplicates=bind.execute(
        sa.text(
            "SELECT github_user_id, COUNT(*) "
            "FROM github_identities "
            "WHERE github_user_id <> '' "
            "GROUP BY github_user_id "
            "HAVING COUNT(*) > 1"
        )
    ).fetchall()

    if duplicates:
        raise RuntimeError(
            "Duplicate immutable GitHub account IDs exist; "
            "resolve them before applying this migration"
        )

    op.create_index(
        "uq_github_identities_github_user_id_nonempty",
        "github_identities",
        ["github_user_id"],
        unique=True,
        sqlite_where=sa.text("github_user_id <> ''"),
        postgresql_where=sa.text("github_user_id <> ''"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_github_identities_github_user_id_nonempty",
        table_name="github_identities",
    )
