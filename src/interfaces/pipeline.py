from __future__ import annotations

import logging

from src.application.use_cases.collect_jobs import CollectJobsUseCase
from src.application.use_cases.embed_jobs import EmbedJobsUseCase
from src.application.use_cases.extract_job_requirements import ExtractJobRequirementsUseCase
from src.application.use_cases.score_profile import ScoreProfileUseCase
from src.domain.value_objects.profile_form import ProfileForm
from src.infrastructure.llm.gemini_extractor import GeminiExtractor
from src.infrastructure.llm.gemini_scorer import GeminiScorer
from src.infrastructure.persistence.database import session_scope
from src.infrastructure.persistence.sqlalchemy_job_repository import SqlAlchemyJobRepository
from src.infrastructure.persistence.sqlalchemy_match_repository import SqlAlchemyMatchRepository
from src.infrastructure.persistence.sqlalchemy_profile_repository import SqlAlchemyProfileRepository
from src.infrastructure.sources.himalayas import HimalayasSource
from src.infrastructure.sources.remotive import RemotiveSource
from src.interfaces.api.dependencies import _embedder_singleton

logger = logging.getLogger(__name__)


def run_collect() -> int:
    with session_scope() as session:
        return CollectJobsUseCase(
            sources=[HimalayasSource(), RemotiveSource()],
            job_repository=SqlAlchemyJobRepository(session),
        ).execute()


def run_extract(limit: int = 200) -> int:
    with session_scope() as session:
        return ExtractJobRequirementsUseCase(
            extractor=GeminiExtractor(),
            job_repository=SqlAlchemyJobRepository(session),
        ).execute(limit=limit)


def run_embed(limit: int = 200) -> int:
    with session_scope() as session:
        return EmbedJobsUseCase(
            embedder=_embedder_singleton(),
            job_repository=SqlAlchemyJobRepository(session),
        ).execute(limit=limit)


def run_score_all_profiles() -> dict[str, int]:
    with session_scope() as session:
        profiles = SqlAlchemyProfileRepository(session).list_all()

    results: dict[str, int] = {}
    for profile in profiles:
        try:
            form = ProfileForm.model_validate(profile.form_data)
        except Exception:
            logger.exception("Skipping profile %s (invalid form_data)", profile.id)
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
            results[form.id] = n
        except Exception:
            logger.exception("Scoring failed for profile %s", profile.id)
    return results
