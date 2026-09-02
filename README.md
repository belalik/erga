# erga

Keep a website's academic publications list current, automatically, without
giving up control of the data.

**Status: alpha (v0.3).** The CLI pipeline works end-to-end and its
output has converged with a production lab site's existing pipeline in a
parallel run against live OpenAlex (187/187 records, zero field diffs).
That site now builds its publications with erga in CI. The JSON schema may
still change before v1.0.

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
- **Delivery**: a pip-installable CLI, or a GitHub Action. One workflow file
  plus one config file is the whole setup.

The name: έργα, "works" — the same term OpenAlex uses for publications.

## Usage

Install with `uv tool install erga` or `pip install erga` (or run one-off
with `uvx erga`). Write an `erga.yml`:

```yaml
mailto: you@example.org          # identifies requests to Crossref/OpenAlex
authors:
  - name: Josiah Carberry
    orcid: 9999-9999-9999-9999   # placeholder: no real iD starts 9999
  - name: Another Person
    openalex_id: A5000000000     # alternative when ORCID is missing/wrong

openalex:
  api_key_env: OPENALEX_API_KEY  # optional; env var name, never the key itself

output:
  path: publications.json
  # exclude_types: [other]       # optional: drop e.g. errata/editorial noise
```

Then:

- `erga build [--config PATH] [--dry-run]` runs the pipeline and writes
  `publications.json`. With `--dry-run` it prints a summary (fetched, merged,
  deduplicated, excluded, backfilled) without writing.
- `erga verify [--config PATH]` prints the author-disambiguation report:
  what each configured author resolves to on OpenAlex, plus a name search
  for same-name profiles the config does not cover. Warnings tell a split
  profile (one person, several ids) apart from an iD carried by strangers,
  and flag resolved profiles whose name does not match the configured
  author, zero-work authors, and implausible works counts. Run it once
  when setting up, and whenever a build looks off.

Run `erga verify` before your first build, because an ORCID does not
reliably identify one person on OpenAlex. The same iD can appear on several
profiles when it has been mistyped or copied into submissions, and erga
tracks all of them, so a wrong iD shows up as a pile of strangers' papers
rather than as an error. The report tells you what you are about to fetch.

`verify` works by comparing names, so the opposite failure is invisible to
it: an iD that is correct, on a profile that has collected a same-name
stranger's works. Two people who Latinize to the same string are one name to
OpenAlex, and re-checking the iD does not help, because the iD is right. So
a verified ORCID means erga fetched the person you meant. It does not mean
every work it returned is theirs. Read the first build against what you
expect, and exclude what does not belong in your overrides file. Where a
career is mostly in one place, `build` also warns about clusters of works
tied to an institution that share no collaborator and no institution with
the rest of the profile, which is what a same-name stranger's works look
like. The warning is advisory; whether to exclude them is your call.

Finding the iD in the first place is your step, and erga does not guess at
it. An ORCID in `erga.yml` is trusted as given. What worked for a department
that had iDs on file for five of sixty-three staff: search OpenAlex under
every Latinization the person has published with, read each candidate's
`last_known_institutions`, confirm the candidate's ORCID against the
employment history on orcid.org, and only then scan the profile for works
that look like someone else's. Name plus institution is not enough on its
own; a same-name stranger can carry your institution on OpenAlex too.

## GitHub Action

The action runs the build and stops there. It writes `publications.json` and
leaves delivery to your workflow, so you compose it with whatever you already
use to commit or open pull requests.

```yaml
- uses: actions/checkout@v5
- uses: belalik/erga@v0.4.0
  with:
    version: "0.4.0"                 # pin explicitly; no default
    config: _data/erga.yml
    api-key: ${{ secrets.OPENALEX_API_KEY }}   # optional
```

Paths inside the config resolve against the config's own directory, so
putting `erga.yml` where the site wants its data is usually the whole
configuration: `_data/erga.yml` writes `_data/publications.json`.

**Recipe 1, commit back inside your build workflow.** The default, and what
the origin site runs. Because the build happens in the same job, it sidesteps
the rule that pushes made with `GITHUB_TOKEN` never trigger another workflow.

```yaml
permissions:
  contents: write

steps:
  - uses: actions/checkout@v5
  - uses: belalik/erga@v0.4.0
    with:
      version: "0.4.0"
      config: _data/erga.yml
      api-key: ${{ secrets.OPENALEX_API_KEY }}
  - run: |
      git config user.name "github-actions[bot]"
      git config user.email "github-actions[bot]@users.noreply.github.com"
      git add _data/publications.json
      git diff --cached --quiet || git commit -m "Update publications"
      git push
  # ...then build and deploy the site as usual, in this same job.
```

**Recipe 2, open a pull request.** The right default when you want a review
gate, and the only clean path on a protected branch. Repeated runs update one
branch and one PR, so quiet weeks produce no noise, and merging is an ordinary
push that fires your deploy workflow.

```yaml
permissions:
  contents: write
  pull-requests: write

steps:
  - uses: actions/checkout@v5
  - uses: belalik/erga@v0.4.0
    with:
      version: "0.4.0"
      config: _data/erga.yml
      api-key: ${{ secrets.OPENALEX_API_KEY }}
  - uses: peter-evans/create-pull-request@v7
    with:
      commit-message: Update publications
      branch: erga/publications
      title: Update publications
```

Inputs, permissions, scheduling and version-pinning notes:
[docs/action.md](docs/action.md).

## Curation

Three optional curation files next to the config survive every refresh:
`manual.yml` (records the APIs miss), `overrides.yml` (per-record patches,
exclusions, dedup exemptions), and `tags.yml` (tag name to DOI/id lists;
tag semantics are entirely yours). The full schema and pipeline design live
in [docs/requirements-v1.md](docs/requirements-v1.md).

## License

MIT
