# Fase 4 · API + Formulario — FastAPI

**Tiempo estimado:** 1 día
**Entregable demostrable:** Swagger en `http://localhost:8000/docs` con los 5 endpoints funcionando contra la BD poblada por la fase 3. Demo: `POST /profile` con un perfil real → `GET /matches` → abrir el top 1 y leer su verdict.

> **Nota de corrección (post-implementación parcial):** el bootstrap de FastAPI ya está hecho (`src/interfaces/api/main.py` + `dependencies.py` + `routers/health.py`). Lo que falta de fase 4 es **solo los routers de negocio**:
> - `src/interfaces/api/routers/profile.py` — `POST /profile`, valida con `ProfileForm` (`src/domain/value_objects/profile_form.py`), usa `ProfileRepositoryDep` + (a fase 3) `EmbedProfileUseCase`.
> - `src/interfaces/api/routers/matches.py` — `GET /matches`, `GET /matches/{job_id}`, usa `MatchRepositoryDep`.
> - `src/interfaces/api/routers/jobs.py` — `POST /jobs/refresh`, encadena `CollectJobsUseCase` + `ExtractJobRequirementsUseCase` + (fase 3) `EmbedJobsUseCase` + `ScoreProfileUseCase` en background.
> - Cada router se registra con `app.include_router(...)` en `main.py`.
> - DI: usar los `Annotated[..., Depends(...)]` aliases ya creados en `dependencies.py` (`SessionDep`, `JobRepositoryDep`, etc.); agregar `ProfileFormDep` para validar bodies.
>
> El código que sigue en este doc usa el patrón viejo (función `get_engine()`, `text()` en handlers). Al implementar, **traducir a use cases + ports** según el bootstrap actual.

---

## 1. Objetivo

Exponer el pipeline como API HTTP:
- **Captura del perfil** (el formulario es el JSON body de `POST /profile`; la UI puede ser cualquiera — usaremos Swagger para la demo).
- **Consulta de matches** ya computados por la fase 3.
- **Refresh manual** del pipeline (útil cuando no se quiere esperar 12h).

**Sin autenticación.** Uso personal, binding a `127.0.0.1` (documentado en el README). Si en algún momento se publica, se añade un API key middleware — fuera de alcance.

---

## 2. Schema del formulario — `ProfileForm`

Archivo: `src/profile/form.py`

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

from src.extraction.schema import Seniority, EnglishLevel


