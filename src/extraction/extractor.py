from __future__ import annotations

import json
import logging
import os
from functools import lru_cache

from google import genai
from google.genai import types
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .schema import JobRequirements

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"
MAX_INPUT_CHARS = 12_000

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


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Create a .env file (see .env.example) "
            "or export the variable before invoking the extractor."
        )
    return genai.Client(api_key=api_key)


def extract_requirements(raw_text: str) -> JobRequirements:
    """Extrae requisitos del texto de la oferta.

    - Trunca a MAX_INPUT_CHARS.
    - Reintenta UNA vez con feedback si la primera respuesta no valida.
    - Si falla todo, devuelve JobRequirements() con confidence=0.0 (no levanta).
    """
    text = raw_text[:MAX_INPUT_CHARS]
    prompt = EXTRACTION_PROMPT.format(raw_text=text)

    try:
        return _call_and_validate(prompt)
    except (ValidationError, json.JSONDecodeError) as e:
        logger.info("Extraction validation failed on attempt 1: %s. Retrying.", e)
        repair_prompt = (
            f"{prompt}\n\nPrevious attempt failed validation with:\n{e}\n"
            "Return a corrected JSON object."
        )
        try:
            return _call_and_validate(repair_prompt)
        except (ValidationError, json.JSONDecodeError) as e2:
            logger.warning("Extraction failed after retry: %s. Returning empty.", e2)
            return JobRequirements(confidence=0.0)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _generate(prompt: str) -> types.GenerateContentResponse:
    return _client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JobRequirements,
            temperature=0.1,
        ),
    )


def _call_and_validate(prompt: str) -> JobRequirements:
    response = _generate(prompt)
    if isinstance(response.parsed, JobRequirements):
        return response.parsed
    # Fallback: try to parse .text manually (rare with schema mode).
    text = (response.text or "").strip()
    data = json.loads(text)
    return JobRequirements.model_validate(data)


def _cli() -> None:
    import argparse

    from src.sources.himalayas import HimalayasSource
    from src.sources.remotive import RemotiveSource

    parser = argparse.ArgumentParser(
        description="Pipe a source through the Gemini extractor (Phase 1 + 2)."
    )
    parser.add_argument("--source", choices=["himalayas", "remotive"], required=True)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    src_cls = {"himalayas": HimalayasSource, "remotive": RemotiveSource}[args.source]
    src = src_cls()

    for i, job in enumerate(src.fetch()):
        if i >= args.limit:
            break
        requirements = extract_requirements(job.raw_text)
        out = {
            "title": job.title,
            "company": job.company,
            "url": str(job.url),
            "requirements": requirements.model_dump(mode="json"),
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
