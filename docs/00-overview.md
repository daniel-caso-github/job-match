# 00 · Overview — Job Match Pipeline

Documento maestro. Funciona como índice y referencia transversal. Cada fase tiene su propio doc con la guía ejecutable de implementación.

---

## 1. Qué resuelve

**Problema real**: dado un perfil profesional, decidir a qué ofertas de empleo postular sin tener que leer cientos de publicaciones a mano.

**Salida del sistema**: por cada oferta procesada produce un *veredicto de ajuste* — puntuación 0-100, requisitos extraídos, fortalezas y riesgos explicados. Es una lista priorizada de a qué postular, con razonamiento. **No es un agregador** ni un buscador de empleos.

**Público objetivo**: el propio autor (uso personal). Genérico para cualquier dev que rellene el formulario con su perfil.

**Por qué este proyecto en portafolio**: combina extracción estructurada + clasificación aumentada (categorías menos saturadas que "otro RAG"), usa Airflow de forma genuina, y resuelve un problema vivido en primera persona.

---

## 2. Diagrama del pipeline (DAG cada 12h)

```
┌────────────┐  ┌──────────┐  ┌─────────────────┐  ┌──────────┐
│ recolectar │─▶│deduplicar│─▶│extraer_requisitos│─▶│embeddings│─┐
└────────────┘  └──────────┘  └─────────────────┘  └──────────┘ │
 Himalayas API   por hash      Gemini + Pydantic    perfil y    │
 + RSS feeds    (source+url)   (JSON estructurado)  oferta      │
                                                                ▼
   API consulta   ┌──────────┐  ┌────────────┐  ┌──────────────────┐
   (top matches)◄─│persistir │◄─│ score_llm  │◄─│ score_semántico  │
                  └──────────┘  └────────────┘  └──────────────────┘
                   Postgres      fit + riesgos    similitud coseno
                                 explicados        (ranking grueso)
```

Detalle de cada task → `phase-5-orquestacion.md`.

---

## 3. Las tres capas de inteligencia

| # | Capa | Para qué | Costo | Cuándo se ejecuta |
|---|------|----------|-------|-------------------|
| 1 | **Scoring semántico** (embeddings + coseno) | Filtrar ofertas irrelevantes antes de gastar LLM | Muy bajo (CPU local) | Sobre **todas** las ofertas nuevas |
| 2 | **Extracción estructurada** (Gemini + Pydantic) | Convertir descripción libre en `JobRequirements` validado | Medio (1 llamada Gemini por oferta) | Solo si `semantic_score ≥ SEMANTIC_THRESHOLD` |
| 3 | **Scoring LLM** (Gemini con perfil + requisitos) | Producir `score 0-100` + fortalezas + riesgos | Medio (1 llamada Gemini por oferta filtrada) | Solo sobre el top K del paso 1 |

**Decisión de costo (orden importa)**: el barato va primero y descarta lo irrelevante; solo las que superan el umbral pasan a Gemini. Con `SEMANTIC_THRESHOLD ≈ 0.65` y top K ≈ 20-30 ofertas/corrida, el tier gratuito de Gemini alcanza de sobra (corremos cada 12h).

---

## 4. Modelo de datos consolidado

Postgres 16 con extensión `pgvector` e índice HNSW. **El schema se define con SQLAlchemy 2.0 declarative** (`src/storage/models.py`) y se aplica con **Alembic** (`alembic upgrade head`) — sin `init.sql`. El SQL equivalente queda implícito.

Resumen de los modelos ORM (fuente de verdad: `src/storage/models.py`):

