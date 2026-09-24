"""The build pipeline (requirements section 7)."""

from __future__ import annotations

from dataclasses import dataclass, field

from erga.config import Config
from erga.contamination import (
    DeclaredHome,
    contamination_warnings,
    find_contamination,
    institution_index,
)
from erga.crossref import CrossrefClient
from erga.curation import (
    apply_overrides,
    apply_tags,
    load_manual,
    load_overrides,
    load_tags,
    mark_keep_distinct,
    redundant_overrides,
    unmatched_overrides,
)
from erga.dedup import cluster_by_title, dedup_by_doi
from erga.delta import Delta, compute_delta
from erga.errors import ConfigError, FetchError
from erga.model import Work
from erga.normalize import malformed_dois, normalize_work, unmapped_types
from erga.openalex import OpenAlexClient
from erga.output import document, dump, previous_venues, read_output, write_atomic


def _declared_homes(
    declarations: dict[str, tuple[str, ...] | None],
    raw_works: list[dict[str, object]],
    openalex: OpenAlexClient,
) -> dict[str, tuple[DeclaredHome, ...]]:
    """Resolve each declared ROR once, then attach it to every profile it covers.

    The corpus answers most declarations for free, since every authorship
    carries both identifiers; only a ROR it never names, or names without a
    country, costs a lookup. Resolution runs after the works fetch for that
    reason, which is safe because nothing is written until the build ends.

    An unresolvable declaration aborts. Falling back to the inferred rule
    would leave two runs with the same config and the same corpus printing
    different advice — cluster warnings that say to exclude works by DOI,
    instead of the verdict that the profile itself is wrong — with nothing
    in the output to say which rule ran.
    """
    declared = {openalex_id: rors for openalex_id, rors in declarations.items() if rors}
    if not declared:
        return {}

    corpus = institution_index(raw_works)
    resolved: dict[str, DeclaredHome] = {}
    for ror in sorted({ror for rors in declared.values() for ror in rors}):
        found = corpus.get(ror)
        if found is None or found[1] is None:
            found = openalex.resolve_institution(ror)
        if found is None:
            raise ConfigError(f"home: ROR {ror} names no OpenAlex institution")
        institution_id, country = found
        if country is None:
            raise ConfigError(f"home: ROR {ror} has no country in OpenAlex; it cannot be a home")
        resolved[ror] = DeclaredHome(institution_id=institution_id, country=country)

    return {
        openalex_id: tuple(resolved[ror] for ror in rors) for openalex_id, rors in declared.items()
    }


@dataclass
class BuildStats:
    fetched: int = 0
    manual: int = 0
    deduplicated: int = 0
    excluded: int = 0
    excluded_types: int = 0
    backfilled_previous: int = 0
    backfilled_crossref: int = 0
    total: int = 0
    written: bool = False
    warnings: list[str] = field(default_factory=list)
    # What changed against the output file the build found in place.
    delta: Delta = field(default_factory=lambda: Delta(total=0))

    def summary(self) -> str:
        return (
            f"fetched {self.fetched}, manual {self.manual}, "
            f"deduplicated {self.deduplicated}, excluded {self.excluded}, "
            f"excluded by type {self.excluded_types}, "
            f"backfilled {self.backfilled_previous + self.backfilled_crossref} "
            f"({self.backfilled_previous} from previous output, "
            f"{self.backfilled_crossref} from Crossref), "
            f"total {self.total}"
        )


def exclude_by_type(works: list[Work], types: frozenset[str]) -> tuple[list[Work], int]:
    """Drop fetched records of unwanted types (editorial front matter, errata).

    `keep` records are exempt: manual entries carry it from construction, and
    an explicit `exclude: false` override rescues an individual fetched
    record. Runs after overrides so a patched type is judged in its corrected
    form.
    """
    if not types:
        return works, 0
    kept = [w for w in works if w.type not in types or w.keep]
    return kept, len(works) - len(kept)


def backfill_venues(
    works: list[Work], previous: dict[str, str], crossref: CrossrefClient, stats: BuildStats
) -> None:
    """Fill missing venues: previous output first, then Crossref.

    A persistent Crossref failure stops the backfill with a warning instead
    of aborting the run; the ratchet means already-known venues survived, and
    the next run retries the rest.
    """
    for work in works:
        if work.venue is not None:
            continue
        key = work.doi_key
        known = (key and previous.get(key)) or previous.get(work.id)
        if known:
            work.venue = known
            stats.backfilled_previous += 1
    for work in works:
        if work.venue is not None or not work.doi_key:
            continue
        try:
            venue = crossref.venue_for_doi(work.doi_key)
        except FetchError as exc:
            stats.warnings.append(f"Crossref backfill stopped: {exc}")
            return
        if venue:
            work.venue = venue
            stats.backfilled_crossref += 1


