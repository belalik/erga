# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## Identity resolution is the uncovered half of the job

**From:** dpsd-new, 2026-08-17. Triggered by widening our cohort from 5 to 9
people the same day, which took a full working session in which the fetch
itself was the trivial part.

**Observation, first-hand.** Everything expensive happened either side of
`build`. We had to go from "Δημήτρης Ζήσης, Professor, University of the
Aegean" to a trustworthy ORCID iD, for four people who had no iD recorded
anywhere. That work was: search OpenAlex under several Latinizations, read
`last_known_institutions`, pull the candidate's ORCID, confirm it against
orcid.org employment history, then scan the profile for the Malisova failure
mode before trusting it. We wrote that script twice in one day, once to
answer your three questions and once to onboard these four.

**Two traps it caught, both of which defeat the obvious approach:**

- Ξυδιάς signs **Xidias**, never "Xydias". A different real person, "Ilias
  Xydias" (INRIA, 2 works), matches our staff record's spelling more closely.
  Name-matching on our own transliteration finds the wrong man.
- There are two Dimitris Zissis. Ours does maritime informatics at UAegean;
  the other does supply chain modelling at Bath and Cranfield. The decoy
  carries **University of the Aegean** among his `last_known_institutions` on
  OpenAlex, so name-plus-institution matching also finds the wrong man. Only
  orcid.org employment history separated them cleanly.

**What this suggests, as a proposal rather than a verdict:** an `erga suggest`
(or `resolve`) that takes a name, an institution and optionally a Scopus iD,
and returns candidate OpenAlex profiles ranked, each with the signals that
actually discriminate: employment history from orcid.org, `primary_topic`
field spread, co-author connected components, and affiliation on the person's
own authorship entries. That is the same computation as the contamination
check you are tuning, pointed at a candidate instead of a configured author.
Notably it also runs **before** anyone is in the config, which `verify`
cannot do by construction.

**A design question we hit, where we think the tempting answer is wrong.**
Thomas raised whether erga should simply *require* a list of manually
verified ORCID iDs, and treat identity as the caller's problem. Requiring an
iD and refusing to guess seems right to us. Calling verification a safety
story does not, and our own pilot is the counter-example: **Malisova's ORCID
was correct and manually verified on 2026-08-11, and the contamination
happened anyway**, because the Czech homonym's works sit inside the correctly
identified profile. Right person, right iD, wrong works.

So there are two failures needing separate answers, and one requirement
cannot carry both:

1. *Wrong person entirely* — Xidias, Zissis. A verified iD does solve this.
2. *Right person, foreign works inside their profile* — Malisova. A verified
   iD does nothing, and this is the one your contamination work addresses.

If erga documents "an ORCID is required and is trusted as given", that is
accurate and useful. If it documents "verified ORCIDs in, clean data out",
every operator inherits a false guarantee at exactly erga's blind spot.

**One scale note that bears on how badly discovery is needed.** Before today,
5 of our 63 staff had an ORCID on file, and those 5 were the entire pilot. As
a hard precondition, verified-iDs-only makes erga unusable for ~92% of a
typical department until somebody does the discovery step by hand. That step
is the proposal above.

**Not asking for:** any commitment. If discovery is out of scope for erga,
that is a reasonable line to draw, and saying so explicitly in the docs would
itself help, because the alternative is every consumer improvising it.

**More coming, deliberately held back.** We are running the confirmation loop
with six people over the next weeks, and the workflow gaps that surface
(recording who has confirmed and when, editorial noise as rules rather than
per-DOI excludes, the fact that onboarding one person means edits in two
systems) will be routed once they carry measurement rather than speculation.

## erga as first-trial candidate for Codex patch mode

**From:** hub (claude-code-config), 2026-09-02. Triggered by the Codex consolidation session: `/codex` patch mode was opened (mechanics drafted in the skill), and its first trial wants a small, mechanical, test-verifiable change on a project with a real test signal — which erga has and most of the portfolio doesn't.

**The proposal:** next time a bounded mechanical change comes up here — a focused refactor, a well-specified fix, a rename confined to a few files; *not* a feature — consider running it as the patch-mode first trial instead of editing directly. Shape (full mechanics in the skill → Patch mode): pin the base commit, Codex writes `local/codex-<task>/changes.patch` + `notes.md` (a diff *file*, never an applied change), the session applies it on a `codex/<task>` branch with `git apply --check` first, runs the tests, reviews the applied diff like any code review, and Thomas decides the merge. A patch that fails `--check` or strays outside the stated boundary goes back whole — never hand-edit hunks.

**Why erga:** real tests (the trial must establish whether tests catch what review misses in a generated patch), Python with clear module boundaries, and prior Codex evidence context — this is also a good project for the review-mode open question (whether the intent-vs-code complementarity split holds on code diffs), so a significant future diff here could get the blind-pair treatment: frozen diff file, `/code-review` and `/codex` review run blind to each other.

**What the trial must record** (→ hub `docs/inbox.md`): diff quality against the pinned base, `git apply` friction in practice, and whether `notes.md` was honest about what Codex could not verify. First trial is deliberately small — if no suitably bounded change materializes, that is a fine reason for this to sit; another project can take it.

**Not asking for:** running Codex on anything current. Thomas-initiated only, per the skill's hard invariant — this entry just marks erga as a preferred venue when the shape appears.
