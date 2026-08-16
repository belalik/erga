# TODO

## High

## Normal
- Work-level contamination check: a homonym sharing the exact Latinized name
  passes every profile-level test verify has, so flag intra-profile outliers
  (works whose affiliation and topic cluster apart from the majority) as
  informational lines. Open: verify fetches 3 titles per profile, so decide
  whether it grows a deeper mode or the check rides on build's work list

## Low
- Mint the moving `v1` tag with the 1.0 release; policy in docs/action.md
- Consumer recipes doc, unblocked now that a second consumer exists. Open it
  with the consumer contract: what erga asks of a consumer site (ORCID iDs,
  owned config, reviewed curation, API key at scale) and what it guarantees.
  Jekyll specifics are already in docs/action.md; the Astro recipe is thin
  (config-relative `src/data/erga.yml` → `publications.json`, imported at
  build time, no schema or convention change), and the empty-unlinked-ORCID
  case is the worked example to narrate
- Surface no consumer has exercised yet, so unproven in the field before
  v1.0: `keep_distinct` overrides, thesis/software types in templates,
  keyless runs
- Parallel-run harnesses must diff every schema field with an explicit
  ignore-list (cited_by_count), not identity fields only: in the v0.2 run
  both real deltas sat exactly in the uncompared fields
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
