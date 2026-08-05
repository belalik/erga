"""The build pipeline (requirements section 7)."""

from __future__ import annotations

from dataclasses import dataclass, field

from erga.config import Config
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
from erga.errors import FetchError
from erga.model import Work
from erga.normalize import normalize_work, unmapped_types
from erga.openalex import OpenAlexClient
from erga.output import previous_venues, render, write_atomic


@dataclass
class BuildStats:
    fetched: int = 0
    manual: int = 0
    deduplicated: int = 0
    excluded: int = 0
    backfilled_previous: int = 0
    backfilled_crossref: int = 0
    total: int = 0
    written: bool = False
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"fetched {self.fetched}, manual {self.manual}, "
            f"deduplicated {self.deduplicated}, excluded {self.excluded}, "
            f"backfilled {self.backfilled_previous + self.backfilled_crossref} "
            f"({self.backfilled_previous} from previous output, "
            f"{self.backfilled_crossref} from Crossref), "
            f"total {self.total}"
        )


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

    tracked_ids: set[str] = set()
    for author in config.authors:
        # Tracking-only entries resolve to nothing by construction, no
        # network involved; that is not the failure this error guards.
        resolved = openalex.resolve_author(author)
        if not author.tracking_only and not resolved.ids:
            raise FetchError(
                f"author {author.name!r}: ORCID {author.orcid} resolved to no "
                f"OpenAlex author; check it or pin openalex_id (see `erga verify`)"
            )
        tracked_ids.update(resolved.ids)
    tracked_orcids = {a.orcid for a in config.authors if a.orcid}
    tracked_names = {name for a in config.authors for name in a.match_names()}

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

    backfill_venues(works, previous_venues(config.output_path), crossref, stats)

    stats.warnings.extend(f"tag matched nothing: {w}" for w in apply_tags(works, tags))

    stats.total = len(works)
    if not dry_run:
        write_atomic(config.output_path, render(works))
        stats.written = True
    return stats
