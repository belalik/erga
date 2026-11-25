from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conftest import FakeTransport, add_pages, no_sleep
from erga.config import AuthorConfig, Config
from erga.model import Work, WorkAuthor
from erga.openalex import OpenAlexClient
from erga.output import document, dump
from erga.verify import BYLINE_SEARCH_LIMIT, _byline_matches, _xpac_link, verify_report

# How a build credits the configured author on a record it lists.
CREDITED = WorkAuthor(name="Priya Nair", tracked=True, tracked_as="Priya Nair")
# The byline search for her name; test_openalex pins the phrase syntax.
PRIYA_BYLINES = 'raw_author_name.search:"Priya Nair"~2 OR "Nair Priya"~2'
JOSIAH_ORCID = "9999-0000-0000-0001"


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
    assert not any("consider pinning" in w for w in warnings)
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


GREEK_CARBERRY = "Ιωσίας Κάρμπερι"


def orcid_warnings(
    profiles: list[dict[str, object]], aliases: list[str] | None = None
) -> list[str]:
    """Warnings for Josiah Carberry, whose ORCID resolves to these profiles."""
    transport = FakeTransport()
    transport.add("/authors", {"filter": f"orcid:{JOSIAH_ORCID}"}, author_page(profiles))
    for p in profiles:
        author_id = str(p["id"]).rsplit("/", 1)[-1]
        transport.add(
            "/works",
            {"filter": f"author.id:{author_id}", "sort": "publication_date:desc"},
            {"results": []},
        )
    add_search(transport, "Josiah Carberry", author_page([]))
    for alias in aliases or []:
        add_search(transport, alias, author_page([]))
    author = AuthorConfig(name="Josiah Carberry", orcid=JOSIAH_ORCID, aliases=aliases or [])
    _, warnings = verify_report(
        Config(mailto="m@example.org", authors=[author]), make_client(transport)
    )
    return warnings


def test_verify_report_cross_script_split_points_to_aliases_not_pinning() -> None:
    """No word crosses scripts, and pinning would drop the other profile's works."""
    warnings = orcid_warnings(
        [profile("A1", "Josiah Carberry", 53, []), profile("A2", GREEK_CARBERRY, 3, [])]
    )
    assert len(warnings) == 1
    assert f"{GREEK_CARBERRY!r} is written in a script the configured names lack" in warnings[0]
    assert "add it to aliases and keep the orcid" in warnings[0]
    assert "different people" not in warnings[0]


def test_verify_report_split_profile_advice_keeps_the_orcid() -> None:
    """With the alias the split is recognised, and pinning is no longer the remedy."""
    warnings = orcid_warnings(
        [profile("A1", "Josiah Carberry", 53, []), profile("A2", GREEK_CARBERRY, 3, [])],
        aliases=[GREEK_CARBERRY],
    )
    assert warnings == [
        "Josiah Carberry: ORCID resolves to 2 author ids (split profile); all are "
        "fetched, so pin openalex_id only if one holds works that are not theirs"
    ]


@pytest.mark.parametrize(
    "stranger",
    [
        "John Smith",
        # A Greek capital kappa inside a Latin name is still Latin.
        "John Κ. Smith",  # noqa: RUF001
    ],
)
def test_verify_report_same_script_stranger_keeps_the_pinning_advice(stranger: str) -> None:
    warnings = orcid_warnings(
        [
            profile("A1", "Josiah Carberry", 8, []),
            profile("A2", GREEK_CARBERRY, 3, []),
            profile("A3", stranger, 300, []),
        ]
    )
    assert len(warnings) == 1
    assert "look like different people" in warnings[0]
    assert "remove the orcid and pin openalex_id" in warnings[0]


def test_verify_report_single_cross_script_profile_suggests_an_alias() -> None:
    warnings = orcid_warnings([profile("A2", GREEK_CARBERRY, 3, [])])
    assert warnings == [
        f"Josiah Carberry: resolves to {GREEK_CARBERRY!r}, which does not look like the "
        "configured name (written in a script the configured names lack: add it to "
        "aliases if it is them)"
    ]


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


