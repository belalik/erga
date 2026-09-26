from __future__ import annotations

from pathlib import Path

import pytest

from conftest import FakeTransport, add_pages, no_sleep
from erga.config import AuthorConfig, Config
from erga.model import Work
from erga.openalex import OpenAlexClient
from erga.output import document, dump
from erga.verify import BYLINE_SEARCH_LIMIT, _byline_matches, verify_report


def profile(author_id: str, name: str, works: int, alternatives: list[str]) -> dict[str, object]:
    return {
        "id": f"https://openalex.org/{author_id}",
        "display_name": name,
        "display_name_alternatives": alternatives,
        "works_count": works,
    }


def author_page(profiles: list[dict[str, object]], total: int | None = None) -> dict[str, object]:
    return {"results": profiles, "meta": {"count": total if total is not None else len(profiles)}}


def make_client(transport: FakeTransport) -> OpenAlexClient:
    return OpenAlexClient(transport, mailto="m@example.org", delay=0.0, sleep=no_sleep)


def add_search(transport: FakeTransport, name: str, page: dict[str, object]) -> None:
    transport.add("/authors", {"search": name}, page)


def test_verify_report_split_orcid_and_zero_works() -> None:
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": "orcid:0000-0002-1825-0097"},
        author_page(
            [
                profile("A1", "Josiah Carberry", 8, ["J. S. Carberry"]),
                profile("A2", "J. Carberry", 1, []),
            ]
        ),
    )
    transport.add(
        "/works",
        {"filter": "author.id:A1", "sort": "publication_date:desc"},
        {"results": [{"title": "Toward a Unified Theory", "publication_year": 2024}]},
    )
    transport.add(
        "/works",
        {"filter": "author.id:A2", "sort": "publication_date:desc"},
        {"results": []},
    )
    transport.add("/authors/A5000000009", {}, profile("A5000000009", "Silent Sam", 0, []))
    transport.add(
        "/works",
        {"filter": "author.id:A5000000009", "sort": "publication_date:desc"},
        {"results": []},
    )
    add_search(transport, "Josiah Carberry", author_page([]))
    add_search(transport, "Silent Sam", author_page([]))

    config = Config(
        mailto="m@example.org",
        authors=[
            AuthorConfig(name="Josiah Carberry", orcid="0000-0002-1825-0097"),
            AuthorConfig(name="Silent Sam", openalex_id="A5000000009"),
        ],
    )
    report, warnings = verify_report(config, make_client(transport))

    assert "A1  Josiah Carberry — 8 works" in report
    assert "also known as: J. S. Carberry" in report
    assert "recent: Toward a Unified Theory (2024)" in report
    assert "Silent Sam" in report
    assert any("2 author ids" in w and "split profile" in w for w in warnings)
    assert any("zero works" in w for w in warnings)


def test_verify_report_tracking_only_author_resolves_nothing() -> None:
    transport = FakeTransport()
    add_search(transport, "Priya Nair", author_page([]))
    config = Config(mailto="m@example.org", authors=[AuthorConfig(name="Priya Nair")])
    report, warnings = verify_report(config, make_client(transport))
    assert "Priya Nair (no ids; tracked by name only, nothing fetched)" in report
    assert warnings == []


def test_verify_report_unresolved_orcid_warns_without_aborting() -> None:
    transport = FakeTransport()
    transport.add("/authors", {"filter": "orcid:0000-0002-1825-0097"}, author_page([]))
    add_search(transport, "Nobody Yet", author_page([]))
    config = Config(
        mailto="m@example.org",
        authors=[AuthorConfig(name="Nobody Yet", orcid="0000-0002-1825-0097")],
    )
    report, warnings = verify_report(config, make_client(transport))
    assert "resolved to no OpenAlex author" in report
    assert any("no OpenAlex author id" in w for w in warnings)


def test_verify_report_contaminated_orcid_flags_different_people() -> None:
    """Strangers carrying the iD is not a split profile and gets its own advice."""
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": "orcid:0000-0002-1825-0097"},
        author_page(
            [
                profile("A1", "Josiah Carberry", 8, []),
                profile("A2", "John Smith", 300, []),
            ]
        ),
    )
    for author_id in ["A1", "A2"]:
        transport.add(
            "/works",
            {"filter": f"author.id:{author_id}", "sort": "publication_date:desc"},
            {"results": []},
        )
    add_search(transport, "Josiah Carberry", author_page([]))
    config = Config(
        mailto="m@example.org",
        authors=[AuthorConfig(name="Josiah Carberry", orcid="0000-0002-1825-0097")],
    )
    _, warnings = verify_report(config, make_client(transport))
    contaminated = [w for w in warnings if "different people" in w]
    assert len(contaminated) == 1
    assert "2 author profiles" in contaminated[0]
    assert "'John Smith'" in contaminated[0]
    assert "remove the orcid and pin openalex_id" in contaminated[0]
    assert not any("split profile" in w for w in warnings)


