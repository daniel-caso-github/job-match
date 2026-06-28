from __future__ import annotations

from typing import Any

from src.application.use_cases.score_profile import ScoreProfileUseCase
from src.domain.entities.job import Job
from src.domain.entities.match import Match
from src.domain.entities.profile import Profile
from src.domain.entities.raw_job import RawJob
from src.domain.ports.embedder import Embedder
from src.domain.ports.job_repository import JobRepository
from src.domain.ports.llm_scorer import LlmScorer
from src.domain.ports.match_repository import MatchRepository
from src.domain.ports.profile_repository import ProfileRepository
from src.domain.value_objects.job_requirements import (
    EnglishLevel,
    JobRequirements,
    Seniority,
)
from src.domain.value_objects.profile_form import ProfileForm, TechItem
from src.domain.value_objects.verdict import Verdict


def _profile_form() -> ProfileForm:
    return ProfileForm(
        id="daniel",
        stack=[TechItem(name="Python", years=8)],
        seniority=Seniority.senior,
        english_level=EnglishLevel.b2,
        location="AR",
        summary="Backend.",
    )


def _job(job_id: str, req: JobRequirements | None) -> Job:
    return Job.model_validate(
        {
            "id": job_id,
            "source": "himalayas",
            "url": f"https://example.com/{job_id}",
            "title": f"Job {job_id}",
            "raw_text": "...",
            "requirements": req.model_dump(mode="json") if req else None,
        }
    )


class _StubEmbedder(Embedder):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]


class _StubScorer(LlmScorer):
    def __init__(self, score_value: int = 80):
        self._score = score_value
        self.calls = 0

    def score(self, profile, requirements) -> Verdict:
        self.calls += 1
        return Verdict(score=self._score, strengths=["match"], risks=[])


class _InMemoryProfileRepo(ProfileRepository):
    def __init__(self):
        self.upserts: list[tuple[str, dict]] = []
        self.embeddings: dict[str, list[float]] = {}

    def upsert(self, profile_id: str, form_data: dict[str, Any]) -> None:
        self.upserts.append((profile_id, form_data))

    def update_embedding(self, profile_id: str, vec: list[float]) -> None:
        self.embeddings[profile_id] = vec

    def get(self, profile_id: str) -> Profile | None:
        return None

    def list_all(self) -> list[Profile]:
        return []


class _InMemoryJobRepo(JobRepository):
    """Repo cuya semantic_top_k devuelve los jobs preconfigurados, con la opción
    de filtrar los ya scoreados (para validar la rama de idempotencia)."""

    def __init__(self, jobs: list[Job], top_k_pairs: list[tuple[str, float]]):
        self._jobs = {j.id: j for j in jobs}
        self._top_k_pairs = top_k_pairs
        self._scored_for_profile: dict[str, set[str]] = {}

    def mark_scored(self, profile_id: str, job_id: str) -> None:
        self._scored_for_profile.setdefault(profile_id, set()).add(job_id)

    def upsert(self, job: RawJob) -> None:
        pass

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list_without_requirements(self, limit: int = 100) -> list[Job]:
        return []

    def list_without_embedding(self, limit: int = 100) -> list[Job]:
        return []

    def update_requirements(self, job_id: str, req: JobRequirements) -> None:
        pass

    def update_embedding(self, job_id: str, vec: list[float]) -> None:
        pass

    def semantic_top_k(
        self,
        embedding: list[float],
        *,
        k: int,
        threshold: float,
        exclude_scored_for: str | None = None,
    ) -> list[tuple[str, float]]:
        scored = (
            self._scored_for_profile.get(exclude_scored_for, set())
            if exclude_scored_for
            else set()
        )
        return [(jid, s) for jid, s in self._top_k_pairs if jid not in scored][:k]


