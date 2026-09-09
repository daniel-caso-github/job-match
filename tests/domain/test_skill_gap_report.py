from __future__ import annotations

from src.domain.value_objects.skill_gap_report import SkillGapReport


def test_defaults():
    r = SkillGapReport()
    assert r.met_requirements == []
    assert r.gaps == []
    assert r.notes is None
    assert r.confidence == 0.0


def test_fallback_shape_matches_error_contract():
    r = SkillGapReport(confidence=0.0)
    assert r.confidence == 0.0
    assert r.met_requirements == []
    assert r.gaps == []


def test_confidence_bounds():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SkillGapReport(confidence=-0.1)
    with pytest.raises(ValidationError):
        SkillGapReport(confidence=1.1)
