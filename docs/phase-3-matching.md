# Fase 3 · Matching — Embeddings + scoring semántico + LLM scoring

**Tiempo estimado:** 1 día
**Entregable demostrable:** dado un perfil + un set de ofertas en la BD, devuelve el top K matches ordenado por `llm_score` con `verdict.strengths` y `verdict.risks` explicados. Esta es la fase que justifica el proyecto: la IA toma decisiones útiles.

---

## 1. Objetivo

Implementar las **dos capas de scoring** y su orquestación local:

1. **Semántico** (barato, sobre todas las ofertas) — descarta lo irrelevante.
2. **LLM** (caro, sobre el top K filtrado) — produce score + explicación.

Más la capa de persistencia (`pgvector_io`) que ambas necesitan.

---

## 2. Embedder

Archivo: `src/matching/embedder.py`

Usa `sentence-transformers` con `BAAI/bge-small-en-v1.5`:
- 384 dimensiones (cuadra con `VECTOR(384)` del schema).
- Modelo pequeño (~133MB), corre en CPU.
- Estado del arte para inglés en su tier de tamaño.
- Importante: bge requiere normalización L2 + un *prefix de query* en lado consulta. Para nuestro caso (similitud documento ↔ documento), usamos solo el modelo base sin prefix.

```python
from __future__ import annotations
from functools import lru_cache
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed(text: str | list[str]) -> np.ndarray:
    """Devuelve embedding(s) normalizado(s) L2.

    - Si recibe str: shape (384,)
    - Si recibe list[str]: shape (N, 384)
    """
    is_single = isinstance(text, str)
    inputs = [text] if is_single else text
    vecs = _model().encode(inputs, normalize_embeddings=True, convert_to_numpy=True)
    return vecs[0] if is_single else vecs


def job_text_for_embedding(job: "RawJob", requirements: "JobRequirements | None") -> str:
    """Texto a embeber para una oferta. Concatena lo más informativo y trunca."""
    parts = [job.title or "", job.company or ""]
    if requirements and requirements.stack:
        parts.append("Stack: " + ", ".join(requirements.stack))
    if requirements and requirements.seniority:
        parts.append(f"Seniority: {requirements.seniority.value}")
    parts.append(job.raw_text[:1500])
    return "\n".join(p for p in parts if p)


def profile_text_for_embedding(form: "ProfileForm") -> str:
    """Texto a embeber para el perfil. Espejo del de jobs."""
    parts = [
        "Stack: " + ", ".join(f"{t.name} ({t.years}y)" for t in form.stack),
        f"Seniority: {form.seniority.value}",
        f"English: {form.english_level.value}",
        f"Location: {form.location}",
        f"Modality: {form.modality}",
    ]
    if form.summary:
        parts.append(form.summary)
    return "\n".join(parts)
```

**Por qué normalización L2 en el embedder y no en la query SQL:**
`pgvector` soporta `<=>` (cosine distance) directamente. Pero precomputar embeddings normalizados permite usar `<#>` (negative inner product) — el mismo resultado, más rápido. Mantenemos `<=>` por legibilidad; el rendimiento es suficiente.

---

## 3. Scoring semántico

Archivo: `src/matching/semantic.py`

Aprovecha `pgvector` con índice HNSW. La query es una sola.

