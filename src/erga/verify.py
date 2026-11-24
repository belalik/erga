"""The author-disambiguation report.

OpenAlex author identities split and conflate people, so this is a
first-class feature: it shows what each configured author actually resolves
to before a build trusts those ids.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from erga.config import AuthorConfig, Config
from erga.curation import Override, load_overrides, mark_keep_distinct
from erga.dedup import merge_group, normalize_title, title_key
from erga.errors import FetchError
from erga.model import Work
from erga.normalize import book_series_names, normalize_work
from erga.openalex import (
    AuthorProfile,
    OpenAlexClient,
    byline_search_key,
    strip_openalex_host,
)
from erga.output import read_output, sort_works, work_from_record
from erga.pipeline import BuildStats, curate

IMPLAUSIBLE_WORKS_COUNT = 2000
RECENT_TITLES = 3
MAX_NAME_VARIANTS = 5
MAX_SAME_NAME = 5
MAX_UNLINKED = 10
# A byline search past this many works has found a common name, not a person.
BYLINE_SEARCH_LIMIT = 1000
# CiteSeerX copies land here; the pages redirect to the Wayback Machine,
# mostly to no snapshot (dpsd-new, 2026-11-23).
CITESEERX_HOST = "citeseerx.ist.psu.edu"


def _name_tokens(name: str) -> set[str]:
    """Comparable word tokens: accents and punctuation folded, initials dropped.

    Names want the same text folding titles do, so dedup's normalizer is the
    single owner of that logic.
    """
    return {t for t in normalize_title(name).split() if len(t) >= 2}


def _looks_like(profile: AuthorProfile, author: AuthorConfig) -> bool:
    """Whether a profile's names plausibly belong to the configured author.

    Sharing one full word (never a bare initial) between any profile name and
    the configured name or aliases counts. Errs toward flagging: a
    transliteration mismatch is a cheap false alarm in a report a human is
    reading, while a stranger's profile fetched silently is the failure this
    report exists to prevent.
    """
    configured: set[str] = set()
    for name in [author.name, *author.aliases]:
        configured |= _name_tokens(name)
    return any(
        _name_tokens(candidate) & configured
        for candidate in [profile.display_name, *profile.alternatives]
    )


def _scripts(name: str) -> set[str]:
    """The scripts a name's letters are written in ("LATIN", "GREEK", …)."""
    return {unicodedata.name(ch, "").split(" ", 1)[0] for ch in name if ch.isalpha()} - {""}


def _other_script(profile: AuthorProfile, author: AuthorConfig) -> bool:
    """Whether the profile's name is written wholly in scripts the configured
    names lack: `_looks_like` can never match it, and an alias can.

    Wholly, so a lone homoglyph inside a Latin name (a Greek capital kappa
    as a middle initial, seen upstream) does not make a same-script
    stranger read as a transliteration.
    """
    configured: set[str] = set()
    for name in [author.name, *author.aliases]:
        configured |= _scripts(name)
    scripts = _scripts(profile.display_name or "")
    return bool(scripts) and not scripts & configured


def _same_name_searches(author: AuthorConfig) -> list[str]:
    """The names a same-name search sends: the configured name, then each
    alias of two full words or more, one per distinct query.

    An alias of initials and a surname ("X. Papageorgiou"), or a surname
    alone, is left out: searched, it lists every namesake who shares it.
    The rest find what the configured name misses: a detached profile under
    a name in another script ("Ιωάννης Ξενάκης") or a nickname ("Harry
    Valsamos"), both seen on dpsd-new 2026-11-21.
    """
    unique = {byline_search_key(author.name): author.name}
    for alias in author.aliases:
        if len(_name_tokens(alias)) >= 2:
            unique.setdefault(byline_search_key(alias), alias)
    return list(unique.values())


def _same_name_lines(
    client: OpenAlexClient, author: AuthorConfig, known_ids: set[str]
) -> list[str]:
    """Profiles a name search surfaces beyond the configured/resolved ids.

    These are what a configured id can never show: homonyms, and conflated
    or detached profiles that hold works OpenAlex misassigned. Informational,
    not warnings: same-name strangers are common and only a human can judge
    them. An alias's lines name it, and a profile shows once.
    """
    lines: list[str] = []
    shown = set(known_ids)
    for name in _same_name_searches(author):
        profiles, total = client.search_authors(name)
        others = [p for p in profiles if p.id not in shown]
        label = "same name" if name == author.name else f"alias {name!r}"
        lines.extend(
            f"  {label}, not configured: {p.id}  {p.display_name} — {p.works_count} works"
            for p in others[:MAX_SAME_NAME]
        )
        shown.update(p.id for p in others[:MAX_SAME_NAME])
        # Matches beyond the fetched page, plus fetched ones past the display cap.
        unshown = (total - len(profiles)) + len(others[MAX_SAME_NAME:])
        if unshown > 0:
            what = "name" if name == author.name else f"{name!r}"
            lines.append(f"  … and {unshown} more {what} match(es) on OpenAlex")
    return lines


