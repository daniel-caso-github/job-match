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

# Docs: https://jobi.cy/apidocs
# Terms: credit Jobicy with a direct link + redirect to original job URL.
JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"

_RETRYABLE_HTTP_EXC = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


class JobicySource(JobSource):
    name = "jobicy"

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    def fetch(
        self,
        *,
        count: int = 50,
        industry: str = "dev",
        geo: str | None = None,
        tag: str | None = None,
    ) -> Iterable[RawJob]:
        params: dict[str, Any] = {"count": count, "industry": industry}
        if geo:
            params["geo"] = geo
        if tag:
            params["tag"] = tag

        try:
            payload = self._get_json(params)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Jobicy fetch failed: %s", exc)
            return

        for j in payload.get("jobs") or []:
            try:
                yield self._to_raw_job(j)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping Jobicy entry: %s", exc)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE_HTTP_EXC + (httpx.HTTPStatusError,)),
        reraise=True,
    )
    def _get_json(self, params: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.get(JOBICY_URL, params=params)
        if resp.status_code == 429 or resp.status_code >= 500:
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()

    def _to_raw_job(self, j: dict[str, Any]) -> RawJob:
        url = j["url"]
        raw_html = j.get("jobDescription") or ""
        text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)
        excerpt = j.get("jobExcerpt") or ""
        if excerpt and len(text) < 200:
            text = f"{excerpt} {text}".strip()

        posted_at: datetime | None = None
        pub = j.get("pubDate")
        if pub:
            try:
                posted_at = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
            except ValueError:
                posted_at = None

        return RawJob(
            id=make_id(self.name, url),
            source=self.name,
            url=url,
            title=j["jobTitle"],
            company=j.get("companyName") or None,
            raw_text=text,
            posted_at=posted_at,
            country=j.get("jobGeo") or None,
            remote=True,
        )
