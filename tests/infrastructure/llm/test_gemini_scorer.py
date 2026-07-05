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
from src.domain.value_objects.verdict import Verdict
from src.infrastructure.llm.gemini_scorer import GeminiScorer


def _mock_response(payload: dict | str) -> MagicMock:
    resp = MagicMock()
    if isinstance(payload, dict):
        try:
            resp.parsed = Verdict.model_validate(payload)
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
        stack=[TechItem(name="Python", years=8), TechItem(name="FastAPI", years=3)],
        seniority=Seniority.senior,
        english_level=EnglishLevel.b2,
        location="AR",
        summary="Backend engineer.",
    )


def _requirements() -> JobRequirements:
    return JobRequirements(
        stack=["python", "fastapi"],
        seniority=Seniority.senior,
        english_level=EnglishLevel.b2,
        remote=True,
        confidence=0.9,
    )


def _job() -> Job:
    return Job.model_validate({
        "id": "abc",
        "source": "himalayas",
        "url": "https://x.com/j/1",
        "title": "Senior Backend Engineer",
        "raw_text": "We need Python and FastAPI experience.",
        "requirements": _requirements().model_dump(mode="json"),
    })


def test_score_happy_path():
    payload = {
        "score": 88,
        "strengths": ["Stack matches", "Seniority aligned"],
        "risks": [],
    }
    scorer = GeminiScorer()
    with patch.object(scorer, "_generate", return_value=_mock_response(payload)):
        v = scorer.score(_profile(), _job())

    assert isinstance(v, Verdict)
    assert v.score == 88
    assert v.strengths == ["Stack matches", "Seniority aligned"]
    assert v.risks == []


def test_score_invalid_then_repaired():
    bad = {"score": 200}  # out of range
    good = {"score": 70, "strengths": ["ok"], "risks": ["minor gap"]}

    scorer = GeminiScorer()
    with patch.object(
        scorer, "_generate", side_effect=[_mock_response(bad), _mock_response(good)]
    ) as mock_gen:
        v = scorer.score(_profile(), _job())

    assert mock_gen.call_count == 2
    assert v.score == 70
    assert v.risks == ["minor gap"]


def test_score_fails_returns_neutral():
    garbage = _mock_response("not json at all")
    scorer = GeminiScorer()
    with patch.object(scorer, "_generate", return_value=garbage):
        v = scorer.score(_profile(), _job())

    assert isinstance(v, Verdict)
    assert v.score == 50
    assert v.strengths == []
    assert v.risks == ["scoring unavailable"]
