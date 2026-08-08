"""Normalize raw OpenAlex works to the canonical schema."""

from __future__ import annotations

import html
import re
from collections import Counter
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

# Raw types deliberately left in "other": corrections and special-issue
# front matter are not research outputs, paratext is other by definition.
KNOWN_OTHER_TYPES = frozenset({"editorial", "erratum", "paratext"})


def unmapped_types(raw_works: list[dict[str, Any]]) -> dict[str, int]:
    """Count raw types nothing decided about — the silent-drift trap.

    A catch-all cannot fail: when OpenAlex introduced conference-paper, an
    origin pipeline misfiled sixty conference papers as "other" for months
    with no signal. Every type must be either mapped or knowingly other.
    """
    counts = Counter(
        raw_type
        for raw in raw_works
        if (raw_type := raw.get("type"))
        and raw_type not in TYPE_MAP
        and raw_type not in KNOWN_OTHER_TYPES
    )
    return dict(sorted(counts.items()))


_HTML_TAG = re.compile(r"<[^>]+>")


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Plaintext from OpenAlex's abstract_inverted_index (word -> positions).

    Publisher-supplied abstracts carry HTML entities — sometimes
    double-encoded (&amp;#039; exists in the wild), so unescape until
    stable — and markup tags (<br>, and entity-encoded ones that only
    appear after unescaping), which are stripped.
    """
    if not inverted_index:
        return None
    positions: dict[int, str] = {}
    for word, places in inverted_index.items():
        for place in places:
            positions[place] = word
    text = " ".join(positions[i] for i in sorted(positions))
    prev = None
    while text != prev:
        prev = text
        text = html.unescape(text)
    return _HTML_TAG.sub("", text).strip() or None


def map_type(raw: dict[str, Any]) -> str:
    """Canonical type, refined by the venue's source type.

    Journal articles at a conference source become "conference" (records
    predating OpenAlex's first-class conference-paper type still carry
    "article"). A software-paper at a journal source is a peer-reviewed
    article about software (SoftwareX, JOSS), not a software artifact.
    """
    raw_type = raw.get("type") or ""
    source = (raw.get("primary_location") or {}).get("source") or {}
    mapped = TYPE_MAP.get(raw_type, "other")
    if mapped == "journal" and source.get("type") == "conference":
        return "conference"
    if raw_type == "software-paper" and source.get("type") == "journal":
        return "journal"
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
    tracked_ids: dict[str, str],
    tracked_orcids: dict[str, str],
    tracked_names: dict[str, str],
) -> Work:
    """Map one raw OpenAlex work to a canonical record.

    The tracked_* mappings resolve to the configured author's canonical
    name. An author is tracked when their OpenAlex id is among the resolved
    ids, their ORCID matches a configured one (split profiles make the id
    alone insufficient), or their name matches a configured name/alias —
    OpenAlex misassigns some authorships to conflated homonym profiles whose
    ids can never be configured, and the flag's consumer renders the name
    anyway.
    """
    authors = []
    for authorship in raw.get("authorships") or []:
        author = authorship.get("author") or {}
        name = author.get("display_name") or authorship.get("raw_author_name") or "Unknown"
        orcid = author.get("orcid")
        author_id = strip_openalex_host(author["id"]) if author.get("id") else None
        tracked_as = (
            (author_id and tracked_ids.get(author_id))
            or (orcid and tracked_orcids.get(normalize_orcid(orcid)))
            or tracked_names.get(name.casefold().strip())
            or None
        )
        authors.append(
            WorkAuthor(
                name=name, orcid=orcid, tracked=tracked_as is not None, tracked_as=tracked_as
            )
        )

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