```python
class Job(Base):
    __tablename__ = "jobs"
    id:            Mapped[str]                 = mapped_column(primary_key=True)       # hash(source+url)
    source:        Mapped[str]                                                          # 'himalayas' | 'remotive' | ...
    url:           Mapped[str]   = mapped_column(Text)                                  # enlace de vuelta (legal)
    title:         Mapped[str]   = mapped_column(Text)
    company:       Mapped[str | None] = mapped_column(Text)
    raw_text:      Mapped[str]   = mapped_column(Text)
    requirements:  Mapped[dict | None] = mapped_column(JSONB)                           # JobRequirements (fase 2)
    embedding:     Mapped[list[float] | None] = mapped_column(Vector(384))              # bge-small-en-v1.5
    posted_at:     Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    country:       Mapped[str | None]
    remote:        Mapped[bool | None]
    fetched_at:    Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    __table_args__ = (
        Index("jobs_embedding_hnsw", "embedding",
              postgresql_using="hnsw",
              postgresql_ops={"embedding": "vector_cosine_ops"}),
        Index("jobs_fetched_at", "fetched_at"),
    )

class Profile(Base):
    __tablename__ = "profiles"
    id:         Mapped[str]   = mapped_column(primary_key=True)
    form_data:  Mapped[dict]  = mapped_column(JSONB)                                    # ProfileForm (fase 4)
    embedding:  Mapped[list[float] | None] = mapped_column(Vector(384))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                                 server_default=func.now(),
                                                 onupdate=func.now())

class Match(Base):
    __tablename__ = "matches"
    profile_id:    Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    job_id:        Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    semantic_score: Mapped[float | None]
    llm_score:     Mapped[int | None]
    verdict:       Mapped[dict | None] = mapped_column(JSONB)                            # Verdict (fase 3)
    scored_at:     Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    __table_args__ = (Index("matches_llm_score", "profile_id", "llm_score"),)
```

Migraciones: una sola revision inicial (`alembic/versions/<hash>_initial_schema.py`) que ejecuta `CREATE EXTENSION IF NOT EXISTS vector` y crea las tres tablas + los cuatro índices. Cambios futuros al schema → `alembic revision --autogenerate -m "..."` y revisar el diff antes de `alembic upgrade head`.

Schemas Pydantic relacionados (no son ORM, son validación de datos): `phase-2-extraccion.md::JobRequirements`, `phase-3-matching.md::Verdict`, `phase-4-api-perfil.md::ProfileForm`. La app valida con Pydantic en el borde y persiste con ORM.

---

## 5. Estructura del repositorio

```
job_match_pipeline/
├── dags/
│   └── job_match.py              # DAG cada 12h (Airflow)
├── src/
│   ├── sources/
│   │   ├── base.py               # Source (ABC) + RawJob (Pydantic)
│   │   ├── himalayas.py          # cliente API JSON
│   │   └── remotive.py           # parser RSS
│   ├── extraction/
│   │   ├── schema.py             # JobRequirements (Pydantic)
│   │   └── extractor.py          # Gemini → JSON validado
│   ├── matching/
│   │   ├── embedder.py           # bge-small-en-v1.5
│   │   ├── semantic.py           # similitud coseno (pgvector)
│   │   └── llm_scorer.py         # Gemini: Verdict (fit + riesgos)
│   ├── storage/
│   │   ├── database.py           # engine + SessionLocal + session_scope
│   │   ├── models.py             # SQLAlchemy 2.0: Job / Profile / Match
│   │   └── pgvector_io.py        # upsert idempotente + queries ORM (fase 3)
│   ├── profile/
│   │   └── form.py               # ProfileForm + validación
│   └── api/
│       └── main.py               # FastAPI + Swagger
├── tests/
├── docs/                         # este directorio
├── docker-compose.yml            # Postgres+pgvector, Airflow (fase 5)
├── alembic.ini                   # Alembic config (sqlalchemy.url se inyecta desde env)
├── alembic/                      # migraciones (env.py + versions/)
├── pyproject.toml + uv.lock      # uv-managed deps
├── .env.example                  # GEMINI_API_KEY, DATABASE_URL, ...
└── README.md
```

---

## 6. Stack

| Capa | Tecnología | Para qué |
|---|---|---|
| Orquestación | Airflow 2.x | DAG cada 12h, retries, idempotencia |
| API | FastAPI + Uvicorn | endpoints + Swagger auto |
| Validación | Pydantic v2 | esquemas (`RawJob`, `JobRequirements`, `Verdict`, `ProfileForm`) |
| LLM | Gemini (`google-genai`) | extracción estructurada + scoring |
| Embeddings | `sentence-transformers` + `BAAI/bge-small-en-v1.5` | vectores de 384 dims, CPU |
| ORM | **SQLAlchemy 2.0** (declarative + `Mapped`) + `pgvector.sqlalchemy.Vector` | modelos de Job/Profile/Match |
| Migraciones | **Alembic** | esquema versionado, una revisión inicial |
| DB | Postgres 16 + `pgvector` (HNSW) | jobs, profiles, matches |
| Driver Postgres | `psycopg[binary]` v3 | DBAPI usado por SQLAlchemy |
| HTTP client | `httpx` | Himalayas API + Remotive API |
| Tests | `pytest` + `httpx.AsyncClient` | unit + integration |
| Infra | Docker Compose | Postgres, Airflow webserver/scheduler |

