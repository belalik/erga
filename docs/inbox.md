# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## 2026-09-25 · from dpsd-new (minis) · A live homonym pair the cluster check is blind to by construction

**Provenance:** dpsd-new byline confirmation work, minis, 2026-09-25 (`docs/staff-bylines.md` → "A same-surname pair already exists inside the department"). Thomas confirmed the identities; the OpenAlex facts below were read live from `api.openalex.org/authors?search=Darzentas` the same day. Neither person is tracked in dpsd-new's `erga.yml` yet, so nothing here was run through erga; this is a fixture offer, not a measured verdict.

**Trigger / what's there:** two Aegean staff, spouses, same surname, same department, overlapping careers. John Darzentas (`A5109152625`, 62 works, **no ORCID**, University of the Aegean) and Jenny Darzentas (`A5028359938`, 95 works, ORCID `0000-0003-3843-7083`, same institution). In dpsd-new's 626-work corpus they have 14 and 13 co-authorships with the tracked cohort, 6 of them shared. Both OpenAlex entities carry **"J. Darzentas"** in `display_name_alternatives`: OpenAlex has split the initial-only bylines between the two by its own disambiguation, and any work it put on the wrong side has the *same* institution and the *same* co-authors as the right ones. That is the failure mode the README names as invisible to `verify` (correct iD, profile collected a stranger's works), and here the `build` cluster warning is also silent by construction: there is no detached cluster, the stranger sits inside the career. The Malisova case (Czech homonym, different country) is the detectable end of this; this pair is the undetectable end, and it is real, stable and public.

- As a fixture: two entities whose alternatives intersect on an initial-only form is a cheap, purely structural signal (`display_name_alternatives` overlap between a resolved author and a same-surname, same-institution neighbour), available from the authors endpoint without fetching works. Whether erga wants to warn on it is its call; the pair lets the warning be tested against ground truth Thomas can supply per work.
- The no-ORCID side (John) would be tracked by pinned `openalex_id`, as Papanikos is. If erga's `verify` name search around a pinned id could list same-surname entities at the same institution and their shared alternatives, this is the case it would catch.
- Caveat on the numbers: the 62 / 95 counts are OpenAlex's, not vetted; the 14 / 13 / 6 are corpus-internal co-authorship counts.

No tier or breadth verdict — triage here decides.

## 2026-09-25 · from dpsd-new (minis) · Member confirmation round started: per-profile ground truth is coming

**Provenance:** dpsd-new, minis, 2026-09-25. Thomas sent one group email to six tracked members (Gavalas, Zissis, Koutsabasis, Xidias, Papageorgiou, Stavrakis) with each person's list link, work count and the ORCID the fetch used, asking three ordered questions: works that are not theirs, glaring omissions, wrong metadata. A reply is "all fine" or a title/DOI. The text names erga and links the repo, and some recipients are technical, so questions or issues may also arrive on GitHub directly.

**Trigger / what's there:** this is the first time erga's output on real profiles gets checked by the people themselves, and each reply is a verdict erga's own checks can be scored against. A foreign work a member reports is a contamination `verify` and the cluster warning either flagged or missed; an omission says whether the gap was OpenAlex, the ORCID link or the fetch. dpsd-new will route the outcome per profile when replies arrive: what was reported, what erga had warned on that profile, how it was fixed (override / manual entry). Until then, one thing erga could decide on its side: the shape it wants such ground truth recorded in, a fixture format or a doc, so the results land in a form its tests can use.

No tier or breadth verdict — triage here decides.

## 2026-09-25 · from dpsd-new (minis) · Three OpenAlex types unmapped on a 626-work department corpus

**Provenance:** dpsd-new, minis, 2026-09-25, the first v0.7.0 build (dry run, nine authors, 692 fetched, 626 written) after upgrading from v0.5.0. Same corpus and config as the 2026-09-22 measurements, plus Koronis's three-home list, which silenced his wrong-profile line as erga predicted while the three known clusters (Essex 2, Toronto 7, Palacký 5) still warned.

**Trigger / what's there:** the build's warning block opened with three lines of the form `unmapped OpenAlex type '<t>' on N work(s) falls back to "other" (upstream vocabulary drift?)`: `conference-abstract` (1), `peer-review` (2), `reference-entry` (10). Answering the question the warning asks: these are not drift on our side, they are types OpenAlex carries that the map does not list. No harm here, since the site's own bucketing sends anything unknown to `other` too. Two things erga might take from it: the three names, as candidates for the type map (`reference-entry` at 10 works is the one a reviewer would notice on a rendered list); and whether the warning should fire on every build for a type that is stably unmapped, since it will now head every weekly PR body for this site until the map changes.

No tier or breadth verdict — triage here decides.

## 2026-09-25 · from dpsd-new (minis) · First three member replies, scored against what erga had said about each profile

**Provenance:** dpsd-new, minis, 2026-09-25, the confirmation round announced in the entry above. Three of six replied the same day (Gavalas, Koutsabasis, Stavrakis); Thomas relayed the emails, and every item below was checked against the built JSON, the live OpenAlex record and Crossref before being acted on. Fixes went into `publications_overrides.yml`; a v0.7.0 dry run of the live config bound every entry (no stale-override warning, 15 excluded, 1 removed, exit 0).

**Trigger / what's there:** the ground truth the earlier entry promised, one line per question erga's checks could be scored on.

- **Foreign works:** none reported by any of the three. On Gavalas the cluster warning fired on his 2 Essex works, which are his own PhD years (staff record: MSc 1997, PhD 2001, Essex) — a true cluster, benign, as the site's doc had predicted from his CV. Papanikos and Malisova still warn as before; both are known.
- **Omissions:** Koutsabasis said "some seem missing against the total number, doesn't matter". Measured: OpenAlex profile 103 works, ORCID 113 work groups, site 91. The 103→91 step is entirely erga's own curation and all of it deliberate: 9 title-cluster merges (six republished chapters/articles that OpenAlex holds twice, three preprint versions of one 2025 paper) and 3 editorial artefacts excluded by override (two PCI author responses, one workshop preface). The 113→103 step is upstream, ORCID entries OpenAlex never linked. So the fetch lost nothing. What would have answered him from the build log instead of a diff script: a per-author line in the summary of the form fetched / merged away / excluded / written.
- **Wrong metadata:** Gavalas, 5 reports on 212 works, all confirmed, mechanisms in the next entry. Stavrakis, 1 report: a co-author rendered in Greek script, mechanism in the entry after.
- **Two asks outside erga's scope, for the record:** Gavalas wants citation counts shown per work (site side; `cited_by_count` is already in the JSON) and remarked that Scopus is the more established source, closed but reachable free from a university server.
- **A summary-page detail seen on the dry run:** the "Other changes" table counted the override-driven updates (type 4, date 3, venue 3, year 3, title 1) under the footer "_Metadata drift from OpenAlex. Nothing to action._". The `Override.changed` flag already exists; the page could report "N field updates from overrides" separately, so a reviewer of the weekly PR can tell curation from drift.

No tier or breadth verdict — triage here decides.

## 2026-09-25 · from dpsd-new (minis) · Three metadata mechanisms behind one member's five corrections

**Provenance:** dpsd-new, minis, 2026-09-25, Gavalas's reply (previous entry). Each mechanism was traced to the raw OpenAlex or Crossref record read live the same day; the record ids are real and public, so any of them works as a fixture.

**Trigger / what's there:**

- **Year from the DOI deposit, not the publication.** Three IEEE conference papers (`10.1109/icc.1999.765564`, `10.1109/iscc.1999.780940`, `10.1109/glocom.1999.831671`) carry `publication_date` 2003-01-20/22. Crossref has `created` on those dates and no `published` part: IEEE registered its back catalogue in 2003, and OpenAlex took the deposit date. The DOI string and the proceedings title both say 1999. A four-digit year inside the DOI, or inside the venue string, that disagrees with `publication_year` is a cheap check; on IEEE DOIs the year segment is structural, so false positives should be rare. Fixed here with `year: 1999` and `date: null` per record, since the day is unknown.
- **A DOI-less twin with a truncated title escapes the title cluster.** `W2187126214` "Optimal Itinerary Planning for Mobile Agents-Based" (2005, no DOI, no source, landing page `ieeexplore.ieee.org/iel5/10511/33285/01577368.pdf`) sits beside `W1989464483` with DOI `10.1109/glocom.2005.1577368`. The title is a strict prefix of the sibling's, and the IEEE article number in the landing URL equals the DOI's last segment. Either signal would pair them: prefix-title clusters within one tracked author and year, or an article-number match between a landing URL and a DOI. Excluded by id here.
- **A repository as `primary_location` sets both venue and type.** `W2152130239` "Status and trends of wireless Web technologies": primary location is WestminsterResearch (source type `repository`, `submittedVersion`), so venue became the repository and type `book-chapter`; the second location has source type `conference` (IASTED CSN 2006, DBLP `conf/iastedCSN/GavalasEK06`). Preferring a non-repository location for venue and type when one exists would have got both right. Patched here.
- **Theses typed `article`, smaller and probably not worth a rule:** two CiteSeerX records with no source and no DOI (`W2340508876` PhD 2001, `W2187394579` MSc 1997, both Essex). The MSc record lists the author twice and a third author named "Supervisor M. C. Sinclair", which is a thesis tell if erga ever wants one. Patched to `thesis` here, with the authors list replaced.

No tier or breadth verdict — triage here decides.

## 2026-09-25 · from dpsd-new (minis) · Author names follow OpenAlex's entity display_name, which drifts and can change script

**Provenance:** dpsd-new, minis, 2026-09-25. Stavrakis's reply pointed at one co-author on the live list printed as «Αναστάσιος Θεοδωρόπουλος» among fourteen Latin names (`W4416393188`, Sensors 2025). Traced in `normalize.py:125`: the name is `author.display_name` first, `raw_author_name` only as fallback. The byline on the paper is "Anastasios Theodoropoulos"; the Greek form was the OpenAlex author entity's display name at the 2026-09-22 fetch.

**Trigger / what's there:** counted on the site's built JSON of 09-22 against the CI branch's fetch of 09-25 (same config, 626 works). Five author entities carried Greek-script display names on the 22nd, 32 authorships across the corpus (Τσερπές 16, Δομέτιος 10, Κώστας 4, Θεοδωρόπουλος 1, Κουρκούτας 1); by the 25th all five had flipped to Latin upstream, the Greek form now in `display_name_alternatives`. The weekly PR fixes this instance by accident, and the next flip can go the other way. Three more names are stable and wrong differently: a Greek capital homoglyph inside an otherwise Latin name ("Eleni Κ. Efthimiadou" 4, "Yiannis Ν. Kontos" 2, "Alexis Τ. Kermanidis" 1; Κ Ν Τ are U+039A, U+039D, U+03A4), present in both fetches. Both shapes are invisible to a grep for Latin letters and neither comes from the paper. Options erga could weigh: fall back to `raw_author_name` when the entity name's script differs from the byline's; normalise a lone Greek capital homoglyph (ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ) inside an otherwise Latin token; or warn per build with a count. The per-work override is no remedy at this grain, since `authors:` replaces the whole list of a work, seven works for the three homoglyph names alone.

No tier or breadth verdict — triage here decides.