```python
from __future__ import annotations
import numpy as np
from sqlalchemy import text
from sqlalchemy.engine import Engine

SEMANTIC_THRESHOLD = 0.65   # similitud coseno mínima (0..1) para pasar al LLM
TOP_K_FOR_LLM = 30          # cuántas ofertas pasan al LLM scorer por corrida


def semantic_top_k(
    engine: Engine,
    profile_embedding: np.ndarray,
    *,
    k: int = TOP_K_FOR_LLM,
    threshold: float = SEMANTIC_THRESHOLD,
    only_unscored_for_profile: str | None = None,
) -> list[tuple[str, float]]:
    """Devuelve [(job_id, semantic_score), ...] ordenado por score desc.

    - `semantic_score` se computa como 1 - cosine_distance (rango 0..1).
    - Filtra ofertas con embedding NULL y las que ya están scoreadas para el perfil
      (si `only_unscored_for_profile` se pasa).
    """
    vec = profile_embedding.tolist()

    sql = """
        SELECT
            j.id,
            1 - (j.embedding <=> CAST(:vec AS vector)) AS semantic_score
        FROM jobs j
        WHERE j.embedding IS NOT NULL
        {filter_already_scored}
        ORDER BY j.embedding <=> CAST(:vec AS vector)
        LIMIT :k
    """
    if only_unscored_for_profile:
        filter_clause = """
          AND NOT EXISTS (
            SELECT 1 FROM matches m
             WHERE m.job_id = j.id
               AND m.profile_id = :profile_id
          )
        """
        sql = sql.format(filter_already_scored=filter_clause)
        params = {"vec": vec, "k": k, "profile_id": only_unscored_for_profile}
    else:
        sql = sql.format(filter_already_scored="")
        params = {"vec": vec, "k": k}

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).all()

    return [(r.id, float(r.semantic_score)) for r in rows if r.semantic_score >= threshold]
```

**Notas:**
- `<=>` es cosine distance (0..2). Como los vectores están normalizados L2, la distancia coseno entre dos vectores positivos queda en 0..1; convertimos a similitud con `1 - distance`.
- `CAST(:vec AS vector)` es necesario porque sqlalchemy no tipea vectores automáticamente.
- `only_unscored_for_profile` permite que el DAG (fase 5) procese solo las nuevas — clave para idempotencia.

---

## 4. LLM scorer

Archivo: `src/matching/llm_scorer.py`

### 4.1 Schema `Verdict`

```python
from __future__ import annotations
from pydantic import BaseModel, Field


class Verdict(BaseModel):
    score: int = Field(ge=0, le=100, description="0-100, ajuste perfil↔requisitos")
    strengths: list[str] = Field(
        default_factory=list,
        description="Razones por las que el perfil encaja. Máx 4 ítems concisos.",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Riesgos o gaps. Máx 4 ítems concisos. Ej: 'piden C1, perfil B2'.",
    )
```

### 4.2 Prompt

```python
SCORING_PROMPT = """\
You are a strict hiring-match evaluator. Compare a candidate profile against extracted
job requirements and return ONLY a JSON object with the schema below.

Schema:
{schema}

Scoring rubric:
- 90-100: strong match. Stack overlap >70%, seniority aligned, no blocking risks.
- 70-89: good match with manageable gaps.
- 50-69: partial match; meaningful risks (language, residency, missing core tech).
- 0-49: poor match.

Rules:
- `strengths`: short bullets like "Stack Python/FastAPI matches". Max 4.
- `risks`: short bullets like "Requires C1 English; profile is B2". Max 4.
  If there are no real risks, return an empty list — do not invent them.
- If a job field is null (unknown), DO NOT treat it as a risk — it's just missing info.
- Be conservative. A null english_level is NOT a risk.

Candidate profile:
{profile_json}

Job requirements:
{requirements_json}

Return only the JSON. No prose, no markdown fences.
"""
```

### 4.3 Función

```python
import json, logging
import google.generativeai as genai
from functools import lru_cache
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from src.extraction.schema import JobRequirements
from src.profile.form import ProfileForm
from .schema import Verdict  # mismo archivo

logger = logging.getLogger(__name__)
MODEL = "gemini-1.5-flash"


@lru_cache(maxsize=1)
def _model():
    return genai.GenerativeModel(MODEL)


def score(profile: ProfileForm, requirements: JobRequirements) -> Verdict:
    prompt = SCORING_PROMPT.format(
        schema=json.dumps(Verdict.model_json_schema(), indent=2),
        profile_json=profile.model_dump_json(indent=2),
        requirements_json=requirements.model_dump_json(indent=2),
    )

    try:
        return _call_and_validate(prompt)
    except (ValidationError, json.JSONDecodeError) as e:
        logger.info("Verdict validation failed: %s. Retrying.", e)
        try:
            return _call_and_validate(prompt + f"\n\nPrevious failed:\n{e}\nReturn corrected JSON.")
        except Exception as e2:
            logger.warning("Verdict failed after retry: %s. Returning neutral.", e2)
            return Verdict(score=50, strengths=[], risks=["scoring unavailable"])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30), reraise=True)
def _call_and_validate(prompt: str) -> Verdict:
    response = _model().generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json", "temperature": 0.1},
    )
    data = json.loads(response.text)
    return Verdict.model_validate(data)
```

