<!--
=============================================================
PROJECT ROADMAP TEMPLATE
=============================================================
PURPOSE
  A reusable skeleton for a multi-phase project roadmap.
  Hand this file to the AI together with a short brief of the
  project. The AI fills in every <PLACEHOLDER>, removes any
  HTML-comment guidance, and produces a finished roadmap in the
  exact style this template enforces.

STYLE RULES (the AI MUST follow)
  - All prose wraps at 80 characters per line.
  - Use Markdown tables for any list of >3 structured items
    (gaps, controls, costs, risks, milestones, etc.).
  - Use ASCII boxes (┌ ┐ └ ┘ │ ─ ▶) for architecture diagrams.
  - Every phase ends with an "Acceptance criteria" section
    written as a bulleted list of testable statements.
  - Every phase's "Acceptance criteria" MUST include at least
    one security check (secret scan clean, SAST + dependency
    audit green, sensitive-data handling verified). Security is
    a per-phase exit gate, never a final-phase afterthought —
    an issue introduced in Phase 2 must be caught in Phase 2,
    before its work is committed, pushed, or merged.
  - This file lives at `docs/roadmap/ROADMAP.md`, and every
    phase roadmap (`phaseNN-roadmap.md`) is written beside it:
    all roadmaps in one folder, none at the repo root. A
    project that keeps its roadmaps git-excluded (e.g.
    `private/`) keeps them there. Relative links resolve from
    `docs/roadmap/` (`../../README.md`, `../ci.md`).
  - Every phase carries a one-line metadata badge:
      **Complexity:** … · **Risk:** … · **Cloud cost:** … ·
      **Handles sensitive data:** <Yes/No — PII, secrets, auth>
  - Every phase carries a **Phase roadmap settings** table
    directly after its metadata badge: the model and dials for
    the session that writes that phase's roadmap with
    `/roadmap-phase N`. The steps inside the phase get their
    own tables in the phase roadmap. Pick it with the model
    selector, quality first. A phase roadmap fixes every step's
    scope, task prompt, acceptance criteria and Settings, so it
    is the phase's highest-leverage session, and it runs once:
    its Quality column is the strongest `planning` model
    the operator's access methods reach, at the deepest
    reasoning rung that model exposes on its platform (`Max`
    in Claude Code, which `/roadmap-phase` sets by itself),
    with thinking on where the model has a Thinking toggle
    (Opus 5.5 and the other models that always think have
    none, and the ladder carries no Thinking row: it is always On where a
    toggle exists). Where `roadmodel` is installed, the table
    is the ladder `roadmodel ladder --category planning
    --complexity high --phase` prints, pasted as printed:
    Cost, Balanced and Quality, each ranked three deep (Pick,
    Runner-up, and a Backup from another maker), each option
    with its level, AA Index and price, every usage pool read
    at headroom. It names no column to run: the operator picks
    the option (roadmodel 0.2.106 on). It ranks on measured
    benchmarks, so a stale catalog letter cannot steer it, and
    a model the user-context names for these sessions still
    wins. Never `Ultracode`: it reasons at `Extra high` and
    adds parallel agents, which one planning document does not
    need. A rule for roadmap-writing sessions in the
    user-context overrides this default, unless it turns on a
    usage pool's state: pool states are informational and never
    steer a pick. Without roadmodel, the
    table takes its platform's single-column shape (the phase
    roadmap template's Settings variants) with a Backup row.
    Its Conversation is always **New**. Once the phase roadmap
    exists, the table is history: only a phase not yet written
    is ever re-picked.
  - Every phase carries a `**Status:**` line directly under its
    `### Phase` heading, before its **Goal:** — `Not started`
    when this roadmap is written. The phase's FIRST step flips it
    to `In progress — <phase roadmap file>` and its FINAL step to
    `Complete — <YYYY-MM-DD>; PR #<n>; <tag>; <phase roadmap
    file>` and appends ` ✅` to the heading (`### Phase 5 —
    <Title> ✅`), each in that step's own PR, so this file on
    `main` marks a phase complete exactly when its last PR merges
    (see §5 "Step lifecycle" Stage 3), and the outline shows it
    the way a phase roadmap shows its steps. The §8 summary table carries the same
    state in its Status column, and the header `> **Status:**`
    line agrees with both. Nothing else records completion.
  - §5 "Security & privacy strategy" is MANDATORY for any
    project touching user data, secrets, PII, credentials, or
    auth. Only omit it for a throwaway with zero sensitive
    surface, and say so explicitly if you do.
  - §5 "Release & deployment strategy" is MANDATORY for any
    project with a deployed or published surface (web app,
    service, registry package, scheduled automation, database).
    Merged is not deployed and deployed is not released: a
    phase that touches such a surface names its post-deploy
    verification in its acceptance criteria.
  - §5 "Operations & observability strategy" is MANDATORY for
    any project that runs a service or scheduled automation.
  - §5 "Worktree strategy" and "Defect handling & triage" are
    kept whenever the branch strategy is kept.
  - Prefer short, declarative sentences over hedged paragraphs.
  - Never invent numbers; mark unknowns as "TBD".
  - Output the finished document in raw Markdown only.
  - Strip every <!-- ... --> instruction block before delivery.
=============================================================
-->

# <PROJECT_NAME> — <ROADMAP_SUBTITLE>

> **Status:** <Draft v1 | Approved | In progress — Phases 1–k
> complete, Phase k+1 next>
> **Owner:** <NAME, ROLE>
> **Audience:** <Internal team | External stakeholders | …>
> **Target environment:** <Local | AWS | Azure | GCP | …>
> **Last updated:** <Month YYYY>

