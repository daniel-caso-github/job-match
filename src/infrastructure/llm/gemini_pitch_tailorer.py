from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.domain.entities.job import Job
from src.domain.ports.pitch_tailorer import PitchTailorer
from src.domain.value_objects.profile_form import ProfileForm
from src.domain.value_objects.skill_gap_report import SkillGapReport
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1"

# Nota (ver wiki/rules/resume-pitch-tailorer-node.md): el proyecto todavía no tiene
# un mapeo real fuente -> tono ("formal" vs. "freelance/entregables"); ninguna de
# las 7 fuentes actuales es un agregador tipo Upwork. Por eso el prompt usa siempre
# un tono profesional/formal y solo pasa `job.source` como contexto informativo,
# en vez de ramificar el tono por fuente (queda TBD hasta que exista una fuente
# que lo justifique).
PITCH_PROMPT = """\
You are a career coach writing application materials for a candidate applying to a
specific job.

Return a JSON object matching the provided schema.

Rules:
- `resume_bullets`: 3-6 CV bullets reordered/rewritten to foreground the experience
  most relevant to THIS job's requirements. Each bullet must be grounded in the
  candidate's actual profile — do not invent experience.
- `cover_letter`: a concise cover letter draft (3-5 short paragraphs, plain text,
  no markdown) addressed to the hiring team. Reference concrete requirements from
  the job and how the candidate meets them; where there is a gap (see the skill
  gap analysis), briefly acknowledge or reframe it without lying.
- Professional, confident tone.

Job title: {title}
Job source: {source}

Job posting (first 2000 chars):
\"\"\"
{raw_text_excerpt}
\"\"\"

Candidate profile:
{profile_json}

Skill gap analysis:
{skill_gap_json}
"""


class _TailoredPitch(BaseModel):
    """Schema interno para la respuesta estructurada de Gemini.

    No es un value object de dominio: `PitchTailorer.tailor` devuelve sus campos
    ya desempaquetados en una tupla (ver `domain/ports/pitch_tailorer.py`).
    """

    resume_bullets: list[str] = Field(default_factory=list)
    cover_letter: str = ""


class GeminiPitchTailorer(PitchTailorer):
    """Implementación de `PitchTailorer` sobre google-genai (Gemini).

    Patrón espejo de `GeminiScorer`: client lazy, retry exponencial con
    feedback de validación, fallback seguro sin levantar excepción.
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
                    "or export the variable before invoking the pitch tailorer."
                )
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def tailor(
        self, profile: ProfileForm, job: Job, skill_gap: SkillGapReport
    ) -> tuple[list[str], str]:
        prompt = PITCH_PROMPT.format(
            title=job.title,
            source=job.source,
            raw_text_excerpt=(job.raw_text or "")[:2000],
            profile_json=profile.model_dump_json(indent=2),
            skill_gap_json=skill_gap.model_dump_json(indent=2),
        )
        logger.info("Redactando pitch: profile=%s job=%s [%s]", profile.username, job.id, job.title)

        try:
            pitch = self._call_and_validate(prompt)
            logger.info(
                "Pitch OK: profile=%s job=%s bullets=%d",
                profile.username, job.id, len(pitch.resume_bullets),
            )
            return pitch.resume_bullets, pitch.cover_letter
        except (ValidationError, json.JSONDecodeError) as e:
            logger.info("Pitch validation failed on attempt 1: %s. Retrying.", e)
            repair_prompt = (
                f"{prompt}\n\nPrevious attempt failed validation with:\n{e}\n"
                "Return a corrected JSON object."
            )
            try:
                pitch = self._call_and_validate(repair_prompt)
                return pitch.resume_bullets, pitch.cover_letter
            except Exception as e2:
                logger.warning("Pitch tailoring failed after retry: %s. Returning empty.", e2)
                return [], ""
        except Exception as e:
            logger.warning("Pitch tailoring failed with unexpected error: %s. Returning empty.", e)
            return [], ""

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
                response_schema=_TailoredPitch,
                temperature=0.2,
            ),
        )

    def _call_and_validate(self, prompt: str) -> _TailoredPitch:
        response = self._generate(prompt)
        if isinstance(response.parsed, _TailoredPitch):
            return response.parsed
        text = (response.text or "").strip()
        data = json.loads(text)
        return _TailoredPitch.model_validate(data)
