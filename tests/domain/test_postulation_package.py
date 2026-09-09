from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.value_objects.postulation_package import PostulationPackage
from src.domain.value_objects.skill_gap_report import SkillGapReport


def _package(**overrides) -> PostulationPackage:
    data = {
        "skill_gap": SkillGapReport(met_requirements=["python"], gaps=["k8s"]),
        "resume_bullets": ["Built X with Python"],
        "cover_letter": "Dear hiring team...",
    }
    data.update(overrides)
    return PostulationPackage(**data)


def test_defaults_to_pendiente_aprobacion():
    pkg = _package()
    assert pkg.status == "pendiente_aprobacion"


def test_status_transitions_are_explicit():
    pkg = _package()
    approved = pkg.model_copy(update={"status": "aprobado"})
    rejected = pkg.model_copy(update={"status": "rechazado"})
    assert approved.status == "aprobado"
    assert rejected.status == "rechazado"
    assert pkg.status == "pendiente_aprobacion"  # inmutable


def test_rejects_invalid_status():
    with pytest.raises(ValidationError):
        _package(status="quien-sabe")


def test_round_trips_through_json_dict():
    pkg = _package()
    payload = pkg.model_dump(mode="json")
    restored = PostulationPackage.model_validate(payload)
    assert restored == pkg
