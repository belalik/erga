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
- Clean HTML-wrapped DOIs on ingest. OpenAlex carries values like
  `https://doi.org/10.13140/rg.2.2.34719.94883">https://dx.doi.org/10.13140/rg.2.2.34719.94883</a`
  (UNH repository records, smartmove-site 2026-09-23), and `normalize.py`
  passes them through: `doi_key` strips only the host, so DOI dedup,
  overrides, tags and Crossref backfill miss, and the output links nowhere.
  Extract the DOI-shaped part in `normalize`, warn when trimming was
  needed, and add that record as a regression fixture
- `write_atomic` (`output.py`) leaves `publications.json` and the summary
  page at mode 0600: `mkstemp` creates the temp file that way and
  `os.replace` keeps it (smartmove-site, 2026-09-23, umask 0002). Harmless
  where CI commits the file, a 403 where a site serves it from a web root
  as another user. Keep an existing target's mode, else `0o666 & ~umask`;
  test both
- Four OpenAlex types warn and fall back to `other`, seen by both
  consumers. dpsd-new builds: `reference-entry` (10 works: encyclopedia
  entries in two editions, a handbook chapter under two DOIs),
  `peer-review` (2, author responses), `conference-abstract` (1).
  smartmove-site scratch profiles (2026-09-23): `conference-abstract` (9),
  `peer-review` (1), `report` (4). Map them or declare them unmapped on
  purpose; the warning fires on raw works before curation, so an override
  cannot silence it
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
  merged profile for a name-only member's own (smartmove-site, 2026-09-23)
- Docs from the smartmove-site inbox (2026-09-23): README, one sentence
  that an undeclared check reads a profile holding mostly someone else's
  works backwards, listing the real person's few works as the strangers;
  requirements section 7, a consumer-#1 paragraph: 0.2.0 and 0.7.0 wrote
  byte-identical JSON (190 works), a declared `home:` was silent on seven
  authors, and the merged-profile scratch case (declared right, undeclared
  backwards)
- Two silent traps in manual entries (smartmove-site, 2026-09-23, their
  manual-file header documented the first). `authors: "A, B, C"` as one
  string becomes one author named "A, B, C" (`curation._parse_authors`
  wraps a string whole), so nobody is tracked, at exit 0: warn when an
  author string holds two or more commas, or contains a configured name or
  alias without matching it ("Surname, Given" stays valid); this needs
  warnings threaded out of `load_manual`, which only raises today. And
  `year` is never derived from `date`, so a date-only entry writes
  `year: null`: derive it from a `YYYY[-MM[-DD]]` date, and raise a
  `ConfigError` when both are set and disagree
## Low
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
