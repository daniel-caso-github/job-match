from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.domain.value_objects.job_requirements import (
    EnglishLevel,
    JobRequirements,
    Seniority,
)
from src.infrastructure.llm.gemini_extractor import GeminiExtractor

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "jobs"


def _mock_response(payload: dict | str) -> MagicMock:
    """Fake GenerateContentResponse: schema mode → .parsed; else raw .text."""
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
    extractor = GeminiExtractor()
    with patch.object(extractor, "_generate", return_value=_mock_response(expected)):
        result = extractor.extract(raw)

    assert isinstance(result, JobRequirements)
    assert result.seniority is Seniority.senior
    assert result.english_level is EnglishLevel.c1
    assert result.latam_friendly is True
    assert result.requires_eu_residency is False
    assert result.stack == ["python", "fastapi", "postgresql"]


def test_extract_invalid_then_repaired():
    bad = {"seniority": "expert"}  # enum value not in Seniority
    good = {"stack": ["go"], "seniority": "senior", "confidence": 0.6}

    extractor = GeminiExtractor()
    with patch.object(
        extractor, "_generate", side_effect=[_mock_response(bad), _mock_response(good)]
    ) as mock_gen:
        result = extractor.extract("...job description...")

    assert mock_gen.call_count == 2
    assert result.stack == ["go"]
    assert result.seniority is Seniority.senior


def test_extract_fails_returns_empty():
    garbage = _mock_response("not json at all")
    extractor = GeminiExtractor()
    with patch.object(extractor, "_generate", return_value=garbage):
        result = extractor.extract("...")

    assert isinstance(result, JobRequirements)
    assert result.confidence == 0.0
    assert result.stack == []
    assert result.seniority is None


def test_truncates_long_input():
    SENTINEL = "Ω"
    extractor = GeminiExtractor(max_input_chars=12_000)
    long_text = SENTINEL * (12_000 + 5_000)
    resp = _mock_response({"confidence": 0.0})

    with patch.object(extractor, "_generate", return_value=resp) as mock_gen:
        extractor.extract(long_text)

    sent_prompt = mock_gen.call_args.args[0]
    assert sent_prompt.count(SENTINEL) == 12_000
