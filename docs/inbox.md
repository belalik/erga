# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

(empty)

## 2026-11-21, dpsd-new (timmy): every XPAC work on one profile is real, and two manual-entry gaps

- **Provenance:** dpsd-new session on timmy, 2026-11-21, after Κυριακουλάκος's reply (2026-11-18) to his batch 4 list; OpenAlex queried live the same day.
- **Seen:** `author.id:A5037482370,is_xpac:true` returns 5 works, and every one is his and real: two Kallipos books, two CEEGS 2024 papers, and a Griffith repository record (`W7027632552`, 2021, type other, no DOI, submitted version) that he confirmed is a separate work, published in ASIFA Magazine (online 2024-12-17). All five are manual stopgaps in dpsd-new now. Evidence for the `include_xpac` decision you deferred until the cohort reaches 17 (batch 5 is next).
- **Gap 1, a fixture shape:** manual entries accept no URL (`MANUAL_KEYS`, v0.9.5), so a DOI-less work with an online home renders unlinked.
- **Gap 2, a dedup shape:** if `include_xpac` is turned on, the Griffith record arrives with no DOI and a title that differs from the manual entry's by "south east" against "Southeast" (and case), so DOI dedup cannot pair them and title dedup may not; dpsd-new's comment says to remove the manual entry and patch the record instead, but a consumer that forgets gets a duplicate.
- **Proposal:** weigh the five in the XPAC decision; consider a `url` key for manual entries; check whether title dedup pairs a compound-word spacing variant.

## 2026-11-21, dpsd-new (minis): batch 5 so far, a census of the curation, and Google Scholar as a second source

- **Provenance and trigger:** dpsd-new's publications batch 5, run 2026-11-21 on erga 0.9.5 (the pinned version). Four of its six people were entered: Arnellos, Spyrou, Kyratzi and Papakostopoulos. Afterwards Thomas asked whether the problems the cohort keeps hitting come from the task itself, from OpenAlex or from erga's design, whether a stable and useful erga is near, and whether a tool such as a Google Scholar MCP server could cross-check identities. He asked for the question to reach erga as food for thought, not as a request.
- **Batch 5 so far, observed:**
  - XPAC per profile: Arnellos 12 of 65 (copies, fragments such as "signatures for" and "Reviewed by:", five thin undated items); Spyrou 0 of 45; Kyratzi 2 of 26, one of them her 2022 Kallipos textbook (now a manual entry, as Kyriakoulakos's were); Papakostopoulos 0 of 22.
  - Two ORCID records hold no employment, and Papakostopoulos's holds no works either, so both iDs were confirmed from the works OpenAlex links to them.
  - Papakostopoulos has a detached one-work entity (`A5000470365`, a 1999 *Applied Ergonomics* paper with Marmaras). It is now a manual entry, taken as his without asking him.
  - Curation came to ten actions over 133 works, and no contamination was found. The actions: a thesis typed article; an LNCS volume duplicating an edited-volume record; a list of conference programmes; a draft PDF whose title starts "This is a draft version"; an Emerald abstract DOI standing in for the article's (both DOIs resolve to `W2097736080`); a title prefixed "Darzentas.:"; an OUP chapter Crossref types "book"; a Zenodo conference paper dated by its upload year; an EVA paper typed other; an edited volume to tag.
- **Census of dpsd-new's curation, counted 2026-11-21:**
  - `publications_overrides.yml` holds 83 entries: 44 excludes and 39 patches. The patches touch venue 26 times, type 16, date 7, authors 7, year 5 and title 5.
  - `publications_manual.yml` holds 24 entries: stopgaps for detached entities, XPAC works and works with no author entity.
  - Read against `docs/publications.md` → Cohort, nearly all of them answer upstream data: identity (a homonym, entities mixing two people, detached entities, a husband merged into his wife's profile), metadata (deposit dates, wrong types, wrong DOIs, junk titles) and data that moves (XPAC, preprint pairs merging and splitting, retypes on refresh).
  - The session's reading, an inference: erga's layers (curation that survives refreshes, `verify`, the PR gate) held, and its changes were additions rather than redesigns.
- **Google Scholar, observed:** `google-scholar-search-mcp` 2.4.0 (PyPI, one maintainer, 2 GitHub stars, 14 releases since 2026-04, six of them in the week of 9 to 16 November), read 2026-11-21:
  - It scrapes Scholar through the `scholarly` library.
  - Its README says author profile pages now need a signed-in Google session, so it has no author tool.
  - It mentions no ORCID and no DOI.
  - It warns that default access often meets Scholar's bot check, and that an IP may be blocked for 24 to 48 hours.
- **From recall, not checked:** Google offers no Scholar API and its terms forbid automated access. Scholar profiles add works automatically by default, so they carry errors, and they do not link to ORCID. So Scholar could not verify an iD.
- **Proposal, erga's call:**
  - Whether the census answers Thomas's question well enough to record. To the session it suggests that the remaining cost is curation, which never reaches zero in this domain.
  - Whether drafting curation stubs for review (the 2026-09-26 proposal) and a short guide to judging identity are the steps that would make erga usable by a maintainer working without a session.
  - Whether Scopus (author ids on 15 dpsd-new staff records; access by the university's network, routed 2026-11-08), rather than Scholar, is the second source worth testing.
