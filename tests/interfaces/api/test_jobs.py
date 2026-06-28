from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.interfaces.api.conftest import ApiContext


def test_refresh_returns_202_and_schedules_background(
    client: TestClient, api: ApiContext
):
    with patch("src.interfaces.api.routers.jobs._run_refresh") as mock_refresh:
        r = client.post("/jobs/refresh")

    assert r.status_code == 202
    assert r.json() == {"status": "scheduled"}
    mock_refresh.assert_called_once()
