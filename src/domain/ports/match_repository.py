from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.entities.job import Job
from src.domain.entities.match import Match


class MatchRepository(ABC):
    """Port de persistencia para matches (par profile-job scoreado)."""

    @abstractmethod
    def upsert(
        self,
        *,
        profile_id: str,
        job_id: str,
        semantic_score: float,
        llm_score: int,
        verdict: dict[str, Any],
    ) -> None: ...

    @abstractmethod
    def top_for_profile(
        self, profile_id: str, limit: int = 20
    ) -> list[tuple[Match, Job]]: ...

    @abstractmethod
    def get_for_pair(
        self, profile_id: str, job_id: str
    ) -> tuple[Match, Job] | None: ...