<!--
1-3 paragraph executive lead. Answer:
  - What does this roadmap take the project FROM and TO?
  - Why now?
  - Link to any prior/archived roadmap that this supersedes.
-->

---

## 1. Executive Summary

<!--
4-6 sentences describing the current state and the destination.
Then enumerate the 3-5 hard constraints driving the work.
Close with a one-line "path" sentence summarising the order of
operations (e.g. "clean → secure → authenticate → cloud →
operate").
-->

The <PROJECT_NAME> is <one-line current-state summary>. It now
needs to <one-line destination summary> while satisfying these
constraints:

1. **<Constraint 1>.** <one sentence>.
2. **<Constraint 2>.** <one sentence>.
3. **<Constraint 3>.** <one sentence>.
4. **<Constraint 4>.** <one sentence>.

The path: **<verb> → <verb> → <verb> → <verb>**. <One sentence
on phase independence and sequencing.>

### <Optional: Initial user roster / scope table>

| <Header A> | <Header B>             | <Header C>          |
|------------|------------------------|---------------------|
| <row>      | <row>                  | <row>               |

---

## 2. Current State Assessment

### What works today
<!-- Bullet list of features/capabilities already in place. -->
- <Capability 1>.
- <Capability 2>.
- <Capability 3>.

### Gaps blocking <DESTINATION_STATE>

<!--
Numbered table of every concrete gap. Severity is one of:
Critical | High | Medium | Low. Order rows by severity, then
by phase that addresses them.
-->

| #  | Gap                                       | Severity |
|----|-------------------------------------------|----------|
| 1  | <Gap description>                         | Critical |
| 2  | <Gap description>                         | High     |
| 3  | <Gap description>                         | Medium   |
| …  | …                                         | …        |

These gaps drive the phase ordering below.

---

## 3. Target Architecture

<!--
ASCII diagram of the destination architecture. Use the same
box-drawing characters demonstrated below. Label every
component, every trust boundary, and every data flow direction.
Keep the diagram under 30 lines. Follow with a 2-3 sentence
description of where everything lives and what the only public
surface is.
-->

```
        ┌──────────────────────────────┐
        │  <External identity / edge>  │
        └────────────┬─────────────────┘
                     │ <protocol>
                     ▼
   ┌─────────────────────────────────────────┐
   │  <Compute tier — frontend>              │
   └────────────────────┬────────────────────┘
                        │ <protocol + auth>
                        ▼
   ┌─────────────────────────────────────────┐
   │  <Compute tier — backend>               │
   └─────┬─────────────────────────────┬─────┘
         ▼                             ▼
   ┌──────────────┐               ┌──────────────┐
   │  <Data>      │               │  <Secrets>   │
   └──────────────┘               └──────────────┘
```

<One paragraph describing region, network boundary, and the
single public ingress point.>

---

## 4. Phased Roadmap

<!--
The heart of the document. Produce 3–8 phases. Each phase MUST
have:
  1. ### Phase N — <Title> (ends in ` ✅` once Complete)
  2. **Status:** Not started (flipped to In progress by the
     phase's first step and to Complete by its final step —
     see the STYLE RULES and §5 "Step lifecycle").
  3. **Goal:** one sentence.
  4. Metadata line: **Complexity:** … · **Risk:** … ·
     **Cloud cost:** … · **Handles sensitive data:** …
  5. **Phase roadmap settings** — the model and dials that
     write this phase's roadmap (`/roadmap-phase N`), picked
     quality first (see the STYLE RULES), then one or two
     sentences on why.
  6. Numbered sub-sections (#### N.1, #### N.2, …) describing
     concrete work.
  7. Tables, code blocks, or schema dumps where they clarify.
  8. **Acceptance criteria** — bulleted, testable list that
     INCLUDES at least one security check for the surface the
     phase touches (see §5 "Security & privacy strategy") and,
     when the phase touches a deployed surface, a deployed-and-
     verified check (see §5 "Release & deployment strategy").
Phases are ordered so each is independently shippable and the
dependency graph in §5 is honoured.
-->

### Phase 1 — <Phase Title>

**Status:** Not started

**Goal:** <One sentence describing the outcome of this phase.>

**Complexity:** <Low | Medium | High> · **Risk:**
<Low | Medium | High> · **Cloud cost:** <$0 | …> ·
**Handles sensitive data:** <Yes/No — PII, secrets, auth>

**Phase roadmap settings** — the session that writes
`phase01-roadmap.md` (`/roadmap-phase 1`):

|               |          | Cost                | Balanced            | Quality             |
| ------------- | -------- | ------------------- | ------------------- | ------------------- |
| **Pick**      | Model    | **<Model>**         | **<Model>**         | **<Model>**         |
|               | Platform | <Platform>          | <Platform>          | <Platform>          |
|               | Level    | <Level>             | <Level>             | <Level>             |
|               | AA       | <AA Index>          | <AA Index>          | <AA Index>          |
|               | Price    | <$ per 1M>          | <$ per 1M>          | <$ per 1M>          |
| **Runner‑up** | Model    | **<Model>**         | **<Model>**         | **<Model>**         |
|               | Platform | <Platform>          | <Platform>          | <Platform>          |
|               | Level    | <Level>             | <Level>             | <Level>             |
|               | AA       | <AA Index>          | <AA Index>          | <AA Index>          |
|               | Price    | <$ per 1M>          | <$ per 1M>          | <$ per 1M>          |
| **Backup**    | Model    | **<Model or none>** | **<Model or none>** | **<Model or none>** |
|               | Platform | <Platform>          | <Platform>          | <Platform>          |
|               | Level    | <Level>             | <Level>             | <Level>             |
|               | AA       | <AA Index>          | <AA Index>          | <AA Index>          |
|               | Price    | <$ per 1M>          | <$ per 1M>          | <$ per 1M>          |

Price: list $ per 1M tokens (3 in : 1 out) × the tokens the model uses at that
level.

**Conversation:** New

<!-- The ladder `roadmodel ladder --category planning
--complexity high --phase` prints, pasted as printed. Without
roadmodel, a single-column table in its platform's shape from
the phase roadmap template's Settings variants: Codex carries
Intelligence and no Thinking row; Cursor carries Max Mode
alone. -->

<One or two sentences: what this phase's roadmap must get
right, and, on its merits alone, the option that fits it best
(quality first: it fixes every step after it). Never which
column runs, a pool's state or the Budget priority: the
operator picks the option.>

#### 1.1 <Sub-section title>
- <Action item>.
- <Action item>.

#### 1.2 <Sub-section title>
- <Action item>.
- <Action item>.

<!-- Add more sub-sections (1.3, 1.4, …) as needed. -->

**Acceptance criteria**
- <Testable statement 1>.
- <Testable statement 2>.
- <Testable statement 3>.
- **Deployed & verified** (when the phase touches a deployed
  surface): <the surface's version/health endpoint reports
  this phase's build, and the changed behaviour was exercised
  in the target environment with real authentication — name
  the endpoint, the request, and the expected result>.
- **Security:** the §5 security gate ran clean on this
  phase's work — no secrets/PII committed, SAST + dependency
  audit green, and the new/changed surface handles sensitive
  data per §5 (least privilege, encrypted in transit + at
  rest, no PII in logs). <Name the concrete check.>

---

### Phase 2 — <Phase Title>

**Status:** Not started

**Goal:** <one sentence>.

**Complexity:** … · **Risk:** … · **Cloud cost:** …

**Phase roadmap settings** — the session that writes
`phase02-roadmap.md` (`/roadmap-phase 2`):

|               |          | Cost  | Balanced | Quality |
| ------------- | -------- | ----- | -------- | ------- |
| **Pick**      | Model    | **…** | **…**    | **…**   |
|               | Platform | …     | …        | …       |
|               | Level    | …     | …        | …       |
|               | AA       | …     | …        | …       |
|               | Price    | …     | …        | …       |
| **Runner‑up** | Model    | **…** | **…**    | **…**   |
|               | Platform | …     | …        | …       |
|               | Level    | …     | …        | …       |
|               | AA       | …     | …        | …       |
|               | Price    | …     | …        | …       |
| **Backup**    | Model    | **…** | **…**    | **…**   |
|               | Platform | …     | …        | …       |
|               | Level    | …     | …        | …       |
|               | AA       | …     | …        | …       |
|               | Price    | …     | …        | …       |

Price: list $ per 1M tokens (3 in : 1 out) × the tokens the model uses at that
level.

**Conversation:** New

<Why, in one or two sentences.>

#### 2.1 <Sub-section title>
- <Action>.

#### 2.2 <Sub-section title>
- <Action>.

**Acceptance criteria**
- <Testable statement>.

---

<!-- Repeat the phase block for Phase 3, 4, … N. -->

### Phase N — <Final Phase Title>

**Status:** Not started

**Goal:** <one sentence>.

**Complexity:** … · **Risk:** … · **Cloud cost:** …

**Phase roadmap settings** — the session that writes
`phaseNN-roadmap.md` (`/roadmap-phase N`):

|               |          | Cost  | Balanced | Quality |
| ------------- | -------- | ----- | -------- | ------- |
| **Pick**      | Model    | **…** | **…**    | **…**   |
|               | Platform | …     | …        | …       |
|               | Level    | …     | …        | …       |
|               | AA       | …     | …        | …       |
|               | Price    | …     | …        | …       |
| **Runner‑up** | Model    | **…** | **…**    | **…**   |
|               | Platform | …     | …        | …       |
|               | Level    | …     | …        | …       |
|               | AA       | …     | …        | …       |
|               | Price    | …     | …        | …       |
| **Backup**    | Model    | **…** | **…**    | **…**   |
|               | Platform | …     | …        | …       |
|               | Level    | …     | …        | …       |
|               | AA       | …     | …        | …       |
|               | Price    | …     | …        | …       |

Price: list $ per 1M tokens (3 in : 1 out) × the tokens the model uses at that
level.

**Conversation:** New

<Why, in one or two sentences.>

#### N.1 <Sub-section title>
- <Action>.

**Acceptance criteria**
- <Testable statement>.

---

## 5. Cross-Cutting Concerns

### Cost projection (monthly, USD, <pilot|prod> scale)

<!-- Skip this section if cost is irrelevant to the project. -->

| Service                                  | Estimate    |
|------------------------------------------|-------------|
| <Service 1>                              | <$X–Y>      |
| <Service 2>                              | <$X–Y>      |
| **Total**                                | **<$X–Y>**  |

### Sequencing & dependencies

<!--
ASCII flow showing which phases depend on which. Use ──▶ for
sequential dependency and branch with ┌─ when phases can run
in parallel.
-->

```
Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ Phase 4 ──▶ Phase 5
                                                  │
                                                  ▼
                                          Phase 6 ──▶ Phase 7
```

- <One bullet per dependency or sequencing rule.>
- <Note any phase that can be done locally with zero spend.>
- <Note the cutover phase (the irreversible one) and its
  readiness-gate sub-step — see "Release & deployment
  strategy".>
- <Name any phases that may run in parallel — they are the
  only concurrency the "Worktree strategy" permits.>

### Branch management strategy

<!--
Include this section for any project with >1 contributor or
any compliance/audit requirement. Skip for solo throwaway
work.
-->

#### Branching model

`main` is the single source of truth. All work happens on
short-lived branches (≤ 1 week) that merge into `main` via
pull request. `main` must always be:

- Green on CI.
- Deployable to the target environment.
- Tagged with semver on every production release.

#### Branch naming convention

| Prefix     | Purpose                          | Example                          |
|------------|----------------------------------|----------------------------------|
| `feature/` | Phase work or new feature        | `feature/phase-1-<slug>`         |
| `fix/`     | Non-urgent bug fix               | `fix/<slug>`                     |
| `hotfix/`  | Urgent production fix from `main`| `hotfix/<slug>`                  |
| `chore/`   | Tooling, deps, housekeeping      | `chore/<slug>`                   |
| `docs/`    | Documentation-only changes       | `docs/<slug>`                    |
| `perf/`    | Performance work                 | `perf/<slug>`                    |
| `release/` | Pre-release stabilisation        | `release/v<X.Y.Z>`               |

#### Pull request rules
1. **Scope discipline.** One PR per phase sub-section.
2. **PR template.** Roadmap reference, summary, test plan,
   screenshots for UI, breaking-change notes, rollback plan.
3. **CI green required.** Lint, type-check, tests, and the
   security scans (secret scan, SAST, dependency audit) all
   pass before merge. CI re-runs the same security gate the
   pre-commit hook ran locally — defense in depth, so a bypassed
   or skipped local hook still cannot land an issue on `main`.
4. **No force-push to `main`.** Allowed on personal branches
   only before review opens.
5. **Squash-merge** to `main` so each phase reads as one
   clean commit.
6. **Conventional Commits** on the squash message.

#### Step lifecycle

Every step / sub-section of every phase follows the same
six-stage lifecycle, in order, with no exceptions. Each stage
is a hard checkpoint — if any stage is skipped, branch
protection or the next step's Stage 1 will fail loudly, and
that is the safety net. AI coding agents executing a step MUST
complete all six stages before declaring the step done.

1. **Create the branch.** Before any Read / Edit / Bash, run
   `git checkout -b <prefix>/<slug>` from a clean,
   up-to-date `main` (e.g. `feature/phase-2-cost-estimator`).
   The branch name comes from the roadmap step's `**Branch:**`
   line, or from the naming convention above for ad-hoc work.
   When the step runs in its own working tree (one of the
   three cases in "Worktree strategy" below), the equivalent
   is `git fetch origin && git worktree add -b <prefix>/<slug>
   <worktree-path> origin/main`, followed by that worktree's
   bootstrap.

2. **Work on the branch, and pass the security gate before
   every commit.** All commits land here. Never push to `main`
   directly — branch protection rejects it. Before each
   `git commit`, the local security gate (see §5 "Security &
   privacy strategy" → "Per-step security gate") must run and
   pass: secret scan clean, SAST clean, dependency audit clean,
   and no sensitive data (PII, credentials, tokens) in the
   diff. The gate is wired into the pre-commit hook and is
   fail-closed — a finding blocks the commit, so a security
   issue introduced while implementing this step is caught here,
   before it ever reaches the branch, the PR, or `main`.

3. **Open the PR, then mark the step.** `gh pr create --base
   main --head <branch>` with a Conventional Commits title and a
   body referencing the roadmap step and its acceptance
   criteria. One PR per step. Then, with the PR number in hand,
   set the step's `**Status:**` line in its phase roadmap to
   `Complete — PR #<n> (<YYYY-MM-DD>)`, commit that edit on the
   step branch (`docs: mark Phase N Step M complete`), and push.
   The PR carries its own completion mark, so the roadmap on
   `main` says the step is complete exactly when the PR merges —
   never before, and never by a later conversation
   reconstructing history from `git log`. The same commit marks
   the phase here: on a phase's first step its `**Status:**`
   line becomes `In progress — <phase roadmap file>`; on its
   final step, `Complete — …` with ` ✅` appended to its
   `### Phase` heading, together with its §8 summary row and the
   header `> **Status:**` line. A roadmap that is
   git-excluded needs the edit only.

4. **Wait for green checks, then squash-merge.** Every required
   status check must report success. If the PR goes BEHIND
   main, refresh with `gh pr update-branch --rebase` — never
   merge `main` into the branch when the repo enforces linear
   history. Once green:

   ```sh
   gh pr merge <PR_NUMBER> --squash --delete-branch
   ```

   Merged is not done for a step that touches a deployed
   surface: complete the post-deploy verification named in the
   step's acceptance criteria (see "Release & deployment
   strategy") before Stage 6.

5. **Retire the branch (remote + local).** The
   `--delete-branch` flag and the repo's
   `delete_branch_on_merge: true` setting retire the remote
   automatically. Sync local state and prune the merged branch
   plus any other `[gone]` labels:

   ```sh
   git switch main
   git pull --ff-only origin main
   git fetch --prune origin
   git branch -vv | grep ': gone]' | awk '{print $1}' \
     | xargs -r git branch -D
   ```

   If the step ran in its own working tree, remove that
   worktree FIRST — `git worktree remove <worktree-path>`, then
   `git worktree prune` — because `git branch -D` refuses to
   delete a branch that is still checked out in a worktree.
   Between steps, `git worktree list` shows only the primary
   tree.

6. **Dispose of every finding, declare completion, then new
   conversation.** Before declaring anything, send every
   finding the step surfaced to its destination per "Defect
   handling & triage" below — a note for a later step is edited
   into that step's prompt now, a bug is fixed or is an issue
   number, a judgement call in the diff is explained in the PR
   body. A finding that is only described is not disposed of,
   and counts as an unmet acceptance criterion. Only once the
   PR is merged — and `main` therefore carries the step's
   `Complete` Status line — every acceptance criterion is
   affirmatively met, and every finding has a destination, end
   the final response with the verbatim line "Step N is
   complete. You can now move on to Step N+1." (or, on the
   phase's last step, "Phase N is complete. You can now move on to
   Phase N+1."). That line is the LAST line of the response.
   Nothing follows it — no "Follow-ups (non-blocking)",
   "Notes", "Next", or suggested improvements. If any
   criterion is unmet or any finding has no destination, say
   plainly that the step is NOT complete, name what is
   outstanding, and withhold the line. "Done" means done. Then,
   for phase-boundary hygiene, the operator closes the current
   Claude Code / Cursor / Codex session and opens a fresh one
   before starting the next step.
   The new conversation begins again at Stage 1 with the next
   step's `**Branch:**` line driving the `git checkout -b`
   command. No work straddles two steps.

#### Worktree strategy

<!--
Keep this subsection whenever the branch strategy is kept. It
bounds the ONE sanctioned way to have more than one working
tree, so parallel work cannot quietly bypass the serial step
lifecycle above.
-->

The default is one working tree — the primary checkout — and
one step in flight at a time; the six-stage lifecycle assumes
it. A second working tree is created only with
`git worktree add` (never a second clone, which would not
share branches, hooks, or config), and only in these cases:

| Case                         | Rule                                                                 |
|------------------------------|----------------------------------------------------------------------|
| Hotfix interrupting a step   | A Critical/High finding (see "Vulnerability handling") gets its `hotfix/` branch in a worktree cut from `origin/main`. The in-flight step's tree is left untouched — nothing stashed, nothing half-committed. |
| Declared-independent steps   | Only steps the "Sequencing & dependencies" diagram (or a phase roadmap's Execution Order) draws in parallel. Each gets its own worktree AND its own conversation; each branches from the same `origin/main` and rebases before merge. Undeclared parallelism is a lifecycle violation, not a shortcut. |
| Subagent isolation in a step | Multi-agent runs inside one step (an agent harness's worktree-isolated subagents) work in throwaway worktrees. Results merge back into the step branch locally; only the step branch opens a PR, and every subagent worktree is removed before Stage 3. |

Rules that apply to every worktree:

1. **Location.** Worktrees live in one recorded place per
   project: a sibling directory (`../<repo>--<branch-slug>`)
   or a git-ignored `.worktrees/<branch-slug>/` inside the
   repo. Agent tooling that creates its own worktrees keeps
   its own location. Never nest a worktree under a tracked
   path. This project uses: <sibling | .worktrees/>.
2. **Bootstrap before use.** A new worktree has NONE of the
   primary tree's untracked state: dependency directories
   (virtualenv, `node_modules`), local env files, tool link
   directories, build caches. Run the project's bootstrap in
   the worktree — install dependencies into a worktree-local
   environment, re-pull env files — before any test or build.
   Never point a worktree at the primary tree's editable
   install or shared environment: tests in the worktree would
   silently import the primary tree's source.
3. **Hooks and config carry over.** `core.hooksPath` and the
   rest of the repo config are per-repository, so the
   pre-commit security gate and branch guard run in every
   worktree without setup. Confirm once per worktree with
   `git config core.hooksPath`.
4. **One conversation, one worktree.** Stage 6 still holds:
   each step (and each hotfix) is its own conversation, and a
   conversation never touches more than one worktree.
   Parallel steps run as parallel conversations, never as one
   conversation switching trees.
5. **Merge from the primary tree.** Run the Stage 4 merge
   command from the primary checkout. Inside a linked
   worktree, `--delete-branch` tries to check out `main`
   locally and fails (it is checked out in the primary tree);
   the merge itself still lands, but the local cleanup is
   left to Stage 5.
6. **Retire with the branch.** No worktree outlives its PR.
   Stage 5 removes it (`git worktree remove <path>`, then
   `git worktree prune`) BEFORE the branch prune, because
   `git branch -D` refuses a branch that is still checked out
   in a worktree. Between steps, `git worktree list` shows
   only the primary tree.

#### Release & tagging

| Milestone tag           | Marker                                |
|-------------------------|---------------------------------------|
| `v0.10.0-phase-1`       | <Phase 1 deliverable>                 |
| `v0.20.0-phase-2`       | <Phase 2 deliverable>                 |
| …                       | …                                     |
| `v1.0.0`                | <Production launch>                   |

### Release & deployment strategy

<!--
MANDATORY for any project with a deployed or published
surface — a web app, a service, a package on a registry,
scheduled automation, a database. Skip only for a library
with no runtime footprint, and say so explicitly if you do.
The point: the step lifecycle above ends at squash-merge, and
for a deployed surface the merge is NOT the finish line.
-->

**Merged is not deployed, and deployed is not released.**
Three distinct events with three distinct triggers. Name all
three for every surface this project ships, so no step can
mistake "the PR merged" for "the change is live".

#### Deployable surfaces

| Surface          | Environments          | Deploy trigger                          | "Released" means                          | Verify with                                  |
|------------------|-----------------------|-----------------------------------------|-------------------------------------------|----------------------------------------------|
| <Web app>        | <preview, production> | <merge to `main` auto-deploys>          | <production build serves the commit>      | <version/health endpoint reports the SHA>    |
| <Service>        | <staging, production> | <redeploy after the package floor bump> | <health endpoint reports the new version> | <authenticated request exercises the change> |
| <Package / CLI>  | <registry>            | <tagged release workflow>               | <version installable from the registry>   | <fresh install + smoke command>              |
| <Database>       | <staging, production> | <migration applied by <who/what>>       | <schema version matches the code's>       | <migration status query>                     |
| <Scheduled jobs> | <production>          | <merge to `main` (workflow file)>       | <next scheduled run succeeds>             | <run log + health alarm green>               |

Fill one row per real surface; delete the rest. A change that
lands in a surface whose deploy trigger is NOT "merge to
`main`" needs its own roadmap step (or an explicit sub-step)
for the release — never assume it happened.

#### Promotion path and cutovers

- Changes move <preview/staging → production>; promotion is
  gated on CI green plus the phase's verification checks
  passing against the pre-production environment.
- **Staged rollout.** When a step spans layers (infrastructure
  → pipeline → application, or schema → backend → frontend),
  deploy and verify each layer before starting the next. Never
  ship all layers in one push: a failure in layer three with
  layers one and two unverified has no clean rollback.
- **Readiness gate before an irreversible cutover.** A DNS or
  domain cut, a data migration with no down path, a key
  rotation, a public launch: each gets its own explicit
  readiness-gate sub-step in the roadmap with a checklist
  (access control, indexing/robots, monitoring in place,
  rollback rehearsed, attribution and legal), separate from
  the cutover step itself. Going live is a decision, not a
  side effect of a merge.

#### Configuration and secrets provisioning

- A step that introduces a required environment variable or
  secret verifies at step kickoff — before writing code that
  fails closed without it — that the value exists in EVERY
  target environment, using the platform's env listing.
- A shared secret (two systems must hold the same value) is
  proven by an **authenticated round-trip**: a real request
  from one system to the other that uses the secret. Listing
  env names or hitting an unauthenticated health endpoint does
  not prove the values match.
- Sensitive values never transit chat or a PR. Hand the
  operator a command to run, never a value to paste back.

#### Data and schema migrations

- Migrations are part of the deploy path, not the merge path.
  State who or what applies them to each environment, in what
  order relative to the code (expand → deploy code → contract),
  and how each is rolled back.
- A merged migration that has not been applied to production
  is a tracked gap, not a done step. Verify with the migration
  status query in the surfaces table.

#### Post-deploy verification

A step that touches a deployed surface is not done at merge.
Its acceptance criteria include a check in the target
environment, and Stage 4 of the step lifecycle runs it:

- The surface's version/health endpoint reports the expected
  build, and
- The changed behaviour is exercised end-to-end with real
  authentication, using a hands-off recipe the roadmap names
  (minted credentials, a rate-limit bypass token, a service
  probe) rather than an ad-hoc manual click-through.

Where a PR that references an issue auto-closes it on merge,
verification is what earns the close: if a gap remains after
the environment check, reopen the issue or open a follow-up.

#### Rollback

| Surface     | Rollback                                     | Time to execute |
|-------------|----------------------------------------------|-----------------|
| <Web app>   | <promote the previous deployment>            | <minutes>       |
| <Service>   | <pin the previous package version, redeploy> | <minutes>       |
| <Package>   | <yank + release a patch; consumers pin>      | <TBD>           |
| <Database>  | <down-migration or restore from snapshot>    | <TBD>           |

Every deploy has a named rollback the operator can run in
minutes; the PR body's "rollback plan" field (PR rule 2)
names which one. Reversible cutovers ship behind a switch (a
feature flag or environment variable) so rollback is a config
change, not a redeploy.

#### Versioning

Releases are tagged per the "Release & tagging" table above.
A consumer that pins a produced package declares a minimum
version floor and bumps it in its own step when a change must
reach it — the bump is the deploy trigger, not the merge.

### Security & privacy strategy

<!--
MANDATORY for any project that touches user data, secrets,
PII, credentials, payments, or auth. The point of this
section is that security is woven into EVERY step of every
phase — not bolted on at the end — so an issue introduced
while implementing a step is caught during development,
before the commit, push, and merge. Fill in the data
classification and the controls; keep the "Per-step security
gate" subsection intact — it is the mechanism the whole
roadmap relies on.
-->

#### Data classification

What sensitive data does this project touch, and how is each
class protected? Fill one row per class actually present;
delete rows that do not apply.

| Data class                     | Present? | Handling requirement                                  |
|--------------------------------|----------|-------------------------------------------------------|
| Client / user PII              | <Yes/No> | Encrypt in transit + at rest; least-privilege access; never in logs. |
| Authentication secrets / creds | <Yes/No> | Secrets manager only; never in source, env files, or client bundles. |
| API keys / service tokens      | <Yes/No> | Server-side only; rotate on exposure; scoped minimally.              |
| Payment / financial data       | <Yes/No> | Delegate to a PCI-compliant processor; never store PANs.            |
| Health / regulated data        | <Yes/No> | Meet the governing regime (HIPAA/GDPR/…); document the basis.       |

#### Threat model (one-paragraph)

<Name the assets worth protecting (the data classes above),
the trust boundaries from §3, the realistic adversaries
(external attacker, malicious insider, a compromised
dependency or CI action, a leaked coding-agent transcript),
and the top
3-5 abuse cases the design must resist. Keep it to a
paragraph plus the risk rows below.>

#### Per-step security gate

This is the core control. Every step of every phase runs the
SAME local, fail-closed security gate before any commit, so a
security issue introduced while implementing a step is caught
in development — before it reaches the branch, the PR, or
`main`. A coding agent handed a phase step must treat this
gate as part of the step's definition of done, exactly like
tests.

The gate is wired into the repo's pre-commit hook (`.githooks/`
+ `git config core.hooksPath .githooks`, or a `pre-commit`
framework config) so it runs automatically, and it is
re-run in CI so a bypassed hook cannot land an issue on `main`.
It has four checks; all must be clean:

| Check                | What it catches                                   | Example tooling                                        |
|----------------------|---------------------------------------------------|--------------------------------------------------------|
| Secret / PII scan    | Committed credentials, tokens, keys, real PII     | `gitleaks`, `detect-secrets`, `trufflehog`             |
| SAST (static a.)     | Injection, unsafe deserialization, weak crypto, path traversal | `bandit` (Py), `semgrep`, `eslint-plugin-security` (JS/TS) |
| Dependency audit     | Known-vulnerable / yanked / typo-squatted deps    | `pip-audit`, `npm audit --audit-level=high`, `osv-scanner` |
| Sensitive-data review| PII in logs, secrets in client bundles, over-broad scopes, missing encryption | Diff review against the data-classification table above |

Rules for the gate:

1. **Fail-closed.** Any finding blocks the commit. The bypass
   (e.g. an env var) is for genuine emergencies only and every
   use is recorded in the PR body with a justification.
2. **Runs per commit, not per phase.** Because it is a
   pre-commit hook, the developer/agent cannot defer security
   to "the end" — the smallest unit of work is already gated.
3. **Mirrored in CI.** The same four checks run as required
   status checks so the merge is blocked even if the local
   hook was skipped (PR rule 3).
4. **Owned by acceptance criteria.** Every phase's Acceptance
   criteria names the concrete security check for its surface;
   the phase is not "done" until the gate is green on its work.
5. **The pipeline is a trust boundary.** The gate is only as
   strong as the CI that mirrors it. Pin third-party actions
   to a commit SHA, grant each workflow the minimum
   `permissions:`, never expose secrets to workflows triggered
   by untrusted pull requests, put deploy and publish jobs
   behind a protected environment, and prefer short-lived
   OIDC credentials over stored long-lived tokens. A change to
   a workflow file is a security-relevant diff and gets the
   sensitive-data review.

#### Security controls by layer

<!-- Skip rows that do not apply. These are the standing
controls the design must carry, distinct from the per-commit
gate above. -->

| Layer               | Control                                                       |
|---------------------|--------------------------------------------------------------|
| Identity / auth     | <MFA, session policy, token lifetime, least-privilege roles> |
| Transport           | <TLS everywhere, HSTS, cert management>                       |
| Data at rest        | <Encryption, key management, backup encryption>              |
| Secrets             | <Manager (Vault/cloud KMS/keychain); never in source/env>    |
| Network / edge      | <WAF, rate limits, allow-lists, private networking>          |
| Dependencies        | <Pinned + audited; automated update + audit cadence>         |
| CI/CD pipeline      | <SHA-pinned actions; least-privilege permissions; OIDC publish; protected environments; no secrets on untrusted triggers> |
| Logging / audit     | <No PII/secrets in logs; tamper-evident audit trail>         |
| Incident response   | <Rotation runbook, disclosure path, on-call owner>           |

#### Vulnerability handling

Security findings — from the gate, CI, a scanner, or a report
— follow the same discover → triage → track → fix → verify
loop as any other defect, but jump the queue by severity:
Critical/High are fixed on a `hotfix/` or `fix/` branch before
new feature work continues; Medium/Low are tracked as issues
with an owner and a due date. Never silence a finding without a
recorded justification.

### Defect handling & triage

<!--
Keep this section. It generalises the discover → triage →
track → fix → verify loop from "Vulnerability handling" to
every finding a step surfaces, and it is what keeps PR rule 1
("one PR per step") true under pressure.
-->

Executing a step surfaces findings that are not the step: a
failing adjacent test, a wrong assumption in the step's own
spec, a gap an earlier step left, a product question, a lesson
about the process. Every finding is classified before it is
acted on, and each class has exactly one destination. Never
conflate classes in a single fix.

| Class                  | Definition                                                                                   | Destination                                                                                                            |
|------------------------|----------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| Spec rot               | The step's own prompt or spec was wrong (wrong API, wrong threshold, a prerequisite claimed but never done) | Edit the step's `<task>` block in the phase roadmap now, before the next conversation.                                  |
| Upstream gap           | An earlier step missed something that belonged to it                                         | Patch the earlier step's prompt so a re-run does not repeat it; add it to the phase's carry-over checklist.             |
| Implementation bug     | The code is wrong                                                                            | If it blocks this step's acceptance criteria, fix it in this step. Otherwise open an issue; fix on its own branch in a fresh conversation. |
| Architectural question | A broader product or design decision was exposed                                             | Open an issue for a future phase. Never fold it into the immediate fix.                                                |
| Process improvement    | A lesson about how the work is done                                                          | Record it where the next conversation will read it (this roadmap, the project's agent-instructions file). If it is a rule, make it a check. |
| Security finding       | Any of the four gate checks, or a threat-model abuse case                                    | Jumps the queue by severity — see "Vulnerability handling".                                                            |

Rules:

1. **Scope discipline.** A step's PR contains the step plus
   only the blocking fixes from the table. Everything else is
   tracked, not smuggled in. The PR body lists the issues it
   opened.
2. **Track before you defer.** A deferred finding exists as an
   issue with a class label, an owner, and the phase or step
   that will absorb it, before the current step is declared
   complete. "We'll remember" is not tracking.
3. **Verify the close.** A PR that references an issue with a
   closing keyword closes it on merge — the first such PR
   wins, even if it fixed only part. Verification in the
   target environment is what earns the close; reopen or open
   a follow-up if a gap remains.
4. **Prevent the class, not the instance.** Every defect that
   escaped a gate gets a guard in the same or the next step —
   a test, a lint rule, a CI check, a verify-script check — so
   the class cannot recur. The phase's QA findings doc records
   the finding and its guard together.
5. **Dispose before you declare.** The table above is the only
   place a finding may go. A step is not declared complete
   while any finding is merely described — in the chat, in a
   "follow-ups" note, in a "worth a glance" aside — rather than
   sitting at its destination. The completion line (Stage 6)
   is the last line of the response; a finding that would need
   to follow it means the step is not done yet.

### Operations & observability strategy

<!--
MANDATORY for any project that runs a service, scheduled
automation, or a published package that consumers depend on.
Skip for a library or CLI with no runtime footprint, and say
so explicitly if you do. The failure mode this section
prevents is silent failure: a cron that stopped running, a
deploy that never happened, a cost that ran unchecked.
-->

Every runtime surface is observable before it is considered
live, and every signal has an owner and a response.

#### Health signals

| Surface          | Signal                                       | Checked by                          | Alerts       |
|------------------|----------------------------------------------|-------------------------------------|--------------|
| <Service>        | <health endpoint reporting version + status> | <uptime probe + post-deploy check>  | <owner/chan> |
| <Scheduled jobs> | <last successful run within cadence>         | <health workflow that fails loudly> | <owner/chan> |
| <Web app>        | <error rate, latency, build status>          | <platform dashboard / alert rule>   | <owner/chan> |
| <Metered deps>   | <spend ledger vs cap>                        | <daily ledger check + hard cap>     | <owner/chan> |

#### Rules

1. **Version + health on every deployed surface.** The health
   endpoint reports the running version; post-deploy
   verification (see "Release & deployment strategy") reads
   it, and so does the uptime check.
2. **Scheduled automation has a heartbeat.** A job that runs
   on a schedule has an alarm that fires when it has NOT
   succeeded within its cadence. Detection without a consumer
   is not health: automation that opens PRs or issues has a
   named merge owner and a staleness policy (the newest
   supersedes older ones; the rest are closed).
3. **Metered dependencies have a ledger and a cap.** Any
   pay-per-use dependency (an AI API, a metered platform
   feature) records per-call cost to an audit ledger,
   enforces a hard cap with a kill switch, and shows the
   worst-case arithmetic in the cost projection above.
4. **Logs are safe by construction.** No PII or secrets in
   logs (see "Security controls by layer"); structured fields
   so an incident can be queried, not grepped.
5. **Every alert has a runbook.** An alert with no owner or
   no runbook is noise; delete it or complete it.

#### Runbooks

| Scenario                   | Runbook                                                  |
|----------------------------|----------------------------------------------------------|
| <Deploy regressed>         | <rollback per "Release & deployment strategy">           |
| <Scheduled job silent>     | <check the run log; re-run manually; fix the trigger>    |
| <Secret leaked / rotated>  | <rotation order + authenticated round-trip to confirm>   |
| <Upstream dependency down> | <degrade path; user-facing message; retry policy>        |

**Acceptance.** A phase that adds a runtime surface is not
done until the surface's health signal and its alarm exist
and have been seen to fire once (or a synthetic failure was
injected to prove they do). Put that in the phase's
acceptance criteria.

### Risks & mitigations

| Risk                                  | Mitigation              |
|---------------------------------------|-------------------------|
| <Risk 1>                              | <Mitigation>            |
| <Risk 2>                              | <Mitigation>            |
| <Risk 3>                              | <Mitigation>            |

---

## 6. Out of Scope

The following are deliberately deferred to a future version:

- <Deferred item 1>.
- <Deferred item 2>.
- <Deferred item 3>.

---

## 7. Glossary

<!-- Only include if the document uses domain-specific jargon. -->

| Term       | Meaning                                          |
|------------|--------------------------------------------------|
| <ACRONYM>  | <Definition>                                     |
| <ACRONYM>  | <Definition>                                     |

---

## 8. Phase Complexity Summary

<!--
The Status column mirrors each phase's `**Status:**` line and is
updated in the same commit (Stage 3 of the phase's first and
final steps). Values: Not started | In progress | Complete —
<YYYY-MM-DD>.
-->

| Phase | Description                       | Complexity   | Status      |
|-------|-----------------------------------|--------------|-------------|
| 1     | <Phase 1 title>                   | <Low/Med/Hi> | Not started |
| 2     | <Phase 2 title>                   | <Low/Med/Hi> | Not started |
| 3     | <Phase 3 title>                   | <Low/Med/Hi> | Not started |
| …     | …                                 | …            | …           |
