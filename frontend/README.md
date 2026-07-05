# Job Match — Frontend

> SPA React que consume la API de Job Match Pipeline y muestra matches con veredicto, filtros avanzados, drawer de detalle y programación de búsquedas.

---

## Stack

React 18.3 · TypeScript 5.5 · Vite 5.4 · Tailwind 3.4 · TanStack Query 5.56 · React Hook Form 7 + Zod 3.23 · React Router v6 · Sonner · Inter + JetBrains Mono (self-hosted)

---

## Cómo correr

**Docker-only** — se levanta junto con el resto del proyecto:

```bash
# Desde la raíz del repo:
docker compose up -d
```

El servicio `frontend` corre `npm run dev` (Vite con HMR) dentro del contenedor. **No publica puerto propio** — el acceso al usuario va vía nginx:

- **UI:** <http://127.0.0.1> (puerto 80 → nginx → `frontend:5173`)
- **API (Swagger):** <http://127.0.0.1:8000/docs>

> El proxy `/api` en `vite.config.ts` apunta a `http://api:8000` dentro de la red de compose. Si intentás correr `npm run dev` directamente en tu máquina, las llamadas a `/api/*` no resolverán.

### Scripts npm (disponibles dentro del contenedor)

| Script | Descripción |
|---|---|
| `npm run dev` | Dev server con HMR (Vite, puerto 5173) |
| `npm run build` | Typecheck + build de producción a `dist/` |
| `npm run type-check` | Solo `tsc --noEmit` |
| `npm run preview` | Sirve el build de `dist/` localmente |

---

## Estructura de `src/`

```
src/
├── pages/              # Pantallas (route-level)
│   ├── MatchesList.tsx   — lista principal + drawer de detalle
│   ├── SearchPage.tsx    — formulario de búsqueda programada
│   ├── SchedulesPage.tsx — historial de corridas y búsquedas guardadas
│   └── ProfileForm.tsx   — crear / actualizar perfil profesional
├── components/         # Componentes de features
│   ├── Gate.tsx          — pantalla de login (username + password)
│   ├── Header.tsx        — barra de navegación + health pill + theme toggle
│   ├── MatchCard.tsx     — card resumida en la lista
│   ├── MatchDetailDrawer.tsx — drawer de detalle (score, veredicto, requisitos)
│   ├── FiltersSidebar.tsx — sidebar de filtros de matches
│   ├── PipelineRunsDrawer.tsx — drawer de historial de corridas
│   ├── VerdictPanel.tsx, RequirementsPanel.tsx, RawTextCollapsible.tsx
│   ├── ScoreBadge.tsx, SourceBadge.tsx, SourceAttribution.tsx
│   ├── StageStepper.tsx, StatusChip.tsx, StackInput.tsx
│   └── ui/               — primitivas: Drawer, FilterChip, MultiSelect,
│                            SegmentedControl, ToggleSwitch, Logo, icons
├── lib/                # Lógica no-UI
│   ├── api.ts            — cliente HTTP tipado + ApiError
│   ├── searchFilters.ts  — tipo SearchFilters, defaults, serializadores, toMatchFilters
│   ├── profileStorage.ts — localStorage: profileId, username, token JWT
│   ├── profile-context.tsx — ProfileProvider + useProfile()
│   ├── queryClient.ts    — configuración de TanStack Query
│   ├── schemas.ts        — schemas Zod (registro, perfil)
│   ├── format.ts         — formateo de fechas, safeHref
│   ├── score.ts          — score → color, metadatos de fuentes
│   └── pipeline.ts       — helpers de estado de corridas
├── hooks/
│   ├── useTheme.ts       — dark/light con persistencia en localStorage
│   └── useSearchFilters.ts — filtros de matches persistidos
└── types/
    └── api.ts            — interfaces TypeScript de todos los responses/requests
```

---

## Rutas y flujo

El routing está **gated por `profileId`**: sin perfil activo solo se accede a `/profile`; todo lo demás renderiza `<Gate>` (pantalla de login).

| Ruta | Componente | Descripción |
|---|---|---|
| `/` | `MatchesList` | Lista principal con sidebar de filtros |
| `/matches/:jobId` | `MatchesList` + `MatchDetailDrawer` | Drawer de detalle sobre la lista |
| `/search` | `SearchPage` | Programar búsqueda con filtros y frecuencia |
| `/programaciones` | `SchedulesPage` | Historial de corridas del pipeline y búsquedas guardadas |
| `/profile` | `ProfileForm` | Crear o actualizar el perfil profesional |

**Flujo típico de un usuario nuevo:**

