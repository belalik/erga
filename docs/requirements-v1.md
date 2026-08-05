# erga v1 Requirements

Status: adopted 2026-08-03. Maintained as a living spec: current state only,
superseded content is replaced rather than appended. Product identity and
scope were fixed at kickoff; this document records the research-backed design
decisions and the concrete v1 surface. Sources: OpenAlex API documentation and live API
verification (2026-08-03), CSL-JSON schema analysis, GitHub Action delivery
research, and an audit of the origin pipeline (a production Jekyll lab site
that this tool generalizes).

## 1. Purpose

erga keeps a website's academic publications list current while the
maintainer stays in control of the data. One config file lists authors
(ORCID iDs). The tool fetches their works from OpenAlex, normalizes and
deduplicates them, applies curation files that survive every refresh,
backfills missing venues from Crossref, and writes a canonical
`publications.json` into the site repository. The site renders it however it
likes; erga renders nothing.

The fetch is disposable. The curated JSON is the durable, reviewable
artifact.

## 2. Decisions on the kickoff open questions

### 2.1 Canonical schema: own minimal JSON, with emitters later

CSL-JSON was evaluated as a candidate canonical format and rejected:

- Five fields this tool needs most have no first-class CSL-JSON home:
  open-access URL, citation count, ORCID on author names (the name schema
  forbids extra properties), keyword arrays (CSL `keyword` is a single
  string), and curation flags. All would land in the unstructured `custom`
  bag.
- No `preprint` item type exists in CSL 1.0.2.
- CSL dates are `date-parts` nested arrays; Jekyll, Astro, and Hugo
  templates all want plain ISO strings and would each need glue code.
- The Jekyll academic ecosystem (jekyll-scholar, al-folio) consumes BibTeX,
  not CSL-JSON, so canonical CSL-JSON would buy no adoption there anyway.
- OpenAlex offers no native CSL-JSON output and no reusable mapping library
  exists in Python, so the mapping is hand-written under either choice.

Decision: a purpose-built minimal schema (section 4) is canonical.
CSL-JSON and BibTeX emitters come after v0.1 as strategic outputs that turn
the existing theme ecosystem into potential adopters. v1.0 means the
canonical schema is declared stable.

### 2.2 Featured/tags: generalize to tags

The origin pipeline had a `featured` boolean fed by a flat DOI list. v1
generalizes this to a single mechanism: every record carries `tags`
(list of strings), and a curation file maps tag names to DOI/id lists.
Manual entries may declare their own tags inline. Tag names carry no
semantics for erga: sites decide what a tag means and whether it exists at
all. A "featured" highlight list is one pattern a site can implement (the
origin site does); the docs present it as an example, never a default.

### 2.3 Action output mode: compose, do not embed

Research across comparable data-updating Actions shows two viable patterns:
built-in output-mode switches (lowlighter/metrics) and composition with
single-purpose commit/PR actions (the dominant pattern for thin tool
wrappers). Decision: the erga Action only produces the output file and
exits. Delivery is composed in the user's workflow, and the docs ship two
copy-paste recipes:

1. Commit-back inside the site's existing build workflow (default recipe):
   run erga, commit the JSON if changed, then build and deploy in the same
   run. Production-proven by the origin site; sidesteps the GITHUB_TOKEN
   restriction that bot pushes never trigger downstream workflows, because
   the build happens in the same workflow.
2. Pull-request mode (cautious recipe): peter-evans/create-pull-request.
   Repeated runs update one branch and PR; quiet weeks produce no noise;
   merges are normal pushes so separately-triggered deploy workflows fire.
   Right default for maintainers who want a review gate, and the only clean
   path for protected branches.

Workflow guidance the docs must include: declare `permissions` explicitly,
use a concurrency group, schedule cron off the top of the hour, and note
GitHub's 60-day auto-disable of scheduled workflows on inactive repos.

### 2.4 Department scale: batching, cursor pagination, cost budget

For 10 to 100 authors and thousands of works per run:

