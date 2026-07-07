from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.saved_search import SavedSearch
from src.interfaces.api.dependencies import verify_internal_api_key
from src.interfaces.api.main import app
from tests.interfaces.api.conftest import FAKE_PROFILE_ID, ApiContext


def test_refresh_triggers_airflow_dag(client: TestClient, api: ApiContext):
    with patch("src.interfaces.api.routers.jobs._run_refresh") as mock_refresh:
        r = client.post("/jobs/refresh")

    assert r.status_code == 202
    assert r.json() == {
        "status": "scheduled",
        "runner": "airflow",
        "dag_run_id": api.airflow.dag_run_id,
    }
    assert api.airflow.triggered == ["job_match"]
    mock_refresh.assert_not_called()


def test_schedule_returns_next_run_from_airflow(client: TestClient, api: ApiContext):
    r = client.get("/jobs/schedule")

    assert r.status_code == 200
    assert r.json() == {
        "schedule": "0 */12 * * *",
        "next_run": "2026-07-05T12:00:00+00:00",
        "is_paused": False,
    }


def test_schedule_degrades_when_airflow_fails(client: TestClient, api: ApiContext):
    api.airflow.error = RuntimeError("airflow down")

    r = client.get("/jobs/schedule")

    assert r.status_code == 200
    assert r.json() == {"schedule": None, "next_run": None, "is_paused": None}


def test_schedule_run_triggers_dag_and_persists_search(
    client: TestClient, api: ApiContext
):
    r = client.post(
        "/jobs/schedule-run",
        json={"filters": {"stack": ["python"], "min_score": 75}},
    )

    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "scheduled"
    assert body["dag_run_id"] == api.airflow.dag_run_id
    assert api.airflow.triggered == ["job_match"]
    assert api.airflow.logical_dates == [body["run_at"]]
    run_at = datetime.fromisoformat(body["run_at"])
    delta = run_at - datetime.now(UTC)
    assert timedelta(hours=11, minutes=55) < delta <= timedelta(hours=12)

    saved = api.saved_searches.items
    assert len(saved) == 1
    assert saved[0].dag_run_id == body["dag_run_id"]
    assert saved[0].profile_id == FAKE_PROFILE_ID
    assert saved[0].filters == {"stack": ["python"], "min_score": 75}
    assert saved[0].run_at.isoformat() == body["run_at"]
    assert api.session.commits == 1


def test_schedule_run_respects_delay_hours(client: TestClient, api: ApiContext):
    r = client.post(
        "/jobs/schedule-run", params={"delay_hours": 24}, json={"filters": {}}
    )

    assert r.status_code == 202
    run_at = datetime.fromisoformat(r.json()["run_at"])
    delta = run_at - datetime.now(UTC)
    assert timedelta(hours=23, minutes=55) < delta <= timedelta(hours=24)


def test_schedule_run_returns_503_when_airflow_fails(
    client: TestClient, api: ApiContext
):
    api.airflow.error = RuntimeError("airflow down")

    r = client.post("/jobs/schedule-run", json={"filters": {}})

    assert r.status_code == 503
    assert api.saved_searches.items == []
    assert api.session.commits == 0


def test_searches_returns_saved_searches_for_profile(
    client: TestClient, api: ApiContext
):
    client.post("/jobs/schedule-run", json={"filters": {"min_score": 70}})

    r = client.get("/jobs/searches")

    assert r.status_code == 200
    searches = r.json()["searches"]
    assert len(searches) == 1
    assert searches[0]["profile_id"] == FAKE_PROFILE_ID
    assert searches[0]["filters"] == {"min_score": 70}
    assert searches[0]["dag_run_id"] == api.airflow.dag_run_id


def test_countries_returns_repo_list_in_order(client: TestClient, api: ApiContext):
    api.jobs.countries = ["United States", "Germany", "Canada"]

    r = client.get("/jobs/countries")

    assert r.status_code == 200
    assert r.json() == {"countries": ["United States", "Germany", "Canada"]}
    assert api.jobs.countries_calls == [100]


