# Fase 2 · Extracción estructurada — Gemini + Pydantic

**Tiempo estimado:** 1 día
**Entregable demostrable:** dado un `RawJob`, devuelve un `JobRequirements` validado por Pydantic. Sobre 10 ofertas reales, ≥9 validaciones deben pasar al primer intento (y las que fallen recuperarse con 1 reintento).

> **Notas de corrección (post-implementación)**:
> - **SDK**: el doc planeaba `google-generativeai` (legacy). Implementado con `google-genai>=1.0` (nuevo SDK oficial), que acepta `response_schema=JobRequirements` directamente y devuelve la instancia parseada en `response.parsed` — código más simple, una sola línea de validación.
> - **Modelo**: el doc decía `gemini-1.5-flash`. Usamos **`gemini-2.5-flash`** (la generación 2.0 ya fue retirada del catálogo público en producción, con error `404 NOT_FOUND` al invocarla; 2.5-flash es la flash estable actual y mantiene el tier gratuito).
> - **CLI**: la CLI vive en `src/interfaces/cli/extract.py` (no `src/extraction/extractor.py::_cli`). Workflow real: `/run-source` recolecta a BD → `/extract` procesa las pendientes.
> - **Arquitectura (Clean Arch)**: la función `extract_requirements` se reemplazó por la clase `GeminiExtractor(RequirementsExtractor)` en `src/infrastructure/llm/gemini_extractor.py`. El port `RequirementsExtractor` (ABC) vive en `src/domain/ports/`. El use case `ExtractJobRequirementsUseCase` (`src/application/use_cases/`) consume el port + `JobRepository`.
> - **JobRequirements** ahora está en `src/domain/value_objects/job_requirements.py` (no en `src/extraction/schema.py`).

---

## 1. Objetivo

Convertir descripciones libres de empleo (`RawJob.raw_text`) en datos **estructurados, tipados y validados**, listos para usar en el scoring de fase 3. Esta es la pieza donde brilla la combinación *backend con tipos* + *LLM*.

Por qué importa:
- El scoring con LLM (fase 3) es más confiable comparando *campo a campo* que comparando texto libre vs. texto libre.
- Permite filtros tipo SQL: `WHERE requirements->>'english_level' = 'C1'`.
- Garantiza que el output del LLM es procesable mecánicamente, no "casi siempre".

---

## 2. Esquema `JobRequirements` (Pydantic)

Archivo: `src/extraction/schema.py`

```python
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class Seniority(str, Enum):
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"
    staff = "staff"


class EnglishLevel(str, Enum):
    a1 = "A1"; a2 = "A2"
    b1 = "B1"; b2 = "B2"
    c1 = "C1"; c2 = "C2"
    native = "native"


class JobRequirements(BaseModel):
    """Requisitos extraídos de la descripción de la oferta."""

    stack: list[str] = Field(
        default_factory=list,
        description="Tecnologías requeridas, normalizadas en lowercase (ej. ['python', 'fastapi', 'postgres']).",
    )
    seniority: Seniority | None = Field(
        None,
        description="Nivel pedido. Null si no se menciona.",
    )
    english_level: EnglishLevel | None = Field(
        None,
        description="Nivel de inglés requerido o pedido en la descripción. Null si no se menciona.",
    )
    requires_eu_residency: bool = Field(
        False,
        description="True solo si la oferta exige residir en UE/UK/Schengen.",
    )
    remote: bool | None = Field(
        None,
        description="True si es 100% remoto. False si es presencial/híbrido obligatorio. Null si no queda claro.",
    )
    latam_friendly: bool | None = Field(
        None,
        description="True si menciona explícitamente que acepta LATAM o time zone Americas.",
    )
    salary_range: str | None = Field(
        None,
        description="Rango salarial textual si la oferta lo publica (ej. '$80k-$120k USD'). Null si no aparece.",
    )
    confidence: float = Field(
        0.0,
        ge=0.0, le=1.0,
        description="Auto-evaluación del modelo sobre qué tan clara fue la extracción. 0=adivinanza, 1=explícito.",
    )

    @field_validator("stack", mode="after")
    @classmethod
    def normalize_stack(cls, v: list[str]) -> list[str]:
        # lowercase, sin duplicados, sin vacíos
        seen, out = set(), []
        for item in v:
            k = (item or "").strip().lower()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out
```

**Decisiones:**
- `english_level` es un `Enum`: el LLM debe elegir un valor del set conocido. Sin enum, devolvería variantes ("upper-intermediate", "fluent") que rompen el matching.
- `requires_eu_residency` por defecto `False` (más común). El extractor lo pone `True` solo con señal clara.
- `confidence` es **auto-reportado por Gemini** (en el prompt se le pide). Útil para flaggear ofertas dudosas en el ranking.
- `stack` se normaliza a lowercase + dedup en el validator — el LLM puede devolver "Python" y "python".

