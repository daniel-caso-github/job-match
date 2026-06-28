from __future__ import annotations

import logging

from src.domain.ports.job_repository import JobRepository
from src.domain.ports.job_source import JobSource

logger = logging.getLogger(__name__)


class CollectJobsUseCase:
    """Recolecta ofertas de N fuentes y las upsertea via JobRepository.

    Depende solo de puertos (`JobSource`, `JobRepository`) — agnóstico de
    httpx/Postgres/feedparser/etc.
    """

    def __init__(self, sources: list[JobSource], job_repository: JobRepository):
        self._sources = sources
        self._job_repository = job_repository

    def execute(self) -> int:
        total = 0
        for source in self._sources:
            count_for_source = 0
            for raw_job in source.fetch():
                self._job_repository.upsert(raw_job)
                count_for_source += 1
            logger.info("Collected %d jobs from %s", count_for_source, source.name)
            total += count_for_source
        return total
