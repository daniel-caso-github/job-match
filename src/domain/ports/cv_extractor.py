from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.value_objects.cv_extraction import CvExtraction


class CvExtractor(ABC):
    """Port: extrae `CvExtraction` a partir de un CV en PDF (multimodal, sin OCR previo).

    Implementación por defecto en `src/infrastructure/llm/gemini_cv_extractor.py`.
    El contrato exige NO levantar excepciones por fallos de validación o de red:
    devolver `CvExtraction(confidence=0.0)` para que el caller siga funcionando
    (nunca un 500 al usuario).
    """

    @abstractmethod
    def extract(self, pdf_bytes: bytes) -> CvExtraction: ...
