from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.domain.entities.job import Job
from src.domain.entities.match import Match
from src.domain.entities.profile import Profile
from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.profile_form import ProfileForm
from tests.interfaces.api.conftest import FAKE_PROFILE_ID, FAKE_USERNAME, ApiContext


def _job(job_id: str = "j1") -> Job:
    return Job.model_validate(
        {
            "id": job_id,
            "source": "himalayas",
            "url": f"https://example.com/{job_id}",
            "title": "Backend Engineer",
            "company": "Acme",
            "raw_text": "We need Python and FastAPI experience.",
            "requirements": {"stack": ["python", "fastapi"], "confidence": 0.9},
        }
    )


def _match(job_id: str = "j1", llm_score: int | None = 88, postulation_package=None) -> Match:
    return Match(
        profile_id=FAKE_PROFILE_ID,
        job_id=job_id,
        semantic_score=0.8,
        llm_score=llm_score,
        verdict={"score": llm_score or 0, "strengths": [], "risks": []},
        scored_at=datetime(2026, 9, 1, tzinfo=UTC),
        postulation_package=postulation_package,
    )


def _seed_profile(api: ApiContext) -> None:
    form = ProfileForm(
        username=FAKE_USERNAME,
        seniority=Seniority.senior,
        english_level=EnglishLevel.b2,
        location="AR",
    )
    api.profiles.profiles[FAKE_PROFILE_ID] = Profile(id=FAKE_PROFILE_ID, form=form)


def test_generate_postulation_returns_201_and_package(client: TestClient, api: ApiContext):
    _seed_profile(api)
    api.matches.pair_response = (_match(), _job())

    r = client.post("/matches/j1/postulation")

    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pendiente_aprobacion"
    assert body["skill_gap"]["met_requirements"] == ["python"]
    assert body["resume_bullets"] == ["stub bullet"]
    assert body["cover_letter"] == "stub cover letter"
    assert api.session.commits == 1
    assert api.matches.postulation_updates[0][:2] == (FAKE_PROFILE_ID, "j1")
    # el squad recibió el profile y el job correctos
    assert api.skill_gap_analyzer.calls[0][0].username == FAKE_USERNAME
    assert api.pitch_tailorer.calls[0][2].met_requirements == ["python"]


def test_generate_postulation_404_when_match_missing(client: TestClient, api: ApiContext):
    _seed_profile(api)
    api.matches.pair_response = None

    r = client.post("/matches/j1/postulation")

    assert r.status_code == 404


def test_generate_postulation_gated_without_llm_score(client: TestClient, api: ApiContext):
    _seed_profile(api)
    api.matches.pair_response = (_match(llm_score=None), _job())

    r = client.post("/matches/j1/postulation")

    assert r.status_code == 422
    assert api.skill_gap_analyzer.calls == []
    assert api.pitch_tailorer.calls == []


def test_generate_postulation_404_when_profile_missing(client: TestClient, api: ApiContext):
    api.matches.pair_response = (_match(), _job())
    # no seed profile -> FakeProfileRepo.get devuelve None

    r = client.post("/matches/j1/postulation")

    assert r.status_code == 404


def test_get_postulation_returns_package(client: TestClient, api: ApiContext):
    package = {
        "skill_gap": {"met_requirements": [], "gaps": [], "notes": None, "confidence": 0.5},
        "resume_bullets": ["b"],
        "cover_letter": "c",
        "status": "pendiente_aprobacion",
    }
    api.matches.pair_response = (_match(postulation_package=package), _job())

    r = client.get("/matches/j1/postulation")

    assert r.status_code == 200
    assert r.json() == package


def test_get_postulation_404_when_never_generated(client: TestClient, api: ApiContext):
    api.matches.pair_response = (_match(postulation_package=None), _job())

    r = client.get("/matches/j1/postulation")

    assert r.status_code == 404


def test_approve_postulation_sets_status(client: TestClient, api: ApiContext):
    package = {
        "skill_gap": {"met_requirements": [], "gaps": [], "notes": None, "confidence": 0.5},
        "resume_bullets": ["b"],
        "cover_letter": "c",
        "status": "pendiente_aprobacion",
    }
    api.matches.pair_response = (_match(postulation_package=package), _job())

    r = client.post("/matches/j1/postulation/approve")

    assert r.status_code == 200
    assert r.json()["status"] == "aprobado"
    assert api.session.commits == 1


def test_reject_postulation_sets_status(client: TestClient, api: ApiContext):
    package = {
        "skill_gap": {"met_requirements": [], "gaps": [], "notes": None, "confidence": 0.5},
        "resume_bullets": ["b"],
        "cover_letter": "c",
        "status": "pendiente_aprobacion",
    }
    api.matches.pair_response = (_match(postulation_package=package), _job())

    r = client.post("/matches/j1/postulation/reject")

    assert r.status_code == 200
    assert r.json()["status"] == "rechazado"


def test_approve_postulation_404_when_never_generated(client: TestClient, api: ApiContext):
    api.matches.pair_response = (_match(postulation_package=None), _job())

    r = client.post("/matches/j1/postulation/approve")

    assert r.status_code == 404
