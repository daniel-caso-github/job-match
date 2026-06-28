"""Shared fixtures for API tests.

Each test gets a `TestClient(app)` with the persistence/LLM/embedder providers
overridden to in-memory fakes via `app.dependency_overrides`. Overrides are
cleared after every test so they don't bleed across the module."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.job import Job
from src.domain.entities.match import Match
from src.domain.entities.profile import Profile
from src.domain.entities.raw_job import RawJob
from src.domain.ports.embedder import Embedder
from src.domain.ports.job_repository import JobRepository
from src.domain.ports.llm_scorer import LlmScorer
from src.domain.ports.match_repository import MatchRepository
from src.domain.ports.profile_repository import ProfileRepository
from src.domain.value_objects.job_requirements import JobRequirements
from src.domain.value_objects.profile_form import ProfileForm
from src.domain.value_objects.verdict import Verdict
from src.interfaces.api.dependencies import (
    get_embedder,
    get_job_repository,
    get_llm_scorer,
    get_match_repository,
    get_profile_repository,
)
from src.interfaces.api.main import app

# --------------------------- fakes ---------------------------


class FakeJobRepo(JobRepository):
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.upserts: list[RawJob] = []
        self.embedding_updates: list[tuple[str, list[float]]] = []
        self.requirements_updates: list[tuple[str, JobRequirements]] = []

    def upsert(self, job: RawJob) -> None:
        self.upserts.append(job)

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def list_without_requirements(self, limit: int = 100) -> list[Job]:
        return [j for j in self.jobs.values() if j.requirements is None][:limit]

    def list_without_embedding(self, limit: int = 100) -> list[Job]:
        return [j for j in self.jobs.values() if j.embedding is None][:limit]

    def update_requirements(self, job_id: str, req: JobRequirements) -> None:
        self.requirements_updates.append((job_id, req))

    def update_embedding(self, job_id: str, vec: list[float]) -> None:
        self.embedding_updates.append((job_id, vec))

    def semantic_top_k(
        self,
        embedding: list[float],
        *,
        k: int,
        threshold: float,
        exclude_scored_for: str | None = None,
    ) -> list[tuple[str, float]]:
        return []


class FakeProfileRepo(ProfileRepository):
    def __init__(self):
        self.profiles: dict[str, Profile] = {}
        self.upserts: list[tuple[str, dict]] = []
        self.embeddings: dict[str, list[float]] = {}

    def upsert(self, profile_id: str, form_data: dict[str, Any]) -> None:
        self.upserts.append((profile_id, form_data))

    def update_embedding(self, profile_id: str, vec: list[float]) -> None:
        self.embeddings[profile_id] = vec

    def get(self, profile_id: str) -> Profile | None:
        return self.profiles.get(profile_id)

    def list_all(self) -> list[Profile]:
        return list(self.profiles.values())


class FakeMatchRepo(MatchRepository):
    def __init__(self):
        self.top_response: list[tuple[Match, Job]] = []
        self.pair_response: tuple[Match, Job] | None = None
        self.upserts: list[dict] = []
        self.top_calls: list[tuple[str, int]] = []
        self.pair_calls: list[tuple[str, str]] = []

    def upsert(
        self,
        *,
        profile_id: str,
        job_id: str,
        semantic_score: float,
        llm_score: int,
        verdict: dict[str, Any],
    ) -> None:
        self.upserts.append(
            {
                "profile_id": profile_id,
                "job_id": job_id,
                "semantic_score": semantic_score,
                "llm_score": llm_score,
                "verdict": verdict,
            }
        )

    def top_for_profile(
        self, profile_id: str, limit: int = 20
    ) -> list[tuple[Match, Job]]:
        self.top_calls.append((profile_id, limit))
        return self.top_response

    def get_for_pair(
        self, profile_id: str, job_id: str
    ) -> tuple[Match, Job] | None:
        self.pair_calls.append((profile_id, job_id))
        return self.pair_response


class FakeEmbedder(Embedder):
    def __init__(self):
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[0.0] * 384 for _ in texts]


class FakeScorer(LlmScorer):
    def __init__(self):
        self.calls: list[tuple[ProfileForm, JobRequirements]] = []

    def score(self, profile: ProfileForm, requirements: JobRequirements) -> Verdict:
        self.calls.append((profile, requirements))
        return Verdict(score=80, strengths=["stub"], risks=[])


# --------------------------- fixtures ---------------------------


@dataclass
class ApiContext:
    jobs: FakeJobRepo = field(default_factory=FakeJobRepo)
    profiles: FakeProfileRepo = field(default_factory=FakeProfileRepo)
    matches: FakeMatchRepo = field(default_factory=FakeMatchRepo)
    embedder: FakeEmbedder = field(default_factory=FakeEmbedder)
    scorer: FakeScorer = field(default_factory=FakeScorer)


@pytest.fixture
def api() -> Iterator[ApiContext]:
    ctx = ApiContext()
    app.dependency_overrides[get_job_repository] = lambda: ctx.jobs
    app.dependency_overrides[get_profile_repository] = lambda: ctx.profiles
    app.dependency_overrides[get_match_repository] = lambda: ctx.matches
    app.dependency_overrides[get_embedder] = lambda: ctx.embedder
    app.dependency_overrides[get_llm_scorer] = lambda: ctx.scorer
    try:
        yield ctx
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client(api: ApiContext) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
