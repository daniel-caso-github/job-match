import { Link, NavLink, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getHealth } from "../lib/api";
import { useProfile } from "../lib/profile-context";
import type { Theme } from "../hooks/useTheme";
import Logo from "./ui/Logo";
import { LogoutIcon, MoonIcon, SunIcon } from "./ui/icons";

interface HeaderProps {
  theme: Theme;
  onToggleTheme: () => void;
}

const NAV_BASE =
  "inline-flex items-center h-8 px-2 sm:px-3 rounded-lg text-sm font-medium transition-colors";

function navClass(active: boolean): string {
  return `${NAV_BASE} ${active ? "text-fg bg-panel2" : "text-sub"}`;
}

function HealthPill() {
  const { data, isError } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const status = isError ? "down" : data?.status;
  const dot =
    status === "ok"
      ? "var(--sc-green-fg)"
      : status === "degraded"
        ? "var(--sc-amber-fg)"
        : "var(--muted)";
  const label =
    status === "ok" ? "Sistema OK" : status === "degraded" ? "Degradado" : "Sin conexión";
  const tip = data
    ? `status: ${data.status} · db: ${data.db ? "✓" : "✗"} · gemini: ${
        data.gemini_key_present ? "✓" : "✗"
      } · ${data.model}`
    : "sin datos del backend";

  return (
    <div
      title={tip}
      className="flex items-center gap-[7px] px-2.5 h-8 border border-line-2 rounded-lg cursor-default"
    >
      <span
        className="w-[7px] h-[7px] rounded-full"
        style={{ background: dot, boxShadow: `0 0 8px ${dot}` }}
      />
      <span className="text-[13px] text-sub hidden sm:inline">{label}</span>
    </div>
  );
}

export default function Header({ theme, onToggleTheme }: HeaderProps) {
  const { session, logout } = useProfile();
  const { pathname } = useLocation();
  const matchesActive = pathname === "/" || pathname.startsWith("/matches");

  return (
    <header className="sticky top-0 z-30 flex items-center gap-1 sm:gap-2 h-[60px] px-3 sm:px-6 bg-head backdrop-blur-md border-b border-head-line">
      <Link to="/" className="flex items-center gap-2.5 mr-1 sm:mr-3 select-none">
        <Logo />
        <span className="font-semibold text-[15px] tracking-[-0.01em] text-fg hidden sm:inline">
          JobMatch
        </span>
      </Link>

      <nav className="flex items-center gap-0.5">
        <Link to="/" className={navClass(matchesActive)}>
          Matches
        </Link>
        <NavLink to="/search" className={({ isActive }) => navClass(isActive)}>
          Buscar
        </NavLink>
        <NavLink to="/programaciones" className={({ isActive }) => navClass(isActive)}>
          Programaciones
        </NavLink>
      </nav>

      <div className="flex-1" />

      <button
        type="button"
        onClick={onToggleTheme}
        title="Cambiar tema"
        className="w-8 h-8 flex items-center justify-center bg-transparent border border-line-2 rounded-lg text-sub"
      >
        {theme === "dark" ? <SunIcon /> : <MoonIcon />}
      </button>

      <HealthPill />

      <Link
        to="/profile"
        title="Editar perfil"
        className="flex items-center gap-2 h-8 pl-2 pr-2.5 bg-panel border border-line-2 rounded-lg"
      >
        <span className="w-5 h-5 rounded-full bg-panel2 flex items-center justify-center text-[11px] font-semibold text-accent-text">
          {(session?.username ?? "?").charAt(0).toUpperCase()}
        </span>
        <span className="font-mono text-[13px] text-fg hidden sm:inline">{session?.username}</span>
      </Link>

      <button
        type="button"
        onClick={logout}
        title="Cerrar sesión"
        className="w-8 h-8 flex items-center justify-center bg-transparent border border-line-2 rounded-lg text-sub hover:text-score-red transition-colors"
      >
        <LogoutIcon />
      </button>

    </header>
  );
}
