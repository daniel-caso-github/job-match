from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Configuración runtime leída del entorno.

    Single source of truth para variables de entorno. Los componentes de
    infrastructure (Gemini extractor, database, ...) leen de aquí en vez de
    hacer `os.environ[...]` directo, así los tests pueden inyectar overrides.
    """

    database_url: str
    gemini_api_key: str | None
    gemini_model: str
    gemini_max_input_chars: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=os.environ.get(
                "DATABASE_URL", "postgresql+psycopg://app:app@app-db:5432/jobmatch"
            ),
            gemini_api_key=os.environ.get("GEMINI_API_KEY"),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            gemini_max_input_chars=int(os.environ.get("GEMINI_MAX_INPUT_CHARS", "12000")),
        )


settings = Settings.from_env()
