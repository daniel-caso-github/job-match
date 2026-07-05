import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ApiError, registerAccount, login as loginApi } from "../lib/api";
import { registerSchema, type RegisterValues } from "../lib/schemas";
import { useProfile } from "../lib/profile-context";
import Logo from "../components/ui/Logo";

const INPUT_CLS =
  "w-full h-[42px] px-3 bg-app border border-line-2 rounded-[9px] text-fg text-[15px] outline-none focus:border-accent";
const LABEL_CLS = "block text-sm font-medium text-fg-2 mb-2";

function registerErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      const detail = (error.body as { detail?: string } | null)?.detail ?? "";
      if (detail.includes("email")) return "Ese email ya está registrado.";
      if (detail.includes("username")) return "Ese username ya existe — elegí otro.";
    }
    if (error.status === 422) return "Revisá los datos del formulario.";
    return `Error ${error.status}: ${error.message}`;
  }
  return "No se pudo crear la cuenta — probá de nuevo.";
}

export default function Register() {
  const navigate = useNavigate();
  const { login } = useProfile();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { first_name: "", last_name: "", username: "", email: "", password: "", confirmPassword: "" },
  });

  const mutation = useMutation({
    mutationFn: async (values: RegisterValues) => {
      await registerAccount({
        username: values.username.trim().toLowerCase(),
        email: values.email.trim().toLowerCase(),
        first_name: values.first_name?.trim() || null,
        last_name: values.last_name?.trim() || null,
        password: values.password,
      });
      return loginApi(values.username.trim().toLowerCase(), values.password);
    },
    onSuccess: (data) => {
      login({ profileId: data.profile_id, username: data.username, token: data.access_token });
      navigate("/");
    },
  });

  return (
    <div className="min-h-screen flex items-center justify-center p-6 animate-fade-in">
      <div className="w-full max-w-[440px]">
        <div className="flex flex-col items-center mb-7">
          <div className="mb-4">
            <Logo size={52} radius={15} fontSize={24} />
          </div>
          <h1 className="m-0 text-[22px] font-bold tracking-[-0.02em]">Crear cuenta</h1>
          <p className="mt-2 text-sm text-sub text-center">
            Completá tus datos para empezar a rankear ofertas.
          </p>
        </div>

        <form
          className="p-6 bg-panel border border-line rounded-2xl"
          onSubmit={handleSubmit((v) => mutation.mutate(v))}
        >
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label htmlFor="reg-first-name" className={LABEL_CLS}>
                Nombre
              </label>
              <input
                id="reg-first-name"
                {...register("first_name")}
                placeholder="Nombre"
                autoComplete="given-name"
                className={INPUT_CLS}
              />
              {errors.first_name && (
                <p className="mt-1 text-[12px] text-neg">{errors.first_name.message}</p>
              )}
            </div>
            <div>
              <label htmlFor="reg-last-name" className={LABEL_CLS}>
                Apellido
              </label>
              <input
                id="reg-last-name"
                {...register("last_name")}
                placeholder="Apellido"
                autoComplete="family-name"
                className={INPUT_CLS}
              />
              {errors.last_name && (
                <p className="mt-1 text-[12px] text-neg">{errors.last_name.message}</p>
              )}
            </div>
          </div>

          <div className="mb-4">
            <label htmlFor="reg-username" className={LABEL_CLS}>
              Username
            </label>
            <input
              id="reg-username"
              {...register("username")}
              placeholder="tu-usuario"
              autoComplete="username"
              className={`${INPUT_CLS} font-mono`}
            />
            {errors.username ? (
              <p className="mt-1 text-[12px] text-neg">{errors.username.message}</p>
            ) : (
              <p className="mt-1 text-[12px] text-muted">Minúsculas, números y . _ -</p>
            )}
          </div>

          <div className="mb-4">
            <label htmlFor="reg-email" className={LABEL_CLS}>
              Email
            </label>
            <input
              id="reg-email"
              type="email"
              {...register("email")}
              placeholder="tu@email.com"
              autoComplete="email"
              className={INPUT_CLS}
            />
            {errors.email && (
              <p className="mt-1 text-[12px] text-neg">{errors.email.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4 mb-5">
            <div>
              <label htmlFor="reg-password" className={LABEL_CLS}>
                Contraseña
              </label>
              <input
                id="reg-password"
                type="password"
                {...register("password")}
                placeholder="mínimo 6 caracteres"
                autoComplete="new-password"
                className={INPUT_CLS}
              />
              {errors.password && (
                <p className="mt-1 text-[12px] text-neg">{errors.password.message}</p>
              )}
            </div>
            <div>
              <label htmlFor="reg-confirm-password" className={LABEL_CLS}>
                Repetir contraseña
              </label>
              <input
                id="reg-confirm-password"
                type="password"
                {...register("confirmPassword")}
                placeholder="••••••"
                autoComplete="new-password"
                className={INPUT_CLS}
              />
              {errors.confirmPassword && (
                <p className="mt-1 text-[12px] text-neg">{errors.confirmPassword.message}</p>
              )}
            </div>
          </div>

          {mutation.isError && (
            <p className="mb-3 text-[13px] text-neg">{registerErrorMessage(mutation.error)}</p>
          )}

          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full h-[42px] bg-accent rounded-[10px] text-accent-ink font-semibold text-[15px] disabled:opacity-60"
          >
            {mutation.isPending ? "Creando cuenta…" : "Crear cuenta"}
          </button>

          <div className="flex items-center gap-3 my-[18px]">
            <div className="flex-1 h-px bg-line" />
            <span className="text-xs text-muted">¿YA TENÉS CUENTA?</span>
            <div className="flex-1 h-px bg-line" />
          </div>

          <button
            type="button"
            onClick={() => navigate("/")}
            className="w-full h-[42px] bg-transparent border border-line-2 rounded-[10px] text-fg font-medium text-[15px] hover:border-accent transition-colors"
          >
            Iniciar sesión
          </button>
        </form>
      </div>
    </div>
  );
}
