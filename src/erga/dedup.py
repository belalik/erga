"""DOI-level and title-cluster deduplication.

Both stages share one ranking: manual entries first, then version-of-record
over repository deposits, then has-DOI, citation count, newest, with the
smallest id as the deterministic tiebreak. The winner inherits abstract and
open-access URL from the copies it absorbs.
"""

from __future__ import annotations

import unicodedata

from erga.model import Work

# DOI prefixes of repository deposits that lose to a version of record:
# arXiv, Zenodo, figshare, Research Square, bioRxiv/medRxiv, SSRN, OSF.
REPOSITORY_DOI_PREFIXES = frozenset(
    {
        "10.48550",
        "10.5281",
        "10.6084",
        "10.21203",
        "10.1101",
        "10.2139",
        "10.17605",
        "10.31219",
        "10.31234",
        "10.31235",
    }
)

MIN_CLUSTER_TITLE_LENGTH = 12


def normalize_title(title: str) -> str:
    """Clustering key: NFKD minus accents, casefolded, punctuation and dash
    variants folded to single spaces."""
    decomposed = unicodedata.normalize("NFKD", title)
    chars = [ch if ch.isalnum() else " " for ch in decomposed if unicodedata.category(ch) != "Mn"]
    return " ".join("".join(chars).casefold().split())


def is_repository_deposit(work: Work) -> bool:
    if work.type == "preprint":
        return True
    key = work.doi_key
    return key is not None and key.split("/", 1)[0] in REPOSITORY_DOI_PREFIXES


def _rank_key(work: Work) -> tuple[bool, bool, bool, int, str]:
    return (
        work.source == "manual",
        not is_repository_deposit(work),
        work.doi is not None,
        work.cited_by_count,
        work.date or "",
    )


def merge_group(group: list[Work]) -> Work:
    """Pick the group's winner and let it inherit what it lacks."""
    ordered = sorted(sorted(group, key=lambda w: w.id), key=_rank_key, reverse=True)
    winner = ordered[0]
    for absorbed in ordered[1:]:
        winner.abstract = winner.abstract or absorbed.abstract
        winner.open_access_url = winner.open_access_url or absorbed.open_access_url
    return winner


def _dedup(works: list[Work], key_of: dict[int, object]) -> list[Work]:
    """Collapse works sharing a key; keyless works pass through untouched."""
    groups: dict[object, list[Work]] = {}
    for work in works:
        key = key_of.get(id(work))
        if key is not None:
            groups.setdefault(key, []).append(work)
    winners = {id(merge_group(group)) for group in groups.values()}
    return [w for w in works if id(w) in winners or key_of.get(id(w)) is None]


def dedup_by_doi(works: list[Work]) -> list[Work]:
    """Collapse records sharing a DOI, case-insensitively."""
    keys: dict[int, object] = {id(w): w.doi_key for w in works}
    return _dedup(works, keys)


def cluster_by_title(works: list[Work]) -> list[Work]:
    """Collapse records sharing a normalized title.

    Datasets never merge with papers (the key includes is-dataset). Titles
    under MIN_CLUSTER_TITLE_LENGTH normalized characters and keep_distinct
    records bypass clustering entirely.
    """
    keys: dict[int, object] = {}
    for work in works:
        normalized = normalize_title(work.title)
        if len(normalized) >= MIN_CLUSTER_TITLE_LENGTH and not work.keep_distinct:
            keys[id(work)] = (normalized, work.type == "dataset")
        else:
            keys[id(work)] = None
    return _dedup(works, keys)