def test_countries_passes_limit(client: TestClient, api: ApiContext):
    api.jobs.countries = ["United States", "Germany", "Canada"]

    r = client.get("/jobs/countries", params={"limit": 2})

    assert r.status_code == 200
    assert r.json() == {"countries": ["United States", "Germany"]}
    assert api.jobs.countries_calls == [2]


def test_technologies_returns_repo_list_in_order(client: TestClient, api: ApiContext):
    api.jobs.technologies = ["python", "aws", "react"]

    r = client.get("/jobs/technologies")

    assert r.status_code == 200
    assert r.json() == {"technologies": ["python", "aws", "react"]}
    assert api.jobs.technologies_calls == [30]


def test_technologies_passes_limit(client: TestClient, api: ApiContext):
    api.jobs.technologies = ["python", "aws", "react"]

    r = client.get("/jobs/technologies", params={"limit": 2})

    assert r.status_code == 200
    assert r.json() == {"technologies": ["python", "aws"]}
    assert api.jobs.technologies_calls == [2]


def test_runs_returns_last_runs_with_tasks_sorted(client: TestClient, api: ApiContext):
    api.airflow.dag_runs = [
        {
            "dag_run_id": "manual__1",
            "state": "success",
            "run_type": "manual",
            "logical_date": "2026-07-04T18:12:24+00:00",
            "start_date": "2026-07-04T18:12:25+00:00",
            "end_date": "2026-07-04T18:12:33+00:00",
        }
    ]
    api.airflow.task_instances = {
        "manual__1": [
            {
                "task_id": "embeddings",
                "state": "success",
                "start_date": "2026-07-04T18:12:29+00:00",
                "end_date": "2026-07-04T18:12:30+00:00",
                "duration": 1.0,
            },
            {
                "task_id": "recolectar",
                "state": "success",
                "start_date": "2026-07-04T18:12:25+00:00",
                "end_date": "2026-07-04T18:12:27+00:00",
                "duration": 2.0,
            },
        ]
    }

    r = client.get("/jobs/runs")

    assert r.status_code == 200
    run = r.json()["runs"][0]
    assert run["dag_run_id"] == "manual__1"
    assert run["state"] == "success"
    assert run["logical_date"] == "2026-07-04T18:12:24+00:00"
    assert [t["task_id"] for t in run["tasks"]] == ["recolectar", "embeddings"]


def test_runs_skips_tasks_when_include_tasks_false(client: TestClient, api: ApiContext):
    api.airflow.dag_runs = [
        {"dag_run_id": "manual__1", "state": "running", "run_type": "manual"}
    ]
    api.airflow.task_instances = {"manual__1": [{"task_id": "recolectar"}]}

    r = client.get("/jobs/runs", params={"include_tasks": "false"})

    assert r.status_code == 200
    run = r.json()["runs"][0]
    assert run["state"] == "running"
    assert run["tasks"] == []


def test_runs_degrades_when_airflow_fails(client: TestClient, api: ApiContext):
    api.airflow.error = RuntimeError("airflow down")

    r = client.get("/jobs/runs")

    assert r.status_code == 200
    assert r.json() == {"runs": []}


def test_refresh_falls_back_to_inline_when_airflow_fails(
    client: TestClient, api: ApiContext
):
    api.airflow.error = RuntimeError("airflow down")

    with patch("src.interfaces.api.routers.jobs._run_refresh") as mock_refresh:
        r = client.post("/jobs/refresh")

    assert r.status_code == 202
    assert r.json() == {"status": "scheduled", "runner": "inline"}
    assert api.airflow.triggered == []
    mock_refresh.assert_called_once()


def test_record_match_count_persists_count_for_known_search(
    client: TestClient, api: ApiContext
):
    dag_run_id = api.airflow.dag_run_id
    api.saved_searches.items.append(
        SavedSearch(
            dag_run_id=dag_run_id,
            profile_id=FAKE_PROFILE_ID,
            filters={"min_score": 70},
            run_at=datetime.now(UTC),
        )
    )
    api.matches.upserts = [
        {"profile_id": FAKE_PROFILE_ID, "job_id": "j1", "semantic_score": 0.9, "llm_score": 80, "verdict": {}},
        {"profile_id": FAKE_PROFILE_ID, "job_id": "j2", "semantic_score": 0.8, "llm_score": 75, "verdict": {}},
    ]

    r = client.post(f"/jobs/searches/{dag_run_id}/match-count")

    assert r.status_code == 200
    body = r.json()
    assert body["updated"] == 1
    assert body["match_count"] == 2
    assert api.session.commits == 1
    saved = api.saved_searches.get_by_dag_run_id(dag_run_id)
    assert saved is not None
    assert saved.match_count == 2


