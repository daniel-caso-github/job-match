from __future__ import annotations

import math

import pytest

from src.infrastructure.embedding.sentence_transformers_embedder import (
    SentenceTransformersEmbedder,
)


@pytest.fixture(scope="module")
def embedder() -> SentenceTransformersEmbedder:
    return SentenceTransformersEmbedder()


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _cos(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_empty_input_returns_empty(embedder: SentenceTransformersEmbedder):
    assert embedder.embed([]) == []


def test_shape_and_normalization(embedder: SentenceTransformersEmbedder):
    vecs = embedder.embed(["Senior Python backend engineer with FastAPI"])
    assert len(vecs) == 1
    assert len(vecs[0]) == 384
    assert math.isclose(_norm(vecs[0]), 1.0, abs_tol=1e-3)


def test_batch_returns_parallel_list(embedder: SentenceTransformersEmbedder):
    vecs = embedder.embed(["hello", "world", "embedding test"])
    assert len(vecs) == 3
    for v in vecs:
        assert len(v) == 384
        assert math.isclose(_norm(v), 1.0, abs_tol=1e-3)


def test_relative_similarity_backend_vs_marketing(
    embedder: SentenceTransformersEmbedder,
):
    a, b, c = embedder.embed(
        [
            "Senior Python backend engineer",
            "Python developer with FastAPI",
            "Marketing copywriter for fashion brand",
        ]
    )
    sim_ab = _cos(a, b)
    sim_ac = _cos(a, c)
    assert sim_ab > sim_ac, f"backend↔backend ({sim_ab:.3f}) should exceed backend↔marketing ({sim_ac:.3f})"
