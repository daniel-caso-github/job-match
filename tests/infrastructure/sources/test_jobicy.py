from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.sources.jobicy import JobicySource

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def test_parses_fixture():
    payload = json.loads((FIXTURES / "jobicy_sample.json").read_text())

    src = JobicySource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch())

    assert len(jobs) == 3
    assert all(j.source == "jobicy" for j in jobs)
    assert all(str(j.url).startswith("https://jobicy.com/") for j in jobs)
    assert len({j.id for j in jobs}) == 3

    j0 = jobs[0]
    assert j0.title == "Senior Python Engineer"
    assert j0.company == "Acme Corp"
    assert j0.country == "Worldwide"
    assert j0.remote is True
    assert j0.posted_at is not None
    assert "FastAPI" in j0.raw_text
    assert "<" not in j0.raw_text


def test_handles_missing_company_and_bad_date():
    payload = json.loads((FIXTURES / "jobicy_sample.json").read_text())

    src = JobicySource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch())

    assert jobs[1].company is None
    assert jobs[1].posted_at is None
    assert jobs[2].country == "EMEA"
    assert jobs[2].posted_at is not None


def test_excerpt_used_when_description_short():
    payload = json.loads((FIXTURES / "jobicy_sample.json").read_text())
    # Make description very short so excerpt is prepended
    payload["jobs"][0]["jobDescription"] = "<p>Short.</p>"
    payload["jobs"][0]["jobExcerpt"] = "We need a senior Python engineer."

    src = JobicySource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch())

    assert "senior Python engineer" in jobs[0].raw_text
