import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import FilterChip from "./ui/FilterChip";
import MultiSelect from "./ui/MultiSelect";
import ToggleSwitch from "./ui/ToggleSwitch";
import { getCountries, getTechnologies } from "../lib/api";
import { scoreColors } from "../lib/score";
import { DEFAULT_FILTERS, type SearchFilters } from "../lib/searchFilters";
import type { Seniority } from "../types/api";

const SOURCE_OPTIONS = [
  { key: "himalayas" as const, label: "Himalayas", dot: "var(--src-him-dot)" },
  { key: "remotive" as const, label: "Remotive", dot: "var(--src-rem-dot)" },
  { key: "jobicy" as const, label: "Jobicy", dot: "var(--src-jcy-dot)" },
  { key: "remoteok" as const, label: "RemoteOK", dot: "var(--src-rok-dot)" },
  { key: "arbeitnow" as const, label: "Arbeitnow", dot: "var(--src-abn-dot)" },
  { key: "adzuna" as const, label: "Adzuna", dot: "var(--src-azn-dot)" },
  { key: "jooble" as const, label: "Jooble", dot: "var(--src-jbl-dot)" },
];

const SENIORITY_OPTIONS: Seniority[] = ["junior", "mid", "senior", "lead", "staff"];

const ENGLISH_OPTIONS = ["A1", "A2", "B1", "B2", "C1", "C2", "native"];

interface FiltersSidebarProps {
  filters: SearchFilters;
  onChange: (filters: SearchFilters) => void;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="py-4 border-t border-hair first:border-t-0 first:pt-0">
      <div className="text-xs font-semibold uppercase tracking-[0.04em] text-sub mb-3">
        {title}
      </div>
      {children}
    </div>
  );
}

export default function FiltersSidebar({ filters, onChange }: FiltersSidebarProps) {
  const { data: techData, isLoading: techsLoading } = useQuery({
    queryKey: ["technologies"],
    queryFn: () => getTechnologies(100),
    staleTime: 5 * 60_000,
  });

  const { data: countryData, isLoading: countriesLoading } = useQuery({
    queryKey: ["countries"],
    queryFn: () => getCountries(200),
    staleTime: 5 * 60_000,
  });

  const toggleSeniority = (level: Seniority) => {
    onChange({
      ...filters,
      seniority: { ...filters.seniority, [level]: !filters.seniority[level] },
    });
  };

  const scoreColor = scoreColors(filters.minScore === 0 ? null : filters.minScore);

  const locationToggles = [
    {
      label: "Solo remoto",
      checked: filters.remoteOnly,
      onChange: (v: boolean) => onChange({ ...filters, remoteOnly: v }),
    },
    {
      label: "LATAM-friendly",
      checked: filters.latamOnly,
      onChange: (v: boolean) => onChange({ ...filters, latamOnly: v }),
    },
    {
      label: "Excluir residencia UE",
      checked: filters.excludeEU,
      onChange: (v: boolean) => onChange({ ...filters, excludeEU: v }),
    },
  ];

  return (
    <aside className="hidden lg:block sticky top-[76px] w-[260px] shrink-0 self-start p-5 bg-panel border border-line rounded-2xl">
      <div className="flex items-center justify-between mb-4">
        <h2 className="m-0 text-sm font-semibold text-fg">Filtros</h2>
        <button
          type="button"
          onClick={() => onChange(DEFAULT_FILTERS)}
          className="text-xs text-accent-text hover:underline"
        >
          Limpiar
        </button>
      </div>

      <Section title="Tecnología">
        <MultiSelect
          options={techData?.technologies ?? []}
          selected={filters.stack}
          onChange={(stack) => onChange({ ...filters, stack })}
          placeholder="Seleccionar tecnologías"
          searchPlaceholder="buscar tecnología"
          loading={techsLoading}
        />
      </Section>

      <Section title="País">
        <MultiSelect
          options={countryData?.countries ?? []}
          selected={filters.countries}
          onChange={(countries) => onChange({ ...filters, countries })}
          placeholder="Seleccionar países"
          searchPlaceholder="buscar país"
          loading={countriesLoading}
        />
      </Section>

      <Section title="Score LLM mínimo">
        <div className="flex items-center justify-between mb-2.5">
          <span
            className={`inline-flex items-center justify-center min-w-[40px] h-7 px-2 rounded-lg border font-mono font-bold text-sm ${scoreColor.bg} ${scoreColor.border} ${scoreColor.fg}`}
          >
            {filters.minScore}
          </span>
          <span className="text-xs text-muted">0–100</span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={filters.minScore}
          onChange={(e) => onChange({ ...filters, minScore: Number(e.target.value) })}
          className="w-full cursor-pointer"
          style={{ accentColor: "var(--accent)" }}
        />
      </Section>

      <Section title="Fuente">
        <div className="flex flex-wrap gap-1.5">
          {SOURCE_OPTIONS.map((src) => (
            <FilterChip
              key={src.key}
              active={filters.sources[src.key]}
              dot={src.dot}
              onClick={() =>
                onChange({
                  ...filters,
                  sources: { ...filters.sources, [src.key]: !filters.sources[src.key] },
                })
              }
            >
              {src.label}
            </FilterChip>
          ))}
        </div>
      </Section>

      <Section title="Seniority">
        <div className="flex flex-wrap gap-1.5">
          {SENIORITY_OPTIONS.map((level) => (
            <button
              key={level}
              type="button"
              onClick={() => toggleSeniority(level)}
              className={`px-2.5 py-1 rounded-[7px] border text-xs font-medium capitalize transition-colors ${
                filters.seniority[level]
                  ? "bg-accent-soft border-accent-line text-accent-text"
                  : "bg-panel2 border-line-2 text-sub"
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </Section>

      <Section title="Nivel de inglés">
        <select
          value={filters.englishMax}
          onChange={(e) => onChange({ ...filters, englishMax: e.target.value })}
          className="w-full h-9 px-3 bg-app border border-line-2 rounded-[9px] text-fg text-[13px] outline-none focus:border-accent cursor-pointer"
        >
          <option value="">Cualquiera</option>
          {ENGLISH_OPTIONS.map((level) => (
            <option key={level} value={level}>
              {level === "native" ? "Nativo" : `${level} o menor`}
            </option>
          ))}
        </select>
      </Section>

      <Section title="Ubicación">
        <div className="flex flex-col gap-3">
          {locationToggles.map((t) => (
            <label
              key={t.label}
              className="flex items-center justify-between gap-2 cursor-pointer"
            >
              <span className="text-[13px] text-fg-2">{t.label}</span>
              <ToggleSwitch checked={t.checked} onChange={t.onChange} />
            </label>
          ))}
        </div>
      </Section>

      <Section title="Salario">
        <label className="flex items-center justify-between gap-2 cursor-pointer">
          <span className="text-[13px] text-fg-2">Solo con salario publicado</span>
          <ToggleSwitch
            checked={filters.withSalary}
            onChange={(v) => onChange({ ...filters, withSalary: v })}
          />
        </label>
      </Section>
    </aside>
  );
}
