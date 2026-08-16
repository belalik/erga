"""Strangers' works inside a correctly-named profile.

`verify` compares names, so it is blind to a homonym who Latinizes to the
same string: a Czech Kateřina Mališová and a Greek Katerina Malisova are one
name to OpenAlex, and four of the former's works reached the latter's
department page before a human noticed every co-author was Czech.

The signal is deliberately conjunctive, because neither half survives real
careers alone. Measured over 40 sampled careers: "worked abroad" flags 7.4%
of all works, because academics move and collaborate; "team of strangers"
flags 9.5%, because new collaborations are constant. Requiring both, and
then requiring a cluster of at least two works sharing one institution,
leaves 3 clusters across those 40 authors — while the contamination that
motivated this is a cluster of four.

Two silences are as important as the signal. A work with no affiliation
data is never anomalous: roughly a third carry none, so absence means the
check has nothing to say. A solo-authored work has no team to be a stranger
to, so it cannot be judged this way either.

What comes out is informational. erga surfaces the cluster; deciding whether
it is a homonym, and excluding it, is the maintainer's call in the overrides
file.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from erga.openalex import strip_openalex_host

# Under this many affiliated works, a "majority country" describes a thin
# record rather than a career, and the check stays quiet.
MIN_AFFILIATED_WORKS = 5
# Contamination arrives as a run from one place; a single paper abroad is
# ordinary academic life, and singletons were most of the residual noise.
MIN_CLUSTER = 2


@dataclass(frozen=True)
class Cluster:
    """Works tied to one institution that look like a different career."""

    author: str
    institution: str
    country: str | None
    work_ids: list[str]
    titles: list[str]


@dataclass(frozen=True)
class _WorkView:
    """One work reduced to what the check reasons about."""

    work_id: str
    title: str
    countries: frozenset[str]
    institutions: frozenset[str]
    team: frozenset[str]


# (bare author id, authorship entry) pairs for one work.
_Authorships = list[tuple[str, dict[str, Any]]]
# One work as a tracked author appears on it: the work, every authorship,
# and that author's own entry.
_Appearance = tuple[dict[str, Any], _Authorships, dict[str, Any]]
# Institution id to the (name, country) the report prints for it.
_Labels = dict[str, tuple[str, str | None]]


def _identified_authorships(raw: dict[str, Any]) -> _Authorships:
    """(bare author id, authorship) for authors OpenAlex could identify."""
    pairs = []
    for entry in raw.get("authorships") or []:
        author = entry.get("author") or {}
        if author.get("id"):
            pairs.append((strip_openalex_host(author["id"]), entry))
    return pairs


def _index(
    raw_works: list[dict[str, Any]], tracked_ids: dict[str, str]
) -> tuple[dict[str, list[_Appearance]], _Labels]:
    """One pass over the corpus: who appears where, and institution labels.

    The corpus is a single fetch for every tracked author, so walking it once
    per author would cost authors x works; this walks it once. Labels come
    from the same pass because an institution's name is a fact about the
    corpus, not about whoever is being checked.
    """
    appearances: dict[str, list[_Appearance]] = defaultdict(list)
    labels: _Labels = {}
    for raw in raw_works:
        authorships = _identified_authorships(raw)
        seen: set[str] = set()
        for author_id, entry in authorships:
            # An author listed twice on one work is still one appearance.
            if author_id not in tracked_ids or author_id in seen:
                continue
            seen.add(author_id)
            appearances[author_id].append((raw, authorships, entry))
            for institution in entry.get("institutions") or []:
                if institution.get("id") and institution.get("display_name"):
                    labels[strip_openalex_host(institution["id"])] = (
                        institution["display_name"],
                        institution.get("country_code"),
                    )
    return appearances, labels


def _view(appearance: _Appearance, tracked_id: str) -> _WorkView:
    """Reduce one work to what the check reasons about, from this author's seat."""
    raw, authorships, own = appearance
    institutions = {
        strip_openalex_host(institution["id"])
        for institution in own.get("institutions") or []
        if institution.get("id")
    }
    return _WorkView(
        work_id=strip_openalex_host(raw["id"]),
        title=raw.get("title") or "",
        countries=frozenset(c for c in (own.get("countries") or []) if c),
        institutions=frozenset(institutions),
        team=frozenset(author_id for author_id, _ in authorships if author_id != tracked_id),
    )


