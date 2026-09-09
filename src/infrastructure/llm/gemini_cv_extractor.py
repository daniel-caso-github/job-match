from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.domain.ports.cv_extractor import CvExtractor
from src.domain.value_objects.cv_extraction import CvExtraction
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1"

CV_PROMPT = """\
You are a strict information extractor for CVs / résumés.

Read the attached PDF and return a JSON object matching the provided schema.

Rules:
- If a field is not explicitly present or clearly inferable, return null (or an
  empty list for list fields). DO NOT invent values; conservative extraction
  beats confident hallucination.
- `stack`: technologies the candidate has actually used, each with your best
  estimate of `years` of experience with it (0 if unclear but mentioned).
  Lowercase names. No duplicates.
- `seniority`: infer from total years of experience and role titles
  (junior/mid/senior/lead/staff). Null if you cannot tell.
- `english_level`: only set if the CV states or clearly evidences a level
  (e.g. written entirely in fluent English with no other signal is NOT enough
  to claim C1/native — only set it if explicitly stated).
- `target_roles`: job titles the candidate is aiming for, from an explicit
  "objective"/summary section, or the most recent role title if no objective
  is stated.
- `years_of_experience`: total professional experience in years, estimated
  from the work history dates.
- `confidence`: honest 0..1 self-rating on how explicit/complete the CV was.

CV (PDF attached).
"""


class GeminiCvExtractor(CvExtractor):
    """Implementación de `CvExtractor` sobre google-genai (Gemini), multimodal.

    Mismo patrón que `GeminiExtractor`: client lazy, retry exponencial con
    feedback de validación, y fallback de baja confianza sin levantar
    excepción ante fallo total.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        max_pdf_bytes: int | None = None,
        client: genai.Client | None = None,
    ):
        self._model = model or settings.gemini_model_cv
        self._max_pdf_bytes = max_pdf_bytes or settings.cv_max_pdf_bytes
        self._client = client  # lazy via _ensure_client()

    def _ensure_client(self) -> genai.Client:
        if self._client is None:
            if not settings.gemini_api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Create a .env file (see .env.example) "
                    "or export the variable before invoking the CV extractor."
                )
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def extract(self, pdf_bytes: bytes) -> CvExtraction:
        if not pdf_bytes or len(pdf_bytes) > self._max_pdf_bytes:
            logger.warning(
                "CV descartado: tamaño inválido (%d bytes, máximo %d)",
                len(pdf_bytes or b""), self._max_pdf_bytes,
            )
            return CvExtraction(confidence=0.0)

        logger.info("Extrayendo CV con Gemini (%d bytes)", len(pdf_bytes))
        try:
            result = self._call_and_validate(CV_PROMPT, pdf_bytes)
            logger.info(
                "Extracción de CV OK — stack=%d target_roles=%s confidence=%.2f",
                len(result.stack), result.target_roles, result.confidence,
            )
            return result
        except (ValidationError, json.JSONDecodeError) as e:
            logger.info("CV extraction validation failed on attempt 1: %s. Retrying.", e)
            repair_prompt = (
                f"{CV_PROMPT}\n\nPrevious attempt failed validation with:\n{e}\n"
                "Return a corrected JSON object."
            )
            try:
                result = self._call_and_validate(repair_prompt, pdf_bytes)
                logger.info("Extracción de CV OK tras retry — confidence=%.2f", result.confidence)
                return result
            except (ValidationError, json.JSONDecodeError) as e2:
                logger.warning("CV extraction failed after retry: %s. Returning empty.", e2)
                return CvExtraction(confidence=0.0)
        except Exception as e:
            logger.warning("CV extraction failed with unexpected error: %s. Returning empty.", e)
            return CvExtraction(confidence=0.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _generate(self, prompt: str, pdf_bytes: bytes) -> types.GenerateContentResponse:
        return self._ensure_client().models.generate_content(
            model=self._model,
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CvExtraction,
                temperature=0.1,
            ),
        )

    def _call_and_validate(self, prompt: str, pdf_bytes: bytes) -> CvExtraction:
        response = self._generate(prompt, pdf_bytes)
        if isinstance(response.parsed, CvExtraction):
            return response.parsed
        text = (response.text or "").strip()
        data = json.loads(text)
        return CvExtraction.model_validate(data)
