<!--
=============================================================
PHASE ROADMAP TEMPLATE
=============================================================
PURPOSE
  A reusable skeleton for a deep-dive roadmap of ONE phase
  (or sub-phase) of a larger project. Use this when a phase
  in the parent project roadmap is large enough that it needs
  its own dedicated planning document — typically because it
  spans multiple steps, each of which is itself a discrete
  Cursor / Claude Code session with its own model selection,
  context bundle, and acceptance criteria.

WHEN TO USE
  - The parent ROADMAP.md treats this phase as a single
    section; this file expands that section into an
    executable plan that can be handed to a coding agent
    one step at a time.
  - Numbering convention: `phaseNN-roadmap.md` where NN is
    the phase number (e.g. `phase31-roadmap.md` for
    Phase 31, `phase04-roadmap.md` for Phase 4).
  - Location: `docs/roadmap/`, beside the project's
    `ROADMAP.md` — every roadmap in one folder. A project
    that keeps its roadmaps git-excluded (e.g. `private/`)
    keeps them there. Relative links resolve from
    `docs/roadmap/` (`../phase{{N}}-qa-findings.md`,
    `../../scripts/…`).

PLACEHOLDER SYNTAX
  - Prose placeholders use {{double-curly}} form so that
    Markdown renderers never mistake them for HTML tags
    (`<like-this>` gets eaten by the renderer — never use it
    outside fenced code blocks).
  - Inside fenced ```xml <task>``` blocks, normal XML angle
    brackets are fine — the fence protects them.
  - Replace every {{token}} with concrete content before
    shipping. A finished roadmap should contain zero
    {{...}} tokens.

