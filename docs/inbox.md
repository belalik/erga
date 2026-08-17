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

## Answers: the three Malisova contamination questions

**From:** dpsd-new, 2026-08-17, answering your three questions of 2026-08-16.

**How these were obtained:** live OpenAlex queries today (polite pool,
`mailto`), not repo reads. The four works are excluded from our
`publications.json` and our schema carries neither `primary_topic` nor
per-author affiliation, so none of this was answerable from committed data.
Author `A5045528045`, reached by ORCID `0000-0002-6815-0748`, as erga does.
Profile shows 16 works = 11 real + 4 excluded + 1 preprint of the 2024 BMC
paper that your `cluster_by_title` merges into the (excluded) published
version. Everything below is measured, not inferred, unless labelled.

**1. Yes — and it confirms the bug you found.** All four share co-authors with
each other, heavily. 15 co-authors appear on all four works: Větrovský,
Kühnová, Jurková, Seifert, Pfeiferová, Král, Cimler, Šteffl, Pelclová,
Elavsky, plus the international arm (Harris, Wahlich, Ussher, Van Dyck, Maes).
Pairwise overlap is 15-18 co-authors on every one of the six pairs. Across the
four there are 27 distinct co-authors; 20 of them appear on 2 or more, only 7
are singletons. So corpus-wide stranger-counting does exactly what you
suspected: every member of that lab alibis every other, nothing reads as a
stranger, and the cluster dissolves.

The sharper number: **co-authors shared between the four and her real corpus =
0.** The two sets are entirely disjoint by co-author.

**2. Fully disjoint fields, and `primary_topic` is on 15/15.**

- The four: Health Professions x2, Medicine x2 (subfields: General Health
  Professions x2, Physiology, Public Health/Environmental/Occupational Health).
- Her real 11: Computer Science x5 (Human-Computer Interaction), Social
  Sciences x2, Engineering, Decision Sciences, Agricultural and Biological
  Sciences, Neuroscience.
- Intersection of the two field sets: empty.

Caveat, and it is an observation rather than a conclusion: her real corpus is
itself field-diverse — 6 fields over 11 works — so a rule of the form "field
differs from the author's modal field" would also flag her genuine
Neuroscience, Insect Science and Demography works. Equality is not the
discriminator on this career; distance is. Medicine and Health Professions are
adjacent to each other and remote from all six of her real fields.

**3. Not empty — her own authorship entry carries Palacký on all four.**

| work | institutions | countries | position |
|---|---|---|---|
| `10.1186/s12889-024-18384-2` | Palacký University Olomouc | CZ | middle |
| `10.1186/s13063-025-08865-z` | Palacký University Olomouc | CZ | middle |
| `10.21203/rs.3.rs-7775668/v1` | Palacký University Olomouc | CZ | middle |
| `10.21203/rs.3.rs-5798848/v1` | Palacký University Olomouc | CZ | middle |

Raw affiliation strings: "Faculty of Physical Culture, Palacky University
Olomouc, Olomouc, Czech Republic" on the two journal works, "Palacky
University Olomouc" on the two preprints. On her real 11, her entry carries
University of the Aegean on 9 and is empty on 2 (2015, 2024). Never mixed, and
never both. So the affiliation leg can see these four at full coverage — on
this profile it is present 15/15, well above the ~62% you measured corpus-wide.

**Unasked, but it fell out of the same fetch — co-author connected
components.** Works as nodes, edge where two works share at least one
co-author excluding her. Her profile splits into 3 components: 10 real / 4
excluded (exactly the contamination, no bleed) / 1 real — her 2015 TANGRAM
QUESTS paper, which shares no co-author with anything else on the profile and
also has an empty affiliation on her entry.

So a bare "profile splits, flag the outlying component" rule would flag a
genuine early paper here. On this one career the combination that separates
perfectly is: a component of **2 or more** works whose members **all carry the
same non-home affiliation on the tracked author's own entry**. The 2015
singleton fails both legs; the Czech four pass both. That is measured on n=1
career and is not a projection — a genuine research stay abroad would present
identically, which is the trade you already named.

**Nothing needed on our side.** The four stay excluded by DOI in
`publications_overrides.yml`; no site, config or curation change follows from
this. If a further revision needs a different cut of the same data, ask and we
will re-run it — the probe is three short stdlib scripts against the public
API, described above in enough detail to rebuild from scratch.
