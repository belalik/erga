# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## 2026-10-17 · from smartmove-site (minis) · a fresh pin fails locally on uv's cached index, and the failure leaves a stale output that reads "no changes"

**Provenance:** smartmove-site session, minis, 2026-10-17, adopting 0.9.3 shortly after its release (PyPI JSON already listed 0.9.3 with 2 files).

**Trigger:** `uvx erga==0.9.3 build --config <scratch>/_data/erga.yml` exited 1 with uv's "no version of erga==0.9.3 ... requirements are unsatisfiable"; `uvx --refresh-package erga erga==0.9.3 ...` then built clean. The same machine had resolved 0.9.2 earlier the same day, so uv's cached index for erga predated 0.9.3. The trap is what follows: the scratch copy still held the old `publications.json`, so a diff of it against main read "no changes", the same verdict the working build later gave. CI is immune (`enable-cache: false`, fresh index), so only local checks bite: consumer sessions verifying a bump, and erga's own release step 7 controls run from a consumer's `_data/`.

**Proposal:** wherever erga tells a consumer to try a new pin locally (release notes, the README, release.md step 7), write `uvx --refresh-package erga erga==X.Y.Z`. Optionally, `build` could stamp the erga version into the output file (or print it first), so a stale file is distinguishable from a fresh one with no changes. No tier or breadth verdict; erga's call.
