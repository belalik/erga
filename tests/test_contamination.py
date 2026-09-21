"""The homonym check: what it catches, and what it must stay quiet about.

Fixtures are handcrafted. The shapes mirror the live API (verified 2026-08-16,
docs/requirements-v1.md section 3), never recorded personal data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conftest import FakeTransport, no_sleep
from erga.config import load_config
from erga.contamination import (
    Cluster,
    DeclaredHome,
    Finding,
    ProfileMismatch,
    contamination_warnings,
    find_contamination,
    institution_index,
)
from erga.crossref import CrossrefClient
from erga.errors import ConfigError
from erga.openalex import OpenAlexClient
from erga.pipeline import build

TRACKED = "A5000000001"
TRACKED_IDS = {TRACKED: "Katerina Malisova"}


def clusters_only(findings: list[Finding]) -> list[Cluster]:
    """The findings as clusters. A profile mismatch here fails the test.

    The undeclared path cannot produce one, so this is an assertion about
    which branch ran, not a filter that would quietly drop the other.
    """
    for finding in findings:
        assert isinstance(finding, Cluster), f"expected clusters, got {finding!r}"
    return [f for f in findings if isinstance(f, Cluster)]


# The ROR ids are well-formed but carry no valid check digits, so they name
# no real institution and a stray live call could not resolve one.
AEGEAN_ROR = "0aegean12"
AEGEAN = {
    "id": "https://openalex.org/I100000001",
    "display_name": "University of the Aegean",
    "country_code": "GR",
    "ror": f"https://ror.org/{AEGEAN_ROR}",
}
PALACKY = {
    "id": "https://openalex.org/I200000002",
    "display_name": "Palacký University",
    "country_code": "CZ",
    "ror": "https://ror.org/0packy456",
}
MIT = {
    "id": "https://openalex.org/I300000003",
    "display_name": "MIT",
    "country_code": "US",
    "ror": "https://ror.org/0mmmttt78",
}
# Same institution, as an authorship that names no country. The corpus can
# carry a place this way for a whole career.
AEGEAN_UNPLACED = {
    "id": "https://openalex.org/I100000001",
    "display_name": "University of the Aegean",
    "ror": f"https://ror.org/{AEGEAN_ROR}",
}
AT_HOME = DeclaredHome(institution_id="I100000001", country="GR")
DECLARED = {TRACKED: AT_HOME}


def work(
    work_id: str,
    *,
    institutions: list[dict[str, Any]] | None = None,
    countries: list[str] | None = None,
    team: list[str] | None = None,
    title: str = "A paper",
) -> dict[str, Any]:
    """One raw work, seen from the tracked author's authorship entry."""
    team = team or []
    institutions = institutions if institutions is not None else [AEGEAN]
    if countries is None:
        countries = [i["country_code"] for i in institutions if i.get("country_code")]
    authorships: list[dict[str, Any]] = [
        {
            "author": {"id": f"https://openalex.org/{TRACKED}", "display_name": "K. Malisova"},
            "institutions": institutions,
            "countries": countries,
        }
    ]
    authorships.extend(
        {"author": {"id": f"https://openalex.org/{member}"}, "institutions": [], "countries": []}
        for member in team
    )
    return {
        "id": f"https://openalex.org/{work_id}",
        "title": title,
        "authorships": authorships,
    }


def home_corpus(count: int = 6) -> list[dict[str, Any]]:
    """A settled career: one country, one institution, a recurring lab."""
    return [
        work(f"W{i:03d}", team=["A5000000900", f"A50000009{i:02d}"], title=f"Home paper {i}")
        for i in range(count)
    ]


def test_flags_a_cluster_of_strangers_works() -> None:
    raw = [
        *home_corpus(),
        work("W900", institutions=[PALACKY], team=["A5000009001"], title="Sports science I"),
        work("W901", institutions=[PALACKY], team=["A5000009002"], title="Sports science II"),
    ]
    clusters = clusters_only(find_contamination(raw, TRACKED_IDS))
    assert clusters == [
        Cluster(
            author="Katerina Malisova",
            institution="Palacký University",
            country="CZ",
            work_ids=["W900", "W901"],
            titles=["Sports science I", "Sports science II"],
        )
    ]


