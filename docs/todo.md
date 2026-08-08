# TODO

## High

## Normal

## Low
- v0.3 Action packaging, notes from the first consumer's CI: pin
  setup-uv to an exact version inside `action.yml` (its repo has no
  moving major tags), set `enable-cache: false` for the uvx pattern
  (cache warns every run without a lockfile), give the `version` input
  no default so consumer pins stay deliberate, and mint the moving `v1`
  tag deliberately (requirements promise one)
- Consumer recipes doc once a second consumer exists; start with the
  Jekyll recipe proven in the flip: config at `_data/erga.yml` puts
  output where Jekyll wants it, and Jekyll exposes the config as
  `site.data.erga` so templates iterate the authors list directly
- Second consumer should exercise the surface the first didn't: manual
  entries, `exclude`/`keep_distinct` override paths, ORCID-based
  resolution, `erga verify`, thesis/software types in templates,
  keyless runs
- Parallel-run harnesses for future adoptions must diff every schema
  field with an explicit ignore-list (cited_by_count), not identity
  fields only — in the v0.2 run both real deltas (abstract entities,
  open-access URLs) sat exactly in the uncompared fields
- CSL-JSON and BibTeX emitters (before the v1.0 promotion push)
- `erga verify`: also search OpenAlex by configured names and flag
  same-name profiles missing from the config (would have surfaced the
  conflated homonym profile the v0.2 run found)
- Config knob to exclude types from output (erratum/editorial front
  matter); until then, per-record `exclude: true` overrides cover it
