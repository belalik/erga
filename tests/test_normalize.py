from __future__ import annotations

from typing import Any

from erga.normalize import (
    map_type,
    normalize_work,
    open_access_url,
    reconstruct_abstract,
    unmapped_types,
)


def test_reconstruct_abstract() -> None:
    index = {"world": [1], "Hello": [0], "hello": [2]}
    assert reconstruct_abstract(index) == "Hello world hello"
    assert reconstruct_abstract(None) is None
    assert reconstruct_abstract({}) is None


def test_reconstruct_abstract_decodes_entities_and_strips_tags() -> None:
    # Single- and double-encoded entities: unescape until stable.
    assert reconstruct_abstract({"Alice&#039;s": [0], "results": [1]}) == "Alice's results"
    assert reconstruct_abstract({"Bob&amp;#039;s": [0], "data": [1]}) == "Bob's data"
    # Literal tags and entity-encoded tags (visible only after unescaping).
    assert reconstruct_abstract({"line<br>break": [0]}) == "linebreak"
    assert reconstruct_abstract({"&lt;p&gt;Intro": [0], "text&lt;/p&gt;": [1]}) == "Intro text"
    # An abstract that is nothing but markup collapses to None, not "".
    assert reconstruct_abstract({"&lt;p&gt;&lt;/p&gt;": [0]}) is None


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


def test_map_type_software_paper_at_journal_source_is_journal() -> None:
    # A peer-reviewed article about software (SoftwareX, JOSS), not an artifact.
    raw = {"type": "software-paper", "primary_location": {"source": {"type": "journal"}}}
    assert map_type(raw) == "journal"
    raw = {"type": "software-paper", "primary_location": {"source": {"type": "repository"}}}
    assert map_type(raw) == "software"
    assert map_type({"type": "software-paper"}) == "software"
    # An actual software record never becomes an article.
    raw = {"type": "software", "primary_location": {"source": {"type": "journal"}}}
    assert map_type(raw) == "software"


def test_unmapped_types_flags_only_undecided_vocabulary() -> None:
    raw_works: list[dict[str, Any]] = [
        {"type": "article"},  # mapped
        {"type": "erratum"},  # deliberately other
        {"type": "expression-of-concern"},
        {"type": "expression-of-concern"},
        {"type": None},
        {},
    ]
    assert unmapped_types(raw_works) == {"expression-of-concern": 2}


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
        raw_work(), tracked_ids={"A5000000001": "J. Carberry"}, tracked_orcids={}, tracked_names={}
    )
    assert work.id == "W1001"
    assert work.venue == "Journal of Psychoceramics"
    assert work.doi == "https://doi.org/10.5555/xyz123"
    assert [a.tracked for a in work.authors] == [True, False, False]
    assert [a.tracked_as for a in work.authors] == ["J. Carberry", None, None]
    assert work.authors[2].name == "Anonymous Collaborator"
    assert work.source == "openalex"


def test_normalize_work_tracked_by_orcid_despite_unknown_id() -> None:
    # Split profiles: the id is not among the resolved ones, the ORCID still matches.
    work = normalize_work(
        raw_work(),
        tracked_ids={},
        tracked_orcids={"0000-0002-1825-0097": "J. Carberry"},
        tracked_names={},
    )
    assert [a.tracked for a in work.authors] == [True, False, False]
    assert work.authors[0].tracked_as == "J. Carberry"


def test_normalize_work_tracked_by_name_despite_unknown_id_and_orcid() -> None:
    # Conflated homonym profiles: neither id nor ORCID can match, the
    # configured name (casefolded) still does.
    work = normalize_work(
        raw_work(),
        tracked_ids={},
        tracked_orcids={},
        tracked_names={"josiah carberry": "J. Carberry"},
    )
    assert [a.tracked for a in work.authors] == [True, False, False]
    assert work.authors[0].tracked_as == "J. Carberry"


def test_normalize_work_null_venue_and_defaults() -> None:
    work = normalize_work(
        raw_work(primary_location=None, doi=None, title=None, cited_by_count=None),
        tracked_ids={},
        tracked_orcids={},
        tracked_names={},
    )
    assert work.venue is None
    assert work.doi is None
    assert work.title == ""
    assert work.cited_by_count == 0