def _clusters_for(author: str, views: list[_WorkView], labels: _Labels) -> list[Cluster]:
    affiliated = [v for v in views if v.countries or v.institutions]
    if len(affiliated) < MIN_AFFILIATED_WORKS:
        return []

    country_counts = Counter(c for v in affiliated for c in v.countries)
    if not country_counts:
        return []
    # Most frequent country, alphabetical on ties so the report is stable.
    home = min(country_counts.items(), key=lambda item: (-item[1], item[0]))[0]
    home_institutions = {i for v in affiliated if home in v.countries for i in v.institutions}

    # The collaboration network spans the whole corpus, including works with
    # no affiliation: a shared co-author vouches for a work either way.
    collaborators = Counter(author_id for v in views for author_id in v.team)

    candidates = [
        v
        for v in affiliated
        if v.team
        and home not in v.countries
        and not (v.institutions & home_institutions)
        and all(collaborators[author_id] <= 1 for author_id in v.team)
    ]

    by_institution: dict[str, list[_WorkView]] = defaultdict(list)
    for view in candidates:
        for institution_id in view.institutions:
            by_institution[institution_id].append(view)

    # Largest cluster first, so a work co-affiliated to two foreign places is
    # reported once, under the institution that gathers the most of them.
    clusters: list[Cluster] = []
    claimed: set[str] = set()
    ordered = sorted(by_institution.items(), key=lambda item: (-len(item[1]), item[0]))
    for institution_id, members in ordered:
        remaining = sorted(
            (v for v in members if v.work_id not in claimed), key=lambda v: v.work_id
        )
        if len(remaining) < MIN_CLUSTER:
            continue
        claimed.update(v.work_id for v in remaining)
        name, country = labels.get(institution_id, (institution_id, None))
        clusters.append(
            Cluster(
                author=author,
                institution=name,
                country=country,
                work_ids=[v.work_id for v in remaining],
                titles=[v.title for v in remaining if v.title],
            )
        )
    return sorted(clusters, key=lambda c: (c.institution, c.work_ids[0]))


def find_contamination(
    raw_works: list[dict[str, Any]], tracked_ids: dict[str, str]
) -> list[Cluster]:
    """Clusters of works that look like they belong to someone else.

    `tracked_ids` maps resolved OpenAlex author ids to the configured
    author's canonical name, exactly as the normalize stage receives it. Each
    tracked author is judged against their own corpus, so a work shared by
    two configured colleagues is read once per person.
    """
    appearances, labels = _index(raw_works, tracked_ids)
    clusters: list[Cluster] = []
    for tracked_id in sorted(tracked_ids):
        views = [_view(a, tracked_id) for a in appearances.get(tracked_id, [])]
        clusters.extend(_clusters_for(tracked_ids[tracked_id], views, labels))
    return clusters


def contamination_warnings(clusters: Iterable[Cluster]) -> list[str]:
    """One warning per cluster, phrased as a question for the maintainer."""
    warnings = []
    for cluster in clusters:
        where = (
            f"{cluster.institution} ({cluster.country})"
            if cluster.country
            else (cluster.institution)
        )
        example = f" (e.g. {cluster.titles[0]!r})" if cluster.titles else ""
        warnings.append(
            f"{cluster.author}: {len(cluster.work_ids)} work(s) tie to {where}, sharing no "
            f"institution and no collaborator with the rest of the profile{example} — a "
            f"same-name stranger's works look like this; exclude them by DOI if so"
        )
    return warnings
