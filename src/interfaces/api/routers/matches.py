from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.match_filters import MatchFilters, english_levels_up_to
from src.domain.value_objects.postulation_package import PostulationPackage
from src.infrastructure.orchestration.langgraph.postulation_graph import (
    build_postulation_graph,
)
from src.interfaces.api.dependencies import (
    CurrentProfileDep,
    MatchRepositoryDep,
    PitchTailorerDep,
    ProfileRepositoryDep,
    SessionDep,
    SkillGapAnalyzerDep,
)

logger = logging.getLogger(__name__)

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
    country: Annotated[list[str] | None, Query()] = None,
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
        countries=country or [],
    )
    rows = repo.top_for_profile(current.profile_id, limit=limit, filters=filters)
    matches = [
        {
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "url": str(job.url),
            "source": job.source,
            "country": job.country,
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
        "country": job.country,
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


def _require_valid_match(match, job_id: str):
    """Gating de [[gating-costo-squad-postulacion]]: el squad de postulación

    (Skill Gap Analyst + Resume & Pitch Tailorer) solo puede correr sobre un
    match que ya pasó el embudo semántico + LLM + non-tech-guardrail existente.
    Un `Match` persistido en `matches` ya lo garantiza (`ScoreProfileUseCase`
    solo upsertea candidatos que superaron `semantic_top_k` y siempre aplica el
    guardrail antes de persistir); acá solo defendemos contra un `llm_score`
    ausente (match nunca terminado de scorear).
    """
    if match.llm_score is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"el match para job_id={job_id} todavía no tiene un llm_score "
                "válido; no se puede generar la postulación"
            ),
        )


@router.post("/{job_id}/postulation", status_code=status.HTTP_201_CREATED)
def generate_postulation(
    job_id: str,
    repo: MatchRepositoryDep,
    profiles: ProfileRepositoryDep,
    session: SessionDep,
    current: CurrentProfileDep,
    skill_gap_analyzer: SkillGapAnalyzerDep,
    pitch_tailorer: PitchTailorerDep,
) -> dict:
    """Dispara el squad de postulación (Skill Gap Analyst -> Resume & Pitch
    Tailorer) de punta a punta, síncrono, y persiste el paquete resultante en
    estado `pendiente_aprobacion`. Ver [[aprobacion-humana-postulacion]]."""
    pair = repo.get_for_pair(current.profile_id, job_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="match not found")
    match, job = pair
    _require_valid_match(match, job_id)

    profile = profiles.get(current.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")

    graph = build_postulation_graph(
        skill_gap_analyzer=skill_gap_analyzer, pitch_tailorer=pitch_tailorer
    )
    state = {
        "profile": profile.form,
        "job": job,
        "skill_gap": None,
        "resume_bullets": [],
        "cover_letter": "",
    }
    result = graph.invoke(state)

    package = PostulationPackage(
        skill_gap=result["skill_gap"],
        resume_bullets=result["resume_bullets"],
        cover_letter=result["cover_letter"],
        status="pendiente_aprobacion",
    )
    payload = package.model_dump(mode="json")
    repo.set_postulation_package(current.profile_id, job_id, payload)
    session.commit()
    logger.info(
        "Postulación generada: profile=%s job=%s status=%s",
        current.profile_id, job_id, package.status,
    )
    return payload


@router.get("/{job_id}/postulation")
def get_postulation(
    job_id: str,
    repo: MatchRepositoryDep,
    current: CurrentProfileDep,
) -> dict:
    pair = repo.get_for_pair(current.profile_id, job_id)
    if pair is None or pair[0].postulation_package is None:
        raise HTTPException(status_code=404, detail="postulation package not found")
    return pair[0].postulation_package


def _decide_postulation(
    job_id: str,
    repo: MatchRepositoryDep,
    session: SessionDep,
    current: CurrentProfileDep,
    new_status: str,
) -> dict:
    pair = repo.get_for_pair(current.profile_id, job_id)
    if pair is None or pair[0].postulation_package is None:
        raise HTTPException(status_code=404, detail="postulation package not found")
    package = PostulationPackage.model_validate(pair[0].postulation_package)
    package = package.model_copy(update={"status": new_status})
    payload = package.model_dump(mode="json")
    repo.set_postulation_package(current.profile_id, job_id, payload)
    session.commit()
    logger.info(
        "Postulación %s: profile=%s job=%s", new_status, current.profile_id, job_id
    )
    return payload


@router.post("/{job_id}/postulation/approve")
def approve_postulation(
    job_id: str,
    repo: MatchRepositoryDep,
    session: SessionDep,
    current: CurrentProfileDep,
) -> dict:
    """Aprobación humana explícita — ver [[aprobacion-humana-postulacion]].

    No dispara ningún envío externo: solo habilita el paquete ya generado para
    descarga/copia por parte del usuario."""
    return _decide_postulation(job_id, repo, session, current, "aprobado")


@router.post("/{job_id}/postulation/reject")
def reject_postulation(
    job_id: str,
    repo: MatchRepositoryDep,
    session: SessionDep,
    current: CurrentProfileDep,
) -> dict:
    """Rechazo simple — sin loop de feedback automático (fuera de alcance, ver
    [[aprobacion-humana-postulacion]])."""
    return _decide_postulation(job_id, repo, session, current, "rechazado")
