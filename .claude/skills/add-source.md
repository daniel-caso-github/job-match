---
name: add-source
description: Bootstrap de una nueva fuente de ofertas de empleo (We Work Remotely, Jobicy, etc.) respetando el contrato `Source` ABC. Úsalo cuando el usuario pida añadir una fuente nueva al pipeline. NO modifica fuentes existentes.
---

Workflow guiado para añadir una nueva fuente al pipeline.

**Argumento:** `<name>` — slug en lowercase de la fuente (ej. `weworkremotely`, `jobicy`).

**Pasos a ejecutar (en orden):**

1. **Leer contexto obligatorio:**
   - `src/domain/ports/job_source.py` — contrato `JobSource` ABC.
   - `src/domain/entities/raw_job.py` — esquema de salida `RawJob` (Pydantic).
   - `src/domain/services/id_hasher.py::make_id` — generación determinista de IDs.
   - `src/infrastructure/sources/himalayas.py` — referencia para clientes HTTP JSON (estructura, retries).
   - `src/infrastructure/sources/remotive.py` — referencia para mapeo de campos `RawJob`.
   - `docs/phase-1-recoleccion.md` §3, §6, §8 — patrones y criterios de aceptación.

2. **Validar la fuente** antes de codear:
   - ¿Tiene API JSON / RSS oficial sin auth?
   - ¿Cuáles son sus términos de uso? (atribución, frecuencia máxima, no redistribución)
   - Confirmar con el usuario el endpoint y los filtros relevantes.

3. **Crear `src/infrastructure/sources/$NAME.py`:**
   - Clase `${Name}Source(JobSource)` con `name = "$name"`.
   - `httpx.Client` en `__init__` (timeout 20s, follow_redirects).
   - Método `fetch(**filters) -> Iterable[RawJob]` con paginación si aplica.
   - Método `_get_json` decorado con `@retry` de `tenacity` (stop_after_attempt=3, wait_exponential).
   - Método `_to_raw_job` que normaliza al esquema `RawJob`, limpia HTML con `BeautifulSoup`, usa `make_id(self.name, url)`.
   - **NO** tiene `if __name__ == "__main__":` — el entrypoint vive en `src/interfaces/cli/collect.py`.

4. **Registrar la fuente** en el CLI: agregar `"$name": ${Name}Source` al `SOURCE_REGISTRY` de `src/interfaces/cli/collect.py`.

5. **Crear `tests/fixtures/${name}_sample.json`** — fixture sintética mínima con 3 ofertas que cubran:
   - 1 oferta normal y completa.
   - 1 con algún campo opcional faltante (sin company, sin location).
   - 1 con un edge case (date malformada, HTML sucio, etc.).

6. **Crear `tests/infrastructure/sources/test_$NAME.py`** siguiendo el patrón de `test_himalayas.py` / `test_remotive.py`:
   - `test_parses_fixture` — happy path.
   - `test_handles_edges` — campos faltantes / inválidos no rompen.
   - Mockear `_get_json` con `unittest.mock.patch`. **Sin red.**

7. **Validar** con `/check` (pytest + ruff). Si pasa, hacer smoke real:
   ```bash
   docker compose run --rm app python -m src.interfaces.cli.collect --source $NAME --limit 3 --dry-run
   ```

8. **Actualizar docs:**
   - `docs/00-overview.md` §7 — añadir fila a la tabla de fuentes con sus condiciones.
   - `docs/phase-1-recoleccion.md` §9 — mover la fuente desde "Lo que NO se hace" al cuerpo del doc.

**No tocar** `himalayas.py`, `remotive.py` ni los tests existentes. Esta tarea es aditiva.
