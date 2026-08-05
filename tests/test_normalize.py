from __future__ import annotations

from typing import Any

from erga.normalize import map_type, normalize_work, open_access_url, reconstruct_abstract


def test_reconstruct_abstract() -> None:
    index = {"world": [1], "Hello": [0], "hello": [2]}
    assert reconstruct_abstract(index) == "Hello world hello"
    assert reconstruct_abstract(None) is None
    assert reconstruct_abstract({}) is None


def test_map_type_vocabulary() -> None:
    assert map_type({"type": "article"}) == "journal"
    assert map_type({"type": "review"}) == "journal"
    assert map_type({"type": "conference-paper"}) == "conference"
    assert map_type({"type": "dissertation"}) == "thesis"
    assert map_type({"type": "software-paper"}) == "software"
    assert map_type({"type": "erratum"}) == "other"
    assert map_type({"type": None}) == "other"
    assert map_type({}) == "other"


def test_map_type_conference_from_source() -> None:
    raw = {"type": "article", "primary_location": {"source": {"type": "conference"}}}
    assert map_type(raw) == "conference"
    # Only journal-mapped types get the conference refinement.
    raw = {"type": "dataset", "primary_location": {"source": {"type": "conference"}}}
    assert map_type(raw) == "dataset"


def test_open_access_url_preference_order() -> None:
    assert (
        open_access_url(
            {
                "open_access": {"oa_url": "https://a.example/oa"},
                "best_oa_location": {"pdf_url": "https://a.example/pdf"},
            }
        )
        == "https://a.example/oa"
    )
    assert (
        open_access_url(
            {
                "open_access": {"oa_url": None},
                "best_oa_location": {
                    "pdf_url": "https://a.example/pdf",
                    "landing_page_url": "https://a.example/landing",
                },
            }
        )
        == "https://a.example/pdf"
    )
    assert (
        open_access_url({"best_oa_location": {"landing_page_url": "https://a.example/landing"}})
        == "https://a.example/landing"
    )
    assert open_access_url({"open_access": {"oa_url": None}, "best_oa_location": None}) is None


def raw_work(**extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "https://openalex.org/W1001",
        "title": "Toward a Unified Theory",
        "publication_year": 2024,
        "publication_date": "2024-03-01",
        "type": "article",
        "doi": "https://doi.org/10.5555/xyz123",
        "cited_by_count": 42,
        "is_retracted": False,
        "primary_location": {"source": {"display_name": "Journal of Psychoceramics"}},
        "authorships": [
            {
                "author": {
                    "id": "https://openalex.org/A5000000001",
                    "display_name": "Josiah Carberry",
                    "orcid": "https://orcid.org/0000-0002-1825-0097",
                }
            },
            {"author": {"id": "https://openalex.org/A5999999999", "display_name": "Someone Else"}},
            {"author": {}, "raw_author_name": "Anonymous Collaborator"},
        ],
    }
    base.update(extra)
    return base


def test_normalize_work_tracked_by_id() -> None:
    work = normalize_work(
        raw_work(), tracked_ids={"A5000000001"}, tracked_orcids=set(), tracked_names=set()
    )
    assert work.id == "W1001"
    assert work.venue == "Journal of Psychoceramics"
    assert work.doi == "https://doi.org/10.5555/xyz123"
    assert [a.tracked for a in work.authors] == [True, False, False]
    assert work.authors[2].name == "Anonymous Collaborator"
    assert work.source == "openalex"


def test_normalize_work_tracked_by_orcid_despite_unknown_id() -> None:
    # Split profiles: the id is not among the resolved ones, the ORCID still matches.
    work = normalize_work(
        raw_work(),
        tracked_ids=set(),
        tracked_orcids={"0000-0002-1825-0097"},
        tracked_names=set(),
    )
    assert [a.tracked for a in work.authors] == [True, False, False]


def test_normalize_work_tracked_by_name_despite_unknown_id_and_orcid() -> None:
    # Conflated homonym profiles: neither id nor ORCID can match, the
    # configured name (casefolded) still does.
    work = normalize_work(
        raw_work(),
        tracked_ids=set(),
        tracked_orcids=set(),
        tracked_names={"josiah carberry"},
    )
    assert [a.tracked for a in work.authors] == [True, False, False]


def test_normalize_work_null_venue_and_defaults() -> None:
    work = normalize_work(
        raw_work(primary_location=None, doi=None, title=None, cited_by_count=None),
        tracked_ids=set(),
        tracked_orcids=set(),
        tracked_names=set(),
    )
    assert work.venue is None
    assert work.doi is None
    assert work.title == ""
    assert work.cited_by_count == 0
