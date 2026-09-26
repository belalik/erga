# TODO

## High
- Release v0.9.0 once the four-OpenAlex-types item (Normal) lands: main
  carries the unreleased `id` + `doi` override patch (ab175f1), which
  lets dpsd-new retire its Gavalas manual stopgap; route both consumers

## Normal
- A listed work whose byline names a member on an authorship with no
  author id leaves that member untracked: `normalize` tracks a name only
  by exact casefold match on the configured name or alias, so
  "Papageorgiou, Xanthi" or "Xanthi S. Papageorgiou" gets `tracked:
  false`, and a site filtering on `tracked_as` drops the work from her
  page (altitude review of `unlinked-authorships`, 2026-09-26). `verify`
  now reports it ("listed without crediting them"), and found no case on
  either consumer's list (2026-09-26). Candidate fix at the source: track
  id-less authorships with `verify`'s `_byline_matches`, moved to a names
  module both use. Changes tracking and the golden output, so it needs its
  own decision and a measurement of how many listed works it would
  re-track per consumer: a scan of `publications.json` for untracked
  authors `_byline_matches` accepts gives that count with no search, and
  would also let `verify` split its uncredited line by cause (a listed
  record printing the byline another way, fixed by an alias, versus a
  listed twin lacking the authorship, fixed by an override), including for
  names too common to search. The same names module should own "a word in
  a name", now defined three ways (config and matcher `normalize_title`,
  the byline query `\w+`), which disagree only on edge input such as an
  NFD "Pérez" (/simplify altitude review, 2026-09-26)
- `read_output` checks record shapes one reader at a time and still
  accepts `doi: 5`, `year: "2024"` and a string `cited_by_count`, each a
  `verify` crash rather than its "not checked" line. One field-to-type
  table beside `work_from_record` would be complete by construction, but
  could reject a file an older erga wrote: check the shapes earlier
  versions wrote first (/simplify altitude review, 2026-09-26)
- ORCID reconciliation, report-only (dpsd-new inbox, 2026-09-26; the
  section 12 carve-out and section 3's ORCID facts). Read each tracked
  iD's works list, resolve every DOI the build did not produce to its
  OpenAlex work (one batched `doi:` filter), and report the rest with
  where each sits: another author entity (its id) or none. Compare against
  the build's own state, never DOI strings: dpsd-new's outside script made
  22 gaps of 6 real ones on 9 members, through three false-positive
  classes that are the test cases. A twin already listed under another DOI
  (dedup-merged); a deliberate exclusion (override or `exclude_types`,
  front matter such as a Preface or a workshop chairs' message); a broken
  copy fetched without its DOI (the repair `verify`'s unlinked bylines
  report as a better record when the DOI record has no entity). So it
  runs inside `build`, where merges and exclusions are known. What only
  this reaches: works on a detached entity (Papageorgiou's
  `A5004005331`, "X. Papageorgiou", 2 works, which `verify` does not list:
  `_same_name_lines` searches the configured name only, not aliases),
  and the confirmation that a same-name entity's works are the member's:
  put that on `verify`'s same-name line (`A5135377975` was listed and read
  as a homonym). Advisory: an outage, a 503 or a spent quota skips it with
  a warning. Token optional from an env var, anonymous without; README and
  `docs/action.md` gain the registration steps when the code ships, not
  before. Later, DOI-less entries by title: `filter=title.search:`
  (full-text `search=` missed known titles) needs every query word in the
  title, so truncate from both ends (a subtitle hid the i-Walk match); of
  one member's 38, 27 are on site and 11 not in OpenAlex. Works OpenAlex
  lacks are not ingested, only reported in that phase; whether one enters
  as a manual entry is the site's call per member. Draft `manual.yml`
  stubs from ORCID were declined at triage 2026-09-26: work summaries
  carry no byline, the one field a manual entry cannot do without; reopen
  if a consumer asks. Fixtures synthetic: ORCID lists are personal data
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
  the build log could have carried it. The 113 → 103 step above that was
  upstream, and its DOI part benign for him (ORCID DOIs landing on dedup
  twins), but not out of reach in general: for two other members it hid
  real gaps and for a third a repair (the ORCID reconciliation item)
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
- Curated DOIs are not checked for shape: `_field_value` turns any value
  into `https://doi.org/<value>`, so a manual or override `doi: 5`, or a
  typo that drops the `10.` prefix, publishes a dead link at exit 0. The
  `id` + `doi` patch (2026-09-26) makes it a patch value as well as a
  manual field. Refuse at load anything whose `doi_key` is not
  `10.<digits>/<suffix>`, the shape `model._DOI_BODY` already encodes.
  Both consumers' 28 curated DOIs pass that shape (checked 2026-09-26), so
  it should break no file
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
- Thomas registers ORCID public API credentials in a future session
  (Developer Tools, steps in requirements section 3), signed in with his
  iD 0009-0001-3431-2825 (confirmed 2026-09-26, now in `CITATION.cff`).
  The form wants name (`erga`), website URL, description and an
  HTTPS redirect URI, which the client-credentials exchange never uses
  (the repo URL serves for both); he can open it in the Chrome debug
  profile for a playwright-cli walk-through. The client secret never goes
  in chat (transcripts export to logbook): Claude puts the token exchange
  command in `cc-commands.txt` once he has the ID and secret, and the
  `/read-public` token goes to his password manager, reaching consumer
  repo secrets when the ORCID reconciliation ships. Not urgent before
  then: anonymous reads serve local runs; the token matters on CI
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
  separated both of their traps was orcid.org employment history; a ranker
  without it puts the wrong Zissis first with confidence. The 2026-09-26
  ORCID carve-out (section 12) covers reading a given iD's works as a
  check, not finding the iD, which stays the consumer's step. Reopen if a third consumer hits the discovery wall,
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
