from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Seniority(StrEnum):
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"
    staff = "staff"


class EnglishLevel(StrEnum):
    a1 = "A1"
    a2 = "A2"
    b1 = "B1"
    b2 = "B2"
    c1 = "C1"
    c2 = "C2"
    native = "native"


class JobRequirements(BaseModel):
    """Requisitos extraídos de la descripción de una oferta."""

    stack: list[str] = Field(
        default_factory=list,
        description=(
            "Tecnologías requeridas, normalizadas en lowercase "
            "(ej. ['python', 'fastapi', 'postgres'])."
        ),
    )
    seniority: Seniority | None = Field(
        default=None, description="Nivel pedido. Null si no se menciona."
    )
    english_level: EnglishLevel | None = Field(
        default=None, description="Nivel de inglés requerido. Null si no se menciona."
    )
    requires_eu_residency: bool = Field(
        default=False, description="True solo si exige residir en UE/UK/Schengen."
    )
    remote: bool | None = Field(
        default=None,
        description=(
            "True si 100% remoto. False si presencial/híbrido obligatorio. "
            "Null si no queda claro."
        ),
    )
    latam_friendly: bool | None = Field(
        default=None,
        description="True solo si menciona explícitamente LATAM/Americas/timezones.",
    )
    salary_range: str | None = Field(
        default=None, description="Rango salarial textual si la oferta lo publica."
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Auto-rating del modelo: 0=adivinanza, 1=explícito.",
    )

    @field_validator("stack", mode="after")
    @classmethod
    def normalize_stack(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            k = (item or "").strip().lower()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out
