from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.profile_form import ProfileForm, TechItem


def _base(**overrides) -> dict:
    base = {
        "id": "daniel-2026",
        "stack": [{"name": "Python", "years": 5}],
        "seniority": "senior",
        "english_level": "B2",
        "location": "AR",
    }
    base.update(overrides)
    return base


def test_minimal_valid_form():
    form = ProfileForm.model_validate(_base())
    assert form.id == "daniel-2026"
    assert form.seniority is Seniority.senior
    assert form.english_level is EnglishLevel.b2
    assert form.willing_to_relocate is False
    assert form.modality == "remote"
    assert form.summary is None


def test_tech_item_validation():
    item = TechItem(name="FastAPI", years=3)
    assert item.years == 3.0
    with pytest.raises(ValidationError):
        TechItem(name="", years=1)
    with pytest.raises(ValidationError):
        TechItem(name="x", years=-1)


def test_rejects_invalid_seniority():
    with pytest.raises(ValidationError):
        ProfileForm.model_validate(_base(seniority="expert"))


def test_rejects_invalid_modality():
    with pytest.raises(ValidationError):
        ProfileForm.model_validate(_base(modality="contract"))


def test_summary_max_length():
    with pytest.raises(ValidationError):
        ProfileForm.model_validate(_base(summary="x" * 2001))