def test_verify_report_single_profile_name_mismatch_warns() -> None:
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": "orcid:0000-0002-1825-0097"},
        author_page([profile("A9", "Someone Else", 40, [])]),
    )
    transport.add(
        "/works",
        {"filter": "author.id:A9", "sort": "publication_date:desc"},
        {"results": []},
    )
    add_search(transport, "Josiah Carberry", author_page([]))
    config = Config(
        mailto="m@example.org",
        authors=[AuthorConfig(name="Josiah Carberry", orcid="0000-0002-1825-0097")],
    )
    _, warnings = verify_report(config, make_client(transport))
    assert any(
        "'Someone Else'" in w and "does not look like the configured name" in w for w in warnings
    )


def test_verify_report_wrong_pinned_id_does_not_blame_the_orcid() -> None:
    """A stranger from a mistyped openalex_id must not trigger the ORCID advice."""
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": "orcid:0000-0002-1825-0097"},
        author_page([profile("A1", "Josiah Carberry", 8, [])]),
    )
    transport.add("/authors/A5000000123", {}, profile("A5000000123", "Someone Else", 40, []))
    for author_id in ["A1", "A5000000123"]:
        transport.add(
            "/works",
            {"filter": f"author.id:{author_id}", "sort": "publication_date:desc"},
            {"results": []},
        )
    add_search(transport, "Josiah Carberry", author_page([]))
    config = Config(
        mailto="m@example.org",
        authors=[
            AuthorConfig(
                name="Josiah Carberry",
                orcid="0000-0002-1825-0097",
                openalex_id="A5000000123",
            )
        ],
    )
    _, warnings = verify_report(config, make_client(transport))
    assert not any("different people" in w or "remove the orcid" in w for w in warnings)
    assert any(
        "'Someone Else'" in w and "does not look like the configured name" in w for w in warnings
    )


def test_verify_report_name_match_survives_diacritics_and_initials() -> None:
    """'J. Carbérry' matches 'Josiah Carberry': initials drop, accents strip."""
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": "orcid:0000-0002-1825-0097"},
        author_page([profile("A1", "J. Carbérry", 8, [])]),
    )
    transport.add(
        "/works",
        {"filter": "author.id:A1", "sort": "publication_date:desc"},
        {"results": []},
    )
    add_search(transport, "Josiah Carberry", author_page([]))
    config = Config(
        mailto="m@example.org",
        authors=[AuthorConfig(name="Josiah Carberry", orcid="0000-0002-1825-0097")],
    )
    _, warnings = verify_report(config, make_client(transport))
    assert not any("does not look like" in w for w in warnings)


def test_verify_report_lists_same_name_profiles_not_configured() -> None:
    """The Zissis pattern: a tracking-only author's homonym profiles surface."""
    transport = FakeTransport()
    add_search(
        transport,
        "Dimitrios Zissis",
        author_page(
            [
                profile("A100", "Dimitrios Zissis", 45, []),
                profile("A101", "D. Zissis", 12, []),
            ],
            total=9,
        ),
    )
    config = Config(mailto="m@example.org", authors=[AuthorConfig(name="Dimitrios Zissis")])
    report, warnings = verify_report(config, make_client(transport))
    assert "same name, not configured: A100  Dimitrios Zissis — 45 works" in report
    assert "same name, not configured: A101  D. Zissis — 12 works" in report
    assert "and 7 more name match(es)" in report
    assert warnings == []


def test_verify_report_name_search_excludes_resolved_profiles() -> None:
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": "orcid:0000-0002-1825-0097"},
        author_page([profile("A1", "Josiah Carberry", 8, [])]),
    )
    transport.add(
        "/works",
        {"filter": "author.id:A1", "sort": "publication_date:desc"},
        {"results": [{"title": "T", "publication_year": 2024}]},
    )
    add_search(
        transport,
        "Josiah Carberry",
        author_page(
            [
                profile("A1", "Josiah Carberry", 8, []),
                profile("A200", "Josiah Carberry", 120, []),
            ]
        ),
    )
    config = Config(
        mailto="m@example.org",
        authors=[AuthorConfig(name="Josiah Carberry", orcid="0000-0002-1825-0097")],
    )
    report, _ = verify_report(config, make_client(transport))
    assert "same name, not configured: A200" in report
    assert "same name, not configured: A1 " not in report


