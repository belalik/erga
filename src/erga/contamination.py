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
motivated this is a cluster of four. Re-measured on 2026-09-02 with the
corrections below in place: 0.25 clusters per author on the original
80-400-work band and 0.23 on a 20-80 band, both upper bounds since the
samples carry no labelled positives; docs/requirements-v1.md section 7 has
the detail.

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

A declared home changes that one thing. Where the config names the
institutions an author's record belongs to (`home:`, requirements section
5), home stops being inferred and the symmetry breaks: an arbiter exists, so
which side is away becomes a fact rather than a guess, and this module says
so — a `ProfileMismatch`, carrying no exclusion advice and pointing at
`verify` for the identity question it still does not answer. It is decided
here because the affiliation data that decides it lives only here; `verify`
compares names and never sees a work.

A declaration can name several places, because careers move. Someone who
joined the declared institution recently has most of their record at a
previous employer, and against one declared place that reads as a wrong
profile by construction (consumer #2, 2026-09-22). The declaration orients
one career; it is not a check on where the author works now. Inferring the
move from the data instead, by collaborators shared across it, was measured
and rejected on 2026-09-23: a shared co-author proves one career, not a
right declaration, and one consortium author can bridge two people.

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
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from erga.model import bare_ror
from erga.openalex import strip_openalex_host

# Under this many works at the home country, a "majority" describes a thin
# record rather than a career, and the check stays quiet.
MIN_HOME_WORKS = 5
# Contamination arrives as a run from one place; a single paper abroad is
# ordinary academic life, and singletons were most of the residual noise.
MIN_CLUSTER = 2


def _is_majority(count: int, total: int) -> bool:
    """More than half, never exactly half.

    One predicate for both paths: a tie is not a majority, which is what
    kept the inferred rule from breaking four-against-four alphabetically,
    and what keeps a declared home from calling an even split a wrong
    profile. A threshold change has one place to land.
    """
    return count * 2 > total


@dataclass(frozen=True)
class Cluster:
    """Works tied to one institution that look like a different career."""

    author: str
    institution: str
    country: str | None
    work_ids: list[str]
    titles: list[str]


@dataclass(frozen=True)
class DeclaredHome:
    """One place the maintainer says an author's record belongs, resolved to the corpus."""

    institution_id: str
    country: str


@dataclass(frozen=True)
class ProfileMismatch:
    """A declaration that most of the profile's established works contradict.

    Only reachable under a declaration. Without one the same shape is
    silence, because nothing says which side is the career; with one, saying
    so is the whole point of the field.
    """

    author: str
    # Every declared place's country, sorted: what "outside" is measured against.
    countries: tuple[str, ...]
    home_works: int
    away_works: int


# What the check can report. A mismatch is about the profile, a cluster about
# works inside it, and the two are mutually exclusive per author.
Finding = Cluster | ProfileMismatch


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
    # An entry can name the institution and still carry no country. Such works
    # counted against home in the majority test without ever voting for it,
    # and enough of them silenced the check on a genuine career; the label
    # supplies what the entry dropped.
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


def _home_institutions(
    affiliated: list[_WorkView], homes: frozenset[str], labels: _Labels
) -> set[str]:
    """Institutions that are themselves at home.

    Taking every institution co-listed on a home work instead let one
    dual-affiliation paper whitelist a foreign institution for the whole
    career, and every later cluster there went unreported. Independent
    country evidence is the qualification; sitting beside a home institution
    is not, and a declaration does not change that for anything but itself.
    """
    return {
        i
        for v in affiliated
        if v.countries & homes
        for i in v.institutions
        if labels.get(i, ("", None))[1] in homes
    }


def _affiliated(views: list[_WorkView]) -> list[_WorkView]:
    """Views carrying at least one piece of affiliation evidence."""
    return [view for view in views if view.countries or view.institutions]


def _clusters_for(author: str, views: list[_WorkView], labels: _Labels) -> list[Cluster]:
    affiliated = _affiliated(views)
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
    if home_works < MIN_HOME_WORKS or not _is_majority(home_works, len(affiliated)):
        return []

    homes = frozenset({home})
    return _cluster_works(
        author, views, affiliated, homes, _home_institutions(affiliated, homes, labels), labels
    )


def _cluster_works(
    author: str,
    views: list[_WorkView],
    affiliated: list[_WorkView],
    homes: frozenset[str],
    home_institutions: set[str],
    labels: _Labels,
) -> list[Cluster]:
    """Group the works that look like a different career, given home.

    Everything above this decides *where* home is; this decides which works
    depart from it, and is identical whether home was counted or declared.
    Counted, home is one country; declared, it is every declared place's.
    """
    outliers = [
        v
        for v in affiliated
        if v.team and not (v.countries & homes) and not (v.institutions & home_institutions)
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


def _declared_for(
    author: str, views: list[_WorkView], labels: _Labels, declared: tuple[DeclaredHome, ...]
) -> list[Finding]:
    """The same check, oriented by a declaration instead of by the counts.

    A declaration answers only *where* home is, so the majority test that
    chose it is gone; nothing a stranger cluster can do wins the baseline
    now. What it does not answer is whether there is enough of a career here
    to reason about, so the thin-record floor stays: the maintainer supplied
    where home is, not that three works characterize a career.

    The denominator narrows to works whose affiliation positively places
    them somewhere. Under the inferred rule a work naming an institution
    with no country anywhere dilutes the count and can silence the check,
    which is deliberate when home is a guess and pointless when it is
    declared.

    Several declared places are one home: a work at any of them is at home,
    and each makes its own country home, as a single declaration always has.
    """
    affiliated = _affiliated(views)
    homes = frozenset(place.country for place in declared)
    declared_institutions = frozenset(place.institution_id for place in declared)

    def at_declared_home(view: _WorkView) -> bool:
        return bool(view.countries & homes or view.institutions & declared_institutions)

    at_home = [v for v in affiliated if at_declared_home(v)]
    # Away is a positive finding, never the complement of home: a work that
    # names an institution the corpus never gave a country to is evidence of
    # nothing and must not vote against the declaration.
    away = [v for v in affiliated if v.countries and not at_declared_home(v)]

    comparable = len(at_home) + len(away)
    if comparable < MIN_HOME_WORKS:
        return []

    # A profile whose established works are mostly elsewhere is a wrong
    # profile, which is `verify`'s question — so say that, instead of
    # reporting the majority of the career as strangers to it.
    if _is_majority(len(away), comparable):
        return [
            ProfileMismatch(
                author=author,
                countries=tuple(sorted(homes)),
                home_works=len(at_home),
                away_works=len(away),
            )
        ]

    # Having failed the away majority, an equal split is the only way home
    # can also fail its own: neither side is most, so the check says nothing,
    # as it does undeclared.
    if len(at_home) == len(away) or len(at_home) < MIN_HOME_WORKS:
        return []

    # A declared institution is home even on a work the corpus never gave a
    # country to; every other institution still has to earn it on its own.
    home_institutions = _home_institutions(affiliated, homes, labels) | declared_institutions
    return list(_cluster_works(author, views, affiliated, homes, home_institutions, labels))


def institution_index(raw_works: list[dict[str, Any]]) -> dict[str, tuple[str, str | None]]:
    """Bare ROR id to the (OpenAlex id, country) the corpus carries for it.

    A declaration names a ROR; everything the check compares is keyed by
    OpenAlex institution id. The corpus already carries both on every
    authorship, so it bridges them for free, and only a ROR absent from it
    costs a lookup. A ROR the corpus maps two ways is left out rather than
    guessed — the authority settles that one.
    """
    ids: dict[str, set[str]] = defaultdict(set)
    countries: dict[str, str] = {}
    for raw in raw_works:
        for entry in raw.get("authorships") or []:
            for institution in entry.get("institutions") or []:
                ror, openalex_id = institution.get("ror"), institution.get("id")
                if not ror or not openalex_id:
                    continue
                bare_id = strip_openalex_host(openalex_id)
                ids[bare_ror(str(ror))].add(bare_id)
                if institution.get("country_code"):
                    countries[bare_id] = institution["country_code"]
    resolved = {}
    for ror, candidates in ids.items():
        if len(candidates) == 1:
            (openalex_id,) = candidates
            resolved[ror] = (openalex_id, countries.get(openalex_id))
    return resolved


def find_contamination(
    raw_works: list[dict[str, Any]],
    tracked_ids: dict[str, str],
    homes: Mapping[str, tuple[DeclaredHome, ...]] | None = None,
) -> list[Finding]:
    """Works that look like they belong to someone else, and profiles that do.

    `tracked_ids` maps resolved OpenAlex author ids to the configured
    author's canonical name, exactly as the normalize stage receives it. Each
    tracked author is judged against their own corpus, so a work shared by
    two configured colleagues is read once per person.

    `homes` carries a declaration, one or more places, for the authors that
    have one, keyed the same way. An author without one is checked exactly
    as before.
    """
    appearances, labels = _index(raw_works, tracked_ids)
    homes = homes or {}
    findings: list[Finding] = []
    for tracked_id in sorted(tracked_ids):
        views = [_view(a, tracked_id, labels) for a in appearances.get(tracked_id, [])]
        author = tracked_ids[tracked_id]
        declared = homes.get(tracked_id)
        if not declared:
            findings.extend(_clusters_for(author, views, labels))
        else:
            findings.extend(_declared_for(author, views, labels, declared))
    return findings


def contamination_warnings(findings: Iterable[Finding]) -> list[str]:
    """One warning per finding, phrased as a question for the maintainer."""
    warnings = []
    for finding in findings:
        if isinstance(finding, ProfileMismatch):
            # Deliberately no exclusion advice: the works are not the
            # problem if the profile is. Excluding them one by one would
            # dismantle the evidence that the iD or the declaration is wrong.
            # The incomplete reading comes first because it is the common
            # one: a department always has someone who recently moved in.
            # Countries, not places: two declared places in one country are
            # one home country, and a country is what "outside" measures.
            declared = ", ".join(finding.countries)
            noun = "country" if len(finding.countries) == 1 else "countries"
            warnings.append(
                f"{finding.author}: {finding.away_works} of "
                f"{finding.home_works + finding.away_works} placed work(s) sit outside "
                f"{declared}, the declared home {noun} — the declaration is incomplete (someone "
                f"who moved here needs their previous institutions listed under `home:`) "
                f"or wrong, or this profile is not only theirs; `erga verify` is where "
                f"that is settled"
            )
            continue
        where = (
            f"{finding.institution} ({finding.country})"
            if finding.country
            else (finding.institution)
        )
        # First work with a title, since titles are positional and some are
        # empty; an untitled first work should not cost the reader the example.
        sample = next((title for title in finding.titles if title), None)
        example = f" (e.g. {sample!r})" if sample else ""
        warnings.append(
            f"{finding.author}: {len(finding.work_ids)} work(s) tie to {where}, sharing no "
            f"institution and no collaborator with the rest of the profile{example} — a "
            f"same-name stranger's works look like this; exclude them by DOI if so"
        )
    return warnings
