"""add review start idempotency key

Revision ID: a02a1e010b45
Revises: ff4cd2343642
Create Date: 2026-08-17 15:09:18.391327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a02a1e010b45"
down_revision: Union[str, Sequence[str], None] = "ff4cd2343642"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add durable Review Start request identity."""
    with op.batch_alter_table("review_sessions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "client_request_id",
                sa.String(length=120),
                nullable=True,
            )
        )
        batch_op.create_unique_constraint(
            "uq_review_sessions_team_client_request_id",
            ["team_id", "client_request_id"],
        )


def downgrade() -> None:
    """Remove durable Review Start request identity."""
    with op.batch_alter_table("review_sessions") as batch_op:
        batch_op.drop_constraint(
            "uq_review_sessions_team_client_request_id",
            type_="unique",
        )
        batch_op.drop_column("client_request_id")
