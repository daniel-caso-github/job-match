from __future__ import annotations

from collections.abc import Iterable

from src.application.use_cases.collect_jobs import CollectJobsUseCase
from src.domain.entities.job import Job
from src.domain.entities.raw_job import RawJob
from src.domain.ports.job_repository import JobRepository
from src.domain.ports.job_source import JobSource
from src.domain.services.id_hasher import make_id
from src.domain.value_objects.job_requirements import JobRequirements


class _FakeSource(JobSource):
    def __init__(self, name: str, jobs: list[RawJob]):
        self.name = name
        self._jobs = jobs

    def fetch(self, **filters) -> Iterable[RawJob]:
        yield from self._jobs


class _InMemoryJobRepo(JobRepository):
    def __init__(self):
        self.upserts: list[RawJob] = []

    def upsert(self, job: RawJob) -> None:
        self.upserts.append(job)

    def get(self, job_id: str) -> Job | None:
        return None

    def list_without_requirements(self, limit: int = 100) -> list[Job]:
        return []

    def list_without_embedding(self, limit: int = 100) -> list[Job]:
        return []

    def update_requirements(self, job_id: str, req: JobRequirements) -> None:
        pass

    def update_embedding(self, job_id: str, vec: list[float]) -> None:
        pass

    def list_stack_technologies(self, limit: int = 30) -> list[str]:
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


def _raw_job(source: str, url: str, title: str = "x") -> RawJob:
    return RawJob(
        id=make_id(source, url),
        source=source,
        url=url,
        title=title,
        raw_text="any text",
    )


def test_collect_jobs_iterates_all_sources_and_upserts_each_job():
    src_a = _FakeSource("a", [_raw_job("a", "https://a/1"), _raw_job("a", "https://a/2")])
    src_b = _FakeSource("b", [_raw_job("b", "https://b/1")])
    repo = _InMemoryJobRepo()

    use_case = CollectJobsUseCase(sources=[src_a, src_b], job_repository=repo)
    total = use_case.execute()

    assert total == 3
    assert len(repo.upserts) == 3
    assert {j.source for j in repo.upserts} == {"a", "b"}


def test_collect_jobs_empty_sources_returns_zero():
    repo = _InMemoryJobRepo()
    use_case = CollectJobsUseCase(sources=[_FakeSource("a", [])], job_repository=repo)
    assert use_case.execute() == 0
    assert repo.upserts == []
