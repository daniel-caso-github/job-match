from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class RawJob(BaseModel):
    """Oferta normalizada al esquema común. Salida de toda fuente."""

    id: str = Field(description="hash(source + url), idempotente")
    source: str = Field(description="'himalayas' | 'remotive' | ...")
    url: HttpUrl = Field(description="enlace a la oferta original (requisito legal)")
    title: str
    company: str | None = None
    raw_text: str = Field(description="descripción completa, sin HTML")
    posted_at: datetime | None = None
    country: str | None = None
    remote: bool | None = None


def make_id(source: str, url: str) -> str:
    """Hash determinista para idempotencia.

    SHA-1 truncado a 16 hex chars: colisiones despreciables a escala del proyecto
    y queda legible en logs.
    """
    return hashlib.sha1(f"{source}|{url}".encode()).hexdigest()[:16]


class Source(ABC):
    """Contrato común. Una implementación por fuente."""

    name: str

    @abstractmethod
    def fetch(self, **filters) -> Iterable[RawJob]: ...
