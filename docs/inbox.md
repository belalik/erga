# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

(empty)

## 2026-11-09 · from dpsd-new (minis) · Proceedings editors appended as authors: a contamination shape no check sees

**Provenance:** dpsd-new's audit of the 2026-11-09 refresh PR (#14, erga 0.9.4), the same day. Excluded on dpsd-new `main` in `91279b2` (`publications_overrides.yml`, by id).

**Trigger / what's there:**

- **The record:** `W2991238467`, "Improving Hydroponic Agriculture through IoT-enabled Collaborative Machine Learning" (2019, no DOI, venue "The Internet of Things"). OpenAlex lists nine authors. The paper's own byline (its landing page, `komninos.info/sites/default/files/samplepaper_0.pdf`, read 2026-11-09) has four: Komninos, Georgiadis, Koskeris, Garofalakis. The other five, Cuomo, Di Lorenzo, Gavalas, Hanke and Mylonas, are the AmI-2019 poster and workshop proceedings editors, appended to the authorship. That is how it landed on Gavalas (tracked) under his real author id, with his real institution.
- **Why nothing caught it:** it is not a same-name stranger. The id, the ORCID and the institution are all correct, and his collaborator Komninos is on the byline, so the stranger warnings and the co-author tell all pass. It sat on his list for weeks, and he did not flag it in his confirmation round (2026-09-25).
- **The tell that was there:** a sibling record, `W3015199473`, "New publication: Joint Proceeding of the Poster and Workshop Sessions of AmI-2019…", listed ten editors as its authors, and all five appended names are among them, in the same order, as the hydroponics record's last five (Komninos, a real author, is one of the ten editors too, so he appears only once). A work whose trailing authors all appear on another fetched record that is a proceedings volume may be this shape. The 9 November refresh removed the sibling and a twin of the paper, and dropped the "New publication:" title prefix, so the record now looks cleaner than it did.
- **Open:** how often OpenAlex does this beyond CEUR-style workshop proceedings is unknown; this is the only case found in dpsd-new's corpus (702 works).

Also, as a data point for 0.9.5: the first live run on dpsd-new (#16) matched the release's control exactly. 95 venues from erga plus 8 from the overrides added for the series it keeps, 97 series resolved (the two IGI chapters whose overrides were dropped included), nothing else.

No tier or breadth verdict: triage there decides.

- Routed from dpsd-new (2026-11-10, minis): a member's own English spelling and her one published byline differ in a digraph. Βιλελμίνη Καλαμπρατσίδου writes "Vilelmini Kalabratsidou" on her own website (Thomas checked) and on the department's old English page, while her one candidate work in the corpus is bylined "Vilelmini Kalampratsidou" (μπ as `mp` there, `b` in her own use). She is not tracked yet (`docs/staff-bylines.md`, Candidate table). Possibly relevant to how erga matches or suggests aliases: a byline search seeded from the person's preferred spelling alone would miss this work; a μπ↔b / ντ↔d variant may need to be an alias rather than a typo.

## 2026-11-10, dpsd-new (minis): Zissis's stray works entered, a third entity pinned, a dataset-typed paper that cannot fold with its preprint

- **Provenance and trigger:** the outcome your 2026-10-17 entry asked for, the seven works on `A5103188414` that dpsd-new settled as his (2026-11-09). Comparing his dpsd-new list with SmartMove's (both erga-built) turned up five more. Everything below was observed on erga 0.9.5 dry runs, OpenAlex, Crossref and DataCite on 2026-11-10, except where marked as inference.
- **Outcome:** nine manual entries in dpsd-new's `publications_manual.yml`: five on `A5103188414` (four MDM 2026 papers, Zenodo `10.5281/zenodo.22092724`) and four whose Zissis authorship has no author entity at all (AegeaNET `10.5281/zenodo.17570823`, "Roads of the Sea" `W7112954265`, GMSA `10.48786/edbt.2024.73`, "Stay the Course" `10.13140/RG.2.2.34719.94883`). The Zenodo copies of the MDM papers on `A5103188414` (`zenodo.20537264`, `.20537360`) were left out. Dry run 702 to 713 works, every addition tracked to him.
- **New shape, a third entity:** `A5136462918`, "Dimitris Zissis", no ORCID, created 2026-01-15, last-known institutions Athena RC and the Aegean, 6 works, all his: EDBT 2026 and its arXiv preprint, an IET 2026 chapter (`10.1049/pbtr053e_ch15`), and three copies of works already fetched (a Publica copy of a Big Data Research paper, a Zenodo copy of an IEEE Access paper, an arXiv preprint of an MDM 2026 paper). dpsd-new pinned it as `openalex_id` beside his ORCID (which resolves to `A5076536574`): the copies dedup away and no contamination warning appeared. So one member's works now sit on four places: his profile, a homonym's ORCID-linked entity, a new no-ORCID entity, and no entity at all.
- **New shape, a paper typed dataset:** `10.48786/edbt.2026.55` and `10.48550/arxiv.2602.11890` have identical titles but stay two records. OpenProceedings registers its EDBT papers at DataCite as `Dataset` (GMSA, EDBT 2024, too), OpenAlex keeps the type, and `title_key` keys on is-dataset, so the pair never clusters; `apply_overrides` runs after `cluster_by_title` (read in `pipeline.py`), so a `type: conference` override corrects the label but cannot fold the pair. dpsd-new excludes the preprint by DOI. A possible proposal, not checked beyond these two DOIs: treat the `10.48786` prefix's datasets as papers, or warn when a dataset and a non-dataset share a title key.
- **Inference only, on why his works scatter:** none of the stray deposits carries his ORCID in Crossref, while two that do (IEEE Access 2025, Big Data Research 2025) sit on his profile; but MDM 2025 and OCEANS 2025 also lack it and sit on his profile, so a missing ORCID allows a misfiling without causing it. The ResearchGate deposit's DataCite record swaps his names ("Dimitris, Zissis").
- **Observed once, not chased:** a Koutsabasis 2011 paper (`10.1108/10650741211192046`) was dropped by one dry run and present in the next, a few minutes apart, same config apart from the pin (which touches only Zissis).
