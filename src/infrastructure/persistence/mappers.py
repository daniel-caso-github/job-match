"""Mapping puro entre entidades de dominio (Pydantic) y modelos ORM (SQLAlchemy).

Reglas:
- Funciones puras; sin Session, sin commits.
- ORM → domain: construir y devolver `Job`/`Profile`/`Match` con sus campos.
- domain → ORM: devolver un dict listo para `pg_insert(...).values(**payload)`
  (en vez de instanciar `JobModel(...)` directamente, así trabajamos bien con
  `on_conflict_do_update`).
"""
from __future__ import annotations

from typing import Any

from src.domain.entities.job import Job
from src.domain.entities.match import Match
from src.domain.entities.profile import Profile
from src.domain.entities.raw_job import RawJob
from src.domain.value_objects.job_requirements import JobRequirements
from src.infrastructure.persistence.orm_models import JobModel, MatchModel, ProfileModel


def raw_job_to_orm_payload(raw_job: RawJob) -> dict[str, Any]:
    payload = raw_job.model_dump(mode="json")
    payload["url"] = str(payload["url"])
    return payload


def job_model_to_domain(m: JobModel) -> Job:
    return Job(
        id=m.id,
        source=m.source,
        url=m.url,
        title=m.title,
        company=m.company,
        raw_text=m.raw_text,
        posted_at=m.posted_at,
        country=m.country,
        remote=m.remote,
        requirements=(
            JobRequirements.model_validate(m.requirements) if m.requirements else None
        ),
        embedding=list(m.embedding) if m.embedding is not None else None,
        fetched_at=m.fetched_at,
    )


def profile_model_to_domain(m: ProfileModel) -> Profile:
    return Profile(
        id=m.id,
        form_data=dict(m.form_data),
        embedding=list(m.embedding) if m.embedding is not None else None,
        updated_at=m.updated_at,
    )


def match_model_to_domain(m: MatchModel) -> Match:
    return Match(
        profile_id=m.profile_id,
        job_id=m.job_id,
        semantic_score=m.semantic_score,
        llm_score=m.llm_score,
        verdict=dict(m.verdict) if m.verdict else None,
        scored_at=m.scored_at,
    )
