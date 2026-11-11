"""Persist search language, mode, sorting, and filters.

Revision ID: 0002_search_options
Revises: 0001_initial
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_search_options"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("searches") as batch_op:
        batch_op.add_column(
            sa.Column("language", sa.String(length=10), server_default="en", nullable=False)
        )
        batch_op.add_column(
            sa.Column(
                "search_mode",
                sa.String(length=20),
                server_default="advanced",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "sort_by",
                sa.String(length=20),
                server_default="relevance",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("min_year", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("max_year", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("min_impact_factor", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("searches") as batch_op:
        batch_op.drop_column("min_impact_factor")
        batch_op.drop_column("max_year")
        batch_op.drop_column("min_year")
        batch_op.drop_column("sort_by")
        batch_op.drop_column("search_mode")
        batch_op.drop_column("language")
