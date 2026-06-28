# Fase 6 · README y demo

**Tiempo estimado:** 0.5 día
**Entregable demostrable:** `README.md` publicable + 2 videos cortos (≤2 min cada uno) que un reclutador o entrevistador pueda mirar en menos de 5 minutos.

---

## 1. Objetivo

Empaquetar el proyecto para que sea **legible en frío** por alguien que llega por GitHub:
- Entienda **qué resuelve** en 30 segundos.
- Pueda **levantarlo en local** en 5 comandos.
- Vea el **pipeline funcionando** en video sin tener que compilar nada.
- Quede claro qué fuentes legales se usaron y qué disclaimers aplican.

Esta fase no escribe código nuevo. Es presentación.

---

## 2. Estructura del `README.md`

```markdown
# Job Match Pipeline

> Clasificador y scoring de ofertas de empleo según un perfil profesional.
> Recolección legal → extracción estructurada (Gemini) → embeddings → scoring con
> fortalezas y riesgos explicados.

![swagger demo](docs/img/swagger.png)

---

## ¿Qué resuelve?

Postular a empleo bien es caro: implica leer cientos de ofertas, intuir si encajan,
filtrar por seniority y stack reales, y descartar las que piden residencia que
no tienes. Este proyecto automatiza ese filtrado: cada 12 horas recolecta ofertas
de fuentes legales, extrae sus requisitos a un schema tipado, y produce un ranking
explicado para tu perfil.

**No es un agregador.** No lista ofertas — devuelve un *veredicto* por cada una:
puntuación 0-100, fortalezas y riesgos respecto a tu perfil.

## Stack

Python · Pydantic v2 · Postgres + pgvector · sentence-transformers (bge-small) ·
Gemini · FastAPI · Airflow · Docker Compose.

## Arquitectura

```
recolectar → deduplicar → extraer_requisitos → embeddings →
score_semántico → score_llm → persistir
```

Tres capas de inteligencia, en orden de costo creciente:
1. **Semántica** (CPU local, todas las ofertas) — filtro grueso.
2. **Extracción estructurada** (Gemini, solo las que pasan el filtro).
3. **Scoring LLM** (Gemini, top K) — devuelve `{score, strengths, risks}`.

Detalles de diseño y plan de implementación: ver [`docs/`](docs/).

## Fuentes de datos

| Fuente | Acceso | Notas |
|---|---|---|
| [Himalayas](https://himalayas.app/) | API JSON pública | filtros por keyword, country, seniority |
| [Remotive](https://remotive.com/)   | RSS oficial      | software-dev, devops |

Atribución obligatoria por términos de uso de las fuentes. **No se redistribuyen
ofertas a terceros**; el sistema es de uso personal y enlaza siempre al posting
original. Frecuencia de fetch: cada 12 horas, muy por debajo del límite.

## Quickstart

```bash
git clone <repo>
cd job_match_pipeline
cp .env.example .env       # rellena GEMINI_API_KEY y genera fernet/secret keys
docker compose up -d       # arranca Postgres+pgvector, Airflow, API

# crear tu perfil
curl -X POST http://127.0.0.1:8000/profile \
     -H 'content-type: application/json' \
     -d @sample_profile.json

# disparar pipeline (primera vez, sin esperar 12h)
curl -X POST http://127.0.0.1:8000/jobs/refresh

# consultar matches
curl 'http://127.0.0.1:8000/matches?profile_id=me&limit=10' | jq
```

Swagger: <http://127.0.0.1:8000/docs>
Airflow UI: <http://127.0.0.1:8080> (admin/admin — solo local).

## Tests

```bash
pip install -r requirements.txt
pytest
```

## Decisiones de diseño

Cada fase del proyecto tiene su doc con decisiones, schemas y código:

- [00 · Overview](docs/00-overview.md)
- [Fase 1 · Recolección](docs/phase-1-recoleccion.md)
- [Fase 2 · Extracción](docs/phase-2-extraccion.md)
- [Fase 3 · Matching](docs/phase-3-matching.md)
- [Fase 4 · API + Perfil](docs/phase-4-api-perfil.md)
- [Fase 5 · Orquestación](docs/phase-5-orquestacion.md)
- [Fase 6 · README y demo](docs/phase-6-readme-demo.md)

## Disclaimers

- El `llm_score` y los riesgos son **orientativos**. La decisión final de postular
  es del usuario; el sistema reduce la lista, no decide por ti.
- Proyecto de portafolio + uso personal. No es un producto SaaS ni hay deploy
  productivo asociado.
- Las ofertas mostradas se enlazan a su fuente original; este repo no almacena ni
  redistribuye empleos a terceros.

## Licencia

MIT.
```

---

## 3. Activos visuales

Crear bajo `docs/img/`:

| Archivo | Contenido | Captura desde |
|---|---|---|
| `swagger.png` | Swagger UI con los 5 endpoints expandidos | `http://127.0.0.1:8000/docs` |
| `airflow-dag.png` | Vista del DAG `job_match` con tasks en verde | Airflow UI tras 1 corrida |
| `match-detail.png` | Response JSON de `/matches/{job_id}` con verdict | Postman/Insomnia o terminal |

Tamaño objetivo: ≤ 200 KB por imagen (comprimir con `pngquant` o `tinypng`).

---

## 4. Videos demo

Dos videos cortos en formato horizontal 1920×1080, ≤ 2 minutos cada uno. Subir a YouTube como "no listado" y enlazar desde el README (sección Quickstart o un bloque dedicado).