---

## 5. Orquestación local del matching

Una función que une las piezas. La llama el DAG (fase 5) y también `POST /jobs/refresh` (fase 4).

Archivo: `src/matching/__init__.py` o `src/matching/pipeline.py`:

```python
from sqlalchemy.engine import Engine

from src.extraction.schema import JobRequirements
from src.profile.form import ProfileForm
from src.storage import pgvector_io as store
from .embedder import embed, profile_text_for_embedding, job_text_for_embedding
from .semantic import semantic_top_k
from .llm_scorer import score


def score_profile_against_corpus(engine: Engine, profile: ProfileForm) -> int:
    """Para un perfil dado, calcula matches sobre todo el corpus.

    Pasos:
      1) embed del perfil (o reusar si ya está en profiles).
      2) filtro semántico → top K ids.
      3) por cada id: carga RawJob + JobRequirements desde la BD,
         llama al LLM scorer, persiste el match.

    Devuelve cuántos matches se computaron en esta corrida.
    """
    profile_text = profile_text_for_embedding(profile)
    profile_vec = embed(profile_text)
    store.upsert_profile_embedding(engine, profile.id, profile_vec)

    top = semantic_top_k(engine, profile_vec, only_unscored_for_profile=profile.id)

    n = 0
    for job_id, sem_score in top:
        job, req = store.get_job_with_requirements(engine, job_id)
        if req is None:
            # Aún no extraído. El DAG lo procesará en la próxima corrida.
            continue
        verdict = score(profile, req)
        store.upsert_match(
            engine,
            profile_id=profile.id,
            job_id=job_id,
            semantic_score=sem_score,
            llm_score=verdict.score,
            verdict=verdict,
        )
        n += 1
    return n


def embed_pending_jobs(engine: Engine, batch_size: int = 32) -> int:
    """Embedde las ofertas que aún no tienen embedding. Idempotente."""
    pending = store.list_jobs_without_embedding(engine, limit=batch_size * 4)
    if not pending:
        return 0
    texts = [job_text_for_embedding(j, r) for j, r in pending]
    vecs = embed(texts)
    for (job, _), vec in zip(pending, vecs):
        store.upsert_job_embedding(engine, job.id, vec)
    return len(pending)
```

---

## 6. Storage — `pgvector_io`

Archivo: `src/storage/pgvector_io.py`

Funciones expuestas (firma + comportamiento). Uso de SQLAlchemy Core + `psycopg2/psycopg` (driver decidido en fase 5 por `requirements.txt`).

