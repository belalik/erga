from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import HOMONYM, FakeTransport, no_sleep
from erga import pipeline
from erga.config import load_config
from erga.crossref import CrossrefClient
from erga.delta import LISTED_CAP, Delta, render_markdown
from erga.http import Response
from erga.model import Work
from erga.openalex import OpenAlexClient
from erga.output import document, dump
from erga.pipeline import (
    BuildStats,
    backfill_venues,
    build,
    curate,
    exclude_by_type,
    exclude_machine_translations,
    ratchet_venues,
    trace_removals,
)

HOMONYM_AUTHORSHIP = {"author": HOMONYM}
# A canned answer for FakeTransport.add: url part, params subset, data, and
# optionally a status.
Route = tuple[Any, ...]


COLLEAGUE = {"author": {"id": "https://openalex.org/A5000000002", "display_name": "Ann Colleague"}}


def _build_one(
    tmp_path: Path,
    authorships: list[dict[str, Any]],
    overrides: str | None = None,
    explain_removals: bool = False,
) -> BuildStats:
    """One fetched work W1 through a real build."""
    raw = {
        "id": "https://openalex.org/W1",
        "title": "Reached through a co-author",
        "publication_year": 2026,
        "type": "article",
        "primary_location": {"source": {"display_name": "Journal of Psychoceramics"}},
        "authorships": [COLLEAGUE, *authorships],
    }
    return _build(tmp_path, [raw], overrides, explain_removals=explain_removals)


def _build(
    tmp_path: Path,
    raws: list[dict[str, Any]],
    overrides: str | None = None,
    crossref: tuple[tuple[str, dict[str, Any]], ...] = (),
    openalex_routes: tuple[Route, ...] = (),
    explain_removals: bool = False,
) -> BuildStats:
    """Fetched works through a real build, both members by openalex_id;
    `crossref` answers each bare DOI with its message, and
    `openalex_routes` go ahead of the fetch's own."""
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
    transport = FakeTransport()
    for route in openalex_routes:
        transport.add(*route)
    for doi, message in crossref:
        transport.add("api.crossref.org/works/" + doi.replace("/", "%2F"), {}, {"message": message})
    for openalex_id, name in (("A5000000001", "Josiah Carberry"), ("A5000000002", "Ann Colleague")):
        transport.add(
            f"api.openalex.org/authors/{openalex_id}",
            {},
            {"id": f"https://openalex.org/{openalex_id}", "display_name": name, "works_count": 1},
        )
    transport.add(
        "api.openalex.org/works", {"cursor": "*"}, {"meta": {"next_cursor": None}, "results": raws}
    )
    config = load_config(tmp_path / "erga.yml")
    return build(
        config,
        OpenAlexClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep),
        CrossrefClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep),
        explain_removals=explain_removals,
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
        # Crossref names no volume: the series stays, the build prints no less,
        # in the fetch's spelling, not the previous output's.
        series_work("W2", "10.5555/ch2"),
        series_work("W3"),
        # Known from the previous build: no lookup.
        series_work("W4", "10.5555/ch4"),
        # A series in the previous output is no replacement.
        series_work("W5", "10.5555/ch1"),
    ]
    previous = {"10.5555/ch4": "Human-Computer Interaction", "W2": LNCS.upper(), "W5": LNCS.upper()}
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
    asked: list[str] = []

    def down(url: str, params: dict[str, str]) -> Response:
        asked.append(url)
        return Response(503, None)

    crossref = CrossrefClient(down, mailto="m@example.org", delay=0.0, sleep=no_sleep)
    works = [series_work("W1", "10.5555/ch1"), series_work("W2", "10.5555/ch2")]
    stats = BuildStats()
    backfill_venues(works, {}, crossref, stats, SERIES_NAMES)
    assert [w.venue for w in works] == [LNCS, LNCS]
    assert len([w for w in stats.warnings if w.startswith("Crossref backfill stopped")]) == 1
    # A persistent failure stops the lookups: the second DOI is never asked.
    assert asked and not [url for url in asked if "ch2" in url]


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


