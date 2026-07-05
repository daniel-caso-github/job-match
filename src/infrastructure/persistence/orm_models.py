from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

EMBEDDING_DIM = 384


class Base(DeclarativeBase):
    pass


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    posted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    country: Mapped[str | None] = mapped_column(String)
    remote: Mapped[bool | None] = mapped_column(Boolean)
    fetched_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    matches: Mapped[list[MatchModel]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "jobs_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("jobs_fetched_at", "fetched_at"),
    )


class ProfileModel(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String)
    first_name: Mapped[str | None] = mapped_column(String(80))
    last_name: Mapped[str | None] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    seniority: Mapped[str] = mapped_column(String, nullable=False)
    english_level: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    modality: Mapped[str] = mapped_column(String, nullable=False, default="remote")
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    summary: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    skills: Mapped[list[ProfileSkillModel]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    matches: Mapped[list[MatchModel]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class SkillModel(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)


class ProfileSkillModel(Base):
    __tablename__ = "profile_skills"

    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    years: Mapped[float] = mapped_column(Float, nullable=False)

    profile: Mapped[ProfileModel] = relationship(back_populates="skills")
    skill: Mapped[SkillModel] = relationship()


class SavedSearchModel(Base):
    __tablename__ = "saved_searches"

    dag_run_id: Mapped[str] = mapped_column(String, primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    run_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    match_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("saved_searches_profile_created", "profile_id", "created_at"),
    )


class MatchModel(Base):
    __tablename__ = "matches"

    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    semantic_score: Mapped[float | None] = mapped_column(Float)
    llm_score: Mapped[int | None] = mapped_column(Integer)
    verdict: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    scored_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    profile: Mapped[ProfileModel] = relationship(back_populates="matches")
    job: Mapped[JobModel] = relationship(back_populates="matches")

    __table_args__ = (Index("matches_llm_score", "profile_id", "llm_score"),)
