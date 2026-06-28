from __future__ import annotations

from src.domain.entities.job import Job
from src.domain.services.embedding_text import (
    job_text_for_embedding,
    profile_text_for_embedding,
)
from src.domain.value_objects.job_requirements import (
    EnglishLevel,
    JobRequirements,
    Seniority,
)
from src.domain.value_objects.profile_form import ProfileForm, TechItem


def _job(**overrides) -> Job:
    base = {
        "id": "j1",
        "source": "himalayas",
        "url": "https://example.com/job/1",
        "title": "Backend Engineer",
        "company": "Acme",
        "raw_text": "We need a backend engineer with Python and FastAPI.",
    }
    base.update(overrides)
    return Job.model_validate(base)


def test_job_text_without_requirements():
    text = job_text_for_embedding(_job())
    assert "Backend Engineer" in text
    assert "Acme" in text
    assert "Python and FastAPI" in text
    assert "Stack:" not in text  # no requirements yet


def test_job_text_with_requirements():
    req = JobRequirements(stack=["python", "fastapi"], seniority=Seniority.senior)
    text = job_text_for_embedding(_job(requirements=req))
    assert "Stack: python, fastapi" in text
    assert "Seniority: senior" in text


def test_job_text_truncates_raw_text():
    long = "x" * 5000
    text = job_text_for_embedding(_job(raw_text=long))
    assert text.count("x") == 1500


def test_job_text_handles_missing_company():
    text = job_text_for_embedding(_job(company=None))
    assert "Backend Engineer" in text
    assert "Acme" not in text


def test_profile_text_basic():
    form = ProfileForm(
        id="d",
        stack=[TechItem(name="Python", years=8), TechItem(name="FastAPI", years=3)],
        seniority=Seniority.senior,
        english_level=EnglishLevel.b2,
        location="AR",
        summary="Backend engineer focused on APIs.",
    )
    text = profile_text_for_embedding(form)
    assert "Python (8y)" in text
    assert "FastAPI (3y)" in text
    assert "Seniority: senior" in text
    assert "English: B2" in text
    assert "Location: AR" in text
    assert "Modality: remote" in text
    assert "Backend engineer focused on APIs." in text


def test_profile_text_without_summary_or_stack():
    form = ProfileForm(
        id="d",
        stack=[],
        seniority=Seniority.junior,
        english_level=EnglishLevel.a2,
        location="MX",
    )
    text = profile_text_for_embedding(form)
    assert "Stack: (unspecified)" in text
    assert "Seniority: junior" in text
