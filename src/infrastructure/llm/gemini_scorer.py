from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.domain.ports.llm_scorer import LlmScorer
from src.domain.value_objects.job_requirements import JobRequirements
from src.domain.value_objects.profile_form import ProfileForm
from src.domain.value_objects.verdict import Verdict
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)


SCORING_PROMPT = """\
You are a strict hiring-match evaluator. Compare the candidate profile against the
extracted job requirements and return a JSON object matching the provided schema.

Scoring rubric (0-100):
- 90-100: strong match. Stack overlap >70%, seniority aligned, no blocking risks.
- 70-89: good match with manageable gaps.
- 50-69: partial match; meaningful risks (language, residency, missing core tech).
- 0-49: poor match.

Rules:
- `strengths`: short bullets like "Stack Python/FastAPI matches". Max 4.
- `risks`: short bullets like "Requires C1 English; profile is B2". Max 4.
  If there are no real risks, return an empty list — do not invent them.
- If a requirements field is null (unknown), DO NOT treat it as a risk — it's just
  missing info. A null `english_level` is NOT a risk.
- Be conservative. Honesty over optimism.

Candidate profile:
{profile_json}

Job requirements:
{requirements_json}
"""


class GeminiScorer(LlmScorer):
    """Implementación de `LlmScorer` sobre google-genai (Gemini).

    Patrón espejo de `GeminiExtractor`: client lazy, retry exponencial,
    fallback neutral sin levantar excepción.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        client: genai.Client | None = None,
    ):
        self._model = model or settings.gemini_model
        self._client = client

    def _ensure_client(self) -> genai.Client:
        if self._client is None:
            if not settings.gemini_api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Create a .env file (see .env.example) "
                    "or export the variable before invoking the scorer."
                )
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def score(self, profile: ProfileForm, requirements: JobRequirements) -> Verdict:
        prompt = SCORING_PROMPT.format(
            profile_json=profile.model_dump_json(indent=2),
            requirements_json=requirements.model_dump_json(indent=2),
        )

        try:
            return self._call_and_validate(prompt)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.info("Verdict validation failed on attempt 1: %s. Retrying.", e)
            repair_prompt = (
                f"{prompt}\n\nPrevious attempt failed validation with:\n{e}\n"
                "Return a corrected JSON object."
            )
            try:
                return self._call_and_validate(repair_prompt)
            except Exception as e2:
                logger.warning("Scoring failed after retry: %s. Returning neutral.", e2)
                return Verdict(score=50, strengths=[], risks=["scoring unavailable"])

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
                response_schema=Verdict,
                temperature=0.1,
            ),
        )

    def _call_and_validate(self, prompt: str) -> Verdict:
        response = self._generate(prompt)
        if isinstance(response.parsed, Verdict):
            return response.parsed
        text = (response.text or "").strip()
        data = json.loads(text)
        return Verdict.model_validate(data)
