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
  ~10% of the catalog and added first-class `conference-paper`, `software`
  and `software-paper`; the classifier re-runs daily. `type_crossref` and
  `raw_type` are absent from live responses (verified). Consequence: rely
  on `type` alone, expect drift, and make drift visible — a raw type that
  is neither mapped nor deliberately "other" raises a build warning
  (a silent catch-all misfiled sixty conference papers on the origin site
  for months). `software-paper` at a journal source is classified `journal`:
  it is a peer-reviewed article about software (SoftwareX, JOSS), not a
  software artifact. Gotcha, should stats ever use it: `group_by=type`
  returns full URI keys (`https://openalex.org/types/...`) while `type` on
  works is the bare string.
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
- **Authorships also carry affiliation** (verified live 2026-08-16, and
  absent from this doc until a consumer needed it): each entry has
  `institutions[]` (`id`, `display_name`, `ror`, `country_code`, `type`,
  `lineage`), a flattened `countries[]`, `affiliations[]`,
  `raw_affiliation_strings[]`, `author_position`, `is_corresponding` and
  `raw_orcid`. All of it arrives under the existing `select=authorships`,
  so affiliation-based checks cost no extra request and no wider response.
  Coverage is partial and is the binding constraint: ~62% of a tracked
  author's own entries carry at least one institution (~52% across a random
  slice of 2024 works), and raw strings add only ~3 points where the parsed
  institution is missing. Consequence for any check built on this: absent
  affiliation must never read as anomalous, since roughly a third of works
  have none.

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
| `authors` | array | `{ "name": str, "orcid": str\|null, "tracked": bool, "tracked_as": str\|null }`; `tracked` = matches a configured author by resolved OpenAlex id, ORCID, or name/alias; `tracked_as` = that author's canonical configured name (null when untracked), so consumers can filter per author without re-implementing alias matching |
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
type added, top-level wrapper added. `authors[].tracked_as` added in 0.2.0
from first-consumer feedback.

A top-level `authors` roster was considered and declined at the second
consumer: that site joined its staff pages to publications entirely on
`tracked_as`, so the roster would have been a convenience for enumerating
tracked authors, not a capability anything needed. Reopen it only if a
consumer is blocked, not because it would be tidy.

## 5. Configuration

One YAML file, default `erga.yml`. All examples use placeholder contacts.
The iD below is deliberately unassignable: ORCID's own fictitious researcher
(0000-0002-1825-0097) is carried by 69 real OpenAlex profiles, because people
paste it into submissions, so a sample using it fetches over a thousand
strangers' works instead of failing.

```yaml
mailto: you@example.org          # identifies requests to Crossref/OpenAlex
home: https://ror.org/0aegean12  # optional: where these people work (ROR id)
authors:
  - name: Josiah Carberry
    orcid: 9999-9999-9999-9999   # placeholder: no real iD starts 9999
    aliases: ["J. S. Carberry"]  # optional, for matching manual entries
  - name: Another Person
    openalex_id: A5000000000     # alternative when ORCID is missing/wrong
    home: https://ror.org/0packy456   # this person's own, overriding above
  - name: Third Person           # no ids at all: tracked by name only
    home: null                   # opts out of the department-wide default

openalex:
  api_key_env: OPENALEX_API_KEY  # optional; env var name, never the key itself
  include_xpac: false

output:
  path: publications.json
  exclude_types: [other]         # optional: types dropped from the output

curation:                        # optional; defaults shown, relative to config
  manual: manual.yml
  overrides: overrides.yml
  tags: tags.yml
```

`home` is a ROR id, bare or as a ror.org URL, and it is read by nothing but
the contamination check. It says where these people work, so the check can
stop inferring that from the counts. Three states: the key absent on an
author inherits the top-level declaration, a value replaces it, and an
explicit `null` opts that author out — a department default has to be able
to carry a visitor without anyone inventing a false ROR. A declaration
follows the configured person, so it covers every OpenAlex profile their
entry resolves to, including split identities.

