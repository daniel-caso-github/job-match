from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.sources.remotive import RemotiveSource

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def test_parses_fixture():
    payload = json.loads((FIXTURES / "remotive_sample.json").read_text())

    src = RemotiveSource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch(categories=["software-development"]))

    assert len(jobs) == 3
    assert all(j.source == "remotive" for j in jobs)
    assert all(str(j.url).startswith("https://remotive.com/") for j in jobs)
    assert len({j.id for j in jobs}) == 3

    j0 = jobs[0]
    assert j0.title == "Senior Backend Engineer (Python)"
    assert j0.company == "Acme"
    assert j0.country == "Worldwide"
    assert j0.posted_at is not None
    assert "FastAPI" in j0.raw_text
    assert "<" not in j0.raw_text


def test_handles_missing_company_and_bad_date():
    payload = json.loads((FIXTURES / "remotive_sample.json").read_text())
    src = RemotiveSource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch(categories=["software-development"]))

    assert jobs[1].company is None
    assert jobs[2].posted_at is None
    assert jobs[2].country == "EMEA"


def test_iterates_multiple_categories():
    payload = json.loads((FIXTURES / "remotive_sample.json").read_text())
    src = RemotiveSource()
    with patch.object(src, "_get_json", return_value=payload) as mock_get:
        jobs = list(src.fetch(categories=["software-development", "devops"]))

    assert mock_get.call_count == 2
    assert len(jobs) == 6
