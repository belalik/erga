from __future__ import annotations

from erga.model import Work
from erga.pipeline import exclude_by_type, ratchet_venues


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
