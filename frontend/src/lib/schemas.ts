import { z } from "zod";

export const techItemSchema = z.object({
  name: z.string().min(1, "Requerido").max(40),
  years: z
    .number({ invalid_type_error: "Número inválido" })
    .min(0, "Debe ser ≥ 0")
    .max(40, "Máximo 40"),
});

export const profileFormSchema = z.object({
  username: z
    .string()
    .min(1, "Requerido")
    .max(64, "Máximo 64 caracteres")
    .regex(
      /^[a-z0-9][a-z0-9._-]*$/,
      "Minúsculas, números y . _ - (empieza con letra o número)",
    ),
  first_name: z.string().max(80).optional(),
  last_name: z.string().max(80).optional(),
  email: z.string().email("Email inválido").max(254).optional(),
  stack: z.array(techItemSchema).min(1, "Agregá al menos una tecnología"),
  seniority: z.enum(["junior", "mid", "senior", "lead", "staff"]),
  english_level: z.enum(["A1", "A2", "B1", "B2", "C1", "C2", "native"]),
  location: z.string().min(1, "Requerido"),
  willing_to_relocate: z.boolean(),
  modality: z.enum(["remote", "hybrid", "onsite"]),
  salary_min_usd: z.number({ invalid_type_error: "Número inválido" }).min(0, "Debe ser ≥ 0"),
  salary_max_usd: z.number({ invalid_type_error: "Número inválido" }).min(0, "Debe ser ≥ 0"),
  summary: z.string().max(2000, "Máximo 2000 caracteres"),
});

export type ProfileFormValues = z.infer<typeof profileFormSchema>;

export const registerSchema = z
  .object({
    first_name: z.string().max(80).optional(),
    last_name: z.string().max(80).optional(),
    username: z
      .string()
      .min(1, "Requerido")
      .max(64)
      .regex(
        /^[a-z0-9][a-z0-9._-]*$/,
        "Minúsculas, números y . _ - (empieza con letra o número)",
      ),
    email: z.string().min(1, "Requerido").email("Email inválido").max(254),
    password: z.string().min(6, "Mínimo 6 caracteres"),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

export type RegisterValues = z.infer<typeof registerSchema>;
