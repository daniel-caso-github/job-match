from __future__ import annotations

from sqlalchemy import func, select, true
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.domain.entities.job import Job
from src.domain.entities.raw_job import RawJob
from src.domain.ports.job_repository import JobRepository
from src.domain.value_objects.job_requirements import JobRequirements
from src.infrastructure.persistence import mappers
from src.infrastructure.persistence.orm_models import JobModel, MatchModel


class SqlAlchemyJobRepository(JobRepository):
    """Implementación SQLAlchemy del `JobRepository` port.

    No commitea: la transacción la maneja el caller (use case dentro de
    `session_scope()`).
    """

    def __init__(self, session: Session):
        self._session = session

    def upsert(self, job: RawJob) -> None:
        payload = mappers.raw_job_to_orm_payload(job)
        stmt = pg_insert(JobModel).values(**payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "title": stmt.excluded.title,
                "company": stmt.excluded.company,
                "raw_text": stmt.excluded.raw_text,
                "url": stmt.excluded.url,
            },
        )
        self._session.execute(stmt)

    def get(self, job_id: str) -> Job | None:
        model = self._session.get(JobModel, job_id)
        return mappers.job_model_to_domain(model) if model else None

    def list_without_requirements(self, limit: int = 100) -> list[Job]:
        stmt = (
            select(JobModel)
            .where(JobModel.requirements.is_(None))
            .order_by(JobModel.fetched_at.desc())
            .limit(limit)
        )
        return [mappers.job_model_to_domain(m) for m in self._session.scalars(stmt)]

    def list_without_embedding(self, limit: int = 100) -> list[Job]:
        stmt = (
            select(JobModel)
            .where(JobModel.embedding.is_(None))
            .order_by(JobModel.fetched_at.desc())
            .limit(limit)
        )
        return [mappers.job_model_to_domain(m) for m in self._session.scalars(stmt)]

    def update_requirements(self, job_id: str, req: JobRequirements) -> None:
        model = self._session.get(JobModel, job_id)
        if model is None:
            raise LookupError(f"Job {job_id} not found")
        model.requirements = req.model_dump(mode="json")

    def update_embedding(self, job_id: str, vec: list[float]) -> None:
        model = self._session.get(JobModel, job_id)
        if model is None:
            raise LookupError(f"Job {job_id} not found")
        model.embedding = vec

    def list_stack_technologies(self, limit: int = 30) -> list[str]:
        tech = (
            func.jsonb_array_elements_text(JobModel.requirements["stack"])
            .table_valued("value")
            .lateral()
        )
        stmt = (
            select(tech.c.value)
            .select_from(JobModel)
            .join(tech, true())
            .group_by(tech.c.value)
            .order_by(func.count().desc(), tech.c.value)
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars())

    def semantic_top_k(
        self,
        embedding: list[float],
        *,
        k: int,
        threshold: float,
        exclude_scored_for: str | None = None,
    ) -> list[tuple[str, float]]:
        distance = JobModel.embedding.cosine_distance(embedding)
        stmt = (
            select(JobModel.id, (1 - distance).label("semantic_score"))
            .where(JobModel.embedding.is_not(None))
            .where(JobModel.requirements.is_not(None))
            .order_by(distance)
            .limit(k)
        )
        if exclude_scored_for is not None:
            already_scored = select(MatchModel.job_id).where(
                MatchModel.profile_id == exclude_scored_for
            )
            stmt = stmt.where(JobModel.id.not_in(already_scored))

        rows = self._session.execute(stmt).all()
        return [
            (row.id, float(row.semantic_score))
            for row in rows
            if row.semantic_score is not None and row.semantic_score >= threshold
        ]
