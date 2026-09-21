from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from conftest import FIXTURES
from erga import cli
from erga.delta import Delta
from erga.pipeline import BuildStats

GOLDEN = FIXTURES / "golden"
PREVIOUS = str(GOLDEN / "previous-publications.json")
EXPECTED = str(GOLDEN / "expected-publications.json")


def test_diff_prints_the_summary(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["diff", PREVIOUS, EXPECTED]) == 0
    out = capsys.readouterr().out
    assert out.startswith("### Publications refresh\n\n**8 added, 0 removed")
    assert "#### Added (8)" in out


def test_diff_treats_a_missing_old_file_as_first_build(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["diff", str(tmp_path / "none.json"), EXPECTED]) == 0
    assert "**First build, 9 works, nothing to compare against.**" in capsys.readouterr().out


def test_diff_rejects_an_unreadable_file_on_either_side(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_bytes(b"[]")
    assert cli.main(["diff", PREVIOUS, str(bad)]) == 1
    assert "not a publications.json" in capsys.readouterr().err
    # An OLD that exists but cannot be read is a mistake, not a first build.
    assert cli.main(["diff", str(bad), EXPECTED]) == 1
    assert "not a publications.json" in capsys.readouterr().err


def test_build_writes_the_summary_even_on_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    shutil.copy(GOLDEN / "erga.yml", tmp_path / "erga.yml")
    stats = BuildStats(total=1, warnings=["something to see"], delta=Delta(total=1))
    monkeypatch.setattr(cli, "_clients", lambda config: (None, None))
    monkeypatch.setattr(cli, "build", lambda *args, **kwargs: stats)
    summary = tmp_path / "summary.md"
    argv = ["build", "--config", str(tmp_path / "erga.yml"), "--dry-run", "--summary", str(summary)]
    assert cli.main(argv) == 0
    page = summary.read_text(encoding="utf-8")
    assert page.startswith("### Publications refresh\n")
    assert "- something to see" in page
    assert not (tmp_path / "publications.json").exists()
    out = capsys.readouterr().out
    assert "since previous output: first build, 1 work, nothing to compare against" in out
    assert f"wrote {summary}" in out
