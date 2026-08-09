from __future__ import annotations

from pathlib import Path

import pytest

from erga.config import AuthorConfig
from erga.curation import (
    apply_overrides,
    apply_tags,
    load_manual,
    load_overrides,
    load_tags,
    mark_keep_distinct,
    redundant_overrides,
    unmatched_overrides,
)
from erga.dedup import cluster_by_title, dedup_by_doi
from erga.errors import ConfigError
from erga.model import Work

CARBERRY = AuthorConfig(
    name="Josiah Carberry", orcid="0000-0002-1825-0097", aliases=["J. S. Carberry"]
)


def write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_missing_curation_files_mean_none(tmp_path: Path) -> None:
    assert load_manual(tmp_path / "manual.yml", []) == []
    assert load_overrides(tmp_path / "overrides.yml") == []
    assert load_tags(tmp_path / "tags.yml") == {}


def test_load_manual_entry(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        "manual.yml",
        """\
- title: The Lost Lectures
  authors: ["J. S. Carberry", "An Outsider"]
  venue: Brown University Press
  year: 2020
  doi: 10.5555/LOST
  type: book
  tags: [legacy]
""",
    )
    (work,) = load_manual(path, [CARBERRY])
    assert work.id == "manual-the-lost-lectures"
    assert work.source == "manual"
    assert work.doi == "https://doi.org/10.5555/lost"
    assert work.type == "book"
    assert work.tags == ["legacy"]
    carberry, outsider = work.authors
    assert carberry.tracked and carberry.orcid == "https://orcid.org/0000-0002-1825-0097"
    # Matched via alias; tracked_as carries the canonical configured name.
    assert carberry.tracked_as == "Josiah Carberry"
    assert not outsider.tracked and outsider.orcid is None
    assert outsider.tracked_as is None


def test_load_manual_single_author_string_and_id_collisions(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        "manual.yml",
        "- title: Same Title\n  authors: Solo Author\n- title: Same Title\n",
    )
    first, second = load_manual(path, [])
    assert first.id == "manual-same-title"
    assert second.id == "manual-same-title-2"
    assert first.authors[0].name == "Solo Author"


