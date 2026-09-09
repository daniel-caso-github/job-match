"""add postulation_package to matches

Revision ID: f2f44c6dfa14
Revises: g1h2i3j4k5l6
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f2f44c6dfa14'
down_revision = 'g1h2i3j4k5l6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'matches',
        sa.Column('postulation_package', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('matches', 'postulation_package')
