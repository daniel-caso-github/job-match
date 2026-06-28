"""CLI: ejecuta ExtractJobRequirementsUseCase sobre las ofertas pendientes.

Usage:
    python -m src.interfaces.cli.extract --limit 5

Requiere `GEMINI_API_KEY` en .env y al menos algunas ofertas ya recolectadas
sin requirements (usar `python -m src.interfaces.cli.collect` antes).
"""
from __future__ import annotations

import argparse
import json
import sys

from src.application.use_cases.extract_job_requirements import (
    ExtractJobRequirementsUseCase,
)
from src.infrastructure.llm.gemini_extractor import GeminiExtractor
from src.infrastructure.persistence.database import session_scope
from src.infrastructure.persistence.sqlalchemy_job_repository import (
    SqlAlchemyJobRepository,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--print-results",
        action="store_true",
        help="después de extraer, imprime job + requirements de las afectadas",
    )
    args = parser.parse_args()

    extractor = GeminiExtractor()

    with session_scope() as session:
        repo = SqlAlchemyJobRepository(session)
        use_case = ExtractJobRequirementsUseCase(extractor=extractor, job_repository=repo)
        n = use_case.execute(limit=args.limit)

    print(f"extracted requirements for {n} jobs", file=sys.stderr)

    if args.print_results and n > 0:
        _print_recent_results(n)


def _print_recent_results(n: int) -> None:
    from sqlalchemy import select

    from src.infrastructure.persistence.orm_models import JobModel

    with session_scope() as session:
        stmt = (
            select(JobModel)
            .where(JobModel.requirements.is_not(None))
            .order_by(JobModel.fetched_at.desc())
            .limit(n)
        )
        for model in session.scalars(stmt):
            print(
                json.dumps(
                    {
                        "title": model.title,
                        "company": model.company,
                        "url": model.url,
                        "requirements": model.requirements,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )


if __name__ == "__main__":
    main()
