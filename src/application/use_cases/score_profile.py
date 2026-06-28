from __future__ import annotations

import logging

from src.domain.ports.embedder import Embedder
from src.domain.ports.job_repository import JobRepository
from src.domain.ports.llm_scorer import LlmScorer
from src.domain.ports.match_repository import MatchRepository
from src.domain.ports.profile_repository import ProfileRepository
from src.domain.services.embedding_text import profile_text_for_embedding
from src.domain.value_objects.profile_form import ProfileForm
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)


class ScoreProfileUseCase:
    """Orquesta el matching de un perfil contra el corpus de ofertas.

    Pasos por corrida (idempotentes):
      1. Upsertea el perfil + su embedding.
      2. Pide al `JobRepository` el top-K semántico (ya filtra threshold +
         excluye los ya scoreados para este perfil).
      3. Por cada candidato: pide al `LlmScorer` un `Verdict` y upsertea el Match.

    El segundo y siguientes runs sobre el mismo perfil + corpus no duplican
    matches (gracias a `exclude_scored_for` + el upsert por (profile_id, job_id)).
    """

    def __init__(
        self,
        *,
        embedder: Embedder,
        llm_scorer: LlmScorer,
        profile_repository: ProfileRepository,
        job_repository: JobRepository,
        match_repository: MatchRepository,
    ):
        self._embedder = embedder
        self._llm_scorer = llm_scorer
        self._profile_repository = profile_repository
        self._job_repository = job_repository
        self._match_repository = match_repository

    def execute(
        self,
        form: ProfileForm,
        *,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> int:
        k = top_k if top_k is not None else settings.top_k_for_llm
        t = threshold if threshold is not None else settings.semantic_threshold

        self._profile_repository.upsert(form.id, form.model_dump(mode="json"))
        profile_vec = self._embedder.embed([profile_text_for_embedding(form)])[0]
        self._profile_repository.update_embedding(form.id, profile_vec)

        top = self._job_repository.semantic_top_k(
            profile_vec, k=k, threshold=t, exclude_scored_for=form.id
        )
        if not top:
            logger.info("No jobs above threshold for profile %s", form.id)
            return 0

        scored = 0
        for job_id, semantic_score in top:
            job = self._job_repository.get(job_id)
            if job is None or job.requirements is None:
                # Defensa: el filtro del repo ya excluye estos, pero por si acaso.
                continue
            verdict = self._llm_scorer.score(form, job.requirements)
            self._match_repository.upsert(
                profile_id=form.id,
                job_id=job_id,
                semantic_score=semantic_score,
                llm_score=verdict.score,
                verdict=verdict.model_dump(mode="json"),
            )
            scored += 1

        logger.info("Scored %d matches for profile %s", scored, form.id)
        return scored
