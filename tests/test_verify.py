from __future__ import annotations

from conftest import FakeTransport, no_sleep
from erga.config import AuthorConfig, Config
from erga.openalex import OpenAlexClient
from erga.verify import verify_report


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
            ],
            total=69,
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
    assert "69 author profiles" in contaminated[0]
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
