from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.domain.entities.job import Job
from src.domain.value_objects.job_requirements import (
    EnglishLevel,
    JobRequirements,
    Seniority,
)
from src.domain.value_objects.profile_form import ProfileForm, TechItem
from src.domain.value_objects.skill_gap_report import SkillGapReport
from src.infrastructure.llm.gemini_skill_gap_analyzer import GeminiSkillGapAnalyzer


def _mock_response(payload: dict | str) -> MagicMock:
    resp = MagicMock()
    if isinstance(payload, dict):
        try:
            resp.parsed = SkillGapReport.model_validate(payload)
            resp.text = json.dumps(payload)
        except Exception:
            resp.parsed = None
            resp.text = json.dumps(payload)
    else:
        resp.parsed = None
        resp.text = payload
    return resp


def _profile() -> ProfileForm:
    return ProfileForm(
        username="d",
        stack=[TechItem(name="Python", years=8)],
        seniority=Seniority.senior,
        english_level=EnglishLevel.b2,
        location="AR",
        summary="Backend engineer.",
    )


def _job() -> Job:
    return Job.model_validate({
        "id": "abc",
        "source": "himalayas",
        "url": "https://x.com/j/1",
        "title": "Senior Backend Engineer",
        "raw_text": "We need Python and Kubernetes experience.",
        "requirements": JobRequirements(
            stack=["python", "kubernetes"], seniority=Seniority.senior, confidence=0.9
        ).model_dump(mode="json"),
    })


def test_analyze_happy_path():
    payload = {
        "met_requirements": ["Python"],
        "gaps": ["Kubernetes"],
        "notes": "Mention transferable container experience.",
        "confidence": 0.85,
    }
    analyzer = GeminiSkillGapAnalyzer()
    with patch.object(analyzer, "_generate", return_value=_mock_response(payload)):
        report = analyzer.analyze(_profile(), _job())

    assert isinstance(report, SkillGapReport)
    assert report.met_requirements == ["Python"]
    assert report.gaps == ["Kubernetes"]
    assert report.confidence == 0.85


def test_analyze_invalid_then_repaired():
    bad = {"confidence": 5}  # out of range
    good = {"met_requirements": ["Python"], "gaps": [], "confidence": 0.7}

    analyzer = GeminiSkillGapAnalyzer()
    with patch.object(
        analyzer, "_generate", side_effect=[_mock_response(bad), _mock_response(good)]
    ) as mock_gen:
        report = analyzer.analyze(_profile(), _job())

    assert mock_gen.call_count == 2
    assert report.confidence == 0.7


def test_analyze_fails_returns_empty_report():
    garbage = _mock_response("not json at all")
    analyzer = GeminiSkillGapAnalyzer()
    with patch.object(analyzer, "_generate", return_value=garbage):
        report = analyzer.analyze(_profile(), _job())

    assert isinstance(report, SkillGapReport)
    assert report.confidence == 0.0
    assert report.met_requirements == []
    assert report.gaps == []


def test_analyze_never_raises_on_unexpected_error():
    analyzer = GeminiSkillGapAnalyzer()
    with patch.object(analyzer, "_generate", side_effect=RuntimeError("boom")):
        report = analyzer.analyze(_profile(), _job())

    assert report == SkillGapReport(confidence=0.0)
