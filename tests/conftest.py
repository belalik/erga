"""Shared test helpers: fixture loading and the fake transport.

The fetch layer takes an injectable transport, so recorded responses need no
HTTP mocking library (requirements section 10).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from erga.http import Response

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(*parts: str) -> Any:
    return json.loads(FIXTURES.joinpath(*parts).read_text(encoding="utf-8"))


def no_sleep(_seconds: float) -> None:
    return None


class FakeTransport:
    """Routes requests to canned responses; unexpected requests fail the test."""

    def __init__(self) -> None:
        self.routes: list[tuple[str, dict[str, str], Response]] = []
        self.calls: list[tuple[str, dict[str, str]]] = []

    def add(
        self, url_part: str, params_subset: dict[str, str], data: Any, status: int = 200
    ) -> None:
        self.routes.append((url_part, params_subset, Response(status, data)))

    def __call__(self, url: str, params: dict[str, str]) -> Response:
        self.calls.append((url, dict(params)))
        for url_part, subset, response in self.routes:
            if url_part in url and all(params.get(k) == v for k, v in subset.items()):
                return response
        raise AssertionError(f"unexpected request: {url} {params}")
