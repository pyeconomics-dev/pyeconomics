# The dogfooding loop: three rounds, and why it stopped

Phase 5 Step 18 ran the protocol in [dogfooding.md](../dogfooding.md) on the site
until another round stopped paying for itself. Each round: build the site, capture
every page type and task state with the harness, give five fresh evaluators (one a
persona, none of whom had seen the implementation or an earlier round) the
protocol's prompt, merge their findings, fix them with every gate green, and begin
again. This page is the loop's account: each round's median, the trend, why it
stopped, what it cost and what is left.

## The rounds

| Round | When | Median | Change | Blocker | High | Medium | Low | Tasks passed, hard, failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [0](../audit-round-0.md) (Step 17, before its design) | 2026-11-15 | 5.75 | | 0 | 7 | 14 | 10 | 9, 12, 0 |
| [1](round-1.md) | 2026-11-16 | 7.00 | +1.25 | 0 | 3 | 17 | 13 | 12, 9, 0 |
| [2](round-2.md) | 2026-11-16 | 7.50 | +0.50 | 0 | 0 | 11 | 17 | 17, 4, 0 |
| [3](round-3.md) | 2026-11-16 | 7.38 | −0.13 | 0 | 0 | 13 | 19 | 17, 4, 0 |
| [Confirmation](confirmation.md), on staging | 2026-11-18 | 7.38 | 0.00 | 0 | 1 | 19 | 27 | 20, 1, 0 |
| [Production](production.md), the readiness gate's | 2026-11-27 | 7.38 | 0.00 | 0 | 0 | 11 | 13 | 18, 3, 0 |

The median is the median of the five evaluators' means over the rubric's eight
dimensions. By dimension:

| Dimension | Round 0 | Round 1 | Round 2 | Round 3 | Confirmation | Production |
| --- | --- | --- | --- | --- | --- | --- |
| D1 First impression and identity | 5 | 8 | 8 | 8 | 8 | 8 |
| D2 Hierarchy and layout | 5 | 7 | 7 | 7 | 7 | 7 |
| D3 Typography and formulas | 6 | 8 | 8 | 8 | 8 | 8 |
| D4 Colour, contrast and theming | 5 | 8 | 8 | 7 | 8 | 7 |
| D5 Interaction, feedback and motion | 6 | 7 | 7 | 7 | 7 | 7 |
| D6 Navigation and findability | 6 | 6 | 7 | 7 | 7 | 7 |
| D7 Content and microcopy | 6 | 6 | 7 | 6 | 7 | 7 |
| D8 Trust and polish | 6 | 7 | 8 | 8 | 7 | 8 |

The readiness gate's round (Phase 5 Step 20) ran on production, on the release
candidate `1.0.0rc2`, with fresh evaluators: median 7.38, as round 3's, with no
Blocker or High, so the design and UX criterion passed. Its findings are in issue
#408 and the issues it names.

## The trend

Step 17's design moved the look: identity, layout, typography and colour rose by
two or three between rounds 0 and 1, and have not moved since. Round 1's fixes moved
what was left in the calculator, the explorer and the words (navigation, content
and trust each rose by one in round 2). Round 3's evaluators, on a site with round
2's fixes, scored it within a quarter of a point of round 2's: every evaluator is
new each round, so a round's median is one draw, and two draws that close say the
site has stopped moving on this rubric.

The findings say the same more plainly than the scores. High findings went 7, 3,
0, 0. Tasks a persona could not finish without a wrong turn went 12, 9, 4, 4 of 21,
and none ever failed. Round 3's Medium findings were smaller than round 1's: a
snippet's box too short for its last lines, a count that differed by one, a version
number whose one read as an l.

## Why it stopped

The rule: stop after the first round, from round 2 on, that finds no Blocker or
High issue and raises the median by less than 0.5 over the round before; stop at
round 6 regardless.

- Round 2 found no Blocker or High issue, but raised the median by exactly 0.5,
  which is not less than 0.5. The loop went on.
- Round 3 found no Blocker or High issue and did not raise the median. The loop
  stopped, three rounds short of its limit.

No High finding was left open, so none is filed for Step 20's gate. Step 20 reruns
the protocol on production's build; its baseline is round 3: a median of 7.38, no
Blocker and no High.

## The confirmation round on staging

