from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.value_objects.profile_form import ProfileForm


class Profile(BaseModel):
    """Perfil persistido. `id` es el UUID surrogate generado por la BD;
    `form` es el formulario reconstruido desde las columnas normalizadas
    (profiles + profile_skills + skills).
    """

    id: str
    form: ProfileForm
    embedding: list[float] | None = None
    updated_at: datetime | None = None
    password_hash: str | None = Field(default=None, exclude=True, repr=False)
