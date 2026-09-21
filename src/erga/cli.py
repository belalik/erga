"""Console entry point: `erga build`, `erga verify` and `erga diff`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from erga import __version__
from erga.config import Config, load_config
from erga.crossref import CrossrefClient
from erga.delta import compute_delta, render_markdown
from erga.errors import ErgaError
from erga.http import UrlTransport
from erga.openalex import OpenAlexClient
from erga.output import read_output, write_atomic
from erga.pipeline import build
from erga.verify import verify_report


def _user_agent(mailto: str) -> str:
    return f"erga/{__version__} (https://github.com/belalik/erga; mailto:{mailto})"


def _clients(config: Config) -> tuple[OpenAlexClient, CrossrefClient]:
    # One transport for both APIs. The key never touches disk: read from the
    # configured env var, passed as a query parameter, nothing else. The
    # transport redacts it from network-error text (requests embeds the full
    # request URL in its exception messages).
    api_key = os.environ.get(config.api_key_env) or None
    if not api_key:
        print(
            f"erga: note: {config.api_key_env} not set; using OpenAlex's keyless per-IP quota",
            file=sys.stderr,
        )
    transport = UrlTransport(_user_agent(config.mailto), secrets=[api_key] if api_key else [])
    return (
        OpenAlexClient(transport, mailto=config.mailto, api_key=api_key),
        CrossrefClient(transport, mailto=config.mailto),
    )


def _print_warnings(warnings: list[str]) -> None:
    for warning in warnings:
        print(f"erga: warning: {warning}", file=sys.stderr)


def _run_build(config: Config, dry_run: bool, summary: Path | None) -> int:
    openalex, crossref = _clients(config)
    stats = build(config, openalex, crossref, dry_run=dry_run)
    _print_warnings(stats.warnings)
    if dry_run:
        print(f"dry run: {stats.summary()}")
        print(f"would write {stats.total} works to {config.output_path}")
    else:
        print(f"wrote {config.output_path} ({stats.total} works)")
    print(f"since previous output: {stats.delta.headline()}")
    # Written under --dry-run too: the flag asks for this one file
    # explicitly, and the delta is what a dry run exists to show.
    if summary is not None:
        write_atomic(summary, render_markdown(stats.delta, stats.warnings))
        print(f"wrote {summary}")
    return 0


def _read_output_or_fail(path: Path, *, missing_ok: bool) -> list[dict[str, Any]] | None:
    """The tolerant reader, made strict for a file the user named.

    A missing OLD is a first build; a file that exists and cannot be read
    is a mistake to report, on either side.
    """
    records = read_output(path)
    if records is None and (path.exists() or not missing_ok):
        raise ErgaError(f"{path}: not a publications.json erga can read")
    return records


def _run_diff(old: Path, new: Path) -> int:
    previous = _read_output_or_fail(old, missing_ok=True)
    current = _read_output_or_fail(new, missing_ok=False)
    assert current is not None
    delta = compute_delta(previous, current)
    print(render_markdown(delta, delta.warnings()), end="")
    return 0


def _run_verify(config: Config) -> int:
    openalex, _ = _clients(config)
    report, warnings = verify_report(config, openalex)
    print(report, end="")
    _print_warnings(warnings)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="erga",
        description="Keep a website's academic publications list current.",
    )
    parser.add_argument("--version", action="version", version=f"erga {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="run the pipeline and write the JSON")
    build_parser.add_argument("--config", type=Path, default=Path("erga.yml"))
    build_parser.add_argument(
        "--dry-run", action="store_true", help="print a summary without writing the JSON"
    )
    build_parser.add_argument(
        "--summary",
        type=Path,
        help="also write a Markdown summary of what changed since the previous output",
    )

    verify_parser = subparsers.add_parser("verify", help="author-disambiguation report")
    verify_parser.add_argument("--config", type=Path, default=Path("erga.yml"))

    diff_parser = subparsers.add_parser(
        "diff", help="summarise what changed between two publications.json files"
    )
    diff_parser.add_argument("old", type=Path, help="the previous output; may not exist yet")
    diff_parser.add_argument("new", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "diff":
            return _run_diff(args.old, args.new)
        config = load_config(args.config)
        if args.command == "build":
            return _run_build(config, args.dry_run, args.summary)
        return _run_verify(config)
    except ErgaError as exc:
        print(f"erga: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
