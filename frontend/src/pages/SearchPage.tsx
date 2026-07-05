import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useProfile } from "../lib/profile-context";
import { getJobsSchedule, scheduleSearchRun } from "../lib/api";
import { relativeTimeTo } from "../lib/format";
import { DEFAULT_FILTERS, type SearchFilters } from "../lib/searchFilters";
import { scoreColors } from "../lib/score";
import type { Seniority } from "../types/api";
import FilterChip from "../components/ui/FilterChip";
import ToggleSwitch from "../components/ui/ToggleSwitch";
import SegmentedControl from "../components/ui/SegmentedControl";
import { toast } from "sonner";
import { PlusIcon, XIcon } from "../components/ui/icons";

const SENIORITY_LEVELS: Seniority[] = ["junior", "mid", "senior", "lead", "staff"];

const SOURCES = [
  { key: "himalayas" as const, label: "Himalayas", dot: "var(--src-him-dot)" },
  { key: "remotive" as const, label: "Remotive", dot: "var(--src-rem-dot)" },
  { key: "jobicy" as const, label: "Jobicy", dot: "var(--src-jcy-dot)" },
  { key: "remoteok" as const, label: "RemoteOK", dot: "var(--src-rok-dot)" },
  { key: "arbeitnow" as const, label: "Arbeitnow", dot: "var(--src-abn-dot)" },
  { key: "adzuna" as const, label: "Adzuna", dot: "var(--src-azn-dot)" },
  { key: "jooble" as const, label: "Jooble", dot: "var(--src-jbl-dot)" },
];

const LABEL_CLS = "block text-sm font-medium text-fg-2 mb-2";

