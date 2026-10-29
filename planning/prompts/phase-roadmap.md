<!-- planning/prompts/phase-roadmap.md -->
# Paste-prompt — write a phase roadmap

Fill the `{{placeholders}}`, then paste everything below the rule
into a **new** chat in the project and submit. Defaults are shown
for every placeholder; delete a bracketed line if it does not
apply.

| Placeholder          | Meaning                                   | Default                                    |
| -------------------- | ----------------------------------------- | ------------------------------------------ |
| `{{N}}`              | Phase number (two digits in filenames)    | —                                          |
| `{{PROJECT_ROADMAP}}` | The parent project roadmap                | `@docs/roadmap/ROADMAP.md`                 |
| `{{OUTPUT}}`         | Where the phase roadmap is written        | `docs/roadmap/phase{{NN}}-roadmap.md`      |
| `{{PRIOR}}`          | Previous phase roadmap(s), for continuity | `@docs/roadmap/phase{{NN-1}}-roadmap.md`   |

---

Write the Phase {{N}} roadmap for this project.

Step 0 — refresh the planning kit so the templates and catalog are
current. Run `pip install -U roadmodel && roadmodel export-kit . --force`
(where roadmodel is not installed, run
`scripts/export-planning-kit.sh .` from a reviewed checkout instead; it bootstraps a released wheel). Then open
`planning/templates/phase-roadmap-template.md` and confirm its Stage 3
reads "OPEN THE PR, THEN MARK THE STEP", its Stage 6 reads "DISPOSE
OF EVERY FINDING, DECLARE COMPLETION, THEN NEW CONVERSATION", and its
Step 1 has `**Status:** Not started` directly under the `## Step 1`
heading. If Stage 3 is a bare "OPEN THE PR", Stage 6 tells you to put
findings in a "Follow-ups (non-blocking)" note after the completion
line, a step's Status line sits after its `**Deploys:**` line, its
Settings tables have no `Backup` row, or its ladder tables have no
`Price` row, STOP
and tell me the kit is stale — do not write the roadmap from it.

