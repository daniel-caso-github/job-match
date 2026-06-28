---
name: db-shell
description: Abre un psql interactivo contra app-db (Postgres+pgvector). Para exploración ad-hoc de datos, debug, o verificar el estado de la BD. NO para cambios estructurales — ésos van por Alembic con /migrate.
---

Shell SQL ad-hoc al servicio `app-db`.

**Argumentos:** ninguno (interactivo), o `--query "SELECT ..."` para una query single-shot.

**Comandos:**

Interactivo:
```bash
docker compose exec app-db psql -U app -d jobmatch
```

Single-shot (no abre TTY):
```bash
docker compose exec -T app-db psql -U app -d jobmatch -c "$QUERY"
```

**Recetas útiles a sugerir al usuario:**

```sql
-- Ver tablas y migraciones aplicadas
\dt
SELECT * FROM alembic_version;

-- Conteo por tabla
SELECT 'jobs' AS tabla, count(*) FROM jobs
UNION ALL SELECT 'profiles', count(*) FROM profiles
UNION ALL SELECT 'matches', count(*) FROM matches;

-- Inspeccionar definición de jobs incluyendo índices
\d jobs

-- Verificar que la extensión pgvector está cargada
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Top 10 ofertas más recientes
SELECT id, source, title, fetched_at FROM jobs ORDER BY fetched_at DESC LIMIT 10;

-- Status del pipeline: cuántas tienen requirements, cuántas embedding
SELECT
  count(*) AS total,
  count(requirements) AS with_requirements,
  count(embedding) AS with_embedding
FROM jobs;
```

**Reglas:**
- **No** ejecutar `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`, `CREATE INDEX`, etc. desde aquí. Schema changes van por Alembic con `/migrate`.
- **No** mutar `alembic_version` a mano — es para Alembic.
- Permitido: SELECTs, UPDATEs/DELETEs de datos de prueba en desarrollo, EXPLAIN, `\d`, `\dt`, `\di`.
- Si `app-db` no está corriendo: sugerir `docker compose up -d app-db`.
