# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## 2026-09-29 · from dpsd-new (minis) · verify's ORCID advice misfires on a cross-script split of one person

**Provenance:** dpsd-new session, minis, 2026-09-29, bumping the site to v0.8.0 (`erga verify`, then a dry run).

**Trigger / what's there:** Modestos Stavrakis's ORCID (0000-0002-0694-6038) now resolves to two profiles: `A5043204875` "Modestos Stavrakis" (53 works) and `A5113438086` "Μόδεστος Σταυράκης" (3 works: his 2009 PhD thesis, `W57574069` with DOI `10.12681/eadd/19140`; the Aegean library's catalog copy of it, `W2963306159`; and a 2021 Greek paper, `10.12681/afiinmec.25676`). All three are his. `_looks_like` shares no token across scripts, so verify warned "look like different people ... remove the orcid and pin openalex_id instead". Following that advice would have dropped exactly the three works. `aliases: ["Μόδεστος Σταυράκης"]` settles the name check, as the docstring intends, but the warning then becomes "ORCID resolves to 2 author ids (split profile; consider pinning openalex_id)", and pinning drops the same works. Both messages advise only the single-profile remedy, while an ORCID-linked second profile that holds real works needs the iD kept. Candidates: name the alias route in the first warning when the other profile's name is in a different script (or transliterate Greek before comparing: Μόδεστος → Modestos is regular), and word the split warning as "judge the second profile's works" rather than "consider pinning". Fixture: the two ids above. The build itself did not warn; only verify did.

No tier or breadth verdict — triage here decides.

## 2026-09-29 · from dpsd-new (minis) · Most "same name, not configured" profiles in the dpsd-new cohort are JST machine translations

**Provenance:** same session. Every profile verify listed under "same name, not configured" for the nine authors was checked against the published list, work by work (OpenAlex `author.id` filter, DOI and title match).

**Trigger / what's there:** Of 9 detached profiles, 4 hold only Japanese machine translations of real papers, titles ending `【Powered by NICT】`, typed article or conference-paper, no DOI: `A5058798701` (Gavalas, 4 works), `A5040504023` (Koutsabasis, 1), `A5106893652` (Zissis, 3, two of them NICT and one an English duplicate), `A5030134532` (Xidias, 1). The rest: a medical homonym (`A5091751261` "D Zissis", case reports), two Zenodo copies of a project deliverable (`A5135377975`, Papageorgiou), one Zissis workshop-titled entry (`A5126290686`, "Big Mobility Data Analytics (BMDA)", likely front matter), and two real detached profiles already known (Papageorgiou `A5004005331`, Stavrakis above). None held a missing work. A reader has to open each NICT profile to learn that. Candidate: label a profile whose works all carry the NICT marker (or a JST source) as "machine translations" in that section. The site keeps the result in its `publications.md` → Gotchas.

No tier or breadth verdict — triage here decides.

## 2026-09-29 · from dpsd-new (minis) · Preprint and published records flip between merged and separate, so DOI excludes flap

**Provenance:** same session; CI refresh of 2026-09-28 (v0.7.0, dpsd-new PR #6) against a local v0.8.0 dry run on 2026-09-29.

**Trigger / what's there:** The Malisova homonym's papers come as preprint and published pairs, and OpenAlex does not keep them stable. On 09-28 the BMC Public Health 2026 paper (`10.1186/s12889-026-26668-y`) was one merged record on her profile under the published DOI, so the override excluding its preprint (`10.21203/rs.3.rs-5798848/v1`, overrides entry 3) "matched nothing" and the stranger's paper arrived as an addition. On 09-29 it was off her profile again (verify's unlinked section listed it as `W7132839818`), and the Family Practice paper (`10.1186/s12875-026-03218-4`) arrived as a record separate from its excluded preprint (`rs-7775668`). The site now excludes both DOIs of each pair, so one "override matched nothing" line is expected most weeks, which trains the reader to skip that warning. A shape erga has no fixture for. Candidates: let an exclude match any DOI among a merged work's locations, not only the primary; or have the warning say when an unmatched DOI's twin (same title cluster) matched. Also for the unlinked-authorship benchmark: that section proposed the homonym's paper as "add any that are theirs" until its DOI was excluded, after which verify dropped it, so the report respects overrides as designed.

No tier or breadth verdict — triage here decides.

## 2026-09-29 · from dpsd-new (minis) · Benchmark data: what OpenAlex fixed on its own in three days

**Provenance:** same session, for the unlinked-authorship section's second benchmark (queued in erga's todo).