STYLE RULES (the AI MUST follow)
  - All prose wraps at 80 characters per line, and every table fits in
    80 columns: a ladder takes one field a row, and a Summary Table
    Scope is at most 30 characters.
  - Use Markdown tables for any list of >3 structured items.
  - Use ASCII boxes / arrows (┌ ┐ └ ┘ │ ─ ▶ ↓) for the
    execution-order diagram.
  - Use fenced code blocks for SQL, schemas, configs, shell,
    and for the XML <task> prompts handed to coding agents.
  - Numbered steps (## Step N — Title). Each step is a
    self-contained Cursor / Claude Code session.
  - Every step carries, in this order: a Status line
    DIRECTLY under its `## Step N — Title` heading, before
    anything else (`**Status:**` — `Not started` when this
    roadmap is written; the step's OWN PR flips it to
    `Complete — PR #n (YYYY-MM-DD)` at Stage 3 and appends
    ` ✅` to the heading, so the roadmap on `main` marks a step
    complete exactly when its PR merges and the completion
    shows in the rendered preview, the outline, and the table
    of contents; see the Overview "Status rule"), Goal
    blockquote, Branch line
    (`feature/phaseNN-stepM-<slug>` — see the Overview
    "Branch strategy", "Branch-first execution rule",
    "Worktree rule", and "Step lifecycle" paragraphs; the
    operator runs `git checkout -b <branch>` BEFORE reading
    files or editing anything in the step, follows the
    six-stage lifecycle for the rest of the step, and starts
    the next step in a fresh conversation), Deploys line
    (`**Deploys:**` — the surface and environment the step's
    merge reaches, or `nothing beyond merge`; see the Overview
    "Deploy-and-verify rule"), Settings
    table, Model rationale paragraph, XML <task> prompt (which
    MUST carry a <security> block alongside its <lifecycle>
    block — see below), and an Acceptance Criteria bullet list
    that carries a "Deployed & verified" bullet whenever the
    Deploys line names a surface
    and whose FINAL bullet is always a security check. The
    Settings table is
    PLATFORM-specific so it mirrors the actual surface the
    operator will see. THE GOVERNING RULE: every table
    carries Model / Platform / Conversation, PLUS ONLY the
    dials the chosen surface actually exposes. A dial the
    surface lacks is OMITTED — never written as "N/A",
    "Off", or "--". Every row must be a control the
    operator can literally set in that panel:
      • Claude Code: Model / Platform / Effort / Thinking
        (On/Off) / Conversation. Effort values are Low /
        Medium / High / Extra High / Max; Ultracode is its
        own switch beside the effort slider (Claude Code
        2.1.284+), written in the Effort cell as
        `<level> + Ultracode` (e.g. `Extra High + Ultracode`),
        never as a separate orchestration row. Thinking is a
        two-position toggle — On or Off — and NEVER
        carries an effort word; a model that always thinks
        (Opus 5.5, Sonnet 5.5, Haiku 5.5 and the Fable models) has no
        Thinking toggle, so its Thinking cell is `—`. NO
        Max Mode row: Claude Code has no such dial.
      • Codex (single Platform covering both the CLI binary
        and the Cursor IDE extension — operator picks the
        surface): Model / Platform / Intelligence /
        Conversation. Intelligence is Codex's own label for
        the reasoning-effort dial; values are Low / Medium
        / High / Extra High. NO Max Mode row and no
        separate Thinking row — Intelligence is the only
        dial that panel exposes.
      • Other reasoning-dial surfaces (ChatGPT app,
        claude.ai web, Anthropic API, OpenAI API, Google
        API, Gemini CLI, DeepSeek API, …): Model /
        Platform / Effort / Thinking (On/Off) /
        Conversation, same shape as Claude Code. These
        surfaces expose a reasoning-effort parameter and
        NO Max Mode — never give them a Max Mode row.
      • Cursor: Model / Platform / Max Mode (ON/OFF) /
        Conversation. Max Mode is a CURSOR-ONLY dial,
        exposed in both of Cursor's UI modes (Composer and
        Chat). Cursor exposes no reasoning dial at all, so
        the table has NO Effort row and NO Thinking row —
        Max Mode is the operator's real control here.
    Every Settings table MUST include Platform (the access
    method picked by `<access-selection>` in
    docs/model-selector.txt against docs/user-context.md);
    the rationale paragraph MUST name the subscription or
    API key that pays for the chosen Platform AND justify
    each EMITTED dial value using the surface's native
    vocabulary (Effort vs Intelligence vs Max Mode; On/Off
    for the thinking toggle vs Low/Medium/High/Extra
    High/Max/Ultracode for the effort level). Never justify
    a dial the table does not carry — no effort level for
    Cursor, no Max Mode for Claude Code or Codex.
  - The document opens with a phase-level Status line
    directly under its `# Phase N Roadmap` title (`Not
    started` → `In progress` from Step 1's PR → `Complete —
    <YYYY-MM-DD>` and a ` ✅` on the title from the final
    step's PR), and its Summary Table carries a Status column
    mirroring each step's Status line. Same Status rule, same
    Stage-3 commits.
  - Findings surfaced while executing a step are classified
    per the Overview "Triage rule" before they are acted on;
    a step's PR contains the step plus blocking fixes only.
  - A phase that adds or changes a runtime surface (service,
    scheduled job, deployed app) carries an "Operations &
    observability surface" in Current State and an operations
    bullet in the final QA step's acceptance criteria (health
    signal + alarm exist and have been seen to fire).
  - Clean stopping point (the AI MUST honor this). When a step's
    work is done and EVERY acceptance criterion is affirmatively
    met, the AI's final response MUST end with an explicit,
    unhedged completion line of the verbatim shape "Step N is
    complete. You can now move on to Step N+1." That line is the
    LAST line of the response. Nothing follows it — no
    "Follow-ups", "Notes", "Next", "worth a glance", or any
    other trailer. Every finding surfaced during the step is
    disposed of BEFORE the line, per the Overview "Triage rule":
    a note for a later step is edited into that step's `<task>`
    block, not narrated; a judgement call on the diff goes in the
    PR body, not the chat; a bug is fixed or is an issue number.
    A finding that has not reached its destination is an unmet
    criterion — the AI says plainly the step is NOT complete,
    names what is outstanding, and omits the completion line.
    "Done" means done. This is Stage 6 of the Step lifecycle and
    is binding; see the Overview "Step lifecycle" paragraph and
    each step's XML `<lifecycle>` block. The completion line also
    presupposes the Status rule: the merged PR carried this
    step's `**Status:** Complete — PR #n (…)` line, so the
    roadmap on `main` already records what the chat declares.
    The same rule applies to
    the phase-level line "Phase N is complete. You can now move
    on to Phase N+1." emitted by the final QA step, which marks
    the phase in the parent project roadmap the same way.
  - End the document with a Post-Implementation Verification
    section (V1-Vn check tables), a Summary Table, optional
    Model-selection blocks, and a Not-in-scope section.
  - Prefer concrete, declarative sentences. No hedging.
  - Mark every unknown as "TBD".
  - Output the finished document in raw Markdown only.
  - Strip every <!-- ... --> instruction block before
    delivery, EXCEPT the inline guidance comments inside
    each section header that help the next author fill it
    in. (Those are explicitly marked "KEEP" below.)
=============================================================
-->

# Phase {{N}} Roadmap — {{Phase Title}}

**Status:** Not started

## Overview

<!--
KEEP NONE OF THESE COMMENTS IN THE FINAL DOC.

The Overview is 3-6 paragraphs of declarative prose that
answers:
  1. What gate does this phase open? (What comes next is
     blocked on this phase shipping.)
  2. What does this phase NOT do? (Two or three negatives,
     to set expectations.)
  3. The phase "lands in N layers" enumeration — one
     paragraph that names every step in order with the
     concrete deliverable each one ships.
  4. The "ship test" paragraph — one paragraph that
     summarizes the testable conditions for phase exit.
  5. Pre-requisite paragraph — which prior phases must be
     closed, with one-sentence rationale per dependency.
  6. Dependency paragraph — which downstream phases consume
     this phase's deliverables, with one-sentence rationale.
  7. Optional "Design rationale" paragraph if this phase
     embodies a non-obvious design choice that reviewers
     will question.
-->

{{Opening paragraph: 2-4 sentences framing what gate this
phase opens, what it explicitly does NOT do, and why the
work is bundled into one phase rather than spread across
several. Reference the prior phase(s) by number where
useful.}}

The phase lands in {{N}} layers:

1. **{{Step 1 short label}}** — {{multi-sentence
   description of the concrete deliverable Step 1 ships.
   Name files, callables, schema fields, UX surfaces.}}
2. **{{Step 2 short label}}** — {{description}}.
3. **{{Step 3 short label}}** — {{description}}.
4. **{{Step N-1 short label}}** — {{description}}.
5. **QA + `verify-phase{{N}}.sh`** — verification script
   (`--fast`, `--swift`, `--node`, `--ui`, `--all`,
   `--post`), `docs/phase{{N}}-qa-findings.md` rollup, and
   `phase-verify.yml` matrix entry that binds the phase to
   CI.

The ship test for Phase {{N}} is straightforward:
{{one long sentence that lists every testable exit
condition, separated by semicolons — e.g. "deliverable X
ships; Jest test Y passes; doc Z carries the verbatim
spec text; and `scripts/verify-phase{{N}}.sh --fast`
exits 0 on Ubuntu CI with the `phase-verify.yml` matrix
entry green"}}.

**Pre-requisite:** {{Phase X closed (one-sentence
rationale). Phase Y closed (one-sentence rationale). Phase
Z closed (one-sentence rationale).}}

**Dependency:** {{Phase N+1 does not start until Phase N's
V-checks are green; one-sentence rationale for what
downstream consumers inherit.}}

**Design rationale ({{short label}}).** {{Optional. Include
only if this phase embodies a non-obvious design choice —
a build-vs-buy call, a synthetic-vs-real trade-off, an
ephemeral-vs-persistent pattern, etc. One or two
paragraphs. Drop the whole subsection if the design is
self-evident from the Overview.}}

**Branch strategy.** Every step in this phase lands on its own
short-lived feature branch
(`feature/phase{{N}}-step{{M}}-<slug>`), opens a pull request
against `main`, waits for the project's CI workflow to go green,
and squash-merges with a Conventional Commits subject line.
Direct pushes to `main` are blocked by branch protection. See
the parent project's ROADMAP "Branch management strategy"
section for the canonical naming convention, PR rules, and
release tagging — this paragraph confirms those rules apply
unchanged within this phase. Per-step branches are listed on
each step header below as `**Branch:**` so reviewers can map
commits 1:1 to the step they implement.

**Branch-first execution rule.** The very first action of every
step — before reading any files, before running any tool, before
drafting any change — is to check out the branch named in that
step's `**Branch:**` line:

```sh
git checkout -b feature/phase{{N}}-step{{M}}-<slug>
```

This is non-negotiable. `main` is protected with
`enforce_admins: true`, so a commit on `main` cannot be pushed and
must be rewound or rebased onto the feature branch before the PR
can open — an avoidable round-trip. If you discover mid-step that
you started on `main`, recover by running the same
`git checkout -b` command immediately (uncommitted changes carry
over to the new branch), then continue. AI coding agents executing
a step from this roadmap must treat the branch checkout as Step 0
of every step.

**Worktree rule.** One working tree, one step in flight — the
lifecycle below assumes the primary checkout. A second working
tree is created only with `git worktree add`, and only for the
three cases the parent ROADMAP "Worktree strategy" sanctions: a
`hotfix/` branch interrupting this step (cut from `origin/main` in
its own worktree so this step's tree is untouched); steps the
Execution Order below explicitly draws in parallel (each in its
own worktree AND its own conversation); and worktree-isolated
subagents inside a step (throwaway trees that merge back into the
step branch locally and are removed before the PR opens). In those
cases Stage 1 becomes `git fetch origin && git worktree add -b
feature/phase{{N}}-step{{M}}-<slug> <worktree-path> origin/main`,
the worktree is bootstrapped before any test or build (fresh
dependency install and env files — a worktree has none of the
primary tree's untracked state, and it must never borrow the
primary tree's editable install), the Stage 4 merge runs from the
primary tree, and Stage 5 removes the worktree BEFORE pruning the
branch. Undeclared parallelism is a lifecycle violation, not a
shortcut. Worktree location for this project: {{sibling directory
`../<repo>--<slug>` or git-ignored `.worktrees/<slug>/` — one
convention per project, matching the parent ROADMAP}}.

**Security-first execution rule.** Security is not a phase — it is
a gate on every commit of every step. Before each `git commit`,
the step's work must pass the local, fail-closed security gate:
secret/PII scan clean, SAST clean, dependency audit clean, and a
diff review confirming no sensitive data (PII, credentials,
tokens) and no new insecure pattern (injection, weak crypto,
over-broad scope, secret in a client bundle or log line). This
gate is wired into the pre-commit hook and re-run in CI, so a
security issue introduced while implementing a step is caught
during development — before it reaches the branch, the PR, or
`main`. See the parent project's ROADMAP "Security & privacy
strategy" → "Per-step security gate" for the canonical checks and
tooling; each step's XML `<task>` carries a `<security>` block
restating them for the agent, and each step's Acceptance Criteria
ends with a security check. AI coding agents executing a step MUST
treat the security gate as part of the step's definition of done,
exactly like its tests. This matters most on projects handling
client PII or secrets: the operator running a step's prompt must
not be able to introduce a data-exposure risk that only surfaces
after merge.

**Deploy-and-verify rule.** Merged is not deployed, and deployed
is not released. Every step header carries a `**Deploys:**` line
naming the surface and environment the step's merge reaches — or
`nothing beyond merge` — and when going live needs a release, a
version-floor bump, a migration, or a redeploy, the line says so
and this step (or a named follow-on step) owns that event. For a
step whose Deploys line names a surface, Stage 4 of the lifecycle
does not end at the squash-merge: the step's acceptance criteria
carry a **Deployed & verified** bullet (the surface's
version/health endpoint reports this build, and the changed
behaviour is exercised in the target environment with real
authentication via the hands-off recipe the step names), and that
bullet must be green before the step is declared complete. A step
that introduces a required environment variable or shared secret
verifies at kickoff that it exists in every target environment and
proves shared values by an authenticated round-trip — never by
listing env names. See the parent ROADMAP "Release & deployment
strategy" for the surfaces table, promotion path, staged-rollout
rule, migrations, and rollback.

**Triage rule.** Findings surfaced while executing a step are
classified before they are acted on, per the parent ROADMAP
"Defect handling & triage": spec rot → edit this roadmap's
affected `<task>` block now; upstream gap → patch the earlier
step's prompt and add it to the carry-over checklist;
implementation bug → fix in-step only if it blocks this step's
acceptance criteria, otherwise an issue and its own branch in a
fresh conversation; architectural question → an issue for a future
phase; process improvement → recorded where the next conversation
will read it; security finding → jumps the queue by severity. A
step's PR contains the step plus blocking fixes only, and lists the
issues it opened. When a merged PR auto-closes an issue, the
environment check is what earns the close — reopen or follow up if
a gap remains. `docs/phase{{N}}-qa-findings.md` is the rollup:
every finding, its class, and the guard added so the class cannot
recur.

**Status rule.** Every step carries a `**Status:**` line directly
under its `## Step N — …` heading, before the Goal, and this file
on `main` is the ledger of what is done — never a chat
transcript, never a later conversation reconstructing history
from `git log`. The line reads `Not started` when this roadmap is
written and is flipped by the step's OWN pull request: at Stage 3,
right after `gh pr create` returns the PR number, the agent sets
it to `Complete — PR #<n> (<YYYY-MM-DD>)`, appends ` ✅` to the
step's heading (`## Step 3 — {{Step Title}} ✅`) so the completion
shows in the rendered preview, the outline, and the table of
contents, sets the step's Summary Table Status cell to `Complete
— PR #<n>`, commits that edit on the step branch, and pushes. The
PR therefore carries its own completion mark, and the roadmap on
`main` says a step is complete exactly when that step's PR merges
— never before. This file's phase-level `**Status:**` line (under
the title) and the parent project roadmap are marked the same
way, in the same commit: Step 1's PR flips both from `Not
started` to `In progress` (the parent's `### Phase {{N}}` line
reads `In progress — phase{{N}}-roadmap.md`), and the final
step's PR flips both to `Complete — …` (the parent's with its row
in the "Phase Complexity Summary" table and the header
`> **Status:**` line) and appends ` ✅` to this file's `# ` title
and to the parent's `### Phase {{N}}` heading, so the project
roadmap shows a finished phase the way this file shows a finished
step. There is no separate
"update the roadmaps" chore: a step whose PR merged without its
Status line is a lifecycle violation, and the next step's Stage 1
(and `/roadmap-step`) refuses to start until the previous step
reads `Complete`. If a post-merge check fails — a Deployed &
verified bullet, an alarm that never fired — the step is NOT
complete despite the merged line; say so, and the `hotfix/` PR
that completes it appends its own number to the line. If this
roadmap is git-excluded (e.g. `private/`), the edit itself is the
mark and there is nothing to commit. `grep -n '^\*\*Status:\*\*'`
on this file is the phase's progress report, and the ✅ headings
are the same report at a glance.

**Step lifecycle.** Every step in this phase follows the exact
same six-stage lifecycle, in order, with no exceptions. Each
stage is a hard checkpoint — if a stage is skipped, branch
protection or the next step's Stage 1 will fail loudly, and that
is the safety net. AI coding agents MUST execute all six stages
before declaring a step complete.

1. **Create the branch.** Before any Read / Edit / Bash, run
   `git checkout -b feature/phase{{N}}-step{{M}}-<slug>` from a
   clean, up-to-date `main`. The exact branch name comes from
   this step's `**Branch:**` line. When the Worktree rule
   applies, the equivalent is `git fetch origin && git worktree
   add -b <branch> <worktree-path> origin/main`, followed by
   the worktree's bootstrap.

2. **Work on the branch, passing the security gate before every
   commit.** All commits land here. Never push to `main` directly
   — branch protection (`enforce_admins: true`) rejects it. Before
   each `git commit`, run the local security gate (secret/PII
   scan, SAST, dependency audit, sensitive-data diff review — see
   the step's `<security>` block and the parent ROADMAP "Per-step
   security gate"). It is fail-closed: a finding blocks the commit,
   so a security issue in this step's work is caught here, before
   the PR and before `main`.

3. **Open the PR, then mark the step.** `gh pr create --base
   main --head <branch>` with a Conventional Commits title and a
   body that references this roadmap step and its acceptance
   criteria. One PR per step; never bundle two steps into one
   PR. Then, with the PR number in hand, set this step's
   `**Status:**` line (directly under its heading) to
   `Complete — PR #<n> (<YYYY-MM-DD>)`, append ` ✅` to the step's
   `## Step` heading, set its Summary Table Status cell to
   `Complete — PR #<n>`, commit that edit on the step branch
   (`docs: mark Phase {{N}} Step {{M}} complete`), and push — the
   PR now carries its own completion mark, so the roadmap on
   `main` will say the step is complete exactly when the PR
   merges (Status rule). On the phase's first step, the same
   commit sets this roadmap's phase-level `**Status:**` (under its
   title) and the parent project roadmap's Phase {{N}}
   `**Status:**` to `In progress`; on the final step, both to
   `Complete`, with ` ✅` appended to this roadmap's `# ` title
   and to the parent's `### Phase {{N}}` heading.

4. **Wait for green checks, then squash-merge.** Every required
   status check (lint, type-check, test-matrix, package-smoke,
   security-scan, the aggregate `test` gate, and the
   `phase-verify.yml` matrix entry for this phase) must report
   success. If the PR goes BEHIND main while waiting, refresh
   with `gh pr update-branch --rebase` — never merge `main` into
   the branch; `required_linear_history: true` enforces rebase.
   Once every check is green:

   ```sh
   gh pr merge <PR_NUMBER> --squash --delete-branch
   ```

   If this step's `**Deploys:**` line names a surface, the merge
   is not the finish line: run the Deployed & verified check from
   the acceptance criteria against the target environment now
   (see the Deploy-and-verify rule) before declaring the step
   complete.

5. **Retire the branch (remote + local).** The
   `--delete-branch` flag plus the repo's
   `delete_branch_on_merge: true` setting retire the remote
   automatically. Sync local state and prune the merged branch
   plus any other `[gone]` labels left over from prior PRs:

   ```sh
   git switch main
   git pull --ff-only origin main
   git fetch --prune origin
   git branch -vv | grep ': gone]' | awk '{print $1}' \
     | xargs -r git branch -D
   ```

   If this step ran in its own worktree, remove it FIRST —
   `git worktree remove <worktree-path>`, then `git worktree
   prune` — because `git branch -D` refuses a branch still
   checked out in a worktree. Confirm with `git branch -vv` that
   only `main` and any intentional long-lived branches remain
   locally, and with `git worktree list` that only the primary
   tree remains.

6. **Dispose of every finding, declare completion, then new
   conversation.** Before you declare anything, walk the findings
   this step surfaced and send each to its destination per the
   Triage rule below — a note that a later step needs is edited
   into that step's `<task>` block now; a wrong claim in this
   step's spec is fixed in this roadmap now; an implementation
   bug is fixed in-step or exists as an issue with a number; a
   judgement call you made in the diff is explained in the PR
   body; a process lesson is written where the next conversation
   reads it. A finding you can only *describe* has not been
   disposed of, and an undisposed finding is an unmet acceptance
   criterion. Only once the PR is merged — and `main` therefore
   carries this step's `Complete` Status line — every acceptance
   criterion is affirmatively met, and every finding has a
   destination, say so plainly: end your final response with an
   explicit, unhedged completion line — verbatim shape
   "Step {{M}} is complete. You can now move on to Step {{M+1}}."
   — so the operator has a clean stopping point at which to close
   this conversation. That line is the LAST line of the response.
   Nothing follows it: no "Follow-ups (non-blocking)", no "Notes",
   no "Next", no "worth a glance", no suggested improvements. If
   you want to show your work, a short ledger may PRECEDE the
   line, one entry per finding naming its destination (an issue
   number, a file you edited, the PR body) — never an open item.
   If any acceptance criterion is NOT met, or any finding has no
   destination yet, do the opposite — state plainly that the step
   is NOT complete, name what is outstanding, and do not emit the
   completion line. "Done" means done, not "done, but here is
   what you still have to do". Then, for phase-boundary hygiene,
   the operator closes this Claude Code / Cursor / Codex session
   and opens a fresh one before starting Step {{M+1}}; the new
   conversation begins again at Stage 1 of this lifecycle, with
   the next step's `**Branch:**` line driving the
   `git checkout -b` command. No work straddles two steps.

---

## Current State (as of Phase {{N-1}})

<!--
KEEP NONE OF THESE COMMENTS IN THE FINAL DOC.

Break the Current State into named "surfaces" — one
sub-section per area of the codebase / product the phase
will touch. Typical surface names:
  - Server / Cloud Functions surface
  - iOS app surface
  - Schema / data model surface
  - Operations & observability surface
  - Payment / entitlement surface
  - Security & sensitive-data surface
  - Verification surfaces

Include a "Security & sensitive-data surface" whenever the
phase touches auth, secrets, PII, payments, or any external
input. It states what sensitive data the phase's steps will
handle, what the current controls are (secret manager, authz
checks, input validation, the pre-commit security gate + CI
security checks), and what pattern each step must mirror so it
does not regress them. This is what lets each step's
`<security>` block name a concrete, project-specific check
instead of a generic one.

Include an "Operations & observability surface" whenever the
phase adds or changes a runtime surface (a service, a scheduled
job, a deployed app, a metered dependency). It states what
health signal and alarm exist today, where the cost ledger and
cap live, how the surface is deployed and rolled back, and what
the new surface must expose before it counts as live. This is
what lets each step's `**Deploys:**` line and the final QA
step's operations bullet name a concrete check.
  - Documentation surface

Each surface answers: what exists today, what is missing,
what file paths the next step will edit, what pattern the
next step should mirror.

The final surface is ALWAYS "Verification surfaces" — it
notes which prior verify-phaseNN.sh templates are the
closest precedent and which entries are already in the
.github/workflows/phase-verify.yml matrix.
-->

### {{Surface 1 — e.g. Matchmaking surface}}

- {{Multi-sentence bullet describing one concrete piece of
  current state. Name file paths. Reference the prior
  phase that established the pattern. State what is
  present today and what is missing. Each surface
  typically has 2-5 such bullets, NOT a "what exists /
  what is missing" two-bullet split.}}
- {{Multi-sentence bullet ...}}
- {{Multi-sentence bullet ...}}

### {{Surface 2 — e.g. iOS app surface}}

- {{Multi-sentence bullet ...}}
- {{Multi-sentence bullet ...}}

### {{Surface N}}

- {{Multi-sentence bullet ...}}

### Verification surfaces

- `scripts/verify-phase{A..N-1}.sh` exist;
  `verify-phase{{N-1}}.sh` is the most recent template
  (Phase {{N-1}} follows the canonical `--fast` / `--swift`
  / `--node` / `--ui` / `--all` / `--post` mode contract).
- `.github/workflows/phase-verify.yml` matrix includes
  {{list of prior phases}}. Phase {{N}} adds {{N}}.

---

## Execution Order

<!--
KEEP NONE OF THESE COMMENTS IN THE FINAL DOC.

ASCII flow diagram showing the sequential dependency between
steps. Use box characters consistently. After the steps,
include a "post-implementation" section listing the
V-checks at a glance. Below the diagram, a short prose
paragraph explains WHY the steps are sequential (which
step depends on which prior step's output). Steps that may
run concurrently are drawn side by side with ┌─ branches;
they are the ONLY steps the Worktree rule allows in flight
at once. If there are none, the prose says so.
-->

```
Step 1  ({{short label}})                 {{one-line deliverable
                                          summary}}
                                          → implement
  ↓
Step 2  ({{short label}})                 {{one-line deliverable
                                          summary}}
                                          → implement
  ↓
Step 3  ({{short label}})                 {{one-line deliverable
                                          summary}}
                                          → implement
  ↓
...
  ↓
Step N  (QA + verify-phase{{N}}.sh)       scripts/verify-phase{{N}}.sh
                                          + docs/phase{{N}}-qa-findings.md
                                          + phase-verify.yml matrix entry
                                          → create

--- post-implementation ---

V1  {{one-line restatement of Step 1
    acceptance criteria.}}
V2  {{one-line restatement of Step 2
    acceptance criteria.}}
...
Vn  {{one-line restatement of Step N
    acceptance criteria.}}
```

Steps are sequential by dependency: one paragraph explaining
which step's output the next step consumes (e.g. "Step 2's
escalation ladder must exist before Step 3's bot spawn
callable can target the bot-fill leaf; Step 4 is ordered
after Step 3 to keep the schema migrations clean; Step N is
sequential after every prior step."). Name any steps drawn in
parallel — they are the only concurrency the Worktree rule
permits — or state that this phase has none.

---

<!--
KEEP NONE OF THESE COMMENTS IN THE FINAL DOC.

SUB-PHASE LABEL CONVENTION
When a phase has multiple distinct work streams (e.g.
"the matchmaking ladder + the bot spawn + the async cap"
all in one phase), label each work stream with a letter:
30A, 30B, 30C, 31A, 31B, etc. Step titles then carry both
the sub-phase label and the descriptive title:

  ## Step 1 — 30A Product Decision Document
  ## Step 2 — 30A Matchmaker Escalation Ladder
  ## Step 3 — 30A Ephemeral Bot Spawn + Teardown
  ## Step 4 — 30C Async Game Concurrency Cap
  ## Step 5 — 30B Trial Harness + Observability
  ...

For single-work-stream phases, the sub-phase label is
optional — `## Step 1 — Database Schema Migration` is
fine. Use sub-phase labels when they help reviewers see
which steps share an owner / surface / acceptance gate.

TERMINAL VERBS
Every step in the Execution Order diagram ends its
right-column deliverable summary with one of three
arrows:
  → implement  AI-driven coding step.
  → operate    Operator wall-clock work (e.g. running a
               7-day trial, doing cross-browser QA).
  → create     QA scaffolding step (the verify script,
               findings doc, CI matrix update).
-->

## Step 1 — {{Step Title}}

**Status:** Not started

> **Goal:** {{One dense paragraph (4-8 sentences) describing
> the concrete deliverable of this step. Reference every
> file path that gets added or edited (use backticks).
> Reference any verification hook (Jest test, XCTest, doc
> test) the step ships alongside. Often frames as: "Land
> the X chassis: a new Y callable that does Z; the iOS-
> side W view that consumes Y; the verification Jest /
> XCTest covering both. This step lands the foundation;
> Steps N-M layer A / B / C on top of the chassis Step 1
> builds." Use semicolons to chain deliverables in one long
> sentence rather than splitting into multiple short
> sentences.}}

**Branch:** `feature/phase{{N}}-step1-{{slug}}`

**Deploys:** {{surface → environment this step's merge reaches,
e.g. "web app → production (auto-deploy on merge)" — or "nothing
beyond merge". If going live needs a release, a version-floor
bump, a migration, or a redeploy, say so here and name the step
that owns it.}}

<!-- Typical model values: GPT-5.3 Codex (long-running
     autonomous agentic sessions), GPT-5.4 (knowledge
     work / writing / domain expertise), Sonnet 4.6
     (correctness-sensitive cross-cutting implementation),
     Composer 2 (multi-file mechanical editing, roadmap
     execution), Gemini 3.1 Pro (multimodal visual
     analysis). Settings table values match the model-
     selector's roadmap-annotation format.

     PLATFORM is the access method picked by
     `<access-selection>` in docs/model-selector.txt against
     the user-specific state in docs/user-context.md.
     Typical values: Claude Code (Claude models when
     claude.ai Max is active), Cursor (single Platform
     covering Cursor's Composer mode for routine multi-file
     editing AND Chat mode for frontier-model picks against
     the Cursor pool; operator picks the mode at task time
     based on the chosen Model), Codex (GPT/Codex models on
     a ChatGPT subscription; single Platform covering both
     the CLI binary and the Cursor IDE extension — operator
     picks the surface), Anthropic API / OpenAI API /
     Google API (pay-per-token fallback when no subscription
     path applies). The
     Settings table MUST name PLATFORM so reviewers can see
     which subscription pays for the step — a step's
     "Sonnet 4.6 via Claude Code" reads very differently
     from "Sonnet 4.6 via Anthropic API" on the cost line.

     THE LADDER — the default wherever roadmodel is
     installed. A step's Settings table carries the full
     recommendation /recommend shows: Cost, Balanced and
     Quality, each ranked three deep — the Pick, the
     Runner-up (the column's next choice, never the Pick's
     series) and a Backup from another maker — each option
     with its own model, platform and effort. The roadmap then
     outlives a usage pool's state: when a pool reads
     `tight` or `exhausted`, the step's runner picks
     another column (the **Runs:** line's rule) instead of
     the roadmap being refreshed. Paste the ladder and its
     **Runs:** line exactly as `roadmodel ladder --category
     <c> --complexity <x> [--novel]` prints them for the
     step's classification (MCP tool: `roadmap_settings`).
     Layout (roadmodel 0.2.95 on): one table whose columns
     are Cost, Balanced and Quality. Each rank — **Pick**, **Runner‑up**,
     **Backup** — names the first of its rows from a column of
     its own (blank below it, no `&nbsp;`), beside
     field rows: Model (bold); Platform; Level, the bare
     level the platform's own dial sets (`High` is
     Intelligence High on Codex and Effort High on Claude
     Code and Antigravity; `—` where the surface has no
     dial); AA, the model's Artificial Analysis Intelligence
     Index at that level (`not measured` where AA has no row
     for it there); and Price, its blended list price per 1M
     tokens (3 in : 1 out) times the tokens it uses at that
     level (`*` where that use is not yet measured). There is
     no Thinking row: Thinking is always On wherever the
     platform has the toggle, and every AA Index and Price
     already assumes it. A note line under the table explains
     Price, and a `**Conversation:**` line closes the
     ladder. Each rank comes from its own maker (roadmodel
     0.2.97 on), because a tight usage pool is a maker's: the
     Runner-up is the column's recommendation with the Pick's
     maker left out, and the Backup leaves out both makers
     above it. Where the user-context funds too few makers, a
     missing rank is the Pick's own model one level lower,
     its Level marked ↓ (it uses less of a tight pool), and
     `none` below the dial's lowest level. The note line
     names the classification the ladder was ranked for. The
     ranks follow the column's own rule, not the AA Index:
     Cost ranks each maker's cheapest adequate option, so its
     AA Index may rise down the column. Every model is the latest
     version of its series, never an older one (GPT-6 Sol
     where GPT-6.1 Sol runs, Opus 5 where Opus 5.5 does).
     Set the Conversation line to **Continue** only when the
     step continues the previous one's session.
     The single-column shapes below are the fallback where
     roadmodel cannot be reached.

     SETTINGS TABLE SHAPE IS PLATFORM-SPECIFIC. Each
     surface exposes a different tuning UI, and the table
     MUST mirror what the operator will actually see in
     that surface so reviewers can audit the choice
     1:1 against the panel. Every table carries Model /
     Backup / Platform / Conversation plus ONLY the dials
     that surface has; a dial the surface lacks gets NO ROW at
     all — do not write "N/A", "Off", or "--" for a
     control that does not exist. There are exactly THREE
     shapes — one per dial set a surface can expose, and
     they line up 1:1 with the three branches of
     `roadmodel.recommend._structured_settings`:

     BACKUP row (every variant): the selector's BACKUP —
     the model to run when the primary is unavailable, from
     a different provider family — written as ONE cell
     carrying its own platform and dial in that surface's
     vocabulary, because the backup usually runs somewhere
     else: `GPT-5.6 Terra — Codex · Intelligence Medium`,
     `Claude Opus 5.5 — Claude Code · Effort Medium`. When
     the selector returns no backup, write `None`.

     EFFORT + THINKING variant (use when PLATFORM is
     "Claude Code" or any other surface exposing a
     reasoning-effort dial that is NOT Codex — ChatGPT app,
     claude.ai web, Anthropic API, Google API, Gemini CLI,
     DeepSeek API, etc.). The Settings panel exposes Model,
     Effort, and a Thinking on/off toggle — there is NO Max
     Mode dial and NO Intelligence dial on these surfaces.
     Table rows: Model / Backup / Platform / Effort /
     Thinking / Conversation.
     EFFORT values: Low / Medium / High / Extra High /
     Max — plus Ultracode, which is CLAUDE CODE ONLY:
     `xhigh` with ultracode's dynamic workflows on, reached
     by launching `claude --effort ultracode` or by running
     `/effort xhigh` then `/effort ultracode` (since Claude
     Code 2.1.284 Ultracode is its own switch that keeps
     the current level), so no other surface has it. The
     Effort cell reads `Extra High + Ultracode`. Map from
     overall complexity per
     `<thinking-context>`: Low → Low, Medium → Medium,
     High → High, High with novel problem-solving or
     cross-file multi-step proof → Extra High,
     ceiling-class tasks demanding the highest available
     reasoning budget → Max, and Ultracode for a
     session-wide ceiling run (Ultracode is the TOP RUNG
     OF EFFORT, never a separate Orchestration row); bump
     up one level for planning / knowledge prompts with
     cross-cutting scope. THINKING is a TOGGLE with
     exactly two values: On / Off. It never carries an
     effort word or a number — the level lives in Effort.
     Default On for any step where extended reasoning is
     desirable; Off only when the step is purely
     mechanical and latency matters. A model that always
     thinks (Opus 5.5, Sonnet 5.5, Haiku 5.5 and the Fable models) has
     no toggle on any surface: its Thinking cell is `—`,
     and a mechanical step lowers Effort instead.

     INTELLIGENCE variant (use for Codex and the OpenAI
     API). Codex is a single Platform covering both the CLI
     binary and the Cursor IDE extension; the operator
     picks the surface at task time. It labels its
     reasoning dial "Intelligence" and exposes no separate
     thinking toggle, and it has no Max Mode dial. Table
     rows: Model / Backup / Platform / Intelligence /
     Conversation.
     INTELLIGENCE values: Low / Medium / High / Extra High.
     Map from overall complexity per `<thinking-context>`:
     Low → Low, Medium → Medium, High → High, S-tier
     coding / cross-file multi-step proof → Extra High.
     NOTE ON VOCABULARY: "Intelligence" is the label Codex
     shows in its own UI, which is what a roadmap table
     must mirror. The selection BLOCK still carries the
     platform-neutral `EFFORT:` line for this surface —
     same value, different name — because the block is a
     cross-platform contract and the table is a picture of
     one panel.

     CURSOR variant (use when PLATFORM is "Cursor" —
     single Platform covering both Composer mode and Chat
     mode). Table rows: Model / Backup / Platform / Max
     Mode / Conversation. MAX MODE values: ON / OFF. Max Mode is
     a CURSOR-ONLY dial and must not appear on any other
     platform's table. Cursor exposes NO reasoning-level
     control in either UI mode, so this variant has NO
     Effort row and NO Thinking row — the operator's real
     lever on this surface is Max Mode, and inventing a
     thinking level for it would document a setting they
     cannot apply.
     -->

Settings — ladder ({{the default wherever roadmodel is
installed: the table and **Runs:** line `roadmodel ladder
--category <c> --complexity <x> [--novel]` prints for the
step's classification, pasted as printed. The three table
shapes after it are the fallback where roadmodel cannot be
reached}}):

|               |          | Cost                  | Balanced              | Quality               |
| ------------- | -------- | --------------------- | --------------------- | --------------------- |
| **Pick**      | Model    | **{{Model}}**         | **{{Model}}**         | **{{Model}}**         |
|               | Platform | {{Platform}}          | {{Platform}}          | {{Platform}}          |
|               | Level    | {{Level}}             | {{Level}}             | {{Level}}             |
|               | AA       | {{AA Index}}          | {{AA Index}}          | {{AA Index}}          |
|               | Price    | {{$ per 1M}}          | {{$ per 1M}}          | {{$ per 1M}}          |
| **Runner‑up** | Model    | **{{Model}}**         | **{{Model}}**         | **{{Model}}**         |
|               | Platform | {{Platform}}          | {{Platform}}          | {{Platform}}          |
|               | Level    | {{Level}}             | {{Level}}             | {{Level}}             |
|               | AA       | {{AA Index}}          | {{AA Index}}          | {{AA Index}}          |
|               | Price    | {{$ per 1M}}          | {{$ per 1M}}          | {{$ per 1M}}          |
| **Backup**    | Model    | **{{Model or none}}** | **{{Model or none}}** | **{{Model or none}}** |
|               | Platform | {{Platform}}          | {{Platform}}          | {{Platform}}          |
|               | Level    | {{Level}}             | {{Level}}             | {{Level}}             |
|               | AA       | {{AA Index}}          | {{AA Index}}          | {{AA Index}}          |
|               | Price    | {{$ per 1M}}          | {{$ per 1M}}          | {{$ per 1M}}          |

Price: list $ per 1M tokens (3 in : 1 out) × the tokens the model uses at that
level.

**Conversation:** New

**Runs:** {{Cost / Balanced / Quality}} — the user-context's Budget priority is
`{{cheap / balanced / best}}`. If that column's usage pool reads `tight` or
`exhausted`, run the first of its Runner-up and Backup whose pool has headroom;
with neither, a `tight` column runs the Cost column and an `exhausted` one its
Backup.

Settings table — Effort + Thinking variant ({{use this
shape when PLATFORM is "Claude Code" or any other
reasoning-dial surface that is not Codex — ChatGPT app,
claude.ai web, Anthropic API, Google API, Gemini CLI,
DeepSeek API. These panels expose Effort + a Thinking
On/Off toggle, never Max Mode and never Intelligence — so
there is no Max Mode row. `Ultracode` is available only
when Platform is Claude Code}}):

| Setting      | Value                          |
| ------------ | ------------------------------ |
| Model        | {{Model name}}                 |
| Backup       | {{Backup model — its platform · its dial, or None}} |
| Platform     | {{Claude Code or other reasoning-dial access method}} |
| Effort       | {{Low/Medium/High/Extra High/Max — or Extra High + Ultracode, Claude Code only}} |
| Thinking     | {{On or Off — or — for a model that always thinks}} |
| Conversation | **{{New or Continue}}**        |

Settings table — Codex variant ({{use this shape when
PLATFORM is "Codex" — covers both the CLI binary and the
Cursor IDE extension as a single Platform; the Codex panel
exposes Intelligence as its only reasoning dial — there is
NO Max Mode and NO Thinking field, so the table omits both
rows}}):

| Setting      | Value                          |
| ------------ | ------------------------------ |
| Model        | {{Model name}}                 |
| Backup       | {{Backup model — its platform · its dial, or None}} |
| Platform     | Codex                          |
| Intelligence | {{Low/Medium/High/Extra High}} |
| Conversation | **{{New or Continue}}**        |

Settings table — Cursor variant ({{use this shape when
PLATFORM is "Cursor" — the single Platform covering both
Composer mode and Chat mode. Max Mode is a Cursor-native
dial and appears on NO other platform's table; Cursor
exposes no reasoning-level control, so there is no Effort
row and no Thinking row}}):

| Setting      | Value                       |
| ------------ | --------------------------- |
| Model        | {{Model name}}              |
| Backup       | {{Backup model — its platform · its dial, or None}} |
| Platform     | Cursor                      |
| Max Mode     | {{ON or OFF}}               |
| Conversation | **{{New or Continue}}**     |

**Model rationale:** {{3-5 sentences explaining the choice.
Lead with the task characteristics (long-running agentic
session / multi-file editing / multimodal visual analysis /
correctness-sensitive reasoning / mechanical translation)
and map them to the model's documented strengths. Name the
PLATFORM and identify the subscription or API key that pays
for it (claude.ai Max funding Claude Code, Cursor Ultra pool
funding Cursor, ChatGPT Pro funding Codex,
Anthropic API direct as pay-per-token fallback, etc.) —
this is the line that distinguishes "Sonnet 4.6 on a flat
$100/mo Max plan" from "Sonnet 4.6 burning $15/M output
tokens." Note the tuning choices in the language of the
actual surface, and justify ONLY the rows the table
actually carries: for Claude Code and the other
reasoning-dial surfaces, why EFFORT is at the stated level
and why THINKING is on or off; for Codex, why
INTELLIGENCE is at the stated level (the surface exposes
no other dial); for Cursor, why MAX MODE is on or off
(and say nothing about an effort or thinking level —
Cursor has neither). Never justify a dial the surface does
not expose. Close with why the conversation is new or
continued (almost always "New per phase-boundary
hygiene").}}

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase{{N}}-step{{M}}-<slug>`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase {{N}} `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase {{N}}`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step {{M}} is
       complete. You can now move
       on to Step {{M+1}}." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step {{M+1}}.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.
  </security>

  <context>
    {{Project name}}. Phase {{N}}.
    Step 1: {{step title}}.

    Current state (as of Phase
    {{N-1}}, post-Phase-{{N}} Step
    {{prior step if any}}):

    - Bullet describing relevant
      current state. Include file
      paths the agent will need.
    - Bullet ...
    - Bullet ...

    Files to read (every file
    before drafting):
    - {{repo-relative path}}
      ({{one-line reason this file
      matters}}).
    - {{repo-relative path}}
      ({{reason}}).
    - {{repo-relative path}}
      ({{reason}}).
  </context>

  <goal>
    2-6 sentences describing what
    the agent must ship. Be
    concrete: name the files, the
    function signatures, the
    schema fields, the UX
    surfaces. Reference acceptance
    criteria implicitly through
    precise language.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in
      context before making any
      changes.
    </requirement>

    <requirement>
      First concrete requirement.
      Be specific about file
      paths, function names,
      contract shapes. Multi-line
      where needed.
    </requirement>

    <requirement>
      Second requirement.
    </requirement>

    <requirement>
      Add {{test file path}}:
      - test{{scenario 1}}.
      - test{{scenario 2}}.
      - test{{scenario 3}}.
    </requirement>

    <requirement>
      Filepath comment: every new
      Swift / TS / Bash / YAML /
      Markdown file gets the
      repo-relative path as the
      first line where the file
      type accepts comments
      (Swift: `// path`; TS:
      `// path`; Bash: `# path`;
      YAML: `# path`; Markdown:
      check sibling docs/
      conventions and match).
    </requirement>
  </requirements>
</task>
```

### Step 1 acceptance criteria

- Testable statement. Verifiable by an automated test, a
  UI inspection, a SQL query, a CI run, or a doc grep.
- Testable statement.
- Testable statement.
- Testable statement.
- `{{test file}}.swift` / `{{test file}}.test.ts` pass.
- **Deployed & verified** (include only when the `**Deploys:**`
  line names a surface): {{the surface's version/health endpoint
  reports this step's build, and the changed behaviour was
  exercised in the target environment with real authentication
  via the hands-off recipe — name the endpoint, the request, and
  the expected result}}.
- **Security gate clean** (always the final criterion): the
  pre-commit security gate passed on this step's diff — secret/
  PII scan clean, SAST clean, dependency audit clean, and the
  {{surface this step touches}} handles sensitive data per the
  project ROADMAP "Security & privacy strategy" ({{name the
  concrete check — e.g. "no PII in the new log lines", "the new
  endpoint enforces authz", "the added dependency passes
  pip-audit"}}).

---

## Step 2 — {{Step Title}}

**Status:** Not started

> **Goal:** One paragraph.

**Branch:** `feature/phase{{N}}-step2-{{slug}}`

**Deploys:** {{surface → environment, or "nothing beyond merge"}}

{{Settings table — the ladder `roadmodel ladder` prints for
this step's classification (the Step 1 guidance), pasted as
printed with its **Runs:** line. Where roadmodel cannot be
reached, the single-column variant that matches PLATFORM,
carrying ONLY the rows that platform's panel exposes.}}

|               |          | Cost                  | Balanced              | Quality               |
| ------------- | -------- | --------------------- | --------------------- | --------------------- |
| **Pick**      | Model    | **{{Model}}**         | **{{Model}}**         | **{{Model}}**         |
|               | Platform | {{Platform}}          | {{Platform}}          | {{Platform}}          |
|               | Level    | {{Level}}             | {{Level}}             | {{Level}}             |
|               | AA       | {{AA Index}}          | {{AA Index}}          | {{AA Index}}          |
|               | Price    | {{$ per 1M}}          | {{$ per 1M}}          | {{$ per 1M}}          |
| **Runner‑up** | Model    | **{{Model}}**         | **{{Model}}**         | **{{Model}}**         |
|               | Platform | {{Platform}}          | {{Platform}}          | {{Platform}}          |
|               | Level    | {{Level}}             | {{Level}}             | {{Level}}             |
|               | AA       | {{AA Index}}          | {{AA Index}}          | {{AA Index}}          |
|               | Price    | {{$ per 1M}}          | {{$ per 1M}}          | {{$ per 1M}}          |
| **Backup**    | Model    | **{{Model or none}}** | **{{Model or none}}** | **{{Model or none}}** |
|               | Platform | {{Platform}}          | {{Platform}}          | {{Platform}}          |
|               | Level    | {{Level}}             | {{Level}}             | {{Level}}             |
|               | AA       | {{AA Index}}          | {{AA Index}}          | {{AA Index}}          |
|               | Price    | {{$ per 1M}}          | {{$ per 1M}}          | {{$ per 1M}}          |

Price: list $ per 1M tokens (3 in : 1 out) × the tokens the model uses at that
level.

**Conversation:** New

**Runs:** {{the line `roadmodel ladder` prints}}

**Model rationale:** 3-5 sentences. With the ladder: the
classification it was printed for (PRIMARY and SECONDARY
category, complexity, novel or not) and why, then what sets
the three columns apart for this step. Otherwise: name the
PLATFORM and the subscription or API key that pays for it. For Claude
Code and the other reasoning-dial surfaces, state why
EFFORT is at the stated level and why THINKING is on or
off. For Codex, state why INTELLIGENCE is at the stated
level (the surface exposes no other reasoning dial). For
Cursor, state why MAX MODE is on or off — and say nothing
about effort or thinking, because that surface exposes
neither. Justify only the rows the table carries.

{{Every step's `<task>` opens with the SAME `<lifecycle>` and
`<security>` blocks shown in full in Step 1 — copy both
verbatim (updating the branch slug). They are omitted here only
to keep the template short; a finished roadmap MUST include
both in every step so the agent gates security on every
commit.}}

```xml
<task>
  <lifecycle>
    {{Six-stage lifecycle — copy
    verbatim from Step 1.}}
  </lifecycle>

  <security>
    {{Security gate — copy
    verbatim from Step 1. Add any
    check specific to what THIS
    step touches, e.g. "the new
    endpoint enforces authz" or
    "no PII in the new events".}}
  </security>

  <context>
    Always restate the project,
    the phase, the step, and the
    current state — every step is
    a fresh conversation so the
    agent has no prior context.

    Files to read:
    - ...
  </context>

  <goal>
    ...
  </goal>

  <requirements>
    <requirement>
      Read all files listed in
      context before making any
      changes.
    </requirement>

    <requirement>
      ...
    </requirement>

    <requirement>
      Filepath comment: every new
      file gets the repo-relative
      path as the first line.
    </requirement>
  </requirements>
</task>
```

### Step 2 acceptance criteria

- ...
- ...
- **Deployed & verified** (only when the Deploys line names a
  surface): {{endpoint, request, expected result}}.
- **Security gate clean** (always the final criterion): the
  pre-commit security gate passed on this step's diff, with the
  concrete check for the surface this step touches named
  explicitly.

---

<!--
Repeat the Step pattern for Step 3, Step 4, ... as many as
the phase requires. Typical phase has 4-7 steps. The final
step is ALWAYS "QA + verify-phaseN.sh".

EVERY step, without exception, carries: a `**Status:** Not
started` line directly under its heading, a `**Deploys:**` line,
the <lifecycle> and
<security> blocks in its <task> (both copied from Step 1), a
"Deployed & verified" bullet whenever the Deploys line names a
surface, and a final "Security gate clean" acceptance-criterion
bullet. This is how "security at every step", "merged is not
deployed", and "the roadmap on main is the ledger" are enforced
mechanically rather than left to memory.
-->

## Step {{N}} — QA & Verification Script

**Status:** Not started

> **Goal:** Package the verification matrix into
> `scripts/verify-phase{{N}}.sh` (with `--fast`, `--swift`,
> `--node`, `--ui`, `--all`, and `--post` modes), produce
> `docs/phase{{N}}-qa-findings.md`, and add `{{N}}` to the
> `phase-verify.yml` matrix. The script greps for every
> Step 1 through Step {{N-1}} deliverable and runs the
> Phase {{N}} XCTest + Jest suites in the appropriate
> modes; the `--post` mode invokes any phase-specific post
> checks (Lighthouse CI, regression sweep, day-completeness
> validator, readiness report consolidator, etc.).

**Branch:** `feature/phase{{N}}-step{{N}}-verify`

**Deploys:** nothing beyond merge — the CI matrix entry is live
on merge.

{{Settings table — the ladder `roadmodel ladder` prints for
this step's classification, pasted as printed with its
**Runs:** line; where roadmodel cannot be reached, the
single-column variant that matches PLATFORM.}}

|               |          | Cost                  | Balanced              | Quality               |
| ------------- | -------- | --------------------- | --------------------- | --------------------- |
| **Pick**      | Model    | **{{Model}}**         | **{{Model}}**         | **{{Model}}**         |
|               | Platform | {{Platform}}          | {{Platform}}          | {{Platform}}          |
|               | Level    | {{Level}}             | {{Level}}             | {{Level}}             |
|               | AA       | {{AA Index}}          | {{AA Index}}          | {{AA Index}}          |
|               | Price    | {{$ per 1M}}          | {{$ per 1M}}          | {{$ per 1M}}          |
| **Runner‑up** | Model    | **{{Model}}**         | **{{Model}}**         | **{{Model}}**         |
|               | Platform | {{Platform}}          | {{Platform}}          | {{Platform}}          |
|               | Level    | {{Level}}             | {{Level}}             | {{Level}}             |
|               | AA       | {{AA Index}}          | {{AA Index}}          | {{AA Index}}          |
|               | Price    | {{$ per 1M}}          | {{$ per 1M}}          | {{$ per 1M}}          |
| **Backup**    | Model    | **{{Model or none}}** | **{{Model or none}}** | **{{Model or none}}** |
|               | Platform | {{Platform}}          | {{Platform}}          | {{Platform}}          |
|               | Level    | {{Level}}             | {{Level}}             | {{Level}}             |
|               | AA       | {{AA Index}}          | {{AA Index}}          | {{AA Index}}          |
|               | Price    | {{$ per 1M}}          | {{$ per 1M}}          | {{$ per 1M}}          |

Price: list $ per 1M tokens (3 in : 1 out) × the tokens the model uses at that
level.

**Conversation:** New

**Runs:** {{the line `roadmodel ladder` prints}}

**Model rationale:** Why this model fits the mechanical
translation of the prior verify-script template into this
phase's deliverables. Name the PLATFORM and the subscription
or API key that pays for it. For Claude Code and the other
reasoning-dial surfaces, state why EFFORT is at the stated
level and why THINKING is on or off. For Codex, state why
INTELLIGENCE is at the stated level (the surface exposes no
other reasoning dial). For Cursor, state why MAX MODE is on
or off, and do not assert an effort or thinking level —
that surface has neither dial.

```xml
<task>
  <lifecycle>
    {{Six-stage lifecycle — copy
    verbatim from Step 1.}}
  </lifecycle>

  <security>
    {{Security gate — copy
    verbatim from Step 1. This
    step also AUTHORS the
    --security verify mode, so its
    own diff must still pass the
    gate before commit.}}
  </security>

  <context>
    {{Project}}. Phase {{N}}.
    Step {{N}}: QA + verification
    script.

    Steps 1 through {{N-1}} have
    been implemented. Now create
    the verification script, QA
    findings doc, and CI matrix
    update.

    Reference scripts (pattern
    templates):
    - scripts/verify-phase{{N-1}}.sh
      (closest structural
      precedent).
    - scripts/verify-phase{{N-2}}.sh
      (secondary pattern
      reference).

    Phase {{N}} deliverables to
    verify ({{K}} static checks
    across Steps 1 through {{N-1}}
    plus 4+ Step {{N}}
    self-checks):

    Step 1 ({{scope}}) — checks
    1-{{x}}:
    1.  Concrete static-check
        description.
    2.  ...

    Step 2 ({{scope}}) — checks
    {{x+1}}-{{y}}:
    {{x+1}}. ...

    Step {{N}} self-checks — checks
    {{last-3}}-{{last}}:
    {{last-3}}. scripts/verify-
        phase{{N}}.sh exists +
        executable.
    {{last-2}}. docs/phase{{N}}-qa-
        findings.md exists.
    {{last-1}}. docs/roadmap/
        phase{{N}}-roadmap.md
        exists (this doc).
    {{last}}. .github/workflows/
        phase-verify.yml matrix
        includes `{{N}}`.

    Files to read:
    - scripts/verify-phase{{N-1}}.sh
      (primary structural
      template).
    - all Phase {{N}} implementation
      files from Steps 1 through
      {{N-1}}.
  </context>

  <goal>
    Create scripts/verify-phase{{N}}.sh
    with {{K}}+ static deliverable
    checks (Steps 1 through {{N-1}})
    plus 4+ Step {{N}} self-checks
    plus a post-implementation
    V1-V{{N}} matrix. Create
    docs/phase{{N}}-qa-findings.md.
    Add `{{N}}` to the
    phase-verify.yml matrix.
  </goal>

  <requirements>
    <requirement>
      Read scripts/verify-phase{{N-1}}.sh
      end-to-end for structure,
      flag parsing, output format,
      record_pass / record_fail
      conventions, and the final
      summary table. Mirror the
      format exactly so the Phase
      {{N}} script is visually
      continuous with the Phase
      {{N-1}} script in CI logs.
    </requirement>

    <requirement>
      scripts/verify-phase{{N}}.sh
      modes:
      - default (no flag): static
        checks + Phase {{N}} Swift
        XCTest suite (macOS +
        Xcode).
      - --fast: static checks
        only, CI-safe on Linux /
        Ubuntu. MUST NOT shell
        out to xcodebuild, any
        Simulator, or any
        macOS-only tool. Static
        checks are grep / test
        -f / test -x / git ls-
        files based.
      - --swift: same as default;
        runs the Phase {{N}}
        XCTest suite.
      - --node: static + `npm
        --prefix functions run
        lint` (must continue to
        pass with `--max-warnings
        0`) + `npm --prefix
        functions test --
        --testPathPattern phase{{N}}`
        for the Phase {{N}} Jest
        slice.
      - --ui: phase-specific UI
        smoke configuration.
      - --security: the security
        gate for this phase's
        surface — secret/PII scan,
        SAST, and dependency audit
        over the phase's files
        (the same checks the
        pre-commit hook and CI
        run). CI-safe on Ubuntu;
        exits non-zero on any
        finding.
      - --all: static + swift +
        node + ui + security.
      - --post: static + V1-V{{N}}
        + phase-specific post
        invocations (lighthouse,
        regression sweep, day-
        completeness validator,
        readiness consolidator,
        etc.) + (when `gh` CLI is
        logged in) `gh pr checks`
        against the current branch.

      Static checks: {{K}}+
      numbered checks. Each check
      must use grep / test -f /
      test -x / git ls-files only;
      print a clear PASS / FAIL
      line referencing the
      deliverable number; be
      independent.

      At least ONE static check
      must be security-oriented and
      confirm the security gate is
      wired, not bypassed: e.g. the
      pre-commit hook config exists
      and runs the secret/SAST/dep
      scans, the phase's security
      checks appear in CI
      (phase-verify.yml / a
      security workflow), and no
      obvious secret pattern is
      committed under the phase's
      paths (grep for private-key
      PEM headers — the five-dash
      BEGIN line — `AKIA` key
      prefixes, etc.). This is the
      CI-side
      backstop to the per-commit
      gate.
    </requirement>

    <requirement>
      Post-implementation V-checks
      section mirroring the Phase
      {{N-1}} structure (V1-V{{N}}):

      V1 — Step 1 scope
      - V1.1 Static checks
        {{range}} all PASS.
      - V1.2 {{Swift XCTest name}}
        passes (--swift).
      - V1.3 {{TS Jest name}}
        passes (--node).

      V2 — Step 2 scope
      - V2.1 ...
      - V2.2 ...
      - V2.3 ...

      ...

      V{{N}} — CI integration +
      security
      - V{{N}}.1 verify-phase{{N}}
        .sh --fast exits 0 on
        Ubuntu CI.
      - V{{N}}.2 phase-verify.yml
        matrix includes `{{N}}`.
      - V{{N}}.3 All static checks
        pass.
      - V{{N}}.4 verify-phase{{N}}
        .sh --security exits 0
        (secret/PII scan, SAST, and
        dependency audit clean over
        the phase's surface).
    </requirement>

    <requirement>
      Create the
      Phase{{N}}VerificationTests
      Swift test file (path
      mirrors the project's
      existing test layout) with:
      - testRoadmapDocExists.
      - testQaFindingsDocExists.
      - testVerifyScriptExistsAnd
        Executable.
      - testPhaseVerifyMatrix
        Includes{{N}}.
    </requirement>

    <requirement>
      Update .github/workflows/
      phase-verify.yml to include
      `{{N}}` in the matrix —
      append `{{N}}` to the
      existing `matrix.phase`
      list. Preserve every prior
      phase entry; this is an
      additive change.
    </requirement>

    <requirement>
      Create docs/phase{{N}}-qa-
      findings.md with rollup
      sections for every Step 1
      through Step {{N-1}}, a Step
      {{N}} verify-script rollup,
      and a "Pre-ship items"
      section noting documented
      limitations + downstream-
      phase follow-ups.
    </requirement>

    <requirement>
      Mark the phase complete in
      the parent project roadmap
      (docs/roadmap/ROADMAP.md,
      beside this file) in the
      SAME Stage-3
      commit that marks this step
      (Status rule):
      - `### Phase {{N}}` gets
        `**Status:** Complete —
        <YYYY-MM-DD>; PR #<n>;
        {{milestone tag}};
        phase{{N}}-roadmap.md`
        directly under its heading,
        and the heading ends in ✅.
      - Its row in the "Phase
        Complexity Summary" table
        reads `Complete` (Step 1's
        PR set it to `In
        progress`).
      - The header `> **Status:**`
        line names Phase {{N}} as
        shipped and Phase {{N+1}}
        as next.
      - Consistency audit: the
        Phase {{N}} "Acceptance
        criteria" there match this
        roadmap's V1-V{{N}} checks.
      And in THIS roadmap, same
      commit: its phase-level
      `**Status:**` line (under the
      title) reads `Complete —
      <YYYY-MM-DD>`, the title and
      every step heading end in ✅,
      and every
      step's Summary Table Status
      cell reads `Complete — PR
      #<n>`.
    </requirement>

    <requirement>
      Script must be executable
      (chmod +x), print clear
      pass / fail per check, exit
      0 on success, exit 1 on
      any failure. Mirror the
      exact output format, check-
      numbering convention, and
      summary table from
      verify-phase{{N-1}}.sh so
      CI log diffing across
      phases is frictionless.

      --fast must complete in
      under 30 seconds on Ubuntu
      CI.
    </requirement>

    <requirement>
      Filepath comment: every new
      file gets the repo-relative
      path as the first line.
    </requirement>
  </requirements>
</task>
```

### Step {{N}} acceptance criteria

- `scripts/verify-phase{{N}}.sh` exists, is executable, and
  passes on a clean tree post-implementation.
- Script has {{K}}+ deliverable checks plus V1-V{{N}}
  post-implementation checks ({{total}}+ total).
- `--fast` runs in under 30 seconds on Ubuntu CI.
- `--post` mode runs cleanly on macOS with all
  phase-specific post-invocations green.
- `docs/phase{{N}}-qa-findings.md` complete with every
  rollup section.
- `.github/workflows/phase-verify.yml` matrix includes
  `{{N}}`; the new check appears on every PR.
- `--security` mode exists and exits 0 (secret/PII scan,
  SAST, and dependency audit clean over the phase's surface);
  V{{N}}.4 is green.
- Branch protection still passes on the resulting PR.
- **Operations** (only when this phase added or changed a
  runtime surface): every such surface has a health signal and
  an alarm that has been seen to fire once (or a synthetic
  failure was injected to prove it) — per the parent ROADMAP
  "Operations & observability strategy". {{Name the signal,
  the alarm, and how it was exercised.}}
- **Security gate clean** (always the final criterion): the
  pre-commit security gate passed on this step's diff and the
  security workflow is green.
- **Phase closed, nothing carried.** Every finding recorded in
  `docs/phase{{N}}-qa-findings.md` has a destination (fixed,
  an issue number, or a named phase that owns it), the "Not in
  scope" section below is current, and no un-tracked item
  remains. Every step of this roadmap, this one included,
  reads `**Status:** Complete — PR #…` on `main` under a ✅
  heading, the Summary Table's Status column and this roadmap's
  phase-level Status line say `Complete` under a ✅ title, and the
  parent project roadmap's Phase {{N}} entry (under a ✅ heading),
  its summary-table row, and its header status line say
  `Complete` — all landed in
  this step's PR. This step's final response ends with two lines and
  nothing after them: "Step {{N}} is complete. You can now move
  on to Step {{N+1}}." is replaced by "Step {{N}} is complete.
  Phase {{N}} is complete. You can now move on to Phase
  {{N+1}}." — same Stage 6 rule: no "Follow-ups", no trailer.

---

## Post-Implementation Verification

<!--
KEEP NONE OF THESE COMMENTS IN THE FINAL DOC.

Open the section with a paragraph explaining what runs
automatically in CI vs what is operator wall-clock work
(e.g. a 14-day soak, a 7-day trial, a cross-browser sweep
on Safari iOS that can't be GitHub-Actions-driven).

Follow with a top-level "Mode" table mapping each verify-
script mode to the workflow that runs it, the runner OS,
and the V-checks it covers.

Follow with a list of local invocation examples (one per
mode).

Then one V-section per step (V1 ... V{{N}}) with a table
listing every check id, what it verifies, and which
workflow runs it.
-->

Every V1-V{{N}} check below runs **automatically in CI** on
every push and pull request — no manual invocation
required, except where noted (list any operator wall-clock
exceptions here).

| Mode             | Workflow                                              | Runner | Coverage                                                                  |
| ---------------- | ----------------------------------------------------- | ------ | ------------------------------------------------------------------------- |
| `--fast`         | `phase-verify.yml` (matrix entry `{{N}}`)             | Ubuntu | Static checks 1-{{K}}, V1.1, V2.1, V3.1, ...                              |
| `--node`         | `phase{{N}}-post.yml` (or `phase-post.yml`)           | Ubuntu | V1.3, V2.3, ... (Phase {{N}} Jest slice + functions ESLint)               |
| `--swift`        | Xcode Cloud (`{{scheme}}` scheme)                     | macOS  | V1.2, V2.2, ... (XCTest)                                                  |
| `--ui`           | Xcode Cloud (`{{UI scheme}}` scheme)                  | macOS  | One-shot smoke / soak / etc.                                              |
| `--security`     | `phase-verify.yml` / security workflow                | Ubuntu | V{{N}}.4 (secret/PII scan + SAST + dependency audit)                      |
| `--post`         | {{workflow or local on macOS}}                        | {{OS}} | V{{n}}.{{m}} (phase-specific post check) + the full V-check sweep         |

Local invocations remain available for ad-hoc runs and
pre-release sweeps:

```bash
./scripts/verify-phase{{N}}.sh --post   # static + V1-V{{N}} + post checks
```

`--post` is the canonical command to run before tagging the
phase release.

Other modes:

```bash
./scripts/verify-phase{{N}}.sh              # static + V-checks + Swift unit tests
./scripts/verify-phase{{N}}.sh --fast       # static + V-checks only (Ubuntu CI)
./scripts/verify-phase{{N}}.sh --node       # static + functions Jest + lint
./scripts/verify-phase{{N}}.sh --swift      # static + Swift XCTest
./scripts/verify-phase{{N}}.sh --ui         # static + UI smoke
./scripts/verify-phase{{N}}.sh --security   # secret/PII scan + SAST + dep audit
./scripts/verify-phase{{N}}.sh --all        # static + Swift + Node + UI + security
```

The script reports each V-check by id (V1.1, V2.1, ...) so
a failure in any workflow above maps directly to the
corresponding row below.

### V1 — {{Step 1 scope}}

> **Automated in CI.** `phase-verify.yml` → V1.1; Xcode
> Cloud / `phase-post.yml` → V1.2 through V1.{{n}}.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V1.1 | Static checks {{range}} all PASS ({{short summary}}).              | `phase-verify.yml` runs `verify-phase{{N}}.sh --fast` on every push/PR.   |
| V1.2 | {{XCTest name}} passes; {{what it verifies}}.                      | Xcode Cloud `{{scheme}}` scheme XCTest run (`--swift` locally).           |
| V1.3 | {{Jest name}} passes; {{what it verifies}}.                        | `phase{{N}}-post.yml` runs `verify-phase{{N}}.sh --node`.                 |

### V2 — {{Step 2 scope}}

> **Automated in CI.** `phase-verify.yml` → V2.1; Xcode
> Cloud → V2.2; `phase{{N}}-post.yml` → V2.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V2.1 | Static checks {{range}} all PASS.                                  | `phase-verify.yml --fast`.                                                |
| V2.2 | {{XCTest name}} passes.                                            | Xcode Cloud (`--swift` locally).                                          |
| V2.3 | {{Jest name}} passes.                                              | `phase{{N}}-post.yml --node`.                                             |

<!-- Repeat V3, V4, ... V{{N-1}} for each step. Every V
     section opens with a one-line `> **Automated in CI.**`
     blockquote that maps the V-checks to the workflows
     that run them. -->

### V{{N}} — CI integration + security

> **Automated in CI.** `phase-verify.yml` → V{{N}}.1
> through V{{N}}.4 on every push/PR.

| ID         | Check                                                          | Automation                                                                |
| ---------- | -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V{{N}}.1   | `verify-phase{{N}}.sh --fast` exits 0 on Ubuntu CI.            | `phase-verify.yml` matrix entry `{{N}}`.                                  |
| V{{N}}.2   | `phase-verify.yml` matrix includes `{{N}}`.                    | `phase-verify.yml --fast` static check.                                   |
| V{{N}}.3   | All static checks in `verify-phase{{N}}.sh` pass.              | `phase-verify.yml --fast` records pass only when `STATIC_DELIVERABLE_FAIL == 0`. |
| V{{N}}.4   | `verify-phase{{N}}.sh --security` exits 0 (secret/PII scan + SAST + dep audit clean). | `phase-verify.yml` / security workflow runs `--security` on every push/PR. |

---

## Summary Table

<!-- One row per step and per verification check. Model is the
     Pick of the column the step's **Runs:** line names (with
     a single-column Settings table, its Model); the step's own
     Settings table carries the platform, the dials, the other
     ranks and the other two columns, so this table need not.
     Scope is at most 30 characters, so every row fits in 80
     columns. A verification row's Model reads `CI`; its
     section names the workflows.

     Column "Status" mirrors each step's `**Status:**` line:
     `Not started` when this roadmap is written, set to
     `Complete — PR #<n>` by the step's own Stage-3 commit
     (Status rule). Verification rows read "--". -->

| Step | Scope                          | Model          | Status             |
| ---- | ------------------------------ | -------------- | ------------------ |
| 1    | {{Step 1 short scope}}         | {{Model}}      | Not started        |
| 2    | {{Step 2 short scope}}         | {{Model}}      | Not started        |
| ...  | ...                            | ...            | ...                |
| {{N}} | QA + verify-phase{{N}}.sh     | {{Model}}      | Not started        |
| V1   | {{Step 1 scope}}               | CI             | --                 |
| V2   | {{Step 2 scope}}               | CI             | --                 |
| ...  | ...                            | CI             | --                 |
| V{{N}} | CI integration               | CI             | --                 |

---

## Model selection blocks

<!--
KEEP NONE OF THESE COMMENTS IN THE FINAL DOC.

Optional but recommended. The per-step Settings tables
above carry the canonical Model / Platform / settings /
Conversation values; the rationale paragraphs map task
characteristics to model strengths. The text block below
restates the same selections in the roadmap-annotation
output format for ease of audit by a roadmodel script.

Include this section if your project has a roadmodel
audit tool that consumes the text format. Skip it if not.
With ladder Settings tables, each block restates the column
the step's **Runs:** line names.
-->

<!-- These blocks follow OUTPUT CONTRACT VERSION 2 of
     `<output-format>` in model-selector.txt. Five lines
     are ALWAYS present — MODEL, BACKUP, PLATFORM,
     CONVERSATION, RATIONALE — and the SETTING lines are
     PLATFORM-CONDITIONAL: emit a line only when the
     chosen PLATFORM actually exposes that dial, and OMIT
     THE WHOLE LINE otherwise. Never write "Off", "N/A",
     or "--" for a control the surface does not have.
       • EFFORT + THINKING → every surface with a
         reasoning dial (Claude Code, Codex, ChatGPT app,
         claude.ai web, Anthropic / OpenAI / Google APIs,
         Gemini CLI, DeepSeek API). EFFORT carries the
         LEVEL (Low/Medium/High/XHigh/Max/Ultracode);
         THINKING is a two-position toggle, On or Off,
         and NEVER carries an effort word; a model that
         always thinks (Opus 5.5, Sonnet 5.5, Haiku 5.5 and the Fable models) gets NO THINKING line. In a roadmap
         table Codex's dial is labelled "Intelligence"
         after its own UI, but the block line is EFFORT.
       • MAX MODE → CURSOR ONLY (On/Off). Cursor exposes
         no reasoning dial, so a Cursor block carries MAX
         MODE and NO EFFORT / THINKING lines at all.
       • ORCHESTRATION → Claude Code only (None or
         PerPrompt). Ultracode is NOT an orchestration
         value in v2 — it is the top rung of EFFORT.
     Version note for audit tooling: v1 blocks emitted MAX
     MODE unconditionally and packed the effort level into
     THINKING. A parser must dual-accept — treat every
     setting line as optional, and when EFFORT is absent
     but THINKING carries an effort word, read that as the
     v1 level. -->

```text
PROMPT: Step 1 — {{step title}}
MODEL: {{model}}
BACKUP: {{fallback model, or None}}
PLATFORM: {{access method name}}
{{Claude Code and every other reasoning-dial surface:}}
EFFORT: {{Low/Medium/High/XHigh/Max/Ultracode}}
THINKING: {{On or Off — omit the line for a model that always thinks}}
{{Claude Code only, additionally:}}
ORCHESTRATION: {{None or PerPrompt}}
{{Cursor only — and INSTEAD OF the two lines above, not alongside them:}}
MAX MODE: {{On or Off}}
CONVERSATION: {{New or Continue}}
RATIONALE: {{Three labelled segments, one crisp sentence
each: "TASK: <primary task category>", "PICK: <the model's
tier rating plus one headline benchmark supporting it>",
"EFFORT: <why the EMITTED setting fields fit this task's
difficulty>". The third segment justifies only the lines
the block actually carries — never an effort level for
Cursor, never Max Mode for Claude Code or Codex. Name the
subscription or API key that pays for the PLATFORM in the
step's prose rationale above, not here.}}

PROMPT: Step 2 — {{step title}}
MODEL: {{model}}
BACKUP: {{fallback model, or None}}
PLATFORM: {{access method name}}
{{Setting lines the PLATFORM exposes: reasoning-dial surface →
EFFORT + THINKING(On/Off, absent for a model that always thinks)
(+ ORCHESTRATION on Claude Code);
Cursor → MAX MODE only.}}
CONVERSATION: {{New or Continue}}
RATIONALE: {{Same TASK / PICK / EFFORT shape as Step 1.}}

PROMPT: Step 3 — {{step title}}
MODEL: {{model}}
BACKUP: {{fallback model, or None}}
PLATFORM: {{access method name}}
{{Setting lines the PLATFORM exposes: reasoning-dial surface →
EFFORT + THINKING(On/Off, absent for a model that always thinks)
(+ ORCHESTRATION on Claude Code);
Cursor → MAX MODE only.}}
CONVERSATION: {{New or Continue}}
RATIONALE: {{...}}

PROMPT: Step {{N}} — QA + verify-phase{{N}}.sh
MODEL: {{model}}
BACKUP: {{fallback model, or None}}
PLATFORM: {{access method name}}
{{Setting lines the PLATFORM exposes: reasoning-dial surface →
EFFORT + THINKING(On/Off, absent for a model that always thinks)
(+ ORCHESTRATION on Claude Code);
Cursor → MAX MODE only.}}
CONVERSATION: {{New or Continue}}
RATIONALE: {{TASK: mechanical translation of the prior
verify-script template into this phase's deliverables.
PICK: known pattern, no novel reasoning — roadmodel's
"standard implementation, multi-file changes, and roadmap
execution" default. EFFORT: <why the emitted dials fit>.}}
```

---

## Not in scope (from product roadmap)

<!--
KEEP NONE OF THESE COMMENTS IN THE FINAL DOC.

Two sub-lists:
  1. Items the parent ROADMAP.md explicitly marks
     out-of-scope for this phase — quote / paraphrase from
     the parent roadmap.
  2. Additional items the AI / author has identified as
     out-of-scope during this roadmap's drafting (typical
     surfaces: cross-platform parity, formal load testing,
     marketing surfaces, post-launch iteration, separate
     follow-up phase territory).

Each item is one bullet, two sentences max. Lead with the
deferred thing, follow with where / when it lives instead.
-->

Per [`docs/roadmap/ROADMAP.md`](ROADMAP.md) Phase {{N}} "Not in
scope":

- Item explicitly deferred by the parent roadmap, with a
  one-sentence pointer to where / when it lives instead.
- Item.
- Item.

Additionally not in scope for this phase:

- Item identified during drafting, with a pointer to the
  follow-up phase that owns it.
- Item.
- Item.

---

_This roadmap is the execution plan for Phase {{N}}. Each
step's `**Status:**` line is flipped by that step's own PR
(Status rule), so this file on `main` is the phase's ledger —
`grep -n '^\*\*Status:\*\*'` reports progress. After all steps and
verification pass, and every finding has a destination, Phase
{{N}} is complete — declared with the line "Phase {{N}} is
complete. You can now move on to Phase {{N+1}}." and nothing
after it — and Phase {{N+1}} ({{title}}) inherits
{{one-sentence summary of the deliverables the next phase
consumes from this one}}._

<!--
=============================================================
POST-MERGE BACK-PATCH PATTERN (optional, append as needed)
=============================================================
When an issue is discovered AFTER a step has been merged
and the phase has moved on, do NOT rewrite the step
in-place. Append a back-patch subsection so the git
history of the decision is preserved.

Pattern: append a `#### Step N back-patch (YYYY-MM-DD) —
short title` subsection under the affected step (or, for
broader changes, a `## Post-merge addendum (YYYY-MM-DD) —
short title` section at the bottom of the file).

The back-patch records:
  - What was discovered post-merge.
  - What was actually shipped to fix it.
  - Cross-references to the audit / QA / backlog rows.
  - Any acceptance criteria that need re-running.
  - Whether the back-patch was later REVERTED — if so,
    keep the original text as a record but mark it
    "⚠️ REVERTED on YYYY-MM-DD by the next subsection"
    so future readers don't re-introduce the rejected
    direction.

Example skeleton:

  #### Step 3 back-patch (2026-MM-DD) — {{short title}}

  {{One paragraph describing what was discovered, what
  shipped to fix it, and where the canonical record of the
  decision lives. Reference the audit doc finding id, the
  QA findings rollup, and any tests that need re-running.}}

  Audit cross-reference: see
  [`docs/phase{{N}}-website-audit.md`](../phase{{N}}-website-audit.md)
  finding `PHASE{{N}}-AUDIT-NNN`. QA cross-reference: see
  [`docs/phase{{N}}-qa-findings.md`](../phase{{N}}-qa-findings.md)
  § "{{Back-patch rollup heading}}".
=============================================================
-->
