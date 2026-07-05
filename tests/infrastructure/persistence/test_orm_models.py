"""Smoke tests for the SQLAlchemy declarative metadata.

We do NOT spin Postgres here — that's covered end-to-end by `alembic upgrade
head`. These tests just assert the metadata exposes what we expect, so a
silent rename of a column or removal of an index breaks loudly.
"""
from src.infrastructure.persistence.orm_models import (
    EMBEDDING_DIM,
    Base,
    JobModel,
    MatchModel,
    ProfileModel,
    ProfileSkillModel,
)


def test_metadata_lists_expected_tables():
    assert set(Base.metadata.tables.keys()) == {
        "jobs",
        "profiles",
        "matches",
        "saved_searches",
        "skills",
        "profile_skills",
    }


def test_profile_columns_present():
    cols = {c.name for c in ProfileModel.__table__.columns}
    expected = {
        "id",
        "username",
        "password_hash",
        "seniority",
        "english_level",
        "location",
        "willing_to_relocate",
        "modality",
        "salary_min",
        "salary_max",
        "salary_currency",
        "summary",
        "embedding",
        "updated_at",
    }
    assert expected.issubset(cols)
    assert "form_data" not in cols


def test_profile_pk_is_server_generated_uuid():
    id_col = ProfileModel.__table__.c.id
    assert id_col.primary_key
    assert id_col.server_default is not None
    assert ProfileModel.__table__.c.username.unique
    for model in (MatchModel, ProfileSkillModel):
        assert str(model.__table__.c.profile_id.type).upper() == "UUID"


def test_profile_skills_composite_pk_and_cascade_fks():
    pk_cols = {c.name for c in ProfileSkillModel.__table__.primary_key.columns}
    assert pk_cols == {"profile_id", "skill_id"}

    fks_by_col = {fk.parent.name: fk for fk in ProfileSkillModel.__table__.foreign_keys}
    assert fks_by_col["profile_id"].ondelete == "CASCADE"
    assert fks_by_col["skill_id"].ondelete == "CASCADE"


def test_job_columns_present():
    cols = {c.name for c in JobModel.__table__.columns}
    expected = {
        "id",
        "source",
        "url",
        "title",
        "company",
        "raw_text",
        "requirements",
        "embedding",
        "posted_at",
        "country",
        "remote",
        "fetched_at",
    }
    assert expected.issubset(cols)


def test_embedding_dimension_matches_bge_small():
    assert EMBEDDING_DIM == 384
    assert JobModel.__table__.c.embedding.type.dim == 384


def test_match_has_composite_pk_and_cascade_fks():
    pk_cols = {c.name for c in MatchModel.__table__.primary_key.columns}
    assert pk_cols == {"profile_id", "job_id"}

    fks_by_col = {fk.parent.name: fk for fk in MatchModel.__table__.foreign_keys}
    assert fks_by_col["profile_id"].ondelete == "CASCADE"
    assert fks_by_col["job_id"].ondelete == "CASCADE"


def test_hnsw_index_declared_on_jobs_embedding():
    idx = next(
        i for i in JobModel.__table__.indexes if i.name == "jobs_embedding_hnsw"
    )
    assert idx.kwargs.get("postgresql_using") == "hnsw"
    assert idx.kwargs.get("postgresql_ops") == {"embedding": "vector_cosine_ops"}
