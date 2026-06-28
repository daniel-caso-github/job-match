---
name: migrate
description: Genera y aplica una migración Alembic tras editar src/storage/models.py. Úsalo cuando el usuario agregue una columna, una tabla, un índice o cambie tipos en los modelos ORM. NO toca la BD si solo se hicieron cambios a código no-storage.
---

Workflow guiado de migración de schema.

**Argumento:** `<mensaje>` — descripción corta de la migración (ej. "add job posting language", "drop matches.scored_at default").

**Pasos a ejecutar en orden:**

1. **Confirmar que `src/storage/models.py` cambió** (`git diff src/storage/models.py`). Si no hay cambios al schema, abortar con explicación: "no hay cambios de modelos, ¿querés correr `alembic upgrade head` solamente?".

2. **Garantizar que `app-db` está corriendo y healthy:**
   ```bash
   docker compose up -d app-db
   until docker compose ps app-db | grep -q '(healthy)'; do sleep 2; done
   ```

3. **Autogenerar la revision:**
   ```bash
   docker compose run --rm app alembic revision --autogenerate -m "$MENSAJE"
   ```

4. **Mostrar el archivo generado** al usuario (`cat alembic/versions/<hash>_*.py`) y pedirle que revise:
   - Si todo se ve bien, continuar.
   - **Si la revision toca columnas `Vector`**: verificar que el import `import pgvector.sqlalchemy` está presente (Alembic puede olvidarlo); agregarlo si falta.
   - **Si la migración cambia índices HNSW de pgvector**: verificar `postgresql_using="hnsw"` y `postgresql_ops={"embedding": "vector_cosine_ops"}` — Alembic puede no autodetectarlos.

5. **Aplicar:**
   ```bash
   docker compose run --rm app alembic upgrade head
   ```

6. **Verificar:**
   ```bash
   docker compose exec app-db psql -U app -d jobmatch -c "\d <tabla afectada>"
   ```

7. **Correr `/check`** para asegurarse que los tests de `tests/test_storage.py` siguen verdes (en particular `test_metadata_lists_expected_tables`, `test_job_columns_present`, etc.).

Reglas:
- **No editar revisions ya aplicadas en otros entornos.** Para deshacer: `alembic downgrade -1` y crear una nueva revision con el fix.
- Nunca usar `Base.metadata.create_all()` en código de aplicación — bypassa Alembic.
- Si el usuario quiere ver el SQL sin aplicarlo: `alembic upgrade head --sql`.
