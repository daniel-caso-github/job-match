from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.value_objects.job_requirements import JobRequirements


class RequirementsExtractor(ABC):
    """Port: extrae `JobRequirements` a partir del texto libre de una oferta.

    Implementación por defecto en `src/infrastructure/llm/gemini_extractor.py`.
    El contrato exige NO levantar excepciones por fallos de validación: devolver
    `JobRequirements(confidence=0.0)` para que el pipeline siga avanzando.
    """

    @abstractmethod
    def extract(self, raw_text: str) -> JobRequirements: ...
