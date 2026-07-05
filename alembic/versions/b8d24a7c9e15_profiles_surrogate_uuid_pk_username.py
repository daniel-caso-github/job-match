"""profiles: surrogate uuid pk + username + password_hash

Revision ID: b8d24a7c9e15
Revises: f3c8a51e0b74
Create Date: 2026-07-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b8d24a7c9e15'
down_revision: Union[str, Sequence[str], None] = 'f3c8a51e0b74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHILD_TABLES = ("matches", "profile_skills", "saved_searches")


def upgrade() -> None:
    """Upgrade schema."""
    # gen_random_uuid() es builtin en PG13+; defensivo para imágenes viejas.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.add_column(
        "profiles",
        sa.Column(
            "new_id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )
    # Unique temporal para poder colgar las FKs antes de que sea PK.
    op.create_unique_constraint("profiles_new_id_key", "profiles", ["new_id"])

    for table in CHILD_TABLES:
        op.add_column(
            table,
            sa.Column("new_profile_id", postgresql.UUID(as_uuid=False), nullable=True),
        )

    profiles_t = sa.table(
        "profiles",
        sa.column("id", sa.String),
        sa.column("new_id", postgresql.UUID(as_uuid=False)),
    )
    conn = op.get_bind()
    for table in CHILD_TABLES:
        child_t = sa.table(
            table,
            sa.column("profile_id", sa.String),
            sa.column("new_profile_id", postgresql.UUID(as_uuid=False)),
        )
        conn.execute(
            child_t.update().values(
                new_profile_id=sa.select(profiles_t.c.new_id)
                .where(profiles_t.c.id == child_t.c.profile_id)
                .scalar_subquery()
            )
        )
        op.alter_column(table, "new_profile_id", nullable=False)

    op.drop_index("matches_llm_score", table_name="matches")
    op.drop_constraint("matches_pkey", "matches", type_="primary")
    op.drop_constraint("matches_profile_id_fkey", "matches", type_="foreignkey")
    op.drop_column("matches", "profile_id")

    op.drop_constraint("profile_skills_pkey", "profile_skills", type_="primary")
    op.drop_constraint("profile_skills_profile_id_fkey", "profile_skills", type_="foreignkey")
    op.drop_column("profile_skills", "profile_id")

    op.drop_index("saved_searches_profile_created", table_name="saved_searches")
    op.drop_constraint("saved_searches_profile_id_fkey", "saved_searches", type_="foreignkey")
    op.drop_column("saved_searches", "profile_id")

    for table in CHILD_TABLES:
        op.alter_column(table, "new_profile_id", new_column_name="profile_id")

    op.drop_constraint("profiles_pkey", "profiles", type_="primary")
    op.alter_column("profiles", "id", new_column_name="username")
    op.alter_column(
        "profiles", "username", type_=sa.String(64), existing_type=sa.String(), existing_nullable=False
    )
    op.alter_column("profiles", "new_id", new_column_name="id")
    op.create_primary_key("profiles_pkey", "profiles", ["id"])
    op.create_unique_constraint("profiles_username_key", "profiles", ["username"])
    op.add_column("profiles", sa.Column("password_hash", sa.String(), nullable=True))
    op.drop_constraint("profiles_new_id_key", "profiles", type_="unique")

    op.create_primary_key("matches_pkey", "matches", ["profile_id", "job_id"])
    op.create_foreign_key(
        "matches_profile_id_fkey", "matches", "profiles",
        ["profile_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("matches_llm_score", "matches", ["profile_id", "llm_score"])

    op.create_primary_key("profile_skills_pkey", "profile_skills", ["profile_id", "skill_id"])
    op.create_foreign_key(
        "profile_skills_profile_id_fkey", "profile_skills", "profiles",
        ["profile_id"], ["id"], ondelete="CASCADE",
    )

    op.create_foreign_key(
        "saved_searches_profile_id_fkey", "saved_searches", "profiles",
        ["profile_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index(
        "saved_searches_profile_created", "saved_searches", ["profile_id", "created_at"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    for table in CHILD_TABLES:
        op.add_column(table, sa.Column("old_profile_id", sa.String(), nullable=True))

    profiles_t = sa.table(
        "profiles",
        sa.column("id", postgresql.UUID(as_uuid=False)),
        sa.column("username", sa.String),
    )
    conn = op.get_bind()
    for table in CHILD_TABLES:
        child_t = sa.table(
            table,
            sa.column("profile_id", postgresql.UUID(as_uuid=False)),
            sa.column("old_profile_id", sa.String),
        )
        conn.execute(
            child_t.update().values(
                old_profile_id=sa.select(profiles_t.c.username)
                .where(profiles_t.c.id == child_t.c.profile_id)
                .scalar_subquery()
            )
        )
        op.alter_column(table, "old_profile_id", nullable=False)

    op.drop_index("matches_llm_score", table_name="matches")
    op.drop_constraint("matches_pkey", "matches", type_="primary")
    op.drop_constraint("matches_profile_id_fkey", "matches", type_="foreignkey")
    op.drop_column("matches", "profile_id")

    op.drop_constraint("profile_skills_pkey", "profile_skills", type_="primary")
    op.drop_constraint("profile_skills_profile_id_fkey", "profile_skills", type_="foreignkey")
    op.drop_column("profile_skills", "profile_id")

    op.drop_index("saved_searches_profile_created", table_name="saved_searches")
    op.drop_constraint("saved_searches_profile_id_fkey", "saved_searches", type_="foreignkey")
    op.drop_column("saved_searches", "profile_id")

    for table in CHILD_TABLES:
        op.alter_column(table, "old_profile_id", new_column_name="profile_id")

    op.drop_column("profiles", "password_hash")
    op.drop_constraint("profiles_username_key", "profiles", type_="unique")
    op.drop_constraint("profiles_pkey", "profiles", type_="primary")
    op.drop_column("profiles", "id")
    op.alter_column("profiles", "username", new_column_name="id")
    op.alter_column(
        "profiles", "id", type_=sa.String(), existing_type=sa.String(64), existing_nullable=False
    )
    op.create_primary_key("profiles_pkey", "profiles", ["id"])

    op.create_primary_key("matches_pkey", "matches", ["profile_id", "job_id"])
    op.create_foreign_key(
        "matches_profile_id_fkey", "matches", "profiles",
        ["profile_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("matches_llm_score", "matches", ["profile_id", "llm_score"])

    op.create_primary_key("profile_skills_pkey", "profile_skills", ["profile_id", "skill_id"])
    op.create_foreign_key(
        "profile_skills_profile_id_fkey", "profile_skills", "profiles",
        ["profile_id"], ["id"], ondelete="CASCADE",
    )

    op.create_foreign_key(
        "saved_searches_profile_id_fkey", "saved_searches", "profiles",
        ["profile_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index(
        "saved_searches_profile_created", "saved_searches", ["profile_id", "created_at"]
    )
