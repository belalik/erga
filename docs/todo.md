# TODO

## High
- Release v0.3.0; README and docs/action.md already reference the
  `belalik/erga@v0.3.0` tag and PyPI release, neither of which exists yet

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
- CSL-JSON and BibTeX emitters (before the v1.0 promotion push)
- `erga verify`: search OpenAlex by configured names too, and flag same-name
  profiles missing from the config
- `erga verify`: flag a configured ORCID carried by several OpenAlex
  profiles, the failure mode that made the old README sample fetch 1022
  strangers' works
- Config knob to exclude types from output (erratum/editorial front matter);
  until then, per-record `exclude: true` overrides cover it
