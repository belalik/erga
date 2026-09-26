"""The author-disambiguation report.

OpenAlex author identities split and conflate people, so this is a
first-class feature: it shows what each configured author actually resolves
to before a build trusts those ids.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from erga.config import AuthorConfig, Config
from erga.dedup import cluster_by_title, dedup_by_doi, merge_group, normalize_title, title_key
from erga.model import Work
from erga.normalize import normalize_work
from erga.openalex import AuthorProfile, OpenAlexClient, strip_openalex_host
from erga.output import read_output, sort_works, work_from_record
from erga.pipeline import exclude_by_type

IMPLAUSIBLE_WORKS_COUNT = 2000
RECENT_TITLES = 3
MAX_NAME_VARIANTS = 5
MAX_SAME_NAME = 5
MAX_UNLINKED = 10
# A byline search past this many works has found a common name, not a person.
BYLINE_SEARCH_LIMIT = 1000


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


def _same_name_lines(
    client: OpenAlexClient, author: AuthorConfig, known_ids: set[str]
) -> list[str]:
    """Profiles a name search surfaces beyond the configured/resolved ids.

    These are what a configured id can never show: homonyms, and conflated
    profiles that hold works OpenAlex misassigned. Informational, not
    warnings: same-name strangers are common and only a human can judge them.
    """
    profiles, total = client.search_authors(author.name)
    others = [p for p in profiles if p.id not in known_ids]
    lines = [
        f"  same name, not configured: {p.id}  {p.display_name} — {p.works_count} works"
        for p in others[:MAX_SAME_NAME]
    ]
    # Matches beyond the fetched page, plus fetched ones past the display cap.
    unshown = (total - len(profiles)) + len(others[MAX_SAME_NAME:])
    if unshown > 0:
        lines.append(f"  … and {unshown} more name match(es) on OpenAlex")
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

    ids: set[str] = field(default_factory=set)
    dois: set[str] = field(default_factory=set)
    titles: dict[tuple[str, bool], list[Work]] = field(default_factory=dict)

    @classmethod
    def of(cls, records: list[dict[str, Any]]) -> _Published:
        published = cls()
        for work in map(work_from_record, records):
            published.ids.add(work.id)
            if work.doi_key:
                published.dois.add(work.doi_key)
            key = title_key(work.title, work.type)
            if key is not None:
                published.titles.setdefault(key, []).append(work)
        return published


def _byline_candidates(
    client: OpenAlexClient, author: AuthorConfig, own_ids: list[str], config: Config
) -> tuple[list[Work], dict[str, str], list[str]]:
    """Works off the author's profiles whose unlinked byline carries their name.

    Returned as a build would keep them, with the matching byline by work
    id and a line for each name too common to search.
    """
    # One search per distinct name, distinct as match_names() counts them.
    unique: dict[str, str] = {}
    for name in [author.name, *author.aliases]:
        unique.setdefault(name.casefold().strip(), name)
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
    works = [normalize_work(raw, {}, {}, {}) for raw in raws]
    # The build's order: versions of one work (a dataset's releases, a
    # deposit beside its published copy) collapse, then types drop.
    works, _ = exclude_by_type(cluster_by_title(dedup_by_doi(works)), config.exclude_types)
    return works, bylines, skipped


def _unlinked_lines(
    client: OpenAlexClient,
    author: AuthorConfig,
    own_ids: list[str],
    config: Config,
    published: _Published | None,
) -> list[str]:
    """Works carrying the author's name with no author id, missing from the list.

    No profile fetch can see these: the authorship names them but links no
    one. Informational, like the same-name lines: a namesake's byline looks
    the same, and only a human can tell, so the remedy is a manual entry.
    Compared against the published list rather than a fresh fetch, because
    that is what a member reads and it already holds the manual entries,
    overrides and type exclusions.
    """
    if published is None:
        return []
    works, bylines, lines = _byline_candidates(client, author, own_ids, config)
    missing: list[Work] = []
    better: list[tuple[Work, list[str]]] = []
    for work in works:
        if work.id in published.ids or (work.doi_key and work.doi_key in published.dois):
            continue
        key = title_key(work.title, work.type)
        twins = published.titles.get(key, []) if key else []
        if not twins:
            missing.append(work)
        elif (
            work.doi and not any(twin.doi for twin in twins) and merge_group([*twins, work]) is work
        ):
            # Dedup would keep this record over the listed copy, which lacks
            # the DOI it carries: a repair, not a gap. A deposit's DOI loses
            # to a listed version of record and is no repair.
            better.append((work, sorted(twin.id for twin in twins)))

    if missing:
        lines.append(
            f"  name in the byline, no author id, not on the published list: "
            f"{len(missing)} work(s); add any that are theirs to {config.manual_path.name}"
        )
        for work in sort_works(missing)[:MAX_UNLINKED]:
            year = f" ({work.year})" if work.year else ""
            doi = f"  {work.doi_key}" if work.doi_key else ""
            title = work.title or "(untitled)"
            lines.append(f"    {work.id}  {title}{year}{doi}  as {bylines[work.id]!r}")
        if len(missing) > MAX_UNLINKED:
            lines.append(f"    … and {len(missing) - MAX_UNLINKED} more")
    for work, listed in sorted(better, key=lambda pair: pair[0].id):
        lines.append(
            f"  better record for a listed work: {work.id} carries {work.doi_key}; "
            f"listed as {', '.join(listed)} without a DOI"
        )
    return lines


def _published_list(config: Config) -> tuple[_Published | None, str]:
    """The published list to compare bylines against, and what was compared."""
    path = config.output_path
    records = read_output(path)
    if records is not None:
        return _Published.of(records), f"compared against {path} ({len(records)} works)."
    if path.exists():
        return None, f"not checked; {path} is not a publications.json erga can read."
    return None, f"not checked; no published list at {path} yet (build first)."


def verify_report(config: Config, client: OpenAlexClient) -> tuple[str, list[str]]:
    """Human-readable report plus a list of warnings."""
    lines: list[str] = []
    warnings: list[str] = []
    published, published_note = _published_list(config)
    for author in config.authors:
        if author.tracking_only:
            lines.append(f"{author.name} (no ids; tracked by name only, nothing fetched)")
            lines.extend(_same_name_lines(client, author, set()))
            lines.extend(_unlinked_lines(client, author, [], config, published))
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
                warnings.append(
                    f"{author.name}: ORCID is carried by {total} author profiles that "
                    f"look like different people (e.g. {example!r}); fetching would pull "
                    f"strangers' works — remove the orcid and pin openalex_id instead"
                )
                reported = orcid_strangers
            else:
                warnings.append(
                    f"{author.name}: ORCID resolves to {total} author ids "
                    f"(split profile; consider pinning openalex_id)"
                )
        for stranger in [p for p in strangers if p not in reported]:
            warnings.append(
                f"{author.name}: resolves to {stranger.display_name!r}, which does "
                f"not look like the configured name (mistyped orcid or openalex_id?)"
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
        lines.extend(_unlinked_lines(client, author, resolved.ids, config, published))
        lines.append("")
    lines.append(f"Unlinked bylines: {published_note}")
    return "\n".join(lines).rstrip() + "\n", warnings
