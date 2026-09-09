from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from src.domain.ports.pitch_tailorer import PitchTailorer
from src.domain.ports.skill_gap_analyzer import SkillGapAnalyzer
from src.infrastructure.orchestration.langgraph.states import PostulationState

logger = logging.getLogger(__name__)


def build_postulation_graph(
    *,
    skill_gap_analyzer: SkillGapAnalyzer,
    pitch_tailorer: PitchTailorer,
    checkpointer=None,
) -> Any:
    """Grafo del squad de postulación: Skill Gap Analyst -> Resume & Pitch Tailorer.

    Corre on-demand y síncrono de punta a punta (ver [[gating-costo-squad-postulacion]]
    y [[aprobacion-humana-postulacion]] en la LLM Wiki). Sin `interrupt`/resume: no
    hay nada que reanudar tras la aprobación (un `PATCH`/`POST` normal cambia el
    `status`), así que a diferencia de `score_graph.py`/`chat_graph.py` este grafo
    **no** compila con `MemorySaver()` por defecto — el estado incluye entidades de
    dominio (`Job` con `HttpUrl`) que el serializer msgpack de los checkpointers de
    LangGraph no sabe serializar, y no hay ningún caso de uso real (resume /
    time-travel) que justifique pagar ese costo. `checkpointer` queda como parámetro
    para poder inyectar uno explícito si tests u otro caller lo necesitaran.
    """

    def _skill_gap_analyst(state: PostulationState) -> dict:
        report = skill_gap_analyzer.analyze(state["profile"], state["job"])
        logger.info(
            "Postulation graph: skill gap analizado para job=%s (confidence=%.2f)",
            state["job"].id, report.confidence,
        )
        return {"skill_gap": report}

    def _resume_pitch_tailorer(state: PostulationState) -> dict:
        skill_gap = state["skill_gap"]
        assert skill_gap is not None, "skill_gap_analyst debe correr antes"
        bullets, cover_letter = pitch_tailorer.tailor(state["profile"], state["job"], skill_gap)
        logger.info(
            "Postulation graph: pitch redactado para job=%s (%d bullets)",
            state["job"].id, len(bullets),
        )
        return {"resume_bullets": bullets, "cover_letter": cover_letter}

    builder = StateGraph(PostulationState)
    builder.add_node("skill_gap_analyst", _skill_gap_analyst)
    builder.add_node("resume_pitch_tailorer", _resume_pitch_tailorer)
    builder.set_entry_point("skill_gap_analyst")
    builder.add_edge("skill_gap_analyst", "resume_pitch_tailorer")
    builder.add_edge("resume_pitch_tailorer", END)

    return builder.compile(checkpointer=checkpointer)
