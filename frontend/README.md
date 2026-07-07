# Job Match — Frontend

> React SPA that consumes the Job Match Pipeline API and displays matches with verdict, advanced filters, a detail drawer, and scheduled searches.
>
> Part of [Job Match Pipeline](../README.md) — see the root README for backend architecture, pipeline, and quickstart.

---

## Stack

React 18.3 · TypeScript 5.5 · Vite 5.4 · Tailwind 3.4 · TanStack Query 5.56 · React Hook Form 7 + Zod 3.23 · React Router v6 · Sonner · Inter + JetBrains Mono (self-hosted)

---

## How to run

**Docker-only** — starts alongside the rest of the project:

```bash
# From the repo root:
docker compose up -d
```

The `frontend` service runs `npm run dev` (Vite with HMR) inside the container. **It does not expose its own port** — user access goes through nginx:

- **UI:** <http://127.0.0.1> (port 80 → nginx → `frontend:5173`)
- **API (Swagger):** <http://127.0.0.1:8000/docs>

> The `/api` proxy in `vite.config.ts` points to `http://api:8000` inside the compose network. If you run `npm run dev` directly on your machine, calls to `/api/*` will not resolve.

### npm scripts (available inside the container)

| Script | Description |
|---|---|
| `npm run dev` | Dev server with HMR (Vite, port 5173) |
| `npm run build` | Typecheck + production build to `dist/` |
| `npm run type-check` | `tsc --noEmit` only |
| `npm run preview` | Serves the `dist/` build locally |

---

## `src/` structure

```
src/
├── pages/              # Screens (route-level)
│   ├── MatchesList.tsx   — main list + detail drawer
│   ├── SearchPage.tsx    — scheduled search form
│   ├── SchedulesPage.tsx — pipeline run history and saved searches
│   └── ProfileForm.tsx   — create / update professional profile
├── components/         # Feature components
│   ├── Gate.tsx          — login screen (username + password)
│   ├── Header.tsx        — navigation bar + health pill + theme toggle
│   ├── MatchCard.tsx     — summary card in the list
│   ├── MatchDetailDrawer.tsx — detail drawer (score, verdict, requirements)
│   ├── FiltersSidebar.tsx — matches filter sidebar
│   ├── PipelineRunsDrawer.tsx — pipeline run history drawer
│   ├── VerdictPanel.tsx, RequirementsPanel.tsx, RawTextCollapsible.tsx
│   ├── ScoreBadge.tsx, SourceBadge.tsx, SourceAttribution.tsx
│   ├── StageStepper.tsx, StatusChip.tsx, StackInput.tsx
│   └── ui/               — primitives: Drawer, FilterChip, MultiSelect,
│                            SegmentedControl, ToggleSwitch, Logo, icons
├── lib/                # Non-UI logic
│   ├── api.ts            — typed HTTP client + ApiError
│   ├── searchFilters.ts  — SearchFilters type, defaults, serializers, toMatchFilters
│   ├── profileStorage.ts — localStorage: profileId, username, JWT token
│   ├── profile-context.tsx — ProfileProvider + useProfile()
│   ├── queryClient.ts    — TanStack Query configuration
│   ├── schemas.ts        — Zod schemas (registration, profile)
│   ├── format.ts         — date formatting, safeHref
│   ├── score.ts          — score → color, source metadata
│   └── pipeline.ts       — run state helpers
├── hooks/
│   ├── useTheme.ts       — dark/light with localStorage persistence
│   └── useSearchFilters.ts — persisted match filters
└── types/
    └── api.ts            — TypeScript interfaces for all responses/requests
```

---

## Routes and flow

Routing is **gated by `profileId`**: without an active profile only `/profile` is accessible; everything else renders `<Gate>` (login screen).

| Route | Component | Description |
|---|---|---|
| `/` | `MatchesList` | Main list with filter sidebar |
| `/matches/:jobId` | `MatchesList` + `MatchDetailDrawer` | Detail drawer over the list |
| `/search` | `SearchPage` | Schedule a search with filters and frequency |
| `/programaciones` | `SchedulesPage` | Pipeline run history and saved searches |
| `/profile` | `ProfileForm` | Create or update the professional profile |

**Typical new-user flow:**

1. **Gate** → enters username + password → `POST /api/auth/login` → JWT stored in localStorage.
2. **Matches list** → filter sidebar → `GET /api/matches` with Bearer token → cards with score and top strength.
3. Click a card → **detail drawer** → verdict, strengths/risks, structured requirements, link to the original posting (sanitized with `safeHref`).
4. Go to `/search` → configure filters → `POST /api/jobs/schedule-run` → search scheduled for 12h, saved to DB.
5. **`/programaciones`** → view run timeline and per-task status (StageStepper); polled every 30s.

---

## API communication

### HTTP client (`lib/api.ts`)

Generic `apiFetch<T>` function that:
- Adds `Content-Type: application/json`.
- Reads the JWT from the current session and adds `Authorization: Bearer <token>` to every request.
- Throws `ApiError(status, body)` on non-2xx responses.

All calls use relative paths `/api/...` that the Vite proxy rewrites to `http://api:8000/...` (stripping the `/api` prefix).

### Consumed endpoints

| Function in `api.ts` | Method + Path | Auth |
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

### Filters and serializers (`lib/searchFilters.ts`)

`SearchFilters` defines the UI state (camelCase: `minScore`, `remoteOnly`, `englishMax`, etc.). Two serializers convert it to the API format:

- **`filtersToQueryParams`** — for `GET /api/matches`: converts to query string (`min_score`, `source`, `stack`, `seniority`, `english_max`, boolean flags).
- **`toMatchFilters`** — for `POST /api/jobs/schedule-run`: converts to snake_case JSON compatible with the Pydantic `MatchFilters` schema (expands `englishMax` into the list of language levels).

### Session (`lib/profileStorage.ts` + `lib/profile-context.tsx`)

The session (`profileId`, `username`, `token`) is persisted in `localStorage["jobmatch.session"]`. `ProfileProvider` exposes it via `useProfile()` with `login(session)` / `logout()` (logout clears the token but remembers the last username for the Gate).

---

## Features

- **Dark/light theme** — `hooks/useTheme.ts`, persisted in `localStorage["jobmatch.theme"]`. An inline script in `index.html` applies the theme before the first render (prevents flash). Toggle available in the header and in the Gate.
- **Persisted filters** — `hooks/useSearchFilters.ts` saves filters to `localStorage["jobmatch.searchFilters"]` and restores them across sessions.
- **Health pill** — `Header.tsx` polls `GET /api/health` every 60s. Shows status (OK / Degraded / Offline) with a tooltip showing DB, Gemini key, and model.
- **Auto-refresh while pipeline runs** — `MatchesList.tsx` detects active runs and polls matches every 15s; on completion, invalidates queries and shows a "Pipeline finished" toast.
- **Source attribution** — `SourceAttribution.tsx` displays the attribution string returned by the API (required by Himalayas and Remotive terms of service).
- **`safeHref`** (`lib/format.ts`) — filters scraped job URLs to allow only `http/https` schemes, preventing a malicious URL (`javascript:...`) from executing on click.
- **Keyword filter** — applied client-side over title, company, strengths, and risks (`matchesKeywords` in `searchFilters.ts`), with no API round-trip.

---

## Conventions

- No explicit `any`; all interfaces in `types/api.ts`.
- No logic in page components — extracted to `lib/` and `hooks/`.
- `profileId` always via `useProfile()`, never reading `localStorage` directly in a component.
- Source attribution is mandatory: `<SourceAttribution>` in both the list and the drawer.
