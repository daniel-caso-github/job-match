# Fase 1 · Recolección — Himalayas + Remotive

**Tiempo estimado:** 1 día
**Entregable demostrable:** un script de CLI que trae N ofertas reales de Himalayas y de Remotive, las normaliza al esquema `RawJob` e imprime el JSON resultante. Listo para grabar en video.

---

## 1. Objetivo

Implementar la capa de **adquisición de ofertas**. Devuelve siempre objetos `RawJob` ya normalizados, independientemente de la fuente. Las fases siguientes ignoran de dónde vino cada oferta.

Esta fase **no** llama a Gemini, no hace embeddings y no escribe en la BD (eso es fase 5, integrado al DAG). Solo: fetch → parse → normalize → return.

---

## 2. Esquema común: `RawJob` (Pydantic)

Archivo: `src/sources/base.py`

```python
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable

from pydantic import BaseModel, Field, HttpUrl


class RawJob(BaseModel):
    """Oferta normalizada al esquema común. Salida de toda fuente."""

    id: str = Field(description="hash(source + url), idempotente")
    source: str = Field(description="'himalayas' | 'remotive' | ...")
    url: HttpUrl = Field(description="enlace a la oferta original (requisito legal)")
    title: str
    company: str | None = None
    raw_text: str = Field(description="descripción completa, sin HTML")
    posted_at: datetime | None = None
    country: str | None = None
    remote: bool | None = None


def make_id(source: str, url: str) -> str:
    """Hash determinista para idempotencia.

    Usar SHA-1 truncado a 16 hex chars: colisiones despreciables a
    escala del proyecto y queda legible en logs.
    """
    return hashlib.sha1(f"{source}|{url}".encode("utf-8")).hexdigest()[:16]


class Source(ABC):
    """Contrato común. Una implementación por fuente."""

    name: str

    @abstractmethod
    def fetch(self, **filters) -> Iterable[RawJob]:
        ...
```

**Notas de diseño:**
- `id` se calcula en cada cliente con `make_id(self.name, url)`. Si la misma URL aparece en dos corridas, el `id` será el mismo y el upsert no duplica (ver fase 3 — storage).
- `raw_text` siempre **sin HTML** (limpiarlo en el parser). Razón: el extractor de fase 2 trabaja sobre texto plano y el embedder de fase 3 también.
- `country` y `remote` son opcionales — algunos feeds no los traen.
- `Source` es un ABC sin estado; cada fuente recibe sus filtros como `**kwargs`.

---

## 3. Cliente Himalayas

Archivo: `src/sources/himalayas.py`

**Endpoint** (sin auth):
```
GET https://himalayas.app/jobs/api?limit={N}&offset={M}&keywords={kw}&country={iso}&seniority={lvl}
```
(Si el endpoint público cambia, validar con `curl` antes de implementar. La estructura del JSON es estable: `{ "jobs": [...] }` con campos `guid`, `title`, `companyName`, `applicationLink`, `description`, `publishedAt`, `countries`, `locationRestrictions`, ...)

**Filtros relevantes para este proyecto:**
- `keywords=python,backend,fastapi`
- `country=` (vacío = todos)
- `seniority=mid,senior`
- `limit=100` (máx por página)

**Rate limit observado**: ~60 req/min. Corremos 1 vez cada 12h y paginamos pocas páginas → cero riesgo.

```python
import httpx
from datetime import datetime
from typing import Iterable
from bs4 import BeautifulSoup

from .base import RawJob, Source, make_id

HIMALAYAS_URL = "https://himalayas.app/jobs/api"


class HimalayasSource(Source):
    name = "himalayas"

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    def fetch(
        self,
        *,
        keywords: str = "python",
        seniority: str | None = None,
        country: str | None = None,
        limit: int = 100,
        max_pages: int = 3,
    ) -> Iterable[RawJob]:
        offset = 0
        for _ in range(max_pages):
            params = {"limit": limit, "offset": offset, "keywords": keywords}
            if seniority:
                params["seniority"] = seniority
            if country:
                params["country"] = country

            resp = self._client.get(HIMALAYAS_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()

            jobs = payload.get("jobs") or []
            if not jobs:
                return

            for j in jobs:
                yield self._to_raw_job(j)

            offset += limit
            if len(jobs) < limit:
                return  # última página

    def _to_raw_job(self, j: dict) -> RawJob:
        url = j.get("applicationLink") or j.get("jobSiteUrl") or ""
        raw_html = j.get("description") or ""
        text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)

        published = j.get("publishedAt") or j.get("createdAt")
        posted_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None

        countries = j.get("locationRestrictions") or j.get("countries") or []
        country = countries[0] if countries else None

        return RawJob(
            id=make_id(self.name, url),
            source=self.name,
            url=url,
            title=j["title"],
            company=j.get("companyName"),
            raw_text=text,
            posted_at=posted_at,
            country=country,
            remote=True,  # Himalayas es 100% remoto por definición
        )
```

