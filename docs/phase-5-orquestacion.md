# Fase 5 · Orquestación e infraestructura — Airflow + Docker + Postgres

**Tiempo estimado:** 1 día
**Entregable demostrable:** `docker compose up` levanta Postgres+pgvector, Airflow y la API. El DAG `job_match` corre end-to-end cada 12h (y a demanda), poblando la BD con matches reales.

---

## 1. Objetivo

Unir todas las piezas en un sistema autónomo:
- **Postgres 16 + pgvector** como única fuente de verdad.
- **Airflow** ejecutando el DAG cada 12h.
- **FastAPI** consultable mientras el DAG no corre.

Idempotencia es **requisito duro**: cualquier task del DAG debe poder reintentarse sin duplicar datos ni romper estado.

---

## 2. `init.sql` — migraciones

Archivo: `init.sql` (raíz del repo, montado en el contenedor de Postgres como `docker-entrypoint-initdb.d`).

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    url           TEXT NOT NULL,
    title         TEXT NOT NULL,
    company       TEXT,
    raw_text      TEXT NOT NULL,
    requirements  JSONB,
    embedding     VECTOR(384),
    posted_at     TIMESTAMPTZ,
    country       TEXT,
    remote        BOOLEAN,
    fetched_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS profiles (
    id            TEXT PRIMARY KEY,
    form_data     JSONB NOT NULL,
    embedding     VECTOR(384),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS matches (
    profile_id     TEXT REFERENCES profiles(id) ON DELETE CASCADE,
    job_id         TEXT REFERENCES jobs(id)     ON DELETE CASCADE,
    semantic_score REAL,
    llm_score      INT,
    verdict        JSONB,
    scored_at      TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (profile_id, job_id)
);

CREATE INDEX IF NOT EXISTS jobs_embedding_hnsw
  ON jobs USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS matches_llm_score
  ON matches (profile_id, llm_score DESC);

CREATE INDEX IF NOT EXISTS jobs_fetched_at
  ON jobs (fetched_at DESC);
```

**Alembic vs script:** Para portafolio, `init.sql` es suficiente y se ejecuta automáticamente por el contenedor `pgvector/pgvector:pg16` la primera vez que arranca. Si más adelante se necesitan migraciones evolutivas, se puede sumar Alembic sin tocar el resto.

---

## 3. `docker-compose.yml`

```yaml
version: "3.9"

x-airflow-common: &airflow-common
  image: apache/airflow:2.9.3-python3.11
  environment:
    AIRFLOW__CORE__EXECUTOR: LocalExecutor
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@airflow-db:5432/airflow
    AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
    AIRFLOW__WEBSERVER__SECRET_KEY: ${AIRFLOW_SECRET_KEY}
    AIRFLOW__CORE__LOAD_EXAMPLES: "false"
    PYTHONPATH: /opt/airflow/repo
    DATABASE_URL: postgresql+psycopg://app:app@app-db:5432/jobmatch
    GEMINI_API_KEY: ${GEMINI_API_KEY}
    SEMANTIC_THRESHOLD: ${SEMANTIC_THRESHOLD:-0.65}
  volumes:
    - ./dags:/opt/airflow/dags
    - ./src:/opt/airflow/repo/src
    - ./requirements.txt:/requirements.txt
  depends_on:
    app-db:
      condition: service_healthy
    airflow-db:
      condition: service_healthy

services:

  app-db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: jobmatch
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - app-db-data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d jobmatch"]
      interval: 5s
      retries: 10

  airflow-db:
    image: postgres:16
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - airflow-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U airflow"]
      interval: 5s
      retries: 10

  airflow-init:
    <<: *airflow-common
    entrypoint: /bin/bash
    command:
      - -c
      - |
        pip install --no-cache-dir -r /requirements.txt
        airflow db migrate
        airflow users create -u admin -p admin -r Admin -e admin@local -f a -l a || true
    restart: "no"

  airflow-webserver:
    <<: *airflow-common
    command: bash -c "pip install --no-cache-dir -r /requirements.txt && airflow webserver"
    ports:
      - "127.0.0.1:8080:8080"
    depends_on:
      airflow-init:
        condition: service_completed_successfully

  airflow-scheduler:
    <<: *airflow-common
    command: bash -c "pip install --no-cache-dir -r /requirements.txt && airflow scheduler"
    depends_on:
      airflow-init:
        condition: service_completed_successfully

  api:
    image: python:3.11-slim
    working_dir: /app
    environment:
      DATABASE_URL: postgresql+psycopg://app:app@app-db:5432/jobmatch
      GEMINI_API_KEY: ${GEMINI_API_KEY}
    volumes:
      - ./src:/app/src
      - ./requirements.txt:/app/requirements.txt
    command:
      - bash
      - -c
      - |
        pip install --no-cache-dir -r requirements.txt
        uvicorn src.api.main:app --host 0.0.0.0 --port 8000
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      app-db:
        condition: service_healthy

volumes:
  app-db-data:
  airflow-db-data:
```

**Notas:**
- Dos BDs separadas: `app-db` (jobmatch, con pgvector) y `airflow-db` (metadatos de Airflow). No mezclar.
- Bindeo a `127.0.0.1` para todos los puertos expuestos — uso personal, no expuesto a la red.
- `pip install` en cada arranque de Airflow es lento pero evita construir imágenes custom. Para producción se construye una imagen propia; para portafolio, vale.
- `Fernet key` y `secret key` se generan una vez con `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` y van a `.env`.

---

## 4. `.env.example`

```dotenv
# Gemini
GEMINI_API_KEY=your-gemini-key

# Postgres app (no cambiar usuarios sin actualizar docker-compose)
DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/jobmatch

# Airflow secrets (generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
AIRFLOW_FERNET_KEY=
AIRFLOW_SECRET_KEY=change-me

# Matching
SEMANTIC_THRESHOLD=0.65
TOP_K_FOR_LLM=30
```

---

## 5. `requirements.txt` (consolidado)

```
# core
pydantic>=2.5,<3
sqlalchemy>=2.0,<3
psycopg[binary]>=3.1
pgvector>=0.2.5

# sources
httpx>=0.27
feedparser>=6.0
beautifulsoup4>=4.12
tenacity>=8.2

# extraction + scoring
google-generativeai>=0.7

# embeddings
sentence-transformers>=2.7
numpy>=1.26

# api
fastapi>=0.110
uvicorn[standard]>=0.27

# orquestación: airflow se instala vía la imagen oficial; aquí solo los providers usados
apache-airflow-providers-postgres>=5.10

# tests
pytest>=8.0
pytest-asyncio>=0.23
```

---

## 6. DAG — `dags/job_match.py`

```python
from __future__ import annotations
import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from sqlalchemy import create_engine, text


DEFAULT_ARGS = {
    "owner": "danielcaso",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}


def _engine():
    return create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)


