"""Configuration loading and validation (requirements section 5)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from erga.errors import ConfigError
from erga.model import normalize_orcid

_ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
_OPENALEX_AUTHOR_RE = re.compile(r"^A\d+$")


@dataclass
class AuthorConfig:
    name: str
    orcid: str | None = None
    openalex_id: str | None = None
    aliases: list[str] = field(default_factory=list)

    def match_names(self) -> set[str]:
        """Casefolded name and aliases, for matching manual entries."""
        return {n.casefold().strip() for n in [self.name, *self.aliases]}


@dataclass
class Config:
    mailto: str
    authors: list[AuthorConfig]
    api_key_env: str = "OPENALEX_API_KEY"
    include_xpac: bool = False
    output_path: Path = Path("publications.json")
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


def _parse_author(entry: Any, path: Path, index: int) -> AuthorConfig:
    where = f"{path}: authors[{index}]"
    if not isinstance(entry, dict):
        raise ConfigError(f"{where}: expected a mapping")
    reject_unknown_keys(entry, {"name", "orcid", "openalex_id", "aliases"}, where)
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
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
    if orcid is None and openalex_id is None:
        raise ConfigError(f"{where}: needs 'orcid' or 'openalex_id'")
    aliases = expect_str_list(entry.get("aliases", []), f"{where}: 'aliases'")
    return AuthorConfig(name=name.strip(), orcid=orcid, openalex_id=openalex_id, aliases=aliases)


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
    reject_unknown_keys(data, {"mailto", "authors", "openalex", "output", "curation"}, str(path))

    mailto = data.get("mailto")
    if not isinstance(mailto, str) or "@" not in mailto:
        raise ConfigError(f"{path}: 'mailto' is required (identifies requests to the APIs)")

    raw_authors = data.get("authors")
    if not isinstance(raw_authors, list) or not raw_authors:
        raise ConfigError(f"{path}: 'authors' must be a non-empty list")
    authors = [_parse_author(entry, path, i) for i, entry in enumerate(raw_authors)]

    openalex = _section(data, "openalex", path, {"api_key_env", "include_xpac"})
    output = _section(data, "output", path, {"path"})
    curation = _section(data, "curation", path, {"manual", "overrides", "tags"})

    return Config(
        mailto=mailto.strip(),
        authors=authors,
        api_key_env=str(openalex.get("api_key_env", "OPENALEX_API_KEY")),
        include_xpac=bool(openalex.get("include_xpac", False)),
        output_path=base / str(output.get("path", "publications.json")),
        manual_path=base / str(curation.get("manual", "manual.yml")),
        overrides_path=base / str(curation.get("overrides", "overrides.yml")),
        tags_path=base / str(curation.get("tags", "tags.yml")),
    )
