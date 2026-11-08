from __future__ import annotations

from typing import Any

import pytest

from conftest import FakeTransport, no_sleep
from erga.crossref import Container, CrossrefClient
from erga.errors import FetchError
from erga.http import Response


def client_with(transport: FakeTransport) -> CrossrefClient:
    return CrossrefClient(transport, mailto="m@example.org", delay=0.0, sleep=no_sleep)


def container_of(message: dict[str, Any]) -> Container | None:
    transport = FakeTransport()
    transport.add("/works/", {}, {"message": message})
    return client_with(transport).container_for_doi("10.5555/any")


def test_container_found() -> None:
    transport = FakeTransport()
    transport.add(
        "/works/10.5555%2Fcracked",
        {},
        {"message": {"container-title": ["Annals of Improbable Ceramics"]}},
    )
    assert client_with(transport).container_for_doi("10.5555/cracked") == Container(
        "Annals of Improbable Ceramics"
    )


def test_a_chapter_in_a_series_names_the_book_second() -> None:
    # 10.4018/978-1-7998-2871-6.ch006 (checked 2026-09-30 and 2026-11-07).
    message = {
        "type": "book-chapter",
        "container-title": [
            "Advances in Religious and Cultural Studies",
            "Applying Innovative Technologies in Heritage Science",
        ],
    }
    assert container_of(message) == Container(
        "Applying Innovative Technologies in Heritage Science", in_series=True
    )
    # A chapter with the book alone is a plain container.
    assert container_of({"type": "book-chapter", "container-title": ["A Book"]}) == Container(
        "A Book"
    )


def test_container_titles_are_stripped() -> None:
    padded = {"type": "book-chapter", "container-title": [" Series ", "  A Book "]}
    assert container_of(padded) == Container("A Book", in_series=True)
    assert container_of({"container-title": ["  A Journal "]}) == Container("A Journal")


def test_two_titles_read_as_a_series_on_chapters_only() -> None:
    # Positions decide, so the rule stays on the one record type measured;
    # anything else keeps the first title, as before 0.9.5.
    for message, first in (
        (
            {"type": "journal-article", "container-title": ["Journal A", "Journal A Online"]},
            "Journal A",
        ),
        ({"container-title": ["Journal A", "Journal A Online"]}, "Journal A"),
        ({"type": "book-chapter", "container-title": ["Series", "Book", "Third"]}, "Series"),
        ({"type": "book-chapter", "container-title": ["Series", " "]}, "Series"),
        # Two usable titles out of three entries is not the measured shape.
        ({"type": "book-chapter", "container-title": ["Series", 5, "Book"]}, "Series"),
    ):
        assert container_of(message) == Container(first), message


def test_datacite_404_skipped_silently() -> None:
    transport = FakeTransport()
    transport.add("/works/", {}, {"status": "error"}, status=404)
    assert client_with(transport).container_for_doi("10.5281/zenodo.1234") is None


def test_empty_container_title_gives_none() -> None:
    assert container_of({"container-title": []}) is None
    assert container_of({"container-title": ["  ", 5]}) is None


def test_persistent_failure_raises_fetch_error() -> None:
    def transport(url: str, params: dict[str, str]) -> Response:
        return Response(503, None)

    client = CrossrefClient(transport, mailto="m@example.org", delay=0.0, sleep=no_sleep)
    with pytest.raises(FetchError):
        client.container_for_doi("10.5555/down")
