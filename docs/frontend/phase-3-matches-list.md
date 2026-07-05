# Fase F3 · Lista de matches

**Tiempo estimado:** 2 horas
**Entregable demostrable:** abrir `http://127.0.0.1:5173/`, ingresar `daniel-2026` en el gate provisional, y ver el grid de cards con scores coloreados y bullets de fortalezas/riesgos.

---

## 1. Objetivo

Primera pantalla con valor visible: muestra los matches del perfil actual ordenados por `llm_score` desc. Como F5 (formulario de perfil) aún no existe, se incluye un `ProfileIdGate` provisional que pide el id del perfil por teclado y lo persiste en `localStorage`. En F5 este gate se reemplaza por el form completo.

**Fuera de scope:** header global, botón refresh, toasts, detalle de match, formulario real.

---

## 2. Decisiones

- **Input provisional (`ProfileIdGate`) en lugar de redirect a `/profile`:** F5 no existe todavía. El gate permite probar F3 end-to-end con `daniel-2026` ya cargado en BD. `window.location.reload()` tras `setCurrentProfileId` es lo más simple y está acotado a este componente provisional; F5 lo reemplazará con `invalidateQueries` + `navigate`.
- **`useQuery` con `enabled: profileId !== null`:** así las reglas de Hooks no se violan (siempre se llama el hook) pero la query no se lanza hasta tener un id.
- **Skeleton con Tailwind `animate-pulse`:** evita una dependencia extra; el look es coherente con el resto del diseño oscuro.
- **`MatchCard` como `<Link>`:** linkea a `/matches/:jobId` aunque F4 aún no exista. Cuando F4 mergee, todos los cards se activan sin tocar F3.
- **Sin layout component todavía:** el Header global llega en F6. Cada page renderiza su propio título inline para reducir el churn.
- **TanStack Query como único server state:** no se agrega Zustand ni estado global. `staleTime: 30s` evita refetch al navegar entre F3 ↔ F4.

---

## 3. Archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `frontend/src/pages/MatchesList.tsx` | Crear | Route `/`; orquesta el gate, la query y el grid |
| `frontend/src/components/ProfileIdGate.tsx` | Crear | Input provisional de profileId (reemplazado en F5) |
| `frontend/src/components/MatchCard.tsx` | Crear | Card individual; muestra score, título, empresa, bullets |
| `frontend/src/components/ScoreBadge.tsx` | Crear | Pill con coloreado por rango (≥70 verde, ≥40 amarillo, <40 gris) |
| `frontend/src/components/SourceAttribution.tsx` | Crear | Footer con texto de atribución (obligatorio por T&C) |
| `frontend/src/App.tsx` | Modificar | Reemplaza el health widget por `<Routes>` con `/` → `MatchesList` |

---

## 4. Implementación

### MatchesList — flujo principal

```
getCurrentProfileId() === null → <ProfileIdGate />
getCurrentProfileId() !== null → useQuery("matches", profileId, enabled: true)
  isLoading  → <SkeletonGrid />           (6 cards con animate-pulse)
  error      → alert rojo                 (mensaje especial si status 404)
  count === 0 → mensaje vacío
  count > 0  → grid 1/2/3 cols + SourceAttribution
```

Header inline simple: título + `profileId` en mono + botón "cambiar" (llama `clearCurrentProfileId()` + reload).

### ScoreBadge — coloreado

```
score >= 70 → bg-green-500/20 text-green-300
score >= 40 → bg-yellow-500/20 text-yellow-300
score <  40 → bg-gray-700 text-gray-400
score null  → "—" en gris
```

Muestra `Math.round(score)` en un círculo de 48×48 px.

### MatchCard — layout

```
[ScoreBadge] [título (truncate)]
             [empresa (truncate)]
             [badge fuente] [sem XX]
─────────────────────────────────
+ fortaleza 1 (text-green-400)
+ fortaleza 2
- riesgo 1    (text-gray-500)
- riesgo 2
```

Muestra las primeras 2 fortalezas y los primeros 2 riesgos. Si `verdict === null`, la sección inferior no se renderiza.

---

## 5. Criterios de aceptación

- [ ] `docker compose run --rm frontend npm run type-check` → 0 errores
- [ ] Abrir `http://127.0.0.1:5173/` con `localStorage` vacío → muestra `ProfileIdGate` con input y botón
- [ ] Ingresar `daniel-2026` + submit → reload → grid de ~20 cards visible
- [ ] Cards con `llm_score >= 70` muestran pill verde; `40–69` amarillo; `< 40` gris
- [ ] Cada card muestra hasta 2 bullets de fortalezas (verde) y 2 de riesgos (gris)
- [ ] Footer con texto de atribución de fuentes
- [ ] Botón "cambiar" en el header inline limpia el id y vuelve al gate
- [ ] Click en una card navega a `/matches/<id>` (sin contenido — OK, F4 lo completa)
- [ ] DevTools Network: 1 sola request a `/api/matches?profile_id=daniel-2026&limit=20`
- [ ] Mobile 375px: grid colapsa a 1 columna

---

## 6. Lo que NO se hace en esta fase

- Header global con logo, navegación y botón "Refrescar ofertas" → F6
- Health badge → F6
- Toasts → F6
- ErrorBoundary global → F6
- Detalle del match (route `/matches/:jobId` real) → F4
- Formulario de perfil → F5
- Filtros, ordenamiento o paginación → el backend ya devuelve ordenado por score; los 20 top caben en pantalla
