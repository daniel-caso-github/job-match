---
name: run-source
description: Smoke test contra la API real de una fuente de empleos (himalayas, remotive, o todas). Acepta el nombre de la fuente y opcionalmente --limit N. Por defecto upsertea a la BD; --dry-run solo imprime. Úsalo cuando el usuario pida ver ofertas reales, validar un cliente, o cargar datos para probar el pipeline.
---

Ejecuta el use case `CollectJobsUseCase` con la(s) fuente(s) elegida(s).

**Argumentos esperados:**
- `<source>` — `himalayas`, `remotive`, o `all` (default `all`).
- `--limit N` — máx por fuente (opcional, default 3).
- `--dry-run` — opcional; imprime JSON normalizado en stdout sin tocar BD.

**Comando:**
```bash
# Persistiendo a la BD (requiere docker compose up -d app-db):
docker compose run --rm app python -m src.interfaces.cli.collect --source $SOURCE --limit $LIMIT

# Solo imprimir, sin tocar BD:
docker compose run --rm app python -m src.interfaces.cli.collect --source $SOURCE --limit $LIMIT --dry-run
```

Reglas:
- Si `$SOURCE` no es `himalayas`/`remotive`/`all`, listar las opciones válidas y abortar.
- Default `--limit 3` si el usuario no especifica.
- Sin `--dry-run`, verifica al final `SELECT count(*), source FROM jobs GROUP BY source` (via `/db-shell`) que aumentó.
- Con `--dry-run`, validar visualmente que el JSON tiene `id`, `source`, `url`, `title`, `raw_text` no vacío.
- Esto hace **llamadas reales** — respeta los límites de las fuentes (≤ 4 req/día por fuente).
- Si la API responde con error, no reintentar más de 1 vez manualmente; los retries `tenacity` ya están en el cliente.
