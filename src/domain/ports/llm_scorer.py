from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.value_objects.job_requirements import JobRequirements
from src.domain.value_objects.profile_form import ProfileForm
from src.domain.value_objects.verdict import Verdict


class LlmScorer(ABC):
    """Port: produce un `Verdict` comparando perfil ↔ requisitos.

    Implementación por defecto en `src/infrastructure/llm/gemini_scorer.py`.
    El contrato exige NO levantar excepciones por fallos de validación o de red:
    devolver un Verdict neutral (`score=50`, `risks=["scoring unavailable"]`)
    para que el pipeline siga avanzando.
    """

    @abstractmethod
    def score(self, profile: ProfileForm, requirements: JobRequirements) -> Verdict: ...
