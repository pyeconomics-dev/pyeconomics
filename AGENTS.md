# AGENTS.md

The rules every coding-agent session in this repository follows: Claude Code,
Codex, Cursor, Antigravity or any other. `CLAUDE.md` imports this file. Humans
follow the same rules through [CONTRIBUTING.md](CONTRIBUTING.md).

The project roadmap is [docs/roadmap/ROADMAP.md](docs/roadmap/ROADMAP.md); each
phase has its own roadmap beside it (`docs/roadmap/phaseNN-roadmap.md`). When a
rule here and the roadmap disagree, the roadmap wins; fix this file in the same
pull request.

## Never print secrets

- Never print, echo, log or paste environment variables, tokens, API keys or
  passwords in a session: no `env`, `printenv`, `set`, `Get-ChildItem Env:`,
  `echo $SOME_TOKEN`, `gh auth token` or `cat .env`. Check that a variable
  exists by name only (for example `test -n "${VAR+x}"`), never by value.
- Never write a real credential into a file, test, fixture, commit message,
  issue or pull request. The gate blocks even fake credentials in docs; refer
  to a test key by its location instead.
- Session transcripts can leak. Treat everything you print as public.

## Repository layout

```
src/pyeconomics/   the package (src layout); py.typed
tests/             unit · golden · property · contract · parity · e2e
  checks/          tests for scripts/checks
  fixtures/legacy/ 0.2.x characterization fixtures, byte-exact: never edit
scripts/checks/    the gate's own checks (licences, lock index, dist contents …)
scripts/legacy/    the 0.2.x fixture recorder, byte-exact: never edit
.semgrep/          project semgrep rules and their tests
docs/adr/          architecture decision records
docs/roadmap/      the project and phase roadmaps: the ledger of what is done
web/               placeholder for the Phase 5 site
planning/          roadmodel's planning kit, re-exported by its updater: never edit
```

The target layout, as phases add it, is in ROADMAP §3: `core/`, `models/`,
`data/`, `cli/`, `server/` and `mcp/` under `src/pyeconomics/`.

## Registry rules

From Phase 2, which builds the registry (ROADMAP §3; ADR-0001):

- A model is a pure function with typed inputs and outputs plus metadata. It
  never does I/O: no data fetching, printing, plotting, file access or LLM
  calls. Live data reaches it through a declared binding the data layer
  resolves.
- One registry feeds every surface. Never hand-write a CLI command, endpoint,
  MCP tool or page for a model; generate it from the registry.
- A model meets the definition of done in ROADMAP §5 "Model quality &
  governance" (CONTRIBUTING lists it): a model card, citations, at least three
  cited golden cases, property tests, units and bounds.
- Model ids are permanent (ADR-0003). Never copy CFA Program curriculum text,
  questions or worked examples.
- Declare a model with `@model` from `pyeconomics.core`, list the `Model` object
  in its module's `__all__`, and name the module in
  `[project.entry-points."pyeconomics.models"]`. `registry.validate()` must pass
  (`uv run python -c "from pyeconomics import registry; registry.validate()"`);
  it reports every problem as `<model>: [<rule>] <detail>`.
- Bound every array field's length on the field, with `Field(max_length=...)`.
  Its elements come from the `RateArray` family or `ARRAY_INPUT`; stacked
  constraints on one type do not narrow, so those aliases fix no length.
- Under `src/pyeconomics/models/`, imports are held to an allowlist
  (`tests/registry/test_model_imports.py`) and the `model-purity` semgrep rule
  bans I/O, the clock, the environment, the network and global randomness.
  Import an extra's library only inside `compute`.
- `pyeconomics.core` exports the decorator as `model`, which hides the module
  of that name. Import by path (`from pyeconomics.core.model import Model`);
  `import pyeconomics.core.model as m` binds the decorator. Likewise
  `pyeconomics.core.provenance` is `core.random`'s function: import the data
  provenance record by path (`from pyeconomics.core.provenance import
  DataSource`) or from `pyeconomics.core`.

## Data layer rules

From Phase 3, which builds the data layer (ADR-0011):

