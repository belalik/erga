# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## 2026-10-17 · from dpsd-new (minis) · v0.9.1 confirmed on the live cohort; four shapes from the refresh audit

**Provenance:** dpsd-new session, minis, 2026-10-17: the pin moved to 0.9.1 and the refresh PR (belalik/dpsd-new#11, run 39005609159) was audited record by record before merge.

**Trigger / what's there:**

- **0.9.1 confirmed.** Same-day scratch builds of 0.9.0 and 0.9.1 on dpsd-new's current config: 702 works under both, `venue` alone differs, 52 records, matching your measurement exactly. No `eBook` venue left after the one override you predicted (`W3181568600`).
- **HTML entities in venues.** Two venues arrive with `&amp;` (`W1571010850` "Virtual Systems &amp; Multimedia (VSMM)", `W4319978610` "(ICE/ITMC) &amp; 31st ... (IAMOT)"), and a third did on main before this run (`W2036128436`, MED 2007). A consumer that escapes on render shows a literal `&amp;` (the site did, live: `&amp;amp;` in the HTML). Titles and author names on the 702 carry none. Unescaping source strings at normalize would make it impossible downstream. Fixed here by two overrides.
- **One edition's name absorbing a series.** Five MED papers (2007, 2009, 2013, 2016 twice; `W2036128436`, `W2150394945`, `W2098248572`, `W2513624788`, `W2516825044`) all came back with venue "2006 14th Mediterranean Conference on Control and Automation", replacing each one's own edition name. It is the shape your delta item has (one value absorbing many), with a check that needs no history: a four-digit year in the venue that differs from the work's year. On the whole 702, that check finds these five plus one legitimate case (`W4229064834`, a 2022 paper at "The 2021 Summit of the International Society for the Study of Information"), so it is a warning, not a rule. Fixed here by five overrides.
- **A NICT machine translation reached the build itself.** `W2744884731`, "Leap Motionを用いたディジタル遺産への運動学的アプローチ:Cycladic彫刻応用【Powered by NICT】", no DOI, arrived as an addition on the tracked profiles of two members (Koutsabasis, Vosinakis), beside the English original (`10.1109/vs-games.2016.7590334`) it translates. Your todo item marks whole same-name profiles made of these; this one sits on the real profile, where only the summary's added list shows it. Excluded here by id.
- **Pending a member's confirmation, for the ORCID item.** Zissis's arXiv preprint `W4399252589` left the list (404 in OpenAlex now); its published version (`W4400728518`, MDM 2024, `10.1109/mdm61037.2024.00031`) sits on a second "Dimitris Zissis" entity, `A5103188414`, 32 works, ORCID `0000-0002-6957-3494` (not the configured `0000-0003-2870-2656`, which resolves to `A5076536574`), institutions AUEB and Aegean. Whether that iD and those works are his is asked on Monday 2026-10-19; outcome routed then.

No tier or breadth verdict — triage here decides.

## 2026-10-17 · from dpsd-new (minis) · correction to the entry above

**Provenance:** same session. **Trigger / what's there:** in the HTML-entities bullet, "Unescaping source strings at normalize would make it impossible downstream" should read "Unescaping source strings at normalize would fix it for every consumer."

No tier or breadth verdict — triage here decides.
