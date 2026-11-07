from __future__ import annotations

from pathlib import Path
from typing import Any

from conftest import HOMONYM, FakeTransport, no_sleep
from erga.config import load_config
from erga.crossref import CrossrefClient
from erga.http import Response
from erga.model import Work
from erga.openalex import OpenAlexClient
from erga.pipeline import (
    BuildStats,
    backfill_venues,
    build,
    curate,
    exclude_by_type,
    exclude_machine_translations,
    ratchet_venues,
)

HOMONYM_AUTHORSHIP = {"author": HOMONYM}


def _build_one(
    tmp_path: Path, authorships: list[dict[str, Any]], overrides: str | None = None
) -> BuildStats:
    """One fetched work W1 through a real build, both members by openalex_id."""
    (tmp_path / "erga.yml").write_text(
        "mailto: you@example.org\n"
        "authors:\n"
        "  - name: Josiah Carberry\n    openalex_id: A5000000001\n"
        "  - name: Ann Colleague\n    openalex_id: A5000000002\n"
        "output:\n  path: publications.json\n",
        encoding="utf-8",
    )
    if overrides is not None:
        (tmp_path / "overrides.yml").write_text(overrides, encoding="utf-8")
    raw = {
        "id": "https://openalex.org/W1",
        "title": "Reached through a co-author",
        "publication_year": 2026,
        "type": "article",
        "primary_location": {"source": {"display_name": "Journal of Psychoceramics"}},
        "authorships": [
            {"author": {"id": "https://openalex.org/A5000000002", "display_name": "Ann Colleague"}},
            *authorships,
        ],
    }
    transport = FakeTransport()
    for openalex_id, name in (("A5000000001", "Josiah Carberry"), ("A5000000002", "Ann Colleague")):
        transport.add(
            f"api.openalex.org/authors/{openalex_id}",
            {},
            {"id": f"https://openalex.org/{openalex_id}", "display_name": name, "works_count": 1},
        )
    transport.add(
        "api.openalex.org/works", {"cursor": "*"}, {"meta": {"next_cursor": None}, "results": [raw]}
    )
    config = load_config(tmp_path / "erga.yml")
    return build(
        config,
        OpenAlexClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep),
        CrossrefClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep),
    )


def test_build_names_each_withheld_orcid(tmp_path: Path) -> None:
    """The wiring: a name-only match's iD reaches the maintainer, not the file."""
    stats = _build_one(tmp_path, [HOMONYM_AUTHORSHIP])
    assert (
        "Josiah Carberry: ORCID 9999-0000-0000-0077 on A5000000077, matched by name only, "
        "not published on 1 work(s): a homonym's, or theirs on a profile the config does "
        "not resolve"
    ) in stats.warnings
    written = (tmp_path / "publications.json").read_text(encoding="utf-8")
    assert "9999-0000-0000-0077" not in written
    assert '"tracked_as": "Josiah Carberry"' in written


def test_build_says_nothing_of_an_excluded_works_orcid(tmp_path: Path) -> None:
    stats = _build_one(tmp_path, [HOMONYM_AUTHORSHIP], overrides="- id: W1\n  exclude: true\n")
    assert not [w for w in stats.warnings if "9999-0000-0000-0077" in w]


def test_build_names_an_orcid_an_authors_patch_drops(tmp_path: Path) -> None:
    # The homonym's iD was withheld before curation ran, so the patch's
    # carry-over cannot bring it back; only the outsider's goes unclaimed.
    outsider = {
        "author": {"display_name": "Bo Outsider", "orcid": "https://orcid.org/9999-0000-0000-0004"}
    }
    stats = _build_one(
        tmp_path,
        [HOMONYM_AUTHORSHIP, outsider],
        overrides='- id: W1\n  authors: ["Ann Colleague", "Josiah Carberry"]\n',
    )
    assert (
        f"override drops upstream ORCIDs: {tmp_path / 'overrides.yml'}: entry 1, W1: Bo Outsider"
    ) in stats.warnings
    assert "9999-0000-0000-0077" not in (tmp_path / "publications.json").read_text(encoding="utf-8")


def test_ratchet_venues_drops_platform_names_this_fetch_carries() -> None:
    """A venue an earlier erga wrote from a platform source is not last-known-good."""
    previous = [
        {"id": "W1", "doi": "https://doi.org/10.5555/ch1", "venue": "Springer eBooks"},
        {"id": "W2", "doi": "https://doi.org/10.5555/ch2", "venue": "A Real Book"},
        {"id": "W3", "venue": "Springer eBooks"},
    ]
    raw_works = [
        {
            "id": "https://openalex.org/W9",
            "primary_location": {
                "source": {"display_name": "Springer eBooks", "type": "ebook platform"},
                "raw_source_name": "Some Other Book",
            },
        }
    ]
    assert ratchet_venues(previous, raw_works) == {
        "10.5555/ch2": "A Real Book",
        "W2": "A Real Book",
    }
    # Without a platform source in the fetch, nothing marks the name and it rides along.
    assert ratchet_venues(previous, [])["W3"] == "Springer eBooks"
    assert ratchet_venues(None, raw_works) == {}


