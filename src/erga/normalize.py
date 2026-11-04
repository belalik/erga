"""Normalize raw OpenAlex works to the canonical schema."""

from __future__ import annotations

import html
import re
from collections import Counter
from typing import Any

from erga.model import Work, WorkAuthor, clean_doi, normalize_orcid
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
    # Encyclopedia and handbook entries: authored contributions to an edited
    # reference work, which is what a book chapter is.
    "reference-entry": "book-chapter",
    "dissertation": "thesis",
    "preprint": "preprint",
    "dataset": "dataset",
    "software": "software",
    "software-paper": "software",
}

# Raw types deliberately left in "other": corrections, special-issue front
# matter and peer reviews (referee reports, author responses) are not
# research outputs, paratext is other by definition. A conference abstract
# stays "other" rather than pass for a conference paper: a full paper
# misfiled as one under-claims visibly and an override fixes it. Reports
# have no canonical type; whether they earn one is a pre-v1.0 question.
# Raw "other" belongs here too — upstream already classified it, so the
# fallback is an identity and a warning would alarm without informing.
KNOWN_OTHER_TYPES = frozenset(
    {"conference-abstract", "editorial", "erratum", "other", "paratext", "peer-review", "report"}
)


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


def malformed_dois(raw_works: list[dict[str, Any]]) -> list[str]:
    """Ids of works whose DOI field holds more than a DOI.

    normalize_work keeps only the DOI; without that, DOI dedup, overrides,
    tags and the Crossref backfill would all miss the record, and the
    output would link nowhere. Listed so the upstream fault stays visible.
    """
    return [
        strip_openalex_host(raw["id"])
        for raw in raw_works
        if (doi := raw.get("doi")) and clean_doi(doi) != doi
    ]


_HTML_TAG = re.compile(r"<[^>]+>")