- Batch authors with the OR-pipe filter (`author.id:A1|A2|...`), at most
  100 values per filter, and deduplicate fetched works by OpenAlex id
  (co-authored works arrive once per matching batch).
- `per-page=100` with cursor pagination (`cursor=*`, then
  `meta.next_cursor`). Basic paging caps at 10,000 results; cursor does not.
  The live API still accepts `per-page=200` but the documented maximum is
  100; the spec uses 100.
- Trim payloads with `select=` (root-level fields only).
- Cost: a 100-author department at roughly 10,000 works is on the order of
  100 to 200 list calls per run, about $0.02 against the $1/day allowance of
  a free API key. A small lab fits even the keyless $0.10/day allowance.
  Runtime is bounded by politeness delays, not data volume.

## 3. OpenAlex operational facts (verified 2026-08-03)

The landscape changed materially in 2025-2026; these facts supersede the
founding documents where they conflict.

- **API keys are the access model** (since 2026-02-13). The mailto "polite
  pool" no longer affects OpenAlex rate limits. Free key: $1/day usage
  allowance. Keyless: $0.10/day. List/filter calls cost $0.0001. Verified
  live: keyless requests succeed and return `x-ratelimit-limit-usd: 0.1`
  headers. Hard throttle 100 req/s. The key is passed as `api_key` query
  parameter; erga reads it from an env var and must never write it to disk.
  Keyless quota can only be tracked per IP, and GitHub-hosted runners share
  IPs, so CI runs must not rely on the keyless allowance; the Action docs
  treat a free key as required setup.
  Crossref, unlike OpenAlex, still operates a mailto polite pool, so the
  config mailto remains first-class for the venue-backfill stage.
- **XPAC subset**: the Nov 2025 backend rewrite added ~190M works (DataCite,
  institutional repositories) that are excluded from queries by default;
  `include_xpac=true` opts in, and works carry an `is_xpac` field (verified
  live). Default off in erga, configurable, because XPAC metadata quality is
  explicitly lower and a publications page wants precision over recall.
  Revisit with department-scale evidence.
- **Type vocabulary drifts**: a July 2026 reclassification changed `type` on
  ~10% of the catalog and added `software` and `software-paper`; the
  classifier re-runs daily. `type_crossref` and `raw_type` are absent from
  live responses (verified). Consequence: rely on `type` alone, expect
  drift, and treat the overrides file as the stability mechanism for
  records a site cares about.
- **OpenAlex already merges many cross-registrar copies**: a single work can
  carry multiple `locations[]` (publisher, DOAJ, Zenodo deposits) with the
  top-level DOI pointing at the published version (verified live on a work
  with 5 locations). erga's own dedup remains necessary for what OpenAlex
  misses, for manual entries, and as a guard, but it is a second line of
  defense rather than the only one.
- **Abstracts** still arrive as `abstract_inverted_index`; standard
  positional reconstruction is unchanged. Coverage is uneven and skews
  recent.
- **Authorships** carry `author.id`, `display_name`, `orcid`, plus
  `raw_author_name`; only ~30% of recent works have publisher-asserted
  ORCID data, so ORCID cannot be the only identity signal. `is_retracted`
  is available and reliable (Retraction Watch data).

## 4. Canonical output schema

Top-level object, not a bare array, so the schema version has a home:

```json
{
  "schema_version": 1,
  "works": [ ... ]
}
```

Per work, all keys always present:

| field | type | notes |
|---|---|---|
| `id` | string | OpenAlex work id without host (`"W4406028178"`), or `"manual-<slug>"` |
| `title` | string | |
| `authors` | array | `{ "name": str, "orcid": str\|null, "tracked": bool }`; `tracked` = matches a configured author by resolved OpenAlex id, ORCID, or name/alias |
| `year` | int \| null | |
| `date` | string \| null | ISO publication date `"2026-01-15"` |
| `venue` | string \| null | null when unknown (origin pipeline used `""`) |
| `type` | string | `journal`, `conference`, `book`, `book-chapter`, `thesis`, `preprint`, `dataset`, `software`, `other` |
| `doi` | string \| null | full `https://doi.org/...` URL |
| `cited_by_count` | int | |
| `abstract` | string \| null | reconstructed plaintext |
| `open_access` | object \| null | `{ "url": str }`; object form leaves room for license/version later |
| `tags` | array of string | from the tags curation file and manual entries |
| `is_retracted` | bool | |
| `source` | string | `"openalex"` or `"manual"` |

