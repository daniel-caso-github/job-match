from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.domain.entities.job import Job
from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.profile_form import ProfileForm, TechItem
from src.domain.value_objects.skill_gap_report import SkillGapReport
from src.infrastructure.llm.gemini_pitch_tailorer import GeminiPitchTailorer, _TailoredPitch


def _mock_response(payload: dict | str) -> MagicMock:
    resp = MagicMock()
    if isinstance(payload, dict):
        try:
            resp.parsed = _TailoredPitch.model_validate(payload)
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


def _job(source: str = "himalayas") -> Job:
    return Job.model_validate({
        "id": "abc",
        "source": source,
        "url": "https://x.com/j/1",
        "title": "Senior Backend Engineer",
        "raw_text": "We need Python experience.",
    })


def _skill_gap() -> SkillGapReport:
    return SkillGapReport(met_requirements=["Python"], gaps=["Kubernetes"], confidence=0.8)


def test_tailor_happy_path():
    payload = {
        "resume_bullets": ["Led backend migration to Python/FastAPI"],
        "cover_letter": "Dear hiring team, ...",
    }
    tailorer = GeminiPitchTailorer()
    with patch.object(tailorer, "_generate", return_value=_mock_response(payload)):
        bullets, cover_letter = tailorer.tailor(_profile(), _job(), _skill_gap())

    assert bullets == ["Led backend migration to Python/FastAPI"]
    assert cover_letter == "Dear hiring team, ..."


def test_tailor_invalid_then_repaired():
    bad = {"resume_bullets": "not-a-list"}
    good = {"resume_bullets": ["ok bullet"], "cover_letter": "ok letter"}

    tailorer = GeminiPitchTailorer()
    with patch.object(
        tailorer, "_generate", side_effect=[_mock_response(bad), _mock_response(good)]
    ) as mock_gen:
        bullets, cover_letter = tailorer.tailor(_profile(), _job(), _skill_gap())

    assert mock_gen.call_count == 2
    assert bullets == ["ok bullet"]
    assert cover_letter == "ok letter"


def test_tailor_fails_returns_empty():
    garbage = _mock_response("not json at all")
    tailorer = GeminiPitchTailorer()
    with patch.object(tailorer, "_generate", return_value=garbage):
        bullets, cover_letter = tailorer.tailor(_profile(), _job(), _skill_gap())

    assert bullets == []
    assert cover_letter == ""


def test_tailor_never_raises_on_unexpected_error():
    tailorer = GeminiPitchTailorer()
    with patch.object(tailorer, "_generate", side_effect=RuntimeError("boom")):
        bullets, cover_letter = tailorer.tailor(_profile(), _job(), _skill_gap())

    assert (bullets, cover_letter) == ([], "")
