from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.entities.saved_search import SavedSearch
from src.domain.ports.saved_search_repository import SavedSearchRepository
from src.infrastructure.persistence import mappers
from src.infrastructure.persistence.orm_models import SavedSearchModel


class SqlAlchemySavedSearchRepository(SavedSearchRepository):
    """Implementación SQLAlchemy del `SavedSearchRepository` port.

    No commitea: la transacción la maneja el caller.
    """

    def __init__(self, session: Session):
        self._session = session

    def add(self, search: SavedSearch) -> None:
        self._session.add(
            SavedSearchModel(
                dag_run_id=search.dag_run_id,
                profile_id=search.profile_id,
                filters=search.filters,
                run_at=search.run_at,
            )
        )

    def get_by_dag_run_id(self, dag_run_id: str) -> SavedSearch | None:
        m = self._session.get(SavedSearchModel, dag_run_id)
        return mappers.saved_search_model_to_domain(m) if m is not None else None

    def set_match_count(self, dag_run_id: str, count: int) -> None:
        m = self._session.get(SavedSearchModel, dag_run_id)
        if m is not None:
            m.match_count = count

    def delete(self, dag_run_id: str) -> None:
        m = self._session.get(SavedSearchModel, dag_run_id)
        if m is not None:
            self._session.delete(m)

    def list_for_profile(self, profile_id: str, limit: int = 20) -> list[SavedSearch]:
        stmt = (
            select(SavedSearchModel)
            .where(SavedSearchModel.profile_id == profile_id)
            .order_by(SavedSearchModel.created_at.desc())
            .limit(limit)
        )
        return [
            mappers.saved_search_model_to_domain(m) for m in self._session.scalars(stmt)
        ]
