# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## 2026-09-26 · from dpsd-new (minis) · Works the member's own ORCID lists, sitting in OpenAlex off the resolved profile

**Provenance:** dpsd-new, minis, 2026-09-26. Xanthi Papageorgiou's reply to the member confirmation round (the per-profile outcome the 2026-09-25 entry promised). She sent ten DOIs as missing and guessed at byline variants ("Xanthi Papageorgiou", "X. Papageorgiou" instead of "Xanthi S. Papageorgiou"). Everything below was read live from `pub.orcid.org/v3.0/<iD>/works`, `api.openalex.org` and Crossref the same day, and checked against a scratch `erga==0.7.0 build` and `verify` of dpsd-new's live config.

**Trigger / what's there:** five of her ten were already on her list. The other five are all on her ORCID record, all in OpenAlex, and none on the profile her ORCID resolves to (`A5002110022`, whose `display_name_alternatives` already carry every variant she named):

- `10.1007/978-3-032-23948-8_5`, `_6` (Springer chapters, 2026): on a detached entity "Xanthi Papageorgiou" (`A5135377975`, 4 works, no ORCID, no institution). `verify` did list it, as "same name, not configured", which reads as a possible homonym rather than "your member's works are here". Pinning it would not have been clean: its other two works are Zenodo records that are not on her ORCID.
- `10.1109/ICSC57768.2022.9993912`, `…9993866` (ICSC 2022): on a second detached entity "X. Papageorgiou" (`A5004005331`, 2 works, University of Patras). `verify` does not list it, presumably because the name search runs on the configured name, not on initials.
- `10.1016/j.ifacol.2025.12.437` (IFAC-PapersOnLine 2025, `W7115913671`): no author entity at all. Every authorship has `author.id: null`, so no author-based fetch or check can see it.

`openalex_id` takes one id, so pinning could not have covered both detached entities, and nothing covers the third case. The one signal that caught all five is one erga already holds the key to and does not read: the member's ORCID works list. erga uses the iD only to resolve the OpenAlex profile (no call to `pub.orcid.org` anywhere in `src/erga/`).

**Cohort measurement.** For each of the nine tracked iDs: every DOI on the ORCID record missing from that person's built list, resolved by DOI on OpenAlex and classified. Script: `/home/thomas/projects/dpsd-new/local/orcid_gap.py` (gitignored, minis only; argument: a `publications.json`). Positive control: Papageorgiou's line reproduced the five found by hand.

| | ORCID DOIs not on list | twin on site | on the ORCID-linked profile | detached or unattributed | not in OpenAlex |
|---|---|---|---|---|---|
| Papageorgiou | 8 | 0 | 2 | 5 | 1 |
| Zissis | 4 | 0 | 1 | 3 | 0 |
| Gavalas | 2 | 0 | 0 | 2 | 0 |
| Koutsabasis | 4 | 0 | 4 | 0 | 0 |
| Koronis | 2 | 0 | 2 | 0 | 0 |
| Stavrakis | 2 | 1 | 1 | 0 | 0 |
| Malisova, Xidias, Papanikos | 0 | 0 | 0 | 0 | 0 |