def test_a_foreign_lab_cannot_vouch_for_itself() -> None:
    """The likeliest real shape: one group, recurring across the stray works.

    Counting collaborators over the whole corpus made these works alibi each
    other — every stranger appeared more than once, so none looked like a
    stranger, and the cluster disappeared.
    """
    raw = [
        *home_corpus(),
        work("W900", institutions=[PALACKY], team=["A5000009001", "A5000009002"]),
        work("W901", institutions=[PALACKY], team=["A5000009001", "A5000009003"]),
        work("W902", institutions=[PALACKY], team=["A5000009002", "A5000009003"]),
    ]
    clusters = clusters_only(find_contamination(raw, TRACKED_IDS))
    assert [c.institution for c in clusters] == ["Palacký University"]
    assert clusters[0].work_ids == ["W900", "W901", "W902"]


def test_the_career_the_pilot_measured() -> None:
    """The whole shape at once, as consumer #2 measured it on 2026-08-17.

    Nine home works, two carrying no affiliation, and five by a same-name
    stranger who shares not one collaborator with any of them. The strangers'
    own team recurs across all five, so they vouch for each other unless
    outliers are held out of the network.

    The older of the unaffiliated pair is why the rule is not phrased as "flag
    every disconnected component": by co-author network alone that genuine
    paper is exactly as isolated as the strangers are. Keying on affiliation
    makes it unflaggable rather than merely unflagged, so what this asserts is
    narrower — that an isolated work does not perturb the home country or the
    network enough to hide the real cluster.
    """
    czech_lab = ["A5000009001", "A5000009002"]
    raw = [
        *home_corpus(9),
        # No affiliation: one with the home lab aboard, one from before it.
        work("W700", institutions=[], countries=[], team=["A5000000900"], title="Late untagged"),
        work("W701", institutions=[], countries=[], team=["A5000007001"], title="Tangram quests"),
        *(
            work(
                f"W90{i}",
                institutions=[PALACKY],
                team=[*czech_lab, f"A500000901{i}"],
                title=f"Sports science {i}",
            )
            for i in range(5)
        ),
    ]
    clusters = clusters_only(find_contamination(raw, TRACKED_IDS))
    assert [(c.institution, c.work_ids) for c in clusters] == [
        ("Palacký University", ["W900", "W901", "W902", "W903", "W904"])
    ]


def test_a_missing_country_does_not_erase_a_known_one() -> None:
    """Which record lands last is fetch order, not a fact about the place.

    The same institution arrives carrying its country on one work and without
    it on another. Letting the later write win made the reported country
    depend on iteration order, and once home institutions began matching on
    that country, a dropped one could push the author's own institution out
    of home and turn their own papers into outliers.
    """
    palacky_no_country = {**PALACKY, "country_code": None}
    with_country = work("W900", institutions=[PALACKY], team=["A5000009001"])
    without_country = work(
        "W901", institutions=[palacky_no_country], countries=[], team=["A5000009002"]
    )
    forward = find_contamination([*home_corpus(), with_country, without_country], TRACKED_IDS)
    reverse = find_contamination([*home_corpus(), without_country, with_country], TRACKED_IDS)
    assert [c.country for c in forward] == ["CZ"]
    assert [c.country for c in reverse] == ["CZ"]


def test_an_institution_country_fills_a_missing_authorship_country() -> None:
    """Missing authorship countries diluted home out of its own majority."""
    raw = [
        *home_corpus(5),
        *(
            work(f"W10{i}", institutions=[AEGEAN], countries=[], team=["A5000000900"])
            for i in range(4)
        ),
        work("W900", institutions=[PALACKY], team=["A5000009001"]),
        work("W901", institutions=[PALACKY], team=["A5000009002"]),
    ]
    clusters = clusters_only(find_contamination(raw, TRACKED_IDS))
    assert [(c.institution, c.work_ids) for c in clusters] == [
        ("Palacký University", ["W900", "W901"])
    ]


def test_clean_corpus_is_silent() -> None:
    assert find_contamination(home_corpus(), TRACKED_IDS) == []


def test_a_single_paper_abroad_is_not_a_cluster() -> None:
    # Ordinary academic life: one visit, one paper, strangers on the byline.
    raw = [*home_corpus(), work("W900", institutions=[MIT], team=["A5000009001"])]
    assert find_contamination(raw, TRACKED_IDS) == []


def test_a_sabbatical_keeps_its_collaborators() -> None:
    # Same person abroad: the works are foreign but a home collaborator came
    # along, so the team is not a set of strangers.
    raw = [
        *home_corpus(),
        work("W900", institutions=[MIT], team=["A5000000900", "A5000009001"]),
        work("W901", institutions=[MIT], team=["A5000000900", "A5000009002"]),
    ]
    assert find_contamination(raw, TRACKED_IDS) == []


