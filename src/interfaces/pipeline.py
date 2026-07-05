from __future__ import annotations

import logging
import time

from src.application.use_cases.collect_jobs import CollectJobsUseCase
from src.application.use_cases.embed_jobs import EmbedJobsUseCase
from src.application.use_cases.extract_job_requirements import ExtractJobRequirementsUseCase
from src.application.use_cases.score_profile import ScoreProfileUseCase
from src.infrastructure.llm.gemini_extractor import GeminiExtractor
from src.infrastructure.llm.gemini_scorer import GeminiScorer
from src.infrastructure.metrics import pipeline_jobs_total, pipeline_stage_duration
from src.infrastructure.persistence.database import session_scope
from src.infrastructure.persistence.sqlalchemy_job_repository import SqlAlchemyJobRepository
from src.infrastructure.persistence.sqlalchemy_match_repository import SqlAlchemyMatchRepository
from src.infrastructure.persistence.sqlalchemy_profile_repository import SqlAlchemyProfileRepository
from src.infrastructure.sources.adzuna import AdzunaSource
from src.infrastructure.sources.arbeitnow import ArbeitnowSource
from src.infrastructure.sources.himalayas import HimalayasSource
from src.infrastructure.sources.jobicy import JobicySource
from src.infrastructure.sources.jooble import JoobleSource
from src.infrastructure.sources.remoteok import RemoteOkSource
from src.infrastructure.sources.remotive import RemotiveSource
from src.interfaces.api.dependencies import _embedder_singleton

logger = logging.getLogger(__name__)


def run_collect() -> int:
    t0 = time.perf_counter()
    with session_scope() as session:
        n = CollectJobsUseCase(
            sources=[
            HimalayasSource(),
            RemotiveSource(),
            JobicySource(),
            RemoteOkSource(),
            ArbeitnowSource(),
            AdzunaSource(),
            JoobleSource(),
        ],
            job_repository=SqlAlchemyJobRepository(session),
        ).execute()
    pipeline_jobs_total.labels(stage="collect").inc(n)
    pipeline_stage_duration.labels(stage="collect").observe(time.perf_counter() - t0)
    return n


def run_extract(limit: int = 200) -> int:
    t0 = time.perf_counter()
    with session_scope() as session:
        n = ExtractJobRequirementsUseCase(
            extractor=GeminiExtractor(),
            job_repository=SqlAlchemyJobRepository(session),
        ).execute(limit=limit)
    pipeline_jobs_total.labels(stage="extract").inc(n)
    pipeline_stage_duration.labels(stage="extract").observe(time.perf_counter() - t0)
    return n


def run_embed(limit: int = 200) -> int:
    t0 = time.perf_counter()
    with session_scope() as session:
        n = EmbedJobsUseCase(
            embedder=_embedder_singleton(),
            job_repository=SqlAlchemyJobRepository(session),
        ).execute(limit=limit)
    pipeline_jobs_total.labels(stage="embed").inc(n)
    pipeline_stage_duration.labels(stage="embed").observe(time.perf_counter() - t0)
    return n


def run_score_all_profiles() -> dict[str, int]:
    t0 = time.perf_counter()
    with session_scope() as session:
        profiles = SqlAlchemyProfileRepository(session).list_all()

    results: dict[str, int] = {}
    for profile in profiles:
        form = profile.form
        try:
            with session_scope() as session:
                n = ScoreProfileUseCase(
                    embedder=_embedder_singleton(),
                    llm_scorer=GeminiScorer(),
                    profile_repository=SqlAlchemyProfileRepository(session),
                    job_repository=SqlAlchemyJobRepository(session),
                    match_repository=SqlAlchemyMatchRepository(session),
                ).execute(form)
            results[form.username] = n
        except Exception:
            logger.exception("Scoring failed for profile %s", form.username)

    total = sum(results.values())
    pipeline_jobs_total.labels(stage="score").inc(total)
    pipeline_stage_duration.labels(stage="score").observe(time.perf_counter() - t0)
    return results
