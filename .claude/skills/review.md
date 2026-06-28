---
name: review
description: Code review del diff actual del proyecto contra las convenciones explícitas (Pydantic v2, idempotencia, retries, sin comentarios inventados, fixtures offline). Úsalo cuando el usuario pida revisar cambios, antes de un commit, o tras implementar una feature. Solo reporta; no aplica cambios.
---

Code review del diff actual del repositorio usando las convenciones de este proyecto.

**Paso 1 — obtener el diff:**
```bash
git diff HEAD                    # cambios no commiteados
# si no hay diff sin commit, considerar:
git diff main...HEAD             # cambios de la rama vs main
```

Si no hay cambios, reportarlo y terminar.

**Paso 2 — revisar contra esta checklist:**

### Críticos (bloquean merge)
- [ ] Modelos de datos usan **Pydantic v2** (no dataclasses, no dicts crudos).
- [ ] IDs idempotentes se construyen con `make_id(source, url)` de `src/sources/base.py`. **No** se calculan hashes ad hoc.
- [ ] Toda nueva fuente hereda de `Source` ABC y devuelve `RawJob`.
- [ ] Clientes HTTP externos usan `tenacity` retries (429, 5xx, timeouts).
- [ ] `RawJob.raw_text` no contiene HTML (limpiado con `BeautifulSoup`).
- [ ] Atribución de la fuente preservada en logs/responses cuando aplica.
- [ ] Tests usan **fixtures sintéticas mínimas** en `tests/fixtures/` (no red).

### Importantes (recomendar arreglar)
- [ ] No hay comentarios/docstrings inventados ni manejo de errores fuera de lo pedido.
- [ ] No hay nuevos `requirements.txt` u otros gestores de deps — solo `pyproject.toml` + `uv.lock`.
- [ ] No se introduce `.venv` local ni se asume Python en el host. **Docker-only.**
- [ ] Identificadores en inglés; comentarios/mensajes para el usuario en español.

### Estilo
- [ ] `ruff check` pasaría (reportar warnings sin auto-fix).
- [ ] Funciones < 50 líneas; archivos < 300 líneas (suave; comentar si excede).

**Paso 3 — reportar:**
- Formato: tabla por severidad (Críticos / Importantes / Estilo) con `archivo:línea — issue → sugerencia`.
- **No aplicar cambios**. Solo reportar. Si el usuario pide aplicar, hacer el cambio explícitamente.
- Si todo pasa, decirlo así y mencionar 1-2 fortalezas observadas (positive feedback).
