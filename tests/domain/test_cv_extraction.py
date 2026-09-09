from __future__ import annotations

from src.domain.value_objects.cv_extraction import CvExtraction
from src.domain.value_objects.job_requirements import EnglishLevel, Seniority


def test_defaults_are_low_confidence_and_empty():
    extraction = CvExtraction()
    assert extraction.confidence == 0.0
    assert extraction.stack == []
    assert extraction.target_roles == []
    assert extraction.seniority is None
    assert extraction.english_level is None


def test_full_extraction():
    extraction = CvExtraction.model_validate(
        {
            "first_name": "Daniel",
            "last_name": "Caso",
            "email": "daniel@example.com",
            "stack": [{"name": "Python", "years": 8}],
            "seniority": "senior",
            "english_level": "C1",
            "location": "Argentina",
            "summary": "Backend engineer.",
            "target_roles": ["Backend Engineer", "backend engineer", "Tech Lead"],
            "years_of_experience": 8,
            "confidence": 0.85,
        }
    )
    assert extraction.seniority is Seniority.senior
    assert extraction.english_level is EnglishLevel.c1
    assert extraction.stack[0].name == "python"
    # dedup case-insensitive preservando el primero
    assert extraction.target_roles == ["Backend Engineer", "Tech Lead"]
    assert extraction.confidence == 0.85


def test_years_of_experience_bounds():
    extraction = CvExtraction.model_validate({"years_of_experience": 0})
    assert extraction.years_of_experience == 0
