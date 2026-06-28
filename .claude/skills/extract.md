---
name: extract
description: Ejecuta ExtractJobRequirementsUseCase sobre las ofertas en BD sin requirements. Llama a Gemini, valida con Pydantic, persiste. Úsalo cuando el usuario quiera completar la extracción para ofertas ya recolectadas, o validar el extractor sobre datos reales.
---

Pipeline de extracción (fase 2) sobre ofertas pendientes en BD.

**Pre-requisito**: ya tener ofertas en `jobs` con `requirements IS NULL` (usar `/run-source` antes).

**Argumentos:**
- `--limit N` — máx de ofertas a procesar (opcional, default 5).
- `--print-results` — opcional; al final, imprime title/company/url/requirements de las `n` procesadas.

**Comando:**
```bash
docker compose run --rm app python -m src.interfaces.cli.extract --limit $LIMIT [--print-results]
```

Reglas:
- Requiere `.env` con `GEMINI_API_KEY=...`. Si no existe, el extractor levanta `RuntimeError` con mensaje claro.
- Cada oferta procesada = 1 llamada a Gemini (más 1 si hay reintento). Default `--limit 5` para no quemar cuota mientras se itera.
- Si `confidence` es 0 en alguna oferta, significa que la extracción falló dos veces (logueado como WARNING) — proponer revisar el prompt o el raw_text.
- Para iterar el prompt: editar `EXTRACTION_PROMPT` en `src/infrastructure/llm/gemini_extractor.py` y volver a correr (no hace falta rebuild, `src/` va por volumen).
- Para "rehacer" la extracción de una oferta: borrar su `requirements` (`UPDATE jobs SET requirements = NULL WHERE id = '...'` via `/db-shell`) y volver a invocar.
