from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.application.use_cases.request_password_reset import RequestPasswordResetUseCase
from src.domain.entities.profile import Profile
from src.domain.value_objects.profile_form import ProfileForm
from tests.interfaces.api.conftest import FAKE_PROFILE_ID, FakeEmailSender, FakeProfileRepo

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


def _make_repo_with_profile() -> FakeProfileRepo:
    repo = FakeProfileRepo()
    repo.profiles[FAKE_PROFILE_ID] = Profile(
        id=FAKE_PROFILE_ID, form=_FORM, embedding=None, updated_at=None, password_hash=None
    )
    return repo


def test_sends_email_when_email_exists():
    repo = _make_repo_with_profile()
    sender = FakeEmailSender()

    RequestPasswordResetUseCase(repo, sender).execute("daniel@example.com")

    assert len(sender.sent) == 1
    assert sender.sent[0][0] == "daniel@example.com"


def test_stores_token_when_email_exists():
    repo = _make_repo_with_profile()
    sender = FakeEmailSender()

    RequestPasswordResetUseCase(repo, sender).execute("daniel@example.com")

    token = sender.sent[0][1]
    assert repo.get_by_reset_token(token) is not None


def test_no_email_sent_for_unknown_address():
    repo = FakeProfileRepo()
    sender = FakeEmailSender()

    RequestPasswordResetUseCase(repo, sender).execute("nobody@example.com")

    assert sender.sent == []


def test_normalizes_email_to_lowercase():
    repo = _make_repo_with_profile()
    sender = FakeEmailSender()

    RequestPasswordResetUseCase(repo, sender).execute("  DANIEL@EXAMPLE.COM  ")

    assert len(sender.sent) == 1
    assert sender.sent[0][0] == "daniel@example.com"


def test_no_email_sent_for_profile_without_email():
    repo = FakeProfileRepo()
    form_no_email = ProfileForm.model_validate(
        {
            "username": "nomail",
            "stack": [],
            "seniority": "senior",
            "english_level": "B2",
            "location": "AR",
            "modality": "remote",
        }
    )
    repo.profiles[FAKE_PROFILE_ID] = Profile(
        id=FAKE_PROFILE_ID, form=form_no_email, embedding=None, updated_at=None, password_hash=None
    )
    sender = FakeEmailSender()

    RequestPasswordResetUseCase(repo, sender).execute("nobody@example.com")

    assert sender.sent == []
