from __future__ import annotations

from pydantic import BaseModel, Field


class SkillGapReport(BaseModel):
    """Análisis de encaje entre un perfil y los requisitos de una oferta.

    Salida del [[skill-gap-analyst-node]] (ver LLM Wiki). Consumido por el
    [[resume-pitch-tailorer-node]] para redactar el paquete de postulación.
    """

    met_requirements: list[str] = Field(
        default_factory=list,
        description="Requisitos de la oferta que el candidato cumple.",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Requisitos que el candidato no cumple o cumple parcialmente.",
    )
    notes: str | None = Field(
        default=None,
        description="Guía sobre cómo justificar o suavizar las brechas en la postulación.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Auto-rating del modelo: 0=fallback ante error, 1=análisis explícito.",
    )
