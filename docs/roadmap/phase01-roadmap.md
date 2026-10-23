# Phase 1 Roadmap — Reset & Foundation ✅

**Status:** Complete — 2026-10-08

## Overview

Phase 1 opens the gate every later phase stands on. Phase 2 cannot write
its first model until the repository has a clean `src/` package skeleton,
a locked toolchain, a fail-closed security gate, CI on Windows, macOS and
Linux, a rehearsed Trusted Publishing pipeline and accepted architecture
decisions — and the people already running 0.2.x cannot wait for any of
that to stop their FRED key reaching their logs. The phase ships no model,
no data provider, no documentation site and no hosted surface (Phases 2–5
own those), and it changes nothing in 0.2.x beyond the credential-logging
fix and the release pipeline that carries it. It is one phase because
every piece shares one precondition: nothing is deleted or rebuilt until
every byte of 0.2.x is preserved and its security patch is on PyPI.

The phase lands in 12 layers:

1. **Preserve 0.2.x and land the roadmaps** — commits the uncommitted
   0.2.x work in progress to `archive/0.2-dev-wip`, tags the heads of
   `dev` and `legacy-dev-0.2.6` as `archive/dev-2024-10` and
   `archive/legacy-dev-0.2.6`, and makes every `archive/` ref immutable
   with a ruleset. It lands `docs/roadmap/` and the roadmodel planning kit
   on `main` — the ledger every later step marks — protects `main`, and
   switches the repository to squash-only merges with branch auto-delete.
2. **Legacy credential-logging fix and hardened release pipeline** — cuts
   `legacy/0.2.x` from `v0.2.5`, removes the three DEBUG log statements in
   `FredClient.__new__` that print the FRED key, and adds a regression
   test. It replaces the branch's token-based `release.yml` with a
   SHA-pinned Trusted Publishing workflow behind `testpypi` and `pypi`
   environments, revokes the PyPI API token, and proves the pipeline by
   publishing `0.2.6.dev1` to TestPyPI with attestations.
3. **0.2.6 readiness gate** — `docs/releases/0.2.6-readiness.md`: access
   control, a file-by-file diff of the rehearsal artifacts against 0.2.5,
   the affected-version range read from every released sdist, the
   advisories against 0.2.x's pinned dependencies, a yank rehearsal on
   TestPyPI, a draft GitHub security advisory, and the maintainer's
   recorded go/no-go. Nothing is published.
4. **0.2.6 security release and advisory** — tags `v0.2.6` on
   `legacy/0.2.x`, publishes to PyPI behind the maintainer's approval,
   verifies a clean install with attestations, publishes the advisory, and
   re-points Read the Docs at `legacy/0.2.x` so the 0.2.x documentation
   survives Step 7.
5. **Characterize and archive 0.2.x** — records input-to-output fixtures
   for the four 0.2.x rules from the published 0.2.6 wheel under
   `tests/fixtures/legacy/` with a deterministic, network-blocked
   recorder; secret-scans and indexes the 44 local research files into a
   private archive repository; closes the 25 automated pull requests; and
   deletes `dev`, `legacy-dev-0.2.6` and every bot branch.
6. **Architecture decision records** — `docs/adr/` with ADRs 0001–0007,
   0009 and 0010 written from their recommended defaults and accepted or
   amended by the maintainer, plus the Phase 1 actions ADR-0009 triggers
   (domain registration and the move to a neutral GitHub organization).
7. **Repository reset and package skeleton** — removes 0.2.x from
   `main`; creates `src/pyeconomics/`, `tests/`, `docs/` and a `web/`
   placeholder; writes one PEP 621 `pyproject.toml` on the `uv_build`
   backend with `requires-python >=3.12`, the Apache-2.0 licence, PEP 735
   dependency groups and the ADR-0002 extras skeleton; commits `uv.lock`
   and an exported `pylock.toml`; exposes version `1.0.0.dev1` through
   `importlib.metadata`; and normalises text to LF.
8. **Per-step security gate** — prek pre-commit hooks running gitleaks,
   bandit, semgrep with project rules, `pip-audit --locked` and a licence
   allowlist, fail-closed; the same checks plus trufflehog, CodeQL,
   zizmor, harden-runner, OpenSSF Scorecard and dependency review in CI,
   required on `main`; secret scanning with push protection, Dependabot
   and private vulnerability reporting switched on.
9. **Quality toolchain** — ruff (strict, including the bandit, NumPy and
   pandas rule families), mypy strict with the pydantic plugin, pyright
   for editors, ty as a non-blocking check, and pytest with hypothesis,
   syrupy, pytest-benchmark, branch coverage, pytest-socket and doctests,
   all wired into prek.
10. **CI/CD and publishing rehearsal** — `ci.yml` (lint, types and tests
    on Ubuntu, Windows and macOS across Python 3.12–3.14, a package smoke
    test, lockfile, PR-title and DCO checks, and an aggregate `test`
    gate), the 1.x `release.yml` with a reusable `release-smoke.yml`, SHA
    pinning enforced by repository policy, required checks on `main`, and
    `v1.0.0.dev1` published to TestPyPI only.
11. **Governance, community and agent instructions** — README,
    CONTRIBUTING, CODE_OF_CONDUCT, SECURITY.md, CHANGELOG, CITATION.cff,
    CODEOWNERS, issue forms, defect-class labels, `AGENTS.md` and
    `CLAUDE.md`, and the Gate G1 funding hooks (GitHub Sponsors,
    thanks.dev, `funding.json`).
12. **QA + `verify-phase01.sh`** — `scripts/verify-phase01.sh` (`--fast`,
    `--python`, `--security`, `--live`, `--all`, `--post`),
    `docs/phase01-qa-findings.md`, and the first
    `.github/workflows/phase-verify.yml` matrix entry — together the
    precedent every later phase copies.

The ship test for Phase 1 is straightforward: 0.2.6 is on PyPI with
attestations and without any credential logging, and a published GitHub
security advisory names the affected and fixed versions and the
key-rotation advice; `archive/0.2-dev-wip`, `archive/dev-2024-10` and
`archive/legacy-dev-0.2.6` exist on `origin` with the work-in-progress
diff intact, and the `dev/` research sits in a private archive with a
clean secret scan and an index; characterization fixtures for the four
0.2.x rules are committed and re-record byte-identically; `uv sync
--locked` and the full test run pass in CI on Ubuntu, Windows and macOS
for every supported Python, and `uv build` produces a wheel and an sdist
that pass `twine check --strict`; `v1.0.0.dev1` reached TestPyPI through
Trusted Publishing with attestations and installs in a clean venv
reporting its version, and no PyPI API token exists in the repository or
the PyPI account; a direct push to `main` is rejected, `git branch -r`
lists only `origin/main`, `origin/legacy/0.2.x` and archive branches, and
ADRs 0001–0007, 0009 and 0010 are merged as Accepted; the pre-commit gate
blocks a planted fake credential and a `pickle.loads` call, the same
checks are required status checks on `main`, zizmor reports nothing above
Low, CodeQL and Scorecard run on `main`, and secret scanning with push
protection and private vulnerability reporting are on; and
`scripts/verify-phase01.sh --fast` exits 0 on Ubuntu CI with the
`phase-verify.yml` matrix entry `01` green.

**Pre-requisite:** No earlier phase exists, so there is no prior phase
roadmap to carry forward. The project roadmap (`docs/roadmap/ROADMAP.md`,
Draft v1) and the roadmodel planning kit (`planning/`) exist only in the
maintainer's working tree until Step 1 lands them on `main`. The operator
holds admin on the GitHub repository, owner rights with 2FA on the PyPI
project `pyeconomics`, a TestPyPI account (Step 2 creates one if absent)
and admin on the Read the Docs project; the GitHub CLI is authenticated
with the `repo` and `workflow` scopes.

**Dependency:** Phase 2 does not start until V1–V12 are green and all
nine ADRs read Accepted: its model registry is written into Step 7's
`src/` skeleton, gated by Step 8's security checks and Step 9's strict
toolchain, run by Step 10's CI matrix, and released as `1.0.0a1` through
Step 10's rehearsed pipeline — the first real PyPI upload of 1.0, which
gets its own readiness gate in Phase 2. Phase 3 inherits Step 5's
characterization fixtures as the contract its rebuilt policy rules must
match or explicitly diverge from.

**Design rationale (patch, preserve, decide, then rebuild).** The order
inside the phase is the design. People running 0.2.x are exposed today,
so the security patch ships before any rebuild work (Steps 2–4). Nothing
is deleted until everything is preserved: the work in progress and the
unreleased branches become immutable archive refs (Step 1), the released
line becomes `legacy/0.2.x` (Step 2), and the rules' behaviour becomes
fixtures while the local research becomes a private archive (Step 5).
Decisions precede the code that encodes them: the ADRs (Step 6) fix the
licence, the Python floor, the extras and the versioning scheme before
Step 7 writes them into `pyproject.toml`. Only then does `main` lose
0.2.x.