Ten detached works across three of nine members. Every "on the ORCID-linked profile" work was checked and is no gap: fetched, then left out on purpose, either dedup-merged into a twin (her two ISIC 2006 papers sit on site under their CACSD-CCA-ISIC DOIs; Koutsabasis's three SSRN preprints under the Computers & Graphics 2025 version, his IJTHI 2014 under the 2013 JTHI one) or excluded by an override (corrigenda and "Correction to" records: Koronis 2, Stavrakis 1, Zissis 1). Her one "not in OpenAlex" (`10.1109/mobihealth.2014.7015934`) is on site under the EAI DOI of the same paper. So a naive DOI-set difference reports 22 gaps where 10 are real: a reconciliation has to resolve each ORCID DOI to an OpenAlex work and compare against what was fetched, merged and excluded, never DOI strings. Not measured: ORCID entries without a DOI (38 on hers alone), which would need title matching, with the same dedup caution.

**Bears on erga's own todo:** the per-author stage-counts item files a member's 113 ORCID → 103 OpenAlex step as "upstream (ORCID entries OpenAlex never linked) and out of reach". For that member (Koutsabasis) the DOI part is indeed benign, but for three others part of the same kind of gap is reachable.

- The proposal: an ORCID reconciliation step, report-first. Read the tracked iD's ORCID works, resolve each DOI the fetch did not produce, drop those that land on an already fetched, merged or excluded work, and report the rest with the entity each sits on (another id, or none). Whether erga then *adds* them is its call. The ORCID record is the member's own claim, stronger evidence than OpenAlex's clustering, but ORCID lists carry auto-imported errors too, and adding means choosing which authorship is the member (by configured name or alias, or by raw name when no entity exists, as on the IFAC paper).
- A smaller one inside it: `verify`'s "same name, not configured" line could say when that entity's works appear on the configured author's ORCID record, turning a homonym hint into "these are your member's works", for one ORCID read per author.
- dpsd-new's stopgap, to be retired by the above: her five works entered in `src/data/publications_manual.yml` on 2026-09-26, commented for removal once a refresh fetches them (manual wins dedup, so a stale entry would freeze the record). Scratch build: 625 → 630, all five tracked to her, no duplicates. Gavalas's 2 and Zissis's 3 are not entered; that waits on Thomas.

No tier or breadth verdict — triage here decides.

## 2026-09-26 · from dpsd-new (minis) · Addendum to the entry above: her ORCID entries without a DOI

**Provenance:** same session, measured after the entry above was appended; it closes that entry's "Not measured" line for one member.

**Trigger / what's there:** her 38 ORCID entries without a DOI, matched by title: 25 are on her list, 1 is on site under a variant title, and 12 (2009-2024, mostly conference papers) are not in OpenAlex at all, checked with `filter=title.search:` and two long-title positive controls passing. Those 12 are out of reach of any OpenAlex-side fix; only ORCID as a record source, or manual entries, would carry them. A method note for whoever builds the step: OpenAlex's `search=` is full-text and missed even a known title in its top results; `filter=title.search:` is the one that works for this.

No tier or breadth verdict — triage here decides.

## 2026-09-26 · from dpsd-new (minis) · Corrections to the two entries above (same day, same session)

**Provenance:** same session, after both entries above; each correction was re-measured live against OpenAlex. The entries are left as written, per append-only routing; read them through this one.

**Trigger / what's there:** two numbers above overstate, both in the same direction.

- **"12 not in OpenAlex at all" is 11.** `title.search` needs every word of the query in the title, so an ORCID title longer than the OpenAlex title finds nothing: the 2020 i-Walk workshop entry ("The i-Walk Assistive Robot: A multimodal intelligent robotic rollator providing…") is on site as the 2021 chapter titled just "The I-Walk Assistive Robot". The two positive controls both had matching full titles, so neither could catch this. Re-run with the first five words plus `raw_author_name.search:papageorgiou`: 11 stay absent. Totals for her 38 no-DOI entries: 27 on site (2 under different titles), 11 not found. Method note: title matching for reconciliation has to handle subtitle truncation both ways.
- **"Ten detached works across three of nine members" is seven real gaps, plus three records that are not gaps.** Of Gavalas's 2 and Zissis's 3, two are front matter the site's editorial policy drops (DCOSS 2010 "Preface", `10.1109/dcossw.2010.5593281`; TrustCom 2015 "Message from the RTStreams 2015 Workshop Chairs", `10.1109/trustcom.2015.552`), and one is a book (`10.4018/978-1-4666-5820-2`, IGI 2014, presumably an edited volume) whose OpenAlex authorships are wrong: two strangers, one with an ORCID glued into the raw name string. Real gaps: Papageorgiou 5, Gavalas 1 (ICC 2006, `10.1109/icc.2006.255712`), Zissis 1 (JSS 2016, `10.1016/j.jss.2016.06.016`). What this adds to the proposal: members' ORCID lists carry front matter too, so a reconciliation step must run the fetched records' exclusion logic over what it finds. And the two real gaps outside hers have **no author entities at all**, like her IFAC paper: 3 of the 7 are invisible to any author-based fetch, and a DOI-based ORCID reconciliation is the only automatic route to them.

No tier or breadth verdict — triage here decides.

## 2026-09-26 · from dpsd-new (minis) · Second correction, an override limit, and a policy proposal for works OpenAlex lacks

**Provenance:** same session, after the three entries above, which stay as written; read them through this one. Everything re-checked by scratch `erga==0.7.0 build` of dpsd-new's live config.

**Trigger / what's there:**

- **Seven real gaps is six.** Gavalas's ICC 2006 paper (`10.1109/icc.2006.255712`) is on his list already, as a broken copy: `W3099828385`, no DOI, no venue, typed journal. The DOI record his ORCID lists sits in OpenAlex with no author entities. A DOI-only comparison reads the broken copy as absent, a third false-positive class next to DOI twins and deliberate exclusions, and the one my own script fell into after the entry above warned against DOI strings. A manual entry for it showed up in the build summary as "1 removed" because title dedup merged the copy into it; that line, not a DOI check, is what exposed it. Real gaps: Papageorgiou 5, Zissis 1. For the reconciliation step, the case turns a gap into a repair: the work is fetched, but its best metadata sits on a record the fetch cannot reach, so a found DOI can also mean "enrich the copy you have".
- **An override cannot add a DOI.** In 0.7.0 `doi` in an override is only a match key, so `id: W3099828385` plus `doi:` aborts the build ("needs exactly one of 'doi' or 'id' to match on"). It failed loudly, as designed, but the consequence is that a DOI-less record can gain a DOI only by being replaced wholesale with a manual entry, which is what dpsd-new did (one copy out, correct type, venue and DOI; his count unchanged at 211). Whether a patch should be able to set `doi` (for example `set_doi:`, or `doi` as a patch field whenever `id` is the key) is erga's call; this is the case that needed it.
- **Policy proposal, Thomas's question at the site end: what should happen to works OpenAlex does not have?** Measured on one member, 11 of her 38 DOI-less ORCID entries (entries above). The view taken here, offered as a proposal: erga should neither ingest them automatically nor stay silent about them. Automatic ingest from ORCID fails on quality. Her DOI-less entries include typos ("Itegrated", "context-awa re", "Inter- national"), duplicates (two 2017 "Towards a User-Adaptive…", the 2020 i-Walk workshop twin of the 2021 chapter), a chapter typed journal-article, and no co-author lists in the work summaries, which is exactly the class of error the member confirmation round exists to remove. Silence leaves a maintainer who wants completeness to find them by hand. The middle, which matches "automatic curation" rather than "automatic ingest": report them (same ORCID read as the reconciliation step) and emit draft `manual.yml` stubs prefilled from the ORCID record, for a person to review, complete and paste. The site then decides per member whether they enter. dpsd-new's own stance until then: they stay out, since each is a hand-kept record nothing refreshes, roughly 250 of them at the planned cohort of 25, and staff profiles already link each member's ORCID and Scholar for completeness.

No tier or breadth verdict — triage here decides.
