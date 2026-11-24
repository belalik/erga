# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

(empty)

## 2026-11-23, dpsd-new (timmy): CiteSeerX landing URLs in OpenAlex are dead, the original PDF sits in `raw_source_name`

- **Provenance and trigger:** dpsd-new session on timmy, 2026-11-23, tracing one of the XPAC leads in erga's entry of the same day, for a batch 5 confirmation email. `W7095382982` ("A Virtual World Installation in an Art Exhibition", Vosinakis and Xenakis; CiteSeerX, XPAC, no year): its only location's `landing_page_url` is `http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.224.3635`.
- **What was seen:** `citeseerx.ist.psu.edu` now answers every path tried, the bare root included, with a 301 to a Wayback snapshot dated 2025-12-30. For this path the snapshot returned 429, then 404 on a variant, and the Wayback availability API lists no snapshot of it. The same location's `raw_source_name` holds the PDF's original URL, `http://www.syros.aegean.gr/users/spyrosv/papers/techmuseums11.pdf`, which serves the paper (15 pages, PDF created April 2011, title and both authors on page 1). Whether CiteSeerX is retired for good is not known here.
- **Hypothesis, one record checked:** other CiteSeerX locations may carry their source PDF in `raw_source_name` the same way.
- **Possibly relevant** to the queued read-only `verify` listing of XPAC-only works: a CiteSeerX row linked by `landing_page_url` would send the reviewer to a dead page, while `raw_source_name`, when it is a URL, may be the link that works. Its host and file name can also hint at owner and date (here a staff member's old personal page, a name ending in `11`).

## 2026-11-24, dpsd-new (timmy): a peer-reviewed article with an mEDRA DOI never reaches the fetch

- **Provenance:** Ioannis Xenakis's reply to dpsd-new's confirmation round (batch 5, 2026-11-24); every check below was run in that session.
- **Observed:** `10.53242/syzetesis/112` (*Syzetesis* XII (2025), pp. 121-143, double-blind peer review, single author, on his ORCID record) resolves through doi.org to the journal's PDF, and `https://doi.org/ra/10.53242` names **mEDRA** as the registration agency. `api.openalex.org/works/doi:10.53242/syzetesis/112` and `api.crossref.org/works/10.53242/syzetesis/112` both answer 404, and an OpenAlex `title.search` with `include_xpac=true` returns 0. A title search for one of his works that OpenAlex does have returned it, so the search itself worked.
- **Cost:** a manual entry is the only route in. dpsd-new added one (`src/data/publications_manual.yml`) as a deliberate exception to its rule that works OpenAlex lacks stay out.
- **Hypothesis, unverified (one case):** OpenAlex's DOI coverage rests on Crossref and DataCite, so DOIs from other agencies (mEDRA here; perhaps JaLC, KISTI, CNKI) on a member's ORCID would be missing systematically, not by chance.
- **Possibly useful for erga:** wherever erga reports ORCID DOIs that the fetch lacks, it could name the DOI's agency (`doi.org/ra/<prefix>`). A consumer would then see at once that the gap is upstream coverage, not attribution, and that only a manual entry fixes it.
- **A second data point, for the XPAC `verify` listing already queued:** the same reply confirmed a real XPAC-only work, `W7095382982` (a CiteSeerX copy of a 2011 conference paper with Vosinakis, no year or venue on the record). The venue came from Vosinakis's ORCID record. It is now a manual entry too.
