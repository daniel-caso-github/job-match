from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.job import Job
from src.domain.value_objects.profile_form import ProfileForm
from src.domain.value_objects.skill_gap_report import SkillGapReport


class SkillGapAnalyzer(ABC):
    """Port: produce un `SkillGapReport` comparando perfil ↔ requisitos de una oferta.

    Implementación por defecto en `src/infrastructure/llm/gemini_skill_gap_analyzer.py`.
    El contrato exige NO levantar excepciones por fallos de validación o de red:
    devolver `SkillGapReport(confidence=0.0)` para que el caller siga funcionando.
    """

    @abstractmethod
    def analyze(self, profile: ProfileForm, job: Job) -> SkillGapReport: ...