def test_the_first_build_after_0_9_4_resolves_series_end_to_end(tmp_path: Path) -> None:
    """The wiring: the fetch's series names reach normalize and the backfill.
    W2's platform names LNCS only through W1's book-series source, and the
    previous output holds the series 0.9.4 printed for both."""

    def chapter(work_id: str, doi: str, location: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": f"https://openalex.org/{work_id}",
            "title": f"Chapter {work_id}",
            "publication_year": 2020,
            "type": "book-chapter",
            "doi": f"https://doi.org/{doi}",
            "primary_location": location,
            "authorships": [COLLEAGUE],
        }

    raws = [
        chapter("W1", "10.5555/ch1", {"source": {"display_name": LNCS, "type": "book series"}}),
        chapter(
            "W2",
            "10.5555/ch2",
            {
                "source": {"display_name": "Springer eBooks", "type": "ebook platform"},
                "raw_source_name": "Lecture Notes in Computer Science",
            },
        ),
    ]
    printed = [
        Work(id="W1", title="Chapter W1", venue=LNCS, doi="https://doi.org/10.5555/ch1"),
        Work(
            id="W2",
            title="Chapter W2",
            venue="Lecture Notes in Computer Science",
            doi="https://doi.org/10.5555/ch2",
        ),
    ]
    (tmp_path / "publications.json").write_text(dump(document(printed)), encoding="utf-8")
    stats = _build(
        tmp_path,
        raws,
        crossref=(
            ("10.5555/ch1", in_series("Semantic Multimedia")),
            ("10.5555/ch2", in_series("Human-Computer Interaction")),
        ),
    )
    written = json.loads((tmp_path / "publications.json").read_text(encoding="utf-8"))
    assert {w["id"]: w["venue"] for w in written["works"]} == {
        "W1": "Semantic Multimedia",
        "W2": "Human-Computer Interaction",
    }
    assert "series resolved to their volume 2," in stats.summary()


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


MEMBER_ID = "A5000000001"
XPAC_NOTE = "listed only with `include_xpac`, which the config leaves off"
FETCHED_NOTE = "still fetched; this build merged it into another record or excluded it"


def _gone(work_id: str, doi: str | None = None, source: str = "openalex") -> dict[str, Any]:
    """A previous output's record that this build no longer lists."""
    return {
        "id": work_id,
        "title": f"Gone {work_id}",
        "doi": f"https://doi.org/{doi}" if doi else None,
        "source": source,
    }


def _hit(work_id: str, *author_ids: str) -> dict[str, Any]:
    """A single-work answer: its id and whose authorships it carries."""
    return {
        "id": f"https://openalex.org/{work_id}",
        "authorships": [{"author": {"id": f"https://openalex.org/{a}"}} for a in author_ids],
    }


def _found(path: str, work_id: str, *author_ids: str) -> Route:
    """The single-work answer at `works/{path}`: `_hit`'s record."""
    return (f"api.openalex.org/works/{path}", {}, _hit(work_id, *author_ids))


def _missing(url_part: str, status: int = 404) -> Route:
    return (url_part, {}, {}, status)


def _listing(filter_value: str, *work_ids: str, xpac: bool = False) -> Route:
    """The listing's answer to an `openalex_id:` filter: the default one, or
    with `xpac` the one that includes XPAC. Each matches its own requests
    only (a None in the subset matches an absent parameter)."""
    rows = [{"id": f"https://openalex.org/{w}"} for w in work_ids]
    return (
        "api.openalex.org/works",
        {"filter": filter_value, "cursor": "*", "include_xpac": "true" if xpac else None},
        {"meta": {"next_cursor": None}, "results": rows},
    )


def _trace(
    removed: list[dict[str, Any]],
    routes: list[Route] | None = None,
    *,
    raw: list[dict[str, Any]] | None = None,
    noted: dict[str, str] | None = None,
    include_xpac: bool = False,
) -> tuple[dict[str, str], list[str], FakeTransport]:
    """Run trace_removals against canned answers; any other request fails."""
    transport = FakeTransport()
    for route in routes or []:
        transport.add(*route)
    client = OpenAlexClient(transport, mailto="you@example.org", delay=0.0, sleep=no_sleep)
    delta = Delta(total=0, removed=removed, removal_notes=dict(noted or {}))
    warnings = trace_removals(
        delta, raw or [], {MEMBER_ID: "Josiah Carberry"}, client, include_xpac
    )
    return delta.removal_notes, warnings, transport