@pytest.mark.parametrize(
    "content, message",
    [
        ("- authors: [X]\n", "'title' is required"),
        ("- title: T\n  citations: 5\n", "unknown keys"),
        ("- title: T\n  type: sonnet\n", "not one of"),
        ("- title: T\n  year: 'twenty'\n", "integer"),
    ],
)
def test_load_manual_rejects(tmp_path: Path, content: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_manual(write(tmp_path, "manual.yml", content), [])


def test_load_overrides_validation(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="exactly one"):
        load_overrides(write(tmp_path, "o1.yml", "- doi: 10.1/x\n  id: W1\n"))
    with pytest.raises(ConfigError, match="exactly one"):
        load_overrides(write(tmp_path, "o2.yml", "- venue: X\n"))
    with pytest.raises(ConfigError, match="unknown fields"):
        load_overrides(write(tmp_path, "o3.yml", "- id: W1\n  venu: X\n"))


def test_apply_overrides_patch_exclude_and_stale(tmp_path: Path) -> None:
    overrides = load_overrides(
        write(
            tmp_path,
            "overrides.yml",
            """\
- doi: https://doi.org/10.5555/XYZ123
  venue: Corrected Journal
  type: conference
- id: W2
  exclude: true
- id: W404
  venue: Never Applied
""",
        )
    )
    works = [
        Work(id="W1", title="A", doi="https://doi.org/10.5555/xyz123"),
        Work(id="W2", title="B"),
    ]
    kept, excluded = apply_overrides(works, overrides, [])
    assert [w.id for w in kept] == ["W1"]
    assert excluded == 1
    assert kept[0].venue == "Corrected Journal"
    assert kept[0].type == "conference"
    assert unmatched_overrides(overrides) == [f"{tmp_path / 'overrides.yml'}: entry 3"]


def test_redundant_overrides_compare_against_pre_patch_values(tmp_path: Path) -> None:
    overrides = load_overrides(
        write(
            tmp_path,
            "overrides.yml",
            """\
- id: W1
  type: conference
- id: W2
  type: conference
- id: W3
  exclude: true
- id: W404
  type: conference
""",
        )
    )
    works = [
        Work(id="W1", title="A", type="conference"),  # upstream caught up
        Work(id="W2", title="B", type="other"),  # still load-bearing
        Work(id="W3", title="C"),
    ]
    apply_overrides(works, overrides, [])
    assert redundant_overrides(overrides) == [f"{tmp_path / 'overrides.yml'}: entry 1"]


def test_apply_overrides_open_access_and_authors(tmp_path: Path) -> None:
    overrides = load_overrides(
        write(
            tmp_path,
            "overrides.yml",
            """\
- id: W1
  open_access: {url: https://oa.example/pdf}
  authors: ["Josiah Carberry"]
- id: W2
  open_access: null
""",
        )
    )
    works = [
        Work(id="W1", title="A"),
        Work(id="W2", title="B", open_access_url="https://stale.example"),
    ]
    kept, _ = apply_overrides(works, overrides, [CARBERRY])
    assert kept[0].open_access_url == "https://oa.example/pdf"
    assert kept[0].authors[0].tracked
    assert kept[1].open_access_url is None


@pytest.mark.parametrize(
    "field_line, message",
    [
        ("year: '2024'", "'year' must be an integer"),
        ("title: 5", "'title' must be a string"),
        ("is_retracted: 1", "'is_retracted' must be a boolean"),
        ("year: true", "'year' must be an integer"),
        ("cited_by_count: '5'", "'cited_by_count' must be an integer"),
    ],
)
def test_apply_overrides_rejects_mistyped_values(
    tmp_path: Path, field_line: str, message: str
) -> None:
    overrides = load_overrides(write(tmp_path, "overrides.yml", f"- id: W1\n  {field_line}\n"))
    with pytest.raises(ConfigError, match=message):
        apply_overrides([Work(id="W1", title="A")], overrides, [])


def test_apply_overrides_coerces_yaml_date(tmp_path: Path) -> None:
    overrides = load_overrides(write(tmp_path, "overrides.yml", "- id: W1\n  date: 2024-03-01\n"))
    kept, _ = apply_overrides([Work(id="W1", title="A")], overrides, [])
    assert kept[0].date == "2024-03-01"


def test_mark_keep_distinct(tmp_path: Path) -> None:
    overrides = load_overrides(
        write(tmp_path, "overrides.yml", "- id: W1\n  keep_distinct: true\n")
    )
    works = [Work(id="W1", title="A"), Work(id="W2", title="A")]
    mark_keep_distinct(works, overrides)
    assert works[0].keep_distinct and not works[1].keep_distinct
    # A pin whose record survives must not warn: matched is settled by the
    # patch stage, so that verdict only exists once apply_overrides has run.
    apply_overrides(works, overrides, [])
    assert unmatched_overrides(overrides) == []


def test_keep_distinct_pin_lost_to_doi_merge_reports_unmatched(tmp_path: Path) -> None:
    """keep_distinct exempts from title clustering only, never from DOI merging.

    When the pinned record loses that merge, the entry's patch cannot apply.
    The build must say so instead of reporting the correction as redundant.
    """
    overrides = load_overrides(
        write(
            tmp_path,
            "overrides.yml",
            "- id: W1\n  keep_distinct: true\n  venue: Corrected Venue\n",
        )
    )
    works = [
        Work(id="W1", title="A Study of Things", doi="https://doi.org/10.5555/abc"),
        Work(
            id="W9",
            title="A Study of Things",
            doi="https://doi.org/10.5555/abc",
            cited_by_count=42,
        ),
    ]
    mark_keep_distinct(works, overrides)
    survivors = cluster_by_title(dedup_by_doi(works))
    assert [w.id for w in survivors] == ["W9"]

    kept, _ = apply_overrides(survivors, overrides, [])
    assert kept[0].venue is None
    assert unmatched_overrides(overrides) == [f"{tmp_path / 'overrides.yml'}: entry 1"]
    assert redundant_overrides(overrides) == []


def test_apply_tags_by_doi_and_id(tmp_path: Path) -> None:
    tags = load_tags(
        write(
            tmp_path,
            "tags.yml",
            """\
featured:
  - https://doi.org/10.5555/XYZ123
  - W2
dataset-of-the-year:
  - 10.5555/GHOST
""",
        )
    )
    works = [
        Work(id="W1", title="A", doi="https://doi.org/10.5555/xyz123", tags=["zeta"]),
        Work(id="W2", title="B"),
    ]
    unmatched = apply_tags(works, tags)
    assert works[0].tags == ["featured", "zeta"]  # sorted
    assert works[1].tags == ["featured"]
    assert unmatched == ["tag 'dataset-of-the-year': 10.5555/GHOST"]


def test_apply_tags_no_duplicates(tmp_path: Path) -> None:
    tags = load_tags(write(tmp_path, "tags.yml", "legacy:\n  - W1\n"))
    works = [Work(id="W1", title="A", tags=["legacy"])]
    apply_tags(works, tags)
    assert works[0].tags == ["legacy"]
