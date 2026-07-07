import type {
  CountriesResponse,
  HealthResponse,
  JobsScheduleResponse,
  JobsScheduleRunResponse,
  LoginResponse,
  MatchDetail,
  MatchesListResponse,
  PipelineRunsResponse,
  ProfileCreatedResponse,
  ProfileForm,
  RegisterAccountRequest,
  SavedSearchesResponse,
  TechnologiesResponse,
} from "../types/api";
import { clearCurrentSession, getCurrentSession } from "./profileStorage";
import { filtersToQueryParams, toMatchFilters, type SearchFilters } from "./searchFilters";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(`API error ${status}`);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const session = getCurrentSession();
  const authHeader = session?.token ? { Authorization: `Bearer ${session.token}` } : {};

  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...authHeader, ...init?.headers },
    ...init,
  });
  const body = await res.json().catch(() => null);

  if (res.status === 401) {
    // Token expirado o inválido durante uso normal → logout y recarga.
    if (session) {
      clearCurrentSession();
      window.location.href = "/";
    }
    throw new ApiError(res.status, body);
  }

  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/health");
}

export function login(username: string, password: string): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function getProfile(profileId: string): Promise<ProfileForm> {
  return apiFetch<ProfileForm>(`/api/profile/${profileId}`);
}

export function registerAccount(
  payload: RegisterAccountRequest,
): Promise<ProfileCreatedResponse> {
  return apiFetch<ProfileCreatedResponse>("/api/profile", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProfile(
  profileId: string,
  form: ProfileForm,
): Promise<ProfileCreatedResponse> {
  return apiFetch<ProfileCreatedResponse>(`/api/profile/${profileId}`, {
    method: "PUT",
    body: JSON.stringify(form),
  });
}

export function getMatches(limit = 20, filters?: SearchFilters): Promise<MatchesListResponse> {
  const params = filters ? filtersToQueryParams(filters) : new URLSearchParams();
  params.set("limit", String(limit));
  return apiFetch<MatchesListResponse>(`/api/matches?${params}`);
}

export function getMatchDetail(jobId: string): Promise<MatchDetail> {
  return apiFetch<MatchDetail>(`/api/matches/${jobId}`);
}

export function getJobsSchedule(): Promise<JobsScheduleResponse> {
  return apiFetch<JobsScheduleResponse>("/api/jobs/schedule");
}

export function getPipelineRuns(limit = 4, includeTasks = true): Promise<PipelineRunsResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (!includeTasks) params.set("include_tasks", "false");
  return apiFetch<PipelineRunsResponse>(`/api/jobs/runs?${params}`);
}

export function scheduleSearchRun(filters: SearchFilters): Promise<JobsScheduleRunResponse> {
  return apiFetch<JobsScheduleRunResponse>("/api/jobs/schedule-run", {
    method: "POST",
    body: JSON.stringify({ filters: toMatchFilters(filters) }),
  });
}

export function getSavedSearches(limit = 20): Promise<SavedSearchesResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiFetch<SavedSearchesResponse>(`/api/jobs/searches?${params}`);
}

export function getTechnologies(limit = 30): Promise<TechnologiesResponse> {
  return apiFetch<TechnologiesResponse>(`/api/jobs/technologies?limit=${limit}`);
}

export function getCountries(limit = 100): Promise<CountriesResponse> {
  return apiFetch<CountriesResponse>(`/api/jobs/countries?limit=${limit}`);
}

export function cancelSearch(dagRunId: string): Promise<{ status: string; dag_run_id: string }> {
  return apiFetch(`/api/jobs/searches/${encodeURIComponent(dagRunId)}`, { method: "DELETE" });
}
