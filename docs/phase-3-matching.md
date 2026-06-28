# Fase 3 · Matching — Embeddings + scoring semántico + LLM scoring

**Tiempo estimado:** 1 día
**Entregable demostrable:** dado un perfil + un set de ofertas en la BD, devuelve el top K matches ordenado por `llm_score` con `verdict.strengths` y `verdict.risks` explicados. Esta es la fase que justifica el proyecto: la IA toma decisiones útiles.

> **Nota de corrección (post-implementación de fase 2 + Clean Arch):** los paths cambiaron y el patrón se reorganiza:
> - **Ports** a crear en domain: `Embedder` (ABC), `LlmScorer` (ABC). El `MatchRepository` (port) ya está en `src/domain/ports/match_repository.py`.
> - **Implementaciones** en infrastructure:
>   - `src/infrastructure/embedding/sentence_transformers_embedder.py::SentenceTransformersEmbedder(Embedder)`.
>   - `src/infrastructure/llm/gemini_scorer.py::GeminiScorer(LlmScorer)`.
> - **Storage** ya existe: `SqlAlchemyJobRepository`, `SqlAlchemyMatchRepository` en `src/infrastructure/persistence/`. Lo que en este doc llaman `pgvector_io.py` se reparte entre esos repos + funciones de query semántica (las queries de pgvector con `cosine_distance` van en el repo o en un helper si conviene).
> - **Use cases** a crear en application:
>   - `EmbedJobsUseCase(embedder, job_repo)` — lo que el doc llama `embed_pending_jobs`.
>   - `ScoreProfileUseCase(embedder, semantic_search, llm_scorer, match_repo, job_repo, profile_repo)` — lo que el doc llama `score_profile_against_corpus`. (la `semantic_search` puede vivir como método del `JobRepository`).
> - **`Verdict`** (value object) ya declarado en `src/domain/value_objects/verdict.py` (a implementar aquí).
> - El código de §3, §5 y §6 a continuación usa firmas viejas; al implementar, traducir a esta arquitectura.

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
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.storage.models import Job, Match

SEMANTIC_THRESHOLD = 0.65   # similitud coseno mínima (0..1) para pasar al LLM
TOP_K_FOR_LLM = 30          # cuántas ofertas pasan al LLM scorer por corrida