It is never identity evidence. Like the ORCID, it is trusted as given: erga
does not check that the declared institution is really where the author
works, and a wrong declaration produces a wrong verdict rather than a
correction. Resolution is from the corpus first, since every authorship
carries both the ROR and the OpenAlex id, and costs one
`/institutions/ror:` lookup only for a ROR the corpus never names. An
unresolvable declaration aborts the build rather than falling back to the
inferred rule: the same config and corpus would otherwise print different
advice depending on whether the API answered.

Author resolution: ORCID resolves via the OpenAlex authors endpoint
(singleton lookups are free). An author entry may pin `openalex_id`
explicitly, and both may coexist for two different reasons: some profiles
are split across multiple OpenAlex author IDs, and a correct iD may
resolve to nothing at all when OpenAlex never linked it to the profile
holding the works. In the second case the pin supplies the works while
the iD still earns the author their byline tagging, so keep both rather
than dropping the iD. An entry with neither id is a tracking-only author:
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
  keys: `exclude: true` drops the record; an explicit `exclude: false`
  exempts it from the `output.exclude_types` filter; `keep_distinct: true`
  exempts it from title clustering. A field patch that no longer changes anything
  (upstream caught up) raises a build warning, measured against the
  pre-patch record — measuring against the output would be circular. The
  warning is information, not an instruction to delete: a redundant
  override may stay as insurance against upstream regressing.
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
   author `tracked` flags. The raw works are also read for contamination
   (a homonym's works sitting inside a correctly-named profile, which
   `verify` cannot see because the names match): a work is a candidate
   only when it has affiliation data, falls outside the author's home
   country, shares no institution with it, is not solo-authored, and its
   co-author team appears nowhere in the rest of that career; candidates
   are then reported only in groups of two or more sharing an institution.
   Home is the majority country of the author's affiliated works, or the
   declared `home:` where the config carries one, which also lets the
   check say a profile looks wrong instead of listing its majority.
   Output is warnings only: erga names the cluster, the maintainer decides
   and excludes. The check reads the raw fetch, ahead of dedup and
   overrides (`build` in `pipeline.py` runs it first), so a cluster's
   count can exceed the override lines that already exclude it while
   nothing is live: on consumer #2 a cluster reads five against four
   excluded DOIs because the fifth is a preprint that folds into its
   excluded published version at dedup. The unmapped-type warning counts
   the same way. Reconcile a count against the built JSON, never against
   the override file.

   **The rule is settled (2026-08-17); the code was independently
   reviewed on 2026-09-02 and released in v0.4.0 the same day. The
   declared home ships in v0.5.0 and is described below.** Two variants were measured against 40 live careers,
   but only for false positives. Counting collaborators across the whole
   fetched corpus keeps noise at ~0.1 clusters per author; counting them
   across the career only, holding outliers out of the network, raises
   noise to ~0.38 clusters per author in sizes up to nine, because a
   genuine research stay abroad is structurally identical to a homonym.
   Recall separated them, and it could only be measured where the one
   known contamination lives: consumer #2 measured that career on
   2026-08-17. The stray works share 15 co-authors with each other and
   **zero** with the real corpus, so the corpus-wide variant lets the lab
   alibi itself and reports nothing, while the career-scoped variant
   reports the cluster whole. The career-scoped variant is therefore the
   rule, and ~0.38 clusters per author is the accepted price of seeing the
   shape the check exists for. `tests/test_contamination.py` carries that
   career as a synthetic fixture; it fails under the corpus-wide variant.

   Field was expected to be the deciding third signal and is not.
   `primary_topic` is present on 100% of works, and on the measured career
   the stray field set and the real one are disjoint — but that career
   spans six fields over eleven works, so "differs from the author's modal
   field" would also flag its genuine Neuroscience and Demography papers.
   The discriminator is field *distance*, which needs a hierarchy metric
   erga does not have and which n=1 does not justify building. No field
   leg ships, and `primary_topic` stays out of `WORKS_SELECT`.

   Review on 2026-08-17 found two defects in that code, both now fixed
   and both invisible to the 40-career measurement. Home was the plurality
   country, so on a thin record a large enough stranger cluster won the
   count and the check reported the genuine career as the intruder — at
   the author's own institution, advising exclusion by DOI. Home now
   requires a strict majority and at least `MIN_HOME_WORKS` works, and is
   silent otherwise. Separately, every institution co-listed on a
   home-country work counted as home, so one dual-affiliation paper
   whitelisted a foreign institution for the whole career and later
   clusters there went unreported; only institutions whose own country is
   home now count. That match reads a country recorded per institution, so
   a record arriving without one no longer erases a country another record
   carried: before the whitelist change that was cosmetic, affecting only
   the warning text, and afterwards it could push the author's own
   institution out of home.

   An independent review of those fixes on 2026-09-02 found a third
   defect, in the majority rule itself, now fixed. The test's denominator
   admitted a work on institution alone while only a work's own countries
   could vote, so an entry naming the institution but carrying no country
   counted against home without ever counting for it; enough of them and a
   genuine career failed its own majority, and the check fell silent on a
   real cluster. A work's countries now include the country the label pass
   resolved for each of its institutions. A work whose institutions carry
   no country anywhere in the corpus still dilutes the count, and is left
   that way deliberately: the check prefers silence to a guess.

   **Re-measured on 2026-09-02 with all three fixes in:** 10 clusters
   across 7 of the same 40 authors, sizes two to six, 0.25 per author,
   with 37 of 40 clearing the majority gate. The net moved down from
   ~0.38. The whitelist and denominator bugs were suppressing clusters, so
   removing them could only add warnings, while the majority rule is a
   new silence gate that can only remove them, and the gate won. The same
   day a `works_count:20-80` band, closer to a department member, gave 9
   clusters across 7 of 40 authors, 0.23 per author, 33 of 40 clearing
   the gate, but sizes up to eleven inside careers of under eighty works.
   Both figures are upper bounds on false positives: the samples carry no
   labelled positives, and a cluster of eleven in a forty-work profile is
   what a homonym looks like. `local/contamination-probes/` is the
   harness; re-run it after any rule change.

   Three caveats stand. Recall is n=1: one career, one homonym. The
   per-author rate is measured at department scale now, but on unlabelled
   samples, so it bounds the noise without separating it from any
   contamination the samples genuinely contain. And the majority rule bounds the inversion without closing it: where a
   stranger's works both outnumber the genuine ones and clear
   `MIN_HOME_WORKS`, the two sides are structurally symmetric and the
   check will still pick the wrong one. That profile is mostly not its
   author's, which is `verify`'s question.

   **The declared home (v0.5.0) answers the third caveat where it is
   declared.** With `home:` set (section 5), the check stops inferring
   where home is and is told, which changes four things. The majority test
   that chose home is gone: nothing a stranger cluster can do wins the
   baseline now. `MIN_HOME_WORKS` stays, because a declaration supplies
   where home is and not how much career is on file — the maintainer did
   not assert that three works characterize anyone. The denominator
   narrows to works whose affiliation positively places them somewhere, so
   a work naming an institution the corpus never gave a country to no
   longer dilutes the count; that dilution is deliberate when home is a
   guess and pointless when it is declared, and it is the silence the
   field was asked for. And a profile whose placed works are mostly *not*
   at home is reported as a wrong profile, with no exclusion advice,
   instead of having its majority listed as strangers — excluding those
   works one at a time would dismantle the evidence that the iD or the
   declaration is what is wrong.

   Three thresholds, stated so they are arguable: the wrong-profile
   verdict needs a strict majority of placed works away from home, cluster
   detection needs a strict majority at home, and anything between —
   a tie, or evidence split three ways — stays silent, as it does
   undeclared. Away is counted positively and is never the complement of
   home, so an unplaced work votes for neither side. The declared
   institution is home even on a work the corpus never placed; every other
   institution still has to earn it on its own country evidence, because
   co-listing beside a home institution is the whitelist defect fixed
   above and a declaration must not reintroduce it pointed the other way.

   **The numbers above are snapshots of cohorts no one recorded, and
   nothing measured after them can be compared with them.** They were
   taken on 2026-09-02 against that day's OpenAlex index. Three runs of
   the *unchanged* module on 2026-09-21 gave 0.15 per author with 34 of 40
   clearing the gate, then the same again, then 0.17 with 35 of 40 — and
   the third differed because `sample=40&seed=17` had returned a different
   cohort: 32 of the 40 author ids matched the set drawn ninety minutes
   earlier, eight were new. Two calls minutes apart do return an identical
   list, so the seed looks stable until the window widens. Sampling, not
   the rule, was the dominant term in any difference between two runs.

   **The cohort is pinned since 2026-09-21.** The harness draws once per
   band, stores the forty authors with their fetched works in
   `local/contamination-probes/cohort-<band>.json`, and every later run
   reads that file with no network call, so a moved number is now the rule
   and nothing else. The pinned baselines, same unchanged module: band
   `80-400`, 17 clusters across 8 of 40 authors, sizes two to nine, 0.42
   per author, 33 of 40 clearing the gate; band `20-80`, 7 clusters across
   5 of 40, sizes two to eight, 0.17 per author, 33 of 40. The 80-400 draw
   is the highest the module has ever scored, on code that had scored 0.15
   two hours earlier: that spread is the sampling term at full size, and
   the upper-bound caveat above applies to it unchanged. A live
   before/after claim is possible against these two files and against no
   earlier figure; deleting a cohort file redraws it and resets the
   baseline.

   **The declared path, measured 2026-09-21 on the pinned cohorts**
   (`local/contamination-probes/validate_declared.py`, offline). Each
   author was declared at their modal institution, the one on most of
   their own authorships, and checked both ways. Band `80-400`: 35 of 40
   authors declarable, 34 verdicts unchanged (26 silent, 8 carrying the
   same 17 clusters), and one silent career reported as a wrong profile
   because its modal institution (13 works) sits outside its modal
   country (53 works) — the proxy declared a minority-country institution
   and got the verdict a wrong declaration is meant to get. Band `20-80`:
   38 of 40 declarable, 38 unchanged. No cluster was added in either band.

   No silence lifted, because none was the majority rule's. Of the seven
   silent authors per band, 80-400 has five with no institution carrying a
   country on any of their authorships, one with a single placed work and
   one exact 35/35 tie; 20-80 has two with no such institution and five
   with one to three placed works. The evidence floor and the tie rule
   hold under a declaration by design, and the dilution case the narrowed
   denominator was written for — a majority hidden by works that name an
   institution without a country — occurred zero times in eighty careers.
   The field's measurable value on a random cohort is therefore the
   wrong-profile verdict, and that one fires: declaring each author's most
   frequent institution in a *second* country produced a mismatch on 53 of
   56 eligible careers, and the three silences were the flipped career
   above, whose "wrong" country is its real home, plus two records of one
   and three placed works. The lifted silence is unobserved rather than
   refuted on a random cohort.

   **The first department cohort with a real declaration, 2026-09-22**
   (consumer #2, nine authors, `home:` set once at the department's ROR,
   `erga==0.5.0` built with and without it minutes apart plus an
   `erga==0.3.0` control the same hour; their record is dpsd-new
   `docs/publications.md`). All three builds wrote byte-identical JSON
   (626 works), so v0.4 and v0.5 changed the log and nothing else for
   this consumer. The known homonym is reported whole in both runs: the
   career recall was settled on above shows its five Palacký works as one
   cluster, declared or not, so the declaration costs no recall on the
   one case that can measure it. Two clusters of own early career
   (Essex 1999-2003, two works; Toronto 1994-99, seven, a doctorate) are
   identical in both runs, the accepted price. No silence lifted here
   either. Exactly one line changed, and it changed for the worse: an
   author with SUTD on 16 of 27 placed works (2016-22), the Aegean on 6
   (since) and Lisbon before that. Undeclared, the majority rule put
   home in Singapore and listed his two Aegean works, his employer's, as
   a stranger cluster. Declared, 21 of 27 placed works sit outside Greece
   and the verdict is a wrong profile. One person, one profile, a correct
   declaration, and the rule produces this by construction for anyone
   whose recorded career sits mostly at a previous employer; a department
   always has some. `home: null` is the only remedy and it removes the
   check for that person. So the declared home's measured value on real
   data is the reverse of the random cohorts' finding: there it changed
   nothing and the wrong-profile verdict was the field's demonstrable
   use; here it changed one verdict and that verdict was wrong. What a
   declaration should mean for a mover, a start year, several homes, or
   verdict text that names the third reading, is an open design decision
   (`docs/todo.md`), and this cohort is its only fixture.

   All of the above argue for the output staying advisory, which it is.
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
8. Apply overrides (patch or exclude), then drop `output.exclude_types`
   records. Manual entries are explicit curation and never type-filtered;
   an `exclude: false` override rescues an individual fetched record.
