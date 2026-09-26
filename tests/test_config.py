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
  exclude_types: [preprint, other]
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
    assert config.exclude_types == frozenset({"preprint", "other"})
    assert config.manual_path == tmp_path / "curation" / "manual.yml"


@pytest.mark.parametrize(
    "content, message",
    [
        ("authors:\n  - {name: X, orcid: 0000-0002-1825-0097}\n", "mailto"),
        ("mailto: a@b.c\nauthors: []\n", "non-empty"),
        ("mailto: a@b.c\nauthors:\n  - {orcid: 0000-0002-1825-0097}\n", "name"),
        ("mailto: a@b.c\nauthors:\n  - {name: '.', orcid: 0000-0002-1825-0097}\n", "name"),
        # A blank alias would search every byline for nothing at all.
        ("mailto: a@b.c\nauthors:\n  - {name: X, aliases: ['  ']}\n", "no name in it"),
        ("mailto: a@b.c\nauthors:\n  - {name: X, aliases: ['_']}\n", "no name in it"),
        ("mailto: a@b.c\nauthors:\n  - {name: X, orcid: not-an-orcid}\n", "invalid ORCID"),
        ("mailto: a@b.c\nauthors:\n  - {name: X, openalex_id: W123}\n", "OpenAlex author id"),
        (MINIMAL + "surprise: true\n", "unknown keys"),
        (MINIMAL + "openalex: {polite: yes}\n", "unknown keys"),
        (MINIMAL + "output: {exclude_types: [sonnet]}\n", "not one of"),
        (MINIMAL + "output: {exclude_types: preprint}\n", "list of strings"),
    ],
)
def test_invalid_configs(tmp_path: Path, content: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(write_config(tmp_path, content))


def test_tracking_only_author_needs_no_ids(tmp_path: Path) -> None:
    config = load_config(
        write_config(
            tmp_path,
            "mailto: a@b.c\nauthors:\n  - {name: Priya Nair, aliases: [P. Nair]}\n",
        )
    )
    author = config.authors[0]
    assert author.orcid is None and author.openalex_id is None
    assert "p. nair" in author.match_names()


def test_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "absent.yml")


def test_normalize_orcid() -> None:
    assert normalize_orcid("https://orcid.org/0000-0002-1825-009x") == "0000-0002-1825-009X"
    assert normalize_orcid("0000-0002-1825-0097") == "0000-0002-1825-0097"


DECLARED_HOME = """\
mailto: maintainer@example.org
home: https://ror.org/0AEGEAN12
authors:
  - name: Josiah Carberry
    orcid: 9999-0000-0000-0001
  - name: A Visitor
    orcid: 9999-0000-0000-0002
    home: 0packy456
  - name: An Exception
    orcid: 9999-0000-0000-0003
    home: null
"""


def test_home_declaration_inherits_replaces_and_opts_out(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, DECLARED_HOME))
    assert config.home == ("0aegean12",)
    # Absent inherits the department default; a value replaces it; an
    # explicit null opts one person out without inventing a false ROR.
    assert [a.home for a in config.authors] == [("0aegean12",), ("0packy456",), None]


@pytest.mark.parametrize(
    "value",
    ["0aegean12", "https://ror.org/0aegean12", "ror.org/0aegean12", "https://ROR.ORG/0AEGEAN12"],
)
def test_every_spelling_of_one_ror_canonicalizes_the_same(tmp_path: Path, value: str) -> None:
    content = MINIMAL.replace("mailto:", f"home: {value}\nmailto:")
    assert load_config(write_config(tmp_path, content)).home == ("0aegean12",)


def test_a_mover_declares_every_post_and_the_list_replaces_the_default(tmp_path: Path) -> None:
    content = DECLARED_HOME.replace(
        "    home: 0packy456\n",
        "    home: [0aegean12, https://ror.org/0packy456, ror.org/0AEGEAN12]\n",
    )
    config = load_config(write_config(tmp_path, content))
    # Order kept, spellings canonicalized, and one id named twice counts once.
    assert config.authors[1].home == ("0aegean12", "0packy456")


def test_a_top_level_list_is_every_authors_default(tmp_path: Path) -> None:
    content = DECLARED_HOME.replace(
        "home: https://ror.org/0AEGEAN12\n", "home: [0aegean12, 0packy456]\n"
    ).replace("    home: 0packy456\n", "")
    config = load_config(write_config(tmp_path, content))
    both = ("0aegean12", "0packy456")
    assert config.home == both
    assert [a.home for a in config.authors] == [both, both, None]


def test_an_empty_home_list_is_refused_not_read_as_an_opt_out(tmp_path: Path) -> None:
    content = MINIMAL + "    home: []\n"
    with pytest.raises(ConfigError, match="use null to opt out"):
        load_config(write_config(tmp_path, content))


def test_a_malformed_ror_in_a_home_list_names_its_position(tmp_path: Path) -> None:
    content = MINIMAL + "    home: [0aegean12, nonsense]\n"
    with pytest.raises(ConfigError, match=r"authors\[0\]: 'home'\[1\]"):
        load_config(write_config(tmp_path, content))


def test_no_declaration_leaves_every_author_undeclared(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, MINIMAL))
    assert config.home is None
    assert config.authors[0].home is None


@pytest.mark.parametrize(
    "value",
    [
        "not-a-ror",
        # Right shape, wrong authority: a ROR is a ror.org id or nothing.
        "https://example.org/0aegean12",
        # The authority has to be the host, not a substring anywhere in it.
        "https://evil.example/ror.org/0aegean12",
        "prefix-ror.org/0aegean12",
        # 'l' is not in the ROR alphabet.
        "0aeglan12",
        # The last two characters are check digits.
        "0aegeanab",
    ],
)
def test_a_malformed_home_is_a_config_error(tmp_path: Path, value: str) -> None:
    content = MINIMAL.replace("mailto:", f"home: {value}\nmailto:")
    with pytest.raises(ConfigError, match=r"ROR|ror\.org"):
        load_config(write_config(tmp_path, content))


def test_a_malformed_author_home_names_the_author(tmp_path: Path) -> None:
    content = MINIMAL + "    home: nonsense\n"
    with pytest.raises(ConfigError, match=r"authors\[0\]"):
        load_config(write_config(tmp_path, content))
