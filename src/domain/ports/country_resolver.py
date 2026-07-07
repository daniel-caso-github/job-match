from __future__ import annotations

from abc import ABC, abstractmethod


class CountryResolver(ABC):
    @abstractmethod
    def resolve(self, raw: str | None) -> int | None:
        """Mapea un string de país/ciudad crudo a un country_id normalizado.

        Retorna None si no puede identificar el país (strings de región,
        "Worldwide", o valores desconocidos).
        """
