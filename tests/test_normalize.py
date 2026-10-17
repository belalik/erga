from __future__ import annotations

from typing import Any

from erga.dedup import dedup_by_doi
from erga.normalize import (
    malformed_dois,
    map_type,
    normalize_work,
    open_access_url,
    platform_names,
    reconstruct_abstract,
    unescape_html,
    unmapped_types,
    venue,
)


def test_unescape_html_decodes_until_stable() -> None:
    assert unescape_html("Systems &amp; Multimedia") == "Systems & Multimedia"
    assert unescape_html("Bob&amp;#039;s") == "Bob's"
    assert unescape_html("Plain & simple") == "Plain & simple"
    assert unescape_html("") == ""


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
    assert map_type({"type": "reference-entry"}) == "book-chapter"
    assert map_type({"type": "erratum"}) == "other"
    assert map_type({"type": "peer-review"}) == "other"
    assert map_type({"type": "conference-abstract"}) == "other"
    assert map_type({"type": "report"}) == "other"
    assert map_type({"type": None}) == "other"
    assert map_type({}) == "other"


def test_map_type_reference_entry_ignores_a_journal_typed_source() -> None:
    # Springer's Encyclopedia of Computer Graphics and Games is a source
    # OpenAlex types "journal"; its entries are still chapters.
    raw = {"type": "reference-entry", "primary_location": {"source": {"type": "journal"}}}
    assert map_type(raw) == "book-chapter"


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
        {"type": "peer-review"},
        {"type": "conference-abstract"},
        {"type": "report"},
        {"type": "reference-entry"},  # mapped since 2026-09-30
        {"type": "other"},  # upstream said other; the fallback is an identity
        {"type": "expression-of-concern"},
        {"type": "expression-of-concern"},
        {"type": None},
        {},
    ]
    assert unmapped_types(raw_works) == {"expression-of-concern": 2}


WRAPPED_DOI = 'https://doi.org/10.5555/xyz123">https://dx.doi.org/10.5555/xyz123</a'


def test_malformed_dois_lists_only_fields_holding_more_than_a_doi() -> None:
    raw_works: list[dict[str, Any]] = [
        raw_work(),
        raw_work(id="https://openalex.org/W1002", doi=WRAPPED_DOI),
        raw_work(id="https://openalex.org/W1003", doi=None),
    ]
    assert malformed_dois(raw_works) == ["W1002"]


def test_repository_copy_with_a_wrapped_doi_merges_with_its_version_of_record() -> None:
    # The harm the cleaning prevents: a copy whose DOI never matches stays a
    # separate record, and every DOI-keyed override or tag misses it.
    record = normalize_work(raw_work(), {}, {}, {})
    copy = normalize_work(
        raw_work(id="https://openalex.org/W1002", doi=WRAPPED_DOI, title="A Repository Copy"),
        {},
        {},
        {},
    )
    assert copy.doi == "https://doi.org/10.5555/xyz123"
    assert len(dedup_by_doi([record, copy])) == 1


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


def platform_location(
    raw_source_name: str | None = "Problems of Fracture Mechanics",
) -> dict[str, Any]:
    location: dict[str, Any] = {
        "source": {"display_name": "Springer eBooks", "type": "ebook platform"}
    }
    if raw_source_name is not None:
        location["raw_source_name"] = raw_source_name
    return location


def test_venue_is_the_book_not_the_platform() -> None:
    # OpenAlex files a chapter under the publisher's platform; the book's
    # title survives only as the location's raw source name.
    assert venue({"primary_location": platform_location()}) == "Problems of Fracture Mechanics"
    work = normalize_work(
        raw_work(type="book-chapter", primary_location=platform_location()),
        tracked_ids={},
        tracked_orcids={},
        tracked_names={},
    )
    assert work.venue == "Problems of Fracture Mechanics"
    assert work.type == "book-chapter"


def test_venue_falls_back_to_the_platform_without_a_raw_name() -> None:
    assert venue({"primary_location": platform_location(raw_source_name=None)}) == "Springer eBooks"
    assert venue({"primary_location": platform_location(raw_source_name="")}) == "Springer eBooks"


def test_venue_keeps_the_source_name_off_platforms() -> None:
    # The rule is gated on the source type, not on a raw name differing:
    # a journal's curated name beats whatever the publisher deposited.
    location = {
        "source": {"display_name": "Journal of Psychoceramics", "type": "journal"},
        "raw_source_name": "J. Psychoceram.",
    }
    assert venue({"primary_location": location}) == "Journal of Psychoceramics"
    assert venue({"primary_location": None}) is None
    assert venue({"primary_location": {"source": None}}) is None


def test_venue_and_title_arrive_decoded() -> None:
    # OpenAlex serves some source names escaped (W4319978610's IEEE joint
    # conference), and a site that escapes on render printed `&amp;`.
    location = {
        "source": {"display_name": "ICE/ITMC &amp; IAMOT Joint Conference", "type": "conference"}
    }
    assert venue({"primary_location": location}) == "ICE/ITMC & IAMOT Joint Conference"
    escaped_book = platform_location(raw_source_name="Theory &amp; Practice")
    assert venue({"primary_location": escaped_book}) == "Theory & Practice"
    work = normalize_work(
        raw_work(title="Cups &amp;amp; Saucers", primary_location=location),
        tracked_ids={},
        tracked_orcids={},
        tracked_names={},
    )
    assert work.title == "Cups & Saucers"
    assert work.venue == "ICE/ITMC & IAMOT Joint Conference"


def test_venue_without_a_source_stays_unknown() -> None:
    # The raw name of a source-less location is the depositor's text, a PDF
    # URL as often as not; unknown goes on to the ratchet and Crossref.
    location = {"source": None, "raw_source_name": "http://example.org/papers/2009.pdf"}
    assert venue({"primary_location": location}) is None
    assert venue({"primary_location": {"raw_source_name": "EDULEARN15 Proceedings"}}) is None


def test_platform_names_collects_only_platform_sources() -> None:
    raw_works: list[dict[str, Any]] = [
        {"primary_location": platform_location()},
        {
            "primary_location": {
                "source": {"display_name": "Routledge eBooks", "type": "ebook platform"}
            }
        },
        {"primary_location": {"source": {"display_name": "Springer Journals", "type": "journal"}}},
        {"primary_location": None},
    ]
    assert platform_names(raw_works) == frozenset({"Springer eBooks", "Routledge eBooks"})
    assert platform_names([]) == frozenset()
    escaped = {"source": {"display_name": "Taylor &amp; Francis eBooks", "type": "ebook platform"}}
    assert platform_names([{"primary_location": escaped}]) == frozenset({"Taylor & Francis eBooks"})
