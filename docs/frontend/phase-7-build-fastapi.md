# Fase F7 · Build de producción + servir desde FastAPI

**Tiempo estimado:** 1.5 horas
**Entregable demostrable:** `docker compose --profile demo up --build -d` → abrir `http://127.0.0.1:8000` → SPA cargada, `curl http://127.0.0.1:8000/api/health` → 200.

---

## 1. Objetivo

Unifica el frontend y el backend en un único origin para demo/producción local. FastAPI sirve el build estático de Vite bajo `/` y mantiene todos los endpoints de la API bajo `/api/*`. El usuario solo necesita un puerto (`:8000`) para el demo.

**Fuera de scope:** deploy en la nube (Fly.io, Railway, etc.), HTTPS/TLS, CDN para assets, autenticación.

---

## 2. Decisiones

- **Multi-stage Dockerfile en `frontend/Dockerfile`**: stage `dev` (actual, con `npm run dev`) + stage `build` (`npm ci && npm run build`, output en `/app/dist`). Docker Compose elige el stage según el contexto (dev vs demo).
- **`FastAPI.mount()` con `StaticFiles(html=True)`**: FastAPI sirve el `index.html` para cualquier ruta no-API, lo que permite el deep-linking de React Router (p.ej. refresh directo en `/matches/:id`).
- **Los routers ya tienen prefijo `/api`**: desde F1, `lib/api.ts` usa `/api/...` y el proxy de Vite reescribe `/api → api:8000`. Los routers de FastAPI no tienen prefix en el código — el prefix `/api` viene del Vite proxy en dev. Para producción (F7), se agrega el prefix a nivel de `include_router`:
  ```python
  app.include_router(health_router, prefix="/api")
  app.include_router(profile_router, prefix="/api")
  # etc.
  ```
  El mount de `StaticFiles` va **después** de los routers para que `/api/*` no se intercepte.
- **Volumen compartido entre servicios en compose**: el servicio `frontend-build` (perfil `demo`) construye el dist y lo deja en `./frontend/dist` en el host (o en un named volume). El servicio `api` lo monta como `:ro`.
- **Sin cambios en los tests del backend**: los routers cambian de path pero los tests ya usan el `TestClient` de FastAPI directamente, no la URL de producción.

---

## 3. Archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `frontend/Dockerfile` | Modificar | Agregar stage `build` con `npm run build` |
| `docker-compose.yml` | Modificar | Servicio `frontend-build` (perfil `demo`) + volumen para dist + mount en `api` |
| `src/interfaces/api/main.py` | Modificar | Agregar prefix `/api` en `include_router` + mount `StaticFiles` al final |
| `README.md` | Modificar | Actualizar quickstart con las dos opciones (dev + demo), listar docs del front |

---

## 4. Implementación

### Dockerfile multi-stage

```dockerfile
FROM node:22-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm ci
CMD ["npm", "run", "dev"]

FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
```

### docker-compose.yml — servicio demo

```yaml
frontend-build:
  build:
    context: ./frontend
    dockerfile: Dockerfile
    target: build
  volumes:
    - ./frontend/dist:/app/dist
  profiles: [demo]
  restart: "no"
```

El servicio `api` agrega:
```yaml
volumes:
  - ./frontend/dist:/app/frontend_dist:ro
```

### FastAPI — prefix + static mount

```python
app.include_router(health_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(matches_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")

_dist = Path("/app/frontend_dist")
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
```

### Flujo demo

```bash
docker compose --profile demo up --build -d
# frontend-build corre npm run build y sale (restart: "no")
# api arranca y encuentra /app/frontend_dist → monta StaticFiles
# Abre http://127.0.0.1:8000 → SPA
# http://127.0.0.1:8000/api/health → JSON
```

---

## 5. Criterios de aceptación

- [ ] `docker compose --profile demo up --build` completa sin error
- [ ] `curl http://127.0.0.1:8000/api/health` → `{"status":"ok",...}`
- [ ] `curl http://127.0.0.1:8000/` → HTML de la SPA (contiene `<div id="root">`)
- [ ] Navegar a `http://127.0.0.1:8000/matches/<id>` y recargar el browser → SPA carga (no 404 de FastAPI)
- [ ] Dev workflow sin cambios: `docker compose up -d frontend api` sigue funcionando en `:5173`
- [ ] `docker compose run --rm app pytest -v` → todos los tests pasan (sin regresar paths `/health` → `/api/health` en tests — los tests usan `TestClient` con `app` directo, no la URL)
- [ ] README actualizado con las dos opciones de quickstart

---

## 6. Lo que NO se hace en esta fase

- Deploy real en la nube → fuera de scope del proyecto (es un pipeline local/demo)
- HTTPS → fuera de scope
- Variables de entorno separadas por entorno (dev/prod) → ya está manejado con `.env`
- Compresión de assets (gzip/brotli) → nginx o el CDN lo harían en prod real; fuera de scope
- Tests del frontend (vitest/playwright) → fuera de scope de este MVP
