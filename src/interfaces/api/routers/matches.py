from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.match_filters import MatchFilters, english_levels_up_to
from src.interfaces.api.dependencies import CurrentProfileDep, MatchRepositoryDep

router = APIRouter(prefix="/matches", tags=["matches"])


SOURCE_ATTRIBUTION = (
    "Jobs via Himalayas (himalayas.app), Remotive (remotive.com), "
    "Jobicy (jobicy.com), Remote OK (remoteok.com), Arbeitnow (arbeitnow.com), "
    "Adzuna (adzuna.com) and Jooble (jooble.org). "
    "Original postings linked in each match."
)


def _round_semantic(score: float | None) -> float | None:
    return round(score, 3) if score is not None else None


@router.get("")
def list_matches(
    repo: MatchRepositoryDep,
    current: CurrentProfileDep,
    limit: int = Query(20, ge=1, le=100),
    min_score: Annotated[int | None, Query(ge=0, le=100)] = None,
    source: Annotated[list[str] | None, Query()] = None,
    stack: Annotated[list[str] | None, Query()] = None,
    seniority: Annotated[list[Seniority] | None, Query()] = None,
    english_max: EnglishLevel | None = None,
    remote_only: bool = False,
    latam_only: bool = False,
    exclude_eu: bool = False,
    with_salary: bool = False,
) -> dict:
    filters = MatchFilters(
        min_score=min_score,
        sources=source or [],
        stack=stack or [],
        seniorities=seniority or [],
        english_levels=english_levels_up_to(english_max) if english_max else [],
        remote_only=remote_only,
        latam_only=latam_only,
        exclude_eu=exclude_eu,
        with_salary=with_salary,
    )
    rows = repo.top_for_profile(current.profile_id, limit=limit, filters=filters)
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
        "profile_id": current.profile_id,
        "count": len(matches),
        "matches": matches,
        "source_attribution": SOURCE_ATTRIBUTION,
    }


@router.get("/{job_id}")
def match_detail(
    job_id: str,
    repo: MatchRepositoryDep,
    current: CurrentProfileDep,
) -> dict:
    pair = repo.get_for_pair(current.profile_id, job_id)
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