def test_ratchet_venues_decodes_what_an_earlier_erga_wrote() -> None:
    """Before 0.9.2 venues were written with their entities; a source-less
    work's venue reaches the build only through the ratchet."""
    previous: list[dict[str, Any]] = [
        {"id": "W1", "venue": "Virtual Systems &amp; Multimedia"},
        {"id": "W2", "venue": "Taylor &amp; Francis eBooks"},
        {"id": "W3", "venue": 5},
    ]
    raw_works = [
        {
            "id": "https://openalex.org/W9",
            "primary_location": {
                "source": {"display_name": "Taylor & Francis eBooks", "type": "ebook platform"},
                "raw_source_name": "Some Book",
            },
        }
    ]
    # The platform name matches in decoded form; a venue no erga writes is skipped.
    assert ratchet_venues(previous, raw_works) == {"W1": "Virtual Systems & Multimedia"}


def test_backfill_decodes_the_crossref_container_title() -> None:
    # Crossref's container-title for 10.1109/vsmm.2014.7136650 reads
    # "Virtual Systems &amp; Multimedia" (checked 2026-10-17).
    transport = FakeTransport()
    transport.add(
        "/works/10.5555%2Fvsmm",
        {},
        {"message": {"container-title": ["Virtual Systems &amp; Multimedia (VSMM)"]}},
    )
    crossref = CrossrefClient(transport, mailto="m@example.org", delay=0.0, sleep=no_sleep)
    work = Work(id="W1", title="A paper", doi="https://doi.org/10.5555/vsmm")
    stats = BuildStats()
    backfill_venues([work], {}, crossref, stats)
    assert work.venue == "Virtual Systems & Multimedia (VSMM)"
    assert stats.backfilled_crossref == 1


LNCS = "Lecture notes in computer science"
SERIES_NAMES = frozenset({LNCS.casefold()})


def series_crossref(*routes: tuple[str, dict[str, Any]]) -> tuple[CrossrefClient, FakeTransport]:
    """A Crossref client answering each bare DOI with its message; any
    other request fails the test, so a lookup that should not happen shows."""
    transport = FakeTransport()
    for doi, message in routes:
        transport.add("/works/" + doi.replace("/", "%2F"), {}, {"message": message})
    return CrossrefClient(transport, mailto="m@example.org", delay=0.0, sleep=no_sleep), transport


def in_series(book: str) -> dict[str, Any]:
    return {"type": "book-chapter", "container-title": ["Lecture Notes in Computer Science", book]}


def series_work(work_id: str, doi: str | None = None) -> Work:
    """A fetched work whose venue named LNCS, as normalize leaves it."""
    return Work(
        id=work_id, title="A paper", series=LNCS, doi=f"https://doi.org/{doi}" if doi else None
    )


def test_backfill_replaces_a_series_with_the_volume() -> None:
    crossref, transport = series_crossref(
        ("10.5555/ch1", in_series("Semantic Multimedia")),
        ("10.5555/ch2", {"type": "book-chapter", "container-title": ["Lecture Notes in CS"]}),
    )
    works = [
        series_work("W1", "10.5555/ch1"),
        # Crossref names no volume: the series stays, the build prints no less.
        series_work("W2", "10.5555/ch2"),
        series_work("W3"),
        # Known from the previous build: no lookup.
        series_work("W4", "10.5555/ch4"),
        # A series in the previous output is no replacement.
        series_work("W5", "10.5555/ch1"),
    ]
    previous = {"10.5555/ch4": "Human-Computer Interaction", "W5": LNCS.upper()}
    stats = BuildStats()
    backfill_venues(works, previous, crossref, stats, SERIES_NAMES)
    assert [w.venue for w in works] == [
        "Semantic Multimedia",
        LNCS,
        LNCS,
        "Human-Computer Interaction",
        "Semantic Multimedia",
    ]
    assert stats.series_resolved == 3
    assert stats.backfilled_previous == stats.backfilled_crossref == 0
    assert len(transport.calls) == 3


def test_backfill_leaves_a_curated_or_settled_venue() -> None:
    # No routes: any Crossref lookup fails the test.
    crossref, _ = series_crossref()
    # A `venue` patch is final, even one naming the series: the maintainer chose it.
    curated = series_work("W1", "10.5555/ch1")
    curated.venue = "Lecture Notes in Computer Science"
    journal = Work(id="W2", title="P", venue="Journal A", doi="https://doi.org/10.5555/j")
    stats = BuildStats()
    backfill_venues([curated, journal], {"10.5555/ch1": "Other"}, crossref, stats, SERIES_NAMES)
    assert (curated.venue, journal.venue) == ("Lecture Notes in Computer Science", "Journal A")
    assert stats.series_resolved == 0


