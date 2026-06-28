from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task

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
        from src.interfaces.pipeline import run_collect
        return run_collect()

    @task
    def extraer_requisitos(_collected: int) -> int:
        from src.interfaces.pipeline import run_extract
        return run_extract(limit=200)

    @task
    def embeddings(_extracted: int) -> int:
        from src.interfaces.pipeline import run_embed
        return run_embed(limit=200)

    @task
    def score_perfiles(_embedded: int) -> dict:
        from src.interfaces.pipeline import run_score_all_profiles
        return run_score_all_profiles()

    n_collected = recolectar()
    n_extracted = extraer_requisitos(n_collected)
    n_embedded = embeddings(n_extracted)
    score_perfiles(n_embedded)


dag = job_match()
