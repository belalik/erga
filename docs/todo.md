# TODO

## High
- Review and merge branch `small-fixes` (DOI cleaning, output file mode,
  manual and override date/byline traps; removes their three Normal items
  below): `/code-review medium small-fixes` first, then a blind Codex
  review of `git diff main...small-fixes`, then fix, merge, push

## Normal
- `verify` section for unlinked authorships: works that carry a configured
  name in the byline but no author id, so no profile fetch sees them
  (smartmove-site, 2026-09-23: 4 of a member's 7 missing papers). OpenAlex
  has the filter (`raw_author_name.search:<name>`, probed 2026-09-24). Query
  each configured name and alias, keep hits whose matching authorship has no
  author id, drop hits the existing dedup clusters with fetched works, apply
  `exclude_types`, list the rest as advisory with a pointer to the manual
  file. Benchmark: Troupiotis-Kapeliaris gave 38 hits, 30 linked, 8 unlinked
  = 3 missing papers, 3 versions of one Zenodo dataset, 2 repository copies
  of linked works. A Greek-script byline (his thesis) is caught only if an
  alias carries that script; common names will pull in namesakes' works
- Four OpenAlex types warn and fall back to `other`, seen by both
  consumers. dpsd-new builds: `reference-entry` (10 works: encyclopedia
  entries in two editions, a handbook chapter under two DOIs),
  `peer-review` (2, author responses), `conference-abstract` (1).
  smartmove-site scratch profiles (2026-09-23): `conference-abstract` (9),
  `peer-review` (1), `report` (4). Map them or declare them unmapped on
  purpose (`KNOWN_OTHER_TYPES` in `normalize.py` is the declare-on-purpose
  list; either list silences the warning); the warning fires on raw works
  before curation, so an override cannot silence it. dpsd-new's first
  v0.7.0 build (2026-09-25, 626 works) confirms the same three names and
  the warning now heads their weekly PR body until this is done
- Contamination cluster warning: drop "exclude them by DOI" for works that
  carry another configured author, and name that author instead
  (`contamination.py`, `contamination_warnings`). Excluding such a work
  deletes the co-author's paper from the site whichever way the verdict
  points. Case (smartmove-site, 2026-09-23): an undeclared scratch build
  on a merged profile put a lab member's two cohort-co-authored papers in
  the stranger cluster and advised their exclusion. Wording only; the
  detection rule stays as settled (a cohort-co-authorship tiebreaker for
  home was proposed and rejected at triage, the same family as the
  collaborator gate section 7 rejected on 2026-09-23)
- `verify` same-name lines: add how many of the profile's works are
  shared with configured authors (one count query per line, e.g.
  `28 works, 2 shared with configured authors`). A bare count plus a
  matching institution led a consumer session to take a three-person
  merged profile for a name-only member's own (smartmove-site, 2026-09-23).
  On the same line, name any alternative the neighbour shares with the
  configured profile and mark a matching institution (one more field in
  the author select): a shared initial-only form at the same institution
  means OpenAlex cannot tell the two careers' initial-only bylines apart,
  and neither `verify` nor the cluster warning sees a work it put on the
  wrong side. Motivating case (dpsd-new, 2026-09-25): John and Jenny
  Darzentas, spouses at the same Aegean department, `A5109152625` (no
  ORCID) and `A5028359938`, both carrying "J. Darzentas" in
  `display_name_alternatives`. Their two author entities are a permitted
  recorded fixture (CC0); per-work ground truth stays with dpsd-new.
  Informational, as the same-name lines are: the remedy is manual either way
- A repository as `primary_location` sets both venue and type.
  `normalize` reads the venue and the source-type refinement from the
  primary location's source alone; when that source is a repository and
  another location carries a journal or conference source, both come out
  wrong (dpsd-new, 2026-09-25: `W2152130239`, primary WestminsterResearch,
  `submittedVersion`, so venue became the repository and type
  `book-chapter`; the second location is the IASTED CSN 2006 conference).
  Prefer the first non-repository location for venue and source type when
  the raw type is not `preprint`; the public record is a permitted fixture
- Author names: render the byline when the entity name carries a script
  the byline lacks. `normalize` takes `author.display_name` first and
  `raw_author_name` only when it is missing, so every upstream rename of
  an author entity reaches the output. dpsd-new (2026-09-25, 626 works):
  five entities flipped Greek → Latin upstream within three days (32
  authorships; «Αναστάσιος Θεοδωρόπουλος» on a Sensors 2025 byline that
  prints "Anastasios Theodoropoulos"), and three carry a lone Greek
  capital homoglyph inside a Latin name ("Eleni Κ. Efthimiadou", Κ U+039A),
  stable across fetches. One rule covers both, in both directions and
  without a homoglyph table: if the entity name contains letters of a
  script absent from the byline, use the byline. Count the fallbacks and
  print one informational line per build. Trap: tracked-by-name matching
  runs on the rendered name, so test both the entity name and the byline
  against the configured names, or an alias that matched the entity name
  loses its tracking when the byline is chosen. Synthetic fixture: a Greek
  entity name over a Latin byline, a homoglyph case, and a Greek byline
  under a Latin entity (the thesis case, which must come out Greek)
- Per-author stage counts in the build summary (`BuildStats` is global
  only: fetched, deduplicated, excluded, total). One line per tracked
  author, fetched / merged away / excluded / written, a co-authored work
  counting for each. Case (dpsd-new, 2026-09-25): a member asked why the
  site lists 91 of his 103 OpenAlex works; the answer (9 title-cluster
  merges, 3 editorial exclusions, all deliberate) took a diff script when
  the build log could have carried it. The 113 → 103 step above that is
  upstream (ORCID entries OpenAlex never linked) and out of reach
- Delta page: report field updates that come from overrides apart from
  drift. The page compares the previous and current output, both
  post-curation, so a newly added override tables as drift under "Metadata
  drift from OpenAlex. Nothing to action." (dpsd-new dry run, 2026-09-25:
  type 4, date 3, venue 3, year 3, title 1, all curation). Have the
  pipeline pass `compute_delta` the (work id, field) pairs a patch touched
  this build; a changed field under a patch is curation, the rest drift.
  `Override.changed` alone cannot do it: it fires on every build a binding
  override runs. Changes the frozen golden summary
  (`tests/fixtures/golden/expected-summary.md`); regenerate and read by eye
