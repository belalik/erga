"""Canonical work record and identifier helpers."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from erga.errors import ConfigError

WORK_TYPES = frozenset(
    {
        "journal",
        "conference",
        "book",
        "book-chapter",
        "thesis",
        "preprint",
        "dataset",
        "software",
        "other",
    }
)


def validate_work_type(value: Any, where: str) -> str:
    """The value as a validated work type; anything else is a ConfigError."""
    if not isinstance(value, str) or value not in WORK_TYPES:
        allowed = ", ".join(sorted(WORK_TYPES))
        raise ConfigError(f"{where}: type {value!r} is not one of: {allowed}")
    return value


_DOI_HOST = re.compile(r"^https?://(dx\.)?doi\.org/", re.IGNORECASE)
_ORCID_HOST = re.compile(r"^https?://orcid\.org/", re.IGNORECASE)


def normalize_orcid(value: str) -> str:
    """Bare ORCID iD from bare or URL form, uppercased checksum digit."""
    return _ORCID_HOST.sub("", value.strip()).upper()


def doi_key(value: str) -> str:
    """Comparison key for a DOI: bare form, lowercase."""
    return _DOI_HOST.sub("", value.strip()).lower()


def doi_url(value: str) -> str:
    """Full https://doi.org/ URL for a DOI given in bare or URL form."""
    return "https://doi.org/" + doi_key(value)


def slugify(text: str) -> str:
    """ASCII slug for manual-entry ids."""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:60].rstrip("-") or "untitled"


@dataclass
class WorkAuthor:
    name: str
    orcid: str | None = None
    tracked: bool = False
    # Canonical configured-author name this authorship matched (None when
    # untracked). erga holds the alias table and does the matching; without
    # this, every consumer re-implements alias logic to build per-author
    # filters against display-name variants.
    tracked_as: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "orcid": self.orcid,
            "tracked": self.tracked,
            "tracked_as": self.tracked_as,
        }


@dataclass
class Work:
    id: str
    title: str
    authors: list[WorkAuthor] = field(default_factory=list)
    year: int | None = None
    date: str | None = None
    venue: str | None = None
    type: str = "other"
    doi: str | None = None
    cited_by_count: int = 0
    abstract: str | None = None
    open_access_url: str | None = None
    tags: list[str] = field(default_factory=list)
    is_retracted: bool = False
    source: str = "openalex"
    # Internal only, set from overrides; never serialized.
    keep_distinct: bool = False
    # Internal only: exempts the record from the exclude_types filter. Set
    # at construction for manual entries and by an explicit `exclude: false`
    # override for fetched records.
    keep: bool = False

    @property
    def doi_key(self) -> str | None:
        return doi_key(self.doi) if self.doi else None

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "authors": [a.to_json() for a in self.authors],
            "year": self.year,
            "date": self.date,
            "venue": self.venue,
            "type": self.type,
            "doi": self.doi,
            "cited_by_count": self.cited_by_count,
            "abstract": self.abstract,
            "open_access": {"url": self.open_access_url} if self.open_access_url else None,
            "tags": self.tags,
            "is_retracted": self.is_retracted,
            "source": self.source,
        }
