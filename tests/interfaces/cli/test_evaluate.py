from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.interfaces.cli.evaluate import _compute_f1, _load_jsonl, _run_offline

GOLDEN_DIR = Path("tests/fixtures/golden")


def test_golden_jobs_jsonl_loads():
    records = _load_jsonl(GOLDEN_DIR / "jobs.jsonl")
    assert len(records) == 30
    for r in records:
        assert "id" in r
        assert "raw_text" in r


def test_golden_profiles_jsonl_loads():
    records = _load_jsonl(GOLDEN_DIR / "profiles.jsonl")
    assert len(records) == 2
    assert records[0]["username"] == "senior_python_dev"
    assert records[1]["username"] == "fullstack_react_ts"


def test_golden_annotations_jsonl_loads():
    records = _load_jsonl(GOLDEN_DIR / "annotations.jsonl")
    assert len(records) == 30
    for r in records:
        assert "job_id" in r
        assert "reference_llm_score" in r


def test_f1_perfect_match():
    assert _compute_f1(["python", "fastapi"], ["python", "fastapi"]) == 1.0


def test_f1_both_empty():
    assert _compute_f1([], []) == 1.0


def test_f1_predicted_empty():
    assert _compute_f1([], ["python"]) == 0.0


def test_f1_expected_empty():
    assert _compute_f1(["python"], []) == 0.0


def test_f1_partial_overlap():
    result = _compute_f1(["python", "fastapi", "redis"], ["python", "fastapi", "docker"])
    assert 0.0 < result < 1.0


def test_f1_case_insensitive():
    assert _compute_f1(["Python", "FastAPI"], ["python", "fastapi"]) == 1.0


def test_offline_metrics_keys():
    annotations = _load_jsonl(GOLDEN_DIR / "annotations.jsonl")
    profiles = _load_jsonl(GOLDEN_DIR / "profiles.jsonl")
    per_job, metrics = _run_offline(annotations, profiles[0])
    assert "extraction_f1_stack" in metrics
    assert "extraction_accuracy_seniority" in metrics
    assert "extraction_accuracy_flags" in metrics
    assert "n_jobs" in metrics
    assert metrics["n_jobs"] == 30


def test_offline_mode_perfect_scores():
    annotations = _load_jsonl(GOLDEN_DIR / "annotations.jsonl")
    profiles = _load_jsonl(GOLDEN_DIR / "profiles.jsonl")
    _, metrics = _run_offline(annotations, profiles[0])
    assert metrics["extraction_f1_stack"] == pytest.approx(1.0)
    assert metrics["extraction_accuracy_flags"] == pytest.approx(1.0)


def test_offline_per_job_count():
    annotations = _load_jsonl(GOLDEN_DIR / "annotations.jsonl")
    profiles = _load_jsonl(GOLDEN_DIR / "profiles.jsonl")
    per_job, _ = _run_offline(annotations, profiles[0])
    assert len(per_job) == 30


def test_offline_output_written(tmp_path):
    annotations = _load_jsonl(GOLDEN_DIR / "annotations.jsonl")
    profiles = _load_jsonl(GOLDEN_DIR / "profiles.jsonl")
    per_job, metrics = _run_offline(annotations, profiles[0])

    out_file = tmp_path / "eval_test.json"
    result = {
        "timestamp": "2026-07-10T00:00:00",
        "golden_dir": str(GOLDEN_DIR),
        "profile_username": profiles[0]["username"],
        "prompt_version": {"extractor": "v1", "scorer": "v1"},
        "metrics": metrics,
        "per_job": per_job,
    }
    out_file.write_text(json.dumps(result, indent=2))

    loaded = json.loads(out_file.read_text())
    assert loaded["metrics"]["n_jobs"] == 30
    assert loaded["prompt_version"]["extractor"] == "v1"
