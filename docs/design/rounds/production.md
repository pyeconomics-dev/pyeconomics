# The dogfooding round on production

The launch readiness gate's design and UX round (Phase 5 Step 20; ROADMAP §4 5.9),
run on 2026-11-27 under the protocol in [dogfooding.md](../dogfooding.md), on the
release candidate itself. It passes when it finds no Blocker or High issue and its
median is no lower than [round 3](round-3.md)'s 7.38 ([summary.md](summary.md)).
**It passed:** median 7.38, no Blocker, no High.

- **Site:** production, `https://pyeconomics.dev`, serving `1.0.0rc2` (tag
  `v1.0.0rc2`, commit `9c22c60`) behind Cloudflare Access. Its data is real: the
  daily snapshot the hosted service reads.
- **Harness:** `npm run dogfood` against production through Access, run
  `production-step20`, 5.3 minutes: 108 page captures and 30 task states. All 138
  passed. None had a console error, a policy violation, a request to another
  origin, sideways overflow or a stray scroll box. The worst layout shift was 0.013
  (the model page with a chart, 820 wide); the 404s are the not-found page type's
  own.
- **The harness on production, changed first.** The harness sent the Access
  service token as Playwright's `extraHTTPHeaders`, which go to every origin, and
  did not switch the analytics tracker off. A production build talks to the
  analytics collector and to Sentry, so `support.ts prepare` now adds the headers
  per request on the site's own origin alone, refuses and records any request to
  another, and sets `umami.disabled` before any page script runs, as the
  deployed-site suite does. This is dated in the protocol's change log; it changes
  no persona, task, rubric, severity or page. The same exposure in the
  deployed-site suite is issue #407.
- **Pictures:** before the evaluators started, one contact sheet was read and seen
  in the main session (the home page at three widths in both themes) and one by a
  throwaway subagent on the evaluators' model (the coverage page, described in
  detail). Both reached their readers.
