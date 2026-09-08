from __future__ import annotations

from pydantic import BaseModel, Field


class JudgeVerdict(BaseModel):
    is_grounded: bool = Field(description="True if the claim is supported by the job text.")
    quote: str | None = Field(default=None, description="Verbatim excerpt supporting the claim.")
    explanation: str = Field(description="Why grounded or not.")


class ScoringJudgement(BaseModel):
    score_in_range: bool = Field(description="True if llm_score is within ±10 pts of reference.")
    estimated_score: int = Field(ge=0, le=100, description="Judge's independent score estimate.")
    reasoning: str = Field(description="Justification for the judgement.")
