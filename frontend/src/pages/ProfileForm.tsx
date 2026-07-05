import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ApiError, getProfile, updateProfile } from "../lib/api";
import { profileFormSchema, type ProfileFormValues } from "../lib/schemas";
import { useProfile } from "../lib/profile-context";
import type { ProfileForm as ProfileFormPayload } from "../types/api";
import StackInput from "../components/StackInput";
import SegmentedControl from "../components/ui/SegmentedControl";
import ToggleSwitch from "../components/ui/ToggleSwitch";

const SENIORITY_OPTIONS = [
  { value: "junior" as const, label: "Junior" },
  { value: "mid" as const, label: "Mid" },
  { value: "senior" as const, label: "Senior" },
  { value: "lead" as const, label: "Lead" },
  { value: "staff" as const, label: "Staff" },
];

const MODALITY_OPTIONS = [
  { value: "remote" as const, label: "Remoto" },
  { value: "hybrid" as const, label: "Híbrido" },
  { value: "onsite" as const, label: "Presencial" },
];

const ENGLISH_OPTIONS = ["A1", "A2", "B1", "B2", "C1", "C2", "native"] as const;

const PROFILE_STACK_KEY = "jobmatch.profileStack";

const LOCATION_OPTIONS = ["US"];

function emptyDefaults(username: string): ProfileFormValues {
  return {
    username,
    first_name: "",
    last_name: "",
    email: "",
    stack: [{ name: "", years: 0 }],
    seniority: "junior",
    english_level: "B1",
    location: "US",
    willing_to_relocate: false,
    modality: "remote",
    salary_min_usd: 0,
    salary_max_usd: 0,
    summary: "",
  };
}

function toFormValues(data: ProfileFormPayload): ProfileFormValues {
  return {
    username: data.username,
    first_name: data.first_name ?? "",
    last_name: data.last_name ?? "",
    email: data.email ?? "",
    stack: data.stack.length > 0 ? data.stack : [{ name: "", years: 0 }],
    seniority: data.seniority,
    english_level: data.english_level,
    location: data.location,
    willing_to_relocate: data.willing_to_relocate,
    modality: data.modality,
    salary_min_usd: data.salary_min ?? 0,
    salary_max_usd: data.salary_max ?? 0,
    summary: data.summary ?? "",
  };
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      const detail = (error.body as { detail?: string } | null)?.detail ?? "";
      if (detail.includes("email")) return "Ese email ya está en uso — usá otro.";
      return "Conflicto al guardar — revisá los datos.";
    }
    if (error.status === 422) {
      const detail = (error.body as { detail?: unknown } | null)?.detail;
      return `Datos inválidos: ${JSON.stringify(detail)}`;
    }
    return `Error ${error.status}: ${error.message}`;
  }
  return error instanceof Error ? error.message : "Error desconocido";
}

const INPUT_CLS =
  "w-full h-10 px-3 bg-panel border border-line-2 rounded-[9px] text-fg text-sm outline-none focus:border-accent";
const LABEL_CLS = "block text-sm font-medium text-fg-2 mb-2";

