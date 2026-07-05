# Fase F6 · Refresh + polish

**Tiempo estimado:** 2 horas
**Entregable demostrable:** header visible en todas las páginas con botón "Refrescar ofertas" que lanza el pipeline y muestra un aviso inline; health badge verde cuando la API responde `ok`.

---

## 1. Objetivo

Completa las acciones del usuario y da feedback de estado del sistema. Agrega el header global con navegación, el botón de refresh del pipeline, el health badge, toasts básicos y un ErrorBoundary global. También revisa responsive en mobile.

**Fuera de scope:** animaciones complejas, paginación de matches, historial de runs del pipeline.

---

## 2. Decisiones

- **Toast con `sonner`** (librería de 1 sola dependencia, <2 KB gzip): evita implementar un sistema de toasts desde cero. Se agrega al `package.json` y se inicializa en `main.tsx` con `<Toaster />`. Si se prefiere cero deps adicionales, se puede hacer con `useState` + portal, pero `sonner` es el estándar de facto en el ecosistema Vite/TanStack.
- **`invalidateQueries(["matches"])` después del refresh**: el botón llama a `refreshJobs()` y luego invalida la cache de matches. La re-fetch ocurre sola. No hace falta un timer manual porque el scoring del backend corre en background task (~30s); el usuario puede refrescar el browser cuando quiera.
- **`<Header>` como componente, no layout nested**: se monta en `App.tsx` fuera del `<Routes>` para que aparezca en todas las páginas sin tener que agregar `<Outlet>` ni reestructurar las routes existentes.
- **ErrorBoundary con clase React**: no hay librería para esto; se escribe la clase directamente con `componentDidCatch`. Fallback simple con mensaje y botón "Recargar".
- **Health badge en el header**: consulta `useQuery(["health"])` con `staleTime: 30s`. No añade una request extra porque TanStack Query deduplica con la misma key.

---

## 3. Archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `frontend/src/components/Header.tsx` | Crear | Barra top: logo, nav links, botón refresh, health badge |
| `frontend/src/components/ErrorBoundary.tsx` | Crear | Clase React con `componentDidCatch`, fallback simple |
| `frontend/src/App.tsx` | Modificar | Monta `<Header>` arriba de `<Routes>`, envuelve en `<ErrorBoundary>` |
| `frontend/src/main.tsx` | Modificar | Agrega `<Toaster />` de sonner |
| `frontend/package.json` | Modificar | Agrega `sonner` en dependencies |

---

## 4. Implementación

### Header — estructura

```
[Job Match Pipeline]   [Mis matches]  [Mi perfil]    [🟢] [Refrescar]
```

- Logo/título: `<Link to="/">` con texto "Job Match"
- Links: `<NavLink to="/">Mis matches</NavLink>`, `<NavLink to="/profile">Mi perfil</NavLink>`
- Health badge: punto circular verde (`bg-green-400`) si `health.status === "ok"`, naranja si no hay data o error
- Botón "Refrescar ofertas": llama `refreshJobs()`, luego `queryClient.invalidateQueries(["matches"])`. Muestra `toast.success("Pipeline en curso (~30s)")`. Mientras `isPending`: texto "Iniciando..." + disabled.

### Botón refresh — lógica

```ts
const mutation = useMutation({
  mutationFn: refreshJobs,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["matches"] });
    toast.success("Pipeline en curso. Los matches se actualizarán en ~30s.");
  },
  onError: (err) => toast.error(err.message),
});
```

### Responsive — revisión

- `MatchCard`: título con `line-clamp-2` (ya está), grid 1/2/3 cols (ya está)
- `Header`: en mobile, links colapsados o en fila scroll horizontal. No hace falta hamburger menu para 2 links.
- `ProfileForm`: inputs a ancho completo en mobile (ya están con `w-full`)

---

## 5. Criterios de aceptación

- [ ] `docker compose run --rm frontend npm run type-check` → 0 errores
- [ ] Header visible en `/`, `/profile` y `/matches/:id`
- [ ] Click "Refrescar ofertas" → toast "Pipeline en curso" → `POST /api/jobs/refresh` en Network
- [ ] Botón disabled mientras la mutación está pendiente
- [ ] Health badge verde cuando `GET /api/health` devuelve `{status: "ok"}`
- [ ] Si la API está caída: badge naranja (o gris si no hubo respuesta)
- [ ] Error en render de cualquier page → ErrorBoundary muestra fallback (sin crash total)
- [ ] Mobile 375px: header en 1 línea usable, grid 1 columna, form usable

---

## 6. Lo que NO se hace en esta fase

- Polling automático post-refresh para mostrar matches nuevos (el usuario hace pull-to-refresh o recarga) → fuera de scope del MVP
- Notificaciones push / WebSocket → fuera de scope
- Modo oscuro / tema claro → fuera de scope (toda la UI ya es oscura)
- Animaciones de transición entre páginas → fuera de scope
- Hamburger menu con drawer → fuera de scope para 2 links de nav
