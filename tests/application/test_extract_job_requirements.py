from __future__ import annotations

from src.application.use_cases.extract_job_requirements import (
    ExtractJobRequirementsUseCase,
)
from src.domain.entities.job import Job
from src.domain.entities.raw_job import RawJob
from src.domain.ports.job_repository import JobRepository
from src.domain.ports.requirements_extractor import RequirementsExtractor
from src.domain.value_objects.job_requirements import JobRequirements, Seniority


def _job(job_id: str, raw_text: str = "...") -> Job:
    return Job(
        id=job_id,
        source="x",
        url="https://example.com/j",
        title="some title",
        raw_text=raw_text,
    )


class _FakeExtractor(RequirementsExtractor):
    """Devuelve un JobRequirements distinto por cada call, en orden."""

    def __init__(self, results: list[JobRequirements]):
        self._results = list(results)
        self.calls: list[str] = []

    def extract(self, raw_text: str) -> JobRequirements:
        self.calls.append(raw_text)
        return self._results.pop(0)


class _FakeJobRepo(JobRepository):
    def __init__(self, pending: list[Job]):
        self._pending = pending
        self.requirements_updates: list[tuple[str, JobRequirements]] = []

    def upsert(self, job: RawJob) -> None:
        pass

    def get(self, job_id: str) -> Job | None:
        return None

    def list_without_requirements(self, limit: int = 100) -> list[Job]:
        return self._pending[:limit]

    def list_without_embedding(self, limit: int = 100) -> list[Job]:
        return []

    def update_requirements(self, job_id: str, req: JobRequirements) -> None:
        self.requirements_updates.append((job_id, req))

    def update_embedding(self, job_id: str, vec: list[float]) -> None:
        pass

    def list_stack_technologies(self, limit: int = 30) -> list[str]:
        return []

    def list_countries(self, limit: int = 100) -> list[str]:
        return []

    def semantic_top_k(
        self,
        embedding: list[float],
        *,
        k: int,
        threshold: float,
        exclude_scored_for: str | None = None,
    ) -> list[tuple[str, float]]:
        return []


def test_extracts_for_every_pending_job_and_updates_repo():
    pending = [_job("a"), _job("b"), _job("c")]
    expected = [
        JobRequirements(seniority=Seniority.senior, confidence=0.8),
        JobRequirements(stack=["go"], confidence=0.5),
        JobRequirements(confidence=0.0),
    ]
    repo = _FakeJobRepo(pending)
    extractor = _FakeExtractor(expected)

    use_case = ExtractJobRequirementsUseCase(extractor=extractor, job_repository=repo)
    processed = use_case.execute(limit=10)

    assert processed == 3
    assert extractor.calls == ["...", "...", "..."]
    assert [job_id for job_id, _ in repo.requirements_updates] == ["a", "b", "c"]
    assert repo.requirements_updates[0][1].seniority is Seniority.senior
    assert repo.requirements_updates[1][1].stack == ["go"]


def test_no_pending_returns_zero_and_no_calls():
    repo = _FakeJobRepo(pending=[])
    extractor = _FakeExtractor(results=[])
    use_case = ExtractJobRequirementsUseCase(extractor=extractor, job_repository=repo)
    assert use_case.execute(limit=10) == 0
    assert extractor.calls == []
    assert repo.requirements_updates == []
