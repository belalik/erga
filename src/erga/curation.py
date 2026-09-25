"""Curation files: manual entries, overrides, tags.

All three survive every refresh; a missing file means "none". Typos fail
loudly: curation is the maintainer's reviewable artifact, and a silently
skipped patch is worse than an aborted run.
"""

from __future__ import annotations

import copy
import datetime
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from erga.config import AuthorConfig, expect_str_list, load_yaml, reject_unknown_keys
from erga.errors import ConfigError
from erga.model import Work, WorkAuthor, doi_key, doi_url, slugify, validate_work_type

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


def _opt_str(entry: dict[str, Any], key: str) -> str | None:
    value = entry.get(key)
    return str(value) if value is not None else None


_ISO_DATE = re.compile(r"\d{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?)?")


def _iso_date(value: Any, where: str) -> str | None:
    """An ISO date of any precision. YAML reads an unquoted full date as a
    date object and a bare year as an int; both stringify to ISO. A quoted
    full date is checked against the calendar too ('2025-02-31')."""
    if value is None:
        return None
    text = str(value)
    if not _ISO_DATE.fullmatch(text):
        raise ConfigError(f"{where}: 'date' must be YYYY, YYYY-MM or YYYY-MM-DD")
    if len(text) == 10:
        try:
            datetime.date.fromisoformat(text)
        except ValueError:
            raise ConfigError(f"{where}: 'date' {text} is not a calendar date") from None
    return text


def _year_for(date: str | None, year: Any, where: str, hint: str = "") -> Any:
    """The year a curated date implies when none is given, so a date-only
    entry does not publish without one; a year it contradicts is an error."""
    if date is None:
        return year
    date_year = int(date[:4])
    if year is None:
        return date_year
    if year != date_year:
        raise ConfigError(f"{where}: 'year' {year} disagrees with 'date' {date}{hint}")
    return year


def byline_warnings(
    manual: list[Work], overrides: list[Override], authors_cfg: list[AuthorConfig]
) -> list[str]:
    """Curated author strings that probably do not mean what they say.

    `authors: "A, B, C"` becomes one author named "A, B, C" who tracks
    nobody, at exit 0. A comma alone proves nothing, since "Surname, Given"
    is one name. Two commas usually mean a list, though a suffix ("Smith,
    John, Jr.") reads the same, hence "may be". A comma-separated piece that
    is itself a configured name or alias is the surer tell: the string is
    either a list holding a configured author or one author spelt so that
    nothing tracks them, and both need the maintainer.
    """
    known = {name for author in authors_cfg for name in author.match_names()}
    bylines = [(f"manual entry {work.title!r}", work.authors) for work in manual] + [
        (o.where, o.patch["authors"]) for o in overrides if "authors" in o.patch
    ]
    warnings = []
    for label, authors in bylines:
        for author in authors:
            if author.tracked:
                continue
            pieces = [p.strip() for p in author.name.split(",")]
            configured = next((p for p in pieces if p.casefold() in known), None)
            if configured is not None:
                warnings.append(
                    f"{label}: {author.name!r} holds the configured name {configured!r} but "
                    "tracks nobody; list several authors separately, or spell one author "
                    "as configured"
                )
            elif len(pieces) >= 3:
                warnings.append(
                    f"{label}: {author.name!r} may be several authors in one string; "
                    "if so, list them separately"
                )
    return warnings


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

        fields = {
            key: _field_value(key, entry[key], authors_cfg, where)
            for key in ("authors", "year", "date", "doi", "type", "tags")
            if key in entry
        }
        date = fields.get("date")
        year = _year_for(date, fields.get("year"), where)

        works.append(
            Work(
                id=work_id,
                title=title,
                authors=fields.get("authors", []),
                year=year,
                date=date,
                venue=_opt_str(entry, "venue"),
                type=fields.get("type", "other"),
                doi=fields.get("doi"),
                abstract=_opt_str(entry, "abstract"),
                tags=fields.get("tags", []),
                source="manual",
                # Manual entries are explicit curation: never type-filtered.
                keep=True,
            )
        )
    return works


@dataclass
class Override:
    where: str
    match_doi: str | None = None  # doi_key form
    match_id: str | None = None
    # Tri-state: absent (None) does nothing; True drops the record; an
    # explicit False exempts it from the exclude_types filter.
    exclude: bool | None = None
    keep_distinct: bool = False
    patch: dict[str, Any] = field(default_factory=dict)
    matched: bool = False
    changed: bool = False