- No module under `src/pyeconomics/core/` imports `pyeconomics.data`, and no
  model does; the vocabulary they need (`DataSource`, `RealtimePeriod`,
  `LicenceClass`, `LlmUse`, later `Binding` and `Bound`) lives in core
  (`tests/data/test_layering.py`).
- Only the data layer's transport, cache, configuration and credential
  modules touch the network, files, the environment or the clock. A new pure
  module joins `PURE_MODULES` in `tests/data/test_layering.py`.
- A frame indexes a period by its last day, marks a missing value `None`
  (never NaN) and holds rates as decimals, converted only in a provider's
  transform step with `percent_to_decimal`.
- A source whose terms forbid storage, FRED and ALFRED among them, is never
  written to disk: no cache path, no opt-in.
- No value type has a field for a URL, host, path or credential; the one URL
  is a source's terms page (`tests/data/test_value_security.py`).
- A key is read only through `pyeconomics.data.credentials` (`resolve_key`)
  and held as a `Secret`. Only `data/credentials/` and `data/transport/` call
  `.reveal()` (the `secret-reveal` semgrep rule). A failure that may hold a
  key or a URL is re-raised with `redaction.call_scrubbed`, never with
  `raise ... from`.
- Every test runs with its own configuration and cache directories, no
  `*_API_KEY` or `PYECONOMICS_*` variable and an in-memory keyring (the
  `isolated` fixture, `tests/config_isolation.py`). Plant keys with
  `tests/data/leakcheck.py`'s `canary()`, never a literal, and check sinks
  with `LeakCheck`: never assert on a key's value in a way pytest could print.

## Units

Rates, returns, yields and percentages are decimals in every API (`0.05`, not
`5`), as ADR-0008 fixes. Every numeric input and output declares its unit.

## Testing

- Run tests with `uv run pytest`, never `python -m pytest`: that puts the
  working directory on `sys.path` and can import a stale copy of the package.
- Sockets are disabled in tests (`pytest-socket`); no test touches the
  network. Warnings are errors.
- Golden tests (cited values with tolerances) and property tests (hypothesis)
  are required for every model from Phase 2. Start a model with
  `uv run python scripts/new_model.py <id>`; the golden format is in
  `tests/golden/README.md`, and CONTRIBUTING's "How it is checked" lists the
  checks a model meets.
- Mark a property test `@pytest.mark.invariant("<model id>", "<invariant id>")`
  for each invariant a model declares, and an independent-library comparison
  `@pytest.mark.oracle("<model id>")`. An oracle test never skips: a missing
  library must fail the suite.
- Never cite the CFA Program curriculum in a golden source or a reference.
- Coverage must stay at or above 95% (branch coverage), and `core/` at 95% and
  `models/` at 90% on their own (`scripts/checks/coverage_floors.py`).

## File headers

- Python files open with three lines; ruff's `CPY001` requires the copyright
  line:
  ```python
  # <repo-relative path>
  # Copyright <year> Nathan Ramos, CFA
  # SPDX-License-Identifier: Apache-2.0
  ```
- YAML and TOML files start with `# <repo-relative path>`. Markdown and JSON
  follow their own conventions (JSON allows no comments).

## The security gate

The pre-commit hook (prek, `.pre-commit-config.yaml`) is the per-step security
gate: secret scan (gitleaks), SAST (bandit, semgrep with project rules),
dependency audit (`pip-audit`) and the runtime licence allowlist, beside the
quality toolchain. CI re-runs the same hooks as required checks.

- It is fail-closed. A finding blocks the commit: fix it in the same step.
- Never use `SKIP=` or `--no-verify` on your own judgement. A bypass is for a
  genuine emergency only, needs the maintainer's approval, and is recorded in
  the pull request body's "Security gate bypass" field with the hook, the
  commit and the justification.
- Before each commit, also review the diff for sensitive data: no key in a log,
  manifest, cache, exception or export; no licensed data in fixtures; least
  privilege for every token and workflow permission.