def test_works_without_affiliation_are_never_anomalous() -> None:
    # A third of works carry no affiliation; absence must read as silence.
    raw = [
        *home_corpus(),
        work("W900", institutions=[], countries=[], team=["A5000009001"]),
        work("W901", institutions=[], countries=[], team=["A5000009002"]),
    ]
    assert find_contamination(raw, TRACKED_IDS) == []


def test_solo_works_cannot_be_judged() -> None:
    # No team means nothing to be a stranger to, whatever the affiliation.
    raw = [
        *home_corpus(),
        work("W900", institutions=[PALACKY], team=[]),
        work("W901", institutions=[PALACKY], team=[]),
    ]
    assert find_contamination(raw, TRACKED_IDS) == []


def test_a_stranger_who_outnumbers_the_career_is_not_flagged_in_reverse() -> None:
    """The inversion: whoever holds the plurality becomes the baseline.

    Two genuine works against four strangers made the strangers' country home,
    and the check then reported the author's own papers as the intruders — at
    their own institution, advising the maintainer to exclude them by DOI.
    """
    raw = [
        *home_corpus(2),
        *(work(f"W90{i}", institutions=[PALACKY], team=[f"A500000900{i}"]) for i in range(4)),
    ]
    assert find_contamination(raw, TRACKED_IDS) == []


def test_an_even_split_picks_no_home_at_all() -> None:
    # Five against five: the tie broke alphabetically, so the country code
    # decided which half of the profile got accused.
    raw = [
        *home_corpus(5),
        *(work(f"W90{i}", institutions=[PALACKY], team=[f"A500000900{i}"]) for i in range(5)),
    ]
    assert find_contamination(raw, TRACKED_IDS) == []


def test_one_dual_affiliation_paper_does_not_whitelist_the_place() -> None:
    """A single work listing home and abroad together used to silence the rest.

    Every institution co-listed on a home-country work counted as home, so one
    such paper vouched for that institution across the whole career and later
    clusters there went unreported.
    """
    raw = [
        *home_corpus(),
        work("W500", institutions=[AEGEAN, PALACKY], team=["A5000000900"], title="Joint venture"),
        work("W900", institutions=[PALACKY], team=["A5000009001"], title="Sports science I"),
        work("W901", institutions=[PALACKY], team=["A5000009002"], title="Sports science II"),
    ]
    clusters = clusters_only(find_contamination(raw, TRACKED_IDS))
    assert [(c.institution, c.work_ids) for c in clusters] == [
        ("Palacký University", ["W900", "W901"])
    ]


def test_thin_record_has_no_majority_to_argue_from() -> None:
    raw = [
        work("W000", team=["A5000000900"]),
        work("W001", team=["A5000000900"]),
        work("W900", institutions=[PALACKY], team=["A5000009001"]),
        work("W901", institutions=[PALACKY], team=["A5000009002"]),
    ]
    assert find_contamination(raw, TRACKED_IDS) == []


def test_untracked_authors_are_not_judged() -> None:
    raw = [
        *home_corpus(),
        work("W900", institutions=[PALACKY], team=["A5000009001"]),
        work("W901", institutions=[PALACKY], team=["A5000009002"]),
    ]
    assert find_contamination(raw, {}) == []


def test_a_work_co_affiliated_abroad_is_reported_once() -> None:
    raw = [
        *home_corpus(),
        work("W900", institutions=[PALACKY, MIT], team=["A5000009001"]),
        work("W901", institutions=[PALACKY], team=["A5000009002"]),
        work("W902", institutions=[PALACKY], team=["A5000009003"]),
    ]
    clusters = clusters_only(find_contamination(raw, TRACKED_IDS))
    assert [c.institution for c in clusters] == ["Palacký University"]
    assert clusters[0].work_ids == ["W900", "W901", "W902"]


def test_each_tracked_colleague_is_judged_separately() -> None:
    colleague = "A5000000002"
    shared = {
        "id": "https://openalex.org/W500",
        "title": "Joint paper",
        "authorships": [
            {
                "author": {"id": f"https://openalex.org/{TRACKED}"},
                "institutions": [AEGEAN],
                "countries": ["GR"],
            },
            {
                "author": {"id": f"https://openalex.org/{colleague}"},
                "institutions": [AEGEAN],
                "countries": ["GR"],
            },
        ],
    }
    raw = [*home_corpus(), shared]
    clusters = find_contamination(raw, {TRACKED: "Katerina Malisova", colleague: "A Colleague"})
    assert clusters == []


