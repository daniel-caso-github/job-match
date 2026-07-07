from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.application.use_cases.confirm_password_reset import ConfirmPasswordResetUseCase
from src.domain.entities.profile import Profile
from src.domain.value_objects.profile_form import ProfileForm
from src.infrastructure.security import verify_password
from tests.interfaces.api.conftest import FAKE_PROFILE_ID, FakeProfileRepo

_FORM = ProfileForm.model_validate(
    {
        "username": "daniel",
        "email": "daniel@example.com",
        "stack": [],
        "seniority": "senior",
        "english_level": "B2",
        "location": "AR",
        "modality": "remote",
    }
)

_TOKEN = "valid-test-token"


def _make_repo_with_token(expires_delta: timedelta = timedelta(minutes=30)) -> FakeProfileRepo:
    repo = FakeProfileRepo()
    repo.profiles[FAKE_PROFILE_ID] = Profile(
        id=FAKE_PROFILE_ID, form=_FORM, embedding=None, updated_at=None, password_hash=None
    )
    repo.set_reset_token(FAKE_PROFILE_ID, _TOKEN, datetime.now(UTC) + expires_delta)
    return repo


def test_returns_true_and_updates_password_for_valid_token():
    repo = _make_repo_with_token()

    result = ConfirmPasswordResetUseCase(repo).execute(_TOKEN, "newpassword123")

    assert result is True
    updated = repo.get_by_username("daniel")
    assert updated is not None
    assert verify_password("newpassword123", updated.password_hash)


def test_clears_token_after_successful_reset():
    repo = _make_repo_with_token()

    ConfirmPasswordResetUseCase(repo).execute(_TOKEN, "newpassword123")

    assert repo.get_by_reset_token(_TOKEN) is None


def test_returns_false_for_unknown_token():
    repo = FakeProfileRepo()

    result = ConfirmPasswordResetUseCase(repo).execute("nonexistent-token", "newpassword123")

    assert result is False


def test_returns_false_for_expired_token():
    repo = _make_repo_with_token(expires_delta=timedelta(minutes=-1))

    result = ConfirmPasswordResetUseCase(repo).execute(_TOKEN, "newpassword123")

    assert result is False


def test_token_cannot_be_reused():
    repo = _make_repo_with_token()

    ConfirmPasswordResetUseCase(repo).execute(_TOKEN, "firstpass123")
    result = ConfirmPasswordResetUseCase(repo).execute(_TOKEN, "secondpass123")

    assert result is False
