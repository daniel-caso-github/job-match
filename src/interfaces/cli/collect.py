"""CLI: ejecuta CollectJobsUseCase contra fuentes reales.

Usage:
    python -m src.interfaces.cli.collect --source himalayas --limit 3
    python -m src.interfaces.cli.collect --source remotive --limit 3
    python -m src.interfaces.cli.collect --source all
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from src.application.use_cases.collect_jobs import CollectJobsUseCase
from src.domain.ports.job_source import JobSource
from src.infrastructure.persistence.database import session_scope
from src.infrastructure.persistence.sqlalchemy_job_repository import (
    SqlAlchemyJobRepository,
)
from src.infrastructure.sources.himalayas import HimalayasSource
from src.infrastructure.sources.remotive import RemotiveSource

SOURCE_REGISTRY: dict[str, type[JobSource]] = {
    "himalayas": HimalayasSource,
    "remotive": RemotiveSource,
}


class _CappedJobSource(JobSource):
    """Wrapper que limita N items para que el smoke no agote la API entera."""

    def __init__(self, inner: JobSource, limit: int):
        self.name = inner.name
        self._inner = inner
        self._limit = limit

    def fetch(self, **filters: Any):
        for i, job in enumerate(self._inner.fetch(**filters)):
            if i >= self._limit:
                break
            yield job


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=[*SOURCE_REGISTRY.keys(), "all"],
        default="all",
    )
    parser.add_argument("--limit", type=int, default=3, help="máx de items por fuente")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="solo imprime ofertas sin escribir a BD",
    )
    args = parser.parse_args()

    if args.source == "all":
        sources: list[JobSource] = [cls() for cls in SOURCE_REGISTRY.values()]
    else:
        sources = [SOURCE_REGISTRY[args.source]()]

    capped = [_CappedJobSource(s, args.limit) for s in sources]

    if args.dry_run:
        for s in capped:
            for raw_job in s.fetch():
                print(json.dumps(raw_job.model_dump(mode="json"), indent=2, ensure_ascii=False))
        return

    with session_scope() as session:
        repo = SqlAlchemyJobRepository(session)
        use_case = CollectJobsUseCase(sources=capped, job_repository=repo)
        n = use_case.execute()
    print(f"upserted {n} jobs", file=sys.stderr)


if __name__ == "__main__":
    main()
