from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, status

from src.application.use_cases.collect_jobs import CollectJobsUseCase
from src.application.use_cases.embed_jobs import EmbedJobsUseCase
from src.application.use_cases.extract_job_requirements import (
    ExtractJobRequirementsUseCase,
)
from src.application.use_cases.score_profile import ScoreProfileUseCase
from src.domain.value_objects.profile_form import ProfileForm
from src.infrastructure.llm.gemini_extractor import GeminiExtractor
from src.infrastructure.llm.gemini_scorer import GeminiScorer
from src.infrastructure.persistence.database import session_scope
from src.infrastructure.persistence.sqlalchemy_job_repository import (
    SqlAlchemyJobRepository,
)
from src.infrastructure.persistence.sqlalchemy_match_repository import (
    SqlAlchemyMatchRepository,
)
from src.infrastructure.persistence.sqlalchemy_profile_repository import (
    SqlAlchemyProfileRepository,
)
from src.infrastructure.sources.himalayas import HimalayasSource
from src.infrastructure.sources.remotive import RemotiveSource
from src.interfaces.api.dependencies import _embedder_singleton

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _run_refresh() -> None:
    """Background task: runs the full pipeline end-to-end.

    Each stage gets its own short transaction so a failure mid-way doesn't
    roll back earlier progress. Per-profile re-scoring also uses its own
    session so one bad profile doesn't tank the rest."""
    try:
        with session_scope() as session:
            collected = CollectJobsUseCase(
                sources=[HimalayasSource(), RemotiveSource()],
                job_repository=SqlAlchemyJobRepository(session),
            ).execute()
        logger.info("Refresh: collected %d jobs", collected)

        with session_scope() as session:
            extracted = ExtractJobRequirementsUseCase(
                extractor=GeminiExtractor(),
                job_repository=SqlAlchemyJobRepository(session),
            ).execute()
        logger.info("Refresh: extracted requirements for %d jobs", extracted)

        with session_scope() as session:
            embedded = EmbedJobsUseCase(
                embedder=_embedder_singleton(),
                job_repository=SqlAlchemyJobRepository(session),
            ).execute()
        logger.info("Refresh: embedded %d jobs", embedded)

        with session_scope() as session:
            profiles = SqlAlchemyProfileRepository(session).list_all()

        for profile in profiles:
            try:
                form = ProfileForm.model_validate(profile.form_data)
            except Exception:
                logger.exception(
                    "Refresh: skipping profile %s (invalid form_data)", profile.id
                )
                continue
            try:
                with session_scope() as session:
                    n = ScoreProfileUseCase(
                        embedder=_embedder_singleton(),
                        llm_scorer=GeminiScorer(),
                        profile_repository=SqlAlchemyProfileRepository(session),
                        job_repository=SqlAlchemyJobRepository(session),
                        match_repository=SqlAlchemyMatchRepository(session),
                    ).execute(form)
                logger.info("Refresh: scored %d matches for profile %s", n, profile.id)
            except Exception:
                logger.exception(
                    "Refresh: scoring failed for profile %s", profile.id
                )
    except Exception:
        logger.exception("Refresh job failed")


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
def refresh(bg: BackgroundTasks) -> dict:
    bg.add_task(_run_refresh)
    return {"status": "scheduled"}
