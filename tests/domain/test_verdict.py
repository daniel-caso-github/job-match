from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.value_objects.verdict import Verdict


def test_defaults():
    v = Verdict(score=70)
    assert v.score == 70
    assert v.strengths == []
    assert v.risks == []


def test_score_must_be_in_range():
    with pytest.raises(ValidationError):
        Verdict(score=-1)
    with pytest.raises(ValidationError):
        Verdict(score=101)


def test_lists_capped_to_four():
    v = Verdict(
        score=80,
        strengths=["a", "b", "c", "d", "e", "f"],
        risks=["r1", "r2", "r3", "r4", "r5"],
    )
    assert v.strengths == ["a", "b", "c", "d"]
    assert v.risks == ["r1", "r2", "r3", "r4"]


def test_strips_blanks():
    v = Verdict(score=50, strengths=["  ok  ", "", "  "], risks=[""])
    assert v.strengths == ["ok"]
    assert v.risks == []
