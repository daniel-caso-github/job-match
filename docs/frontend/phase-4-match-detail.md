# Fase F4 · Detalle de match

**Tiempo estimado:** 1.5 horas
**Entregable demostrable:** click en una card de F3 → página `/matches/:jobId` con score, fortalezas, riesgos, requisitos extraídos y link al posting original.

---

## 1. Objetivo

Segunda pantalla con valor real: muestra el detalle completo de un match — verdict con fortalezas/riesgos completos, requisitos extraídos por Gemini (stack, seniority, flags de modalidad) y el texto crudo colapsable. Requiere el `profile_id` del perfil activo (viene de `localStorage`).

**Fuera de scope:** header global, toasts, botón refresh, formulario de perfil.

---

## 2. Decisiones

- **`useParams` para el `jobId`:** React Router inyecta el id desde la URL `/matches/:jobId`. No se necesita estado global.
- **`profileId` de `localStorage`:** igual que en F3, `getCurrentProfileId()` sin prop drilling.
- **`<details>` nativo para el raw_text:** evita una librería de acordeón; el comportamiento del browser es suficiente. El texto es largo pero solo interesa a usuarios técnicos; colapsado por defecto.
- **`ScoreBadge` reutilizado de F3:** mismo componente, contexto diferente. Confirma que la abstracción es correcta.
- **Link `← Volver` → `/`:** navega de vuelta a la lista. No es un `history.back()` para evitar comportamiento raro si el usuario llegó directo por URL.

---

## 3. Archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `frontend/src/pages/MatchDetail.tsx` | Crear | Route `/matches/:jobId`; orquesta query y sub-paneles |
| `frontend/src/components/VerdictPanel.tsx` | Crear | Score + 2 columnas fortalezas/riesgos completas |
| `frontend/src/components/RequirementsPanel.tsx` | Crear | Stack chips, badges de seniority/inglés, flags booleanos, salary |
| `frontend/src/components/RawTextCollapsible.tsx` | Crear | `<details>` con texto crudo de la oferta |
| `frontend/src/App.tsx` | Modificar | Agrega route `/matches/:jobId` → `MatchDetail` |

---

## 4. Implementación

### MatchDetail — flujo

```
useParams() → jobId
getCurrentProfileId() → profileId (null → mensaje + link volver)
useQuery("match", jobId, profileId, enabled: !!jobId && !!profileId)
  isLoading → skeleton
  error 404  → "Match no encontrado"
  error otro → error.message
  data       → header (score + título + empresa + link posting)
               VerdictPanel (si data.verdict)
               RequirementsPanel (si data.requirements)
               RawTextCollapsible (si data.raw_text)
               SourceAttribution
```

### VerdictPanel — layout

```
┌─────────────────────────────────┐
│ VEREDICTO              sem XX   │
├────────────────┬────────────────┤
│ FORTALEZAS     │ RIESGOS        │
│ + fortaleza 1  │ - riesgo 1     │
│ + fortaleza 2  │ - riesgo 2     │
│ ...            │ ...            │
└────────────────┴────────────────┘
```

### RequirementsPanel — secciones

1. Stack: chips `font-mono` en gris-800
2. Badges: seniority + inglés + salary_range
3. Flags: `remote`, `latam_friendly` (verde si true, tachado si false), `requires_eu_residency` (rojo si true)
4. Confianza: `Math.round(confidence * 100)%` en esquina superior derecha

---

## 5. Criterios de aceptación

- [ ] `docker compose run --rm frontend npm run type-check` → 0 errores
- [ ] Click en card de F3 → navega a `/matches/<id>` y muestra el detalle
- [ ] Score visible con color correcto (mismo `ScoreBadge` de F3)
- [ ] Fortalezas completas en columna verde, riesgos en columna roja
- [ ] Requisitos: chips de stack, badges de seniority/inglés, flags booleanos coloreados
- [ ] Link "Ver oferta original ↗" abre en pestaña nueva
- [ ] "← Volver" navega a `/`
- [ ] `GET /api/matches/<id>?profile_id=...` aparece en DevTools Network (1 request)
- [ ] Si `raw_text` presente: acordeón colapsado por defecto, expandible con click

---

## 6. Lo que NO se hace en esta fase

- Header global con navegación → F6
- Toasts → F6
- ErrorBoundary → F6
- Botón "Refrescar" → F6
- Formulario de perfil → F5
- Edición / bookmarks del match → fuera de scope
