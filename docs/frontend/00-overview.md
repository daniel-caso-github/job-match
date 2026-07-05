# Frontend · Overview

**Stack:** React 18 · TypeScript · Vite · Tailwind CSS · TanStack Query · React Hook Form + Zod · React Router v6 · Docker

**Entorno:** Docker-only. En dev, Vite corre en `:5173` con HMR y hace proxy de `/api/*` a `api:8000`. Para demo, FastAPI sirve el build estático en `:8000`.

---

## Arquitectura

```
frontend/
├── public/
│   └── sample_profile.json      # precarga del formulario de perfil
├── src/
│   ├── lib/
│   │   ├── api.ts               # cliente HTTP tipado (apiFetch + funciones por endpoint)
│   │   ├── queryClient.ts       # instancia QueryClient (staleTime, retries)
│   │   ├── schemas.ts           # schema Zod de ProfileForm (espeja validaciones Pydantic)
│   │   └── profileStorage.ts    # helpers localStorage (get/set profileId actual)
│   ├── types/
│   │   └── api.ts               # tipos TS de todos los endpoints FastAPI
│   ├── pages/
│   │   ├── MatchesList.tsx      # route /
│   │   ├── MatchDetail.tsx      # route /matches/:jobId
│   │   └── ProfileForm.tsx      # route /profile
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── MatchCard.tsx
│   │   ├── ScoreBadge.tsx
│   │   ├── SourceAttribution.tsx
│   │   ├── VerdictPanel.tsx
│   │   ├── RequirementsPanel.tsx
│   │   ├── RawTextCollapsible.tsx
│   │   ├── StackInput.tsx
│   │   ├── Toast.tsx
│   │   └── ErrorBoundary.tsx
│   ├── App.tsx                  # router + providers
│   ├── main.tsx                 # QueryClientProvider + BrowserRouter + StrictMode
│   └── index.css                # @tailwind base/components/utilities
├── index.html
├── vite.config.ts               # proxy /api → api:8000
├── tailwind.config.js
├── tsconfig.json
└── Dockerfile                   # multi-stage: dev (HMR) y build (dist/)
```

## Decisiones técnicas

| Decisión | Alternativa considerada | Por qué esta |
|---|---|---|
| **TanStack Query** | SWR / fetch manual | DevTools, soporte de mutaciones, invalidación por key, `staleTime` declarativo |
| **Zod** para validación | Yup / validación manual | Inferencia de tipos directa desde el schema; mantiene en sync con Pydantic |
| **React Hook Form** | Formik | Menos re-renders, integración nativa con Zod via `@hookform/resolvers` |
| **Tailwind CSS** | CSS modules / MUI | Velocity de prototipado, sin archivos `.css` separados, purge automático |
| **React Router v6** | Wouter / Next.js | Routing estándar SPA; no necesitamos SSR ni file-based routing |
| **Vite proxy** (no CORS) | CORS + directo a API | Evita CORS en dev; el proxy reescribe `/api/*` → `http://api:8000/*` dentro de la red Docker |

## Rutas de la SPA

| Path | Componente | Descripción |
|---|---|---|
| `/` | `MatchesList` | Lista de matches del perfil activo. Requiere `profileId` en localStorage |
| `/matches/:jobId` | `MatchDetail` | Detalle completo: verdict, requirements, strengths/risks |
| `/profile` | `ProfileForm` | Crear/actualizar perfil. Pre-llena con `sample_profile.json` si no hay nada en localStorage |

## Cómo correr

```bash
# Dev con HMR (requiere api + app-db levantados)
docker compose up -d app-db api
docker compose up -d frontend
open http://127.0.0.1:5173

# Demo (frontend buildeado servido por FastAPI)
docker compose --profile demo up --build -d
open http://127.0.0.1:8000
```

## Mapa de fases

| Fase | Doc | Entregable |
|---|---|---|
| F1 · Bootstrap | [phase-1-bootstrap.md](phase-1-bootstrap.md) | Vite corriendo en Docker, hello world contra `/api/health` |
| F2 · Cliente API | [phase-2-api-client.md](phase-2-api-client.md) | Tipos TS + cliente HTTP + QueryClientProvider |
| F3 · Lista matches | [phase-3-matches-list.md](phase-3-matches-list.md) | Grid de cards con scores y fortalezas |
| F4 · Detalle match | [phase-4-match-detail.md](phase-4-match-detail.md) | Página con verdict completo |
| F5 · Formulario perfil | [phase-5-profile-form.md](phase-5-profile-form.md) | Form tipado que upsertea el perfil |
| F6 · Refresh + polish | [phase-6-refresh-polish.md](phase-6-refresh-polish.md) | Header funcional, toasts, responsive |
| F7 · Build + FastAPI | [phase-7-build-fastapi.md](phase-7-build-fastapi.md) | Un solo `docker compose up` sirve todo en `:8000` |

## Convenciones

- **Sin comentarios** salvo WHY no obvio.
- **Tipos siempre explícitos**: no `any`. Las respuestas de la API se castean a los tipos de `src/types/api.ts`.
- **No lógica en componentes de pantalla**: los `pages/` solo componen; la lógica de fetch va en hooks TanStack Query definidos inline o en el mismo archivo de la página.
- **`profileId` viene siempre de `profileStorage.ts`**: ningún componente lee localStorage directamente.
- **Atribución de fuentes**: `SourceAttribution` siempre visible en `/` (obligatorio por términos de Himalayas y Remotive).
