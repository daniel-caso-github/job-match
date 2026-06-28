from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from src.domain.entities.raw_job import RawJob


class JobSource(ABC):
    """Port: contrato común para toda fuente de ofertas (Himalayas, Remotive, ...).

    Las implementaciones viven en `src/infrastructure/sources/`.
    """

    name: str

    @abstractmethod
    def fetch(self, **filters) -> Iterable[RawJob]:
        """Devuelve un iterable lazy de ofertas ya normalizadas a `RawJob`."""
