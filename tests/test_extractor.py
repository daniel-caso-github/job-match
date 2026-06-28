from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.extraction.extractor import MAX_INPUT_CHARS, extract_requirements
from src.extraction.schema import EnglishLevel, JobRequirements, Seniority

FIXTURES = Path(__file__).parent / "fixtures" / "jobs"


def _mock_response(payload: dict | str) -> MagicMock:
    """Build a fake GenerateContentResponse.

    If `payload` is a dict that validates as JobRequirements, `.parsed` returns
    the parsed instance (mimicking the SDK's schema mode). Otherwise `.parsed`
    is None and `.text` carries the raw string (mimicking a malformed response).
    """
    resp = MagicMock()
    if isinstance(payload, dict):
        try:
            resp.parsed = JobRequirements.model_validate(payload)
            resp.text = json.dumps(payload)
        except Exception:
            resp.parsed = None
            resp.text = json.dumps(payload)
    else:
        resp.parsed = None
        resp.text = payload
    return resp


def test_stack_normalization():
    req = JobRequirements(stack=["Python", "python", "FastAPI", "", "  Postgres  "])
    assert req.stack == ["python", "fastapi", "postgres"]


def test_extract_happy_path():
    raw = (FIXTURES / "job_clear_backend.txt").read_text()
    expected = {
        "stack": ["Python", "FastAPI", "PostgreSQL"],
        "seniority": "senior",
        "english_level": "C1",
        "requires_eu_residency": False,
        "remote": True,
        "latam_friendly": True,
        "salary_range": "$90k - $130k USD",
        "confidence": 0.9,
    }
    with patch("src.extraction.extractor._generate", return_value=_mock_response(expected)):
        result = extract_requirements(raw)

    assert isinstance(result, JobRequirements)
    assert result.seniority is Seniority.senior
    assert result.english_level is EnglishLevel.c1
    assert result.latam_friendly is True
    assert result.requires_eu_residency is False
    # validator normalized stack to lowercase + dedup
    assert result.stack == ["python", "fastapi", "postgresql"]


def test_extract_invalid_then_repaired():
    bad = {"seniority": "expert"}  # enum value not in Seniority
    good = {"stack": ["go"], "seniority": "senior", "confidence": 0.6}

    bad_resp = _mock_response(bad)
    good_resp = _mock_response(good)

    with patch(
        "src.extraction.extractor._generate", side_effect=[bad_resp, good_resp]
    ) as mock_gen:
        result = extract_requirements("...job description...")

    assert mock_gen.call_count == 2
    assert result.stack == ["go"]
    assert result.seniority is Seniority.senior
    assert result.confidence == 0.6


def test_extract_fails_returns_empty():
    garbage = _mock_response("not json at all")

    with patch("src.extraction.extractor._generate", return_value=garbage):
        result = extract_requirements("...")

    assert isinstance(result, JobRequirements)
    assert result.confidence == 0.0
    assert result.stack == []
    assert result.seniority is None


def test_truncates_long_input():
    # Use a sentinel char that doesn't appear in the prompt template ("Ω").
    SENTINEL = "Ω"
    long_text = SENTINEL * (MAX_INPUT_CHARS + 5000)
    resp = _mock_response({"confidence": 0.0})

    with patch("src.extraction.extractor._generate", return_value=resp) as mock_gen:
        extract_requirements(long_text)

    sent_prompt = mock_gen.call_args.args[0]
    assert sent_prompt.count(SENTINEL) == MAX_INPUT_CHARS
