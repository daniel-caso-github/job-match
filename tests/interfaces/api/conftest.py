"""Shared fixtures for API tests.

Each test gets a `TestClient(app)` with the persistence/LLM/embedder providers
overridden to in-memory fakes via `app.dependency_overrides`. Overrides are
cleared after every test so they don't bleed across the module."""
from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.job import Job
from src.domain.entities.match import Match
from src.domain.entities.profile import Profile
from src.domain.entities.raw_job import RawJob
from src.domain.entities.saved_search import SavedSearch
from src.domain.ports.email_sender import EmailSender
from src.domain.ports.embedder import Embedder
from src.domain.ports.job_repository import JobRepository
from src.domain.ports.llm_scorer import LlmScorer
from src.domain.ports.match_repository import MatchRepository
from src.domain.ports.profile_repository import ProfileRepository
from src.domain.ports.saved_search_repository import SavedSearchRepository
from src.domain.value_objects.job_requirements import JobRequirements
from src.domain.value_objects.match_filters import MatchFilters
from src.domain.value_objects.profile_form import ProfileForm
from src.domain.value_objects.verdict import Verdict
from src.infrastructure.security import create_access_token
from src.interfaces.api.dependencies import (
    TokenData,
    get_airflow_client,
    get_current_profile,
    get_email_sender,
    get_embedder,
    get_job_repository,
    get_llm_scorer,
    get_match_repository,
    get_profile_repository,
    get_saved_search_repository,
    get_session,
    verify_internal_api_key,
)
from src.interfaces.api.main import app

FAKE_PROFILE_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "daniel-test"))
FAKE_USERNAME = "daniel-test"


def make_auth_headers(profile_id: str = FAKE_PROFILE_ID, username: str = FAKE_USERNAME) -> dict:
    """Devuelve headers con un JWT válido para los tests."""
    token = create_access_token(profile_id, username)
    return {"Authorization": f"Bearer {token}"}

# --------------------------- fakes ---------------------------


class FakeJobRepo(JobRepository):
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.upserts: list[RawJob] = []
        self.embedding_updates: list[tuple[str, list[float]]] = []
        self.requirements_updates: list[tuple[str, JobRequirements]] = []
        self.technologies: list[str] = []
        self.technologies_calls: list[int] = []
        self.countries: list[str] = []
        self.countries_calls: list[int] = []

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

    def list_stack_technologies(self, limit: int = 30) -> list[str]:
        self.technologies_calls.append(limit)
        return self.technologies[:limit]

    def list_countries(self, limit: int = 100) -> list[str]:
        self.countries_calls.append(limit)
        return self.countries[:limit]

    def semantic_top_k(
        self,
        embedding: list[float],
        *,
        k: int,
        threshold: float,
        exclude_scored_for: str | None = None,
    ) -> list[tuple[str, float]]:
        return []


class FakeEmailSender(EmailSender):
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send_password_reset(self, to_email: str, reset_token: str) -> None:
        self.sent.append((to_email, reset_token))


class FakeProfileRepo(ProfileRepository):
    def __init__(self):
        self.profiles: dict[str, Profile] = {}
        self.upserts: list[ProfileForm] = []
        self.embeddings: dict[str, list[float]] = {}
        self._ids_by_username: dict[str, str] = {}
        self._reset_tokens: dict[str, tuple[str, datetime]] = {}

    def upsert(self, form: ProfileForm, password_hash: str | None = None) -> str:
        self.upserts.append(form)
        # Busca un perfil existente por username (incluye los insertados manualmente)
        existing_id = next(
            (pid for pid, p in self.profiles.items() if p.form.username == form.username),
            None,
        )
        if existing_id:
            profile_id = existing_id
            self._ids_by_username[form.username] = existing_id
        else:
            profile_id = self._ids_by_username.setdefault(
                form.username, str(uuid.uuid5(uuid.NAMESPACE_DNS, form.username))
            )
        from src.domain.entities.profile import Profile
        self.profiles[profile_id] = Profile(id=profile_id, form=form, password_hash=password_hash)
        return profile_id

    def update_embedding(self, profile_id: str, vec: list[float]) -> None:
        self.embeddings[profile_id] = vec

    def get(self, profile_id: str) -> Profile | None:
        return self.profiles.get(profile_id)

    def get_by_username(self, username: str) -> Profile | None:
        for profile in self.profiles.values():
            if profile.form.username == username:
                return profile
        return None

    def get_by_email(self, email: str) -> Profile | None:
        for profile in self.profiles.values():
            if profile.form.email == email:
                return profile
        return None

    def set_reset_token(self, profile_id: str, token: str, expires_at: datetime) -> None:
        self._reset_tokens[token] = (profile_id, expires_at)

    def get_by_reset_token(self, token: str) -> Profile | None:
        entry = self._reset_tokens.get(token)
        if entry is None:
            return None
        profile_id, expires_at = entry
        if datetime.now(UTC) > expires_at:
            return None
        return self.profiles.get(profile_id)

    def clear_reset_token(self, profile_id: str) -> None:
        self._reset_tokens = {
            t: v for t, v in self._reset_tokens.items() if v[0] != profile_id
        }

    def list_all(self) -> list[Profile]:
        return list(self.profiles.values())


