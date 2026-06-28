from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, status

from src.application.use_cases.score_profile import ScoreProfileUseCase
from src.domain.value_objects.profile_form import ProfileForm
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
from src.interfaces.api.dependencies import _embedder_singleton

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])


def _run_scoring(form: ProfileForm) -> None:
    """Background task: runs ScoreProfileUseCase in its own transaction.

    The request session is gone by the time this runs, so we open a fresh
    `session_scope()` and instantiate concrete adapters here. The embedder is
    a process-wide singleton (heavy to load); the scorer is cheap to create
    per-call."""
    try:
        with session_scope() as session:
            use_case = ScoreProfileUseCase(
                embedder=_embedder_singleton(),
                llm_scorer=GeminiScorer(),
                profile_repository=SqlAlchemyProfileRepository(session),
                job_repository=SqlAlchemyJobRepository(session),
                match_repository=SqlAlchemyMatchRepository(session),
            )
            n = use_case.execute(form)
        logger.info("Background scoring finished for profile %s: %d matches", form.id, n)
    except Exception:
        logger.exception("Background scoring failed for profile %s", form.id)


@router.post("", status_code=status.HTTP_201_CREATED)
def upsert_profile(form: ProfileForm, bg: BackgroundTasks) -> dict:
    bg.add_task(_run_scoring, form)
    return {"profile_id": form.id, "matching": "scheduled"}
