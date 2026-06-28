---
name: test
description: Corre la suite de tests del proyecto dentro de Docker. Acepta opcionalmente un patrón -k para filtrar. Úsalo cuando el usuario pida correr tests, validar cambios, o iterar TDD.
---

Corre los tests del proyecto dentro del contenedor.

**Comando base:**
```bash
docker compose run --rm app pytest -v
```

**Si el usuario pasa argumentos como filtro o expresión `-k`:**
```bash
docker compose run --rm app pytest -v -k "$ARGS"
```

Reglas:
- No correr `pytest` localmente (no hay `.venv` en host por diseño — Docker-only).
- Si falla un test, **reportar el fallo con el traceback resumido** y proponer un diagnóstico breve. No editar código para "arreglar" tests sin que el usuario lo pida explícitamente.
- Si la imagen no está construida, sugerir `/build` primero.
- Mostrar siempre el resumen `X passed / Y failed` al final.
