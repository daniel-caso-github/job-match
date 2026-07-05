# Job Match Pipeline

> Clasificador y scoring de ofertas de empleo según un perfil profesional.
> Recolección legal → extracción estructurada (Gemini) → embeddings → scoring con fortalezas y riesgos explicados → UI React.

![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## ¿Qué resuelve?

Postular bien es caro: implica leer cientos de ofertas, intuir si encajan con tu perfil, filtrar por seniority y stack reales, y descartar las que piden residencia que no tenés. Este proyecto automatiza ese filtrado: cada 12 horas recolecta ofertas de fuentes legales, extrae sus requisitos a un schema tipado, y produce un ranking explicado para tu perfil.

**No es un agregador.** No lista ofertas — devuelve un *veredicto* por cada una: puntuación 0-100, fortalezas y riesgos respecto a tu perfil.

---

## Stack

**Backend:** Python 3.12 · Pydantic v2 · PostgreSQL 16 + pgvector · sentence-transformers (`bge-small-en-v1.5`) · Gemini 2.5 Flash · FastAPI · bcrypt + PyJWT · Airflow 2.10

**Frontend:** React 18 · TypeScript 5.5 · Vite 5.4 · Tailwind 3.4 · TanStack Query 5.56 · React Hook Form + Zod

**Infra:** Docker Compose · nginx · Prometheus + Loki + Promtail + Grafana

---

## Arquitectura

```
nginx (entrypoint)
 ├── :80  → frontend (React SPA, Vite)
 ├── :8000 → api (FastAPI)
 ├── :8080 → airflow-webserver
 └── :3000 → grafana
```

El pipeline backend sigue Clean Architecture con cuatro capas estrictas:

```
interfaces/   ← FastAPI + CLI (entrypoints)
application/  ← use cases (orquestación, sin lógica de negocio)
domain/       ← entidades, value objects, ports (ABCs)
infrastructure/ ← Postgres, Gemini, sentence-transformers, httpx
```

Las dependencias apuntan siempre hacia adentro: `infrastructure` implementa los `ports` del `domain`; los `use cases` solo conocen abstracciones.

**Tres capas de inteligencia, en orden de costo creciente:**

1. **Semántica** (CPU local, todas las ofertas) — filtro grueso por similitud coseno.
2. **Extracción estructurada** (Gemini, solo las que pasan el filtro) — extrae stack, seniority, modalidad a `JobRequirements` Pydantic validado.
3. **Scoring LLM** (Gemini, top K) — devuelve `{score, verdict, strengths, risks}`.

Ver [`frontend/README.md`](frontend/README.md) para la arquitectura del frontend.

---

## Fuentes de datos

| Fuente | Acceso | Notas |
|---|---|---|
| [Himalayas](https://himalayas.app/) | API JSON pública | filtros por keyword, country, seniority |
| [Remotive](https://remotive.com/) | API JSON oficial (`/api/remote-jobs`) | software-dev, devops, design |
| [Jobicy](https://jobicy.com/) | API JSON pública (`/api/v2/remote-jobs`) | remoto, con geo/industry |
| [RemoteOK](https://remoteok.com/) | API JSON pública (`/api`) | tech remoto, tags |
| [Arbeitnow](https://www.arbeitnow.com/) | API JSON pública (`/api/job-board-api`) | sin key, remoto EU/global |
| [Adzuna](https://www.adzuna.com/) | API JSON (key gratuita) | agregador multi-país; requiere `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` |
| [Jooble](https://jooble.org/) | API JSON (key gratuita) | agregador; requiere `JOOBLE_API_KEY` |

Recolección con `--source all`; las fuentes que requieren key se omiten automáticamente si no está configurada. Atribución obligatoria por términos de uso. **No se redistribuyen ofertas a terceros**; el sistema es de uso personal y enlaza siempre al posting original. Frecuencia de fetch: cada 12 horas, muy por debajo del límite de las fuentes.

---

## Quickstart

**Requisito:** Docker + Docker Compose.

```bash
git clone <repo>
cd job_match_pipeline

# 1. Configurar entorno
cp .env.example .env
# Editar .env:
#   GEMINI_API_KEY=...   (Google AI Studio, tier gratuito alcanza)
#   AIRFLOW_FERNET_KEY=... (python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
#   JWT_SECRET=...       (cualquier string largo y aleatorio)

# 2. Levantar todos los servicios
docker compose up -d

# 3. Aplicar migraciones (primera vez)
docker compose run --rm app alembic upgrade head

# 4. Registrar tu perfil
curl -X POST http://127.0.0.1:8000/profile \
     -H 'Content-Type: application/json' \
     -d '{"username": "daniel", "email": "tu@email.com", "password": "tu-password"}'
# → {"profile_id": "...", "username": "daniel", "matching": "scheduled"}

# 5. Obtener un token JWT
curl -X POST http://127.0.0.1:8000/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"username": "daniel", "password": "tu-password"}'
# → {"access_token": "...", "token_type": "bearer", "profile_id": "...", "username": "daniel"}

# 6. Disparar el pipeline (primera vez, sin esperar 12h)
curl -X POST http://127.0.0.1:8000/jobs/refresh

# 7. Consultar matches (~30s después)
curl -H "Authorization: Bearer <token>" \
     'http://127.0.0.1:8000/matches?limit=10' | python -m json.tool
```

**URLs de acceso vía nginx (todas en `127.0.0.1`):**

| URL | Servicio |
|---|---|
| <http://127.0.0.1> | UI (frontend React) |
| <http://127.0.0.1:8000/docs> | Swagger / OpenAPI |
| <http://127.0.0.1:8080> | Airflow UI (`admin / admin`, solo local) |
| <http://127.0.0.1:3000> | Grafana (anónimo Viewer) |

---

## CLI

Los pasos del pipeline también están disponibles como comandos individuales (útil para debug o recolección manual):

| Comando | Descripción |
|---|---|
| `docker compose run --rm app python -m src.interfaces.cli.collect --source all --limit 10` | Recolecta y upsertea ofertas en BD |
| `docker compose run --rm app python -m src.interfaces.cli.extract --limit 50 --print-results` | Extrae `JobRequirements` via Gemini |
| `docker compose run --rm app python -m src.interfaces.cli.embed --limit 200` | Genera embeddings (sentence-transformers) |
| `docker compose run --rm app python -m src.interfaces.cli.score --profile-file sample_profile.json --print-top 5` | Scorea ofertas contra el perfil |

Todos son idempotentes: re-ejecutarlos no duplica estado.

---

## Orquestación (Airflow)

El DAG `job_match` corre las 4 tasks en secuencia, cada 12 horas:

```
recolectar → extraer_requisitos → embeddings → score_perfiles
```

Para levantarlo:

```bash
docker compose up -d airflow-init      # inicializa BD de Airflow (one-shot)
docker compose up -d airflow-webserver airflow-scheduler
```

Accedé a <http://127.0.0.1:8080> con `admin/admin`, habilitá el DAG `job_match` y disparalo manualmente la primera vez.

---

## API

Los endpoints de **matches**, **profile** (GET/PUT) y **jobs de usuario** (schedule-run, searches) requieren `Authorization: Bearer <token>`.

| Método | Path | Auth | Descripción |
|---|---|---|---|
| `GET` | `/health` | — | Estado de la API, BD y Gemini key |
| **Auth** | | | |
| `POST` | `/auth/login` | — | Login con username/password → JWT |
| **Perfil** | | | |
| `POST` | `/profile` | — | Registrar cuenta (username, email, password) |
| `GET` | `/profile/{profile_id}` | ✓ | Obtener datos del perfil propio |
| `PUT` | `/profile/{profile_id}` | ✓ | Actualizar perfil y re-scorear |
| **Matches** | | | |
| `GET` | `/matches` | ✓ | Lista matches del perfil autenticado (filtros opcionales) |
| `GET` | `/matches/{job_id}` | ✓ | Detalle: score, veredicto, fortalezas, riesgos, requisitos |
| **Jobs (usuario)** | | | |
| `POST` | `/jobs/schedule-run` | ✓ | Programa una búsqueda con filtros vía Airflow |
| `GET` | `/jobs/searches` | ✓ | Búsquedas guardadas del perfil |
| `POST` | `/jobs/searches/{dag_run_id}/match-count` | — | Registra cantidad de matches de una búsqueda programada |
| `GET` | `/jobs/technologies` | — | Stack technologies más frecuentes |
| `GET` | `/jobs/schedule` | — | Próxima corrida del DAG |
| `GET` | `/jobs/runs` | — | Últimas corridas con estado de tasks |
| **Jobs (ops/debug)** | | | |
| `POST` | `/jobs/refresh` | — | Dispara el pipeline completo |
| `POST` | `/jobs/collect` | — | Solo recolección |
| `POST` | `/jobs/extract` | — | Solo extracción de requisitos |
| `POST` | `/jobs/embed` | — | Solo generación de embeddings |
| `POST` | `/jobs/score` | — | Solo scoring de todos los perfiles |

---

## Frontend

SPA React que consume la API y muestra matches con veredicto, filtros, drawer de detalle y programación de búsquedas. Tema dark/light, auto-refresh mientras corre el pipeline.

Ver [`frontend/README.md`](frontend/README.md) para stack, rutas, estructura y cómo extender.

---

## Observabilidad

El stack de observabilidad levanta junto con `docker compose up -d`:

- **Prometheus** — scrape de `/metrics` en la API (latencias, conteos por endpoint via `prometheus-fastapi-instrumentator`). Config: `observability/prometheus/prometheus.yml`.
- **Loki + Promtail** — centraliza los logs de todos los contenedores. Config: `observability/loki/` y `observability/promtail/`.
- **Grafana** — dashboards en `observability/grafana/dashboards/`. Acceso anónimo en rol `Viewer` (puede ver, no editar). URL: <http://127.0.0.1:3000>.

---

## Tests

```bash
docker compose run --rm app pytest -v         # 21 módulos, offline-first
docker compose run --rm app ruff check src tests   # lint
```

Tests offline-first (mocks via `unittest.mock.patch` e `app.dependency_overrides`). Sin dependencia de BD real ni llamadas externas en el suite principal.

---

## Seguridad (postura demo-local)

- Todos los puertos bindeados a `127.0.0.1` (no expuestos a red).
- JWT Bearer (bcrypt + PyJWT) en endpoints de usuario; ops/debug no autenticados (sin rate-limit por diseño local).
- Grafana anónimo en rol `Viewer` (no puede editar datasources ni dashboards).
- Headers de seguridad en nginx: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `server_tokens off`.
- URLs externas en el frontend sanitizadas a `http/https` via `safeHref` (evita `javascript:` en links de ofertas scrapeadas).
- `filters` de búsquedas programadas validados contra `MatchFilters` Pydantic (no se persiste JSON arbitrario).
- HTTPS/TLS, CORS restringido y rate-limiting: **fuera de scope** (demo local single-user).

---

## Disclaimers

- El `llm_score` y los riesgos son **orientativos**. La decisión final de postular es del usuario; el sistema reduce la lista, no decide por vos.
- Proyecto de portafolio + uso personal. No es un producto SaaS ni hay deploy productivo asociado.
- Las ofertas mostradas se enlazan a su fuente original; este repo no almacena ni redistribuye empleos a terceros.

---

## Licencia

MIT — ver [LICENSE](LICENSE).

<!--
CHECKLIST PRE-PUBLICACIÓN (completar antes de hacer el repo público)
====================================================================
Videos (subir a YouTube no listado, pegar URLs en sección Demo):
  [ ] Video 1 — Pipeline (≤2 min): docker compose up → Airflow → trigger → logs → psql count
  [ ] Video 2 — Matches (≤2 min): registro → login → POST /jobs/refresh → UI con matches + detalle

Repo:
  [ ] gitleaks detect --no-banner (sin hits)
  [ ] git ls-files | grep -i env (verificar que .env no está trackeado)
  [ ] Repo público en GitHub
  [ ] Topics: python, airflow, pydantic, pgvector, gemini, fastapi, react, llm, job-search
  [ ] Descripción: "Pipeline que recolecta ofertas remotas, extrae requisitos con LLM y matchea contra tu perfil"
  [ ] Pin en perfil
-->
