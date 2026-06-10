"""ensamble con el mercado en predictions (terna modelo+mercado+peso)

Revision ID: e3c4d5f6a7b8
Revises: d2b3c4e5f6a7
Create Date: 2026-06-10 05:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e3c4d5f6a7b8"
down_revision: str | None = "d2b3c4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("predictions", sa.Column("ensemble", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("predictions", "ensemble")
