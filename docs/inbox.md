# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

---

**From dpsd-new, 2026-08-11** (consumer-#2 pilot ran to completion the same day the brief landed: 5 authors configured, 228 works built, filterable Astro page live on the dev domain — the pilot-keyed todo items can unblock). Findings, most useful first:

1. **Contamination can be invisible to verify when the homonym shares the exact Latinized name.** Katerina Malisova's ORCID-linked OpenAlex profile had absorbed 4 works by a Czech Kateřina Mališová (Palacký University); OpenAlex renders both as "Katerina Malisova", so the name-mismatch check had nothing to bite on — verify showed one clean profile, no flags. Caught only by reading the built JSON (all-Czech co-author teams, sports-science venues). DOI-exclude overrides handled it fine.
2. **`erga verify`/build warning noise**: every build prints `unmapped OpenAlex type 'other' … falls back to "other"` — the fallback equals the mapped value, so the warning alarms without informing.
3. **The orcid + openalex_id combo worked as designed** for the empty-unlinked-ORCID case (Papanikos: iD his, profile empty, OpenAlex never linked it — pinned id fetched 87 works, iD kept for byline tagging). The pipeline error message pointing at verify was what surfaced the case.
4. **Authors-roster candidate**: not needed. The consumer solved the staff↔publications join with a site-side field (`publicationName` on the staff schema) matched against `tracked_as`; a top-level roster in the JSON would have been convenient for enumerating tracked authors but nothing blocked on it.
5. **Astro shape**: config-relative path resolution was sufficient — `src/data/erga.yml` → `src/data/publications.json`, imported at build time; no `_data/` convention or schema change needed.
