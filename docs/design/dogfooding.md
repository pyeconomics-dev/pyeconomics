# The dogfooding protocol

How pyeconomics.dev is looked at as a visitor sees it. Phase 5 Step 17 wrote this
protocol and ran its round 0. Step 18 repeats it after each round of fixes, and
Step 20's readiness gate runs it once more. Every round runs it **unchanged**: the
same personas, tasks, rubric, severity scale, evaluator rules and harness. A
change to any of them is a change to this file, made in its own pull request and
dated below, so the rounds stay comparable.

A round has four parts:

1. The harness captures every page type (section 5).
2. Five evaluators work in parallel, one for each persona (section 4).
3. The implementer merges their findings and scores (section 6).
4. The round's record goes in `docs/design/` (section 6 names the file).

## 1. Personas and tasks

Each evaluator is one persona and does that persona's tasks in a real browser, in
the persona's own words. A task **passes** when the persona finishes it without
help from outside the site. It is **hard** when the persona finishes it only after
a wrong turn or a guess. It **fails** when the persona cannot finish it.

### P1. A CFA® Program candidate

Studying for an exam, checking a formula they half remember, on a laptop in the
evening.

1. "I want to check the formula for a bond's Macaulay and modified duration, and
   what each symbol means."
2. "Compute the price of a 5-year bond with a 4% annual coupon at a 5% yield, and
   see the answer with its units."
3. "Change one input to something impossible, like a negative number of years,
   and see whether the site tells me what is wrong."
4. "Find the other models for the same topic area I am studying."

### P2. A Python developer

Evaluating the library for a project: wants code, not prose.

1. "Find how to install it and run one model from Python."
2. "Get the command-line and curl versions of a calculation I just ran on the
   site."
3. "Find out whether there is an MCP server I can give my AI assistant, and the
   tool's name for a model."
4. "Decide whether the results are reproducible: what comes with a result besides
   the number?"

### P3. An economics student

Writing an essay on unemployment and interest rates.

1. "Find the US unemployment rate and look at it as a chart over the last ten
   years."
2. "Download that series as a CSV and check where the data comes from and how to
   cite it."
3. "Find a model that uses live data, such as a policy rule, and run it on the
   latest data."
4. "Find out which data sources the site can and cannot serve, and why."

### P4. A first-time visitor

Arrived from a link and gives the site thirty seconds.

1. "In thirty seconds: what is this, who is it for, and is it free?"
2. "Is it credible? Who made it, where do the formulas come from, is it tested?"
3. "Try one thing without reading any instructions."
4. "Find the terms of use and the privacy policy, and whether I can be told when
   1.0 ships."

### P5. A phone visitor on a slow connection

On a phone in a train, on a slow and patchy connection.

1. "Open the home page and get to a model's calculator."
2. "Run the calculator with its example and read the result without zooming or
   scrolling sideways."
3. "Use the site's search to find 'Sharpe ratio'."
4. "Open the menu of domains and go to one."
5. "Read a long formula on a model page."

## 2. The rubric

Each evaluator scores each of the eight dimensions from 1 to 10 for the pages they
used, against the anchors below. A score between two anchors means "between those
descriptions". Every score of 6 or less comes with at least one finding that
explains it.