def test_build_surfaces_the_cluster(tmp_path: Path) -> None:
    """The wiring: a contaminated fetch reaches the maintainer as a warning."""
    (tmp_path / "erga.yml").write_text(
        "mailto: you@example.org\n"
        "authors:\n"
        f"  - name: Katerina Malisova\n    openalex_id: {TRACKED}\n"
        "output:\n  path: publications.json\n",
        encoding="utf-8",
    )
    raw = [
        *home_corpus(),
        work("W900", institutions=[PALACKY], team=["A5000009001"], title="Sports science I"),
        work("W901", institutions=[PALACKY], team=["A5000009002"], title="Sports science II"),
    ]
    transport = FakeTransport()
    transport.add(
        f"api.openalex.org/authors/{TRACKED}",
        {},
        {
            "id": f"https://openalex.org/{TRACKED}",
            "display_name": "Katerina Malisova",
            "display_name_alternatives": [],
            "works_count": len(raw),
        },
    )
    transport.add(
        "api.openalex.org/works", {"cursor": "*"}, {"meta": {"next_cursor": None}, "results": raw}
    )

    config = load_config(tmp_path / "erga.yml")
    stats = build(
        config,
        OpenAlexClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep),
        CrossrefClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep),
        dry_run=True,
    )
    assert [w for w in stats.warnings if "Palacký University (CZ)" in w]


def test_titles_stay_paired_with_work_ids() -> None:
    # An untitled work used to shorten `titles` without shortening `work_ids`,
    # so anything reading them as pairs silently mismatched.
    untitled = work("W902", institutions=[PALACKY], team=["A5000009003"], title="")
    raw = [
        *home_corpus(),
        work("W900", institutions=[PALACKY], team=["A5000009001"], title="Sports science I"),
        work("W901", institutions=[PALACKY], team=["A5000009002"], title="Sports science II"),
        untitled,
    ]
    (cluster,) = clusters_only(find_contamination(raw, TRACKED_IDS))
    assert cluster.work_ids == ["W900", "W901", "W902"]
    assert cluster.titles == ["Sports science I", "Sports science II", ""]


def test_an_untitled_first_work_still_yields_an_example() -> None:
    cluster = Cluster(
        author="Katerina Malisova",
        institution="Palacký University",
        country="CZ",
        work_ids=["W900", "W901"],
        titles=["", "Sports science II"],
    )
    (warning,) = contamination_warnings([cluster])
    assert "Sports science II" in warning


def test_warning_names_the_place_and_what_to_do() -> None:
    cluster = Cluster(
        author="Katerina Malisova",
        institution="Palacký University",
        country="CZ",
        work_ids=["W900", "W901"],
        titles=["Sports science I"],
    )
    (warning,) = contamination_warnings([cluster])
    assert "Katerina Malisova" in warning
    assert "2 work(s)" in warning
    assert "Palacký University (CZ)" in warning
    assert "Sports science I" in warning
    assert "exclude them by DOI" in warning


# --- the declared home (requirements section 3) -----------------------------

# An institution the corpus never places. Enough of these silence the
# inferred rule, which is the case the declaration exists to rescue.
UNPLACED = {
    "id": "https://openalex.org/I400000004",
    "display_name": "An unplaced institute",
}


def test_institution_index_bridges_ror_to_openalex_id() -> None:
    index = institution_index([*home_corpus(1), work("W900", institutions=[PALACKY])])
    assert index[AEGEAN_ROR] == ("I100000001", "GR")
    assert index["0packy456"] == ("I200000002", "CZ")


def test_institution_index_drops_a_ror_the_corpus_maps_two_ways() -> None:
    # Two OpenAlex ids under one ROR is corpus disagreement, not a fact; the
    # lookup settles it rather than the first row winning.
    impostor = {**PALACKY, "id": "https://openalex.org/I999999999"}
    index = institution_index(
        [work("W900", institutions=[PALACKY]), work("W901", institutions=[impostor])]
    )
    assert "0packy456" not in index