**Trigger / what's there:** Between 09-26 and 09-29, with no action from either repo, OpenAlex moved three of Papageorgiou's five stopgap works onto her profile (`W7160440128`, `W7160285383` from the detached `A5135377975`; `W7115913671` IFAC, which had no author ids at all) and attributed Zissis's JSS 2016 paper (`W2949119045`) to his. Still unfixed: the two ICSC 2022 papers on `A5004005331`, and Gavalas's ICC 2006 DOI record (`W2166485328`, author id still null). So on this cohort the gaps a scratch build reported on 09-26 were half gone three days later, which argues for the report staying report-only and for a stopgap's retirement check being cheap to rerun. The v0.8.0 dry run: 630 → 633, curation loaded clean.

No tier or breadth verdict — triage here decides.

## 2026-09-29 · from dpsd-new (minis) · Corrections to two entries above

**Provenance:** same session, re-reading the entries just appended; they stay as written, read them through this one.

**Trigger / what's there:** (1) In the NICT entry, `A5106893652`'s third work is not a "duplicate" in any sense checked: it is an English record whose title matches a work already on the list, which is all the check established. (2) In the benchmark entry, `W7160440128` and `W7160285383` are the Springer chapters' ids as of 09-29. That they sat on `A5135377975` on 09-26 comes from the site's `publications.md`, and whether OpenAlex moved those records or minted new ones was not checked (the detached profile now holds two Zenodo records instead).

No tier or breadth verdict — triage here decides.

## 2026-09-29 · from dpsd-new (minis) · The preprint/published flapping let a homonym work through