- Docs from the smartmove-site inbox (2026-09-23): README, one sentence
  that an undeclared check reads a profile holding mostly someone else's
  works backwards, listing the real person's few works as the strangers;
  requirements section 7, a consumer-#1 paragraph: 0.2.0 and 0.7.0 wrote
  byte-identical JSON (190 works), a declared `home:` was silent on seven
  authors, and the merged-profile scratch case (declared right, undeclared
  backwards). And a consumer-#2 paragraph from dpsd-new's member
  confirmation round (2026-09-25, three of six replied): no foreign work
  reported on any profile; the one cluster warning that fired on a
  replying member (Gavalas, Essex, 2 works) was his own PhD years, a true
  and benign cluster; one member's "some missing" was 113 ORCID → 103
  OpenAlex → 91 site, the fetch lost nothing; six metadata corrections
  landed as overrides (the repository-location item above and the IEEE
  DOI-year item under Low are the two mechanisms worth a rule; a
  truncated-title DOI-less twin and two theses typed `article` were fixed
  by override and declined as rules at triage). Two asks recorded
  as out of scope: citation counts per work (site side, `cited_by_count`
  is in the JSON) and Scopus as a source (v1 non-goal). Ground truth from
  members is recorded here, never as fixtures: it is curated personal data
  under the fixture rule; only signals traced to public OpenAlex records
  are fixture material
