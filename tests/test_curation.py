from __future__ import annotations

from pathlib import Path

import pytest

from erga.config import AuthorConfig
from erga.curation import (
    Override,
    apply_overrides,
    apply_tags,
    byline_warnings,
    load_manual,
    load_overrides,
    load_tags,
    mark_keep_distinct,
    orcid_drops,
    redundant_overrides,
    shared_dois,
    unmatched_overrides,
)
from erga.dedup import cluster_by_title, dedup_by_doi
from erga.errors import ConfigError
from erga.model import Work, WorkAuthor

CARBERRY = AuthorConfig(
    name="Josiah Carberry", orcid="0000-0002-1825-0097", aliases=["J. S. Carberry"]
)


def write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def overrides_from(
    tmp_path: Path, content: str, authors: list[AuthorConfig] | None = None
) -> list[Override]:
    return load_overrides(write(tmp_path, "overrides.yml", content), authors or [])


def test_missing_curation_files_mean_none(tmp_path: Path) -> None:
    assert load_manual(tmp_path / "manual.yml", []) == []
    assert load_overrides(tmp_path / "overrides.yml", []) == []
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
    assert work.keep is True  # explicit curation: exempt from exclude_types
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
        ("- title: T\n  year: true\n", "integer"),
        ("- title: T\n  date: 'Nov 2025'\n", "YYYY-MM-DD"),
        ("- title: T\n  date: 2025-13\n", "YYYY-MM-DD"),
        ("- title: T\n  date: '2025-02-31'\n", "not a calendar date"),
        ("- title: T\n  year: 2024\n  date: 2025-11-03\n", "disagrees"),
    ],
)
def test_load_manual_rejects(tmp_path: Path, content: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_manual(write(tmp_path, "manual.yml", content), [])


def test_load_manual_year_comes_from_date_when_absent(tmp_path: Path) -> None:
    # Unquoted, YAML hands over a date object and an int; quoted, strings.
    path = write(
        tmp_path,
        "manual.yml",
        "- title: A\n  date: 2025-11-03\n"
        "- title: B\n  date: '2024-07'\n"
        "- title: C\n  date: 2023\n"
        "- title: D\n  year: 2022\n  date: '2022-05-01'\n",
    )
    works = load_manual(path, [])
    assert [(w.year, w.date) for w in works] == [
        (2025, "2025-11-03"),
        (2024, "2024-07"),
        (2023, "2023"),
        (2022, "2022-05-01"),
    ]


def test_byline_warnings_flag_joined_lists_and_untracked_configured_names(
    tmp_path: Path,
) -> None:
    surname_alias = AuthorConfig(name="Ann Example", aliases=["Example"])
    path = write(
        tmp_path,
        "manual.yml",
        """\
- title: Joined
  authors: "Josiah Carberry, An Outsider"
- title: Three Strangers
  authors: "One Person, Two Person, Three Person"
- title: Suffix
  authors: "Smith, John, Jr."
- title: Surname First, Alias Inside
  authors: "Example, Ann"
- title: One Name, Surname First
  authors: ["Outsider, An", "J. S. Carberry"]
""",
    )
    overrides_path = write(
        tmp_path,
        "overrides.yml",
        '- id: W1\n  authors: "J. S. Carberry, An Outsider"\n- id: W2\n  authors: [Solo Author]\n',
    )
    configured = [CARBERRY, surname_alias]
    manual = load_manual(path, configured)
    overrides = load_overrides(overrides_path, configured)

    def holds(name: str) -> str:
        return (
            f"holds the configured name {name!r} but tracks nobody; "
            "list several authors separately, or spell one author as configured"
        )

    may_be = "may be several authors in one string; if so, list them separately"
    assert byline_warnings(manual, overrides, configured) == [
        f"manual entry 'Joined': 'Josiah Carberry, An Outsider' {holds('Josiah Carberry')}",
        f"manual entry 'Three Strangers': 'One Person, Two Person, Three Person' {may_be}",
        f"manual entry 'Suffix': 'Smith, John, Jr.' {may_be}",
        f"manual entry 'Surname First, Alias Inside': 'Example, Ann' {holds('Example')}",
        f"{overrides_path}: entry 1: 'J. S. Carberry, An Outsider' {holds('J. S. Carberry')}",
    ]


def test_load_overrides_validation(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="needs 'id' or 'doi' to match on"):
        load_overrides(write(tmp_path, "o2.yml", "- venue: X\n"), [])
    with pytest.raises(ConfigError, match="unknown fields"):
        load_overrides(write(tmp_path, "o3.yml", "- id: W1\n  venu: X\n"), [])


def test_id_override_patches_doi_and_a_doi_override_matches_on_it(tmp_path: Path) -> None:
    overrides = overrides_from(
        tmp_path,
        """\
- id: W1
  doi: 10.5555/FOUND
  venue: Found Proceedings
- id: W2
  doi: null
- doi: 10.5555/kept
  venue: Only A Patch
- id: W4
  doi: https://doi.org/10.5555/same
""",
    )
    assert [(o.match_id, o.match_doi) for o in overrides] == [
        ("W1", None),
        ("W2", None),
        (None, "10.5555/kept"),
        ("W4", None),
    ]
    assert "doi" not in overrides[2].patch
    works = [
        Work(id="W1", title="A Broken Copy"),
        Work(id="W2", title="B", doi="https://doi.org/10.5555/wrong"),
        Work(id="W3", title="C", doi="https://doi.org/10.5555/kept"),
        Work(id="W4", title="D", doi="https://doi.org/10.5555/same"),
    ]
    kept, _ = apply_overrides(works, overrides)
    assert [w.doi for w in kept] == [
        "https://doi.org/10.5555/found",
        None,
        "https://doi.org/10.5555/kept",
        "https://doi.org/10.5555/same",
    ]
    assert kept[0].venue == "Found Proceedings"
    assert kept[2].venue == "Only A Patch"
    assert unmatched_overrides(overrides) == []
    assert redundant_overrides(overrides) == [f"{tmp_path / 'overrides.yml'}: entry 4"]
    # Tags run after overrides and match the patched DOI.
    assert apply_tags(kept, {"found": ["10.5555/found"]}) == []
    assert kept[0].tags == ["found"]


def test_shared_dois_warns_on_a_patched_doi_and_keeps_both(tmp_path: Path) -> None:
    overrides = overrides_from(tmp_path, "- id: W1\n  doi: 10.5555/taken\n")
    works = [
        Work(id="W1", title="A Broken Copy"),
        Work(id="W2", title="The Record Itself", doi="https://doi.org/10.5555/TAKEN"),
        Work(id="W3", title="Unrelated", doi="https://doi.org/10.5555/other"),
    ]
    assert shared_dois(works) == []
    kept, _ = apply_overrides(works, overrides)
    assert [w.id for w in kept] == ["W1", "W2", "W3"]
    assert shared_dois(kept) == [
        "DOI 10.5555/taken is on W1, W2 after an override patched it in; both stay listed: "
        "exclude the patched copy if the other is its DOI record, else fix the patch"
    ]


def test_apply_overrides_patch_exclude_and_stale(tmp_path: Path) -> None:
    overrides = overrides_from(
        tmp_path,
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
    works = [
        Work(id="W1", title="A", doi="https://doi.org/10.5555/xyz123"),
        Work(id="W2", title="B"),
    ]
    kept, excluded = apply_overrides(works, overrides)
    assert [w.id for w in kept] == ["W1"]
    assert excluded == 1
    assert kept[0].venue == "Corrected Journal"
    assert kept[0].type == "conference"
    assert unmatched_overrides(overrides) == [f"{tmp_path / 'overrides.yml'}: entry 3"]


def test_apply_overrides_explicit_exclude_false_marks_keep(tmp_path: Path) -> None:
    overrides = overrides_from(
        tmp_path,
        """\
- id: W1
  exclude: false
  venue: Kept and Patched
- id: W2
  venue: Only Patched
""",
    )
    works = [Work(id="W1", title="A"), Work(id="W2", title="B")]
    kept, excluded = apply_overrides(works, overrides)
    assert excluded == 0
    assert kept[0].keep is True
    assert kept[0].venue == "Kept and Patched"
    # An override that merely patches must not exempt the record.
    assert kept[1].keep is False
    assert kept[1].venue == "Only Patched"


def test_redundant_overrides_compare_against_pre_patch_values(tmp_path: Path) -> None:
    overrides = overrides_from(
        tmp_path,
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
    works = [
        Work(id="W1", title="A", type="conference"),  # upstream caught up
        Work(id="W2", title="B", type="other"),  # still load-bearing
        Work(id="W3", title="C"),
    ]
    apply_overrides(works, overrides)
    assert redundant_overrides(overrides) == [f"{tmp_path / 'overrides.yml'}: entry 1"]


def test_apply_overrides_open_access_and_authors(tmp_path: Path) -> None:
    overrides = overrides_from(
        tmp_path,
        """\
- id: W1
  open_access: {url: https://oa.example/pdf}
  authors: ["Josiah Carberry"]
- id: W2
  open_access: null
""",
        [CARBERRY],
    )
    works = [
        Work(id="W1", title="A"),
        Work(id="W2", title="B", open_access_url="https://stale.example"),
    ]
    kept, _ = apply_overrides(works, overrides)
    assert kept[0].open_access_url == "https://oa.example/pdf"
    assert kept[0].authors[0].tracked
    assert kept[1].open_access_url is None


MEMBER = AuthorConfig(name="Ann Member", openalex_id="A5000000003", aliases=["Annie Member"])


def _id(n: int) -> str:
    return f"https://orcid.org/9999-0000-0000-000{n}"


def test_an_authors_patch_keeps_the_records_orcids(tmp_path: Path) -> None:
    # smartmove-site (2026-10-30): a patch fixing one name stripped every
    # iD on the record, an openalex_id-only member's and each co-author's.
    overrides = overrides_from(
        tmp_path, '- id: W1\n  authors: ["Ann Member", "Bo Colleague", "Cy Re-Named"]\n', [MEMBER]
    )
    upstream = [
        WorkAuthor("Annie Member", orcid=_id(3), tracked=True, tracked_as="Ann Member"),
        WorkAuthor("Bo Colleague", orcid=_id(4)),
        WorkAuthor("Cy Renamed", orcid=_id(5)),
    ]
    kept, _ = apply_overrides([Work(id="W1", title="A", authors=upstream)], overrides)
    # The member by tracked_as across the rename, the co-author by name.
    assert [a.orcid for a in kept[0].authors] == [_id(3), _id(4), None]
    assert kept[0].authors[0].name == "Ann Member"
    assert orcid_drops(overrides) == [f"{tmp_path / 'overrides.yml'}: entry 1, W1: Cy Renamed"]
    # The patch's own authors are shared by every record it hits: untouched.
    assert [a.orcid for a in overrides[0].patch["authors"]] == [None, None, None]


def test_an_authors_patch_upstream_agrees_with_is_redundant(tmp_path: Path) -> None:
    # Dropping the iDs used to make every authors patch look load-bearing.
    overrides = overrides_from(tmp_path, '- id: W1\n  authors: ["Bo Colleague"]\n')
    upstream = [WorkAuthor("Bo Colleague", orcid=_id(4))]
    apply_overrides([Work(id="W1", title="A", authors=upstream)], overrides)
    assert redundant_overrides(overrides) == [f"{tmp_path / 'overrides.yml'}: entry 1"]
    assert orcid_drops(overrides) == []


def test_an_authors_patch_keeps_ids_across_accent_fixes_and_repeats(tmp_path: Path) -> None:
    overrides = overrides_from(
        tmp_path, '- id: W1\n  authors: ["Ann Member", "Bo Müller"]\n', [MEMBER]
    )
    member = WorkAuthor("Annie Member", orcid=_id(3), tracked=True, tracked_as="Ann Member")
    # OpenAlex repeats the member's authorship; the patch names them once.
    upstream = [member, member, WorkAuthor("Bo Muller", orcid=_id(4))]
    kept, _ = apply_overrides([Work(id="W1", title="A", authors=upstream)], overrides)
    assert [a.orcid for a in kept[0].authors] == [_id(3), _id(4)]
    # The repeat's iD is still on the record: nothing was dropped.
    assert orcid_drops(overrides) == []


def _apply(
    tmp_path: Path,
    names: list[str],
    upstream: list[WorkAuthor],
    authors_cfg: list[AuthorConfig] | None = None,
) -> tuple[list[str | None], list[str]]:
    """One `authors` patch on one record: the published iDs, and the drops."""
    listed = ", ".join(f'"{name}"' for name in names)
    overrides = overrides_from(tmp_path, f"- id: W1\n  authors: [{listed}]\n", authors_cfg)
    kept, _ = apply_overrides([Work(id="W1", title="A", authors=upstream)], overrides)
    drops = [drop.split(", W1: ", 1)[1] for drop in orcid_drops(overrides)]
    return [a.orcid for a in kept[0].authors], drops


def test_two_people_folding_alike_never_trade_ids(tmp_path: Path) -> None:
    upstream = [WorkAuthor("Bo Müller", orcid=_id(1)), WorkAuthor("Bo Muller", orcid=_id(2))]
    # Reordered: each keeps their own, by exact name.
    assert _apply(tmp_path, ["Bo Muller", "Bo Müller"], upstream) == ([_id(2), _id(1)], [])
    # One removed: the other keeps theirs, the removed one's is reported.
    assert _apply(tmp_path, ["Bo Muller"], upstream) == ([_id(2)], ["Bo Müller"])
    # Spelled as neither: the folded name fits both, so no iD moves.
    assert _apply(tmp_path, ["Bo  Muller."], upstream) == ([None], ["Bo Müller, Bo Muller"])


def test_an_authors_patch_carry_edge_cases(tmp_path: Path) -> None:
    # Punctuation folds to spaces, so a hyphen fix keeps the iD.
    assert _apply(tmp_path, ["Bo Muller"], [WorkAuthor("Bo-Muller", orcid=_id(4))]) == (
        [_id(4)],
        [],
    )
    # Two people of one name, listed twice: each entry takes its own iD.
    same = [WorkAuthor("Cy Same", orcid=_id(5)), WorkAuthor("Cy Same", orcid=_id(6))]
    assert _apply(tmp_path, ["Cy Same", "Cy Same"], same) == ([_id(5), _id(6)], [])
    # A removed author repeated upstream is named once.
    gone = [WorkAuthor("Bo Colleague", orcid=_id(4)), *[WorkAuthor("Cy Gone", orcid=_id(5))] * 2]
    assert _apply(tmp_path, ["Bo Colleague"], gone) == ([_id(4)], ["Cy Gone"])
    # The configured iD in URL form and the same iD bare upstream are one iD.
    configured = AuthorConfig(name="Ann Member", orcid="9999-0000-0000-0003")
    bare = [
        WorkAuthor("Ann Member", orcid="9999-0000-0000-0003", tracked=True, tracked_as="Ann Member")
    ]
    assert _apply(tmp_path, ["Ann Member"], bare, [configured]) == ([_id(3)], [])


def test_a_configured_id_replacing_an_upstream_one_is_a_drop(tmp_path: Path) -> None:
    configured = AuthorConfig(name="Ann Member", orcid="9999-0000-0000-0001")
    overrides = overrides_from(tmp_path, '- id: W1\n  authors: ["Ann Member"]\n', [configured])
    upstream = [WorkAuthor("Annie Member", orcid=_id(3), tracked=True, tracked_as="Ann Member")]
    kept, _ = apply_overrides([Work(id="W1", title="A", authors=upstream)], overrides)
    assert kept[0].authors[0].orcid == _id(1)
    assert orcid_drops(overrides) == [f"{tmp_path / 'overrides.yml'}: entry 1, W1: Annie Member"]


@pytest.mark.parametrize(
    "field_line, message",
    [
        ("year: '2024'", "'year' must be an integer"),
        ("title: 5", "'title' must be a string"),
        ("is_retracted: 1", "'is_retracted' must be a boolean"),
        ("year: true", "'year' must be an integer"),
        ("cited_by_count: '5'", "'cited_by_count' must be an integer"),
        ("date: 'Nov 2025'", "YYYY-MM-DD"),
    ],
)
def test_load_overrides_rejects_mistyped_values_before_any_match(
    tmp_path: Path, field_line: str, message: str
) -> None:
    # The id matches nothing on purpose: a stale entry must not carry a typo
    # through a successful build.
    with pytest.raises(ConfigError, match=message):
        overrides_from(tmp_path, f"- id: W404\n  {field_line}\n")


def test_apply_overrides_coerces_yaml_date(tmp_path: Path) -> None:
    overrides = overrides_from(tmp_path, "- id: W1\n  date: 2024-03-01\n")
    kept, _ = apply_overrides([Work(id="W1", title="A")], overrides)
    assert kept[0].date == "2024-03-01"


def test_apply_overrides_patched_date_carries_its_year(tmp_path: Path) -> None:
    overrides = overrides_from(tmp_path, "- id: W1\n  date: 2024-03-01\n- id: W2\n  date: null\n")
    works = [
        Work(id="W1", title="A", year=2020, date="2020-01-01"),
        Work(id="W2", title="B", year=2020, date="2020-01-01"),
    ]
    kept, _ = apply_overrides(works, overrides)
    assert [(w.year, w.date) for w in kept] == [(2024, "2024-03-01"), (2020, None)]
    # A contradiction inside one entry fails at load, matched or not.
    with pytest.raises(ConfigError, match="disagrees"):
        overrides_from(tmp_path, "- id: W404\n  date: 2024-03-01\n  year: 2023\n")


def test_apply_overrides_patched_year_must_agree_with_the_kept_date(tmp_path: Path) -> None:
    overrides = overrides_from(
        tmp_path,
        "- id: W1\n  year: 1999\n  date: null\n"  # only the year is known
        "- id: W2\n  year: 2020\n"  # agrees with the fetched date
        "- id: W3\n  year: null\n"  # derived from the fetched date
        "- id: W4\n  year: 1999\n",  # contradicts the fetched date
    )
    works = [
        Work(id="W1", title="A", year=2003, date="2003-01-20"),
        Work(id="W2", title="B", year=2019, date="2020-01-01"),
        Work(id="W3", title="C", year=2019, date="2020-01-01"),
    ]
    kept, _ = apply_overrides(works, overrides[:3])
    assert [(w.year, w.date) for w in kept] == [
        (1999, None),
        (2020, "2020-01-01"),
        (2020, "2020-01-01"),
    ]
    with pytest.raises(ConfigError, match="disagrees with 'date' 2003-01-20 \\(patch 'date' too"):
        apply_overrides([Work(id="W4", title="D", year=2003, date="2003-01-20")], overrides[3:])


def test_mark_keep_distinct(tmp_path: Path) -> None:
    overrides = overrides_from(tmp_path, "- id: W1\n  keep_distinct: true\n")
    works = [Work(id="W1", title="A"), Work(id="W2", title="A")]
    mark_keep_distinct(works, overrides)
    assert works[0].keep_distinct and not works[1].keep_distinct
    # A pin whose record survives must not warn: matched is settled by the
    # patch stage, so that verdict only exists once apply_overrides has run.
    apply_overrides(works, overrides)
    assert unmatched_overrides(overrides) == []


def test_keep_distinct_pin_lost_to_doi_merge_reports_unmatched(tmp_path: Path) -> None:
    """keep_distinct exempts from title clustering only, never from DOI merging.

    When the pinned record loses that merge, the entry's patch cannot apply.
    The build must say so instead of reporting the correction as redundant.
    """
    overrides = overrides_from(
        tmp_path, "- id: W1\n  keep_distinct: true\n  venue: Corrected Venue\n"
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

    kept, _ = apply_overrides(survivors, overrides)
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