def test_record_match_count_noop_for_unknown_dag_run(
    client: TestClient, api: ApiContext
):
    r = client.post("/jobs/searches/nonexistent__run/match-count")

    assert r.status_code == 200
    assert r.json() == {"updated": 0}
    assert api.session.commits == 0


def test_searches_response_includes_match_count(client: TestClient, api: ApiContext):
    dag_run_id = api.airflow.dag_run_id
    api.saved_searches.items.append(
        SavedSearch(
            dag_run_id=dag_run_id,
            profile_id=FAKE_PROFILE_ID,
            filters={},
            run_at=datetime.now(UTC),
            match_count=7,
        )
    )

    r = client.get("/jobs/searches")

    assert r.status_code == 200
    searches = r.json()["searches"]
    assert searches[0]["match_count"] == 7


def _make_search(dag_run_id: str, profile_id: str = FAKE_PROFILE_ID) -> SavedSearch:
    return SavedSearch(
        dag_run_id=dag_run_id,
        profile_id=profile_id,
        filters={},
        run_at=datetime.now(UTC),
    )


def test_cancel_search_removes_dag_run_and_saved_search(
    client: TestClient, api: ApiContext
):
    dag_run_id = api.airflow.dag_run_id
    api.saved_searches.items.append(_make_search(dag_run_id))

    r = client.delete(f"/jobs/searches/{dag_run_id}")

    assert r.status_code == 200
    assert r.json() == {"status": "cancelled", "dag_run_id": dag_run_id}
    assert api.saved_searches.get_by_dag_run_id(dag_run_id) is None
    assert api.session.commits == 1


def test_cancel_search_returns_404_for_unknown(client: TestClient, api: ApiContext):
    r = client.delete("/jobs/searches/nonexistent__run")

    assert r.status_code == 404
    assert api.session.commits == 0


def test_cancel_search_returns_403_for_wrong_profile(
    client: TestClient, api: ApiContext
):
    dag_run_id = api.airflow.dag_run_id
    api.saved_searches.items.append(_make_search(dag_run_id, profile_id="other_profile"))

    r = client.delete(f"/jobs/searches/{dag_run_id}")

    assert r.status_code == 403
    assert api.saved_searches.get_by_dag_run_id(dag_run_id) is not None
    assert api.session.commits == 0


def test_cancel_search_returns_503_when_airflow_fails_and_does_not_delete_search(
    client: TestClient, api: ApiContext
):
    dag_run_id = api.airflow.dag_run_id
    api.saved_searches.items.append(_make_search(dag_run_id))
    api.airflow.error = Exception("Airflow caído")

    r = client.delete(f"/jobs/searches/{dag_run_id}")

    assert r.status_code == 503
    assert api.saved_searches.get_by_dag_run_id(dag_run_id) is not None
    assert api.session.commits == 0


@pytest.mark.parametrize("endpoint", ["/jobs/collect", "/jobs/extract", "/jobs/embed", "/jobs/score"])
def test_ops_endpoints_require_internal_api_key(endpoint: str):
    app.dependency_overrides.pop(verify_internal_api_key, None)
    try:
        with TestClient(app) as c:
            r = c.post(endpoint)
        assert r.status_code == 401
    finally:
        app.dependency_overrides[verify_internal_api_key] = lambda: None


def test_ops_endpoint_rejects_wrong_key():
    app.dependency_overrides.pop(verify_internal_api_key, None)
    try:
        with TestClient(app) as c:
            r = c.post("/jobs/collect", headers={"X-Internal-Api-Key": "wrong-key"})
        assert r.status_code == 401
    finally:
        app.dependency_overrides[verify_internal_api_key] = lambda: None
