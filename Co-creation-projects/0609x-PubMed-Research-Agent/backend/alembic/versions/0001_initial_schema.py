"""Create the original application schema.

Revision ID: 0001_initial
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "searches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("pubmed_query", sa.Text(), nullable=False),
        sa.Column("max_results", sa.Integer(), nullable=False),
        sa.Column("total_found", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "analysis",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("search_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("research_background", sa.Text(), nullable=False),
        sa.Column("current_hotspots", sa.Text(), nullable=False),
        sa.Column("main_findings", sa.Text(), nullable=False),
        sa.Column("experimental_methods", sa.Text(), nullable=False),
        sa.Column("future_directions", sa.Text(), nullable=False),
        sa.Column("model_used", sa.Text(), nullable=False),
        sa.Column("token_usage", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["search_id"], ["searches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("search_id"),
    )
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("search_id", sa.Integer(), nullable=False),
        sa.Column("pmid", sa.String(length=20), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=False),
        sa.Column("authors", sa.Text(), nullable=False),
        sa.Column("journal", sa.String(length=500), nullable=False),
        sa.Column("publish_date", sa.String(length=50), nullable=False),
        sa.Column("publication_type", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["search_id"], ["searches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_articles_pmid", "articles", ["pmid"], unique=False)
    op.create_index("ix_articles_search_id", "articles", ["search_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_articles_search_id", table_name="articles")
    op.drop_index("ix_articles_pmid", table_name="articles")
    op.drop_table("articles")
    op.drop_table("analysis")
    op.drop_table("searches")
