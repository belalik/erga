from __future__ import annotations

import pytest

from conftest import FakeTransport, no_sleep
from erga.crossref import CrossrefClient
from erga.errors import FetchError
from erga.http import Response


def client_with(transport: FakeTransport) -> CrossrefClient:
    return CrossrefClient(transport, mailto="m@example.org", delay=0.0, sleep=no_sleep)


def test_venue_found() -> None:
    transport = FakeTransport()
    transport.add(
        "/works/10.5555%2Fcracked",
        {},
        {"message": {"container-title": ["Annals of Improbable Ceramics"]}},
    )
    assert (
        client_with(transport).venue_for_doi("10.5555/cracked") == "Annals of Improbable Ceramics"
    )


def test_datacite_404_skipped_silently() -> None:
    transport = FakeTransport()
    transport.add("/works/", {}, {"status": "error"}, status=404)
    assert client_with(transport).venue_for_doi("10.5281/zenodo.1234") is None


def test_empty_container_title_gives_none() -> None:
    transport = FakeTransport()
    transport.add("/works/", {}, {"message": {"container-title": []}})
    assert client_with(transport).venue_for_doi("10.5555/no-venue") is None


def test_persistent_failure_raises_fetch_error() -> None:
    def transport(url: str, params: dict[str, str]) -> Response:
        return Response(503, None)

    client = CrossrefClient(transport, mailto="m@example.org", delay=0.0, sleep=no_sleep)
    with pytest.raises(FetchError):
        client.venue_for_doi("10.5555/down")