def _byline_matches(byline: str, configured: str) -> bool:
    """Whether a raw byline could be this configured name.

    Every full word of the configured name must appear, in any order, since
    OpenAlex keeps bylines as printed ("Papageorgiou, Xanthi"). Each initial
    then needs a remaining byline word starting with it, unless none is left
    to contradict it: "X. Papageorgiou" takes "Xanthi S. Papageorgiou" and
    refuses "K. Papageorgiou". A full word never matches an initial, so a
    configured full name misses initial-only bylines; an initial alias opts
    the author into them, namesakes included.
    """
    wanted = normalize_title(configured).split()
    rest = normalize_title(byline).split()
    for word in [w for w in wanted if len(w) > 1]:
        if word not in rest:
            return False
        rest.remove(word)
    for initial in [w for w in wanted if len(w) == 1]:
        match = next((w for w in rest if w.startswith(initial)), None)
        if match is not None:
            rest.remove(match)
        elif rest:
            return False
    return True


def _unlinked_byline(raw: dict[str, Any], names: list[str]) -> str | None:
    """The first byline on a work that carries a configured name but no author id."""
    for authorship in raw.get("authorships") or []:
        if (authorship.get("author") or {}).get("id"):
            continue
        byline = authorship.get("raw_author_name") or ""
        if any(_byline_matches(byline, name) for name in names):
            return byline
    return None


@dataclass
class _Published:
    """The published list, keyed the ways a build would merge a record into it."""

    by_id: dict[str, Work] = field(default_factory=dict)
    by_doi: dict[str, Work] = field(default_factory=dict)
    titles: dict[tuple[str, bool], list[Work]] = field(default_factory=dict)

    @classmethod
    def of(cls, records: list[dict[str, Any]], overrides: list[Override]) -> _Published:
        published = cls()
        works = [work_from_record(record) for record in records]
        # The list cannot show a keep_distinct; only the overrides record it.
        mark_keep_distinct(works, overrides)
        for work in works:
            published.by_id[work.id] = work
            if work.doi_key:
                published.by_doi[work.doi_key] = work
            key = title_key(work)
            if key is not None:
                published.titles.setdefault(key, []).append(work)
        return published

    def holding(self, work: Work) -> tuple[list[Work], bool]:
        """The listed records that hold a work, and whether only by title."""
        listed = self.by_id.get(work.id)
        if listed is None and work.doi_key:
            listed = self.by_doi.get(work.doi_key)
        if listed is not None:
            return [listed], False
        key = title_key(work)
        return (self.titles.get(key, []) if key else []), True


def _work_lines(
    works: list[Work], tails: dict[str, str], cap: int | None = MAX_UNLINKED
) -> list[str]:
    """One line per work, its tail by work id after the title and year,
    capped unless `cap` is None."""
    ordered = sort_works(works)
    shown = ordered if cap is None else ordered[:cap]
    lines = []
    for work in shown:
        year = f" ({work.year})" if work.year else ""
        lines.append(f"    {work.id}  {work.title or '(untitled)'}{year}{tails[work.id]}")
    if len(ordered) > len(shown):
        lines.append(f"    … and {len(ordered) - len(shown)} more")
    return lines


def _byline_tails(works: list[Work], bylines: dict[str, str]) -> dict[str, str]:
    """Each work's DOI, if any, and the byline that names the author."""
    return {
        work.id: (f"  {work.doi_key}" if work.doi_key else "") + f"  as {bylines[work.id]!r}"
        for work in works
    }


def _normalized(raws: list[dict[str, Any]]) -> list[Work]:
    """Raw finds as canonical records, the venue chosen as a build chooses
    it: a book series is held back, never printed as the volume."""
    series_names = book_series_names(raws)
    return [normalize_work(raw, {}, {}, {}, series_names) for raw in raws]


