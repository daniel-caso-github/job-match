from __future__ import annotations

from typing import Annotated

from langgraph.graph.message import add
from typing_extensions import TypedDict


class VerdictRef(TypedDict):
    job_id: str
    llm_score: int
    semantic_score: float
    guardrail_applied: bool


def _merge_verdict_refs(
    left: list[VerdictRef], right: list[VerdictRef]
) -> list[VerdictRef]:
    seen = {v["job_id"] for v in left}
    return left + [v for v in right if v["job_id"] not in seen]


class ScoreState(TypedDict):
    profile_id: str
    candidate_job_ids: list[str]
    verdicts: Annotated[list[VerdictRef], _merge_verdict_refs]
    failed_job_ids: Annotated[list[str], add]


class ChatState(TypedDict):
    profile_id: str
    messages: Annotated[list, add]
    cited_job_ids: Annotated[list[str], add]
