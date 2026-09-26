from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from erga.model import Work, WorkAuthor
from erga.output import document, dump, read_output, sort_works, work_from_record, write_atomic


def test_work_from_record_inverts_to_json(tmp_path: Path) -> None:
    work = Work(
        id="W1",
        title="Ψυχοκεραμικά",
        authors=[WorkAuthor(name="Priya Nair", orcid=None, tracked=True, tracked_as="Priya Nair")],
        year=2024,
        date="2024-03-01",
        venue="Some Venue",
        type="conference",
        doi="https://doi.org/10.5555/x",
        cited_by_count=7,
        abstract="An abstract.",
        open_access_url="https://example.org/x.pdf",
        tags=["featured"],
        is_retracted=True,
        source="manual",
    )
    path = tmp_path / "publications.json"
    path.write_text(dump(document([work])), encoding="utf-8")
    records = read_output(path)
    assert records is not None
    assert work_from_record(records[0]) == work
    # An older schema's missing keys take the defaults.
    assert work_from_record({"id": "W2", "title": "T"}) == Work(id="W2", title="T")


def test_sort_year_desc_then_id_with_nulls_last() -> None:
    works = [
        Work(id="W2", title="B", year=2024),
        Work(id="W1", title="A", year=2024),
        Work(id="W3", title="C", year=2025),
        Work(id="manual-x", title="D", year=None),
    ]
    assert [w.id for w in sort_works(works)] == ["W3", "W1", "W2", "manual-x"]


def test_render_is_deterministic_utf8_with_trailing_newline() -> None:
    works = [Work(id="W1", title="Ψυχοκεραμικά")]
    text = dump(document(works))
    assert text.endswith("}\n")
    assert "Ψυχοκεραμικά" in text  # ensure_ascii=False
    assert dump(document(list(works))) == text
    data = json.loads(text)
    assert data["schema_version"] == 1
    assert data["works"][0]["id"] == "W1"


def test_write_atomic(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "publications.json"
    write_atomic(target, "content\n")
    assert target.read_text(encoding="utf-8") == "content\n"
    assert [p.name for p in target.parent.iterdir()] == ["publications.json"]


def test_write_atomic_mode_follows_umask_then_the_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "publications.json"
    previous = os.umask(0o027)
    try:
        write_atomic(target, "first\n")
        assert stat.S_IMODE(target.stat().st_mode) == 0o640  # not mkstemp's 0600
        target.chmod(0o604)
        write_atomic(target, "second\n")
        assert stat.S_IMODE(target.stat().st_mode) == 0o604
    finally:
        os.umask(previous)


def test_read_output_returns_the_records_of_a_file_erga_wrote(tmp_path: Path) -> None:
    target = tmp_path / "publications.json"
    target.write_text(dump(document([Work(id="W1", title="t")])), encoding="utf-8")
    records = read_output(target)
    assert records is not None
    assert [r["id"] for r in records] == ["W1"]
    assert read_output(tmp_path / "missing.json") is None


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"[]",
        b'{"works": {}}',
        # A work that is not a mapping: dropping it would pass a truncated or
        # hand-edited file off as a real, smaller output.
        b'{"works": [null]}',
        # A byline that is not a list of mappings would crash the delta.
        b'{"works": [{"id": "W1", "authors": [1]}]}',
        b'{"works": [{"id": "W1", "authors": {"name": "x"}}]}',
        # Fields verify reads back into a record, in shapes erga never writes.
        b'{"works": [{"id": "W1", "open_access": "https://example.org/w1"}]}',
        b'{"works": [{"id": "W1", "title": ["t"]}]}',
        b'{"works": [{"id": "W1", "tags": 3}]}',
    ],
)
def test_read_output_rejects_files_erga_did_not_write(tmp_path: Path, content: bytes) -> None:
    target = tmp_path / "publications.json"
    target.write_bytes(content)
    assert read_output(target) is None
