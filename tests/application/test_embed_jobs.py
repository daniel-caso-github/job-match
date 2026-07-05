from __future__ import annotations

from src.application.use_cases.embed_jobs import EmbedJobsUseCase
from src.domain.entities.job import Job
from src.domain.entities.raw_job import RawJob
from src.domain.ports.embedder import Embedder
from src.domain.ports.job_repository import JobRepository
from src.domain.value_objects.job_requirements import JobRequirements


def _job(job_id: str, title: str = "Backend Engineer") -> Job:
    return Job.model_validate(
        {
            "id": job_id,
            "source": "himalayas",
            "url": f"https://example.com/{job_id}",
            "title": title,
            "raw_text": f"Description for {title}.",
        }
    )


class _StubEmbedder(Embedder):
    def __init__(self, dim: int = 384):
        self._dim = dim
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[float(i) / max(len(texts), 1)] * self._dim for i in range(len(texts))]


class _FakeJobRepo(JobRepository):
    def __init__(self, pending: list[Job]):
        self._pending = pending
        self.embedding_updates: list[tuple[str, list[float]]] = []

    def upsert(self, job: RawJob) -> None:
        pass

    def get(self, job_id: str) -> Job | None:
        return next((j for j in self._pending if j.id == job_id), None)

    def list_without_requirements(self, limit: int = 100) -> list[Job]:
        return []

    def list_without_embedding(self, limit: int = 100) -> list[Job]:
        return self._pending[:limit]

    def update_requirements(self, job_id: str, req: JobRequirements) -> None:
        pass

    def update_embedding(self, job_id: str, vec: list[float]) -> None:
        self.embedding_updates.append((job_id, vec))

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


def test_embeds_every_pending_job():
    repo = _FakeJobRepo([_job("a"), _job("b"), _job("c")])
    embedder = _StubEmbedder()

    n = EmbedJobsUseCase(embedder=embedder, job_repository=repo).execute()

    assert n == 3
    assert [jid for jid, _ in repo.embedding_updates] == ["a", "b", "c"]
    assert all(len(v) == 384 for _, v in repo.embedding_updates)
    # one batched call to the embedder, not three individual ones
    assert len(embedder.calls) == 1
    assert len(embedder.calls[0]) == 3


def test_no_pending_returns_zero_without_calling_embedder():
    repo = _FakeJobRepo(pending=[])
    embedder = _StubEmbedder()

    n = EmbedJobsUseCase(embedder=embedder, job_repository=repo).execute()

    assert n == 0
    assert embedder.calls == []
    assert repo.embedding_updates == []


def test_respects_limit():
    repo = _FakeJobRepo([_job(str(i)) for i in range(10)])
    embedder = _StubEmbedder()

    n = EmbedJobsUseCase(embedder=embedder, job_repository=repo).execute(limit=4)

    assert n == 4
    assert len(repo.embedding_updates) == 4
