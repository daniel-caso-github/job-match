from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Profile(BaseModel):
    """Perfil persistido. `form_data` mantiene el payload del formulario tal cual
    (validado contra ProfileForm en el borde de la API en fase 4).
    """

    id: str
    form_data: dict[str, Any]
    embedding: list[float] | None = None
    updated_at: datetime | None = None
