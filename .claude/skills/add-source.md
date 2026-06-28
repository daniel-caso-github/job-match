---
name: add-source
description: Bootstrap de una nueva fuente de ofertas de empleo (We Work Remotely, Jobicy, etc.) respetando el contrato `Source` ABC. Úsalo cuando el usuario pida añadir una fuente nueva al pipeline. NO modifica fuentes existentes.
---

Workflow guiado para añadir una nueva fuente al pipeline.

**Argumento:** `<name>` — slug en lowercase de la fuente (ej. `weworkremotely`, `jobicy`).

**Pasos a ejecutar (en orden):**

1. **Leer contexto obligatorio:**
   - `src/sources/base.py` — contrato `Source` ABC, `RawJob`, `make_id`.
   - `src/sources/himalayas.py` — referencia para clientes HTTP JSON (estructura, retries, CLI).
   - `src/sources/remotive.py` — referencia para mapeo de campos `RawJob`.
   - `docs/phase-1-recoleccion.md` §3, §6, §8 — patrones y criterios de aceptación.

2. **Validar la fuente** antes de codear:
   - ¿Tiene API JSON / RSS oficial sin auth?
   - ¿Cuáles son sus términos de uso? (atribución, frecuencia máxima, no redistribución)
   - Confirmar con el usuario el endpoint y los filtros relevantes.

3. **Crear `src/sources/$NAME.py`:**
   - Clase `${Name}Source(Source)` con `name = "$name"`.
   - `httpx.Client` en `__init__` (timeout 20s, follow_redirects).
   - Método `fetch(**filters) -> Iterable[RawJob]` con paginación si aplica.
   - Método `_get_json` decorado con `@retry` de `tenacity` (stop_after_attempt=3, wait_exponential).
   - Método `_to_raw_job` que normaliza al esquema `RawJob`, limpia HTML con `BeautifulSoup`, usa `make_id(self.name, url)`.
   - Bloque `if __name__ == "__main__":` con CLI argparse análogo a himalayas/remotive.

4. **Crear `tests/fixtures/${name}_sample.json`** (o `.xml`) — fixture sintética mínima con 3 ofertas que cubran:
   - 1 oferta normal y completa.
   - 1 con algún campo opcional faltante (sin company, sin location).
   - 1 con un edge case (date malformada, HTML sucio, etc.).

5. **Añadir tests a `tests/test_sources.py`** (no crear archivo nuevo, extender el existente):
   - `test_${name}_parses_fixture` — happy path.
   - `test_${name}_handles_edges` — campos faltantes / inválidos no rompen.
   - Mockear el cliente HTTP con `unittest.mock.patch`, igual que los existentes. **Sin red.**

6. **Validar** con `/check` (pytest + ruff). Si pasa, hacer smoke real:
   ```bash
   docker compose run --rm app python -m src.sources.$NAME --limit 3
   ```

7. **Actualizar docs:**
   - `docs/00-overview.md` §7 — añadir fila a la tabla de fuentes con sus condiciones.
   - `docs/phase-1-recoleccion.md` §9 — mover la fuente desde "Lo que NO se hace" al cuerpo del doc.

**No tocar** `himalayas.py`, `remotive.py` ni los tests existentes. Esta tarea es aditiva.
