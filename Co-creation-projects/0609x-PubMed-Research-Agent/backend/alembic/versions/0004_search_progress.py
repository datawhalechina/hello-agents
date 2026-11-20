"""Add durable search progress snapshots.

Revision ID: 0004_search_progress
Revises: 0003_search_jobs
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_search_progress"
down_revision: Union[str, None] = "0003_search_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("searches") as batch_op:
        batch_op.add_column(
            sa.Column(
                "progress_percent", sa.Integer(), server_default="0", nullable=False
            )
        )
        batch_op.add_column(
            sa.Column(
                "progress_stage",
                sa.String(length=40),
                server_default="queued",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "progress_message",
                sa.String(length=255),
                server_default="",
                nullable=False,
            )
        )
    op.execute(
        sa.text(
            """
            UPDATE searches
            SET progress_percent = 100,
                progress_stage = status
            WHERE status IN ('completed', 'partial', 'failed', 'cancelled')
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("searches") as batch_op:
        batch_op.drop_column("progress_message")
        batch_op.drop_column("progress_stage")
        batch_op.drop_column("progress_percent")