class TechItem(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    years: float = Field(ge=0, le=40)


class ProfileForm(BaseModel):
    id: str = Field(min_length=1, max_length=64, description="slug del perfil. Stable.")
    stack: list[TechItem] = Field(default_factory=list)
    seniority: Seniority
    english_level: EnglishLevel
    location: str = Field(description="ISO-3166 alpha-2 o ciudad. Ej: 'AR', 'Madrid'.")
    willing_to_relocate: bool = False
    modality: Literal["remote", "hybrid", "onsite"] = "remote"
    salary_expectation: str | None = Field(
        None, description="texto libre, opcional. Ej: '$70k-$90k USD'."
    )
    summary: str | None = Field(
        None, max_length=2000,
        description="texto libre que enriquece el embedding (resumen profesional).",
    )
```

**Notas:**
- `id` es **provisto por el cliente** (slug estable; ej: `daniel-2026`). Permite re-postear `/profile` para actualizar sin generar perfiles huérfanos.
- `seniority` y `english_level` comparten enum con `JobRequirements` → comparación campo a campo sin convertir.
- `summary` es la pieza más fuerte del embedding del perfil: que el usuario lo rellene siempre.

---

## 3. Endpoints

Archivo: `src/api/main.py`

```python
from __future__ import annotations
import os
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.extraction.schema import JobRequirements
from src.matching import pipeline as matching_pipeline
from src.matching.embedder import embed, profile_text_for_embedding
from src.profile.form import ProfileForm
from src.storage import pgvector_io as store
from src.storage.database import SessionLocal, engine
from src.storage.models import Profile

app = FastAPI(
    title="Job Match Pipeline",
    description="Recolección + extracción + scoring de ofertas vs. perfil. Uso personal.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # local; restringir si se publica
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_session() -> Session:
    """FastAPI dependency: yields a Session and ensures cleanup.

    The Session is opened per-request and closed on response.
    Endpoints commit explicitly when they perform writes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/health")
def health(session: SessionDep) -> dict:
    db_ok = True
    try:
        session.execute(select(1))
    except Exception:
        db_ok = False
    gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
    return {"status": "ok" if (db_ok and gemini_ok) else "degraded",
            "db": db_ok, "gemini_key_present": gemini_ok}


@app.post("/profile", status_code=status.HTTP_201_CREATED)
def upsert_profile_endpoint(
    form: ProfileForm, session: SessionDep, bg: BackgroundTasks
) -> dict:
    store.upsert_profile(session, form.id, form.model_dump(mode="json"))
    vec = embed(profile_text_for_embedding(form))
    store.upsert_profile_embedding(session, form.id, vec)
    session.commit()
    # Scoring corre en background; abre su propio session_scope.
    bg.add_task(matching_pipeline.score_profile_against_corpus, form)
    return {"profile_id": form.id, "matching": "scheduled"}


@app.get("/matches")
def list_matches(
    session: SessionDep, profile_id: str, limit: int = 20
) -> dict:
    if limit < 1 or limit > 100:
        raise HTTPException(400, "limit must be between 1 and 100")
    rows = store.top_matches_for_profile(session, profile_id, limit=limit)
    return {
        "profile_id": profile_id,
        "count": len(rows),
        "matches": [
            {
                "job_id": m.job_id,
                "title": j.title,
                "company": j.company,
                "url": j.url,
                "source": j.source,
                "llm_score": m.llm_score,
                "semantic_score": round(m.semantic_score, 3) if m.semantic_score else None,
                "verdict": m.verdict,
            }
            for m, j in rows
        ],
        "source_attribution": "Jobs via Himalayas (himalayas.app) and Remotive (remotive.com)",
    }


@app.get("/matches/{job_id}")
def match_detail(session: SessionDep, job_id: str, profile_id: str) -> dict:
    from src.storage.models import Job, Match
    stmt = (
        select(Match, Job)
        .join(Job, Match.job_id == Job.id)
        .where(Match.profile_id == profile_id, Match.job_id == job_id)
    )
    row = session.execute(stmt).first()
    if row is None:
        raise HTTPException(404, "match not found")
    m, j = row
    return {
        "job_id": j.id,
        "title": j.title,
        "company": j.company,
        "url": j.url,
        "source": j.source,
        "llm_score": m.llm_score,
        "semantic_score": round(m.semantic_score, 3) if m.semantic_score else None,
        "verdict": m.verdict,
        "requirements": j.requirements,
        "raw_text": j.raw_text,           # útil para que el usuario verifique
        "scored_at": m.scored_at.isoformat() if m.scored_at else None,
    }


@app.post("/jobs/refresh", status_code=status.HTTP_202_ACCEPTED)
def refresh_jobs(bg: BackgroundTasks) -> dict:
    """Dispara una corrida manual del pipeline completo (además del schedule de 12h)."""
    from src.extraction.extractor import extract_requirements
    from src.matching import pipeline as mp
    from src.sources.himalayas import HimalayasSource
    from src.sources.remotive import RemotiveSource
    from src.storage.database import session_scope

    def _run():
        # 1) recolectar + upsert
        with session_scope() as session:
            for src_cls in (HimalayasSource, RemotiveSource):
                for job in src_cls().fetch():
                    store.upsert_job(session, job)
        # 2) extraer requirements faltantes
        with session_scope() as session:
            for job in store.list_jobs_without_requirements(session, limit=100):
                req = extract_requirements(job.raw_text)
                store.update_job_requirements(session, job.id, req)
        # 3) embeddings faltantes
        mp.embed_pending_jobs()
        # 4) re-scorear todos los perfiles activos
        with session_scope() as session:
            profiles = session.scalars(select(Profile)).all()
        for p in profiles:
            form = ProfileForm.model_validate(p.form_data)
            mp.score_profile_against_corpus(form)

    bg.add_task(_run)
    return {"status": "scheduled"}
```

**Decisiones:**
- `BackgroundTasks` (FastAPI nativo) en vez de Celery/RQ — sobra para uso personal. La task corre en el mismo proceso del servidor; si se reinicia uvicorn a mitad, no se reanuda, pero como hay schedule cada 12h y todo es idempotente, no es problema.
- `/jobs/refresh` devuelve `202 Accepted` inmediato; el progreso se ve en logs y en `/matches` cuando aparezcan resultados.
- El `source_attribution` en `/matches` cumple el requisito legal de las fuentes.

---

## 4. Responses (ejemplos)

### `GET /matches?profile_id=daniel-2026&limit=2`

```json
{
  "profile_id": "daniel-2026",
  "count": 2,
  "matches": [
    {
      "job_id": "a3f1c92ef0",
      "title": "Senior Backend Engineer (Python)",
      "company": "Acme",
      "url": "https://himalayas.app/jobs/acme-senior-backend",
      "source": "himalayas",
      "llm_score": 92,
      "semantic_score": 0.812,
      "verdict": {
        "score": 92,
        "strengths": [
          "Stack Python/FastAPI matches profile",
          "Seniority aligned (senior)",
          "Remote LATAM-friendly"
        ],
        "risks": [
          "Requires C1 English; profile declared B2"
        ]
      }
    },
    {
      "job_id": "8b22d10ee1",
      "title": "Backend Developer",
      "company": "Beta Corp",
      "url": "https://remotive.com/remote-jobs/backend/beta-corp-backend",
      "source": "remotive",
      "llm_score": 78,
      "semantic_score": 0.741,
      "verdict": {
        "score": 78,
        "strengths": ["Python + Postgres match"],
        "risks": ["Stack heavy on Django, profile is FastAPI"]
      }
    }
  ],
  "source_attribution": "Jobs via Himalayas (himalayas.app) and Remotive (remotive.com)"
}
```

### `GET /matches/a3f1c92ef0?profile_id=daniel-2026`

```json
{
  "job_id": "a3f1c92ef0",
  "title": "Senior Backend Engineer (Python)",
  "company": "Acme",
  "url": "https://himalayas.app/jobs/acme-senior-backend",
  "source": "himalayas",
  "llm_score": 92,
  "semantic_score": 0.812,
  "verdict": { "score": 92, "strengths": ["..."], "risks": ["..."] },
  "requirements": {
    "stack": ["python", "fastapi", "postgres"],
    "seniority": "senior",
    "english_level": "C1",
    "requires_eu_residency": false,
    "remote": true,
    "latam_friendly": true,
    "salary_range": "$90k-$130k USD",
    "confidence": 0.9
  },
  "raw_text": "We are looking for a senior backend engineer ... (full text)",
  "scored_at": "2026-06-28T10:14:22.301000+00:00"
}
```

### `POST /profile` (request body)

```json
{
  "id": "daniel-2026",
  "stack": [
    {"name": "Python", "years": 8},
    {"name": "FastAPI", "years": 3},
    {"name": "Postgres", "years": 6}
  ],
  "seniority": "senior",
  "english_level": "B2",
  "location": "AR",
  "willing_to_relocate": false,
  "modality": "remote",
  "salary_expectation": "$80k-$110k USD",
  "summary": "Backend engineer, 8 años, foco en APIs, integraciones y pipelines de datos. Buscando rol remoto LATAM-friendly."
}
```

Response: `201 { "profile_id": "daniel-2026", "matching": "scheduled" }`.

---

## 5. Tests

Archivo: `tests/test_api.py`

```python
import pytest
from httpx import AsyncClient, ASGITransport

from src.api.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/health")
    assert r.status_code == 200
    assert "status" in r.json()


@pytest.mark.asyncio
async def test_post_profile_creates(monkeypatch):
    # Engine + matching mockeados; foco en contract de la API.
    from src.api import main as mod
    monkeypatch.setattr(mod.store, "upsert_profile", lambda *a, **k: None)
    monkeypatch.setattr(mod.store, "upsert_profile_embedding", lambda *a, **k: None)
    monkeypatch.setattr(
        mod.matching_pipeline, "score_profile_against_corpus", lambda *a, **k: 0
    )
    monkeypatch.setattr(mod, "get_engine", lambda: object())
    monkeypatch.setattr(mod, "embed", lambda *_: [0.0] * 384)
    monkeypatch.setattr(mod, "profile_text_for_embedding", lambda *_: "x")

    body = {
        "id": "test", "stack": [{"name": "Python", "years": 5}],
        "seniority": "senior", "english_level": "B2",
        "location": "AR", "modality": "remote",
        "summary": "backend"
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/profile", json=body)
    assert r.status_code == 201
    assert r.json()["profile_id"] == "test"


@pytest.mark.asyncio
async def test_post_profile_rejects_invalid_seniority():
    body = {"id": "t", "stack": [], "seniority": "expert",
            "english_level": "B2", "location": "AR", "modality": "remote"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/profile", json=body)
    assert r.status_code == 422
```

Test de `/matches` requiere BD real → integración (con la misma estrategia de testcontainers que fase 3).

---

## 6. Cómo correr el servidor

(El comando se documenta también en `phase-6-readme-demo.md` para el README final.)

```bash
# Desarrollo
export DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/jobmatch
export GEMINI_API_KEY=...
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000

# Demo del Swagger
open http://127.0.0.1:8000/docs
```

En docker-compose (fase 5), el servicio `api` corre `uvicorn src.api.main:app --host 0.0.0.0 --port 8000` y se expone como `127.0.0.1:8000` en el host.

---

## 7. Criterios de aceptación

- [ ] Swagger en `/docs` lista los 5 endpoints.
- [ ] `POST /profile` con body válido → 201 + dispara matching en background.
- [ ] `POST /profile` con seniority/english_level inválido → 422.
- [ ] `GET /matches?profile_id=...` devuelve la lista ordenada por `llm_score DESC` + `source_attribution`.
- [ ] `GET /matches/{job_id}` devuelve `requirements` + `raw_text` para que el usuario verifique.
- [ ] `POST /jobs/refresh` devuelve 202 y, al cabo de unos minutos, hay matches nuevos en BD.
- [ ] `GET /health` reporta `db` y `gemini_key_present`.
- [ ] Tests `tests/test_api.py` pasan.

---

## 8. Lo que NO se hace en esta fase

- **UI/frontend** del formulario. Swagger basta.
- **Autenticación**. Bindeamos a `127.0.0.1` y documentamos.
- **Paginación cursor-based** en `/matches`. `limit` simple alcanza.
- **WebSockets / streaming** del progreso del refresh. El usuario re-pide `/matches` y ya.