- **Evaluators:** five fresh subagents on Claude Sonnet 5.5 (the implementer was
  Claude Opus 5.5), one per persona. None had seen an earlier round or anything of
  the implementation. Each was given the protocol's prompt word for word, with the
  confirmation round's working notes, changed only for the site's address, the run
  name and the sign-in helper (`web/dogfood-out/with_prod_access.py`, which
  production's keyring entry signs in). Each read its prompt from a file in
  `web/dogfood-out/prod-prompts/`, did its tasks in Chromium through
  `tests/dogfood/visit.ts`, and read the contact sheets.
- **After scoring**, each was shown the confirmation round's merged list and said
  which items it found fixed, still there or worse. That pass changed no score.

## Scores

| Dimension | P1 candidate | P2 developer | P3 student | P4 first visit | P5 phone | Median | Confirmation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D1 First impression and identity | 8 | 8 | 8 | 8 | 8 | **8** | 8 |
| D2 Hierarchy and layout | 7 | 7 | 7 | 7 | 8 | **7** | 7 |
| D3 Typography and formulas | 8 | 8 | 8 | 8 | 8 | **8** | 8 |
| D4 Colour, contrast and theming | 7 | 7 | 7 | 8 | 8 | **7** | 8 |
| D5 Interaction, feedback and motion | 7 | 7 | 6 | 7 | 7 | **7** | 7 |
| D6 Navigation and findability | 7 | 7 | 7 | 7 | 8 | **7** | 7 |
| D7 Content and microcopy | 7 | 7 | 6 | 7 | 8 | **7** | 7 |
| D8 Trust and polish | 8 | 8 | 8 | 8 | 8 | **8** | 8 |
| **Mean** | 7.38 | 7.38 | 7.13 | 7.50 | 7.88 | **7.38** | 7.38 |

The round's median is the median of the five means: **7.38**, equal to round 3's
and to the confirmation round's. The gate needed no lower than 7.38.

## Tasks

| Persona | Task 1 | Task 2 | Task 3 | Task 4 | Task 5 |
| --- | --- | --- | --- | --- | --- |
| P1 CFA® Program candidate | pass | hard: the duration page links no pricing model, so the evaluator guessed "Bond price and yield" | pass | pass | |
| P2 Python developer | pass | pass | pass | pass | |
| P3 economics student | pass | pass | hard: the policy-rule calculator is far down a long page and still loading when reached | pass | |
| P4 first-time visitor | pass | pass | hard: by its own account, the evaluator first clicked a link whose name contained "Run" | pass | |
| P5 phone visitor | pass | pass | pass | pass | pass |

Of 21 tasks, 18 passed, 3 were hard and none failed (confirmation round: 20, 1,
0; round 3: 17, 4, 0). The candidate's pricing task has been hard in every round.
As in every round since round 0, a hard task is recorded here and its cause among
the findings, at the severity the evaluator gave it: no evaluator rated a finding
High.

## Findings

The evaluators returned 11 Medium and 14 Low findings and no Blocker or High.
Merged by page and cause they are 11 Medium and 13 Low, listed with their
destinations in issue #408. None was fixed in this step: the candidate soaked is
the candidate released (ADR-0013 decision 18), so changes to the site wait until
after 1.0.0.

### Blocker

None.

### High

None.

### Medium

| # | Finding | Personas | Destination |
| --- | --- | --- | --- |
| M1 | The bond duration page links no pricing model, and its related models omit it | P1 | #408 |
| M2 | A price's unit reads "money"; options show ids beside names; rates are decimals | P1 | disputed, as in every round; ids #375 |
| M3 | Run does nothing until the island hydrates; a server-side error shows below the form | P1 | #373 |
| M4 | On a phone the curl snippet is cut at the box's edge, with no scroll cue | P2 | #376 |
| M5 | The policy-rule calculator still loading when its heading is in view, far down a long page | P3 | #408, #372 |
| M6 | A live result's "observations to 2036-12-31" reads as data | P3 | #374 |
| M7 | A live result gives no plain reading; "the Report" undefined; the gap terms' unit "rate" | P3 | #374, #375 |
| M8 | The first result leads with an id, "money" and two hashes | P4 | #375, #376 |
| M9 | About and the legal pages are reachable only from the footer | P4 | #372 |
| M10 | The header's domain row weighs as much as the main links at 1440 | P4 | disputed, as round 3's L4 |
| M11 | Search from the header's icon lands on an unfocused box and loses typed text | P5 | #371 |

### Low

| # | Finding | Personas | Destination |
| --- | --- | --- | --- |
| L1 | On a phone the install line and the preview note come before the try-it area | P1 | the preview note goes at 1.0.0 |
| L2 | The snippet keeps the last valid inputs while a field shows an error | P1 | #373 |
| L3 | The Python snippet's install line sits outside what Copy copies | P2 | #376 |
| L4 | "Use it elsewhere" repeats the worked example in narrow scrolling boxes | P2 | #376 |
| L5 | `/assistants/` does not show how to reach models without a tool of their own | P2 | #376 |
| L6 | The manifest does not say whether a hash holds across platforms | P2 | #376 |
| L7 | The live-data notice shows profile codes and runs long | P3 | #374 |
| L8 | `/sources/` gives every local-only source the same reason | P3 | #375 |
| L9 | A series page's chart is below the first screen at 1440x900 | P3 | #408 |
| L10 | The home calculator's form is dense and its result lands below the fold | P4 | #408 |
| L11 | "Preview" and "rc2" are unexplained | P4 | goes at 1.0.0 |
| L12 | Results show ten digits on a phone | P5 | disputed, as in every round |
| L13 | The duration page's largest paint was 2.6 to 2.8 s at 390 in the harness | P5 | #408 |
| L14 | Formula subscripts are small on a phone | P5 | #372 |

Every Medium is one an earlier round found, or the same class on another page,
except M1 and M5, which are new and in #408. Nothing an earlier round fixed has
come back.

## The confirmation round's list, checked after scoring

After scoring, each evaluator was shown the confirmation round's merged list, laid
out item by item from its issues (#371 to #377) and its seven disputed Low findings
(31 items with an id each: `web/dogfood-out/prod-prompts/second_pass.txt`). Of 154
judgments, 34 were "fixed", 41 "still there", 79 "not checked" and none "worse".
One evaluator left out one item.

- **The confirmation round's High (H1), the hosted copy of each BLS series cut to
  three years:** fixed, by all five. Each saw the unemployment rate's ten years, 120
  observations from 2016-11-30 to 2026-10-31.
- **Still there, by at least three:** the phone menu without About or the legal
  links (P1, #372), seven filters before the first model on a phone (P3, #372),
  internal terms in visitor text (W3, #375), a price's unit "money" and ten digits
  (O3, disputed), and a source's notice in three places (O6, by rule). Each is held
  in its issue for after 1.0.0, or disputed with its reason in an earlier round.
- **Fixed, by at least three:** H1, an exact title ranked first (S3), the counts
  agreeing page to page (W1), the REST API and MCP named on the home page (C2), and
  what a manifest's hashes cover (C6).

So rc2 carries what the confirmation round needed before launch (H1, through
#370 and #378, and the dark theme's select lists, #388), and the rest stays in the
issues that hold it.

## Cost

- **Harness:** 5.3 minutes for 138 states on production.
- **Evaluators:** 626,301 tokens for the five, both passes, as the agent tool
  reported them; the subagent that checked a picture could be seen, 74,889.

## Screenshots

The harness's captures, the evaluators' visits and their ten JSON documents are in
the git-ignored `web/dogfood-out/production-step20/`; no picture is added here,
because the round changed nothing on the site.
