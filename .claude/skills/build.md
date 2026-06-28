---
name: build
description: Rebuildea la imagen Docker del proyecto. Úsalo después de cambiar pyproject.toml, uv.lock o Dockerfile. Si el cambio es solo a src/ o tests/, NO hace falta build (montados como volumes).
---

Rebuild de la imagen Docker.

**Comando:**
```bash
docker compose build app
```

Cuándo usar `/build`:
- Tras editar `pyproject.toml` o regenerar `uv.lock` (`uv lock`).
- Tras editar `Dockerfile` o `.dockerignore`.

Cuándo **NO** hace falta `/build`:
- Cambios en `src/` o `tests/` — están montados como volúmenes en `docker-compose.yml`, los ve el contenedor en caliente.
- Cambios en `docs/` o `README.md`.

Tras un build exitoso, sugerir `/check` para validar que todo sigue funcionando con las deps nuevas.

Si el build falla, reportar la línea exacta del Dockerfile que falló y los últimos 10 líneas de log.
