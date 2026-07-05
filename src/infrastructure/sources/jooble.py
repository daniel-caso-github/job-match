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

# Key (free): request at jooble.org → email → JOOBLE_API_KEY
JOOBLE_BASE_URL = "https://jooble.org/api/{key}"

_RETRYABLE_HTTP_EXC = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


class JoobleSource(JobSource):
    name = "jooble"

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)
        self._api_key = settings.jooble_api_key

    def fetch(
        self,
        *,
        keywords: str = "python developer",
        location: str = "",
        max_pages: int = 1,
    ) -> Iterable[RawJob]:
        if not self._api_key:
            logger.warning("Jooble: JOOBLE_API_KEY not set — skipping")
            return

        url = JOOBLE_BASE_URL.format(key=self._api_key)

        for page in range(1, max_pages + 1):
            body: dict[str, Any] = {"keywords": keywords, "location": location, "page": page}

            try:
                payload = self._post_json(url, body)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Jooble fetch failed at page=%s: %s", page, exc)
                return

            jobs = payload.get("jobs") or []
            if not jobs:
                return

            for j in jobs:
                try:
                    yield self._to_raw_job(j)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Skipping Jooble entry: %s", exc)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE_HTTP_EXC + (httpx.HTTPStatusError,)),
        reraise=True,
    )
    def _post_json(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.post(url, json=body)
        if resp.status_code == 429 or resp.status_code >= 500:
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()

    def _to_raw_job(self, j: dict[str, Any]) -> RawJob:
        url = j["link"]
        raw_html = j.get("snippet") or ""
        text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)

        posted_at: datetime | None = None
        updated = j.get("updated")
        if updated:
            try:
                posted_at = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
            except ValueError:
                posted_at = None

        return RawJob(
            id=make_id(self.name, url),
            source=self.name,
            url=url,
            title=j["title"],
            company=j.get("company") or None,
            raw_text=text,
            posted_at=posted_at,
            country=j.get("location") or None,
            remote=None,
        )
