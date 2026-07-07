# Job Match Pipeline

> Job offer classifier and scorer against a professional profile.
> Legal collection → structured extraction (Gemini) → embeddings → scoring with explained strengths and risks → React UI.

![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## What problem does it solve?

Applying well is expensive: it means reading hundreds of job postings, guessing whether they fit your profile, filtering by real seniority and stack, and discarding ones that require residency you don't have. This project automates that filtering: every 12 hours it collects job offers from legal sources, extracts their requirements into a typed schema, and produces an explained ranking for your profile.

**This is not an aggregator.** It doesn't list jobs — it returns a *verdict* for each one: a 0-100 score, strengths and risks against your profile.

---

## Stack

**Backend:** Python 3.12 · Pydantic v2 · PostgreSQL 16 + pgvector · sentence-transformers (`bge-small-en-v1.5`) · Gemini 2.5 Flash · FastAPI · bcrypt + PyJWT · Airflow 2.10

**Frontend:** React 18 · TypeScript 5.5 · Vite 5.4 · Tailwind 3.4 · TanStack Query 5.56 · React Hook Form + Zod

**Infra:** Docker Compose · nginx · Prometheus + Loki + Promtail + Grafana

---

## Architecture

```
nginx (entrypoint)
 ├── :80  → frontend (React SPA, Vite)
 ├── :8000 → api (FastAPI)
 ├── :8080 → airflow-webserver
 └── :3000 → grafana
```

The backend pipeline follows Clean Architecture with four strict layers:

```
interfaces/   ← FastAPI + CLI (entrypoints)
application/  ← use cases (orchestration, no business logic)
domain/       ← entities, value objects, ports (ABCs)
infrastructure/ ← Postgres, Gemini, sentence-transformers, httpx
```

Dependencies always point inward: `infrastructure` implements the `domain` `ports`; `use cases` only know abstractions.

**Three intelligence layers, in increasing cost order:**

1. **Semantic** (local CPU, all offers) — coarse filter by cosine similarity.
2. **Structured extraction** (Gemini, only those that pass the filter) — extracts stack, seniority, modality into a validated `JobRequirements` Pydantic model.
3. **LLM scoring** (Gemini, top K) — returns `{score, verdict, strengths, risks}`.

See [`frontend/README.md`](frontend/README.md) for the frontend architecture.

---

## Data sources

| Source | Access | Notes |
|---|---|---|
| [Himalayas](https://himalayas.app/) | Public JSON API | filters by keyword, country, seniority |
| [Remotive](https://remotive.com/) | Official JSON API (`/api/remote-jobs`) | software-dev, devops, design |
| [Jobicy](https://jobicy.com/) | Public JSON API (`/api/v2/remote-jobs`) | remote, with geo/industry |
| [RemoteOK](https://remoteok.com/) | Public JSON API (`/api`) | remote tech, tags |
| [Arbeitnow](https://www.arbeitnow.com/) | Public JSON API (`/api/job-board-api`) | no key required, remote EU/global |
| [Adzuna](https://www.adzuna.com/) | JSON API (free key) | multi-country aggregator; requires `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` |
| [Jooble](https://jooble.org/) | JSON API (free key) | aggregator; requires `JOOBLE_API_KEY` |

Collection with `--source all`; sources that require a key are automatically skipped if not configured. Attribution is mandatory per terms of use. **Job offers are not redistributed to third parties**; the system is for personal use and always links to the original posting. Fetch frequency: every 12 hours, well below source limits.

---

## Quickstart

**Requirement:** Docker + Docker Compose.

```bash
git clone <repo>
cd job_match_pipeline

# 1. Configure environment
cp .env.example .env
# Edit .env:
#   GEMINI_API_KEY=...   (Google AI Studio, free tier is enough)
#   AIRFLOW_FERNET_KEY=... (python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
#   JWT_SECRET=...       (any long random string)

# 2. Start all services
docker compose up -d

# 3. Apply migrations (first time)
docker compose run --rm app alembic upgrade head

# 4. Register your profile
curl -X POST http://127.0.0.1:8000/profile \
     -H 'Content-Type: application/json' \
     -d '{"username": "daniel", "email": "tu@email.com", "password": "tu-password"}'
# → {"profile_id": "...", "username": "daniel", "matching": "scheduled"}

# 5. Get a JWT token
curl -X POST http://127.0.0.1:8000/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"username": "daniel", "password": "tu-password"}'
# → {"access_token": "...", "token_type": "bearer", "profile_id": "...", "username": "daniel"}

# 6. Trigger the pipeline (first time, without waiting 12h)
curl -X POST http://127.0.0.1:8000/jobs/refresh \
     -H "X-Internal-Api-Key: dev-internal-key"

# 7. Query matches (~30s later)
curl -H "Authorization: Bearer <token>" \
     'http://127.0.0.1:8000/matches?limit=10' | python -m json.tool
```

**Access URLs via nginx (all on `127.0.0.1`):**

| URL | Service |
|---|---|
| <http://127.0.0.1> | UI (React frontend) |
| <http://127.0.0.1:8000/docs> | Swagger / OpenAPI |
| <http://127.0.0.1:8080> | Airflow UI (`admin / admin`, local only) |
| <http://127.0.0.1:3000> | Grafana (anonymous Viewer) |

---

## CLI

Pipeline steps are also available as individual commands (useful for debugging or manual collection):

| Command | Description |
|---|---|
| `docker compose run --rm app python -m src.interfaces.cli.collect --source all --limit 10` | Collect and upsert job offers into the DB |
| `docker compose run --rm app python -m src.interfaces.cli.extract --limit 50 --print-results` | Extract `JobRequirements` via Gemini |
| `docker compose run --rm app python -m src.interfaces.cli.embed --limit 200` | Generate embeddings (sentence-transformers) |
| `docker compose run --rm app python -m src.interfaces.cli.score --profile-file sample_profile.json --print-top 5` | Score offers against the profile |

All commands are idempotent: re-running them does not duplicate state.

---

## Orchestration (Airflow)

The `job_match` DAG runs the 4 tasks in sequence, every 12 hours:

```
recolectar → extraer_requisitos → embeddings → score_perfiles
```

To start it:

```bash
docker compose up -d airflow-init      # initializes Airflow DB (one-shot)
docker compose up -d airflow-webserver airflow-scheduler
```

Go to <http://127.0.0.1:8080> with `admin/admin`, enable the `job_match` DAG, and trigger it manually the first time.

---

## API

**Matches**, **profile** (GET/PUT) and **user jobs** (schedule-run, searches) endpoints require `Authorization: Bearer <token>`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | API, DB and Gemini key status |
| **Auth** | | | |
| `POST` | `/auth/login` | — | Login with username/password → JWT |
| `POST` | `/auth/forgot-password` | — | Request password reset email |
| `POST` | `/auth/reset-password` | — | Confirm reset with token + new password |
| **Profile** | | | |
| `POST` | `/profile` | — | Register account (username, email, password) |
| `GET` | `/profile/{profile_id}` | ✓ | Get own profile data |
| `PUT` | `/profile/{profile_id}` | ✓ | Update profile and re-score |
| **Matches** | | | |
| `GET` | `/matches` | ✓ | List matches for the authenticated profile (optional filters) |
| `GET` | `/matches/{job_id}` | ✓ | Detail: score, verdict, strengths, risks, requirements |
| **Jobs (user)** | | | |
| `POST` | `/jobs/schedule-run` | ✓ | Schedule a search with filters via Airflow |
| `GET` | `/jobs/searches` | ✓ | Saved searches for the profile |
| `POST` | `/jobs/searches/{dag_run_id}/match-count` | — | Register match count for a scheduled search |
| `GET` | `/jobs/technologies` | — | Most frequent stack technologies |
| `GET` | `/jobs/schedule` | — | Next DAG run |
| `GET` | `/jobs/runs` | — | Latest runs with task status |
| **Jobs (ops/debug)** | | | |
| `POST` | `/jobs/refresh` | `X-Internal-Api-Key` | Trigger the full pipeline |
| `POST` | `/jobs/collect` | `X-Internal-Api-Key` | Collection only |
| `POST` | `/jobs/extract` | `X-Internal-Api-Key` | Requirements extraction only |
| `POST` | `/jobs/embed` | `X-Internal-Api-Key` | Embedding generation only |
| `POST` | `/jobs/score` | `X-Internal-Api-Key` | Scoring of all profiles only |

---

## Frontend

React SPA that consumes the API and displays matches with verdict, filters, detail drawer, and scheduled search setup. Dark/light theme, auto-refresh while the pipeline runs.

See [`frontend/README.md`](frontend/README.md) for stack, routes, structure, and how to extend it.

---

## Observability

The observability stack starts alongside `docker compose up -d`:

- **Prometheus** — scrapes `/metrics` on the API (latencies, counts per endpoint via `prometheus-fastapi-instrumentator`). Config: `observability/prometheus/prometheus.yml`.
- **Loki + Promtail** — centralizes logs from all containers. Config: `observability/loki/` and `observability/promtail/`.
- **Grafana** — dashboards in `observability/grafana/dashboards/`. Anonymous access in `Viewer` role (can view, not edit). URL: <http://127.0.0.1:3000>.

---

## Tests

```bash
docker compose run --rm app pytest -v         # 172 tests, offline-first
docker compose run --rm app ruff check src tests   # lint
```

Offline-first tests (mocks via `unittest.mock.patch` and `app.dependency_overrides`). No real DB dependency or external calls in the main suite.

---

## Security (local demo posture)

- All ports bound to `127.0.0.1` (not exposed to the network).
- JWT Bearer (bcrypt + PyJWT) on user endpoints; pipeline ops endpoints (`/jobs/collect`, `/jobs/extract`, `/jobs/embed`, `/jobs/score`, `/jobs/refresh`) require the `X-Internal-Api-Key` header shared between the API and the Airflow DAG.
- Grafana anonymous in `Viewer` role (cannot edit datasources or dashboards).
- Security headers in nginx: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `server_tokens off`.
- External URLs in the frontend sanitized to `http/https` via `safeHref` (prevents `javascript:` in scraped job offer links).
- Scheduled search `filters` validated against `MatchFilters` Pydantic (no arbitrary JSON persisted).
- HTTPS/TLS, restricted CORS and rate-limiting: **out of scope** (local single-user demo).

---

## Disclaimers

- The `llm_score` and risks are **indicative**. The final decision to apply belongs to the user; the system narrows the list, it does not decide for you.
- Portfolio project + personal use. Not a SaaS product; no production deployment.
- Displayed offers link to their original source; this repo does not store or redistribute jobs to third parties.

---

## License

MIT — see [LICENSE](LICENSE).

<!--
PRE-PUBLICATION CHECKLIST (complete before making the repo public)
==================================================================
Videos (upload to unlisted YouTube, paste URLs in Demo section):
  [ ] Video 1 — Pipeline (≤2 min): docker compose up → Airflow → trigger → logs → psql count
  [ ] Video 2 — Matches (≤2 min): register → login → POST /jobs/refresh → UI with matches + detail

Repo:
  [ ] gitleaks detect --no-banner (no hits)
  [ ] git ls-files | grep -i env (verify .env is not tracked)
  [ ] Public repo on GitHub
  [ ] Topics: python, airflow, pydantic, pgvector, gemini, fastapi, react, llm, job-search
  [ ] Description: "Pipeline that collects remote job offers, extracts requirements with LLM and matches them against your profile"
  [ ] Pin on profile
-->
