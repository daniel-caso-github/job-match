"""backfill default password (123456) for existing profiles

Revision ID: c1a2b3d4e5f6
Revises: b8d24a7c9e15
Create Date: 2026-07-05 12:00:00.000000

"""
from typing import Sequence, Union

import bcrypt
import sqlalchemy as sa
from alembic import op

revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, None] = "b8d24a7c9e15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    default_hash = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode()
    op.execute(
        sa.text("UPDATE profiles SET password_hash = :h WHERE password_hash IS NULL").bindparams(
            h=default_hash
        )
    )


def downgrade() -> None:
    pass
