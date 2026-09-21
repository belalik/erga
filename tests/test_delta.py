from __future__ import annotations

from typing import Any

from erga.delta import LISTED_CAP, compute_delta, render_markdown
from erga.model import Work, WorkAuthor

# Built through the dataclasses, so a schema change reaches these records.
TRACKED = WorkAuthor("Josiah Carberry", tracked=True, tracked_as="Josiah Carberry").to_json()
COAUTHOR = WorkAuthor("A. Coauthor").to_json()


def record(work_id: str, **overrides: Any) -> dict[str, Any]:
    base = Work(
        id=work_id,
        title=f"Title {work_id}",
        authors=[
            WorkAuthor("Josiah Carberry", tracked=True, tracked_as="Josiah Carberry"),
            WorkAuthor("A. Coauthor"),
        ],
        year=2024,
        date="2024-01-01",
        venue="Journal of Psychoceramics",
        type="journal",
        doi=f"https://doi.org/10.5555/{work_id}",
        cited_by_count=3,
    ).to_json()
    base.update(overrides)
    return base


def test_first_build_has_nothing_to_compare() -> None:
    delta = compute_delta(None, [record("W1")])
    assert delta.first_build
    assert delta.total == 1
    assert delta.warnings() == []
    assert delta.headline() == "first build, 1 work, nothing to compare against"


def test_identical_documents_are_unchanged() -> None:
    delta = compute_delta([record("W1"), record("W2")], [record("W1"), record("W2")])
    assert delta.unchanged
    assert delta.headline() == "no changes, 2 works"


def test_added_and_removed_keep_output_order() -> None:
    previous = [record("W1"), record("W2")]
    current = [record("W3", year=2025), record("W1"), record("W4", year=2023)]
    delta = compute_delta(previous, current)
    assert [w["id"] for w in delta.added] == ["W3", "W4"]
    assert [w["id"] for w in delta.removed] == ["W2"]
    assert delta.headline() == "2 added, 1 removed (2 → 3 works)"


def test_retraction_turning_on_is_listed_turning_off_is_drift() -> None:
    previous = [record("W1"), record("W2", is_retracted=True)]
    current = [record("W1", is_retracted=True), record("W2")]
    delta = compute_delta(previous, current)
    assert [w["id"] for w in delta.retracted] == ["W1"]
    assert delta.field_counts == {"is_retracted": 1}


def test_tracking_change_is_listed_and_byline_drift_is_counted() -> None:
    untracked = {**TRACKED, "tracked": False, "tracked_as": None}
    renamed = {**COAUTHOR, "name": "Alice Coauthor"}
    current = [
        record("W1", authors=[untracked, dict(COAUTHOR)]),
        record("W2", authors=[dict(TRACKED), renamed]),
    ]
    delta = compute_delta([record("W1"), record("W2")], current)
    assert [(w["id"], before) for w, before in delta.retracked] == [("W1", ["Josiah Carberry"])]
    assert delta.field_counts == {"authors": 1}
    assert delta.headline() == (
        "0 added, 0 removed, 1 with tracking changed, 1 field update (2 → 2 works)"
    )
    page = render_markdown(delta, [])
    assert "#### Tracking changed (1)" in page
    assert "Tracked: **nobody**\n  Co-authors: Josiah Carberry, A. Coauthor\n" in page
    assert "Previously tracked: Josiah Carberry" in page


def test_tags_are_curation_not_drift() -> None:
    delta = compute_delta([record("W1")], [record("W1", tags=["featured"])])
    assert delta.tag_changes == 1
    assert delta.field_counts == {}
    assert "Tags changed on 1 work, from your tags file" in render_markdown(delta, [])


def test_field_drift_is_counted_per_field() -> None:
    previous = [record("W1"), record("W2")]
    current = [record("W1", cited_by_count=9, venue="Other"), record("W2", cited_by_count=1)]
    delta = compute_delta(previous, current)
    assert delta.field_counts == {"cited_by_count": 2, "venue": 1}
    assert delta.field_updates == 3


def test_shrink_warning_fires_only_above_a_tenth() -> None:
    previous = [record(f"W{i}") for i in range(20)]
    assert compute_delta(previous, previous[2:]).warnings() == []
    warnings = compute_delta(previous, previous[3:]).warnings()
    assert len(warnings) == 1
    assert warnings[0].startswith("3 of 20 works removed since the previous output")


def test_render_lists_additions_with_the_tell_and_marks_manual() -> None:
    stranger = {"name": "Stranger", "orcid": None, "tracked": False, "tracked_as": None}
    current = [
        record("W1"),
        record("manual-x", source="manual", doi=None, authors=[stranger]),
    ]
    page = render_markdown(compute_delta([record("W1")], current), ["contamination: x"])
    assert page.startswith("### Publications refresh\n\n**1 added, 0 removed (1 → 2 works).**\n")
    assert "**Warnings**\n\n- contamination: x\n" in page
    assert "> **Check the additions before merging.**" in page
    assert "#### Added (1)" in page
    assert "  2024 · Journal of Psychoceramics · journal · manual entry\n" in page
    assert "  Tracked: **nobody**\n  Co-authors: Stranger\n" in page
    assert "#### Removed" not in page
    assert "#### Other changes" not in page


def test_render_first_build_and_no_changes() -> None:
    first = render_markdown(compute_delta(None, [record("W1")]), [])
    assert "**First build, 1 work, nothing to compare against.**" in first
    same = render_markdown(compute_delta([record("W1")], [record("W1")]), [])
    assert same == "### Publications refresh\n\n**No changes, 1 work.**\n"


def test_render_field_table_is_ranked_then_named() -> None:
    previous = [record("W1"), record("W2")]
    current = [record("W1", venue="X", abstract="a"), record("W2", venue="Y", cited_by_count=1)]
    page = render_markdown(compute_delta(previous, current), [])
    table = page.split("| Field | Works affected |\n|---|---|\n")[1].split("\n\n")[0]
    assert table == "| `venue` | 2 |\n| `abstract` | 1 |\n| `cited_by_count` | 1 |"
    assert "_Metadata drift from OpenAlex. Nothing to action._" in page


def test_render_caps_listed_entries_and_says_so() -> None:
    current = [record(f"W{i:04d}") for i in range(LISTED_CAP + 5)]
    page = render_markdown(compute_delta([], current), [])
    assert page.count("\n- **Title") == LISTED_CAP
    assert "_5 more not listed; see the raw diff._" in page


def test_render_caps_coauthors() -> None:
    crowd = [{**COAUTHOR, "name": f"Person {i}"} for i in range(8)]
    page = render_markdown(compute_delta([], [record("W1", authors=[dict(TRACKED), *crowd])]), [])
    assert "Co-authors: Person 0, Person 1, Person 2, Person 3, Person 4, Person 5, +2 more" in page