```python
from __future__ import annotations
import json
import numpy as np
from typing import Iterable
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.sources.base import RawJob
from src.extraction.schema import JobRequirements
from src.matching.llm_scorer import Verdict   # ajustar import si Verdict vive en otro módulo


# ---------- Jobs ----------

def upsert_job(engine: Engine, job: RawJob) -> None:
    """Inserta una oferta; si el id ya existe, no toca requirements ni embedding."""
    sql = text("""
        INSERT INTO jobs (id, source, url, title, company, raw_text, posted_at, country, remote)
        VALUES (:id, :source, :url, :title, :company, :raw_text, :posted_at, :country, :remote)
        ON CONFLICT (id) DO UPDATE SET
            -- solo refrescar metadatos baratos; preservar requirements/embedding ya calculados
            title    = EXCLUDED.title,
            company  = EXCLUDED.company,
            raw_text = EXCLUDED.raw_text
    """)
    with engine.begin() as conn:
        conn.execute(sql, job.model_dump(mode="json"))


def update_job_requirements(engine: Engine, job_id: str, req: JobRequirements) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE jobs SET requirements = CAST(:r AS jsonb) WHERE id = :id"),
            {"r": req.model_dump_json(), "id": job_id},
        )


def upsert_job_embedding(engine: Engine, job_id: str, vec: np.ndarray) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE jobs SET embedding = CAST(:v AS vector) WHERE id = :id"),
            {"v": vec.tolist(), "id": job_id},
        )


def list_jobs_without_requirements(engine: Engine, limit: int = 100) -> list[RawJob]:
    sql = text("SELECT * FROM jobs WHERE requirements IS NULL ORDER BY fetched_at DESC LIMIT :n")
    with engine.connect() as conn:
        rows = conn.execute(sql, {"n": limit}).mappings().all()
    return [RawJob.model_validate(dict(r)) for r in rows]


def list_jobs_without_embedding(engine: Engine, limit: int = 100) -> list[tuple[RawJob, JobRequirements | None]]:
    sql = text("""
        SELECT id, source, url, title, company, raw_text, posted_at, country, remote, requirements
        FROM jobs
        WHERE embedding IS NULL
        ORDER BY fetched_at DESC
        LIMIT :n
    """)
    out = []
    with engine.connect() as conn:
        rows = conn.execute(sql, {"n": limit}).mappings().all()
    for r in rows:
        d = dict(r)
        req_raw = d.pop("requirements", None)
        req = JobRequirements.model_validate(req_raw) if req_raw else None
        out.append((RawJob.model_validate(d), req))
    return out


def get_job_with_requirements(engine: Engine, job_id: str) -> tuple[RawJob, JobRequirements | None]:
    sql = text("SELECT * FROM jobs WHERE id = :id")
    with engine.connect() as conn:
        row = conn.execute(sql, {"id": job_id}).mappings().one()
    d = dict(row)
    req_raw = d.pop("requirements", None)
    req = JobRequirements.model_validate(req_raw) if req_raw else None
    return RawJob.model_validate(d), req


# ---------- Profiles ----------

def upsert_profile(engine: Engine, profile_id: str, form_data: dict) -> None:
    sql = text("""
        INSERT INTO profiles (id, form_data) VALUES (:id, CAST(:f AS jsonb))
        ON CONFLICT (id) DO UPDATE
        SET form_data = EXCLUDED.form_data, updated_at = now()
    """)
    with engine.begin() as conn:
        conn.execute(sql, {"id": profile_id, "f": json.dumps(form_data)})


def upsert_profile_embedding(engine: Engine, profile_id: str, vec: np.ndarray) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE profiles SET embedding = CAST(:v AS vector) WHERE id = :id"),
            {"v": vec.tolist(), "id": profile_id},
        )


# ---------- Matches ----------

def upsert_match(
    engine: Engine,
    *,
    profile_id: str,
    job_id: str,
    semantic_score: float,
    llm_score: int,
    verdict: Verdict,
) -> None:
    sql = text("""
        INSERT INTO matches (profile_id, job_id, semantic_score, llm_score, verdict)
        VALUES (:p, :j, :s, :l, CAST(:v AS jsonb))
        ON CONFLICT (profile_id, job_id) DO UPDATE SET
            semantic_score = EXCLUDED.semantic_score,
            llm_score      = EXCLUDED.llm_score,
            verdict        = EXCLUDED.verdict,
            scored_at      = now()
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "p": profile_id, "j": job_id,
            "s": semantic_score, "l": llm_score,
            "v": verdict.model_dump_json(),
        })


def top_matches_for_profile(engine: Engine, profile_id: str, limit: int = 20) -> list[dict]:
    """Lista de matches con metadatos del job para mostrar en /matches (fase 4)."""
    sql = text("""
        SELECT m.job_id, m.semantic_score, m.llm_score, m.verdict,
               j.title, j.company, j.url, j.source
        FROM matches m
        JOIN jobs j ON j.id = m.job_id
        WHERE m.profile_id = :p
        ORDER BY m.llm_score DESC
        LIMIT :n
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"p": profile_id, "n": limit}).mappings().all()
    return [dict(r) for r in rows]
```

---

## 7. Tests

Archivo: `tests/test_matching.py`

