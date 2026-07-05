# Fase F1 · Bootstrap del frontend

**Tiempo estimado:** 2-3 horas
**Entregable demostrable:** `docker compose up -d frontend` levanta sin errores. Abrir `http://127.0.0.1:5173` muestra el status de la API (`{status: "ok", ...}`) fetcheado desde `/api/health`.

---

## 1. Objetivo

Establecer el entorno completo del frontend dentro de Docker: Vite + React + TypeScript + Tailwind corriendo con HMR, con proxy configurado a `api:8000`. Al final de esta fase cualquier archivo en `frontend/src/` se edita en el host y el browser lo refleja sin rebuild.

Esta fase **no implementa ninguna pantalla real**. Solo un `App.tsx` que prueba el wire con la API.

---

## 2. Decisiones

- **Node 22-alpine** en el Dockerfile de dev: imagen chica, LTS activo.
- **Proxy en Vite** (no CORS): `/api/*` → `http://api:8000/*` (rewrite saca el `/api` del path). Esto funciona porque Vite y la API están en la misma red Docker. En el browser, todas las calls van a `localhost:5173/api/...` → Vite las redirige internamente → no hay CORS.
- **Volúmenes con `:ro`** para `src/`, `public/`, `index.html`, `vite.config.ts`: HMR funciona porque Vite observa el filesystem del contenedor, que recibe los cambios del host vía el bind mount.
- **`node_modules` NO se monta desde el host**: el `Dockerfile` hace `npm ci` dentro de la imagen; el `node_modules` queda en la capa del contenedor. Esto evita colisiones de binarios entre macOS y Linux.

---

## 3. Archivos

| Archivo | Responsabilidad |
|---|---|
| `frontend/package.json` | Deps + scripts (`dev`, `build`, `type-check`) |
| `frontend/tsconfig.json` | TS config base (target ES2022, moduleResolution bundler) |
| `frontend/tsconfig.node.json` | TS config para `vite.config.ts` (node environment) |
| `frontend/vite.config.ts` | Plugin React, host 0.0.0.0, port 5173, proxy `/api` |
| `frontend/tailwind.config.js` | Content paths (`./src/**/*.{ts,tsx}`, `./index.html`) |
| `frontend/postcss.config.js` | Plugins: tailwindcss, autoprefixer |
| `frontend/index.html` | Entry HTML con `<div id="root">` y script `src/main.tsx` |
| `frontend/src/main.tsx` | `ReactDOM.createRoot` + `<App />` |
| `frontend/src/App.tsx` | Fetch a `/api/health` + mostrar resultado |
| `frontend/src/index.css` | `@tailwind base; @tailwind components; @tailwind utilities;` |
| `frontend/Dockerfile` | Stage `dev`: `node:22-alpine`, `npm ci`, `CMD npm run dev` |
| `frontend/.dockerignore` | `node_modules/`, `dist/` |
| `frontend/.gitignore` | `node_modules/`, `dist/`, `.env` |
| `docker-compose.yml` | Agregar servicio `frontend` |

---

## 4. Implementación

### `vite.config.ts` — proxy

```ts
server: {
  host: "0.0.0.0",
  port: 5173,
  proxy: {
    "/api": {
      target: "http://api:8000",
      rewrite: (path) => path.replace(/^\/api/, ""),
    },
  },
},
```

`/api/health` en el browser → Vite lo recibe → rewrite a `/health` → forward a `http://api:8000/health`.

### `App.tsx` — smoke test del wire

```tsx
const [status, setStatus] = useState<string>("...");
useEffect(() => {
  fetch("/api/health").then(r => r.json()).then(d => setStatus(d.status));
}, []);
return <p>API status: {status}</p>;
```

### Servicio en `docker-compose.yml`

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  image: job-match-frontend:dev
  ports:
    - "127.0.0.1:5173:5173"
  volumes:
    - ./frontend/src:/app/src:ro
    - ./frontend/public:/app/public:ro
    - ./frontend/index.html:/app/index.html:ro
    - ./frontend/vite.config.ts:/app/vite.config.ts:ro
  depends_on:
    - api
```

---

## 5. Criterios de aceptación

- [ ] `docker compose build frontend` termina sin error
- [ ] `docker compose up -d frontend` levanta (status `running`)
- [ ] `curl -s http://127.0.0.1:5173 | grep "root"` devuelve el HTML del entry point
- [ ] Abrir `http://127.0.0.1:5173` en browser: muestra "API status: ok"
- [ ] Editar `src/App.tsx` (cambiar un texto), guardar → el browser actualiza sin reload completo (HMR)
- [ ] `docker compose run --rm frontend npx tsc --noEmit` sin errores de tipos

---

## 6. Lo que NO se hace en esta fase

- Routing (React Router) — va en F2/F3
- TanStack Query — va en F2
- Ninguna pantalla real — solo el smoke test del wire
- Tailwind visual real — se importa pero solo para verificar que compila
- Multi-stage Dockerfile (build para prod) — va en F7
