# TODO

## High

## Normal
- Normalize reconstructed abstracts: decode HTML entities (unescape
  until stable — double-encoded `&amp;#039;` exists in the wild) and
  strip tags (`<br>`). The origin pipeline did this; the convergence
  compare never covered abstracts, and 6 of smartmove's 187 differ, one
  visibly (renders a literal `&#039;`). Same gap in open_access: erga
  correctly finds 2 OA URLs origin missed — fine, but uncompared

## Low
- CSL-JSON and BibTeX emitters (before the v1.0 promotion push)
- `erga verify`: also search OpenAlex by configured names and flag
  same-name profiles missing from the config (would have surfaced the
  conflated homonym profile the v0.2 run found)
- Config knob to exclude types from output (erratum/editorial front
  matter); until then, per-record `exclude: true` overrides cover it
