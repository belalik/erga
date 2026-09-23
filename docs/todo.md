# TODO

## High

## Normal
- Release the `home:` list form (on main since 2026-09-23, a new config
  shape, so a minor bump), then route dpsd-new its two actions: Koronis's
  entry becomes `home: [https://ror.org/03zsp3p94,
  https://ror.org/05j6fvn87, https://ror.org/01c27hj86]` (the Aegean,
  SUTD, Lisbon; silent on his record re-fetched 2026-09-23), and its
  `docs/publications.md` says `home: null` removes the check, which is
  false: it returns the author to the inferred rule
## Low
- Add `orcid:` under the author in `CITATION.cff` once Thomas confirms
  his iD: the one public record under his name (0009-0001-3431-2825,
  empty, 2023) is unconfirmed; orcid.org's forgot-iD form settles it
- Three OpenAlex types warn on every dpsd-new build and fall back to
  `other`: `reference-entry` (10 works: encyclopedia entries in two
  editions, a handbook chapter under two DOIs), `peer-review` (2, author
  responses), `conference-abstract` (1). Map them or declare them
  unmapped on purpose; the warning fires on raw works before curation,
  so an override cannot silence it
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