Estrategia: unidad para el embedder (real, es CPU y rápido) + scorer mockeado + storage contra una BD Postgres efímera (testcontainers o BD docker-compose dedicada al test).

```python
import numpy as np
from unittest.mock import patch, MagicMock

from src.matching.embedder import embed
from src.matching.llm_scorer import score, Verdict
from src.extraction.schema import JobRequirements, Seniority, EnglishLevel
from src.profile.form import ProfileForm   # ver fase 4


def test_embedder_shape_and_norm():
    v = embed("Senior Python backend engineer with FastAPI")
    assert v.shape == (384,)
    assert abs(np.linalg.norm(v) - 1.0) < 1e-3  # L2 normalized


def test_embedder_similarity_relative_order():
    a = embed("Senior Python backend engineer")
    b = embed("Python developer with FastAPI")
    c = embed("Marketing copywriter for fashion brand")
    sim_ab = float(np.dot(a, b))
    sim_ac = float(np.dot(a, c))
    assert sim_ab > sim_ac   # backend ↔ backend más cercano que backend ↔ marketing


def test_scorer_happy_path():
    profile = _fake_profile()
    req = JobRequirements(
        stack=["python", "fastapi"], seniority=Seniority.senior,
        english_level=EnglishLevel.b2, remote=True,
    )
    fake_verdict = {"score": 88, "strengths": ["Stack matches"], "risks": []}
    with patch("src.matching.llm_scorer._model") as m:
        m.return_value.generate_content.return_value = MagicMock(text='{"score": 88, "strengths": ["Stack matches"], "risks": []}')
        v = score(profile, req)
    assert isinstance(v, Verdict)
    assert v.score == 88


def test_scorer_invalid_then_neutral():
    profile = _fake_profile()
    req = JobRequirements()
    with patch("src.matching.llm_scorer._model") as m:
        m.return_value.generate_content.return_value = MagicMock(text='not json')
        v = score(profile, req)
    assert v.score == 50  # fallback neutral


def _fake_profile() -> ProfileForm:
    # Mínimo necesario; el detalle del schema se define en fase 4.
    return ProfileForm.model_validate({
        "id": "test",
        "stack": [{"name": "Python", "years": 5}],
        "seniority": "senior",
        "english_level": "B2",
        "location": "AR",
        "modality": "remote",
        "summary": "Backend engineer focused on APIs",
    })
```

Para tests de storage: usar `testcontainers-python` con `pgvector/pgvector:pg16`, ejecutar `init.sql` (de fase 5) en el setup, y ejecutar las funciones reales.

---

## 8. Dependencias añadidas

A `requirements.txt`:
```
sentence-transformers>=2.7
numpy>=1.26
sqlalchemy>=2.0
psycopg[binary]>=3.1
pgvector>=0.2.5   # helpers opcionales (registrar tipos en SQLAlchemy)
```

---

## 9. Criterios de aceptación

- [ ] `embed("...")` devuelve vector (384,) normalizado L2.
- [ ] `semantic_top_k` devuelve solo ofertas con `semantic_score ≥ SEMANTIC_THRESHOLD`.
- [ ] `score(profile, requirements)` devuelve `Verdict` válido con score 0-100.
- [ ] `score_profile_against_corpus` procesa N ofertas e inserta N filas en `matches`.
- [ ] Re-ejecutar `score_profile_against_corpus` no duplica (upsert por `(profile_id, job_id)`).
- [ ] Tests pasan; el de similitud relativa (backend > marketing) demuestra que el embedder discrimina.
- [ ] Smoke manual: con 10 ofertas reales + 1 perfil, `top_matches_for_profile` devuelve 5 con `llm_score > 0` y `verdict.risks` poblado donde aplique.

---

## 10. Lo que NO se hace en esta fase

- **Endpoints HTTP** que llamen a `score_profile_against_corpus` → fase 4 (`POST /profile` lo dispara al final).
- **DAG** que orqueste `embed_pending_jobs` + scoring por todos los perfiles activos → fase 5.
- **UI** o frontend del formulario → out of scope (uso vía Swagger).