Output is deterministic: sorted by year descending then id, UTF-8,
2-space indent, `ensure_ascii=False`, trailing newline. Unchanged inputs
produce a byte-identical file, so "did anything change" is exactly
`git diff`.

Schema changes vs the origin pipeline (its consumer migrates with a
template tweak during the parallel run): `featured` boolean replaced by
`tags`, `is_lab_member` renamed `tracked`, empty-string venue becomes null,
`date` and `is_retracted` added, `dissertation` renamed `thesis`, `software`
type added, top-level wrapper added.

## 5. Configuration

One YAML file, default `erga.yml`. All examples use placeholder contacts
(0000-0002-1825-0097 is ORCID's fictitious researcher Josiah Carberry).

```yaml
mailto: you@example.org          # identifies requests to Crossref/OpenAlex
authors:
  - name: Josiah Carberry
    orcid: 0000-0002-1825-0097
    aliases: ["J. S. Carberry"]  # optional, for matching manual entries
  - name: Another Person
    openalex_id: A5000000000     # alternative when ORCID is missing/wrong
  - name: Third Person           # no ids at all: tracked by name only

openalex:
  api_key_env: OPENALEX_API_KEY  # optional; env var name, never the key itself
  include_xpac: false

output:
  path: publications.json

curation:                        # optional; defaults shown, relative to config
  manual: manual.yml
  overrides: overrides.yml
  tags: tags.yml
```

Author resolution: ORCID resolves via the OpenAlex authors endpoint
(singleton lookups are free). An author entry may pin `openalex_id`
explicitly, and both may coexist (some profiles are split across multiple
OpenAlex author IDs). An entry with neither id is a tracking-only author:
it contributes its name and aliases to the `tracked` flag and to manual-
entry matching but resolves and fetches nothing (for authors without any
registrar identity, or whose works OpenAlex misassigns to a conflated
homonym profile that must not be fetched).

## 6. Curation files

All three survive every refresh; a missing file means "none".

- **`manual.yml`**: list of records the APIs miss. Fields mirror the output
  schema loosely: `title`, `authors` (string or list), `venue`, `year`,
  `doi`, `type`, `tags`. Authors are matched to configured authors by
  name/alias for the `tracked` flag.
- **`overrides.yml`**: list of patches keyed by `doi` (case-insensitive) or
  `id`. Any other key overwrites that field on the merged record. Special
  keys: `exclude: true` drops the record; `keep_distinct: true` exempts it
  from title clustering.
- **`tags.yml`**: mapping of tag name to list of DOIs/ids:

  ```yaml
  featured:
    - https://doi.org/10.5555/12345678
  ```

  Tag names are arbitrary; "featured" above is only an example.

## 7. Pipeline stages

Ported from the production origin pipeline with generalization deltas noted.

1. Load config and curation files.
2. Resolve authors to OpenAlex author IDs (section 5).
3. Fetch works: OR-pipe author batches, `select=` trimmed fields,
   `per-page=100`, cursor pagination, retry with backoff on 429/5xx,
   politeness delay between calls. Deduplicate by work id. Any fetch
   failure aborts the run without touching existing output; a transient
   API failure must never shrink a published list.
4. Normalize to the canonical schema: type mapping, abstract
   reconstruction, OA URL from `best_oa_location`/`open_access.oa_url`,
   author `tracked` flags.
5. Merge manual entries; their DOIs seed the dedup set so manual always
   wins.
6. DOI-level dedup, case-insensitive.
7. Title-cluster dedup. Normalize (NFKD, lowercase, fold dash variants,
   strip non-alphanumerics, collapse whitespace); group by
   (normalized title, is-dataset) so datasets never merge with papers;
   titles under 12 normalized characters and `keep_distinct` records bypass
   clustering. Rank within a cluster: manual first, then version-of-record
   over repository deposits (known repository DOI prefixes: arXiv, Zenodo,
   figshare, Research Square, bio/medRxiv, SSRN, OSF, Fraunhofer publica,
   and `preprint` type), then has-DOI, then citation count, then newest
   OpenAlex record (numeric W-id; publication dates deliberately play no
   part — within a same-title cluster they differ by deposit-version
   artifacts and favor the wrong copies). The winner inherits `abstract`
   and `open_access` from absorbed copies when it lacks them.
8. Apply overrides (patch or exclude).
9. Crossref venue backfill with the last-known-good ratchet: reuse venues
   from the previous output first, then query Crossref (polite mailto
   User-Agent) only for records still lacking one; DataCite DOIs 404 there
   and are skipped silently.
10. Apply tags.
11. Sort deterministically and write.

## 8. CLI

`erga` console entry point, two subcommands in v1:

- `erga build [--config PATH] [--dry-run]`: run the pipeline. `--dry-run`
  prints a summary (fetched, merged, deduplicated, excluded, backfilled)
  without writing. Exit 0 on success (changed or not; change detection is
  git's job), nonzero on any failure.
- `erga verify [--config PATH]`: the author-disambiguation report, a
  first-class feature because OpenAlex author IDs split and conflate
  people. Per configured author: resolved ID(s), works count, name
  variants, most recent titles; warnings for ORCIDs resolving to multiple
  author IDs, zero-work authors, and implausible works counts.

Python >= 3.10. Runtime dependencies: `requests` and `PyYAML` only.

## 9. GitHub Action

A composite action in this repo (`action.yml`): pinned `setup-uv`, then
`uvx erga==<version> build`. Inputs: `config` (path), `version`. No commit
or PR logic inside the action (section 2.3). Full semver tags plus a moving
`v1` major tag, actions/checkout convention. The README pitch stays "one
workflow file plus one config file", with the two delivery recipes.

Action packaging lands after the CLI is proven (see milestones); the
consumer sites can run the CLI directly in their workflows meanwhile.

## 10. Testing and fixtures

- Two-tier fixtures, per the scaffold decisions: small handcrafted records
  exercising dedup/curation logic (they double as documentation of the
  ranking rules), plus a few recorded OpenAlex responses for the fetch
  layer. Synthetic or clearly-public CC0 data only; never the origin
  site's curated real-people data.
- The fetch layer takes an injectable transport so recorded fixtures need
  no HTTP mocking library.
- One end-to-end golden test: fixture config plus recorded responses in,
  byte-exact `publications.json` out.
- CI: ruff, ruff format, mypy strict, pytest across Python 3.10-3.13
  (already in place).

## 11. Milestones

- **v0.1**: CLI end-to-end (config in, correct curated JSON out), tested,
  documented. No Action, no emitters.
- **v0.2**: consumer #1, the origin Jekyll lab site (14 authors), runs erga
  in parallel with its embedded pipeline until outputs match, then
  switches.
- **v0.3**: GitHub Action packaging; consumer #2, an Astro 5 department
  site (tens of authors), stress-tests scale and disambiguation.
- **CSL-JSON and BibTeX emitters** slot in after v0.1 as demand warrants,
  before the public flip.
- **Public + v1.0**: strong README (before/after dedup story, head-on
  "why not BibBase" answer), schema declared stable, PyPI via Trusted
  Publishing, promotion in the channels where the demand already sits.

## 12. Non-goals (v1)

No rendering or UI components, no Google Scholar (scraping is the failure
mode this tool exists to replace), no database, no hosted service, no
sources beyond OpenAlex plus manual entries. Multi-source merging (PubMed,
ADS, DBLP) stays a documented architectural possibility only.

