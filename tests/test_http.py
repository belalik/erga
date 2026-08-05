"""UrlTransport secret redaction.

requests embeds the full request URL (query string included) in its network
exceptions, so an api_key sent as a query parameter leaks into stderr and CI
logs unless the transport scrubs it.
"""

from __future__ import annotations

from typing import Any

import pytest
import requests

from erga.http import TransportError, UrlTransport

KEY = "sk-live-1234"


def failing_transport(message: str) -> UrlTransport:
    transport = UrlTransport("erga-test", secrets=[KEY])

    def explode(*args: Any, **kwargs: Any) -> Any:
        raise requests.ConnectionError(message)

    transport._session.get = explode  # type: ignore[method-assign]
    return transport


def test_secret_redacted_from_network_error() -> None:
    transport = failing_transport(
        f"HTTPSConnectionPool(host='api.openalex.org'): Max retries exceeded "
        f"with url: /works?filter=x&api_key={KEY}"
    )
    with pytest.raises(TransportError) as excinfo:
        transport("https://api.openalex.org/works", {})
    assert KEY not in str(excinfo.value)
    assert "api_key=***" in str(excinfo.value)


def test_original_exception_not_chained() -> None:
    transport = failing_transport(f"boom api_key={KEY}")
    with pytest.raises(TransportError) as excinfo:
        transport("https://api.openalex.org/works", {})
    # Chaining would put the unredacted message back into the traceback.
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__


def test_no_secrets_still_raises_transport_error() -> None:
    transport = UrlTransport("erga-test")

    def explode(*args: Any, **kwargs: Any) -> Any:
        raise requests.Timeout("timed out")

    transport._session.get = explode  # type: ignore[method-assign]
    with pytest.raises(TransportError, match="timed out"):
        transport("https://api.openalex.org/works", {})
