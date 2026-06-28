from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.domain.entities.job import Job
from src.domain.entities.match import Match
from src.domain.ports.match_repository import MatchRepository
from src.infrastructure.persistence import mappers
from src.infrastructure.persistence.orm_models import JobModel, MatchModel


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
        self, profile_id: str, limit: int = 20
    ) -> list[tuple[Match, Job]]:
        stmt = (
            select(MatchModel, JobModel)
            .join(JobModel, MatchModel.job_id == JobModel.id)
            .where(MatchModel.profile_id == profile_id)
            .order_by(MatchModel.llm_score.desc())
            .limit(limit)
        )
        rows = self._session.execute(stmt).all()
        return [
            (mappers.match_model_to_domain(m), mappers.job_model_to_domain(j))
            for m, j in rows
        ]
