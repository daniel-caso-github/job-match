from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.domain.entities.job import Job
from src.domain.entities.match import Match
from tests.interfaces.api.conftest import ApiContext


def _job(job_id: str = "j1") -> Job:
    return Job.model_validate(
        {
            "id": job_id,
            "source": "himalayas",
            "url": f"https://example.com/{job_id}",
            "title": f"Backend Engineer {job_id}",
            "company": "Acme",
            "raw_text": "...full description...",
            "requirements": {
                "stack": ["python", "fastapi"],
                "seniority": "senior",
                "confidence": 0.9,
            },
        }
    )


def _match(profile_id: str = "p1", job_id: str = "j1", llm_score: int = 88) -> Match:
    return Match(
        profile_id=profile_id,
        job_id=job_id,
        semantic_score=0.812,
        llm_score=llm_score,
        verdict={"score": llm_score, "strengths": ["match"], "risks": []},
        scored_at=datetime(2026, 6, 28, 10, 0, 0, tzinfo=UTC),
    )


def test_list_matches_returns_payload_with_attribution(
    client: TestClient, api: ApiContext
):
    api.matches.top_response = [
        (_match(job_id="j1", llm_score=90), _job("j1")),
        (_match(job_id="j2", llm_score=70), _job("j2")),
    ]

    r = client.get("/matches", params={"profile_id": "p1"})

    assert r.status_code == 200
    body = r.json()
    assert body["profile_id"] == "p1"
    assert body["count"] == 2
    assert "Himalayas" in body["source_attribution"]
    assert "Remotive" in body["source_attribution"]
    assert [m["job_id"] for m in body["matches"]] == ["j1", "j2"]
    first = body["matches"][0]
    assert first["title"] == "Backend Engineer j1"
    assert first["company"] == "Acme"
    assert first["llm_score"] == 90
    assert first["semantic_score"] == 0.812
    assert first["verdict"]["strengths"] == ["match"]


def test_list_matches_passes_limit_to_repo(client: TestClient, api: ApiContext):
    api.matches.top_response = []

    r = client.get("/matches", params={"profile_id": "p1", "limit": 5})

    assert r.status_code == 200
    assert api.matches.top_calls == [("p1", 5)]


def test_list_matches_rejects_invalid_limit(client: TestClient, api: ApiContext):
    r_low = client.get("/matches", params={"profile_id": "p1", "limit": 0})
    r_high = client.get("/matches", params={"profile_id": "p1", "limit": 200})
    assert r_low.status_code == 422
    assert r_high.status_code == 422


def test_list_matches_requires_profile_id(client: TestClient, api: ApiContext):
    r = client.get("/matches")
    assert r.status_code == 422


def test_match_detail_returns_full_payload(client: TestClient, api: ApiContext):
    api.matches.pair_response = (_match(llm_score=92), _job("j1"))

    r = client.get("/matches/j1", params={"profile_id": "p1"})

    assert r.status_code == 200
    body = r.json()
    assert body["job_id"] == "j1"
    assert body["llm_score"] == 92
    assert body["verdict"]["score"] == 92
    assert body["requirements"]["stack"] == ["python", "fastapi"]
    assert body["raw_text"] == "...full description..."
    assert body["scored_at"].startswith("2026-06-28")
    assert api.matches.pair_calls == [("p1", "j1")]


def test_match_detail_returns_404_when_missing(client: TestClient, api: ApiContext):
    api.matches.pair_response = None

    r = client.get("/matches/nope", params={"profile_id": "p1"})

    assert r.status_code == 404
    assert r.json()["detail"] == "match not found"