### Video 1 — Pipeline (≤ 2 min)

**Guion:**
1. (0:00-0:15) Pantalla del README: "Esto es Job Match Pipeline. Cada 12h recolecta ofertas y las puntúa contra mi perfil."
2. (0:15-0:30) Terminal: `docker compose up -d` → mostrar containers arriba.
3. (0:30-0:50) Airflow UI: navegar al DAG `job_match`, mostrar grafo de las 4 tasks (`recolectar → extraer → embeddings → score_perfiles`).
4. (0:50-1:20) Trigger manual del DAG. Avance en vivo (×4 speed si hace falta). Logs de `recolectar` mostrando ofertas pulled de Himalayas y Remotive.
5. (1:20-1:50) Logs de `extraer_requisitos` mostrando JSON validado por Pydantic.
6. (1:50-2:00) `psql` rápido: `SELECT count(*), source FROM jobs GROUP BY source;`.

### Video 2 — Matches (≤ 2 min)

**Guion:**
1. (0:00-0:15) "Ahora vamos a ver el output: pasar mi perfil y obtener el ranking."
2. (0:15-0:35) Swagger: `POST /profile` con un body pre-rellenado. Response 201.
3. (0:35-1:00) `GET /matches?profile_id=me&limit=10`. Recorrer 2-3 resultados, leer `llm_score` y `verdict`.
4. (1:00-1:35) Abrir el top 1: `GET /matches/{job_id}` — mostrar `requirements` extraídos + `raw_text` (verificable) + `verdict.risks`.
5. (1:35-2:00) Cierre: "Esto corre solo cada 12h. Cuando entro al match, ya tengo el contexto para decidir si postular en 30 segundos en vez de 10 minutos."

**Producción:**
- Grabar con OBS o ScreenStudio. Cursor visible. Zoom en regiones de interés.
- Subtitular automáticamente en YouTube (no hace falta voz en off si no se quiere).
- Si se quiere voz: hablar pausado, sin jerga innecesaria.

---

## 5. Checklist final antes de publicar

Pre-publicación:

- [ ] `.env` y cualquier archivo con secrets en `.gitignore` (verificar `git status` y `git ls-files | grep env`).
- [ ] `GEMINI_API_KEY` **no** aparece en commits (revisar con `git log -p | grep -i gemini` o usar `gitleaks`).
- [ ] `pytest` pasa en local con `pip install -r requirements.txt`.
- [ ] `docker compose up -d` arranca sin error desde cero (`docker compose down -v` y volver a subir).
- [ ] Atribución de Himalayas y Remotive visible en README **y** en el response de `/matches` (`source_attribution`).
- [ ] Disclaimers en README (scoring orientativo, no SaaS, no redistribución).
- [ ] 3 imágenes en `docs/img/` y 2 videos enlazados.
- [ ] `sample_profile.json` en la raíz para que el quickstart funcione.
- [ ] LICENSE (MIT) presente.
- [ ] README abre bien en GitHub web (preview local con `grip` o similar).

Publicación:

- [ ] Repo público en GitHub.
- [ ] Topics: `python`, `airflow`, `pydantic`, `pgvector`, `gemini`, `fastapi`, `llm`, `job-search`.
- [ ] Descripción del repo: la línea hero del README (≤ 120 chars).
- [ ] Pin del repo en el perfil.
- [ ] Enlace al repo en el CV / LinkedIn / portfolio.

Post-publicación (opcional, recomendado para entrevistas):

- [ ] Un post de blog técnico (~5 min lectura) explicando *por qué* el orden semántico → LLM importa para el costo.
- [ ] Sección "Lo que NO hice" en el README (consciente del alcance) — ver `phase-5-orquestacion.md` §10.

---

## 6. Cómo defenderlo en entrevista

Tres puntos fuertes a remarcar (uno por bloque del pipeline):

1. **Extracción estructurada con Pydantic** — "El LLM devuelve JSON validado; si no valida, reintenta con el error como feedback. Es lo mismo que hago con cualquier input externo en backend tradicional."
2. **Orden de las capas de scoring** — "El barato va primero. Embeddings en CPU descartan el 80% del corpus antes de gastar una sola llamada a Gemini. Así me mantengo en el tier gratuito sin scope creep."
3. **Idempotencia end-to-end** — "Cada task del DAG es safe-to-retry. `id = hash(source+url)`, upserts en todo, y cada task consulta su propio estado en la BD en vez de confiar en el output de la anterior. Si crashea a mitad, no pasa nada."

Anti-pattern a evitar: presentarlo como "otro proyecto con LLM". Es un **pipeline de datos** que usa LLM como una herramienta más, no como el protagonista.

---

## 7. Criterios de aceptación

- [ ] `README.md` cubre todas las secciones del esquema anterior.
- [ ] 3 capturas en `docs/img/` (PNG, < 200 KB cada una).
- [ ] 2 videos subidos a YouTube (no listados), enlaces en el README.
- [ ] `sample_profile.json` funcional (probado el quickstart desde cero).
- [ ] Repo público, sin secretos, con LICENSE.
- [ ] `gitleaks detect --no-banner` (o equivalente) no reporta hits.

---

## 8. Lo que NO se hace en esta fase

- Marketing / publicar en HN/Reddit. Esto es portafolio, no producto.
- Landing page propia. El README es la landing.
- Métricas de uso / analytics. Es local.
