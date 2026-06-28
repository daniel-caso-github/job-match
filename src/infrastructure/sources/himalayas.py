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

logger = logging.getLogger(__name__)

HIMALAYAS_URL = "https://himalayas.app/jobs/api"


_RETRYABLE_HTTP_EXC = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


class HimalayasSource(JobSource):
    name = "himalayas"

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    def fetch(
        self,
        *,
        keywords: str = "python",
        seniority: str | None = None,
        country: str | None = None,
        limit: int = 100,
        max_pages: int = 3,
    ) -> Iterable[RawJob]:
        offset = 0
        for _ in range(max_pages):
            params: dict[str, Any] = {
                "limit": limit,
                "offset": offset,
                "keywords": keywords,
            }
            if seniority:
                params["seniority"] = seniority
            if country:
                params["country"] = country

            try:
                payload = self._get_json(params)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Himalayas fetch failed at offset=%s: %s", offset, exc)
                return

            jobs = payload.get("jobs") or []
            if not jobs:
                return

            for j in jobs:
                try:
                    yield self._to_raw_job(j)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Skipping Himalayas entry: %s", exc)

            offset += limit
            if len(jobs) < limit:
                return

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE_HTTP_EXC + (httpx.HTTPStatusError,)),
        reraise=True,
    )
    def _get_json(self, params: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.get(HIMALAYAS_URL, params=params)
        if resp.status_code == 429 or resp.status_code >= 500:
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()

    def _to_raw_job(self, j: dict[str, Any]) -> RawJob:
        url = j.get("applicationLink") or j.get("jobSiteUrl") or j.get("url") or ""
        raw_html = j.get("description") or ""
        text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)

        published = j.get("publishedAt") or j.get("createdAt")
        posted_at: datetime | None = None
        if published:
            try:
                posted_at = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
            except ValueError:
                posted_at = None

        countries = j.get("locationRestrictions") or j.get("countries") or []
        country = countries[0] if countries else None

        return RawJob(
            id=make_id(self.name, url),
            source=self.name,
            url=url,
            title=j["title"],
            company=j.get("companyName"),
            raw_text=text,
            posted_at=posted_at,
            country=country,
            remote=True,
        )
