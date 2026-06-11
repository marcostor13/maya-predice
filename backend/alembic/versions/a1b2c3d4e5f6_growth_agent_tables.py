"""growth_runs / growth_insights (agente de crecimiento)

Revision ID: a1b2c3d4e5f6
Revises: f5a6b7c8d9e0
Create Date: 2026-06-11 06:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "growth_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="running", nullable=False),
        sa.Column("model", sa.String(length=60), nullable=True),
        sa.Column("trigger", sa.String(length=20), server_default="growth", nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("insights_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_growth_runs_status", "growth_runs", ["status"])

    op.create_table(
        "growth_insights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="3", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="new", nullable=False),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("action_type", sa.String(length=30), server_default="email_only", nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["growth_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_growth_insights_run_id", "growth_insights", ["run_id"])
    op.create_index("ix_growth_insights_category", "growth_insights", ["category"])
    op.create_index("ix_growth_insights_status", "growth_insights", ["status"])


def downgrade() -> None:
    op.drop_index("ix_growth_insights_status", table_name="growth_insights")
    op.drop_index("ix_growth_insights_category", table_name="growth_insights")
    op.drop_index("ix_growth_insights_run_id", table_name="growth_insights")
    op.drop_table("growth_insights")
    op.drop_index("ix_growth_runs_status", table_name="growth_runs")
    op.drop_table("growth_runs")
