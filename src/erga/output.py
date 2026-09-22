"""Reading and writing the canonical output file.

Serialization is deterministic: unchanged inputs produce a byte-identical
file, so "did anything change" is exactly `git diff`.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from erga.model import Work, doi_key

SCHEMA_VERSION = 1

_NO_YEAR = -(10**9)  # records without a year sort last


def sort_works(works: list[Work]) -> list[Work]:
    """Year descending, then id ascending."""
    return sorted(works, key=lambda w: (-(w.year if w.year is not None else _NO_YEAR), w.id))


def document(works: list[Work]) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "works": [w.to_json() for w in sort_works(works)]}


def dump(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def read_output(path: Path) -> list[dict[str, Any]] | None:
    """Records of an existing output file, or None when there is none to read.

    The reader-side inverse of document/Work.to_json, kept next to them so a
    schema change touches one module. Deliberately tolerant: the file may be
    absent, malformed, or from an older schema, and its readers (the venue
    ratchet, the build delta) must degrade to "nothing known" rather than
    abort.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("works"), list):
        return None
    records: list[Any] = data["works"]
    # Only the shapes the readers touch are checked: a work that is not a
    # mapping, or a byline that is not a list of mappings, is not a file erga
    # wrote, and dropping the odd entry would let a hand-edited or truncated
    # file pass as a real, smaller output.
    if not all(isinstance(record, dict) for record in records):
        return None
    for record in records:
        authors = record.get("authors")
        if authors is not None and not (
            isinstance(authors, list) and all(isinstance(a, dict) for a in authors)
        ):
            return None
    return records


def previous_venues(records: list[dict[str, Any]] | None) -> dict[str, str]:
    """Venue by DOI-key and by id from the previous output's records, for
    the last-known-good backfill ratchet."""
    venues: dict[str, str] = {}
    for record in records or []:
        if not record.get("venue"):
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
