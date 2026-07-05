import { formatDateTime, relativeTime, relativeTimeTo } from "./format";
import { DEFAULT_FILTERS, selectedSeniorities, type SearchFilters } from "./searchFilters";
import type { PipelineRun, PipelineTask, SavedSearchResponse } from "../types/api";

export interface StateMeta {
  label: string;
  fg: string;
  bg: string;
  border: string;
}

export function stateMeta(state: string | null): StateMeta {
  switch (state) {
    case "success":
      return { label: "éxito", fg: "text-pos", bg: "bg-pos-soft", border: "border-pos-line" };
    case "failed":
    case "upstream_failed":
      return { label: "falló", fg: "text-neg", bg: "bg-neg-soft", border: "border-neg-line" };
    case "running":
      return {
        label: "corriendo",
        fg: "text-accent-text",
        bg: "bg-accent-soft",
        border: "border-accent-line",
      };
    case "queued":
      return { label: "en cola", fg: "text-sub", bg: "bg-panel2", border: "border-line-2" };
    default:
      return {
        label: "pendiente",
        fg: "text-muted",
        bg: "bg-panel2",
        border: "border-line-2",
      };
  }
}

export type StageState = "success" | "running" | "failed" | "pending";

export function stageState(task: PipelineTask): StageState {
  switch (task.state) {
    case "success":
      return "success";
    case "running":
      return "running";
    case "failed":
    case "upstream_failed":
      return "failed";
    default:
      return "pending";
  }
}

export type RunStatus = "queued" | "running" | "success" | "failed";

export function runStatus(run: PipelineRun): RunStatus {
  switch (run.state) {
    case "success":
      return "success";
    case "failed":
      return "failed";
    case "running":
      return "running";
    default:
      return "queued";
  }
}

export function shortId(dagRunId: string): string {
  const [kind, rest] = dagRunId.split("__");
  const tail = (rest ?? dagRunId).replace("+00:00", "").slice(-6);
  return `${kind || "run"} · …${tail}`;
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 90) return `${Math.round(seconds)}s`;
  return `${Math.round(seconds / 60)} min`;
}

export function runDuration(run: PipelineRun): string {
  if (!run.start_date || !run.end_date) return "—";
  return formatDuration(
    (new Date(run.end_date).getTime() - new Date(run.start_date).getTime()) / 1000,
  );
}

const ALL_SOURCE_KEYS = ["himalayas", "remotive", "jobicy", "remoteok", "arbeitnow", "adzuna", "jooble"] as const;

export function searchFiltersFrom(raw: Record<string, unknown>): SearchFilters {
  const parsed = raw as Partial<SearchFilters>;
  const rawSources = raw.sources;
  let sources = { ...DEFAULT_FILTERS.sources };

  if (Array.isArray(rawSources)) {
    sources = Object.fromEntries(
      ALL_SOURCE_KEYS.map((s) => [s, rawSources.includes(s)]),
    ) as typeof DEFAULT_FILTERS.sources;
  } else if (rawSources && typeof rawSources === "object") {
    sources = { ...DEFAULT_FILTERS.sources, ...(rawSources as typeof DEFAULT_FILTERS.sources) };
  }

  return { ...DEFAULT_FILTERS, ...parsed, sources };
}

export interface ProgItem {
  run?: PipelineRun;
  search?: SavedSearchResponse;
  status: RunStatus;
  key: string;
}

export const SYSTEM_PROFILE_ID = "system";

function progItemTime(item: ProgItem): number {
  const d =
    item.run?.start_date ??
    item.run?.logical_date ??
    item.search?.run_at ??
    item.search?.created_at ??
    null;
  return d ? new Date(d).getTime() : 0;
}

export function buildProgItems(
  runs: PipelineRun[],
  searches: SavedSearchResponse[],
  profileId: string | null,
): ProgItem[] {
  const showAll = profileId === SYSTEM_PROFILE_ID;
  const items: ProgItem[] = [];
  for (const run of runs) {
    const search = searches.find((s) => s.dag_run_id === run.dag_run_id);
    const isSharedCron = run.run_type === "scheduled";
    if (!showAll && !search && !isSharedCron) continue;
    items.push({ run, search, status: runStatus(run), key: run.dag_run_id });
  }
  for (const search of searches) {
    if (!runs.some((r) => r.dag_run_id === search.dag_run_id)) {
      items.push({ search, status: "queued", key: search.dag_run_id });
    }
  }
  items.sort((a, b) => progItemTime(b) - progItemTime(a));
  return items;
}

export function progItemMeta(item: ProgItem): string {
  const { run, search, status } = item;
  const scheduledFor = search?.run_at ?? run?.logical_date ?? null;
  if (status === "queued")
    return scheduledFor ? `inicia ${relativeTimeTo(scheduledFor) ?? "pronto"}` : "en cola";
  const start = run?.start_date ? formatDateTime(run.start_date) : "—";
  if (status === "running") return `${start} · en curso`;
  if (status === "failed") return `${start} · falló`;
  return `${start}${run?.end_date ? ` · ${runDuration(run)}` : ""}`;
}

export function summaryChips(f: SearchFilters): string[] {
  const sources = (["himalayas", "remotive", "jobicy", "remoteok", "arbeitnow", "adzuna", "jooble"] as const).filter((s) => f.sources[s]);
  const fuentes = sources.length === 7 ? "Todas" : sources.join(", ") || "—";
  const chips: string[] = [];
  if (f.minScore > 0) chips.push(`≥ ${f.minScore}`);
  const seniorities = selectedSeniorities(f);
  if (seniorities.length > 0) chips.push(seniorities.join(" · "));
  chips.push(`Fuentes: ${fuentes}`);
  if (f.remoteOnly) chips.push("remoto");
  if (f.latamOnly) chips.push("LATAM");
  if (f.excludeEU) chips.push("excluye UE");
  if (f.withSalary) chips.push("salario publicado");
  return chips;
}
