from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.infrastructure.orchestration.langgraph.states import ScoreState

logger = logging.getLogger(__name__)


def _fan_out(state: ScoreState) -> dict:
    logger.info(
        "Score graph: fan-out for profile=%s, %d candidates",
        state["profile_id"],
        len(state["candidate_job_ids"]),
    )
    return {}


def _collect(state: ScoreState) -> dict:
    logger.info(
        "Score graph: collected %d verdicts, %d failures",
        len(state["verdicts"]),
        len(state["failed_job_ids"]),
    )
    return {}


def build_score_graph(checkpointer=None) -> Any:
    """Build and compile the scoring StateGraph.

    Args:
        checkpointer: LangGraph checkpointer instance. Defaults to MemorySaver
            (testable offline). Pass PostgresSaver for production checkpointing.
    """
    builder = StateGraph(ScoreState)
    builder.add_node("fan_out", _fan_out)
    builder.add_node("collect", _collect)
    builder.set_entry_point("fan_out")
    builder.add_edge("fan_out", "collect")
    builder.add_edge("collect", END)
    cp = checkpointer if checkpointer is not None else MemorySaver()
    return builder.compile(checkpointer=cp)
