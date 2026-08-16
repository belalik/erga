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
