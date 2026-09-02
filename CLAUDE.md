# erga

Automated publications pipeline for academic websites. One config file lists
authors (ORCID iDs); erga fetches their works from OpenAlex, normalizes and
deduplicates them across registrars, applies the maintainer's curation files,
backfills venues from Crossref, and writes a canonical `publications.json`
for any static site to render. Delivered as a GitHub Action and a CLI.

Design principle: the fetch is disposable, the curated JSON is the durable,
reviewable artifact. Curation (manual additions, per-record overrides,
highlights) lives in separate files that survive every automated refresh.

erga is a contract, not a service (settled 2026-08-11): consumers supply
ORCID iDs, an owned config, reviewed curation and an API key at scale; erga
guarantees deterministic JSON, `verify` as the input-checking handshake, and
schema stability at v1.0. Consumer-side detail — faculty composition, ORCID
coverage, where the site renders it — is theirs, stated as a requirement with
a fallback, never solved inside erga.

## Status

v0.4.0 released 2026-09-02 (PyPI via Trusted Publishing, GitHub
Releases; repo public since v0.1.0, 2026-08-05). The pipeline is
implemented end-to-end (config, fetch, normalize, dedup, curation,
Crossref backfill, deterministic output, `build`/`verify` CLI) with unit
suites plus a byte-exact golden test. Two consumers build with it in CI:
the origin Jekyll lab site (v0.2) and dpsd-new, an Astro department site
whose pilot (5 authors, 228 works, 2026-08-11) shaped the department-scale
intake that v0.4.0 ships: verify separates split profiles from
contaminated ORCIDs by name matching and name-searches for unconfigured
same-name profiles, `output.exclude_types` filters noise types wholesale,
and a work-level contamination check warns about a homonym whose
Latinized name matches, which `verify` cannot see. The check is advisory
and its rule is settled on the one career that could measure recall, so
do not tune it on local data: `docs/requirements-v1.md` section 7 has
the measurements and the three standing caveats. Identity is a line, not
a feature: finding an iD is the consumer's step and the ORCID is trusted
as given (README). Next is the declared home for the check (v0.5.0, work
order in `docs/todo.md`). See `docs/requirements-v1.md` for the v1
design, `docs/action.md` for the Action, and `docs/todo.md` for open
work.

Module map (`src/erga/`): `config` (erga.yml), `http` (injectable transport
+ retry), `openalex`/`crossref` (clients), `normalize` (raw work → canonical
record), `dedup` (DOI + title clustering), `contamination` (homonym works
inside a correct profile), `curation` (manual/overrides/tags), `pipeline`
(stage orchestration), `output` (deterministic JSON), `verify`
(disambiguation report), `cli`. `action.yml` at the root wraps
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
  (v1.0 = the JSON schema is declared stable). Procedure: `docs/release.md`
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
