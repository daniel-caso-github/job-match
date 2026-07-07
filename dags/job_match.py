from __future__ import annotations

import os
from datetime import datetime, timedelta

import requests
from airflow.decorators import dag, task

PIPELINE_API_URL = os.getenv("PIPELINE_API_URL", "http://api:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
TIMEOUT = 1800  # 30 min por tarea
_HEADERS = {"X-Internal-Api-Key": INTERNAL_API_KEY}

DEFAULT_ARGS = {
    "owner": "danielcaso",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}


@dag(
    dag_id="job_match",
    description="Recolección → extracción → embeddings → scoring (cada 12h).",
    schedule="0 */12 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["jobs", "ai"],
)
def job_match():

    @task
    def recolectar() -> int:
        r = requests.post(f"{PIPELINE_API_URL}/jobs/collect", headers=_HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["collected"]

    @task
    def extraer_requisitos(_collected: int) -> int:
        r = requests.post(f"{PIPELINE_API_URL}/jobs/extract", headers=_HEADERS, params={"limit": 200}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["extracted"]

    @task
    def embeddings(_extracted: int) -> int:
        r = requests.post(f"{PIPELINE_API_URL}/jobs/embed", headers=_HEADERS, params={"limit": 200}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["embedded"]

    @task
    def score_perfiles(_embedded: int) -> dict:
        r = requests.post(f"{PIPELINE_API_URL}/jobs/score", headers=_HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["scored"]

    @task
    def registrar_conteo(_scored) -> None:
        from airflow.operators.python import get_current_context
        run_id = get_current_context()["dag_run"].run_id
        r = requests.post(
            f"{PIPELINE_API_URL}/jobs/searches/{run_id}/match-count",
            headers=_HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()

    n_collected = recolectar()
    n_extracted = extraer_requisitos(n_collected)
    n_embedded = embeddings(n_extracted)
    scores = score_perfiles(n_embedded)
    registrar_conteo(scores)


dag = job_match()
