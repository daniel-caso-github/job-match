from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.value_objects.job_requirements import EnglishLevel, Seniority

_ENGLISH_ORDER: list[EnglishLevel] = [
    EnglishLevel.a1,
    EnglishLevel.a2,
    EnglishLevel.b1,
    EnglishLevel.b2,
    EnglishLevel.c1,
    EnglishLevel.c2,
    EnglishLevel.native,
]


def english_levels_up_to(max_level: EnglishLevel) -> list[EnglishLevel]:
    return _ENGLISH_ORDER[: _ENGLISH_ORDER.index(max_level) + 1]


class MatchFilters(BaseModel):
    """Filtros opcionales para el listado de matches de un perfil."""

    min_score: int | None = Field(default=None, ge=0, le=100)
    sources: list[str] = Field(default_factory=list, max_length=50)
    keywords: list[str] = Field(default_factory=list, max_length=50)
    stack: list[str] = Field(default_factory=list, max_length=50)
    seniorities: list[Seniority] = Field(default_factory=list)
    english_levels: list[EnglishLevel] = Field(default_factory=list)
    remote_only: bool = False
    latam_only: bool = False
    exclude_eu: bool = False
    with_salary: bool = False
    countries: list[str] = Field(default_factory=list, max_length=50)
