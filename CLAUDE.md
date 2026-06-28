# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

**Job Match Pipeline** — sistema que recolecta ofertas de empleo de fuentes legales cada 12 h, extrae sus requisitos con un LLM (Gemini) a un schema Pydantic validado, calcula embeddings, hace scoring semántico + LLM contra un perfil profesional, y expone los matches con fortalezas/riesgos vía FastAPI.

Estado actual:
- ✅ **Fase 1** (recolección — Himalayas + Remotive) implementada.
- ✅ **Fase 2** (extracción Gemini) implementada.
- ✅ **Storage layer** (SQLAlchemy 2.0 ORM + Alembic + Postgres+pgvector) en pre-bootstrap.
- ✅ **FastAPI** en pre-bootstrap (servicio `api` corre, `GET /health`, DI vía `Depends`).
- ⏳ Fases 3–6 (matching, profile/match routers, Airflow, README/demo) pendientes.

La planificación detallada de cada fase vive en `docs/` — leer el doc de la fase antes de implementarla.

## Arquitectura: Clean Architecture

Cuatro capas estrictas. **La dirección de las dependencias va siempre hacia adentro** (interfaces → infrastructure → application → domain). Domain no importa de nadie.

```
src/
├── domain/                        # pura — sin frameworks externos
│   ├── entities/                  # RawJob, Job, Profile, Match
│   ├── value_objects/             # JobRequirements + Seniority + EnglishLevel
│   ├── services/                  # make_id (función pura)
│   └── ports/                     # ABC: JobSource, JobRepository, ProfileRepository,
│                                  # MatchRepository, RequirementsExtractor
├── application/
│   └── use_cases/                 # CollectJobsUseCase, ExtractJobRequirementsUseCase
├── infrastructure/                # implementa los ports del domain
│   ├── config.py                  # Settings (lee env)
│   ├── sources/                   # HimalayasSource, RemotiveSource (httpx)
│   ├── llm/                       # GeminiExtractor (google-genai)
│   └── persistence/               # SQLAlchemy: ORM models + repos + mappers
└── interfaces/                    # entrypoints
    ├── api/                       # FastAPI: main.py + dependencies.py + routers/
    └── cli/                       # collect.py, extract.py (entrypoints argparse)
```

**Reglas de oro:**
- `domain/` **NO** importa nada de `infrastructure/`, `application/`, `interfaces/`, ni librerías externas pesadas (excepto Pydantic, que es validación, no framework).
- `application/use_cases/*` reciben dependencias por constructor (DIP). Solo conocen los **ports** (`domain/ports/`), no las implementaciones concretas.
- `infrastructure/persistence/sqlalchemy_*_repository.py` traducen entre entidades de dominio (Pydantic) y `orm_models` (SQLAlchemy) via `mappers.py`. **Cero `text()` / SQL en duro** en código de aplicación.
- `interfaces/api/dependencies.py` cablea ports → implementaciones concretas via `Depends()`. Es el único lugar donde se sabe que un `JobRepository` es realmente un `SqlAlchemyJobRepository`.

Para añadir una fuente nueva: heredar de `JobSource` (port en domain), implementar en `infrastructure/sources/`, registrar en `src/interfaces/cli/collect.py::SOURCE_REGISTRY`. Use case no cambia.

## Workflow: Docker-only

Todo Python corre dentro del contenedor. **No hay `.venv` local** ni se debe crear. `uv` vive solo en la imagen (`/opt/venv`). Esto evita el "funciona en mi máquina" y deja una única fuente de verdad de dependencias (`pyproject.toml` + `uv.lock`).

```bash
docker compose build                                                   # tras cambios en deps/Dockerfile
docker compose up -d app-db                                            # arrancar Postgres+pgvector
docker compose up -d api                                               # arrancar FastAPI (puerto 8000)
docker compose run --rm app pytest -v                                  # tests (offline-first)
docker compose run --rm app pytest -v -k <patrón>                      # un test específico
docker compose run --rm app ruff check src tests                       # lint
docker compose run --rm app alembic upgrade head                       # aplicar migraciones
docker compose run --rm app alembic revision --autogenerate -m "msg"   # nueva migración tras editar modelos
docker compose run --rm app python -m src.interfaces.cli.collect \     # recolectar a BD
  --source himalayas --limit 3
docker compose run --rm app python -m src.interfaces.cli.collect \     # recolectar sin tocar BD (smoke)
  --source remotive --limit 3 --dry-run
docker compose run --rm app python -m src.interfaces.cli.extract \     # extraer requirements (Gemini)
  --limit 5 --print-results                                            # requiere .env con GEMINI_API_KEY
docker compose exec app-db psql -U app -d jobmatch                     # shell SQL ad-hoc
curl http://127.0.0.1:8000/health                                      # API health
open http://127.0.0.1:8000/docs                                        # Swagger
```

