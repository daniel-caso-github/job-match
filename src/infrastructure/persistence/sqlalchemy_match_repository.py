from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.domain.entities.job import Job
from src.domain.entities.match import Match
from src.domain.ports.match_repository import MatchRepository
from src.domain.value_objects.match_filters import MatchFilters
from src.infrastructure.persistence import mappers
from src.infrastructure.persistence.orm_models import CountryModel, JobModel, MatchModel


class SqlAlchemyMatchRepository(MatchRepository):
    def __init__(self, session: Session):
        self._session = session

    def upsert(
        self,
        *,
        profile_id: str,
        job_id: str,
        semantic_score: float,
        llm_score: int,
        verdict: dict[str, Any],
    ) -> None:
        stmt = pg_insert(MatchModel).values(
            profile_id=profile_id,
            job_id=job_id,
            semantic_score=semantic_score,
            llm_score=llm_score,
            verdict=verdict,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["profile_id", "job_id"],
            set_={
                "semantic_score": stmt.excluded.semantic_score,
                "llm_score": stmt.excluded.llm_score,
                "verdict": stmt.excluded.verdict,
                "scored_at": func.now(),
            },
        )
        self._session.execute(stmt)

    def top_for_profile(
        self, profile_id: str, limit: int = 20, filters: MatchFilters | None = None
    ) -> list[tuple[Match, Job]]:
        stmt = (
            select(MatchModel, JobModel)
            .join(JobModel, MatchModel.job_id == JobModel.id)
            .where(MatchModel.profile_id == profile_id)
        )
        if filters is not None:
            stmt = self._apply_filters(stmt, filters)
        stmt = stmt.order_by(MatchModel.llm_score.desc()).limit(limit)
        rows = self._session.execute(stmt).all()
        return [
            (mappers.match_model_to_domain(m), mappers.job_model_to_domain(j))
            for m, j in rows
        ]

    @staticmethod
    def _apply_filters(stmt, filters: MatchFilters):
        req = JobModel.requirements
        if filters.min_score is not None:
            stmt = stmt.where(MatchModel.llm_score >= filters.min_score)
        if filters.sources:
            stmt = stmt.where(JobModel.source.in_(filters.sources))
        if filters.stack:
            stmt = stmt.where(req["stack"].has_any(array(filters.stack)))
        if filters.seniorities:
            stmt = stmt.where(
                req["seniority"].astext.in_([s.value for s in filters.seniorities])
            )
        if filters.english_levels:
            english = req["english_level"].astext
            stmt = stmt.where(
                or_(
                    english.is_(None),
                    english.in_([e.value for e in filters.english_levels]),
                )
            )
        if filters.remote_only:
            stmt = stmt.where(
                func.coalesce(req["remote"].as_boolean(), True).is_(True)
            )
        if filters.latam_only:
            stmt = stmt.where(req["latam_friendly"].as_boolean().is_(True))
        if filters.exclude_eu:
            stmt = stmt.where(
                func.coalesce(
                    req["requires_eu_residency"].as_boolean(), False
                ).is_(False)
            )
        if filters.with_salary:
            stmt = stmt.where(req["salary_range"].astext.is_not(None))
        if filters.countries:
            stmt = stmt.where(
                JobModel.country_rel.has(CountryModel.name.in_(filters.countries))
            )
        return stmt

    def get_for_pair(
        self, profile_id: str, job_id: str
    ) -> tuple[Match, Job] | None:
        stmt = (
            select(MatchModel, JobModel)
            .join(JobModel, MatchModel.job_id == JobModel.id)
            .where(MatchModel.profile_id == profile_id, MatchModel.job_id == job_id)
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        m, j = row
        return mappers.match_model_to_domain(m), mappers.job_model_to_domain(j)

    def count_for_profile(
        self, profile_id: str, filters: MatchFilters | None = None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(MatchModel)
            .join(JobModel, MatchModel.job_id == JobModel.id)
            .where(MatchModel.profile_id == profile_id)
        )
        if filters is not None:
            stmt = self._apply_filters(stmt, filters)
        return self._session.scalar(stmt) or 0
