# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

**Job Match Pipeline** — sistema que recolecta ofertas de empleo de fuentes legales cada 12 h, extrae sus requisitos con un LLM (Gemini) a un schema Pydantic validado, calcula embeddings, hace scoring semántico + LLM contra un perfil profesional, y expone los matches con fortalezas/riesgos vía FastAPI.

Estado actual: **Fases 1 (recolección) y 2 (extracción Gemini)** implementadas. **Pre-bootstrap de fase 3/5**: capa de persistencia lista (SQLAlchemy 2.0 ORM + Alembic + `app-db` corriendo en docker-compose con `pgvector/pgvector:pg16`). Las fases 3–6 están diseñadas en `docs/` pero aún no implementadas — la planificación es la fuente de verdad, leer el doc de la fase antes de implementarla.

## Workflow: Docker-only

Todo Python corre dentro del contenedor. **No hay `.venv` local** ni se debe crear. `uv` vive solo en la imagen (`/opt/venv`). Esto evita el "funciona en mi máquina" y deja una única fuente de verdad de dependencias (`pyproject.toml` + `uv.lock`).

```bash
docker compose build                                                   # tras cambios en deps/Dockerfile
docker compose run --rm app pytest -v                                  # tests
docker compose run --rm app pytest -v -k <patrón>                      # un test específico
docker compose run --rm app ruff check src tests                       # lint
docker compose run --rm app python -m src.sources.himalayas --limit 3  # smoke Himalayas (API real)
docker compose run --rm app python -m src.sources.remotive --limit 3   # smoke Remotive (API real)
docker compose run --rm app python -m src.extraction.extractor \       # fase 1 → fase 2 end-to-end
  --source himalayas --limit 3                                          # requiere .env con GEMINI_API_KEY

docker compose up -d app-db                                             # arrancar Postgres+pgvector
docker compose run --rm app alembic upgrade head                        # aplicar migraciones
docker compose run --rm app alembic revision --autogenerate -m "msg"    # nueva migración tras editar modelos
docker compose exec app-db psql -U app -d jobmatch                      # shell SQL ad-hoc
```

Hay skills atajo proyecto-locales — ver sección **Skills** más abajo.

## Skills (`.claude/skills/`)

Skills invocables como `/<nombre>`. Preferí usarlas antes de tipear los comandos a mano: encapsulan el flujo correcto, los argumentos por defecto y las reglas del proyecto.

| Skill | Cuándo usarla | Qué hace |
|---|---|---|
| `/test [-k patrón]` | tests, iterar TDD, validar un cambio | `docker compose run --rm app pytest -v`, con filtro opcional. Reporta fallos sin auto-fix |
| `/run-source <himalayas\|remotive> [--limit N]` | smoke test contra la API real | corre el CLI de la fuente; default `--limit 3`. Cuenta para el cupo (≤ 4 req/día por fuente) |
| `/extract <himalayas\|remotive> [--limit N]` | ver requisitos extraídos por Gemini | encadena fase 1 + fase 2: trae N ofertas y las pasa por el extractor. Requiere `.env` con `GEMINI_API_KEY` |
| `/add-source <name>` | añadir una nueva fuente (We Work Remotely, Jobicy, …) | workflow guiado: lee `base.py` + docs, crea `src/sources/<name>.py` + fixture + tests. **No toca fuentes existentes** |
| `/review` | antes de un commit o al cerrar una feature | code review del diff actual contra las convenciones del proyecto (Pydantic v2, idempotencia, retries, fixtures offline). Solo reporta |
| `/check` | gate pre-commit | corre pytest + ruff combinados; reporta el primer fallo de cada uno |
| `/build` | tras cambiar `pyproject.toml`, `uv.lock` o `Dockerfile` | `docker compose build app`. **No hace falta** para cambios solo en `src/`/`tests/` (van por volúmenes) |
| `/migrate` | tras editar `src/storage/models.py` o cambiar el schema | autogenera la revision Alembic y la aplica. Recordar revisar el diff antes de `upgrade head` |
| `/db-shell` | inspección ad-hoc de la BD | `docker compose exec app-db psql -U app -d jobmatch`. Solo lectura/exploración; cambios estructurales van por Alembic |

