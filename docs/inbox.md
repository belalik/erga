# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## 2026-10-17 · from smartmove-site (minis) · a fresh pin fails locally on uv's cached index, and the failure leaves a stale output that reads "no changes"

**Provenance:** smartmove-site session, minis, 2026-10-17, adopting 0.9.3 shortly after its release (PyPI JSON already listed 0.9.3 with 2 files).

**Trigger:** `uvx erga==0.9.3 build --config <scratch>/_data/erga.yml` exited 1 with uv's "no version of erga==0.9.3 ... requirements are unsatisfiable"; `uvx --refresh-package erga erga==0.9.3 ...` then built clean. The same machine had resolved 0.9.2 earlier the same day, so uv's cached index for erga predated 0.9.3. The trap is what follows: the scratch copy still held the old `publications.json`, so a diff of it against main read "no changes", the same verdict the working build later gave. CI is immune (`enable-cache: false`, fresh index), so only local checks bite: consumer sessions verifying a bump, and erga's own release step 7 controls run from a consumer's `_data/`.

**Proposal:** wherever erga tells a consumer to try a new pin locally (release notes, the README, release.md step 7), write `uvx --refresh-package erga erga==X.Y.Z`. Optionally, `build` could stamp the erga version into the output file (or print it first), so a stale file is distinguishable from a fresh one with no changes. No tier or breadth verdict; erga's call.

## 2026-10-30 · from smartmove-site (minis) · a name-tracked author is emitted with a homonym's ORCID

**Provenance:** smartmove-site session, minis, 2026-10-30, collecting team ORCIDs for the About page (erga 0.9.3 output, `_data/publications.json` as committed by CI).

**Trigger:** five works list `{"name": "Dimitris Zissis", "orcid": "https://orcid.org/0000-0002-6957-3494", "tracked": true, "tracked_as": "Dimitris Zissis"}`: doi 10.1109/mdm71479.2026.00019, .00073, .00075, .00076 and 10.5281/zenodo.22092724. That iD is a different Dimitris Zissis (ORCID record, read 30 Oct: employment Cranfield University and University of Bath, 18 works on supply chains and electricity pricing); the configured author's iD is 0000-0003-2870-2656 (University of the Aegean, 92 works). OpenAlex files these authorships under A5103188414, the contaminated homonym profile the site deliberately does not configure (its config pins `openalex_id: A5076536574`, no `orcid`). The works arrive through tracked co-authors, erga marks the Zissis authorship tracked by name/alias, and passes that profile's ORCID through beside `tracked_as`. A consumer that renders `authors[].orcid` as a link for tracked authors would send readers to the other man; nothing warns. smartmove-site renders no ORCIDs today, so nothing is visible there. Checked alongside: every lab paper in A5103188414 since 2024 reaches the site through a co-author, so no work is missing.

**Proposal:** when an authorship is tracked by name/alias only (its OpenAlex id is neither configured nor resolved for that author), either withhold its ORCID from the tracked author's output or emit a warning naming the author, the foreign iD, the profile and the work count. Optionally, if a configured `orcid` exists, prefer it over the authorship's. No tier or breadth verdict; erga's call.