| Dimension | 1–2 | 3–4 | 5–6 | 7–8 | 9–10 |
| --- | --- | --- | --- | --- | --- |
| **D1. First impression and identity** | Looks broken or abandoned | Generic template, no identity; reads as a draft | Tidy but stock; nothing says what it is or makes it memorable | A clear identity: you know what it is and it looks deliberate | Distinctive and confident; the first screen shows what it does and invites you in |
| **D2. Hierarchy and layout** | No clear order; things overlap or break | Long undifferentiated columns; hard to tell what matters | Order is clear but flat; every section weighs the same | Clear primary, secondary and tertiary content; good use of width at every size | The layout guides the eye to the task; dense content stays easy to scan |
| **D3. Typography and formulas** | Text or formulas unreadable, clipped or overlapping | Poor measure or leading; formulas cramped or inconsistent | Readable system text; formulas legible but plain | A deliberate type scale; formulas typeset well and alike on every system | Typography carries the identity; formulas read like a well-set textbook |
| **D4. Colour, contrast and theming** | Text fails contrast; a theme is broken | Grey everywhere or clashing colour; dark theme an afterthought | Consistent but colourless; colour carries no meaning | A real palette in both themes; colour marks actions and states | Colour is purposeful and polished in both themes; states are unmistakable |
| **D5. Interaction, feedback and motion** | Controls do not work or give no feedback | Feedback is missing or confusing; states are unclear | Works, with plain feedback; loading, empty and error states are bare | Clear states for loading, empty, error and success; motion helps orientation | Interactions feel immediate and explain themselves; motion is subtle and purposeful |
| **D6. Navigation and findability** | Can't find the main things | Navigation is crowded or hidden; dead ends | You can find things with effort | The main paths are obvious; search and the menus work at every size | You always know where you are and where to go next |
| **D7. Content and microcopy** | Wrong, contradictory or jargon only | Heavy jargon, raw identifiers, unexplained terms | Accurate but dry; some jargon | Plain, accurate words; terms explained where they appear | Clear, warm and exact; every label and message helps |
| **D8. Trust and polish** | Errors, broken pieces or misleading claims | Rough edges everywhere; looks unfinished | Correct but unpolished; inconsistent details | Consistent and careful; sources and caveats are easy to find | Feels like a product a professional would rely on and cite |

## 3. Severity

| Severity | Meaning |
| --- | --- |
| **Blocker** | A task fails, or a page is broken (missing content, a crash, a layout that hides content, a console error). |
| **High** | A task is hard, or a page looks broken or unfinished. |
| **Medium** | Friction or inconsistency: the task works, but something slows it or reads wrong. |
| **Low** | Polish: spacing, alignment, wording that could be better. |

## 4. Evaluators

