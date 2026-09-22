"""End-to-end golden test: fixture config plus recorded responses in,
byte-exact publications.json and change summary out (requirements
section 10)."""

from __future__ import annotations

import shutil
from pathlib import Path

from conftest import FIXTURES, FakeTransport, load_fixture, no_sleep
from erga.config import load_config
from erga.crossref import CrossrefClient
from erga.delta import render_markdown
from erga.openalex import OpenAlexClient
from erga.pipeline import BuildStats, build

GOLDEN = FIXTURES / "golden"


def golden_transport() -> FakeTransport:
    transport = FakeTransport()
    transport.add(
        "api.openalex.org/authors/A5000000002",
        {},
        load_fixture("openalex", "authors-a5000000002.json"),
    )
    transport.add(
        "api.openalex.org/authors",
        {"filter": "orcid:0000-0002-1825-0097"},
        load_fixture("openalex", "authors-orcid.json"),
    )
    transport.add(
        "api.openalex.org/works", {"cursor": "*"}, load_fixture("openalex", "works-page1.json")
    )
    transport.add(
        "api.openalex.org/works",
        {"cursor": "page-two"},
        load_fixture("openalex", "works-page2.json"),
    )
    transport.add(
        "api.crossref.org/works/10.5555%2Fcracked", {}, load_fixture("crossref", "cracked.json")
    )
    transport.add(
        "api.crossref.org/works/10.5281%2Fzenodo.7777", {}, {"status": "error"}, status=404
    )
    return transport


def run_golden(
    tmp_path: Path,
    *,
    dry_run: bool = False,
    seed: bool = True,
    transport: FakeTransport | None = None,
) -> BuildStats:
    if seed:
        for name in ("erga.yml", "manual.yml", "overrides.yml", "tags.yml"):
            shutil.copy(GOLDEN / name, tmp_path / name)
        shutil.copy(GOLDEN / "previous-publications.json", tmp_path / "publications.json")

    transport = transport or golden_transport()
    config = load_config(tmp_path / "erga.yml")
    openalex = OpenAlexClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep)
    crossref = CrossrefClient(transport, mailto=config.mailto, delay=0.0, sleep=no_sleep)
    return build(config, openalex, crossref, dry_run=dry_run)


def test_golden_build_byte_exact(tmp_path: Path) -> None:
    stats = run_golden(tmp_path)
    produced = (tmp_path / "publications.json").read_bytes()
    expected = (GOLDEN / "expected-publications.json").read_bytes()
    assert produced == expected

    assert stats.fetched == 10  # W1003 arrives on both pages, counted once
    assert stats.manual == 2
    assert stats.deduplicated == 2  # W1002 into W1001, W1005 into manual entry
    assert stats.excluded == 1  # W1007
    assert stats.backfilled_previous == 1  # W1010 via the ratchet
    assert stats.backfilled_crossref == 1  # W1003
    assert stats.total == 9
    assert stats.warnings == []
    assert stats.written


def test_golden_summary_byte_exact(tmp_path: Path) -> None:
    stats = run_golden(tmp_path)
    produced = render_markdown(stats.delta, stats.warnings)
    expected = (GOLDEN / "expected-summary.md").read_text(encoding="utf-8")
    assert produced == expected
    assert stats.delta.headline() == (
        "8 added, 0 removed, 1 with tracking changed, 6 field updates, 1 tag change (1 → 9 works)"
    )


def test_golden_build_is_idempotent(tmp_path: Path) -> None:
    run_golden(tmp_path)
    first = (tmp_path / "publications.json").read_bytes()
    # Second run: previous output is now the first run's file, so both
    # already-backfilled venues come from the ratchet without Crossref.
    stats = run_golden(tmp_path, seed=False)
    assert (tmp_path / "publications.json").read_bytes() == first
    assert stats.backfilled_previous == 2  # W1010 and W1003 both known now
    assert stats.backfilled_crossref == 0
    assert stats.delta.unchanged


def test_golden_build_warns_about_an_unreadable_previous_output(tmp_path: Path) -> None:
    for name in ("erga.yml", "manual.yml", "overrides.yml", "tags.yml"):
        shutil.copy(GOLDEN / name, tmp_path / name)
    (tmp_path / "publications.json").write_bytes(b"[]")
    # With no ratchet, W1010's venue comes from Crossref instead.
    transport = golden_transport()
    transport.add(
        "api.crossref.org/works/10.5555%2Fteacup",
        {},
        {"message": {"container-title": ["Teacup Quarterly"]}},
    )
    stats = run_golden(tmp_path, seed=False, transport=transport)
    # Never an abort: the file is replaced by a correct one, but the reviewer
    # is told the comparison and the ratchet had nothing to work from.
    assert (tmp_path / "publications.json").read_bytes() == (
        GOLDEN / "expected-publications.json"
    ).read_bytes()
    assert stats.delta.first_build
    assert stats.backfilled_previous == 0
    assert stats.warnings == [
        f"{tmp_path / 'publications.json'}: not a publications.json erga can read; "
        "treated as a first build, so nothing was compared or ratcheted"
    ]


def test_golden_dry_run_leaves_output_untouched(tmp_path: Path) -> None:
    stats = run_golden(tmp_path, dry_run=True)
    assert not stats.written
    assert stats.total == 9
    previous = (GOLDEN / "previous-publications.json").read_bytes()
    assert (tmp_path / "publications.json").read_bytes() == previous