Versiones pineadas → `pyproject.toml` + `uv.lock`.

---

## 7. Fuentes de datos y términos de uso

**Solo fuentes legales con API o RSS oficial.** Sin scraping de plataformas que lo prohíben (LinkedIn et al.).

| Fuente | Acceso | Notas |
|---|---|---|
| Himalayas | API JSON pública (sin key) | filtros por keyword, country, seniority, type, timezone |
| Remotive | API JSON oficial (`/api/remote-jobs`) | filtros por categoría/search; delay de 24h; el RSS fue descontinuado |
| We Work Remotely | RSS oficial por categoría | múltiples feeds de programación |
| Jobicy | API + RSS (sin key) | filtros por región, industria, keyword |

**Reglas comunes (incorporadas al diseño):**
- Enlazar **siempre** a la oferta original (campo `url`).
- Mencionar la fuente al exponer datos (`source_attribution` en `/matches` response).
- **No** redistribuir empleos a terceros (Google Jobs, LinkedIn, etc.).
- Frecuencia: no más de 1 consulta/hora por fuente. Cada 12h queda muy por debajo.

Esta app es **uso personal**, no una bolsa pública → queda holgadamente dentro de términos. Documentado además en el README.

Fase 1 implementa solo Himalayas + Remotive. We Work Remotely y Jobicy quedan como extensión natural (mismo `Source` ABC).

---

## 8. Glosario

| Término | Significado |
|---|---|
| `RawJob` | Oferta normalizada al esquema común tras recolectar (fase 1). |
| `JobRequirements` | Resultado de la extracción estructurada (fase 2). |
| `embedding` | Vector denso de 384 dims que representa el contenido de un texto. |
| `semantic_score` | Similitud coseno entre embedding del perfil y del job (0..1). |
| `llm_score` | Puntuación 0..100 producida por Gemini comparando perfil vs. requisitos. |
| `Verdict` | `{score, strengths, risks}` — explicación del fit. |
| `fit` | Sinónimo coloquial del veredicto: qué tan bien encaja perfil con oferta. |
| `idempotente` | Re-ejecutar la operación N veces produce el mismo estado (gracias a `job_id = hash(source+url)` y upserts). |

---

## 9. Cómo cada fase contribuye al pipeline

| Fase | Doc | Pieza del pipeline | Tablas tocadas |
|---|---|---|---|
| 1 | `phase-1-recoleccion.md` | `recolectar` + `deduplicar` | escribe `jobs` (sin requirements, sin embedding) |
| 2 | `phase-2-extraccion.md` | `extraer_requisitos` | actualiza `jobs.requirements` |
| 3 | `phase-3-matching.md` | `embeddings` + `score_semantico` + `score_llm` + `persistir` | actualiza `jobs.embedding`, escribe `matches` |
| 4 | `phase-4-api-perfil.md` | (no es task del DAG) `POST /profile`, `GET /matches`, `POST /jobs/refresh` | escribe `profiles`, lee `matches` |
| 5 | `phase-5-orquestacion.md` | DAG + Docker + migraciones | infraestructura completa |
| 6 | `phase-6-readme-demo.md` | README + videos demo | — |

---

## 10. Riesgos y notas de honestidad (a reflejar en README)

- **Términos de fuentes**: atribución obligatoria, no redistribución. Documentar uso personal.
- **Cuota de Gemini**: scoring semántico antes del LLM mantiene dentro del tier gratuito. Cachear extracciones por `job_id`.
- **Calidad de extracción**: Pydantic + reintento mitiga; mostrar `raw_text` junto al veredicto en la UI/API para que el usuario verifique.
- **No inflar el alcance**: proyecto de portafolio con pipeline completo y demo en video; no afirmar "deploy productivo" ni "miles de ofertas" si no es el caso.
- **Sesgo del scoring**: el `llm_score` es orientativo, no verdad absoluta. Comunicarlo en el README.
