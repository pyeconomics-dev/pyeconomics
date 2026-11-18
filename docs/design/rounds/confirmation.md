# The confirmation round on staging

Phase 5 Step 18 ends with one round of the protocol in
[dogfooding.md](../dogfooding.md) on the deployed staging site, through Cloudflare
Access: the harness, then five fresh evaluators. It passes with no Blocker or High
finding and a median no lower than [round 3](round-3.md)'s 7.38.

**Where it stands (2026-11-18): the harness passes on staging; the evaluators' pass
has not been run.** The harness found three defects that no local run had shown;
they were fixed and the harness is clean on the fixed deployment. The evaluators
were started and could not be shown the site's screenshots, so nothing they returned
is counted, and their pass waits on the maintainer (below). Step 18's "Deployed &
verified" criterion is therefore met for the deploy and not yet for the round. The
three issues the loop left open have since been fixed, and the harness is clean on
the deployment that holds them (below).

## The harness on the merge commit's deployment

Staging's deploy of Step 18's merge commit (238e937) succeeded. `npm run dogfood`
against it, run `staging-confirm`: all 138 states answered, with no console error
and no policy violation, but with two kinds of problem the local rounds never had.
Locally the API answers in a few milliseconds and the data is the stand-in world's;
on staging the API is a network away and the data is real.

