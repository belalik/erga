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
