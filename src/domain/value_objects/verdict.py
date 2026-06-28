from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Verdict(BaseModel):
    """Resultado del LLM scoring de un perfil contra una oferta."""

    score: int = Field(
        ge=0, le=100, description="0-100, ajuste perfil↔requisitos."
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Razones por las que el perfil encaja. Máx 4 ítems concisos.",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Riesgos o gaps. Máx 4 ítems concisos. Lista vacía si no hay.",
    )

    @field_validator("strengths", "risks", mode="after")
    @classmethod
    def cap_to_four(cls, v: list[str]) -> list[str]:
        return [item.strip() for item in v if item and item.strip()][:4]
