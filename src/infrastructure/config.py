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
    embedding_model: str
    semantic_threshold: float
    top_k_for_llm: int
    adzuna_app_id: str | None
    adzuna_app_key: str | None
    adzuna_country: str
    jooble_api_key: str | None
    airflow_api_url: str
    airflow_api_user: str
    airflow_api_password: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=os.environ.get(
                "DATABASE_URL", "postgresql+psycopg://app:app@app-db:5432/jobmatch"
            ),
            gemini_api_key=os.environ.get("GEMINI_API_KEY"),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            gemini_max_input_chars=int(os.environ.get("GEMINI_MAX_INPUT_CHARS", "12000")),
            embedding_model=os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
            semantic_threshold=float(os.environ.get("SEMANTIC_THRESHOLD", "0.65")),
            top_k_for_llm=int(os.environ.get("TOP_K_FOR_LLM", "30")),
            adzuna_app_id=os.environ.get("ADZUNA_APP_ID"),
            adzuna_app_key=os.environ.get("ADZUNA_APP_KEY"),
            adzuna_country=os.environ.get("ADZUNA_COUNTRY", "gb"),
            jooble_api_key=os.environ.get("JOOBLE_API_KEY"),
            airflow_api_url=os.environ.get(
                "AIRFLOW_API_URL", "http://airflow-webserver:8080"
            ),
            airflow_api_user=os.environ.get("AIRFLOW_API_USER", "admin"),
            airflow_api_password=os.environ.get("AIRFLOW_API_PASSWORD", "admin"),
            jwt_secret=os.environ.get("JWT_SECRET", "dev-secret-change-in-production-32b"),
            jwt_algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(
                os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
            ),
        )


settings = Settings.from_env()
