from __future__ import annotations

import json
from pathlib import Path

from erga.model import Work
from erga.output import render, sort_works, write_atomic


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
    text = render(works)
    assert text.endswith("}\n")
    assert "Ψυχοκεραμικά" in text  # ensure_ascii=False
    assert render(list(works)) == text
    data = json.loads(text)
    assert data["schema_version"] == 1
    assert data["works"][0]["id"] == "W1"


def test_write_atomic(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "publications.json"
    write_atomic(target, "content\n")
    assert target.read_text(encoding="utf-8") == "content\n"
    assert [p.name for p in target.parent.iterdir()] == ["publications.json"]
