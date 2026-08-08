"""Curation files: manual entries, overrides, tags.

All three survive every refresh; a missing file means "none". Typos fail
loudly: curation is the maintainer's reviewable artifact, and a silently
skipped patch is worse than an aborted run.
"""

from __future__ import annotations

import copy
import datetime
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from erga.config import AuthorConfig, expect_str_list, load_yaml, reject_unknown_keys
from erga.errors import ConfigError
from erga.model import WORK_TYPES, Work, WorkAuthor, doi_key, doi_url, slugify

MANUAL_KEYS = {"title", "authors", "venue", "year", "date", "doi", "type", "tags", "abstract"}
PATCH_KEYS = {
    "title",
    "authors",
    "venue",
    "year",
    "date",
    "doi",
    "type",
    "cited_by_count",
    "abstract",
    "open_access",
    "tags",
    "is_retracted",
}


def _parse_authors(value: Any, authors_cfg: list[AuthorConfig], where: str) -> list[WorkAuthor]:
    """Author strings matched to configured authors by name/alias."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise ConfigError(f"{where}: 'authors' must be a string or a list of strings")
    parsed = []
    for name in value:
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(f"{where}: 'authors' entries must be non-empty strings")
        name = name.strip()
        matched = next((a for a in authors_cfg if name.casefold() in a.match_names()), None)
        parsed.append(
            WorkAuthor(
                name=name,
                orcid=f"https://orcid.org/{matched.orcid}" if matched and matched.orcid else None,
                tracked=matched is not None,
                tracked_as=matched.name if matched else None,
            )
        )
    return parsed


def _parse_type(value: Any, where: str) -> str:
    if not isinstance(value, str) or value not in WORK_TYPES:
        allowed = ", ".join(sorted(WORK_TYPES))
        raise ConfigError(f"{where}: type {value!r} is not one of: {allowed}")
    return value


def _opt_str(entry: dict[str, Any], key: str) -> str | None:
    value = entry.get(key)
    return str(value) if value is not None else None


def load_manual(path: Path, authors_cfg: list[AuthorConfig]) -> list[Work]:
    """Manual records the APIs miss; absent file means none."""
    if not path.exists():
        return []
    entries = load_yaml(path, list)
    works = []
    used_ids: set[str] = set()
    for index, entry in enumerate(entries):
        where = f"{path}: entry {index + 1}"
        if not isinstance(entry, dict):
            raise ConfigError(f"{where}: expected a mapping")
        reject_unknown_keys(entry, MANUAL_KEYS, where)
        title = entry.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ConfigError(f"{where}: 'title' is required")
        title = title.strip()

        base_id = "manual-" + slugify(title)
        work_id, suffix = base_id, 2
        while work_id in used_ids:
            work_id, suffix = f"{base_id}-{suffix}", suffix + 1
        used_ids.add(work_id)

        year = entry.get("year")
        if year is not None and not isinstance(year, int):
            raise ConfigError(f"{where}: 'year' must be an integer")

        works.append(
            Work(
                id=work_id,
                title=title,
                authors=_parse_authors(entry.get("authors", []), authors_cfg, where),
                year=year,
                date=_opt_str(entry, "date"),
                venue=_opt_str(entry, "venue"),
                type=_parse_type(entry.get("type", "other"), where),
                doi=doi_url(str(entry["doi"])) if entry.get("doi") else None,
                abstract=_opt_str(entry, "abstract"),
                tags=expect_str_list(entry.get("tags", []), f"{where}: 'tags'"),
                source="manual",
            )
        )
    return works


@dataclass
class Override:
    where: str
    match_doi: str | None = None  # doi_key form
    match_id: str | None = None
    exclude: bool = False
    keep_distinct: bool = False
    patch: dict[str, Any] = field(default_factory=dict)
    matched: bool = False
    changed: bool = False


def load_overrides(path: Path) -> list[Override]:
    if not path.exists():
        return []
    entries = load_yaml(path, list)
    overrides = []
    for index, entry in enumerate(entries):
        where = f"{path}: entry {index + 1}"
        if not isinstance(entry, dict):
            raise ConfigError(f"{where}: expected a mapping")
        if ("doi" in entry) == ("id" in entry):
            raise ConfigError(f"{where}: needs exactly one of 'doi' or 'id' to match on")
        patch = {
            k: v for k, v in entry.items() if k not in {"doi", "id", "exclude", "keep_distinct"}
        }
        reject_unknown_keys(patch, PATCH_KEYS, where, noun="fields")
        overrides.append(
            Override(
                where=where,
                match_doi=doi_key(str(entry["doi"])) if "doi" in entry else None,
                match_id=str(entry["id"]) if "id" in entry else None,
                exclude=bool(entry.get("exclude", False)),
                keep_distinct=bool(entry.get("keep_distinct", False)),
                patch=patch,
            )
        )
    return overrides


def load_tags(path: Path) -> dict[str, list[str]]:
    """Mapping of tag name to list of DOI/id references."""
    if not path.exists():
        return {}
    data = load_yaml(path, dict)
    tags: dict[str, list[str]] = {}
    for name, refs in data.items():
        where = f"{path}: tag {name!r}"
        if not isinstance(name, str):
            raise ConfigError(f"{where}: tag names must be strings")
        tags[name] = expect_str_list(refs, where)
    return tags


def _iter_matches(overrides: list[Override], works: list[Work]) -> Iterator[tuple[Override, Work]]:
    """Pair each override with the works it hits, in override file order.

    Indexes the works once, and flips `matched` in this one place so the
    stale-override detection cannot drift between callers. Pre-dedup, several
    works can share a DOI, so the indexes map to lists.
    """
    by_doi: dict[str, list[Work]] = {}
    by_id: dict[str, list[Work]] = {}
    for work in works:
        if work.doi_key:
            by_doi.setdefault(work.doi_key, []).append(work)
        by_id.setdefault(work.id, []).append(work)
    for override in overrides:
        if override.match_doi is not None:
            hits = by_doi.get(override.match_doi, [])
        else:
            hits = by_id.get(override.match_id or "", [])
        for work in hits:
            override.matched = True
            yield override, work


def mark_keep_distinct(works: list[Work], overrides: list[Override]) -> None:
    """Applied before title clustering, ahead of the override patch stage."""
    keep = [o for o in overrides if o.keep_distinct]
    for _, work in _iter_matches(keep, works):
        work.keep_distinct = True


# Expected value shapes for the scalar patch fields; a mistyped value must
# fail as a ConfigError at apply time, not as a TypeError deep in the
# pipeline (sorting, clustering) where the file/entry context is lost.
_SCALAR_PATCH_TYPES: dict[str, tuple[str, tuple[type, ...]]] = {
    "title": ("a string", (str,)),
    "venue": ("a string or null", (str, type(None))),
    "year": ("an integer or null", (int, type(None))),
    "cited_by_count": ("an integer", (int,)),
    "abstract": ("a string or null", (str, type(None))),
    "is_retracted": ("a boolean", (bool,)),
}


def _patch_work(
    work: Work, patch: dict[str, Any], authors_cfg: list[AuthorConfig], where: str
) -> None:
    for key, value in patch.items():
        if key == "authors":
            work.authors = _parse_authors(value, authors_cfg, where)
        elif key == "open_access":
            if isinstance(value, dict):
                value = value.get("url")
            work.open_access_url = str(value) if value else None
        elif key == "doi":
            work.doi = doi_url(str(value)) if value else None
        elif key == "type":
            work.type = _parse_type(value, where)
        elif key == "tags":
            work.tags = expect_str_list(value, f"{where}: 'tags'")
        elif key == "date":
            # YAML parses unquoted ISO dates as date objects; accept both.
            if value is not None and not isinstance(value, (str, datetime.date)):
                raise ConfigError(f"{where}: 'date' must be an ISO date string or null")
            work.date = str(value) if value is not None else None
        else:
            description, types = _SCALAR_PATCH_TYPES[key]
            if not isinstance(value, types) or (isinstance(value, bool) and bool not in types):
                raise ConfigError(f"{where}: '{key}' must be {description}")
            setattr(work, key, value)


def apply_overrides(
    works: list[Work], overrides: list[Override], authors_cfg: list[AuthorConfig]
) -> tuple[list[Work], int]:
    """Patch or exclude merged records; returns (kept, excluded_count)."""
    excluded: set[int] = set()
    for override, work in _iter_matches(overrides, works):
        if override.exclude:
            excluded.add(id(work))
        elif override.patch:
            # Compare against the pre-patch record: comparing the override
            # against the output would be circular, the output already has
            # the override applied and every entry would look load-bearing.
            # Deep copy so the check stays honest even if a patch branch
            # ever mutates a list in place instead of reassigning it.
            before = copy.deepcopy(work)
            _patch_work(work, override.patch, authors_cfg, override.where)
            if work != before:
                override.changed = True
    return [w for w in works if id(w) not in excluded], len(excluded)


def unmatched_overrides(overrides: list[Override]) -> list[str]:
    """Locations of overrides that touched nothing (stale DOI or id)."""
    return [o.where for o in overrides if not o.matched]


def redundant_overrides(overrides: list[Override]) -> list[str]:
    """Locations of field patches that no longer change anything.

    Upstream caught up with the correction. Redundant is information, not
    an instruction to delete: an override may stay as insurance against the
    upstream regressing again. keep_distinct-only entries drop out via the
    empty-patch check; `exclude` needs its explicit guard because an
    exclude entry carrying patch fields never runs them.
    """
    return [o.where for o in overrides if o.matched and o.patch and not o.exclude and not o.changed]


def apply_tags(works: list[Work], tags: dict[str, list[str]]) -> list[str]:
    """Attach curated tags; returns unmatched references for warnings.

    References are matched as DOIs when they look like one (URL or 10.x
    form), else as record ids. Each record's final tag list is sorted for
    deterministic output.
    """
    by_doi = {w.doi_key: w for w in works if w.doi_key}
    by_id = {w.id: w for w in works}
    unmatched = []
    for name, refs in tags.items():
        for ref in refs:
            key = doi_key(ref)
            work = by_doi.get(key) if key.startswith("10.") else by_id.get(ref)
            if work is None:
                unmatched.append(f"tag {name!r}: {ref}")
            elif name not in work.tags:
                work.tags.append(name)
    for work in works:
        work.tags.sort()
    return unmatched