- A new runtime dependency must pass the licence allowlist (ADR-0004). Run
  `uv add`, `uv lock` and `uv export` with `--no-config`, so a user-level
  private index never reaches `uv.lock`.

## The step lifecycle

Roadmap steps run one at a time, each in its own conversation, following six
stages with no exceptions (ROADMAP §5 "Step lifecycle"; the phase roadmap's
Overview restates them):

1. **Create the branch first.** Before any other action, run
   `git checkout -b <the step's **Branch:** line>` from a clean, up-to-date
   `main`. `main` is protected with `enforce_admins`; a direct push fails.
2. **Work on the branch**, passing the security gate on every commit.
3. **Open the pull request, then mark the step.** `gh pr create --base main`
   with a Conventional Commits title and a body that references the step and
   its acceptance criteria. Then set the step's `**Status:**` line to
   `Complete — PR #<n> (<YYYY-MM-DD>)`, append ` ✅` to its heading, set its
   Summary Table cell, and commit (`docs: mark Phase N Step M complete`) and
   push on the same branch.
4. **Wait for every required check, then squash-merge**
   (`gh pr merge <n> --squash --delete-branch`). If the branch falls behind,
   `gh pr update-branch --rebase`; never merge `main` into it. A step that
   deploys or publishes is not done until its Deployed & verified check
   passes.
5. **Retire the branch**: `git switch main`, `git pull --ff-only`,
   `git fetch --prune`, and delete local branches whose upstream is gone.
6. **Dispose of every finding, then declare completion** with the exact line
   the roadmap gives, as the last line of the response.

**Status rule.** The phase roadmap on `main` is the ledger. A step is complete
exactly when its own pull request, carrying its `Complete` line, merges. Never
mark a step complete from your own reading of the git history, and never start
a step whose predecessor does not read `Complete`.

**Triage rule.** Classify every finding that is not the step before acting on
it (ROADMAP §5 "Defect handling & triage"). Each class has one destination and
a label: `spec-rot` (edit the step's task now), `upstream-gap` (patch the
earlier step and the carry-over list), `bug` (fix in-step only if it blocks
the step, otherwise an issue), `model-error` (High: `fix/` branch, golden test,
errata), `architecture` (an issue for a future phase), `process` (write it
where the next session reads it; make it a check if it is a rule) and
`security` (jumps the queue by severity). A finding that is only described in
chat is not disposed of. A pull request holds its step plus blocking fixes
only, and lists the issues it opened.

## Commits and pull requests

- Commit with `git commit -s`. The `dco` check requires a `Signed-off-by:`
  trailer matching each commit's author name and email.
- Pull request titles are Conventional Commits:
  `<type>(<scope>)!: <description>`, with type one of `feat`, `fix`, `docs`,
  `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. The
  title becomes the squash commit on `main`.
- Fill in every section of the pull request template.
- Branch prefixes: `feature/`, `fix/`, `hotfix/`, `chore/`, `docs/`, `perf/`,
  `release/`, `model/`.

## Worktrees

One working tree and one step in flight is the default. A second tree is made
only with `git worktree add`, never a second clone, and only for a `hotfix/`
interrupting a step, steps a roadmap's Execution Order draws in parallel, or
worktree-isolated subagents inside a step (ROADMAP §5 "Worktree strategy").

- Location: the git-ignored `.worktrees/<branch-slug>/` inside the repository.
- Bootstrap before use: run `uv sync --locked` inside the new worktree. Never
  borrow the primary tree's environment.
- One conversation touches one worktree. Merge from the primary tree.
- Remove the worktree (`git worktree remove`, then `git worktree prune`)
  before deleting its branch.

## Windows notes

- Use Git Bash for POSIX shell commands. Set `MSYS_NO_PATHCONV=1` before a
  command with a `rev:path` argument (such as `git show origin/main:file`), or
  Git Bash rewrites it into a Windows path.
- Text is LF everywhere (`.gitattributes`, `.editorconfig`). Python's
  `write_text` writes CRLF on Windows; write bytes, or let an editor tool make
  the change.
- Windows has no executable bit. Mark a script executable in the index with
  `git update-index --chmod=+x <path>`.
