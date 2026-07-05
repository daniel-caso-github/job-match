"""normalize profiles schema: columns + skills/profile_skills

Revision ID: f3c8a51e0b74
Revises: d46cfbb8bf63
Create Date: 2026-07-05 00:00:00.000000

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f3c8a51e0b74'
down_revision: Union[str, Sequence[str], None] = 'd46cfbb8bf63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


profiles_t = sa.table(
    "profiles",
    sa.column("id", sa.String),
    sa.column("form_data", postgresql.JSONB),
    sa.column("seniority", sa.String),
    sa.column("english_level", sa.String),
    sa.column("location", sa.String),
    sa.column("willing_to_relocate", sa.Boolean),
    sa.column("modality", sa.String),
    sa.column("salary_min", sa.Integer),
    sa.column("salary_max", sa.Integer),
    sa.column("salary_currency", sa.String),
    sa.column("summary", sa.Text),
)

skills_t = sa.table(
    "skills",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
)

profile_skills_t = sa.table(
    "profile_skills",
    sa.column("profile_id", sa.String),
    sa.column("skill_id", sa.Integer),
    sa.column("years", sa.Float),
)


def _parse_salary(text: str | None) -> tuple[int | None, int | None, str | None]:
    """Parsea el texto libre legacy ('USD 50000-90000', '$80k-$110k USD')."""
    if not text:
        return None, None, None
    nums = [
        int(float(value) * (1000 if suffix else 1))
        for value, suffix in re.findall(r"(\d+(?:\.\d+)?)\s*([kK]?)", text)
    ]
    if not nums:
        return None, None, None
    salary_min = nums[0]
    salary_max = nums[1] if len(nums) > 1 else None
    return salary_min, salary_max, "USD"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'skills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'profile_skills',
        sa.Column('profile_id', sa.String(), nullable=False),
        sa.Column('skill_id', sa.Integer(), nullable=False),
        sa.Column('years', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('profile_id', 'skill_id'),
    )
    op.add_column('profiles', sa.Column('seniority', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('english_level', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('location', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('willing_to_relocate', sa.Boolean(), nullable=True))
    op.add_column('profiles', sa.Column('modality', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('salary_min', sa.Integer(), nullable=True))
    op.add_column('profiles', sa.Column('salary_max', sa.Integer(), nullable=True))
    op.add_column('profiles', sa.Column('salary_currency', sa.String(length=3), nullable=True))
    op.add_column('profiles', sa.Column('summary', sa.Text(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.select(profiles_t.c.id, profiles_t.c.form_data)).all()

    skill_names = sorted({
        (item.get("name") or "").strip().lower()
        for _, form_data in rows
        for item in (form_data.get("stack") or [])
        if (item.get("name") or "").strip()
    })
    skill_ids: dict[str, int] = {}
    if skill_names:
        conn.execute(skills_t.insert(), [{"name": n} for n in skill_names])
        skill_ids = dict(conn.execute(sa.select(skills_t.c.name, skills_t.c.id)).all())

    for profile_id, form_data in rows:
        salary_min, salary_max, currency = _parse_salary(form_data.get("salary_expectation"))
        conn.execute(
            profiles_t.update()
            .where(profiles_t.c.id == profile_id)
            .values(
                seniority=form_data.get("seniority"),
                english_level=form_data.get("english_level"),
                location=form_data.get("location"),
                willing_to_relocate=bool(form_data.get("willing_to_relocate", False)),
                modality=form_data.get("modality") or "remote",
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=currency,
                summary=form_data.get("summary"),
            )
        )
        seen: set[str] = set()
        skill_rows = []
        for item in form_data.get("stack") or []:
            name = (item.get("name") or "").strip().lower()
            if name and name not in seen:
                seen.add(name)
                skill_rows.append({
                    "profile_id": profile_id,
                    "skill_id": skill_ids[name],
                    "years": float(item.get("years") or 0),
                })
        if skill_rows:
            conn.execute(profile_skills_t.insert(), skill_rows)

    op.alter_column('profiles', 'seniority', nullable=False)
    op.alter_column('profiles', 'english_level', nullable=False)
    op.alter_column('profiles', 'location', nullable=False)
    op.alter_column('profiles', 'willing_to_relocate', nullable=False)
    op.alter_column('profiles', 'modality', nullable=False)
    op.drop_column('profiles', 'form_data')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('profiles', sa.Column('form_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(
        sa.select(
            profiles_t.c.id,
            profiles_t.c.seniority,
            profiles_t.c.english_level,
            profiles_t.c.location,
            profiles_t.c.willing_to_relocate,
            profiles_t.c.modality,
            profiles_t.c.salary_min,
            profiles_t.c.salary_max,
            profiles_t.c.salary_currency,
            profiles_t.c.summary,
        )
    ).all()
    stacks: dict[str, list[dict]] = {}
    for profile_id, name, years in conn.execute(
        sa.select(profile_skills_t.c.profile_id, skills_t.c.name, profile_skills_t.c.years)
        .select_from(profile_skills_t.join(skills_t, profile_skills_t.c.skill_id == skills_t.c.id))
    ):
        stacks.setdefault(profile_id, []).append({"name": name, "years": years})

    for row in rows:
        salary = None
        if row.salary_min is not None and row.salary_max is not None:
            salary = f"{row.salary_currency or 'USD'} {row.salary_min}-{row.salary_max}"
        elif row.salary_min is not None:
            salary = f"{row.salary_currency or 'USD'} {row.salary_min}+"
        conn.execute(
            profiles_t.update()
            .where(profiles_t.c.id == row.id)
            .values(form_data={
                "id": row.id,
                "stack": stacks.get(row.id, []),
                "seniority": row.seniority,
                "english_level": row.english_level,
                "location": row.location,
                "willing_to_relocate": row.willing_to_relocate,
                "modality": row.modality,
                "salary_expectation": salary,
                "summary": row.summary,
            })
        )

    op.alter_column('profiles', 'form_data', nullable=False)
    op.drop_column('profiles', 'summary')
    op.drop_column('profiles', 'salary_currency')
    op.drop_column('profiles', 'salary_max')
    op.drop_column('profiles', 'salary_min')
    op.drop_column('profiles', 'modality')
    op.drop_column('profiles', 'willing_to_relocate')
    op.drop_column('profiles', 'location')
    op.drop_column('profiles', 'english_level')
    op.drop_column('profiles', 'seniority')
    op.drop_table('profile_skills')
    op.drop_table('skills')
