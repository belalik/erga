"""The homonym check: what it catches, and what it must stay quiet about.

Fixtures are handcrafted. The shapes mirror the live API (verified 2026-08-16,
docs/requirements-v1.md section 3), never recorded personal data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conftest import FakeTransport, no_sleep
from erga.config import load_config
from erga.contamination import Cluster, contamination_warnings, find_contamination
from erga.crossref import CrossrefClient
from erga.openalex import OpenAlexClient
from erga.pipeline import build

TRACKED = "A5000000001"
TRACKED_IDS = {TRACKED: "Katerina Malisova"}

AEGEAN = {
    "id": "https://openalex.org/I100000001",
    "display_name": "University of the Aegean",
    "country_code": "GR",
}
PALACKY = {
    "id": "https://openalex.org/I200000002",
    "display_name": "Palacký University",
    "country_code": "CZ",
}
MIT = {
    "id": "https://openalex.org/I300000003",
    "display_name": "MIT",
    "country_code": "US",
}


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
    clusters = find_contamination(raw, TRACKED_IDS)
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
    clusters = find_contamination(raw, TRACKED_IDS)
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
    clusters = find_contamination(raw, TRACKED_IDS)
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
    clusters = find_contamination(raw, TRACKED_IDS)
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
    clusters = find_contamination(raw, TRACKED_IDS)
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
    (cluster,) = find_contamination(raw, TRACKED_IDS)
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
