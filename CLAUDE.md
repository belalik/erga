# erga

Automated publications pipeline for academic websites. One config file lists
authors (ORCID iDs); erga fetches their works from OpenAlex, normalizes and
deduplicates them across registrars, applies the maintainer's curation files,
backfills venues from Crossref, and writes a canonical `publications.json`
for any static site to render. Delivered as a GitHub Action and a CLI.

Design principle: the fetch is disposable, the curated JSON is the durable,
reviewable artifact. Curation (manual additions, per-record overrides,
highlights) lives in separate files that survive every automated refresh.

## Status

v0.2.0 released 2026-08-08 (PyPI via Trusted Publishing, GitHub
Releases; repo public since v0.1.0, 2026-08-05). The pipeline is
implemented end-to-end (config, fetch, normalize, dedup, curation,
Crossref backfill, deterministic output, `build`/`verify` CLI) with unit
suites plus a byte-exact golden test. The v0.2 milestone landed
2026-08-05: the origin lab site builds its publications with erga in CI,
after a parallel run to full convergence (187/187 records). 0.2.0
carries the first consumer-feedback changes: abstract entity/tag cleanup
and `authors[].tracked_as`. Next up is v0.3 (GitHub Action packaging,
second consumer site). See `docs/requirements-v1.md` for the v1 design
and `docs/todo.md` for open work.

Module map (`src/erga/`): `config` (erga.yml), `http` (injectable transport
+ retry), `openalex`/`crossref` (clients), `normalize` (raw work → canonical
record), `dedup` (DOI + title clustering), `curation` (manual/overrides/
tags), `pipeline` (stage orchestration), `output` (deterministic JSON),
`verify` (disambiguation report), `cli`.

## Commands

- `uv sync`: install the dev environment
- `uv run pytest`: run tests
- `uv run ruff check` / `uv run ruff format`: lint / format
- `uv run mypy`: type-check (strict)

## Layout

- `src/erga/`: package source (src layout)
- `tests/`: pytest suite; fixtures are handcrafted records plus recorded
  OpenAlex responses (synthetic or CC0 data only, never real curated
  personal data)
- `docs/`: design docs and `todo.md`
- `local/`: gitignored scratch space (session notes, reference material).
  Session continuity lives here: `local/next-session-prompt.md`, never a
  tracked `feedback/` — public-from-commit-1 discipline, no session state
  in the repo or its history

## Conventions

- Python ≥ 3.10; CI runs the matrix 3.10–3.13 on GitHub Actions
- uv manages the environment and lockfile; ruff lints and formats; mypy is
  strict; all four checks must pass in CI
- Releases: GitHub Releases only, no CHANGELOG file; semver from 0.x
  (v1.0 = the JSON schema is declared stable)
- PyPI publishing via Trusted Publishing (OIDC) from a release workflow;
  no stored tokens
- Config samples, docs, and fixtures use placeholder mailto/ORCID values,
  never real contact details
- v1 non-goals: no rendering or UI, no Google Scholar scraping, no database,
  no hosted service, no sources beyond OpenAlex + manual entries
