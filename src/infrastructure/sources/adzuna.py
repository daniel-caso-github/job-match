from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.domain.entities.raw_job import RawJob
from src.domain.ports.job_source import JobSource
from src.domain.services.id_hasher import make_id
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)

# Docs: https://developer.adzuna.com/
# Key (free): register at developer.adzuna.com → ADZUNA_APP_ID + ADZUNA_APP_KEY
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

_RETRYABLE_HTTP_EXC = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


class AdzunaSource(JobSource):
    name = "adzuna"

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)
        self._app_id = settings.adzuna_app_id
        self._app_key = settings.adzuna_app_key
        self._country = settings.adzuna_country

    def fetch(
        self,
        *,
        what: str = "python developer",
        max_pages: int = 1,
        results_per_page: int = 50,
        max_days_old: int = 30,
    ) -> Iterable[RawJob]:
        if not self._app_id or not self._app_key:
            logger.warning("Adzuna: ADZUNA_APP_ID / ADZUNA_APP_KEY not set — skipping")
            return

        for page in range(1, max_pages + 1):
            url = ADZUNA_BASE_URL.format(country=self._country, page=page)
            params: dict[str, Any] = {
                "app_id": self._app_id,
                "app_key": self._app_key,
                "results_per_page": results_per_page,
                "what": what,
                "max_days_old": max_days_old,
                "content-type": "application/json",
            }

            try:
                payload = self._get_json(url, params)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Adzuna fetch failed at page=%s: %s", page, exc)
                return

            results = payload.get("results") or []
            if not results:
                return

            for j in results:
                try:
                    yield self._to_raw_job(j)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Skipping Adzuna entry: %s", exc)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE_HTTP_EXC + (httpx.HTTPStatusError,)),
        reraise=True,
    )
    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.get(url, params=params)
        if resp.status_code == 429 or resp.status_code >= 500:
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()

    def _to_raw_job(self, j: dict[str, Any]) -> RawJob:
        url = j["redirect_url"]
        raw_html = j.get("description") or ""
        text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)

        sal_min = j.get("salary_min")
        sal_max = j.get("salary_max")
        if sal_min or sal_max:
            text = f"{text} Salary: {sal_min or '?'}–{sal_max or '?'}".strip()

        posted_at: datetime | None = None
        created = j.get("created")
        if created:
            try:
                posted_at = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
            except ValueError:
                posted_at = None

        company = (j.get("company") or {}).get("display_name") or None
        location = (j.get("location") or {}).get("display_name") or None

        title = j.get("title", "")
        remote: bool | None = True if "remote" in (raw_html + title).lower() else None

        return RawJob(
            id=make_id(self.name, url),
            source=self.name,
            url=url,
            title=title,
            company=company,
            raw_text=text,
            posted_at=posted_at,
            country=location,
            remote=remote,
        )
