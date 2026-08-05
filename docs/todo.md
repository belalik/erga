# TODO

## High

## Normal
- v0.2 flip: the origin Jekyll lab site switches from its embedded
  pipeline to erga (parallel outputs fully converged 2026-08-05, 187/187
  records, zero field diffs). Mostly a smartmove-site session: install
  released erga, port config + curation files (prune the 23 overrides erga
  reports redundant, or keep deliberately as regression insurance),
  template tweaks per requirements section 4 schema changes. Erga side:
  none known

## Low
- CSL-JSON and BibTeX emitters (before the v1.0 promotion push)
- `erga verify`: also search OpenAlex by configured names and flag
  same-name profiles missing from the config (would have surfaced the
  conflated homonym profile the v0.2 run found)
- Config knob to exclude types from output (erratum/editorial front
  matter); until then, per-record `exclude: true` overrides cover it
