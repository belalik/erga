# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

(empty)

## 2026-11-22, smartmove-site (minis): "when in doubt, leave it out" adopted; this consumer accepts recall features only opt-in and reviewed

- **Provenance and trigger:** smartmove-site session on minis, 2026-11-22, triaging erga's entry of 2026-11-21 that asked this site to settle the stance and write back. Thomas decided it in the session. Recorded in smartmove-site `docs/publications-data-sources.md` → Inclusion stance, with a pointer in its `CLAUDE.md` → Publications.
- **The stance:** adopted as dpsd-new words it. A record whose authorship, standing as a publication, or metadata is in real doubt is excluded by override with a comment saying what it lacks, and returns as a manual entry if the member confirms it. Fixable metadata is fixed by override, not grounds for dropping a work.
- **Constraint on erga's open `include_xpac` / recall decision:** for this site, any recall feature (works OpenAlex lists only under `include_xpac`, drafted manual entries) is acceptable only opt-in and reported for review, never merged silently. The same constraint dpsd-new set.
- **The `other` records, decided:** the entry's count was stale. The site held three, not four: the two errata had been excluded on 2026-10-30 with the lab head's corrections. Kept: Zissis's two special-issue guest editorials (`10.1016/j.jss.2017.02.022`, `10.1016/j.future.2020.04.017`), as recognised editorial service. dpsd-new keeps its five guest editorials for the same reason and drops only prefaces, contributor lists and corrigenda, so the entry's "dpsd-new drops front matter of that kind" does not reach editorials. Left out: `W1758967400`, a 2008 Essex repository deposit (unrefereed, no conference named, no full text, venue "UNSPECIFIED"), excluded by `id`.
- **Possibly for erga:** OpenAlex carries the JSS editorial's title with LaTeX quote marks (``...''), fixed here by a title override. If erga normalised TeX quotes in titles, other consumers would get it free.
- **Also done:** the pin moved to erga 0.9.6. A same-day 0.9.5 and 0.9.6 build of this site's config wrote identical JSON (198 works), as the release entry predicted.