def test_a_removal_the_default_listing_hides_is_named_xpac() -> None:
    """dpsd-new's refresh, 2026-11-17: a reference entry on a member's
    profile, whose record reads `is_xpac: false`, stopped being listed."""
    single = _found("W51", "W51", MEMBER_ID)
    notes, warnings, transport = _trace(
        [_gone("W51", "10.5555/w51")],
        [single, _listing("openalex_id:W51"), _listing("openalex_id:W51", "W51", xpac=True)],
    )
    assert notes == {"W51": f"still in OpenAlex, {XPAC_NOTE}"}
    assert warnings == []
    # The single record without XPAC, then the default listing, then the XPAC
    # one for what the default missed; each listing asks for ids only.
    assert [params.get("include_xpac") for _, params in transport.calls] == [None, None, "true"]
    assert [params["select"] for _, params in transport.calls[1:]] == ["id", "id"]
    # Missing from the XPAC listing too: an absence alone names no cause.
    notes, _, _ = _trace(
        [_gone("W51", "10.5555/w51")],
        [single, _listing("openalex_id:W51"), _listing("openalex_id:W51", xpac=True)],
    )
    assert notes == {"W51": "still in OpenAlex, not in the works listing, even with `include_xpac`"}
    # Positive control: the same work, listed, reads as a missed fetch, and
    # the XPAC listing is never asked.
    notes, _, transport = _trace(
        [_gone("W51", "10.5555/w51")], [single, _listing("openalex_id:W51", "W51")]
    )
    assert notes == {
        "W51": "still in OpenAlex, on a configured profile and listed, yet not fetched: rerun first"
    }
    assert len(transport.calls) == 2


def test_removals_the_build_made_itself_need_no_lookup() -> None:
    """No route is registered: a single request would fail the test."""
    same_doi = "now listed as W64, same DOI"  # compute_delta's, offline
    notes, warnings, transport = _trace(
        [
            _gone("manual-note", source="manual"),
            _gone("W60", "10.5555/flipped"),
            _gone("W61"),
        ],
        raw=[{"id": "https://openalex.org/W61"}],
        noted={"W60": same_doi},
    )
    assert notes == {"W60": same_doi, "W61": FETCHED_NOTE}
    assert warnings == []
    assert transport.calls == []


def test_a_fetched_twin_sharing_the_doi_does_not_explain_a_removal() -> None:
    """The fetch returned another record with this DOI (excluded by type,
    say), not the removed work, so the work itself is looked up."""
    notes, _, _ = _trace(
        [_gone("W62", "10.5555/twin")],
        [
            _found("W62", "W62", MEMBER_ID),
            _listing("openalex_id:W62"),
            _listing("openalex_id:W62", "W62", xpac=True),
        ],
        raw=[{"id": "https://openalex.org/W63", "doi": "https://doi.org/10.5555/twin"}],
    )
    assert notes == {"W62": f"still in OpenAlex, {XPAC_NOTE}"}


def test_a_removal_merged_upstream_names_the_survivor() -> None:
    notes, _, _ = _trace(
        [_gone("W70"), _gone("W72")],
        [
            # Re-attributed: the member's authorship carries no configured id now.
            _found("W70", "W71", "A5000000099"),
            _found("W72", "W73", MEMBER_ID),
            _listing("openalex_id:W71", "W71"),
        ],
        raw=[{"id": "https://openalex.org/W73"}],
    )
    assert notes == {
        "W70": "merged upstream into W71, on no configured profile now",
        "W72": "merged upstream into W73, which this build fetched",
    }


def test_a_removal_is_found_by_doi_when_its_id_is_gone() -> None:
    notes, _, _ = _trace(
        [_gone("W74", "10.5555/w74"), _gone("W75", "10.5555/w75")],
        [
            _missing("api.openalex.org/works/W74"),
            _found("doi:10.5555/w74", "W76", "A5000000099"),
            _missing("api.openalex.org/works/W75"),
            _missing("api.openalex.org/works/doi:10.5555/w75"),
            _listing("openalex_id:W76"),
            _listing("openalex_id:W76", "W76", xpac=True),
        ],
    )
    assert notes == {
        # Found through the DOI only: no merge is shown, so none is claimed.
        "W74": f"its DOI is now on W76, on no configured profile now; {XPAC_NOTE}",
        "W75": "gone from OpenAlex: neither its id nor its DOI finds a work",
    }