class FakeMatchRepo(MatchRepository):
    def __init__(self):
        self.top_response: list[tuple[Match, Job]] = []
        self.pair_response: tuple[Match, Job] | None = None
        self.upserts: list[dict] = []
        self.top_calls: list[tuple[str, int, MatchFilters | None]] = []
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
        self, profile_id: str, limit: int = 20, filters: MatchFilters | None = None
    ) -> list[tuple[Match, Job]]:
        self.top_calls.append((profile_id, limit, filters))
        return self.top_response

    def get_for_pair(
        self, profile_id: str, job_id: str
    ) -> tuple[Match, Job] | None:
        self.pair_calls.append((profile_id, job_id))
        return self.pair_response

    def count_for_profile(
        self, profile_id: str, filters: MatchFilters | None = None
    ) -> int:
        return sum(1 for u in self.upserts if u["profile_id"] == profile_id)


class FakeSavedSearchRepo(SavedSearchRepository):
    def __init__(self):
        self.items: list[SavedSearch] = []

    def add(self, search: SavedSearch) -> None:
        self.items.append(search)

    def list_for_profile(self, profile_id: str, limit: int = 20) -> list[SavedSearch]:
        return [s for s in reversed(self.items) if s.profile_id == profile_id][:limit]

    def get_by_dag_run_id(self, dag_run_id: str) -> SavedSearch | None:
        return next((s for s in self.items if s.dag_run_id == dag_run_id), None)

    def set_match_count(self, dag_run_id: str, count: int) -> None:
        for s in self.items:
            if s.dag_run_id == dag_run_id:
                self.items[self.items.index(s)] = s.model_copy(update={"match_count": count})
                return

    def delete(self, dag_run_id: str) -> None:
        self.items = [s for s in self.items if s.dag_run_id != dag_run_id]


class FakeSession:
    def __init__(self):
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class FakeAirflowClient:
    def __init__(self):
        self.triggered: list[str] = []
        self.dag_run_id = "manual__2026-07-04T00:00:00+00:00"
        self.dag_info: dict = {
            "schedule_interval": {"value": "0 */12 * * *"},
            "next_dagrun": "2026-07-05T00:00:00+00:00",
            "next_dagrun_data_interval_end": "2026-07-05T12:00:00+00:00",
            "is_paused": False,
        }
        self.confs: list[dict] = []
        self.logical_dates: list[str | None] = []
        self.dag_runs: list[dict] = []
        self.task_instances: dict[str, list[dict]] = {}
        self.error: Exception | None = None

    def trigger_dag(
        self,
        dag_id: str,
        conf: dict | None = None,
        logical_date: str | None = None,
    ) -> str:
        if self.error is not None:
            raise self.error
        self.triggered.append(dag_id)
        self.confs.append(conf or {})
        self.logical_dates.append(logical_date)
        return self.dag_run_id

    def get_dag(self, dag_id: str) -> dict:
        if self.error is not None:
            raise self.error
        return self.dag_info

    def list_dag_runs(self, dag_id: str, limit: int = 4) -> list[dict]:
        if self.error is not None:
            raise self.error
        return self.dag_runs[:limit]

    def delete_dag_run(self, dag_id: str, dag_run_id: str) -> None:
        if self.error is not None:
            raise self.error
        self.triggered = [r for r in self.triggered if r != dag_run_id]

    def list_task_instances(self, dag_id: str, dag_run_id: str) -> list[dict]:
        if self.error is not None:
            raise self.error
        return self.task_instances.get(dag_run_id, [])


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
    airflow: FakeAirflowClient = field(default_factory=FakeAirflowClient)
    saved_searches: FakeSavedSearchRepo = field(default_factory=FakeSavedSearchRepo)
    session: FakeSession = field(default_factory=FakeSession)
    email: FakeEmailSender = field(default_factory=FakeEmailSender)


@pytest.fixture
def api() -> Iterator[ApiContext]:
    ctx = ApiContext()
    app.dependency_overrides[get_job_repository] = lambda: ctx.jobs
    app.dependency_overrides[get_profile_repository] = lambda: ctx.profiles
    app.dependency_overrides[get_match_repository] = lambda: ctx.matches
    app.dependency_overrides[get_embedder] = lambda: ctx.embedder
    app.dependency_overrides[get_llm_scorer] = lambda: ctx.scorer
    app.dependency_overrides[get_airflow_client] = lambda: ctx.airflow
    app.dependency_overrides[get_saved_search_repository] = lambda: ctx.saved_searches
    app.dependency_overrides[get_session] = lambda: ctx.session
    app.dependency_overrides[get_email_sender] = lambda: ctx.email
    app.dependency_overrides[verify_internal_api_key] = lambda: None
    app.dependency_overrides[get_current_profile] = lambda: TokenData(
        profile_id=FAKE_PROFILE_ID, username=FAKE_USERNAME
    )
    try:
        yield ctx
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client(api: ApiContext) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
