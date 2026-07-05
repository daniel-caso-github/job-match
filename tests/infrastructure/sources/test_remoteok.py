from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.sources.remoteok import RemoteOkSource

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def test_parses_fixture():
    payload = json.loads((FIXTURES / "remoteok_sample.json").read_text())

    src = RemoteOkSource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch())

    assert len(jobs) == 3
    assert all(j.source == "remoteok" for j in jobs)
    assert all(str(j.url).startswith("https://remoteok.com/") for j in jobs)
    assert len({j.id for j in jobs}) == 3

    j0 = jobs[0]
    assert j0.title == "Senior Python Engineer"
    assert j0.company == "Acme Corp"
    assert j0.remote is True
    assert j0.posted_at is not None
    assert "FastAPI" in j0.raw_text
    assert "<" not in j0.raw_text


def test_skips_legal_notice():
    payload = json.loads((FIXTURES / "remoteok_sample.json").read_text())

    src = RemoteOkSource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch())

    # Legal notice element (first in array) must be skipped
    assert all(j.title != "legal" for j in jobs)
    assert len(jobs) == 3


def test_handles_missing_company_and_bad_date():
    payload = json.loads((FIXTURES / "remoteok_sample.json").read_text())

    src = RemoteOkSource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch())

    assert jobs[1].company is None
    assert jobs[2].posted_at is None


def test_falls_back_to_epoch_when_date_missing():
    payload = json.loads((FIXTURES / "remoteok_sample.json").read_text())
    payload[3]["date"] = None  # force fallback to epoch
    payload[3]["epoch"] = 1751270400

    src = RemoteOkSource()
    with patch.object(src, "_get_json", return_value=payload):
        jobs = list(src.fetch())

    assert jobs[2].posted_at is not None
