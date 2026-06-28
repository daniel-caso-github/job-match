---
name: extract
description: Pipeline end-to-end fase 1 + fase 2 — trae N ofertas de una fuente y las pasa por el extractor Gemini. Imprime title/company/requirements en JSON. Úsalo cuando el usuario pida ver requisitos extraídos, validar el extractor sobre datos reales, o iterar el prompt.
---

End-to-end Fase 1 (recolección) + Fase 2 (extracción Gemini).

**Argumentos:**
- `<source>` — `himalayas` o `remotive` (obligatorio).
- `--limit N` — número de ofertas a procesar (opcional, default 3).

**Comando:**
```bash
docker compose run --rm app python -m src.extraction.extractor --source $SOURCE --limit $LIMIT
```

Reglas:
- Requiere `.env` con `GEMINI_API_KEY=...`. Si no existe, el extractor levanta `RuntimeError` con mensaje claro.
- Cada oferta procesada = 1 llamada a Gemini (más 1 si hay reintento). Default `--limit 3` para no quemar cuota mientras se itera.
- Si `confidence` es 0 en alguna oferta, significa que la extracción falló dos veces (logueado como WARNING) — proponer revisar el prompt o el raw_text.
- Para iterar el prompt: editar `EXTRACTION_PROMPT` en `src/extraction/extractor.py` y volver a correr (no hace falta rebuild, src/ va por volumen).
- También consume cupo de la fuente subyacente (≤ 4 req/día Remotive, ~1/h Himalayas).
