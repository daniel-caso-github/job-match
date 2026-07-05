from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.domain.entities.profile import Profile
from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.profile_form import ProfileForm
from tests.interfaces.api.conftest import FAKE_PROFILE_ID, ApiContext


def _valid_body(**overrides) -> dict:
    body = {
        "username": "daniel-test",
        "email": "daniel@example.com",
        "password": "secret123",
    }
    body.update(overrides)
    return body


def _valid_profile_form(**overrides) -> dict:
    form = {
        "username": "daniel-test",
        "stack": [{"name": "Python", "years": 8}],
        "seniority": "senior",
        "english_level": "B2",
        "location": "AR",
        "modality": "remote",
        "summary": "Backend engineer focused on APIs.",
    }
    form.update(overrides)
    return form


def test_post_profile_upserts_and_schedules_scoring(
    client: TestClient, api: ApiContext
):
    with patch("src.interfaces.api.routers.profile._run_scoring") as mock_scoring:
        r = client.post("/profile", json=_valid_body())

    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "daniel-test"
    assert body["matching"] == "scheduled"
    assert api.session.commits == 1
    mock_scoring.assert_called_once()
    assert mock_scoring.call_args.args[0].username == "daniel-test"


def test_post_profile_creates_with_default_professional_fields(
    client: TestClient, api: ApiContext
):
    with patch("src.interfaces.api.routers.profile._run_scoring"):
        r = client.post("/profile", json=_valid_body())

    assert r.status_code == 201
    saved_form = api.profiles.upserts[0]
    assert saved_form.seniority == Seniority.junior
    assert saved_form.english_level == EnglishLevel.b1
    assert saved_form.location == "US"
    assert saved_form.modality == "remote"
    assert saved_form.stack == []


def test_post_profile_stores_email_and_name(client: TestClient, api: ApiContext):
    with patch("src.interfaces.api.routers.profile._run_scoring"):
        r = client.post(
            "/profile",
            json=_valid_body(first_name="Daniel", last_name="Caso"),
        )

    assert r.status_code == 201
    saved_form = api.profiles.upserts[0]
    assert saved_form.email == "daniel@example.com"
    assert saved_form.first_name == "Daniel"
    assert saved_form.last_name == "Caso"


def test_post_profile_rejects_duplicate_username(client: TestClient, api: ApiContext):
    form = ProfileForm.model_validate(_valid_profile_form())
    api.profiles.profiles[FAKE_PROFILE_ID] = Profile(
        id=FAKE_PROFILE_ID, form=form, embedding=None, updated_at=None
    )

    r = client.post("/profile", json=_valid_body())

    assert r.status_code == 409
    assert "username" in r.json()["detail"]


def test_post_profile_rejects_duplicate_email(client: TestClient, api: ApiContext):
    form = ProfileForm.model_validate({**_valid_profile_form(), "email": "daniel@example.com"})
    api.profiles.profiles[FAKE_PROFILE_ID] = Profile(
        id=FAKE_PROFILE_ID, form=form, embedding=None, updated_at=None
    )

    r = client.post("/profile", json=_valid_body(username="other-user"))

    assert r.status_code == 409
    assert "email" in r.json()["detail"]


def test_post_profile_normalizes_username(client: TestClient, api: ApiContext):
    with patch("src.interfaces.api.routers.profile._run_scoring"):
        r = client.post("/profile", json=_valid_body(username="  Daniel-Test "))

    assert r.status_code == 201
    assert r.json()["username"] == "daniel-test"


def test_post_profile_rejects_invalid_username(client: TestClient, api: ApiContext):
    r = client.post("/profile", json=_valid_body(username="daniel test!"))
    assert r.status_code == 422


def test_post_profile_requires_password(client: TestClient, api: ApiContext):
    body = {"username": "daniel-test", "email": "daniel@example.com"}
    r = client.post("/profile", json=body)
    assert r.status_code == 422


def test_post_profile_rejects_short_password(client: TestClient, api: ApiContext):
    r = client.post("/profile", json=_valid_body(password="abc"))
    assert r.status_code == 422


def test_post_profile_requires_email(client: TestClient, api: ApiContext):
    body = {"username": "daniel-test", "password": "secret123"}
    r = client.post("/profile", json=body)
    assert r.status_code == 422


def test_post_profile_rejects_invalid_email(client: TestClient, api: ApiContext):
    r = client.post("/profile", json=_valid_body(email="not-an-email"))
    assert r.status_code == 422


def test_get_profile_returns_form(client: TestClient, api: ApiContext):
    form = ProfileForm.model_validate(_valid_profile_form())
    api.profiles.profiles[FAKE_PROFILE_ID] = Profile(
        id=FAKE_PROFILE_ID, form=form, embedding=None, updated_at=None
    )

    r = client.get(f"/profile/{FAKE_PROFILE_ID}")

    assert r.status_code == 200
    assert r.json() == form.model_dump(mode="json")


def test_get_profile_returns_403_for_other_profile(client: TestClient, api: ApiContext):
    r = client.get("/profile/other-profile-id")
    assert r.status_code == 403


def test_get_profile_returns_404_when_missing(client: TestClient, api: ApiContext):
    r = client.get(f"/profile/{FAKE_PROFILE_ID}")
    assert r.status_code == 404
