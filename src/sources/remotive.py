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

from .base import RawJob, Source, make_id

logger = logging.getLogger(__name__)

# Remotive officially deprecated its RSS feeds; only the JSON API remains.
# Docs: https://remotive.com/api-documentation
# Terms: link back to job url, attribute Remotive, ≤4 requests/day.
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"

DEFAULT_CATEGORIES: tuple[str, ...] = ("software-development", "devops")


_RETRYABLE_HTTP_EXC = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


class RemotiveSource(Source):
    name = "remotive"

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    def fetch(
        self,
        *,
        categories: list[str] | None = None,
        search: str | None = None,
        limit_per_category: int = 50,
    ) -> Iterable[RawJob]:
        cats = categories if categories is not None else list(DEFAULT_CATEGORIES)
        for cat in cats:
            params: dict[str, Any] = {"category": cat, "limit": limit_per_category}
            if search:
                params["search"] = search

            try:
                payload = self._get_json(params)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Remotive fetch failed for category=%s: %s", cat, exc)
                continue

            jobs = payload.get("jobs") or []
            for j in jobs:
                try:
                    yield self._to_raw_job(j)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Skipping Remotive entry: %s", exc)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE_HTTP_EXC + (httpx.HTTPStatusError,)),
        reraise=True,
    )
    def _get_json(self, params: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.get(REMOTIVE_URL, params=params)
        if resp.status_code == 429 or resp.status_code >= 500:
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()

    def _to_raw_job(self, j: dict[str, Any]) -> RawJob:
        url = j["url"]
        raw_html = j.get("description") or ""
        text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)

        posted_at: datetime | None = None
        pub = j.get("publication_date")
        if pub:
            try:
                # Remotive uses ISO 8601 without timezone (treat as UTC implicitly).
                posted_at = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except ValueError:
                posted_at = None

        loc = j.get("candidate_required_location") or ""
        # "Worldwide" / "Anywhere" / "USA Only" / "EMEA" etc. Keep raw; downstream uses
        # JobRequirements for structured filtering.
        country = loc or None

        return RawJob(
            id=make_id(self.name, url),
            source=self.name,
            url=url,
            title=j["title"],
            company=j.get("company_name"),
            raw_text=text,
            posted_at=posted_at,
            country=country,
            remote=True,
        )


def _cli() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Smoke test the Remotive source.")
    parser.add_argument(
        "--categories",
        nargs="*",
        default=None,
        help=f"categorías a consumir (default: {list(DEFAULT_CATEGORIES)})",
    )
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    src = RemotiveSource()
    for i, job in enumerate(src.fetch(categories=args.categories)):
        if i >= args.limit:
            break
        print(json.dumps(job.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