def test_a_declaration_rescues_a_career_the_counts_cannot_place() -> None:
    """The motivating case: unplaced works dilute the majority into silence."""
    raw = [
        *home_corpus(5),
        # The author's own works, at a place OpenAlex never gave a country;
        # the usual lab is on them, so the career vouches for them.
        *(
            work(f"W8{i:02d}", institutions=[UNPLACED], team=["A5000000900", f"A50000081{i:02d}"])
            for i in range(5)
        ),
        work("W900", institutions=[PALACKY], team=["A5000009001"], title="Sports science I"),
        work("W901", institutions=[PALACKY], team=["A5000009002"], title="Sports science II"),
    ]
    assert find_contamination(raw, TRACKED_IDS) == []

    (cluster,) = clusters_only(find_contamination(raw, TRACKED_IDS, DECLARED))
    assert cluster.institution == "Palacký University"
    assert cluster.work_ids == ["W900", "W901"]


def test_a_mostly_away_profile_is_reported_as_wrong_not_accused() -> None:
    raw = [
        *home_corpus(2),
        *(work(f"W9{i:02d}", institutions=[PALACKY], team=[f"A50000090{i:02d}"]) for i in range(6)),
    ]
    findings = find_contamination(raw, TRACKED_IDS, DECLARED)
    assert findings == [
        ProfileMismatch(author="Katerina Malisova", country="GR", home_works=2, away_works=6)
    ]


def test_four_all_away_works_stay_below_the_evidence_floor() -> None:
    # Below the floor both paths are silent, so no fixture can make them
    # disagree here; the test below, one work over the floor, is what proves
    # the declared branch runs on this shape. This one pins the floor's edge.
    raw = [work(f"W9{i:02d}", institutions=[PALACKY], team=[f"A50000090{i:02d}"]) for i in range(4)]
    assert find_contamination(raw, TRACKED_IDS, DECLARED) == []


def test_five_all_away_works_are_a_profile_mismatch() -> None:
    raw = [work(f"W9{i:02d}", institutions=[PALACKY], team=[f"A50000090{i:02d}"]) for i in range(5)]
    assert find_contamination(raw, TRACKED_IDS, DECLARED) == [
        ProfileMismatch(author="Katerina Malisova", country="GR", home_works=0, away_works=5)
    ]


def test_four_home_and_five_away_works_are_a_profile_mismatch() -> None:
    raw = [
        *home_corpus(4),
        *(work(f"W9{i:02d}", institutions=[PALACKY], team=[f"A50000090{i:02d}"]) for i in range(5)),
    ]
    assert find_contamination(raw, TRACKED_IDS, DECLARED) == [
        ProfileMismatch(author="Katerina Malisova", country="GR", home_works=4, away_works=5)
    ]


def test_five_home_and_four_away_works_flag_the_stranger_cluster() -> None:
    raw = [
        *(
            work(
                f"W0{i:02d}",
                institutions=[AEGEAN, PALACKY],
                team=["A5000000900", f"A50000001{i:02d}"],
            )
            for i in range(5)
        ),
        *(work(f"W9{i:02d}", institutions=[PALACKY], team=[f"A50000090{i:02d}"]) for i in range(4)),
    ]
    assert find_contamination(raw, TRACKED_IDS, DECLARED) == [
        Cluster(
            author="Katerina Malisova",
            institution="Palacký University",
            country="CZ",
            work_ids=["W900", "W901", "W902", "W903"],
            titles=["A paper", "A paper", "A paper", "A paper"],
        )
    ]


def test_a_home_and_away_work_counts_once_below_the_evidence_floor() -> None:
    # Counting the dual-affiliated work in both buckets turns four comparable
    # works into five and creates an away-majority verdict. Both paths are
    # silent below the floor, so this pins the count, not the branch.
    raw = [
        work("W800", institutions=[AEGEAN, PALACKY], team=["A5000008001"]),
        *(work(f"W9{i:02d}", institutions=[PALACKY], team=[f"A50000090{i:02d}"]) for i in range(3)),
    ]
    assert find_contamination(raw, TRACKED_IDS, DECLARED) == []


def test_a_declared_tie_still_picks_no_side() -> None:
    # Five against five under the declaration. Inference instead sees CZ on
    # eight works and flags the two at MIT, so silence proves this branch ran.
    raw = [
        *(
            work(
                f"W0{i:02d}",
                institutions=[AEGEAN, PALACKY],
                team=["A5000000900", f"A50000001{i:02d}"],
            )
            for i in range(5)
        ),
        *(work(f"W8{i:02d}", institutions=[PALACKY], team=[f"A50000080{i:02d}"]) for i in range(3)),
        work("W900", institutions=[MIT], team=["A5000009001"]),
        work("W901", institutions=[MIT], team=["A5000009002"]),
    ]
    assert find_contamination(raw, TRACKED_IDS, DECLARED) == []


