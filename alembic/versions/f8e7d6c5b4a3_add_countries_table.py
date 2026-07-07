"""add countries table and normalize jobs.country

Revision ID: f8e7d6c5b4a3
Revises: e5f6a7b8c9d0
Create Date: 2026-07-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "f8e7d6c5b4a3"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
    )
    op.create_index("uq_countries_name", "countries", ["name"], unique=True)

    op.add_column("jobs", sa.Column("country_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "jobs_country_id_fkey",
        "jobs",
        "countries",
        ["country_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute("""
        INSERT INTO countries (name)
        SELECT DISTINCT country FROM jobs WHERE country IS NOT NULL
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        UPDATE jobs j
        SET country_id = c.id
        FROM countries c
        WHERE j.country = c.name
    """)

    op.drop_column("jobs", "country")


def downgrade() -> None:
    op.add_column("jobs", sa.Column("country", sa.String(), nullable=True))

    op.execute("""
        UPDATE jobs j
        SET country = c.name
        FROM countries c
        WHERE j.country_id = c.id
    """)

    op.drop_constraint("jobs_country_id_fkey", "jobs", type_="foreignkey")
    op.drop_column("jobs", "country_id")

    op.drop_index("uq_countries_name", table_name="countries")
    op.drop_table("countries")