## Low
- Advisory warning when an IEEE conference DOI's year segment disagrees
  with `publication_year` (dpsd-new, 2026-09-25: `10.1109/icc.1999.765564`,
  `10.1109/iscc.1999.780940`, `10.1109/glocom.1999.831671` carry
  `publication_date` 2003-01, the Crossref `created` date of IEEE's
  back-catalogue registration, with no `published` part). Scope it to the
  `10.1109/<conf>.<year>.` shape, where the year is structural; a general
  DOI-year check false-positives on Elsevier DOIs, whose year is the online
  year and legitimately precedes the issue. Warn, never correct: the
  override (`year: 1999`, `date: null`) is the settled fix
- Replace ORCID's fictitious-researcher iD (`0000-0002-1825-0097`) in the
  tests with a `9999` placeholder, per the CLAUDE.md fixture rule: six
  test modules plus the OpenAlex and golden fixtures, so the golden
  expected output changes with it (`grep -rl 1825-0097 tests`)
- Add `orcid:` under the author in `CITATION.cff` once Thomas confirms
  his iD: the one public record under his name (0009-0001-3431-2825,
  empty, 2023) is unconfirmed; orcid.org's forgot-iD form settles it
- `verify`'s `recent:` lines repeat one paper across the three slots
  (smartmove-site, 2026-09-23: H3CPP three times): `recent_works` takes the
  three newest records before any dedup. Ask for ~10 in the same call, drop
  repeats by `dedup.normalize_title`, print the first three distinct
- Two configured authors with different non-null `home:` values can resolve
  to one OpenAlex profile, and the later entry's declaration wins, as its
  name already does (`src/erga/pipeline.py`, the `declarations.update`).
  Neither the code nor section 5 defines that as the rule, so no test
  freezes it (Codex, `local/codex-test-gaps/notes.md`). Define it, or
  reject the overlap at config time with a message naming both entries
- Mint the moving `v1` tag with the 1.0 release; policy in docs/action.md
- Consumer recipes doc, unblocked now that a second consumer exists. Open it
  with the consumer contract: what erga asks of a consumer site (ORCID iDs,
  owned config, reviewed curation, API key at scale) and what it guarantees.
  Jekyll specifics are already in docs/action.md; the Astro recipe is thin
  (config-relative `src/data/erga.yml` → `publications.json`, imported at
  build time, no schema or convention change), and the empty-unlinked-ORCID
  case is the worked example to narrate. Also carry the discovery recipe
  dpsd-new measured, since finding an iD is the consumer's step: search
  OpenAlex under several Latinizations, read `last_known_institutions`,
  confirm the candidate's ORCID against orcid.org employment history, then
  scan the profile for the same-name-stranger shape. Their two traps are
  the cautionary examples (a person who signs "Xidias" where the staff
  record says "Xydias"; two Dimitris Zissis where the wrong one carries the
  right institution on OpenAlex)
- `erga suggest` (name and institution in, ranked candidate profiles out),
  proposed by dpsd-new and declined for v1 on 2026-09-02. The signal that
  separated both of their traps was orcid.org employment history, a second
  source the v1 non-goals exclude; a ranker without it puts the wrong Zissis
  first with confidence. Reopen if a third consumer hits the discovery wall,
  or when the sources non-goal is revisited after v1
- Surface no consumer has exercised yet, so unproven in the field before
  v1.0: `keep_distinct` overrides, thesis/software types in templates,
  keyless runs
- Publish a formal JSON Schema for the output and validate against it in
  tests (pre-v1.0): consumers get machine-checkable contract + generated
  types (Astro/TS)
- CSL-JSON and BibTeX emitters (before the v1.0 promotion push)
- Per-author review export (markdown per tracked author) so the maintainer
  can send each person their list for confirmation before publishing. A
  sibling of the other emitters; the consumer #2 pilot returned no input on
  it, so shape it from erga's side unless a consumer asks for something
- Year-cutoff knob (global; maybe per-author) as an output convenience, post-
  v1. Decided with consumer #2: fetch stays full-career, period views are the
  renderer's job; this knob would only spare consumers that filter
