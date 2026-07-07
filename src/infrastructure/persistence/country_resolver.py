from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.domain.ports.country_resolver import CountryResolver
from src.infrastructure.persistence.orm_models import CountryModel


class SqlAlchemyCountryResolver(CountryResolver):
    """Resuelve strings de país crudos a country_id usando la tabla countries normalizada.

    Estrategias (en orden):
    1. ISO-2 exacto (2 letras mayúsculas).
    2. Nombre de país (case-insensitive).
    3. Patrón "Ciudad, País" — toma la última parte tras la última coma.

    Si ninguna estrategia coincide, retorna None (no inserta basura en countries).
    Cachea resultados por sesión para evitar queries repetidos.
    """

    def __init__(self, session: Session):
        self._session = session
        self._cache: dict[str, int | None] = {}

    def resolve(self, raw: str | None) -> int | None:
        if not raw:
            return None
        normalized = raw.strip()
        if not normalized:
            return None
        if normalized in self._cache:
            return self._cache[normalized]
        result = self._lookup(normalized)
        self._cache[normalized] = result
        return result

    def _lookup(self, raw: str) -> int | None:
        # 1. ISO-2 exacto
        if len(raw) == 2 and raw.isupper():
            row = self._session.execute(
                select(CountryModel.id).where(CountryModel.iso2 == raw)
            ).scalar_one_or_none()
            if row is not None:
                return row

        # 2. Nombre exacto (case-insensitive)
        row = self._session.execute(
            select(CountryModel.id).where(func.lower(CountryModel.name) == raw.lower())
        ).scalar_one_or_none()
        if row is not None:
            return row

        # 3. "Ciudad, País" — toma la última parte
        if "," in raw:
            country_part = raw.rsplit(",", 1)[-1].strip()
            if country_part:
                if len(country_part) == 2 and country_part.isupper():
                    row = self._session.execute(
                        select(CountryModel.id).where(CountryModel.iso2 == country_part)
                    ).scalar_one_or_none()
                    if row is not None:
                        return row
                row = self._session.execute(
                    select(CountryModel.id).where(
                        func.lower(CountryModel.name) == country_part.lower()
                    )
                ).scalar_one_or_none()
                if row is not None:
                    return row

        return None
