from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SavedSearch(BaseModel):
    """Búsqueda programada por un perfil: filtros + corrida de Airflow asociada."""

    dag_run_id: str
    profile_id: str
    filters: dict[str, Any] = Field(default_factory=dict)
    run_at: datetime
    created_at: datetime | None = None
    match_count: int | None = None
