# TODO

## High
- Ship v0.5.0 once the test gaps below are closed. The declared home is
  measured (`docs/requirements-v1.md` section 7, 2026-09-21): no verdict
  moved that a random career already had, no cluster added, the
  wrong-profile verdict fired on 53 of 56 wrong declarations. What the
  field was built to lift — a majority-rule silence — occurred zero times
  in eighty random careers, so that claim stays unobserved; the only place
  it can be seen is a department cohort with a real declaration, which is
  the dpsd-new entry below
- Close the declared-home test gaps Codex named, listed with line cites in
  `local/codex-home-review/review.md`. None is a known defect; each is a
  rule the code states that no test reaches: the evidence floor just below
  and exactly at five with all-away data, the one-away-from-equal
  boundaries (4/5 and 5/4), a work affiliated both home and away, the
  authority fallback for a ROR absent from the corpus, the abort when
  something resolves but carries no country, one configured author across
  several profiles, and a per-author override or opt-out reaching the
  check end to end. It also notes the declared-tie and thin-record tests
  pass even if the declaration never reaches the checker, since the
  inferred path is silent on the same fixtures — they lean on the rescue
  test to establish the branch ran. Same pass: the `affiliated`
  comprehension is duplicated verbatim between `_clusters_for` and
  `_declared_for`, so a change to what counts as affiliated can drift
  between the two paths unnoticed; one helper (`/code-review high` on
  `689b860`, 2026-09-21, its only finding not already listed here)
- `resolve_author` reads one 25-row ORCID page and records a larger total
  without fetching the tail (`src/erga/openalex.py`), so "the declaration
  follows the person to every profile" is bounded by what the resolver
  materializes. Pre-existing and unrelated to `home:`, surfaced by the
  same review; decide whether the promise or the resolver should move
- Tell dpsd-new the field is in and what its config line looks like. They
  asked for it, and their pilot is the only place a real declaration and a
  known homonym coexist. Ask for one thing back: a build with `home:` set
  and the warnings it prints beside the undeclared run's, since a lifted
  silence or a wrong-profile verdict on a real department is the
  observation the random cohorts could not produce

## Normal
- Build-delta summary: diff the `publications.json` already at the output path
  against the new build and report what changed, with schema knowledge of which
  fields are cosmetic (cited_by_count) versus audit-critical — consumers need it
  to review a weekly PR too large for GitHub to render. Additive, so not a v1.0
  gate. Proposal received in f77de08; working spec
  `~/projects/dpsd-new/scripts/publications_summary.py`
  - Subsumes the parallel-run lesson: diff every schema field against an
    explicit ignore-list, not identity fields only
  - Name the partial-fetch hazard in the docs alongside it: a rate-limited
    fetch yields valid-but-smaller JSON that reads as mass removals
  - Undecided: stdout only or also an `action.yml` output; shrink guard in scope

## Low
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
