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


def test_verify_report_split_orcid_and_zero_works() -> None:
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": "orcid:0000-0002-1825-0097"},
        {
            "results": [
                profile("A1", "Josiah Carberry", 8, ["J. S. Carberry"]),
                profile("A2", "J. Carberry", 1, []),
            ]
        },
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

    config = Config(
        mailto="m@example.org",
        authors=[
            AuthorConfig(name="Josiah Carberry", orcid="0000-0002-1825-0097"),
            AuthorConfig(name="Silent Sam", openalex_id="A5000000009"),
        ],
    )
    client = OpenAlexClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep)
    report, warnings = verify_report(config, client)

    assert "A1  Josiah Carberry — 8 works" in report
    assert "also known as: J. S. Carberry" in report
    assert "recent: Toward a Unified Theory (2024)" in report
    assert "Silent Sam" in report
    assert any("2 author ids" in w for w in warnings)
    assert any("zero works" in w for w in warnings)


def test_verify_report_unresolved_orcid_warns_without_aborting() -> None:
    transport = FakeTransport()
    transport.add("/authors", {"filter": "orcid:0000-0002-1825-0097"}, {"results": []})
    config = Config(
        mailto="m@example.org",
        authors=[AuthorConfig(name="Nobody Yet", orcid="0000-0002-1825-0097")],
    )
    client = OpenAlexClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep)
    report, warnings = verify_report(config, client)
    assert "resolved to no OpenAlex author" in report
    assert any("no OpenAlex author id" in w for w in warnings)