def _as_built(works: list[Work], config: Config, overrides: list[Override]) -> list[Work]:
    """Finds as a build would keep them: versions of one work (a dataset's
    releases, a deposit beside its published copy) collapse, and a work the
    maintainer excluded stays out."""
    return curate(works, overrides, config.exclude_types, BuildStats())


def _byline_candidates(
    client: OpenAlexClient,
    author: AuthorConfig,
    own_ids: list[str],
    config: Config,
    overrides: list[Override],
) -> tuple[list[Work], dict[str, str], list[str]]:
    """Works off the author's profiles whose unlinked byline carries their name.

    Returned as a build would keep them, with the matching byline by work
    id and a line for each name too common to search.
    """
    # One search per distinct query: names differing only in case, order or
    # punctuation send the same one, and the byline match ignores all three.
    unique: dict[tuple[str, ...], str] = {}
    for name in [author.name, *author.aliases]:
        unique.setdefault(byline_search_key(name), name)
    names = list(unique.values())
    skipped: list[str] = []
    bylines: dict[str, str] = {}
    raws: list[dict[str, Any]] = []
    for name in names:
        found, total = client.works_by_byline(
            name, exclude_ids=own_ids, limit=BYLINE_SEARCH_LIMIT, include_xpac=config.include_xpac
        )
        if total > BYLINE_SEARCH_LIMIT:
            skipped.append(
                f"  byline search skipped for {name!r}: {total} works, too common to judge"
            )
            continue
        for raw in found:
            work_id = strip_openalex_host(raw["id"])
            byline = _unlinked_byline(raw, names)
            if byline is not None and work_id not in bylines:
                bylines[work_id] = byline
                raws.append(raw)
    return _as_built(_normalized(raws), config, overrides), bylines, skipped


def _unlinked_lines(
    client: OpenAlexClient,
    author: AuthorConfig,
    own_ids: list[str],
    config: Config,
    published: _Published | None,
    overrides: list[Override],
) -> list[str]:
    """Works carrying the author's name with no author id, missing from the list.

    No profile fetch can see these: the authorship names them but links no
    one. Informational, like the same-name lines: a namesake's byline looks
    the same, and only a human can tell, so the remedy is a manual entry.
    Compared against the published list rather than a fresh fetch, because
    that is what a member reads and it already holds the manual entries,
    patches and type exclusions; the finds go through the same overrides.
    """
    if published is None:
        return []
    works, bylines, lines = _byline_candidates(client, author, own_ids, config, overrides)
    missing: list[Work] = []
    better: list[tuple[Work, list[str]]] = []
    # Listed record id to the byline naming the author, for a record that
    # does not credit them: the build tracks an authorship with no id only by
    # exact name, so a byline printed another way, or a listed copy lacking
    # it, leaves the work off any page that filters on tracked_as.
    uncredited: dict[str, str] = {}
    for work in works:
        held, by_title = published.holding(work)
        if not held:
            missing.append(work)
            continue
        if not any(a.tracked_as == author.name for record in held for a in record.authors):
            for record in held:
                uncredited.setdefault(record.id, bylines[work.id])
        if (
            by_title
            and work.doi
            and not any(twin.doi for twin in held)
            and merge_group([*held, work]) is work
        ):
            # Dedup would keep this record over the listed copy, which lacks
            # the DOI it carries: a repair, not a gap. A deposit's DOI loses
            # to a listed version of record and is no repair.
            better.append((work, sorted(twin.id for twin in held)))

    if missing:
        lines.append(
            f"  name in the byline, no author id, not on the published list: "
            f"{len(missing)} work(s); add any that are theirs to {config.manual_path.name}"
        )
        lines.extend(_work_lines(missing, _byline_tails(missing, bylines)))
    if uncredited:
        lines.append(
            f"  listed without crediting them: {len(uncredited)} work(s); if theirs, an alias "
            f"spelling the byline or an override patching the record's authors credits them"
        )
        records = [published.by_id[i] for i in uncredited]
        lines.extend(_work_lines(records, _byline_tails(records, uncredited)))
    for work, listed in sorted(better, key=lambda pair: pair[0].id):
        lines.append(
            f"  better record for a listed work: {work.id} carries {work.doi_key}; "
            f"listed as {', '.join(listed)} without a DOI, which an `id` override can patch in"
        )
    return lines