---

## 3. Extractor

Archivo: `src/extraction/extractor.py`

### 3.1 Prompt

```python
EXTRACTION_PROMPT = """\
You are a strict information extractor for job postings.

Read the job description below and return ONLY a JSON object matching this schema:

{schema}

Rules:
- If a field is not explicitly mentioned, return null (or false for booleans whose default is false).
  DO NOT invent values. Conservative extraction is preferred over confident hallucination.
- For `stack`: only list technologies explicitly required or strongly preferred. Lowercase. No duplicates.
- For `english_level`: only set if a level is mentioned (B2, C1, "fluent" -> C1, "native" -> native).
- For `requires_eu_residency`: true ONLY if the posting explicitly says residency in EU/UK/Schengen is mandatory.
- For `remote`: true if 100% remote; false if hybrid/onsite is mandatory; null if unclear.
- For `latam_friendly`: true ONLY if it explicitly mentions LATAM, Americas, or similar time zones.
- `confidence`: your honest 0..1 self-rating on how explicit the posting was.

Job description:
\"\"\"
{raw_text}
\"\"\"

Return only the JSON. No prose, no markdown fences.
"""
```

### 3.2 Función principal

```python
import json
import logging
from functools import lru_cache

import google.generativeai as genai
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .schema import JobRequirements

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 12_000        # ~3k tokens. Truncar evita quotas y costos.
MODEL = "gemini-1.5-flash"      # tier gratuito generoso


@lru_cache(maxsize=1)
def _model():
    return genai.GenerativeModel(MODEL)


def extract_requirements(raw_text: str) -> JobRequirements:
    """Extrae requisitos del texto de la oferta. Devuelve JobRequirements validado.

    Estrategia:
      1) llamar a Gemini con response_mime_type=application/json + schema.
      2) intentar parsear y validar.
      3) si falla, reintentar UNA vez con el error como feedback.
      4) si vuelve a fallar, devolver JobRequirements() vacío con confidence=0.0
         y log de WARNING. NO levantar excepción — el pipeline debe avanzar.
    """
    text = raw_text[:MAX_INPUT_CHARS]
    schema_json = JobRequirements.model_json_schema()
    prompt = EXTRACTION_PROMPT.format(
        schema=json.dumps(schema_json, indent=2),
        raw_text=text,
    )

    # --- Intento 1 ---
    try:
        return _call_and_validate(prompt)
    except (ValidationError, json.JSONDecodeError) as e:
        logger.info("Extraction validation failed on attempt 1: %s. Retrying with feedback.", e)
        repair_prompt = prompt + f"\n\nPrevious attempt failed validation with:\n{e}\nReturn corrected JSON."
        try:
            return _call_and_validate(repair_prompt)
        except (ValidationError, json.JSONDecodeError) as e2:
            logger.warning("Extraction failed after retry: %s. Returning empty requirements.", e2)
            return JobRequirements(confidence=0.0)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(Exception),  # Gemini SDK lanza varias
    reraise=True,
)
def _call_gemini(prompt: str) -> str:
    response = _model().generate_content(
        prompt,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.1,
        },
    )
    return response.text


def _call_and_validate(prompt: str) -> JobRequirements:
    raw = _call_gemini(prompt)
    data = json.loads(raw)
    return JobRequirements.model_validate(data)
```

### 3.3 Cache por `job_id` (idempotencia + ahorro de cuota)

La cache vive en la BD: el DAG (fase 5) llama a `extract_requirements` **solo si `jobs.requirements IS NULL`** para ese `job_id`. No hace falta cache en memoria — la BD ya es la fuente de verdad.

Si se quiere acelerar tests/desarrollo local, se puede añadir un `@lru_cache(maxsize=512)` sobre `extract_requirements`, pero **no se usa en producción** (porque `extract_requirements` no recibe `job_id`, solo texto, y dos jobs distintos podrían tener texto idéntico raramente — la cache real es a nivel `job_id` en la BD).

---

## 4. Guardrails

| Guardrail | Implementación |
|---|---|
| Input demasiado largo | Truncar `raw_text[:MAX_INPUT_CHARS]` antes del prompt. |
| Modelo devuelve markdown ``` ```json ``` | `response_mime_type="application/json"` lo evita; si igualmente aparece, hacer strip en `_call_and_validate`. |
| JSON inválido | `JSONDecodeError` → reintento con feedback. |
| Campos inválidos (enum equivocado, tipos) | `ValidationError` Pydantic → reintento con feedback. |
| 429 / 503 de Gemini | `tenacity` retry exponencial (2s → 8s → 30s). |
| Alucinación de campos | Prompt explícito + `temperature=0.1` + Pydantic recorta extras (modelos Pydantic ignoran fields no declarados por defecto). |
| Hallar `confidence=0` tras reintento | Pipeline continúa, pero el job queda flaggeado: en el LLM scorer (fase 3) se puede degradar su `llm_score`. |

---

## 5. Tests

Archivo: `tests/test_extractor.py`

Estrategia: **golden fixtures** — 3 ofertas reales (ya guardadas en `tests/fixtures/`) con su `JobRequirements` esperado. Las llamadas a Gemini se mockean.

```python
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.extraction.extractor import extract_requirements
from src.extraction.schema import JobRequirements, Seniority, EnglishLevel

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_gemini():
    with patch("src.extraction.extractor._model") as m:
        instance = MagicMock()
        m.return_value = instance
        yield instance


