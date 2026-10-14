<!-- planning/prompts/project-roadmap.md -->
# Paste-prompt — write the project roadmap

Fill the `{{placeholders}}`, then paste everything below the rule
into a **new** chat in the project and submit. Defaults are shown
for every placeholder; delete a bracketed line if it does not
apply.

| Placeholder    | Meaning                                                  | Default                     |
| -------------- | -------------------------------------------------------- | --------------------------- |
| `{{BRIEF}}`    | Where the project is described: files, or inline prose   | `@README.md`                |
| `{{OUTPUT}}`   | Where the roadmap is written                             | `docs/roadmap/ROADMAP.md`   |
| `{{CONSTRAINTS}}` | Hard constraints the roadmap must respect (optional)  | —                           |

---

Write the project roadmap for this project.

Step 0 — refresh the planning kit so the templates and catalog are
current. Run `pip install -U roadmodel && roadmodel export-kit . --force`
(where roadmodel is not installed, run
`scripts/export-planning-kit.sh .` from a reviewed checkout instead; it bootstraps a released wheel). Then open
`planning/templates/project-roadmap-template.md` and confirm its Step
lifecycle Stage 3 reads "Open the PR, then mark the step" and Stage 6
reads "Dispose of every finding, declare completion, then new
conversation". If Stage 3 is a bare "Open the PR", Stage 6 tells
you to put findings in a "Follow-ups (non-blocking)" note after the
completion line, a `### Phase` section's `**Status:**` line sits
after its **Goal:** rather than directly under its heading, or a
`### Phase` section has no **Phase roadmap settings** table, STOP and
tell me the kit is stale — do not write the roadmap from it.

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

Step 1 — write `{{OUTPUT}}` from
`@planning/templates/project-roadmap-template.md`. The project brief
is {{BRIEF}}. [Hard constraints: {{CONSTRAINTS}}.] Read the codebase
as needed to fill "Current State Assessment" from what actually
exists, not from the brief alone.

Keep every mandatory §5 section the template marks for a project with
this project's surfaces (security & privacy, release & deployment,
operations & observability, worktree strategy, defect handling), and
say explicitly which optional ones you omitted and why.

For **each phase's** Phase roadmap settings table — the model and
dials for the session that will write that phase's roadmap with
`/roadmap-phase N` — run the model selector in
`@planning/model-selector.txt` (prices from
`@planning/model-tier-cost-scale.md`, display rules from
`@planning/settings-display.md`) against `@planning/user-context.md`,
quality first as the template's style rule says: the strongest
`planning` model the operator's access methods reach, at the deepest
reasoning rung it exposes on its platform (`Max` in Claude Code),
thinking on, never `Ultracode` — unless the user-context states a rule
for roadmap-writing sessions. Where `roadmodel` is installed, take the
model and the backup, not their effort, from the PRIMARY and BACKUP
lines of `roadmodel score --category planning --complexity high
--budget best`: it ranks on measured benchmarks, so a stale catalog
letter cannot steer them, and a model the user-context names for these
sessions still wins. Use the selector the same way wherever
else the roadmap names a model or platform. You are the engine — do
not call any external API. Honor every availability exclusion in the
selector, and write each phase's backup model into its table's Backup
row, with the backup's own platform and dial.

Honor the template's style rules: 80-column prose, no `<PLACEHOLDER>`
tokens left, every `<!-- ... -->` guidance block stripped, numbers
marked "TBD" rather than invented, every phase carrying
`**Status:** Not started` directly under its `### Phase` heading,
before its Goal, the §8 summary table carrying a Status column
(each phase's final step flips both and appends ✅ to the heading),
and every phase carrying its Phase roadmap settings table directly
after its metadata badge.

When the file is written, reply with its path and the phase list with
one line each, naming the model and effort that will write each
phase's roadmap. Do not start Phase 1 — each phase gets its own phase
roadmap in a separate conversation (see
`planning/prompts/phase-roadmap.md`).
