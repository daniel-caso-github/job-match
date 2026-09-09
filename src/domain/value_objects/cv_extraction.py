from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.profile_form import TechItem


class CvExtraction(BaseModel):
    """Extracción propuesta a partir de un CV en PDF (vía `CvExtractor`).

    No es un `Profile` ni se persiste directo: el usuario la revisa/edita en el
    frontend y confirma el alta/edición a través del flujo normal de
    `ProfileForm` (POST/PUT /profile). Mismo contrato de fallo que
    `JobRequirements`: ante error de extracción, `confidence=0.0` y el resto de
    los campos en sus defaults — nunca se levanta una excepción.
    """

    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=254)
    stack: list[TechItem] = Field(default_factory=list)
    seniority: Seniority | None = Field(
        default=None, description="Nivel inferido del CV. Null si no queda claro."
    )
    english_level: EnglishLevel | None = Field(
        default=None, description="Nivel de inglés inferido del CV. Null si no se menciona."
    )
    location: str | None = Field(default=None, max_length=120)
    summary: str | None = Field(
        default=None,
        max_length=2000,
        description="Resumen profesional propuesto, listo para revisar en el ProfileForm.",
    )
    target_roles: list[str] = Field(
        default_factory=list, description="Roles objetivo mencionados o inferidos del CV."
    )
    years_of_experience: float | None = Field(default=None, ge=0, le=60)
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Auto-rating del modelo: 0=extracción fallida/vacía, 1=explícito.",
    )

    @field_validator("target_roles", mode="after")
    @classmethod
    def normalize_target_roles(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            k = (item or "").strip()
            if k and k.lower() not in seen:
                seen.add(k.lower())
                out.append(k)
        return out
