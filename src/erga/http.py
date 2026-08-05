"""HTTP transport abstraction.

The pipeline talks to APIs through a Transport callable so tests can inject
recorded responses without an HTTP mocking library. Retry/backoff lives above
the transport, in request_with_retry, so it is exercised by the same fakes.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import requests

from erga.errors import FetchError

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


@dataclass
class Response:
    status_code: int
    data: Any  # parsed JSON body, or None if the body was not JSON


class TransportError(Exception):
    """Network-level failure (connection refused, timeout); retryable."""


Transport = Callable[[str, dict[str, str]], Response]


class Pacer:
    """Politeness delay between successive requests, none before the first."""

    def __init__(self, delay: float, sleep: Callable[[float], None]) -> None:
        self._delay = delay
        self._sleep = sleep
        self._requested = False

    def wait(self) -> None:
        if self._requested:
            self._sleep(self._delay)
        self._requested = True


class UrlTransport:
    """requests-backed transport with a fixed User-Agent.

    secrets are redacted from network-error messages: requests embeds the
    full request URL — query string and thus api_key included — in
    ConnectionError/Timeout text, which would otherwise surface in stderr
    and CI logs whenever a failure propagates.
    """

    def __init__(self, user_agent: str, timeout: float = 30.0, secrets: Sequence[str] = ()) -> None:
        self._session = requests.Session()
        self._session.headers["User-Agent"] = user_agent
        self._timeout = timeout
        self._secrets = [s for s in secrets if s]

    def __call__(self, url: str, params: dict[str, str]) -> Response:
        try:
            resp = self._session.get(url, params=params, timeout=self._timeout)
        except requests.RequestException as exc:
            message = str(exc)
            for secret in self._secrets:
                message = message.replace(secret, "***")
            # from None: chaining would put the unredacted original back
            # into the printed traceback.
            raise TransportError(message) from None
        try:
            data = resp.json()
        except ValueError:
            data = None
        return Response(resp.status_code, data)


def request_with_retry(
    transport: Transport,
    url: str,
    params: dict[str, str],
    *,
    sleep: Callable[[float], None],
    attempts: int = 4,
    backoff: float = 1.0,
) -> Response:
    """GET with exponential backoff on 429/5xx and network errors.

    Returns the final response, which may still be an error status the caller
    treats specially (e.g. Crossref 404). Raises FetchError when retryable
    failures persist through all attempts.
    """
    last: str = ""
    for attempt in range(attempts):
        if attempt:
            sleep(backoff * 2 ** (attempt - 1))
        try:
            response = transport(url, params)
        except TransportError as exc:
            last = str(exc)
            continue
        if response.status_code in RETRY_STATUSES:
            last = f"HTTP {response.status_code}"
            continue
        return response
    raise FetchError(f"{url}: {last} after {attempts} attempts")
