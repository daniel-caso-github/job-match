from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.interfaces.api.dependencies import (
    CurrentProfileDep,
    JobRepositoryDep,
    MatchRepositoryDep,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatSource(BaseModel):
    job_id: str
    title: str
    url: str
    company: str | None = None


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    sources: list[ChatSource] = []


@router.post("", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    current: CurrentProfileDep,
    job_repo: JobRepositoryDep,
    match_repo: MatchRepositoryDep,
) -> ChatResponse:
    """Chat conversacional sobre las ofertas y matches del usuario autenticado.

    El agente es read-only: solo consulta ofertas y matches del perfil autenticado.
    """
    from src.infrastructure.config import settings

    thread_id = req.thread_id or str(uuid.uuid4())

    try:
        from google import genai as genai_client
        from langchain_core.messages import HumanMessage

        from src.infrastructure.orchestration.langgraph.chat_graph import build_chat_graph

        if not settings.gemini_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chat no disponible: GEMINI_API_KEY no configurada.",
            )

        client = genai_client.Client(api_key=settings.gemini_api_key)
        graph = build_chat_graph(
            job_repo=job_repo,
            match_repo=match_repo,
            gemini_client=client,
            model=settings.gemini_model_score,
        )

        state = {
            "profile_id": current.profile_id,
            "messages": [HumanMessage(content=req.message)],
            "cited_job_ids": [],
        }
        config = {"configurable": {"thread_id": f"{current.profile_id}:{thread_id}"}}
        result = graph.invoke(state, config=config)

        messages = result.get("messages", [])
        answer = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and getattr(msg, "type", "") in ("ai", "assistant"):
                answer = msg.content
                break

        if not answer:
            answer = "No pude generar una respuesta. Intenta reformular tu pregunta."

        return ChatResponse(thread_id=thread_id, answer=answer, sources=[])

    except HTTPException:
        raise
    except ImportError as exc:
        logger.error("LangGraph/langchain-core no disponible: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat no disponible: dependencias no instaladas. Ejecutar docker compose build.",
        ) from exc
    except Exception as exc:
        logger.error("Chat error for profile=%s: %s", current.profile_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno en el chat.",
        ) from exc
