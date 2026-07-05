from __future__ import annotations

import json
import logging
import time

from google import genai
from google.genai import types
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.domain.entities.job import Job
from src.domain.ports.llm_scorer import LlmScorer
from src.domain.value_objects.profile_form import ProfileForm
from src.domain.value_objects.verdict import Verdict
from src.infrastructure.config import settings
from src.infrastructure.metrics import gemini_request_duration, gemini_requests_total, llm_score_histogram

logger = logging.getLogger(__name__)


SCORING_PROMPT = """\
You are a strict hiring-match evaluator. You see (1) the candidate profile,
(2) the actual job posting text, and (3) the requirements extracted from it.

Return a JSON object matching the provided schema.

Scoring rubric (0-100):
- 90-100: strong match. Stack overlap >70%, seniority aligned, no blocking risks.
- 70-89: good match with manageable gaps.
- 50-69: partial match; meaningful risks (language, residency, missing core tech).
- 0-49: poor match.
- If `requirements.stack` is empty AND the candidate has a technical profile,
  the role is likely non-engineering (support, sales, ops, etc.). Score 0-30
  unless the job text itself proves the role is technical.

Rules:
- `strengths`: max 4 bullets. EACH strength MUST cite something the job
  actually requires (visible in `requirements` or in the job text). Do NOT
  list profile attributes that the job does not require. If `requirements.stack`
  is empty, you CANNOT cite the candidate's tech stack as a strength.
- `risks`: max 4 bullets. If no real risks, return []. Do not invent.
- If a requirements field is null (unknown), DO NOT treat it as a risk OR a
  strength — it is missing info, not evidence.
- Be conservative. Honesty over optimism.

Job title: {title}

Job posting (first 2000 chars):
\"\"\"
{raw_text_excerpt}
\"\"\"

Candidate profile:
{profile_json}

Extracted job requirements:
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

    def score(self, profile: ProfileForm, job: Job) -> Verdict:
        prompt = SCORING_PROMPT.format(
            title=job.title,
            raw_text_excerpt=(job.raw_text or "")[:2000],
            profile_json=profile.model_dump_json(indent=2),
            requirements_json=job.requirements.model_dump_json(indent=2),
        )
        logger.info("Scoring con Gemini: profile=%s job=%s [%s]", profile.username, job.id, job.title)

        t0 = time.perf_counter()
        try:
            verdict = self._call_and_validate(prompt)
            gemini_requests_total.labels(type="score", status="success").inc()
            llm_score_histogram.observe(verdict.score)
            logger.info(
                "Score OK: profile=%s job=%s score=%d strengths=%d risks=%d",
                profile.username, job.id, verdict.score, len(verdict.strengths), len(verdict.risks),
            )
            return verdict
        except (ValidationError, json.JSONDecodeError) as e:
            logger.info("Verdict validation failed on attempt 1: %s. Retrying.", e)
            gemini_requests_total.labels(type="score", status="retry").inc()
            repair_prompt = (
                f"{prompt}\n\nPrevious attempt failed validation with:\n{e}\n"
                "Return a corrected JSON object."
            )
            try:
                verdict = self._call_and_validate(repair_prompt)
                llm_score_histogram.observe(verdict.score)
                return verdict
            except Exception as e2:
                logger.warning("Scoring failed after retry: %s. Returning neutral.", e2)
                gemini_requests_total.labels(type="score", status="failed").inc()
                return Verdict(score=50, strengths=[], risks=["scoring unavailable"])
        finally:
            gemini_request_duration.labels(type="score").observe(time.perf_counter() - t0)

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
