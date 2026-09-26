# erga

Keep a website's academic publications list current, automatically, without
giving up control of the data.

## In short

**The problem.** A lab or department site's publications page is either
maintained by hand, and rots, or handed to an embed or a scraper, and then
the data is not yours.

**What erga does.** You list your people's ORCID iDs in one config file.
It fetches their works from OpenAlex, deduplicates them across registrars,
applies your corrections, and writes one `publications.json` into your
repository. CI refreshes it on a schedule; your site (Jekyll, Astro, Hugo,
anything) renders it however it likes. Your manual additions, exclusions
and highlights live in their own files and survive every refresh.

**What it is not.** It renders nothing, scrapes nothing and hosts nothing.
A hosted embed puts the list in someone else's JavaScript, outside your
HTML, your git history and your review; Google Scholar has no API and its
terms forbid scraping it.

**Where it stands.** It grew out of one lab site's embedded script and now
builds two sites in CI, a lab and a department. The JSON schema may still
change before 1.0.

## What it does

- **Curation that survives refresh**: manual additions, per-record overrides,
  and highlights live in their own files and are re-applied on every
  automated run.
- **Identity checks**: `verify` reports what each iD resolves to before you
  fetch, and the build warns about clusters of works that look like a
  same-name stranger's.
- **Proper APIs, no scraping**: OpenAlex (CC0 data) plus Crossref venue
  backfill, with API etiquette built in (keys, delays, retries).
- **Git-owned data**: the output is a diffable, PR-reviewable file in your
  repo: no hosted embed, no runtime dependency, publications present in the
  initial HTML.
- **Delivery**: a pip-installable CLI, or a GitHub Action. One workflow file
  plus one config file is the whole setup.

The name: έργα, "works" — the same term OpenAlex uses for publications.

## Quick start

Install with `uv tool install erga` or `pip install erga` (or run one-off
with `uvx erga`). Write an `erga.yml`:

```yaml
mailto: you@example.org          # identifies requests to Crossref/OpenAlex
# home: https://ror.org/...      # optional: where these careers belong (ROR id or list)
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

- `erga build [--config PATH] [--dry-run] [--summary PATH]` runs the
  pipeline and writes `publications.json`. With `--dry-run` it prints a
  summary (fetched, merged, deduplicated, excluded, backfilled) without
  writing the JSON. Every build says in one line what changed since the
  output it found in place; `--summary` also writes that as a Markdown page
  for a reviewer, with additions and removals listed and metadata drift
  counted.
- `erga diff OLD NEW` prints the same page for any two output files.
- `erga verify [--config PATH]` prints the author-disambiguation report:
  what each configured author resolves to on OpenAlex, plus a name search
  for same-name profiles the config does not cover. Warnings tell a split
  profile (one person, several ids) apart from an iD carried by strangers,
  and flag resolved profiles whose name does not match the configured
  author, zero-work authors, and implausible works counts. Run it once
  when setting up, and whenever a build looks off.

## Getting the identities right

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

That check works out where "one place" is by counting, which goes quiet on
anyone whose record is scattered across places. Setting `home:` to your
institution's ROR id tells it instead, for everyone in the file or per
author, and then it can also tell you that a profile is mostly somebody
else's work rather than listing that majority as strangers. Someone who
joined recently has most of their record at a previous employer, so give
them a list, `home: [<your ROR>, <their previous ROR>]`, or the check will
read their career as someone else's. A thin record
stays quiet whoever declares it. It is only ever
read by this check: like the ORCID, a declared home is trusted as given and
is never treated as evidence that a profile is the right person.

The reverse gap, a work that is theirs but never arrives, is what the last
lines of each author's `verify` entry are for. OpenAlex sometimes prints a
name in a byline without linking it to any profile, and no fetch by profile
can see that work. Once a build has written `publications.json`, `verify`
searches bylines for each configured name and alias, drops whatever the
list already holds by id, DOI or title (a title of 12 characters or more,
as dedup requires), and lists the rest: add the ones
that are theirs to your manual file. A work your overrides exclude stays
out. It also names a listed copy that lacks a DOI when a record carrying
one exists, and a listed work that does not credit them because its
byline prints their name another way ("Nair, Priya"): an alias spelling
that byline, or an override patching the record's authors, credits them. A full name matches only bylines
that spell it out, in any order; an initial alias such as `P. Nair` catches
the initial-only ones too, along with every namesake that shares the
initial. Write a name with its diacritics, as bylines print it: the search
also tries it without them, but cannot restore accents a configured name
lacks. A name too common to judge is skipped with a count.

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
- uses: belalik/erga@v0.8.0
  with:
    version: "0.8.0"                 # pin explicitly; no default
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
  - uses: belalik/erga@v0.8.0
    with:
      version: "0.8.0"
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
push that fires your deploy workflow. The `summary` page becomes the PR body,
so the review is a skim of what changed rather than a diff GitHub may refuse
to render.

```yaml
permissions:
  contents: write
  pull-requests: write

steps:
  - uses: actions/checkout@v5
  - uses: belalik/erga@v0.8.0
    with:
      version: "0.8.0"
      config: _data/erga.yml
      api-key: ${{ secrets.OPENALEX_API_KEY }}
      summary: ${{ runner.temp }}/publications-summary.md
  - uses: peter-evans/create-pull-request@v7
    with:
      add-paths: _data/publications.json
      commit-message: Update publications
      branch: erga/publications
      title: Update publications
      body-path: ${{ runner.temp }}/publications-summary.md
```

Inputs, permissions, scheduling and version-pinning notes:
[docs/action.md](docs/action.md).

## Curation

Three optional curation files next to the config survive every refresh:
`manual.yml` (records the APIs miss), `overrides.yml` (per-record patches,
exclusions, dedup exemptions), and `tags.yml` (tag name to DOI/id lists;
tag semantics are entirely yours). The full schema and pipeline design live
in [docs/requirements-v1.md](docs/requirements-v1.md).

## Author

Thomas Kogias ([kogias.org](https://kogias.org)). Built for the SmartMove
lab site at the University of the Aegean, which has run it since August
2026.

## License

MIT
