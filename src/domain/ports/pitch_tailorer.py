from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.job import Job
from src.domain.value_objects.profile_form import ProfileForm
from src.domain.value_objects.skill_gap_report import SkillGapReport


class PitchTailorer(ABC):
    """Port: redacta bullets de CV + carta de presentación a partir de un `SkillGapReport`.

    Implementación por defecto en `src/infrastructure/llm/gemini_pitch_tailorer.py`.
    El contrato exige NO levantar excepciones por fallos de validación o de red:
    devolver `([], "")` (bullets vacíos, carta vacía) para que el caller siga
    funcionando.

    Devuelve `(resume_bullets, cover_letter)` en vez de un value object propio:
    ambos campos ya viven, sin envoltorio adicional, en `PostulationPackage`.
    """

    @abstractmethod
    def tailor(
        self, profile: ProfileForm, job: Job, skill_gap: SkillGapReport
    ) -> tuple[list[str], str]: ...