def test_verify_report_searches_full_name_aliases_too() -> None:
    """A detached profile under another script or a nickname surfaces
    through its alias (Xenakis, Valsamos on dpsd-new, 2026-11-21); an
    initial alias, a surname alone and a reordered name send no search."""
    transport = FakeTransport()
    add_search(
        transport,
        "Josiah Carberry",
        author_page([profile("A300", "Josiah Carberry", 4, [])]),
    )
    add_search(
        transport,
        GREEK_CARBERRY,
        author_page(
            [profile("A300", "Josiah Carberry", 4, []), profile("A301", GREEK_CARBERRY, 2, [])],
            total=8,
        ),
    )
    add_search(transport, "Joe Carberry", author_page([profile("A302", "Joe Carberry", 6, [])]))
    config = Config(
        mailto="m@example.org",
        authors=[
            AuthorConfig(
                name="Josiah Carberry",
                aliases=[
                    "J. Carberry",
                    "Carberry",
                    "Carberry, Josiah",
                    GREEK_CARBERRY,
                    "Joe Carberry",
                ],
            )
        ],
    )
    report, warnings = verify_report(config, make_client(transport))
    assert "same name, not configured: A300  Josiah Carberry — 4 works" in report
    assert f"alias {GREEK_CARBERRY!r}, not configured: A301  {GREEK_CARBERRY} — 2 works" in report
    assert "alias 'Joe Carberry', not configured: A302  Joe Carberry — 6 works" in report
    assert f"and 6 more {GREEK_CARBERRY!r} match(es)" in report
    assert report.count("A300") == 1  # shown once, under the name that found it first
    searched = [p["search"] for url, p in transport.calls if "search" in p]
    assert searched == ["Josiah Carberry", GREEK_CARBERRY, "Joe Carberry"]
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
    year: int | None = 2024,
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
            Work(id="W10", title="Already Listed By Its Id", authors=[CREDITED]),
            Work(
                id="W11",
                title="Listed Under Its Version Of Record",
                doi="https://doi.org/10.5555/twin",
                authors=[CREDITED],
            ),
            Work(id="W20", title="A Broken Copy Without Its DOI", authors=[CREDITED]),
            Work(
                id="W21",
                title="A Listed Twin With Its Own DOI",
                doi="https://doi.org/10.5555/vor",
                authors=[CREDITED],
            ),
            Work(
                id="W22",
                title="A Version Of Record Listed Bare",
                type="journal",
                authors=[CREDITED],
            ),
        ],
    )
    transport = FakeTransport()
    add_search(transport, "Priya Nair", author_page([]))
    add_byline_search(
        transport,
        PRIYA_BYLINES,
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
        # The aliases repeat the name in another case and order: one search.
        authors=[AuthorConfig(name="Priya Nair", aliases=["priya nair", "Nair, Priya"])],
        output_path=output,
        exclude_types=frozenset({"other"}),
    )

    report, warnings = verify_report(config, make_client(transport))

    assert "not on the published list: 2 work(s); add any that are theirs to manual.yml" in report
    assert "W1  A Paper No Profile Fetch Sees (2024)  10.5555/missing  as 'Nair, Priya'" in report
    # Two releases of one dataset are one line, as a build would keep them.
    assert ("W8  Synthetic" in report) != ("W9  Synthetic" in report)
    assert (
        "better record for a listed work: W4 carries 10.5555/better; listed as W20 without a DOI, "
        "which an `id` override can patch in"
    ) in report
    for dropped in ("W10  ", "W3  ", "W5  ", "W6  ", "W7  ", "W12", "W13"):
        assert dropped not in report
    assert f"Unlinked bylines: compared against {output} (5 works)." in report
    # Both pages walked, and the alias did not search a second time.
    assert [p["cursor"] for p in byline_calls(transport)] == ["*", "page-2"]
    assert warnings == []


