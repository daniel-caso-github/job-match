"""FastAPI dependencies: factory functions wired to concrete infra implementations.

Endpoints depend on the *ports* via `Annotated[SomePort, Depends(get_*)]` so the
endpoint code stays infra-agnostic. Swapping an adapter (e.g. a fake repo in
tests) is one `app.dependency_overrides` call away.
"""
from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from src.domain.ports.embedder import Embedder
from src.domain.ports.job_repository import JobRepository
from src.domain.ports.llm_scorer import LlmScorer
from src.domain.ports.match_repository import MatchRepository
from src.domain.ports.profile_repository import ProfileRepository
from src.domain.ports.requirements_extractor import RequirementsExtractor
from src.infrastructure.embedding.sentence_transformers_embedder import (
    SentenceTransformersEmbedder,
)
from src.infrastructure.llm.gemini_extractor import GeminiExtractor
from src.infrastructure.llm.gemini_scorer import GeminiScorer
from src.infrastructure.persistence.database import SessionLocal
from src.infrastructure.persistence.sqlalchemy_job_repository import (
    SqlAlchemyJobRepository,
)
from src.infrastructure.persistence.sqlalchemy_match_repository import (
    SqlAlchemyMatchRepository,
)
from src.infrastructure.persistence.sqlalchemy_profile_repository import (
    SqlAlchemyProfileRepository,
)


def get_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionDep = Annotated[Session, Depends(get_session)]


def get_job_repository(session: SessionDep) -> JobRepository:
    return SqlAlchemyJobRepository(session)


def get_profile_repository(session: SessionDep) -> ProfileRepository:
    return SqlAlchemyProfileRepository(session)


def get_match_repository(session: SessionDep) -> MatchRepository:
    return SqlAlchemyMatchRepository(session)


def get_requirements_extractor() -> RequirementsExtractor:
    return GeminiExtractor()


@lru_cache(maxsize=1)
def _embedder_singleton() -> SentenceTransformersEmbedder:
    # Cargar el modelo en memoria es caro (~133 MB); lo compartimos entre requests.
    return SentenceTransformersEmbedder()


def get_embedder() -> Embedder:
    return _embedder_singleton()


def get_llm_scorer() -> LlmScorer:
    return GeminiScorer()


JobRepositoryDep = Annotated[JobRepository, Depends(get_job_repository)]
ProfileRepositoryDep = Annotated[ProfileRepository, Depends(get_profile_repository)]
MatchRepositoryDep = Annotated[MatchRepository, Depends(get_match_repository)]
RequirementsExtractorDep = Annotated[
    RequirementsExtractor, Depends(get_requirements_extractor)
]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
LlmScorerDep = Annotated[LlmScorer, Depends(get_llm_scorer)]