| # | Found | Cause | Destination |
| --- | --- | --- | --- |
| S1 | Choosing live data on a phone scrolled the page sideways: 504 pixels on a 390-pixel screen, on a model none of whose profiles the site serves | Round 3 had made the profile picker's options long ("Default (United States data): your own computer only"); a select is as wide as its longest option, and a fieldset does not shrink below its content. No check chose live data on a phone | Fixed in #355: where a profile runs is its group's name (`<optgroup>`), an option is a name alone, the fieldset may shrink |
| S2 | A calculator's result arrived as a jump of the whole page: a layout shift of 0.52 to 0.73 in five of the eight captures that ran a model | A browser counts a move within half a second of a press as the visitor's own. A run on staging takes longer than that | Fixed in #355: the result's heading and a skeleton of its outputs, manifest and downloads take their place with the press of Run; the answer changes values, not positions |
| S3 | A series' page moved when its chart arrived: up to 1.18 on a phone | The room held for the chart was sized to the stand-in data, whose source record is shorter than the hosted site's (no line for the site's daily copy, a shorter notice), and round 3 added a line under the chart: 190 pixels short on a phone, 110 at 820 wide | Fixed in #355: the series keeps the room its placeholder held, sized to the hosted record as measured on staging |
| S4 | A source record read as raw text: `served_from_snapshot:` before its sentence, a retrieval time to the microsecond | Only the hosted site's records carry them | Fixed in #355: the sentence, then its code; a time to the minute. The JSON is unchanged |
| S5 | `/search/` shifted by 0.125 in one of its six captures, and its header grew from 56 to 60 pixels a third of a second after it opened | The text font arriving after the first paint, so the page is drawn twice | Issue [#354](https://github.com/pyeconomics-dev/pyeconomics/issues/354): a fallback face matched to the font's metrics, with a check that holds the font back. It belongs to the font loading Step 17 set up |

S1 is a regression of round 3's own fix (its M10), found one deployment later. Each
of S1 to S3 has a check that reproduces it locally, because the local build cannot
show it by itself: a run held back by a second must move nothing, for a long result,
a result of one output and a result with a chart; live data chosen on a phone, each
profile in turn, must keep the page in its width; a series must stand in the room
held for it with space to spare for a longer record.

## The harness on the fixed deployment

Staging's deploy of #355's merge commit (089ce01) succeeded. Run `staging-confirm-2`:
all 138 states passed, none scrolled sideways, none had a stray scroll box, a console
error or a policy violation, and no capture or task state shifted by more than 0.011
(before the fix: seven above 0.1). The run's 1,359 output files were searched for the
Access service token's two values, and none holds either.

## The three issues the loop filed, fixed

The loop left three findings as issues ([summary](summary.md), "What is left"). The
maintainer asked for all three to be fixed before the evaluators' pass, each in a
pull request of its own:

| Issue | What changed | Pull request |
| --- | --- | --- |
| #354, a late text font moves the page | Fallback faces over the system serifs with the text font's metrics, and a check that holds every font file back | #358 |
| #350, the formulas' typography | A word in a subscript or superscript is upright; no formula is wider than a phone's screen | #363 |
| #351, the bond models' first example | Each opens on a five-year bond with a 4% annual coupon at a 5% yield, and a price says it is per 100 of face value | #365 |

What the first of them does not reach is written down, with its measurements, in
[direction.md](../direction.md) ("Late fonts") and issue #359: a late font can still
rewrap a paragraph on a Linux desktop at ordinary density, and macOS, iOS and Android
were not measured.

Staging's deploy of #365's merge commit (638696e) succeeded. Run `staging-confirm-3`,
on 2026-11-18: all 138 states passed, none scrolled sideways, none had a stray scroll
box, a console error or a policy violation, and no capture or task state shifted by
more than 0.013. Its 1,358 output files hold neither value of the Access service
token. Measured on the same deployment at a phone's width, all 247 display formulas
fit the plate that holds them; before #363, 54 of 194 did not.

The evaluators' pass, when it runs, runs on a deployment that holds these.

## The evaluators

Five fresh evaluators on Claude Sonnet 5.5 were started on the fixed deployment, one
per persona, with the protocol's prompt word for word and the working notes of rounds
1 to 3, changed only for where the site is and how the browser tool signs in to it.

**None of them could see the site.** On the maintainer's machine a gateway removes
images from what an agent reads, so that no client document can reach a model, and
by this round it removed every screenshot an evaluator opened. One evaluator stopped
at once and said so. Two returned scores and said in their findings that the four
visual dimensions were scored from text and accessibility trees and were unverified.
The other two were stopped by the implementer once three had reported the same
thing. **No score from this pass is counted**: the protocol judges what a visitor
sees, and none of these saw it. In rounds 2 and 3 the evaluators described details
only a picture shows and reported no removal, so those rounds stand.

What two of them could read as text, checked:

| Said | Checked |
| --- | --- |
| On a phone, pressing Run showed no result | Not reproduced: a run on staging at 390 wide reads "The run finished: 16 outputs, no warnings." The tool had pressed the link "Run the calculator" before the form loaded |
| Filling the field labelled "Search" timed out on a phone | The tool's fault: it took the first control with that label, the header's hidden box, and a link that shares the label. It now takes the first such control in view (dogfooding.md's change log, 2026-11-17) |
| The bond models take dates, and a price has no unit a learner knows | Issue #351, as in all three rounds |
| An error about two inputs sat under one of them | Not reproduced: the check that both fields are marked passes |
| A search result's excerpt for a domain page begins with a stray fragment | Low; not yet looked at, and left for the pass that follows |

**What the pass waits for.** Lifting the gateway for the site's own screenshots is
the maintainer's decision, not an agent's to work around. When it is lifted, the
five evaluators run again on staging and this record gains their scores, findings
and after-scoring check of round 3's list. Until then Step 19 does not start: a High
finding here is fixed on a `fix/` branch first.

## The visual baselines, checked again

The commit that drew the 52 baselines, and the description of pull request #352, say
each picture was looked at before it was committed. That was not so: the session that
committed them could not see images, for the same reason the evaluators could not,
and had checked them by count, size and name. They have since been checked by two
means that need no eye:

- **By text.** On the thirteen sample pages at both widths, the only text in a first
  screen that names the site's operator or gives a mail address is the privacy
  policy's contact paragraph, which the comparison masks. No such text is outside a
  mask.
- **By pixels.** Exactly four of the 52 pictures, the privacy page's, hold the mask's
  colour, each as one solid rectangle of the size and at the place that paragraph has.

So no baseline holds personal data. Whether each picture looks right is still for an
eye, the maintainer's or an agent's once images may be read. #355 changed no first
screen (the web job's comparison passed on it), so the baselines stood as committed.

#363 changed how formulas are written, and so 14 of the 52: the first screens of the
bond pricing, policy rule and time value pages at both widths in both themes, and
the GARCH page at 1440 wide. They were redrawn by the web job and committed unseen,
checked the same two ways: every pixel that differs from the earlier picture lies
inside the page's formula plate, whose box was read from the built page in the
runner's own Linux image, and on the two pages whose first formula was not rewritten
that formula is the same in every pixel. The pull request says so and asks the
maintainer to look. #358 and #365 changed no first screen.

## Cost

- **Harness:** 4.6, 4.5 and 4.9 minutes for the three runs of 138 states on staging.
- **Evaluators:** about 257,000 tokens for the three that reported (81,164, 86,493
  and 89,633), none of it a counted evaluation; the two that were stopped reported no
  figure.
- **Implementer:** two and a half hours from the first harness run to #355's fixes
  and checks, with every gate run on the fix's build (772 unit, 366 built-site and 521
  end-to-end tests, the local app's 4, web parity's 92, and Lighthouse on the fifteen
  sample pages: 97 to 100 for performance, 100 for accessibility). One of the new
  checks raced on the CI runner, which is faster than the machine it was written on,
  and was corrected before the merge.
