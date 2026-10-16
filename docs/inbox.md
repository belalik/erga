# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## 2026-10-02 · from claude-code-config (minis) · Two Codex snapshot dirs hold stale copies of this CLAUDE.md, which load as live instructions

**Provenance:** hub session, minis, 2026-10-02, CC 2.1.284. Found while tracing why hub sessions carry the global CLAUDE.md twice; the stale-copy case was tested in the hub the same day.

**Trigger / what's there:** A `Read` of a file in a subdirectory of the session's project loads the CLAUDE.md of the folders it sits in as project instructions, gitignored folders included, and nothing marks a copy as stale (`~/projects/claude-code-config/docs/cc-quirks.md` → Skills & context). Two of this repo's Codex review snapshots hold such copies: `local/codex-small-fixes/branch/CLAUDE.md` (2026-09-25) and `local/codex-unlinked-review/branch/CLAUDE.md` (2026-09-26). No erga session has read into either (transcripts checked), so nothing has gone wrong yet; the first `Read` there would put that week's rules beside today's. If those reviews are closed, delete the two `branch/` dirs; if one is still wanted, delete its `CLAUDE.md`. The Codex skill's snapshot export now excludes `CLAUDE.md` and `.claude/` (`references/running.md` → Review), so new runs will not recreate them.

No tier or breadth verdict — triage here decides.

**Update, same day:** the hub then added `claudeMdExcludes` for `**/local/**/CLAUDE.md` to the shared settings (tested live), so a copy under `local/` no longer loads at all: on minis now, on timmy after its next hub pull. Deleting the two dirs is housekeeping now, not a fix.

**Correction, same day, to the entry above:** the snapshot-export excludes it mentions were reverted. Codex briefs point at the snapshot's own `CLAUDE.md` (as `codex-unlinked-review` did), so new snapshots carry a copy again, and the setting keeps it from loading into CC.

## 2026-10-02 · from dpsd-new (minis) · One author id on two bylines of one work: a conflation erga could flag

**Provenance:** dpsd-new session, minis, 2026-10-02, the v0.9.0 bump. Acting on the release notes' HICSS override (`W1627971907`), the site's list showed Jenny Darzentas twice on that paper; the notes did not mention it.

**Trigger / what's there:** Crossref's byline has two Darzentas authors, "J.S." (Jenny) and "J." (John), both staff of the department. OpenAlex gives both authorships the same author id, `A5028359938` (Jenny's), with the raw names kept apart (`raw_author_name` "J.S. Darzentas" and "J. Darzentas"). A sweep of the site's 700 works for a name listed twice on one work found two more, same pair, same id: `W2147248713` (10.1076/ilee.9.3.231.3569) and `W2159824452` (10.1504/ijceell.2001.000378), 3 of 700 in all, each checked against Crossref. The site fixes all three by overrides patching `authors`. The shape is cheap to detect in the fetched records: one author id on two authorships of one work, the raw names differing. Here it hits an untracked co-author, so it only misprints a list. On a tracked member's id it would mean a second person's byline was merged into the member's profile, the same-name contamination `verify` cannot otherwise see, caught at the work level. Not checked: whether OpenAlex ever repeats an id for a genuinely duplicated authorship (the same raw name twice), which a check should probably skip or report separately.

No tier or breadth verdict — triage here decides.