function loadProfileStack(): string[] {
  try {
    const raw = localStorage.getItem("jobmatch.profileStack");
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export default function SearchPage() {
  const navigate = useNavigate();
  const { profileId } = useProfile();
  const [draft, setDraft] = useState<SearchFilters>(DEFAULT_FILTERS);
  const [kwInput, setKwInput] = useState("");
  const profileStack = loadProfileStack();

  const { data: scheduleInfo } = useQuery({
    queryKey: ["jobs-schedule"],
    queryFn: getJobsSchedule,
    staleTime: 60_000,
  });
  const nextRun = relativeTimeTo(scheduleInfo?.next_run ?? null);

  const mutation = useMutation({
    mutationFn: () => scheduleSearchRun(draft),
    onSuccess: (data) => {
      toast.success(
        `Búsqueda programada — se ejecutará ${relativeTimeTo(data.run_at) ?? "en 12 h"}`,
      );
      navigate("/");
    },
    onError: () => {
      toast.error("Airflow no disponible — no se pudo registrar la programación");
    },
  });

  const addKeyword = () => {
    const value = kwInput.trim().toLowerCase();
    if (!value || draft.keywords.includes(value)) {
      setKwInput("");
      return;
    }
    setDraft({ ...draft, keywords: [...draft.keywords, value] });
    setKwInput("");
  };

  const seedFromProfile = () => {
    const merged = [...new Set([...draft.keywords, ...profileStack])];
    setDraft({ ...draft, keywords: merged });
  };

  const toggles = [
    {
      key: "remoteOnly" as const,
      label: "Solo remoto",
      hint: "Excluir presencial e híbrido",
    },
    {
      key: "latamOnly" as const,
      label: "Solo LATAM-friendly",
      hint: "Ofertas abiertas a Latinoamérica",
    },
    {
      key: "excludeEU" as const,
      label: "Excluir residencia UE",
      hint: "Descarta ofertas que exigen residir en la UE",
    },
  ];

  const minScoreColor = scoreColors(draft.minScore === 0 ? null : draft.minScore);

  return (
    <main className="max-w-[760px] mx-auto px-6 pt-6 pb-[120px] animate-fade-in">
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

      <h1 className="m-0 mb-1 text-2xl font-bold tracking-[-0.02em]">Programar búsqueda</h1>
      <p className="m-0 mb-7 text-sm text-sub">
        Se guarda como programación para tu perfil{" "}
        <span className="font-mono text-accent-text">{profileId}</span> y se ejecuta una única
        vez, 12 h después de programarla. No modifica los filtros de tu lista.
      </p>

      <div className="mb-6">
        <label htmlFor="search-kw" className={LABEL_CLS}>
          Palabras clave
        </label>
        {draft.keywords.length > 0 && (
          <div className="flex flex-wrap gap-[7px] mb-2.5">
            {draft.keywords.map((kw) => (
              <span
                key={kw}
                className="inline-flex items-center gap-1.5 pl-[11px] pr-2 py-[5px] bg-panel2 border border-line-2 rounded-lg font-mono text-[13px] text-accent-text"
              >
                {kw}
                <button
                  type="button"
                  onClick={() =>
                    setDraft({ ...draft, keywords: draft.keywords.filter((k) => k !== kw) })
                  }
                  className="flex text-muted hover:text-neg transition-colors"
                >
                  <XIcon size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <input
            id="search-kw"
            value={kwInput}
            onChange={(e) => setKwInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addKeyword();
              }
            }}
            placeholder="agregar palabra clave y Enter"
            className="flex-1 h-[38px] px-3 bg-panel border border-line-2 rounded-[9px] text-fg font-mono text-sm outline-none focus:border-accent"
          />
          <button
            type="button"
            onClick={addKeyword}
            className="w-[38px] h-[38px] flex-none flex items-center justify-center bg-panel2 border border-line-2 rounded-[9px] text-accent-text"
          >
            <PlusIcon size={16} />
          </button>
        </div>
        {profileStack.length > 0 && (
          <button
            type="button"
            onClick={seedFromProfile}
            className="inline-flex items-center gap-1.5 mt-2.5 text-accent-text text-[13px]"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" />
            </svg>
            Usar el stack de mi perfil
          </button>
        )}
      </div>

      <div className="mb-6">
        <label className={LABEL_CLS}>Fuentes</label>
        <div className="flex flex-wrap gap-2">
          {SOURCES.map((src) => (
            <FilterChip
              key={src.key}
              active={draft.sources[src.key]}
              dot={src.dot}
              onClick={() =>
                setDraft({
                  ...draft,
                  sources: { ...draft.sources, [src.key]: !draft.sources[src.key] },
                })
              }
            >
              {src.label}
            </FilterChip>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <label htmlFor="search-min-score" className="text-sm font-medium text-fg-2">
            Score LLM mínimo
          </label>
          <span
            className={`inline-flex items-center justify-center min-w-[44px] h-7 px-2 rounded-lg border font-mono font-bold text-[15px] ${minScoreColor.bg} ${minScoreColor.border} ${minScoreColor.fg}`}
          >
            {draft.minScore}
          </span>
        </div>
        <input
          id="search-min-score"
          type="range"
          min={0}
          max={100}
          step={5}
          value={draft.minScore}
          onChange={(e) => setDraft({ ...draft, minScore: Number(e.target.value) })}
          className="w-full cursor-pointer"
          style={{ accentColor: "var(--accent)" }}
        />
        <div className="flex justify-between text-xs text-muted mt-1">
          <span>0</span>
          <span>100</span>
        </div>
      </div>

      <div className="mb-6">
        <label className={LABEL_CLS}>Seniority objetivo</label>
        <div className="flex flex-wrap gap-2">
          {SENIORITY_LEVELS.map((level) => (
            <FilterChip
              key={level}
              active={!!draft.seniority[level]}
              onClick={() =>
                setDraft({
                  ...draft,
                  seniority: { ...draft.seniority, [level]: !draft.seniority[level] },
                })
              }
            >
              {level.charAt(0).toUpperCase() + level.slice(1)}
            </FilterChip>
          ))}
        </div>
      </div>

      <div className="flex flex-col mb-6 bg-panel border border-line rounded-xl px-4 py-1">
        {toggles.map((t) => (
          <div
            key={t.key}
            className="flex items-center justify-between py-3 border-t border-hair first:border-t-0"
          >
            <div>
              <div className="text-sm font-medium text-fg">{t.label}</div>
              <div className="text-[13px] text-muted">{t.hint}</div>
            </div>
            <ToggleSwitch
              checked={draft[t.key]}
              onChange={(checked) => setDraft({ ...draft, [t.key]: checked })}
            />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start mb-8">
        <div>
          <label htmlFor="search-salary-min" className={LABEL_CLS}>
            Rango salarial (USD/año)
          </label>
          <div className="flex items-center gap-2">
            <input
              id="search-salary-min"
              type="number"
              min={0}
              step={1000}
              value={draft.salaryMinUsd || ""}
              onChange={(e) =>
                setDraft({ ...draft, salaryMinUsd: Number(e.target.value) || 0 })
              }
              placeholder="mín 60000"
              className="w-full h-10 px-3 bg-panel border border-line-2 rounded-[9px] text-fg font-mono text-sm outline-none focus:border-accent"
            />
            <span className="text-muted text-sm">—</span>
            <input
              id="search-salary-max"
              type="number"
              min={0}
              step={1000}
              value={draft.salaryMaxUsd || ""}
              onChange={(e) =>
                setDraft({ ...draft, salaryMaxUsd: Number(e.target.value) || 0 })
              }
              placeholder="máx 120000"
              className="w-full h-10 px-3 bg-panel border border-line-2 rounded-[9px] text-fg font-mono text-sm outline-none focus:border-accent"
            />
          </div>
          <p className="mt-[7px] text-[13px] text-muted">
            Informativo — el rango publicado es texto libre y no siempre comparable.
          </p>
        </div>
        <div>
          <label className={LABEL_CLS}>Frecuencia</label>
          <SegmentedControl
            options={[{ value: "12h", label: "12 h" }]}
            value="12h"
            onChange={() => {}}
            disabled
          />
          <p className="mt-[7px] text-[13px] text-muted">
            Esta búsqueda se ejecuta una vez, 12 h después de programarla. El pipeline base del
            perfil corre además cada 12 h{nextRun ? ` (próxima ejecución ${nextRun})` : ""}.
          </p>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="h-[42px] px-6 bg-accent rounded-[10px] text-accent-ink font-semibold text-[15px] disabled:opacity-60"
        >
          {mutation.isPending ? "Programando…" : "Programar búsqueda"}
        </button>
        <button
          type="button"
          onClick={() => navigate("/")}
          className="h-[42px] px-5 bg-transparent border border-line-2 rounded-[10px] text-fg-2 font-medium text-[15px]"
        >
          Cancelar
        </button>
      </div>
    </main>
  );
}
