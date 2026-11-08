# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

(empty)

## 2026-11-08 · from dpsd-new (minis) · Aegean has Scopus access by network address (campus or VPN): a route to test for the API

**Provenance:** Βοσινάκης's reply to Thomas's email of 2026-11-04, which asked whether the department has Scopus access and who holds the account; Thomas pasted it into a dpsd-new session on 2026-11-08. His answer, in full: «Ναι, μπαίνουμε κανονικά στο scopus μέσω IP Αιγαίου ή VPN.» Background: Thomas told him earlier that Scopus is worth trying in erga, being more reliable and the base of the ΕΘΑΑΕ evaluations.

**Trigger / what's there:**

- **What the answer means:** the university's subscription is IP-based, with no account or password. Traffic from the Aegean's network, on campus or through the university VPN, is recognised as a subscriber and opens scopus.com fully. Nobody needs to be asked for credentials.
- **What it does not answer: the API.** From recall, not checked: Elsevier issues a free API key on registration at dev.elsevier.com, and the key gets the subscriber's entitlements only when the request comes from a subscriber IP; off campus without VPN, an institutional token (`insttoken`) has to be requested from Elsevier through the library. Verify against Elsevier's developer pages, dated, before planning on it.
- **The caveat that could decide it:** from recall, Elsevier's API terms restrict displaying Scopus data on public websites and caching it. erga's output is public publication lists, so read the current API service agreement and display rules before building anything on Scopus.
- **A test, about 15 minutes, on a machine Thomas can put on the VPN:** (1) VPN on, open scopus.com: the header should name the University of the Aegean as the access provider; if it does not, the VPN is split-tunnel and does not carry Elsevier's traffic. (2) Thomas registers a key and stores it in a file under `~/.config/` (never printed in a session). (3) VPN still on, one Author Search call, reading the entitlement from the response, then the same call off VPN as the control.

No tier or breadth verdict: triage there decides.
