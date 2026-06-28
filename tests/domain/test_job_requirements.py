from src.domain.value_objects.job_requirements import (
    EnglishLevel,
    JobRequirements,
    Seniority,
)


def test_stack_normalization():
    req = JobRequirements(stack=["Python", "python", "FastAPI", "", "  Postgres  "])
    assert req.stack == ["python", "fastapi", "postgres"]


def test_enums_accept_canonical_values():
    req = JobRequirements(seniority="senior", english_level="C1")
    assert req.seniority is Seniority.senior
    assert req.english_level is EnglishLevel.c1


def test_defaults():
    req = JobRequirements()
    assert req.stack == []
    assert req.seniority is None
    assert req.requires_eu_residency is False
    assert req.remote is None
    assert req.confidence == 0.0
