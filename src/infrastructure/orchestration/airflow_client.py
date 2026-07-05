from __future__ import annotations

import httpx

from src.infrastructure.config import settings

TRIGGER_TIMEOUT_SECONDS = 10.0


class AirflowClient:
    """Cliente mínimo de la REST API de Airflow para disparar DAG runs."""

    def __init__(
        self,
        base_url: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self._base_url = (base_url or settings.airflow_api_url).rstrip("/")
        self._auth = (
            user or settings.airflow_api_user,
            password or settings.airflow_api_password,
        )

    def trigger_dag(
        self,
        dag_id: str,
        conf: dict | None = None,
        logical_date: str | None = None,
    ) -> str:
        body: dict = {"conf": conf or {}}
        if logical_date is not None:
            body["logical_date"] = logical_date
        response = httpx.post(
            f"{self._base_url}/api/v1/dags/{dag_id}/dagRuns",
            json=body,
            auth=self._auth,
            timeout=TRIGGER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["dag_run_id"]

    def get_dag(self, dag_id: str) -> dict:
        response = httpx.get(
            f"{self._base_url}/api/v1/dags/{dag_id}",
            auth=self._auth,
            timeout=TRIGGER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def list_dag_runs(self, dag_id: str, limit: int = 4) -> list[dict]:
        response = httpx.get(
            f"{self._base_url}/api/v1/dags/{dag_id}/dagRuns",
            params={"limit": limit, "order_by": "-execution_date"},
            auth=self._auth,
            timeout=TRIGGER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["dag_runs"]

    def delete_dag_run(self, dag_id: str, dag_run_id: str) -> None:
        response = httpx.delete(
            f"{self._base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}",
            auth=self._auth,
            timeout=TRIGGER_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            return
        response.raise_for_status()

    def list_task_instances(self, dag_id: str, dag_run_id: str) -> list[dict]:
        response = httpx.get(
            f"{self._base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
            auth=self._auth,
            timeout=TRIGGER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["task_instances"]
