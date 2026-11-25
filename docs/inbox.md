# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

(empty)

## 2026-11-24, dpsd-new (minis): after launch, dpsd-new will take works OpenAlex lacks from each member's ORCID, reviewed once; two data points on ORCID's DOI-less entries

- **Provenance and trigger:** Ioannis Xenakis's email of 2026-11-24 17:51, answering dpsd-new's confirmation round. He argued that the department should not leave members' works out, and proposed that the site pull from ORCID, with members responsible for keeping it current. Thomas adopted the idea the same day as the method for the after-launch catch-up already decided (dpsd-new `docs/backlog.md` → Future Features).
- **The consumer's decision:** after the switch, works OpenAlex does not have are drafted from each member's ORCID and reviewed once before they enter `publications_manual.yml`; never pulled unreviewed each week. Members are told their ORCID is where they add what is missing (dpsd-new `/el/site-feedback/`). This leaves erga's ruling of 2026-09-26 (ORCID a check, never a record source) as it stands on the fetch side; the queued proposal to draft reviewable `manual.yml` stubs now has a consumer and a date (after dpsd-new's cutover, expected early December 2026).
- **Data point 1, read live from `pub.orcid.org/v3.0/0000-0001-5607-3514/works` the same day:** a record the owner does not recognise ("Sharing the Experience of Real and Virtual Visitors in Museums and Exhibitions", book-chapter, 2011, Re-Thinking Technology in Museums, no external ids) has `source` = the owner's own account. Self-entered does not mean verified by the owner, so a stub drafted from ORCID still needs the review.
- **Data point 2, same record:** a real paper of his (Vosinakis and Xenakis 2011, the same conference, pp. 253-264) is absent from his ORCID and present on his co-author's. A stub generator reading only each member's own ORCID would miss it; reading tracked co-authors' records too, and attributing by byline, would catch it.
- **Possibly useful:** when stubs are drafted, mark the ORCID `source` (owner, or an importer such as Scopus or Crossref) and the absence of external ids, so the reviewer knows which drafts are thinnest.

## 2026-11-25, dpsd-new (minis): correction to the 2026-11-24 entry's data point 1, and what dpsd-new's review of an ORCID draft consists of

- **Provenance and trigger:** Thomas and the session re-read Xenakis's email of 2026-11-24 17:51 on 2026-11-25, before the reply went out; his public ORCID works and Vosinakis's (`pub.orcid.org/v3.0/0000-0003-1735-4297/works`) were read live the same day. The reply was sent 2026-11-25.
- **Correction:** data point 1 said the owner "does not recognise" the record "Sharing the Experience of Real and Virtual Visitors in Museums and Exhibitions". He wrote only "Το άλλο δεν ξέρω τι είναι", answering a question that had not told him the title sits on his own ORCID. So this case does not show that a self-entered record can be unknown to its owner; the entry's conclusion (a stub drafted from ORCID still needs the review) rests on dpsd-new's other evidence, not on this.
- **Observed on 2026-11-25:** the record's `source` is his own account and its `created-date` is 2022-03-22, the day nine of his seventeen self-entered records were created. At that conference (Re-thinking Technology in Museums 2011) his ORCID lists one record, under this title, and lacks the real title; Vosinakis's ORCID lists one paper there, under the real title ("A Virtual World Installation in an Art Exhibition: ..."). A standard web search for the exact title returned no work.
- **Inference, unconfirmed:** the same paper under another title. The reply asks him; dpsd-new will route his answer.
- **Possibly a fixture if he confirms:** one work, two titles, on two co-authors' ORCID records, no external id on either. A title match cannot pair them; venue plus year plus a tracked co-author can.
- **The consumer's review, as the reply promised the member:** two questions per drafted entry (is the work already on the list under another title; are title, year, venue and co-authors complete), and the author is asked where an entry is unclear. Possibly useful for what a drafted stub shows its reviewer: candidate matches on the existing list by venue and year, not only by title, and which fields are empty.
- **Also told to the member:** Scopus may be looked at after erga v1.0 "as a possible check that proposes corrections", one clause standing for stage 1 of erga's `docs/scopus.md`. Nothing beyond "possible" was promised.
