from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Match(BaseModel):
    """Par profile-job scoreado.

    `verdict` queda como dict aquí; en fase 3 se valida contra Verdict (value
    object) en los use cases / handlers.
    """

    profile_id: str
    job_id: str
    semantic_score: float | None = None
    llm_score: int | None = None
    verdict: dict[str, Any] | None = None
    scored_at: datetime | None = None
