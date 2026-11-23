# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

(empty)

## 2026-11-23, dpsd-new (timmy): CiteSeerX landing URLs in OpenAlex are dead, the original PDF sits in `raw_source_name`

- **Provenance and trigger:** dpsd-new session on timmy, 2026-11-23, tracing one of the XPAC leads in erga's entry of the same day, for a batch 5 confirmation email. `W7095382982` ("A Virtual World Installation in an Art Exhibition", Vosinakis and Xenakis; CiteSeerX, XPAC, no year): its only location's `landing_page_url` is `http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.224.3635`.
- **What was seen:** `citeseerx.ist.psu.edu` now answers every path tried, the bare root included, with a 301 to a Wayback snapshot dated 2025-12-30. For this path the snapshot returned 429, then 404 on a variant, and the Wayback availability API lists no snapshot of it. The same location's `raw_source_name` holds the PDF's original URL, `http://www.syros.aegean.gr/users/spyrosv/papers/techmuseums11.pdf`, which serves the paper (15 pages, PDF created April 2011, title and both authors on page 1). Whether CiteSeerX is retired for good is not known here.
- **Hypothesis, one record checked:** other CiteSeerX locations may carry their source PDF in `raw_source_name` the same way.
- **Possibly relevant** to the queued read-only `verify` listing of XPAC-only works: a CiteSeerX row linked by `landing_page_url` would send the reviewer to a dead page, while `raw_source_name`, when it is a URL, may be the link that works. Its host and file name can also hint at owner and date (here a staff member's old personal page, a name ending in `11`).