Sin agents customizados — los preexistentes (`feature-dev`, `code-reviewer`, `Explore`, `Plan`) ya cubren. Si llegamos a un patrón repetido que los justifique, se agregan en `.claude/agents/`.

## Arquitectura

```
recolectar (fase 1) → deduplicar → extraer_requisitos (fase 2, Gemini)
  → embeddings (fase 3) → score_semántico → score_llm → persistir
```

Tres capas de inteligencia, en orden de costo creciente:
1. **Semántica** (CPU local, sobre todas las ofertas) — filtro grueso.
2. **Extracción estructurada** (Gemini, solo las que pasan el filtro).
3. **Scoring LLM** (Gemini, top K) — devuelve `{score, strengths, risks}`.

Capas implementadas hoy: **1 (recolección) + 2 (extracción)**. El resto está en `docs/phase-N-*.md` con schemas Pydantic, prompts, SQL y pseudocódigo listos para traducir.

### Componentes de fase 1 (`src/sources/`)

- `base.py` — `RawJob` (Pydantic), `Source` (ABC), `make_id(source, url)` (SHA-1 truncado, **único punto** para IDs idempotentes).
- `himalayas.py` — cliente `httpx` con paginador + retries `tenacity` + `BeautifulSoup` para limpiar HTML + CLI argparse.
- `remotive.py` — cliente `httpx` contra la API JSON oficial (`/api/remote-jobs`). El RSS fue descontinuado por Remotive; usar siempre la API JSON.

Toda fuente nueva debe heredar de `Source` y devolver `RawJob` con `raw_text` sin HTML. Fixtures de tests **sintéticas mínimas** en `tests/fixtures/` — sin llamadas de red en CI.

### Componentes de fase 2 (`src/extraction/`)

- `schema.py` — `JobRequirements` (Pydantic v2) + `Seniority` y `EnglishLevel` (`StrEnum`). Validator de `stack` (lowercase + dedup).
- `extractor.py` — `extract_requirements(raw_text) -> JobRequirements`. Usa el SDK nuevo `google-genai` con `response_schema=JobRequirements` para parseo nativo. Reintento con feedback ante `ValidationError`/`JSONDecodeError`. Si todo falla devuelve `JobRequirements(confidence=0.0)` — **nunca levanta** (el pipeline tiene que avanzar). Cliente Gemini lazy via `@lru_cache`. Requiere `GEMINI_API_KEY` (vía `.env`).
- CLI integrada: `python -m src.extraction.extractor --source himalayas --limit 3` encadena fase 1 + fase 2 end-to-end.

### Componentes de storage (pre-bootstrap fase 3 / 5) (`src/storage/`)

- `models.py` — `Base` (`DeclarativeBase`) + `Job`, `Profile`, `Match` (SQLAlchemy 2.0 con `Mapped[]` y `mapped_column`). Embeddings via `pgvector.sqlalchemy.Vector(384)`. JSONB para `requirements`/`form_data`/`verdict`. Índice HNSW (`vector_cosine_ops`) sobre `jobs.embedding` declarado en `__table_args__`.
- `database.py` — `engine` + `SessionLocal` + `session_scope()` context manager (commit on success, rollback on error). `DATABASE_URL` se lee de env con default a `postgresql+psycopg://app:app@app-db:5432/jobmatch`.
- `alembic/` (raíz, no en `src/`) — migraciones versionadas. La inicial crea la extensión `vector`, las 3 tablas y los 4 índices. Para cambios al schema: editar modelos → `alembic revision --autogenerate -m "..."` → revisar diff → `alembic upgrade head`.

