# TODO

## High

## Normal

## Low
- Mint the moving `v1` tag with the 1.0 release; policy in docs/action.md
- Consumer recipes doc once a second consumer exists; the Jekyll specifics
  proven in the flip are already in docs/action.md. Open it with the
  consumer contract: what erga asks of a consumer site (ORCID iDs, owned
  config, reviewed curation, API key at scale) and what it guarantees
- Second consumer should exercise the surface the first didn't:
  `exclude`/`keep_distinct` overrides, ORCID-based resolution, `erga verify`,
  thesis/software types in templates, keyless runs
- Parallel-run harnesses must diff every schema field with an explicit
  ignore-list (cited_by_count), not identity fields only: in the v0.2 run
  both real deltas sat exactly in the uncompared fields
- Top-level `authors` roster in the output (canonical name, orcid, resolved
  id): additive; covers zero-work authors and makes the site-roster join
  explicit. Decide during the consumer #2 pilot
- Publish a formal JSON Schema for the output and validate against it in
  tests (pre-v1.0): consumers get machine-checkable contract + generated
  types (Astro/TS)
- CSL-JSON and BibTeX emitters (before the v1.0 promotion push)
- Per-author review export (markdown per tracked author) so the maintainer
  can send each person their list for confirmation before publishing; shape
  the format after the consumer #2 pilot. A sibling of the other emitters
- Year-cutoff knob (global; maybe per-author) as an output convenience, post-
  v1. Decided with consumer #2: fetch stays full-career, period views are the
  renderer's job; this knob would only spare consumers that filter
