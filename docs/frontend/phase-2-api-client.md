# Fase F2 · Cliente API + tipos + TanStack Query

**Tiempo estimado:** 1-2 horas
**Entregable demostrable:** `npm run type-check` sin errores. `http://127.0.0.1:5173` muestra el mismo health que F1 pero ahora el fetch pasa por TanStack Query (`useQuery`) en vez de `useState` + `useEffect` manual.

---

## 1. Objetivo

Dejar listo todo el "plumbing" de datos para que las pantallas F3-F6 solo se ocupen de UI:
- **Tipos TS exhaustivos** espejando los schemas Pydantic del backend (sin `any`)
- **Cliente HTTP centralizado** con manejo de errores tipados
- **TanStack Query** configurado como provider global
- **`profileStorage`** como única interfaz al `localStorage`

Esta fase es invisible al usuario — la pantalla sigue mostrando el health de F1. La diferencia es interna.

---

## 2. Decisiones

| Decisión | Por qué |
|---|---|
| String literal unions en vez de `enum` TS | Alinea con `StrEnum` de Pydantic; los valores son el wire-format JSON directamente |
| `ApiError` como clase | Permite `error instanceof ApiError && error.status === 404` en componentes |
| Sin `axios` ni `ky` | `fetch` nativo alcanza para 5 endpoints; menos deps, sin magia implícita |
| Sin barrel exports | Imports explícitos → mejor tree-shaking, más fácil rastrear qué viene de dónde |
| `staleTime: 30_000` | El pipeline tarda ~30s en procesar; no tiene sentido refetch más rápido |
| `refetchOnWindowFocus: false` | Molesta durante desarrollo cuando se alterna editor/browser |
| `BrowserRouter` ya en F2 | Evita tocar `main.tsx` en F3 cuando se agregan las rutas |
| `profileStorage` como wrapper | Ningún componente lee `localStorage` directo; si migramos a otro storage solo cambia este archivo |

---

## 3. Archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `frontend/src/types/api.ts` | Crear | Todos los tipos TS de los 5 endpoints |
| `frontend/src/lib/api.ts` | Crear | `ApiError`, `apiFetch<T>`, funciones por endpoint |
| `frontend/src/lib/queryClient.ts` | Crear | Instancia `QueryClient` con defaults |
| `frontend/src/lib/profileStorage.ts` | Crear | `get/set/clear` del `profileId` activo |
| `frontend/src/main.tsx` | Modificar | Envolver `<App>` con `<QueryClientProvider>` + `<BrowserRouter>` |
| `frontend/src/App.tsx` | Modificar | Reemplazar fetch manual por `useQuery({ queryFn: getHealth })` |

---

## 4. Implementación

### `types/api.ts` — enums como string literal unions

```ts
export type Seniority = "junior" | "mid" | "senior" | "lead" | "staff";
export type EnglishLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2" | "native";
export type Modality = "remote" | "hybrid" | "onsite";
```

Los valores coinciden exactamente con los `StrEnum` de Pydantic. JSON parsing no necesita ninguna transformación.

### `lib/api.ts` — `ApiError` y `apiFetch`

```ts
export class ApiError extends Error {
  constructor(public readonly status: number, public readonly body: unknown) {
    super(`API error ${status}`);
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}
```

Cada función de endpoint llama a `apiFetch<TipoEsperado>(...)`. El type cast es seguro porque el backend tiene schemas Pydantic fijos.

### `main.tsx` — providers

```tsx
<QueryClientProvider client={queryClient}>
  <BrowserRouter>
    <App />
  </BrowserRouter>
</QueryClientProvider>
```

`BrowserRouter` se agrega ya (F3 lo necesita) para no tocar `main.tsx` en la siguiente fase.

---

## 5. Criterios de aceptación

- [ ] `docker compose run --rm frontend npm run type-check` termina sin errores
- [ ] `http://127.0.0.1:5173` sigue mostrando el health (mismo visual que F1)
- [ ] DevTools → Network: request a `/api/health` aparece una sola vez al cargar
- [ ] Editar un tipo en `types/api.ts` → TypeScript marca error en `api.ts` si el tipo no coincide (verificar que el check funciona)

---

## 6. Lo que NO se hace en esta fase

- Ninguna pantalla nueva (la app sigue mostrando el health)
- Rutas con React Router (solo se instala el `<BrowserRouter>`, sin `<Routes>`)
- `useMutation` (va en F5, para el formulario de perfil)
- Tests del cliente API (opcional, puede dejarse para después de F3)
