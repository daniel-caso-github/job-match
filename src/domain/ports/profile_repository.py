from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.entities.profile import Profile


class ProfileRepository(ABC):
    """Port de persistencia para perfiles."""

    @abstractmethod
    def upsert(self, profile_id: str, form_data: dict[str, Any]) -> None: ...

    @abstractmethod
    def update_embedding(self, profile_id: str, vec: list[float]) -> None: ...

    @abstractmethod
    def get(self, profile_id: str) -> Profile | None: ...

    @abstractmethod
    def list_all(self) -> list[Profile]: ...
