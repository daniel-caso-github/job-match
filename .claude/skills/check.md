---
name: check
description: Gate pre-commit. Corre pytest + ruff en una sola pasada dentro de Docker y reporta el primer fallo de cada uno. Úsalo cuando el usuario pida validar antes de commit, "is it ready", o al final de implementar una feature.
---

Validación combinada antes de commit: tests + lint, en paralelo cuando es posible.

**Comandos:**
```bash
docker compose run --rm app pytest -v
docker compose run --rm app ruff check src tests
```

Reglas:
- Correr los dos siempre, aunque el primero falle (queremos el panorama completo).
- Reportar el **primer fallo** de cada uno con una sentencia accionable. Ej: `test_himalayas_parses_fixture FAILED: KeyError 'companyName' → fixture cambió de schema, actualizar tests/fixtures/himalayas_sample.json`.
- Si ruff reporta múltiples issues, agrupar por regla (`E501 x3 in src/sources/...`) y sugerir `ruff check --fix` solo cuando son fix automáticos seguros (NO `--unsafe-fixes`).
- Si todo pasa, output corto: `✓ pytest 7 passed | ✓ ruff clean`.
- No correr `pytest`/`ruff` localmente — solo dentro del contenedor.