**Provenance:** same session, later: the v0.8.0 CI refresh (dpsd-new run 36591757287, PR #6 at `73aa134`), read before merge.

**Trigger / what's there:** Adds evidence to the flapping entry above. The Malisova homonym's 2024 pair had always merged: the published record `10.1186/s12889-024-18384-2` was excluded and its preprint `10.21203/rs.3.rs-3834098/v1` folded into it. This run split the pair, so the published DOI's exclude "matched nothing" and the preprint (`W4391163269`) arrived alone, tracked to her. It sat in the PR's Added list with the homonym's co-author roster, and nothing else flagged it: the contamination warning's count went down (6 to 3) because OpenAlex has meanwhile moved several of the homonym's works to a profile of her own (`A5012087995` "Kateřina Mališová"), so the warning read as improvement while a leak arrived. Four of the seven homonym excludes matched nothing in that run. Caught by a co-author roster check on every Malisova addition; the site now excludes both DOIs of all three pairs. Candidates, beyond the entry above: when an exclude matches nothing, check whether any fetched work shares its title cluster and warn by name ("excluded DOI X is absent, but its preprint/published twin Y arrived"); that one line would have named this leak.

No tier or breadth verdict — triage here decides.

## 2026-09-29 · from dpsd-new (minis) · Correction to the entry above: the homonym's works did not move

**Provenance:** same session, wrap-up self-review, checked live against OpenAlex after the entry above was appended; it stays as written, read it through this one.

**Trigger / what's there:** The entry says the contamination count fell from 6 to 3 "because OpenAlex has meanwhile moved several of the homonym's works to a profile of her own (`A5012087995`)". That was inferred, not checked, and it is wrong. `A5012087995` holds six unrelated works (mercury speciation, trace metals, a 2020 activity-tracker paper), none of the mHealth trials. The three works whose excludes matched nothing in that CI run (`10.1186/s13063-025-08865-z` `W4410541693`, `10.21203/rs.3.rs-7775668/v1` `W4415664258`, `10.1186/s12889-024-18384-2` `W4393357993`) still carry our Malisova's id `A5045528045` on their own work records, queried by DOI the same afternoon. Why the build did not match them is not known here: dedup folding them into another record, or the author-filtered works listing lagging behind the work records, are both possible and neither was tested. The candidate in the entry above stands; the explanation of the falling count does not.

No tier or breadth verdict — triage here decides.

## 2026-09-30 · from dpsd-new (minis) · An edited proceedings volume arrives typed as a journal article

**Provenance:** dpsd-new session, mocking the publications page's type badges; read from dpsd-new's built `src/data/publications.json`.

**Trigger / what's there:** Vosinakis's SETN 2008 proceedings, `W2916396009`, "Proceedings of the 5th Hellenic conference on Artificial Intelligence: Theories, Models and Applications", reach the output with `type: 'journal'`, no DOI and no venue. dpsd-new plans to mark edited volumes by hand with an `edited-volume` tag (its `publications.md` → edited volumes), and had assumed a volume "arrives looking like a book". A corpus shape erga may have no fixture for: a volume whose own record is typed as a journal article, so any type-based handling of editorships (a tag that only relabels books, a check that flags book-typed works with front-matter titles) would miss it. Not checked: what OpenAlex's own `type` / `type_crossref` fields say for this work, or whether erga maps it to `journal` itself.

No tier or breadth verdict — triage here decides.

## 2026-09-30 · from dpsd-new (minis) · Book-chapter venues carry the book series, not the book

**Provenance:** dpsd-new session; Vosinakis's confirmation-round reply (2026-09-30), then a count over dpsd-new's built `src/data/publications.json`.

**Trigger / what's there:** The member reports that on his older chapters the venue names the book series instead of the book, e.g. `W3006289525` (`10.4018/978-1-7998-2871-6.ch006`, "The Use of Digital Characters in Interactive Applications for Cultural Heritage"), venue "Advances in religious and cultural studies (ARCS) book series". It is not his alone: 13 of the site's 66 `book-chapter` records carry a series-like venue by a coarse regex (`series|lecture notes|advances in`, case-insensitive): five IGI Global "Advances in … book series" chapters, Springer series (Design and Innovation twice, Cultural Computing, Materials Science), Lecture Notes in Electrical Engineering, Advances in Intelligent Systems and Computing, and a 1999 "Advances in Intelligent Systems". The regex's recall was not measured; every hit looked like a series by eye. Not checked: which OpenAlex field erga takes the venue from for chapters, or whether Crossref's `container-title` for these DOIs names the book (erga already talks to Crossref for backfill).

The same reply raises a related shape: three chapters of a 2015 open textbook on the Kallipos repository (no DOIs, typed article upstream, retyped `book-chapter` by override on dpsd-new) that the member would rather see as one record for the book. He also expects small errors on pre-2004 records and named none.

No tier or breadth verdict — triage here decides.

## 2026-09-30 · from dpsd-new (minis) · Scopus as a source: a second member asks, with a reason

**Provenance:** dpsd-new session; Vosinakis's confirmation-round reply (2026-09-30). The first ask (Gavalas, 2026-09-25) is already recorded in erga's `todo.md` as out of scope, Scopus being a v1 non-goal.

**Trigger / what's there:** A second member recommends Scopus as the more reliable source: it misses some works, but what it holds has correct metadata. The new part is his reason: ΕΘΑΑΕ (the Greek higher-education quality authority) now assesses staff research performance from Scopus data. That makes Scopus the record Greek departments are measured by, which may matter to erga's intended users beyond this pilot. The consumer side is blocked on access, not on erga: dpsd-new holds no Scopus API key, and Thomas does not know whether the department or university has institutional access or who manages it (asked the member, reply pending). Access terms are recall, unverified here: Elsevier's API keys are self-service, but Scopus search reportedly works only from a subscribing institution's network or with an institutional token. Thomas recalled erga having, or planning, Scopus as a configurable alternative source; the docs record it only as a v1 non-goal. Candidate question for triage: a post-v1 Scopus source or cross-check, given that access would be per-institution.

No tier or breadth verdict — triage here decides.

## 2026-09-30 · from dpsd-new (minis) · Scopus access terms, now checked (addendum to the Scopus entry above)

**Provenance:** same session, later; read from the raw page of Elsevier's IR/CRIS use case (https://dev.elsevier.com/ir_cris_vivo.html) on 2026-09-30. Read the entry above through this one.

**Trigger / what's there:** The entry above gave the access terms as recall. Checked: Elsevier allows an application operated by, or on behalf of, an academic institution with a Scopus subscription to find its researchers' publications (including those from before they joined) and show title, year, source title, DOI, authors, affiliations, document type and citation counts to anyone; abstracts may not be shown publicly; stored metadata may be kept after the subscription ends, with no new retrieval. A third party contracted by the institution needs its own agreement with Elsevier. The API key is free; entitlement comes from the institution's IP range, or an institutional token (issued only to customers, to be kept server-side), so a CI refresh outside the campus network needs the token. For erga this reads as a per-institution optional source that the institution itself must run, never a default. Not confirmed: that Greek universities' Scopus comes through HEAL-Link (search-result summaries only; the library page 404'd to a direct fetch). Quotas not checked.

No tier or breadth verdict — triage here decides.

## 2026-09-30 · from dpsd-new (minis) · Series-as-venue: Crossref names the book (addendum to the series entry above)

**Provenance:** same session, later; one Crossref lookup (`api.crossref.org/works/10.4018/978-1-7998-2871-6.ch006`).

**Trigger / what's there:** Closes one "not checked" of the series-as-venue entry: for the member's IGI chapter, Crossref's `container-title` holds both names, `["Advances in Religious and Cultural Studies", "Applying Innovative Technologies in Heritage Science"]`, series first, book second, while OpenAlex's venue is the series. One DOI only; the order, and whether Springer or Lecture Notes chapters follow the same shape, were not checked.

No tier or breadth verdict — triage here decides.

## 2026-09-30 · from dpsd-new (minis) · The refresh summary called two regressions "nothing to action"

**Provenance:** dpsd-new, reviewing refresh PR #7 (belalik/dpsd-new, CI run 36742683367, erga 0.8.0) before merging; field-by-field diff of the old and new `publications.json`.

**Trigger / what's there:** The summary's "Other changes" table listed `type` 1, `title` 1, `venue` 1 and `open_access` 1 among 40 field updates, under "_Metadata drift from OpenAlex. Nothing to action._" Two of them were regressions a consumer has to act on: W2800028494, a Springer journal article (*Education and Information Technologies*, DOI 10.1007/s10639-018-9724-4), retyped `journal` → `book-chapter`, which moves it between filter groups on the site; and W2767568788, whose title switched from English to the journal's Italian translation («Creare il giocatore computerizzato…»). Both are now pinned by override in dpsd-new. The same record's venue (DOAJ → *Italian Journal of Educational Technology*) and open-access link changed for the better in the same refresh, so a blanket "flag every change on a record" would have cost a correct improvement. What the summary could not tell apart: counts per field say nothing about which record or in which direction. Possible shapes, for triage: name the record and old → new value for low-volume, high-impact fields (`type`, `title`, `venue`), at least below some count; and keep "nothing to action" for the volume fields (`authors`, `cited_by_count`). Only one refresh observed; whether type and title flips recur is not known.

No tier or breadth verdict — triage here decides.
