from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.domain.entities.job import Job
from src.domain.entities.match import Match
from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.match_filters import MatchFilters
from tests.interfaces.api.conftest import FAKE_PROFILE_ID, ApiContext


def _job(job_id: str = "j1", country: str | None = "Argentina") -> Job:
    return Job.model_validate(
        {
            "id": job_id,
            "source": "himalayas",
            "url": f"https://example.com/{job_id}",
            "title": f"Backend Engineer {job_id}",
            "company": "Acme",
            "country": country,
            "raw_text": "...full description...",
            "requirements": {
                "stack": ["python", "fastapi"],
                "seniority": "senior",
                "confidence": 0.9,
            },
        }
    )


def _match(profile_id: str = FAKE_PROFILE_ID, job_id: str = "j1", llm_score: int = 88) -> Match:
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

    r = client.get("/matches")

    assert r.status_code == 200
    body = r.json()
    assert body["profile_id"] == FAKE_PROFILE_ID
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

    r = client.get("/matches", params={"limit": 5})

    assert r.status_code == 200
    assert api.matches.top_calls == [(FAKE_PROFILE_ID, 5, MatchFilters())]


def test_list_matches_defaults_to_empty_filters(client: TestClient, api: ApiContext):
    api.matches.top_response = []

    r = client.get("/matches")

    assert r.status_code == 200
    _, _, filters = api.matches.top_calls[0]
    assert filters == MatchFilters()


def test_list_matches_builds_filters_from_query_params(
    client: TestClient, api: ApiContext
):
    api.matches.top_response = []

    r = client.get(
        "/matches",
        params=[
            ("min_score", "70"),
            ("source", "himalayas"),
            ("stack", "python"),
            ("stack", "fastapi"),
            ("seniority", "senior"),
            ("seniority", "staff"),
            ("remote_only", "true"),
            ("latam_only", "true"),
            ("exclude_eu", "true"),
            ("with_salary", "true"),
        ],
    )

    assert r.status_code == 200
    _, _, filters = api.matches.top_calls[0]
    assert filters == MatchFilters(
        min_score=70,
        sources=["himalayas"],
        stack=["python", "fastapi"],
        seniorities=[Seniority.senior, Seniority.staff],
        remote_only=True,
        latam_only=True,
        exclude_eu=True,
        with_salary=True,
    )


def test_list_matches_expands_english_max(client: TestClient, api: ApiContext):
    api.matches.top_response = []

    r = client.get("/matches", params={"english_max": "B2"})

    assert r.status_code == 200
    _, _, filters = api.matches.top_calls[0]
    assert filters.english_levels == [
        EnglishLevel.a1,
        EnglishLevel.a2,
        EnglishLevel.b1,
        EnglishLevel.b2,
    ]


def test_list_matches_rejects_invalid_filter_values(
    client: TestClient, api: ApiContext
):
    r_score = client.get("/matches", params={"min_score": 150})
    r_seniority = client.get("/matches", params={"seniority": "principal"})
    assert r_score.status_code == 422
    assert r_seniority.status_code == 422


def test_list_matches_rejects_invalid_limit(client: TestClient, api: ApiContext):
    r_low = client.get("/matches", params={"limit": 0})
    r_high = client.get("/matches", params={"limit": 200})
    assert r_low.status_code == 422
    assert r_high.status_code == 422


def test_match_detail_returns_full_payload(client: TestClient, api: ApiContext):
    api.matches.pair_response = (_match(llm_score=92), _job("j1"))

    r = client.get("/matches/j1")

    assert r.status_code == 200
    body = r.json()
    assert body["job_id"] == "j1"
    assert body["llm_score"] == 92
    assert body["verdict"]["score"] == 92
    assert body["requirements"]["stack"] == ["python", "fastapi"]
    assert body["raw_text"] == "...full description..."
    assert body["scored_at"].startswith("2026-06-28")
    assert api.matches.pair_calls == [(FAKE_PROFILE_ID, "j1")]


def test_match_detail_returns_404_when_missing(client: TestClient, api: ApiContext):
    api.matches.pair_response = None

    r = client.get("/matches/nope")

    assert r.status_code == 404
    assert r.json()["detail"] == "match not found"


def test_list_matches_includes_country_in_response(client: TestClient, api: ApiContext):
    api.matches.top_response = [(_match(job_id="j1"), _job("j1", country="United States"))]

    r = client.get("/matches")

    assert r.status_code == 200
    first = r.json()["matches"][0]
    assert "country" in first
    assert first["country"] == "United States"


def test_match_detail_includes_country_in_response(client: TestClient, api: ApiContext):
    api.matches.pair_response = (_match(llm_score=85), _job("j1", country="Germany"))

    r = client.get("/matches/j1")

    assert r.status_code == 200
    body = r.json()
    assert "country" in body
    assert body["country"] == "Germany"


def test_list_matches_builds_country_filter(client: TestClient, api: ApiContext):
    api.matches.top_response = []

    r = client.get("/matches", params=[("country", "United States"), ("country", "Canada")])

    assert r.status_code == 200
    _, _, filters = api.matches.top_calls[0]
    assert filters.countries == ["United States", "Canada"]
