# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

(empty)

## 2026-11-24, dpsd-new (minis): after launch, dpsd-new will take works OpenAlex lacks from each member's ORCID, reviewed once; two data points on ORCID's DOI-less entries

- **Provenance and trigger:** Ioannis Xenakis's email of 2026-11-24 17:51, answering dpsd-new's confirmation round. He argued that the department should not leave members' works out, and proposed that the site pull from ORCID, with members responsible for keeping it current. Thomas adopted the idea the same day as the method for the after-launch catch-up already decided (dpsd-new `docs/backlog.md` → Future Features).
- **The consumer's decision:** after the switch, works OpenAlex does not have are drafted from each member's ORCID and reviewed once before they enter `publications_manual.yml`; never pulled unreviewed each week. Members are told their ORCID is where they add what is missing (dpsd-new `/el/site-feedback/`). This leaves erga's ruling of 2026-09-26 (ORCID a check, never a record source) as it stands on the fetch side; the queued proposal to draft reviewable `manual.yml` stubs now has a consumer and a date (after dpsd-new's cutover, expected early December 2026).
- **Data point 1, read live from `pub.orcid.org/v3.0/0000-0001-5607-3514/works` the same day:** a record the owner does not recognise ("Sharing the Experience of Real and Virtual Visitors in Museums and Exhibitions", book-chapter, 2011, Re-Thinking Technology in Museums, no external ids) has `source` = the owner's own account. Self-entered does not mean verified by the owner, so a stub drafted from ORCID still needs the review.
- **Data point 2, same record:** a real paper of his (Vosinakis and Xenakis 2011, the same conference, pp. 253-264) is absent from his ORCID and present on his co-author's. A stub generator reading only each member's own ORCID would miss it; reading tracked co-authors' records too, and attributing by byline, would catch it.
- **Possibly useful:** when stubs are drafted, mark the ORCID `source` (owner, or an importer such as Scopus or Crossref) and the absence of external ids, so the reviewer knows which drafts are thinnest.
