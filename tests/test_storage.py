"""Storage layer smoke tests.

These tests verify that the SQLAlchemy 2.0 declarative models import cleanly,
that Base.metadata exposes the expected tables, and that the schema definitions
are coherent (PKs, FKs, indexes). We do NOT spin up Postgres+pgvector here
(that's an integration concern verified end-to-end via `alembic upgrade head`
in CI / dev). Offline-first.
"""
from __future__ import annotations

from src.storage.models import EMBEDDING_DIM, Base, Job, Match, Profile


def test_metadata_lists_expected_tables():
    assert set(Base.metadata.tables.keys()) == {"jobs", "profiles", "matches"}


def test_job_columns_present():
    cols = {c.name for c in Job.__table__.columns}
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
    # bge-small-en-v1.5 produces 384-d vectors.
    assert EMBEDDING_DIM == 384
    assert Job.__table__.c.embedding.type.dim == 384
    assert Profile.__table__.c.embedding.type.dim == 384


def test_match_has_composite_pk_and_cascade_fks():
    pk_cols = {c.name for c in Match.__table__.primary_key.columns}
    assert pk_cols == {"profile_id", "job_id"}

    fks_by_col = {fk.parent.name: fk for fk in Match.__table__.foreign_keys}
    assert fks_by_col["profile_id"].ondelete == "CASCADE"
    assert fks_by_col["job_id"].ondelete == "CASCADE"


def test_hnsw_index_declared_on_jobs_embedding():
    idx = next(i for i in Job.__table__.indexes if i.name == "jobs_embedding_hnsw")
    assert idx.kwargs.get("postgresql_using") == "hnsw"
    assert idx.kwargs.get("postgresql_ops") == {"embedding": "vector_cosine_ops"}
