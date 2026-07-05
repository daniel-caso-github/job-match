"""add account fields (first_name, last_name, email)

Revision ID: a1b2c3d4e5f6
Revises: c1a2b3d4e5f6
Create Date: 2026-07-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "c1a2b3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("first_name", sa.String(80), nullable=True))
    op.add_column("profiles", sa.Column("last_name", sa.String(80), nullable=True))
    op.add_column("profiles", sa.Column("email", sa.String(254), nullable=True))
    op.create_unique_constraint("uq_profiles_email", "profiles", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_profiles_email", "profiles", type_="unique")
    op.drop_column("profiles", "email")
    op.drop_column("profiles", "last_name")
    op.drop_column("profiles", "first_name")