@dag(
    dag_id="job_match",
    description="Recolección → extracción → embeddings → scoring (cada 12h).",
    schedule="0 */12 * * *",                # 00:00 y 12:00 UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["jobs", "ai"],
)
def job_match():

    @task
    def recolectar() -> int:
        from src.sources.himalayas import HimalayasSource
        from src.sources.remotive import RemotiveSource
        from src.storage import pgvector_io as store
        engine = _engine()
        n = 0
        for src_cls in (HimalayasSource, RemotiveSource):
            for job in src_cls().fetch():
                store.upsert_job(engine, job)
                n += 1
        return n

    @task
    def extraer_requisitos(_collected: int) -> int:
        from src.extraction.extractor import extract_requirements
        from src.storage import pgvector_io as store
        engine = _engine()
        pending = store.list_jobs_without_requirements(engine, limit=200)
        for job in pending:
            req = extract_requirements(job.raw_text)
            store.update_job_requirements(engine, job.id, req)
        return len(pending)

    @task
    def embeddings(_extracted: int) -> int:
        from src.matching import pipeline as mp
        engine = _engine()
        # procesa en lotes hasta que no queden pendientes
        total = 0
        while True:
            n = mp.embed_pending_jobs(engine, batch_size=32)
            total += n
            if n == 0:
                break
        return total

    @task
    def score_perfiles(_embedded: int) -> int:
        from src.matching import pipeline as mp
        from src.profile.form import ProfileForm
        engine = _engine()
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT id, form_data FROM profiles")).mappings().all()
        total = 0
        for r in rows:
            form = ProfileForm.model_validate(r["form_data"])
            total += mp.score_profile_against_corpus(engine, form)
        return total

    n_collected = recolectar()
    n_extracted = extraer_requisitos(n_collected)
    n_embedded = embeddings(n_extracted)
    score_perfiles(n_embedded)