def semantic_top_k(
    session: Session,
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

    Usa el operador `<=>` (cosine distance) de pgvector a través del helper
    `Job.embedding.cosine_distance(...)` que registra `pgvector.sqlalchemy`.
    """
    distance = Job.embedding.cosine_distance(profile_embedding.tolist())

    stmt = (
        select(Job.id, (1 - distance).label("semantic_score"))
        .where(Job.embedding.is_not(None))
        .order_by(distance)
        .limit(k)
    )
    if only_unscored_for_profile:
        already_scored = select(Match.job_id).where(Match.profile_id == only_unscored_for_profile)
        stmt = stmt.where(Job.id.not_in(already_scored))

    rows = session.execute(stmt).all()
    return [(r.id, float(r.semantic_score)) for r in rows if r.semantic_score >= threshold]
```

**Notas:**
- `<=>` es cosine distance (0..2). Como los vectores están normalizados L2, la distancia coseno entre dos vectores positivos queda en 0..1; convertimos a similitud con `1 - distance`.
- `Job.embedding.cosine_distance(vec)` es el helper que `pgvector.sqlalchemy` registra sobre la columna `Vector` — equivale a `embedding <=> vec` pero queda dentro del ORM (sin `text()`).
- `Job.id.not_in(select(Match.job_id).where(...))` evita re-scorear ofertas ya procesadas para el perfil — clave para la idempotencia que el DAG (fase 5) explota.

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
from src.extraction.schema import JobRequirements
from src.profile.form import ProfileForm
from src.storage import pgvector_io as store
from src.storage.database import session_scope
from .embedder import embed, job_text_for_embedding, profile_text_for_embedding
from .llm_scorer import score
from .semantic import semantic_top_k


def score_profile_against_corpus(profile: ProfileForm) -> int:
    """Para un perfil dado, calcula matches sobre todo el corpus.

    Pasos:
      1) embed del perfil + upsert.
      2) filtro semántico → top K ids (excluye los ya scoreados).
      3) por cada job: carga Job ORM (con .requirements ya parseado), llama al
         LLM scorer, upsert del Match.

    Devuelve cuántos matches se computaron en esta corrida.
    Toda la unidad de trabajo en una transacción gestionada por session_scope.
    """
    profile_vec = embed(profile_text_for_embedding(profile))

    n = 0
    with session_scope() as session:
        store.upsert_profile_embedding(session, profile.id, profile_vec)
        top = semantic_top_k(session, profile_vec, only_unscored_for_profile=profile.id)

        for job_id, sem_score in top:
            job = store.get_job(session, job_id)
            if job is None or job.requirements is None:
                # Aún no extraído. El DAG lo procesará en la próxima corrida.
                continue
            req = JobRequirements.model_validate(job.requirements)
            verdict = score(profile, req)
            store.upsert_match(
                session,
                profile_id=profile.id,
                job_id=job_id,
                semantic_score=sem_score,
                llm_score=verdict.score,
                verdict=verdict,
            )
            n += 1
    return n


def embed_pending_jobs(batch_size: int = 32) -> int:
    """Embedde las ofertas que aún no tienen embedding. Idempotente."""
    with session_scope() as session:
        pending = store.list_jobs_without_embedding(session, limit=batch_size * 4)
        if not pending:
            return 0
        texts = [
            job_text_for_embedding(
                j,
                JobRequirements.model_validate(j.requirements) if j.requirements else None,
            )
            for j in pending
        ]
        vecs = embed(texts)
        for job, vec in zip(pending, vecs, strict=True):
            store.upsert_job_embedding(session, job.id, vec)
        return len(pending)
```

---

## 6. Storage — `pgvector_io`

Archivo: `src/storage/pgvector_io.py`

Capa **fina** sobre los modelos ORM (`src/storage/models.py`: `Job`, `Profile`, `Match`). Cero `text()`: todo es `select()` / `insert()` con `on_conflict_do_update`. Las funciones toman un `Session` ya abierto (transacción manejada por el llamador con `session_scope()`).

```python
from __future__ import annotations
from collections.abc import Iterable

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.extraction.schema import JobRequirements
from src.matching.llm_scorer import Verdict   # ajustar import si Verdict vive en otro módulo
from src.sources.base import RawJob
from src.storage.models import Job, Match, Profile


# ---------- Jobs ----------

def upsert_job(session: Session, job: RawJob) -> None:
    """Inserta una oferta; si el id ya existe, preserva requirements/embedding y
    solo refresca title/company/raw_text/url (metadatos baratos)."""
    payload = job.model_dump(mode="json")
    payload["url"] = str(payload["url"])

    stmt = pg_insert(Job).values(**payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "title": stmt.excluded.title,
            "company": stmt.excluded.company,
            "raw_text": stmt.excluded.raw_text,
            "url": stmt.excluded.url,
        },
    )
    session.execute(stmt)


def update_job_requirements(session: Session, job_id: str, req: JobRequirements) -> None:
    job = session.get(Job, job_id)
    if job is None:
        raise LookupError(f"Job {job_id} not found")
    job.requirements = req.model_dump(mode="json")


def upsert_job_embedding(session: Session, job_id: str, vec: np.ndarray) -> None:
    job = session.get(Job, job_id)
    if job is None:
        raise LookupError(f"Job {job_id} not found")
    job.embedding = vec.tolist()


def list_jobs_without_requirements(session: Session, limit: int = 100) -> list[Job]:
    stmt = (
        select(Job)
        .where(Job.requirements.is_(None))
        .order_by(Job.fetched_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def list_jobs_without_embedding(session: Session, limit: int = 100) -> list[Job]:
    stmt = (
        select(Job)
        .where(Job.embedding.is_(None))
        .order_by(Job.fetched_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def get_job(session: Session, job_id: str) -> Job | None:
    return session.get(Job, job_id)


# ---------- Profiles ----------

def upsert_profile(session: Session, profile_id: str, form_data: dict) -> None:
    stmt = pg_insert(Profile).values(id=profile_id, form_data=form_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={"form_data": stmt.excluded.form_data},
    )
    session.execute(stmt)


def upsert_profile_embedding(session: Session, profile_id: str, vec: np.ndarray) -> None:
    profile = session.get(Profile, profile_id)
    if profile is None:
        raise LookupError(f"Profile {profile_id} not found")
    profile.embedding = vec.tolist()


# ---------- Matches ----------

def upsert_match(
    session: Session,
    *,
    profile_id: str,
    job_id: str,
    semantic_score: float,
    llm_score: int,
    verdict: Verdict,
) -> None:
    stmt = pg_insert(Match).values(
        profile_id=profile_id,
        job_id=job_id,
        semantic_score=semantic_score,
        llm_score=llm_score,
        verdict=verdict.model_dump(mode="json"),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["profile_id", "job_id"],
        set_={
            "semantic_score": stmt.excluded.semantic_score,
            "llm_score": stmt.excluded.llm_score,
            "verdict": stmt.excluded.verdict,
            "scored_at": func.now(),
        },
    )
    session.execute(stmt)


def top_matches_for_profile(
    session: Session, profile_id: str, limit: int = 20
) -> list[tuple[Match, Job]]:
    """Matches + Job adjunto para mostrar en /matches (fase 4).

    Devuelve tuplas (Match, Job) — el ORM ya tiene la relación cargada via
    `Match.job` (`back_populates="matches"`), pero hacemos el join explícito
    aquí para que sea una sola query con eager loading.
    """
    stmt = (
        select(Match, Job)
        .join(Job, Match.job_id == Job.id)
        .where(Match.profile_id == profile_id)
        .order_by(Match.llm_score.desc())
        .limit(limit)
    )
    return [(m, j) for m, j in session.execute(stmt).all()]
```

**Notas:**
- `pg_insert(...).on_conflict_do_update(...)` es el equivalente ORM-friendly del `INSERT ... ON CONFLICT DO UPDATE` de Postgres. Mantiene la idempotencia sin perder los `Mapped[]` ni los validadores Pydantic externos.
- `session.get(Job, id)` aprovecha el identity map de SQLAlchemy y evita un round-trip si el objeto ya está en la sesión.
- Para los embeddings, no hace falta `CAST(... AS vector)`: la columna `Vector(384)` ya tipea la asignación. Pasamos `vec.tolist()` (list de floats).
- `func.now()` es el helper de `sqlalchemy.sql.func`, equivalente a `NOW()`. Recordar `from sqlalchemy.sql import func` al usarlo.

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

Para tests de storage: usar `testcontainers-python` con `pgvector/pgvector:pg16`, correr `alembic upgrade head` en el setup, y ejecutar las funciones reales.

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
