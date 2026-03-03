"""Initial tables: guides and evaluation_runs

Revision ID: 001
Revises:
Create Date: 2026-03-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guides",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("product", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("experience_level", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("sections", JSON(), nullable=True),
        sa.Column("evaluation", JSON(), nullable=True),
        sa.Column("generation_metadata", JSON(), nullable=True),
        sa.Column("focus_areas", JSON(), nullable=True),
        sa.Column("tech_stack", JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_guides_product_role", "guides", ["product", "role"])

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("guide_id", sa.String(), nullable=False, index=True),
        sa.Column("run_type", sa.String(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("dimension_scores", JSON(), nullable=True),
        sa.Column("section_scores", JSON(), nullable=True),
        sa.Column("ragas_metrics", JSON(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_seconds", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("evaluation_runs")
    op.drop_index("ix_guides_product_role", table_name="guides")
    op.drop_table("guides")
