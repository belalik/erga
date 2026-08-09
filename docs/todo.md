# TODO

## High

## Normal

## Low
- Mint the moving `v1` tag with the 1.0 release; policy in docs/action.md
- Consumer recipes doc once a second consumer exists; the Jekyll specifics
  proven in the flip are already in docs/action.md
- Second consumer should exercise the surface the first didn't:
  `exclude`/`keep_distinct` overrides, ORCID-based resolution, `erga verify`,
  thesis/software types in templates, keyless runs
- Parallel-run harnesses must diff every schema field with an explicit
  ignore-list (cited_by_count), not identity fields only: in the v0.2 run
  both real deltas sat exactly in the uncompared fields
- Top-level `authors` roster in the output (canonical name, orcid, resolved
  id): makes the faculty-dropdown and site-roster join explicit instead of
  derived from authorships, and covers configured authors with zero works.
  Additive; decide during the consumer #2 pilot
- Publish a formal JSON Schema for the output and validate against it in
  tests (pre-v1.0): consumers get machine-checkable contract + generated
  types (Astro/TS)
- CSL-JSON and BibTeX emitters (before the v1.0 promotion push)
- Per-author review export (markdown, one file per tracked author): the
  maintainer sends each person their generated list for confirmation before
  publishing. Decided with consumer #2; shape the format after the pilot
  batch shows what reviewers ask about. A sibling of the other emitters
- Year-cutoff knob (global; maybe per-author) as an output convenience, post-
  v1. Decided with consumer #2: fetch stays full-career, period views are the
  renderer's job; this knob would only spare consumers that filter
