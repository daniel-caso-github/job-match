from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.infrastructure.sources.himalayas import HimalayasSource

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def test_parses_fixture():
    payload = json.loads((FIXTURES / "himalayas_sample.json").read_text())

    src = HimalayasSource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch(limit=100, max_pages=1))

    assert len(jobs) == 3

    j0 = jobs[0]
    assert j0.source == "himalayas"
    assert j0.title == "Senior Backend Engineer (Python)"
    assert j0.company == "Acme"
    assert j0.country == "AR"
    assert j0.remote is True
    assert j0.posted_at is not None

    # third entry has a malformed publishedAt → posted_at must be None, not raise
    assert jobs[2].posted_at is None
    assert jobs[2].country == "DE"


def test_strips_html_from_description():
    payload = json.loads((FIXTURES / "himalayas_sample.json").read_text())
    src = HimalayasSource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch(limit=100, max_pages=1))

    for j in jobs:
        assert "<" not in j.raw_text, f"raw HTML leaked into raw_text: {j.raw_text!r}"
        assert ">" not in j.raw_text
    assert "FastAPI" in jobs[0].raw_text
    assert "EU residency required" in jobs[2].raw_text


def test_get_json_retries_on_5xx():
    import httpx

    src = HimalayasSource()
    err_resp = MagicMock()
    err_resp.status_code = 503
    err_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=err_resp
    )
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.raise_for_status.return_value = None
    ok_resp.json.return_value = {"jobs": []}

    with patch.object(src._client, "get", side_effect=[err_resp, err_resp, ok_resp]):
        src._get_json.retry.wait = lambda *_a, **_kw: 0  # type: ignore[attr-defined]
        result = src._get_json({"limit": 1})
    assert result == {"jobs": []}
