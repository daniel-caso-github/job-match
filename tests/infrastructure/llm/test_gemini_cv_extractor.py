from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.domain.value_objects.cv_extraction import CvExtraction
from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.infrastructure.llm.gemini_cv_extractor import GeminiCvExtractor

FAKE_PDF = b"%PDF-1.4 fake pdf bytes for tests"


def _mock_response(payload: dict | str) -> MagicMock:
    """Fake GenerateContentResponse: schema mode → .parsed; else raw .text."""
    resp = MagicMock()
    if isinstance(payload, dict):
        try:
            resp.parsed = CvExtraction.model_validate(payload)
            resp.text = json.dumps(payload)
        except Exception:
            resp.parsed = None
            resp.text = json.dumps(payload)
    else:
        resp.parsed = None
        resp.text = payload
    return resp


def test_extract_happy_path():
    expected = {
        "first_name": "Daniel",
        "last_name": "Caso",
        "email": "daniel@example.com",
        "stack": [{"name": "Python", "years": 8}, {"name": "FastAPI", "years": 3}],
        "seniority": "senior",
        "english_level": "C1",
        "location": "Argentina",
        "summary": "Backend engineer with 8 years of experience.",
        "target_roles": ["Backend Engineer", "Tech Lead"],
        "years_of_experience": 8,
        "confidence": 0.9,
    }
    extractor = GeminiCvExtractor()
    with patch.object(extractor, "_generate", return_value=_mock_response(expected)):
        result = extractor.extract(FAKE_PDF)

    assert isinstance(result, CvExtraction)
    assert result.first_name == "Daniel"
    assert result.seniority is Seniority.senior
    assert result.english_level is EnglishLevel.c1
    assert [t.name for t in result.stack] == ["python", "fastapi"]
    assert result.target_roles == ["Backend Engineer", "Tech Lead"]
    assert result.confidence == 0.9


def test_extract_invalid_then_repaired():
    bad = {"seniority": "expert"}  # enum value not in Seniority
    good = {"stack": [{"name": "go", "years": 2}], "seniority": "mid", "confidence": 0.6}

    extractor = GeminiCvExtractor()
    with patch.object(
        extractor, "_generate", side_effect=[_mock_response(bad), _mock_response(good)]
    ) as mock_gen:
        result = extractor.extract(FAKE_PDF)

    assert mock_gen.call_count == 2
    assert [t.name for t in result.stack] == ["go"]
    assert result.seniority is Seniority.mid


def test_extract_fails_returns_empty():
    garbage = _mock_response("not json at all")
    extractor = GeminiCvExtractor()
    with patch.object(extractor, "_generate", return_value=garbage):
        result = extractor.extract(FAKE_PDF)

    assert isinstance(result, CvExtraction)
    assert result.confidence == 0.0
    assert result.stack == []
    assert result.seniority is None


def test_extract_rejects_oversized_pdf_without_calling_gemini():
    extractor = GeminiCvExtractor(max_pdf_bytes=10)
    with patch.object(extractor, "_generate") as mock_gen:
        result = extractor.extract(FAKE_PDF)

    mock_gen.assert_not_called()
    assert result.confidence == 0.0


def test_extract_rejects_empty_pdf():
    extractor = GeminiCvExtractor()
    with patch.object(extractor, "_generate") as mock_gen:
        result = extractor.extract(b"")

    mock_gen.assert_not_called()
    assert result.confidence == 0.0


def test_generate_sends_pdf_as_inline_part():
    extractor = GeminiCvExtractor(client=MagicMock())
    resp = _mock_response({"confidence": 0.0})
    extractor._client.models.generate_content.return_value = resp

    extractor.extract(FAKE_PDF)

    call_kwargs = extractor._client.models.generate_content.call_args.kwargs
    assert call_kwargs["contents"][0].inline_data.data == FAKE_PDF
    assert call_kwargs["contents"][0].inline_data.mime_type == "application/pdf"
