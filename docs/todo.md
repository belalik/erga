# TODO

## High
- Declared home for the contamination check, target v0.5.0. Decided
  2026-09-02 together with dpsd-new's identity entry: optional `home:` at the
  top level (a ROR id; OpenAlex authorship institutions carry `ror` as a
  full `https://ror.org/...` URL under the existing select, verified live
  2026-09-02) with a per-author override. Used only by the check: home
  country and home institution come from the declaration instead of the
  plurality, the majority gate is bypassed, and when most affiliated works
  are not at home the check says the profile looks wrong (verify's question)
  instead of listing them as strangers. Institution country from the corpus
  labels, else one `/institutions/ror:` fetch. Never identity evidence; the
  docs say it is trusted as given, like the ORCID. The Zissis trap (a wrong
  same-name profile carrying the right institution) is a wrong-person
  failure, which this field does not touch in either direction. Motivation
  in numbers: at 20-80 works the gate silences 7 of 40 authors
  (docs/requirements-v1.md section 7)

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
