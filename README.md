# erga

Keep a website's academic publications list current, automatically, without
giving up control of the data.

**Status: alpha (v0.1).** The CLI pipeline works end-to-end and its
output has converged with a production lab site's existing pipeline in a
parallel run against live OpenAlex (187/187 records, zero field diffs).
The JSON schema may still change before v1.0.

## What it does

You list your authors (ORCID iDs) in one config file. erga fetches their works
from OpenAlex, normalizes and deduplicates them across registrars (arXiv,
Zenodo, publisher records), applies your curation files, and writes a
canonical `publications.json` into your site repository. Your site (Jekyll,
Astro, Hugo, anything) renders it however it likes.

- **Curation that survives refresh**: manual additions, per-record overrides,
  and highlights live in their own files and are re-applied on every
  automated run.
- **Proper APIs, no scraping**: OpenAlex (CC0 data) plus Crossref venue
  backfill, with API etiquette built in (keys, delays, retries).
- **Git-owned data**: the output is a diffable, PR-reviewable file in your
  repo: no hosted embed, no runtime dependency, publications present in the
  initial HTML.
- **Delivery**: a pip-installable CLI today; GitHub Action packaging is
  planned once the CLI is proven on consumer sites.

The name: έργα, "works" — the same term OpenAlex uses for publications.

## Usage

Install with `uv tool install erga` or `pip install erga` (or run one-off
with `uvx erga`). Write an `erga.yml`:

```yaml
mailto: you@example.org          # identifies requests to Crossref/OpenAlex
authors:
  - name: Josiah Carberry
    orcid: 0000-0002-1825-0097
  - name: Another Person
    openalex_id: A5000000000     # alternative when ORCID is missing/wrong

openalex:
  api_key_env: OPENALEX_API_KEY  # optional; env var name, never the key itself

output:
  path: publications.json
```

Then:

- `erga build [--config PATH] [--dry-run]` runs the pipeline and writes
  `publications.json`. With `--dry-run` it prints a summary (fetched, merged,
  deduplicated, excluded, backfilled) without writing.
- `erga verify [--config PATH]` prints the author-disambiguation report:
  what each configured author resolves to on OpenAlex, with warnings for
  split profiles, zero-work authors, and implausible works counts. Run it
  once when setting up, and whenever a build looks off.

Three optional curation files next to the config survive every refresh:
`manual.yml` (records the APIs miss), `overrides.yml` (per-record patches,
exclusions, dedup exemptions), and `tags.yml` (tag name to DOI/id lists;
tag semantics are entirely yours). The full schema and pipeline design live
in [docs/requirements-v1.md](docs/requirements-v1.md).

## License

MIT
