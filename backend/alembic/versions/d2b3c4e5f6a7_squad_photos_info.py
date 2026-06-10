"""fotos e info de jugadores/entrenadores (enriquecimiento de plantillas)

Revision ID: d2b3c4e5f6a7
Revises: c1a2b3d4e5f6
Create Date: 2026-06-10 04:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d2b3c4e5f6a7"
down_revision: str | None = "c1a2b3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("players", sa.Column("photo_url", sa.String(length=500), nullable=True))
    op.add_column("players", sa.Column("info", sa.Text(), nullable=True))
    op.add_column("coaches", sa.Column("photo_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("coaches", "photo_url")
    op.drop_column("players", "info")
    op.drop_column("players", "photo_url")
