# Fase 5 · Orquestación e infraestructura — Airflow + Docker + Postgres

**Tiempo estimado:** 1 día
**Entregable demostrable:** `docker compose up` levanta Postgres+pgvector, Airflow y la API. El DAG `job_match` corre end-to-end cada 12h (y a demanda), poblando la BD con matches reales.

> **Nota de corrección (post-implementación parcial):** lo que ya está hecho como pre-bootstrap:
> - `app-db` (`pgvector/pgvector:pg16`) en `docker-compose.yml` con healthcheck + volumen + `127.0.0.1:5432`.
> - `api` (uvicorn, `127.0.0.1:8000`) en `docker-compose.yml`.
> - Alembic con `initial_schema` aplicada (`CREATE EXTENSION vector` + tablas + HNSW). No hay `init.sql`.
>
> Lo que falta de fase 5: **Airflow webserver + scheduler + airflow-db**, el DAG `job_match`, y sus tasks. El DAG debe invocar los **use cases existentes** (`CollectJobsUseCase`, `ExtractJobRequirementsUseCase`, y los de fase 3 `EmbedJobsUseCase`/`ScoreProfileUseCase`), cableando dependencias concretas dentro de cada task con `session_scope()`. NO duplicar lógica desde código viejo (`text()`, queries crudas); todo via los repos y ports ya definidos.

---

## 1. Objetivo

Unir todas las piezas en un sistema autónomo:
- **Postgres 16 + pgvector** como única fuente de verdad.
- **Airflow** ejecutando el DAG cada 12h.
- **FastAPI** consultable mientras el DAG no corre.

Idempotencia es **requisito duro**: cualquier task del DAG debe poder reintentarse sin duplicar datos ni romper estado.

---

## 2. Migraciones con Alembic

> **Nota de corrección (post-implementación):** el plan original usaba un `init.sql` montado como `docker-entrypoint-initdb.d`. **Cambiamos a Alembic** (decisión del usuario al introducir el ORM en pre-bootstrap). El schema es la proyección de los modelos `src/storage/models.py` (SQLAlchemy 2.0 declarativo) — autogenerada y versionada bajo `alembic/versions/`. Ya no hay `init.sql`.

Archivos relevantes:
- `alembic.ini` — config; `sqlalchemy.url` se inyecta desde `$DATABASE_URL` en `alembic/env.py`.
- `alembic/env.py` — importa `Base` de `src.storage.models`, registra `pgvector.sqlalchemy`, configura `target_metadata = Base.metadata`.
- `alembic/versions/<hash>_initial_schema.py` — primera migración (manual + autogenerate): ejecuta `CREATE EXTENSION IF NOT EXISTS vector`, crea las tres tablas y los cuatro índices (incluyendo el HNSW `vector_cosine_ops`).

**Comandos canónicos:**
```bash
# Aplicar todas las migraciones pendientes (en CI, en producción, y tras git pull):
docker compose run --rm app alembic upgrade head

# Crear una nueva migración después de cambiar modelos:
docker compose run --rm app alembic revision --autogenerate -m "add X column"

# Ver historia:
docker compose run --rm app alembic history --verbose
```

**Reglas:**
- Toda modificación al schema entra por una nueva revision; no editar revisions ya aplicadas en otros entornos.
- Revisar siempre el diff autogenerado antes de aplicar — Alembic puede no detectar `postgresql_using`/`postgresql_ops` para índices de pgvector (la revision inicial los recibió bien, pero verificar cada vez).
- La extensión `vector` se crea en la primera migración. Migraciones futuras no necesitan re-crearla.

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
      # NB: no se monta init.sql — Alembic se encarga (alembic upgrade head)
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

## 5. Dependencias (`pyproject.toml`)

> **Nota de corrección:** el proyecto no usa `requirements.txt`. Las deps se gestionan con `uv` (`pyproject.toml` + `uv.lock`). Para Airflow, que tradicionalmente se configura con requirements, exportamos al vuelo:
> ```bash
> uv export --frozen --no-dev --no-emit-project --format requirements-txt > /tmp/airflow-reqs.txt
> ```
> y montamos ese archivo en los contenedores de Airflow. O construimos una imagen Airflow custom que ya tenga las deps instaladas (recomendado).

Resumen de deps **del proyecto** (las que ya están en `pyproject.toml` tras pre-bootstrap de fase 3/5):

```toml
dependencies = [
  # sources (fase 1)
  "httpx>=0.27",
  "beautifulsoup4>=4.12",
  "tenacity>=8.2",
  # validación (transversal)
  "pydantic>=2.5",
  # extracción + scoring LLM (fase 2 y 3)
  "google-genai>=1.0",
  # persistencia (fase 3 + 5)
  "sqlalchemy>=2.0,<3",
  "psycopg[binary]>=3.1",
  "pgvector>=0.2.5",
  "alembic>=1.13",
  # matching (fase 3) — se sumará al implementar
  # "sentence-transformers>=2.7",
  # "numpy>=1.26",
  # api (fase 4) — se sumará al implementar
  # "fastapi>=0.110",
  # "uvicorn[standard]>=0.27",
]
```

Para Airflow se monta el código del proyecto como volumen (`./src:/opt/airflow/repo/src:ro`) y se instalan las deps Python con `uv pip install --system -r <reqs export>` dentro del contenedor Airflow al arrancar (o build de imagen custom).

---

## 6. DAG — `dags/job_match.py`

```python
from __future__ import annotations
import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from sqlalchemy import select


DEFAULT_ARGS = {
    "owner": "danielcaso",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}


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
        from src.storage.database import session_scope
        n = 0
        with session_scope() as session:
            for src_cls in (HimalayasSource, RemotiveSource):
                for job in src_cls().fetch():
                    store.upsert_job(session, job)
                    n += 1
        return n

    @task
    def extraer_requisitos(_collected: int) -> int:
        from src.extraction.extractor import extract_requirements
        from src.storage import pgvector_io as store
        from src.storage.database import session_scope
        with session_scope() as session:
            pending = store.list_jobs_without_requirements(session, limit=200)
            for job in pending:
                req = extract_requirements(job.raw_text)
                store.update_job_requirements(session, job.id, req)
        return len(pending)

    @task
    def embeddings(_extracted: int) -> int:
        from src.matching import pipeline as mp
        total = 0
        while True:
            n = mp.embed_pending_jobs(batch_size=32)
            total += n
            if n == 0:
                break
        return total

    @task
    def score_perfiles(_embedded: int) -> int:
        from src.matching import pipeline as mp
        from src.profile.form import ProfileForm
        from src.storage.database import session_scope
        from src.storage.models import Profile
        with session_scope() as session:
            profiles = session.scalars(select(Profile)).all()
        total = 0
        for p in profiles:
            form = ProfileForm.model_validate(p.form_data)
            total += mp.score_profile_against_corpus(form)
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
- (Alembic ya implementado; este punto del doc original quedó obsoleto.)
- **HPA / scaling horizontal del API**. Uvicorn 1 worker es suficiente.
- **CI/CD**. Si se quiere, una acción de GitHub que corra `pytest` está bien — fuera de alcance del MVP.
