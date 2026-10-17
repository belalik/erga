# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## 2026-10-17 · from smartmove-site (minis) · the "upstream" removal in the v0.9.1 note was a lab paper lost to a homonym profile

**Provenance:** smartmove-site session, minis, 2026-10-17, while adopting 0.9.1 (pin moved, CI green at `550967d`, bot commit `75f3f36`). Scratch build of the site's `_data/` under 0.9.1 against main's list.

**Trigger:** the v0.9.1 entry called the build's one removal (196 → 195) "upstream, not the release". True, but the consequence went unflagged: the removed work, `W4399252589` (arXiv preprint "On Vessel Location Forecasting and the Effect of Federated Learning", Zissis), now 404s; OpenAlex merged it into the MDM 2024 published version `W4400728518` (DOI `10.1109/mdm61037.2024.00031`), whose Zissis authorship is credited to `A5103188414`, the contaminated homonym the site must never add. No other member is on the byline, so no profile fetch sees it and name-fallback tracking never gets the chance. The paper silently left the site. A sweep of all 32 works on `A5103188414` against the new list found it the only lab paper lost this way (one 2017 BDVA whitepaper with no DOI was never on the site).

**Proposal:** when a build removes a work, look its old id up; a 404 or a redirect to a different W-id means a merge, and the build line (or `verify`) could name the survivor and the profile it now sits on, so "1 removed" reads as "merged into W…, credited to an unconfigured profile". `verify`'s unlinked-authorship check cannot catch this shape, since the authorship has an id, just the wrong one. No tier or breadth verdict; erga's call.