1. **Gate** → ingresa username + password → `POST /api/auth/login` → JWT guardado en localStorage.
2. **Lista de matches** → sidebar de filtros → `GET /api/matches` con Bearer token → cards con score y fortaleza principal.
3. Click en una card → **drawer de detalle** → veredicto, fortalezas/riesgos, requisitos estructurados, link a la oferta original (sanitizado con `safeHref`).
4. Acceder a `/search` → configurar filtros → `POST /api/jobs/schedule-run` → búsqueda programada para 12h, guardada en BD.
5. **`/programaciones`** → ver timeline de corridas y estado por task (StageStepper); poll cada 30s.

---

## Comunicación con la API

### Cliente HTTP (`lib/api.ts`)

Función genérica `apiFetch<T>` que:
- Añade `Content-Type: application/json`.
- Lee el JWT de la sesión actual y añade `Authorization: Bearer <token>` en cada request.
- Lanza `ApiError(status, body)` en respuestas no-2xx.

Todas las llamadas usan rutas relativas `/api/...` que el proxy de Vite reescribe a `http://api:8000/...` (sin el prefijo `/api`).

### Endpoints consumidos

| Función en `api.ts` | Método + Path | Auth |
|---|---|---|
| `login` | `POST /api/auth/login` | — |
| `registerProfile` | `POST /api/profile` | — |
| `getProfile` | `GET /api/profile/{id}` | ✓ |
| `getMatches` | `GET /api/matches` | ✓ |
| `getMatchDetail` | `GET /api/matches/{job_id}` | ✓ |
| `getJobsSchedule` | `GET /api/jobs/schedule` | — |
| `getPipelineRuns` | `GET /api/jobs/runs` | — |
| `scheduleSearchRun` | `POST /api/jobs/schedule-run` | ✓ |
| `getSavedSearches` | `GET /api/jobs/searches` | ✓ |
| `getTechnologies` | `GET /api/jobs/technologies` | — |

### Filtros y serializadores (`lib/searchFilters.ts`)

`SearchFilters` define el estado de la UI (camelCase: `minScore`, `remoteOnly`, `englishMax`, etc.). Dos serializadores lo convierten al formato de la API:

- **`filtersToQueryParams`** — para `GET /api/matches`: convierte a query string (`min_score`, `source`, `stack`, `seniority`, `english_max`, flags booleanos).
- **`toMatchFilters`** — para `POST /api/jobs/schedule-run`: convierte a JSON snake_case compatible con `MatchFilters` Pydantic (expande `englishMax` a la lista de niveles de idioma).

### Sesión (`lib/profileStorage.ts` + `lib/profile-context.tsx`)

La sesión (`profileId`, `username`, `token`) se persiste en `localStorage["jobmatch.session"]`. `ProfileProvider` la expone via `useProfile()` con `login(session)` / `logout()` (logout limpia el token pero recuerda el último username para el Gate).

---

## Features

- **Tema dark/light** — `hooks/useTheme.ts`, persistido en `localStorage["jobmatch.theme"]`. Script inline en `index.html` aplica el tema antes del primer render (evita flash). Toggle disponible en el header y en el Gate.
- **Filtros persistidos** — `hooks/useSearchFilters.ts` guarda los filtros en `localStorage["jobmatch.searchFilters"]` y los restaura entre sesiones.
- **Health pill** — `Header.tsx` consulta `GET /api/health` cada 60s. Muestra el estado (OK / Degradado / Sin conexión) con tooltip de BD, Gemini key y modelo.
- **Auto-refresh mientras corre el pipeline** — `MatchesList.tsx` detecta corridas activas y hace poll de matches cada 15s; cuando finaliza, invalida las queries y muestra un toast "Pipeline finalizado".
- **Atribución de fuentes** — `SourceAttribution.tsx` muestra el string de atribución devuelto por la API (obligatorio por los términos de Himalayas y Remotive).
- **`safeHref`** (`lib/format.ts`) — filtra URLs de ofertas scrapeadas para que solo pasen esquemas `http/https`, evitando que una URL maliciosa (`javascript:...`) se ejecute al hacer click.
- **Keyword filter** — aplicado del lado cliente sobre título, empresa, fortalezas y riesgos (`matchesKeywords` en `searchFilters.ts`), sin round-trip a la API.

---

## Convenciones

- Sin `any` explícito; todas las interfaces en `types/api.ts`.
- Sin lógica en componentes de página — extraída a `lib/` y `hooks/`.
- `profileId` siempre via `useProfile()`, nunca leer `localStorage` directamente en un componente.
- Atribución de fuentes obligatoria: `<SourceAttribution>` en lista y drawer.
- Los docs de fases en `docs/frontend/` describen el diseño incremental pero su inventario de archivos está desactualizado; este README es la referencia vigente.
