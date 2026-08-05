"""Console entry point: `erga build` and `erga verify`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from erga import __version__
from erga.config import Config, load_config
from erga.crossref import CrossrefClient
from erga.errors import ErgaError
from erga.http import UrlTransport
from erga.openalex import OpenAlexClient
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


def _run_build(config: Config, dry_run: bool) -> int:
    openalex, crossref = _clients(config)
    stats = build(config, openalex, crossref, dry_run=dry_run)
    _print_warnings(stats.warnings)
    if dry_run:
        print(f"dry run: {stats.summary()}")
        print(f"would write {stats.total} works to {config.output_path}")
    else:
        print(f"wrote {config.output_path} ({stats.total} works)")
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
        "--dry-run", action="store_true", help="print a summary without writing"
    )

    verify_parser = subparsers.add_parser("verify", help="author-disambiguation report")
    verify_parser.add_argument("--config", type=Path, default=Path("erga.yml"))

    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "build":
            return _run_build(config, args.dry_run)
        return _run_verify(config)
    except ErgaError as exc:
        print(f"erga: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