def load_overrides(path: Path, authors_cfg: list[AuthorConfig]) -> list[Override]:
    """Patches keyed by DOI or id; absent file means none.

    Every field is checked and coerced here, not when a record matches: an
    entry whose id has gone stale would otherwise carry a typo through a
    successful build, the silently skipped patch the module contract bars.
    """
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
        patch = {k: _field_value(k, v, authors_cfg, where) for k, v in patch.items()}
        # A patched date carries its year, as a manual date does, and a year
        # the same patch contradicts is an error here, matched or not.
        if patch.get("date") is not None:
            patch["year"] = _year_for(patch["date"], patch.get("year"), where)
        overrides.append(
            Override(
                where=where,
                match_doi=doi_key(str(entry["doi"])) if "doi" in entry else None,
                match_id=str(entry["id"]) if "id" in entry else None,
                exclude=bool(entry["exclude"]) if "exclude" in entry else None,
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


def _iter_matches(
    overrides: list[Override], works: list[Work], *, record_match: bool = True
) -> Iterator[tuple[Override, Work]]:
    """Pair each override with the works it hits, in override file order.

    Indexes the works once, and flips `matched` in this one place so the
    stale-override detection cannot drift between callers. Pre-dedup, several
    works can share a DOI, so the indexes map to lists.

    `record_match=False` is for passes that run before dedup: a work they hit
    may not survive to the patch stage, and a match recorded against a record
    that later loses a DOI merge would mask the override as bound when nothing
    it names still exists.
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
            if record_match:
                override.matched = True
            yield override, work


def mark_keep_distinct(works: list[Work], overrides: list[Override]) -> None:
    """Applied before title clustering, ahead of the override patch stage.

    Deliberately does not record matches: `keep_distinct` exempts a record
    from title clustering only, so a marked work can still lose an earlier
    DOI-level merge. Whether an override bound to anything is decided by
    `apply_overrides`, against the records that actually survived.
    """
    keep = [o for o in overrides if o.keep_distinct]
    for _, work in _iter_matches(keep, works, record_match=False):
        work.keep_distinct = True


# Expected value shapes for the scalar fields; a mistyped value must fail
# as a ConfigError when the file loads, not as a TypeError deep in the
# pipeline (sorting, clustering) where the file/entry context is lost.
_SCALAR_PATCH_TYPES: dict[str, tuple[str, tuple[type, ...]]] = {
    "title": ("a string", (str,)),
    "venue": ("a string or null", (str, type(None))),
    "year": ("an integer or null", (int, type(None))),
    "cited_by_count": ("an integer", (int,)),
    "abstract": ("a string or null", (str, type(None))),
    "is_retracted": ("a boolean", (bool,)),
}


# Patch keys whose record attribute is named differently.
_PATCH_ATTRS = {"open_access": "open_access_url"}


def _field_value(key: str, value: Any, authors_cfg: list[AuthorConfig], where: str) -> Any:
    """One curated field, checked and coerced. The manual and override
    loaders share it, so the two files cannot drift apart on a rule."""
    if key == "authors":
        return _parse_authors(value, authors_cfg, where)
    if key == "open_access":
        if isinstance(value, dict):
            value = value.get("url")
        return str(value) if value else None
    if key == "doi":
        return doi_url(str(value)) if value else None
    if key == "type":
        return validate_work_type(value, where)
    if key == "tags":
        return expect_str_list(value, f"{where}: 'tags'")
    if key == "date":
        return _iso_date(value, where)
    description, types = _SCALAR_PATCH_TYPES[key]
    if not isinstance(value, types) or (isinstance(value, bool) and bool not in types):
        raise ConfigError(f"{where}: '{key}' must be {description}")
    return value


def _patch_work(work: Work, patch: dict[str, Any], where: str) -> None:
    for key, value in patch.items():
        # Lists are copied: the record's own list gets appended to later
        # (tags), and the override must keep what the file said.
        copied = list(value) if isinstance(value, list) else value
        setattr(work, _PATCH_ATTRS.get(key, key), copied)
    # The one check that needs the record: a patched year against the date
    # the record keeps, so no output carries a year beside a date that
    # contradicts it. A date patch settled its own year when the file loaded.
    if "year" in patch and "date" not in patch:
        work.year = _year_for(
            work.date,
            patch["year"],
            where,
            hint=" (patch 'date' too, or 'date: null' when only the year is known)",
        )


def apply_overrides(works: list[Work], overrides: list[Override]) -> tuple[list[Work], int]:
    """Patch or exclude merged records; returns (kept, excluded_count)."""
    excluded: set[int] = set()
    for override, work in _iter_matches(overrides, works):
        if override.exclude:
            excluded.add(id(work))
            continue
        if override.exclude is False:
            work.keep = True
        if override.patch:
            # Compare against the pre-patch record: comparing the override
            # against the output would be circular, the output already has
            # the override applied and every entry would look load-bearing.
            # Deep copy so the check stays honest even if a value is ever
            # mutated in place instead of reassigned.
            before = copy.deepcopy(work)
            _patch_work(work, override.patch, override.where)
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
