# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

(empty)

## 2026-11-21, dpsd-new (timmy): every XPAC work on one profile is real, and two manual-entry gaps

- **Provenance:** dpsd-new session on timmy, 2026-11-21, after Κυριακουλάκος's reply (2026-11-18) to his batch 4 list; OpenAlex queried live the same day.
- **Seen:** `author.id:A5037482370,is_xpac:true` returns 5 works, and every one is his and real: two Kallipos books, two CEEGS 2024 papers, and a Griffith repository record (`W7027632552`, 2021, type other, no DOI, submitted version) that he confirmed is a separate work, published in ASIFA Magazine (online 2024-12-17). All five are manual stopgaps in dpsd-new now. Evidence for the `include_xpac` decision you deferred until the cohort reaches 17 (batch 5 is next).
- **Gap 1, a fixture shape:** manual entries accept no URL (`MANUAL_KEYS`, v0.9.5), so a DOI-less work with an online home renders unlinked.
- **Gap 2, a dedup shape:** if `include_xpac` is turned on, the Griffith record arrives with no DOI and a title that differs from the manual entry's by "south east" against "Southeast" (and case), so DOI dedup cannot pair them and title dedup may not; dpsd-new's comment says to remove the manual entry and patch the record instead, but a consumer that forgets gets a duplicate.
- **Proposal:** weigh the five in the XPAC decision; consider a `url` key for manual entries; check whether title dedup pairs a compound-word spacing variant.