def test_a_declaration_does_not_stand_in_for_a_career() -> None:
    # Four works at home is a thin record whoever names it, so the check
    # stays quiet: the maintainer supplied where home is, not how much of a
    # career is on file.
    # Inference sees five CZ works and flags the two at MIT; declaration sees
    # only four home works, so silence also proves the declared branch ran.
    raw = [
        *(
            work(
                f"W0{i:02d}",
                institutions=[AEGEAN, PALACKY],
                team=["A5000000900", f"A50000001{i:02d}"],
            )
            for i in range(4)
        ),
        work("W800", institutions=[PALACKY], team=["A5000008001"]),
        work("W900", institutions=[MIT], team=["A5000009001"]),
        work("W901", institutions=[MIT], team=["A5000009002"]),
    ]
    assert find_contamination(raw, TRACKED_IDS, DECLARED) == []


def test_the_declared_institution_is_home_where_the_corpus_gives_no_country() -> None:
    raw = [
        *(
            work(
                f"W{i:03d}",
                institutions=[AEGEAN_UNPLACED],
                team=["A5000000900", f"A50000009{i:02d}"],
            )
            for i in range(6)
        ),
        work("W900", institutions=[PALACKY], team=["A5000009001"], title="Sports science I"),
        work("W901", institutions=[PALACKY], team=["A5000009002"], title="Sports science II"),
    ]
    # Counted, the only country on file is CZ, so the check has no home to
    # reason from and says nothing.
    assert find_contamination(raw, TRACKED_IDS) == []

    (cluster,) = clusters_only(find_contamination(raw, TRACKED_IDS, DECLARED))
    assert cluster.institution == "Palacký University"


def test_co_listing_with_the_declared_institution_does_not_make_a_place_home() -> None:
    # The whitelist defect, pointed the other way: a declaration vouches for
    # itself, never for whatever shared a byline with it.
    raw = [
        *home_corpus(5),
        work("W800", institutions=[AEGEAN, MIT], team=["A5000008001"], title="A visit"),
        work("W900", institutions=[MIT], team=["A5000009001"], title="Stranger I"),
        work("W901", institutions=[MIT], team=["A5000009002"], title="Stranger II"),
    ]
    (cluster,) = clusters_only(find_contamination(raw, TRACKED_IDS, DECLARED))
    assert cluster.institution == "MIT"
    assert cluster.work_ids == ["W900", "W901"]


def test_the_mismatch_warning_sends_the_reader_to_verify_and_advises_no_exclusion() -> None:
    mismatch = ProfileMismatch(author="Katerina Malisova", country="GR", home_works=2, away_works=6)
    (warning,) = contamination_warnings([mismatch])
    assert "Katerina Malisova" in warning
    assert "6 of 8" in warning
    assert "GR" in warning
    assert "verify" in warning
    # Excluding the works one by one would remove the evidence that the
    # profile, or the declaration, is what is wrong.
    assert "exclude" not in warning


def _declared_build(tmp_path: Path, ror: str, raw: list[dict[str, Any]]) -> FakeTransport:
    (tmp_path / "erga.yml").write_text(
        "mailto: you@example.org\n"
        f"home: {ror}\n"
        "authors:\n"
        f"  - name: Katerina Malisova\n    openalex_id: {TRACKED}\n"
        "output:\n  path: publications.json\n",
        encoding="utf-8",
    )
    transport = FakeTransport()
    transport.add(
        f"api.openalex.org/authors/{TRACKED}",
        {},
        {
            "id": f"https://openalex.org/{TRACKED}",
            "display_name": "Katerina Malisova",
            "display_name_alternatives": [],
            "works_count": len(raw),
        },
    )
    transport.add(
        "api.openalex.org/works", {"cursor": "*"}, {"meta": {"next_cursor": None}, "results": raw}
    )
    return transport


def _run(tmp_path: Path, transport: FakeTransport) -> Any:
    config = load_config(tmp_path / "erga.yml")
    return build(
        config,
        OpenAlexClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep),
        CrossrefClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep),
        dry_run=True,
    )


