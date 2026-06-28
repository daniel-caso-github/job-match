from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.job import Job
from src.domain.entities.raw_job import RawJob
from src.domain.value_objects.job_requirements import JobRequirements


class JobRepository(ABC):
    """Port de persistencia para ofertas. Implementación en
    `src/infrastructure/persistence/sqlalchemy_job_repository.py`.

    Convención: los métodos NO commitean. La transacción la maneja el caller
    (use case dentro de `session_scope()`).
    """

    @abstractmethod
    def upsert(self, job: RawJob) -> None: ...

    @abstractmethod
    def get(self, job_id: str) -> Job | None: ...

    @abstractmethod
    def list_without_requirements(self, limit: int = 100) -> list[Job]: ...

    @abstractmethod
    def list_without_embedding(self, limit: int = 100) -> list[Job]: ...

    @abstractmethod
    def update_requirements(self, job_id: str, req: JobRequirements) -> None: ...

    @abstractmethod
    def update_embedding(self, job_id: str, vec: list[float]) -> None: ...
