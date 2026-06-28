# Job Match Pipeline

> Recolección, extracción estructurada y scoring de ofertas de empleo según un perfil profesional.

Proyecto de portafolio + uso personal. Pipeline IA aplicada con Python · Pydantic · pgvector · Gemini · FastAPI · Airflow.

> **Estado actual:** Fase 1 (recolección Himalayas + Remotive). Ver [`docs/`](docs/) para diseño completo por fases.

## Requisitos

- Docker + Docker Compose (todo el código corre dentro de contenedores).

## Quickstart

```bash
# build inicial (~30s la primera vez, cacheado después)
docker compose build

# tests
docker compose run --rm app pytest -v

# smoke test contra Himalayas (API real)
docker compose run --rm app python -m src.sources.himalayas --limit 3

# smoke test contra Remotive (API real)
docker compose run --rm app python -m src.sources.remotive --limit 3
```

## ¿Por qué Docker-only?

Un único entorno reproducible para dev y para los servicios que vendrán en fases siguientes (Postgres + pgvector, Airflow, FastAPI). Evita el clásico "funciona en mi máquina" y mantiene `pyproject.toml`/`uv.lock` como única fuente de verdad de dependencias.

### IDE (PyCharm / VSCode)

Para autocompletado y linting locales, configurar el intérprete remoto apuntando al contenedor:
- **PyCharm**: Settings → Project → Python Interpreter → Add → Docker Compose → service `app`.
- **VSCode**: extensión *Dev Containers* → "Reopen in Container" usando el `Dockerfile` del repo.

## Documentación

Cada fase tiene su doc con decisiones, schemas y código:

- [00 · Overview](docs/00-overview.md)
- [Fase 1 · Recolección](docs/phase-1-recoleccion.md)
- [Fase 2 · Extracción](docs/phase-2-extraccion.md)
- [Fase 3 · Matching](docs/phase-3-matching.md)
- [Fase 4 · API + Perfil](docs/phase-4-api-perfil.md)
- [Fase 5 · Orquestación](docs/phase-5-orquestacion.md)
- [Fase 6 · README y demo](docs/phase-6-readme-demo.md)

## Fuentes de datos

- [Himalayas](https://himalayas.app/) — API JSON pública.
- [Remotive](https://remotive.com/) — API JSON oficial (`/api/remote-jobs`).

Atribución obligatoria por términos de uso de las fuentes. No se redistribuyen ofertas a terceros; el sistema enlaza siempre al posting original.

## Licencia

MIT.
