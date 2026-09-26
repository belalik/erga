"""Configuration loading and validation (requirements section 5)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from erga.dedup import normalize_title
from erga.errors import ConfigError
from erga.model import bare_ror, normalize_orcid, validate_work_type

_ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
_OPENALEX_AUTHOR_RE = re.compile(r"^A\d+$")
# A ROR id is "0" then six characters of a base32 alphabet without i, l, o
# and u, then two check digits. The checksum is not verified here: a
# well-formed id that names no institution fails at resolution, with a
# message that can say so.
_ROR_RE = re.compile(r"^0[0-9a-hj-km-np-tv-z]{6}\d{2}$")
# The whole value when a URL is given, so the host is checked rather than
# merely found somewhere in the string: `https://evil.example/ror.org/<id>`
# is not a ROR URL, and `https://ROR.ORG/<id>` is.
_ROR_URL_RE = re.compile(r"^(?:https?://)?ror\.org/(?P<id>[^/]+)$", re.IGNORECASE)


def normalize_ror(value: Any, where: str) -> str:
    """Canonical bare ROR id, from a bare id or a ror.org URL.

    OpenAlex carries an institution's `ror` as a full URL, so the bare form
    is what the corpus is matched on, by suffix.
    """
    text = str(value).strip().rstrip("/")
    if "/" in text:
        url = _ROR_URL_RE.match(text)
        if not url:
            raise ConfigError(f"{where}: {value!r} is not a ror.org id")
        text = url.group("id")
    bare = bare_ror(text)
    if not _ROR_RE.match(bare):
        raise ConfigError(f"{where}: invalid ROR id {value!r} (expected e.g. 05a28rw58)")
    return bare


def parse_home(value: Any, where: str) -> tuple[str, ...]:
    """A declaration: one ROR, or a list of them for a career that moved.

    An empty list is refused rather than read as an opt-out, because `null`
    already says that and a list someone forgot to fill in should not
    silently mean it.
    """
    if not isinstance(value, list):
        return (normalize_ror(value, where),)
    if not value:
        raise ConfigError(f"{where}: an empty list declares nothing; use null to opt out")
    rors = [normalize_ror(item, f"{where}[{i}]") for i, item in enumerate(value)]
    # Duplicates, bare and URL forms of one id included, count once.
    return tuple(dict.fromkeys(rors))


@dataclass
class AuthorConfig:
    name: str
    orcid: str | None = None
    openalex_id: str | None = None
    aliases: list[str] = field(default_factory=list)
    # The declaration that applies to this author, top-level default already
    # resolved in: bare ROR ids, one per declared place. None means no
    # declaration governs them.
    home: tuple[str, ...] | None = None

    def match_names(self) -> set[str]:
        """Casefolded name and aliases, for matching manual entries."""
        return {n.casefold().strip() for n in [self.name, *self.aliases]}

    @property
    def tracking_only(self) -> bool:
        """No registrar ids: contributes names to tracking, fetches nothing."""
        return self.orcid is None and self.openalex_id is None


@dataclass
class Config:
    mailto: str
    authors: list[AuthorConfig]
    # The top-level declaration, kept as configured; every author already
    # carries the one that governs them.
    home: tuple[str, ...] | None = None
    api_key_env: str = "OPENALEX_API_KEY"
    include_xpac: bool = False
    output_path: Path = Path("publications.json")
    exclude_types: frozenset[str] = frozenset()
    manual_path: Path = Path("manual.yml")
    overrides_path: Path = Path("overrides.yml")
    tags_path: Path = Path("tags.yml")


def load_yaml(path: Path, expect: type) -> Any:
    """Parse a YAML file and check its top-level type."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except OSError as exc:
        raise ConfigError(f"{path}: {exc.strerror or exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc
    if data is None:
        data = expect()
    if not isinstance(data, expect):
        raise ConfigError(f"{path}: expected a {expect.__name__} at top level")
    return data


def reject_unknown_keys(
    mapping: dict[str, Any], allowed: set[str], where: str, noun: str = "keys"
) -> None:
    unknown = set(mapping) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown {noun}: {', '.join(sorted(unknown))}")


def expect_str_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{where}: must be a list of strings")
    return list(value)


def _has_words(name: str) -> bool:
    """Whether a name leaves words for verify's byline match, which folds
    names as titles are folded. A name of punctuation alone would search
    for nothing and match every byline."""
    return bool(normalize_title(name))


def _parse_author(
    entry: Any, path: Path, index: int, default_home: tuple[str, ...] | None
) -> AuthorConfig:
    where = f"{path}: authors[{index}]"
    if not isinstance(entry, dict):
        raise ConfigError(f"{where}: expected a mapping")
    reject_unknown_keys(entry, {"name", "orcid", "openalex_id", "aliases", "home"}, where)
    name = entry.get("name")
    if not isinstance(name, str) or not _has_words(name):
        raise ConfigError(f"{where}: 'name' is required")
    orcid = entry.get("orcid")
    if orcid is not None:
        orcid = normalize_orcid(str(orcid))
        if not _ORCID_RE.match(orcid):
            raise ConfigError(f"{where}: invalid ORCID iD {orcid!r}")
    openalex_id = entry.get("openalex_id")
    if openalex_id is not None:
        openalex_id = str(openalex_id).strip()
        if not _OPENALEX_AUTHOR_RE.match(openalex_id):
            raise ConfigError(f"{where}: invalid OpenAlex author id {openalex_id!r}")
    # Neither id is fine: the entry contributes its names to the tracked
    # flag but resolves and fetches nothing (authors without any registrar
    # identity, or whose works OpenAlex misassigns to a conflated profile).
    aliases = expect_str_list(entry.get("aliases", []), f"{where}: 'aliases'")
    for alias in aliases:
        if not _has_words(alias):
            raise ConfigError(f"{where}: 'aliases' holds an entry with no name in it: {alias!r}")
    # Three states, because a department-wide default must be able to carry
    # an exception: the key absent inherits it, a value replaces it, and an
    # explicit null opts this author out without inventing a false ROR.
    if "home" not in entry:
        home = default_home
    elif entry["home"] is None:
        home = None
    else:
        home = parse_home(entry["home"], f"{where}: 'home'")
    return AuthorConfig(
        name=name.strip(), orcid=orcid, openalex_id=openalex_id, aliases=aliases, home=home
    )


def _section(data: dict[str, Any], key: str, path: Path, allowed: set[str]) -> dict[str, Any]:
    section = data.get(key) or {}
    if not isinstance(section, dict):
        raise ConfigError(f"{path}: '{key}' must be a mapping")
    reject_unknown_keys(section, allowed, f"{path}: {key}")
    return section


def load_config(path: Path) -> Config:
    """Load and validate erga.yml; relative paths resolve against its directory."""
    data = load_yaml(path, dict)
    base = path.resolve().parent
    reject_unknown_keys(
        data, {"mailto", "authors", "openalex", "output", "curation", "home"}, str(path)
    )

    mailto = data.get("mailto")
    if not isinstance(mailto, str) or "@" not in mailto:
        raise ConfigError(f"{path}: 'mailto' is required (identifies requests to the APIs)")

    raw_home = data.get("home")
    home = parse_home(raw_home, f"{path}: 'home'") if raw_home is not None else None

    raw_authors = data.get("authors")
    if not isinstance(raw_authors, list) or not raw_authors:
        raise ConfigError(f"{path}: 'authors' must be a non-empty list")
    authors = [_parse_author(entry, path, i, home) for i, entry in enumerate(raw_authors)]

    openalex = _section(data, "openalex", path, {"api_key_env", "include_xpac"})
    output = _section(data, "output", path, {"path", "exclude_types"})
    curation = _section(data, "curation", path, {"manual", "overrides", "tags"})

    exclude_types = expect_str_list(
        output.get("exclude_types", []), f"{path}: output.exclude_types"
    )
    for value in exclude_types:
        validate_work_type(value, f"{path}: output.exclude_types")

    return Config(
        mailto=mailto.strip(),
        authors=authors,
        home=home,
        api_key_env=str(openalex.get("api_key_env", "OPENALEX_API_KEY")),
        include_xpac=bool(openalex.get("include_xpac", False)),
        output_path=base / str(output.get("path", "publications.json")),
        exclude_types=frozenset(exclude_types),
        manual_path=base / str(curation.get("manual", "manual.yml")),
        overrides_path=base / str(curation.get("overrides", "overrides.yml")),
        tags_path=base / str(curation.get("tags", "tags.yml")),
    )