Hay skills atajo proyecto-locales — ver sección **Skills** más abajo.

## Skills (`.claude/skills/`)

Skills invocables como `/<nombre>`. Preferí usarlas antes de tipear los comandos a mano: encapsulan el flujo correcto, los argumentos por defecto y las reglas del proyecto.

| Skill | Cuándo usarla | Qué hace |
|---|---|---|
| `/test [-k patrón]` | tests, iterar TDD, validar un cambio | `docker compose run --rm app pytest -v`, con filtro opcional. Reporta fallos sin auto-fix |
| `/run-source <himalayas\|remotive\|all> [--limit N] [--dry-run]` | recolectar a BD (o smoke en stdout) | corre `CollectJobsUseCase`; default `all --limit 3`. Cuenta para el cupo (≤ 4 req/día por fuente) |
| `/extract [--limit N] [--print-results]` | extraer requirements via Gemini | corre `ExtractJobRequirementsUseCase` sobre ofertas con `requirements IS NULL`. Requiere `.env` con `GEMINI_API_KEY` |
| `/add-source <name>` | añadir una nueva fuente (We Work Remotely, Jobicy, …) | workflow guiado: lee ports + docs, crea `src/infrastructure/sources/<name>.py` + fixture + tests + registra en CLI. **No toca fuentes existentes** |
| `/migrate` | tras editar `orm_models.py` o cambiar el schema | autogenera la revision Alembic, la revisa (verifica imports pgvector + HNSW), aplica `upgrade head` |
| `/db-shell` | inspección ad-hoc de la BD | `docker compose exec app-db psql -U app -d jobmatch`. Solo lectura/exploración; cambios estructurales van por Alembic |
| `/review` | antes de un commit o al cerrar una feature | code review del diff actual contra las convenciones del proyecto. Solo reporta |
| `/check` | gate pre-commit | corre pytest + ruff combinados; reporta el primer fallo de cada uno |
| `/build` | tras cambiar `pyproject.toml`, `uv.lock` o `Dockerfile` | `docker compose build app`. **No hace falta** para cambios solo en `src/`/`tests/` (van por volúmenes) |

Sin agents customizados — los preexistentes (`feature-dev`, `code-reviewer`, `Explore`, `Plan`) ya cubren. Si llegamos a un patrón repetido que los justifique, se agregan en `.claude/agents/`.

## Convenciones de código

- **Pydantic v2** para entidades de dominio y value objects. No usar dataclasses ni dicts crudos cuando hay un schema. Excepción: `Settings` en `infrastructure/config.py` (frozen dataclass — no necesita validación, lee env).
- **No inventar comentarios/docstrings ni manejo de errores donde no se pide.** Las funciones tienen tipos; el código bien nombrado se explica solo.
- **Idempotencia**: cualquier operación debe poder reintentarse sin duplicar estado. IDs siempre vía `make_id`; persistencia vía `pg_insert.on_conflict_do_update` en los repos.
- **Retries `tenacity`** en todo cliente HTTP/LLM externo (429, 5xx, timeouts). Patrón en `src/infrastructure/sources/himalayas.py::_get_json` y `src/infrastructure/llm/gemini_extractor.py::_generate`.
- **Tests offline-first**: fixtures sintéticas en `tests/fixtures/`, mocks con `unittest.mock.patch`. Un test que requiere BD real va con marker `integration` (no usado todavía).
- **DIP en use cases**: los use cases reciben **ports** (`JobRepository`, `JobSource`, ...) en el constructor, nunca clases concretas. Tests pueden inyectar in-memory fakes (ver `tests/application/`).
- **Sin SQL en duro**: toda persistencia via `select()` / `pg_insert()` sobre `orm_models`. Schema changes pasan **siempre** por Alembic.
- **Idioma**: identificadores en inglés; mensajes de log y respuestas al usuario en español.

## Componentes implementados

### Domain (`src/domain/`)
- `entities/{raw_job,job,profile,match}.py` — entities Pydantic.
- `value_objects/job_requirements.py` — `JobRequirements` + `Seniority`/`EnglishLevel` (`StrEnum`). Validator de `stack` (lowercase + dedup).
- `services/id_hasher.py::make_id` — SHA-1 truncado para idempotencia.
- `ports/{job_source,job_repository,profile_repository,match_repository,requirements_extractor}.py` — ABCs.

### Application (`src/application/use_cases/`)
- `collect_jobs.py::CollectJobsUseCase` — itera sources, upsertea via `JobRepository`.
- `extract_job_requirements.py::ExtractJobRequirementsUseCase` — extrae Gemini, persiste.

