from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC, datetime
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

logger = logging.getLogger(__name__)

# Docs: https://www.arbeitnow.com/api/job-board-api (public, no key required)
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"

_RETRYABLE_HTTP_EXC = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


class ArbeitnowSource(JobSource):
    name = "arbeitnow"

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    def fetch(self, *, max_pages: int = 2) -> Iterable[RawJob]:
        for page in range(1, max_pages + 1):
            try:
                payload = self._get_json({"page": page})
            except Exception as exc:  # noqa: BLE001
                logger.warning("Arbeitnow fetch failed at page=%s: %s", page, exc)
                return

            jobs = payload.get("data") or []
            if not jobs:
                return

            for j in jobs:
                try:
                    yield self._to_raw_job(j)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Skipping Arbeitnow entry: %s", exc)

            links = payload.get("links") or {}
            if not links.get("next"):
                return

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE_HTTP_EXC + (httpx.HTTPStatusError,)),
        reraise=True,
    )
    def _get_json(self, params: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.get(ARBEITNOW_URL, params=params)
        if resp.status_code == 429 or resp.status_code >= 500:
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()

    def _to_raw_job(self, j: dict[str, Any]) -> RawJob:
        url = j["url"]
        raw_html = j.get("description") or ""
        text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)

        posted_at: datetime | None = None
        ts = j.get("created_at")
        if ts is not None:
            try:
                posted_at = datetime.fromtimestamp(int(ts), tz=UTC)
            except (ValueError, OSError, TypeError):
                posted_at = None

        remote_flag = j.get("remote")
        remote: bool | None = bool(remote_flag) if remote_flag is not None else None

        return RawJob(
            id=make_id(self.name, url),
            source=self.name,
            url=url,
            title=j["title"],
            company=j.get("company_name") or None,
            raw_text=text,
            posted_at=posted_at,
            country=j.get("location") or None,
            remote=remote,
        )