**Manejo de errores:**
- `httpx.TimeoutException` → reintenta 2 veces con backoff exponencial (2s, 4s). Si persiste, log warning y devuelve lo acumulado hasta ese punto.
- HTTP 429 → respetar `Retry-After`. En caso de no traerlo, esperar 60s.
- HTTP 5xx → reintento 1 vez. Si persiste, abortar fuente (el DAG sigue con las demás).
- JSON sin clave `jobs` o forma inesperada → log error con preview del payload, devolver vacío.

**Importante:** los reintentos van en una decorator/utility separada para no enredar el método `fetch`. Usar `tenacity` (`@retry(stop=stop_after_attempt(3), wait=wait_exponential())`) es la forma idiomática.

---

## 4. Cliente Remotive (API JSON oficial)

Archivo: `src/sources/remotive.py`

> **Nota — corrección de diseño:** la versión original del doc planeaba usar el RSS oficial de Remotive (`/remote-jobs/feed/<categoria>`). Al implementarlo descubrimos que **Remotive descontinuó los feeds RSS** (la URL responde HTML genérico de la landing). La API JSON sigue siendo la vía oficial y documentada (`https://remotive.com/api/remote-jobs`), sin auth, con un *legal notice* explícito: enlazar de vuelta, atribuir, y consultar ≤ 4 veces/día. Nuestro pipeline cada 12 h queda holgadamente dentro del límite. Docs: <https://remotive.com/api-documentation>.

**Endpoint:**
```
GET https://remotive.com/api/remote-jobs?category={slug}&limit={N}&search={kw}
```

**Slugs relevantes** (verificados contra `/api/remote-jobs/categories`):
- `software-development` — Software Development
- `devops` — Devops

**Forma del JSON** (campos que usamos):
- `url`, `title`, `company_name`, `description` (HTML), `publication_date` (ISO 8601 sin TZ), `candidate_required_location` ("Worldwide", "USA Only", "EMEA", ...).

```python
import httpx
from bs4 import BeautifulSoup
from datetime import datetime

from .base import RawJob, Source, make_id

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
DEFAULT_CATEGORIES = ("software-development", "devops")


class RemotiveSource(Source):
    name = "remotive"

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    def fetch(
        self,
        *,
        categories: list[str] | None = None,
        search: str | None = None,
        limit_per_category: int = 50,
    ):
        cats = categories if categories is not None else list(DEFAULT_CATEGORIES)
        for cat in cats:
            params = {"category": cat, "limit": limit_per_category}
            if search:
                params["search"] = search
            payload = self._get_json(params)   # con @retry tenacity, igual que Himalayas
            for j in payload.get("jobs") or []:
                yield self._to_raw_job(j)

    def _to_raw_job(self, j: dict) -> RawJob:
        url = j["url"]
        text = BeautifulSoup(j.get("description") or "", "html.parser").get_text(" ", strip=True)
        posted_at = None
        if pub := j.get("publication_date"):
            try:
                posted_at = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except ValueError:
                posted_at = None
        return RawJob(
            id=make_id(self.name, url),
            source=self.name,
            url=url,
            title=j["title"],
            company=j.get("company_name"),
            raw_text=text,
            posted_at=posted_at,
            country=j.get("candidate_required_location") or None,
            remote=True,
        )
```

**Diferencias clave vs el plan RSS original:**
- `company_name` viene como campo separado en JSON; el truco de partir el título por `:` queda obsoleto.
- `candidate_required_location` no es un país ISO sino una descripción libre (`"Worldwide"`, `"USA Only"`, `"EMEA"`). Se mapea a `RawJob.country` tal cual; la fase 2 (extracción) lo refina con `JobRequirements.requires_eu_residency` / `latam_friendly`.
- `feedparser` desaparece de las dependencias. Sumamos `httpx` y `bs4` (que Himalayas ya usaba).

---

## 5. CLI de demostración

Cada cliente expone un entrypoint mínimo para grabar el video de fase 1. No es una API pública; es un script de smoke test.

Al final de `src/sources/himalayas.py`:

