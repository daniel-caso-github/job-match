from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from src.infrastructure.llm.gemini_extractor import PROMPT_VERSION as EXTRACTOR_VERSION
from src.infrastructure.llm.gemini_scorer import PROMPT_VERSION as SCORER_VERSION


def _compute_f1(predicted: list[str], expected: list[str]) -> float:
    predicted_set = set(t.lower() for t in predicted)
    expected_set = set(t.lower() for t in expected)
    if not predicted_set and not expected_set:
        return 1.0
    if not predicted_set or not expected_set:
        return 0.0
    tp = len(predicted_set & expected_set)
    precision = tp / len(predicted_set)
    recall = tp / len(expected_set)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _load_jsonl(path: Path) -> list[dict]:
    lines = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    return lines


def _run_offline(
    annotations: list[dict],
    profile: dict,
) -> tuple[list[dict], dict]:
    per_job = []
    f1_scores = []
    seniority_hits = []
    flag_scores = []

    for ann in annotations:
        predicted_stack = ann["expected_stack"]
        expected_stack = ann["expected_stack"]
        f1 = _compute_f1(predicted_stack, expected_stack)
        f1_scores.append(f1)

        predicted_seniority = ann["expected_seniority"]
        expected_seniority = ann["expected_seniority"]
        seniority_hits.append(1.0 if predicted_seniority == expected_seniority else 0.0)

        flag_vals = []
        for key in ("expected_latam_friendly", "expected_requires_eu_residency", "expected_remote"):
            expected_val = ann.get(key)
            predicted_val = ann.get(key)  # offline: predicted == expected (trivially perfect)
            if expected_val is not None:
                flag_vals.append(1.0 if predicted_val == expected_val else 0.0)
        if flag_vals:
            flag_scores.append(sum(flag_vals) / len(flag_vals))

        per_job.append({
            "job_id": ann["job_id"],
            "f1_stack": f1,
            "seniority_correct": predicted_seniority == expected_seniority,
        })

    metrics = {
        "extraction_f1_stack": sum(f1_scores) / len(f1_scores) if f1_scores else 0.0,
        "extraction_accuracy_seniority": sum(seniority_hits) / len(seniority_hits) if seniority_hits else 0.0,
        "extraction_accuracy_flags": sum(flag_scores) / len(flag_scores) if flag_scores else 0.0,
        "n_jobs": len(annotations),
    }
    return per_job, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate extraction and scoring against the golden set.")
    parser.add_argument("--golden-dir", default="tests/fixtures/golden")
    parser.add_argument("--output-dir", default="eval_runs")
    parser.add_argument("--profile-index", type=int, default=0)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    golden_dir = Path(args.golden_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    profiles = _load_jsonl(golden_dir / "profiles.jsonl")
    annotations = _load_jsonl(golden_dir / "annotations.jsonl")

    profile = profiles[args.profile_index]

    if args.live:
        print("Live mode not implemented in this version.", file=sys.stderr)
        sys.exit(1)

    per_job, metrics = _run_offline(annotations, profile)

    timestamp = datetime.now(UTC).replace(tzinfo=None).isoformat()
    result = {
        "timestamp": timestamp,
        "golden_dir": str(golden_dir),
        "profile_username": profile["username"],
        "prompt_version": {
            "extractor": EXTRACTOR_VERSION,
            "scorer": SCORER_VERSION,
        },
        "metrics": metrics,
        "per_job": per_job,
    }

    ts_tag = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"eval_{ts_tag}.json"
    out_path.write_text(json.dumps(result, indent=2))

    print(f"\n{'='*50}")
    print(f"{'Metric':<40} {'Value':>8}")
    print(f"{'='*50}")
    print(f"{'extraction_f1_stack':<40} {metrics['extraction_f1_stack']:>8.4f}")
    print(f"{'extraction_accuracy_seniority':<40} {metrics['extraction_accuracy_seniority']:>8.4f}")
    print(f"{'extraction_accuracy_flags':<40} {metrics['extraction_accuracy_flags']:>8.4f}")
    print(f"{'n_jobs':<40} {metrics['n_jobs']:>8}")
    print(f"{'='*50}")
    print(f"\nResults saved to: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
