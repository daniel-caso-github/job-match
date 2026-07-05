import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { ApiError, login as loginApi } from "../lib/api";
import { useProfile } from "../lib/profile-context";
import type { Theme } from "../hooks/useTheme";
import Logo from "./ui/Logo";
import { MoonIcon, SunIcon } from "./ui/icons";

interface GateProps {
  theme: Theme;
  onToggleTheme: () => void;
}

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) {
    return "Usuario o contraseña incorrectos.";
  }
  return "No se pudo iniciar sesión — probá de nuevo.";
}

export default function Gate({ theme, onToggleTheme }: GateProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const { login } = useProfile();
  const navigate = useNavigate();
  const trimmedUsername = username.trim();

  const mutation = useMutation({
    mutationFn: ({ u, p }: { u: string; p: string }) => loginApi(u, p),
    onSuccess: (data) =>
      login({ profileId: data.profile_id, username: data.username, token: data.access_token }),
  });

  const canSubmit = trimmedUsername.length > 0 && password.length > 0 && !mutation.isPending;

  return (
    <div className="min-h-screen relative flex items-center justify-center p-6 animate-fade-in">
      <button
        type="button"
        onClick={onToggleTheme}
        title="Cambiar tema"
        className="absolute top-5 right-6 w-9 h-9 flex items-center justify-center bg-panel border border-line-2 rounded-[10px] text-sub"
      >
        {theme === "dark" ? <SunIcon size={17} /> : <MoonIcon size={17} />}
      </button>

      <div className="w-full max-w-[400px]">
        <div className="flex flex-col items-center mb-7">
          <div className="mb-4">
            <Logo size={52} radius={15} fontSize={24} />
          </div>
          <h1 className="m-0 text-[22px] font-bold tracking-[-0.02em]">JobMatch</h1>
          <p className="mt-2 text-sm text-sub text-center">
            Ofertas remotas rankeadas contra tu perfil.
          </p>
        </div>

        <form
          className="p-6 bg-panel border border-line rounded-2xl"
          onSubmit={(e) => {
            e.preventDefault();
            if (canSubmit) mutation.mutate({ u: trimmedUsername, p: password });
          }}
        >
          <label htmlFor="gate-username" className="block text-sm font-medium text-fg-2 mb-2">
            Username
          </label>
          <input
            id="gate-username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="tu-username"
            autoComplete="username"
            className="w-full h-[42px] px-3 bg-app border border-line-2 rounded-[9px] text-fg font-mono text-[15px] outline-none focus:border-accent"
          />

          <label
            htmlFor="gate-password"
            className="block text-sm font-medium text-fg-2 mt-4 mb-2"
          >
            Contraseña
          </label>
          <input
            id="gate-password"

            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••"
            autoComplete="current-password"
            className="w-full h-[42px] px-3 bg-app border border-line-2 rounded-[9px] text-fg text-[15px] outline-none focus:border-accent"
          />

          {mutation.isError && (
            <p className="mt-2 mb-0 text-[13px] text-neg">
              {loginErrorMessage(mutation.error)}
            </p>
          )}
          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full h-[42px] mt-3.5 bg-accent rounded-[10px] text-accent-ink font-semibold text-[15px] disabled:opacity-60"
          >
            {mutation.isPending ? "Entrando…" : "Entrar"}
          </button>

          <div className="flex items-center gap-3 my-[18px]">
            <div className="flex-1 h-px bg-line" />
            <span className="text-xs text-muted">¿PRIMERA VEZ?</span>
            <div className="flex-1 h-px bg-line" />
          </div>

          <button
            type="button"
            onClick={() => navigate("/register")}
            className="w-full h-[42px] bg-transparent border border-line-2 rounded-[10px] text-fg font-medium text-[15px] hover:border-accent transition-colors"
          >
            Crear usuario
          </button>
        </form>

      </div>
    </div>
  );
}
