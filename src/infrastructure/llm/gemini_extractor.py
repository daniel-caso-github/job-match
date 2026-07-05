from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.domain.ports.requirements_extractor import RequirementsExtractor
from src.domain.value_objects.job_requirements import JobRequirements
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """\
You are a strict information extractor for job postings.

Read the job description below and return a JSON object matching the provided schema.

Rules:
- If a field is not explicitly mentioned, return null (or false for booleans whose
  default is false). DO NOT invent values; conservative extraction beats confident
  hallucination.
- `stack`: only list technologies explicitly required or strongly preferred. Lowercase.
  No duplicates.
- `english_level`: only set if a level is mentioned (B2, C1, "fluent" -> C1,
  "native" -> native). If unspecified, return null.
- `requires_eu_residency`: true ONLY if the posting explicitly says residency in
  EU/UK/Schengen is mandatory.
- `remote`: true if 100% remote; false if hybrid/onsite is mandatory; null if unclear.
- `latam_friendly`: true ONLY if it explicitly mentions LATAM, Americas, or
  similar time zones.
- `confidence`: honest 0..1 self-rating on how explicit the posting was.

Job description:
\"\"\"
{raw_text}
\"\"\"
"""


class GeminiExtractor(RequirementsExtractor):
    """Implementación de RequirementsExtractor sobre google-genai (Gemini)."""

    def __init__(
        self,
        *,
        model: str | None = None,
        max_input_chars: int | None = None,
        client: genai.Client | None = None,
    ):
        self._model = model or settings.gemini_model
        self._max_input_chars = max_input_chars or settings.gemini_max_input_chars
        self._client = client  # lazy via _ensure_client()

    def _ensure_client(self) -> genai.Client:
        if self._client is None:
            if not settings.gemini_api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Create a .env file (see .env.example) "
                    "or export the variable before invoking the extractor."
                )
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def extract(self, raw_text: str) -> JobRequirements:
        text = raw_text[: self._max_input_chars]
        prompt = EXTRACTION_PROMPT.format(raw_text=text)
        logger.info("Extrayendo requisitos con Gemini (%d chars)", len(text))

        try:
            result = self._call_and_validate(prompt)
            logger.info(
                "Extracción OK — stack=%s seniority=%s confidence=%.2f",
                result.stack, result.seniority, result.confidence,
            )
            return result
        except (ValidationError, json.JSONDecodeError) as e:
            logger.info("Extraction validation failed on attempt 1: %s. Retrying.", e)
            repair_prompt = (
                f"{prompt}\n\nPrevious attempt failed validation with:\n{e}\n"
                "Return a corrected JSON object."
            )
            try:
                result = self._call_and_validate(repair_prompt)
                logger.info("Extracción OK tras retry — confidence=%.2f", result.confidence)
                return result
            except (ValidationError, json.JSONDecodeError) as e2:
                logger.warning("Extraction failed after retry: %s. Returning empty.", e2)
                return JobRequirements(confidence=0.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _generate(self, prompt: str) -> types.GenerateContentResponse:
        return self._ensure_client().models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JobRequirements,
                temperature=0.1,
            ),
        )

    def _call_and_validate(self, prompt: str) -> JobRequirements:
        response = self._generate(prompt)
        if isinstance(response.parsed, JobRequirements):
            return response.parsed
        text = (response.text or "").strip()
        data = json.loads(text)
        return JobRequirements.model_validate(data)