def test_build_resolves_a_declared_home_from_the_corpus(tmp_path: Path) -> None:
    """The declaration costs no lookup when the works already carry the ROR."""
    raw = [
        *home_corpus(5),
        *(
            work(f"W8{i:02d}", institutions=[UNPLACED], team=["A5000000900", f"A50000081{i:02d}"])
            for i in range(5)
        ),
        work("W900", institutions=[PALACKY], team=["A5000009001"], title="Sports science I"),
        work("W901", institutions=[PALACKY], team=["A5000009002"], title="Sports science II"),
    ]
    transport = _declared_build(tmp_path, AEGEAN_ROR, raw)
    stats = _run(tmp_path, transport)

    assert [w for w in stats.warnings if "Palacký University (CZ)" in w]
    assert not [url for url, _ in transport.calls if "institutions" in url]


def test_build_resolves_a_declared_home_absent_from_the_corpus(tmp_path: Path) -> None:
    # The inferred path is silent on this diluted career, so the cluster also
    # proves the authority result became the declaration used by the checker.
    absent = "0zzzzzz99"
    raw = [
        *home_corpus(5),
        *(work(f"W8{i:02d}", institutions=[UNPLACED], team=["A5000000900"]) for i in range(5)),
        work("W900", institutions=[PALACKY], team=["A5000009001"]),
        work("W901", institutions=[PALACKY], team=["A5000009002"]),
    ]
    transport = _declared_build(tmp_path, absent, raw)
    transport.add(
        f"api.openalex.org/institutions/ror:{absent}",
        {},
        {"id": "https://openalex.org/I100000001", "country_code": "GR"},
    )

    stats = _run(tmp_path, transport)
    assert len([warning for warning in stats.warnings if "Palacký University (CZ)" in warning]) == 1


def test_one_declaration_reaches_every_resolved_profile(tmp_path: Path) -> None:
    orcid = "9999-0000-0000-0001"
    second = "A5000000002"
    (tmp_path / "erga.yml").write_text(
        "mailto: you@example.org\n"
        f"home: {AEGEAN_ROR}\n"
        "authors:\n"
        f"  - name: Katerina Malisova\n    orcid: {orcid}\n"
        "output:\n  path: publications.json\n",
        encoding="utf-8",
    )
    first_works = [
        work(f"W1{i:02d}", institutions=[PALACKY], team=[f"A50000081{i:02d}"]) for i in range(5)
    ]
    second_works = [
        work(f"W2{i:02d}", institutions=[PALACKY], team=[f"A50000082{i:02d}"]) for i in range(5)
    ]
    for raw in second_works:
        raw["authorships"][0]["author"]["id"] = f"https://openalex.org/{second}"

    transport = FakeTransport()
    transport.add(
        "api.openalex.org/authors",
        {"filter": f"orcid:{orcid}"},
        {
            "meta": {"count": 2},
            "results": [
                {
                    "id": f"https://openalex.org/{TRACKED}",
                    "display_name": "Katerina Malisova",
                    "display_name_alternatives": [],
                    "works_count": 5,
                },
                {
                    "id": f"https://openalex.org/{second}",
                    "display_name": "Katerina Malisova",
                    "display_name_alternatives": [],
                    "works_count": 5,
                },
            ],
        },
    )
    transport.add(
        "api.openalex.org/works",
        {"cursor": "*"},
        {"meta": {"next_cursor": None}, "results": [*first_works, *second_works]},
    )
    transport.add(
        f"api.openalex.org/institutions/ror:{AEGEAN_ROR}",
        {},
        {"id": "https://openalex.org/I100000001", "country_code": "GR"},
    )

    stats = _run(tmp_path, transport)
    assert len([warning for warning in stats.warnings if "5 of 5" in warning]) == 2


def test_a_per_author_home_replaces_the_top_level_home_in_build(tmp_path: Path) -> None:
    raw = [
        *(
            work(
                f"W0{i:02d}",
                institutions=[PALACKY],
                team=["A5000000800", f"A50000008{i:02d}"],
            )
            for i in range(5)
        ),
        *(work(f"W8{i:02d}", institutions=[UNPLACED], team=["A5000000800"]) for i in range(5)),
        work("W900", institutions=[AEGEAN], team=["A5000009001"]),
        work("W901", institutions=[AEGEAN], team=["A5000009002"]),
    ]
    transport = _declared_build(tmp_path, AEGEAN_ROR, raw)
    (tmp_path / "erga.yml").write_text(
        "mailto: you@example.org\n"
        f"home: {AEGEAN_ROR}\n"
        "authors:\n"
        f"  - name: Katerina Malisova\n    openalex_id: {TRACKED}\n    home: 0packy456\n"
        "output:\n  path: publications.json\n",
        encoding="utf-8",
    )

    stats = _run(tmp_path, transport)
    assert (
        len([warning for warning in stats.warnings if "University of the Aegean (GR)" in warning])
        == 1
    )


