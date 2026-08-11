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

v0.3.0 released 2026-08-09 (PyPI via Trusted Publishing, GitHub
Releases; repo public since v0.1.0, 2026-08-05): the composite GitHub
Action, the post-dedup override-match fix, unassignable sample ORCIDs.
The pipeline is implemented end-to-end (config, fetch, normalize, dedup,
curation, Crossref backfill, deterministic output, `build`/`verify` CLI)
with unit suites plus a byte-exact golden test. The origin lab site (the
v0.2 milestone) builds its publications with erga in CI. Post-release,
main carries department-scale intake hardening shaped by the consumer #2
scope decisions: verify separates split profiles from contaminated
ORCIDs by name matching, name-searches for unconfigured same-name
profiles, and `output.exclude_types` filters noise types wholesale.
The consumer #2 (dpsd-new, an Astro department site) handoff is routed
(2026-08-11): an adoption brief in `local/`, a pointer in that repo's
inbox. The ball is with the pilot there; findings return via this
repo's `docs/inbox.md`, and the pilot-keyed todo items (authors roster,
review export, recipes doc) wait on them. See `docs/requirements-v1.md`
for the v1 design, `docs/action.md` for the Action, and `docs/todo.md`
for open work.

Module map (`src/erga/`): `config` (erga.yml), `http` (injectable transport
+ retry), `openalex`/`crossref` (clients), `normalize` (raw work → canonical
record), `dedup` (DOI + title clustering), `curation` (manual/overrides/
tags), `pipeline` (stage orchestration), `output` (deterministic JSON),
`verify` (disambiguation report), `cli`. `action.yml` at the root wraps
`uvx erga build`; it holds no logic of its own.

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
  never real contact details. Sample ORCIDs must be unassignable (9999
  prefix): ORCID's fictitious-researcher iD and 0000-0000-0000-0000 are
  both carried by real OpenAlex profiles and fetch strangers' works
- v1 non-goals: no rendering or UI, no Google Scholar scraping, no database,
  no hosted service, no sources beyond OpenAlex + manual entries
- No `.claudeignore`, deliberately: every noise dir is gitignored and CC
  search respects `.gitignore`, so it would duplicate that for no gain
