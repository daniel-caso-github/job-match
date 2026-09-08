from __future__ import annotations

import json
import logging
from typing import Any

from google.genai import types
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.infrastructure.orchestration.langgraph.states import ChatState

logger = logging.getLogger(__name__)


def build_chat_graph(
    *,
    job_repo,
    match_repo,
    gemini_client,
    model: str = "gemini-2.5-flash",
    checkpointer=None,
) -> Any:
    """Build the conversational chat agent graph.

    The agent answers questions about the user's job matches using two
    read-only query helpers exposed as closures (not LLM tool-calls yet):
    filter_jobs and get_match_detail. Tool-calling via genai function
    declarations is deferred to a future iteration.
    """

    def _filter_jobs(profile_id: str, min_score: int = 50, limit: int = 10) -> str:
        from src.domain.value_objects.match_filters import MatchFilters

        try:
            filters = MatchFilters(min_score=min_score)
            results = match_repo.top_for_profile(profile_id, limit=limit, filters=filters)
            items = [
                {
                    "job_id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "score": m.llm_score,
                    "url": j.url,
                }
                for m, j in results
            ]
            return json.dumps(items)
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def _get_match_detail(profile_id: str, job_id: str) -> str:
        try:
            result = match_repo.get_for_pair(profile_id, job_id)
            if result is None:
                return json.dumps({"error": "match not found"})
            m, j = result
            return json.dumps(
                {
                    "job_id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "url": j.url,
                    "llm_score": m.llm_score,
                    "verdict": m.verdict,
                }
            )
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    SYSTEM_PROMPT = (
        "You are a job-search assistant. You help the authenticated user understand "
        "their job matches. Always cite the job_id and original URL for every job you mention. "
        "If you don't find relevant jobs, say so — never make up job listings. "
        "Stay on topic: only discuss jobs, matches, and the user's profile/skills."
    )

    def call_model(state: ChatState) -> dict:
        profile_id = state["profile_id"]
        messages = state["messages"]

        context_data = _filter_jobs(profile_id, min_score=0, limit=5)
        system_instruction = (
            f"{SYSTEM_PROMPT}\nUser profile_id: {profile_id}\n"
            f"Top matches context (use as reference, do not hallucinate beyond this):\n"
            f"{context_data}"
        )

        contents = []
        for msg in messages:
            role = getattr(msg, "type", "user")
            content = getattr(msg, "content", str(msg))
            if role in ("human", "user"):
                contents.append(
                    types.Content(role="user", parts=[types.Part(text=content)])
                )
            elif role in ("ai", "assistant"):
                contents.append(
                    types.Content(role="model", parts=[types.Part(text=content)])
                )

        if not contents:
            contents = [types.Content(role="user", parts=[types.Part(text="hello")])]

        try:
            response = gemini_client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                    max_output_tokens=2048,
                ),
            )
            answer = response.text or ""
        except Exception as exc:
            logger.error("Chat model call failed: %s", exc)
            answer = "Lo siento, ocurrió un error al procesar tu consulta."

        from langchain_core.messages import AIMessage

        return {"messages": [AIMessage(content=answer)]}

    builder = StateGraph(ChatState)
    builder.add_node("agent", call_model)
    builder.set_entry_point("agent")
    builder.add_edge("agent", END)

    cp = checkpointer if checkpointer is not None else MemorySaver()
    return builder.compile(checkpointer=cp)
