from __future__ import annotations

import logging

from src.domain.ports.job_repository import JobRepository
from src.domain.ports.requirements_extractor import RequirementsExtractor

logger = logging.getLogger(__name__)


class ExtractJobRequirementsUseCase:
    """Itera las ofertas sin `requirements` y las completa via el extractor.

    Idempotente: solo procesa las que aún no tienen requirements (el filtro
    está en `JobRepository.list_without_requirements`).
    """

    def __init__(
        self,
        extractor: RequirementsExtractor,
        job_repository: JobRepository,
    ):
        self._extractor = extractor
        self._job_repository = job_repository

    def execute(self, limit: int = 100) -> int:
        pending = self._job_repository.list_without_requirements(limit=limit)
        for job in pending:
            requirements = self._extractor.extract(job.raw_text)
            self._job_repository.update_requirements(job.id, requirements)
        logger.info("Extracted requirements for %d jobs", len(pending))
        return len(pending)
