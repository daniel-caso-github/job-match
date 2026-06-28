"""CLI: ejecuta EmbedJobsUseCase sobre las ofertas sin embedding.

Usage:
    python -m src.interfaces.cli.embed --limit 32

Idempotente: solo procesa ofertas con `embedding IS NULL`. Re-correrlo no
duplica trabajo. Por convención del proyecto, conviene extraer requirements
(`python -m src.interfaces.cli.extract`) antes de embeber, así el texto del
embedding incluye el stack/seniority normalizados.
"""
from __future__ import annotations

import argparse
import sys

from src.application.use_cases.embed_jobs import EmbedJobsUseCase
from src.infrastructure.embedding.sentence_transformers_embedder import (
    SentenceTransformersEmbedder,
)
from src.infrastructure.persistence.database import session_scope
from src.infrastructure.persistence.sqlalchemy_job_repository import (
    SqlAlchemyJobRepository,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=32)
    args = parser.parse_args()

    embedder = SentenceTransformersEmbedder()

    with session_scope() as session:
        repo = SqlAlchemyJobRepository(session)
        use_case = EmbedJobsUseCase(embedder=embedder, job_repository=repo)
        n = use_case.execute(limit=args.limit)

    print(f"embedded {n} jobs", file=sys.stderr)


if __name__ == "__main__":
    main()