The step ends with one round on the deployed staging site
([confirmation.md](confirmation.md)). Its harness found what no local round could:
staging's API is a network away and its data is real. Choosing live data on a phone
scrolled the page sideways (a regression of round 3's own fix), a result that took
more than half a second arrived as a jump of the whole page, and a series' page
moved when its chart arrived, because the hosted site's source record is longer than
the stand-in data's. All three were fixed (#355), each with a check that reproduces
it locally, and the harness is clean on the fixed deployment: 138 states, no
sideways scroll, no capture shifting by more than 0.011.

**Its evaluators' pass ran on 2026-11-18 and 19**, once the maintainer's machine let
an agent see the site's own screenshots (a first attempt on 2026-11-17 saw none, and
is not counted). The median is 7.38, round 3's exactly. Twenty of twenty-one tasks
passed and none failed: the candidate's bond-pricing task, hard in all three rounds,
passes. There was no Blocker and one High finding, which only a deployed site could
show: the site's daily copy of the unemployment rate held under three years of a
series that begins in 1948, because its source answers a request without dates with
three years, and the page drew them and said "Done". It is fixed in #370 and #378:
the copy reads each such series from its first year, and a series' page says the
dates it drew. Both are deployed and verified on staging: the copy holds 274 months of
each series after its first run and gains twenty years a run, and a fresh evaluator
in the student's persona passed all four tasks on the fixed site, with no Blocker
and no High.

## What is left