def test_unlinked_bylines_follow_the_curation_the_list_was_built_with(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(
        output,
        [
            Work(id="W30", title="Editorial For The Special Issue"),
            Work(id="W32", title="Report Of The Annual Meeting"),
        ],
    )
    overrides = tmp_path / "overrides.yml"
    overrides.write_text(
        "- doi: 10.5555/rejected\n"
        "  exclude: true\n"
        "- id: W5\n"
        "  exclude: false\n"
        # Distinct from its same-title neighbour, on either side of the list.
        "- id: W30\n"
        "  keep_distinct: true\n"
        "- id: W33\n"
        "  keep_distinct: true\n",
        encoding="utf-8",
    )
    transport = FakeTransport()
    add_search(transport, "Priya Nair", author_page([]))
    add_byline_search(
        transport,
        PRIYA_BYLINES,
        [
            [
                raw_work("W4", "A Namesake Paper Rejected Once", doi="10.5555/rejected"),
                raw_work("W5", "Correction Kept On Purpose", work_type="erratum"),
                raw_work("W31", "Editorial For The Special Issue"),
                raw_work("W33", "Report Of The Annual Meeting"),
            ]
        ],
    )
    config = Config(
        mailto="m@example.org",
        authors=[AuthorConfig(name="Priya Nair")],
        output_path=output,
        overrides_path=overrides,
        exclude_types=frozenset({"other"}),
    )

    report, _ = verify_report(config, make_client(transport))

    assert "not on the published list: 3 work(s)" in report
    for listed in ("W5  Correction", "W31  Editorial", "W33  Report"):
        assert listed in report
    assert "W4  " not in report


def test_unlinked_bylines_name_a_listed_work_that_does_not_credit_them(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    colleague = WorkAuthor(name="Ravi Rao", tracked=True, tracked_as="Ravi Rao")
    write_published(
        output,
        [
            # Listed through a colleague, her byline linked to no one.
            Work(
                id="W40",
                title="Fetched Through A Colleague",
                year=2024,
                authors=[WorkAuthor(name="Nair, Priya"), colleague],
            ),
            Work(
                id="W41",
                title="Listed Under Its Other Record",
                year=2024,
                doi="https://doi.org/10.5555/other",
                authors=[colleague],
            ),
            Work(id="W42", title="Credited Where It Is Listed", year=2024, authors=[CREDITED]),
        ],
    )
    transport = FakeTransport()
    add_search(transport, "Priya Nair", author_page([]))
    add_byline_search(
        transport,
        PRIYA_BYLINES,
        [
            [
                raw_work("W40", "Fetched Through A Colleague", bylines=(("Nair, Priya", None),)),
                raw_work("W43", "Listed Under Its Other Record", doi="10.5555/other"),
                raw_work("W42", "Credited Where It Is Listed"),
            ]
        ],
    )
    config = Config(
        mailto="m@example.org", authors=[AuthorConfig(name="Priya Nair")], output_path=output
    )

    report, _ = verify_report(config, make_client(transport))

    assert "listed without crediting them: 2 work(s)" in report
    assert "W40  Fetched Through A Colleague (2024)  as 'Nair, Priya'" in report
    assert "W41  Listed Under Its Other Record (2024)  10.5555/other  as 'Priya Nair'" in report
    assert "W42" not in report
    assert "not on the published list" not in report


def test_unlinked_bylines_leave_the_authors_own_profiles_to_the_fetch(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [])
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": f"orcid:{JOSIAH_ORCID}"},
        author_page([profile("A1", "Josiah Carberry", 8, []), profile("A2", "J. Carberry", 1, [])]),
    )
    for author_id in ("A1", "A2"):
        transport.add(
            "/works",
            {"filter": f"author.id:{author_id}", "sort": "publication_date:desc"},
            {"results": []},
        )
    add_pages(transport, "/works", {"filter": "author.id:A1|A2", "include_xpac": "true"}, [[]])
    add_search(transport, "Josiah Carberry", author_page([]))
    add_byline_search(
        transport,
        'raw_author_name.search:"Josiah Carberry"~2 OR "Carberry Josiah"~2,author.id:!A1|A2',
        [[raw_work("W1", "Unlinked Everywhere But Here", bylines=(("Josiah Carberry", None),))]],
    )
    config = Config(
        mailto="m@example.org",
        authors=[AuthorConfig(name="Josiah Carberry", orcid=JOSIAH_ORCID)],
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
    assert f"XPAC-only works: not checked; no published list at {output} yet" in report
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
        'raw_author_name.search:"Wei Zhang"~2 OR "Zhang Wei"~2',
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


CITESEERX = "http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.1.1"


def located(
    raw: dict[str, object],
    landing: str,
    raw_source: str | None = None,
    source_name: str | None = None,
) -> dict[str, object]:
    """A raw work with a primary location, at a named source if given."""
    raw["primary_location"] = {
        "landing_page_url": landing,
        "raw_source_name": raw_source,
        "source": {"display_name": source_name} if source_name else None,
    }
    return raw


def xpac_config(output: Path, **settings: Any) -> Config:
    """The author `xpac_transport` resolves, with the published list at `output`."""
    return Config(
        mailto="m@example.org",
        authors=[AuthorConfig(name="Josiah Carberry", orcid=JOSIAH_ORCID)],
        output_path=output,
        **settings,
    )


def xpac_transport(
    xpac_pages: list[list[object]] | None, in_default: list[str] | None
) -> FakeTransport:
    """One resolved profile A1, no byline finds, its works with XPAC (no
    pages: that walk fails), and the default listing's answer (None: it fails)."""
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": f"orcid:{JOSIAH_ORCID}"},
        author_page([profile("A1", "Josiah Carberry", 9, [])]),
    )
    transport.add(
        "/works", {"filter": "author.id:A1", "sort": "publication_date:desc"}, {"results": []}
    )
    add_search(transport, "Josiah Carberry", author_page([]))
    add_byline_search(
        transport,
        'raw_author_name.search:"Josiah Carberry"~2 OR "Carberry Josiah"~2,author.id:!A1',
        [[]],
    )
    xpac_walk = {"filter": "author.id:A1", "include_xpac": "true"}
    if xpac_pages is None:
        transport.add("/works", xpac_walk, {}, status=503)
    else:
        add_pages(transport, "/works", xpac_walk, xpac_pages)
    if in_default is None:
        transport.add("/works", {"select": "id"}, {}, status=503)
    else:
        add_pages(
            transport,
            "/works",
            {"select": "id"},
            [[{"id": f"https://openalex.org/{work_id}"} for work_id in in_default]],
        )
    return transport


def listing_calls(transport: FakeTransport) -> list[dict[str, str]]:
    return [p for _, p in transport.calls if p.get("select") == "id"]


def test_xpac_listing_reports_only_what_the_published_list_lacks(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(
        output,
        [
            Work(id="W10", title="Listed From The Default Fetch", year=2020),
            Work(id="W11", title="Listed Version Of Record", doi="https://doi.org/10.5555/vor"),
            Work(
                id="manual-creative-aspects",
                title="Creative Aspects Of Southeast Animation",
                source="manual",
            ),
        ],
    )
    overrides = tmp_path / "overrides.yml"
    overrides.write_text("- id: W7\n  exclude: true\n", encoding="utf-8")
    pages: list[list[object]] = [
        [
            raw_work("W10", "Listed From The Default Fetch", year=2020),
            located(
                raw_work("W1", "A Repository Paper Of His", doi="10.5281/zenodo.1"),
                "https://doi.org/10.5281/zenodo.1",
                "Zenodo",
                source_name="Zenodo",
            ),
            raw_work("W2", "Its Repository Copy", doi="10.5555/vor"),
            # Differs from the manual twin only by a space, which dedup ignores.
            raw_work("W3", "Creative Aspects of South East Animation"),
        ],
        [
            located(
                raw_work("W4", "A Paper Only CiteSeerX Kept", year=None),
                CITESEERX,
                "http://www.example.org/~josiah/papers/kept11.pdf",
            ),
            located(raw_work("W5", "SUMMARY", year=None), CITESEERX, "Unknown"),
            # Added upstream after the list was built: the next build lists it.
            raw_work("W6", "A Default Work Newer Than The List"),
            raw_work("W7", "A Namesake Paper Excluded Once"),
        ],
    ]
    transport = xpac_transport(pages, in_default=["W6"])
    config = xpac_config(output, overrides_path=overrides)

    report, warnings = verify_report(config, make_client(transport))

    assert (
        "XPAC only, not on the published list: 1 work(s), outside the default fetch; "
        "add any that are theirs to manual.yml\n"
        "    W1  A Repository Paper Of His (2024)  Zenodo  https://doi.org/10.5281/zenodo.1\n"
    ) in report
    assert "CiteSeerX copies, XPAC only, not on the published list: 2;" in report
    assert (
        "    W4  A Paper Only CiteSeerX Kept  http://www.example.org/~josiah/papers/kept11.pdf"
        in report
    )
    # No PDF named: the dead landing page is all there is.
    assert f"    W5  SUMMARY  {CITESEERX}" in report
    for dropped in ("W10  ", "W2  ", "W3  ", "W6  ", "W7  "):
        assert dropped not in report
    assert f"XPAC-only works: compared against {output} (3 works)." in report
    # Only the works the list lacks are asked of the default listing.
    (call,) = listing_calls(transport)
    assert set(call["filter"].removeprefix("openalex_id:").split("|")) == {"W1", "W4", "W5", "W6"}
    assert "include_xpac" not in call
    assert warnings == []


def test_xpac_listing_stays_quiet_when_the_list_holds_everything(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [Work(id="W10", title="Listed From The Default Fetch")])
    transport = xpac_transport([[raw_work("W10", "Listed From The Default Fetch")]], in_default=[])

    report, _ = verify_report(xpac_config(output), make_client(transport))

    assert "XPAC only" not in report
    assert "CiteSeerX" not in report
    assert listing_calls(transport) == []


def test_xpac_listing_left_to_the_build_when_the_config_includes_xpac(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [])
    transport = xpac_transport([[raw_work("W1", "Fetched By The Build Already")]], in_default=[])

    report, _ = verify_report(xpac_config(output, include_xpac=True), make_client(transport))

    assert "W1  " not in report
    assert "XPAC-only works: not listed; the config's include_xpac fetches them" in report
    assert not any(
        p.get("filter") == "author.id:A1" and "sort" not in p for _, p in transport.calls
    )


def test_xpac_listing_sees_a_listed_twin_its_copy_absorbed(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [Work(id="W1", title="The Title The List Prints")])
    overrides = tmp_path / "overrides.yml"
    overrides.write_text("- id: W1\n  title: The Title The List Prints\n", encoding="utf-8")
    # The copy wins the merge on its newer id and keeps the upstream title.
    upstream = "An Upstream Title Of A Listed Paper"
    pages: list[list[object]] = [
        [raw_work("W1", upstream), located(raw_work("W8", upstream), CITESEERX)]
    ]
    transport = xpac_transport(pages, in_default=[])

    report, _ = verify_report(xpac_config(output, overrides_path=overrides), make_client(transport))

    assert "W8  " not in report
    assert listing_calls(transport) == []


def test_xpac_listing_holds_a_chain_its_listed_member_started(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [Work(id="W1", title="The Title The List Prints")])
    # W2 takes W1's DOI merge, then W3 takes W2's title merge: one group,
    # whose winner shares no key with the listed W1.
    second = "A Second Copy Under Its Own Title"
    pages: list[list[object]] = [
        [
            raw_work("W1", "An Old Upstream Title", doi="10.5555/a"),
            raw_work("W2", second, doi="10.5555/a"),
            raw_work("W3", second, doi="10.5555/b"),
        ]
    ]
    transport = xpac_transport(pages, in_default=[])

    report, _ = verify_report(xpac_config(output), make_client(transport))

    assert "W3  " not in report
    assert listing_calls(transport) == []


def test_xpac_listing_holds_what_an_overrides_repair_names(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    repaired = "The Title The Override Set"
    write_published(output, [Work(id="W1", title=repaired, doi="https://doi.org/10.5555/repaired")])
    overrides = tmp_path / "overrides.yml"
    overrides.write_text(
        f"- id: W1\n  doi: 10.5555/repaired\n  title: {repaired}\n", encoding="utf-8"
    )
    # W1 arrives broken; the XPAC records carrying the DOI or the title its
    # override set are the listed paper, though no merge reaches W1.
    pages: list[list[object]] = [
        [
            raw_work("W1", "A Broken Copy Of The Paper"),
            raw_work("W6", "Some Other Rendering Of It", doi="10.5555/repaired"),
            raw_work("W7", repaired),
            raw_work("W8", "A Paper The List Lacks"),
        ]
    ]
    transport = xpac_transport(pages, in_default=[])

    report, _ = verify_report(xpac_config(output, overrides_path=overrides), make_client(transport))

    assert "    W8  A Paper The List Lacks (2024)\n" in report
    for held in ("W1  ", "W6  ", "W7  "):
        assert held not in report


def test_xpac_listing_drops_a_group_the_default_fetch_supplies(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [])
    # The XPAC copy wins on its newer id, but its default twin, newer than
    # the list, arrives with the next build anyway.
    title = "A Paper Indexed Twice Upstream"
    transport = xpac_transport([[raw_work("W1", title), raw_work("W2", title)]], in_default=["W1"])

    report, _ = verify_report(xpac_config(output), make_client(transport))

    assert "W2  " not in report
    (call,) = listing_calls(transport)
    assert set(call["filter"].removeprefix("openalex_id:").split("|")) == {"W1", "W2"}


def test_xpac_listing_survives_a_doi_patch_on_a_distinct_record(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    title = "A Title Two Records Carry"
    write_published(output, [Work(id="W1", title=title, doi="https://doi.org/10.5555/d2")])
    overrides = tmp_path / "overrides.yml"
    # keep_distinct names the upstream DOI, which the id override then patches.
    overrides.write_text(
        "- doi: 10.5555/d\n  keep_distinct: true\n- id: W1\n  doi: 10.5555/d2\n",
        encoding="utf-8",
    )
    pages: list[list[object]] = [[raw_work("W1", title, doi="10.5555/d"), raw_work("W5", title)]]
    transport = xpac_transport(pages, in_default=[])

    report, _ = verify_report(xpac_config(output, overrides_path=overrides), make_client(transport))

    assert f"    W5  {title} (2024)\n" in report


def test_xpac_listing_shows_each_pdf_a_page_text_title_merged(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [])
    pdf = "http://www.example.org/~josiah/papers/{}.pdf"
    real = "A Repository Paper With Its CiteSeerX Copy"
    pages: list[list[object]] = [
        [
            located(raw_work("W1", "signatures for", year=None), CITESEERX, pdf.format("one")),
            located(raw_work("W2", "signatures for", year=None), CITESEERX, pdf.format("two")),
            # The same PDF indexed twice is one line.
            located(raw_work("W3", "signatures for", year=None), CITESEERX, pdf.format("two")),
            # A real record wins its group: its CiteSeerX copy is that paper.
            raw_work("W4", real, doi="10.5555/real"),
            located(raw_work("W5", real, year=None), CITESEERX, pdf.format("four")),
            # A CiteSeerX copy's newer id outranks an older DOI-less record:
            # both keep a line, the record among the dated works.
            located(raw_work("W6", "A Deposit Kept Without A DOI", year=2010), REPOSITORY),
            located(
                raw_work("W9", "A Deposit Kept Without A DOI", year=None),
                CITESEERX,
                pdf.format("nine"),
            ),
        ]
    ]
    transport = xpac_transport(pages, in_default=[])

    report, _ = verify_report(xpac_config(output), make_client(transport))

    assert "CiteSeerX copies, XPAC only, not on the published list: 3;" in report
    assert "rather than the paper; add any that are theirs to manual.yml\n" in report
    assert f"    W1  signatures for  {pdf.format('one')}\n" in report
    assert f"    W3  signatures for  {pdf.format('two')}\n" in report
    assert f"    W9  A Deposit Kept Without A DOI  {pdf.format('nine')}\n" in report
    assert "XPAC only, not on the published list: 2 work(s)" in report
    assert f"    W4  {real} (2024)  https://doi.org/10.5555/real\n" in report
    assert f"    W6  A Deposit Kept Without A DOI (2010)  {REPOSITORY}\n" in report
    for hidden in ("W2  ", "W5  "):
        assert hidden not in report


def test_xpac_listing_lists_nothing_when_the_default_listing_fails(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [])
    # Read as empty, a failed membership call would pass default works off
    # as XPAC-only.
    transport = xpac_transport([[raw_work("W1", "A Work Of Unknown Standing")]], None)

    report, warnings = verify_report(xpac_config(output), make_client(transport))

    assert "  XPAC-only works not checked: " in report
    assert "W1  " not in report
    assert warnings == []


def test_xpac_listing_keeps_out_an_excluded_type(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [])
    pages: list[list[object]] = [
        [
            raw_work("W1", "Erratum To A Paper Of His", work_type="erratum"),
            raw_work("W2", "A Paper Of His Kept Only In XPAC"),
        ]
    ]
    transport = xpac_transport(pages, in_default=[])
    # Normalized, OpenAlex's erratum is erga's "other".
    config = xpac_config(output, exclude_types=frozenset({"other"}))

    report, _ = verify_report(config, make_client(transport))

    assert "W1  " not in report
    assert "    W2  A Paper Of His Kept Only In XPAC (2024)\n" in report


def test_xpac_listing_is_uncapped_newest_first(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [])
    # Twelve leads, over the byline lists' cap of ten, ids against year order.
    years = range(2001, 2013)
    pages: list[list[object]] = [
        [raw_work(f"W{year}", f"An XPAC Paper From The Year {year}", year=year) for year in years]
    ]
    transport = xpac_transport(pages, in_default=[])

    report, _ = verify_report(xpac_config(output), make_client(transport))

    assert "XPAC only, not on the published list: 12 work(s)" in report
    assert "    … and " not in report
    printed = [line.split()[0] for line in report.splitlines() if line.startswith("    W")]
    assert printed == [f"W{year}" for year in reversed(years)]


def test_xpac_listing_failure_leaves_the_rest_of_the_report(tmp_path: Path) -> None:
    output = tmp_path / "publications.json"
    write_published(output, [])
    transport = xpac_transport(None, in_default=[])

    report, warnings = verify_report(xpac_config(output), make_client(transport))

    assert "A1  Josiah Carberry — 9 works" in report
    assert "  XPAC-only works not checked: " in report
    assert "HTTP 503" in report
    assert warnings == []


PDF = "http://www.example.org/kept11.pdf"
REPOSITORY = "https://repository.example.org/record/4"
LOOKALIKE_HOST = "https://citeseerx.ist.psu.edu.example.org/x"
LOOKALIKE_PATH = "https://example.org/citeseerx.ist.psu.edu/x"


@pytest.mark.parametrize(
    ("doi", "landing", "raw_source", "expected"),
    [
        (None, CITESEERX, PDF, (PDF, True)),
        # A PDF on an FTP server is still the PDF.
        (None, CITESEERX, "ftp://ftp.example.org/x.pdf", ("ftp://ftp.example.org/x.pdf", True)),
        # A scheme with no host is a depositor's note, not a PDF.
        (None, CITESEERX, "https:Paper collection", (CITESEERX, True)),
        (None, CITESEERX, "http://[broken", (CITESEERX, True)),
        # A landing page too malformed to parse is no CiteSeerX copy, and no crash.
        (None, "http://[broken", PDF, ("http://[broken", False)),
        # CiteSeerX is its host, not a host or path that contains the name.
        (None, LOOKALIKE_HOST, PDF, (LOOKALIKE_HOST, False)),
        (None, LOOKALIKE_PATH, PDF, (LOOKALIKE_PATH, False)),
        # An ordinary record: its DOI before its landing page, else the page.
        ("https://doi.org/10.5555/x", REPOSITORY, None, ("https://doi.org/10.5555/x", False)),
        (None, REPOSITORY, None, (REPOSITORY, False)),
    ],
)
def test_xpac_link_takes_only_a_real_url(
    doi: str | None, landing: str, raw_source: str | None, expected: tuple[str, bool]
) -> None:
    raw = located(raw_work("W4", "A Paper Kept In XPAC"), landing, raw_source)
    assert _xpac_link(Work(id="W4", title="A Paper Kept In XPAC", doi=doi), raw) == expected
