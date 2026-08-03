from __future__ import annotations

import pytest

from conftest import FakeTransport, no_sleep
from erga.config import AuthorConfig
from erga.errors import FetchError
from erga.http import Response, request_with_retry
from erga.openalex import OpenAlexClient, strip_openalex_host


def profile(author_id: str, name: str = "Someone", works: int = 10) -> dict[str, object]:
    return {
        "id": f"https://openalex.org/{author_id}",
        "display_name": name,
        "display_name_alternatives": [],
        "works_count": works,
    }


def client_with(transport: FakeTransport) -> OpenAlexClient:
    return OpenAlexClient(transport, mailto="m@example.org", delay=0.0, sleep=no_sleep)


def test_strip_openalex_host() -> None:
    assert strip_openalex_host("https://openalex.org/W123") == "W123"
    assert strip_openalex_host("W123") == "W123"


def test_resolve_author_orcid_may_split() -> None:
    transport = FakeTransport()
    transport.add(
        "/authors",
        {"filter": "orcid:0000-0002-1825-0097"},
        {"results": [profile("A1"), profile("A2")]},
    )
    resolved = client_with(transport).resolve_author(
        AuthorConfig(name="X", orcid="0000-0002-1825-0097")
    )
    assert resolved.ids == ["A1", "A2"]


def test_resolve_author_pinned_id_adds_profile() -> None:
    transport = FakeTransport()
    transport.add("/authors", {"filter": "orcid:0000-0002-1825-0097"}, {"results": [profile("A1")]})
    transport.add("/authors/A9", {}, profile("A9"))
    resolved = client_with(transport).resolve_author(
        AuthorConfig(name="X", orcid="0000-0002-1825-0097", openalex_id="A9")
    )
    assert resolved.ids == ["A1", "A9"]


def test_resolve_author_missing_pinned_id_aborts() -> None:
    transport = FakeTransport()
    transport.add("/authors/A404", {}, None, status=404)
    with pytest.raises(FetchError, match="A404"):
        client_with(transport).resolve_author(AuthorConfig(name="X", openalex_id="A404"))


def test_fetch_works_paginates_and_dedups() -> None:
    transport = FakeTransport()
    transport.add(
        "/works",
        {"cursor": "*"},
        {
            "results": [{"id": "https://openalex.org/W1"}, {"id": "https://openalex.org/W2"}],
            "meta": {"next_cursor": "page-two"},
        },
    )
    transport.add(
        "/works",
        {"cursor": "page-two"},
        {
            "results": [{"id": "https://openalex.org/W2"}, {"id": "https://openalex.org/W3"}],
            "meta": {"next_cursor": None},
        },
    )
    works = client_with(transport).fetch_works(["A1"])
    assert sorted(w["id"] for w in works) == [
        "https://openalex.org/W1",
        "https://openalex.org/W2",
        "https://openalex.org/W3",
    ]


def test_fetch_works_batches_authors_with_or_pipe() -> None:
    transport = FakeTransport()
    ids = [f"A{i}" for i in range(150)]
    transport.add(
        "/works",
        {"filter": "author.id:" + "|".join(ids[:100])},
        {"results": [], "meta": {"next_cursor": None}},
    )
    transport.add(
        "/works",
        {"filter": "author.id:" + "|".join(ids[100:])},
        {"results": [], "meta": {"next_cursor": None}},
    )
    assert client_with(transport).fetch_works(ids) == []
    assert len(transport.calls) == 2


def test_fetch_works_passes_xpac_and_credentials() -> None:
    transport = FakeTransport()
    transport.add("/works", {}, {"results": [], "meta": {"next_cursor": None}})
    client = OpenAlexClient(
        transport, mailto="m@example.org", api_key="secret", delay=0.0, sleep=no_sleep
    )
    client.fetch_works(["A1"], include_xpac=True)
    _, params = transport.calls[0]
    assert params["include_xpac"] == "true"
    assert params["api_key"] == "secret"
    assert params["mailto"] == "m@example.org"


def test_politeness_delay_between_requests() -> None:
    sleeps: list[float] = []
    transport = FakeTransport()
    transport.add("/works", {}, {"results": [], "meta": {"next_cursor": None}})
    client = OpenAlexClient(transport, mailto="m@example.org", delay=0.25, sleep=sleeps.append)
    client.fetch_works(["A1"])
    client.fetch_works(["A1"])
    assert sleeps == [0.25]  # between the two calls, not before the first


def test_request_with_retry_backs_off_then_succeeds() -> None:
    sleeps: list[float] = []
    responses = [Response(429, None), Response(503, None), Response(200, {"ok": True})]

    def transport(url: str, params: dict[str, str]) -> Response:
        return responses.pop(0)

    response = request_with_retry(transport, "https://x", {}, sleep=sleeps.append)
    assert response.data == {"ok": True}
    assert sleeps == [1.0, 2.0]


def test_request_with_retry_gives_up() -> None:
    def transport(url: str, params: dict[str, str]) -> Response:
        return Response(500, None)

    with pytest.raises(FetchError, match="HTTP 500"):
        request_with_retry(transport, "https://x", {}, sleep=no_sleep)