9. Crossref venue backfill with the last-known-good ratchet: reuse venues
   from the previous output first, then query Crossref (polite mailto
   User-Agent) only for records still lacking one; DataCite DOIs 404 there
   and are skipped silently.
10. Apply tags.
11. Sort deterministically and write.
12. Build delta (after v0.5.0; decided 2026-09-21 on consumer #2's
    proposal, whose weekly PR diff had outgrown what GitHub renders).
    The records about to be written are compared, by work id, against
    the output file found in place: the same single read that feeds the
    venue ratchet, taken before the file is replaced, so the build knows
    "before" without the consumer reconstructing it from git. Identity
    is the work id: a manual entry retitled, or a title cluster whose
    winner switched because a DOI arrived, lists as removed and added
    rather than as a field change, which is also what the site sees. A
    first build lists nothing, since there is nothing to compare
    against; its review is `verify` and the file itself, and the run's
    warnings still head the page. A file in place that erga cannot read
    counts as a first build, with a warning saying so. Three
    classes of change. *Listed one by one*: added and removed works, a
    retraction flag turning on, and a change in the set of tracked
    people on a work, since these alter who is credited or whether the
    work belongs on the site at all; each entry carries the audit tell
    (tracked person, co-authors, venue, DOI, a manual-entry mark),
    because a same-name researcher's works arrive as additions and
    `verify` cannot see them. *Counted per field*: every other change
    OpenAlex makes (citations, abstract, open access, venue, dates,
    title, DOI, type, byline names and iDs), one table labelled as drift
    with nothing to action; drift is large, since consumer #2 saw
    OpenAlex expand author initials on 303 of 626 works between two
    days' builds (2026-09-21 to 22, reproduced by a v0.3.0 control), so
    the byline row can name half the corpus in one week. *Curation, counted and labelled as the
    maintainer's own*: tag changes, with manual entries marked in the
    lists. Listed sections cap at 150 entries and state how many more
    there are, sized against GitHub's 65,536-character PR body. The
    run's warnings head the page, contamination included, so they reach
    a reviewer rather than dying in a CI log. Shrink guard: a warning,
    never a refusal, when removals exceed a tenth of the previous build.
    erga cannot tell a degraded fetch from a dropped author or a new
    `exclude_types` entry, so the consumer's review gate is the stop; the
    hazard is a successful response carrying fewer works, since a failed
    fetch aborts before writing. The page is prose for a reviewer, not
    part of the schema contract: nothing should parse it. A byte-exact
    golden test freezes it alongside the JSON.

