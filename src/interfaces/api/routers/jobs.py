from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.domain.entities.saved_search import SavedSearch
from src.domain.value_objects.match_filters import MatchFilters
from src.interfaces.api.dependencies import (
    AirflowClientDep,
    CurrentProfileDep,
    InternalKeyDep,
    JobRepositoryDep,
    MatchRepositoryDep,
    SavedSearchRepositoryDep,
    SessionDep,
)
from src.interfaces.pipeline import run_collect, run_embed, run_extract, run_score_all_profiles

PIPELINE_DAG_ID = "job_match"


class ScheduleRunRequest(BaseModel):
    filters: MatchFilters = Field(default_factory=MatchFilters)

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
def refresh(bg: BackgroundTasks, airflow: AirflowClientDep) -> dict:
    try:
        dag_run_id = airflow.trigger_dag(PIPELINE_DAG_ID)
        logger.info("Refresh: DAG %s disparado (%s)", PIPELINE_DAG_ID, dag_run_id)
        return {"status": "scheduled", "runner": "airflow", "dag_run_id": dag_run_id}
    except Exception:
        logger.warning(
            "Refresh: Airflow no disponible, ejecutando pipeline inline", exc_info=True
        )
        bg.add_task(_run_refresh)
        return {"status": "scheduled", "runner": "inline"}


@router.post("/schedule-run", status_code=status.HTTP_202_ACCEPTED)
def schedule_run(
    request: ScheduleRunRequest,
    airflow: AirflowClientDep,
    searches: SavedSearchRepositoryDep,
    session: SessionDep,
    current: CurrentProfileDep,
    delay_hours: Annotated[int, Query(ge=1, le=48)] = 12,
) -> dict:
    run_at = datetime.now(UTC) + timedelta(hours=delay_hours)
    try:
        dag_run_id = airflow.trigger_dag(
            PIPELINE_DAG_ID,
            conf={"scheduled_by": "search"},
            logical_date=run_at.isoformat(),
        )
    except Exception as exc:
        logger.warning("Schedule-run: Airflow no disponible", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Airflow no disponible — no se pudo registrar la programación",
        ) from exc

    searches.add(
        SavedSearch(
            dag_run_id=dag_run_id,
            profile_id=current.profile_id,
            filters=request.filters.model_dump(mode="json", exclude_defaults=True),
            run_at=run_at,
        )
    )
    session.commit()
    logger.info(
        "Schedule-run: DAG %s programado para %s (%s) por %s",
        PIPELINE_DAG_ID,
        run_at.isoformat(),
        dag_run_id,
        current.profile_id,
    )
    return {"status": "scheduled", "dag_run_id": dag_run_id, "run_at": run_at.isoformat()}


