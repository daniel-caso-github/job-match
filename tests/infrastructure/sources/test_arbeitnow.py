from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.sources.arbeitnow import ArbeitnowSource

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def test_parses_fixture():
    payload = json.loads((FIXTURES / "arbeitnow_sample.json").read_text())

    src = ArbeitnowSource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch(max_pages=1))

    assert len(jobs) == 3
    assert all(j.source == "arbeitnow" for j in jobs)
    assert all(str(j.url).startswith("https://www.arbeitnow.com/") for j in jobs)
    assert len({j.id for j in jobs}) == 3

    j0 = jobs[0]
    assert j0.title == "Senior Python Engineer"
    assert j0.company == "Acme Corp"
    assert j0.remote is True
    assert j0.posted_at is not None
    assert "FastAPI" in j0.raw_text
    assert "<" not in j0.raw_text


def test_handles_missing_company_and_bad_timestamp():
    payload = json.loads((FIXTURES / "arbeitnow_sample.json").read_text())

    src = ArbeitnowSource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch(max_pages=1))

    assert jobs[1].company is None
    assert jobs[1].posted_at is None
    assert jobs[1].remote is False


def test_stops_pagination_when_no_next_link():
    payload = json.loads((FIXTURES / "arbeitnow_sample.json").read_text())

    src = ArbeitnowSource()
    with patch.object(src, "_get_json", return_value=payload) as mock_get:
        jobs = list(src.fetch(max_pages=3))

    # links.next is null in fixture → should stop after 1 page
    assert mock_get.call_count == 1
    assert len(jobs) == 3
