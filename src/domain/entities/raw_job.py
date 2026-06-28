from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class RawJob(BaseModel):
    """Oferta tal como sale de una fuente externa (sin requirements ni embedding).

    Es la unidad de input al pipeline: lo que produce un `JobSource` y consume
    el `JobRepository.upsert(...)`.
    """

    id: str = Field(description="hash(source + url), idempotente")
    source: str = Field(description="'himalayas' | 'remotive' | ...")
    url: HttpUrl = Field(description="enlace a la oferta original (requisito legal)")
    title: str
    company: str | None = None
    raw_text: str = Field(description="descripción completa, sin HTML")
    posted_at: datetime | None = None
    country: str | None = None
    remote: bool | None = None