class _InMemoryMatchRepo(MatchRepository):
    def __init__(self):
        self.matches: dict[tuple[str, str], dict] = {}

    def upsert(
        self,
        *,
        profile_id: str,
        job_id: str,
        semantic_score: float,
        llm_score: int,
        verdict: dict[str, Any],
    ) -> None:
        self.matches[(profile_id, job_id)] = {
            "semantic_score": semantic_score,
            "llm_score": llm_score,
            "verdict": verdict,
        }

    def top_for_profile(
        self, profile_id: str, limit: int = 20
    ) -> list[tuple[Match, Job]]:
        return []


def _requirements() -> JobRequirements:
    return JobRequirements(stack=["python"], seniority=Seniority.senior)


def test_scores_every_candidate_and_upserts_match():
    form = _profile_form()
    jobs = [_job("a", _requirements()), _job("b", _requirements())]
    job_repo = _InMemoryJobRepo(jobs, [("a", 0.81), ("b", 0.73)])
    profile_repo = _InMemoryProfileRepo()
    match_repo = _InMemoryMatchRepo()
    scorer = _StubScorer(score_value=80)

    n = ScoreProfileUseCase(
        embedder=_StubEmbedder(),
        llm_scorer=scorer,
        profile_repository=profile_repo,
        job_repository=job_repo,
        match_repository=match_repo,
    ).execute(form)

    assert n == 2
    assert scorer.calls == 2
    assert profile_repo.upserts == [(form.id, form.model_dump(mode="json"))]
    assert profile_repo.embeddings[form.id] == [0.1] * 384
    assert set(match_repo.matches.keys()) == {(form.id, "a"), (form.id, "b")}
    assert match_repo.matches[(form.id, "a")]["semantic_score"] == 0.81
    assert match_repo.matches[(form.id, "a")]["llm_score"] == 80
    assert match_repo.matches[(form.id, "a")]["verdict"]["strengths"] == ["match"]


def test_skips_jobs_without_requirements():
    form = _profile_form()
    jobs = [_job("a", None), _job("b", _requirements())]
    job_repo = _InMemoryJobRepo(jobs, [("a", 0.9), ("b", 0.7)])
    match_repo = _InMemoryMatchRepo()
    scorer = _StubScorer()

    n = ScoreProfileUseCase(
        embedder=_StubEmbedder(),
        llm_scorer=scorer,
        profile_repository=_InMemoryProfileRepo(),
        job_repository=job_repo,
        match_repository=match_repo,
    ).execute(form)

    assert n == 1
    assert scorer.calls == 1
    assert set(match_repo.matches.keys()) == {(form.id, "b")}


def test_idempotent_second_run_does_not_double_score():
    """Si el segundo run usa exclude_scored_for, no re-scorea matches existentes."""
    form = _profile_form()
    jobs = [_job("a", _requirements()), _job("b", _requirements())]
    job_repo = _InMemoryJobRepo(jobs, [("a", 0.8), ("b", 0.7)])
    match_repo = _InMemoryMatchRepo()
    scorer = _StubScorer()
    use_case = ScoreProfileUseCase(
        embedder=_StubEmbedder(),
        llm_scorer=scorer,
        profile_repository=_InMemoryProfileRepo(),
        job_repository=job_repo,
        match_repository=match_repo,
    )

    n1 = use_case.execute(form)
    # simulate persisted state: el repo de jobs ahora sabe qué se scoreó.
    for (pid, jid) in match_repo.matches:
        job_repo.mark_scored(pid, jid)

    n2 = use_case.execute(form)

    assert n1 == 2
    assert n2 == 0
    assert scorer.calls == 2  # no se llamó al LLM la segunda vez


def test_no_candidates_returns_zero_without_calling_scorer():
    form = _profile_form()
    job_repo = _InMemoryJobRepo(jobs=[], top_k_pairs=[])
    match_repo = _InMemoryMatchRepo()
    scorer = _StubScorer()

    n = ScoreProfileUseCase(
        embedder=_StubEmbedder(),
        llm_scorer=scorer,
        profile_repository=_InMemoryProfileRepo(),
        job_repository=job_repo,
        match_repository=match_repo,
    ).execute(form)

    assert n == 0
    assert scorer.calls == 0
    assert match_repo.matches == {}
