from __future__ import annotations

import logging

from src.domain.ports.embedder import Embedder
from src.domain.ports.job_repository import JobRepository
from src.domain.services.embedding_text import job_text_for_embedding

logger = logging.getLogger(__name__)


class EmbedJobsUseCase:
    """Itera las ofertas sin embedding y las vectoriza en batch.

    Idempotente: solo procesa las que aún no tienen embedding (filtro en
    `JobRepository.list_without_embedding`).
    """

    def __init__(self, embedder: Embedder, job_repository: JobRepository):
        self._embedder = embedder
        self._job_repository = job_repository

    def execute(self, limit: int = 100) -> int:
        pending = self._job_repository.list_without_embedding(limit=limit)
        if not pending:
            return 0

        texts = [job_text_for_embedding(job) for job in pending]
        vectors = self._embedder.embed(texts)

        for job, vec in zip(pending, vectors, strict=True):
            self._job_repository.update_embedding(job.id, vec)

        logger.info("Embedded %d jobs", len(pending))
        return len(pending)
