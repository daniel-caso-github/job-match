"""CLI: scorea un perfil contra el corpus actual de ofertas.

Usage:
    python -m src.interfaces.cli.score --profile-file path/to/profile.json [--top-k N]

Lee el JSON del perfil (validado contra `ProfileForm`), upsertea el perfil + su
embedding, y corre `ScoreProfileUseCase`. Idempotente: re-ejecutar no duplica
matches (gracias al filtro `exclude_scored_for` del repo).

Requiere `.env` con `GEMINI_API_KEY` y al menos algunas ofertas con embedding
(usar `python -m src.interfaces.cli.embed` antes).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.application.use_cases.score_profile import ScoreProfileUseCase
from src.domain.value_objects.profile_form import ProfileForm
from src.infrastructure.embedding.sentence_transformers_embedder import (
    SentenceTransformersEmbedder,
)
from src.infrastructure.llm.gemini_scorer import GeminiScorer
from src.infrastructure.persistence.database import session_scope
from src.infrastructure.persistence.sqlalchemy_job_repository import (
    SqlAlchemyJobRepository,
)
from src.infrastructure.persistence.sqlalchemy_match_repository import (
    SqlAlchemyMatchRepository,
)
from src.infrastructure.persistence.sqlalchemy_profile_repository import (
    SqlAlchemyProfileRepository,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile-file",
        type=Path,
        required=True,
        help="ruta a un JSON con el perfil (schema: ProfileForm).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="top-K semántico que pasa al LLM (default: settings.top_k_for_llm=30).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="similitud mínima (default: settings.semantic_threshold=0.65).",
    )
    parser.add_argument(
        "--print-top",
        type=int,
        default=0,
        help="después de scorear, imprime los N mejores matches por llm_score.",
    )
    args = parser.parse_args()

    form = ProfileForm.model_validate(json.loads(args.profile_file.read_text()))
    embedder = SentenceTransformersEmbedder()
    scorer = GeminiScorer()

    with session_scope() as session:
        profile_repo = SqlAlchemyProfileRepository(session)
        job_repo = SqlAlchemyJobRepository(session)
        match_repo = SqlAlchemyMatchRepository(session)
        use_case = ScoreProfileUseCase(
            embedder=embedder,
            llm_scorer=scorer,
            profile_repository=profile_repo,
            job_repository=job_repo,
            match_repository=match_repo,
        )
        n = use_case.execute(form, top_k=args.top_k, threshold=args.threshold)

    print(f"scored {n} matches for profile {form.id!r}", file=sys.stderr)

    if args.print_top > 0:
        _print_top(form.id, args.print_top)


def _print_top(profile_id: str, n: int) -> None:
    with session_scope() as session:
        repo = SqlAlchemyMatchRepository(session)
        rows = repo.top_for_profile(profile_id, limit=n)

    for match, job in rows:
        print(
            json.dumps(
                {
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "url": str(job.url),
                    "llm_score": match.llm_score,
                    "semantic_score": (
                        round(match.semantic_score, 3)
                        if match.semantic_score is not None
                        else None
                    ),
                    "verdict": match.verdict,
                },
                indent=2,
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
