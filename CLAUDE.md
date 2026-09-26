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

v0.8.0 released 2026-09-26 (PyPI via Trusted Publishing, GitHub
Releases; repo public since v0.1.0, 2026-08-05). The pipeline is
implemented end-to-end (config, fetch, normalize, dedup, curation,
Crossref backfill, deterministic output, `build`/`verify` CLI) with unit
suites plus a byte-exact golden test. Two consumers build with it in CI:
the origin Jekyll lab site (smartmove-site) and dpsd-new, an Astro department site
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
as given (README). The declared home (`home:`, a ROR id, v0.5.0; a list
of them, v0.7.0) tells
the check where an author's career belongs instead of inferring it, which lifts the
majority gate's silence and lets a mostly-elsewhere profile be reported
as wrong rather than accused.
Measured 2026-09-21 on the pinned cohorts (section 7): a declaration
changes no verdict a random career already had and adds no cluster, the
wrong-profile verdict fires on nearly every wrong declaration, and the
silence it was built to lift did not occur once in eighty careers, so
that claim is unobserved, not refuted. The first department cohort with
a real declaration (dpsd-new, nine authors, 2026-09-22) lifted no
silence either and changed one verdict, wrongly: a recent mover, mostly
at a previous employer, is reported as a wrong profile under a correct
declaration. Settled 2026-09-23: a declaration orients one career and
does not check current employment, so a mover's entry lists every post
(`home: [...]`); inferring the move from shared collaborators was
measured and rejected after an independent review found four shapes
where it is wrong. The record is section 7. The probe
cohort is pinned since 2026-09-21 (`local/contamination-probes/`, one
cached file per band, read offline): a before/after claim is valid
against those files and against no earlier figure, since `sample=40&seed=17`
re-drew eight of forty authors within ninety minutes and no earlier
run's cohort was recorded. v0.6.0 ships the build delta (`build
--summary`, `erga diff`, the Action's `summary` input), which turns the
consumer's weekly PR into a reviewable page; its three change classes
and the shrink warning are stage 12 of section 7, settled 2026-09-21
and frozen by a golden test. v0.8.0 adds `verify`'s unlinked bylines:
works naming a member on an authorship with no author id, which no
profile fetch sees, checked against the published list. See `docs/requirements-v1.md`
for the v1 design, `docs/action.md` for the Action, and `docs/todo.md`
for open work.

Module map (`src/erga/`): `config` (erga.yml), `http` (injectable transport
+ retry), `openalex`/`crossref` (clients), `normalize` (raw work → canonical
record), `dedup` (DOI + title clustering), `contamination` (homonym works
inside a correct profile), `curation` (manual/overrides/tags), `pipeline`
(stage orchestration), `output` (deterministic JSON, and the tolerant
reader of the previous file), `delta` (what changed since it, and the
reviewer's page), `verify` (disambiguation report, unlinked bylines), `cli`. `action.yml`
at the root wraps `uvx erga build`; it holds no logic of its own.

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
  no hosted service, no sources beyond OpenAlex + manual entries (ORCID
  may be read as a check, never as a record source: requirements section 12)
- No `.claudeignore`, deliberately: every noise dir is gitignored and CC
  search respects `.gitignore`, so it would duplicate that for no gain
