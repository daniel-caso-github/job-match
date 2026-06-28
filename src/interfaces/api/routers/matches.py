from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.interfaces.api.dependencies import MatchRepositoryDep

router = APIRouter(prefix="/matches", tags=["matches"])


SOURCE_ATTRIBUTION = (
    "Jobs via Himalayas (himalayas.app) and Remotive (remotive.com). "
    "Original postings linked in each match."
)


def _round_semantic(score: float | None) -> float | None:
    return round(score, 3) if score is not None else None


@router.get("")
def list_matches(
    repo: MatchRepositoryDep,
    profile_id: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    rows = repo.top_for_profile(profile_id, limit=limit)
    matches = [
        {
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "url": str(job.url),
            "source": job.source,
            "llm_score": match.llm_score,
            "semantic_score": _round_semantic(match.semantic_score),
            "verdict": match.verdict,
        }
        for match, job in rows
    ]
    return {
        "profile_id": profile_id,
        "count": len(matches),
        "matches": matches,
        "source_attribution": SOURCE_ATTRIBUTION,
    }


@router.get("/{job_id}")
def match_detail(
    job_id: str,
    repo: MatchRepositoryDep,
    profile_id: str = Query(..., min_length=1),
) -> dict:
    pair = repo.get_for_pair(profile_id, job_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="match not found")
    match, job = pair
    return {
        "job_id": job.id,
        "title": job.title,
        "company": job.company,
        "url": str(job.url),
        "source": job.source,
        "llm_score": match.llm_score,
        "semantic_score": _round_semantic(match.semantic_score),
        "verdict": match.verdict,
        "requirements": (
            job.requirements.model_dump(mode="json") if job.requirements else None
        ),
        "raw_text": job.raw_text,
        "scored_at": match.scored_at.isoformat() if match.scored_at else None,
        "source_attribution": SOURCE_ATTRIBUTION,
    }
