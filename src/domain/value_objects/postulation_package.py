from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.domain.value_objects.skill_gap_report import SkillGapReport

PostulationStatus = Literal["pendiente_aprobacion", "aprobado", "rechazado"]


class PostulationPackage(BaseModel):
    """Paquete completo generado por el squad de postulación para un match.

    Producido por [[skill-gap-analyst-node]] + [[resume-pitch-tailorer-node]] y
    persistido en `matches.postulation_package` (JSONB). El `status` implementa
    [[aprobacion-humana-postulacion]]: nace `pendiente_aprobacion` y solo pasa a
    `aprobado`/`rechazado` vía una acción explícita del usuario.
    """

    skill_gap: SkillGapReport
    resume_bullets: list[str] = Field(default_factory=list)
    cover_letter: str = ""
    status: PostulationStatus = "pendiente_aprobacion"
