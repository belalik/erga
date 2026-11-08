# Scopus

Post-v1 only. Scopus is a v1 non-goal; its place among erga's sources
follows the source roles in `docs/requirements-v1.md` section 12: a check
whose output is proposed curation, never a record source. This file holds
the reasons, the terms, the planned stages and the access test.

## Why it is worth having

Two dpsd-new members asked for it (Gavalas 2026-09-25, Vosinakis
2026-09-30): fewer works, better metadata. ΕΘΑΑΕ, the Greek
higher-education quality authority, assesses staff research from Scopus
data, so it is the record Greek departments are measured by.

The larger reason (2026-11-08): what erga keeps needing from members is
confirmation of which works are theirs, and few members answer (dpsd-new's
confirmation round, 2026-09-25: three of six replied). A Scopus author
profile is that confirmation, kept up without the member. OpenAlex now lets
authors claim and fix their own profiles (the Normal item in
`docs/todo.md`), but few members will (Thomas, 2026-11-08). That Scopus
profiles are more precise than OpenAlex's is recall, not measured: the
check's first run is the measurement.

## Terms

Read on dev.elsevier.com on 2026-11-08; recheck before building.

- The API Service Agreement (current version) defers to the institution's
  own Scopus licence. The key identifies the calling application and
  grants no data access by itself (the API key settings page); the
  entitlement comes from the subscriber's network address, or an
  institutional token Elsevier issues through the library, kept
  server-side, never in browser code or a URL.
- The IR/CRIS/VIVO use case (`ir_cris_vivo.html`) lets an application run
  by or for a subscribing institution (a contractor needs its own
  agreement with Elsevier) retrieve its researchers' works and show
  publicly their ids, DOI, authors with Scopus author ids, affiliations,
  title, year, source, type, volume and pages, and citation counts. Never
  abstracts. Stored in perpetuity, even after cancellation. Each record
  attributed to Scopus with a link to its Scopus record and cited-by list.
  Cited-by counts never aggregated for external display.
- Unanswered: whether a public JSON file in a public repo counts as that
  display. Ask Elsevier support before stage 2.
- The agreement's AI clause (2.4) allows AI tools only in a closed,
  enterprise-grade environment that shares no Elsevier content with a
  third party, and 2.5 makes the key holder liable for any AI tool they
  let near the API. "Elsevier content" means anything the API returns,
  metadata included. So real Scopus responses stay out of Claude and Codex
  sessions: sessions see statuses, counts and field names; a real record
  is read by a person in a script's output. Fixtures are synthetic, as
  always.

## Stages

Each only if the one before shows a need (revised 2026-11-08).

1. **A check that proposes curation.** The maintainer runs it from a
   subscriber network, with the consumer's key from an env var, skipped
   without one; no token, and CI never calls Scopus. It compares each
   member's Scopus profile with the build and writes proposed curation for
   review:
   - an exclude for a listed work Scopus does not credit to the member,
     only where Scopus indexes the venue (from recall, its silence means
     nothing for datasets, many theses, Greek-language venues);
   - an include for a credited work the build lacks but OpenAlex holds (on
     a detached or namesake profile, or never listed), which needs the
     include entry (Normal in `docs/todo.md`);
   - a report line for credited works OpenAlex lacks (manual-entry
     candidates).

   Scopus decides membership, OpenAlex still supplies every record, and the
   curation files hold only OpenAlex ids and DOIs, so attribution, the
   public-JSON question and the abstracts rule never arise. The report shows
   OpenAlex titles and ids, never Scopus records. Its gate is v1.
2. **Optional and last: enrichment.** Per-field enrichment of works already
   fetched, matched by DOI (authors with Scopus ids, affiliations, type), as
   the Crossref venue backfill does. Never abstracts. Needs a token holder
   at the institution for CI and Elsevier's answer on the public JSON.

Scopus-only works entering the list is section 12's multi-source merging,
only on consumer demand. The v1.0 schema freeze should leave room for
stage 2 (the JSON Schema item in `docs/todo.md`).

## Access test (2026-11-08, minis)

Vosinakis confirmed the Aegean's subscription is by network address, on
campus or through the university VPN, with no account. Nobody holds an
institutional token yet, which CI would need.

Tested the same day with a fresh key (label `erga`, kept outside the
repo):

- The VPN carries Elsevier's traffic (IPv4 only, no split tunnel for
  `api.elsevier.com` or `www.scopus.com`), and scopus.com reads "Brought
  to you by University of the Aegean".
- On the VPN, Author Search and Scopus Search's COMPLETE view answer 200.
  Off it, both answer 401 `AUTHORIZATION_ERROR`, while the STANDARD view
  answers any key with the same fields and values. STANDARD carries the
  first author only (`dc:creator`).
- COMPLETE carries what erga would need: every author with a Scopus
  `authid`, `afid`, given name and surname (capped at 100 per record),
  plus abstract, keywords and funding. At most 25 results per request;
  weekly quotas 20,000 for Scopus Search, 5,000 for Author Search.
- The Authentication API refuses the key (403, "configuration settings
  insufficient"). Harmless: it only resolves addresses shared by several
  accounts.
- Entitlement was immediate on the Aegean's address, although the key
  settings page says new keys get no data access until an entitlement is
  verified.
- Not a valid control: after leaving the VPN, the attached Chrome still
  showed the Aegean banner (its session apparently kept the access), and a
  fresh headless browser met Cloudflare's challenge before the page.