Step 0b — roadmaps live in `docs/roadmap/`: `ROADMAP.md` and every
`phaseNN-roadmap.md`, together. A project that keeps them git-excluded
(e.g. `private/`) keeps them there, and the rest of this step does not
apply: a tracked `ROADMAP.md` beside them is a published copy.
Otherwise, STOP and tell me to run `/roadmap-refresh` first when this
project's roadmaps have not moved yet: a `phaseNN-roadmap.md` that git
does not ignore (committed, or written and not yet committed) sits
outside `docs/roadmap/`, or `docs/roadmap/` holds no project roadmap
while this project's roadmap sits elsewhere. `/roadmap-refresh` moves
them into `docs/roadmap/` and updates every reference to them. Do not
write a new roadmap beside them. Once the project roadmap is in
`docs/roadmap/`, any other file named `ROADMAP.md` is a different
document (a brief's status page, a published copy): leave it alone. A
project roadmap written before this convention may carry another name
(e.g. `agentic-bot-farm-v1.md`); it is the file in `docs/roadmap/` the
phase roadmaps name as their parent.

Step 0c — this roadmap is written with the settings the project
roadmap names for it. Read the `### Phase {{N}}` section of
`{{PROJECT_ROADMAP}}` and its **Phase roadmap settings** table, and
print one line: `Phase {{N}} roadmap settings: Model <M> · Platform
<P> · <its dials, e.g. Effort Max, plus Thinking On where the model has the toggle>. This session: <your
own model> on <this surface>.`

- Name your exact model, never only its family. On Codex your
  instructions say just "based on GPT-6", but the model picked and its
  effort are in the session's rollout: the most recently modified
  `rollout-*.jsonl` under `sessions/` in `CODEX_HOME` (default
  `~/.codex`; `%USERPROFILE%\.codex` on Windows) whose first line
  (`session_meta`) has this repo as its `cwd`, compared case- and
  slash-insensitively (Windows records `e:\Code\…` where the shell
  prints `E:\Code\…`); its last `turn_context` line holds `"model"`
  (e.g. `gpt-6.1-sol`) and `"effort"`. Read it with a reader that shares
  the open file (Python's `open`, PowerShell's `Get-Content`), and never
  take a rollout from another directory. Where no source names
  the model, print `unverified`, ask me which I picked, and go on with my
  answer.
- A ladder (Cost / Balanced / Quality columns): each column ranks a
  Pick, a Runner-up and a Backup — from roadmodel 0.2.95 a bold group
  label each, beside its Model / Platform / Level / AA / Price rows
  (0.2.94 wrote them as `- Pick:` lists, 0.2.93 as `1 · Pick` rows,
  and older ladders Model / Backup rows with no Runner-up) — and its
  **Runs:** line names the
  column this session runs (Quality, for a phase roadmap). Apply that
  line's rule to the Usage-pool status table in
  `planning/user-context.md`: a pool that reads `tight` or `exhausted`
  moves the run to the first of the column's Runner-up and Backup whose
  pool has headroom; with neither, `tight` moves it to the Cost
  column's Pick and `exhausted` to the column's Backup. That option's
  model, platform and dials are the ones checked below; print which
  column and rank it is.
- You are its Model on its Platform, or a newer version in the same
  line (Opus 5 → Opus 5.5, Fable 5 → Fable 5.1, GPT-6 Sol → GPT-6.1
  Sol): continue, and say so on the line. In a ladder, any
  option on its own platform continues too; when it is not the one
  the rule selects, say which one is.
- You are its Backup on the backup's platform: continue — I have
  switched to it — and say so on the line.
- Anything else — a different line, an older version, another
  surface: STOP and tell me how to switch (Claude Code: `/model <M>`,
  then `/roadmap-phase {{N}}` again; elsewhere: the model picker and
  reasoning setting). Do not write the roadmap on a model it did not
  intend.
- You cannot see your own reasoning dial (Codex's is the rollout's
  `"effort"`; print it). `/roadmap-phase` sets Claude
  Code's effort to `Max` by itself, the deepest rung, so never below
  the table; pasted by hand, or on another surface, the printed line
  is my cue to set the dial before you go on.
- No such table (a project roadmap written before roadmodel 0.2.54):
  pick the settings now by the **Phase roadmap settings** rule in
  `planning/templates/project-roadmap-template.md`, print them on the
  same line, and apply the same checks. Leave the project roadmap as it
  is — `/roadmap-refresh` adds the table.

Step 1 — write `{{OUTPUT}}` from
`@planning/templates/phase-roadmap-template.md`, expanding the
Phase {{N}} section of `{{PROJECT_ROADMAP}}` into an executable plan.
Carry forward anything `{{PRIOR}}` hands to this phase (its closing
"inherits" line, its Not-in-scope items owned by this phase, and any
carry-over checklist).

For **each step's** Settings table, classify the step first: its
PRIMARY and SECONDARY category, its complexity, and whether it is novel
problem-solving (the model selector's Steps 1 and 2 in
`@planning/model-selector.txt`, against `@planning/user-context.md`).
Where `roadmodel` is installed, the Settings are the ladder
`roadmodel ladder --category <c> --complexity <x> [--novel]` prints for
that classification (MCP tool: `roadmap_settings`), pasted as printed
with its **Runs:** line. It carries the full recommendation /recommend
shows: Cost, Balanced and Quality, each ranked three deep (the Pick,
the Runner-up, and a Backup from another maker), each option on one
its own level, AA Index and price. The step's runner picks the column from the
usage pools on the day, so the roadmap needs no refresh when a pool
tightens. Its models are always the latest version of their series.
The Model rationale explains the classification and what sets the
columns apart for the step; the Summary Table row and the step's
selection block restate the column the **Runs:** line names.

Where `roadmodel` cannot be reached, run the model selector as the
engine instead (prices from `@planning/model-tier-cost-scale.md`,
display rules from `@planning/settings-display.md`) and write the
single-column variant that matches the step's platform. You are the
engine — do not call any external API. Honor every availability
exclusion in the selector, write each step's backup model into its
Settings table's Backup row with the backup's own platform and dial,
and never name an older version of a series (GPT-6 Sol where GPT-6.1
Sol runs, Opus 5 where Opus 5.5 does).

Honor the template's style rules: 80-column prose, zero `{{...}}`
tokens left, `**Status:** Not started` directly under the title and
directly under every `## Step` heading (the step's own PR flips it and
adds ✅ to the heading — Status rule), a Status column in the Summary
Table, every `<task>` block
carrying the full `<lifecycle>` and `<security>` blocks verbatim, and
a Post-Implementation Verification section.

When the file is written, reply with its path and a one-paragraph
summary of the steps and their models. Do not start Step 1 of the
phase — that is a separate conversation.
