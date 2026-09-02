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
left a fraction of a cluster per author — while the contamination that
motivated this is a cluster of four. That rate was measured before the two
corrections below and no longer describes this code; it has not been
re-measured, and docs/requirements-v1.md section 7 says why the direction
is not guessable.

"Stranger" is measured against the career, not the corpus. A homonym's works
usually come from one group, so counting collaborators across everything
fetched let those works vouch for each other and the cluster vanished. The
network is therefore built from the works that are not themselves outliers.

The check assumes the real career is the majority of the profile: home is the
country holding more than half the affiliated works, and everything else is
read as a deviation from it. Where that does not hold, the two sides are
structurally symmetric — a stranger's cluster looks exactly like a career with
a stranger's cluster in it — so the check stays silent rather than guess which
side is the career. A profile that is mostly someone else's work is a wrong
profile, which is `verify`'s question, not this one's.

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

# Under this many works at the home country, a "majority" describes a thin
# record rather than a career, and the check stays quiet.
MIN_HOME_WORKS = 5
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
                if not (institution.get("id") and institution.get("display_name")):
                    continue
                key = strip_openalex_host(institution["id"])
                country = institution.get("country_code")
                known = labels.get(key)
                # A country absent from one record must not erase one another
                # record carried: which entry lands last is an accident of
                # fetch order, and home institutions are matched on this.
                if known and country is None:
                    country = known[1]
                labels[key] = (institution["display_name"], country)
    return appearances, labels


def _view(appearance: _Appearance, tracked_id: str, labels: _Labels) -> _WorkView:
    """Reduce one work to what the check reasons about, from this author's seat."""
    raw, authorships, own = appearance
    institutions = {
        strip_openalex_host(institution["id"])
        for institution in own.get("institutions") or []
        if institution.get("id")
    }
    countries = {c for c in (own.get("countries") or []) if c}
    countries.update(
        country
        for institution_id in institutions
        if (country := labels.get(institution_id, ("", None))[1]) is not None
    )
    return _WorkView(
        work_id=strip_openalex_host(raw["id"]),
        title=raw.get("title") or "",
        countries=frozenset(countries),
        institutions=frozenset(institutions),
        team=frozenset(author_id for author_id, _ in authorships if author_id != tracked_id),
    )


def _clusters_for(author: str, views: list[_WorkView], labels: _Labels) -> list[Cluster]:
    affiliated = [v for v in views if v.countries or v.institutions]
    country_counts = Counter(c for v in affiliated for c in v.countries)
    if not country_counts:
        return []
    # Most frequent country, alphabetical on ties so the report is stable.
    home, home_works = min(country_counts.items(), key=lambda item: (-item[1], item[0]))

    # Everything downstream reads as a deviation from home, so a home that is
    # merely the largest minority cannot carry that weight. On a thin record a
    # big enough stranger cluster wins the count, and the check then reports
    # the genuine career as the anomaly — the exact inversion of its purpose.
    # A plain majority is not enough either: at four against four the tie broke
    # alphabetically, by country code.
    if home_works < MIN_HOME_WORKS or home_works * 2 <= len(affiliated):
        return []

    # Only institutions that are themselves at home. Taking every institution
    # co-listed on a home work instead let one dual-affiliation paper whitelist
    # a foreign institution for the whole career, and every later cluster there
    # went unreported.
    home_institutions = {
        i
        for v in affiliated
        if home in v.countries
        for i in v.institutions
        if labels.get(i, ("", None))[1] == home
    }

    outliers = [
        v
        for v in affiliated
        if v.team and home not in v.countries and not (v.institutions & home_institutions)
    ]
    outlying = {v.work_id for v in outliers}

    # The career's own network: every work that is not itself an affiliation
    # outlier, including works with no affiliation at all, since a shared
    # co-author vouches for a work either way. Outliers are held out because
    # a stranger's works must not vouch for each other — counting them let a
    # whole foreign lab pass, which is the likeliest shape of the real thing.
    network = Counter(author_id for v in views if v.work_id not in outlying for author_id in v.team)

    candidates = [v for v in outliers if not any(network[a] for a in v.team)]

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
                # Positional, one per work id, empty where OpenAlex has no
                # title. Filtering the blanks out here silently misaligned the
                # two lists for anything that reads them as pairs.
                titles=[v.title for v in remaining],
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
        views = [_view(a, tracked_id, labels) for a in appearances.get(tracked_id, [])]
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
        # First work with a title, since titles are positional and some are
        # empty; an untitled first work should not cost the reader the example.
        sample = next((title for title in cluster.titles if title), None)
        example = f" (e.g. {sample!r})" if sample else ""
        warnings.append(
            f"{cluster.author}: {len(cluster.work_ids)} work(s) tie to {where}, sharing no "
            f"institution and no collaborator with the rest of the profile{example} — a "
            f"same-name stranger's works look like this; exclude them by DOI if so"
        )
    return warnings