def test_with_xpac_included_its_listing_is_the_one_asked() -> None:
    single = _found("W80", "W80", MEMBER_ID)
    notes, _, transport = _trace(
        [_gone("W80")], [single, _listing("openalex_id:W80", "W80", xpac=True)], include_xpac=True
    )
    assert notes == {
        "W80": "still in OpenAlex, on a configured profile and listed, yet not fetched: rerun first"
    }
    assert [params.get("include_xpac") for _, params in transport.calls] == [None, "true"]
    notes, _, transport = _trace(
        [_gone("W80")], [single, _listing("openalex_id:W80", xpac=True)], include_xpac=True
    )
    assert notes == {"W80": "still in OpenAlex, not in the works listing, even with `include_xpac`"}
    assert len(transport.calls) == 2  # the walked listing is the XPAC one: asked once


def test_a_doi_is_quoted_once_into_the_lookup_path() -> None:
    notes, _, transport = _trace(
        [_gone("W77", "10.1002/(sici)1097-4571")],
        [
            _missing("api.openalex.org/works/W77"),
            _missing("api.openalex.org/works/doi:10.1002/%28sici%291097-4571"),
        ],
    )
    assert notes == {"W77": "gone from OpenAlex: neither its id nor its DOI finds a work"}
    assert transport.calls[1][0] == "https://api.openalex.org/works/doi:10.1002/%28sici%291097-4571"


def test_only_the_removals_the_page_lists_are_looked_up() -> None:
    removed = [_gone(f"W{3000 + i}") for i in range(LISTED_CAP + 1)]
    notes, _, transport = _trace(removed, [_missing("api.openalex.org/works/W3")])
    assert len(notes) == len(transport.calls) == LISTED_CAP
    assert f"W{3000 + LISTED_CAP}" not in notes


def test_more_than_a_hundred_survivors_are_listed_in_batches() -> None:
    ids = [f"W{4000 + i}" for i in range(101)]
    routes = [_found(w, w, MEMBER_ID) for w in ids]
    routes += [
        _listing("openalex_id:" + "|".join(ids[:100]), *ids[:100]),
        _listing(f"openalex_id:{ids[100]}", ids[100]),
    ]
    notes, _, transport = _trace([_gone(w) for w in ids], routes)
    assert len(notes) == 101
    assert set(notes.values()) == {
        "still in OpenAlex, on a configured profile and listed, yet not fetched: rerun first"
    }
    assert len(transport.calls) == 101 + 2


@pytest.mark.parametrize(
    "body",
    [
        {},  # a 200 with no id
        None,  # a 200 that is not JSON
        ["https://openalex.org/W85"],
        {"id": "https://openalex.org/W85"},  # no authorships
        {"id": "https://openalex.org/W85", "authorships": [None]},
        {"id": "https://openalex.org/W85", "authorships": [{"author": "A5000000001"}]},
        {"id": 85, "authorships": []},
    ],
)
def test_a_malformed_answer_is_a_failure_never_a_reason(body: Any) -> None:
    """Neither "gone" nor "on no configured profile" may rest on an answer
    that is not a work record."""
    notes, warnings, _ = _trace(
        [_gone("W85", "10.5555/w85")], [("api.openalex.org/works/W85", {}, body)]
    )
    assert notes == {}
    assert len(warnings) == 1
    assert warnings[0].startswith("removed works not all traced in OpenAlex: ")


def test_a_failed_lookup_stops_the_rest_and_keeps_what_was_found() -> None:
    notes, warnings, transport = _trace(
        [_gone("W88"), _gone("W89"), _gone("W90"), _gone("W92"), _gone("W91")],
        [
            _missing("api.openalex.org/works/W88"),
            _found("W89", "W89", MEMBER_ID),
            _missing("api.openalex.org/works/W90", status=403),
            _listing("openalex_id:W89"),
            _listing("openalex_id:W89", "W89", xpac=True),
        ],
        raw=[{"id": "https://openalex.org/W91"}],
    )
    assert notes == {
        "W88": "gone from OpenAlex: neither its id nor its DOI finds a work",
        "W89": f"still in OpenAlex, {XPAC_NOTE}",
        "W91": FETCHED_NOTE,
    }
    assert len(warnings) == 1
    assert warnings[0].startswith("removed works not all traced in OpenAlex: ")
    # W92 was never asked: the lookups stopped at W90's failure.
    assert not any("W92" in url for url, _ in transport.calls)


