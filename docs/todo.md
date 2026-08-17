# TODO

## High

## Normal
- Release the contamination check. Reviewed 2026-08-17, the two severe
  findings fixed; four remain, none of them severe: an institution with a
  null `country_code` reads as structurally abroad, the warning's country is
  decided by fetch order, `titles` and `work_ids` are not positionally
  aligned, and a duplicate authorship entry may lose the affiliation
  (unverified against real API shapes). Then re-measure the false-positive
  load on `local/contamination-probes/`, which the fixes invalidated.
  Rationale and standing caveats: docs/requirements-v1.md section 7
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
  case is the worked example to narrate
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
