"""Add durable background-search job fields.

Revision ID: 0003_search_jobs
Revises: 0002_search_options
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_search_jobs"
down_revision: Union[str, None] = "0002_search_options"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("searches") as batch_op:
        batch_op.add_column(sa.Column("job_id", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column(
                "cancel_requested",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_searches_job_id", ["job_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("searches") as batch_op:
        batch_op.drop_index("ix_searches_job_id")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("cancel_requested")
        batch_op.drop_column("job_id")