export default function ProfileForm() {
  const navigate = useNavigate();
  const { profileId, session } = useProfile();

  const {
    register,
    control,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: emptyDefaults(session?.username ?? ""),
  });

  const { data: savedProfile } = useQuery({
    queryKey: ["profile", profileId],
    queryFn: () => getProfile(profileId!),
    enabled: profileId !== null,
    retry: false,
  });

  useEffect(() => {
    if (savedProfile) reset(toFormValues(savedProfile));
  }, [savedProfile, reset]);

  const queryClient = useQueryClient();

  const updateMutation = useMutation({
    mutationFn: (payload: ProfileFormPayload) => updateProfile(profileId!, payload),
    onSuccess: (_data, payload) => {
      queryClient.setQueryData(["profile", profileId], payload);
      queryClient.invalidateQueries({ queryKey: ["matches"] });
      localStorage.setItem(
        PROFILE_STACK_KEY,
        JSON.stringify(payload.stack.map((t) => t.name)),
      );
      toast.success("Perfil guardado — el scoring corre en background (~30 s)");
      navigate("/");
    },
  });

  const onSubmit = (values: ProfileFormValues) => {
    const { salary_min_usd, salary_max_usd, first_name, last_name, email, ...rest } = values;
    const payload: ProfileFormPayload = {
      ...rest,
      first_name: first_name?.trim() || null,
      last_name: last_name?.trim() || null,
      email: email?.trim().toLowerCase() || null,
      stack: values.stack.map((t) => ({ name: t.name.trim().toLowerCase(), years: t.years })),
      salary_min: salary_min_usd > 0 ? salary_min_usd : null,
      salary_max: salary_max_usd > 0 ? salary_max_usd : null,
      salary_currency: "USD",
      summary: values.summary.trim() || null,
    };
    updateMutation.mutate(payload);
  };

  const summaryLength = (watch("summary") ?? "").length;
  const locationOptions = [
    ...new Set([...LOCATION_OPTIONS, watch("location")].filter(Boolean)),
  ];

  return (
    <main className="max-w-[720px] mx-auto px-6 pt-6 pb-[120px] animate-fade-in">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 mb-[22px] text-sub text-sm hover:text-fg transition-colors"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="19" y1="12" x2="5" y2="12" />
          <polyline points="12 19 5 12 12 5" />
        </svg>
        Matches
      </Link>

      <h1 className="m-0 mb-1 text-2xl font-bold tracking-[-0.02em]">Administrá tu perfil</h1>
      <p className="m-0 mb-7 text-sm text-sub">
        Define contra qué se rankean las ofertas. El scoring corre en background tras guardar.
      </p>

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="mb-7 p-5 bg-panel border border-line rounded-2xl">
          <h2 className="m-0 mb-4 text-[13px] font-semibold tracking-[0.04em] uppercase text-muted">
            Cuenta
          </h2>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label htmlFor="profile-first-name" className={LABEL_CLS}>Nombre</label>
              <input
                id="profile-first-name"
                {...register("first_name")}
                placeholder="Nombre"
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label htmlFor="profile-last-name" className={LABEL_CLS}>Apellido</label>
              <input
                id="profile-last-name"
                {...register("last_name")}
                placeholder="Apellido"
                className={INPUT_CLS}
              />
            </div>
          </div>

          <div className="mb-4">
            <label htmlFor="profile-username" className={LABEL_CLS}>Username</label>
            <input
              id="profile-username"
              {...register("username")}
              disabled
              className={`${INPUT_CLS} font-mono opacity-60`}
            />
          </div>

          <div>
            <label htmlFor="profile-email" className={LABEL_CLS}>Email</label>
            <input
              id="profile-email"
              type="email"
              {...register("email")}
              placeholder="tu@email.com"
              className={INPUT_CLS}
            />
            {errors.email && (
              <p className="mt-[7px] text-[13px] text-neg">{errors.email.message}</p>
            )}
          </div>
        </div>

        <div className="mb-[22px]">
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="profile-summary" className="text-sm font-medium text-fg-2">
              Resumen profesional
            </label>
            <span
              className={`text-[13px] font-mono ${
                summaryLength > 1900 ? "text-score-amber" : "text-muted"
              }`}
            >
              {summaryLength}/2000
            </span>
          </div>
          <textarea
            id="profile-summary"
            rows={5}
            {...register("summary")}
            placeholder="Backend developer con foco en APIs..."
            className="w-full p-3 bg-panel border border-line-2 rounded-[9px] text-fg text-[15px] leading-relaxed resize-y outline-none focus:border-accent"
          />
          {errors.summary ? (
            <p className="mt-[7px] text-[13px] text-neg">{errors.summary.message}</p>
          ) : (
            <p className="mt-[7px] text-[13px] text-accent-text">
              ★ Es la pieza más importante del matching semántico — sé específico sobre
              tecnologías, dominios y logros.
            </p>
          )}
        </div>

        <div className="mb-[22px]">
          <label className={LABEL_CLS}>Stack &amp; experiencia</label>
          <StackInput control={control} register={register} errors={errors} />
        </div>

        <div className="mb-[22px]">
          <label className={LABEL_CLS}>Seniority</label>
          <Controller
            control={control}
            name="seniority"
            render={({ field }) => (
              <SegmentedControl
                options={SENIORITY_OPTIONS}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </div>

        <div className="mb-[22px]">
          <label className={LABEL_CLS}>Modalidad</label>
          <Controller
            control={control}
            name="modality"
            render={({ field }) => (
              <SegmentedControl
                options={MODALITY_OPTIONS}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-[22px]">
          <div>
            <label htmlFor="profile-english" className={LABEL_CLS}>
              Nivel de inglés
            </label>
            <select
              id="profile-english"
              {...register("english_level")}
              className={`${INPUT_CLS} cursor-pointer`}
            >
              {ENGLISH_OPTIONS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="profile-location" className={LABEL_CLS}>
              Ubicación
            </label>
            <select
              id="profile-location"
              {...register("location")}
              className={`${INPUT_CLS} cursor-pointer`}
            >
              {locationOptions.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
            {errors.location && (
              <p className="mt-[7px] text-[13px] text-neg">{errors.location.message}</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-[1fr_auto] gap-4 items-end mb-8">
          <div>
            <label htmlFor="profile-salary-min" className={LABEL_CLS}>
              Expectativa salarial (USD/año)
            </label>
            <div className="flex items-center gap-2">
              <input
                id="profile-salary-min"
                type="number"
                min={0}
                step={1000}
                {...register("salary_min_usd", {
                  setValueAs: (v) => (v === "" || v === null ? 0 : Number(v)),
                })}
                placeholder="mín 60000"
                className={`${INPUT_CLS} font-mono`}
              />
              <span className="text-muted text-sm">—</span>
              <input
                id="profile-salary-max"
                type="number"
                min={0}
                step={1000}
                {...register("salary_max_usd", {
                  setValueAs: (v) => (v === "" || v === null ? 0 : Number(v)),
                })}
                placeholder="máx 120000"
                className={`${INPUT_CLS} font-mono`}
              />
            </div>
          </div>
          <div>
            <label className={LABEL_CLS}>¿Dispuesto a relocar?</label>
            <Controller
              control={control}
              name="willing_to_relocate"
              render={({ field }) => (
                <div className="flex items-center gap-2.5 h-10 px-3.5 bg-panel border border-line-2 rounded-[9px] text-sm text-fg">
                  <ToggleSwitch checked={field.value} onChange={field.onChange} />
                  {field.value ? "Sí" : "No"}
                </div>
              )}
            />
          </div>
        </div>

        {updateMutation.isError && (
          <div className="mb-5 px-4 py-3 bg-neg-soft border border-neg-line rounded-[10px] text-sm text-neg">
            {errorMessage(updateMutation.error)}
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="h-[42px] px-6 bg-accent rounded-[10px] text-accent-ink font-semibold text-[15px] disabled:opacity-60"
          >
            {updateMutation.isPending ? "Guardando…" : "Guardar perfil"}
          </button>
          <button
            type="button"
            onClick={() => navigate("/")}
            className="h-[42px] px-5 bg-transparent border border-line-2 rounded-[10px] text-fg-2 font-medium text-[15px]"
          >
            Cancelar
          </button>
        </div>
      </form>
    </main>
  );
}
