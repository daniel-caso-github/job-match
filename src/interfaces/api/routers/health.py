from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from src.infrastructure.config import settings
from src.interfaces.api.dependencies import SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: SessionDep) -> dict:
    db_ok = True
    try:
        session.execute(select(1))
    except Exception:
        db_ok = False

    gemini_ok = bool(settings.gemini_api_key)
    overall = "ok" if (db_ok and gemini_ok) else "degraded"
    return {
        "status": overall,
        "db": db_ok,
        "gemini_key_present": gemini_ok,
        "model": settings.gemini_model,
    }
