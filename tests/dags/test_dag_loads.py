from __future__ import annotations

import pytest

airflow = pytest.importorskip("airflow")


def test_dag_loads_without_errors():
    from airflow.models import DagBag

    bag = DagBag(dag_folder="dags/", include_examples=False)
    assert bag.import_errors == {}, f"DAG import errors: {bag.import_errors}"
    assert "job_match" in bag.dags


def test_dag_has_four_tasks():
    from airflow.models import DagBag

    bag = DagBag(dag_folder="dags/", include_examples=False)
    assert len(bag.dags["job_match"].tasks) == 4


def test_dag_task_ids():
    from airflow.models import DagBag

    bag = DagBag(dag_folder="dags/", include_examples=False)
    task_ids = {t.task_id for t in bag.dags["job_match"].tasks}
    assert task_ids == {"recolectar", "extraer_requisitos", "embeddings", "score_perfiles"}
