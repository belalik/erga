"""Crossref venue lookup for the backfill stage.

Crossref still operates a mailto polite pool, so the mailto rides along both
as a query parameter and in the transport's User-Agent.
"""

from __future__ import annotations

import time
import urllib.parse
from collections.abc import Callable

from erga.http import Pacer, Transport, request_with_retry

CROSSREF_BASE = "https://api.crossref.org/works/"


class CrossrefClient:
    def __init__(
        self,
        transport: Transport,
        *,
        mailto: str,
        delay: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._transport = transport
        self._mailto = mailto
        self._sleep = sleep
        self._pacer = Pacer(delay, sleep)

    def venue_for_doi(self, doi: str) -> str | None:
        """Container title for a bare DOI, or None.

        DataCite DOIs 404 here and are skipped silently, as is any record
        without a container title. Raises FetchError only when retryable
        failures persist (the caller stops backfilling, keeping nulls).
        """
        self._pacer.wait()
        url = CROSSREF_BASE + urllib.parse.quote(doi, safe="")
        response = request_with_retry(
            self._transport, url, {"mailto": self._mailto}, sleep=self._sleep
        )
        if response.status_code != 200 or not isinstance(response.data, dict):
            return None
        message = response.data.get("message") or {}
        titles = message.get("container-title") or []
        if titles and isinstance(titles[0], str) and titles[0].strip():
            return titles[0].strip()
        return None
