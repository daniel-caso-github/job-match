from __future__ import annotations

import contextlib
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

# Docs: https://remoteok.com/api
# Terms: linkback with follow (no nofollow!) to remoteok.com + mention "Remote OK".
REMOTEOK_URL = "https://remoteok.com/api"

_RETRYABLE_HTTP_EXC = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


class RemoteOkSource(JobSource):
    name = "remoteok"

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "job-match-pipeline/1.0 (+contact)"},
        )

    def fetch(self, *, tags: str = "dev") -> Iterable[RawJob]:
        try:
            entries = self._get_json({"tags": tags})
        except Exception as exc:  # noqa: BLE001
            logger.warning("RemoteOK fetch failed: %s", exc)
            return

        for entry in entries:
            # First element is a legal-notice dict without "position"
            if not isinstance(entry, dict) or "position" not in entry:
                continue
            try:
                yield self._to_raw_job(entry)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping RemoteOK entry: %s", exc)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE_HTTP_EXC + (httpx.HTTPStatusError,)),
        reraise=True,
    )
    def _get_json(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        resp = self._client.get(REMOTEOK_URL, params=params)
        if resp.status_code == 429 or resp.status_code >= 500:
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()

    def _to_raw_job(self, j: dict[str, Any]) -> RawJob:
        url = j.get("url") or f"https://remoteok.com/remote-jobs/{j['slug']}"
        raw_html = j.get("description") or ""
        text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)

        posted_at: datetime | None = None
        date_str = j.get("date")
        if date_str:
            with contextlib.suppress(ValueError):
                posted_at = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        if posted_at is None:
            epoch = j.get("epoch")
            if epoch:
                try:
                    posted_at = datetime.fromtimestamp(int(epoch), tz=UTC)
                except (ValueError, OSError):
                    posted_at = None

        tags = j.get("tags") or []
        location = j.get("location") or (", ".join(tags) if tags else None)

        return RawJob(
            id=make_id(self.name, url),
            source=self.name,
            url=url,
            title=j["position"],
            company=j.get("company") or None,
            raw_text=text,
            posted_at=posted_at,
            country=location or None,
            remote=True,
        )