### Infrastructure (`src/infrastructure/`)
- `config.py::Settings` — frozen dataclass leído de env (default `from_env()` se exporta como singleton `settings`).
- `sources/{himalayas,remotive}.py` — `httpx` con paginador, `tenacity` retries, `BeautifulSoup` para limpiar HTML.
- `llm/gemini_extractor.py::GeminiExtractor` — implementa `RequirementsExtractor`. SDK nuevo `google-genai` con `response_schema=JobRequirements`. Reintento con feedback ante validation error. **Nunca levanta** — devuelve `JobRequirements(confidence=0.0)` al fallo total.
- `persistence/orm_models.py` — `Base`, `JobModel`, `ProfileModel`, `MatchModel` (SQLAlchemy 2.0 con `Mapped[]`, `Vector(384)` de pgvector, JSONB, HNSW index `vector_cosine_ops`, FK CASCADE).
- `persistence/database.py` — `engine`, `SessionLocal`, `session_scope()` (commit on success, rollback on error).
- `persistence/mappers.py` — funciones puras ORM ↔ domain.
- `persistence/sqlalchemy_*_repository.py` — implementaciones de los repos. Convención: **NO commitean** (transacción la maneja el caller).
- `alembic/` (raíz, no en `src/`) — migraciones versionadas. La inicial crea la extensión `vector`, las 3 tablas y los 4 índices.

### Interfaces (`src/interfaces/`)
- `api/main.py` — `FastAPI(app)` + lifespan placeholder + include_router.
- `api/dependencies.py` — `get_session`, `get_*_repository`, `get_requirements_extractor` + `Annotated[..., Depends(...)]` aliases (`SessionDep`, `JobRepositoryDep`, etc.).
- `api/routers/health.py` — `GET /health` con check de DB + Gemini key.
- `cli/collect.py` — `python -m src.interfaces.cli.collect --source <name> [--limit N] [--dry-run]`.
- `cli/extract.py` — `python -m src.interfaces.cli.extract [--limit N] [--print-results]`.

## Términos de las fuentes (obligatorio)

- **Atribución**: cada respuesta de la API debe incluir `source_attribution` (planificado en fase 4).
- **No redistribución** de empleos a terceros (Google Jobs, LinkedIn, etc.).
- **Frecuencia**: ≤ 4 req/día por fuente. El DAG corre cada 12 h → 2 req/día → holgado.

Si se añade una nueva fuente, validar primero sus términos y replicar las garantías.

## Docs por fase

| Fase | Doc | Estado |
|---|---|---|
| Overview transversal | [`docs/00-overview.md`](docs/00-overview.md) | ✅ |
| 1 · Recolección (Himalayas + Remotive) | [`docs/phase-1-recoleccion.md`](docs/phase-1-recoleccion.md) | ✅ implementada |
| 2 · Extracción (Gemini + Pydantic) | [`docs/phase-2-extraccion.md`](docs/phase-2-extraccion.md) | ✅ implementada |
| 3 · Matching (embeddings + scoring) | [`docs/phase-3-matching.md`](docs/phase-3-matching.md) | ⏳ (storage + ports pre-bootstrap ✅) |
| 4 · API + perfil (FastAPI) | [`docs/phase-4-api-perfil.md`](docs/phase-4-api-perfil.md) | ⏳ (bootstrap FastAPI + /health ✅) |
| 5 · Orquestación (Airflow + Postgres+pgvector) | [`docs/phase-5-orquestacion.md`](docs/phase-5-orquestacion.md) | ⏳ (BD pre-bootstrap ✅) |
| 6 · README + demo | [`docs/phase-6-readme-demo.md`](docs/phase-6-readme-demo.md) | ⏳ |

Antes de implementar una fase: **leer su doc completo**. Tiene decisiones, schemas y criterios de aceptación (DoD).

## Cambios respecto al diseño original (importantes)

- **Remotive**: el doc original planeaba RSS. La realidad: Remotive descontinuó RSS (responde HTML 404). Implementado contra API JSON oficial (`https://remotive.com/api/remote-jobs`).
- **Deps**: el doc menciona `requirements.txt`; el proyecto usa `pyproject.toml` + `uv.lock`.
- **Docker-only**: el doc deja Docker para fase 5; lo adoptamos desde fase 1 para tener un único entorno reproducible.
- **SDK de Gemini**: el doc menciona `google-generativeai` (SDK legacy). Implementado con el SDK nuevo `google-genai`, que soporta `response_schema=PydanticModel` nativo y devuelve la instancia parseada en `response.parsed`.
- **Modelo Gemini**: el doc dice `gemini-1.5-flash`. Usamos `gemini-2.5-flash` (2.0-flash ya retirada del catálogo público).
- **Persistencia**: el doc original usaba SQL en duro (`sqlalchemy.text("...")`) y un `init.sql`. **Cambiamos a SQLAlchemy 2.0 ORM declarativo + Alembic + Repository pattern**.
- **Arquitectura**: el doc original tenía estructura plana por módulo. **Reorganizado a Clean Architecture** (domain → application → infrastructure → interfaces) con ports e implementaciones separadas. Los docs de fases 3/4/5 están reescritos para reflejarlo.
