from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, status

from src.interfaces.pipeline import run_collect, run_embed, run_extract, run_score_all_profiles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _run_refresh() -> None:
    try:
        collected = run_collect()
        logger.info("Refresh: collected %d jobs", collected)
        extracted = run_extract()
        logger.info("Refresh: extracted requirements for %d jobs", extracted)
        embedded = run_embed()
        logger.info("Refresh: embedded %d jobs", embedded)
        scores = run_score_all_profiles()
        for profile_id, n in scores.items():
            logger.info("Refresh: scored %d matches for profile %s", n, profile_id)
    except Exception:
        logger.exception("Refresh job failed")


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
def refresh(bg: BackgroundTasks) -> dict:
    bg.add_task(_run_refresh)
    return {"status": "scheduled"}