**Bootstrap rule.** Phase 1 builds the guardrails its own lifecycle
assumes, so the lifecycle tightens step by step rather than all at once.
Step 1 protects `main` — pull request required, `enforce_admins: true`,
linear history, no force-push or deletion — with no required status
checks, because none exist yet. Until Step 8 wires the pre-commit gate,
every step runs the four security checks by hand before each commit (the
commands are in each step's `<security>` block) and pastes their summary
lines into the PR body. Each step that creates a CI check adds it to
`main`'s required checks only after it has reported green once: the
gate's checks in Step 8, the CI, package, lockfile, PR-title and DCO
checks in Step 10, and the `phase-verify.yml` entry in Step 12. The 0.2.x
`pytest` and `sphinx` workflows still trigger on pull requests to `main`
until Step 7 deletes them along with the token-based `release.yml`; they
are not required and their results gate nothing.

**Legacy-branch rule.** Steps 2 and 4 change `legacy/0.2.x`, not `main`,
but the ledger lives on `main`. Each of those steps therefore runs two
branches and two pull requests: a work branch cut from
`origin/legacy/0.2.x` (`fix/legacy-0.2.6-credential-logging` in Step 2,
`release/v0.2.6` in Step 4) whose PR targets `legacy/0.2.x`, and the step
branch named on its `**Branch:**` line, cut from `main` at Stage 1 as
always, whose PR carries the Stage-3 Status mark and any `main`-side
record. Both are squash-merged, and the step is complete only when both
have merged. `legacy/0.2.x` takes security fixes only, never merges into
`main`, and reaches end-of-life when 1.0.0 ships (ADR-0003).

**Branch strategy.** Every step in this phase lands on its own
short-lived feature branch (`feature/phase01-step<M>-<slug>`), opens a
pull request against `main`, waits for the project's CI workflow to go
green, and squash-merges with a Conventional Commits subject line.
Direct pushes to `main` are blocked by branch protection from Step 1
onward. See the parent project's ROADMAP "Branch management strategy"
section for the canonical naming convention, PR rules, and release
tagging — this paragraph confirms those rules apply unchanged within this
phase, with the Bootstrap rule's staging of required checks and the
Legacy-branch rule's second pull request in Steps 2 and 4. Per-step
branches are listed on each step header below as `**Branch:**` so
reviewers can map commits 1:1 to the step they implement.

**Branch-first execution rule.** The very first action of every step —
before reading any files, before running any tool, before drafting any
change — is to check out the branch named in that step's `**Branch:**`
line:

```sh
git checkout -b feature/phase01-step<M>-<slug>
```

This is non-negotiable. `main` is protected with `enforce_admins: true`
from Step 1 onward, so a commit on `main` cannot be pushed and must be
rewound or rebased onto the feature branch before the PR can open — an
avoidable round-trip. If you discover mid-step that you started on
`main`, recover by running the same `git checkout -b` command immediately
(uncommitted changes carry over to the new branch), then continue. AI
coding agents executing a step from this roadmap must treat the branch
checkout as Step 0 of every step. Step 1 is the one exception, because
its tree starts dirty and on `dev`: its first action is the preservation
branch `git switch -c archive/0.2-dev-wip`, and its own Stage 1 follows
as soon as the work in progress is safe (Step 1, first requirements).

**Worktree rule.** One working tree, one step in flight — the lifecycle
below assumes the primary checkout. A second working tree is created only
with `git worktree add`, and only for the three cases the parent ROADMAP
"Worktree strategy" sanctions: a `hotfix/` branch interrupting this step
(cut from `origin/main` in its own worktree so this step's tree is
untouched); steps the Execution Order below explicitly draws in parallel
(each in its own worktree AND its own conversation); and
worktree-isolated subagents inside a step (throwaway trees that merge
back into the step branch locally and are removed before the PR opens).
In those cases Stage 1 becomes `git fetch origin && git worktree add -b
feature/phase01-step<M>-<slug> <worktree-path> origin/main`, the worktree
is bootstrapped before any test or build (fresh dependency install and
env files — a worktree has none of the primary tree's untracked state,
and it must never borrow the primary tree's editable install), the Stage
4 merge runs from the primary tree, and Stage 5 removes the worktree
BEFORE pruning the branch. Undeclared parallelism is a lifecycle
violation, not a shortcut. Worktree location for this project:
git-ignored `.worktrees/<branch-slug>/` inside the repository, matching
the parent ROADMAP (Step 1 adds `.worktrees/` to `.gitignore`).

**Security-first execution rule.** Security is not a phase — it is a
gate on every commit of every step. Before each `git commit`, the step's
work must pass the local, fail-closed security gate: secret/PII scan
clean, SAST clean, dependency audit clean, and a diff review confirming
no sensitive data (PII, credentials, tokens) and no new insecure pattern
(injection, weak crypto, over-broad scope, secret in a client bundle or
log line). From Step 8 this gate is wired into the pre-commit hook and
re-run in CI, so a security issue introduced while implementing a step is
caught during development — before it reaches the branch, the PR, or
`main`; Steps 1–7 run the same four checks by hand (Bootstrap rule). See
the parent project's ROADMAP "Security & privacy strategy" → "Per-step
security gate" for the canonical checks and tooling; each step's XML
`<task>` carries a `<security>` block restating them for the agent, and
each step's Acceptance Criteria ends with a security check. AI coding
agents executing a step MUST treat the security gate as part of the
step's definition of done, exactly like its tests. This matters most in a
phase that handles the maintainer's FRED and OpenAI keys and the PyPI
publishing credential: the operator running a step's prompt must not be
able to introduce a data-exposure risk that only surfaces after merge.

**Deploy-and-verify rule.** Merged is not deployed, and deployed is not
released. Every step header carries a `**Deploys:**` line naming the
surface and environment the step's merge reaches — or `nothing beyond
merge` — and when going live needs a release, a version-floor bump, a
migration, or a redeploy, the line says so and this step (or a named
follow-on step) owns that event. For a step whose Deploys line names a
surface, Stage 4 of the lifecycle does not end at the squash-merge: the
step's acceptance criteria carry a **Deployed & verified** bullet (the
surface's version/health endpoint reports this build, and the changed
behaviour is exercised in the target environment with real
authentication via the hands-off recipe the step names), and that bullet
must be green before the step is declared complete. In Phase 1 the
surfaces are TestPyPI (Steps 2 and 10) and PyPI plus the published
security advisory (Step 4); their hands-off recipe is a clean-venv
install of the exact version and the provider's integrity API. A step
that introduces a required environment variable or shared secret
verifies at kickoff that it exists in every target environment and
proves shared values by an authenticated round-trip — never by listing
env names. See the parent ROADMAP "Release & deployment strategy" for the
surfaces table, promotion path, staged-rollout rule, migrations, and
rollback.

**Triage rule.** Findings surfaced while executing a step are classified
before they are acted on, per the parent ROADMAP "Defect handling &
triage": spec rot → edit this roadmap's affected `<task>` block now;
upstream gap → patch the earlier step's prompt and add it to the
carry-over checklist (the last list in this file's Not-in-scope
section); implementation bug → fix in-step only if it blocks
this step's acceptance criteria, otherwise an issue and its own branch in
a fresh conversation; architectural question → an issue for a future
phase; process improvement → recorded where the next conversation will
read it; security finding → jumps the queue by severity. A step's PR
contains the step plus blocking fixes only, and lists the issues it
opened. When a merged PR auto-closes an issue, the environment check is
what earns the close — reopen or follow up if a gap remains.
`docs/phase01-qa-findings.md` is the rollup: every finding, its class,
and the guard added so the class cannot recur. Until Step 11 creates the
defect-class labels, issues carry their class as the first word of the
title (`[spec-rot]`, `[bug]`, …) and Step 11 relabels them.

**Status rule.** Every step carries a `**Status:**` line directly under
its `## Step N — …` heading, before the Goal, and this file on `main` is
the ledger of what is done — never a chat transcript, never a later
conversation reconstructing history from `git log`. The line reads `Not
started` when this roadmap is written and is flipped by the step's OWN
pull request: at Stage 3, right after `gh pr create` returns the PR
number, the agent sets it to `Complete — PR #<n> (<YYYY-MM-DD>)`, appends
` ✅` to the step's heading (`## Step 3 — 0.2.6 Readiness Gate ✅`) so the
completion shows in the rendered preview, the outline, and the table of
contents, sets the step's Summary Table Status cell to `Complete — PR
#<n>`, commits that edit on the step branch, and pushes. The PR therefore
carries its own completion mark, and the roadmap on `main` says a step is
complete exactly when that step's PR merges — never before. This file's
phase-level `**Status:**` line (under the title) and the parent project
roadmap are marked the same way, in the same commit: Step 1's PR flips
both from `Not started` to `In progress` (the parent's `### Phase 1`
line reads `In progress — phase01-roadmap.md`), and the final step's PR
flips both to `Complete — …` (the parent's with its row in the "Phase
Complexity Summary" table and the header `> **Status:**` line) and
appends ` ✅` to this file's `# ` title and to the parent's `### Phase 1`
heading, so the project roadmap shows a finished phase the way this file
shows a finished step. There is no separate "update the roadmaps" chore:
a step whose PR merged without its Status line is a lifecycle violation,
and the next step's Stage 1 (and `/roadmap-step`) refuses to start until
the previous step reads `Complete`. If a post-merge check fails — a
Deployed & verified bullet, an alarm that never fired — the step is NOT
complete despite the merged line; say so, and the `hotfix/` PR that
completes it appends its own number to the line. In Steps 2 and 4 the
Status mark rides on the `main`-side PR (Legacy-branch rule).
`grep -n '^\*\*Status:\*\*'` on this file is the phase's progress report,
and the ✅ headings are the same report at a glance.

**Step lifecycle.** Every step in this phase follows the exact same
six-stage lifecycle, in order, with no exceptions. Each stage is a hard
checkpoint — if a stage is skipped, branch protection or the next step's
Stage 1 will fail loudly, and that is the safety net. AI coding agents
MUST execute all six stages before declaring a step complete.

1. **Create the branch.** Before any Read / Edit / Bash, run
   `git checkout -b feature/phase01-step<M>-<slug>` from a clean,
   up-to-date `main`. The exact branch name comes from this step's
   `**Branch:**` line. When the Worktree rule applies, the equivalent is
   `git fetch origin && git worktree add -b <branch> <worktree-path>
   origin/main`, followed by the worktree's bootstrap.

2. **Work on the branch, passing the security gate before every
   commit.** All commits land here. Never push to `main` directly —
   branch protection (`enforce_admins: true`) rejects it. Before each
   `git commit`, run the local security gate (secret/PII scan, SAST,
   dependency audit, sensitive-data diff review — see the step's
   `<security>` block and the parent ROADMAP "Per-step security gate").
   It is fail-closed: a finding blocks the commit, so a security issue in
   this step's work is caught here, before the PR and before `main`.

3. **Open the PR, then mark the step.** `gh pr create --base main --head
   <branch>` with a Conventional Commits title and a body that references
   this roadmap step and its acceptance criteria. One PR per step; never
   bundle two steps into one PR (Steps 2 and 4 add their legacy-side PR
   under the Legacy-branch rule). Then, with the PR number in hand, set
   this step's `**Status:**` line (directly under its heading) to
   `Complete — PR #<n> (<YYYY-MM-DD>)`, append ` ✅` to the step's `##
   Step` heading, set its Summary Table Status cell to `Complete — PR
   #<n>`, commit that edit on the step branch (`docs: mark Phase 1 Step M
   complete`), and push — the PR now carries its own completion mark, so
   the roadmap on `main` will say the step is complete exactly when the
   PR merges (Status rule). On the phase's first step, the same commit
   sets this roadmap's phase-level `**Status:**` (under its title) and
   the parent project roadmap's Phase 1 `**Status:**` to `In progress`;
   on the final step, both to `Complete`, with ` ✅` appended to this
   roadmap's `# ` title and to the parent's `### Phase 1` heading.

4. **Wait for green checks, then squash-merge.** Every required status
   check must report success — the set this phase grows step by step
   under the Bootstrap rule, ending with lint, types, the test matrix's
   aggregate `test` gate, package, lockfile, PR-title, DCO, the security
   checks, and the `phase-verify.yml` matrix entry for this phase. If the
   PR goes BEHIND main while waiting, refresh with `gh pr update-branch
   --rebase` — never merge `main` into the branch;
   `required_linear_history: true` enforces rebase. Once every check is
   green:

   ```sh
   gh pr merge <PR_NUMBER> --squash --delete-branch
   ```

   If this step's `**Deploys:**` line names a surface, the merge is not
   the finish line: run the Deployed & verified check from the
   acceptance criteria against the target environment now (see the
   Deploy-and-verify rule) before declaring the step complete.

5. **Retire the branch (remote + local).** The `--delete-branch` flag
   plus the repo's `delete_branch_on_merge: true` setting retire the
   remote automatically. Sync local state and prune the merged branch
   plus any other `[gone]` labels left over from prior PRs:

   ```sh
   git switch main
   git pull --ff-only origin main
   git fetch --prune origin
   git branch -vv | grep ': gone]' | awk '{print $1}' \
     | xargs -r git branch -D
   ```

   If this step ran in its own worktree, remove it FIRST —
   `git worktree remove <worktree-path>`, then `git worktree prune` —
   because `git branch -D` refuses a branch still checked out in a
   worktree. Confirm with `git branch -vv` that only `main` and any
   intentional long-lived branches remain locally, and with `git worktree
   list` that only the primary tree remains.

6. **Dispose of every finding, declare completion, then new
   conversation.** Before you declare anything, walk the findings this
   step surfaced and send each to its destination per the Triage rule
   above — a note that a later step needs is edited into that step's
   `<task>` block now; a wrong claim in this step's spec is fixed in this
   roadmap now; an implementation bug is fixed in-step or exists as an
   issue with a number; a judgement call you made in the diff is
   explained in the PR body; a process lesson is written where the next
   conversation reads it. A finding you can only *describe* has not been
   disposed of, and an undisposed finding is an unmet acceptance
   criterion. Only once the PR is merged — and `main` therefore carries
   this step's `Complete` Status line — every acceptance criterion is
   affirmatively met, and every finding has a destination, say so
   plainly: end your final response with an explicit, unhedged
   completion line — verbatim shape "Step M is complete. You can now move
   on to Step M+1." — so the operator has a clean stopping point at which
   to close this conversation. That line is the LAST line of the
   response. Nothing follows it: no "Follow-ups (non-blocking)", no
   "Notes", no "Next", no "worth a glance", no suggested improvements. If
   you want to show your work, a short ledger may PRECEDE the line, one
   entry per finding naming its destination (an issue number, a file you
   edited, the PR body) — never an open item. If any acceptance criterion
   is NOT met, or any finding has no destination yet, do the opposite —
   state plainly that the step is NOT complete, name what is
   outstanding, and do not emit the completion line. "Done" means done,
   not "done, but here is what you still have to do". Then, for
   phase-boundary hygiene, the operator closes this Claude Code / Cursor
   / Codex session and opens a fresh one before starting Step M+1; the
   new conversation begins again at Stage 1 of this lifecycle, with the
   next step's `**Branch:**` line driving the `git checkout -b` command.
   No work straddles two steps.

---

## Current State (as of 0.2.x, before Phase 1)

### Repository and branch surface

- The maintainer's checkout sits on `dev` at
  `d4a692d7c76c75119c98dbc980d0ec5454a8fa05` (equal to `origin/dev`) with
  uncommitted 0.2.x work in progress that exists on no branch:
  `pyeconomics/ai/taylor_rule.py` (+123/−61, the OpenAI v1 client),
  `pyeconomics/api/openai_api.py` (+7/−3), `pyeconomics/utils/utils.py`
  (+16/−12, Bloomberg `ECCCUS`/`ECUPUS` consensus-forecast tickers),
  `requirements.txt` (+1, the `git+https://github.com/PaulMest/tia.git`
  dependency PyPI rejects) and two regenerated plots,
  `media/gaps_plot.png` and `media/taylor_rule_plot.png`. The same tree
  holds a four-line `.gitignore` change and the untracked `docs/roadmap/`
  and `planning/` directories, which belong to the 1.0 rebuild rather
  than to 0.2.x. Step 1 preserves the first set and lands the second.
- `origin/main` is `v0.2.5` (`ad494c1c1a2f0d052561cd0dd94c92f5279ac8d0`,
  2024-05-30); `origin/dev` is 34 commits ahead and never released; and
  `origin/legacy-dev-0.2.6` (`2b7e8a6e1dd3dbc11b4a8e395e8679fe31487d15`)
  is a third unreleased line. Tags `v0.2.0`–`v0.2.5` exist. The remote
  also carries 24 `snyk-fix-*` branches and one Dependabot branch behind
  25 open pull requests (#18–#45; 24 Snyk, 1 Dependabot). The default
  branch is `main`.
- Nothing is protected: `main` has no branch protection, the repository
  has no rulesets and no deployment environments, it allows merge, rebase
  and squash merges, and `delete_branch_on_merge` is off. The `archive/`,
  `legacy/` and `feature/` prefixes are unused, and no worktree exists.
- Local-only, git-ignored content that exists nowhere else: `dev/` (44
  research files plus 35 notebook checkpoints, 76 MB — quantity-of-money
  and DCF prototypes, Bitcoin factor work, stock-to-flow variants),
  `generate_tests.py`, `render_readme.py` and `output.html` at the root,
  `cache/` (pickled FRED responses, 7.3 MB) and `.env` (FRED and OpenAI
  keys). `planning/user-context.md` is ignored only by the uncommitted
  `.gitignore` change. Because a `dev/` directory exists, `git log dev`
  is ambiguous in this checkout — write `origin/dev` or `dev --`.

### Package and build surface

- `setup.py` builds the package: it reads the version from the root
  `__version__.py` (`0.2.5` on `main`, `0.2.6` on `dev`), copies
  `install_requires` verbatim from `requirements.txt` — so pytest,
  sphinx, jupyterlab and setuptools ship as runtime dependencies — and
  sets `python_requires='>=3.11, <3.13'` at `v0.2.5`. `pyproject.toml` is
  a stub (setuptools backend plus pytest options); `pytest.ini`,
  `.coveragerc` (an 80% floor), `MANIFEST.in`, `.readthedocs.yml`, the
  JupyterLab `Dockerfile`, `.dockerignore` and `start.sh`, and the
  tracked `test_import.py` sit at the root. There is no lockfile.
- PyPI holds 0.1.0 and 0.2.0–0.2.5, all uploaded in May 2024, with
  `requires_python <3.13,>=3.11` and no licence metadata; 0.2.6 was never
  published. TestPyPI has no `pyeconomics` project, so its first
  publisher must be a pending publisher.
- `.gitattributes` holds `* text=auto` only, so CRLF working copies
  produce warnings; `.editorconfig` exists; `.gitignore` ignores `*.csv`
  and `*.json` everywhere, which would silently drop JSON test fixtures.
- The target layout (`src/pyeconomics/`, `uv_build`, PEP 735 groups,
  `uv.lock`, `pylock.toml`) does not exist; Step 7 creates it under the
  decisions ADR-0002, ADR-0003, ADR-0004 and ADR-0010 fix in Step 6.

### Legacy code surface (0.2.5)

- `pyeconomics/api/fred_api.py` at `v0.2.5` writes the FRED key to the
  log at DEBUG in `FredClient.__new__` — lines 75–76 (the key from the
  argument or `FRED_API_KEY`), 82–83 (the key from the keyring) and 91
  (`Using API Key`) — and the module builds `fred_client = FredClient()`
  at import, so importing the package without a key raises `ValueError`.
  Every 0.2.x release on PyPI ships the bug; whether 0.1.0 does is TBD
  until Step 3 reads its sdist.
- The four rules are `taylor_rule`, `balanced_approach_rule` (with and
  without `use_shortfalls_rule`) and `first_difference_rule` in
  `pyeconomics/models/monetary_policy/`, plus the combined
  `calculate_policy_rule_estimates`. Each takes an `EconomicIndicators`
  dataclass (`pyeconomics/data/economic_indicators.py`) and a parameters
  dataclass (`pyeconomics/data/model_parameters.py`: `inflation_target`,
  `alpha`, `beta`, `okun_factor`, `rho`, `elb`, `apply_elb`, `verbose`),
  fetches any indicator left `None` from FRED through `fred_client`, and
  returns a value rounded to 2 dp. The `historical_*` variants always
  fetch whole series and return rounded DataFrames. Step 5 characterizes
  all of them.
- `pyeconomics/api/cache_manager.py` pickles FRED responses into a
  `cache/` directory computed from the module path and created at import
  time. 0.2.6 leaves it alone (security-only scope); Phase 3 replaces it.

### CI/CD and publishing surface

- Three workflows exist on every branch: `tests.yml` (pytest on Python
  3.11–3.12 at `v0.2.5`, 3.10–3.12 on `dev`; it echoes the dummy keys it
  sets and uploads to Codecov with `CODECOV_TOKEN`), `docs.yml` (a Sphinx
  build) and `release.yml`, which publishes on every `v*` tag with the
  long-lived `PYPI_API_TOKEN` through `pypa/gh-action-pypi-publish@v1.4.2`
  and `python setup.py sdist bdist_wheel` in a three-version matrix, after
  writing the tag's version into `pyeconomics/__version__.py` — a file
  `setup.py` never reads, so a tag and its package can disagree.
- Every action is pinned by tag, no workflow declares `permissions:`, and
  all three workflows are active. Repository secrets: `PYPI_API_TOKEN`
  and `CODECOV_TOKEN` (both 2024-05-21). The last Actions runs were Snyk
  pull-request checks in January–February 2026.
- GitHub Actions runs a workflow from the tagged commit, so a `v*` tag
  pushed at any old commit would run the token-based `release.yml` while
  the secret exists — the reason archive refs use the `archive/` prefix
  and the reason Step 2 revokes the token before its first tag.

### Security and sensitive-data surface

- Sensitive data in play this phase: the maintainer's FRED and OpenAI
  keys in the local `.env` (git-ignored, never committed); the PyPI API
  token (a repository secret, live on PyPI until Step 2); the Codecov
  token (until Step 10); the GitHub CLI token in the maintainer's shell
  environment; and Bloomberg-licensed output that may sit in `dev/`
  notebooks and in the regenerated plots. None of it may reach a commit,
  a log, a PR, a chat transcript or the public repository.
- History is clean: no key-shaped string appears in any commit on any
  branch (assessed 2026-10-03). There is no secret scan, SAST or
  dependency audit locally or in CI; GitHub secret scanning, push
  protection, Dependabot alerts and security updates and private
  vulnerability reporting are all off; Snyk is connected and opens pull
  requests.
- Tools already on the maintainer's machine: gitleaks 8.30.1 (winget),
  pre-commit 3.8.0, uv 0.12.15, Docker, and GitHub CLI 2.76.2
  authenticated with the `repo` and `workflow` scopes. Every step that
  touches a credential mirrors one pattern: the operator enters secrets
  in the provider's own UI, never in chat or a file, and the agent
  verifies by name or by an authenticated round-trip — never by printing
  a value, the environment, or `gh auth token`.

### Operations and observability surface

- No runtime surface exists and nothing reports health. Phase 1 adds one
  surface — package publishing to TestPyPI and PyPI — whose health
  signal is the post-publish smoke job (a fresh-venv install of the exact
  version, a version check, and for 0.2.x the credential-logging check).
  Step 2 builds it into the legacy `release.yml`; Step 10 builds it as
  the reusable `release-smoke.yml` for 1.x. The alarm is GitHub's
  failed-workflow notification to the maintainer, and Step 12 proves it
  fires with a synthetic failure.
- Phase 1 also adds scheduled automation — CodeQL and Scorecard weekly,
  Dependabot weekly — whose failures reach the maintainer the same way.
  Rollback for the publishing surface is a PyPI yank followed by a fixed
  patch release (ROADMAP §5 "Rollback"); Step 3 rehearses the yank on
  TestPyPI.

### Documentation and governance surface

- `README.md` is the PyPI long description: a badge table pointing at
  Codecov, Code Climate, libraries.io, Snyk and the 0.2.x workflows, and a
  "Roadmap" section holding the 2024 wishlist. The Sphinx sources and the
  wishlist pages (`docs/roadmap*.rst`, `docs/create_roadmap_files.bat`)
  build on Read the Docs from `main`; Phase 7 reads the wishlist from
  `legacy/0.2.x` once Step 7 removes it from `main`.
- `markdown/` holds CHANGELOG, CODE_OF_CONDUCT, CONTRIBUTING and the
  0.2.x FRED configuration guide; `CITATION.cff` still says 0.2.0;
  `LICENSE` is MIT with "Nathan Ramos, CFA®", and 123 commits carry the
  git author name "Nathan Ramos, CFA®" — CFA Institute's rules put no ®
  after a name. There is no SECURITY.md, CODEOWNERS, issue form, PR
  template, label scheme, `AGENTS.md` or `CLAUDE.md`.
- `docs/roadmap/ROADMAP.md` (Draft v1) and this file are untracked until
  Step 1; `docs/adr/` and `docs/releases/` do not exist.

### Verification surfaces

- No `scripts/verify-phase*.sh` exists: Phase 1 is the first phase, so
  Step 12 writes the first verify script and sets the precedent later
  phases copy. Its mode contract fits a Python project — `--fast`,
  `--python`, `--security`, `--live`, `--all`, `--post` — in place of the
  template's `--swift`, `--node` and `--ui` modes, which a later phase
  adds only if it brings those stacks (`web/` arrives in Phase 5).
- `.github/workflows/phase-verify.yml` does not exist; Step 12 creates it
  with matrix entry `01`, the first entry later phases append to.

---

## Execution Order

```
Step 1  (preserve + bootstrap)        archive/0.2-dev-wip, archive tags,
                                      roadmaps on main, main protected
                                      → implement
  ↓
Step 2  (legacy fix + pipeline)       legacy/0.2.x, credential-log fix,
                                      Trusted Publishing, 0.2.6.dev1 on
                                      TestPyPI → implement
  ↓
Step 3  (0.2.6 readiness gate)        docs/releases/0.2.6-readiness.md,
                                      draft advisory, GO / NO-GO
                                      → implement
  ↓
Step 4  (0.2.6 release)               v0.2.6 on PyPI, advisory public,
                                      Read the Docs on legacy/0.2.x
                                      → operate
  ↓
Step 5  (characterize + archive)      tests/fixtures/legacy/, private
                                      research archive, PRs and
                                      branches retired → implement
  ↓
Step 6  (ADRs)                        docs/adr/ 0001-0007, 0009, 0010
                                      Accepted; domains; org move
                                      → implement
  ↓
Step 7  (reset + skeleton)            src/ layout, pyproject on
                                      uv_build, uv.lock + pylock.toml
                                      → implement
  ↓
Step 8  (security gate)               prek gate, security workflows,
                                      GitHub security settings
                                      → implement
  ↓
Step 9  (quality toolchain)           ruff, mypy strict, pytest stack,
                                      prek hooks → implement
  ↓
Step 10 (CI/CD + rehearsal)           ci.yml, release.yml,
                                      release-smoke.yml, 1.0.0.dev1 on
                                      TestPyPI → implement
  ↓
Step 11 (governance)                  community files, AGENTS.md and
                                      CLAUDE.md, labels, funding
                                      → implement
  ↓
Step 12 (QA + verify-phase01.sh)      scripts/verify-phase01.sh
                                      + docs/phase01-qa-findings.md
                                      + phase-verify.yml matrix entry
                                      → create

--- post-implementation ---

V1   Archive refs exact and immutable; roadmaps and kit on main; main
     protected; squash-only merges.
V2   legacy/0.2.x logs no credential; the hardened pipeline published
     0.2.6.dev1 to TestPyPI with attestations; no PyPI token exists.
V3   Readiness checklist evidenced, with the maintainer's GO.
V4   0.2.6 installs from PyPI with attestations; advisory published;
     Read the Docs serves 0.2.x from legacy/0.2.x.
V5   Fixtures re-record byte-identically from 0.2.6; research archived
     privately with a clean scan; only main, legacy/0.2.x and archive
     branches remain; no automated PR open.
V6   Nine ADRs Accepted; ADR-0009 actions done or amended.
V7   0.2.x gone from main; uv sync --locked, uv build and twine check
     pass; artifacts hold only allowlisted paths.
V8   The gate blocks a planted credential and pickle.loads; CI mirrors
     it as required checks; GitHub security settings on.
V9   ruff, mypy strict and pytest (sockets off, doctests on) pass.
V10  CI green on 3 OS x 3 Pythons; 1.0.0.dev1 on TestPyPI with
     attestations; required checks set; SHA pinning enforced.
V11  Community files, labels, agent instructions and G1 funding live.
V12  verify-phase01.sh --fast and --security exit 0 in phase-verify.yml;
     the release-smoke alarm was seen to fire.
```

Steps are sequential by dependency. Step 1 must preserve the work in
progress before any checkout moves the tree, and must land the roadmaps
on `main` before any step can mark itself there. Steps 2–4 put the patch
in users' hands before anything else changes, and Step 4 re-points Read
the Docs before Step 7 deletes the Sphinx sources from `main`. Step 5
records fixtures from the PyPI wheel Step 4 publishes, and retires `dev`
only after Step 1's archive tags exist. Step 6's accepted ADRs fix the
licence, Python floor, extras and versioning that Step 7 writes into
`pyproject.toml`, and its organization move must precede Step 10's
publisher-bound rehearsal. Step 8's `pip-audit --locked` needs Step 7's
lockfile; Step 9 adds its hooks to Step 8's prek configuration; Step 10's
CI runs Step 9's toolchain and Step 8's gate; Step 11 documents the
finished pipeline and gate; Step 12 is sequential after every prior
step. No steps are drawn in parallel, so the Worktree rule's
declared-parallelism case does not arise in this phase.

---

## Step 1 — Preserve 0.2.x and Land the Roadmaps ✅

**Status:** Complete — PR #46 (2026-10-04)

> **Goal:** Preserve every byte of 0.2.x before anything moves, then make
> `main` the ledger. Commit the uncommitted work in progress — the OpenAI
> v1 client in `pyeconomics/ai/taylor_rule.py` and
> `pyeconomics/api/openai_api.py`, the Bloomberg forecast tickers in
> `pyeconomics/utils/utils.py`, the `tia` line in `requirements.txt` and
> the two regenerated plots — to a new `archive/0.2-dev-wip` branch; tag
> `origin/dev` and `origin/legacy-dev-0.2.6` as `archive/dev-2024-10` and
> `archive/legacy-dev-0.2.6`; and add `archive-immutable-*` rulesets that
> forbid updating or deleting any `archive/` branch or tag. Then land
> `docs/roadmap/ROADMAP.md`, this file and the roadmodel planning kit
> (`planning/`, without the personal `planning/user-context.md`) on
> `main` through this step's PR, with `.gitignore` ignoring
> `planning/user-context.md` and `.worktrees/`; protect `main` (pull
> request required, `enforce_admins`, linear history, no force-push or
> deletion, conversation resolution); and switch the repository to
> squash-only merges titled by the PR title, with
> `delete_branch_on_merge` and branch updates enabled. The ignored local
> content — `dev/`, `.env`, `cache/` and the root scripts — ends the step
> exactly as it began. Parent: ROADMAP §4 Phase 1 → 1.1 and §5 "Branch
> management strategy".

**Branch:** `feature/phase01-step1-preserve-and-bootstrap`

**Deploys:** nothing beyond merge — the archive refs, rulesets and
repository settings this step changes take effect on `origin` at once and
are verified in its acceptance criteria.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence Medium       |
| Platform     | Claude Code                                   |
| Effort       | Medium                                        |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** The step is agentic, Medium-complexity git and
GitHub administration — a fixed command sequence whose only hard part is
never losing the uncommitted work — and Opus 5.5 is rated S for agentic
work and S for coding in the selector catalog. Under the operator's
`balanced` budget and `capped` consumption posture a Medium step runs on
the surface's default, and Claude Code on the claude.ai Max plan
($200/month, $0 marginal while the weekly pool shows headroom) opens on
Opus 5.5 at its Medium default effort: run as opened, no change. Effort
stays Medium because every command is specified and the risk lies in
following them exactly, not in reasoning depth; Thinking stays On, the
operator's standing setting. The backup, GPT-6 Sol on Codex under the
ChatGPT Pro 5x subscription, is S in agentic work and coding and leads
the cross-provider field on coverage. New conversation per phase-boundary
hygiene.

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
       feature/phase01-step1-preserve-and-bootstrap`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 1 is
       complete. You can now move
       on to Step 2." That
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
       one before Step 2.
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

    THIS STEP ALSO (Bootstrap rule — the pre-commit hook
    does not exist until Step 8, so run the gate by hand
    before every commit and paste each command's summary
    line into the PR body):
    - Secrets: `gitleaks git --pre-commit --staged --redact`
      before each commit, and `gitleaks git --redact
      --log-opts="origin/dev..HEAD"` before
      `archive/0.2-dev-wip` is pushed — the archive goes to
      a PUBLIC remote.
    - SAST: `uvx bandit -q <staged .py files>` on the
      archive commit. Findings in preserved 0.2.x code are
      listed in the PR body, not fixed: the archive must
      stay byte-identical and never merges.
    - Dependencies: none added. The archived
      requirements.txt line is preserved, never installed.
    - Sensitive data: no `.env`, `cache/`, `dev/` or
      `planning/user-context.md` path in any pushed tree,
      and neither plot may show Bloomberg-licensed data —
      open both before staging them.
    - Never print the environment, a token or a key; the
      maintainer's shell holds a GitHub token.
  </security>

  <context>
    pyeconomics — a Python library on PyPI being rebuilt as
    1.0 per docs/roadmap/ROADMAP.md. Phase 1 (Reset &
    Foundation). Step 1: Preserve 0.2.x and land the
    roadmaps. Sole maintainer: Nathan Ramos, CFA. Machine:
    Windows 11, Git Bash and PowerShell, uv 0.12.x, gh
    authenticated (repo and workflow scopes), gitleaks
    8.30.1 installed.

    Current state (as of 0.2.x, before Phase 1):

    - The checkout is on `dev` at d4a692d7c76c (equal to
      origin/dev) with UNCOMMITTED 0.2.x work that exists
      nowhere else: pyeconomics/ai/taylor_rule.py
      (+123/-61), pyeconomics/api/openai_api.py (+7/-3),
      pyeconomics/utils/utils.py (+16/-12),
      requirements.txt (+1, the `tia` git dependency), and
      media/gaps_plot.png plus media/taylor_rule_plot.png
      (regenerated). Also modified: .gitignore (+4 lines
      ignoring planning/user-context.md — planning kit, not
      0.2.x work). Untracked: docs/roadmap/ (ROADMAP.md and
      this file) and planning/ (the roadmodel kit).
    - Ignored and irreplaceable: dev/ (44 research files and
      35 checkpoints), .env (FRED and OpenAI keys), cache/,
      generate_tests.py, render_readme.py, output.html.
      planning/user-context.md is personal and must never
      be committed. A dev/ directory exists, so write
      `origin/dev` or `dev --` in git commands that also
      accept paths.
    - origin/main = v0.2.5 = ad494c1c1a2f (unprotected).
      origin/dev = d4a692d7c76c75119c98dbc980d0ec5454a8fa05.
      origin/legacy-dev-0.2.6 =
      2b7e8a6e1dd3dbc11b4a8e395e8679fe31487d15. No
      rulesets, no environments; merge, rebase and squash
      all allowed; delete_branch_on_merge off.
    - The 0.2.x release.yml publishes on any `v*` tag with
      the PYPI_API_TOKEN secret. Archive refs use the
      `archive/` prefix, which cannot match `v*`. This step
      pushes no `v*` tag.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md (§2 Current State; §4 Phase 1
      and 1.1; §5 "Branch management strategy", "Worktree
      strategy", "Per-step security gate").
    - docs/roadmap/phase01-roadmap.md (this file: the
      Overview's Bootstrap rule, Status rule and Step
      lifecycle).
    - planning/HOW-TO-USE.md (what the kit is; why
      user-context.md stays local).
    - The output of `git status --short`, `git diff --stat`
      and `git diff --numstat` (the work to preserve).
    - .gitignore in the working tree and
      `git show origin/main:.gitignore` (the conflict you
      will resolve).
  </context>

  <goal>
    The work in progress is preserved on
    archive/0.2-dev-wip and the two unreleased heads as
    annotated archive tags, all immutable on origin;
    docs/roadmap/ and planning/ (without user-context.md)
    are on main through this step's PR; main is protected
    and the repository merges by squash only. Every ignored
    local file is exactly as it was.
  </goal>

  <requirements>
    <requirement>
      First action — the one-time exception to the
      Branch-first rule, because the tree is dirty and not
      on main: `git switch -c archive/0.2-dev-wip` (it
      carries the uncommitted work from dev). Until this
      step says otherwise, never run `git clean`,
      `git reset --hard`, `git checkout -- <path>`,
      `git restore` on a work-in-progress path,
      `git add -A`, `git add .` or `git stash drop`.
    </requirement>

    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Preserve the work in progress:
      1. Save `git status --short`, `git diff --numstat`,
         `find dev -type f | wc -l` (expect 79) and a
         SHA-256 list of every file under dev/ to the
         scratchpad; the first two go in the PR body, the
         last two are the end-of-step integrity baseline.
      2. Open both plots. If either draws a Bloomberg-sourced
         series (the ECCCUS or ECUPUS consensus forecasts),
         copy it to dev/wip-media/ (ignored; Step 5 archives
         it privately), confirm the copy's SHA-256, then
         `git restore media/<that file>` for that file only.
      3. Stage by explicit path: the three .py files,
         requirements.txt, and each plot that passed check
         2. Do not stage .gitignore.
      4. Run the gate (see the security block), then
         `git commit -s -m "chore(archive): preserve
         uncommitted 0.2.x work in progress"` and
         `git push -u origin archive/0.2-dev-wip`.
      5. `git tag -a archive/dev-2024-10
         d4a692d7c76c75119c98dbc980d0ec5454a8fa05` and
         `git tag -a archive/legacy-dev-0.2.6
         2b7e8a6e1dd3dbc11b4a8e395e8679fe31487d15`, each
         with a message naming what it preserves; confirm
         each with `git rev-parse <tag>^{commit}`; push each
         tag by name, never with `--tags`.
      6. `git stash push --include-untracked -m "phase01
         step1: roadmaps and kit" -- .gitignore docs/roadmap
         planning`, then confirm `git status --short` lists
         nothing but `planning/user-context.md` (no longer
         ignored once .gitignore reverts; it is never
         staged).
    </requirement>

    <requirement>
      Stage 1 proper: `git switch main`,
      `git pull --ff-only origin main`,
      `git switch -c
      feature/phase01-step1-preserve-and-bootstrap`, then
      `git stash pop`. The .gitignore hunk will conflict;
      resolve it to origin/main's content plus this block:
        # roadmodel planning kit: personal posture, never commit
        planning/user-context.md
        # git worktrees (ROADMAP §5 "Worktree strategy")
        .worktrees/
      Then confirm `git check-ignore -v
      planning/user-context.md` names .gitignore and
      `git status --short` shows only .gitignore,
      docs/roadmap/ and planning/. Drop the stash entry only
      after both checks pass.
    </requirement>

    <requirement>
      Commit the ledger on the step branch by explicit path:
      .gitignore, docs/roadmap/ROADMAP.md,
      docs/roadmap/phase01-roadmap.md and planning/ (safe
      only after the check-ignore above passes; confirm with
      `git diff --cached --name-only` that user-context.md
      is absent). One signed-off commit: `docs: land the 1.0
      roadmaps and planning kit`.
    </requirement>

    <requirement>
      Repository settings with `gh api` (show the operator
      each payload first; OWNER/REPO comes from
      `gh repo view --json nameWithOwner`):
      - `PATCH repos/OWNER/REPO`: allow_squash_merge true,
        allow_merge_commit false, allow_rebase_merge false,
        delete_branch_on_merge true, allow_update_branch
        true, squash_merge_commit_title PR_TITLE,
        squash_merge_commit_message COMMIT_MESSAGES (so the
        squash body keeps each commit's Signed-off-by).
      - `PUT repos/OWNER/REPO/branches/main/protection`:
        required_status_checks null, enforce_admins true,
        required_pull_request_reviews with
        required_approving_review_count 0 (a sole maintainer
        must be able to merge; the PR is the requirement),
        restrictions null, required_linear_history true,
        allow_force_pushes false, allow_deletions false,
        required_conversation_resolution true.
      - Two rulesets (names must be unique per repository): `archive-immutable-branches` with
        target `branch` including `refs/heads/archive/**`,
        `archive-immutable-tags` with target `tag` including
        `refs/tags/archive/**`; rules `deletion`,
        `non_fast_forward` and `update`; no bypass actors;
        enforcement `active`. Verify through
        `gh api repos/OWNER/REPO/rulesets` and
        `gh api repos/OWNER/REPO/rules/branches/archive/0.2-dev-wip`;
        never test by attempting a deletion.
    </requirement>

    <requirement>
      Stage 3 under the Bootstrap rule: this is the first PR
      under protection and it has no required checks. The
      0.2.x `pytest` and `sphinx` workflows may run on it and
      fail; record their conclusions in the PR body and do
      not wait on them. The PR body also carries the saved
      numstat, the archive commit SHA, both tag SHAs, the
      gate summary lines, any bandit findings on the
      archived code, and the decision on each plot. The
      Stage-3 commit is the phase's first: this step's
      Status line, ✅ heading and Summary Table cell; this
      file's phase-level Status → `In progress`; and in
      docs/roadmap/ROADMAP.md the `### Phase 1` Status →
      `In progress — phase01-roadmap.md` and its §8 row →
      `In progress`.
    </requirement>

    <requirement>
      End-of-step integrity check, after Stage 5: the dev/
      file count and SHA-256 list match the baseline; .env
      and cache/ still exist and are untracked;
      `git ls-tree -r --name-only` of origin/main and of
      origin/archive/0.2-dev-wip lists no .env, cache/,
      dev/ or planning/user-context.md path.
    </requirement>

    <requirement>
      Filepath comment: this step creates no source files;
      the Markdown it lands follows the docs/roadmap/
      convention, which carries no filepath line.
    </requirement>
  </requirements>
</task>
```

### Step 1 acceptance criteria

- `origin/archive/0.2-dev-wip` exists, and `git diff --numstat
  archive/dev-2024-10 origin/archive/0.2-dev-wip` equals the saved
  work-in-progress numstat minus `.gitignore` (and minus any plot
  withheld under the licensing check, recorded in the PR body).
- `git ls-remote --tags origin 'archive/*'` shows `archive/dev-2024-10`
  peeling to `d4a692d7c76c75119c98dbc980d0ec5454a8fa05` and
  `archive/legacy-dev-0.2.6` peeling to
  `2b7e8a6e1dd3dbc11b4a8e395e8679fe31487d15`.
- Both `archive-immutable-*` rulesets (`-branches`, `-tags`) are active, and `gh api
  repos/OWNER/REPO/rules/branches/archive/0.2-dev-wip` lists `deletion`,
  `non_fast_forward` and `update`.
- `main` carries `docs/roadmap/ROADMAP.md`,
  `docs/roadmap/phase01-roadmap.md` and the `planning/` kit;
  `git ls-files planning/user-context.md` prints nothing and
  `git check-ignore planning/user-context.md` matches.
- `gh api repos/OWNER/REPO/branches/main/protection` shows
  `enforce_admins` enabled, linear history required, force pushes and
  deletions disallowed, and pull-request reviews required with zero
  approvals; the repository allows squash merges only, titles them by the
  PR title, and deletes merged branches.
- The `dev/` file count (79) and SHA-256 list are unchanged; `.env` and
  `cache/` are present and untracked.
- This file's phase Status reads `In progress`; ROADMAP.md's Phase 1
  Status reads `In progress — phase01-roadmap.md` and its §8 row reads
  `In progress`.
- **Security gate clean** (always the final criterion): gitleaks reported
  no leaks on the archive commit, on `origin/dev..archive/0.2-dev-wip`
  and on the ledger commit; no pushed tree contains `.env`, `cache/`,
  `dev/` or `planning/user-context.md`; no Bloomberg-licensed plot reached
  the public remote; bandit findings on the preserved code are listed in
  the PR body.

---

## Step 2 — Legacy Credential-Logging Fix and Hardened Release Pipeline ✅

**Status:** Complete — PR #48 (2026-10-05)

> **Goal:** Cut `legacy/0.2.x` from `v0.2.5` and protect it, then fix and
> re-plumb it on `fix/legacy-0.2.6-credential-logging`. Delete the three
> statements in `pyeconomics/api/fred_api.py` that write the FRED key to
> the log; add `tests/test_credential_logging.py` and
> `scripts/check_credential_logging.py` (the same assertion run against
> an installed artifact); set `__version__.py` to `0.2.6.dev1`; and add a
> CHANGELOG entry and a README security notice. Replace the branch's
> workflows: delete `docs.yml`; harden `tests.yml` (Python 3.11 and 3.12,
> SHA-pinned actions, least-privilege `permissions`, harden-runner, no
> Codecov, no echoed variables); and rewrite `release.yml` as a Trusted
> Publishing pipeline that verifies the tag, tests, builds once with `uv
> build`, runs `twine check --strict`, publishes `.devN` versions to
> TestPyPI through the `testpypi` environment and every other version to
> PyPI through the `pypi` environment behind the maintainer's approval,
> and finishes with a smoke job that installs the exact version in a
> fresh venv and runs the credential check. Configure both environments,
> both trusted publishers and a `release-tags` ruleset on `v*`; revoke the
> PyPI API token and delete its secret; merge, tag `v0.2.6.dev1`, and
> prove the whole pipeline on TestPyPI. Parent: 1.1 and 1.5.

**Branch:** `feature/phase01-step2-legacy-patch` (from `main`; carries the
Status mark) with work branch `fix/legacy-0.2.6-credential-logging` (from
`origin/legacy/0.2.x`; PR → `legacy/0.2.x`), per the Legacy-branch rule.

**Deploys:** TestPyPI — `pyeconomics==0.2.6.dev1` from tag `v0.2.6.dev1`
on `legacy/0.2.x`, through the hardened `release.yml` and the `testpypi`
environment. The PyPI release belongs to Step 4.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence High         |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** This is High-complexity, security-sensitive coding —
a release pipeline whose mistakes publish irreversibly — whose hard parts
are knowledge: OIDC Trusted Publishing, PEP 740 attestations, deployment
environments and a dependency-confusion-safe smoke install. Coding is
the PRIMARY category and knowledge the SECONDARY; Opus 5.5 is rated S in
both, ties Fable 5.1 on both and on coverage, and wins the selector's
cost tie-break at $20 against $50 per million output tokens. Claude Code
on the claude.ai Max subscription runs it at $0 marginal while the weekly
pool has headroom. Effort rises from Opus 5.5's Medium default to High
because the step is security-sensitive and spans the fix, two workflows,
GitHub and PyPI settings and a live rehearsal; it stops short of Extra
High because Trusted Publishing is a documented PyPA pattern, not novel
design. Thinking stays On. The backup, GPT-6 Sol on Codex under ChatGPT
Pro 5x, is S in coding and leads the cross-provider field on coverage.
New conversation per phase-boundary hygiene.

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
       feature/phase01-step2-legacy-patch`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 2 is
       complete. You can now move
       on to Step 3." That
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
       one before Step 3.
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

    THIS STEP ALSO (Bootstrap rule — run the gate by hand
    before every commit; summary lines in the PR bodies):
    - Secrets: `gitleaks git --pre-commit --staged --redact`.
      The test sentinel must not be key-shaped (FRED keys
      are 32 lowercase alphanumerics): use a value such as
      `sentinel-not-a-fred-key`.
    - SAST: `uvx bandit -q -r pyeconomics scripts tests`
      adds no finding, and `uvx zizmor .github/workflows/`
      reports nothing above Low.
    - Dependencies: the package gains and bumps none.
      `uvx pip-audit -r requirements.txt` output is recorded
      for Step 3's gate, not acted on here.
    - Pipeline: `id-token: write` only on the two publish
      jobs; no `password:` input; every `uses:` pinned to a
      40-character SHA; no `pull_request_target`;
      `persist-credentials: false` on every checkout;
      untrusted values reach `run:` only through `env:`.
    - Credentials: the operator revokes the PyPI token in
      PyPI's UI; the agent deletes the secret with
      `gh secret delete PYPI_API_TOKEN`. No value is ever
      printed, pasted or written to a file.
  </security>

  <context>
    pyeconomics. Phase 1. Step 2: Legacy credential-logging
    fix and hardened release pipeline.

    Current state (as of Phase 1 Step 1):

    - Step 1 landed docs/roadmap/ and planning/ on main,
      protected main (PR required, enforce_admins, linear
      history), set squash-only merges, and made the archive
      refs immutable. No required checks exist yet
      (Bootstrap rule).
    - v0.2.5 (ad494c1c1a2f) is the last release.
      pyeconomics/api/fred_api.py logs the FRED key at DEBUG
      in FredClient.__new__ — lines 75-76, 82-83 and 91 —
      and builds `fred_client = FredClient()` at import.
      setup.py reads the version from the root
      __version__.py ('0.2.5') and install_requires from
      requirements.txt; python_requires '>=3.11, <3.13'.
    - v0.2.5 workflows: tests.yml (3.11 and 3.12;
      tag-pinned actions; no permissions; echoes dummy keys;
      Codecov upload), docs.yml (Sphinx), and release.yml
      (any `v*` tag, PYPI_API_TOKEN, gh-action-pypi-publish
      v1.4.2, a version file setup.py never reads).
    - PyPI has 0.1.0 and 0.2.0-0.2.5; TestPyPI has no
      `pyeconomics` project, so its publisher starts as a
      pending publisher. Repository secrets: PYPI_API_TOKEN,
      CODECOV_TOKEN. No environments; no `v*` ruleset.
    - Read the Docs builds the 0.2.x docs from main; Step 4
      re-points it at legacy/0.2.x.

    Files to read (every file before drafting):
    - `git show v0.2.5:pyeconomics/api/fred_api.py` (the
      three statements to delete).
    - `git show v0.2.5:pyeconomics/__init__.py` and
      `git show v0.2.5:pyeconomics/api/__init__.py`
      (import-time side effects).
    - `git show v0.2.5:tests/test_fred_api.py` and
      `git show v0.2.5:tests/conftest.py` (the test
      patterns to mirror).
    - `git show v0.2.5:.github/workflows/release.yml`, and
      the same for tests.yml and docs.yml (what is
      replaced).
    - `git show v0.2.5:` for setup.py, __version__.py,
      requirements.txt, MANIFEST.in, pyproject.toml,
      markdown/CHANGELOG.md and README.md (the build inputs
      and release notes).
    - docs/roadmap/ROADMAP.md §4 1.1 and 1.5; §5 "Release &
      deployment strategy" and "Security & privacy
      strategy".
  </context>

  <goal>
    legacy/0.2.x exists, is protected, logs no credential,
    and releases only through a hardened Trusted Publishing
    workflow; no PyPI API token exists anywhere; and
    0.2.6.dev1 is on TestPyPI with attestations, installed
    and checked by the pipeline's own smoke job.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff verification, by the operator in the
      providers' own UIs (nothing typed into chat): the PyPI
      account has 2FA; a TestPyPI account exists with 2FA
      (create it if not). No PyPI or TestPyPI change happens
      before the operator confirms both.
    </requirement>

    <requirement>
      Create and protect the line: `git push origin
      ad494c1c1a2f0d052561cd0dd94c92f5279ac8d0:refs/heads/legacy/0.2.x`;
      apply Step 1's protection payload to
      `branches/legacy%2F0.2.x/protection`; add the legacy
      CI job names as required checks after their first
      green run on the fix PR.
    </requirement>

    <requirement>
      Baseline before editing, on
      `git switch -c fix/legacy-0.2.6-credential-logging
      origin/legacy/0.2.x`: create a fresh environment with
      `uv venv --python 3.12`, install `-r requirements.txt`
      and `-e .` into it, and run the v0.2.5 suite with a
      non-key-shaped FRED_API_KEY. If it fails on dependency
      drift rather than code, add `constraints-ci.txt`, used
      only by CI (`-c constraints-ci.txt`) and never by
      install_requires, and list each pin with its reason in
      the PR body.
    </requirement>

    <requirement>
      The fix, and nothing else in package code: delete the
      statements in FredClient.__new__ that interpolate
      `api_key_retrieved` (v0.2.5 lines 75-76, 82-83 and
      91), keeping the non-sensitive debug lines; read every
      other logging call in pyeconomics/ and confirm none
      can carry a credential, exception text included. The
      import-time client, the pickle cache and the pins stay
      as they are (scope: security only).
    </requirement>

    <requirement>
      Regression coverage:
      - tests/test_credential_logging.py: with
        FredClient.reset_instance() between cases, DEBUG
        capture on the root logger and a non-key-shaped
        sentinel, construct the client through the argument,
        through FRED_API_KEY and through a mocked keyring;
        assert the sentinel appears in no record's message,
        args or formatted output. Mock `fredapi.Fred` so no
        request is made.
      - scripts/check_credential_logging.py: the same
        assertion as a standalone script that imports the
        INSTALLED package — it refuses to run when
        `pyeconomics.__file__` lies inside the checkout — and
        exits non-zero on a leak. The smoke job runs it.
    </requirement>

    <requirement>
      Release notes: __version__.py → '0.2.6.dev1';
      markdown/CHANGELOG.md gains `## [0.2.6] - Unreleased`
      with a Security entry (the FRED key is no longer
      logged; rotate a key whose DEBUG logs were stored or
      shared; 0.2.x reaches end-of-life when 1.0.0 ships);
      README.md gains a short security notice at the top
      saying the same. Step 4 dates the entry and links the
      advisory.
    </requirement>

    <requirement>
      Workflows on the work branch:
      - Delete .github/workflows/docs.yml; Read the Docs
        builds the docs itself.
      - tests.yml becomes the legacy CI: on pull_request and
        push for legacy/0.2.x; top-level `permissions: {}`
        and `contents: read` per job; harden-runner first
        (egress audit); checkout with
        `persist-credentials: false`; Python 3.11 and 3.12;
        install `-r requirements.txt` (plus the constraints
        file if the baseline needed one) and `-e .`; flake8
        as before, then pytest; a non-key-shaped
        FRED_API_KEY; no Codecov step and no echo of any
        variable; concurrency that cancels superseded PR
        runs.
      - release.yml runs on `push: tags: ['v0.2.*']` only,
        with `permissions: {}` and per-ref concurrency that
        never cancels. Jobs: `verify` (fetch-depth 0; the
        tag's commit is an ancestor of origin/legacy/0.2.x;
        the tag equals `v` plus __version__.py; output
        `index` = testpypi for a `.devN` version, otherwise
        pypi); `test` (the CI matrix); `build` (`uv build`
        once, `uvx twine check --strict dist/*`, the built
        version equals the tag, upload the dist artifact);
        `publish-testpypi` (when index is testpypi;
        `environment: testpypi`; `id-token: write`;
        pypa/gh-action-pypi-publish with `repository-url:
        https://test.pypi.org/legacy/`); `publish-pypi`
        (when index is pypi; `environment: pypi`;
        `id-token: write`); and `smoke` (after the publish
        job: a fresh Python 3.12 venv installs
        `pyeconomics==<version>` with `--no-deps` from the
        index it went to, then its dependencies from PyPI
        ONLY — TestPyPI never resolves a third-party name —
        retrying while the index propagates; it asserts
        `importlib.metadata.version("pyeconomics")` equals
        the tag and runs
        scripts/check_credential_logging.py).
      - Every `uses:` is pinned to a full commit SHA with a
        `# vX.Y.Z` comment, looked up at write time.
      - `uvx zizmor .github/workflows/` reports nothing
        above Low.
    </requirement>

    <requirement>
      GitHub configuration with `gh api` (payloads shown
      first):
      - Environment `testpypi`: custom deployment policy,
        tag pattern `v*`.
      - Environment `pypi`: required reviewer = the
        maintainer; prevent_self_review false (sole
        maintainer); custom deployment policy, tag pattern
        `v*`.
      - Ruleset `release-tags` (target tag, include
        `refs/tags/v*`): rules creation, update and
        deletion; bypass actor = the repository admin role,
        mode always.
    </requirement>

    <requirement>
      Trusted publishers and the token, by the operator in
      the providers' UIs; the agent verifies:
      - PyPI, project pyeconomics → Publishing: add a GitHub
        publisher with the owner and repository from
        `gh repo view --json nameWithOwner`, workflow
        `release.yml`, environment `pypi`.
      - TestPyPI: add a pending publisher for project
        `pyeconomics` with the same owner, repository and
        workflow, environment `testpypi`.
      - Revoke every PyPI API token able to upload
        `pyeconomics`, then `gh secret delete
        PYPI_API_TOKEN` and confirm with `gh secret list`.
        From here no stored credential can publish, so no
        old workflow at any commit can either.
    </requirement>

    <requirement>
      Land and rehearse: open the work PR against
      legacy/0.2.x (title such as `fix(security): stop
      logging the FRED API key`); squash-merge when the
      legacy CI is green; make its checks required on
      legacy/0.2.x; then `git tag -a v0.2.6.dev1 <merge
      SHA> -m "0.2.6.dev1: TestPyPI rehearsal"` and push the
      tag by name. Follow the run with `gh run watch`;
      `publish-testpypi` and `smoke` must be green.
    </requirement>

    <requirement>
      Return to the step branch for Stage 3: the main PR
      carries this step's Status mark and lists both PR
      numbers, the release run URL and the gate output.
    </requirement>

    <requirement>
      Filepath comment: every new Python or YAML file starts
      with `# <repo-relative path>`, matching the 0.2.x
      convention.
    </requirement>
  </requirements>
</task>
```

### Step 2 acceptance criteria

- `legacy/0.2.x` exists on `origin`, was cut from
  `ad494c1c1a2f0d052561cd0dd94c92f5279ac8d0`, and is protected like
  `main`, with the legacy CI jobs required.
- `git show origin/legacy/0.2.x:pyeconomics/api/fred_api.py` contains no
  logging call that interpolates a credential, and `git diff v0.2.5
  origin/legacy/0.2.x --stat` touches only that file, `__version__.py`,
  the CHANGELOG, the README, the new test and script, the workflows and
  (if the baseline needed it) `constraints-ci.txt`.
- `tests/test_credential_logging.py` passes in the legacy CI on Python
  3.11 and 3.12.
- On `legacy/0.2.x` every workflow `uses:` is SHA-pinned, the top-level
  `permissions` is `{}`, `id-token: write` appears only on the two publish
  jobs, there is no `password:` input and no `docs.yml`, and
  `uvx zizmor .github/workflows/` reports nothing above Low.
- Environments `testpypi` and `pypi` exist with tag policy `v*`, `pypi`
  requires the maintainer's review, and the `release-tags` ruleset is
  active on `refs/tags/v*`.
- `gh secret list` shows no `PYPI_API_TOKEN`, and the operator confirms in
  the PR that no PyPI API token able to upload `pyeconomics` remains.
- **Deployed & verified:** the `v0.2.6.dev1` release run is green through
  `publish-testpypi` and `smoke`; TestPyPI lists `pyeconomics 0.2.6.dev1`
  and `https://test.pypi.org/integrity/pyeconomics/0.2.6.dev1/<file>/provenance`
  returns an attestation for both files; a clean venv that installs
  `pyeconomics==0.2.6.dev1` from TestPyPI with `--no-deps`, plus its
  dependencies from PyPI, reports `0.2.6.dev1` and passes
  `scripts/check_credential_logging.py`.
- **Security gate clean** (always the final criterion): gitleaks, bandit
  and zizmor ran clean on every commit of both PRs, with summary lines in
  the PR bodies; the regression test proves no FRED key reaches a log
  record; no stored PyPI credential exists in GitHub or on PyPI; and
  publishing ran on short-lived OIDC credentials only.

---

## Step 3 — 0.2.6 Readiness Gate ✅

**Status:** Complete — PR #49 (2026-10-05)

> **Goal:** Decide, with evidence, that publishing 0.2.6 to PyPI is safe —
> the rebuild's first irreversible cutover, which ROADMAP §5 "Promotion
> path and cutovers" gives its own readiness-gate step. Write
> `docs/releases/0.2.6-readiness.md` and fill every section from commands
> run in this step: access control (environment reviewers, the
> `release-tags` ruleset, trusted publishers, no API token, 2FA, branch
> protection); the artifacts (the TestPyPI `0.2.6.dev1` wheel and sdist
> diffed file by file against PyPI's 0.2.5, with metadata unchanged);
> behaviour (the credential check against the installed rehearsal
> artifact); the affected range (every released sdist read for the
> logging lines without executing it); the advisories against 0.2.x's
> pinned dependencies and the maintainer's decision on them; monitoring
> (the smoke job and its failure notification); a rollback rehearsal
> (yank `0.2.6.dev1` on TestPyPI and observe pip); and attribution
> (CHANGELOG, README notice, end-of-life statement). Create the GitHub
> security advisory as a draft — never published here — and end with the
> maintainer's recorded GO or NO-GO. Parent: §5 "Promotion path and
> cutovers" and 1.1.

**Branch:** `feature/phase01-step3-release-gate`

**Deploys:** nothing beyond merge — the advisory stays a draft and
nothing is published; the TestPyPI yank is a reversible index flag on a
rehearsal version.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6.1 Sol — Codex · Intelligence Medium     |
| Platform     | Claude Code                                   |
| Effort       | Medium                                        |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** The step is Medium-complexity knowledge work —
reading artifacts and terms, scoring an advisory with CWE and CVSS, and
writing a checklist a release can be judged against — carried out as a
sequence of verification commands, so knowledge is PRIMARY and agentic
work SECONDARY. Opus 5.5 is rated S for knowledge, one of only two
catalog models with that rating (the other, Fable 5.1, costs 2.5 times
as much). The operator's `balanced`, `capped` posture runs a Medium step
on the surface's default, so Claude Code on the claude.ai Max plan ($0
marginal while the weekly pool has headroom) opens on Opus 5.5 at its
Medium default — run as opened. Medium effort fits a bounded checklist
whose hard calls (the CVSS vector, the pin decision) end with the
maintainer; Thinking stays On. The backup, GPT-6.1 Sol on Codex under
ChatGPT Pro 5x, ties GPT-6 Sol on knowledge A, agentic S, coverage and
price, and is taken on its higher Artificial Analysis Intelligence Index
(51.8 against 47.6). New conversation per phase-boundary hygiene.

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
       feature/phase01-step3-release-gate`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 3 is
       complete. You can now move
       on to Step 4." That
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
       one before Step 4.
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

    THIS STEP ALSO (Bootstrap rule — run the gate by hand
    before every commit; summary lines in the PR body):
    - Secrets: `gitleaks git --pre-commit --staged --redact`.
      The readiness document and the advisory draft quote
      no key, token or log excerpt containing one.
    - SAST: this step adds no code to the repository; any
      helper it writes stays in the scratchpad.
    - Reading old releases must not execute them: fetch
      each sdist with `curl` from the URL in PyPI's JSON API
      and read it with `tar`; never `pip download`,
      `pip install` or `setup.py` for this audit.
    - The advisory is created in `draft` state only;
      publishing it belongs to Step 4.
  </security>

  <context>
    pyeconomics. Phase 1. Step 3: 0.2.6 readiness gate.

    Current state (as of Phase 1 Step 2):

    - legacy/0.2.x carries the credential-logging fix,
      version 0.2.6.dev1, a CHANGELOG entry, a README
      notice, tests/test_credential_logging.py,
      scripts/check_credential_logging.py, and hardened
      tests.yml and release.yml; it is protected, with its
      CI required.
    - v0.2.6.dev1 is on TestPyPI with attestations,
      published through the `testpypi` environment; the
      `pypi` environment requires the maintainer's
      approval; the `release-tags` ruleset guards `v*`;
      PYPI_API_TOKEN is revoked and deleted.
    - PyPI releases: 0.1.0 and 0.2.0-0.2.5. The project
      roadmap assumes every version up to 0.2.5 is affected;
      whether 0.1.0 is stays TBD until this step reads it.
    - The 0.2.x runtime pins (requirements.txt) include
      setuptools~=68.2.2, jupyterlab~=4.1.8, sphinx~=7.3.7
      and others; Step 2's PR body recorded `pip-audit`
      output for them.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §5 "Promotion path and
      cutovers", "Rollback", "Vulnerability handling" and
      "Release & deployment strategy" (the checklist and
      the rollback table).
    - The Step 2 PR bodies (main and legacy) and the
      v0.2.6.dev1 release run log.
    - `git show origin/legacy/0.2.x:markdown/CHANGELOG.md`
      and `git show origin/legacy/0.2.x:README.md` (the
      release notes the gate signs off).
    - `git diff v0.2.5 origin/legacy/0.2.x --stat`.
  </context>

  <goal>
    docs/releases/0.2.6-readiness.md is on main with every
    section evidenced and a GO or NO-GO line the maintainer
    wrote or approved; a draft GitHub security advisory
    exists with the verified affected range, CWE-532 and a
    CVSS vector.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Create docs/releases/0.2.6-readiness.md with ten
      numbered sections — Access control, Artifact diff,
      Behaviour, Affected versions, Dependency advisories,
      Monitoring, Rollback rehearsal, Attribution and legal,
      Advisory draft, Decision — where every item records
      the command run, the observed result, and PASS or
      FAIL.
    </requirement>

    <requirement>
      Access control: `gh api` reads of the `pypi` and
      `testpypi` environments (reviewers, tag policy), the
      rulesets, `gh secret list`, and the legacy/0.2.x
      protection; the operator confirms on PyPI and TestPyPI
      that the trusted publishers match release.yml and its
      environments, that no API token remains, and that 2FA
      is on. No screenshot with personal data is committed.
    </requirement>

    <requirement>
      Artifact diff: fetch PyPI's 0.2.5 wheel and sdist and
      TestPyPI's 0.2.6.dev1 wheel and sdist (URLs from each
      index's JSON API) into the scratchpad; list and diff
      their members and contents. Expected differences only:
      pyeconomics/api/fred_api.py, the version metadata, the
      long description, and — in the sdist, through
      MANIFEST.in — the CHANGELOG, README, new test and
      workflows (docs.yml gone). Step 2 found four more,
      each expected: (a) build-backend metadata — 0.2.5 was
      built by setuptools of 2024 (Metadata-Version 2.1),
      0.2.6.dev1 by current setuptools under `uv build`
      (Metadata-Version 2.4, `Dynamic:` fields, LICENSE under
      `.dist-info/licenses/`, a newer WHEEL generator); (b)
      the wheel also gains tests/test_credential_logging.py,
      because `find_packages()` has always shipped `tests/`;
      (c) the sdist does NOT contain scripts/ — MANIFEST.in
      never included it; (d) both 0.2.5 artifacts contain a
      `pyeconomics/__version__.py` that 0.2.6.dev1 lacks: the
      old release.yml wrote it at build time and it was never
      in git. (d) removes an importable module, so the
      Decision section records the maintainer's call on it
      (ship as is, or restore the file — a package change
      that needs `0.2.6.dev2`). `Requires-Dist` and
      `Requires-Python` must be identical as parsed
      requirements (`packaging.requirements.Requirement`);
      their text differs (`fredapi ~=0.5.1` against
      `fredapi~=0.5.1`). Any other difference is a FAIL.
    </requirement>

    <requirement>
      Behaviour: in a clean venv install 0.2.6.dev1 from
      TestPyPI with `--no-deps` and its dependencies from
      PyPI, then run scripts/check_credential_logging.py
      against it; link the green legacy CI run.
    </requirement>

    <requirement>
      Affected versions: for 0.1.0 and each of 0.2.0-0.2.5,
      fetch the sdist, extract it with `tar`, and record
      whether its fred_api.py contains a logging call that
      interpolates the key. The advisory's affected range is
      exactly what this evidence shows (for example
      `<= 0.2.5` or `>= 0.2.0, <= 0.2.5`).
    </requirement>

    <requirement>
      Dependency advisories: run `uvx pip-audit -r
      requirements.txt` on legacy/0.2.x's HEAD and list each
      advisory with whether 0.2.x's use of the package
      reaches the vulnerable code. The maintainer decides,
      in the PR: ship the pins unchanged and list the
      advisories as known issues in the release notes (the
      recommendation — 0.2.x is security-only and ends at
      1.0.0), or widen a named pin, which requires a new
      rehearsal (`0.2.6.dev2`) before a GO is possible.
    </requirement>

    <requirement>
      Monitoring: confirm the smoke job ran green in the
      rehearsal and fails the run when its check fails; the
      operator confirms GitHub's notification settings email
      failed workflow runs to the maintainer.
    </requirement>

    <requirement>
      Rollback rehearsal, after the artifact diff and the
      behaviour check: the operator yanks 0.2.6.dev1 on
      TestPyPI with the reason "rehearsal of the 0.2.6
      rollback"; the agent shows in a clean venv that an
      exact pin (`pyeconomics==0.2.6.dev1`, `--no-deps`)
      still installs while an unpinned pre-release request
      no longer selects it. Then write the PyPI rollback
      procedure — yank 0.2.6 with a reason, ship 0.2.7
      through the same pipeline, update the advisory — with
      its commands and who runs each.
    </requirement>

    <requirement>
      Advisory draft: `gh api -X POST
      repos/OWNER/REPO/security-advisories` with a summary,
      a description (impact; the affected configuration —
      DEBUG logging enabled; the patched version; the
      workaround; key-rotation advice; 0.2.x end-of-life at
      1.0.0), one vulnerability entry (ecosystem pip,
      package pyeconomics, the range from the evidence,
      patched version 0.2.6), cwe_ids ["CWE-532"] and a
      CVSS 3.1 vector justified in the document. Record the
      draft GHSA id. Record the maintainer's decision on
      requesting a CVE at publication (recommended, so
      pip-audit and OSV users are warned).
    </requirement>

    <requirement>
      Decision: the document ends with
      `Decision: GO — <YYYY-MM-DD> — Nathan Ramos, CFA` or
      `Decision: NO-GO — <blockers>`. The maintainer writes
      or explicitly approves that line in the PR; the agent
      never fills it in alone. A NO-GO stops the phase until
      a new gate passes.
    </requirement>

    <requirement>
      Filepath comment: docs/releases/ Markdown follows the
      docs/ convention and carries no filepath line.
    </requirement>
  </requirements>
</task>
```

### Step 3 acceptance criteria

- `docs/releases/0.2.6-readiness.md` is on `main` with all ten sections,
  every item showing its command, its result and PASS or FAIL, and no
  FAIL left unresolved.
- The artifact diff shows only the expected files changed between 0.2.5
  and 0.2.6.dev1, with identical `Requires-Dist` and `Requires-Python`.
- The affected range in the document and in the draft advisory follows
  from the sdists actually read, one line per released version.
- A draft advisory exists (`gh api
  'repos/OWNER/REPO/security-advisories?state=draft'` lists it) with
  CWE-532, a CVSS vector, the affected range and patched version 0.2.6.
- The TestPyPI yank rehearsal is recorded with pip's observed behaviour,
  and the PyPI rollback procedure names its commands and owner.
- The maintainer's GO or NO-GO line is present and was written or
  approved by the maintainer in the PR conversation.
- **Security gate clean** (always the final criterion): gitleaks reported
  no leaks on the commit; the document and the advisory contain no
  credential and no log excerpt carrying one; no old release was executed
  to read it.

---

## Step 4 — 0.2.6 Security Release and Advisory ✅

**Status:** Complete — PR #51 (2026-10-05)

> **Goal:** Execute the GO recorded in `docs/releases/0.2.6-readiness.md`.
> On `release/v0.2.6` (from `origin/legacy/0.2.x`) set `__version__.py` to
> `0.2.6`, date the CHANGELOG entry and link the advisory from the README
> notice; squash-merge to `legacy/0.2.x`; tag `v0.2.6` on the merge
> commit; the maintainer approves the `pypi` deployment; and the `smoke`
> job installs 0.2.6 from PyPI and runs the credential check. Then verify
> a clean install and both attestations independently, publish the GitHub
> security advisory (requesting a CVE if the gate decided so), re-point
> Read the Docs so `stable` serves 0.2.6 and `latest` builds from
> `legacy/0.2.x`, and append a release record — run URL, file hashes,
> advisory id — to the readiness document on `main`. Parent: 1.1 and §5
> "Release & deployment strategy".

**Branch:** `feature/phase01-step4-release-0.2.6` (from `main`; Status
mark and release record) with work branch `release/v0.2.6` (from
`origin/legacy/0.2.x`; PR → `legacy/0.2.x`), per the Legacy-branch rule.

**Deploys:** PyPI — `pyeconomics==0.2.6` from tag `v0.2.6` on
`legacy/0.2.x`, through the `pypi` environment after the maintainer's
approval; the GitHub security advisory goes public; Read the Docs
`stable` rebuilds 0.2.6 from the tag.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence Medium       |
| Platform     | Claude Code                                   |
| Effort       | Medium                                        |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** The step is agentic execution of a checklist already
decided — bump, merge, tag, approve, verify, publish — with coding
SECONDARY for the version and release-notes edit; several systems
interlock, so complexity is Medium, but nothing in it is new design. Opus
5.5 is rated S in agentic work and coding, and the operator's `balanced`,
`capped` posture runs a Medium step on the surface's default: Claude Code
on the claude.ai Max plan opens on Opus 5.5 at its Medium default, $0
marginal while the weekly pool has headroom — run as opened. Medium
effort suffices because the gate removed the judgement calls and every
action is verified by a command; Thinking stays On. The irreversible
moment, approving the `pypi` deployment, belongs to the maintainer, not
the model. The backup is GPT-6 Sol on Codex under ChatGPT Pro 5x (S in
agentic work, top cross-provider coverage). New conversation per
phase-boundary hygiene.

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
       feature/phase01-step4-release-0.2.6`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 4 is
       complete. You can now move
       on to Step 5." That
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
       one before Step 5.
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

    THIS STEP ALSO (Bootstrap rule — run the gate by hand
    before every commit; summary lines in the PR bodies):
    - Secrets: `gitleaks git --pre-commit --staged --redact`.
    - SAST: no code changes beyond the version string.
    - Dependencies: none added or bumped — unless the Step 3
      gate decided to widen a named pin, in which case that
      pin alone, audited with
      `uvx pip-audit -r requirements.txt`.
    - Release integrity: the maintainer's account creates
      the tag on the merge commit and it is pushed by name;
      publishing uses OIDC only; the advisory text and the
      release record quote no key or log line containing
      one.
  </security>

  <context>
    pyeconomics. Phase 1. Step 4: 0.2.6 security release
    and advisory.

    Current state (as of Phase 1 Step 3):

    - docs/releases/0.2.6-readiness.md is on main and ends
      with the maintainer's `Decision: GO` line; it records
      the draft advisory's GHSA id, the affected range, the
      CVE decision and the PyPI rollback procedure.
    - legacy/0.2.x is at version 0.2.6.dev1 with the fix,
      the regression test, the smoke script and the hardened
      workflows; tag v0.2.6.dev1 was published to TestPyPI
      and then yanked there as the rollback rehearsal.
    - The `pypi` environment requires the maintainer's
      approval; the trusted publisher for release.yml and
      `pypi` exists; no PyPI API token exists.
    - Read the Docs builds the 0.2.x docs from main's Sphinx
      sources, which Step 7 deletes.

    Files to read (every file before drafting):
    - docs/releases/0.2.6-readiness.md (the decision and
      every verified item this step relies on).
    - `git show origin/legacy/0.2.x:` for __version__.py,
      markdown/CHANGELOG.md, README.md and
      .github/workflows/release.yml.
    - docs/roadmap/ROADMAP.md §5 "Post-deploy verification"
      and "Rollback".
  </context>

  <goal>
    0.2.6 is on PyPI with attestations, published by the
    hardened pipeline after the maintainer's approval and
    verified in a clean environment; the advisory is public
    with the gate's ranges; Read the Docs serves 0.2.x from
    legacy/0.2.x; the release record is on main.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff check: the GO line is on main, and
      `git log v0.2.6.dev1..origin/legacy/0.2.x` is empty —
      nothing reached the line since the gate checked it. If
      either fails, stop: the gate is void and Step 3 runs
      again.
    </requirement>

    <requirement>
      Work branch: `git switch -c release/v0.2.6
      origin/legacy/0.2.x`; set __version__.py to '0.2.6';
      date the CHANGELOG entry (`## [0.2.6] - YYYY-MM-DD`);
      link the advisory from the README notice (the GHSA URL
      is fixed by the draft id). Step 3's gate also requires,
      in the same PR: (a) the CHANGELOG entry and the README
      notice name the affected versions as "0.2.0 to 0.2.5",
      not "0.2.5 and earlier" — 0.1.0 never logged the key
      (readiness §4); (b) if decision D2 shipped the pins
      unchanged, a `### Known issues` subsection in the 0.2.6
      entry listing the pinned jupyterlab, pytest and
      setuptools advisories, that installing pyeconomics
      downgrades setuptools to 68.2.x, and the advice to
      install it in its own virtual environment (readiness
      §5); (c) if decision D1 shipped as is, a `### Removed`
      line: `pyeconomics/__version__.py`, written at build
      time by the old release workflow, is no longer shipped;
      use `importlib.metadata.version("pyeconomics")`. Open
      the PR against legacy/0.2.x as `chore(release): 0.2.6`
      and squash-merge it once the legacy CI is green.
    </requirement>

    <requirement>
      Tag and publish: `git tag -a v0.2.6 <merge SHA> -m
      "0.2.6: security release"` and `git push origin
      v0.2.6`. The maintainer reviews the run's `verify`,
      `test` and `build` jobs, then approves the `pypi`
      deployment in the Actions UI; follow the run with
      `gh run watch` until `smoke` is green.
    </requirement>

    <requirement>
      Independent verification: in a clean Python 3.12 venv
      install `pyeconomics==0.2.6` from PyPI only; confirm
      `importlib.metadata.version("pyeconomics")` is 0.2.6;
      run scripts/check_credential_logging.py (from a
      checkout of the tag) against the installed package;
      confirm `curl
      https://pypi.org/integrity/pyeconomics/0.2.6/<file>/provenance`
      returns an attestation naming this repository's
      release.yml for both files; and confirm an unpinned
      `pip install pyeconomics` resolves 0.2.6. Install with
      `pip --isolated` or `uv … --no-config`: the operator's
      user-level uv configuration adds a package-firewall
      index ahead of the one named on the command line, so a
      plain `uv pip install --index-url …` can resolve from
      it instead (Step 3 hit this).
    </requirement>

    <requirement>
      Publish the advisory: request the CVE first if the
      gate decided so (`gh api -X POST
      repos/OWNER/REPO/security-advisories/GHSA_ID/cve`),
      then `gh api -X PATCH
      repos/OWNER/REPO/security-advisories/GHSA_ID -f
      state=published`. Confirm the public page shows the
      gate's affected range and patched version.
    </requirement>

    <requirement>
      Read the Docs, by the operator in its admin: default
      branch → legacy/0.2.x; default version → stable.
      Confirm `stable` built 0.2.6 from the tag and `latest`
      built from legacy/0.2.x, and that both URLs return
      200. If a build fails, fixing the legacy docs build is
      a blocking fix under the Triage rule: a further PR to
      legacy/0.2.x in this step.
    </requirement>

    <requirement>
      Release record: on the step branch, append a `Release
      record` section to docs/releases/0.2.6-readiness.md —
      date, tag SHA, run URL, approver, file names and
      SHA-256 from PyPI's JSON API, the attestation check,
      the advisory URL and CVE id (or "not requested"), and
      the Read the Docs URLs. Stage 3 marks this step on the
      same branch.
    </requirement>

    <requirement>
      Filepath comment: no new source file; the release
      record extends existing Markdown.
    </requirement>
  </requirements>
</task>
```

### Step 4 acceptance criteria

- `v0.2.6` is an annotated tag on a `legacy/0.2.x` commit whose
  `__version__.py` reads `0.2.6`; the CHANGELOG entry is dated and the
  README notice links the advisory.
- The release run shows `verify`, `test`, `build`, `publish-pypi`
  (approved by the maintainer) and `smoke` green, with `publish-testpypi`
  skipped.
- **Deployed & verified:** in a clean venv, `pip install pyeconomics==0.2.6`
  from PyPI reports 0.2.6 and passes `scripts/check_credential_logging.py`;
  PyPI's integrity API returns a provenance attestation for both files
  naming this repository's `release.yml`; an unpinned `pip install
  pyeconomics` resolves 0.2.6.
- The advisory is published with the gate's affected range, patched
  version 0.2.6, CWE-532 and its CVSS vector, and the CVE is requested if
  the gate asked for one; the id is recorded when GitHub assigns it
  (issue #52).

> Criterion amended 2026-10-05 by the maintainer: GitHub assigns CVE ids
> after a manual review that outlasts the step, so the request closes the
> step and issue #52 records the id.
- Read the Docs `stable` serves 0.2.6 and `latest` builds from
  `legacy/0.2.x`; both URLs return 200.
- The release record is appended to `docs/releases/0.2.6-readiness.md` on
  `main`.
- **Security gate clean** (always the final criterion): gitleaks reported
  no leaks on either PR's commits; publishing used OIDC only; the
  advisory and the release record contain no credential.

---

## Step 5 — Characterize and Archive 0.2.x ✅

**Status:** Complete — PR #53 (2026-10-05)

> **Goal:** Finish preserving 0.2.x, then retire its leftovers. Write
> `scripts/legacy/record_characterization.py`, a PEP 723 script that
> installs the published `pyeconomics==0.2.6` in an isolated
> environment, blocks the network before import, and runs the four rules
> — Taylor, balanced-approach, balanced-approach with shortfalls, and
> first-difference — over a deterministic grid of explicit inputs, plus
> the combined table and each `historical_*` variant over one synthetic
> monthly panel with FRED access stubbed. It writes
> `tests/fixtures/legacy/*.json`, a `manifest.json` holding every
> fixture's SHA-256 and the exact environment, and a `README.md` stating
> the Phase 3 contract; its `--check` mode re-records into a temporary
> directory and fails on any byte difference. Inventory the 44 research
> files in `dev/` and the root-level local scripts, secret-scan them with
> gitleaks, screen notebooks for licensed output, and push the keepers
> the maintainer approves to a new private repository with an `INDEX.md`
> mapping each prototype to its Phase 7 domain. Close the 25 automated
> pull requests as superseded after confirming each changes only
> dependency manifests, delete their branches, delete `dev` and
> `legacy-dev-0.2.6` after checking the archive tags, and disconnect
> Snyk. Parent: 1.1.

**Branch:** `feature/phase01-step5-characterize-archive`

**Deploys:** nothing beyond merge — the private archive repository, the
closed pull requests and the deleted branches are GitHub-side changes
verified in the acceptance criteria.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence Medium       |
| Platform     | Claude Code                                   |
| Effort       | Medium                                        |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding leads — a reproducible, network-blocked
recorder and a fixture format Phase 3 will test against — with agentic
work SECONDARY in the inventory, the private repository and some thirty
branch and pull-request operations; each part is bounded, so the step is
Medium. Opus 5.5 is S in coding and in agentic work. The operator's
`balanced`, `capped` posture runs a Medium step on the surface default,
and Claude Code on the claude.ai Max plan opens on Opus 5.5 at Medium, $0
marginal while the weekly pool has headroom — run as opened. Medium
effort covers the grid design and the keep-or-discard proposals, whose
final calls belong to the maintainer; Thinking stays On. The backup is
GPT-6 Sol on Codex under ChatGPT Pro 5x (S in coding and agentic work).
New conversation per phase-boundary hygiene.

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
       feature/phase01-step5-characterize-archive`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 5 is
       complete. You can now move
       on to Step 6." That
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
       one before Step 6.
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

    THIS STEP ALSO (Bootstrap rule — run the gate by hand
    before every commit; summary lines in the PR body):
    - Secrets: `gitleaks git --pre-commit --staged --redact`
      on every commit, and `gitleaks dir <path> --redact`
      over dev/ and each root-level local script before
      anything is copied to the archive. A finding is
      removed from the copy, or the file is discarded,
      before the push — private is not a reason to keep a
      secret.
    - Licensed data: ROADMAP §5 says licensed market data is
      never committed, notebook outputs included. Notebooks
      that import `tia`, `blpapi`, `xbbg` or `pdblp`, or
      whose outputs show Bloomberg fields or tickers
      (PX_LAST, ` Index`, ` Curncy`, ` Equity`), are archived
      with outputs cleared or not at all. `cache/` (FRED
      content) and `.env` are never archived. Nothing from
      dev/ enters the public repository.
    - Fixtures hold synthetic inputs and 0.2.6's outputs
      only — no FRED, Bloomberg or Coin Metrics value. The
      recorder blocks sockets before importing 0.2.6 and
      sets a non-key-shaped FRED_API_KEY in-process.
    - SAST: `uvx bandit -q -r scripts/legacy` is clean.
    - Dependencies: the recorder's inline pins resolve only
      in its isolated environment and never enter the
      repository's dependency set.
  </security>

  <context>
    pyeconomics. Phase 1. Step 5: Characterize and archive
    0.2.x.

    Current state (as of Phase 1 Step 4):

    - 0.2.6 is on PyPI with attestations; the advisory is
      public; Read the Docs serves 0.2.x from legacy/0.2.x;
      the archive refs are immutable; legacy/0.2.x is
      protected.
    - The 0.2.6 rule API: each current-value rule takes an
      EconomicIndicators (current_fed_rate,
      current_inflation_rate, current_unemployment_rate,
      natural_unemployment_rate,
      long_term_real_interest_rate,
      lagged_unemployment_rate,
      lagged_natural_unemployment_rate, plus FRED series
      ids) and its parameters dataclass
      (TaylorRuleParameters, BalancedApproachRuleParameters
      with use_shortfalls_rule,
      FirstDifferenceRuleParameters: inflation_target,
      alpha, beta, okun_factor, rho, elb=0.125, apply_elb,
      verbose). An indicator left None is fetched from
      FRED; a None current_fed_rate fetches DFEDTARU.
      Results are rounded to 2 dp. The historical_*
      functions call fred_client.fetch_data(series_id) and
      fetch_historical_fed_funds_rate(). Importing the
      package builds fred_client, which needs a key, and
      creates a cache directory.
    - main still ignores *.json and *.csv everywhere (Step 7
      refreshes .gitignore).
    - dev/ holds 44 research files and 35 checkpoints:
      notebooks on Bitcoin factors and stock-to-flow
      (including dev/s2f_models/ with OLS, WLS, GLS, RLM,
      GAM, ARIMA and random-forest variants), FRED access,
      monetary-policy rules, quantity of money and model
      specifications; discounted_cash_flow.py,
      quantity_of_money.py, stock_to_flow.py and
      taylor_rule.py; four CSVs; test_fred_api.bak. Root
      local scripts: generate_tests.py, render_readme.py,
      output.html. dev/wip-media/ exists if Step 1 withheld
      a plot.
    - 25 open automated PRs (#18-#45; 24 Snyk, 1
      Dependabot), their branches, and the unreleased
      branches dev and legacy-dev-0.2.6 remain on origin;
      Snyk is connected.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §4 1.1, Phase 3's 3.6 (how the
      fixtures are used), 7.5 (how the prototypes are used),
      and §5 "Data licensing policy" and "Data
      classification".
    - `git show v0.2.6:pyeconomics/models/monetary_policy/`
      for taylor_rule.py, balanced_approach_rule.py,
      first_difference_rule.py and monetary_policy_rules.py.
    - `git show v0.2.6:` for
      pyeconomics/data/economic_indicators.py,
      pyeconomics/data/model_parameters.py,
      pyeconomics/api/__init__.py and
      pyeconomics/api/fred_api.py.
    - .gitignore on main.
  </context>

  <goal>
    tests/fixtures/legacy/ holds byte-reproducible
    characterization fixtures for every 0.2.x rule; the
    local research is in a private archive with a clean scan
    and an index; only main, legacy/0.2.x and archive
    branches remain on origin; no automated PR is open and
    Snyk no longer watches the repository.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Recorder, scripts/legacy/record_characterization.py:
      - A PEP 723 block: `requires-python = ">=3.12,<3.13"`;
        dependencies `pyeconomics==0.2.6` plus only the pins
        0.2.6 needs to import and run on CPython 3.12 (for
        example a NumPy ceiling its matplotlib pin requires),
        each commented with its reason. Run it with `uv run
        --no-config --script
        scripts/legacy/record_characterization.py`: the
        operator's user-level uv configuration adds a
        package-firewall index ahead of PyPI (Steps 3 and 4).
        A plain `uv venv` has no pip; add `--seed` when a
        recipe calls `python -m pip`.
      - Before importing pyeconomics: replace socket.socket,
        socket.create_connection and socket.getaddrinfo with
        functions that raise; set FRED_API_KEY to a
        non-key-shaped dummy; set MPLBACKEND=Agg.
      - Current-value grid, every indicator explicit so
        nothing is fetched: inflation {-1.0, 0.0, 2.0, 3.5,
        9.0}; unemployment {3.5, 4.2, 6.0, 10.0}; natural
        rate {4.2}; long-run real rate {0.5, 2.0}; current
        fed rate {0.125, 2.5, 5.375}; first-difference lagged
        (unemployment, natural rate) pairs {(4.0, 4.2), (6.5,
        4.2)}; rho {0.0, 0.7, 0.85}; apply_elb {false, true};
        one non-default corner each for alpha, beta,
        okun_factor and inflation_target; balanced-approach
        with use_shortfalls_rule false and true. Each case
        records its full inputs, full parameters and the
        returned value; a case that raises records the
        exception type and message — 0.2.x's behaviour,
        errors included, is the contract.
      - calculate_policy_rule_estimates over a small subset
        of that grid.
      - One synthetic monthly panel, 2000-01 to 2024-12,
        built from closed-form expressions (no randomness),
        fed to each historical_* function by stubbing
        fred_client.fetch_data per series id and
        fetch_historical_fed_funds_rate; DataFrames recorded
        as JSON (orient "split", ISO dates).
      - Output: one JSON file per rule, per historical
        variant and for the combined table; manifest.json
        (pyeconomics version, Python version, every
        installed distribution and version, the grid, the
        recorder's own SHA-256, and a SHA-256 per fixture);
        README.md (layout; units are percent as 0.2.x used
        them; 0.2.x rounds to 2 dp; the Phase 3 contract —
        the rebuilt suite matches these outputs or documents
        each intentional difference).
      - Determinism: sorted keys, fixed separators, LF line
        endings, floats via repr, no timestamps; `--check`
        re-records into a temporary directory and diffs
        byte for byte.
      - Add `!tests/fixtures/**/*.json` to .gitignore until
        Step 7 removes the blanket `*.json` ignore.
    </requirement>

    <requirement>
      Research inventory, built in the scratchpad: one row
      per file in dev/ (checkpoints included), each root
      local script and anything in dev/wip-media/ — path,
      kind, size, one-line summary, Phase 7 domain (quantity
      theory and macro, DCF and equity, crypto and
      stock-to-flow — evidence status `rejected` — policy
      rules, or tooling), data sources and licence notes,
      gitleaks result, licensed-output flag, and a proposed
      decision: keep, keep with outputs cleared, or discard.
      The maintainer approves the decisions in chat or the
      PR before anything is copied.
    </requirement>

    <requirement>
      Private archive: assemble it OUTSIDE the public
      checkout (for example ../pyeconomics-research-archive/);
      clear outputs where decided (`uvx nbstripout`); add the
      approved INDEX.md and a README stating the archive is
      private, all rights reserved, and reference-only per
      ROADMAP 7.5; `gitleaks dir . --redact` must be clean;
      create it with `gh repo create
      <maintainer>/pyeconomics-research-archive --private
      --disable-wiki --disable-issues` (the name confirmed
      with the maintainer; the maintainer's personal
      account); push; confirm `gh repo view
      <maintainer>/pyeconomics-research-archive --json
      visibility` reports PRIVATE. The local dev/ stays in
      place unless the maintainer deletes it after checking
      the archive.
    </requirement>

    <requirement>
      Automated PRs: for each open PR authored by Snyk
      (under the maintainer's account) or Dependabot, record
      `gh pr diff <n> --name-only`; when it lists only
      dependency manifests (Dockerfile, requirements.txt,
      workflow pins), close it with `gh pr close <n>
      --delete-branch --comment "Superseded by the 1.0
      rebuild (docs/roadmap/ROADMAP.md, Phase 1); dependency
      updates now come from Dependabot."`. A PR touching
      anything else goes to the maintainer instead of being
      closed.
    </requirement>

    <requirement>
      Branches: confirm `git rev-parse
      archive/dev-2024-10^{commit}` equals
      `git rev-parse origin/dev` and
      `archive/legacy-dev-0.2.6^{commit}` equals
      origin/legacy-dev-0.2.6; then `git push origin
      --delete dev legacy-dev-0.2.6`; delete the local dev
      and legacy-dev-0.2.6 branches with `git branch -D`;
      `git fetch --prune origin`. Apart from head branches
      of open pull requests (this step's own, or a new
      Dependabot one), `git ls-remote --heads origin` must
      list only main, legacy/0.2.x and archive/0.2-dev-wip.
    </requirement>

    <requirement>
      Snyk: the operator removes this repository from Snyk
      (or uninstalls Snyk's GitHub app for it) and confirms
      in the PR; Dependabot replaces it in Step 8.
    </requirement>

    <requirement>
      Filepath comment: record_characterization.py starts
      with `# scripts/legacy/record_characterization.py`
      above its PEP 723 block; fixture README.md follows the
      docs convention (none).
    </requirement>
  </requirements>
</task>
```

### Step 5 acceptance criteria

- `tests/fixtures/legacy/` holds one JSON file per rule (Taylor,
  balanced-approach, balanced-approach with shortfalls, first-difference),
  one for the combined table, one per historical variant, `manifest.json`
  and `README.md`; the manifest records `pyeconomics 0.2.6`, the Python
  version, every installed distribution, the grid and a SHA-256 per file
  that matches the committed bytes.
- `uv run --script scripts/legacy/record_characterization.py --check`
  exits 0, re-recording byte-identically with sockets blocked.
- Each rule's fixture covers the ELB binding and not binding, rho 0, 0.7
  and 0.85, negative and positive gaps, and the non-default parameter
  corners.
- The private archive repository exists and reports `PRIVATE`; its
  `INDEX.md` holds one row per inventoried file with the maintainer's
  decision; its tree passed `gitleaks dir` clean; and no `dev/` path is
  tracked in the public repository.
- None of the 25 automated pull requests remains open, each closed PR's
  file list is recorded in the PR body, and after Stage 5 `git ls-remote
  --heads origin` returns `main`, `legacy/0.2.x` and
  `archive/0.2-dev-wip` plus, at most, head branches of open pull
  requests — no `dev`, `legacy-dev-0.2.6` or `snyk-fix-*` branch.
- The maintainer confirms Snyk no longer watches the repository.
- **Security gate clean** (always the final criterion): gitleaks reported
  no leaks on the commit or the archive tree; bandit is clean on
  `scripts/legacy`; the fixtures contain no third-party data and no key;
  and no notebook output carrying Bloomberg-licensed data reached any
  repository.

---

## Step 6 — Architecture Decision Records ✅

**Status:** Complete — PR #54 (2026-10-05)

> **Goal:** Write the decisions every later phase builds on into
> `docs/adr/`, each from the recommended default in ROADMAP §4 1.6 and the
> §5 section it implements: `0001-product-boundaries.md`,
> `0002-distributions-and-extras.md`,
> `0003-versioning-and-deprecation.md`,
> `0004-licence-and-contributions.md`, `0005-data-licence-model.md`,
> `0006-web-stack-and-hosting.md`, `0007-documentation-tooling.md`,
> `0009-name-domains-and-trademark.md` and
> `0010-python-support-policy.md`, plus `docs/adr/README.md` (index,
> lifecycle, ADR-0008 reserved for Phase 2's numerical conventions) and
> `docs/adr/template.md`. Each ADR states context, decision drivers, the
> options considered, the decision, its consequences and the check that
> confirms compliance; facts that move — release dates, version floors,
> licences, domain and organization-name availability — are re-verified at
> write time with source and access date. The maintainer accepts or amends
> each ADR in review, and the PR merges only when all nine read Accepted.
> Then run the Phase 1 actions the accepted ADRs trigger: register the
> four domains and — if ADR-0009 keeps the move — create the neutral
> GitHub organization, transfer the repository, and repoint `origin`,
> both trusted publishers and Read the Docs. Parent: 1.6 and Gate G1 (§5
> "Monetization strategy & validation gates").

**Branch:** `feature/phase01-step6-adrs`

**Deploys:** nothing beyond merge — domain registration and the
organization transfer take effect immediately and are verified in the
acceptance criteria.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Astra — Codex · Intelligence Extra High |
| Platform     | Claude Code                                   |
| Effort       | Extra High                                    |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Planning is PRIMARY — nine architecture decisions
that bind every phase after this one — and knowledge SECONDARY, because
each ADR rests on licence, trademark, packaging and support-policy facts
that must be right. Overall complexity is High (cross-cutting scope,
real ambiguity in licensing and naming), which requires S in planning:
Opus 5.5 and Fable 5.1 are both S in planning and knowledge and tie on
coverage, and the selector's cost tie-break picks Opus 5.5 at $20 against
$50 per million output tokens. Claude Code on the claude.ai Max plan runs
it at $0 marginal while the weekly pool has headroom. Effort rises from
Opus 5.5's Medium default to Extra High: High for the complexity, one
rung more for a planning task with cross-cutting scope. Not Max, because
the project roadmap already recommends each default and the step argues
and verifies them rather than discovering them; not Ultracode, because a
document set needs no multi-agent orchestration and the operator
reserves Ultracode for exhaustive sweeps. Thinking stays On. The backup,
GPT-6 Astra on Codex under ChatGPT Pro 5x, is the only non-Anthropic
model rated S in planning. New conversation per phase-boundary hygiene.

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
       feature/phase01-step6-adrs`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 6 is
       complete. You can now move
       on to Step 7." That
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
       one before Step 7.
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

    THIS STEP ALSO (Bootstrap rule — run the gate by hand
    before every commit; summary lines in the PR body):
    - Secrets: `gitleaks git --pre-commit --staged --redact`.
      An ADR may name a registrar and a cost — never an
      account, login, auth code or payment detail.
    - SAST and dependencies: no code and no dependency in
      this step.
    - Organization move: after the transfer, prove every
      dependent configuration by an API read or a real
      round-trip, never by assumption — branch protection,
      rulesets, environments and their reviewers, the
      secrets list, Actions settings — and have the operator
      replace both trusted publishers before any later
      release step relies on them.
  </security>

  <context>
    pyeconomics. Phase 1. Step 6: Architecture decision
    records.

    Current state (as of Phase 1 Step 5):

    - 0.2.6 is released and its advisory published;
      legacy/0.2.x is protected; fixtures are in
      tests/fixtures/legacy/; the research archive is
      private; origin holds only main, legacy/0.2.x and
      archive branches.
    - The repository lives under the maintainer's personal
      handle, which contains the CFA mark — the reason
      ADR-0009 recommends a neutral GitHub organization.
      Trusted publishers on PyPI and TestPyPI name that
      owner; Read the Docs is connected to it.
    - No docs/adr/ exists. ADR-0008 (numerical conventions)
      belongs to Phase 2, where it is first needed.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §4 1.6 (the ADR table and its
      recommended defaults).
    - For 0001: §1 "Where pyeconomics fits" and §6 Out of
      Scope. For 0002: §3 Target Architecture and §5
      "Dependency licences". For 0003: §5 "Release &
      tagging" and "Versioning". For 0004: §5 "Dependency
      licences" and "pyeconomics' own licence, name and
      posture". For 0005: §5 "Data licensing policy" and
      "Data terms". For 0006: §3, §5 "Cost projection" and
      "Release & deployment strategy". For 0007: §4 2.5 and
      5.6. For 0009: §5 "Legal & brand guardrails" and §1's
      note on similarly named projects. For 0010: §2 gap 13
      and §4 1.2.
    - docs/releases/0.2.6-readiness.md (the 0.2.x
      end-of-life statement ADR-0003 must match).
  </context>

  <goal>
    docs/adr/ holds an index, a template and nine ADRs, all
    Accepted by the maintainer, each naming the check that
    enforces it; the actions ADR-0009 triggers in Phase 1
    are done, or the ADR records the maintainer's
    amendment.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      docs/adr/template.md uses MADR-style sections: Status,
      Date, Deciders, Context and problem, Decision drivers,
      Considered options, Decision outcome, Consequences
      (good and bad), Confirmation, More information.
      docs/adr/README.md holds the index (number, title,
      status, date) and the lifecycle: Proposed → Accepted;
      amended in place before acceptance; afterwards changed
      only by a new ADR that supersedes it. It lists ADR-0008
      as reserved for Phase 2.
    </requirement>

    <requirement>
      The nine ADRs, each opening with `Status: Proposed` and
      a date, each covering at least:
      - 0001: pyeconomics is the model layer; it complements
        OpenBB (data plumbing) and QuantEcon (theory
        teaching); it may become a dependency of the
        maintainer's portfolio system, never the reverse;
        the §6 exclusions.
      - 0002: one distribution with extras server, mcp, ai,
        econometrics, plot, one per provider, and all; the
        built web app as a separate pyeconomics-app wheel
        behind [app] (Phase 5); [bloomberg] installs the
        pure-Python side only, blpapi comes from Bloomberg's
        index and is never named in published metadata; the
        core stays pure Python (Pyodide, xlwings Lite).
      - 0003: PEP 440 and SemVer; 1.0.0 at the Phase 5
        launch is the first stable API; one pre-release per
        phase (the §5 milestone table); permanent model ids;
        one minor release of warnings before a removal; the
        tag must equal the pyproject version; 0.2.x reaches
        end-of-life at 1.0.0, as the advisory says.
      - 0004: Apache-2.0 for the public repository from 1.0
        (an express patent grant); 0.2.x stays MIT; hosted
        paid features in a separate private repository; no
        AGPL and no dual licensing; DCO sign-off on every
        commit; a CLA only if an outside contribution might
        ever be relicensed; a permissive-only runtime
        dependency allowlist (MIT, BSD, Apache-2.0, ISC,
        NCSA, PSF) with attributions in NOTICE.
      - 0005: the five source classes and the seven
        enforcement rules of §5 "Data licensing policy".
      - 0006: Astro static output with React islands,
        Tailwind and shadcn/ui; the static site on
        Cloudflare; FastAPI on Cloud Run with Fly.io as
        runner-up; Next.js only if a logged-in app becomes
        the main experience.
      - 0007: Sphinx with MyST-NB, sphinx-autoapi and
        sphinx-gallery on Read the Docs; Sybil for Markdown
        doctests; revisit Zensical at its 1.0 (Material for
        MkDocs is in maintenance mode).
      - 0009: register pyeconomics.com, .org, .io and .dev
        before any announcement; a clearance search before
        any filing; the merely-descriptive risk and the
        coined-brand option for the hosted product; a USPTO
        intent-to-use filing in classes 9 and 42 at about
        $1,000 in government fees plus attorney fees (TBD);
        the move to a neutral GitHub organization; the
        distinction from davidrpugh/pyeconomics and
        pyecon.org; no "CFA" in any name.
      - 0010: requires-python >=3.12 (the NumPy and SciPy
        floors that force it); CI on 3.12, 3.13 and 3.14,
        plus 3.15 once final (due 2026-10-09); floors rise
        with NumPy and SciPy under SPEC 0.
      Every time-sensitive fact carries a source URL and an
      access date; anything that cannot be verified reads
      TBD, never a guess.
    </requirement>

    <requirement>
      Each ADR's Confirmation section names the check that
      enforces it and the step that builds that check — for
      example ADR-0010 → requires-python (Step 7) and the CI
      matrix (Step 10); ADR-0004 → the licence allowlist
      (Step 8) and the DCO check (Step 10); ADR-0003 → the
      release workflow's tag-equals-version check (Step 10).
    </requirement>

    <requirement>
      Acceptance protocol: open the PR (Stage 3) with all
      nine ADRs Proposed and ask the maintainer to review
      each. Apply amendments in follow-up commits. Flip an
      ADR's Status to `Accepted` with the date only on the
      maintainer's explicit word for that ADR. The PR
      merges only when all nine read Accepted and the index
      matches.
    </requirement>

    <requirement>
      Actions triggered by ADRs accepted as written (an
      amendment changes or cancels them; record which):
      - ADR-0009 domains: the operator registers the four
        domains; the ADR's Consequences records the
        registrar and renewal month only; verify each with
        an RDAP lookup or `nslookup -type=NS`.
      - ADR-0009 organization: confirm the name is free
        (`gh api orgs/<name>` returns 404 before creation);
        the operator creates it (free plan, 2FA required for
        members) and transfers the repository; then
        `git remote set-url origin
        https://github.com/<org>/pyeconomics.git`; confirm
        `gh repo view --json nameWithOwner`, that the old
        URL redirects, and that branch protection, rulesets,
        environments with the `pypi` reviewer, the secrets
        list and Actions settings came across — recreating
        anything that did not; the operator adds trusted
        publishers for the new owner on PyPI and TestPyPI
        and removes the old ones, and reconnects Read the
        Docs, whose next `latest` build must succeed.
    </requirement>

    <requirement>
      Filepath comment: docs/adr/ Markdown follows the docs
      convention and carries no filepath line.
    </requirement>
  </requirements>
</task>
```

### Step 6 acceptance criteria

- `docs/adr/` holds `README.md`, `template.md` and the nine ADRs; each ADR
  reads `Status: Accepted` with a date, and the index lists 0001–0007,
  0009 and 0010 as Accepted and 0008 as reserved for Phase 2.
- Every ADR has Context, Decision drivers, Considered options, Decision,
  Consequences and Confirmation sections, and every time-sensitive fact
  carries a source and access date or reads TBD.
- Each ADR's Confirmation names its enforcing check and the step that
  builds it.
- The maintainer's acceptance or amendment of each ADR is visible in the
  PR conversation.
- The four domains show a registration in RDAP — or ADR-0009 records the
  maintainer's amendment.
- `gh repo view --json nameWithOwner` names the new organization, the old
  URL redirects, `git remote -v` points at it, protection, rulesets,
  environments and the `pypi` reviewer are verified, both trusted
  publishers are replaced (operator-confirmed), and Read the Docs builds
  `latest` — or ADR-0009 records the amendment that keeps the personal
  account.
- **Security gate clean** (always the final criterion): gitleaks reported
  no leaks; no ADR or PR contains an account detail, auth code or payment
  detail; the post-move configuration was verified by API reads, not
  assumed.

---

## Step 7 — Repository Reset and Package Skeleton ✅

**Status:** Complete — PR #59 (2026-10-07)

> **Goal:** Replace 0.2.x on `main` with the 1.0 skeleton the accepted
> ADRs describe. Remove the 0.2.x package, its tests (keeping
> `tests/fixtures/legacy/`), examples, media, Sphinx sources and wishlist
> pages, `setup.py`, `requirements.txt`, `__version__.py`, `pytest.ini`,
> `MANIFEST.in`, `.coveragerc`, `.readthedocs.yml`, the JupyterLab
> `Dockerfile`, `.dockerignore` and `start.sh`, `test_import.py` and the
> three 0.2.x workflows — all preserved on `legacy/0.2.x` and the archive
> tags — and move CHANGELOG, CODE_OF_CONDUCT and CONTRIBUTING from
> `markdown/` to the root. Create `src/pyeconomics/__init__.py` (version
> from `importlib.metadata`) and `py.typed`, `tests/unit/test_version.py`
> and a `web/README.md` placeholder; write one PEP 621 `pyproject.toml` on
> `uv_build` with version `1.0.0.dev1`, `requires-python = ">=3.12"`,
> `license = "Apache-2.0"` with `LICENSE` and `NOTICE`, no runtime
> dependencies yet, the ADR-0002 extras skeleton and PEP 735 groups;
> commit `uv.lock` and an exported `pylock.toml`; normalise text to LF
> with `.gitattributes`; and refresh `.editorconfig` and `.gitignore`.
> Prove it with `uv sync --locked`, `uv build`, `twine check --strict`,
> an artifact allowlist and a clean-venv import. Parent: 1.2.

**Branch:** `feature/phase01-step7-repo-reset`

**Deploys:** nothing beyond merge — Read the Docs already serves 0.2.x
from `legacy/0.2.x` (Step 4), so deleting the Sphinx sources from `main`
changes no published page.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence High         |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY — a repository-wide restructure
and a packaging configuration — and knowledge SECONDARY, because PEP 621,
PEP 639, PEP 735, PEP 751 and the `uv_build` backend must be applied
exactly. Scope is cross-cutting (every file on `main` moves or goes), so
overall complexity is High and S in coding is required; Opus 5.5 and
Fable 5.1 are both S in coding and knowledge and tie on coverage, and the
selector's cost tie-break picks Opus 5.5 ($20 against $50 per million
output tokens). Claude Code on the claude.ai Max plan runs it at $0
marginal while the weekly pool has headroom. Effort rises from the Medium
default to High for the cross-cutting scope; it stays below Extra High
because the decisions are made (ADR-0002, -0003, -0004 and -0010) and the
work applies them. Thinking stays On. The backup is GPT-6 Sol on Codex
under ChatGPT Pro 5x (S in coding, top cross-provider coverage). New
conversation per phase-boundary hygiene.

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
       feature/phase01-step7-repo-reset`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 7 is
       complete. You can now move
       on to Step 8." That
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
       one before Step 8.
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

    THIS STEP ALSO (Bootstrap rule — the last step that runs
    the gate by hand; summary lines in the PR body):
    - Secrets: `gitleaks git --pre-commit --staged --redact`
      on every commit, and `gitleaks dir . --redact` over
      the final tree.
    - SAST: `uvx bandit -q -r src` is clean.
    - Dependencies: `uv_build` and the test group's pytest
      are the only new packages; `uvx pip-audit` over the
      exported pylock.toml (or the synced environment) is
      clean.
    - Artifacts: the wheel and the sdist contain only
      allowlisted paths — never `.env`, `planning/`, `dev/`,
      `cache/`, `docs/roadmap/`, `scripts/legacy/` or the
      legacy fixtures.
  </security>

  <context>
    pyeconomics. Phase 1. Step 7: Repository reset and
    package skeleton.

    Current state (as of Phase 1 Step 6):

    - Nine ADRs are Accepted in docs/adr/ — read their
      decisions, amendments included: 0002 (extras), 0003
      (versioning), 0004 (Apache-2.0, DCO, licence
      allowlist), 0010 (Python >=3.12). The repository may
      now live in a neutral organization (ADR-0009); take
      OWNER/REPO from `gh repo view --json nameWithOwner`.
    - main is the 0.2.5 tree plus docs/roadmap/, planning/,
      docs/releases/, docs/adr/, scripts/legacy/ and
      tests/fixtures/legacy/. Its 0.2.x paths: pyeconomics/,
      tests/ (old suite), examples/, media/, markdown/,
      docs/ Sphinx sources (conf.py, *.rst including the
      roadmap*.rst wishlist, Makefile, make.bat,
      create_roadmap_files.bat, _static/, _templates/),
      setup.py, requirements.txt, __version__.py,
      pytest.ini, MANIFEST.in, .coveragerc,
      .readthedocs.yml, Dockerfile, .dockerignore, start.sh,
      test_import.py, and .github/workflows/tests.yml,
      docs.yml and release.yml.
    - Read the Docs serves 0.2.x from legacy/0.2.x (Step 4).
      Phase 7 reads the wishlist from legacy/0.2.x.
    - .gitignore still ignores *.json and *.csv, with Step
      5's fixture negation; .gitattributes holds
      `* text=auto` only.
    - uv 0.12.x is installed; the uv_build version range is
      read from uv's documentation at write time.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §3 (the repository layout)
      and §4 1.2.
    - docs/adr/0002, 0003, 0004 and 0010.
    - pyproject.toml, .gitignore, .gitattributes,
      .editorconfig, LICENSE, README.md and markdown/*.md on
      main.
    - tests/fixtures/legacy/README.md (what must survive the
      reset).
  </context>

  <goal>
    main holds only the 1.0 skeleton and the preserved
    Phase 1 records: src/pyeconomics with its version from
    package metadata, one pyproject.toml on uv_build,
    uv.lock and pylock.toml, Apache-2.0 LICENSE and NOTICE,
    LF-normalised text, and a build whose artifacts carry
    only allowlisted files.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff check: Read the Docs still serves 0.2.x
      (`stable` and `latest` return 200 with 0.2.x content).
      If not, stop — Step 4's acceptance is not met.
    </requirement>

    <requirement>
      Delete with `git rm -r`: pyeconomics/; every path
      under tests/ except tests/fixtures/legacy/; examples/;
      media/; docs/_static/, docs/_templates/, docs/*.rst,
      docs/conf.py, docs/Makefile, docs/make.bat and
      docs/create_roadmap_files.bat; setup.py;
      requirements.txt; __version__.py; pytest.ini;
      MANIFEST.in; .coveragerc; .readthedocs.yml;
      Dockerfile; .dockerignore; start.sh; test_import.py;
      and .github/workflows/tests.yml, docs.yml and
      release.yml (the 1.x pipeline arrives in Step 10;
      legacy/0.2.x keeps its own). Keep
      .github/dependabot.yml (Step 8 rewrites it),
      docs/roadmap/, docs/adr/, docs/releases/, planning/,
      scripts/legacy/ and tests/fixtures/legacy/.
    </requirement>

    <requirement>
      `git mv` markdown/CHANGELOG.md, CODE_OF_CONDUCT.md and
      CONTRIBUTING.md to the root (Step 11 rewrites them).
      Remove markdown/FRED_API_CONFIGURATION.md: it is a
      0.2.x usage guide that stays on legacy/0.2.x, and
      Phase 3 writes the 1.0 data-sources guide. Record this
      refinement of 1.2's "move markdown/*.md" in the PR
      body.
    </requirement>

    <requirement>
      New files:
      - src/pyeconomics/__init__.py: a module docstring;
        `__version__` set from
        `importlib.metadata.version("pyeconomics")`;
        `__all__ = ["__version__"]`.
      - src/pyeconomics/py.typed (empty).
      - tests/unit/test_version.py: `__version__` equals the
        installed distribution's version and starts with
        "1.0.0".
      - web/README.md: a placeholder naming Phase 5 and
        ADR-0006.
      - LICENSE: the Apache License 2.0 text, verbatim.
      - NOTICE: "pyeconomics", a copyright line for
        2024-2026 "Nathan Ramos, CFA" (no ®), and a line
        that releases up to 0.2.x remain MIT-licensed.
      - README.md: an interim page — 1.0 is being rebuilt;
        `pip install pyeconomics` installs 0.2.6 (MIT,
        legacy/0.2.x); links to docs/roadmap/ROADMAP.md and
        the licence. Step 11 writes the full README.
    </requirement>

    <requirement>
      pyproject.toml (PEP 621, 639, 735):
      - [build-system]: requires `uv_build` pinned to the
        range uv documents for the installed uv;
        build-backend `uv_build`; module name pyeconomics
        under the default src root.
      - [project]: name, version "1.0.0.dev1", description,
        readme, requires-python ">=3.12", license
        "Apache-2.0", license-files ["LICENSE", "NOTICE"],
        authors (Nathan Ramos, CFA, with the public
        address), keywords, classifiers (Development Status
        2 - Pre-Alpha, Python 3.12/3.13/3.14, Typing ::
        Typed, OS Independent), dependencies [] and
        [project.urls].
      - [project.optional-dependencies]: the ADR-0002 extras
        as empty lists (server, mcp, ai, econometrics, plot,
        all), each filled by the phase that needs it; [app]
        and [bloomberg] are added only when their packages
        exist (Phases 5 and 6).
      - [dependency-groups]: test = ["pytest"]; dev includes
        test; docs = []. Step 9 completes them.
    </requirement>

    <requirement>
      Lock and version: `uv lock --no-config`; `uv export
      --no-config --format pylock.toml --output-file
      pylock.toml`; `uv version` prints 1.0.0.dev1. Both
      lock files are committed and name no index but
      https://pypi.org/simple. `--no-config` is required: the
      operator's user-level uv configuration adds a
      package-firewall index ahead of PyPI, and a plain
      `uv lock` writes that private URL into both files
      (found in this step).
    </requirement>

    <requirement>
      Text and ignores:
      - .gitattributes: `* text=auto eol=lf` plus binary
        patterns (images, archives, wheels); then
        `git add --renormalize .`; `git ls-files --eol`
        shows no CRLF in the index for any text file.
      - .editorconfig: LF, UTF-8, final newline, trimmed
        trailing whitespace except Markdown; 4-space Python
        and TOML; 2-space YAML and JSON.
      - .gitignore, rewritten: Python, uv and tool caches
        (.venv/, dist/, build/, .ruff_cache/, .mypy_cache/,
        .pytest_cache/, .hypothesis/, .benchmarks/,
        htmlcov/, .coverage*, coverage.xml); .env and
        .env.*; dev/; cache/; .worktrees/;
        planning/user-context.md; the local scripts
        generate_tests.py, render_readme.py and output.html;
        and NO blanket `*.json` or `*.csv` line (drop Step
        5's negation with it).
    </requirement>

    <requirement>
      Verify on the maintainer's machine and paste the
      results into the PR body (main has no CI until Step
      10): `uv sync --locked`; `uv run pytest`; `uv build`;
      `uvx twine check --strict dist/*`; list both
      artifacts' members — the wheel holds pyeconomics/
      __init__.py and py.typed plus dist-info with LICENSE
      and NOTICE; the sdist holds PKG-INFO, pyproject.toml,
      README.md, LICENSE, NOTICE and src/pyeconomics/ only,
      plus the pyproject.toml.orig that uv_build 0.12 always
      writes, allowed only when it is byte-identical to the
      committed pyproject.toml — and fail on any other path;
      install the wheel into a clean venv and, from a
      directory outside the checkout (a stale
      `pyeconomics.egg-info` at the repository root shadows
      the wheel's metadata), print `pyeconomics.__version__`
      (1.0.0.dev1).
    </requirement>

    <requirement>
      Filepath comment: every new Python, TOML and config
      file starts with `# <repo-relative path>` (above the
      docstring in Python); Markdown follows the docs
      convention.
    </requirement>
  </requirements>
</task>
```

### Step 7 acceptance criteria

- None of the 0.2.x paths listed in the task is tracked on `main`
  (`git ls-files` check); `tests/fixtures/legacy/`, `scripts/legacy/`,
  `docs/roadmap/`, `docs/adr/`, `docs/releases/` and `planning/` are
  intact.
- `src/pyeconomics/__init__.py` takes `__version__` from
  `importlib.metadata`, and `src/pyeconomics/py.typed` exists.
- `pyproject.toml` declares `build-backend = "uv_build"`, version
  `1.0.0.dev1`, `requires-python = ">=3.12"`, `license = "Apache-2.0"`
  with `LICENSE` and `NOTICE`, no runtime dependencies, the ADR-0002
  extras and PEP 735 groups; `uv.lock` and `pylock.toml` are committed
  and current.
- `uv sync --locked`, `uv run pytest`, `uv build` and `uvx twine check
  --strict dist/*` all pass; both artifacts contain only allowlisted
  paths; a clean-venv install of the wheel prints `1.0.0.dev1`.
- `git ls-files --eol` shows no CRLF text in the index; `.gitignore`
  holds `.worktrees/`, `planning/user-context.md`, `dev/` and `.env` and
  no blanket `*.json` or `*.csv` line.
- `LICENSE` is the Apache-2.0 text; no `®` appears in `LICENSE`, `NOTICE`
  or `pyproject.toml`.
- **Security gate clean** (always the final criterion): gitleaks reported
  no leaks on the commits or the final tree; bandit is clean on `src`;
  `pip-audit` over the locked set is clean; neither artifact contains a
  secret, a personal planning file or legacy material.

---

## Step 8 — Per-Step Security Gate ✅

**Status:** Complete — PR #60 (2026-10-07)

> **Goal:** Make security a gate on every commit, locally and in CI. Add
> `.pre-commit-config.yaml`, run by prek from the `dev` dependency group
> and installed with `prek install`: gitleaks (with `.gitleaks.toml`
> extending the default rules); bandit (configured in `pyproject.toml`);
> semgrep with the project rules in `.semgrep/rules/` — no `pickle`,
> `marshal` or `shelve`, no `eval` or `exec`, no `yaml.load` without a
> safe loader, and no logging call whose arguments include a variable
> named like a key, token, secret, password or credential — each rule
> tested by `semgrep --test` against `.semgrep/tests/`; `pip-audit
> --locked` over `pylock.toml`; a licence allowlist check over the locked
> runtime set (MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, NCSA,
> PSF-2.0); and `no-commit-to-branch` for `main`. Mirror the same hooks in
> `.github/workflows/security.yml` as required checks; add trufflehog,
> zizmor and dependency review there, CodeQL in `codeql.yml` and OpenSSF
> Scorecard in `scorecard.yml`, with harden-runner first in every job;
> rewrite `.github/dependabot.yml` for the `uv` and `github-actions`
> ecosystems; add `.github/pull_request_template.md` with its
> sensitive-data checklist; switch on secret scanning with push
> protection, Dependabot alerts and security updates, and private
> vulnerability reporting; confirm 2FA; and prove the gate blocks a
> planted fake credential and a `pickle.loads` call in a throwaway
> commit. Parent: 1.4.

**Branch:** `feature/phase01-step8-security-gate`

**Deploys:** nothing beyond merge — the GitHub security settings take
effect when switched on and the security workflows run from the merge
onward; both are verified in the acceptance criteria.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence Extra High   |
| Platform     | Claude Code                                   |
| Effort       | Extra High                                    |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** This is the project's core control (ROADMAP §5
"Per-step security gate"): coding is PRIMARY — hook configuration, custom
semgrep rules with tests, and five workflows — and knowledge SECONDARY,
because each tool's fail-closed behaviour, its CI twin and GitHub's
security settings must be exactly right. Overall complexity is High, so S
in coding is required; Opus 5.5 and Fable 5.1 are both S in coding and
knowledge and tie on coverage, and the cost tie-break picks Opus 5.5.
Claude Code on the claude.ai Max plan runs it at $0 marginal while the
weekly pool has headroom. Effort rises from the Medium default to Extra
High because the step is High-complexity work with multi-step
verification — proving the gate blocks a planted credential and an
unsafe call, locally on Windows and in CI on Ubuntu — and a chain of
reasoning across many files; Max is not warranted because the tools are
known and the step assembles rather than invents them. Thinking stays
On. The backup is GPT-6 Sol on Codex under ChatGPT Pro 5x. New
conversation per phase-boundary hygiene.

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
       feature/phase01-step8-security-gate`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 8 is
       complete. You can now move
       on to Step 9." That
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
       one before Step 9.
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

    THIS STEP ALSO:
    - This step builds the gate, so its commits before the
      hooks are installed run the four checks by hand
      (Bootstrap rule); once `prek install` has run, every
      commit runs them through the hook, and none may use
      SKIP or --no-verify.
    - The planted fake credential and the `pickle.loads`
      call live only on a throwaway branch that is never
      pushed and is deleted afterwards; the credential is a
      documented test pattern, never a real key.
    - Workflow changes are security-relevant diffs:
      top-level `permissions: {}`; per-job grants only
      (`security-events: write` for SARIF uploads,
      `id-token: write` for Scorecard publishing only); no
      `pull_request_target`; SHA-pinned actions;
      `persist-credentials: false`; zizmor reports nothing
      above Low.
  </security>

  <context>
    pyeconomics. Phase 1. Step 8: Per-step security gate.

    Current state (as of Phase 1 Step 7):

    - main holds the 1.0 skeleton: src/pyeconomics,
      pyproject.toml on uv_build (version 1.0.0.dev1, no
      runtime dependencies, test and dev groups), uv.lock,
      pylock.toml, Apache-2.0 LICENSE and NOTICE. main has
      no workflow (Step 7 deleted the 0.2.x ones), its
      .github/dependabot.yml covers github-actions only,
      and no required status checks exist (Bootstrap
      rule).
    - Repository security settings are off: secret
      scanning, push protection, Dependabot security
      updates, private vulnerability reporting. Dependabot
      alerts are on (Step 5 found 15 open, all raised by the
      0.2.x requirements.txt and Dockerfile that Step 7
      deletes); confirm they have closed, and dismiss any
      left on a deleted manifest as such.
    - Repository webhooks (Step 5 audit): Read the Docs
      (keep), Code Climate (id 479620223, a 0.2.x leftover:
      remove it unless this step adopts the service), and
      Snyk until the operator disconnects it in Step 5.
      2FA on GitHub and PyPI is unconfirmed for Phase 1.
    - Local tools: gitleaks 8.30.1 (winget), uv 0.12.x;
      prek is not installed yet; whether semgrep runs
      natively on Windows is TBD until this step tries it.
    - ADR-0004 fixes the runtime licence allowlist and
      requires DCO sign-off; ROADMAP §5 fixes the gate's
      four checks and its CI mirror.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §4 1.4; §5 "Security & privacy
      strategy" (data classification, threat model,
      per-step security gate, controls by layer,
      vulnerability handling) and "Dependency licences".
    - docs/adr/0004-licence-and-contributions.md.
    - pyproject.toml, uv.lock, pylock.toml,
      .github/dependabot.yml.
  </context>

  <goal>
    Every commit passes a fail-closed local gate — secrets,
    SAST with project rules, dependency audit, licence
    allowlist — that CI re-runs as required checks alongside
    trufflehog, zizmor, dependency review, CodeQL and
    Scorecard; GitHub's security features are on; and the
    gate is proven to block a planted credential and an
    unsafe call.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      .pre-commit-config.yaml, run by prek (added to the dev
      group; `uv run prek install`), every hook rev pinned:
      - gitleaks from the gitleaks repository. If its golang
        hook cannot build under prek on Windows, use its
        `gitleaks-system` hook and document the gitleaks
        install for contributors (Step 11 adds it to
        CONTRIBUTING).
      - bandit (`-c pyproject.toml`).
      - semgrep: a local hook running `semgrep scan --config
        .semgrep/rules --error --metrics=off`. If semgrep
        does not run natively on Windows, add
        scripts/checks/forbidden_patterns.py, an AST check
        for the same four rules, as a local hook so the
        local gate never weakens silently; semgrep stays in
        CI.
      - pip-audit: `pip-audit --locked` over pylock.toml;
        osv-scanner on uv.lock is the fallback ROADMAP §5
        names.
      - Lock index: a local hook (and its CI mirror) that
        fails if uv.lock or pylock.toml names any index or
        file URL outside https://pypi.org/simple and
        https://files.pythonhosted.org. The operator's
        user-level uv configuration adds a private
        package-firewall index, so a `uv lock` or `uv add`
        run without `--no-config` writes its URL into both
        lock files (Step 7). Run every lock-changing uv
        command with `--no-config`.
      - Licence allowlist: scripts/checks/licences.py reads
        the runtime closure from uv.lock (empty today) and
        each package's licence metadata from the synced
        environment, and fails on any licence outside the
        ADR-0004 allowlist or with no licence metadata. It
        also fails on any package ADR-0004 excludes by name
        (FinancePy, rateslib, getfactormodels, dbnomics,
        full_fred), whatever its metadata says. ADR-0004's
        only escape hatch is a reviewed exceptions file
        beside the script, each entry naming the package,
        its licence and why; it starts empty.
      - `no-commit-to-branch` with `--branch main`.
      `uv run prek run --all-files` must pass.
    </requirement>

    <requirement>
      .semgrep/rules/ holds four rules — unsafe
      deserialization (pickle, marshal, shelve), dynamic code
      (eval, exec), unsafe YAML (yaml.load without
      SafeLoader), and credential logging (a logging or
      print call whose arguments, f-string parts included,
      reference a name matching
      key|token|secret|password|passwd|credential,
      case-insensitive) — and .semgrep/tests/ holds annotated
      `ruleid:` and `ok:` cases for each; the `semgrep-test`
      hook passes. (Step 8 found that the bare `semgrep
      --test .semgrep/` pairs nothing when rules and tests
      sit in separate folders, and exits 0 on "No unit tests
      found". The hook runs scripts/checks/semgrep_tests.py,
      which runs `semgrep --test --config <rule> <test>` per
      pair and fails on any rule without both cases.)
    </requirement>

    <requirement>
      .gitleaks.toml extends the default configuration; any
      allowlist entry names a path that holds only
      documented fake patterns, with a comment saying why.
    </requirement>

    <requirement>
      .github/workflows/security.yml, on pull_request and on
      push to main, `permissions: {}` at the top: jobs
      gate-secrets, gate-sast (bandit, semgrep and
      `semgrep --test`), gate-deps and gate-licences each
      run the matching prek hook with `uv run prek run
      <hook-id> --all-files`, so local and CI cannot drift;
      plus trufflehog (verified and unknown results over the
      PR's commits or the push), zizmor (every workflow;
      fails above Low) and dependency-review (pull requests
      only; fails on high severity and on licences outside
      the allowlist). Every job starts with harden-runner,
      checks out with `persist-credentials: false`, and uses
      setup-uv where Python runs.
    </requirement>

    <requirement>
      .github/workflows/codeql.yml (languages python and
      actions; push to main, pull requests, weekly) and
      .github/workflows/scorecard.yml (push to main and
      weekly; results published; SARIF uploaded), each with
      harden-runner first and minimal permissions.
    </requirement>

    <requirement>
      .github/dependabot.yml covers the `uv` ecosystem
      (directory "/", weekly, minor and patch grouped) and
      `github-actions` (weekly), with commit-message
      prefixes `chore(deps)` and `chore(ci)` so Dependabot's
      PR titles pass Step 10's Conventional Commits check.
    </requirement>

    <requirement>
      .github/pull_request_template.md: roadmap step,
      summary, test plan, screenshots for UI, breaking
      changes, rollback plan (naming the ROADMAP §5 rollback
      it uses), a licence check for any new dependency or
      data source, the sensitive-data checklist (no key in
      logs, manifests, caches, exceptions or exports; no
      licensed data in fixtures or notebooks; no secret in a
      client bundle; least-privilege scopes; workflow
      changes reviewed), and a gate-bypass field that reads
      "none" or carries the justification.
    </requirement>

    <requirement>
      GitHub settings with `gh api` (payloads shown first):
      `PATCH repos/OWNER/REPO` enabling secret_scanning and
      secret_scanning_push_protection under
      security_and_analysis; `PUT .../vulnerability-alerts`;
      `PUT .../automated-security-fixes`;
      `PUT .../private-vulnerability-reporting`. 2FA:
      `gh api user --jq .two_factor_authentication` (or the
      operator confirms on github.com if the field is not
      returned); the operator confirms PyPI 2FA; if the
      repository is in an organization, the organization
      requires 2FA.
    </requirement>

    <requirement>
      Prove the gate on a throwaway branch that is never
      pushed (`git switch -c throwaway/gate-proof`): a
      commit adding a file with a documented fake AWS
      access-key pattern is blocked by the gitleaks hook (use
      the fake AKIA key in gitleaks' own test fixtures,
      testdata/repos/nogit/main.go: gitleaks allowlists AWS's
      documented `…EXAMPLE` key by design, so it passes); a
      commit adding `pickle.loads(b"")` under src/ is
      blocked by semgrep and bandit. Paste both redacted
      outputs into the PR body, then `git switch -` and
      `git branch -D throwaway/gate-proof`.
    </requirement>

    <requirement>
      Required checks: once security.yml and codeql.yml have
      reported green on this PR, add gate-secrets,
      gate-sast, gate-deps, gate-licences, trufflehog,
      zizmor, dependency-review and the CodeQL analyses to
      main's required status checks with `strict: true`.
    </requirement>

    <requirement>
      Filepath comment: every new YAML and Python file starts
      with `# <repo-relative path>`; the PR template follows
      the docs convention.
    </requirement>
  </requirements>
</task>
```

### Step 8 acceptance criteria

- `.pre-commit-config.yaml` runs gitleaks, bandit, semgrep (or its
  documented portable twin on Windows), `pip-audit --locked`, the
  licence allowlist check and `no-commit-to-branch`, all pinned, and
  `uv run prek run --all-files` passes on Windows and in CI.
- The `semgrep-test` hook (`scripts/checks/semgrep_tests.py`, which runs
  `semgrep --test` per rule; the bare `semgrep --test .semgrep/` passes
  vacuously) passes, with `ruleid:` and `ok:` cases for each of the four
  project rules.
- The throwaway-branch proof is in the PR body: the hook blocked the
  planted fake credential and the `pickle.loads` call, and neither commit
  was pushed.
- `security.yml`, `codeql.yml` and `scorecard.yml` exist; every job
  starts with harden-runner; zizmor reports nothing above Low; CodeQL and
  Scorecard have run on `main` after the merge.
- `.github/dependabot.yml` covers `uv` and `github-actions`, and the PR
  template carries the sensitive-data checklist, rollback plan and
  licence check.
- `gh api repos/OWNER/REPO` shows secret scanning and push protection
  enabled; Dependabot alerts, security updates and private vulnerability
  reporting are on; 2FA is confirmed for GitHub and PyPI.
- `main`'s required checks include gate-secrets, gate-sast, gate-deps,
  gate-licences, trufflehog, zizmor, dependency-review and CodeQL, with
  strict status checks.
- **Security gate clean** (always the final criterion): this step's own
  commits passed the gate it builds; the security workflow is green on
  the PR; no fake credential or unsafe call reached a pushed branch.

---

## Step 9 — Quality Toolchain ✅

**Status:** Complete — PR #63 (2026-10-07)

> **Goal:** Give the skeleton the strict toolchain every later model is
> held to. Complete the PEP 735 groups (`test`: pytest, pytest-cov,
> hypothesis, syrupy, pytest-benchmark and pytest-socket; `dev`: the
> test group plus ruff, mypy, pydantic for the mypy plugin until Phase 2
> makes it a runtime dependency, pyright, ty and prek) and configure them
> in `pyproject.toml`: ruff lint and format with `select = ["ALL"]` and a
> short, commented ignore list (so the bandit `S`, NumPy `NPY` and pandas
> `PD` families are on); mypy `strict` with the `pydantic.mypy` plugin as
> the gate; pyright strict for editors; ty as a non-blocking check;
> pytest with `--strict-markers`, `--strict-config`, `--doctest-modules`,
> `--import-mode=importlib` and `--disable-socket`, warnings as errors,
> hypothesis profiles in `tests/conftest.py`, and branch coverage with a
> 95% floor. Add `tests/unit/test_network_blocked.py` and a module
> doctest in `src/pyeconomics/__init__.py`, and wire ruff, mypy and the
> lockfile checks into prek beside Step 8's gate. Parent: 1.3.

**Branch:** `feature/phase01-step9-quality-toolchain`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence Medium       |
| Platform     | Claude Code                                   |
| Effort       | Medium                                        |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY — tool configuration and a handful
of smoke tests — with agentic work SECONDARY in running each tool on
Windows and confirming it fails closed; the configurations are known
patterns applied to a near-empty package, so the step is Medium. Opus 5.5
is S in coding. Under the operator's `balanced`, `capped` posture a
Medium step runs on the surface default, and Claude Code on the
claude.ai Max plan opens on Opus 5.5 at its Medium default, $0 marginal
while the weekly pool has headroom — run as opened. Medium effort is
enough to choose a strict ruff selection and justify each ignore;
Thinking stays On. The backup is GPT-6 Sol on Codex under ChatGPT Pro
5x. New conversation per phase-boundary hygiene.

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
       feature/phase01-step9-quality-toolchain`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 9 is
       complete. You can now move
       on to Step 10." That
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
       one before Step 10.
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

    THIS STEP ALSO:
    - Step 8's gate runs on every commit through prek; no
      SKIP and no --no-verify.
    - ruff's `S` (flake8-bandit) family is selected, so the
      linter and bandit both flag unsafe calls.
    - pytest-socket's `--disable-socket` is the suite-wide
      default: a test that needs the network must opt in by
      marker, and none does in Phase 1.
    - Every new tool joins the dev or test group and passes
      `pip-audit --locked`.
  </security>

  <context>
    pyeconomics. Phase 1. Step 9: Quality toolchain.

    Current state (as of Phase 1 Step 8):

    - main holds the 1.0 skeleton (src/pyeconomics with
      __version__, py.typed, tests/unit/test_version.py),
      pyproject.toml on uv_build with test = ["pytest"] and
      a dev group holding prek, uv.lock and pylock.toml.
    - The security gate runs through prek on every commit
      and in security.yml, codeql.yml and scorecard.yml;
      its checks are required on main. No lint, type or
      test workflow exists yet (Step 10).
    - ROADMAP §4 Phase 2 will lean on this toolchain: strict
      typing on core/, hypothesis property tests, syrupy
      snapshots, golden fixtures, branch coverage of at
      least 95% on core/ and 90% on models/.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §4 1.3 and Phase 2's 2.1-2.4.
    - docs/adr/0010-python-support-policy.md.
    - pyproject.toml, .pre-commit-config.yaml, tests/, and
      src/pyeconomics/__init__.py.
  </context>

  <goal>
    `uv run ruff format --check`, `uv run ruff check`,
    `uv run mypy` and `uv run pytest` pass on a strict
    configuration with sockets disabled, doctests collected
    and branch coverage enforced; prek runs format, lint,
    types and lockfile checks beside the security gate.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Dependency groups: test = pytest, pytest-cov,
      hypothesis, syrupy, pytest-benchmark, pytest-socket;
      dev = the test group plus ruff, mypy, pydantic (for
      the mypy plugin, until Phase 2 moves it to the runtime
      dependencies), pyright, ty and prek, keeping Step 8's
      `packaging` (scripts/checks/licences.py imports it).
      Re-lock and re-export pylock.toml with `uv lock
      --no-config` and
      `uv export --no-config …`: without it the operator's
      package-firewall index lands in both lock files
      (Step 7).
    </requirement>

    <requirement>
      ruff: target-version py312; line-length 88; lint
      `select = ["ALL"]` with an ignore list limited to the
      formatter conflicts (COM812, ISC001) and one
      docstring-convention pair, each commented; pydocstyle
      convention numpy; per-file ignores for tests (S101 and
      the D rules) only; the formatter at its defaults.
      From Step 8: exclude `.semgrep/tests/` (deliberately
      unsafe semgrep test cases) from ruff, mypy, pyright
      and ty, as the bandit and semgrep hooks and CodeQL
      already do. scripts/checks/*.py are CLI checks that
      report with `print` (T201) and run semgrep through
      `subprocess` (S404 and S603, already `# nosec` with a
      reason). Give each a commented `# noqa` or a commented
      per-file ignore for scripts/, never a blanket one.
      GitHub's dependency graph classes uv.lock's dev groups
      as runtime scope (PR #60 listed prek as `runtime`), so
      security.yml's dependency-review applies ADR-0004's
      allowlist to dev tools too. Add an
      `allow-dependencies-licenses` purl, with a comment, for
      each new dev-only package outside it (hypothesis and
      mypy's pathspec are MPL-2.0). ADR-0004 keeps dev tools
      outside the allowlist, and the `licences` hook still
      checks the runtime closure.
    </requirement>

    <requirement>
      mypy: `strict = true`; `plugins =
      ["pydantic.mypy"]`; warn_unreachable;
      enable_error_code ignore-without-code, redundant-expr,
      truthy-bool and possibly-undefined; python_version
      3.12; files src and tests. pyright: strict mode for
      src and tests (editor use, not a gate). ty: a minimal
      [tool.ty] section; Step 10 runs it non-blocking.
    </requirement>

    <requirement>
      pytest and coverage in pyproject.toml: addopts with
      --strict-markers, --strict-config, -ra,
      --doctest-modules, --import-mode=importlib and
      --disable-socket; testpaths tests and src; xfail_strict
      true; filterwarnings error; doctest_optionflags
      NORMALIZE_WHITESPACE and ELLIPSIS; benchmarks disabled
      unless requested. Doctests must import the installed
      package, never a second copy from src/. Coverage:
      branch true, source pyeconomics, fail_under 95,
      show_missing, skip_covered. tests/conftest.py
      registers hypothesis profiles `ci` (derandomize, no
      deadline, print_blob) and `dev`, chosen by
      HYPOTHESIS_PROFILE.
    </requirement>

    <requirement>
      Smoke tests: tests/unit/test_network_blocked.py
      asserts that opening a socket raises pytest-socket's
      SocketBlockedError; src/pyeconomics/__init__.py gains
      a module doctest showing `__version__` is a string.
    </requirement>

    <requirement>
      prek hooks beside the gate, revs pinned: ruff-format,
      ruff check, mypy (a local hook running `uv run mypy`),
      `uv lock --check`, a pylock.toml freshness check
      (re-export and diff), check-yaml, check-toml,
      end-of-file-fixer, trailing-whitespace and
      mixed-line-ending with `--fix=lf`.
    </requirement>

    <requirement>
      Run every tool on Windows and paste the outputs into
      the PR body: `uv sync --locked`, `uv run ruff format
      --check`, `uv run ruff check`, `uv run mypy`,
      `uv run pyright` and `uv run ty check`
      (informational), `uv run pytest --cov`. Ubuntu and
      macOS run in Step 10's CI.
    </requirement>

    <requirement>
      Filepath comment: every new Python file starts with
      `# <repo-relative path>`.
    </requirement>
  </requirements>
</task>
```

### Step 9 acceptance criteria

- `pyproject.toml` selects ruff `ALL` (so `S`, `NPY` and `PD` are on)
  with a commented ignore list, sets mypy `strict = true` with the
  `pydantic.mypy` plugin, configures pyright strict and ty, and enables
  branch coverage with `fail_under = 95`.
- `uv run ruff format --check`, `uv run ruff check`, `uv run mypy` and
  `uv run pytest --cov` pass on Windows, with the coverage floor met.
- pytest runs with sockets disabled (`test_network_blocked.py` passes)
  and collects the module doctest in `src/pyeconomics/__init__.py`.
- prek runs ruff-format, ruff check, mypy, `uv lock --check`, the
  pylock.toml freshness check and the hygiene hooks beside the security
  gate; `uv run prek run --all-files` passes.
- `uv.lock` and `pylock.toml` are current (`uv lock --check` passes and a
  fresh export matches).
- **Security gate clean** (always the final criterion): every commit
  passed the prek gate; `pip-audit --locked` is clean with the new tools;
  ruff's `S` rules and bandit report nothing; no test opens a socket.

---

## Step 10 — CI/CD and Publishing Rehearsal ✅

**Status:** Complete — PR #64 (2026-10-07)

> **Goal:** Run every check on every pull request and prove the 1.x
> release path end to end. Write `.github/workflows/ci.yml` — `lint`
> (ruff format and check), `types` (mypy), a non-blocking `ty` job, a
> `tests` matrix on Ubuntu, Windows and macOS across Python 3.12, 3.13
> and 3.14 (and 3.15 if final) running `uv sync --locked` and `pytest
> --cov`, `package` (`uv build`, `twine check --strict`, a clean-venv
> import and the artifact allowlist), `lockfile`, `pr-title`
> (Conventional Commits), `dco` (a `Signed-off-by` on every commit) and
> an aggregate job named `test` that fails when any of them did. Port
> Step 2's hardened design to `main` as `release.yml` — verify the tag is
> on `main` and equals `uv version`, build once, publish `.devN` to
> TestPyPI and everything else to PyPI behind the `pypi` approval, over
> OIDC with attestations — and as a reusable `release-smoke.yml`, the
> health signal for every 1.x release. Enforce SHA pinning and read-only
> default token permissions by repository policy, delete
> `CODECOV_TOKEN`, make the new checks required on `main`, and after the
> merge tag `v1.0.0.dev1` and prove it on TestPyPI only. Parent: 1.3
> (Conventional Commits check) and 1.5.

**Branch:** `feature/phase01-step10-ci-cd`

**Deploys:** TestPyPI — `pyeconomics==1.0.0.dev1` from tag `v1.0.0.dev1`
on `main`, pushed after this step's PR merges (Stage 4), through
`release.yml` and the `testpypi` environment.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Sonnet 5.5                             |
| Backup       | GPT-6 Sol — Codex · Intelligence High         |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY — four workflows and their
repository settings — and agentic work SECONDARY — driving the rehearsal
tag, the environment and the required-check set end to end. Step 2
already proved the hardened design on `legacy/0.2.x`, so the knowledge
load is lighter than there, but the scope (every future merge and
release) makes overall complexity High and requires S in coding. Sonnet
5.5, Opus 5.5, Fable 5.1, GPT-6 Astra and GPT-6 Sol are all S in coding
and agentic work; Sonnet 5.5 wins the selector's coverage tie-break with
S or A in all seven categories, and under the operator's `balanced`,
`capped` posture it also draws less of the claude.ai Max weekly pool.
Claude Code on the Max plan runs it at $0 marginal while the pool has
headroom: switch the model with `/model`, and raise Effort from Sonnet
5.5's Medium default to High for the High complexity — not Extra High,
because porting a proven design is not a new proof. Thinking stays On.
The backup is GPT-6 Sol on Codex under ChatGPT Pro 5x. New conversation
per phase-boundary hygiene.

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
       feature/phase01-step10-ci-cd`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 10 is
       complete. You can now move
       on to Step 11." That
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
       one before Step 11.
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

    THIS STEP ALSO:
    - The prek gate runs on every commit; no SKIP and no
      --no-verify.
    - Every workflow: top-level `permissions: {}`; per-job
      `contents: read` unless the job needs more;
      `id-token: write` only on the two publish jobs (and
      Scorecard's results-publishing job, Step 8);
      `persist-credentials: false` on every checkout; no
      `pull_request_target`; no secret reachable from a job
      a fork PR can trigger; the PR title and every other
      untrusted value reach `run:` only through `env:`;
      zizmor reports nothing above Low.
    - Delete CODECOV_TOKEN (`gh secret delete
      CODECOV_TOKEN`): the 1.x CI prints coverage and
      enforces its floor with no third-party upload.
    - Repository Actions policy: full-SHA pinning required,
      default GITHUB_TOKEN permissions read-only, and
      Actions may not create or approve pull requests.
    - The rehearsal publishes only a `.devN` version, only
      to TestPyPI, only over OIDC; smoke installs resolve
      third-party packages from PyPI only.
  </security>

  <context>
    pyeconomics. Phase 1. Step 10: CI/CD and publishing
    rehearsal.

    Current state (as of Phase 1 Step 9):

    - main holds the skeleton with the full toolchain
      (ruff ALL, mypy strict, pytest with sockets disabled,
      doctests and a 95% branch-coverage floor) and the
      prek gate; security.yml, codeql.yml and scorecard.yml
      run, and their checks are required on main.
    - main has no ci.yml and no release.yml (Step 7 deleted
      the 0.2.x workflows). legacy/0.2.x keeps its own
      hardened release.yml (tags `v0.2.*` only) and
      tests.yml.
    - Trusted publishers for workflow release.yml with
      environments `pypi` (PyPI) and `testpypi` (TestPyPI)
      exist for the current owner (Step 2; replaced in
      Step 6 if the repository moved). Environments
      `testpypi` and `pypi` (maintainer review) and the
      `release-tags`, `archive-immutable-branches` and `archive-immutable-tags` rulesets exist.
    - pyproject.toml version is 1.0.0.dev1. CODECOV_TOKEN is
      still a repository secret. ADR-0010 puts CI on 3.12,
      3.13 and 3.14, plus 3.15 once final (due
      2026-10-09).

    Files to read (every file before drafting):
    - `git show origin/legacy/0.2.x:.github/workflows/release.yml`
      and `...tests.yml` (the proven hardened pattern).
    - .github/workflows/security.yml (job conventions).
    - pyproject.toml, docs/adr/0003 and docs/adr/0010.
    - docs/roadmap/ROADMAP.md §4 1.5; §5 "Release &
      deployment strategy" and "Operations & observability
      strategy".
  </context>

  <goal>
    Every pull request to main runs lint, types, the
    three-OS test matrix, package, lockfile, PR-title and
    DCO checks behind one aggregate `test` gate; main's
    release.yml publishes 1.x through OIDC with attestations
    and a reusable smoke job; and 1.0.0.dev1 is on TestPyPI,
    installed and verified.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      .github/workflows/ci.yml, on pull_request and push to
      main, concurrency cancelling superseded PR runs:
      - lint: `uv run ruff format --check` and `uv run ruff
        check --no-fix`.
      - types: `uv run mypy`.
      - ty: `uv run ty check`, `continue-on-error: true`,
        never required.
      - tests: matrix os ubuntu-latest, windows-latest,
        macos-latest × python 3.12, 3.13, 3.14 (plus 3.15
        if final when this step runs; otherwise open an
        issue to add it and its classifier at release, per
        ADR-0010), running `uv sync --locked` and
        `uv run pytest --cov` with the coverage report
        printed, then `uv run prek run licences
        --all-files`. Step 8's licence check skips runtime
        packages whose markers exclude the running platform,
        so each OS checks its own.
      - package: `uv build`; `uvx twine check --strict
        dist/*`; the Step 7 artifact allowlist (it admits
        the sdist's PKG-INFO, and the pyproject.toml.orig
        uv_build 0.12 always writes only when it is
        byte-identical to the committed pyproject.toml);
        install the wheel in a clean venv and import
        `__version__` from a directory outside the checkout.
      - lockfile: `uv lock --check` and a pylock.toml
        freshness diff.
      - pr-title (pull requests only): the title, passed via
        `env:`, matches the Conventional Commits pattern.
      - dco (pull requests only): every commit in the PR
        range carries a `Signed-off-by:` trailer matching
        its author.
      - test: `needs:` every job above except ty,
        `if: always()`, and fails unless each succeeded (or
        was skipped by design) — the single aggregate check
        branch protection requires for the matrix.
      Each job: harden-runner first, checkout with
      `persist-credentials: false`, setup-uv with caching,
      SHA-pinned actions.
    </requirement>

    <requirement>
      From Step 9: run the Step 9 hooks by id, as security.yml
      does, so local and CI cannot drift: lint runs `uv run
      --locked prek run <id> --all-files --verbose` for
      check-yaml, check-toml, end-of-file-fixer,
      trailing-whitespace, mixed-line-ending, ruff-format and
      ruff-check; types runs the `mypy` hook; lockfile runs
      `uv-lock` and `pylock-fresh` (scripts/checks/pylock_fresh.py,
      the freshness diff). ruff-format also formats Python
      blocks in Markdown. The tests job sets
      `HYPOTHESIS_PROFILE: ci` (tests/conftest.py). pyright
      stays out of CI (editor only): its PyPI wrapper fetches
      Node at first run. The tests run with `uv run pytest`,
      never `python -m pytest`, which puts the working
      directory on sys.path.
    </requirement>

    <requirement>
      .github/workflows/release-smoke.yml, a reusable
      workflow (`workflow_call` and `workflow_dispatch`)
      with inputs `version` and `index` (pypi or testpypi):
      a fresh venv installs `pyeconomics==<version>` with
      `--no-deps` from that index (retrying while it
      propagates), then its dependencies from PyPI only, and
      asserts `pyeconomics.__version__` equals the input.
      This job is the 1.x publishing surface's health signal.
    </requirement>

    <requirement>
      .github/workflows/release.yml on `push: tags: ['v*']`,
      `permissions: {}`, per-ref concurrency without
      cancellation:
      - verify: refuse `v0.*` tags (legacy/0.2.x releases
        through its own workflow); the tag's commit is an
        ancestor of origin/main; the tag equals `v` plus
        `uv version --short`; output index = testpypi for a
        `.devN` version, otherwise pypi.
      - build: `uv build` once, `uvx twine check --strict`,
        upload the artifact.
      - publish-testpypi and publish-pypi exactly as on
        legacy/0.2.x (environments testpypi and pypi,
        `id-token: write`, pypa/gh-action-pypi-publish with
        attestations on).
      - smoke: calls release-smoke.yml with the version and
        index.
    </requirement>

    <requirement>
      Repository Actions settings with `gh api` (payloads
      shown first; confirm field names against GitHub's REST
      documentation at write time): require full-length SHA
      pinning (`PUT repos/OWNER/REPO/actions/permissions`);
      default workflow permissions `read` and
      can_approve_pull_request_reviews false
      (`PUT .../actions/permissions/workflow`). Then
      `gh secret delete CODECOV_TOKEN` and confirm with
      `gh secret list` that no repository secret remains.
    </requirement>

    <requirement>
      Required checks: once ci.yml has reported green on
      this PR, add lint, types, test, package, lockfile,
      pr-title and dco to main's required status checks,
      keeping Step 8's security checks and `strict: true`.
    </requirement>

    <requirement>
      Rehearsal at Stage 4, after the merge: `git switch
      main && git pull --ff-only origin main`; confirm
      `uv version --short` prints 1.0.0.dev1; `git tag -a
      v1.0.0.dev1 -m "1.0.0.dev1: TestPyPI rehearsal"` on
      main's HEAD; `git push origin v1.0.0.dev1`;
      `gh run watch` until publish-testpypi and smoke are
      green.
    </requirement>

    <requirement>
      Filepath comment: every new YAML file starts with
      `# <repo-relative path>`.
    </requirement>
  </requirements>
</task>
```

### Step 10 acceptance criteria

- `ci.yml` runs lint, types, ty (non-blocking), the 3 × 3 `tests` matrix
  (Ubuntu, Windows, macOS × Python 3.12, 3.13, 3.14, plus 3.15 if final
  or an open issue to add it), package, lockfile, pr-title and dco, and
  its aggregate `test` job is green on the PR and on `main` after the
  merge.
- `release.yml` refuses `v0.*` tags and tags not on `main`, compares the
  tag with `uv version`, routes `.devN` to TestPyPI and everything else to
  PyPI behind the `pypi` approval, and calls the reusable
  `release-smoke.yml`.
- Every workflow on `main` has top-level `permissions: {}`,
  `persist-credentials: false` on each checkout, SHA-pinned actions and
  no `pull_request_target`; zizmor reports nothing above Low.
- The repository requires SHA pinning, defaults the workflow token to
  read-only and forbids Actions from approving pull requests;
  `gh secret list` returns no secret.
- `main`'s required checks are lint, types, test, package, lockfile,
  pr-title, dco and Step 8's security checks, with strict status checks.
- **Deployed & verified:** the `v1.0.0.dev1` release run is green
  through `publish-testpypi` and `smoke`; TestPyPI lists `pyeconomics
  1.0.0.dev1`;
  `https://test.pypi.org/integrity/pyeconomics/1.0.0.dev1/<file>/provenance`
  returns an attestation for the wheel and the sdist; and a clean venv
  that installs `pyeconomics==1.0.0.dev1` from TestPyPI with `--no-deps`
  prints `1.0.0.dev1` for `pyeconomics.__version__`.
- **Security gate clean** (always the final criterion): the prek gate and
  the security workflow are green on every commit of the PR; publishing
  used OIDC only; no long-lived publishing or coverage credential exists;
  `id-token: write` appears only on the two publish jobs and on
  `scorecard.yml`'s results-publishing job (Step 8).

---

## Step 11 — Governance, Community and Agent Instructions ✅

**Status:** Complete — PR #67 (2026-10-07)

> **Goal:** Give the project the files, rules and funding hooks that
> outside users, contributors and coding agents read first. Rewrite
> `README.md` (a 1.0 status banner, a pointer to 0.2.x and its advisory,
> the distinction from similarly named projects, the CFA marks notice,
> "as is; not investment advice", the licences, and links to the
> roadmaps), `CONTRIBUTING.md` (setup with uv and prek, DCO sign-off,
> Conventional Commits, the step lifecycle, the model definition of done
> from ROADMAP §5, the gate and its bypass rule, the licence check for new
> dependencies), `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md` (Keep
> a Changelog) and `CITATION.cff`; add `.github/CODEOWNERS`, issue forms
> for bugs, model requests (citation required) and data-source requests
> (terms-of-use URL required), the defect-class labels, `AGENTS.md` (the
> rules every coding-agent session follows) with a `CLAUDE.md` that
> imports it, and the Gate G1 funding hooks — `.github/FUNDING.yml`,
> `funding.json`, a live GitHub Sponsors profile and thanks.dev — and
> remove the ® from the maintainer's name everywhere it still appears
> going forward. Parent: 1.7 and Gate G1.

**Branch:** `feature/phase01-step11-governance`

**Deploys:** nothing beyond merge — community files, labels and funding
links are live on merge; GitHub Sponsors and thanks.dev are external
enrolments verified in the acceptance criteria.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Astra — Codex · Intelligence Medium     |
| Platform     | Claude Code                                   |
| Effort       | Medium                                        |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Knowledge is PRIMARY — trademark notices, licence
statements, DCO, disclosure policy and the rules agents must follow, all
of which must match ROADMAP §5 exactly — with planning SECONDARY in
shaping the agent instructions; the files are many but templated, so
complexity is Medium. Opus 5.5 is rated S for knowledge. Under the
operator's `balanced`, `capped` posture a Medium step runs on the
surface default: Claude Code on the claude.ai Max plan opens on Opus 5.5
at its Medium default, $0 marginal while the weekly pool has headroom —
run as opened. Medium effort suffices because the wording that carries
legal weight is quoted verbatim from the project roadmap rather than
composed; Thinking stays On. The backup, GPT-6 Astra on Codex under
ChatGPT Pro 5x, is A in knowledge and the only non-Anthropic model rated
S in planning. New conversation per phase-boundary hygiene.

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
       feature/phase01-step11-governance`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 11 is
       complete. You can now move
       on to Step 12." That
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
       one before Step 12.
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

    THIS STEP ALSO:
    - The prek gate runs on every commit; no SKIP.
    - Public files carry only the maintainer's public
      contact address already in the 0.2.x metadata — no
      phone number, home address or other PII.
    - SECURITY.md routes reports to GitHub private
      vulnerability reporting, never to a public issue.
    - funding.json, FUNDING.yml and the Sponsors profile
      contain no payout or account details.
    - AGENTS.md forbids printing environment variables,
      tokens or keys in a session and restates that a gate
      bypass needs a justification in the PR body.
  </security>

  <context>
    pyeconomics. Phase 1. Step 11: Governance, community and
    agent instructions.

    Current state (as of Phase 1 Step 10):

    - main has the skeleton, toolchain, security gate, CI
      (lint, types, three-OS tests, package, lockfile,
      pr-title, dco, aggregate test) and the 1.x release
      path; 1.0.0.dev1 is on TestPyPI.
    - Root CHANGELOG.md, CODE_OF_CONDUCT.md and
      CONTRIBUTING.md are the 0.2.x versions Step 7 moved
      from markdown/; README.md is Step 7's interim page;
      CITATION.cff still says 0.2.0 and MIT; the PR template
      exists (Step 8).
    - No SECURITY.md, CODEOWNERS, issue forms, labels,
      AGENTS.md, CLAUDE.md, FUNDING.yml or funding.json.
      Issues opened earlier in the phase carry their class
      in the title (Triage rule).
    - The maintainer's GitHub profile name is "Nathan Ramos,
      CFA®", the author of 123 commits; the local git
      user.name is "Nathan Ramos".
    - ADR-0009 decided the repository's home; take
      OWNER/REPO from `gh repo view --json nameWithOwner`
      for every URL.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §4 1.7; §5 "Legal & brand
      guardrails" (the CFA notice, data notices,
      disclaimers), "Model quality & governance" (the model
      definition of done), "Defect handling & triage" (the
      label classes), "Monetization strategy & validation
      gates" (G1); §1 (similarly named projects).
    - docs/adr/0001, 0003, 0004 and 0009.
    - The current root README.md, CHANGELOG.md,
      CODE_OF_CONDUCT.md, CONTRIBUTING.md, CITATION.cff,
      NOTICE and .github/pull_request_template.md.
    - This file's Overview (the rules AGENTS.md restates).
  </context>

  <goal>
    The repository's community profile is complete; every
    public file states the 1.0 status, licences, notices and
    disclosure path correctly; agents get one rulebook
    (AGENTS.md, imported by CLAUDE.md); defect-class labels
    exist; and Gate G1's funding hooks are live.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      README.md: a status banner (1.0 is in development;
      `pip install pyeconomics` installs 0.2.6; pre-releases
      need `--pre`); a 0.2.x section (MIT, legacy/0.2.x,
      security fixes only until 1.0.0, the advisory link,
      Read the Docs); the note distinguishing this project
      from davidrpugh/pyeconomics and pyecon.org; the CFA
      notice quoted verbatim from ROADMAP §5 ("CFA® and
      Chartered Financial Analyst® are trademarks owned by
      CFA Institute. pyeconomics is not affiliated with,
      endorsed by, or a Prep Provider of CFA Institute.");
      "As is; not investment advice"; Apache-2.0 for 1.0;
      links to docs/roadmap/ROADMAP.md, CONTRIBUTING and
      SECURITY. Only live badges (CI, PyPI, licence,
      Scorecard); the 2024 wishlist "Roadmap" section is
      gone.
    </requirement>

    <requirement>
      CONTRIBUTING.md: setup (`uv sync`, `uv run prek
      install`; no separate gitleaks install, because Step 8
      verified on Windows that prek builds the pinned
      gitleaks hook with its own Go toolchain on the first
      run); DCO with `git commit -s` (the `dco` check wants a
      `Signed-off-by` matching each commit's author, and
      exempts only Dependabot's own pull requests); Conventional
      Commits on PR titles; the six-stage step lifecycle and
      the Triage rule in brief; the model definition of done
      from ROADMAP §5 "Model quality & governance"; the
      security gate and its emergency-only bypass with a
      PR-body justification; the licence check for any new
      dependency or data source; and, from Step 9, the
      Python file header: `# <repo-relative path>`, then
      `# Copyright <year> Nathan Ramos, CFA` and
      `# SPDX-License-Identifier: Apache-2.0` (ruff's CPY001
      requires the copyright line; it is not ignored), and
      `uv run pytest`, never `python -m pytest`, which puts
      the working directory on sys.path. AGENTS.md carries
      the same header rule.
      CODE_OF_CONDUCT.md: the current Contributor Covenant
      with the maintainer's public address as the contact.
      SECURITY.md: supported versions (the latest 1.0
      pre-release; 0.2.x for security fixes until 1.0.0,
      then end-of-life), reporting through GitHub private
      vulnerability reporting, response targets, and the
      advisory, yank and key-rotation practice.
    </requirement>

    <requirement>
      CHANGELOG.md in Keep a Changelog 1.1.0 form:
      [Unreleased] and [1.0.0.dev1] (the skeleton and
      pipeline), with a pointer to the 0.2.x history on
      legacy/0.2.x. CITATION.cff: version 1.0.0.dev1, its
      date, licence Apache-2.0, the author as "Nathan Ramos,
      CFA" with no ®, and the repository URL; it passes
      `uvx cffconvert --validate`.
    </requirement>

    <requirement>
      .github/CODEOWNERS (the maintainer for everything,
      explicitly for .github/ and docs/adr/); issue forms in
      .github/ISSUE_TEMPLATE/: bug.yml; model-request.yml
      with a required citation field and a link to
      docs/adr/0001-product-boundaries.md and ROADMAP §6
      Out of Scope (ADR-0001's confirmation); data-source-request.yml
      with a required terms-of-use URL field; config.yml
      disabling blank issues and linking private
      vulnerability reporting. Labels with `gh label create`
      for the defect classes — spec-rot, upstream-gap, bug,
      model-error, architecture, process, security — and
      relabel the phase's earlier issues from their title
      prefixes.
    </requirement>

    <requirement>
      AGENTS.md, the single rulebook for coding agents:
      repository layout; registry rules from ROADMAP §3
      (models are pure functions — no I/O, printing,
      plotting or LLM calls — taking effect in Phase 2);
      units (decimals in APIs, pending ADR-0008); testing
      (sockets disabled; golden and property tests from
      Phase 2); the security gate and the bypass rule; the
      six-stage lifecycle with branch-first, Status and
      Triage rules; Conventional Commits and `git commit
      -s`; the Worktree rule and `.worktrees/`; Windows
      notes (Git Bash, LF, `git update-index --chmod=+x`);
      never print environment variables, tokens or keys.
      CLAUDE.md imports it (`@AGENTS.md`) and adds only
      Claude Code specifics.
    </requirement>

    <requirement>
      Funding for Gate G1: .github/FUNDING.yml (GitHub
      Sponsors and thanks.dev); funding.json at the root,
      valid against the published funding.json schema; the
      operator enrols in GitHub Sponsors and thanks.dev and
      the agent confirms each profile returns 200: the
      Sponsors URL without following redirects (with no
      listing, github.com/sponsors/<name> answers 302 to the
      profile, so `curl -L` reports a false 200), and
      thanks.dev through its profile API,
      https://api.thanks.dev/v1/profile/gh/<name> (200 with
      JSON when claimed, 500 when not), because thanks.dev
      serves every page path as a single-page app with
      status 403. If Sponsors approval is still pending at
      merge time, the step is not complete until it is
      live.
      Amended 2026-10-08 by the maintainer: Sponsors
      onboarding stalled on a GitHub Support ticket (a
      Stripe account linked to the wrong legal entity), so
      Step 11 merges with thanks.dev live and the Sponsors
      listing tracked in issue #68. Until the listing is
      live, FUNDING.yml and funding.json name thanks.dev
      only; #68 restores the Sponsors entries, and Step 12's
      V11.4 must see the listing live before Phase 1 is
      complete.
    </requirement>

    <requirement>
      The ® after the maintainer's name: the operator sets
      the GitHub profile name to "Nathan Ramos, CFA" and
      `git config --global user.name "Nathan Ramos, CFA"`;
      confirm with `gh api user --jq .name` and with this
      PR's squash-commit author. History is not rewritten.
    </requirement>

    <requirement>
      Filepath comment: YAML files start with
      `# <repo-relative path>`; Markdown and JSON follow
      their conventions (JSON allows no comments).
    </requirement>
  </requirements>
</task>
```

### Step 11 acceptance criteria

- `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`,
  `CHANGELOG.md`, `CITATION.cff`, `NOTICE`, `AGENTS.md`, `CLAUDE.md`,
  `funding.json`, `.github/CODEOWNERS`, `.github/FUNDING.yml` and the
  three issue forms plus `config.yml` exist on `main`.
- The README carries the CFA notice verbatim, the 0.2.x pointer with the
  advisory link, the disambiguation note and "As is; not investment
  advice", and no 2024 wishlist section.
- The repository's community standards are complete: `gh api
  repos/OWNER/REPO/community/profile` reports README, CONTRIBUTING,
  CODE_OF_CONDUCT and the PR template; GraphQL `isSecurityPolicyEnabled`
  is true; and the public page `https://github.com/OWNER/REPO/community`
  checks Security policy and Issue templates. (The REST profile has no
  security-policy field, and reports `issue_template` as null for YAML
  issue forms, a known GitHub API gap.)
- `uvx cffconvert --validate` passes; `CITATION.cff` names `1.0.0.dev1`,
  `Apache-2.0` and the author without ®; `gh api user --jq .name` prints
  "Nathan Ramos, CFA".
- The seven defect-class labels exist, and every issue the phase opened
  carries its class label.
- `AGENTS.md` states the lifecycle, the security gate, the Triage rule
  and the commit conventions, and `CLAUDE.md` imports it.
- Gate G1: `https://api.thanks.dev/v1/profile/gh/pyeconomics-dev` returns
  200, `funding.json` validates against the funding.json schema, and the
  GitHub Sponsors listing is tracked in issue #68 (amended by the maintainer
  on 2026-10-08; Step 12's V11.4 requires it live, returning 200 without
  following redirects, before Phase 1 is complete).
- **Security gate clean** (always the final criterion): every commit
  passed the prek gate and the security workflow; public files carry no
  PII beyond the maintainer's public address; SECURITY.md routes reports
  privately.

---

## Step 12 — QA and Verification Script ✅

**Status:** Complete — PR #70 (2026-10-08)

> **Goal:** Package the phase's verification into
> `scripts/verify-phase01.sh` — the first verify script, whose mode
> contract (`--fast`, `--python`, `--security`, `--live`, `--all`,
> `--post`) later phases copy — produce `docs/phase01-qa-findings.md`, and
> create `.github/workflows/phase-verify.yml` with matrix entry `01`. The
> script runs 45 numbered static checks covering Steps 1–11 and five Step
> 12 self-checks with grep, test, git and `git show`; the Python suite and
> build; the full security gate; and, locally with the maintainer's
> authenticated session, live checks of GitHub settings, PyPI, TestPyPI
> and Read the Docs, then a V1–V12 summary. Add
> `tests/repo/test_phase01.py`, prove the release-smoke alarm fires with a
> synthetic failure, walk every Phase 1 acceptance criterion, and mark
> the phase complete in this roadmap and in the project roadmap. Parent:
> Phase 1 acceptance criteria.

**Branch:** `feature/phase01-step12-verify`

**Deploys:** nothing beyond merge — the CI matrix entry is live on merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence Medium       |
| Platform     | Claude Code                                   |
| Effort       | Medium                                        |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY — a Bash verification script, its
pytest twin and a workflow — and agentic work SECONDARY — running every
live check against GitHub, PyPI, TestPyPI and Read the Docs and walking
the phase's acceptance criteria. No earlier verify script exists to
translate, so the step designs the mode contract later phases copy, but
each check is a known grep, file, git or API test, so complexity is
Medium. Opus 5.5 is S in coding and agentic work, and under the
operator's `balanced`, `capped` posture a Medium step runs on Claude
Code's default — Opus 5.5 at Medium on the claude.ai Max plan, $0
marginal while the weekly pool has headroom: run as opened. Medium
effort fits numerous but mechanical checks; Thinking stays On. The
backup is GPT-6 Sol on Codex under ChatGPT Pro 5x. New conversation per
phase-boundary hygiene.

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
       feature/phase01-step12-verify`
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
       Phase 1 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 1`
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
       shape "Step 12 is
       complete. Phase 1 is
       complete. You can now move
       on to Phase 2." That
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
       one before Phase 2.
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

    THIS STEP ALSO:
    - The prek gate runs on every commit; no SKIP. This
      step also AUTHORS the --security verify mode, so its
      own diff must still pass the gate before commit.
    - `--live` reads GitHub settings through the
      maintainer's authenticated gh session and never prints
      a token, a secret value or the environment; CI never
      runs `--live`.
    - The synthetic alarm test dispatches release-smoke.yml
      against a version that does not exist; it publishes
      nothing.
  </security>

  <context>
    pyeconomics. Phase 1. Step 12: QA and verification
    script.

    Steps 1 through 11 have been implemented. Now create the
    verification script, the QA findings document and the CI
    matrix entry, verify every Phase 1 criterion, and close
    the phase.

    Reference scripts (pattern templates): none — Phase 1 is
    the first phase, so this script sets the precedent. Its
    modes replace the template's --swift, --node and --ui
    (no Swift, Node or UI stack exists) with --python and
    --live.

    Phase 1 deliverables to verify (45 static checks across
    Steps 1 through 11 plus 5 Step 12 self-checks):

    Step 1 (preserve and bootstrap) — checks 1-5:
    1.  docs/roadmap/ROADMAP.md and
        docs/roadmap/phase01-roadmap.md are tracked.
    2.  The planning kit files (model-selector.txt,
        model-tier-cost-scale.md, settings-display.md,
        templates/, prompts/, HOW-TO-USE.md) are tracked;
        planning/user-context.md is untracked and ignored.
    3.  Tag archive/dev-2024-10 peels to
        d4a692d7c76c75119c98dbc980d0ec5454a8fa05.
    4.  Tag archive/legacy-dev-0.2.6 peels to
        2b7e8a6e1dd3dbc11b4a8e395e8679fe31487d15.
    5.  origin has archive/0.2-dev-wip, and its parent is
        d4a692d7c76c75119c98dbc980d0ec5454a8fa05.

    Step 2 (legacy fix and pipeline) — checks 6-10, read
    with `git show origin/legacy/0.2.x:<path>`:
    6.  fred_api.py has no logging call that interpolates
        api_key.
    7.  tests/test_credential_logging.py and
        scripts/check_credential_logging.py exist.
    8.  release.yml triggers on `v0.2.*` only, has no
        `password:`, names environments testpypi and pypi,
        and grants `id-token: write` on exactly two jobs.
    9.  Every `uses:` in the legacy workflows is pinned to a
        40-hex SHA, and docs.yml is absent.
    10. Tag v0.2.6.dev1 exists and is an ancestor of
        origin/legacy/0.2.x.

    Step 3 (readiness gate) — check 11:
    11. docs/releases/0.2.6-readiness.md has its ten
        sections, no unresolved FAIL, and a
        `Decision: GO` line.

    Step 4 (0.2.6 release) — checks 12-13:
    12. Tag v0.2.6 is on legacy/0.2.x, and __version__.py
        at the tag reads 0.2.6.
    13. The legacy CHANGELOG has a dated [0.2.6] entry, and
        the readiness document has a Release record section
        with a GHSA id.

    Step 5 (characterize and archive) — checks 14-16:
    14. tests/fixtures/legacy/manifest.json exists, and
        every file it lists exists with a matching SHA-256.
    15. scripts/legacy/record_characterization.py has a PEP
        723 block pinning pyeconomics==0.2.6.
    16. No path under dev/ is tracked, and apart from the
        head branches of open pull requests,
        `git ls-remote --heads origin` lists only main,
        legacy/0.2.x and archive/ branches (no dev,
        legacy-dev-0.2.6 or snyk-fix-* branch).

    Step 6 (ADRs) — checks 17-18:
    17. docs/adr/ holds README.md, template.md and the nine
        ADR files.
    18. Each of the nine reads `Status: Accepted`, the
        index lists each as Accepted with its file's date,
        and the index lists 0008 as reserved.

    Step 7 (reset and skeleton) — checks 19-25:
    19. No 0.2.x path is tracked: setup.py,
        requirements.txt, __version__.py, pytest.ini,
        MANIFEST.in, .coveragerc, .readthedocs.yml,
        Dockerfile, .dockerignore, start.sh, test_import.py,
        pyeconomics/, examples/, media/, markdown/,
        docs/conf.py, docs/roadmap*.rst.
    20. src/pyeconomics/__init__.py reads its version
        through importlib.metadata, and py.typed exists.
    21. pyproject.toml has build-backend "uv_build",
        requires-python ">=3.12", license "Apache-2.0" and
        a [dependency-groups] table; no package or module
        path under src/, console-script entry point, project
        URL, author email or extra name contains "cfa",
        case-insensitive (ADR-0009).
    22. uv.lock and pylock.toml are tracked.
    23. .gitattributes sets eol=lf, and `git ls-files --eol`
        shows no CRLF text in the index.
    24. .gitignore holds .worktrees/,
        planning/user-context.md, dev/ and .env, and no
        blanket *.json or *.csv line.
    25. LICENSE is the Apache License 2.0; NOTICE exists;
        no ® appears in LICENSE, NOTICE, pyproject.toml or
        CITATION.cff.

    Step 8 (security gate) — checks 26-30:
    26. .pre-commit-config.yaml has hooks for gitleaks,
        bandit, semgrep (or its portable twin), pip-audit,
        the licence check and no-commit-to-branch.
    27. .semgrep/rules/ covers pickle, eval/exec, yaml.load
        and credential logging, and .semgrep/tests/ exists.
    28. security.yml (with trufflehog, zizmor and
        dependency-review), codeql.yml and scorecard.yml
        exist, and every job begins with harden-runner.
    29. .github/pull_request_template.md holds the
        sensitive-data checklist, the rollback plan and the
        licence check.
    30. .github/dependabot.yml lists the uv and
        github-actions ecosystems.

    Step 9 (quality toolchain) — checks 31-34:
    31. ruff lint selects ALL (so S, NPY and PD are on).
    32. mypy is strict with the pydantic.mypy plugin.
    33. pytest addopts include --disable-socket and
        --doctest-modules; coverage has branch = true and
        fail_under >= 95.
    34. The prek config holds ruff-format, ruff check and
        mypy hooks.

    Step 10 (CI/CD) — checks 35-40:
    35. ci.yml's matrix names ubuntu, windows and macos and
        Python 3.12, 3.13 and 3.14, and runs
        `uv sync --locked`; pyproject.toml's
        `Programming Language :: Python :: 3.N` classifiers
        name exactly the matrix's Python versions
        (ADR-0010).
    36. release.yml refuses v0.* tags and tags off main,
        compares the tag with `uv version`, uses the testpypi
        and pypi environments with `id-token: write` on the
        publish jobs only; release-smoke.yml has
        workflow_call and workflow_dispatch.
    37. Every workflow on main has top-level
        `permissions: {}`, `persist-credentials: false` on
        each checkout, SHA-pinned `uses:` (a local reusable
        workflow, `uses: ./.github/workflows/...`, is exempt:
        release.yml calls release-smoke.yml that way) and no
        pull_request_target.
    38. tests.yml and docs.yml are absent on main.
    39. ci.yml has pr-title and dco jobs and an aggregate
        job named test.
    40. Tag v1.0.0.dev1 exists and is an ancestor of
        origin/main.

    Step 11 (governance) — checks 41-45:
    41. README.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md,
        SECURITY.md, CHANGELOG.md, CITATION.cff, NOTICE,
        AGENTS.md, CLAUDE.md, funding.json,
        .github/CODEOWNERS and .github/FUNDING.yml exist,
        and FUNDING.yml names `thanks_dev:`. Amended
        2026-10-08 by the maintainer: the GitHub Sponsors
        listing (issue #68) moves to ROADMAP 8.1, so
        `github:` is required only once FUNDING.yml names
        it again, and then V11.4 requires its listing.
    42. The issue forms exist: bug.yml, model-request.yml
        (a required citation field),
        data-source-request.yml (a required terms-of-use URL
        field) and config.yml (blank issues off).
    43. README.md holds the CFA notice verbatim, the 0.2.x
        pointer, the disambiguation note and "not investment
        advice", and no wishlist section.
    44. CITATION.cff names version 1.0.0.dev1 and licence
        Apache-2.0.
    45. AGENTS.md names the step lifecycle, the security
        gate and the Triage rule, and CLAUDE.md imports it.

    Step 12 self-checks — checks 46-50:
    46. scripts/verify-phase01.sh exists with git index mode
        100755.
    47. docs/phase01-qa-findings.md exists.
    48. docs/roadmap/phase01-roadmap.md exists (this doc).
    49. .github/workflows/phase-verify.yml's matrix
        includes "01".
    50. Security backstop: no tracked file holds a private
        key's PEM header (the five-dash BEGIN line), an AWS
        access-key id prefix followed by 16 key characters,
        a GitHub token or a PyPI token; checks 26 and 28
        confirm the gate is wired locally and in CI.

    Files to read:
    - Every file the checks above name, on main and (with
      `git show`) on origin/legacy/0.2.x.
    - docs/roadmap/ROADMAP.md §4 Phase 1 acceptance criteria
      and §5 "Operations & observability strategy".
    - This file's Post-Implementation Verification section
      (the V-check tables the script reports).
  </context>

  <goal>
    Create scripts/verify-phase01.sh with 45 static
    deliverable checks (Steps 1-11), 5 Step 12 self-checks
    and the V1-V12 post-implementation matrix; create
    docs/phase01-qa-findings.md and tests/repo/test_phase01.py;
    add .github/workflows/phase-verify.yml with matrix entry
    "01"; prove the release-smoke alarm; and mark Phase 1
    complete in both roadmaps.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      scripts/verify-phase01.sh modes:
      - default (no flag) and --fast: static checks 1-50
        only, CI-safe on Ubuntu, using grep, test -f,
        test -x, git ls-files, git show and git ls-remote;
        under 30 seconds.
      - --python: static checks plus `uv sync --locked`,
        `uv run ruff format --check`, `uv run ruff check`,
        `uv run mypy`, `uv run pytest --cov`, `uv build`,
        `uvx twine check --strict dist/*` and the artifact
        allowlist.
      - --security: the gate for the phase's surface —
        `uv run prek run --all-files` (gitleaks, bandit,
        semgrep, semgrep-test, pip-audit, lock-index,
        licences, zizmor), and zizmor over legacy/0.2.x's
        workflows (extracted to a temporary directory with
        `git show`). CI-safe on Ubuntu; exits non-zero on any
        finding. From Step 8: the bare `semgrep --test
        .semgrep/` is vacuous, so use the semgrep-test hook.
        On a `main` checkout, set `SKIP=no-commit-to-branch`,
        because that hook fails there by design. gitleaks'
        hook scans staged changes only, so scan the whole
        tree the way security.yml's gate-secrets does (stage
        it on an orphan branch in a scratch clone).
      - --live: local only, with the maintainer's gh
        session — branch protection on main and
        legacy/0.2.x, rulesets, environments and the pypi
        reviewer, the security settings, the required-check
        list, Actions policy, `gh secret list` (empty),
        open-PR authors, the private archive's visibility,
        PyPI 0.2.6 and its attestations, TestPyPI
        1.0.0.dev1 and its attestations, the published
        advisory, Read the Docs stable and latest, the
        Sponsors URL (200 without following redirects; a
        302 means no listing) and thanks.dev's profile API
        (https://api.thanks.dev/v1/profile/gh/<name>, 200;
        its page URLs answer 403 to every client that is not
        a browser); RDAP for the four
        ADR-0009 domains (V6.2 — `.io` through
        https://rdap.identitydigital.services/rdap/, since
        the IANA bootstrap that rdap.org follows has no
        `.io` entry); `gh repo view --json nameWithOwner`
        naming ADR-0009's organization, and the old
        `nathanramoscfa/pyeconomics` URL redirecting to it
        (V6.3).
      - --all: --fast, --python and --security.
      - --post: --all, --live, the fixture re-record
        (`uv run --script
        scripts/legacy/record_characterization.py --check`),
        the V1-V12 summary, and `gh pr checks` when gh is
        logged in and the branch has a PR.
      Each check is numbered, independent, and prints a
      clear PASS or FAIL line naming its deliverable.
    </requirement>

    <requirement>
      The script reports the V-checks by id (V1.1, V2.1, …)
      exactly as this file's Post-Implementation
      Verification section lists them, and ends with a
      summary table of totals per mode; it records V12.3 as
      PASS only when no static check failed.
    </requirement>

    <requirement>
      tests/repo/test_phase01.py:
      - test_roadmap_doc_exists.
      - test_qa_findings_doc_exists.
      - test_verify_script_exists_and_executable (the git
        index mode is 100755; subprocess calls to git carry
        an inline `# noqa` with its justification).
      - test_phase_verify_matrix_includes_01.
    </requirement>

    <requirement>
      .github/workflows/phase-verify.yml: on pull_request
      and push to main; `permissions: {}`; a matrix `phase:
      ["01"]` whose fast job runs `scripts/verify-phase<phase>.sh
      --fast` (checkout with fetch-depth 0 and tags) and
      whose security job runs `--security`; harden-runner
      first; SHA-pinned actions. Later phases append to the
      matrix; nothing here is phase-specific beyond the
      list. Once it has reported green on this PR, add both
      jobs to main's required checks.
    </requirement>

    <requirement>
      Synthetic alarm (Operations acceptance): dispatch
      release-smoke.yml with index testpypi and a version
      that does not exist (for example 0.0.0.dev0); confirm
      the run fails and the maintainer receives GitHub's
      failed-workflow notification; record the run URL and
      the notification's arrival in the QA findings.
    </requirement>

    <requirement>
      docs/phase01-qa-findings.md: one rollup section per
      step (1-11) listing every finding the step surfaced,
      its Triage class, its destination (fixed in PR #,
      issue #, or the phase that owns it) and the guard that
      now prevents the class; a Step 12 verify-script
      rollup; and a "Pre-ship items" section with documented
      limitations and downstream-phase follow-ups.
    </requirement>

    <requirement>
      Mark the phase complete in the SAME Stage-3 commit
      that marks this step (Status rule):
      - In docs/roadmap/ROADMAP.md, `### Phase 1 — Reset &
        Foundation` gets `**Status:** Complete —
        <YYYY-MM-DD>; PR #<n>; v1.0.0.dev1;
        phase01-roadmap.md` directly under it and ✅ at the
        end of the heading; its §8 row reads `Complete`; the
        header `> **Status:**` line names Phase 1 as shipped
        and Phase 2 as next; and its Phase 1 acceptance
        criteria are audited against V1-V12 here.
      - In this file: the phase-level Status reads
        `Complete — <YYYY-MM-DD>`; the title and every step
        heading end in ✅; every Summary Table Status cell
        reads `Complete — PR #<n>`.
    </requirement>

    <requirement>
      The script is executable (`git update-index
      --chmod=+x scripts/verify-phase01.sh` on Windows),
      prints PASS or FAIL per check, and exits 0 on success
      and 1 on any failure; --fast finishes in under 30
      seconds on Ubuntu CI.
    </requirement>

    <requirement>
      Filepath comment: every new file gets its
      repo-relative path as the first line (`# path` for
      Bash, Python and YAML; Markdown follows the docs
      convention).
    </requirement>
  </requirements>
</task>
```

### Step 12 acceptance criteria

- `scripts/verify-phase01.sh` exists with git index mode 100755 and passes
  on a clean tree after implementation.
- The script has 45 deliverable checks plus 5 self-checks and the V1–V12
  post-implementation checks.
- `--fast` runs in under 30 seconds on Ubuntu CI.
- `--post` runs cleanly on the maintainer's machine with every live
  check and the fixture re-record green.
- `docs/phase01-qa-findings.md` is complete, with every rollup section.
- `.github/workflows/phase-verify.yml` matrix includes `01`; its fast and
  security jobs appear on every PR and are required on `main`.
- `--security` exists and exits 0 (secret/PII scan, SAST, dependency
  audit and licence check clean over the phase's surface); V12.4 is
  green.
- `tests/repo/test_phase01.py` passes in the CI matrix.
- Branch protection still passes on the resulting PR.
- **Operations:** the publishing surface's health signal
  (`release-smoke.yml`) and its alarm (GitHub's failed-workflow
  notification to the maintainer) were seen to fire once, by dispatching
  the smoke job against a version that does not exist; the run URL and
  the notification are recorded in the QA findings.
- **Security gate clean** (always the final criterion): the pre-commit
  gate passed on this step's diff and the security workflow is green.
- **Phase closed, nothing carried.** Every finding recorded in
  `docs/phase01-qa-findings.md` has a destination (fixed, an issue
  number, or a named phase that owns it), the "Not in scope" section
  below is current, and no untracked item remains. Every step of this
  roadmap, this one included, reads `**Status:** Complete — PR #…` on
  `main` under a ✅ heading, the Summary Table's Status column and this
  roadmap's phase-level Status line say `Complete` under a ✅ title, and
  the parent project roadmap's Phase 1 entry (under a ✅ heading), its
  summary-table row and its header status line say `Complete` — all
  landed in this step's PR. This step's final response ends with two
  lines and nothing after them: "Step 12 is complete. You can now move
  on to Step 13." is replaced by "Step 12 is complete. Phase 1 is
  complete. You can now move on to Phase 2." — same Stage 6 rule: no
  "Follow-ups", no trailer.

---

## Post-Implementation Verification

Every V1–V12 check below runs **automatically in CI** on every push and
pull request — no manual invocation required — except the `--live` and
`--post` checks. Those read state that needs the maintainer's
authenticated `gh` session with admin rights (branch protection,
rulesets, environments, security settings, the required-check list),
external registries and enrolments (PyPI, TestPyPI, Read the Docs, RDAP,
GitHub Sponsors, thanks.dev), the networked fixture re-record, and the
operator-observed alarm notification. They run on the maintainer's
machine with `./scripts/verify-phase01.sh --post` before Phase 1 is
declared complete.

| Mode             | Workflow                                              | Runner                   | Coverage                                                                  |
| ---------------- | ----------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------- |
| `--fast`         | `phase-verify.yml` (matrix entry `01`, fast job)      | Ubuntu                   | Static checks 1–50; V1.1, V2.1, V3.1, V4.1, V5.1, V6.1, V7.1, V8.1, V9.1, V10.1, V11.1, V12.1–V12.3 |
| `--python`       | `ci.yml` (lint, types, tests, package run the same commands); local | Ubuntu, Windows, macOS | V7.2, V7.3, V9.2, V9.3                                     |
| `--security`     | `phase-verify.yml` (security job); `security.yml`     | Ubuntu                   | V2.3, V8.2, V12.4 (secret/PII scan + SAST + dependency audit + licences)  |
| `--live`         | local only — the maintainer's `gh` session            | Maintainer's machine     | V1.2–V1.4, V2.2, V2.4, V2.5, V4.3, V4.4, V5.3, V5.4, V6.2, V6.3, V8.4, V8.5, V10.2, V10.4, V10.5, V11.2–V11.4 |
| `--all`          | local                                                 | Any                      | `--fast` + `--python` + `--security`                                      |
| `--post`         | local, before the phase is declared complete          | Maintainer's machine     | `--all` + `--live` + V4.2, V5.2, V8.3, V10.3, V12.5 + `gh pr checks`      |

Local invocations remain available for ad-hoc runs and pre-release
sweeps:

```bash
./scripts/verify-phase01.sh --post   # static + V1-V12 + live + post checks
```

`--post` is the canonical command to run before declaring Phase 1
complete (and, from Phase 2 on, before tagging a phase release).

Other modes:

```bash
./scripts/verify-phase01.sh              # static checks (same as --fast)
./scripts/verify-phase01.sh --fast       # static checks only (Ubuntu CI)
./scripts/verify-phase01.sh --python     # static + lint, types, tests, build
./scripts/verify-phase01.sh --security   # secrets, SAST, dep audit, licences
./scripts/verify-phase01.sh --live       # GitHub, PyPI, TestPyPI, RTD (local)
./scripts/verify-phase01.sh --all        # static + python + security
```

The script reports each V-check by id (V1.1, V2.1, …) so a failure in any
workflow above maps directly to the corresponding row below.

### V1 — Preserve 0.2.x and land the roadmaps

> **Automated in CI.** `phase-verify.yml` → V1.1; `--live` → V1.2
> through V1.4.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V1.1 | Static checks 1–5 all PASS (roadmaps and kit tracked, user-context ignored, archive tags and branch exact). | `phase-verify.yml` runs `verify-phase01.sh --fast` on every push/PR. |
| V1.2 | `main` requires a PR, enforces admins and linear history, and forbids force-push and deletion. | `--live` (`gh api .../branches/main/protection`).                  |
| V1.3 | Squash-only merges titled by the PR title; merged branches deleted. | `--live` (`gh api repos/OWNER/REPO`).                                     |
| V1.4 | Both `archive-immutable-*` rulesets (`-branches`, `-tags`) are active. | `--live` (`gh api .../rulesets`).                                         |

### V2 — Legacy credential-logging fix and hardened pipeline

> **Automated in CI.** `phase-verify.yml` → V2.1 and V2.3; `--live` →
> V2.2, V2.4 and V2.5.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V2.1 | Static checks 6–10 all PASS (no credential logging, regression test and smoke script present, hardened and pinned workflows, rehearsal tag). | `phase-verify.yml --fast`.                         |
| V2.2 | The legacy CI is green on `legacy/0.2.x`'s HEAD on Python 3.11 and 3.12, credential-logging test included. | `--live` (`gh run list --branch legacy/0.2.x`).              |
| V2.3 | zizmor reports nothing above Low on the legacy workflows.          | `phase-verify.yml` security job (`--security`).                           |
| V2.4 | TestPyPI's integrity API returns attestations for both 0.2.6.dev1 files. | `--live`.                                                           |
| V2.5 | No `PYPI_API_TOKEN` secret; `testpypi` and `pypi` environments with tag policy `v*` and the maintainer as `pypi` reviewer; `release-tags` ruleset active. | `--live`.                               |

### V3 — 0.2.6 readiness gate

> **Automated in CI.** `phase-verify.yml` → V3.1.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V3.1 | Static check 11 PASS: the readiness document has its ten sections, no unresolved FAIL and a `Decision: GO` line. | `phase-verify.yml --fast`.                           |

### V4 — 0.2.6 security release and advisory

> **Automated in CI.** `phase-verify.yml` → V4.1; `--post` → V4.2;
> `--live` → V4.3 and V4.4.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V4.1 | Static checks 12–13 PASS (`v0.2.6` on the legacy line at version 0.2.6; dated CHANGELOG; release record with GHSA id). | `phase-verify.yml --fast`.                     |
| V4.2 | A clean-venv install of `pyeconomics==0.2.6` from PyPI reports 0.2.6, passes `check_credential_logging.py`, and both files carry attestations. | `--post`.                         |
| V4.3 | The advisory is published with the gate's affected range, patched version 0.2.6 and CWE-532. | `--live` (`gh api .../security-advisories`).             |
| V4.4 | Read the Docs `stable` serves 0.2.6 and `latest` builds from `legacy/0.2.x`. | `--live` (HTTP 200 and version text).                     |

### V5 — Characterize and archive 0.2.x

> **Automated in CI.** `phase-verify.yml` → V5.1; `--post` → V5.2;
> `--live` → V5.3 and V5.4.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V5.1 | Static checks 14–16 PASS (fixture hashes match the manifest; recorder pinned to 0.2.6; no `dev/` path tracked; besides open-PR head branches, only `main`, `legacy/0.2.x` and `archive/` branches on `origin`). | `phase-verify.yml --fast`. |
| V5.2 | `record_characterization.py --check` re-records byte-identically with sockets blocked. | `--post` (needs the network to build the isolated 0.2.6 environment). |
| V5.3 | The research archive repository exists, reports `PRIVATE` and holds `INDEX.md`. | `--live`.                                                    |
| V5.4 | None of the 25 pre-Phase-1 automated pull requests is open, and no Snyk pull request is open (Step 5 closed them; a closed pull request cannot be deleted). | `--live` (`gh api .../pulls?state=open`). |

### V6 — Architecture decision records

> **Automated in CI.** `phase-verify.yml` → V6.1; `--live` → V6.2 and
> V6.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V6.1 | Static checks 17–18 PASS (nine ADRs Accepted; index with 0008 reserved). | `phase-verify.yml --fast`.                                          |
| V6.2 | The four domains show a registration in RDAP, or ADR-0009 records the amendment. | `--live`.                                                   |
| V6.3 | The repository's owner matches ADR-0009, and the previous URL redirects. | `--live` (`gh repo view`).                                          |

### V7 — Repository reset and package skeleton

> **Automated in CI.** `phase-verify.yml` → V7.1; `ci.yml` (package job)
> → V7.2 and V7.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V7.1 | Static checks 19–25 PASS (0.2.x paths gone; `src/` package; `uv_build`, `>=3.12`, Apache-2.0; lock files; LF; ignores; licence files without ®). | `phase-verify.yml --fast`. |
| V7.2 | `uv sync --locked`, `uv build` and `twine check --strict` pass, and a clean-venv import prints the version. | `ci.yml` package job (`--python` locally).                  |
| V7.3 | The wheel and the sdist contain only allowlisted paths.            | `ci.yml` package job, which runs `scripts/checks/dist_contents.py` (`--python` locally). |

### V8 — Per-step security gate

> **Automated in CI.** `phase-verify.yml` → V8.1 and V8.2; `--post` →
> V8.3; `--live` → V8.4 and V8.5.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V8.1 | Static checks 26–30 PASS (hooks, semgrep rules and tests, security workflows with harden-runner, PR template, Dependabot ecosystems). | `phase-verify.yml --fast`.               |
| V8.2 | The `semgrep-test` hook passes (the bare `semgrep --test .semgrep/` is vacuous) and `prek run --all-files` is clean (with `SKIP=no-commit-to-branch` on a `main` checkout). | `phase-verify.yml` security job; `security.yml`. |
| V8.3 | With the repository's configuration, gitleaks flags a planted fake credential (the fake AKIA key in gitleaks' `testdata/repos/nogit/main.go`; gitleaks allowlists AWS's `…EXAMPLE` key) and semgrep and bandit flag `pickle.loads`, in a temporary directory outside the repository (expected failures). | `--post`. |
| V8.4 | Secret scanning, push protection, Dependabot alerts and security updates, and private vulnerability reporting are on. | `--live`.                         |
| V8.5 | The gate's checks are required on `main` with strict status checks. | `--live`.                                                                |

### V9 — Quality toolchain

> **Automated in CI.** `phase-verify.yml` → V9.1; `ci.yml` (lint, types
> and tests jobs) → V9.2 and V9.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V9.1 | Static checks 31–34 PASS (ruff `ALL`; mypy strict with the pydantic plugin; pytest with sockets off and doctests; branch coverage ≥ 95; prek hooks). | `phase-verify.yml --fast`. |
| V9.2 | `ruff format --check`, `ruff check` and `mypy` are clean.          | `ci.yml` lint and types jobs (`--python` locally).                        |
| V9.3 | `pytest --cov` passes with sockets disabled, doctests collected and the coverage floor met. | `ci.yml` tests matrix (`--python` locally).        |

### V10 — CI/CD and publishing rehearsal

> **Automated in CI.** `phase-verify.yml` → V10.1; `--live` → V10.2,
> V10.4 and V10.5; `--post` → V10.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V10.1 | Static checks 35–40 PASS (matrix, release routing, hardened workflows, old workflows gone, pr-title/dco/test jobs, `v1.0.0.dev1` on `main`). | `phase-verify.yml --fast`.       |
| V10.2 | The aggregate `test` check is green on `main`'s HEAD across all nine matrix cells. | `--live` (`gh run list --workflow ci.yml`).               |
| V10.3 | A clean-venv install of `pyeconomics==1.0.0.dev1` from TestPyPI prints its version, and both files carry attestations. | `--post`.                 |
| V10.4 | `main`'s required checks are lint, types, test, package, lockfile, pr-title, dco, the security checks and both `phase-verify` jobs, with strict status checks. | `--live`. |
| V10.5 | SHA pinning is required, the default workflow token is read-only, and `gh secret list` is empty. | `--live`.                                  |

### V11 — Governance, community and agent instructions

> **Automated in CI.** `phase-verify.yml` → V11.1; `--live` → V11.2
> through V11.4.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V11.1 | Static checks 41–45 PASS (community and agent files, issue forms, README notices, CITATION, AGENTS/CLAUDE). | `phase-verify.yml --fast`.                     |
| V11.2 | The community profile API lists README, CONTRIBUTING, CODE_OF_CONDUCT and the PR template; GraphQL `isSecurityPolicyEnabled` is true; the issue forms parse (GraphQL `contactLinks` lists `config.yml`'s links). The REST profile cannot show SECURITY or YAML issue forms, and `https://github.com/OWNER/REPO/community` renders only in a signed-in browser, so its Issue templates tick is a manual check (seen in Step 11). | `--live`.                |
| V11.3 | The seven defect-class labels exist.                              | `--live` (`gh label list`).                                               |
| V11.4 | thanks.dev's profile API returns 200; `funding.json` validates and lists every channel FUNDING.yml names; and when FUNDING.yml names `github:`, the Sponsors profile returns 200 without following redirects (issue #68, deferred to ROADMAP 8.1 by the maintainer on 2026-10-08). | `--live`. |

### V12 — CI integration + security

> **Automated in CI.** `phase-verify.yml` → V12.1 through V12.4 on every
> push/PR; `--post` → V12.5.

| ID         | Check                                                          | Automation                                                                |
| ---------- | -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V12.1      | `verify-phase01.sh --fast` exits 0 on Ubuntu CI.               | `phase-verify.yml` matrix entry `01`.                                     |
| V12.2      | `phase-verify.yml` matrix includes `01`.                       | `phase-verify.yml --fast` static check 49.                                |
| V12.3      | All static checks in `verify-phase01.sh` pass.                 | `phase-verify.yml --fast` records PASS only when no static check failed. |
| V12.4      | `verify-phase01.sh --security` exits 0 (secret/PII scan + SAST + dependency audit + licences clean). | `phase-verify.yml` security job on every push/PR. |
| V12.5      | The release-smoke alarm fired once on a synthetic failure, and the notification reached the maintainer. | `--post` reads the recorded run's conclusion; the notification is recorded in `docs/phase01-qa-findings.md`. |

---

## Summary Table

| Step    | Scope                          | Model             | Platform     | Reasoning dial  | Thinking | Conv | Status      |
| ------- | ------------------------------ | ----------------- | ------------ | --------------- | -------- | ---- | ----------- |
| 1       | Preserve 0.2.x, land roadmaps  | Claude Opus 5.5   | Claude Code  | Effort Medium   | On       | New  | Complete — PR #46 |
| 2       | Legacy fix + hardened pipeline | Claude Opus 5.5   | Claude Code  | Effort High     | On       | New  | Complete — PR #48 |
| 3       | 0.2.6 readiness gate           | Claude Opus 5.5   | Claude Code  | Effort Medium   | On       | New  | Complete — PR #49 |
| 4       | 0.2.6 release + advisory       | Claude Opus 5.5   | Claude Code  | Effort Medium   | On       | New  | Complete — PR #51 |
| 5       | Characterize + archive 0.2.x   | Claude Opus 5.5   | Claude Code  | Effort Medium   | On       | New  | Complete — PR #53 |
| 6       | Architecture decision records  | Claude Opus 5.5   | Claude Code  | Effort XHigh    | On       | New  | Complete — PR #54 |
| 7       | Reset + package skeleton       | Claude Opus 5.5   | Claude Code  | Effort High     | On       | New  | Complete — PR #59 |
| 8       | Per-step security gate         | Claude Opus 5.5   | Claude Code  | Effort XHigh    | On       | New  | Complete — PR #60 |
| 9       | Quality toolchain              | Claude Opus 5.5   | Claude Code  | Effort Medium   | On       | New  | Complete — PR #63 |
| 10      | CI/CD + publishing rehearsal   | Claude Sonnet 5.5 | Claude Code  | Effort High     | On       | New  | Complete — PR #64 |
| 11      | Governance + agent instructions | Claude Opus 5.5  | Claude Code  | Effort Medium   | On       | New  | Complete — PR #67 |
| 12      | QA + verify-phase01.sh         | Claude Opus 5.5   | Claude Code  | Effort Medium   | On       | New  | Complete — PR #70 |
| V1      | Preserve + bootstrap           | CI: phase-verify.yml; live | --  | --              | --       | --   | --          |
| V2      | Legacy fix + pipeline          | CI: phase-verify.yml; live | --  | --              | --       | --   | --          |
| V3      | Readiness gate                 | CI: phase-verify.yml | --        | --              | --       | --   | --          |
| V4      | 0.2.6 release                  | CI: phase-verify.yml; live, post | -- | --         | --       | --   | --          |
| V5      | Characterize + archive         | CI: phase-verify.yml; live, post | -- | --         | --       | --   | --          |
| V6      | ADRs                           | CI: phase-verify.yml; live | --  | --              | --       | --   | --          |
| V7      | Reset + skeleton               | CI: phase-verify.yml, ci.yml | -- | --             | --       | --   | --          |
| V8      | Security gate                  | CI: phase-verify.yml, security.yml; live, post | -- | -- | --  | --   | --          |
| V9      | Quality toolchain              | CI: phase-verify.yml, ci.yml | -- | --             | --       | --   | --          |
| V10     | CI/CD + rehearsal              | CI: phase-verify.yml; live, post | -- | --         | --       | --   | --          |
| V11     | Governance                     | CI: phase-verify.yml; live | --  | --              | --       | --   | --          |
| V12     | CI integration                 | CI: phase-verify.yml | --        | --              | --       | --   | --          |

---

## Model selection blocks

```text
PROMPT: Step 1 — Preserve 0.2.x and Land the Roadmaps
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: Medium
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: agentic — an exact git and GitHub-settings sequence that
preserves uncommitted work and protects main. PICK: Opus 5.5 is S in
agentic work and Claude Code's default model (AA Intelligence Index
57.6). EFFORT: Medium, the default, fits a fully specified procedure
whose risk is precision, not depth; thinking on; single agent.

PROMPT: Step 2 — Legacy Credential-Logging Fix and Hardened Release Pipeline
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — a security fix plus a
Trusted Publishing pipeline whose mistakes publish irreversibly. PICK:
Opus 5.5 is S in coding and knowledge and beats Fable 5.1 on the cost
tie-break (SciCode 66.9). EFFORT: High for security-sensitive,
multi-system work; a documented pattern, so not Extra High; thinking on.

PROMPT: Step 3 — 0.2.6 Readiness Gate
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: Medium
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: knowledge — an evidenced release checklist, an
affected-range audit and a CWE- and CVSS-scored advisory draft. PICK:
Opus 5.5 is S in knowledge, one of two catalog models so rated (HLE
61.4%). EFFORT: Medium, the default, fits a bounded checklist whose
judgement calls end with the maintainer; thinking on; single agent.

PROMPT: Step 4 — 0.2.6 Security Release and Advisory
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: Medium
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: agentic — executing a decided release: bump, merge, tag,
approve, verify and publish the advisory. PICK: Opus 5.5 is S in agentic
work and Claude Code's default model (AA Intelligence Index 57.6).
EFFORT: Medium, the default, because the gate removed the judgement
calls and each action is verified by command; thinking on.

PROMPT: Step 5 — Characterize and Archive 0.2.x
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: Medium
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — a deterministic
network-blocked recorder plus inventory, private archive and branch
retirement. PICK: Opus 5.5 is S in coding and Claude Code's default
model (SciCode 66.9). EFFORT: Medium, the default, fits bounded parts
whose keep-or-discard calls belong to the maintainer; thinking on.

PROMPT: Step 6 — Architecture Decision Records
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Astra
PLATFORM: Claude Code
EFFORT: XHigh
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: planning, knowledge secondary — nine architecture
decisions binding every later phase, each resting on verifiable facts.
PICK: Opus 5.5 is S in planning and knowledge and beats Fable 5.1 on the
cost tie-break (AA Intelligence Index 57.6). EFFORT: XHigh — High plus a
rung for cross-cutting planning; defaults exist, so neither Max nor
Ultracode.

PROMPT: Step 7 — Repository Reset and Package Skeleton
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — a repository-wide reset
and exact PEP 621, 639, 735 and 751 packaging. PICK: Opus 5.5 is S in
coding and knowledge and beats Fable 5.1 on the cost tie-break (SciCode
66.9). EFFORT: High for cross-cutting scope that applies settled ADRs
rather than deciding them; thinking on; single agent.

PROMPT: Step 8 — Per-Step Security Gate
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: XHigh
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — the fail-closed gate,
custom semgrep rules and five security workflows. PICK: Opus 5.5 is S in
coding and knowledge and beats Fable 5.1 on the cost tie-break (AA
Intelligence Index 57.6). EFFORT: XHigh for multi-step verification
across many files and two operating systems; thinking on; single agent.

PROMPT: Step 9 — Quality Toolchain
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: Medium
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — strict lint, type and test
configuration for a near-empty package, verified by running each tool.
PICK: Opus 5.5 is S in coding and Claude Code's default model (SciCode
66.9). EFFORT: Medium, the default, suffices for well-known tool
configurations; thinking on; single agent.

PROMPT: Step 10 — CI/CD and Publishing Rehearsal
MODEL: Claude Sonnet 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — the CI matrix, the 1.x
release pipeline and an end-to-end TestPyPI rehearsal. PICK: Sonnet 5.5
is S in coding and agentic work and wins the coverage tie-break (AA
Intelligence Index 56.0). EFFORT: High for scope covering every future
merge and release; a port of a proven design; thinking on.

PROMPT: Step 11 — Governance, Community and Agent Instructions
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Astra
PLATFORM: Claude Code
EFFORT: Medium
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: knowledge, planning secondary — community, legal-notice
and agent-instruction files that must match the project roadmap exactly.
PICK: Opus 5.5 is S in knowledge and Claude Code's default model (HLE
61.4%). EFFORT: Medium, the default, because legally weighted wording is
quoted verbatim rather than composed; thinking on; single agent.

PROMPT: Step 12 — QA and Verification Script
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: Medium
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — the first verify script, its
tests and workflow, and a live walk of every criterion. PICK: Opus 5.5 is
S in coding and agentic work, Claude Code's default model (AA
Intelligence Index 57.6). EFFORT: Medium, the default, fits numerous but
mechanical checks; thinking on; single agent.
```

---

## Not in scope (from product roadmap)

The parent ROADMAP's Phase 1 section carries no separate "Not in scope"
list; these items are deferred by its phase boundaries and its §6 "Out
of Scope":

- The model registry, ADR-0008 (numerical conventions) and every catalog
  model. They are Phase 2's, built on Step 7's skeleton.
- The data layer — providers, credential redaction for 1.x, the
  licence-aware cache, vintages — and rebuilding the four policy rules on
  ALFRED. Phase 3 owns them and tests against Step 5's fixtures.
- The documentation site (Sphinx with MyST-NB per ADR-0007) and its
  preview. Phase 2 (2.5) builds them; Read the Docs serves 0.2.x until
  Phase 5 replaces it.
- The CLI, REST API, MCP server and exports (Phase 4), and the web app,
  hosting, Cloudflare and Cloud Run (Phase 5).
- The first PyPI upload of 1.0 (`1.0.0a1`) and its readiness gate. Phase
  2 releases it through Step 10's pipeline.
- Personalised advice, trading features, licensed-data redistribution
  and the other §6 exclusions. They stay excluded in every phase.

Additionally not in scope for this phase:

- Any 0.2.x change beyond the credential-logging fix and its pipeline:
  the import-time FRED client, the pickle cache, FRED caching against its
  terms, development tools as runtime dependencies, and Python 3.13
  support. 0.2.x is security-only and ends at 1.0.0 (ADR-0003).
- A trademark clearance search and USPTO filing. ADR-0009 records the
  decision; the maintainer schedules them (cost TBD) before the Phase 5
  launch at the latest.
- A contributor licence agreement. ADR-0004 requires one only if an
  outside contribution might ever be relicensed.
- Codecov or any other third-party coverage service. CI prints coverage
  and enforces its floor itself (Step 10).
- Python 3.15 in CI if it is not final when Step 10 runs. Step 10 opens
  an issue that adds it on release.
- A Docker image. The JupyterLab image retires with 0.2.x; a service
  container arrives in Phase 4 (4.7).
- Porting any `dev/` prototype. Phase 7 reviews them as reference
  material only (7.5).
- Rewriting history to remove the ® from past commit authors. Only
  future commits change (Step 11).

Carried over during execution — the Triage rule's carry-over checklist:
each upstream gap or deferred finding, the step whose `<task>` was
patched, and the step or phase that owns it. Phase 2's roadmap carries
forward whatever is still open here.

- None when this roadmap was written.
- From Step 6 (ADRs). Patched: Steps 8, 11 and 12, for the checks the
  ADRs' Confirmation sections name. Owned by Phase 2's roadmap:
  - a Pyodide import smoke test of the core wheel (ADR-0002);
  - the `FutureWarning`-based deprecation warning class, and
    `registry.validate()` rejecting a released model id that is missing
    or reused (ADR-0003);
  - a docs build with warnings as errors, executed notebooks and Sybil
    collecting Markdown examples (ADR-0007);
  - every release step re-checking NumPy's and SciPy's `requires_python`
    and raising the floor if either moved (ADR-0010). SPEC 0 already
    drops Python 3.12 in 2026 Q4, so the move to `>=3.13` is expected
    during the 1.0 pre-releases;
  - every release step checking its tag against ADR-0003's milestone
    table.
- From Step 10 (CI/CD). Patched: Step 11 (CONTRIBUTING says the `dco`
  check exempts only Dependabot's pull requests) and Step 12 (static
  check 37 exempts `uses: ./...` local reusable workflows; V7.3 names
  `scripts/checks/dist_contents.py`); Step 10's own `id-token`
  wording now names Scorecard's job beside the two publish jobs.
  Owned by issue #65: Python 3.15
  joins `ci.yml`'s matrix, with its classifier, at its final release
  (expected 2026-10-09; ADR-0010).
- From Step 11 (governance). Patched: Step 11's funding requirement and
  criterion (amended by the maintainer on 2026-10-08), and Step 12
  (static check 41 and V11.4 require the Sponsors listing; the `--live`
  checks verify Sponsors without following redirects and thanks.dev
  through its API). Owned by issue #68, moved from Step 12 to ROADMAP
  8.1 (Gate G1 carry-over) by the maintainer on 2026-10-08: the
  `pyeconomics-dev` GitHub Sponsors listing goes live after GitHub
  Support detaches the wrongly linked Stripe account, and FUNDING.yml
  and funding.json regain their Sponsors entries. Phase 1 closed with
  thanks.dev live.

---

_This roadmap is the execution plan for Phase 1. Each step's
`**Status:**` line is flipped by that step's own PR (Status rule), so
this file on `main` is the phase's ledger — `grep -n '^\*\*Status:\*\*'`
reports progress. After all steps and verification pass, and every
finding has a destination, Phase 1 is complete — declared with the line
"Phase 1 is complete. You can now move on to Phase 2." and nothing after
it — and Phase 2 (Model Engine & Core Catalog) inherits a protected
`main` holding the `src/pyeconomics` skeleton on `uv_build` with locked
dependencies, the fail-closed security gate and strict toolchain, a
three-OS CI matrix, a Trusted Publishing pipeline rehearsed to TestPyPI,
nine accepted ADRs, one agent rulebook, and `verify-phase01.sh` as the
template for `verify-phase02.sh`, while Phase 3 inherits the 0.2.x
characterization fixtures._

## Post-merge addendum (2026-10-09) — Phase 2 changes to verify-phase01.sh

Phase 2's Cross-phase verification rule: a Phase 2 pull request that
legitimately invalidates one of this phase's checks narrows the check to the
invariant it protected, never deletes it, and adds one line here.

- Static check 18 (Phase 2 Step 1): accepts ADR-0008's index row as either
  reserved or Accepted with its file's date, because Phase 2 accepted
  ADR-0008. It still requires the nine Phase 1 ADRs Accepted.
- Static check 44 (Phase 2 Step 1): `CITATION.cff`'s version equals
  `pyproject.toml`'s, and its licence is Apache-2.0, because the version
  moved to `1.0.0a1.dev1` and moves again at each release.
- V7.2 (`--python`, Phase 2 Step 1): the clean venv installs the wheel with
  its runtime dependencies from PyPI (`--no-config`, no `--no-index`),
  because the wheel now requires pydantic, NumPy, SciPy and pandas.
- Not a script check, recorded for the same reason: Step 8's
  `tests/checks/test_licences.py` pinned an empty
  `licence_exceptions.toml`; it now pins the four exceptions the maintainer
  reviewed in Phase 2 Step 1 (numpy, scipy, pandas, python-dateutil).

- Static check 19 (Phase 2 Step 7): permits the new `docs/conf.py` only with
  MyST-NB, sphinx-autoapi over `src/pyeconomics`, the PyData theme and the
  model-page extension. All other legacy paths remain forbidden.
- Static check 35 and V10.2 (issue #65, 2026-10-12): require Python
  3.12-3.15 with matching classifiers and twelve green OS/Python cells,
  preserving the full supported-version matrix after Python 3.15's final
  release. CI uses uv 0.13.0, which knows the final 3.15 interpreter builds;
  the former uv 0.12.15 resolves `3.15` to a release candidate. The minimum
  Python floor remains 3.12, so static check 21 is unchanged.

- V7.2 (`--python`, Phase 2 Step 15, 2026-10-14): explicitly selects the
  project's interpreter for its fresh wheel environment, preserving the
  wheel/dependency install and version-import proof. The global uv default
  otherwise selected Python 3.15 after a Python 3.13 local suite; all supported
  minors remain covered by CI. No check or supported version is removed.

## Post-merge addendum (2026-10-22) — Phase 3 changes to verify-phase01.sh

- Static check 13 (Phase 3 Step 20): consumes the complete changelog and
  release-record producer output before deciding whether evidence matches.
  Early-exit grep could otherwise cause a false SIGPIPE failure under Bash
  pipefail. The dated 0.2.6 changelog and GHSA inside the Release record
  remain required; large-output positives and missing-evidence negatives
  verify the unchanged acceptance invariant.
