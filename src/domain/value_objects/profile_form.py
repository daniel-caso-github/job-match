from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.domain.value_objects.job_requirements import EnglishLevel, Seniority


class TechItem(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    years: float = Field(ge=0, le=40)


class ProfileForm(BaseModel):
    """Formulario del perfil profesional. Body de POST /profile (fase 4)
    y entrada del CLI `score` (fase 3)."""

    id: str = Field(
        min_length=1,
        max_length=64,
        description="slug del perfil, estable (ej. 'daniel-2026').",
    )
    stack: list[TechItem] = Field(default_factory=list)
    seniority: Seniority
    english_level: EnglishLevel
    location: str = Field(description="ISO-3166 alpha-2 o ciudad (ej. 'AR', 'Madrid').")
    willing_to_relocate: bool = False
    modality: Literal["remote", "hybrid", "onsite"] = "remote"
    salary_expectation: str | None = Field(
        default=None, description="texto libre opcional."
    )
    summary: str | None = Field(
        default=None,
        max_length=2000,
        description="resumen profesional. Pieza más fuerte del embedding del perfil.",
    )
