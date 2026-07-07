from __future__ import annotations

from src.domain.ports.profile_repository import ProfileRepository
from src.infrastructure.security import hash_password


class ConfirmPasswordResetUseCase:
    def __init__(self, profile_repo: ProfileRepository) -> None:
        self._repo = profile_repo

    def execute(self, token: str, new_password: str) -> bool:
        profile = self._repo.get_by_reset_token(token)
        if profile is None:
            return False
        self._repo.clear_reset_token(profile.id)
        self._repo.upsert(profile.form, password_hash=hash_password(new_password))
        return True