def test_a_per_author_null_opts_out_of_the_top_level_home_in_build(tmp_path: Path) -> None:
    raw = [
        *(
            work(
                f"W0{i:02d}",
                institutions=[AEGEAN, PALACKY],
                team=["A5000000900", f"A50000001{i:02d}"],
            )
            for i in range(4)
        ),
        work("W800", institutions=[PALACKY], team=["A5000008001"]),
        work("W900", institutions=[MIT], team=["A5000009001"]),
        work("W901", institutions=[MIT], team=["A5000009002"]),
    ]
    transport = _declared_build(tmp_path, AEGEAN_ROR, raw)
    (tmp_path / "erga.yml").write_text(
        "mailto: you@example.org\n"
        f"home: {AEGEAN_ROR}\n"
        "authors:\n"
        f"  - name: Katerina Malisova\n    openalex_id: {TRACKED}\n    home: null\n"
        "output:\n  path: publications.json\n",
        encoding="utf-8",
    )

    stats = _run(tmp_path, transport)
    assert len([warning for warning in stats.warnings if "MIT (US)" in warning]) == 1


def test_an_opt_out_clears_a_shared_profiles_inherited_home(tmp_path: Path) -> None:
    """Two configured entries can land on one OpenAlex profile.

    The later entry's name already wins that profile, so its `home: null`
    has to win too. Recording only the declared authors left the opt-out
    checked against the institution it opted out of.
    """
    (tmp_path / "erga.yml").write_text(
        "mailto: you@example.org\n"
        f"home: {AEGEAN_ROR}\n"
        "authors:\n"
        f"  - name: Katerina Malisova\n    openalex_id: {TRACKED}\n"
        f"  - name: Kateřina Mališová\n    openalex_id: {TRACKED}\n    home: null\n"
        "output:\n  path: publications.json\n",
        encoding="utf-8",
    )
    # The corpus the counts cannot place: silent inferred, a cluster when a
    # declaration governs. So a warning here means the opt-out was ignored.
    raw = [
        *home_corpus(5),
        *(
            work(f"W8{i:02d}", institutions=[UNPLACED], team=["A5000000900", f"A50000081{i:02d}"])
            for i in range(5)
        ),
        work("W900", institutions=[PALACKY], team=["A5000009001"], title="Sports science I"),
        work("W901", institutions=[PALACKY], team=["A5000009002"], title="Sports science II"),
    ]
    transport = FakeTransport()
    transport.add(
        f"api.openalex.org/authors/{TRACKED}",
        {},
        {
            "id": f"https://openalex.org/{TRACKED}",
            "display_name": "Katerina Malisova",
            "display_name_alternatives": [],
            "works_count": len(raw),
        },
    )
    transport.add(
        "api.openalex.org/works", {"cursor": "*"}, {"meta": {"next_cursor": None}, "results": raw}
    )

    stats = _run(tmp_path, transport)
    assert not [w for w in stats.warnings if "Palacký" in w]


def test_an_unresolvable_declared_home_aborts_the_build(tmp_path: Path) -> None:
    # Falling back to the inferred rule would print different advice for the
    # same config and corpus, with nothing in the output to say which ran.
    absent = "0zzzzzz99"
    transport = _declared_build(tmp_path, absent, home_corpus(6))
    transport.add(f"api.openalex.org/institutions/ror:{absent}", {}, None, status=404)

    with pytest.raises(ConfigError, match="names no OpenAlex institution"):
        _run(tmp_path, transport)


def test_a_countryless_corpus_and_authority_home_aborts_the_build(tmp_path: Path) -> None:
    raw = [work(f"W{i:03d}", institutions=[AEGEAN_UNPLACED], countries=[]) for i in range(5)]
    transport = _declared_build(tmp_path, AEGEAN_ROR, raw)
    transport.add(
        f"api.openalex.org/institutions/ror:{AEGEAN_ROR}",
        {},
        {"id": "https://openalex.org/I100000001", "country_code": None},
    )

    with pytest.raises(ConfigError, match="has no country in OpenAlex"):
        _run(tmp_path, transport)