@pytest.mark.parametrize(
    ("body", "status"),
    [({}, 403), ({"meta": {"next_cursor": None}}, 200)],  # a refusal; a page without results
)
def test_a_failed_listing_keeps_the_reasons_that_need_no_listing(
    body: dict[str, Any], status: int
) -> None:
    notes, warnings, _ = _trace(
        [_gone("W93"), _gone("W94"), _gone("W95"), _gone("W97")],
        [
            _found("W93", "W93", MEMBER_ID),
            _missing("api.openalex.org/works/W94"),
            _found("W95", "W96", MEMBER_ID),
            _found("W97", "W97", "A5000000099"),
            ("api.openalex.org/works", {"filter": "openalex_id:W93|W97"}, body, status),
        ],
        raw=[{"id": "https://openalex.org/W96"}],
    )
    assert notes == {
        # W93 is on a member's profile: only the listing could say why it left.
        "W94": "gone from OpenAlex: neither its id nor its DOI finds a work",
        "W95": "merged upstream into W96, which this build fetched",
        "W97": "still in OpenAlex, on no configured profile now",
    }
    assert len(warnings) == 1
    assert warnings[0].startswith("removed works not checked against the OpenAlex listing: ")


def test_a_failed_xpac_listing_keeps_what_the_default_listing_said() -> None:
    notes, warnings, _ = _trace(
        [_gone("W83"), _gone("W84")],
        [
            _found("W83", "W83", MEMBER_ID),
            _found("W84", "W84", MEMBER_ID),
            _listing("openalex_id:W83|W84", "W83"),
            (
                "api.openalex.org/works",
                {"filter": "openalex_id:W84", "include_xpac": "true"},
                {},
                403,
            ),
        ],
    )
    # W84 is missing from the default listing, and only the XPAC one could say why.
    assert notes == {
        "W83": "still in OpenAlex, on a configured profile and listed, yet not fetched: rerun first"
    }
    assert len(warnings) == 1
    assert warnings[0].startswith(
        "removed works not checked against the OpenAlex listing with `include_xpac`: "
    )


def test_a_failed_lookup_and_a_failed_listing_are_both_reported() -> None:
    _, warnings, _ = _trace(
        [_gone("W81"), _gone("W82")],
        [
            _found("W81", "W81", MEMBER_ID),
            _missing("api.openalex.org/works/W82", status=403),
            ("api.openalex.org/works", {"filter": "openalex_id:W81"}, {}, 403),
        ],
    )
    assert [w.split(":")[0] for w in warnings] == [
        "removed works not all traced in OpenAlex",
        "removed works not checked against the OpenAlex listing",
    ]


def test_a_trace_that_breaks_costs_neither_the_output_nor_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: object) -> list[str]:
        raise RuntimeError("unforeseen")

    monkeypatch.setattr(pipeline, "trace_removals", broken)
    (tmp_path / "publications.json").write_text(
        dump(document([Work(id="W99", title="A reference entry")])), encoding="utf-8"
    )
    stats = _build_one(tmp_path, [], explain_removals=True)
    assert "removed works not traced: RuntimeError: unforeseen" in stats.warnings
    assert stats.written
    assert '"id": "W1"' in (tmp_path / "publications.json").read_text(encoding="utf-8")


def test_a_build_prints_why_a_listed_work_was_removed(tmp_path: Path) -> None:
    gone = Work(id="W99", title="A reference entry", doi="https://doi.org/10.5555/entry")
    (tmp_path / "publications.json").write_text(dump(document([gone])), encoding="utf-8")
    raw = {
        "id": "https://openalex.org/W1",
        "title": "Still here",
        "publication_year": 2026,
        "type": "article",
        "authorships": [COLLEAGUE],
    }
    routes: tuple[Route, ...] = (
        _found("W99", "W99", MEMBER_ID),
        _listing("openalex_id:W99"),
        _listing("openalex_id:W99", "W99", xpac=True),
    )
    stats = _build(tmp_path, [raw], openalex_routes=routes, explain_removals=True)
    page = render_markdown(stats.delta, stats.warnings)
    assert "#### Removed (1)" in page
    assert f"  https://doi.org/10.5555/entry\n  Why: still in OpenAlex, {XPAC_NOTE}\n" in page
    # Without the flag (a build with no summary to write) nothing is looked up.
    (tmp_path / "publications.json").write_text(dump(document([gone])), encoding="utf-8")
    stats = _build(tmp_path, [raw])
    assert stats.delta.removed and not stats.delta.removal_notes
