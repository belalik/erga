# TODO

## High
- README's sample config uses ORCID's fictional test iD (0000-0002-1825-0097),
  which 69 real OpenAlex profiles carry: the quickstart as written fetches
  1022 unrelated works from 25 strangers. Use an ORCID that resolves to
  nothing, or annotate the sample so nobody runs it verbatim
- Release v0.3.0 — README and docs/action.md already reference the
  `belalik/erga@v0.3.0` tag and the 0.3.0 PyPI release, neither of which
  exists yet

## Normal

## Low
- Mint the moving `v1` tag with the 1.0 release; policy in docs/action.md
- Consumer recipes doc once a second consumer exists; start with the Jekyll
  recipe proven in the flip: config at `_data/erga.yml` puts output where
  Jekyll wants it, Jekyll exposes the config as `site.data.erga` so templates
  iterate the authors list directly, and the author filter is a one-line
  `a.tracked_as` template change with no alias logic in JS
- Second consumer should exercise the surface the first didn't:
  `exclude`/`keep_distinct` override paths, ORCID-based resolution,
  `erga verify`, thesis/software types in templates, keyless runs (manual
  entries and alias tracking now covered by the action CI job)
- Parallel-run harnesses for future adoptions must diff every schema field
  with an explicit ignore-list (cited_by_count), not identity fields only —
  in the v0.2 run both real deltas (abstract entities, open-access URLs) sat
  exactly in the uncompared fields
- CSL-JSON and BibTeX emitters (before the v1.0 promotion push)
- `erga verify`: also search OpenAlex by configured names and flag same-name
  profiles missing from the config (would have surfaced the conflated homonym
  profile the v0.2 run found), and flag a configured ORCID carried by many
  profiles at all — the fictional iD above is the extreme case at 69
- Config knob to exclude types from output (erratum/editorial front matter);
  until then, per-record `exclude: true` overrides cover it
