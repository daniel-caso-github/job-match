export type Seniority = "junior" | "mid" | "senior" | "lead" | "staff";
export type EnglishLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2" | "native";
export type Modality = "remote" | "hybrid" | "onsite";

export interface TechItem {
  name: string;
  years: number;
}

export interface ProfileForm {
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
  stack: TechItem[];
  seniority: Seniority;
  english_level: EnglishLevel;
  location: string;
  willing_to_relocate: boolean;
  modality: Modality;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  summary: string | null;
}

export interface RegisterAccountRequest {
  username: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  password: string;
}

export interface Verdict {
  score: number;
  strengths: string[];
  risks: string[];
}

export interface JobRequirements {
  stack: string[];
  seniority: Seniority | null;
  english_level: EnglishLevel | null;
  requires_eu_residency: boolean;
  remote: boolean | null;
  latam_friendly: boolean | null;
  salary_range: string | null;
  confidence: number;
}

export interface MatchListItem {
  job_id: string;
  title: string;
  company: string;
  url: string;
  source: string;
  country: string | null;
  llm_score: number | null;
  semantic_score: number | null;
  verdict: Verdict | null;
}

export interface MatchDetail extends MatchListItem {
  requirements: JobRequirements | null;
  raw_text: string | null;
  scored_at: string | null;
  source_attribution: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  db: boolean;
  gemini_key_present: boolean;
  model: string;
}

export interface MatchesListResponse {
  profile_id: string;
  count: number;
  matches: MatchListItem[];
  source_attribution: string;
}

export interface ProfileCreatedResponse {
  profile_id: string;
  username: string;
  matching: "scheduled";
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  profile_id: string;
  username: string;
}

export interface JobsScheduleResponse {
  schedule: string | null;
  next_run: string | null;
  is_paused: boolean | null;
}

export interface JobsScheduleRunResponse {
  status: "scheduled";
  dag_run_id: string;
  run_at: string;
}

export interface PipelineTask {
  task_id: string;
  state: string | null;
  start_date: string | null;
  end_date: string | null;
  duration: number | null;
}

export interface PipelineRun {
  dag_run_id: string;
  state: string | null;
  run_type: string | null;
  logical_date: string | null;
  start_date: string | null;
  end_date: string | null;
  tasks: PipelineTask[];
}

export interface PipelineRunsResponse {
  runs: PipelineRun[];
}

export interface TechnologiesResponse {
  technologies: string[];
}

export interface CountriesResponse {
  countries: string[];
}

export interface SavedSearchResponse {
  dag_run_id: string;
  profile_id: string;
  filters: Record<string, unknown>;
  run_at: string;
  created_at: string | null;
  match_count: number | null;
}

export interface SavedSearchesResponse {
  searches: SavedSearchResponse[];
}
