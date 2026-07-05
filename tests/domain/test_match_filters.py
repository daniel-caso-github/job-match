from src.domain.value_objects.job_requirements import EnglishLevel
from src.domain.value_objects.match_filters import (
    MatchFilters,
    english_levels_up_to,
)


def test_english_levels_up_to_lowest():
    assert english_levels_up_to(EnglishLevel.a1) == [EnglishLevel.a1]


def test_english_levels_up_to_mid_level():
    assert english_levels_up_to(EnglishLevel.b2) == [
        EnglishLevel.a1,
        EnglishLevel.a2,
        EnglishLevel.b1,
        EnglishLevel.b2,
    ]


def test_english_levels_up_to_native_includes_all():
    assert english_levels_up_to(EnglishLevel.native) == list(EnglishLevel)


def test_match_filters_defaults_are_empty():
    filters = MatchFilters()
    assert filters.min_score is None
    assert filters.sources == []
    assert filters.stack == []
    assert filters.seniorities == []
    assert filters.english_levels == []
    assert not filters.remote_only
    assert not filters.latam_only
    assert not filters.exclude_eu
    assert not filters.with_salary
