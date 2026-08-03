"""Reading and writing the canonical output file.

Serialization is deterministic: unchanged inputs produce a byte-identical
file, so "did anything change" is exactly `git diff`.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from erga.model import Work, doi_key

SCHEMA_VERSION = 1

_NO_YEAR = -(10**9)  # records without a year sort last


def sort_works(works: list[Work]) -> list[Work]:
    """Year descending, then id ascending."""
    return sorted(works, key=lambda w: (-(w.year if w.year is not None else _NO_YEAR), w.id))


def render(works: list[Work]) -> str:
    document = {
        "schema_version": SCHEMA_VERSION,
        "works": [w.to_json() for w in sort_works(works)],
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def previous_venues(path: Path) -> dict[str, str]:
    """Venue by DOI-key and by id from the previous output, for the
    last-known-good backfill ratchet.

    The reader-side inverse of render/Work.to_json, kept next to them so a
    schema change touches one module. Deliberately tolerant: the previous
    file may be absent, malformed, or from an older schema, and the ratchet
    must degrade to "no known venues" rather than abort.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    venues: dict[str, str] = {}
    works = data.get("works", []) if isinstance(data, dict) else []
    for record in works:
        if not isinstance(record, dict) or not record.get("venue"):
            continue
        if record.get("doi"):
            venues[doi_key(str(record["doi"]))] = record["venue"]
        if record.get("id"):
            venues[str(record["id"])] = record["venue"]
    return venues


def write_atomic(path: Path, content: str) -> None:
    """Write via a sibling temp file + rename so a failed run never leaves a
    truncated publications.json behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(temp_name, path)
    except BaseException:
        os.unlink(temp_name)
        raise