@router.get("/searches")
def searches(
    repo: SavedSearchRepositoryDep,
    current: CurrentProfileDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    return {
        "searches": [
            s.model_dump(mode="json")
            for s in repo.list_for_profile(current.profile_id, limit=limit)
        ]
    }


@router.get("/technologies")
def technologies(
    repo: JobRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> dict:
    return {"technologies": repo.list_stack_technologies(limit=limit)}


@router.get("/countries")
def countries_list(
    repo: JobRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> dict:
    return {"countries": repo.list_countries(limit=limit)}


@router.get("/schedule")
def schedule(airflow: AirflowClientDep) -> dict:
    try:
        dag = airflow.get_dag(PIPELINE_DAG_ID)
        return {
            "schedule": dag.get("schedule_interval", {}).get("value"),
            "next_run": dag.get("next_dagrun_data_interval_end") or dag.get("next_dagrun"),
            "is_paused": dag.get("is_paused", False),
        }
    except Exception:
        logger.warning("Schedule: Airflow no disponible", exc_info=True)
        return {"schedule": None, "next_run": None, "is_paused": None}


@router.get("/runs")
def runs(
    airflow: AirflowClientDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 4,
    include_tasks: bool = True,
) -> dict:
    try:
        dag_runs = airflow.list_dag_runs(PIPELINE_DAG_ID, limit=limit)
    except Exception:
        logger.warning("Runs: Airflow no disponible", exc_info=True)
        return {"runs": []}

    out = []
    for run in dag_runs:
        tasks: list[dict] = []
        if include_tasks:
            try:
                tasks = airflow.list_task_instances(PIPELINE_DAG_ID, run["dag_run_id"])
            except Exception:
                logger.warning(
                    "Runs: no se pudieron leer las tasks de %s",
                    run["dag_run_id"],
                    exc_info=True,
                )
        out.append(
            {
                "dag_run_id": run["dag_run_id"],
                "state": run.get("state"),
                "run_type": run.get("run_type"),
                "logical_date": run.get("logical_date") or run.get("execution_date"),
                "start_date": run.get("start_date"),
                "end_date": run.get("end_date"),
                "tasks": sorted(
                    (
                        {
                            "task_id": t["task_id"],
                            "state": t.get("state"),
                            "start_date": t.get("start_date"),
                            "end_date": t.get("end_date"),
                            "duration": t.get("duration"),
                        }
                        for t in tasks
                    ),
                    key=lambda t: t["start_date"] or "9999",
                ),
            }
        )
    return {"runs": out}


@router.post("/collect", status_code=status.HTTP_200_OK)
def collect(_: InternalKeyDep) -> dict:
    n = run_collect()
    logger.info("collect: %d jobs", n)
    return {"collected": n}


@router.post("/extract", status_code=status.HTTP_200_OK)
def extract(_: InternalKeyDep, limit: Annotated[int, Query(ge=1, le=500)] = 200) -> dict:
    n = run_extract(limit=limit)
    logger.info("extract: %d jobs", n)
    return {"extracted": n}


@router.post("/embed", status_code=status.HTTP_200_OK)
def embed(_: InternalKeyDep, limit: Annotated[int, Query(ge=1, le=500)] = 200) -> dict:
    n = run_embed(limit=limit)
    logger.info("embed: %d jobs", n)
    return {"embedded": n}


@router.post("/score", status_code=status.HTTP_200_OK)
def score(_: InternalKeyDep) -> dict:
    scores = run_score_all_profiles()
    logger.info("score: %s", scores)
    return {"scored": scores}


@router.delete("/searches/{dag_run_id}", status_code=status.HTTP_200_OK)
def cancel_search(
    dag_run_id: str,
    airflow: AirflowClientDep,
    searches: SavedSearchRepositoryDep,
    session: SessionDep,
    current: CurrentProfileDep,
) -> dict:
    search = searches.get_by_dag_run_id(dag_run_id)
    if search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="programación no encontrada")
    if search.profile_id != current.profile_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="acceso denegado")
    try:
        airflow.delete_dag_run(PIPELINE_DAG_ID, dag_run_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Airflow no disponible — no se pudo cancelar",
        ) from exc
    searches.delete(dag_run_id)
    session.commit()
    logger.info("cancel-search: búsqueda %s cancelada por %s", dag_run_id, current.profile_id)
    return {"status": "cancelled", "dag_run_id": dag_run_id}


@router.post("/searches/{dag_run_id}/match-count", status_code=status.HTTP_200_OK)
def record_match_count(
    dag_run_id: str,
    _: InternalKeyDep,
    searches: SavedSearchRepositoryDep,
    matches: MatchRepositoryDep,
    session: SessionDep,
) -> dict:
    search = searches.get_by_dag_run_id(dag_run_id)
    if search is None:
        return {"updated": 0}
    count = matches.count_for_profile(
        search.profile_id, MatchFilters(**search.filters)
    )
    searches.set_match_count(dag_run_id, count)
    session.commit()
    logger.info("match-count: %d resultados para búsqueda %s", count, dag_run_id)
    return {"updated": 1, "match_count": count}
