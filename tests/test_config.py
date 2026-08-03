from __future__ import annotations

from pathlib import Path

import pytest

from erga.config import load_config
from erga.errors import ConfigError
from erga.model import normalize_orcid

MINIMAL = """\
mailto: maintainer@example.org
authors:
  - name: Josiah Carberry
    orcid: 0000-0002-1825-0097
"""


def write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "erga.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_minimal_config_defaults(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, MINIMAL))
    assert config.mailto == "maintainer@example.org"
    assert config.api_key_env == "OPENALEX_API_KEY"
    assert config.include_xpac is False
    assert config.output_path == tmp_path / "publications.json"
    assert config.manual_path == tmp_path / "manual.yml"
    assert config.overrides_path == tmp_path / "overrides.yml"
    assert config.tags_path == tmp_path / "tags.yml"
    author = config.authors[0]
    assert author.orcid == "0000-0002-1825-0097"
    assert author.match_names() == {"josiah carberry"}


def test_full_config(tmp_path: Path) -> None:
    config = load_config(
        write_config(
            tmp_path,
            """\
mailto: maintainer@example.org
authors:
  - name: Josiah Carberry
    orcid: https://orcid.org/0000-0002-1825-0097
    aliases: ["J. S. Carberry"]
  - name: Vera Chan
    openalex_id: A5000000002
openalex:
  api_key_env: MY_KEY
  include_xpac: true
output:
  path: data/publications.json
curation:
  manual: curation/manual.yml
""",
        )
    )
    assert config.authors[0].orcid == "0000-0002-1825-0097"
    assert "j. s. carberry" in config.authors[0].match_names()
    assert config.authors[1].openalex_id == "A5000000002"
    assert config.api_key_env == "MY_KEY"
    assert config.include_xpac is True
    assert config.output_path == tmp_path / "data" / "publications.json"
    assert config.manual_path == tmp_path / "curation" / "manual.yml"


@pytest.mark.parametrize(
    "content, message",
    [
        ("authors:\n  - {name: X, orcid: 0000-0002-1825-0097}\n", "mailto"),
        ("mailto: a@b.c\nauthors: []\n", "non-empty"),
        ("mailto: a@b.c\nauthors:\n  - {name: X}\n", "orcid"),
        ("mailto: a@b.c\nauthors:\n  - {orcid: 0000-0002-1825-0097}\n", "name"),
        ("mailto: a@b.c\nauthors:\n  - {name: X, orcid: not-an-orcid}\n", "invalid ORCID"),
        ("mailto: a@b.c\nauthors:\n  - {name: X, openalex_id: W123}\n", "OpenAlex author id"),
        (MINIMAL + "surprise: true\n", "unknown keys"),
        (MINIMAL + "openalex: {polite: yes}\n", "unknown keys"),
    ],
)
def test_invalid_configs(tmp_path: Path, content: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(write_config(tmp_path, content))


def test_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "absent.yml")


def test_normalize_orcid() -> None:
    assert normalize_orcid("https://orcid.org/0000-0002-1825-009x") == "0000-0002-1825-009X"
    assert normalize_orcid("0000-0002-1825-0097") == "0000-0002-1825-0097"
