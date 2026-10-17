from __future__ import annotations

from typing import Any

from conftest import FakeTransport, no_sleep
from erga.crossref import CrossrefClient
from erga.model import Work
from erga.pipeline import (
    BuildStats,
    backfill_venues,
    curate,
    exclude_by_type,
    exclude_machine_translations,
    ratchet_venues,
)


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
