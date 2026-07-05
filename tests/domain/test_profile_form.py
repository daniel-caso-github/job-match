from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.profile_form import ProfileForm, TechItem


def _base(**overrides) -> dict:
    base = {
        "username": "daniel-2026",
        "stack": [{"name": "Python", "years": 5}],
        "seniority": "senior",
        "english_level": "B2",
        "location": "AR",
    }
    base.update(overrides)
    return base


def test_minimal_valid_form():
    form = ProfileForm.model_validate(_base())
    assert form.username == "daniel-2026"
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


def test_username_is_stripped_and_lowercased():
    form = ProfileForm.model_validate(_base(username="  Daniel-2026 "))
    assert form.username == "daniel-2026"


def test_username_rejects_invalid_characters():
    with pytest.raises(ValidationError):
        ProfileForm.model_validate(_base(username="daniel test!"))
    with pytest.raises(ValidationError):
        ProfileForm.model_validate(_base(username="-empieza-mal"))


def test_tech_item_name_is_stripped_and_lowercased():
    assert TechItem(name="  PostgreSQL ", years=4).name == "postgresql"


def test_tech_item_rejects_blank_name():
    with pytest.raises(ValidationError):
        TechItem(name="   ", years=1)


def test_stack_dedups_by_normalized_name_keeping_first():
    form = ProfileForm.model_validate(_base(stack=[
        {"name": "Python", "years": 5},
        {"name": " python ", "years": 2},
        {"name": "AWS", "years": 3},
    ]))
    assert [(t.name, t.years) for t in form.stack] == [("python", 5.0), ("aws", 3.0)]


def test_salary_defaults_to_none_with_usd_currency():
    form = ProfileForm.model_validate(_base())
    assert form.salary_min is None
    assert form.salary_max is None
    assert form.salary_currency == "USD"


def test_salary_currency_is_uppercased():
    form = ProfileForm.model_validate(_base(salary_currency="usd"))
    assert form.salary_currency == "USD"


def test_salary_min_cannot_exceed_max():
    with pytest.raises(ValidationError):
        ProfileForm.model_validate(_base(salary_min=90000, salary_max=50000))


def test_salary_accepts_open_ended_range():
    form = ProfileForm.model_validate(_base(salary_min=60000))
    assert form.salary_min == 60000
    assert form.salary_max is None
