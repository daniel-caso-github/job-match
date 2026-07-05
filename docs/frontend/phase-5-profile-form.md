# Fase F5 · Formulario de perfil

**Tiempo estimado:** 2.5 horas
**Entregable demostrable:** abrir `http://127.0.0.1:5173/profile`, ver el form precargado con `sample_profile.json`, modificar campos, submitir y recibir redirect a `/` con los matches del nuevo perfil.

---

## 1. Objetivo

Reemplaza el `<ProfileIdGate />` provisional de F3 con el flujo completo de creación de perfil: formulario tipado con validación Zod, array dinámico de stack, llamada a `POST /api/profile` y persistencia del `profile_id` en `localStorage`. El usuario puede crear o actualizar su perfil sin tocar JSON.

**Fuera de scope:** edición de un perfil existente (actualizar campos individuales), historial de perfiles, validación de id único (la API devuelve 409 si ya existe — se muestra el error del backend).

---

## 2. Decisiones

- **React Hook Form + `zodResolver`**: manejo de estado del form sin re-renders por keystroke; Zod valida en cliente con las mismas reglas que Pydantic en el backend.
- **`useFieldArray` para stack**: RHF nativo, sin estado extra. Cada fila es `{ name: string; years: number }`. Botones add/remove sin librería drag-and-drop.
- **Precarga desde `sample_profile.json` público**: el form se inicializa con los valores del sample si `localStorage` está vacío. El sample vive en `frontend/public/sample_profile.json` (ya existe como copia de `sample_profile.json` del repo). Si `getCurrentProfileId()` tiene un id, se precarga solo ese id para que el usuario actualice los datos.
- **`useMutation` para el submit**: TanStack Query maneja el estado pending/error/success. Al éxito: `setCurrentProfileId(data.profile_id)` + `navigate("/")`.
- **Sin toast de F6 todavía**: se muestra un alert inline "Scoring en curso (~30s)" debajo del botón. F6 lo convierte en toast. El redirect ocurre igual.
- **Zod schema en `lib/schemas.ts`**: reutilizable en tests. Replica las reglas del `ProfileForm` Pydantic (id min 1 max 64, years >= 0, stack min 1 item).

---

## 3. Archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `frontend/src/pages/ProfileForm.tsx` | Crear | Route `/profile`; form con RHF + Zod, `useMutation`, redirect |
| `frontend/src/lib/schemas.ts` | Crear | `profileFormSchema` Zod + tipo inferido `ProfileFormValues` |
| `frontend/src/components/StackInput.tsx` | Crear | Array dinámico de `{ name, years }` con `useFieldArray` |
| `frontend/public/sample_profile.json` | Crear | Copia del sample del repo para precarga del form |
| `frontend/src/App.tsx` | Modificar | Agrega route `/profile` → `ProfileForm` |

---

## 4. Implementación

### Zod schema (`lib/schemas.ts`)

```ts
const techItemSchema = z.object({
  name: z.string().min(1),
  years: z.number().int().min(0),
});

const profileFormSchema = z.object({
  id: z.string().min(1).max(64),
  stack: z.array(techItemSchema).min(1),
  seniority: z.enum(["junior", "mid", "senior", "lead", "staff"]),
  english_level: z.enum(["A1", "A2", "B1", "B2", "C1", "C2", "native"]),
  location: z.string().min(1),
  willing_to_relocate: z.boolean(),
  modality: z.enum(["remote", "hybrid", "onsite"]),
  salary_expectation: z.string().nullable(),
  summary: z.string().max(2000).nullable(),
});
```

### ProfileForm — flujo de submit

```
handleSubmit(onSubmit)
  → mutation.mutate(values)
    → createProfile(values) (POST /api/profile)
      success: setCurrentProfileId(data.profile_id) → navigate("/")
      error 409: mostrar "El id ya existe en la BD — cambiá el id"
      error 422: mostrar los detalles del campo inválido del backend
      error otro: error.message
```

### StackInput — interacción

- `useFieldArray({ control, name: "stack" })`
- Cada fila: `input[text]` para name + `input[number]` para years + botón `×` (remove)
- Botón "+ Agregar tecnología" al final (append `{ name: "", years: 0 }`)
- Error inline si name vacío o years negativo (Zod valida)

---

## 5. Criterios de aceptación

- [ ] `docker compose run --rm frontend npm run type-check` → 0 errores
- [ ] `/profile` con `localStorage` vacío → form precargado con valores de `sample_profile.json`
- [ ] Cada campo del stack es editable; botones add/remove funcionan
- [ ] Submit con datos válidos → `POST /api/profile` → 201 → `localStorage` tiene el `profile_id` → redirect a `/`
- [ ] Submit con `id` vacío → error inline "Requerido" sin llamar a la API
- [ ] `years` negativo → error inline
- [ ] Error 409 del backend → mensaje claro "El id ya existe"
- [ ] "← Volver" (sin submit) navega a `/`
- [ ] DevTools: solo 1 request `POST /api/profile` al submitir

---

## 6. Lo que NO se hace en esta fase

- Editar un perfil existente (GET + patch) → fuera de scope total del MVP
- Toast de feedback post-submit → F6 (se usa alert inline en F5)
- Validación de unicidad del id en tiempo real (debounce + GET) → fuera de scope
- Foto de perfil o campos adicionales → fuera de scope
- Header global con navegación → F6
