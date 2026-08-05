"""Normalize raw OpenAlex works to the canonical schema."""

from __future__ import annotations

from typing import Any

from erga.model import Work, WorkAuthor, normalize_orcid
from erga.openalex import strip_openalex_host

# OpenAlex type -> canonical type. The vocabulary drifts (a 2026
# reclassification touched ~10% of the catalog); anything unmapped is "other"
# and the overrides file is the stability mechanism for records a site
# cares about.
TYPE_MAP = {
    "article": "journal",
    "review": "journal",
    "conference-paper": "conference",
    "book": "book",
    "book-chapter": "book-chapter",
    "dissertation": "thesis",
    "preprint": "preprint",
    "dataset": "dataset",
    "software": "software",
    "software-paper": "software",
}


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Plaintext from OpenAlex's abstract_inverted_index (word -> positions)."""
    if not inverted_index:
        return None
    positions: dict[int, str] = {}
    for word, places in inverted_index.items():
        for place in places:
            positions[place] = word
    return " ".join(positions[i] for i in sorted(positions))


def map_type(raw: dict[str, Any]) -> str:
    """Canonical type; journal articles published at a conference source
    also become "conference" — records predating OpenAlex's first-class
    conference-paper type still carry "article"."""
    mapped = TYPE_MAP.get(raw.get("type") or "", "other")
    if mapped == "journal":
        source = (raw.get("primary_location") or {}).get("source") or {}
        if source.get("type") == "conference":
            return "conference"
    return mapped


def open_access_url(raw: dict[str, Any]) -> str | None:
    oa_url = (raw.get("open_access") or {}).get("oa_url")
    if oa_url:
        return str(oa_url)
    best = raw.get("best_oa_location") or {}
    url = best.get("pdf_url") or best.get("landing_page_url")
    return str(url) if url else None


def normalize_work(
    raw: dict[str, Any],
    tracked_ids: set[str],
    tracked_orcids: set[str],
) -> Work:
    """Map one raw OpenAlex work to a canonical record.

    An author is tracked when their OpenAlex id is among the resolved ids or
    their ORCID matches a configured one (split profiles make the id alone
    insufficient). Name matching is reserved for manual entries.
    """
    authors = []
    for authorship in raw.get("authorships") or []:
        author = authorship.get("author") or {}
        name = author.get("display_name") or authorship.get("raw_author_name") or "Unknown"
        orcid = author.get("orcid")
        author_id = strip_openalex_host(author["id"]) if author.get("id") else None
        tracked = bool(
            (author_id and author_id in tracked_ids)
            or (orcid and normalize_orcid(orcid) in tracked_orcids)
        )
        authors.append(WorkAuthor(name=name, orcid=orcid, tracked=tracked))

    source = (raw.get("primary_location") or {}).get("source") or {}
    venue = source.get("display_name") or None

    return Work(
        id=strip_openalex_host(raw["id"]),
        title=raw.get("title") or "",
        authors=authors,
        year=raw.get("publication_year"),
        date=raw.get("publication_date"),
        venue=venue,
        type=map_type(raw),
        doi=raw.get("doi") or None,
        cited_by_count=raw.get("cited_by_count") or 0,
        abstract=reconstruct_abstract(raw.get("abstract_inverted_index")),
        open_access_url=open_access_url(raw),
        is_retracted=bool(raw.get("is_retracted")),
        source="openalex",
    )