def _xpac_link(work: Work, raw: dict[str, Any]) -> tuple[str | None, bool]:
    """Where a reviewer can read an XPAC-only work, and whether it is a
    CiteSeerX copy.

    A CiteSeerX copy's landing page is dead, but its location's raw source
    name keeps the URL of the PDF it was indexed from: on all 33 of one
    consumer's copies, which carry no year and no source (2026-11-24).
    """
    location = raw.get("primary_location") or {}
    landing = location.get("landing_page_url")
    landing = landing if isinstance(landing, str) and landing else None
    if landing and _host(landing) == CITESEERX_HOST:
        pdf = location.get("raw_source_name")
        if isinstance(pdf, str) and _host(pdf, schemes={"http", "https", "ftp"}):
            return pdf, True
        return landing, True
    return work.doi or landing, False


def _host(url: str, schemes: frozenset[str] | set[str] | None = None) -> str | None:
    """A URL's host, or None for text that is no URL (a depositor's note, a
    scheme with nothing after it) or a URL too malformed to parse."""
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return None
    if schemes is not None and parts.scheme not in schemes:
        return None
    return host


def _xpac_lines(
    client: OpenAlexClient,
    own_ids: list[str],
    config: Config,
    published: _Published | None,
    overrides: list[Override],
) -> list[str]:
    """XPAC-only works on the author's profiles, missing from the list.

    OpenAlex leaves its expansion pack (repository records, CiteSeerX
    copies) out of the default listing, and the build follows it unless the
    config sets `include_xpac` (settled 2026-11-23, requirements' XPAC
    paragraph: the careers holding real XPAC works hold the scrapes too).
    So they surface here, read-only, for a member to confirm. The finds go
    through the build's curation and meet the published list as a build
    would merge them; one more listing call drops what the default fetch
    also returns, a work upstream added after the list was built.
    Advisory: a failed call leaves this one section unchecked.
    """
    if published is None or config.include_xpac or not own_ids:
        return []
    try:
        raws = {
            strip_openalex_host(raw["id"]): raw
            for raw in client.fetch_works(own_ids, include_xpac=True)
        }
        works = _normalized(list(raws.values()))
        # An XPAC copy can win the merge with a listed default record (a
        # newer id at equal rank) and keep none of its evidence, least of
        # all a title an override patched on the list. Its keys, read before
        # the merge as dedup reads them, still say it is held.
        mark_keep_distinct(works, overrides)
        held = [work for work in works if published.holding(work)[0]]
        held_dois = {work.doi_key for work in held if work.doi_key}
        held_titles = {key for work in held if (key := title_key(work)) is not None}
        leads = [
            work
            for work in _as_built(works, config, overrides)
            if not published.holding(work)[0]
            and work.doi_key not in held_dois
            and title_key(work) not in held_titles
        ]
        if leads:
            default = client.in_listing([work.id for work in leads], include_xpac=False)
            leads = [work for work in leads if work.id not in default]
    except FetchError as exc:
        return [f"  XPAC-only works not checked: {exc}"]
    # What a reviewer opens, after the venue.
    tails: dict[str, str] = {}
    dated: list[Work] = []
    citeseerx: list[Work] = []
    for work in leads:
        link, on_citeseerx = _xpac_link(work, raws[work.id])
        tails[work.id] = (f"  {work.venue}" if work.venue else "") + (f"  {link}" if link else "")
        (citeseerx if on_citeseerx else dated).append(work)

    # Uncapped, unlike the byline lists: these are bounded by the member's
    # own profiles, and the long tail is where a real paper sat among
    # page-text titles (dpsd-new, 2026-11-24).
    lines: list[str] = []
    if dated:
        lines.append(
            f"  XPAC only, not on the published list: {len(dated)} work(s), outside the "
            f"default fetch; add any that are theirs to {config.manual_path.name}"
        )
        lines.extend(_work_lines(dated, tails, cap=None))
    if citeseerx:
        lines.append(
            f"  CiteSeerX copies, XPAC only, not on the published list: {len(citeseerx)}; "
            f"each linked to the PDF it was indexed from where its record names one, and many "
            f"titled from page text "
            f"rather than the paper"
        )
        lines.extend(_work_lines(citeseerx, tails, cap=None))
    return lines


def _published_list(config: Config, overrides: list[Override]) -> tuple[_Published | None, str]:
    """The published list to compare bylines against, and what was compared."""
    path = config.output_path
    records = read_output(path)
    if records is not None:
        published = _Published.of(records, overrides)
        return published, f"compared against {path} ({len(records)} works)."
    if path.exists():
        return None, f"not checked; {path} is not a publications.json erga can read."
    return None, f"not checked; no published list at {path} yet (build first)."