dag = job_match()
```

**Decisiones del DAG:**
- Una task por etapa lógica del pipeline. Suficientemente granular para reintentar puntos costosos sin re-correr todo.
- `deduplicar` no es una task separada: la dedup ocurre en `store.upsert_job` (idempotente por `job_id`). Más simple.
- `extraer_requisitos` toma `_collected` solo para crear la dependencia, no usa el valor — la lista de pendientes la calcula consultando la BD (`WHERE requirements IS NULL`), lo que la hace **resiliente a reintentos parciales**.
- `score_perfiles` itera todos los perfiles existentes. Para un único perfil (uso personal), itera 1 vez. Para varios, escala lineal — suficiente.
- `retries=2` con backoff exponencial: Gemini puede dar 429 esporádicos; tras 2 reintentos lo damos por perdido y la próxima corrida (12h) lo retoma.

---

## 7. Cómo correrlo

```bash
# 1) copiar y rellenar env
cp .env.example .env
# editar GEMINI_API_KEY y generar fernet/secret keys

# 2) arrancar
docker compose up -d

# 3) ver Airflow UI
open http://127.0.0.1:8080      # admin / admin

# 4) ver Swagger
open http://127.0.0.1:8000/docs

# 5) crear perfil
curl -X POST http://127.0.0.1:8000/profile \
     -H "content-type: application/json" \
     -d @perfil.json

# 6) disparar pipeline manual (la primera vez, sin esperar 12h)
curl -X POST http://127.0.0.1:8000/jobs/refresh
# o desde Airflow UI: Trigger DAG → job_match

# 7) consultar matches
curl 'http://127.0.0.1:8000/matches?profile_id=daniel-2026&limit=10' | jq
```

---

## 8. Idempotencia — checklist

| Operación | Cómo se garantiza idempotencia |
|---|---|
| Recolectar misma oferta 2 veces | `upsert_job` con `ON CONFLICT (id) DO UPDATE` — `id = hash(source+url)` |
| Reintento de `extraer_requisitos` | La task consulta `WHERE requirements IS NULL` cada vez — no reprocesa lo ya hecho |
| Reintento de `embeddings` | `list_jobs_without_embedding` filtra a las que aún no tienen vector |
| Reintento de `score_perfiles` | `semantic_top_k(only_unscored_for_profile=...)` excluye las ya scoreadas; `upsert_match` por `PRIMARY KEY (profile_id, job_id)` |
| Crash a mitad de DAG | Próxima corrida (manual o cada 12h) retoma donde quedó, sin tocar lo persistido |

---

## 9. Criterios de aceptación

- [ ] `docker compose up -d` arranca sin errores; los healthchecks ponen `app-db` y `airflow-db` en `healthy`.
- [ ] `http://127.0.0.1:8080` muestra DAG `job_match` (paused → activarlo).
- [ ] Trigger manual del DAG completa las 4 tasks en verde.
- [ ] Tras 1 corrida: `SELECT count(*) FROM jobs;` > 0, `SELECT count(*) FROM jobs WHERE requirements IS NOT NULL;` > 0, `SELECT count(*) FROM jobs WHERE embedding IS NOT NULL;` > 0.
- [ ] Con un perfil creado vía API: `SELECT count(*) FROM matches WHERE profile_id='daniel-2026';` ≥ 10.
- [ ] Re-trigger del DAG no aumenta `count(jobs)` para ofertas ya vistas y no duplica matches.
- [ ] `docker compose restart airflow-scheduler` no rompe el siguiente run.

---

## 10. Lo que NO se hace en esta fase

- **Despliegue cloud** (Cloud Run, ECS, Fly.io...). El proyecto es local + portafolio.
- **Observabilidad avanzada** (Prometheus, Grafana). Logs de Airflow + tabla `matches` alcanzan.
- **Alembic / migraciones evolutivas**. `init.sql` basta para v0.
- **HPA / scaling horizontal del API**. Uvicorn 1 worker es suficiente.
- **CI/CD**. Si se quiere, una acción de GitHub que corra `pytest` está bien — fuera de alcance del MVP.