def build(
    config: Config,
    openalex: OpenAlexClient,
    crossref: CrossrefClient,
    *,
    dry_run: bool = False,
) -> BuildStats:
    stats = BuildStats()

    # Curation loads first: a typo in a curation file must abort before any
    # network traffic.
    manual = load_manual(config.manual_path, config.authors)
    overrides = load_overrides(config.overrides_path)
    tags = load_tags(config.tags_path)

    # Each mapping resolves a match key to the configured author's canonical
    # name, which the output carries as authors[].tracked_as.
    tracked_ids: dict[str, str] = {}
    # A declaration is made about a person, and one person can resolve to
    # several profiles; spreading it over all of them is what stops a split
    # identity from being half-declared.
    declarations: dict[str, tuple[str, ...] | None] = {}
    for author in config.authors:
        # Tracking-only entries resolve to nothing by construction, no
        # network involved; that is not the failure this error guards.
        resolved = openalex.resolve_author(author)
        if not author.tracking_only and not resolved.ids:
            raise FetchError(
                f"author {author.name!r}: ORCID {author.orcid} resolved to no "
                f"OpenAlex author; check it or pin openalex_id (see `erga verify`)"
            )
        tracked_ids.update((openalex_id, author.name) for openalex_id in resolved.ids)
        # Recorded for every id including the opt-outs, not only the declared
        # ones. Two configured entries can resolve to one profile, and the
        # name above already lets the later win; a `home: null` that could
        # not clear an earlier entry's declaration would leave the person who
        # opted out being checked against someone else's institution.
        declarations.update((openalex_id, author.home) for openalex_id in resolved.ids)
    tracked_orcids = {a.orcid: a.name for a in config.authors if a.orcid}
    tracked_names = {name: a.name for a in config.authors for name in a.match_names()}

    raw_works = openalex.fetch_works(sorted(tracked_ids), include_xpac=config.include_xpac)
    stats.fetched = len(raw_works)

    works = manual + [
        normalize_work(raw, tracked_ids, tracked_orcids, tracked_names) for raw in raw_works
    ]
    stats.manual = len(manual)
    stats.warnings.extend(
        f'unmapped OpenAlex type {raw_type!r} on {count} work(s) falls back to "other" '
        f"(upstream vocabulary drift?)"
        for raw_type, count in unmapped_types(raw_works).items()
    )
    if malformed := malformed_dois(raw_works):
        stats.warnings.append(
            f"OpenAlex's DOI field held more than a DOI on {len(malformed)} work(s) "
            f"(e.g. {', '.join(malformed[:3])}); only the DOI is kept"
        )
    # Reads the raw works, not the canonical ones: affiliation is what the
    # check reasons about and the canonical record deliberately drops it.
    homes = _declared_homes(declarations, raw_works, openalex)
    stats.warnings.extend(contamination_warnings(find_contamination(raw_works, tracked_ids, homes)))

    mark_keep_distinct(works, overrides)
    before = len(works)
    works = cluster_by_title(dedup_by_doi(works))
    stats.deduplicated = before - len(works)

    works, stats.excluded = apply_overrides(works, overrides, config.authors)
    stats.warnings.extend(f"override matched nothing: {w}" for w in unmatched_overrides(overrides))
    stats.warnings.extend(
        f"override redundant (upstream now agrees; kept as-is): {w}"
        for w in redundant_overrides(overrides)
    )

    works, stats.excluded_types = exclude_by_type(works, config.exclude_types)

    # Read once: the previous output feeds the venue ratchet here and the
    # delta below, and it must be the file as found, before it is replaced.
    previous = read_output(config.output_path)
    if previous is None and config.output_path.exists():
        # Never abort a build over the previous file, but a file that is in
        # place and unreadable is a mistake to report, not a first build.
        stats.warnings.append(
            f"{config.output_path}: not a publications.json erga can read; "
            "treated as a first build, so nothing was compared or ratcheted"
        )
    backfill_venues(works, previous_venues(previous), crossref, stats)

    stats.warnings.extend(f"tag matched nothing: {w}" for w in apply_tags(works, tags))

    stats.total = len(works)
    doc = document(works)
    stats.delta = compute_delta(previous, doc["works"])
    stats.warnings.extend(stats.delta.warnings())
    if not dry_run:
        write_atomic(config.output_path, dump(doc))
        stats.written = True
    return stats
