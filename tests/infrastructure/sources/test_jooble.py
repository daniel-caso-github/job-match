from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.sources.jooble import JoobleSource

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def test_no_key_returns_empty_without_raising():
    src = JoobleSource()
    src._api_key = None

    jobs = list(src.fetch())

    assert jobs == []


def test_parses_fixture():
    payload = json.loads((FIXTURES / "jooble_sample.json").read_text())

    src = JoobleSource()
    src._api_key = "test_key"
    with patch.object(src, "_post_json", return_value=payload):
        jobs = list(src.fetch(max_pages=1))

    assert len(jobs) == 3
    assert all(j.source == "jooble" for j in jobs)
    assert all(str(j.url).startswith("https://jooble.org/") for j in jobs)
    assert len({j.id for j in jobs}) == 3

    j0 = jobs[0]
    assert j0.title == "Senior Python Engineer"
    assert j0.company == "Acme Corp"
    assert j0.country == "Worldwide"
    assert j0.posted_at is not None
    assert "FastAPI" in j0.raw_text
    assert "<" not in j0.raw_text


def test_handles_missing_company_and_bad_date():
    payload = json.loads((FIXTURES / "jooble_sample.json").read_text())

    src = JoobleSource()
    src._api_key = "test_key"
    with patch.object(src, "_post_json", return_value=payload):
        jobs = list(src.fetch(max_pages=1))

    assert jobs[1].company is None
    assert jobs[1].posted_at is None
    assert jobs[2].country == "EMEA"
