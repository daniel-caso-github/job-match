import type { MatchListItem, Seniority } from "../types/api";

export interface SearchFilters {
  keywords: string[];
  sources: { himalayas: boolean; remotive: boolean; jobicy: boolean; remoteok: boolean; arbeitnow: boolean; adzuna: boolean; jooble: boolean };
  minScore: number;
  stack: string[];
  seniority: Partial<Record<Seniority, boolean>>;
  englishMax: string;
  remoteOnly: boolean;
  latamOnly: boolean;
  excludeEU: boolean;
  withSalary: boolean;
  salaryMinUsd: number;
  salaryMaxUsd: number;
}

export const DEFAULT_FILTERS: SearchFilters = {
  keywords: [],
  sources: { himalayas: true, remotive: true, jobicy: true, remoteok: true, arbeitnow: true, adzuna: true, jooble: true },
  minScore: 0,
  stack: [],
  seniority: {},
  englishMax: "",
  remoteOnly: false,
  latamOnly: false,
  excludeEU: false,
  withSalary: false,
  salaryMinUsd: 0,
  salaryMaxUsd: 0,
};

const FILTERS_KEY = "jobmatch.searchFilters";

export function loadFilters(): SearchFilters {
  try {
    const raw = localStorage.getItem(FILTERS_KEY);
    if (!raw) return DEFAULT_FILTERS;
    const parsed = JSON.parse(raw) as Partial<SearchFilters>;
    return {
      ...DEFAULT_FILTERS,
      ...parsed,
      sources: { ...DEFAULT_FILTERS.sources, ...parsed.sources },
    };
  } catch {
    return DEFAULT_FILTERS;
  }
}

export function saveFilters(filters: SearchFilters): void {
  localStorage.setItem(FILTERS_KEY, JSON.stringify(filters));
}

export function selectedSeniorities(filters: SearchFilters): Seniority[] {
  return (Object.entries(filters.seniority) as [Seniority, boolean][])
    .filter(([, active]) => active)
    .map(([level]) => level);
}

export function isDefaultFilters(filters: SearchFilters): boolean {
  return (
    filters.keywords.length === 0 &&
    filters.sources.himalayas &&
    filters.sources.remotive &&
    filters.sources.jobicy &&
    filters.sources.remoteok &&
    filters.sources.arbeitnow &&
    filters.sources.adzuna &&
    filters.sources.jooble &&
    filters.minScore === 0 &&
    filters.stack.length === 0 &&
    selectedSeniorities(filters).length === 0 &&
    filters.englishMax === "" &&
    !filters.remoteOnly &&
    !filters.latamOnly &&
    !filters.excludeEU &&
    !filters.withSalary
  );
}

export function filtersToQueryParams(filters: SearchFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.minScore > 0) params.set("min_score", String(filters.minScore));

  const enabledSources = (["himalayas", "remotive", "jobicy", "remoteok", "arbeitnow", "adzuna", "jooble"] as const).filter(
    (s) => filters.sources[s],
  );
  if (enabledSources.length === 1) params.append("source", enabledSources[0]);
  if (enabledSources.length === 0) params.append("source", "__none__");

  filters.stack.forEach((tech) => params.append("stack", tech));
  selectedSeniorities(filters).forEach((level) => params.append("seniority", level));
  if (filters.englishMax) params.set("english_max", filters.englishMax);
  if (filters.remoteOnly) params.set("remote_only", "true");
  if (filters.latamOnly) params.set("latam_only", "true");
  if (filters.excludeEU) params.set("exclude_eu", "true");
  if (filters.withSalary) params.set("with_salary", "true");
  return params;
}

const ENGLISH_ORDER = ["a1", "a2", "b1", "b2", "c1", "c2", "native"] as const;

export function toMatchFilters(f: SearchFilters): Record<string, unknown> {
  const enabledSources = (["himalayas", "remotive", "jobicy", "remoteok", "arbeitnow", "adzuna", "jooble"] as const).filter((s) => f.sources[s]);
  const seniorities = selectedSeniorities(f);
  const englishMax = f.englishMax as (typeof ENGLISH_ORDER)[number] | "";
  const englishIdx = englishMax ? ENGLISH_ORDER.indexOf(englishMax) : -1;
  const englishLevels = englishIdx >= 0 ? ENGLISH_ORDER.slice(0, englishIdx + 1) : [];
  return {
    ...(f.minScore > 0 && { min_score: f.minScore }),
    ...(f.keywords.length > 0 && { keywords: f.keywords }),
    sources: enabledSources,
    stack: f.stack,
    seniorities,
    english_levels: englishLevels,
    remote_only: f.remoteOnly,
    latam_only: f.latamOnly,
    exclude_eu: f.excludeEU,
    with_salary: f.withSalary,
  };
}

export function matchesKeywords(match: MatchListItem, keywords: string[]): boolean {
  if (keywords.length === 0) return true;
  const haystack = [
    match.title,
    match.company,
    ...(match.verdict?.strengths ?? []),
    ...(match.verdict?.risks ?? []),
  ]
    .join(" ")
    .toLowerCase();
  return keywords.some((kw) => haystack.includes(kw.toLowerCase()));
}
