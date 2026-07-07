from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.profile import Profile
from src.domain.value_objects.profile_form import ProfileForm


class ProfileRepository(ABC):
    """Port de persistencia para perfiles."""

    @abstractmethod
    def upsert(self, form: ProfileForm, password_hash: str | None = None) -> str:
        """Inserta o actualiza por `username`; devuelve el id (UUID) del perfil.

        `password_hash` solo se escribe cuando se pasa explícitamente (no None).
        Así un re-score no pisa el hash existente.
        """

    @abstractmethod
    def update_embedding(self, profile_id: str, vec: list[float]) -> None: ...

    @abstractmethod
    def get(self, profile_id: str) -> Profile | None: ...

    @abstractmethod
    def get_by_username(self, username: str) -> Profile | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Profile | None: ...

    @abstractmethod
    def list_all(self) -> list[Profile]: ...

    @abstractmethod
    def set_reset_token(self, profile_id: str, token: str, expires_at: datetime) -> None: ...

    @abstractmethod
    def get_by_reset_token(self, token: str) -> Profile | None: ...

    @abstractmethod
    def clear_reset_token(self, profile_id: str) -> None: ...