@pytest.mark.parametrize(
    ("byline", "configured", "expected"),
    [
        ("Priya Nair", "Priya Nair", True),
        ("Nair, Priya", "Priya Nair", True),  # bylines keep the printed order
        ("Priya K. Nair", "Priya Nair", True),  # a middle initial is extra, not wrong
        ("P. Nair", "Priya Nair", False),  # a full word never matches an initial
        ("Priya Nair", "P. Nair", True),
        ("Priya K. Nair", "P. Nair", True),
        ("K. Nair", "P. Nair", False),  # the initial is contradicted
        ("Nair", "P. Nair", True),  # nothing left to contradict it
        ("Priya Nair", "Priya S. Nair", True),
        ("Priya K. Nair", "Priya S. Nair", False),
        ("Anna-Maria Kovač", "Anna Maria Kovac", True),  # hyphens and accents fold
        ("Παπαδοπούλου, Μαρία", "Μαρία Παπαδοπουλου", True),
        ("Ravi Nair", "Priya Nair", False),
    ],
)
def test_byline_matches(byline: str, configured: str, expected: bool) -> None:
    assert _byline_matches(byline, configured) is expected


def raw_work(
    work_id: str,
    title: str,
    *,
    doi: str | None = None,
    work_type: str = "article",
    year: int = 2024,
    bylines: tuple[tuple[str, str | None], ...] = (("Priya Nair", None),),
) -> dict[str, object]:
    """A raw OpenAlex work; a None author id is an authorship linked to no one."""
    return {
        "id": f"https://openalex.org/{work_id}",
        "title": title,
        "publication_year": year,
        "type": work_type,
        "doi": f"https://doi.org/{doi}" if doi else None,
        "authorships": [
            {
                "raw_author_name": name,
                "author": {"id": f"https://openalex.org/{author_id}" if author_id else None},
            }
            for name, author_id in bylines
        ],
    }


def add_byline_search(
    transport: FakeTransport,
    filters: str,
    pages: list[list[object]],
    total: int | None = None,
) -> None:
    count = sum(len(page) for page in pages) if total is None else total
    add_pages(transport, "/works", {"filter": filters}, pages, count=count)


def write_published(path: Path, works: list[Work]) -> None:
    path.write_text(dump(document(works)), encoding="utf-8")


def byline_calls(transport: FakeTransport) -> list[dict[str, str]]:
    return [p for _, p in transport.calls if p.get("filter", "").startswith("raw_author_name")]


