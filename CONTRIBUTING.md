# Contributing to pyeconomics

Thank you for helping. pyeconomics 1.0 is being rebuilt phase by phase from the
[project roadmap](docs/roadmap/ROADMAP.md); read its §4 for the phase in flight
before proposing large changes. By taking part you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md). Report security issues privately, as
[SECURITY.md](SECURITY.md) describes, never in a public issue.

Coding agents follow [AGENTS.md](AGENTS.md), which restates these rules.

## Setup

You need [uv](https://docs.astral.sh/uv/) and git. Then, once per clone:

```sh
git clone https://github.com/pyeconomics-dev/pyeconomics.git
cd pyeconomics
uv sync
uv run prek install
```

`uv sync` installs the package in editable mode with the `dev` dependency
group. `uv run prek install` installs the pre-commit hook that runs the quality
toolchain and the security gate on every commit. There is nothing else to
install: prek builds the pinned gitleaks hook with its own Go toolchain on its
first run.

Run the tests with `uv run pytest`, never `python -m pytest`, which puts the
working directory on `sys.path` and can import a stale copy of the package.
Run every hook by hand with `uv run prek run --all-files`.

## Making a change

1. Open an issue first for anything larger than a small fix, using one of the
   issue forms. A model request needs a citation; a data-source request needs
   the source's terms-of-use URL.
2. Branch from an up-to-date `main` with a prefix from ROADMAP §5 "Branch
   naming convention": `feature/`, `fix/`, `hotfix/`, `chore/`, `docs/`,
   `perf/`, `release/` or `model/`.
3. Commit with sign-off (`git commit -s`; see below). The pre-commit hook must
   pass.
4. Open a pull request against `main` and fill in the template: the roadmap
   step, summary, test plan, breaking changes, rollback plan, licence check and
   sensitive-data checklist.
5. Every required check must pass. Pull requests are squash-merged, so the
   pull request title becomes the commit on `main`.

### Commit conventions

- **Conventional Commits.** The pull request title must match
  `<type>(<scope>)!: <description>`, where type is one of `feat`, `fix`,
  `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore` or
  `revert`; the scope and `!` are optional. `!` (or a `BREAKING CHANGE:`
  footer) marks a breaking change. The `pr-title` check enforces it.
- **DCO sign-off.** Every commit carries a `Signed-off-by:` trailer certifying
  the [Developer Certificate of Origin 1.1](https://developercertificate.org/),
  added by `git commit -s`. The `dco` check requires the trailer's name and
  email to match each commit's author, so set `user.name` and `user.email`
  before committing. Only Dependabot's own pull requests are exempt. To fix a
  branch that lacks sign-offs, run `git rebase --signoff main` and force-push
  your branch.
- **No CLA.** The DCO is the whole of the paperwork (ADR-0004).

### Python file header

Every Python file opens with three comment lines; ruff's `CPY001` requires the
copyright line:

```python
# src/pyeconomics/example.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
```

The first line is the file's repository-relative path. YAML and TOML files
start with the same path comment; Markdown and JSON follow their own
conventions.

## The security gate

The pre-commit hook is the project's per-step security gate (ROADMAP §5
"Per-step security gate"): gitleaks for secrets, bandit and semgrep with the
project's rules for SAST, `pip-audit` over `uv.lock` for the dependency audit,
the runtime licence allowlist, and zizmor (security) and actionlint (validity)
over the workflows. It is fail-closed, and CI re-runs the same hooks as
required checks.

The bypass (`SKIP=<hook>` or `git commit --no-verify`) is for genuine
emergencies only. Every use is recorded in the pull request body's "Security
gate bypass" field with the hook, the commit and why it could not wait. CI still
runs every check, so a bypass never lands an issue on `main`.

## Licence check for dependencies and data sources

pyeconomics is Apache-2.0 from 1.0 (ADR-0004).

- **A new runtime dependency**, meaning anything a user installs with the
  package or an extra, must carry one of `MIT`, `BSD-2-Clause`,
  `BSD-3-Clause`, `Apache-2.0`, `ISC`, `NCSA` or `PSF-2.0`. The `licences` hook
  checks the locked runtime closure. FinancePy, rateslib, getfactormodels, the
  DBnomics client, AGPL OpenBB extensions and MCP servers, and `full_fred` are
  excluded by name. List each new dependency and its licence in the pull
  request.
- **A new data source** must have terms that allow its intended use. Record its
  terms-of-use URL and how ROADMAP §5 "Data licensing policy" classes it
  (hosted-safe or library-only), and carry its required notice.
- Add or change dependencies with `uv add --no-config …` / `uv lock --no-config`
  if your user-level uv configuration adds a private index, so no private URL
  reaches `uv.lock`.

## Model definition of done

From Phase 2, a model merges only when it meets ROADMAP §5 "Model quality &
governance", enforced by `registry.validate()` and the pull request template:

| Requirement      | Rule                                                                                         |
|------------------|----------------------------------------------------------------------------------------------|
| Identity         | Permanent dotted id; a per-model version that bumps on any output change                     |
| Model card       | Summary, formula, variables with units, assumptions, limitations, evidence status, curriculum mapping, references |
| Citations        | At least one primary reference; every golden case cites its source; no copied copyrighted text — numbers and formulas only, in our own words |
| Golden tests     | At least three cited cases including an edge case, each with a tolerance                     |
| Property tests   | One per invariant the domain guarantees                                                      |
| Units and bounds | Every numeric input and output                                                               |
| Parity           | Identical canonical outputs from Python, CLI, REST API, MCP and web                          |
| Hosted budget    | Declared compute cost class; heavy models get caps or async jobs in hosted mode              |
| Errata           | A shipped wrong number is a High defect: fixed, regression-tested, and logged on a public errata page |

A model is a pure function: it never fetches data, prints, plots or calls an
LLM. Never copy CFA Program curriculum text, questions or worked examples; cite
each formula's originators and take golden values from independent sources.
Requests outside the model layer are closed by citing
[ADR-0001](docs/adr/0001-product-boundaries.md) and ROADMAP §6.

### How it is checked

Start a model with `uv run python scripts/new_model.py <domain>.<name>`. It
creates the model module, a golden file and a property-test file, each failing
until you complete it, and says what to register by hand. Then:

- **`registry.validate()`** rejects an incomplete specification, one line per
  problem naming the model and the rule. Run it with
  `uv run python -c "from pyeconomics import registry; registry.validate()"`.
- **`tests/golden/`** holds the golden cases. `tests/golden/README.md` fixes the
  format; the harness fails a registered model with no file, fewer than three
  cases or no edge case (unless the file records why), a case with no source or
  locator, an expected field the model does not output, and any output outside
  its tolerance. A textbook value is recomputed independently or quoted at its
  published precision.
- **The citation guard** (`tests/golden/test_sources.py`) fails any golden source
  or model reference that cites the CFA Program curriculum. Papers in the
  *Financial Analysts Journal* are allowed.
- **The `invariant` marker.** For each invariant the specification declares,
  write a hypothesis property test marked
  `@pytest.mark.invariant("<model id>", "<invariant id>")`.
  `tests/models/test_invariant_coverage.py` scans the tests and fails on an
  uncovered invariant, on a marker naming a model or invariant that does not
  exist, and on a marked test that is not a property test.
- **The `oracle` marker.** A test that compares the model with an independent
  library carries `@pytest.mark.oracle("<model id>")`. It never skips: import
  the library at the top of the module, so a missing oracle fails the suite.
- **The contract suite** (`tests/models/test_contract.py`) generates valid inputs
  from each model's fields (`tests/strategies.py`) and checks that outputs stay
  within their bounds and are finite or `None` with a warning, that nothing but
  `DomainError` and `ConvergenceError` escapes (for a model that lists
  limitations, which the reviewer reads for the condition, and never for every
  input), that two runs give the same canonical JSON, and that the result
  survives a round trip. A model with a rule between fields (a strike
  below a spot) adds a strategy to `strategies.OVERRIDES`.
- **The schema snapshots** (`tests/surfaces/test_registry_snapshots.py`) hold
  every model's input and output JSON Schema, the registry schema and the
  (id, version, domain) index under `tests/surfaces/__snapshots__/`. A new
  model fails until its snapshots exist, and a changed schema fails until they
  are rewritten: run `uv run pytest tests/surfaces --snapshot-update`, review
  the diff, and name every changed schema in `CHANGELOG.md`, because model ids,
  field names, units and their schemas are public API at 1.0.0 (ADR-0003).
- **The parity suite** (`tests/parity/`) runs each golden case through the
  Python API, the command line, the REST API and MCP and requires the same
  bytes from each; it needs no edit for a new model. A model with bindings is
  also bound with its default profile over stand-ins for every provider
  (`tests/parity/parity_world.py`): if its default profile needs an input that
  is not data, add it to `GIVEN` there.
- **The coverage floors.** CI's tests job runs
  `scripts/checks/coverage_floors.py`: 95% branch coverage on `src/pyeconomics/core/`
  and 90% on `src/pyeconomics/models/`, beside the overall 95%.

## How roadmap steps run

The maintainer and coding agents implement the roadmap one step at a time, each
in its own branch, pull request and conversation. Every step follows a
six-stage lifecycle (ROADMAP §5 "Step lifecycle"):

1. **Create the branch** named on the step's `**Branch:**` line, from an
   up-to-date `main`, before any other work.
2. **Work on the branch**, passing the security gate on every commit.
3. **Open the pull request, then mark the step** `Complete — PR #n (date)` in
   its phase roadmap, on the same branch.
4. **Wait for green checks, then squash-merge.**
5. **Retire the branch** locally and remotely.
6. **Dispose of every finding, then declare completion.**

**Triage rule.** A finding that is not the step is classified before it is
acted on (ROADMAP §5 "Defect handling & triage"), and each class has one
destination and one label:

| Label          | Class                  | Destination                                                    |
|----------------|------------------------|----------------------------------------------------------------|
| `spec-rot`     | Spec rot               | Edit the step's task in the phase roadmap now                  |
| `upstream-gap` | Upstream gap           | Patch the earlier step's task; add it to the carry-over list   |
| `bug`          | Implementation bug     | Fix in-step only if it blocks the step; otherwise an issue     |
| `model-error`  | Model error            | High: a `fix/` branch, a golden test and an errata entry       |
| `architecture` | Architectural question | An issue for a future phase                                    |
| `process`      | Process improvement    | Written where the next session reads it; a check if it is a rule |
| `security`     | Security finding       | Jumps the queue by severity (SECURITY.md)                      |

A pull request contains its step plus blocking fixes only, and lists the issues
it opened.

### Phase verification

Each completed phase has a verifier, `scripts/verify-phaseNN.sh`, and
`phase-verify.yml` runs every one of them (`--fast` and `--security`) on each
pull request. Run one by hand from the repository with
`bash scripts/verify-phase04.sh --fast`. The verifiers need bash 4 or later:
under an older bash (macOS's `/bin/bash` is 3.2) each exits 2 with a message
rather than run, so install a newer one first (`brew install bash`). A check
that crashes ends the script with a non-zero status, never a pass. On Windows,
run them in Git Bash.
