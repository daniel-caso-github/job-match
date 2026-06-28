---
name: run-source
description: Smoke test contra la API real de una fuente de empleos (himalayas o remotive). Acepta el nombre de la fuente y opcionalmente --limit N. Úsalo cuando el usuario pida ver ofertas reales, validar un cliente, o verificar conectividad.
---

Smoke test de un cliente de `src/sources/` contra la API real.

**Argumentos esperados:**
- `<source>` — `himalayas` o `remotive` (obligatorio).
- `--limit N` — número de ofertas a imprimir (opcional, default 3).

**Comando:**
```bash
docker compose run --rm app python -m src.sources.$SOURCE --limit $LIMIT
```

Reglas:
- Si `$SOURCE` no es `himalayas` ni `remotive`, listar las fuentes válidas y abortar.
- Default `--limit 3` si el usuario no especifica.
- Validar visualmente que el JSON tiene `id`, `source`, `url`, `title`, `raw_text` no vacío.
- Esto hace **llamadas reales** — respeta los límites de las fuentes (≤ 4 req/día por fuente).
- Si la API responde con error, no reintentar más de 1 vez manualmente; los retries `tenacity` ya están en el cliente.