**Reglas de persistencia:**
- **Cero `text()` / SQL en duro** en código de aplicación. Todo via `select()`, `insert()` (con `pg_insert.on_conflict_do_update` para upserts) sobre los modelos.
- Idempotencia por upsert: `pg_insert(...).on_conflict_do_update(...)` en `src/storage/pgvector_io.py` (fase 3, aún no implementado).
- Embeddings: asignación directa (`job.embedding = vec.tolist()`); no hay `CAST(... AS vector)` necesario, la columna `Vector(384)` ya tipea.
- Schema changes pasan **siempre** por Alembic — nunca editar el schema con SQL manual ni `Base.metadata.create_all()`.

## Convenciones de código

- **Pydantic v2** para todo modelo de datos. No usar dataclasses ni dicts crudos cuando hay un schema.
- **No inventar comentarios/docstrings ni manejo de errores donde no se pide.** Las funciones tienen tipos; el código bien nombrado se explica solo.
- **Idempotencia**: cualquier operación debe poder reintentarse sin duplicar estado. IDs siempre vía `make_id`; persistencia vía upsert (fase 3+).
- **Retries `tenacity`** en todo cliente HTTP externo (429, 5xx, timeouts). Patrón en `src/sources/himalayas.py::_get_json`.
- **Tests offline-first**: fixtures sintéticas en `tests/fixtures/`, todo lo de red mockeado con `unittest.mock.patch`.
- **Idioma**: identificadores en inglés; mensajes de log y respuestas al usuario en español.

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
| 3 · Matching (embeddings + scoring) | [`docs/phase-3-matching.md`](docs/phase-3-matching.md) | ⏳ (storage pre-bootstrap ✅) |
| 4 · API + perfil (FastAPI) | [`docs/phase-4-api-perfil.md`](docs/phase-4-api-perfil.md) | ⏳ |
| 5 · Orquestación (Airflow + Postgres+pgvector) | [`docs/phase-5-orquestacion.md`](docs/phase-5-orquestacion.md) | ⏳ (BD pre-bootstrap ✅) |
| 6 · README + demo | [`docs/phase-6-readme-demo.md`](docs/phase-6-readme-demo.md) | ⏳ |

Antes de implementar una fase: **leer su doc completo**. Tiene decisiones, schemas y criterios de aceptación (DoD).

## Cambios respecto al diseño original (importantes)

- **Remotive**: el doc original planeaba RSS. La realidad: Remotive descontinuó RSS (responde HTML 404). Implementado contra API JSON oficial (`https://remotive.com/api/remote-jobs`). Si en el futuro Remotive cambia de nuevo, actualizar `src/sources/remotive.py` y la nota en `docs/phase-1-recoleccion.md` §4.
- **Deps**: el doc menciona `requirements.txt`; el proyecto usa `pyproject.toml` + `uv.lock`.
- **Docker-only**: el doc deja Docker para fase 5; lo adoptamos desde fase 1 para tener un único entorno reproducible.
- **SDK de Gemini**: el doc menciona `google-generativeai` (SDK legacy). Implementado con el SDK nuevo `google-genai`, que soporta `response_schema=PydanticModel` nativo y devuelve la instancia parseada en `response.parsed`. Código más limpio.
- **Modelo Gemini**: el doc dice `gemini-1.5-flash`. Usamos `gemini-2.5-flash` (generación 2.0 ya fue retirada del catálogo público en producción; 2.5-flash es la flash estable actual).
- **Persistencia**: el doc original usaba SQL en duro (`sqlalchemy.text("...")`) y un `init.sql`. **Cambiamos a SQLAlchemy 2.0 ORM declarativo + Alembic** (decisión del usuario). Los docs de fases 3/4/5 están reescritos para reflejarlo (`Session` + `Select`, `pg_insert.on_conflict_do_update`, `alembic upgrade head`).
