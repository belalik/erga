# erga

Keep a website's academic publications list current, automatically, without
giving up control of the data.

**Status: early development.** Nothing is usable yet; v0.1 will be the first
end-to-end release.

## What it will do

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
- **Delivery**: a GitHub Action (weekly cron + on push) and a pip-installable
  CLI.

The name: έργα, "works" — the same term OpenAlex uses for publications.

## License

MIT