```python
if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    src = HimalayasSource()
    for i, job in enumerate(src.fetch(limit=args.limit, max_pages=1)):
        if i >= args.limit:
            break
        print(json.dumps(job.model_dump(mode="json"), indent=2, ensure_ascii=False))
```

Análogo en `src/sources/remotive.py`.

**Demo (criterio de aceptación):**
```bash
docker compose run --rm app python -m src.sources.himalayas --limit 5
docker compose run --rm app python -m src.sources.remotive --limit 5
```
Salida esperada: JSON válido de `RawJob` con todos los campos requeridos (`id`, `source`, `url`, `title`, `raw_text` no vacío).

---

## 6. Tests

Archivo: `tests/test_sources.py`

Estrategia: **fixtures grabadas** (no llamadas de red en CI). Guardar 1 respuesta JSON de Himalayas y 1 feed XML de Remotive bajo `tests/fixtures/`. El parser debe ser pura función del input.

```python
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.sources.himalayas import HimalayasSource
from src.sources.remotive import RemotiveSource

FIXTURES = Path(__file__).parent / "fixtures"


def test_himalayas_parses_fixture():
    payload = json.loads((FIXTURES / "himalayas_sample.json").read_text())
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None

    src = HimalayasSource()
    with patch.object(src._client, "get", return_value=mock_resp):
        jobs = list(src.fetch(limit=100, max_pages=1))

    assert len(jobs) > 0
    j = jobs[0]
    assert j.source == "himalayas"
    assert j.raw_text  # no vacío
    assert "<" not in j.raw_text  # HTML limpiado
    assert j.id == j.id  # determinismo: dos calls al mismo url → mismo id


def test_remotive_parses_fixture(tmp_path):
    # feedparser acepta URL o string
    feed_xml = (FIXTURES / "remotive_sample.xml").read_text()
    src = RemotiveSource()
    import feedparser
    parsed = feedparser.parse(feed_xml)
    jobs = [src._to_raw_job(e) for e in parsed.entries]

    assert len(jobs) > 0
    assert all(j.source == "remotive" for j in jobs)
    assert all(j.url for j in jobs)


def test_make_id_is_deterministic():
    from src.sources.base import make_id
    assert make_id("himalayas", "https://x/y") == make_id("himalayas", "https://x/y")
    assert make_id("himalayas", "https://x/y") != make_id("remotive", "https://x/y")
```

**Fixtures usadas (sintéticas mínimas, sin red):**
- `tests/fixtures/himalayas_sample.json` — payload con 3 ofertas (HTML en `description`, una sin `companyName`, una con `publishedAt` malformado).
- `tests/fixtures/remotive_sample.json` — respuesta JSON con 3 ofertas (HTML en `description`, una con `company_name: null`, una con `publication_date` malformado).

---

## 7. Dependencias añadidas en esta fase

En `pyproject.toml` (gestionado por `uv`):
```
httpx>=0.27
pydantic>=2.5
beautifulsoup4>=4.12
tenacity>=8.2
# dev:
pytest>=8.0
ruff>=0.5
```

(`feedparser` ya no es necesario tras migrar Remotive de RSS a API JSON.)

---

## 8. Criterios de aceptación (Definition of Done)

Todos los comandos se ejecutan vía Docker (`docker compose build` previa una vez).

- [ ] `src/sources/base.py` define `RawJob`, `Source`, `make_id`.
- [ ] `docker compose run --rm app python -m src.sources.himalayas --limit 5` trae ≥ 3 ofertas reales.
- [ ] `docker compose run --rm app python -m src.sources.remotive --limit 5` trae ≥ 3 ofertas reales.
- [ ] `docker compose run --rm app pytest -v` pasa sin red (usa fixtures).
- [ ] `RawJob.raw_text` no contiene tags HTML.
- [ ] `make_id` es determinista (mismo input → mismo id, sources distintos → ids distintos).
- [ ] Reintentos con `tenacity` en Himalayas y Remotive para 429/5xx/timeout.
- [ ] Video corto del demo grabado.

---

## 9. Lo que NO se hace en esta fase (referencias)

- **Persistir** las ofertas en Postgres → fase 5 (lo orquesta el DAG llamando a `storage.upsert_job`).
- **Extraer requisitos** (`JobRequirements`) → fase 2.
- **Embeddings** → fase 3.
- **Endpoint `/jobs/refresh`** → fase 4.
- **Añadir We Work Remotely / Jobicy** → extensión post-MVP. La fase 1 deja el ABC `Source` listo para sumarlas sin tocar el resto del pipeline.