def unescape_html(text: str) -> str:
    """Text with its HTML entities decoded, until stable.

    Upstream strings carry entities, sometimes double-encoded (&amp;#039;
    exists in the wild): abstracts, and venue names from OpenAlex and
    Crossref alike ("Virtual Systems &amp; Multimedia", 2026-10). Output is
    plain text, so a site that escapes on render would print them.
    """
    prev = None
    while text != prev:
        prev = text
        text = html.unescape(text)
    return text


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Plaintext from OpenAlex's abstract_inverted_index (word -> positions).

    Publisher-supplied abstracts carry HTML entities, decoded until stable,
    and markup tags (<br>, and entity-encoded ones that only appear after
    unescaping), which are stripped.
    """
    if not inverted_index:
        return None
    positions: dict[int, str] = {}
    for word, places in inverted_index.items():
        for place in places:
            positions[place] = word
    text = unescape_html(" ".join(positions[i] for i in sorted(positions)))
    return _HTML_TAG.sub("", text).strip() or None


# Tags JST appends to the titles of its machine translations of other papers
# (NICT's engine, and the Kyoto University one before it); about 195,000
# and 317,000 OpenAlex works, 2026-10. Matched exactly as a title suffix:
# the translator's own provenance mark, never a wording heuristic.
MACHINE_TRANSLATION_TAGS = ("【Powered by NICT】", "【JST・京大機械翻訳】")


def is_machine_translation(title: str) -> bool:
    return title.rstrip().endswith(MACHINE_TRANSLATION_TAGS)


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


# Source types that name where a work is hosted, not what it is part of.
# OpenAlex files book chapters under the publisher's e-book platform
# ("Springer eBooks", "Routledge eBooks"; 40 of a consumer's chapters moved
# there in one week, 2026-10) and keeps the book's own title only in the
# location's raw_source_name. The type decides, never the name.
PLATFORM_SOURCE_TYPES = frozenset({"ebook platform"})


def venue(raw: dict[str, Any]) -> str | None:
    """The publication a work belongs to, never the platform it sits on.

    On a platform source the display name is the imprint, so the venue is
    the location's raw source name, with the imprint as the fallback when
    even that is missing. Everywhere else the source's display name is the
    curated one, and with no source at all the venue stays unknown for the
    ratchet and Crossref: a source-less location's raw name is whatever the
    depositor wrote, and on a consumer's list that was a PDF URL nine times
    in eleven (2026-10-16), so it never serves as a venue.
    """
    location = raw.get("primary_location") or {}
    source = location.get("source") or {}
    if source.get("type") in PLATFORM_SOURCE_TYPES:
        name = location.get("raw_source_name") or source.get("display_name")
    else:
        name = source.get("display_name")
    return unescape_html(name) if name else None


def platform_names(raw_works: list[dict[str, Any]]) -> frozenset[str]:
    """Display names of the corpus's platform sources: an earlier erga
    wrote them as venues, so the ratchet must not carry them forward.
    Decoded as venue() decodes them, the form the ratchet compares in."""
    names = set()
    for raw in raw_works:
        source = (raw.get("primary_location") or {}).get("source") or {}
        if source.get("type") in PLATFORM_SOURCE_TYPES and source.get("display_name"):
            names.add(unescape_html(str(source["display_name"])))
    return frozenset(names)


def open_access_url(raw: dict[str, Any]) -> str | None:
    oa_url = (raw.get("open_access") or {}).get("oa_url")
    if oa_url:
        return str(oa_url)
    best = raw.get("best_oa_location") or {}
    url = best.get("pdf_url") or best.get("landing_page_url")
    return str(url) if url else None


def _work_author(
    authorship: dict[str, Any],
    tracked_ids: dict[str, str],
    tracked_orcids: dict[str, str],
    tracked_names: dict[str, str],
) -> tuple[WorkAuthor, tuple[str, str, str | None] | None]:
    """One authorship as published, and what it withholds: (configured
    author, the profile's bare iD, the profile or None when unlinked), or
    None.

    A name-only match carries no iD. The paths run id, ORCID, name, so the
    profile's iD matches no configured one: a homonym's, or the member's own
    on a split profile the config never resolved, and nothing here tells
    which. Nor does the configured iD stand in: the name is the weakest of
    the three matches, and the member's own iD beside a homonym's byline
    would make the guess look verified. A wrong iD misattributes a person, a
    missing one costs a link; foreign_orcids reports each withheld iD, so a
    consumer whose member owns one can configure it. (A manual entry's
    names do carry the configured iD: there the maintainer named the
    person, erga did not guess.)
    """
    author = authorship.get("author") or {}
    name = author.get("display_name") or authorship.get("raw_author_name") or "Unknown"
    orcid = author.get("orcid")
    author_id = strip_openalex_host(author["id"]) if author.get("id") else None
    tracked_as = (
        (author_id and tracked_ids.get(author_id))
        or (orcid and tracked_orcids.get(normalize_orcid(orcid)))
        or None
    )
    withheld = None
    if tracked_as is None and (tracked_as := tracked_names.get(name.casefold().strip())):
        if orcid:
            withheld = (tracked_as, normalize_orcid(orcid), author_id)
        orcid = None
    published = WorkAuthor(
        name=name, orcid=orcid, tracked=tracked_as is not None, tracked_as=tracked_as
    )
    return published, withheld


def foreign_orcids(
    raw_works: list[dict[str, Any]],
    tracked_ids: dict[str, str],
    tracked_orcids: dict[str, str],
    tracked_names: dict[str, str],
    published: list[Work],
) -> list[str]:
    """A line per configured author and iD that normalize_work withheld on
    a published work, naming the profiles that carry it.

    Counted against the records the output keeps, after curation: an
    excluded work raises nothing, a merged twin is not counted twice, and a
    work whose final authors still show the iD beside that member (a split
    profile, resolved on one authorship and name-matched on another) is not
    one it was "not published" on. No advice: the iD may be a homonym's,
    which nothing silences, or the member's own, which only the consumer
    can tell and configure.
    """
    shown = {
        work.id: {(a.tracked_as, normalize_orcid(a.orcid)) for a in work.authors if a.orcid}
        for work in published
    }
    found: dict[tuple[str, str], tuple[set[str], set[str], int]] = {}
    for raw in raw_works:
        if (work_id := strip_openalex_host(raw["id"])) not in shown:
            continue
        for authorship in raw.get("authorships") or []:
            _, withheld = _work_author(authorship, tracked_ids, tracked_orcids, tracked_names)
            if withheld and withheld[:2] not in shown[work_id]:
                tracked_as, orcid, profile = withheld
                profiles, works, unlinked = found.get((tracked_as, orcid), (set(), set(), 0))
                if profile:
                    profiles.add(profile)
                works.add(work_id)
                found[(tracked_as, orcid)] = (profiles, works, unlinked + (profile is None))
    lines = []
    for (tracked_as, orcid), (profiles, works, unlinked) in sorted(found.items()):
        carriers = sorted(profiles) + (
            [f"{unlinked} byline(s) with no profile"] if unlinked else []
        )
        lines.append(
            f"{tracked_as}: ORCID {orcid} on {', '.join(carriers)}, matched by name only, "
            f"not published on {len(works)} work(s): a homonym's, or theirs on a profile "
            f"the config does not resolve"
        )
    return lines


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
    anyway. Which iD a tracked author carries: _work_author.
    """
    authors = [
        _work_author(authorship, tracked_ids, tracked_orcids, tracked_names)[0]
        for authorship in raw.get("authorships") or []
    ]

    return Work(
        id=strip_openalex_host(raw["id"]),
        title=unescape_html(raw.get("title") or ""),
        authors=authors,
        year=raw.get("publication_year"),
        date=raw.get("publication_date"),
        venue=venue(raw),
        type=map_type(raw),
        doi=clean_doi(raw["doi"]) if raw.get("doi") else None,
        cited_by_count=raw.get("cited_by_count") or 0,
        abstract=reconstruct_abstract(raw.get("abstract_inverted_index")),
        open_access_url=open_access_url(raw),
        is_retracted=bool(raw.get("is_retracted")),
        source="openalex",
    )
