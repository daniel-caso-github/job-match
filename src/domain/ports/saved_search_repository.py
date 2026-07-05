from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.saved_search import SavedSearch


class SavedSearchRepository(ABC):
    """Port de persistencia para búsquedas programadas.

    Convención: los métodos NO commitean. La transacción la maneja el caller.
    """

    @abstractmethod
    def add(self, search: SavedSearch) -> None: ...

    @abstractmethod
    def list_for_profile(
        self, profile_id: str, limit: int = 20
    ) -> list[SavedSearch]: ...

    @abstractmethod
    def get_by_dag_run_id(self, dag_run_id: str) -> SavedSearch | None: ...

    @abstractmethod
    def set_match_count(self, dag_run_id: str, count: int) -> None: ...

    @abstractmethod
    def delete(self, dag_run_id: str) -> None: ...
