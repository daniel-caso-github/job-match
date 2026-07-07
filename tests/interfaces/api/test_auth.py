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


# ---- forgot-password ----

def test_forgot_password_returns_200_for_existing_email(client: TestClient, api: ApiContext):
    api.profiles.profiles[FAKE_PROFILE_ID] = _make_profile()
    api.profiles._ids_by_username["daniel-test"] = FAKE_PROFILE_ID

    r = client.post("/auth/forgot-password", json={"email": "daniel@example.com"})

    assert r.status_code == 200


def test_forgot_password_returns_200_for_unknown_email(client: TestClient, api: ApiContext):
    r = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})

    assert r.status_code == 200


def test_forgot_password_sends_email_only_when_registered(client: TestClient, api: ApiContext):
    profile = Profile(
        id=FAKE_PROFILE_ID,
        form=ProfileForm.model_validate({**_FORM_DATA, "email": "daniel@example.com"}),
        embedding=None,
        updated_at=None,
        password_hash=None,
    )
    api.profiles.profiles[FAKE_PROFILE_ID] = profile

    client.post("/auth/forgot-password", json={"email": "daniel@example.com"})
    assert len(api.email.sent) == 1
    assert api.email.sent[0][0] == "daniel@example.com"

    client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert len(api.email.sent) == 1  # no second email


# ---- reset-password ----

def test_reset_password_updates_password_with_valid_token(client: TestClient, api: ApiContext):
    from datetime import UTC, datetime, timedelta

    profile = Profile(
        id=FAKE_PROFILE_ID,
        form=ProfileForm.model_validate(_FORM_DATA),
        embedding=None,
        updated_at=None,
        password_hash=None,
    )
    api.profiles.profiles[FAKE_PROFILE_ID] = profile
    api.profiles.set_reset_token(
        FAKE_PROFILE_ID, "valid-token", datetime.now(UTC) + timedelta(minutes=30)
    )

    r = client.post(
        "/auth/reset-password", json={"token": "valid-token", "new_password": "newpass123"}
    )

    assert r.status_code == 200


def test_reset_password_returns_400_for_invalid_token(client: TestClient, api: ApiContext):
    r = client.post(
        "/auth/reset-password", json={"token": "bad-token", "new_password": "newpass123"}
    )

    assert r.status_code == 400


def test_reset_password_rejects_short_password(client: TestClient, api: ApiContext):
    r = client.post("/auth/reset-password", json={"token": "any", "new_password": "short"})

    assert r.status_code == 422