- **Fresh.** Each evaluator is a new session or subagent. Before its own pass it
  has seen nothing of the implementation: no source code, no diff, no git history,
  no pull request, and no earlier round's findings or record. It must not open
  `docs/design/` (other than this file's sections 1 to 3, which it is given) or
  anything under `web/src/`.
- **Given only:** its persona and tasks (section 1), the rubric and severity scale
  (sections 2 and 3), the harness output for the round, the site's address and the
  harness's `visit` tool (section 5).
- **Model.** Use a model from another maker than the implementer's where the
  platform allows. Where it does not (Claude Code's subagents run Claude models
  only), use a different model than the implementer's and record which model it
  was.
- **In a real browser.** The evaluator does its tasks with the `visit` tool, at
  the widths and themes its persona implies (P5 at 390 wide; the others at 1440
  and at least once at 390), and reads the harness's screenshots for every page
  type at all three widths in both themes.
- **Returns** one JSON document, and nothing else counts:

```json
{
  "persona": "P1",
  "model": "the evaluator's model",
  "tasks": [
    { "task": 1, "outcome": "pass | hard | fail", "notes": "what happened" }
  ],
  "scores": { "D1": 0, "D2": 0, "D3": 0, "D4": 0, "D5": 0, "D6": 0, "D7": 0, "D8": 0 },
  "findings": [
    {
      "page": "/models/fixed-income/duration/",
      "viewport": "390x844 | 820x1180 | 1440x900 | all",
      "theme": "light | dark | both",
      "severity": "Blocker | High | Medium | Low",
      "dimension": "D1 … D8",
      "evidence": "what is seen, and the screenshot file that shows it",
      "fix": "a suggested change, in visitor terms"
    }
  ]
}
```

The prompt every evaluator gets, with `<…>` filled in:

```text
You are evaluating a website as a visitor. You are <persona name and description>.
Do these tasks in a real browser, in this order: <tasks>.

You have:
- the site at <base URL>;
- a browser tool: `node tests/dogfood/visit.ts --help` (run from web/), which
  opens pages in Chromium at a width and theme you choose, follows steps you give
  it (click, fill, select, press, scroll) and saves screenshots you can read;
- the harness's screenshots of every page type at 390, 820 and 1440 wide in light
  and dark, listed in <harness index>.

Rules: do not read any source code, diff, git history, pull request or anything
under docs/design/ or web/src/; judge only what a visitor sees. Never print,
log or write an environment variable. Score the site with this rubric
<sections 2 and 3>. Return only the JSON document in <section 4's schema>.
```

## 5. The harness

`web/tests/dogfood/`, a Playwright configuration of its own that the end-to-end
run does not include. Chromium is launched **without** `--hide-scrollbars`, so
scrollbars are drawn as they are on Windows (issue #319 showed only there).

```text
cd web
npm run build                       # the local build
npm run dogfood                     # every page type: 3 widths x 2 themes
npm run dogfood -- --grep tasks     # the scripted interaction states only
node tests/dogfood/visit.ts --help  # the evaluators' browser tool
```

- **Local** (the default): `wrangler dev` serves `dist/` on 127.0.0.1:8788 and
  `tests/web/e2e_api.py` answers the API on 127.0.0.1:8799, over the catalog
  world's stand-in data. The harness forwards the page's `/v1/` requests and
  `GET /version` to it, as the end-to-end tests do.
- **Deployed:** set `DOGFOOD_BASE_URL` (for example
  `https://staging.pyeconomics.dev`). Behind Cloudflare Access, also set
  `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` to the CI service token.
  They travel only as request headers. The harness never prints, logs or writes
  them, and no screenshot or record can show them.
- **Output** goes to the git-ignored `web/dogfood-out/<run>/`:
  - for each capture, a full-page screenshot, the first screen, viewport-high
    tiles of the page (for reading a long page), the accessibility tree
    (`.aria.yml`), and a record with load timings, font requests, console errors
    and Content Security Policy violations;
  - `index.json` and `index.md` listing every capture.
- **Page types:** home, `/models/`, a domain, a model page of each kind (instant,
  bound, with a chart, a family, and one whose data the hosted site may not
  serve), `/data/`, a concept, `/coverage/`, `/search/`, a problem page,
  `/newsletter/`, `/pro/`, a legal page, `/sources/` and the 404 page. They are
  listed in `web/tests/dogfood/pages.ts`.
- **Widths and themes:** 390x844, 820x1180 and 1440x900, each in light and dark.
- **Task states** (`tasks.spec.ts`): a calculator before and after a run, a run
  with a chart, a family's calculation switched, a problem shown for a bad input,
  the explorer's chart, a search, the domains menu open on a phone, and the
  library-only notice. Sign-up forms are always captured empty.

## 6. Merging a round

1. Read all five JSON documents. Merge findings that share a page type and a
   cause (keep the highest severity, list every persona that found it).
2. Score table: one row per dimension, one column per persona, and the median of
   the five.
3. Findings by severity, Blocker first, each with its personas, page, evidence and
   destination (fixed in the round, an issue number, or a later step).
4. At most twelve key screenshots, as WebP under 200 KB each, in
   `docs/design/img/`, named `round-<n>-<what>.webp`.
5. Task outcomes: one row per persona and task.

Round 0's record is `docs/design/audit-round-0.md`; Step 18's rounds are
`docs/design/rounds/round-<n>.md`. From round 1 on, each evaluator, **after** it
has returned its scores and findings, is shown the previous round's merged list
and says for each item whether it is fixed, still there or made worse; that
second pass never changes its scores. The round's median is the median of the
five evaluators' means over the eight dimensions. Step 18's stopping rule reads
it: stop after the first round, from round 2 on, that finds no Blocker or High
issue and raises the median by less than 0.5 over the round before, and at round
6 regardless.

## Changes to this protocol

- 2026-11-15: written (Phase 5 Step 17).