def _fake_response(text: str):
    resp = MagicMock()
    resp.text = text
    return resp


def test_extract_happy_path(mock_gemini):
    expected = {
        "stack": ["Python", "FastAPI", "PostgreSQL"],
        "seniority": "senior",
        "english_level": "C1",
        "requires_eu_residency": False,
        "remote": True,
        "latam_friendly": True,
        "salary_range": "$80k-$120k USD",
        "confidence": 0.9,
    }
    mock_gemini.generate_content.return_value = _fake_response(json.dumps(expected))

    raw = (FIXTURES / "job_acme_backend.txt").read_text()
    result = extract_requirements(raw)

    assert isinstance(result, JobRequirements)
    assert result.seniority == Seniority.senior
    assert result.english_level == EnglishLevel.c1
    assert "python" in result.stack and "fastapi" in result.stack
    # validator normalizó a lowercase
    assert "Python" not in result.stack


def test_extract_invalid_then_repaired(mock_gemini):
    bad = json.dumps({"seniority": "expert"})  # enum inválido
    good = json.dumps({"stack": ["go"], "confidence": 0.6})
    mock_gemini.generate_content.side_effect = [_fake_response(bad), _fake_response(good)]

    result = extract_requirements("...descripcion...")
    assert result.stack == ["go"]
    assert mock_gemini.generate_content.call_count == 2


def test_extract_fails_returns_empty(mock_gemini):
    mock_gemini.generate_content.return_value = _fake_response("not json at all")
    result = extract_requirements("...")
    assert isinstance(result, JobRequirements)
    assert result.confidence == 0.0
    assert result.stack == []


def test_stack_normalized():
    req = JobRequirements(stack=["Python", "python", "FastAPI", ""])
    assert req.stack == ["python", "fastapi"]
```

**Fixtures a crear (3 ofertas reales):**
1. `job_acme_backend.txt` — oferta clara, requiere C1, stack Python/FastAPI, remoto LATAM.
2. `job_eu_only.txt` — oferta que exige residencia EU, sin nivel inglés explícito.
3. `job_ambiguous.txt` — descripción larga sin nivel ni seniority claros (caso límite).

Las 3 deben generarse copiando descripciones reales (sin atribución a empresa específica si es para repo público; en tests locales no importa).

---

## 6. Cuota de Gemini — cálculo de costos

Asumiendo `gemini-1.5-flash`, tier gratuito (al momento del diseño):
- 15 RPM, 1,500 req/día.
- Pipeline corre cada 12h → 2 corridas/día.
- Por corrida: ~50 ofertas nuevas pasan el filtro semántico → ~50 llamadas de extracción + ~50 de scoring (fase 3) = 100 calls.
- Total: 200 calls/día → **bien dentro del límite gratuito** (13% del cupo diario).

Con margen para reintentos. Si se aumenta el throughput, considerar `gemini-1.5-flash-8b` (más barato y suficiente para esta tarea).

---

## 7. Dependencias añadidas en esta fase

A `requirements.txt`:
```
google-generativeai>=0.7
```

(Pydantic y tenacity ya están de la fase 1.)

---

## 8. Criterios de aceptación

- [ ] `src/extraction/schema.py` define `JobRequirements`, `Seniority`, `EnglishLevel`.
- [ ] `src/extraction/extractor.py` define `extract_requirements(raw_text) -> JobRequirements`.
- [ ] Validator normaliza `stack` (lowercase + dedup).
- [ ] Reintento con feedback ante `ValidationError` o `JSONDecodeError`.
- [ ] No levanta excepciones al fallo total (devuelve `JobRequirements()` con `confidence=0`).
- [ ] Tests `tests/test_extractor.py` pasan sin red.
- [ ] Smoke test manual: correr `extract_requirements` sobre las 10 ofertas traídas en fase 1 → ≥9 con `confidence > 0`.

---

## 9. Lo que NO se hace en esta fase

- **Persistir** `requirements` en `jobs.requirements` → fase 5 (DAG task `extraer_requisitos` llama a `storage.update_job_requirements`).
- **Scoring** del perfil contra los requirements → fase 3 (`llm_scorer.py`).
- **Endpoint para re-extraer** una oferta individual → fase 4 si se decide exponerlo; opcional.
