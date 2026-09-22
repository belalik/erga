from __future__ import annotations

import json
from pathlib import Path

import pytest

from erga.model import Work
from erga.output import document, dump, read_output, sort_works, write_atomic


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
    ],
)
def test_read_output_rejects_files_erga_did_not_write(tmp_path: Path, content: bytes) -> None:
    target = tmp_path / "publications.json"
    target.write_bytes(content)
    assert read_output(target) is None