## 8. CLI

`erga` console entry point, three subcommands:

- `erga build [--config PATH] [--dry-run] [--summary PATH]`: run the
  pipeline. `--dry-run` prints a summary (fetched, merged, deduplicated,
  excluded, backfilled) without writing the JSON. Every build prints a
  one-line headline of what changed since the output it found in place;
  `--summary` also writes the full Markdown page (stage 12), under
  `--dry-run` too, since the flag asks for that one file explicitly and
  the delta is what a dry run exists to show. Exit 0 on success (changed
  or not; change detection is git's job), nonzero on any failure.
- `erga diff OLD NEW`: the same page for any two output files, on
  stdout, with no config or network. A missing OLD is a first build; an
  OLD that exists but cannot be read is an error, as an unreadable NEW
  is, because the user named it. `build` meets the same file in place
  with a warning and goes on as a first build, since a build never
  aborts over its previous output.
- `erga verify [--config PATH]`: the author-disambiguation report, a
  first-class feature because OpenAlex author IDs split and conflate
  people. Per configured author: resolved ID(s), works count, name
  variants, most recent titles, and a name search listing same-name
  profiles the config does not cover (homonyms, and conflated profiles
  holding misassigned works — surfaced for tracking-only authors too).
  Warnings separate the ORCID failure modes by comparing profile names
  to the configured name/aliases: a split profile (several ids, names
  all match; pin `openalex_id`) versus an iD carried by apparently
  different people (strangers' works would be fetched; remove the
  `orcid` and pin `openalex_id` — judged only against the profiles the
  ORCID itself resolved to), plus any resolved profile whose name does
  not look like the configured author (mistyped id), zero-work authors,
  and implausible works counts.

Python >= 3.10. Runtime dependencies: `requests` and `PyYAML` only.

## 9. GitHub Action

A composite action in this repo (`action.yml`): pinned `setup-uv`, then
`uvx erga==<version> build`. Inputs: `config` (path), `version`, and
`summary` (a path; passes through as `--summary`, so the change page is a
second produced file, not delivery). No commit or PR logic inside the
action (section 2.3). Full semver tags plus a moving
`v1` major tag, actions/checkout convention. The README pitch stays "one
workflow file plus one config file", with the two delivery recipes.

Landed in v0.3. Operational detail (inputs, path resolution, permissions,
scheduling, the `v1` tag policy, how CI exercises it) lives in
[action.md](action.md); this section stays the design decision only.

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

- **v0.1** (released 2026-08-05 as v0.1.0): CLI end-to-end (config in,
  correct curated JSON out), tested, documented. No Action, no emitters.
- **v0.2** (done 2026-08-05): consumer #1, the origin Jekyll lab site
  (7 authors), ran erga in parallel with its embedded pipeline to full
  convergence (187/187 records), then switched its CI to erga 0.1.0.
  The v0.2.0 package release followed on 2026-08-08 with the first
  changes driven by that adoption (abstract cleanup, tracked_as).
- **v0.3** (released 2026-08-09 as v0.3.0): GitHub Action packaging,
  built and exercised by CI. Consumer #2, an Astro 5 department site
  (tens of authors) stress-testing scale and disambiguation, is handed
  off (2026-08-11) and pilots on its own side; its findings drive the
  next changes.
- **v0.4** (released 2026-09-02 as v0.4.0): the department-scale intake
  hardening from the consumer #2 pilot (verify separating split profiles
  from contaminated iDs, the same-name search, `output.exclude_types`) and
  the work-level contamination check, advisory, with its rule settled on
  the one career that could measure recall.