def test_unlinked_bylines_report_gaps_and_repairs_against_the_published_list(
    tmp_path: Path,
) -> None:
    output = tmp_path / "publications.json"
    write_published(
        output,
        [
            Work(id="W10", title="Already Listed By Its Id"),
            Work(
                id="W11",
                title="Listed Under Its Version Of Record",
                doi="https://doi.org/10.5555/twin",
            ),
            Work(id="W20", title="A Broken Copy Without Its DOI"),
            Work(
                id="W21", title="A Listed Twin With Its Own DOI", doi="https://doi.org/10.5555/vor"
            ),
            Work(id="W22", title="A Version Of Record Listed Bare", type="journal"),
        ],
    )
    transport = FakeTransport()
    add_search(transport, "Priya Nair", author_page([]))
    add_byline_search(
        transport,
        "raw_author_name.search:Priya Nair",
        [
            [
                raw_work(
                    "W1",
                    "A Paper No Profile Fetch Sees",
                    doi="10.5555/missing",
                    bylines=(("Nair, Priya", None),),
                ),
                raw_work("W10", "Already Listed By Its Id"),
                raw_work("W3", "Listed Under Another Record", doi="10.5555/twin"),
                raw_work("W4", "A Broken Copy Without Its DOI", doi="10.5555/better"),
                raw_work("W5", "Linked To A Profile Already", bylines=(("Priya Nair", "A9"),)),
                raw_work("W6", "A Namesake Paper Entirely", bylines=(("Ravi Nair", None),)),
                raw_work("W7", "Correction To A Paper Of Hers", work_type="erratum"),
                raw_work("W8", "Synthetic Coastal Dataset", work_type="dataset", doi="10.5281/v1"),
                raw_work("W9", "Synthetic Coastal Dataset", work_type="dataset", doi="10.5281/v2"),
                raw_work("W12", "A Listed Twin With Its Own DOI", doi="10.5555/preprint"),
            ],
            # A deposit's DOI loses to the listed version of record: no repair.
            [raw_work("W13", "A Version Of Record Listed Bare", doi="10.48550/arxiv.2401.1")],
        ],
    )
    config = Config(
        mailto="m@example.org",
        # The alias repeats the name in another case: one search, not two.
        authors=[AuthorConfig(name="Priya Nair", aliases=["priya nair"])],
        output_path=output,
        exclude_types=frozenset({"other"}),
    )

    report, warnings = verify_report(config, make_client(transport))

    assert "not on the published list: 2 work(s); add any that are theirs to manual.yml" in report
    assert "W1  A Paper No Profile Fetch Sees (2024)  10.5555/missing  as 'Nair, Priya'" in report
    # Two releases of one dataset are one line, as a build would keep them.
    assert ("W8  Synthetic" in report) != ("W9  Synthetic" in report)
    assert "better record for a listed work: W4 carries 10.5555/better; listed as W20" in report
    for dropped in ("W10  ", "W3  ", "W5  ", "W6  ", "W7  ", "W12", "W13"):
        assert dropped not in report
    assert f"Unlinked bylines: compared against {output} (5 works)." in report
    # Both pages walked, and the alias did not search a second time.
    assert [p["cursor"] for p in byline_calls(transport)] == ["*", "page-2"]
    assert warnings == []


def test_unlinked_bylines_leave_the_authors_own_profiles_to_the_fetch(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [])
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": "orcid:9999-0000-0000-0001"},
        author_page([profile("A1", "Josiah Carberry", 8, []), profile("A2", "J. Carberry", 1, [])]),
    )
    for author_id in ("A1", "A2"):
        transport.add(
            "/works",
            {"filter": f"author.id:{author_id}", "sort": "publication_date:desc"},
            {"results": []},
        )
    add_search(transport, "Josiah Carberry", author_page([]))
    add_byline_search(
        transport,
        "raw_author_name.search:Josiah Carberry,author.id:!A1|A2",
        [[raw_work("W1", "Unlinked Everywhere But Here", bylines=(("Josiah Carberry", None),))]],
    )
    config = Config(
        mailto="m@example.org",
        authors=[AuthorConfig(name="Josiah Carberry", orcid="9999-0000-0000-0001")],
        output_path=output,
    )

    report, _ = verify_report(config, make_client(transport))

    assert "W1  Unlinked Everywhere But Here (2024)  as 'Josiah Carberry'" in report


def test_unlinked_bylines_not_checked_without_a_published_list(tmp_path: Path) -> None:
    transport = FakeTransport()
    add_search(transport, "Priya Nair", author_page([]))
    output = tmp_path / "publications.json"
    config = Config(
        mailto="m@example.org", authors=[AuthorConfig(name="Priya Nair")], output_path=output
    )

    report, _ = verify_report(config, make_client(transport))

    assert f"not checked; no published list at {output} yet" in report
    assert byline_calls(transport) == []

    output.write_text("not json", encoding="utf-8")
    report, _ = verify_report(config, make_client(transport))
    assert f"not checked; {output} is not a publications.json erga can read" in report
    assert byline_calls(transport) == []


def test_unlinked_bylines_skip_a_name_too_common_to_judge(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [])
    transport = FakeTransport()
    add_search(transport, "Wei Zhang", author_page([]))
    add_byline_search(
        transport,
        "raw_author_name.search:Wei Zhang",
        [[raw_work("W1", "Some Paper", bylines=(("Wei Zhang", None),))], []],
        total=BYLINE_SEARCH_LIMIT + 1,
    )
    config = Config(
        mailto="m@example.org", authors=[AuthorConfig(name="Wei Zhang")], output_path=output
    )

    report, _ = verify_report(config, make_client(transport))

    assert f"byline search skipped for 'Wei Zhang': {BYLINE_SEARCH_LIMIT + 1} works" in report
    assert "W1  " not in report
    # The first page's count decides; nothing past it is walked.
    assert [p["cursor"] for p in byline_calls(transport)] == ["*"]