def test_a_crossref_failure_still_prints_the_series() -> None:
    def down(url: str, params: dict[str, str]) -> Response:
        return Response(503, None)

    crossref = CrossrefClient(down, mailto="m@example.org", delay=0.0, sleep=no_sleep)
    works = [series_work("W1", "10.5555/ch1"), series_work("W2", "10.5555/ch2")]
    stats = BuildStats()
    backfill_venues(works, {}, crossref, stats, SERIES_NAMES)
    assert [w.venue for w in works] == [LNCS, LNCS]
    assert [w for w in stats.warnings if w.startswith("Crossref backfill stopped")]


def test_a_previous_series_fills_a_gap_as_replaceable() -> None:
    """A source-less work's venue reaches the build only through the ratchet;
    a series an earlier erga wrote there still beats none, and Crossref may
    still name the volume."""
    crossref, _ = series_crossref(("10.5555/ch1", in_series("Semantic Multimedia")))
    found = Work(id="W1", title="P", doi="https://doi.org/10.5555/ch1")
    kept = Work(id="W2", title="P")
    stats = BuildStats()
    backfill_venues([found, kept], {"10.5555/ch1": LNCS, "W2": LNCS}, crossref, stats, SERIES_NAMES)
    assert (found.venue, kept.venue) == ("Semantic Multimedia", LNCS)
    # Each venue counted once, by where it finally came from.
    assert stats.backfilled_previous == 1
    assert stats.series_resolved == 1


def test_the_plain_backfill_takes_the_volume_not_the_series() -> None:
    # Before 0.9.5 a venue-less chapter took Crossref's first title, the series.
    crossref, _ = series_crossref(("10.5555/ch1", in_series("Semantic Multimedia")))
    work = Work(id="W1", title="P", doi="https://doi.org/10.5555/ch1")
    stats = BuildStats()
    backfill_venues([work], {}, crossref, stats)
    assert work.venue == "Semantic Multimedia"
    assert stats.backfilled_crossref == 1


def test_machine_translations_are_excluded_and_named() -> None:
    works = [
        Work(id="W1", title="Kinematic approach to digital heritage"),
        Work(id="W2", title="ディジタル遺産への運動学的アプローチ【Powered by NICT】"),
        # The maintainer's own entry stays, whatever its title.
        Work(id="manual-x", title="翻訳【JST・京大機械翻訳】", source="manual", keep=True),
    ]
    stats = BuildStats()
    kept = exclude_machine_translations(works, stats)
    assert [w.id for w in kept] == ["W1", "manual-x"]
    assert len(stats.warnings) == 1
    assert stats.warnings[0].startswith("machine translation excluded: W2 ")


def test_a_translation_carrying_its_originals_doi_cannot_win_the_merge() -> None:
    # Seven NICT records carry the DOI of the paper they translate; ranked
    # in dedup, the more-cited translation would take the original's place.
    original = Work(id="W1", title="Neurosurgery training", doi="https://doi.org/10.5555/cma")
    translation = Work(
        id="W2",
        title="神経外科の学科建設【Powered by NICT】",
        doi="https://doi.org/10.5555/cma",
        cited_by_count=9,
    )
    kept = curate([translation, original], [], frozenset(), BuildStats())
    assert [(w.id, w.title) for w in kept] == [("W1", "Neurosurgery training")]


def test_exclude_by_type_filters_fetched_records() -> None:
    works = [
        Work(id="W1", title="Article", type="journal"),
        Work(id="W2", title="Erratum", type="other"),
        Work(id="W3", title="Preprint", type="preprint"),
    ]
    kept, dropped = exclude_by_type(works, frozenset({"other", "preprint"}))
    assert [w.id for w in kept] == ["W1"]
    assert dropped == 2


def test_exclude_by_type_exempts_kept_records() -> None:
    """Manual entries and exclude:false rescues arrive with `keep` set."""
    works = [
        Work(id="manual-note", title="Note", type="other", source="manual", keep=True),
        Work(id="W2", title="Rescued", type="other", keep=True),
        Work(id="W3", title="Dropped", type="other"),
    ]
    kept, dropped = exclude_by_type(works, frozenset({"other"}))
    assert [w.id for w in kept] == ["manual-note", "W2"]
    assert dropped == 1


def test_exclude_by_type_no_config_is_a_no_op() -> None:
    works = [Work(id="W1", title="A", type="other")]
    kept, dropped = exclude_by_type(works, frozenset())
    assert kept == works
    assert dropped == 0
