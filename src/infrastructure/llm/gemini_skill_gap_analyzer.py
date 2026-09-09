from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.domain.entities.job import Job
from src.domain.ports.skill_gap_analyzer import SkillGapAnalyzer
from src.domain.value_objects.profile_form import ProfileForm
from src.domain.value_objects.skill_gap_report import SkillGapReport
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1"

SKILL_GAP_PROMPT = """\
You are a career coach analyzing how well a candidate profile fits a job's requirements.

Return a JSON object matching the provided schema.

Rules:
- `met_requirements`: concrete requirements from the job (from `requirements` or the
  posting text) that the candidate profile already satisfies. Cite the actual
  requirement, not just a restatement of the candidate's skill.
- `gaps`: concrete requirements the candidate does not satisfy or only partially
  satisfies. Be specific and actionable.
- `notes`: short guidance on how to present these gaps in the application (justify,
  reframe, or omit). Empty string if there is nothing to add.
- Be conservative — do not invent requirements not present in the job text/requirements.
- `confidence`: honest 0..1 self-rating on how explicit the comparison was.

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


class GeminiSkillGapAnalyzer(SkillGapAnalyzer):
    """Implementación de `SkillGapAnalyzer` sobre google-genai (Gemini).

    Patrón espejo de `GeminiScorer`: client lazy, retry exponencial con
    feedback de validación, fallback de baja confianza sin levantar excepción.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        client: genai.Client | None = None,
    ):
        self._model = model or settings.gemini_model_score
        self._client = client

    def _ensure_client(self) -> genai.Client:
        if self._client is None:
            if not settings.gemini_api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Create a .env file (see .env.example) "
                    "or export the variable before invoking the skill gap analyzer."
                )
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def analyze(self, profile: ProfileForm, job: Job) -> SkillGapReport:
        prompt = SKILL_GAP_PROMPT.format(
            title=job.title,
            raw_text_excerpt=(job.raw_text or "")[:2000],
            profile_json=profile.model_dump_json(indent=2),
            requirements_json=job.requirements.model_dump_json(indent=2)
            if job.requirements
            else "null",
        )
        logger.info(
            "Analizando skill gap: profile=%s job=%s [%s]", profile.username, job.id, job.title
        )

        try:
            report = self._call_and_validate(prompt)
            logger.info(
                "Skill gap OK: profile=%s job=%s met=%d gaps=%d confidence=%.2f",
                profile.username, job.id, len(report.met_requirements),
                len(report.gaps), report.confidence,
            )
            return report
        except (ValidationError, json.JSONDecodeError) as e:
            logger.info("Skill gap validation failed on attempt 1: %s. Retrying.", e)
            repair_prompt = (
                f"{prompt}\n\nPrevious attempt failed validation with:\n{e}\n"
                "Return a corrected JSON object."
            )
            try:
                return self._call_and_validate(repair_prompt)
            except Exception as e2:
                logger.warning("Skill gap analysis failed after retry: %s. Returning empty.", e2)
                return SkillGapReport(confidence=0.0)
        except Exception as e:
            logger.warning(
                "Skill gap analysis failed with unexpected error: %s. Returning empty.", e
            )
            return SkillGapReport(confidence=0.0)

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
                response_schema=SkillGapReport,
                temperature=0.1,
            ),
        )

    def _call_and_validate(self, prompt: str) -> SkillGapReport:
        response = self._generate(prompt)
        if isinstance(response.parsed, SkillGapReport):
            return response.parsed
        text = (response.text or "").strip()
        data = json.loads(text)
        return SkillGapReport.model_validate(data)
