from __future__ import annotations

from prometheus_client import Counter, Histogram

pipeline_jobs_total = Counter(
    "pipeline_jobs_total",
    "Total jobs procesados por etapa del pipeline",
    ["stage"],
)

pipeline_stage_duration = Histogram(
    "pipeline_stage_duration_seconds",
    "Duración de cada etapa del pipeline",
    ["stage"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1200],
)

gemini_requests_total = Counter(
    "gemini_requests_total",
    "Total de llamadas a la API de Gemini",
    ["type", "status"],  # type: extract|score  status: success|retry|failed
)

gemini_request_duration = Histogram(
    "gemini_request_duration_seconds",
    "Duración de cada llamada a Gemini",
    ["type"],
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60],
)

llm_score_histogram = Histogram(
    "llm_score",
    "Distribución de scores LLM (0-100)",
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

semantic_score_histogram = Histogram(
    "semantic_score",
    "Distribución de scores semánticos (similitud coseno)",
    buckets=[0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0],
)