- **v0.5** (released 2026-09-21 as v0.5.0): the declared home (`home:`,
  a ROR id) for the contamination check, measured on pinned cohorts
  before shipping (section 7): safe on every random career, the
  wrong-profile verdict working, the lifted silence unobserved there and
  again on the first department cohort with a real declaration
  (2026-09-22), where the declaration's one changed verdict was a recent
  mover reported as a wrong profile.
- **v0.6** (released 2026-09-22 as v0.6.0): the build delta (stage 12): a
  headline on every build, `--summary`, `erga diff`, the Action's
  `summary` input and the shrink warning; and the previous output's
  reader reporting a file in place it cannot read instead of calling it
  a first build.
- **CSL-JSON and BibTeX emitters** slot in after v0.1 as demand warrants,
  before the v1.0 promotion push.
- **v1.0**: strong README (before/after dedup story, head-on "why not
  BibBase" answer), schema declared stable, promotion in the channels
  where the demand already sits. Repo visibility and PyPI Trusted
  Publishing moved up to v0.1.

## 12. Non-goals (v1)

No rendering or UI components, no Google Scholar (scraping is the failure
mode this tool exists to replace), no database, no hosted service, no
sources beyond OpenAlex plus manual entries. Multi-source merging (PubMed,
ADS, DBLP) stays a documented architectural possibility only.

