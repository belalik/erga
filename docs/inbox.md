# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## Delta summary between builds

**From:** dpsd-new (consumer #2), 2026-08-16, wiring the weekly CI refresh.

**Trigger:** `publications.json` is ~440 KB at 5 tracked authors and grows with
the cohort, past the size GitHub renders a diff for in the browser. The weekly
PR was therefore unreviewable in practice, which defeats the stated goal in
`docs/action.md` that "the data in your repo changes only when you can see why".

erga is stateless per build and its action declares no outputs, so it cannot
report what changed since the previous run. `--dry-run` summarises a single
fetch (fetched/merged/deduplicated/excluded/backfilled), which is a different
question. dpsd-new worked around it with a local consumer-side script
(`scripts/publications_summary.py`) that diffs two snapshots by work `id` and
emits Markdown: added and removed works listed with tracked person, co-authors
and venue; everything else collapsed to per-field counts.

**Why it may belong upstream:** deciding which fields are cosmetic (a
`cited_by_count` bump) versus audit-critical (a new work appearing) is schema
knowledge, and every consumer needs the same judgment. Delivery (PR body,
email, chat) is correctly the consumer's job and should stay there. A possible
split is erga computing the delta and exposing it as an action output plus
stdout, with consumers deciding where it goes.

**Also surfaced while building it:** the summary doubles as a fetch health
check. A rate-limited or partial fetch produces a valid but smaller JSON, which
reads as mass removals. Without a delta view that is invisible, and merging it
silently deletes real records. Whatever erga does or does not adopt here, that
failure mode is worth naming in the docs.

**Working spec:** `~/projects/dpsd-new/scripts/publications_summary.py` and
`~/projects/dpsd-new/docs/publications-pipeline.md`.
