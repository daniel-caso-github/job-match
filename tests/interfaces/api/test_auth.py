from __future__ import annotations

from fastapi.testclient import TestClient

from src.domain.entities.profile import Profile
from src.domain.value_objects.profile_form import ProfileForm
from src.infrastructure.security import hash_password
from tests.interfaces.api.conftest import FAKE_PROFILE_ID, ApiContext

_FORM_DATA = {
    "username": "daniel-test",
    "stack": [],
    "seniority": "senior",
    "english_level": "B2",
    "location": "AR",
    "modality": "remote",
}


def _make_profile(password: str = "secret123") -> Profile:
    return Profile(
        id=FAKE_PROFILE_ID,
        form=ProfileForm.model_validate(_FORM_DATA),
        embedding=None,
        updated_at=None,
        password_hash=hash_password(password),
    )


def test_login_returns_token_for_valid_credentials(client: TestClient, api: ApiContext):
    api.profiles.profiles[FAKE_PROFILE_ID] = _make_profile("secret123")

    r = client.post("/auth/login", json={"username": "daniel-test", "password": "secret123"})

    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body
    assert body["profile_id"] == FAKE_PROFILE_ID
    assert body["username"] == "daniel-test"


def test_login_normalizes_username(client: TestClient, api: ApiContext):
    api.profiles.profiles[FAKE_PROFILE_ID] = _make_profile("secret123")

    r = client.post(
        "/auth/login", json={"username": "  Daniel-Test ", "password": "secret123"}
    )

    assert r.status_code == 200
    assert r.json()["username"] == "daniel-test"


def test_login_rejects_wrong_password(client: TestClient, api: ApiContext):
    api.profiles.profiles[FAKE_PROFILE_ID] = _make_profile("secret123")

    r = client.post("/auth/login", json={"username": "daniel-test", "password": "wrongpass"})

    assert r.status_code == 401


def test_login_rejects_unknown_username(client: TestClient, api: ApiContext):
    r = client.post("/auth/login", json={"username": "nobody", "password": "secret123"})

    assert r.status_code == 401


def test_login_rejects_profile_without_hash(client: TestClient, api: ApiContext):
    profile = Profile(
        id=FAKE_PROFILE_ID,
        form=ProfileForm.model_validate(_FORM_DATA),
        embedding=None,
        updated_at=None,
        password_hash=None,
    )
    api.profiles.profiles[FAKE_PROFILE_ID] = profile

    r = client.post("/auth/login", json={"username": "daniel-test", "password": "secret123"})

    assert r.status_code == 401


def test_login_does_not_reveal_whether_user_exists(client: TestClient, api: ApiContext):
    r_no_user = client.post(
        "/auth/login", json={"username": "nobody", "password": "secret123"}
    )
    api.profiles.profiles[FAKE_PROFILE_ID] = _make_profile("correct")
    r_bad_pass = client.post(
        "/auth/login", json={"username": "daniel-test", "password": "wrong"}
    )

    assert r_no_user.status_code == r_bad_pass.status_code == 401
    assert r_no_user.json()["detail"] == r_bad_pass.json()["detail"]


def test_login_rejects_missing_password_field(client: TestClient, api: ApiContext):
    r = client.post("/auth/login", json={"username": "daniel-test"})
    assert r.status_code == 422
