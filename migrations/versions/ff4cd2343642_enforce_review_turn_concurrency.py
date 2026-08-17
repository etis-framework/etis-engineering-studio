"""enforce review turn concurrency

Revision ID: ff4cd2343642
Revises: fcd1f7578040
Create Date: 2026-08-17 13:44:35.411790

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ff4cd2343642"
down_revision: Union[str, Sequence[str], None] = "fcd1f7578040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add database-enforced ordering and idempotency for review turns."""
    with op.batch_alter_table("review_turns") as batch_op:
        batch_op.add_column(
            sa.Column(
                "client_turn_id",
                sa.String(length=120),
                nullable=True,
            )
        )
        batch_op.create_unique_constraint(
            "uq_review_turns_session_client_turn_id",
            ["session_id", "client_turn_id"],
        )
        batch_op.create_unique_constraint(
            "uq_review_turns_session_sequence",
            ["session_id", "sequence"],
        )


def downgrade() -> None:
    """Remove review-turn concurrency constraints."""
    with op.batch_alter_table("review_turns") as batch_op:
        batch_op.drop_constraint(
            "uq_review_turns_session_sequence",
            type_="unique",
        )
        batch_op.drop_constraint(
            "uq_review_turns_session_client_turn_id",
            type_="unique",
        )
        batch_op.drop_column("client_turn_id")
