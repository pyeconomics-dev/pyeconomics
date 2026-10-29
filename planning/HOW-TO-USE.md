<!-- planning/HOW-TO-USE.md -->
# roadmodel planning kit — how to use

This folder is a **planning kit** exported from
[roadmodel](https://github.com/nathanramoscfa/roadmodel). It lets an in-editor
AI (Claude Code, Cursor, etc.) author project and phase roadmaps **with
per-step model recommendations**, without installing anything or calling any
paid API.

## What's here

| File | Purpose |
| ---- | ------- |
| `model-selector.txt` | The recommendation **algorithm** + the inline model **catalog** (ratings, `best-for`, availability exclusions) + `<benchmark-sources>`. |
| `model-tier-cost-scale.md` | Per-token **prices** and **subscription tiers** — the funding/cost data the selector's access-selection step consumes. |
| `settings-display.md` | The **display contract**: how the selector's setting fields map to the real controls each surface exposes (which dials to show, which to omit). Read it before writing any Settings table. |
| `user-context.md` | The operator's **subscriptions + API keys + platform preference order** — decides *which platform pays* for each pick. |
| `templates/project-roadmap-template.md` | Skeleton for a whole-project `docs/roadmap/ROADMAP.md`. |
| `templates/phase-roadmap-template.md` | Skeleton for one `docs/roadmap/phaseNN-roadmap.md`, beside it. |
| `prompts/project-roadmap.md` | **Fill-in paste-prompt** that writes `ROADMAP.md` from the project template — refreshes the kit first. |
| `prompts/phase-roadmap.md` | **Fill-in paste-prompt** that writes one `phaseNN-roadmap.md` — refreshes the kit first. |

## The one rule: **you are the engine**

When asked to recommend a model for a step, **run the `model-selector.txt`
algorithm yourself, in your own context.** Do **not** call any external API,
MCP tool, or web service — the operator's editor session already pays for your
reasoning (e.g. Claude Code funded by a flat Max plan = $0 marginal). Calling
out would add cost for no benefit.

**Where `roadmodel` is installed, the Settings come from it.** Classify
the step (step 1 below), then paste the ladder and **Runs:** line
`roadmodel ladder --category <c> --complexity <x> [--novel]` prints: the
Cost / Balanced / Quality picks /recommend shows, each ranked three deep (the
Pick, the Runner-up, and a Backup from another maker), each option with its
level, AA Index and price. It is local code — no API
call, no engine — and it
reads every usage pool at headroom, so the ladder outlives a pool's state: when
a pool reads `tight` or `exhausted`, `/roadmap-step` runs another column
instead of the roadmap being refreshed. Its models are always the latest
version of their series (GPT-6.1 Sol, never GPT-6 Sol where both run). The
project roadmap's phase tables come from `roadmodel ladder --category
planning --complexity high --phase`. Steps 2–4 are the fallback where
`roadmodel` cannot be reached.

Concretely, for each roadmap step:

1. **Classify** the step's task with the selector's
   `<task-categorization>` / `<selection-algorithm>` (PRIMARY category +
   complexity).
2. **Pick the model** by running `<selection-algorithm>` against the inline
   `<model>` catalog in `model-selector.txt` and the prices in
   `model-tier-cost-scale.md`. Honor the **availability exclusions** (any model
   marked "do NOT recommend" — e.g. a withdrawn flagship — is off the table;
   use its documented fallback).
3. **Pick the platform** by running `<access-selection>` against
   `user-context.md` — the cheapest access method that can run the chosen model
   given the operator's active subscriptions (a Claude pick → "Claude Code"
   funded by Max; a GPT pick → "Codex" funded by ChatGPT Pro; etc.).
4. **Emit** the step's Settings table using the **platform-specific variant**
   the template defines. Every table carries Model / Backup / Platform /
   Conversation plus **only the dials the chosen surface actually exposes** — Claude Code →
   Effort + Thinking(On/Off), with Thinking `—` on a model that always thinks
   (Opus 5.5, Sonnet 5.5, Haiku 5.5, the Fable models), which has no toggle; Codex and the other reasoning-dial surfaces
   (ChatGPT app, provider APIs, Gemini CLI) → the effort dial under that
   surface's own label (Codex calls it Intelligence) + Thinking where it has a
   separate toggle; Cursor → Max Mode alone, since Cursor exposes no reasoning
   dial. A dial the surface lacks is **omitted**, never written as `Off` or
   `N/A`; Max Mode in particular is a Cursor-only row and must not appear on a
   Claude Code or Codex table. Add a Model-rationale paragraph that names the
   funding source and justifies each emitted dial in the surface's native
   vocabulary. The **Backup** row names the model to run in case the primary is
   unavailable to the operator — from a different provider family, with its
   own platform and dial in one cell (`GPT-5.6 Terra — Codex · Intelligence
   Medium`).

The project roadmap uses the same engine for one more table per phase: its
**Phase roadmap settings**, the model and dials for the session that writes
that phase's roadmap. They are picked quality first — the strongest planning
model the operator's access methods reach, at its deepest reasoning rung —
because a phase roadmap fixes every step after it. `prompts/phase-roadmap.md`
checks the session against them before it writes anything.

## Paste-prompt

Do not type the ask each time. Open `prompts/phase-roadmap.md` (or
`prompts/project-roadmap.md`), fill the `{{placeholders}}` in its table, paste
everything below its rule into a **new** chat in this project, and submit.

Each prompt starts with a Step 0 that refreshes this kit
(`pip install -U roadmodel && roadmodel export-kit . --force`) and checks the
template's step lifecycle is current (Stage 3 marks the step's `**Status:**`
line, directly under its heading, in its own PR; Stage 6 disposes of every finding before the completion
line) before anything is written, so a stale kit fails loudly instead of baking
an old step lifecycle into every step. The ask itself
is the one below — the prompt files carry it with the placeholders filled:

> Write the Phase N roadmap `.md` using `@planning/templates/phase-roadmap-template.md`
> as the template. For **each step's** Settings table and Model rationale, run
> the model selector in `@planning/model-selector.txt` (with prices from
> `@planning/model-tier-cost-scale.md`) against `@planning/user-context.md` — you
> are the engine, do not call any external API. Honor every availability
> exclusion in the selector. Fill the rest of the template from the project
> roadmap, and include a backup model per step.

## Staying current

This kit is a **snapshot**. roadmodel's catalog is refreshed continuously
(new models, price changes, availability kill-switches), so **re-export the kit
at the start of each phase** to pull the latest:

```sh
# Cross-platform (Windows / macOS / Linux), with roadmodel installed:
pip install -U roadmodel
roadmodel export-kit /path/to/this/project

# Or use the release wrapper from a reviewed roadmodel checkout:
scripts/export-planning-kit.sh /path/to/this/project
```

A stale kit risks recommending a model that has since been withdrawn or
repriced — re-exporting is the cheap insurance.
