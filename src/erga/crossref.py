"""Crossref venue lookup for the backfill stage.

Crossref still operates a mailto polite pool, so the mailto rides along both
as a query parameter and in the transport's User-Agent.
"""

from __future__ import annotations

import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

from erga.http import Pacer, Transport, request_with_retry

CROSSREF_BASE = "https://api.crossref.org/works/"


@dataclass(frozen=True)
class Container:
    """What Crossref says a work appeared in."""

    title: str
    # True when Crossref also names a series the title belongs to. A
    # chapter's container-title then reads [series, book], in that order,
    # whether the book is a monograph or a proceedings volume (104 of 104
    # two-title chapter records on two consumers, 2026-11-07). Position
    # decides, never the name: OpenAlex's name for the same series can
    # differ ("... book series" appended), so matching names picks the
    # series again.
    in_series: bool = False


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

    def container_for_doi(self, doi: str) -> Container | None:
        """What a bare DOI's record appeared in, or None.

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
        raw = message.get("container-title") or []
        titles = [t.strip() for t in raw if isinstance(t, str) and t.strip()]
        if not titles:
            return None
        if message.get("type") == "book-chapter" and len(raw) == len(titles) == 2:
            return Container(titles[1], in_series=True)
        return Container(titles[0])