The confirmation round's 19 Medium and 27 Low findings stopped no task. They are
issues [#371](https://github.com/pyeconomics-dev/pyeconomics/issues/371) to
[#377](https://github.com/pyeconomics-dev/pyeconomics/issues/377), by part of the
site (search, a phone's layout, the calculator's errors, series pages, words, the
developer's pages, the time-value model's first example), with seven Low findings
disputed or sent elsewhere for the reasons in [its record](confirmation.md). Step 20
reruns the protocol on production's build, held to 7.38 with no Blocker and no High.

All three issues below were fixed on 2026-11-17 and 18, after the loop and before
the confirmation round's evaluators ([confirmation.md](confirmation.md)): #351 in
pull request #365, #350 in #363 and #354 in #358. What #358 does not reach is issue
[#359](https://github.com/pyeconomics-dev/pyeconomics/issues/359).

Two findings came back in more than one round and belong to the models, not the
pages, so each was an issue:

- [#351](https://github.com/pyeconomics-dev/pyeconomics/issues/351): the bond
  models take dates and open on a thirty-year Treasury; a learner thinks in "five
  years, 4%, 5%". The candidate persona's pricing task was hard in all three rounds
  for this reason.
- [#350](https://github.com/pyeconomics-dev/pyeconomics/issues/350): the formulas'
  typography, written in the models: word subscripts set in italic (round 0), and
  long formulas that a phone reads by swiping (round 3).

A third came from the confirmation round:
[#354](https://github.com/pyeconomics-dev/pyeconomics/issues/354), the text font
that arrives after a page's first paint and reflows it on a slow connection.

Five findings were disputed each time they returned, each with its reason in the
rounds' records: the header's two rows of navigation (every domain one click away,
ADR-0013 decision 10); "On this page" listing every section; a model's formulas in
one plate (its card gives a list, with no groups to lay out); a form showing every
field that has a default (its value changes the result); and the unit "money" (the
models hold no currency). They are the places a later design pass would look first.

## What locks it in

- Visual baselines: the first screen of ADR-0013 decision 19's thirteen sample
  pages at 390 and 1440 pixels wide, in light and dark, compared in the web job on
  Linux (`npm run e2e:visual`). They were committed without having been seen (the
  session could not read images), checked by their pages' text and their masks'
  pixels, and then, on 2026-11-18, each looked at
  ([confirmation.md](confirmation.md)). The look found what the measurements had
  not: formulas written over two lines stood misaligned on 14 model pages (#369).
- A check for each class of bug the rounds found, so the class fails CI and not
  only the instance:

| Bug class | Found in | Check |
| --- | --- | --- |
| A word glued to the link or code beside it | Round 1 | `tests/site/` "prose", over every built page |
| What is typed before an island loads is lost; a control that cannot work yet | Rounds 0 and 1 | `tests/e2e/hydration.spec.ts` |
| A page shifts as its calculator, chart or results load | Rounds 0 to 2 | `tests/e2e/layout-shift.spec.ts`, three sizes; `scripts/form-room.ts` to refit |
| A failed copy says nothing | Round 0 | `tests/e2e/copy.spec.ts`; one copy control, a unit test |
| A result or a reference table wider than a phone | Rounds 1 and 2 | `calculator.spec.ts` and `pages.spec.ts`, measured at 390 |
| Anything in a closed disclosure transitions | Step 17 | `tests/e2e/motion.spec.ts` |
| A control fades back from its disabled state | Round 2's gates | a unit test over every source file |
| A page of formulas paints in two steps | Round 2's gates | `tests/site/`: the link that holds the first paint, on every model page |
| A notice that contradicts what the page does | Round 1 | `tests/site/` and `models.test.ts`: the profiles that run here come first |
| JSON a page shows that does not parse back | Round 2 | `snippets.test.ts`, every golden case's inputs |
| The site's MCP tools drift from the server's | Round 2 | `tests/web/test_mcp_tools_listed.py` |
| Two counts of one thing | Round 3 | `calculator.spec.ts`: the line under the form and the result's summary |
| A result that arrives more than half a second after the press moves the page | Confirmation, on staging | `layout-shift.spec.ts`, "a slow run": the request is held back by a second |
| A control as wide as its longest option pushes a phone's page sideways | Confirmation, on staging | `calculator.spec.ts`: live data chosen at 390 wide, each profile in turn |
| Room sized to the test data, not to what the hosted site shows | Confirmation, on staging | `explorer.spec.ts`: a series stands in the room held for it, with space to spare |
| A formula over two lines set as a centred table | Confirmation, the first look at the baselines | `pages.spec.ts`: every row of every such table, on every model's page |
| The hosted copy of a series cut short by its source's default | Confirmation, on staging | `test_snapshot_set.py`: every BLS entry has its first year; `tests/staging/explorer.spec.ts`, after every deploy; and the page says the dates it drew |
| A picture taken while the page is still scrolling | Confirmation (the harness's own) | `support.ts settled` waits for the scroll to end |

## What it cost

| Round | Harness | Evaluators (both passes) | Evaluators' tokens | Implementer pass |
| --- | --- | --- | --- | --- |
| 1 | 3.9 min | 16 min | 650,610 | 1 h 40 min |
| 2 | 4.1 min | 12 min | 851,929 | 2 h 23 min |
| 3 | 4.2 min | 12 min | 656,861 | 29 min |
| Total | 12 min | 40 min | 2,159,400 | 4 h 32 min |
| Confirmation, on staging | 5 runs, 23.0 min | 7 to 22 min, then 9 to 33 min; the re-check 17 min | 1,322,072, and 237,088 for the re-check | in [its record](confirmation.md) |

- **Evaluators:** fifteen runs of Claude Sonnet 5.5, 2.16 million tokens as the
  platform reported each subagent's use. Claude Code's subagents run Claude models
  only, so the evaluators were a different model from the implementer's, and the
  same model round 0 used, which keeps the four rounds' scores comparable.
- **Implementer:** Claude Fable 5.2, in one session of 6.5 hours from the step's
  start to the end of round 3's pass, the issue-343 work (the formulas' symbols, 756
  definitions across the 50 models) included: 0.78 million tokens written, 1.64
  million tokens of new context, and 283 million tokens of context read back from
  the cache, as the session's own record counts them.
- **Where the implementer's time went:** about an hour of round 2's pass went to
  what the gates found and no evaluator did (a two-step paint that Lighthouse timed
  at 3.5 seconds, a room estimate that had drifted, a button read mid-fade). The
  evaluators find what a visitor meets; the gates find what a visitor would meet
  one time in six.

## What the loop taught

- A fresh evaluator finds what the last one could not: the page it never saw
  improved. Round 2's first-time visitor asked "who made this?" of a site whose
  round-1 fix had only moved the answer; round 3's passed every task.
- Evaluators are sometimes wrong on a fact (a bond price recomputed badly, a row
  height judged from a thumbnail, a search read before its results). Each claim
  was checked by running or measuring before it was fixed or disputed, and the
  records say which were not reproduced.
- The harness is part of the product under test. Four of its own faults were
  charged to the site (a capture mid-animation, a tool that could not open a
  disclosure, a scripted choice scored as a layout shift, a fill that took a hidden
  control), each fixed and dated in the protocol's change log.
- The local build is not the deployed site. A local API answers in milliseconds and
  serves stand-in data, so anything that depends on latency or on a real record's
  length shows only on staging. Run the harness there and read its records before
  the evaluators start, and give each class a check that makes the local build
  slow or long on purpose.
- An evaluation that did not see the pages is not an evaluation. Three evaluators of
  the confirmation round said their screenshots had been removed; their scores were
  discarded, not averaged in.
- A measurement is not a look. The two-line formulas passed every check of width
  and stood misaligned in the pictures; the first time anyone looked, it took one
  picture to see.
- The deployed site's data is part of the site. Every local round's unemployment
  series ran from 2018, in stand-in data; the deployed copy ran from 2024. Give a
  deployed check to whatever only the deployment holds.
- A fix to the data plane is rehearsed against the source, not only against a
  script of it. The first fix for the short history passed every test and, on its
  first run on staging, left each series shorter still, because a real source's
  notice carries the day it was read and a scripted one's never changed.
