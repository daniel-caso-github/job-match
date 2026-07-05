from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.domain.value_objects.job_requirements import EnglishLevel, Seniority

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TechItem(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    years: float = Field(ge=0, le=40)

    @field_validator("name", mode="after")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        normalized = v.strip().lower()
        if not normalized:
            raise ValueError("name cannot be blank")
        return normalized


class ProfileForm(BaseModel):
    """Formulario del perfil profesional. Body de POST /profile (fase 4)
    y entrada del CLI `score` (fase 3)."""

    username: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
        description="username único del perfil (ej. 'daniel-2026').",
    )
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=254)
    stack: list[TechItem] = Field(default_factory=list)
    seniority: Seniority
    english_level: EnglishLevel
    location: str = Field(description="ISO-3166 alpha-2 o ciudad (ej. 'AR', 'Madrid').")
    willing_to_relocate: bool = False
    modality: Literal["remote", "hybrid", "onsite"] = "remote"
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str = Field(default="USD", min_length=3, max_length=3)
    summary: str | None = Field(
        default=None,
        max_length=2000,
        description="resumen profesional. Pieza más fuerte del embedding del perfil.",
    )

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, v: object) -> object:
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: object) -> object:
        if v is None:
            return None
        if not isinstance(v, str):
            return v
        v = v.strip().lower()
        if v and not _EMAIL_RE.match(v):
            raise ValueError("email inválido")
        return v or None

    @field_validator("stack", mode="after")
    @classmethod
    def dedup_stack(cls, v: list[TechItem]) -> list[TechItem]:
        seen: set[str] = set()
        out: list[TechItem] = []
        for item in v:
            if item.name not in seen:
                seen.add(item.name)
                out.append(item)
        return out

    @field_validator("salary_currency", mode="after")
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def salary_range_is_ordered(self) -> ProfileForm:
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min cannot exceed salary_max")
        return self
