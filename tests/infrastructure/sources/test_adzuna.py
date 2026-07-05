from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.sources.adzuna import AdzunaSource

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def test_no_key_returns_empty_without_raising():
    src = AdzunaSource()
    src._app_id = None
    src._app_key = None

    jobs = list(src.fetch())

    assert jobs == []


def test_parses_fixture():
    payload = json.loads((FIXTURES / "adzuna_sample.json").read_text())

    src = AdzunaSource()
    src._app_id = "test_id"
    src._app_key = "test_key"
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch(max_pages=1))

    assert len(jobs) == 3
    assert all(j.source == "adzuna" for j in jobs)
    assert all(str(j.url).startswith("https://www.adzuna.com/") for j in jobs)
    assert len({j.id for j in jobs}) == 3

    j0 = jobs[0]
    assert j0.title == "Senior Python Engineer"
    assert j0.company == "Acme Corp"
    assert j0.posted_at is not None
    assert "FastAPI" in j0.raw_text
    assert "<" not in j0.raw_text
    assert "Salary:" in j0.raw_text


def test_handles_missing_company_and_bad_date():
    payload = json.loads((FIXTURES / "adzuna_sample.json").read_text())

    src = AdzunaSource()
    src._app_id = "test_id"
    src._app_key = "test_key"
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch(max_pages=1))

    assert jobs[1].company is None
    assert jobs[1].posted_at is None


def test_remote_detected_from_title():
    payload = json.loads((FIXTURES / "adzuna_sample.json").read_text())

    src = AdzunaSource()
    src._app_id = "test_id"
    src._app_key = "test_key"
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch(max_pages=1))

    # jobs[2] title is "Remote DevOps Engineer"
    assert jobs[2].remote is True
    # jobs[1] has no "remote" in title/description
    assert jobs[1].remote is None
