from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.interfaces.api.conftest import ApiContext


def _valid_body(**overrides) -> dict:
    body = {
        "id": "daniel-test",
        "stack": [{"name": "Python", "years": 8}],
        "seniority": "senior",
        "english_level": "B2",
        "location": "AR",
        "modality": "remote",
        "summary": "Backend engineer focused on APIs.",
    }
    body.update(overrides)
    return body


def test_post_profile_accepts_valid_body_and_schedules_scoring(
    client: TestClient, api: ApiContext
):
    with patch(
        "src.interfaces.api.routers.profile._run_scoring"
    ) as mock_scoring:
        r = client.post("/profile", json=_valid_body())

    assert r.status_code == 201
    body = r.json()
    assert body == {"profile_id": "daniel-test", "matching": "scheduled"}
    # FastAPI runs background tasks after the response is built; with TestClient
    # they execute synchronously by the time we get here.
    mock_scoring.assert_called_once()
    assert mock_scoring.call_args.args[0].id == "daniel-test"


def test_post_profile_rejects_invalid_seniority(client: TestClient, api: ApiContext):
    r = client.post("/profile", json=_valid_body(seniority="expert"))
    assert r.status_code == 422


def test_post_profile_rejects_invalid_english_level(
    client: TestClient, api: ApiContext
):
    r = client.post("/profile", json=_valid_body(english_level="Z9"))
    assert r.status_code == 422


def test_post_profile_rejects_invalid_modality(client: TestClient, api: ApiContext):
    r = client.post("/profile", json=_valid_body(modality="contract"))
    assert r.status_code == 422


def test_post_profile_rejects_missing_required_field(
    client: TestClient, api: ApiContext
):
    body = _valid_body()
    body.pop("seniority")
    r = client.post("/profile", json=body)
    assert r.status_code == 422
