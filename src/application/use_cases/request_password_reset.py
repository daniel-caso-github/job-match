from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from src.domain.ports.email_sender import EmailSender
from src.domain.ports.profile_repository import ProfileRepository
from src.infrastructure.config import settings


class RequestPasswordResetUseCase:
    def __init__(self, profile_repo: ProfileRepository, email_sender: EmailSender) -> None:
        self._repo = profile_repo
        self._email = email_sender

    def execute(self, email: str) -> None:
        profile = self._repo.get_by_email(email.strip().lower())
        if profile is None:
            return
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.reset_token_ttl_minutes)
        self._repo.set_reset_token(profile.id, token, expires_at)
        self._email.send_password_reset(email.strip().lower(), token)
