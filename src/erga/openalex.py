"""OpenAlex API client: author resolution and batched works fetching."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from erga.config import AuthorConfig
from erga.errors import FetchError
from erga.http import Pacer, Transport, request_with_retry

OPENALEX_BASE = "https://api.openalex.org"
AUTHOR_BATCH_SIZE = 100  # OR-pipe filters accept at most 100 values
PER_PAGE = 100
WORKS_SELECT = ",".join(
    [
        "id",
        "title",
        "authorships",
        "publication_year",
        "publication_date",
        "primary_location",
        "type",
        "doi",
        "cited_by_count",
        "abstract_inverted_index",
        "open_access",
        "best_oa_location",
        "is_retracted",
    ]
)
AUTHOR_SELECT = "id,display_name,display_name_alternatives,works_count"


def strip_openalex_host(value: str) -> str:
    """Bare id (W..., A...) from https://openalex.org/... or bare form."""
    return value.rsplit("/", 1)[-1]


@dataclass
class AuthorProfile:
    id: str
    display_name: str
    alternatives: list[str]
    works_count: int


@dataclass
class ResolvedAuthor:
    config: AuthorConfig
    profiles: list[AuthorProfile]
    # Total ORCID matches reported by the API; exceeds the fetched page when
    # a heavily contaminated iD (copied into strangers' submissions) overflows
    # it. The count is the interesting signal, not the tail entries.
    orcid_profile_total: int = 0
    # How many head entries of `profiles` the ORCID query produced; a pinned
    # openalex_id contributes at most one entry after these. Warnings about
    # the ORCID must judge only its own profiles, not the pinned one.
    orcid_profile_count: int = 0

    @property
    def ids(self) -> list[str]:
        return [p.id for p in self.profiles]

    @property
    def orcid_profiles(self) -> list[AuthorProfile]:
        """The profiles the ORCID itself resolved to."""
        return self.profiles[: self.orcid_profile_count]


def _meta_total(data: Any, rows: list[Any]) -> int:
    """API-reported total match count, falling back to the fetched page."""
    return int((data.get("meta") or {}).get("count") or len(rows))


def _profile_from(data: dict[str, Any]) -> AuthorProfile:
    return AuthorProfile(
        id=strip_openalex_host(data["id"]),
        display_name=data.get("display_name") or "",
        alternatives=data.get("display_name_alternatives") or [],
        works_count=data.get("works_count") or 0,
    )


class OpenAlexClient:
    def __init__(
        self,
        transport: Transport,
        *,
        mailto: str,
        api_key: str | None = None,
        delay: float = 0.2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._transport = transport
        self._mailto = mailto
        self._api_key = api_key
        self._sleep = sleep
        self._pacer = Pacer(delay, sleep)

    def _get(self, path: str, params: dict[str, str], *, ok_missing: bool = False) -> Any:
        self._pacer.wait()
        params = {**params, "mailto": self._mailto}
        if self._api_key:
            params["api_key"] = self._api_key
        url = OPENALEX_BASE + path
        response = request_with_retry(self._transport, url, params, sleep=self._sleep)
        if response.status_code == 404 and ok_missing:
            return None
        if response.status_code != 200:
            raise FetchError(f"{url}: HTTP {response.status_code}")
        return response.data

    def resolve_author(self, author: AuthorConfig) -> ResolvedAuthor:
        """All OpenAlex author profiles for a configured author.

        An ORCID may resolve to several profiles (split identities); a pinned
        openalex_id that does not exist is a config error and aborts. An ORCID
        matching nothing yields an empty list for the caller to judge.
        """
        profiles: list[AuthorProfile] = []
        orcid_total = 0
        if author.orcid:
            data = self._get(
                "/authors",
                {"filter": f"orcid:{author.orcid}", "select": AUTHOR_SELECT, "per-page": "25"},
            )
            results = data.get("results", [])
            profiles.extend(_profile_from(row) for row in results)
            orcid_total = _meta_total(data, results)
        orcid_count = len(profiles)
        if author.openalex_id and author.openalex_id not in {p.id for p in profiles}:
            data = self._get(
                f"/authors/{author.openalex_id}", {"select": AUTHOR_SELECT}, ok_missing=True
            )
            if data is None:
                raise FetchError(
                    f"configured openalex_id {author.openalex_id} for {author.name!r} not found"
                )
            profiles.append(_profile_from(data))
        return ResolvedAuthor(
            config=author,
            profiles=profiles,
            orcid_profile_total=orcid_total,
            orcid_profile_count=orcid_count,
        )

    def search_authors(self, name: str, count: int = 10) -> tuple[list[AuthorProfile], int]:
        """Author profiles matching a name search, plus the total match count.

        Search covers display names and their alternatives, so this surfaces
        homonym and conflated profiles a configured id never resolves to.
        """
        data = self._get(
            "/authors",
            {"search": name, "select": AUTHOR_SELECT, "per-page": str(count)},
        )
        rows = data.get("results", [])
        return [_profile_from(row) for row in rows], _meta_total(data, rows)

    def fetch_works(
        self, author_ids: list[str], *, include_xpac: bool = False
    ) -> list[dict[str, Any]]:
        """All works by the given authors, deduplicated by work id.

        Authors are batched with the OR-pipe filter; each batch is walked with
        cursor pagination (basic paging caps at 10,000 results, cursors do not).
        Co-authored works arrive once per matching batch; the id dedup here
        collapses them.
        """
        works: dict[str, dict[str, Any]] = {}
        for start in range(0, len(author_ids), AUTHOR_BATCH_SIZE):
            batch = author_ids[start : start + AUTHOR_BATCH_SIZE]
            params = {
                "filter": "author.id:" + "|".join(batch),
                "select": WORKS_SELECT,
                "per-page": str(PER_PAGE),
                "cursor": "*",
            }
            if include_xpac:
                params["include_xpac"] = "true"
            while True:
                data = self._get("/works", params)
                results = data.get("results", [])
                for raw in results:
                    works.setdefault(strip_openalex_host(raw["id"]), raw)
                cursor = (data.get("meta") or {}).get("next_cursor")
                if not cursor or not results:
                    break
                params = {**params, "cursor": cursor}
        return list(works.values())

    def recent_works(self, author_id: str, count: int = 3) -> list[dict[str, Any]]:
        """Most recent works for one author profile (verify report)."""
        data = self._get(
            "/works",
            {
                "filter": f"author.id:{author_id}",
                "select": "title,publication_year",
                "sort": "publication_date:desc",
                "per-page": str(count),
            },
        )
        rows: list[dict[str, Any]] = data.get("results", [])
        return rows
