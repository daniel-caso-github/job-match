from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, HttpUrl

from src.domain.value_objects.job_requirements import JobRequirements


class Job(BaseModel):
    """Oferta persistida con su estado completo (post-extracción y post-embedding).

    Salida de `JobRepository.get(...)` y `list_*`. Combina lo que vino de la
    fuente (`RawJob`) más los enriquecimientos del pipeline.
    """

    id: str
    source: str
    url: HttpUrl
    title: str
    company: str | None = None
    raw_text: str
    posted_at: datetime | None = None
    country: str | None = None
    remote: bool | None = None
    requirements: JobRequirements | None = None
    embedding: list[float] | None = None
    fetched_at: datetime | None = None
