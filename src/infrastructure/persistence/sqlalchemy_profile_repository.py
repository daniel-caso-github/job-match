from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.domain.entities.profile import Profile
from src.domain.ports.profile_repository import ProfileRepository
from src.infrastructure.persistence import mappers
from src.infrastructure.persistence.orm_models import ProfileModel


class SqlAlchemyProfileRepository(ProfileRepository):
    def __init__(self, session: Session):
        self._session = session

    def upsert(self, profile_id: str, form_data: dict[str, Any]) -> None:
        # Serializa a JSON-compatible primitive dict (asegura datetime, etc.).
        sanitized = json.loads(json.dumps(form_data, default=str))
        stmt = pg_insert(ProfileModel).values(id=profile_id, form_data=sanitized)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={"form_data": stmt.excluded.form_data},
        )
        self._session.execute(stmt)

    def update_embedding(self, profile_id: str, vec: list[float]) -> None:
        model = self._session.get(ProfileModel, profile_id)
        if model is None:
            raise LookupError(f"Profile {profile_id} not found")
        model.embedding = vec

    def get(self, profile_id: str) -> Profile | None:
        model = self._session.get(ProfileModel, profile_id)
        return mappers.profile_model_to_domain(model) if model else None

    def list_all(self) -> list[Profile]:
        models = self._session.scalars(select(ProfileModel)).all()
        return [mappers.profile_model_to_domain(m) for m in models]