def verify_report(config: Config, client: OpenAlexClient) -> tuple[str, list[str]]:
    """Human-readable report plus a list of warnings."""
    lines: list[str] = []
    warnings: list[str] = []
    # Curation loads first, as in build: a typo in it aborts before any
    # network traffic, whether or not a build has run yet.
    overrides = load_overrides(config.overrides_path, config.authors)
    published, published_note = _published_list(config, overrides)
    for author in config.authors:
        if author.tracking_only:
            lines.append(f"{author.name} (no ids; tracked by name only, nothing fetched)")
            lines.extend(_same_name_lines(client, author, set()))
            lines.extend(_unlinked_lines(client, author, [], config, published, overrides))
            lines.append("")
            continue
        identity = author.orcid or author.openalex_id or ""
        lines.append(f"{author.name} ({identity})")
        resolved = client.resolve_author(author)
        strangers = [p for p in resolved.profiles if not _looks_like(p, author)]

        if not resolved.profiles:
            lines.append("  resolved to no OpenAlex author")
            warnings.append(f"{author.name}: resolves to no OpenAlex author id")
        # The ORCID warnings judge only the profiles the ORCID resolved to: a
        # profile contributed by a pinned openalex_id says nothing about the
        # iD, and blaming the orcid for a mistyped pin inverts the advice.
        orcid_profiles = resolved.orcid_profiles
        orcid_strangers = [p for p in orcid_profiles if not _looks_like(p, author)]
        reported: list[AuthorProfile] = []
        if len(orcid_profiles) > 1:
            total = len(orcid_profiles)
            if orcid_strangers:
                example = orcid_strangers[0].display_name or orcid_strangers[0].id
                # Pinning drops every other profile, so when the only
                # mismatch is a script no word can cross, the alias comes
                # first: it keeps a real split's works (Stavrakis, dpsd-new).
                if all(_other_script(p, author) for p in orcid_strangers):
                    warnings.append(
                        f"{author.name}: ORCID is carried by {total} author profiles, and "
                        f"{example!r} is written in a script the configured names lack; "
                        f"if it is the same person, add it to aliases and keep the orcid, "
                        f"which fetches every profile; if not, remove the orcid and pin "
                        f"openalex_id"
                    )
                else:
                    warnings.append(
                        f"{author.name}: ORCID is carried by {total} author profiles that "
                        f"look like different people (e.g. {example!r}); fetching would pull "
                        f"strangers' works — remove the orcid and pin openalex_id instead"
                    )
                reported = orcid_strangers
            else:
                warnings.append(
                    f"{author.name}: ORCID resolves to {total} author ids (split profile); "
                    f"all are fetched, so pin openalex_id only if one holds works that "
                    f"are not theirs"
                )
        for stranger in [p for p in strangers if p not in reported]:
            hint = (
                "written in a script the configured names lack: add it to aliases if it is them"
                if _other_script(stranger, author)
                else "mistyped orcid or openalex_id?"
            )
            warnings.append(
                f"{author.name}: resolves to {stranger.display_name!r}, which does "
                f"not look like the configured name ({hint})"
            )

        total_works = 0
        for profile in resolved.profiles:
            total_works += profile.works_count
            lines.append(f"  {profile.id}  {profile.display_name} — {profile.works_count} works")
            if profile.alternatives:
                variants = "; ".join(profile.alternatives[:MAX_NAME_VARIANTS])
                lines.append(f"    also known as: {variants}")
            for raw in client.recent_works(profile.id, RECENT_TITLES):
                title = raw.get("title") or "(untitled)"
                year = raw.get("publication_year")
                lines.append(f"    recent: {title} ({year})")
            if profile.works_count > IMPLAUSIBLE_WORKS_COUNT:
                warnings.append(
                    f"{author.name}: profile {profile.id} has {profile.works_count} works "
                    f"(implausibly many; possibly conflated with another person)"
                )
        if resolved.profiles and total_works == 0:
            warnings.append(f"{author.name}: resolved profile(s) have zero works")
        lines.extend(_same_name_lines(client, author, set(resolved.ids)))
        lines.extend(_unlinked_lines(client, author, resolved.ids, config, published, overrides))
        lines.extend(_xpac_lines(client, resolved.ids, config, published, overrides))
        lines.append("")
    lines.append(f"Unlinked bylines: {published_note}")
    lines.append(
        "XPAC-only works: not listed; the config's include_xpac fetches them into the build."
        if config.include_xpac
        else f"XPAC-only works: {published_note}"
    )
    return "\n".join(lines).rstrip() + "\n", warnings
