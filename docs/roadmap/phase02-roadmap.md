# Phase 2 Roadmap — Model Engine & Core Catalog ✅

**Status:** Complete — 2026-10-14

## Overview

Phase 2 opens the gate every surface stands on. Phase 3 binds live data to
models, Phase 4 generates the CLI, REST API and MCP server from them, and
Phase 5 renders a web page for each one, so none of them can start until
the model contract is fixed and proven: the numerical conventions, the
specification and registry, the result and its manifest, the schemas and
the verification harness. The phase ships that engine and the 32 data-free
entries of the 50-entry launch catalog, in the Python API only, and
releases them to PyPI as the pre-release `1.0.0a1`, the first public
artifact of 1.0. It fetches no data (Phase 3 owns providers, credentials,
caching and the 18 live-data entries), generates no command, endpoint or
MCP tool (Phase 4), and launches no web app or production documentation
(Phase 5): its documentation is a preview that never displaces 0.2.x on
Read the Docs. It is one phase because a contract is proven only by the
models that use it: the catalog is the engine's acceptance test, and
`1.0.0a1` is the moment both become public.

The phase lands in 15 layers:

1. **ADR-0008 and core conventions** — writes
   `docs/adr/0008-numerical-conventions.md`, which the maintainer accepts
   in the step's pull request: decimal rates, the unit vocabulary and
   bounds, frequencies and compounding, day counts and calendars,
   tolerances, seeds, arrays and tabular data, pandas 3 semantics,
   non-finite results, root finding, canonical JSON numbers and the error
   taxonomy. It adds the runtime baseline (pydantic, NumPy, SciPy and
   pandas, at floors Pyodide can satisfy, with reviewed licence
   exceptions), implements the date-free conventions in
   `src/pyeconomics/core/`, moves `main` to version `1.0.0a1.dev1`, and adds
   the Pyodide import smoke test ADR-0002 asked Phase 2 for.
2. **Dates, day counts and calendars** — the six day-count conventions,
   coupon schedules with stubs and the end-of-month rule, and business-day
   adjustment over calendars from the `holidays` package, every one
   cross-checked against QuantLib, the phase's first test oracle.
3. **Model specification and registry** — `ModelSpec`, the `@model`
   decorator, the unit-typed field aliases, discovery through the
   `pyeconomics.models` entry-point group, aliases that warn under
   ADR-0003, `pyeconomics.registry.validate()`, the released-id ledger and
   the `model-purity` semgrep rule.
4. **Results, provenance and schemas** — `pyeconomics.run()` and
   `run_batch()`, the `Result` and its deterministic manifest, RFC 8785
   canonical JSON, JSON Schema 2020-12 export, conversions to pandas,
   Polars, Arrow and Parquet, `.card()`, plotting behind the `[plot]` extra,
   and `scripts/smoke.py`, which runs one model per domain in CI and in
   `release-smoke.yml`.
5. **Verification harness** — cited golden cases in `tests/golden/`, the
   harness that runs them with their tolerances, a meta-test that holds
   every declared invariant to a property test, schema-driven hypothesis
   strategies, coverage floors for `core/` and `models/`, and the model
   checklist in CONTRIBUTING and the pull request template.
6. **Launch catalog: foundations** — five entries, the first end-to-end
   proof of the contracts.
7. **Model cards and documentation preview** — the Sphinx site ADR-0007
   chose, with one generated page per model, Sybil-tested pages, an
   executed tutorial and a warnings-as-errors build in CI, published as the
   `main` preview on Read the Docs.
8. **Launch catalog: fixed income** — six entries.
9. **Launch catalog: derivatives and international** — six entries.
10. **Launch catalog: equity, corporate and accounting** — seven entries.
11. **Launch catalog: portfolio and performance** — five entries.
12. **Launch catalog: risk and econometrics** — three entries, and the
    `[econometrics]` extra, the first one a model's computation needs.
13. **1.0.0a1 readiness gate** — a TestPyPI rehearsal of the exact
    candidate and `docs/releases/1.0.0a1-readiness.md`, ending in the
    maintainer's GO or NO-GO.
14. **1.0.0a1 release** — `v1.0.0a1` on PyPI as a pre-release with
    attestations, the released-id ledger filled, release notes and a
    GitHub release.
15. **QA + `verify-phase02.sh`** — `scripts/verify-phase02.sh` (`--fast`,
    `--python`, `--security`, `--live`, `--all`, `--post`),
    `docs/phase02-qa-findings.md`, and matrix entry `02` in
    `.github/workflows/phase-verify.yml`, which binds the phase to CI.

The ship test for Phase 2 is straightforward: ADR-0008 is Accepted and the
runtime baseline passes the licence allowlist, the dependency audit and a
Pyodide import; all 32 entries in the launch-catalog table below are
registered and `registry.validate()` passes in CI; each has a model card,
at least three cited golden cases (fewer only with a recorded reason) and a
property test for every invariant it declares; every input and output
model exports JSON Schema that validates against the 2020-12 meta-schema,
and canonical-JSON round trips are lossless; mypy passes in strict mode,
and branch coverage is at least 95% on `core/` and 90% on `models/`; the docs
build passes with warnings as errors and Read the Docs serves the preview
from `main` while `stable` still serves 0.2.6; `pip install --pre
pyeconomics==1.0.0a1` in a clean venv runs a smoke script that executes one
model per domain (the econometrics model through its `[econometrics]`
extra, which the extra-less run names), plain `pip install pyeconomics`
still resolves 0.2.6, and both files carry attestations; and
`scripts/verify-phase02.sh --fast` exits 0 on Ubuntu CI with the
`phase-verify.yml` matrix entry `02` green.

**Pre-requisite:** Phase 1 is closed — V1–V12 green on 2026-10-08 (PR
#70), nine ADRs Accepted, `main` protected with 18 strict required checks,
the fail-closed gate and strict toolchain in prek and CI, and the 1.x
Trusted Publishing pipeline rehearsed with `v1.0.0.dev1` on TestPyPI. The
engine is written into Phase 1's `src/` skeleton, gated by its security
checks, typed by its mypy configuration, tested by its three-OS matrix and
released through its pipeline; ADR-0002, ADR-0003, ADR-0004, ADR-0007 and
ADR-0010 bind the decisions this phase encodes. The operator holds admin on
the GitHub repository, owner rights with 2FA on the PyPI project, the
`pypi` environment's review, and admin on the Read the Docs project; the
GitHub CLI is authenticated with the `repo` and `workflow` scopes.

**Dependency:** Phase 3 does not start until V1–V15 are green and
`1.0.0a1` is on PyPI. It fills the `bindings` field this phase reserves in
`ModelSpec` and the `data_sources` list it reserves in the manifest, so its
providers attach to models without a contract change, and its 18 live-data
entries pass the same golden, property and schema suites. Phase 4
generates every command, endpoint and MCP tool from the JSON Schemas and
canonical JSON fixed here, and builds request limits on the bounds and
cost classes every input declares. Phase 5 renders model pages from the
cards, and Phase 7's syllabus crosswalks key on the permanent ids this
phase releases.

**Design rationale (contracts first, the catalog as their proof).** The
order inside the phase is the design. Conventions come before the code that
encodes them: ADR-0008 settles decimals, units, day counts and float
formatting before any model can bake in a choice (Step 1), and dates get
their own step because six day-count conventions and their schedules are
where bond math goes wrong (Step 2). The contract follows in three
self-contained layers — specification and registry (Step 3), results and
schemas (Step 4), verification (Step 5) — each testable with toy models
before a real one exists. The first catalog step (Step 6) is the
contract's end-to-end proof, where upstream gaps surface while they are
still cheap, and the documentation preview (Step 7) follows it so the
first generated pages render real models. The remaining catalog steps
(Steps 8–12) apply a settled contract, domain by domain. The first PyPI
upload of 1.0 cannot be reused once published, only yanked, so it gets its
own readiness gate with a rehearsal of the exact candidate (Step 13)
before the release (Step 14), as 0.2.6 did in Phase 1.

**The model contract.** One catalog entry is one registered model: one
permanent id, one card, one `ModelSpec`, one pure `compute`, one typed input
model and one typed output model. Ids are `<domain>.<name>` in snake_case,
where the domain is one of the fifteen ROADMAP §4 7.2 lists and the id
never changes after release (ADR-0003); a later phase may add a third
segment for a sub-family. A family whose formulas take different inputs —
the time-value engine, the duration family — exposes them as a
discriminated union on a `calculation` field, with a matching output union,
so every model keeps one input schema and one output schema. Every numeric
field carries a unit from ADR-0008's vocabulary, finite bounds and a
description, and every array a maximum length. `compute` never does I/O:
it fetches nothing, prints nothing, plots nothing, reads no clock and draws
no unseeded random number, and reports non-fatal conditions through
`pyeconomics.core.warn()`, which the runner records in the result. A model
whose computation needs an extra's library names that extra in its spec
and imports the library inside `compute`, so the core install stays small
and the error for a missing extra names it.
`pyeconomics.run()` returns a `Result` holding inputs, outputs, warnings and
a manifest whose hashes cover canonical JSON. The shape, as Step 3 builds
it (an illustrative model, not a catalog entry):

```python
from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Rate,
    Reference,
    Years,
    model,
)


class ZeroCouponInputs(ModelInputs):
    face_value: Money = Field(gt=0, le=1e12, description="Face value")
    rate: Rate = Field(ge=-0.5, le=1.0, description="Annual yield")
    years: Years = Field(gt=0, le=100, description="Time to maturity")


class ZeroCouponOutputs(ModelOutputs):
    price: Money = Field(ge=0, le=1e14, description="Present value")


FISHER = Reference(
    key="fisher1930",
    citation="Fisher, I. (1930). The Theory of Interest. Macmillan.",
    url="https://www.econlib.org/library/YPDBooks/Fisher/fshToI.html",
    locator="Part I",
)


@model(
    id="fixed_income.zero_coupon_example",
    version=1,
    title="Zero-coupon bond price",
    summary="Price of a zero-coupon bond from its annual yield.",
    formula=(r"P = \frac{F}{(1 + y)^T}",),
    assumptions=("The yield is compounded once a year.",),
    limitations=("Ignores credit risk, taxes and settlement conventions.",),
    references=(FISHER,),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    invariants=(
        Invariant(
            id="price_falls_as_yield_rises",
            statement="For a positive maturity, the price falls as the yield rises.",
        ),
    ),
    examples=(
        Example(
            name="ten_years_at_five_percent",
            inputs={"face_value": 100, "rate": 0.05, "years": 10},
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def zero_coupon(inputs: ZeroCouponInputs) -> ZeroCouponOutputs:
    discount = (1 + inputs.rate) ** inputs.years
    return ZeroCouponOutputs(price=inputs.face_value / discount)
```

**Launch catalog, part one — the final list.** ROADMAP §4 2.6 leaves the
list to this roadmap. These 32 ids are final and become permanent when
Step 14 releases them; each entry's formulas are the ones its catalog step
names.

| #  | Model id                           | Entry (ROADMAP §4 2.6)                                                  | Step |
|----|------------------------------------|-------------------------------------------------------------------------|------|
| 1  | `foundations.time_value`           | TVM engine: PV/FV, annuities, the five-key solve, NPV, IRR, XNPV/XIRR, amortization | 6 |
| 2  | `foundations.returns`              | Return toolkit: holding-period, arithmetic, geometric, harmonic, annualized, log, real | 6 |
| 3  | `foundations.risk_statistics`      | Volatility, semideviation, skewness, kurtosis, maximum drawdown         | 6    |
| 4  | `foundations.hypothesis_tests`     | t, z, χ² and F tests with confidence intervals                          | 6    |
| 5  | `foundations.simulation`           | GBM Monte Carlo and the bootstrap                                       | 6    |
| 6  | `fixed_income.bond_pricing`        | Full and flat price, accrued interest, YTM, YTC, YTW                    | 8    |
| 7  | `fixed_income.money_market`        | Discount, money-market, bond-equivalent, effective and holding-period yields | 8 |
| 8  | `fixed_income.curve_bootstrap`     | Spot, par and forward rates and discount factors by bootstrapping       | 8    |
| 9  | `fixed_income.duration`            | Macaulay, modified, effective and key-rate duration; DV01               | 8    |
| 10 | `fixed_income.convexity`           | Convexity, effective convexity and the price-change approximation       | 8    |
| 11 | `fixed_income.credit_spread`       | Expected loss, spread and hazard rate, survival, spread return          | 8    |
| 12 | `derivatives.forwards`             | Cost-of-carry forwards and covered-interest-parity FX forwards          | 9    |
| 13 | `derivatives.interest_rate_swap`   | Swap valuation, par swap rate and annuity factor                        | 9    |
| 14 | `derivatives.black_scholes_merton` | BSM/Merton prices, Greeks and implied volatility                        | 9    |
| 15 | `derivatives.binomial_tree`        | CRR binomial, European and American, with put-call parity              | 9    |
| 16 | `derivatives.futures_fx_options`   | Black-76 and Garman-Kohlhagen, with Greeks and implied volatility       | 9    |
| 17 | `international.parity_conditions`  | Covered and uncovered interest parity, PPP, international Fisher, real exchange rates | 9 |
| 18 | `equity.dividend_discount`         | Gordon growth, two-stage, H-model, PVGO, implied required return        | 10   |
| 19 | `equity.free_cash_flow`            | FCFF and FCFE, and one- and two-stage DCF valuation                     | 10   |
| 20 | `corporate.cost_of_capital`        | CAPM, WACC, Hamada unlevering and relevering, country risk premium      | 10   |
| 21 | `corporate.capital_budgeting`      | NPV, IRR, MIRR, payback, discounted payback, PI, EAA                    | 10   |
| 22 | `corporate.leverage`               | DOL, DFL, DTL and breakeven                                             | 10   |
| 23 | `accounting.financial_ratios`      | Liquidity, activity, solvency and profitability ratios; 3- and 5-step DuPont | 10 |
| 24 | `accounting.scoring_models`        | Altman Z, Beneish M and Piotroski F                                     | 10   |
| 25 | `portfolio.mean_variance`          | Portfolio math, efficient frontier, minimum-variance and tangency portfolios | 11 |
| 26 | `portfolio.utility`                | Mean-variance utility, optimal risky share, Kelly fraction              | 11   |
| 27 | `performance.return_measurement`   | TWR, MWR and Modified Dietz                                             | 11   |
| 28 | `performance.risk_adjusted`        | Sharpe, Sortino, Treynor, Jensen, IR and tracking error, M², Calmar, capture ratios | 11 |
| 29 | `performance.brinson_attribution`  | Brinson-Hood-Beebower and Brinson-Fachler, with Carino linking          | 11   |
| 30 | `risk.value_at_risk`               | VaR and ES: parametric, Cornish-Fisher, historical, Monte Carlo, EWMA   | 12   |
| 31 | `risk.var_backtest`                | Kupiec, Christoffersen and the Basel traffic light                      | 12   |
| 32 | `econometrics.ols`                 | OLS with HC and HAC errors and the 0.2.x diagnostics, over statsmodels  | 12   |

**Version rule.** Step 1 moves `main` from `1.0.0.dev1` to `1.0.0a1.dev1`:
the version records the milestone `main` is building towards, and
`release.yml` already routes any `.devN` tag to TestPyPI. Step 13 tags
`main`'s HEAD `v1.0.0a1.devN` to rehearse the exact candidate on TestPyPI
(a failed rehearsal is a NO-GO; the fix lands on a `fix/` branch that
bumps `N`, and the gate runs again). Step 14 sets `1.0.0a1` and tags the
release. `CITATION.cff` carries the same version as `pyproject.toml` at
every commit.

**Dependency rule.** Every dependency Phase 2 adds — runtime, extra, test
or docs — is added with `uv add --no-config` (and `uv lock --no-config`,
`uv export --no-config`), so the maintainer's private index never reaches
the lock files. It must install on every CI cell (Python 3.12–3.14 on
Ubuntu, Windows and macOS, and 3.15 once issue #65 adds it) and pass
`pip-audit`. A runtime dependency, or any package an extra pulls in, must
also pass the ADR-0004 licence allowlist (the `licences` hook) or carry a
reviewed entry in `scripts/checks/licence_exceptions.toml` that the
maintainer approves in the pull request. A required runtime dependency must
be pure Python or have a Pyodide build (ADR-0002), and its lower bound may
not exceed the version Pyodide bundles. A package an extra pulls in also
joins the `test` dependency group, so the default `uv sync` environment —
which CI's `tests` and `types` jobs, Phase 1's V9.3 and CONTRIBUTING's
setup all use — tests and type-checks the code that needs it, while the
package job's clean venv keeps proving the extra-less install. GitHub's
dependency graph files uv.lock's dependency groups as runtime, so
`dependency-review` can flag a development-only package; such a package is
exempted by purl in `security.yml`, with a comment naming why, only after
the `licences` hook has shown it is outside the runtime closure.

**Cross-phase verification rule.** `phase-verify.yml` runs
`verify-phase01.sh --fast` and `--security` on every Phase 2 pull request,
and those checks were written against Phase 1's tree. When a Phase 2 change
legitimately invalidates one of them, the same pull request narrows the
check to the invariant it was protecting, never deletes it, and appends a
line to the "Post-merge addendum" at the end of
`docs/roadmap/phase01-roadmap.md`. The ones this roadmap foresees:

| Phase 1 check | What it pins today | Step that narrows it |
|---------------|--------------------|----------------------|
| Static check 18 | ADR-0008's index row reads "Reserved" | Step 1 (ADR-0008 becomes Accepted) |
| Static check 44 | `CITATION.cff` names `1.0.0.dev1` | Step 1 (the version moves) |
| V7.2 (`--python`) | The clean-venv wheel install uses `--no-index`, which cannot resolve runtime dependencies | Step 1 (the first runtime dependencies) |
| Static check 19 | No tracked `docs/conf.py`, because 0.2.x had one | Step 7 (the 1.0 docs site) |
| Static checks 21 and 35 | `requires-python = ">=3.12"`, and a Python set of exactly 3.12–3.14 in the matrix and classifiers | Steps 13–14, only if the ADR-0010 floor moves |

Issue #65 (Python 3.15) also breaks check 35 and V10.2's count of nine
matrix cells; its own pull request narrows them. Two Phase 1 checks need
no change if Phase 2 respects them: check 38 forbids workflows named
`tests.yml` or `docs.yml`, so the docs build is a job in `ci.yml`; and V8.5
and V10.4 test membership, so new required checks never break them.

**Contract-change rule.** Steps 6–12 build on the contract Steps 1–5 fix.
A catalog step that cannot be completed without a contract change makes
the change in-step (Triage rule: an upstream gap that blocks the step):
the smallest change that works, every registered model and golden case
kept green, the owning step's `<task>` block patched and the change added
to the carry-over checklist in this file's last section. A change to a
decision ADR-0008 records is a superseding ADR in the same pull request,
because an Accepted ADR is never edited (`docs/adr/README.md`).

**Citation rule.** A golden case cites an independent source with a
locator (page, table, section or equation): certified or official values
(NIST, the Federal Reserve, the US Treasury and 31 CFR Part 356, BIS, ISDA),
a peer-reviewed paper, a textbook value recomputed independently, or a
closed-form identity. CFA Program curriculum examples, questions and text
are never used, and no source's prose is copied: numbers and formulas only,
in our own words. A textbook value is either quoted at its published
precision, with a tolerance no tighter than its rounding, or recomputed
with a named independent method. Each catalog pull request lists every
new source in its body.

**Branch strategy.** Every step in this phase lands on its own short-lived
feature branch (`feature/phase02-step<M>-<slug>`), opens a pull request
against `main`, waits for the project's CI workflow to go green, and
squash-merges with a Conventional Commits subject line. Direct pushes to
`main` are blocked by branch protection. See the parent project's ROADMAP
"Branch management strategy" section for the canonical naming convention,
PR rules, and release tagging — this paragraph confirms those rules apply
unchanged within this phase. Per-step branches are listed on each step
header below as `**Branch:**` so reviewers can map commits 1:1 to the step
they implement.

**Branch-first execution rule.** The very first action of every step —
before reading any files, before running any tool, before drafting any
change — is to check out the branch named in that step's `**Branch:**`
line:

```sh
git checkout -b feature/phase02-step<M>-<slug>
```

This is non-negotiable. `main` is protected with `enforce_admins: true`, so
a commit on `main` cannot be pushed and must be rewound or rebased onto the
feature branch before the PR can open — an avoidable round-trip. If you
discover mid-step that you started on `main`, recover by running the same
`git checkout -b` command immediately (uncommitted changes carry over to the
new branch), then continue. AI coding agents executing a step from this
roadmap must treat the branch checkout as Step 0 of every step. Step 1
starts with this roadmap and the refreshed planning kit uncommitted in the
tree; they carry over to its branch and become its first two commits.

**Worktree rule.** One working tree, one step in flight — the lifecycle
below assumes the primary checkout. A second working tree is created only
with `git worktree add`, and only for the three cases the parent ROADMAP
"Worktree strategy" sanctions: a `hotfix/` branch interrupting this step
(cut from `origin/main` in its own worktree so this step's tree is
untouched); steps the Execution Order below explicitly draws in parallel
(each in its own worktree AND its own conversation); and worktree-isolated
subagents inside a step (throwaway trees that merge back into the step
branch locally and are removed before the PR opens). In those cases Stage 1
becomes `git fetch origin && git worktree add -b
feature/phase02-step<M>-<slug> <worktree-path> origin/main`, the worktree
is bootstrapped before any test or build (fresh dependency install and env
files — a worktree has none of the primary tree's untracked state, and it
must never borrow the primary tree's editable install), the Stage 4 merge
runs from the primary tree, and Stage 5 removes the worktree BEFORE pruning
the branch. Undeclared parallelism is a lifecycle violation, not a
shortcut. Worktree location for this project: git-ignored
`.worktrees/<branch-slug>/` inside the repository, matching the parent
ROADMAP; bootstrap with `uv sync --locked` inside it.

**Security-first execution rule.** Security is not a phase — it is a gate
on every commit of every step. Before each `git commit`, the step's work
must pass the local, fail-closed security gate: secret/PII scan clean, SAST
clean, dependency audit clean, and a diff review confirming no sensitive
data (PII, credentials, tokens) and no new insecure pattern (injection,
weak crypto, over-broad scope, secret in a client bundle or log line). This
gate is wired into the pre-commit hook (prek) and re-run in CI, so a
security issue introduced while implementing a step is caught during
development — before it reaches the branch, the PR, or `main`. See the
parent project's ROADMAP "Security & privacy strategy" → "Per-step security
gate" for the canonical checks and tooling; each step's XML `<task>`
carries a `<security>` block restating them for the agent, and each step's
Acceptance Criteria ends with a security check. AI coding agents executing
a step MUST treat the security gate as part of the step's definition of
done, exactly like its tests. Phase 2 handles no credentials and no
personal data; its exposure is the supply chain (the first runtime
dependencies), model inputs without bounds (the cost-exhaustion vector
Phase 4's hosted API inherits), models that could reach the network or the
filesystem, and the first irreversible upload of 1.0.

**Deploy-and-verify rule.** Merged is not deployed, and deployed is not
released. Every step header carries a `**Deploys:**` line naming the
surface and environment the step's merge reaches — or `nothing beyond
merge` — and when going live needs a release, a version-floor bump, a
migration, or a redeploy, the line says so and this step (or a named
follow-on step) owns that event. For a step whose Deploys line names a
surface, Stage 4 of the lifecycle does not end at the squash-merge: the
step's acceptance criteria carry a **Deployed & verified** bullet (the
surface's version/health endpoint reports this build, and the changed
behaviour is exercised in the target environment with real authentication
via the hands-off recipe the step names), and that bullet must be green
before the step is declared complete. In Phase 2 the surfaces are Read the
Docs (the `main` preview, Step 7), TestPyPI (the rehearsal, Step 13) and
PyPI (Step 14); their hands-off recipes are the Read the Docs API and page
text, and a clean-venv install of the exact version followed by
`scripts/smoke.py`. A step that introduces a required environment variable
or shared secret verifies at kickoff that it exists in every target
environment and proves shared values by an authenticated round-trip —
never by listing env names. See the parent ROADMAP "Release & deployment
strategy" for the surfaces table, promotion path, staged-rollout rule,
migrations, and rollback.

**Triage rule.** Findings surfaced while executing a step are classified
before they are acted on, per the parent ROADMAP "Defect handling &
triage": spec rot → edit this roadmap's affected `<task>` block now;
upstream gap → patch the earlier step's prompt and add it to the
carry-over checklist (the last list in this file's Not-in-scope section);
implementation bug → fix in-step only if it blocks this step's acceptance
criteria, otherwise an issue and its own branch in a fresh conversation;
model error (a published model returns a wrong number) → a High defect: a
`fix/` branch, the failing case added as a golden test, and an entry on
the errata page Step 7 creates; architectural question → an issue for a
future phase; process improvement → recorded where the next conversation
will read it; security finding → jumps the queue by severity. A step's PR
contains the step plus blocking fixes only, and lists the issues it
opened. When a merged PR auto-closes an issue, the environment check is
what earns the close — reopen or follow up if a gap remains.
`docs/phase02-qa-findings.md` is the rollup: every finding, its class, and
the guard added so the class cannot recur. Issues carry the defect-class
labels Phase 1 created (`spec-rot`, `upstream-gap`, `bug`, `model-error`,
`architecture`, `process`, `security`).

**Status rule.** Every step carries a `**Status:**` line directly under its
`## Step N — …` heading, before the Goal, and this file on `main` is the
ledger of what is done — never a chat transcript, never a later
conversation reconstructing history from `git log`. The line reads `Not
started` when this roadmap is written and is flipped by the step's OWN pull
request: at Stage 3, right after `gh pr create` returns the PR number, the
agent sets it to `Complete — PR #<n> (<YYYY-MM-DD>)`, appends ` ✅` to the
step's heading (`## Step 3 — Model Specification and Registry ✅`) so the
completion shows in the rendered preview, the outline, and the table of
contents, sets the step's Summary Table Status cell to `Complete — PR
#<n>`, commits that edit on the step branch, and pushes. The PR therefore
carries its own completion mark, and the roadmap on `main` says a step is
complete exactly when that step's PR merges — never before. This file's
phase-level `**Status:**` line (under the title) and the parent project
roadmap are marked the same way, in the same commit: Step 1's PR flips
both from `Not started` to `In progress` (the parent's `### Phase 2` line
reads `In progress — phase02-roadmap.md`), and the final step's PR flips
both to `Complete — …` (the parent's with its row in the "Phase Complexity
Summary" table and the header `> **Status:**` line) and appends ` ✅` to
this file's `# ` title and to the parent's `### Phase 2` heading, so the
project roadmap shows a finished phase the way this file shows a finished
step. There is no separate "update the roadmaps" chore: a step whose PR
merged without its Status line is a lifecycle violation, and the next
step's Stage 1 (and `/roadmap-step`) refuses to start until the previous
step reads `Complete`. If a post-merge check fails — a Deployed & verified
bullet, an alarm that never fired — the step is NOT complete despite the
merged line; say so, and the `hotfix/` PR that completes it appends its own
number to the line. `grep -n '^\*\*Status:\*\*'` on this file is the
phase's progress report, and the ✅ headings are the same report at a
glance.

**Step lifecycle.** Every step in this phase follows the exact same
six-stage lifecycle, in order, with no exceptions. Each stage is a hard
checkpoint — if a stage is skipped, branch protection or the next step's
Stage 1 will fail loudly, and that is the safety net. AI coding agents MUST
execute all six stages before declaring a step complete.

1. **Create the branch.** Before any Read / Edit / Bash, run
   `git checkout -b feature/phase02-step<M>-<slug>` from a clean,
   up-to-date `main`. The exact branch name comes from this step's
   `**Branch:**` line. When the Worktree rule applies, the equivalent is
   `git fetch origin && git worktree add -b <branch> <worktree-path>
   origin/main`, followed by the worktree's bootstrap.

2. **Work on the branch, passing the security gate before every commit.**
   All commits land here, each signed off (`git commit -s`). Never push to
   `main` directly — branch protection (`enforce_admins: true`) rejects it.
   Before each `git commit`, run the local security gate (secret/PII scan,
   SAST, dependency audit, sensitive-data diff review — see the step's
   `<security>` block and the parent ROADMAP "Per-step security gate"). It
   is fail-closed: a finding blocks the commit, so a security issue in this
   step's work is caught here, before the PR and before `main`.

3. **Open the PR, then mark the step.** `gh pr create --base main --head
   <branch>` with a Conventional Commits title and a body that references
   this roadmap step and its acceptance criteria. One PR per step; never
   bundle two steps into one PR. Then, with the PR number in hand, set this
   step's `**Status:**` line (directly under its heading) to `Complete — PR
   #<n> (<YYYY-MM-DD>)`, append ` ✅` to the step's `## Step` heading, set
   its Summary Table Status cell to `Complete — PR #<n>`, commit that edit
   on the step branch (`docs: mark Phase 2 Step M complete`), and push —
   the PR now carries its own completion mark, so the roadmap on `main`
   will say the step is complete exactly when the PR merges (Status rule).
   On the phase's first step, the same commit sets this roadmap's
   phase-level `**Status:**` (under its title) and the parent project
   roadmap's Phase 2 `**Status:**` to `In progress`; on the final step,
   both to `Complete`, with ` ✅` appended to this roadmap's `# ` title and
   to the parent's `### Phase 2` heading.

4. **Wait for green checks, then squash-merge.** Every required status
   check must report success: the 18 Phase 1 made required (lint, types,
   the test matrix's aggregate `test` gate, package, lockfile, pr-title,
   dco, the nine security checks, and both `phase-verify` jobs for `01`),
   plus both `phase-verify` jobs for `02` once Step 15 adds them. The
   `pyodide` job (Step 1) and the `docs` job (Step 7) run inside the `test`
   aggregate. If the PR goes BEHIND main while waiting, refresh with `gh pr
   update-branch --rebase` — never merge `main` into the branch;
   `required_linear_history: true` enforces rebase. Once every check is
   green:

   ```sh
   gh pr merge <PR_NUMBER> --squash --delete-branch
   ```

   If this step's `**Deploys:**` line names a surface, the merge is not the
   finish line: run the Deployed & verified check from the acceptance
   criteria against the target environment now (see the Deploy-and-verify
   rule) before declaring the step complete.

5. **Retire the branch (remote + local).** The `--delete-branch` flag plus
   the repo's `delete_branch_on_merge: true` setting retire the remote
   automatically. Sync local state and prune the merged branch plus any
   other `[gone]` labels left over from prior PRs:

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
   conversation.** Before you declare anything, walk the findings this step
   surfaced and send each to its destination per the Triage rule above — a
   note that a later step needs is edited into that step's `<task>` block
   now; a wrong claim in this step's spec is fixed in this roadmap now; an
   implementation bug is fixed in-step or exists as an issue with a number;
   a judgement call you made in the diff is explained in the PR body; a
   process lesson is written where the next conversation reads it. A
   finding you can only *describe* has not been disposed of, and an
   undisposed finding is an unmet acceptance criterion. Only once the PR is
   merged — and `main` therefore carries this step's `Complete` Status line
   — every acceptance criterion is affirmatively met, and every finding has
   a destination, say so plainly: end your final response with an
   explicit, unhedged completion line — verbatim shape "Step M is complete.
   You can now move on to Step M+1." — so the operator has a clean stopping
   point at which to close this conversation. That line is the LAST line of
   the response. Nothing follows it: no "Follow-ups (non-blocking)", no
   "Notes", no "Next", no "worth a glance", no suggested improvements. If
   you want to show your work, a short ledger may PRECEDE the line, one
   entry per finding naming its destination (an issue number, a file you
   edited, the PR body) — never an open item. If any acceptance criterion
   is NOT met, or any finding has no destination yet, do the opposite —
   state plainly that the step is NOT complete, name what is outstanding,
   and do not emit the completion line. "Done" means done, not "done, but
   here is what you still have to do". Then, for phase-boundary hygiene,
   the operator closes this Claude Code / Cursor / Codex session and opens
   a fresh one before starting Step M+1; the new conversation begins again
   at Stage 1 of this lifecycle, with the next step's `**Branch:**` line
   driving the `git checkout -b` command. No work straddles two steps.

---

## Current State (as of Phase 1)

### Package and contract surface

- `src/pyeconomics/` holds only `__init__.py`, which reads `__version__`
  from the installed distribution's metadata, and `py.typed`. No `core/`,
  `models/`, registry, result type or convention exists, and nothing is
  importable beyond the version. `pyproject.toml` (PEP 621, `uv_build`)
  declares version `1.0.0.dev1` (published to TestPyPI by Phase 1 Step 10),
  `requires-python = ">=3.12"`, `license = "Apache-2.0"`, the Pre-Alpha
  classifier and classifiers for Python 3.12–3.14, `dependencies = []`, and
  the ADR-0002 extras `server`, `mcp`, `ai`, `econometrics`, `plot` and
  `all` as empty lists. No entry-point group exists.
- `pydantic` sits in the `dev` dependency group only so mypy's
  `pydantic.mypy` plugin can load, with a comment saying Phase 2 makes it a
  runtime dependency. The `test` group holds hypothesis, pytest,
  pytest-benchmark, pytest-cov, pytest-socket and syrupy; the `docs` group
  is empty.
- `scripts/checks/dist_contents.py` is the artifact allowlist: the wheel
  may hold only `pyeconomics/**/*.py`, `pyeconomics/py.typed`, and in its
  dist-info `METADATA`, `WHEEL`, `RECORD` and the licence files; the sdist
  only `src/pyeconomics/**` of the same kinds plus the root metadata
  files. The first entry point (Step 6) puts `entry_points.txt` in the
  dist-info, which model discovery reads, so Step 6 admits it; otherwise
  Phase 2 keeps every package resource a Python module (the released-id
  ledger included), and a step that needs package data extends the
  allowlist in the same change.
- `docs/adr/README.md` lists ADR-0008 as "Reserved for Phase 2" for the
  numerical conventions. ADR-0002 (extras, pure-Python core, the Pyodide
  smoke test), ADR-0003 (permanent ids, the `FutureWarning` deprecation
  class, milestone tags), ADR-0004 (the runtime licence allowlist and its
  exceptions file), ADR-0007 (Sphinx, MyST-NB, sphinx-autoapi and Sybil on
  Read the Docs; Phase 2 chooses the preview mechanism) and ADR-0010 (the
  Python floor follows NumPy and SciPy) each name a check Phase 2 builds.

### Dependency and licence surface

- Facts this roadmap relies on, read from PyPI and Pyodide on 2026-10-08.
  The `licences` hook reads each package's installed metadata and is the
  authority at step time; this table predicts what it will report.

| Package | Latest | Licence metadata | Predicted `licences` result | Pyodide 314.0.7 bundles |
|---------|--------|------------------|-----------------------------|-------------------------|
| numpy | 2.5.3 | `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | Fails (0BSD, Zlib and CC0-1.0 are outside the allowlist): reviewed exception | 2.4.6 |
| scipy | 1.18.1 | Licence text in `License`; classifier `BSD License` | Fails (ambiguous classifier): reviewed exception | 1.18.0 |
| pandas | 3.0.6 | Licence text in `License`; classifier `BSD License` | Fails (ambiguous classifier): reviewed exception | 3.0.2 |
| python-dateutil | 2.9.0.post0 | `Dual License`; Apache and BSD classifiers | Fails (ambiguous): reviewed exception | 2.9.0.post0 |
| pydantic, pydantic-core | 2.14.0, 2.50.0 | `MIT` | Passes | 2.12.5, 2.41.5 |
| holidays | 0.106 | `MIT` (pure Python) | Passes | not bundled; installs from PyPI |
| plotly, narwhals | 7.1.0, 2.26.0 | `MIT` (pure Python) | Passes | narwhals 2.18.1; plotly from PyPI |
| statsmodels | 0.15.0 | `BSD-3-Clause` | Passes; its closure (patsy `2-clause BSD`, formulaic) needs review | 0.14.6 |
| QuantLib (test only) | 1.43 | `BSD-3-Clause`; abi3 wheels for every CI platform | Outside the allowlist's scope (a dependency group) | — |

- Pyodide 314.0.7 (Python 3.14.2) is the current Pyodide release. Its
  bundled versions cap the lower bounds a required runtime dependency may
  declare (Dependency rule), while `uv.lock` pins the newest releases for
  CI.
- Excluded by name, whatever their metadata says: FinancePy, rateslib,
  getfactormodels, the DBnomics client and `full_fred` (ADR-0004,
  `scripts/checks/licences.py`). `scripts/checks/licence_exceptions.toml`
  exists and is empty. `security.yml`'s `dependency-review` allows
  ADR-0004's seven licences and exempts, by purl, trufflehog's action,
  hypothesis, pathspec and typing-extensions.

### Toolchain and test surface

- ruff selects `ALL` (with `CPY001`: every Python file opens with its path,
  the copyright line and the SPDX identifier) and also formats Python code
  blocks in Markdown files, roadmaps included. mypy runs strict with the
  pydantic plugin over `src` and `tests`; pyright is editor-only and ty is
  informational.
- pytest runs with `--strict-markers --strict-config --doctest-modules
  --import-mode=importlib --disable-socket --benchmark-disable`, testpaths
  `tests` and `src`, `xfail_strict`, and `filterwarnings = ["error"]`, so a
  test that expects a warning must catch it. `tests/conftest.py` registers
  the hypothesis profiles `ci` (derandomized, no deadline, prints the blob)
  and `dev`. Coverage measures branches through `source_pkgs =
  ["pyeconomics"]` with `fail_under = 95`. `tests/` holds `checks/`,
  `repo/test_phase01.py`, `unit/test_network_blocked.py` and
  `unit/test_version.py`, and the byte-exact `tests/fixtures/legacy/`.
- On the maintainer's Windows machine: run tests with `uv run pytest`,
  never `python -m pytest` (a stale `pyeconomics/` directory at the repo
  root shadows the package); Python's `write_text` writes CRLF, so write
  bytes or use an editor tool; run every lock-changing uv command with
  `--no-config`; and VS Code's language servers hold `.venv` open, so a
  rebuild needs their interpreters pointed elsewhere first.

### CI/CD and publishing surface

- `ci.yml`: `lint`, `types`, `ty` (informational), `tests` (Ubuntu, Windows
  and macOS × Python 3.12, 3.13 and 3.14; `uv sync --locked`, then `uv run
  --locked pytest --cov` and the `licences` hook, which syncs every
  extra), `package` (`uv build`, `twine check --strict`, the artifact
  allowlist and a clean-venv import of the wheel from outside the
  checkout), `lockfile`, `pr-title`, `dco` and the aggregate `test`. The
  `tests` and `types` jobs sync the default groups and no extras, which is
  why an extra's packages also join the `test` group (Dependency rule).
- `release.yml`: a `v*` tag on `main` whose name equals `v` plus `uv version
  --short` is built once, checked against the artifact allowlist, and
  published with PEP 740 attestations — a `.devN` version to TestPyPI
  through the `testpypi` environment, anything else to PyPI through the
  `pypi` environment, which waits for the maintainer's approval. It then
  calls `release-smoke.yml`, which installs the exact version in a fresh
  venv outside any checkout, installs its dependencies from PyPI only, and
  checks the reported version. The 1.x path to PyPI has never run.
- `main` requires 18 checks, strict: lint, types, test, package,
  lockfile, pr-title, dco, gate-secrets, gate-sast, gate-deps,
  gate-licences, trufflehog, zizmor, dependency-review, codeql (python),
  codeql (actions), `phase-verify-fast (01)` and `phase-verify-security
  (01)`. Workflows are SHA-pinned (enforced by repository policy), start
  every job with harden-runner, set `permissions: {}` at the top and run on
  GitHub-hosted runners, as a public repository's do; `ubuntu-latest`
  moves to Ubuntu 26 on 2026-10-19.
- Open items owned elsewhere: issue #65 adds Python 3.15 (final due
  2026-10-09) to the matrix and classifiers, after which every compiled
  dependency needs `cp315` or abi3 wheels; Dependabot PR #61 (`uv_build`
  bump) needs `@dependabot rebase`; issues #52 (CVE id), #62 (Scorecard
  dispositions) and #68 (GitHub Sponsors, ROADMAP 8.1).

### Security and sensitive-data surface

- Phase 2 handles no credentials and no personal data: no provider, no
  key, no network call, no service. Its exposures are the supply chain (the
  first runtime dependencies and extras), unbounded model inputs (the
  cost-exhaustion vector Phase 4's hosted API would inherit), a model that
  reaches the network, the filesystem or the clock, unsafe
  deserialization in result or fixture handling, notebooks that execute
  during the docs build, and the integrity of the first public 1.0 upload.
- The prek gate (`.pre-commit-config.yaml`) runs gitleaks (staged changes;
  CI stages the whole tree), bandit, semgrep with the project rules
  `credential-logging`, `dynamic-code`, `unsafe-deserialization` and
  `unsafe-yaml` (and the `semgrep-test` hook that tests them one at a
  time), `pip-audit --locked`, `lock-index`, `licences`, zizmor and
  `no-commit-to-branch`, beside ruff, mypy, `uv-lock` and `pylock-fresh`.
  `security.yml` re-runs them as required checks, with trufflehog, zizmor
  and `dependency-review`; CodeQL and Scorecard run weekly.
- Patterns every step mirrors: refer to a fake credential by its location,
  never quote it (the gate blocks literal fake keys, docs included); treat
  a workflow change as a security-relevant diff (SHA-pinned actions,
  least-privilege `permissions:`, `persist-credentials: false`, no
  `pull_request_target`, zizmor clean); and keep the private uv index out
  of the lock files with `--no-config`.

### Documentation surface

- `main` has no Sphinx site. `docs/` holds `adr/`, `roadmap/`,
  `releases/0.2.6-readiness.md` and `phase01-qa-findings.md`, and
  `.gitignore` already ignores `docs/_build/`. Read the Docs project
  `pyeconomics` serves 0.2.x: default branch `legacy/0.2.x`, default
  version `stable` (tag `v0.2.6`), and `latest` built from `legacy/0.2.x`,
  whose own `.readthedocs.yml` and Sphinx sources it uses. `stable` follows
  the newest non-pre-release tag, so `v1.0.0a1` leaves it on 0.2.6 until
  Phase 5's cutover.
- This roadmap settles ADR-0007's open choice of preview mechanism: Read
  the Docs builds the 1.0 site from `main` as the active, non-default
  version `main` (`/en/main/`), configured by a new `.readthedocs.yaml` on
  `main`. sphinx-gallery and Read the Docs pull-request builds wait for
  Phase 5.
- `README.md` is the PyPI long description: CI, PyPI, licence and Scorecard
  badges, a status banner (1.0 is in development; `pip install --pre`), the
  0.2.x notice, the disambiguation note and the CFA® marks notice.
  `CHANGELOG.md` follows Keep a Changelog, `CITATION.cff` names 1.0.0.dev1,
  CONTRIBUTING carries ROADMAP §5's model definition of done, and the pull
  request template has Roadmap step, Summary, Test plan, Screenshots,
  Breaking changes, Rollback plan, Licence check, Sensitive-data checklist
  and Security gate bypass sections.

### Operations and observability surface

- No runtime service exists. The one live surface is package publishing:
  its health signal is `release-smoke.yml` (a fresh-venv install of the
  exact version and a version check), and its alarm is GitHub's
  failed-workflow email to the maintainer, seen to fire in Phase 1 (V12.5,
  run 37866605106). Its rollback is a PyPI yank followed by a fixed release
  through the same pipeline; for a pre-release that is `1.0.0a1.post1`,
  which `release.yml`'s version pattern already accepts.
- Phase 2 changes the signal (Step 4 makes the smoke run one model per
  domain, Step 12 adds the extras path), so Step 15 proves the alarm again
  with a synthetic failure. The documentation preview (Step 7) is a
  non-production surface: the CI `docs` job keeps a broken build off
  `main`, `--live` reads the Read the Docs build status, and production
  documentation monitoring belongs to Phase 5.

### Verification surfaces

- `scripts/verify-phase01.sh` (50 static checks, V1–V12, modes `--fast`,
  `--python`, `--security`, `--live`, `--all` and `--post`) is the template
  for `verify-phase02.sh`: the same `record` / `check` / `vcheck` /
  `vstatic` helpers, the PASS/FAIL line format and the per-mode summary.
  `tests/repo/test_phase01.py` is the template for its pytest twin.
- `.github/workflows/phase-verify.yml` runs the matrix `phase: ["01"]` —
  `verify-phase<NN>.sh --fast` and `--security` — on every pull request and
  push to `main`, and both jobs are required. Phase 2 appends `"02"`.
- Phase 1 checks this phase touches are tabulated in the Cross-phase
  verification rule: checks 18 and 44 and V7.2 (Step 1), check 19 (Step 7),
  and checks 21 and 35 (Steps 13–14, if the floor moves). Check 38 and
  V8.5/V10.4 stay as they are. Check 35 also pins exactly Python 3.12–3.14
  and V10.2 counts exactly nine `tests (…)` matrix cells, so the pull
  request for issue #65 (Python 3.15) updates both.

---

## Execution Order

```
Step 1  (ADR-0008 + conventions)      docs/adr/0008, core units, rates,
                                      compounding, tolerance, seeds,
                                      runtime baseline, Pyodide smoke
                                      → implement
  ↓
Step 2  (dates + calendars)           six day counts, schedules,
                                      business-day calendars; QuantLib
                                      oracle → implement
  ↓
Step 3  (spec + registry)             ModelSpec, @model, unit-typed
                                      fields, entry points, aliases,
                                      validate(), model-purity rule
                                      → implement
  ↓
Step 4  (results + schemas)           run(), Result, manifest, RFC 8785
                                      JSON, JSON Schema, cards, [plot],
                                      model smoke → implement
  ↓
Step 5  (verification harness)        tests/golden/, invariant coverage,
                                      strategies, coverage floors
                                      → implement
  ↓
Step 6  (catalog: foundations)        5 entries, the first end-to-end
                                      proof → implement
  ↓
Step 7  (cards + docs preview)        Sphinx site, generated model pages,
                                      Sybil, Read the Docs main preview
                                      → implement
  ↓
Step 8  (catalog: fixed income)       6 entries → implement
  ↓
Step 9  (catalog: derivatives +       6 entries → implement
         international)
  ↓
Step 10 (catalog: equity, corporate,  7 entries → implement
         accounting)
  ↓
Step 11 (catalog: portfolio +         5 entries → implement
         performance)
  ↓
Step 12 (catalog: risk +              3 entries, the [econometrics]
         econometrics)                extra → implement
  ↓
Step 13 (1.0.0a1 readiness gate)      v1.0.0a1.devN on TestPyPI,
                                      docs/releases/1.0.0a1-readiness.md,
                                      GO / NO-GO → implement
  ↓
Step 14 (1.0.0a1 release)             v1.0.0a1 on PyPI, GitHub release,
                                      released-id ledger → operate
  ↓
Step 15 (QA + verify-phase02.sh)      scripts/verify-phase02.sh
                                      + docs/phase02-qa-findings.md
                                      + phase-verify.yml matrix entry
                                      → create

--- post-implementation ---

V1   ADR-0008 Accepted; runtime baseline passes licences, audit and a
     Pyodide import; core conventions tested.
V2   Six day counts, schedules and calendars agree with QuantLib.
V3   validate() passes and rejects every incomplete toy spec; the
     model-purity rule holds.
V4   Canonical JSON passes RFC 8785 vectors; every schema is valid
     2020-12; the smoke runs one model per domain.
V5   Every model's golden cases pass; every invariant has a property
     test; coverage floors hold.
V6   Five foundations entries meet the definition of done.
V7   Docs build with warnings as errors; one page per model; Read the
     Docs serves the main preview and stable still serves 0.2.6.
V8   Six fixed-income entries meet the definition of done.
V9   Six derivatives and international entries meet it.
V10  Seven equity, corporate and accounting entries meet it.
V11  Five portfolio and performance entries meet it.
V12  Three risk and econometrics entries meet it; [econometrics]
     installs and runs, and its absence is reported.
V13  Readiness evidenced, with the maintainer's GO; the rehearsal is on
     TestPyPI with attestations.
V14  1.0.0a1 on PyPI with attestations runs one model per domain;
     plain pip install still resolves 0.2.6.
V15  verify-phase02.sh --fast and --security exit 0 in phase-verify.yml;
     the release-smoke alarm fired again; verify-phase01.sh stays green.
```

Steps are sequential by dependency. Step 1's ADR-0008 fixes the units,
bounds, frequencies and float formatting that every later layer encodes,
and its runtime baseline is what Step 2's dates and Step 3's field types
import. Step 2's day counts are the date layer Step 6's XIRR and every
Step 8 bond calculation use. Step 3's `ModelSpec` and registry are what
Step 4's `run()`, results and schemas operate on, and Step 5's harness runs
Step 4's results against cited fixtures and Step 3's declared invariants.
Step 6 is the first consumer of all five, so it follows them; Step 7
renders Step 4's cards for Step 6's real models. Steps 8–12 reuse Step 6's
numerical helpers (root finding, discounting, return statistics) and each
other's in order: fixed income's discount factors feed swap valuation in
Step 9; Step 6's time-value and statistics entries feed capital budgeting
(Step 10), money-weighted returns and the Calmar ratio (Step 11), and
Monte Carlo and EWMA VaR (Step 12). Step 13 rehearses the tree Steps 1–12
leave on
`main`, Step 14 releases it only after the maintainer's GO, and Step 15 is
sequential after every prior step. Catalog domains do not share files
cleanly (`pyproject.toml`'s entry points, shared numerics, this roadmap's
Summary Table) and a contract fix found in one must reach the next, so no
steps are drawn in parallel; the Worktree rule's declared-parallelism case
does not arise in this phase.

---

## Step 1 — ADR-0008 Numerical Conventions and Core Types ✅

**Status:** Complete — PR #71 (2026-10-09)

> **Goal:** Fix the numerical conventions every later layer encodes, and lay
> the runtime foundation beneath them. Land this roadmap and the refreshed
> planning kit; write `docs/adr/0008-numerical-conventions.md` from the
> fourteen recommended defaults in this step's task and have the maintainer
> accept or amend it in the pull request; add pydantic, NumPy, SciPy and
> pandas as the runtime baseline, at floors Pyodide 314.0.7 can satisfy,
> with reviewed licence exceptions; implement the date-free conventions in
> `src/pyeconomics/core/` (`units.py`, `rates.py`, `compounding.py`,
> `tolerance.py`, `random.py`, `numerics.py`, `errors.py`, `warnings.py`)
> with unit, property and doctest coverage, including
> `PyeconomicsDeprecationWarning`, the `FutureWarning` subclass ADR-0003
> asks Phase 2 for; move `main` to `1.0.0a1.dev1` with `CITATION.cff` in
> step; narrow the three Phase 1 checks this step breaks (static checks 18
> and 44, and V7.2); and add `scripts/smoke.py`
> and a `pyodide` CI job that imports the wheel in Pyodide, the smoke test
> ADR-0002 asks for. Steps 2–5 build the rest of the contract on these
> conventions. Parent: ROADMAP §4 2.1; ADR-0002, ADR-0003, ADR-0004 and
> ADR-0010.

**Branch:** `feature/phase02-step1-conventions`

**Deploys:** nothing beyond merge — the version moves to `1.0.0a1.dev1`,
but no tag is pushed and nothing is published until Step 13.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Astra — Codex · Intelligence Extra High |
| Platform     | Claude Code                                   |
| Effort       | Extra High                                    |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Planning is PRIMARY — ADR-0008 settles the
conventions every model, schema and surface will encode — and knowledge
SECONDARY, because each convention (day counts, compounding, float
formatting) must follow a cited definition exactly. The step is High
complexity on every axis: many interacting decisions, trade-offs to judge,
scope across the whole platform, and no precedent in the repository. High
complexity requires S in planning; Opus 5.5 is S in planning and
knowledge, ties Fable 5.1 on both and wins the cost tie-break (AA
Intelligence Index 57.6). Claude Code on the claude.ai Max plan pays for
it, $0 marginal while the weekly pool has headroom; the pool reads `tight`
until Tue 2026-10-13 20:00 EDT, and High-complexity work keeps its place on
it. Claude Code opens on Opus 5.5 at its Medium default; Extra High is the
recommended raise — High for the complexity, one rung more for planning
with cross-cutting scope — and not Max, because this roadmap already gives
every decision a recommended default for the maintainer to accept or
amend. Thinking stays On. The backup is GPT-6 Astra on Codex under ChatGPT
Pro 5x, the only OpenAI model rated S in planning, at Intelligence Extra
High. New conversation per phase-boundary hygiene.

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
       feature/phase02-step1-conventions`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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

    THIS STEP ALSO:
    - The runtime baseline is this step's supply-chain
      surface: each new package passes pip-audit, the
      `licences` hook (or a reviewed exception the
      maintainer approves in the PR) and dependency-review;
      lock files are made with `--no-config`, and the
      `lock-index` hook proves they name only PyPI.
    - The `pyodide` job downloads pyodide-build and its
      cross-build environment at run time: pin both to exact
      versions, grant `contents: read` only, start with
      harden-runner, and keep zizmor clean.
    - The core modules do no I/O: no network, file, clock or
      environment access (pytest-socket proves the network
      part; review proves the rest).
    - The ADR, tests and fixtures quote no credential, real
      or fake.
  </security>

  <context>
    pyeconomics. Phase 2. Step 1: ADR-0008 numerical
    conventions and core types.

    Current state (as of Phase 1; no Phase 2 step has run):

    - This roadmap (docs/roadmap/phase02-roadmap.md) is
      untracked, and planning/ holds roadmodel's refreshed
      kit (model-selector.txt and model-tier-cost-scale.md
      modified by /roadmap-phase 2 on 2026-10-09). Both carry
      over to the step branch.
    - src/pyeconomics/ holds __init__.py and py.typed only.
      pyproject.toml has version 1.0.0.dev1, no runtime
      dependency, and pydantic in the dev group for mypy's
      plugin. CITATION.cff names 1.0.0.dev1, and
      verify-phase01.sh static check 44 requires exactly
      that; static check 18 requires the 0008 index row to
      read "Reserved"; V7.2 installs the wheel with
      `--no-index`.
    - ADR-0008 is reserved in docs/adr/README.md. The format
      is docs/adr/template.md, and the nine accepted ADRs
      show the house style: context with sourced, dated
      facts; decision drivers; considered options; the
      decision; consequences; a Confirmation table.
    - scripts/checks/licences.py evaluates SPDX expressions
      and maps only unambiguous classifiers;
      licence_exceptions.toml is empty. This roadmap's
      Current State predicts which packages need an
      exception.
    - ci.yml's package job installs the wheel in a clean
      venv outside the checkout and checks the version; no
      Pyodide check exists.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §3, §4 2.1–2.4 and §5 "Model
      quality & governance" (the conventions in scope).
    - docs/adr/README.md, docs/adr/template.md, and
      ADR-0002, ADR-0003, ADR-0004 and ADR-0010 (the
      decisions ADR-0008 must agree with).
    - pyproject.toml and CITATION.cff.
    - scripts/checks/licences.py,
      scripts/checks/licence_exceptions.toml and
      .github/workflows/security.yml (dependency-review's
      allow list and purl exemptions).
    - .github/workflows/ci.yml (the package job and the
      `test` aggregate's needs).
    - scripts/verify-phase01.sh (static checks 18 and 44,
      and V7.2) and the end of
      docs/roadmap/phase01-roadmap.md.
    - This roadmap's Overview (the Version, Dependency and
      Cross-phase verification rules) and Current State.
  </context>

  <goal>
    ADR-0008 is merged as Accepted with the fourteen
    decisions below; the runtime baseline is locked,
    audited and licence-clean with reviewed exceptions;
    src/pyeconomics/core/ implements and tests the
    date-free conventions and the error and warning
    taxonomy; main reads 1.0.0a1.dev1 in pyproject.toml and
    CITATION.cff; the three Phase 1 checks this step breaks
    are narrowed; and CI runs scripts/smoke.py against the
    wheel in a clean venv and in Pyodide.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Land the roadmap first. After Stage 1, commit
      planning/ as /roadmap-step §5 instructs
      (`chore(planning): refresh the roadmodel kit to
      <version>`), then this file (`docs(roadmap): add the
      Phase 2 roadmap`), each signed off and gated, before
      any other change.
    </requirement>

    <requirement>
      Kickoff, one batched question to the maintainer: the
      fourteen ADR-0008 decisions (accept or amend each)
      and the licence exceptions the `licences` hook will
      need. Record the answers in the PR body; never fill
      in the ADR's acceptance alone.
    </requirement>

    <requirement>
      Write docs/adr/0008-numerical-conventions.md from
      docs/adr/template.md, with facts sourced and dated,
      and these decisions as its recommended defaults:
      1. Decimals: rates, returns, yields, spreads,
         volatilities and probabilities are decimals in
         every API (0.05 is 5%). Percent and basis points
         exist only in display formatting and at the data
         boundary, where core/rates.py's
         percent_to_decimal and decimal_to_percent are the
         only converters.
      2. Units: every numeric input and output field
         declares one unit kind from a closed vocabulary in
         core/units.py — rate, return, money, years, days,
         periods, count, ratio, probability, volatility,
         correlation, index_level and date — exported to
         JSON Schema as `x-unit`. A money field takes its
         currency (ISO 4217) from an input field, or is
         currency-agnostic when the formula is linear in
         money and all its money fields share one currency.
         Adding a unit kind is a reviewed code change, not
         an ADR change.
      3. Bounds: every numeric field has finite lower and
         upper bounds, every array and string a maximum
         length. The ADR tabulates default bounds per unit
         kind (for example rate −0.99 to 10, volatility
         above 0 to 10, years 0 to 200, correlation −1 to
         1, dates 1900-01-01 to 2200-12-31) that a model may
         narrow, and widen only with a recorded reason. Bounds protect correctness and are
         what Phase 4's request limits build on.
      4. Frequency and compounding: a Frequency enum
         (annual, semiannual, quarterly, monthly, weekly,
         daily) with periods per year; a Compounding enum
         (simple, periodic, continuous); conversions among
         nominal, effective annual and continuous rates and
         discount factors in core/compounding.py.
         Annualizing a return series takes an explicit
         periods_per_year, never a guess; time-indexed data
         use pandas 3's ME, QE, YE, W and B aliases.
      5. Day counts and calendars, built in Step 2:
         DayCount members THIRTY_360_US, THIRTY_E_360,
         ACT_360, ACT_365_FIXED, ACT_ACT_ISDA and
         ACT_ACT_ICMA, each defined by its source (ISDA 2006
         Definitions §4.16 for 30E/360, ACT/360, ACT/365F and
         ACT/ACT ISDA; ICMA Rule 251 for ACT/ACT ICMA; the US
         30/360 end-of-month rules as QuantLib's
         Thirty360.USA applies them), cited by section and
         never quoted; BusinessDayConvention members
         UNADJUSTED, FOLLOWING, MODIFIED_FOLLOWING,
         PRECEDING and MODIFIED_PRECEDING; calendars from
         the `holidays` package (MIT, pure Python) behind
         stable calendar ids; schedules unadjusted unless an
         input asks otherwise.
      6. Tolerance: an output's tolerance is an absolute
         and a relative bound with math.isclose semantics;
         defaults per unit kind live in core/tolerance.py; a
         golden case may loosen its tolerance to its
         source's published precision and records why.
      7. Randomness: every stochastic model takes a bounded
         integer `seed` input with a documented default and
         draws from numpy.random.Generator(PCG64(seed))
         through core/random.py, with no global or unseeded
         state. The manifest records the seed, the bit
         generator and NumPy's version, because NumPy does
         not promise identical streams across versions.
      8. Arrays and tabular data: a field is scalar unless
         declared with an array type and a maximum length.
         Array fields accept lists, tuples, NumPy arrays and
         objects exposing the Arrow PyCapsule stream
         interface (pandas 3, Polars, pyarrow), without a
         copy where the layout allows. run_batch (Step 4)
         evaluates a scalar model over the rows of a table.
         Results default to pandas. Polars and pyarrow are
         never dependencies, not even through an extra — a
         caller asking for a Polars or Arrow result already
         has the library — so conversions import them lazily
         and raise MissingOptionalDependencyError naming the
         package.
      9. pandas 3 semantics: Copy-on-Write, the default
         string dtype, the ME/QE/YE aliases, and one
         explicit datetime resolution, which the ADR names
         after checking pandas 3.0's resolution rules.
      10. Non-finite and undefined results: inputs reject
          NaN and infinity, and NaN and infinity never reach
          a Result or canonical JSON. One rule decides
          between an error and a null: when valid inputs
          leave the model's result as a whole undefined (a
          Gordon value with a return not above growth, a
          singular covariance matrix), compute raises
          DomainError; when one output is undefined while
          the others are meaningful (an IRR with no sign
          change, a ratio with a zero denominator, a Sharpe
          ratio with zero volatility), that output is None
          (JSON null) with a warning code saying why.
      11. Root finding: bracketed Brent's method
          (scipy.optimize.brentq) with tolerances from the
          policy, a documented bracket-expansion rule and an
          iteration cap. No root raises ConvergenceError or
          returns a documented None with a warning; several
          roots (an IRR with several sign changes) yield a
          documented choice and a warning.
      12. Canonical JSON numbers: RFC 8785 (JCS) — UTF-8,
          object keys sorted by UTF-16 code units, numbers
          in ECMAScript's shortest round-trip form, no NaN
          or infinity, integers exact within ±2^53, and
          dates as ISO 8601 strings. Step 4 implements it.
      13. Errors and warnings: PyeconomicsError as the
          base; InputError (wrapping pydantic's validation
          error), DomainError (valid inputs with no defined
          result), ConvergenceError, ModelNotFoundError,
          RegistryError and MissingOptionalDependencyError
          (naming the extra or package to install);
          PyeconomicsWarning, ModelWarning (carried in a
          Result) and PyeconomicsDeprecationWarning, a
          FutureWarning subclass, visible by default, that
          names the replacement and the removing release
          (ADR-0003).
      14. Runtime dependencies and Pyodide: the required
          runtime set is pydantic, NumPy, SciPy and pandas
          (and `holidays` from Step 2). Each lower bound is
          no higher than the version the current Pyodide
          bundles (Pyodide 314.0.7: numpy 2.4.6, scipy
          1.18.0, pandas 3.0.2, pydantic 2.12.5), and none
          has an upper bound; the Python floor still follows
          ADR-0010.
      The Decision outcome has one numbered subsection per
      decision, 1 to 14 in this order, and the Confirmation
      table names each decision's check and the Phase 2 step
      that builds it. Add the ADR to docs/adr/README.md's
      index, replacing the reserved 0008 row. It reads
      `Status: Accepted`, with the acceptance date, only
      after the maintainer accepts or amends it in this PR.
    </requirement>

    <requirement>
      Runtime baseline: `uv add --no-config` pydantic,
      numpy, scipy and pandas at the floors decision 14
      allows (numpy>=2.4, scipy>=1.18, pandas>=3.0,
      pydantic>=2.12); move pydantic out of the dev group
      and delete its comment there; `uv lock --no-config`;
      refresh pylock.toml with `uv export --no-config` (the
      `pylock-fresh` hook checks it). Run the `licences`
      hook. For each package it fails (expected: numpy,
      scipy, pandas and python-dateutil), add a
      licence_exceptions.toml entry whose `licence` is
      exactly what the hook reports and whose `reason`
      names the licence file read in that version's
      distribution (for numpy: its bundled sources are
      0BSD, MIT, Zlib and CC0-1.0, and its compiled wheels,
      like scipy's, also bundle OpenBLAS, LAPACK and the
      GCC runtime library under its runtime-library
      exception; disclose all of them). On the
      PR, exempt from dependency-review by purl, with a
      comment, only a package it flags whose licence the
      `licences` hook already accepts or excepts. Confirm a
      wheel exists for every CI cell.
    </requirement>

    <requirement>
      Implement in src/pyeconomics/core/, each module with
      the three-line header, numpy-style docstrings whose
      examples run as doctests, and no I/O:
      - units.py: the UnitKind enum, the Annotated unit
        markers (Rate, Return, Money, Years, Days, Periods,
        Count, Ratio, Probability, Volatility, Correlation,
        IndexLevel, DateValue) that Step 3's fields build
        on, and the default bounds table;
      - rates.py: percent and basis-point converters for
        boundary code, and display formatting;
      - compounding.py: Frequency, Compounding, and the
        conversions of decision 4;
      - tolerance.py: Tolerance, its isclose, per-unit
        defaults;
      - random.py: generator(seed) and the seed bounds;
      - numerics.py: the bracketed root finder and its
        convergence policy;
      - errors.py and warnings.py: decision 13's taxonomy;
      - __init__.py re-exporting the public names in
        __all__.
    </requirement>

    <requirement>
      Tests, with sockets disabled and hypothesis's `ci`
      profile in CI:
      - tests/unit/core/, one module per core module:
        conversions against closed-form values, the bounds
        table, tolerance semantics, generator determinism
        (one seed, identical draws) and independence
        (different seeds differ), the root finder on a known
        root, a no-root case and a several-root case, and
        the taxonomy (PyeconomicsDeprecationWarning is a
        FutureWarning and is shown under default filters).
      - Property tests: periodic → continuous → periodic
        round trips within tolerance; the effective annual
        rate rises with compounding frequency for a positive
        rate; discount factors fall as maturity rises for a
        positive rate; percent conversions round-trip.
    </requirement>

    <requirement>
      Version and citation (Version rule): `uv version
      1.0.0a1.dev1 --no-config`, and set CITATION.cff's
      `version` to match. tests/unit/test_version.py still
      passes.
    </requirement>

    <requirement>
      Cross-phase verification rule — this step breaks three
      Phase 1 checks and narrows each in the script's style,
      keeping its number and intent:
      - static check 44 becomes "CITATION.cff's version
        equals pyproject.toml's version, and its licence is
        Apache-2.0";
      - static check 18 accepts the 0008 index row as either
        reserved or Accepted with its file's date (it keeps
        requiring the nine Phase 1 ADRs Accepted);
      - V7.2 installs the wheel into its clean venv with its
        runtime dependencies from PyPI (`--no-config`, no
        `--no-index`), since the wheel now has dependencies.
      Append to docs/roadmap/phase01-roadmap.md a `## Post-merge
      addendum (<YYYY-MM-DD>) — Phase 2 changes to
      verify-phase01.sh` section (the template's back-patch
      pattern) with one line per check; later Phase 2 steps
      add their lines there. Run `verify-phase01.sh --fast`
      and `--python` before the PR.
    </requirement>

    <requirement>
      Smoke script and Pyodide (ADR-0002's carry-over):
      - scripts/smoke.py imports pyeconomics from the
        installed distribution, refuses to run when the
        imported package resolves inside the checkout's
        src/ tree, checks __version__ against
        importlib.metadata, and exercises a compounding
        conversion and a tolerance check, printing one line
        per check. Step 4 extends it to run models.
      - ci.yml's package job runs it from outside the
        checkout against the clean-venv wheel.
      - A new `pyodide` job in ci.yml: harden-runner first,
        `permissions: contents: read`, SHA-pinned actions,
        `persist-credentials: false`. It builds the wheel,
        creates a Pyodide virtual environment with an
        exact-pinned pyodide-build (through `uvx --python
        3.14`, since Pyodide 314.0.7 runs Python 3.14) and
        its matching cross-build environment, installs the
        wheel there with NumPy, SciPy, pandas and pydantic
        from Pyodide's own index, and runs scripts/smoke.py
        from outside the checkout. Add `pyodide` to the
        `test` aggregate's needs, so `test` requires it. If
        Pyodide cannot satisfy a floor, lower the floor;
        never skip the job.
    </requirement>

    <requirement>
      CHANGELOG.md: under [Unreleased], "Added" entries for
      ADR-0008, the core conventions and the runtime
      dependencies, and a "Changed" entry for the version.
    </requirement>

    <requirement>
      Filepath comment: every new Python, YAML and TOML file
      gets its repo-relative path as the first line, and
      Python files the full three-line header (CPY001); ADRs
      follow docs/adr/'s convention and carry no filepath
      line.
    </requirement>
  </requirements>
</task>
```

### Step 1 acceptance criteria

- This roadmap and the refreshed planning kit reached `main` as the step
  branch's first two commits.
- `docs/adr/0008-numerical-conventions.md` reads `Status: Accepted` with the
  maintainer's acceptance date, carries the fourteen decisions and a
  Confirmation table, and `docs/adr/README.md` lists it as Accepted.
- `pyproject.toml` requires pydantic, NumPy, SciPy and pandas with lower
  bounds no higher than Pyodide 314.0.7 bundles and no upper bound;
  pydantic is gone from the dev group; the `uv-lock`, `pylock-fresh` and
  `lock-index` hooks pass.
- The `licences` hook passes; every entry in
  `scripts/checks/licence_exceptions.toml` names the licence the hook
  reports and a verified reason, and the maintainer approved each in the
  PR; `dependency-review` is green.
- `src/pyeconomics/core/` holds the eight modules and its `__init__.py`;
  mypy strict and ruff are clean; the unit, property and doctest suites
  pass on all nine CI cells.
- `PyeconomicsDeprecationWarning` subclasses `FutureWarning`, and a test
  shows it is displayed under the default warning filters.
- `pyproject.toml` and `CITATION.cff` both read `1.0.0a1.dev1`;
  `verify-phase01.sh --fast` and `--python` pass with checks 18 and 44 and
  V7.2 narrowed, and `docs/roadmap/phase01-roadmap.md` ends with the
  post-merge addendum naming all three.
- The `pyodide` job is green and in the `test` aggregate's needs, and
  `scripts/smoke.py` passes both in Pyodide and in the package job's clean
  venv.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the runtime baseline is audited,
  licence-checked and locked to PyPI only, while the `pyodide` job holds
  `contents: read` alone, pins its tools and passes zizmor.

---

## Step 2 — Dates, Day Counts and Calendars ✅

**Status:** Complete — PR #73 (2026-10-09)

> **Goal:** Build the date layer ADR-0008 decided: `core/dates.py` (month
> arithmetic and the end-of-month rule), `core/daycount.py` (`DayCount` with
> `THIRTY_360_US`, `THIRTY_E_360`, `ACT_360`, `ACT_365_FIXED`,
> `ACT_ACT_ISDA` and `ACT_ACT_ICMA`, and `year_fraction`), `core/schedule.py`
> (coupon schedules generated backward from maturity with short or long
> stubs, the end-of-month rule, and unadjusted accrual dates beside adjusted
> payment dates) and `core/calendars.py` (`BusinessDayConvention`, calendars
> from the `holidays` package behind stable ids, `adjust`,
> `is_business_day` and `add_business_days`). Add `holidays` as a runtime
> dependency and QuantLib as the phase's first test oracle; prove every
> convention against cited worked examples and against QuantLib over
> generated date pairs, schedules against QuantLib's `Schedule`, and
> calendars against QuantLib's over 2000–2030. Step 6's XIRR and every
> Step 8 bond calculation use this layer. Parent: ROADMAP §4 2.1;
> ADR-0008 decision 5.

**Branch:** `feature/phase02-step2-dates`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | GPT-6.1 Sol                                   |
| Backup       | Claude Opus 5.5 — Claude Code · Effort Medium |
| Platform     | Codex                                         |
| Intelligence | Medium                                        |
| Conversation | **New**                                       |

> Settings updated 2026-10-09: was GPT-6 Sol · Intelligence Medium.
> GPT-6.1 Sol supersedes it in the same model line; this session ran at Medium.

**Model rationale:** Coding is PRIMARY — six day-count conventions,
schedule generation and business-day adjustment — and knowledge SECONDARY,
because each convention follows a cited definition. ADR-0008 has already
chosen the definitions and QuantLib checks every result, so ambiguity and
novelty are low and overall complexity is Medium, with a tier floor of A in
coding. The claude.ai Max weekly pool reads `tight` until Tue 2026-10-13
20:00 EDT and Codex is the lane with slack, so the operator's posture sends
this GPT-adequate Medium step to Codex on the ChatGPT Pro 5x plan, $0
marginal. GPT-6 Sol is S in coding and wins the coverage tie-break over
GPT-6 Astra (SciCode 57.6). Codex opens on its provider default; set GPT-6
Sol at Intelligence Medium, the ladder value for Medium work, because the
oracle tests carry the verification load. The backup is Claude Opus 5.5 on
Claude Code at Effort Medium, its default, S in coding and knowledge. New
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
       feature/phase02-step2-dates`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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

    THIS STEP ALSO:
    - `holidays` joins the runtime set and QuantLib the test
      group: both pass pip-audit; `holidays` passes the
      `licences` hook (MIT); both install on every CI cell
      (QuantLib from its abi3 wheels) and lock with
      `--no-config`.
    - The date layer does no I/O and reads no clock: "today"
      is never a default. A date the caller does not pass is
      an input error, not the current date.
    - Golden values come from cited worked examples and are
      recomputed, never copied prose; no CFA Program
      material.
  </security>

  <context>
    pyeconomics. Phase 2. Step 2: dates, day counts and
    calendars.

    Current state (as of Phase 2 Step 1):

    - ADR-0008 is Accepted; decision 5 fixes the six
      DayCount members and their sources, the five
      BusinessDayConvention members, calendars from
      `holidays` behind stable ids, and unadjusted schedules
      by default.
    - src/pyeconomics/core/ holds units.py (with the
      DateValue marker), rates.py, compounding.py,
      tolerance.py, random.py, numerics.py, errors.py and
      warnings.py. The runtime set is pydantic, NumPy, SciPy
      and pandas; python-dateutil (pulled in by pandas) has
      a reviewed licence exception.
    - scripts/smoke.py runs in the package job's clean venv
      and in the `pyodide` job; Pyodide installs pure-Python
      packages it does not bundle, such as `holidays`, from
      PyPI.

    Files to read (every file before drafting):
    - docs/adr/0008-numerical-conventions.md (decisions 5,
      6 and 13).
    - src/pyeconomics/core/ (all modules) and tests/unit/core/.
    - pyproject.toml, scripts/smoke.py and
      .github/workflows/ci.yml (the pyodide job).
    - QuantLib's Python documentation for DayCounter,
      Thirty360, ActualActual, Schedule and the calendars
      named below (the oracle's semantics).
  </context>

  <goal>
    year_fraction implements the six conventions exactly as
    ADR-0008 defines them and agrees with QuantLib;
    schedules and business-day adjustment agree with
    QuantLib's Schedule and calendars; `holidays` is a
    locked, audited runtime dependency that Pyodide
    installs; QuantLib is the test oracle.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      core/dates.py: add_months and add_years with the
      end-of-month rule (a month-end start stays at
      month-end when the rule is on), is_end_of_month,
      actual day differences, and validation that rejects
      dates outside 1900-01-01 to 2200-12-31 (the default
      date bounds ADR-0008 tabulates).
    </requirement>

    <requirement>
      core/daycount.py: the DayCount enum with exactly the
      members THIRTY_360_US, THIRTY_E_360, ACT_360,
      ACT_365_FIXED, ACT_ACT_ISDA and ACT_ACT_ICMA, and
      year_fraction(start, end, convention, *,
      reference_start=None, reference_end=None,
      frequency=None). ACT_ACT_ICMA requires the reference
      coupon period and the frequency, and handles short
      and long irregular periods as ICMA Rule 251 does;
      every other convention rejects reference arguments
      it does not use. start after end returns the negative
      of the reversed fraction. Each member's docstring
      cites its definition by section (decision 5) and
      quotes no source text.
    </requirement>

    <requirement>
      core/schedule.py: generate(effective, maturity,
      frequency, *, stub="short_front" | "long_front",
      end_of_month, calendar=None, convention=UNADJUSTED)
      returns the unadjusted accrual dates and the adjusted
      payment dates, generated backward from maturity as
      bond schedules are. A schedule with no full period is
      an InputError.
    </requirement>

    <requirement>
      core/calendars.py: BusinessDayConvention with exactly
      UNADJUSTED, FOLLOWING, MODIFIED_FOLLOWING, PRECEDING
      and MODIFIED_PRECEDING; calendar ids `weekends_only`,
      `us_federal`, `us_nyse`, `target2` and `uk_england`,
      each mapped to the `holidays` calendar that defines it
      (look up the package's financial and country
      calendars; record the mapping in the module); adjust,
      is_business_day and add_business_days. A calendar
      `holidays` does not provide (SIFMA's US bond-market
      calendar is one) is not invented; it waits for a
      later step with a source. Reject dates outside a provider's
      declared start_year/end_year with InputError instead of
      accepting its silently empty holiday set (holidays 0.106
      ends in 2100; TARGET begins in 1999). weekends_only
      supports the full ADR date range. `uv add --no-config
      holidays` with a floor no higher than the release
      this step tests, then lock and export.
    </requirement>

    <requirement>
      Oracle: `uv add --no-config --group test QuantLib`.
      Tests in tests/unit/core/:
      - test_daycount.py: for each convention, worked
        examples from cited sources — for ACT/ACT ISDA and
        ICMA, the worked examples in ISDA's 1998 "EMU and
        Market Conventions: Recent Developments" (which
        QuantLib's own test suite reproduces); for the
        30/360 family, hand-computed cases covering every
        end-of-month rule, February in leap and common
        years included — each with its source and locator
        in a comment; and a hypothesis test comparing
        year_fraction with QuantLib's day counter for
        generated date pairs from 1950 to 2150 within
        1e-14.
      - test_schedule.py: regular, short-stub and long-stub
        schedules and end-of-month maturities against
        QuantLib's Schedule (backward rule); adjusted dates
        are business days; unadjusted periods are regular
        except the stub.
      - test_calendars.py: business days from 2000 through
        2030 agree, id by id, with QuantLib's WeekendsOnly
        (weekends_only), UnitedStates(Settlement)
        (us_federal), UnitedStates(NYSE) (us_nyse), TARGET
        (target2) and UnitedKingdom(Settlement)
        (uk_england), except dates listed in the test with
        the source that explains each difference; and each
        convention's adjustment of known holidays and
        month-ends.
      - Property tests: ACT/360 and ACT/365F fractions are
        additive over adjacent periods, as ACT/ACT ISDA is
        across a year end; a year fraction is zero for equal
        dates; adding k months and then −k months returns
        the original date whenever its day of the month is
        28 or less.
    </requirement>

    <requirement>
      Extend scripts/smoke.py with one year_fraction check
      and one calendar adjustment, so the clean-venv and
      Pyodide smokes prove `holidays` installs and works.
    </requirement>

    <requirement>
      Export the new public names from
      pyeconomics.core.__init__; CHANGELOG [Unreleased]
      "Added" entries for the date layer and the `holidays`
      dependency.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (path, copyright, SPDX).
    </requirement>
  </requirements>
</task>
```

### Step 2 acceptance criteria

- `DayCount` has exactly the six members ADR-0008 names, and
  `year_fraction` reproduces every cited worked example and agrees with
  QuantLib within 1e-14 on generated date pairs from 1950 to 2150.
- Schedules match QuantLib's `Schedule` for regular, short-stub,
  long-stub and end-of-month cases, with unadjusted accrual dates and
  adjusted payment dates.
- `BusinessDayConvention` has exactly the five members ADR-0008 names; each
  of the five calendar ids agrees with its named QuantLib calendar from 2000
  through 2030 except the listed, sourced differences.
- `holidays` is a runtime dependency that passes the `licences` hook and
  pip-audit, QuantLib is in the test group, and both install on every CI
  cell; the `pyodide` job runs the extended smoke script green.
- Unit, property and doctest suites pass on all nine CI cells; mypy
  strict and ruff are clean.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the date layer reads no clock and
  does no I/O (no `date.today()` or `datetime.now()` default anywhere in
  `core/`).

---

## Step 3 — Model Specification and Registry ✅

**Status:** Complete — PR #76 (2026-10-09)

> **Goal:** Turn the Overview's model contract into code. Add
> `core/spec.py` (`ModelSpec`, `Reference`, `Evidence` with `standard`,
> `practitioner`, `contested`, `rejected` and `historical`, `CostClass`,
> `Invariant`, `Example`, `ChartSpec`, `ChangelogEntry`, an `extra` naming
> the extra a model's computation needs, and a reserved, empty `bindings`
> field for Phase 3), `core/model.py` (`ModelInputs` and
> `ModelOutputs`, frozen and closed; the array field types; the `Model`
> object the `@model` decorator returns, which validates inputs and
> outputs around a pure `compute`; discriminated unions on `calculation`),
> `core/context.py` (`warn()`), `core/registry.py` (discovery through the
> `pyeconomics.models` entry-point group, deterministic order, conflict
> errors, aliases that warn with `PyeconomicsDeprecationWarning`),
> `core/_released.py` (the released-id ledger, empty until Step 14) and
> the public facade `pyeconomics.registry` with `ids`, `get`, `models`,
> `domains`, `resolve` and `validate`. `validate()` rejects every
> incomplete spec, the ADR-0003 cases included (a released id missing or
> reused). Purity is enforced twice: the `model-purity` semgrep rule bans
> I/O, clock, print, global-random and `warnings.warn` calls under
> `src/pyeconomics/models/`, and an AST test holds that tree's imports to
> an allowlist. Toy models in `tests/registry/` prove each rule; no catalog
> model lands yet. Parent: ROADMAP §4 2.2; ADR-0001, ADR-0003, ADR-0008.

**Branch:** `feature/phase02-step3-registry`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Sonnet 5.5                             |
| Backup       | GPT-6 Astra — Codex · Intelligence Extra High |
| Platform     | Claude Code                                   |
| Effort       | Extra High                                    |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and planning SECONDARY: the step
turns this roadmap's model contract into the API every model and every
generated surface calls — specification, decorator, unit-typed fields,
entry-point discovery, aliases and deprecation, `validate()`, the
released-id ledger and the purity guards — and a flaw in it compounds
across hundreds of models. High complexity with novel design across many
files requires S in coding; Sonnet 5.5 is S in coding and planning, ties
Opus 5.5, Fable 5.1 and GPT-6 Astra on both, and wins the coverage
tie-break, rated S or A in all seven categories (AA Intelligence Index
56.0). Claude Code on the claude.ai Max plan pays for it, $0 marginal while
the weekly pool has headroom; High work keeps its place while the pool
reads `tight`. Claude Code opens on Opus 5.5 at Medium; switch to Sonnet
5.5 at Extra High — High for the complexity, one rung more for novel API
design reasoned across many files — and not Max, because this roadmap
already fixes the contract's shape. Thinking stays On. The backup is GPT-6
Astra on Codex under ChatGPT Pro 5x, S in coding and planning, at
Intelligence Extra High. New conversation per phase-boundary hygiene.

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
       feature/phase02-step3-registry`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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

    THIS STEP ALSO:
    - Purity is a security property here: a model that could
      reach the network, the filesystem or the clock is a
      data-exfiltration and SSRF path once Phase 4 serves
      it. The `model-purity` rule and the import allowlist
      are part of this step's definition of done, and the
      `semgrep-test` hook proves the rule fires.
    - Entry-point discovery imports third-party code by
      design: load only the `pyeconomics.models` group, in
      a deterministic order, and fail closed on a conflict
      or a malformed entry point, naming the distribution.
    - Every field has bounds, so no model input is
      unbounded in size (the cost-exhaustion vector Phase 4
      inherits); validate() enforces it.
  </security>

  <context>
    pyeconomics. Phase 2. Step 3: model specification and
    registry.

    Current state (as of Phase 2 Step 2):

    - ADR-0008 is Accepted. core/ holds the conventions
      (units.py with the Annotated unit markers Rate,
      Return, Money, Years, Days, Periods, Count, Ratio,
      Probability, Volatility, Correlation, IndexLevel and
      DateValue; rates, compounding, tolerance, random,
      numerics, errors, warnings) and the date layer
      (dates, daycount, schedule, calendars).
    - PyeconomicsDeprecationWarning (a FutureWarning) and
      the error taxonomy exist; nothing yet registers,
      discovers or validates a model.
    - The wheel allowlist admits only Python modules under
      pyeconomics/, so the ledger is a module, not data.
    - .semgrep/rules/ holds four rules, each with a test in
      .semgrep/tests/, run one at a time by the
      `semgrep-test` hook (scripts/checks/semgrep_tests.py).

    Files to read (every file before drafting):
    - This roadmap's Overview: "The model contract", the
      launch-catalog table and the Contract-change rule.
    - docs/roadmap/ROADMAP.md §4 2.2 and §5 "Model quality
      & governance" (the definition of done validate()
      enforces).
    - docs/adr/0001-product-boundaries.md,
      0003-versioning-and-deprecation.md,
      0009-name-domains-and-trademark.md (no "cfa" in any
      name) and 0008-numerical-conventions.md.
    - src/pyeconomics/core/ and src/pyeconomics/__init__.py.
    - .semgrep/rules/, .semgrep/tests/ and
      scripts/checks/semgrep_tests.py.
  </context>

  <goal>
    A third-party package or pyeconomics itself registers a
    model by exporting a decorated function from a module
    named in the `pyeconomics.models` entry-point group;
    pyeconomics.registry discovers, resolves and validates
    every registered model; validate() rejects each
    incomplete or unsafe spec with a message naming the
    model and the rule; and the purity guards hold under
    src/pyeconomics/models/.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      core/model.py:
      - ModelInputs and ModelOutputs: pydantic BaseModel
        subclasses with frozen=True, extra="forbid",
        allow_inf_nan=False and validate_default=True.
      - Array field types: one tuple alias per unit kind
        (RateArray, MoneyArray, DateArray and the rest),
        whose elements carry the unit and its default
        bounds, and ARRAY_INPUT, the before-validator that
        accepts lists, tuples, NumPy arrays, one-column
        frames and objects exposing the Arrow PyCapsule
        stream interface (ADR-0008 decision 8), converting
        through NumPy without an intermediate copy where the
        layout allows (pyarrow, imported on demand, reads a
        stream with no NumPy view). An alias fixes no
        length: a field bounds it with Field(max_length=),
        because constraints stacked on one type do not
        narrow, the last one wins.
      - Model: an immutable object holding the ModelSpec
        and compute. Calling it — model(inputs) or
        model(**fields) — validates the inputs (a
        discriminated union is resolved on its
        `calculation` field), runs compute, and validates
        the outputs, so an out-of-bounds output is a model
        bug that raises, never a silent value. Invalid
        inputs raise InputError carrying pydantic's
        details.
      - model(...): the decorator that builds the
        ModelSpec from its arguments and the compute
        function's type hints, with no global side effect
        at import time.
    </requirement>

    <requirement>
      core/spec.py: ModelSpec with id, version (an integer,
      at least 1, that increments whenever outputs for some
      valid input change or a schema changes), title,
      summary, domain (derived from the id), tags, formula
      (one or more LaTeX strings), assumptions, limitations,
      references, evidence, cost, invariants, examples,
      charts, aliases, changelog, bindings and the inputs and
      outputs types, plus `extra`: the name of the extra
      whose library compute imports, or None. Reference
      carries key, citation, a doi or url, a locator (page,
      table, section, equation or chapter; ROADMAP §4 2.2
      asks for "DOI or URL plus page or table") and an
      optional isbn. Invariant carries a snake_case id and a
      statement in plain words. Example carries a name,
      inputs and an optional note. ChangelogEntry carries a
      model version and a note. CostClass is INSTANT, LIGHT
      or HEAVY (ROADMAP §5 "Hosted budget"). bindings is
      reserved for Phase 3 and must be empty.
    </requirement>

    <requirement>
      core/context.py: warn(code, message) records a
      ModelWarning in the active run context (a
      contextvars collector Step 4's run() installs) and,
      outside a run, issues it through the warnings module
      with stacklevel pointing at the caller. Codes are
      snake_case and documented per model.
      (From Step 1: core/warnings.py already defines
      warn(code, message, *, stacklevel=1), which only
      issues a ModelWarning through the warnings module,
      and core/numerics.find_root calls it for
      `several_roots`. Move warn() here, or have it
      delegate here, so pyeconomics.core exports exactly
      one warn() that records into the collector; keep its
      stacklevel semantics and the snake_case check in
      ModelWarning, and make find_root's warning land in
      the collector too.)
    </requirement>

    <requirement>
      core/registry.py and the facade
      src/pyeconomics/registry.py:
      - Discovery reads importlib.metadata entry points in
        the `pyeconomics.models` group, sorted by name and
        distribution; each names a module, whose `__all__`
        lists the Model objects it registers. Discovery is
        lazy (first use, never at `import pyeconomics`) and
        cached, with a refresh() for tests.
      - A duplicate canonical id or alias across entry
        points, a malformed entry point, or a module whose
        import fails raises RegistryError naming the
        distribution and the id.
      - ids(), get(id), models(domain=None), domains() and
        resolve(id). get and resolve accept an alias, issue
        PyeconomicsDeprecationWarning naming the canonical
        id and the release that removes the alias, and
        return the canonical model; an unknown id raises
        ModelNotFoundError with close matches.
      - Registry.from_models(...) builds an isolated
        registry, so tests never touch the installed one.
    </requirement>

    <requirement>
      validate(registry=None) checks every model and raises
      RegistryError listing every problem, each naming the
      model and the rule, or returns None when all pass:
      - the id matches ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,2}$,
        its first segment is one of the fifteen domains in
        core/spec.py's DOMAINS (foundations, econometrics,
        macro, international, micro, accounting, corporate,
        equity, fixed_income, derivatives, alternatives,
        portfolio, asset_pricing, risk, performance), and no
        id or alias contains "cfa" (ADR-0009);
      - version is at least 1 and the changelog has an entry
        for it;
      - title and summary are non-empty and within their
        lengths; there is at least one formula, assumption,
        limitation and reference, and every reference has a
        doi or url and a locator;
      - `extra`, when set, names an extra the model's
        distribution declares (its Provides-Extra
        metadata);
      - evidence and cost are set;
      - inputs and outputs are ModelInputs and ModelOutputs
        subclasses, or discriminated unions of them on a
        `calculation` field whose input and output members
        name the same calculations;
      - every numeric field, nested or in an array, carries
        a unit marker, finite lower and upper bounds and a
        description; every array and string field a maximum
        length; no field is typed Any, object or an
        unconstrained dict;
      - there is at least one example, and every example
        validates and runs, its outputs within bounds; each
        calculation of a union has an example. When a
        model's `extra` is not installed, its examples must
        still validate, and running one must raise
        MissingOptionalDependencyError naming that extra —
        validate() checks that instead of the outputs, so
        it passes in an extra-less environment;
      - invariant ids are unique, and a model with none
        records why in its spec;
      - aliases are valid ids, distinct from every canonical
        id and unique in the registry;
      - bindings is empty;
      - every id in core/_released.py still resolves, to the
        model released under it or to a model that lists it
        as an alias (ADR-0003: a released id is never deleted
        or reused).
    </requirement>

    <requirement>
      Purity guards:
      - .semgrep/rules/model-purity.yaml, scoped to
        src/pyeconomics/models/: flags open, print, input,
        warnings.warn, logging calls, time.time,
        datetime.now, date.today, numpy's global random
        functions (np.random.seed, np.random.rand and the
        other legacy calls, default_rng with no seed), the
        random module, os.environ, subprocess and socket
        use. .semgrep/tests/model-purity.py carries
        `ruleid:` and `ok:` cases for each; the
        `semgrep-test` hook runs it.
      - tests/registry/test_model_imports.py parses every
        module under src/pyeconomics/models/ with ast and
        fails on any import outside an allowlist: the
        standard library's math, cmath, statistics,
        dataclasses, enum, functools, itertools, operator,
        collections, typing, decimal and datetime (types
        only); numpy, scipy, pandas, pydantic and
        pyeconomics.core; and the module's own domain
        package (pyeconomics.models.<domain>, or a relative
        import inside it), so a domain's __init__.py can
        list its models and share helpers. One domain never
        imports another: a helper two domains need moves to
        core/. An extra's library is allowed only inside
        compute, in a model whose spec names that extra
        (Step 12's statsmodels for econometrics.ols).
    </requirement>

    <requirement>
      core/_released.py: RELEASED, a read-only mapping from
      released id to the canonical id it named at release and
      the first package version that shipped it; empty in
      this step. Step 14 fills it with a reviewed script.
    </requirement>

    <requirement>
      Tests in tests/registry/ with toy models in
      tests/registry/toy_models.py (scalar, array-input and
      multi-calculation examples, and one whose `extra`
      names an extra that is not installed), using
      Registry.from_models and a monkeypatched entry-point
      list:
      - one test per validate() rule, each with a toy spec
        that breaks exactly that rule;
      - discovery order, caching and conflict errors;
      - alias resolution warns
        PyeconomicsDeprecationWarning (caught with
        pytest.warns, since warnings are errors) and returns
        the canonical model;
      - calling a model rejects out-of-bounds, NaN and
        infinite inputs and unknown fields, enforces output
        bounds, and keeps inputs frozen;
      - warn() records into a collector and falls back to
        the warnings module outside one;
      - validate() passes on the installed registry, which
        is empty in this step.
    </requirement>

    <requirement>
      Export the public names from pyeconomics.core and make
      `import pyeconomics` expose the registry facade without
      triggering discovery. CHANGELOG [Unreleased] "Added"
      entries for the specification and registry.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; the semgrep rule and its YAML get
      `# <path>` as the first line.
    </requirement>
  </requirements>
</task>
```

### Step 3 acceptance criteria

- `pyeconomics.registry` exposes `ids`, `get`, `models`, `domains`,
  `resolve` and `validate`, and discovery reads only the
  `pyeconomics.models` entry-point group, lazily, in a deterministic order.
- Every `validate()` rule in this step's task has a toy spec that breaks
  exactly that rule, and `validate()` rejects each one with a message
  naming the model and the rule; it passes on the installed registry.
- An alias resolves to its canonical model with a
  `PyeconomicsDeprecationWarning` naming the replacement and the removing
  release; a duplicate id or alias across entry points raises
  `RegistryError` naming the distribution.
- Calling a model rejects out-of-bounds, NaN, infinite and unknown
  inputs and enforces output bounds; inputs are immutable.
- `core/_released.py` exists and `validate()` checks it; it is empty
  until Step 14.
- `.semgrep/rules/model-purity.yaml` fires on every `ruleid:` case and no
  `ok:` case (the `semgrep-test` hook), and the import-allowlist test
  passes.
- mypy strict, ruff and the full suite pass on all nine CI cells.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the purity guards make a model that
  opens a socket, a file or the clock fail the gate or the suite before it
  can merge.

---

## Step 4 — Results, Provenance and Schemas ✅

**Status:** Complete — PR #77 (2026-10-09)

> **Goal:** Make every model run produce a `Result` other software can
> trust and reproduce. Add `pyeconomics.run(model_id, inputs=None, /,
> **fields)` and `pyeconomics.run_batch(model_id, rows)`; `core/results.py`
> (`Result`: inputs, outputs, warnings and a manifest; immutable) and
> `core/manifest.py` (a deterministic `Manifest`: model id and version,
> package and dependency versions, seed and bit generator for stochastic
> models, an empty `data_sources` list Phase 3 fills, and SHA-256 hashes
> of the canonical inputs and of the result body — no clock, host or
> path); `core/canonical.py` (RFC 8785 canonical JSON, implemented in-house
> and checked against the RFC's test vectors and the `rfc8785` package as a
> test oracle); `core/schema.py` (JSON Schema 2020-12 for every input and
> output model, with `x-unit` and discriminated unions); conversions to
> dict, canonical JSON, pandas, Polars, Arrow and Parquet; `core/cards.py`
> and `Result.card()`; `Result.plot()` behind the `[plot]` extra (Plotly);
> and `registry.describe(id)`, the JSON description Phase 4's export builds
> on. `scripts/smoke.py` now runs one model per registered domain, and
> `release-smoke.yml` runs it against every published release. Parent:
> ROADMAP §4 2.3; ADR-0008 decisions 7, 8, 10 and 12.

**Branch:** `feature/phase02-step4-results`

**Deploys:** nothing beyond merge — `release-smoke.yml` changes, but it
runs only after a release; Step 13's rehearsal is its first run.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Sonnet 5.5                             |
| Backup       | GPT-6 Astra — Codex · Intelligence High       |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and planning SECONDARY: the result,
manifest, canonical JSON and schemas are the contracts Phase 4's parity
suite will compare byte for byte across four surfaces, and their design
choices (what the manifest hashes, how a union becomes a schema) are
permanent once released. High complexity requires S in coding; Sonnet 5.5
is S in coding and planning and wins the coverage tie-break, S or A in all
seven categories (AA Intelligence Index 56.0). Claude Code on the
claude.ai Max plan pays for it, $0 marginal while the weekly pool has
headroom; High work keeps its place while the pool reads `tight`. Claude
Code opens on Opus 5.5 at Medium; switch to Sonnet 5.5 at High — the
design is fixed by ADR-0008 and this task, and RFC 8785's vectors plus an
independent implementation check the hardest part, so High suffices
without Extra High. Thinking stays On. The backup is GPT-6 Astra on Codex
under ChatGPT Pro 5x, S in coding and planning, at Intelligence High. New
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
       feature/phase02-step4-results`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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

    THIS STEP ALSO:
    - Canonical JSON and schemas parse and emit with the
      standard json module only; no pickle, eval or
      yaml.load path (the existing semgrep rules hold).
    - The manifest and every serialization carry no
      credential, environment variable, host name, user
      path or wall-clock time; a test inspects a manifest's
      keys and values.
    - run_batch bounds its row count, so a batch is never an
      unbounded workload.
    - plotly joins the `plot` extra and rfc8785 and
      jsonschema the test group: each passes pip-audit,
      plotly's closure passes the `licences` hook, and all
      lock with `--no-config`.
    - release-smoke.yml's new checkout keeps
      `persist-credentials: false`, `contents: read` and a
      SHA-pinned action; zizmor stays clean.
  </security>

  <context>
    pyeconomics. Phase 2. Step 4: results, provenance and
    schemas.

    Current state (as of Phase 2 Step 3):

    - Models are ModelInputs → ModelOutputs functions
      wrapped by @model; core/registry.py discovers them
      through the `pyeconomics.models` entry-point group;
      pyeconomics.registry exposes ids, get, models,
      domains, resolve and validate; warn() records into a
      contextvars collector when one is active.
    - What Step 3 built for this step to use:
      core/context.collect_warnings() is the context manager
      run() wraps around compute (it yields the list of
      ModelWarnings); a Model has validate_inputs,
      validate_outputs, input_adapter and output_adapter
      (pydantic TypeAdapters, the schema source), compute
      (the raw function), and spec; get and resolve both
      return the canonical Model, and an alias warns with
      PyeconomicsDeprecationWarning. An out-of-bounds
      output raises pydantic's ValidationError, not
      InputError. ChartSpec is id, title, kind (line, bar
      or scatter), x, y (output field names), x_label,
      y_label and calculation; validate() holds x and y to
      array outputs, and this step may extend it. The
      spec's no_invariants_reason records why a model
      declares no invariant. pyeconomics.core exports the
      decorator as `model`, so import the module by path:
      `from pyeconomics.core.model import Model`.
    - No catalog model is registered yet; the toy models in
      tests/registry/toy_models.py (scalar, array-input and
      multi-calculation) are what this step's tests run.
    - ADR-0008 fixes randomness (decision 7), arrays and
      tabular data (8), non-finite results (10) and
      canonical JSON numbers (12).
    - release-smoke.yml installs the released version in a
      fresh venv and checks only its version string; the
      `plot` extra is an empty list.

    Files to read (every file before drafting):
    - docs/adr/0008-numerical-conventions.md.
    - docs/roadmap/ROADMAP.md §3 (the manifest), §4 2.3 and
      4.1 (what Phase 4 builds on describe() and the
      schemas) and §5 "Model quality & governance".
    - src/pyeconomics/core/ (spec, model, context,
      registry) and tests/registry/.
    - RFC 8785 (JSON Canonicalization Scheme), sections 3.2
      and Appendix B, and the JSON Schema 2020-12 core and
      validation specifications.
    - scripts/smoke.py, .github/workflows/ci.yml and
      .github/workflows/release-smoke.yml.
  </context>

  <goal>
    run() returns a Result whose canonical JSON and
    manifest hashes are identical on every run of the same
    inputs in the same environment; every registered
    model's input and output schemas are valid 2020-12
    schemas its examples satisfy; canonical-JSON round
    trips are lossless; results convert to pandas, Polars,
    Arrow and Parquet and render a card and, with [plot], a
    Plotly figure; and the smoke script runs one model per
    domain wherever it runs.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      run and run_batch, exported from pyeconomics:
      - run(model_id, inputs=None, /, **fields) resolves the
        id (aliases warn), validates the inputs, installs
        the warning collector, runs the model and returns a
        Result. DomainError, ConvergenceError and
        InputError propagate unchanged.
      - run_batch(model_id, rows) accepts a pandas or Polars
        DataFrame, any object exposing the Arrow PyCapsule
        stream interface, or an iterable of mappings, with at
        most 100,000 rows, runs the model on each row and
        returns a BatchResult with its Results and
        to_pandas, to_polars and to_arrow (input columns,
        output columns and each row's result hash).
    </requirement>

    <requirement>
      core/results.py and core/manifest.py:
      - Result: model id, model version, inputs, outputs,
        warnings (code and message) and manifest; immutable;
        to_dict(), to_json() (canonical), to_pandas(),
        to_polars(), to_arrow(), to_parquet(path), card()
        and plot().
      - Manifest: schema_version, model_id, model_version,
        package_version, the versions of numpy, scipy,
        pandas and pydantic, seed and bit_generator (for a
        model with a seed input), data_sources (an empty
        list, reserved for Phase 3), inputs_sha256 (over the
        canonical JSON of the model id, model version and
        inputs) and result_sha256 (over the canonical JSON of
        the result body). It holds no wall-clock time, host
        name, user path or environment value, so two runs of
        the same inputs produce the same bytes.
      - Polars and pyarrow are imported lazily and, when
        absent, raise MissingOptionalDependencyError naming
        the package (ADR-0008 decision 8); to_parquet
        writes through pyarrow.
    </requirement>

    <requirement>
      core/canonical.py: canonical_json(value) -> bytes
      implementing RFC 8785 for the JSON values results
      produce: object keys sorted by UTF-16 code units,
      strings escaped as the RFC specifies, numbers in
      ECMAScript's shortest round-trip form (derived from
      repr), integers exact within ±2^53, ISO 8601 dates,
      and an error on NaN or infinity. Tests: the RFC's
      Appendix B number samples and its key-sorting example;
      a hypothesis comparison with the `rfc8785` package
      (`uv add --no-config --group test rfc8785`) over
      generated JSON values; and json.loads round trips that
      reproduce every finite float exactly.
    </requirement>

    <requirement>
      core/schema.py: input_schema(id) and output_schema(id)
      return JSON Schema 2020-12 documents with `$schema`
      set to the 2020-12 dialect URI, a stable `$id`
      (urn:pyeconomics:model:<id>:<version>:input|output),
      `x-unit` on every numeric field, bounds, descriptions,
      examples, and a union rendered as oneOf with a
      discriminator mapping on `calculation`. Tests
      (`uv add --no-config --group test jsonschema`): for
      every registered model and every toy model, both
      schemas pass Draft202012Validator.check_schema; each
      example validates against the input schema and its
      outputs against the output schema; and inputs →
      canonical JSON → json.loads → model validation returns
      equal inputs (lossless round trip). These tests iterate
      over the registry, so every catalog model Steps 6–12
      add is covered without new test code.
    </requirement>

    <requirement>
      registry.describe(id) returns a JSON-serializable dict
      — id, version, domain, title, summary, tags, formula,
      assumptions, limitations, evidence, cost, references,
      invariants, examples, changelog, input and output
      schemas, and the card's Markdown — that canonical_json
      accepts. Phase 4's registry.json is a list of these.
    </requirement>

    <requirement>
      core/cards.py: ModelCard built from a spec, with
      sections for the title and summary, the formula
      (LaTeX), a variables table (name, unit, bounds,
      description) for inputs and outputs, assumptions,
      limitations, the evidence status and what it means, a
      worked example (the first example's inputs and
      computed outputs), references, a curriculum-mapping
      section that reads "Not yet mapped; syllabus
      crosswalks arrive in Phase 7", the changelog, and the
      notice "Educational and informational use only; not
      investment advice." It renders to MyST Markdown
      (to_markdown) and in notebooks (_repr_markdown_).
      Result.card() returns its model's card.
    </requirement>

    <requirement>
      Plotting: `uv add --no-config --optional plot plotly`
      and `uv add --no-config --group test plotly`
      (Dependency rule: the default environment then tests
      and type-checks the plotting code, while the package
      job's clean venv keeps proving the extra-less
      install), and add plot to the `all` extra.
      Result.plot() imports Plotly lazily, builds the figure
      from the spec's ChartSpecs, and raises
      MissingOptionalDependencyError naming
      `pyeconomics[plot]` when Plotly is absent; a test
      simulates its absence. If Plotly ships no type
      information, add a narrow mypy override for
      `plotly.*` with a comment.
    </requirement>

    <requirement>
      Smoke: scripts/smoke.py runs, for every registered
      domain, the first model's first example through
      run(), checks that two runs give identical canonical
      JSON and manifest hashes, and that validate() passes;
      `--all` runs every example of every model;
      `--min-domains N` fails when fewer than N domains were
      covered. A model whose spec names an extra that is
      not installed is exercised by asserting that running
      it raises MissingOptionalDependencyError naming the
      extra, which covers its domain in an extra-less
      environment (ADR-0002's "no extras installed" smoke);
      `--extras` instead fails unless every such model ran
      and returned outputs.
      release-smoke.yml checks out the repository at the
      released tag (scripts/ only, persist-credentials:
      false) and runs `scripts/smoke.py --min-domains 11`
      with the installed release, from outside the checkout.
      The package and pyodide jobs keep running it without a
      minimum.
    </requirement>

    <requirement>
      Tests (sockets disabled): Result and Manifest
      determinism and immutability, hash coverage, the
      absence of volatile manifest fields, each conversion
      (with Polars and pyarrow absent and, in a test-only
      environment where present, present), card sections,
      run_batch's row bound, and warnings collected into the
      Result rather than raised. CHANGELOG [Unreleased]
      "Added" entries for results, canonical JSON, schemas,
      cards and the plot extra.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; workflow edits keep `# <path>` as
      the first line.
    </requirement>
  </requirements>
</task>
```

### Step 4 acceptance criteria

- `pyeconomics.run` and `pyeconomics.run_batch` exist; a `Result` holds
  inputs, outputs, warnings and a manifest, and two runs of the same
  inputs produce byte-identical canonical JSON and identical manifest
  hashes.
- The manifest holds no wall-clock time, host name, user path or
  environment value; `data_sources` is an empty list.
- `canonical_json` passes RFC 8785's Appendix B samples and key-sorting
  example and agrees with the `rfc8785` package on generated values;
  finite floats round-trip exactly.
- Every registered and toy model's input and output schemas pass
  `Draft202012Validator.check_schema`, carry `x-unit` on numeric fields,
  and accept their examples; input round trips are lossless.
- `registry.describe(id)` is canonical-JSON serializable; `Result.card()`
  renders every section; `Result.plot()` works with `[plot]` and names
  `pyeconomics[plot]` without it.
- `scripts/smoke.py` runs one model per registered domain;
  `release-smoke.yml` runs it with `--min-domains 11` from outside a
  checkout of the released tag.
- mypy strict, ruff and the full suite pass on all nine CI cells, with
  plotly in both the `plot` extra and the `test` group.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and no result, manifest or export can
  carry a credential, environment value or host detail (tested).

---

## Step 5 — Verification Harness ✅

**Status:** Complete — PR #78 (2026-10-10)

> **Goal:** Build the machinery that holds every catalog model to the
> definition of done before a single model exists. Define the golden-case
> format (`tests/golden/<domain>/<name>.toml`, documented in
> `tests/golden/README.md`) with cited sources, locators, edge cases and
> per-output tolerances; write the harness (`tests/golden/test_golden.py`)
> that requires a golden file for every registered model, at least three
> cases with an edge case (or a recorded reason), a valid citation for
> every case and no CFA Program curriculum source, and runs each case
> through `run()` with ADR-0008's tolerance policy; add the `invariant` and
> `oracle` pytest markers and a meta-test that holds every declared
> invariant to a marked property test; add `tests/strategies.py`, which
> generates valid inputs from each model's fields, and a contract suite
> that fuzzes every registered model for bounds, determinism, round trips
> and documented errors; enforce branch-coverage floors of 95% on `core/`
> and 90% on `models/` with `scripts/checks/coverage_floors.py` in CI; add
> the `scripts/new_model.py` scaffold; and write the mechanics into
> CONTRIBUTING and a model checklist into the pull request template.
> Parent: ROADMAP §4 2.4 and §5 "Model quality & governance".

**Branch:** `feature/phase02-step5-harness`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Sonnet 5.5                             |
| Backup       | GPT-6 Astra — Codex · Intelligence High       |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and planning SECONDARY: a golden-case
format, a harness, an invariant meta-test, input strategies and coverage
floors that every one of the 32 catalog entries must pass. The patterns are
known, but a vacuous check here would let 32 models through unverified —
Phase 1 found a vacuous semgrep test — so the scope is cross-cutting and
the step is High complexity. High requires S in coding; Sonnet 5.5 is S in
coding and planning and wins the coverage tie-break, S or A in all seven
categories (AA Intelligence Index 56.0). Claude Code on the claude.ai Max
plan pays for it, $0 marginal while the weekly pool has headroom; High
work keeps its place while the pool reads `tight`. Claude Code opens on
Opus 5.5 at Medium; switch to Sonnet 5.5 at High, the ladder value — the
harness applies a fixed design, so no Extra High. Thinking stays On. The
backup is GPT-6 Astra on Codex under ChatGPT Pro 5x, S in coding and
planning, at Intelligence High. New conversation per phase-boundary
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
       feature/phase02-step5-harness`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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

    THIS STEP ALSO:
    - Golden files are read with tomllib only (no
      evaluation of fixture content), and the loader
      rejects unknown keys.
    - Fixtures hold only the handful of published values a
      case needs, each cited; no dataset is mirrored and no
      licensed data enters the repository (ROADMAP §5 "Data
      terms").
    - scripts/new_model.py writes only inside the
      repository's src/ and tests/ trees, refuses existing
      files, and validates the id first, so it cannot
      overwrite or traverse paths.
  </security>

  <context>
    pyeconomics. Phase 2. Step 5: verification harness.

    Current state (as of Phase 2 Step 4):

    - pyeconomics.run returns a Result with canonical JSON
      and a deterministic manifest; schemas and
      describe() exist; the contract tests in
      tests/registry/ and the schema tests iterate over the
      registry, which still holds no catalog model.
    - What Step 4 built for this step to use: run(model_id,
      ...) looks the model up in the installed registry, so
      the harness's own tests, which use toy models, call
      pyeconomics.core.run_model(model, inputs) (and
      run_model_batch) instead; both return a Result with
      .inputs, .outputs (validated models), .warnings
      (code, message), .manifest and .to_dict()/.to_json().
      Warnings land in the Result, never in Python's
      warnings machinery. Canonical JSON writes a
      whole-number double such as 5.78e16 without an
      exponent, so json.loads returns an exact int: compare
      with float(loaded), and canonicalize parsed data again
      only through json.loads(text, parse_int=float).
      tests/results/ shows the pattern (schemas, round
      trips, conversions over the registry plus
      tests/registry/toy_results_models.py).
    - ModelSpec declares invariants (snake_case ids with a
      statement), examples, references and a cost class;
      ADR-0008 decision 6 fixes the tolerance semantics and
      core/tolerance.py the per-unit defaults.
    - pytest runs with --strict-markers (a marker must be
      registered), filterwarnings = error, sockets disabled
      and hypothesis profiles; coverage uses source_pkgs and
      fail_under = 95 overall.
    - CONTRIBUTING's "Model definition of done" holds the
      ROADMAP §5 table; the pull request template has no
      model section.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §4 2.4 and §5 "Model quality &
      governance" and "Legal & brand guardrails" (CFA
      Institute marks and content).
    - This roadmap's Overview: the Citation rule and the
      launch-catalog table.
    - docs/adr/0008-numerical-conventions.md (tolerance,
      bounds, non-finite results).
    - src/pyeconomics/core/ (spec, model, registry,
      results, tolerance) and tests/registry/.
    - pyproject.toml ([tool.pytest.ini_options],
      [tool.coverage.*]), tests/conftest.py,
      .github/workflows/ci.yml, CONTRIBUTING.md and
      .github/pull_request_template.md.
  </context>

  <goal>
    From the next step on, a model cannot merge unless the
    harness finds its golden file, runs at least three cited
    cases with an edge case within tolerance, finds a
    marked property test for every invariant it declares,
    fuzzes it without an undocumented error, and the
    coverage floors hold.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      tests/golden/README.md fixes the format, one TOML file
      per model at tests/golden/<domain>/<name>.toml:
      - top level: `model` (the id) and an optional
        `min_cases_reason`;
      - `[[sources]]`: key, kind (certified, official,
        paper, textbook or identity), citation, and url, doi
        or isbn (not needed for identity); a textbook source
        adds `recomputed_with` (the independent method) or
        `published_digits`;
      - `[[cases]]`: id, source, locator (required unless
        the kind is identity), edge (bool), inputs (an
        inline table, with `calculation` for a union model),
        expected (output field → value), an optional
        `expected_none` list for outputs that must be None,
        an optional per-field tolerance (`abs`, `rel`), and
        an optional note.
      It lists the edge-case categories each model draws
      from where they apply: zero and negative rates, very
      long maturities (50 years or more), extreme
      volatilities (2.0 or more), and degenerate inputs (a
      single cash flow, zero variance, the smallest valid
      sample).
    </requirement>

    <requirement>
      The harness (tests/golden/_loader.py and
      tests/golden/test_golden.py) fails when:
      - a registered model has no golden file, or a file
        names an unregistered model;
      - a file has unknown keys, a case cites an undefined
        source, or a non-identity case has no locator;
      - a model has fewer than three cases without a
        `min_cases_reason`, or no edge case;
      - a textbook case lacks `recomputed_with` and its
        tolerance is tighter than half a unit in its
        `published_digits`;
      - an expected field is not an output of the case's
        calculation, or a case's outputs differ from
        `expected` beyond the tolerance (the case's own,
        else ADR-0008's per-unit default, compared with
        math.isclose semantics).
      Cases run through pyeconomics.run, one parametrized
      test per case, named by model and case id.
    </requirement>

    <requirement>
      Citation guard (tests/golden/test_sources.py): fail on
      any golden source or ModelSpec reference that cites
      the CFA Program curriculum — its readings, levels,
      learning outcome statements, practice problems or mock
      exams, or a cfainstitute.org URL other than the
      Financial Analysts Journal. Papers in the Financial
      Analysts Journal (which CFA Institute publishes) are
      peer-reviewed sources and stay allowed.
    </requirement>

    <requirement>
      Markers and invariant coverage: register `invariant`
      (invariant(model_id, invariant_id)) and `oracle` in
      [tool.pytest.ini_options] markers. A meta-test
      (tests/models/test_invariant_coverage.py) scans the
      test tree with ast, so it holds whatever subset of
      tests runs, and fails when a registered model declares
      an invariant no `invariant`-marked test covers, or a
      marker names an unknown model or invariant. An
      `oracle` test compares a model with an independent
      library, and never skips: a missing oracle is an
      import error that fails the suite.
    </requirement>

    <requirement>
      tests/strategies.py: inputs(model) returns a
      hypothesis strategy of valid inputs built from the
      fields' unit markers, bounds, maximum lengths and enums,
      choosing a calculation for a union.
      Strategy-support tests search for valid witnesses to
      optional/enum choices, each union tag and declared
      examples; they do not require a finite random batch
      to happen to visit every supported branch (Step 15
      verification correction, 2026-10-14).
      tests/models/test_contract.py runs, for every
      registered model, under the `ci` profile with a
      bounded number of examples per model: outputs are
      within bounds, finite or None with a warning; the only
      exceptions are DomainError and ConvergenceError; two
      runs give identical canonical JSON; and the result's
      canonical JSON round-trips. A model whose valid inputs
      can legitimately raise DomainError documents the
      condition in its limitations.
    </requirement>

    <requirement>
      Coverage floors: scripts/checks/coverage_floors.py
      reads `coverage json` output and fails when branch
      coverage is below 95% for src/pyeconomics/core/ or
      below 90% for src/pyeconomics/models/; a package with
      no measured files passes with a note (models/ until
      Step 6). pyproject.toml's overall fail_under = 95
      stays. ci.yml's tests job writes the JSON report and
      runs the script; tests/checks/test_coverage_floors.py
      covers it.
    </requirement>

    <requirement>
      scripts/new_model.py <id>: validates the id (Step 3's
      rules), then creates
      src/pyeconomics/models/<domain>/<name>.py (headers, a
      spec skeleton that fails validate() until completed),
      tests/golden/<domain>/<name>.toml (a skeleton the
      harness rejects until completed) and
      tests/models/<domain>/test_<name>.py (an
      invariant-marked property-test skeleton); it refuses
      to overwrite and prints the entry-point line to add
      when the domain is new.
    </requirement>

    <requirement>
      CONTRIBUTING.md: under "Model definition of done", a
      "How it is checked" subsection naming validate(),
      tests/golden/ and its README, the invariant marker,
      the contract suite, the coverage floors, the citation
      guard and the scaffold.
      .github/pull_request_template.md: a "Model checklist"
      section for model pull requests — id final and in its
      domain; validate() passes; at least three cited golden
      cases with an edge case, or a recorded reason; a
      property test for each invariant; oracle tests where
      an oracle exists; every new source listed in the body;
      no curriculum content; the card renders.
    </requirement>

    <requirement>
      Tests of the harness itself use toy models
      (Registry.from_models) and golden files written to
      tmp_path: each failure rule above has a case that
      triggers it, so the harness cannot pass vacuously.
      With no catalog model registered yet, the parametrized
      golden test collects no case and says so in its skip
      reason; Step 6 adds test_registry_is_not_empty, after
      which an empty registry fails.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; TOML files `# <path>`; Markdown
      follows the docs convention. CHANGELOG [Unreleased]
      "Added" entry for the harness.
    </requirement>
  </requirements>
</task>
```

### Step 5 acceptance criteria

- `tests/golden/README.md` fixes the format, and every harness failure
  rule in this step's task has a test that triggers it with a toy model.
- The citation guard rejects curriculum sources and allows the Financial
  Analysts Journal (tested both ways).
- The `invariant` and `oracle` markers are registered, and the
  invariant-coverage meta-test fails on an uncovered invariant and on an
  unknown marker (tested with toy models).
- `tests/strategies.py` and `tests/models/test_contract.py` exercise every
  registered model (toy models in this step) for bounds, documented
  errors, determinism and round trips.
- `scripts/checks/coverage_floors.py` runs in `ci.yml`'s tests job and
  fails below 95% branch coverage on `core/` or 90% on `models/`; it has
  its own tests.
- `scripts/new_model.py` creates the three skeleton files for a new id,
  refuses to overwrite, and its skeletons fail `validate()` and the
  harness until completed.
- CONTRIBUTING and the pull request template carry the mechanics and the
  model checklist.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and fixtures are parsed with `tomllib`
  only, hold no licensed dataset, and the scaffold cannot write outside
  `src/` and `tests/`.

---

## Step 6 — Launch Catalog: Foundations ✅

**Status:** Complete — PR #79 (2026-10-10)

> **Goal:** Register the five foundations entries and prove the contract
> end to end. Add `src/pyeconomics/models/foundations/` with
> `foundations.time_value` (present and future value of sums and annuities,
> the five-key solve, NPV, IRR, XNPV, XIRR and amortization schedules),
> `foundations.returns` (holding-period, arithmetic, geometric, harmonic,
> annualized, log and real returns), `foundations.risk_statistics`
> (volatility, semideviation, skewness, excess kurtosis and maximum
> drawdown), `foundations.hypothesis_tests` (t, z, χ² and F tests with
> confidence intervals, from summary statistics) and
> `foundations.simulation` (seeded GBM Monte Carlo and the bootstrap); the
> `foundations` entry point, with the artifact allowlist admitting the
> `entry_points.txt` it adds to the wheel; reusable numerics in `core/`
> (cash-flow discounting, IRR, annuity factors, moment statistics,
> drawdown) that Steps 8–12 import; a golden file per entry under
> `tests/golden/foundations/` with
> at least three cited cases and an edge case; property tests for every
> declared invariant; and oracle tests against SciPy's independent
> routines. This is the first real use of Steps 1–5: a contract gap found
> here is an upstream gap, fixed in-step when it blocks, with the earlier
> step's prompt patched. Parent: ROADMAP §4 2.6 (`foundations`).

**Branch:** `feature/phase02-step6-foundations`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence High         |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: five
entries with exact formulas, cited golden values that must be real and
correctly located, and the first end-to-end use of a five-step contract,
where upstream gaps surface. That is High complexity, which requires S in
coding; with knowledge secondary, Opus 5.5 (S in both) outranks Sonnet 5.5
(A in knowledge) and wins the cost tie-break against Fable 5.1 (HLE
61.4%). Claude Code on the claude.ai Max plan pays for it, $0 marginal
while the weekly pool has headroom; High work keeps its place while the
pool reads `tight`. Claude Code opens on Opus 5.5 at its Medium default;
High is the raise, earned by correctness-sensitive numerics and citation
research; not Extra High, because the formulas are textbook and the
harness checks them. Thinking stays On. The backup is GPT-6 Sol on Codex
under ChatGPT Pro 5x — S in coding, winning the coverage tie-break over
GPT-6 Astra — at Intelligence High. New conversation per phase-boundary
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
       feature/phase02-step6-foundations`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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

    THIS STEP ALSO:
    - The purity guards apply from this step: the
      model-purity rule and the import allowlist must pass
      on src/pyeconomics/models/foundations/ with no
      suppression.
    - simulation is a HEAVY cost class: its paths, steps,
      resamples and sample sizes are bounded so the largest
      valid input finishes within the time budget the
      roadmap's Phase 4 inherits (record the measured worst
      case in the PR body).
    - Golden sources are cited, independent and free of CFA
      Program material; the citation guard passes.
  </security>

  <context>
    pyeconomics. Phase 2. Step 6: launch catalog,
    foundations.

    Current state (as of Phase 2 Step 5):

    - The contract is complete: conventions and dates in
      core/, @model and ModelSpec, the registry and
      validate(), run() with canonical JSON and manifests,
      schemas and cards, and the harness (golden format,
      invariant meta-test, strategies, contract suite,
      coverage floors, scaffold). No catalog model is
      registered, and no entry point exists.
    - core/numerics.py holds the bracketed root finder;
      core/compounding.py the rate conversions;
      core/daycount.py ACT_365_FIXED, which XNPV and XIRR
      use (the convention spreadsheet XNPV/XIRR functions
      use).
    - scripts/new_model.py scaffolds a model, its golden
      file and its property tests.
    - Harness facts from Step 5: tests/golden/_loader.py
      holds the rules and tests/contract.py the contract.
      A golden file's `min_cases_reason` also waives its
      edge-case requirement; a per-field `tolerance`
      replaces the unit default, and an omitted `abs` or
      `rel` is zero. The contract suite draws inputs from
      tests/strategies.py field by field, so a model with a
      rule between fields (a strike below a spot) adds a
      strategy to `strategies.OVERRIDES`; it lets
      DomainError and ConvergenceError through only for a
      model whose `limitations` are not empty, and its
      fuzz fails when valid inputs push an output past its
      own bound (the toy growth, time-value and zero-coupon
      models do, so size each output bound to the input
      bounds). Test file basenames stay unique across
      tests/ (mypy). An id `domain.family.name` uses the
      file stem `family_name`. The scaffold creates a new
      domain's `__init__.py` and prints the entry-point
      line; it never edits pyproject.toml.

    Files to read (every file before drafting):
    - This roadmap's Overview: the model contract, the
      launch-catalog table, the Contract-change and
      Citation rules.
    - docs/adr/0008-numerical-conventions.md.
    - src/pyeconomics/core/ (all modules) and
      src/pyeconomics/registry.py.
    - tests/golden/README.md, tests/strategies.py,
      tests/models/ and tests/registry/toy_models.py (the
      patterns to follow).
    - CONTRIBUTING.md "Model definition of done".
  </context>

  <goal>
    The five foundations models are registered through the
    `foundations` entry point, pass validate(), the golden
    harness, their invariant property tests, the contract
    suite and their oracle tests, render their cards, and
    run in the clean-venv and Pyodide smokes.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Package layout: src/pyeconomics/models/__init__.py
      (Step 3 added it, a docstring only, so the purity
      guards had a tree to guard) and
      src/pyeconomics/models/foundations/ with one module per
      entry and an __init__.py whose __all__ lists the five
      Models; pyproject.toml gains
      [project.entry-points."pyeconomics.models"] with
      `foundations = "pyeconomics.models.foundations"`.
      Reusable, pure numerics (cash-flow discounting, NPV,
      IRR, annuity factors, moment statistics, drawdown)
      go in core/ so later domains import them from there;
      each model module adapts them to its inputs and
      outputs.
    </requirement>

    <requirement>
      Artifact allowlist: the first entry point puts
      entry_points.txt in the wheel's dist-info, and model
      discovery reads it, so scripts/checks/dist_contents.py
      admits `pyeconomics-<version>.dist-info/entry_points.txt`
      in the wheel (and nothing else new), with a case in
      tests/checks/test_dist_contents.py. Without this the
      package job and release.yml's build job reject the
      wheel.
    </requirement>

    <requirement>
      foundations.time_value — a union on `calculation`:
      present_value and future_value (a single sum, a level
      annuity paid in arrears or in advance, a growing
      annuity, a perpetuity), solve (the five-key time-value
      equation in N, rate, PV, PMT and FV with the
      cash-flow sign convention, solving for whichever one
      is omitted), npv and irr (periodic cash flows), xnpv
      and xirr (dated cash flows, ACT_365_FIXED), and
      amortization (a level-payment schedule as arrays of
      payment, interest, principal and balance). IRR with no
      sign change returns None with a warning; several sign
      changes choose the root ADR-0008 decision 11
      documents and warn. Invariants at least:
      pv_fv_inverse, npv_zero_at_irr,
      npv_decreasing_in_rate (conventional cash flows),
      annuity_due_ratio and amortization_ends_at_zero.
      Golden sources: closed-form identities; Microsoft's
      published XIRR and XNPV function examples (cited by
      URL, values recomputed); and textbook worked examples
      recomputed independently.
    </requirement>

    <requirement>
      foundations.returns — a union on `calculation`:
      holding_period (from beginning and ending values and
      income), means (arithmetic, geometric and harmonic of a
      return series), annualized (a periodic return with an
      explicit periods_per_year), log (continuously
      compounded from simple, and back) and real (the exact
      Fisher relation). Invariants at least: means_ordering
      (harmonic ≤ geometric ≤ arithmetic for returns above
      −1), log_returns_additive and fisher_identity.
      (Patched in Step 11 under the Contract-change rule:
      the compounding of annualized lives in
      core/descriptive.py's annualized_return, which
      foundations.returns calls.)
    </requirement>

    <requirement>
      foundations.risk_statistics — from a return series
      (or, for drawdown, a value series): sample volatility
      (stating its degrees of freedom) and its annualization
      with an explicit periods_per_year, semideviation below
      the mean and below a target, adjusted skewness and
      excess kurtosis (naming the estimator, e.g. G1 and G2),
      and maximum drawdown with its peak and trough
      positions. Invariants at least:
      volatility_scale_equivariant,
      volatility_shift_invariant and
      drawdown_between_zero_and_one. Golden sources: NIST's
      Statistical Reference Datasets for univariate summary
      statistics where a dataset is small enough to inline
      (NumAcc1), hand-computable series, and identities.
      Oracle: scipy.stats' skew and kurtosis with
      bias=False.
    </requirement>

    <requirement>
      foundations.hypothesis_tests — a union on
      `calculation`, from summary statistics (sizes, means,
      standard deviations), so fixtures hold a handful of
      published values rather than datasets: one-sample t,
      two-sample t (pooled and Welch), paired t from the
      differences' summary, z for a mean with known σ, χ²
      for a variance, and F for two variances; each with the
      statistic, degrees of freedom, a p-value for the
      chosen alternative, the critical value and decision at
      α, and the confidence interval. Invariants at least:
      p_value_in_unit_interval, interval_contains_estimate
      and two_sided_p_is_twice_one_sided. Golden sources:
      the worked examples of the NIST/SEMATECH e-Handbook of
      Statistical Methods (a US-government public-domain
      work), cited by section. Oracle: scipy.stats'
      from-statistics routines where they exist.
    </requirement>

    <requirement>
      foundations.simulation — a union on `calculation`,
      cost class HEAVY, each with a seed input (ADR-0008
      decision 7):
      - gbm: initial value, drift, volatility, horizon,
        steps and paths (bounded), with optional antithetic
        variates; outputs the terminal mean and standard
        deviation, chosen percentiles, the probability of
        ending below a level, and the standard error of the
        mean;
      - bootstrap: a sample (bounded length), a statistic
        (mean, median or standard deviation), the number of
        resamples (bounded) and a confidence level; outputs
        the estimate, the bootstrap standard error and the
        percentile interval.
      Invariants at least: terminal_values_positive,
      same_seed_same_result and
      antithetic_reduces_variance (for a monotone payoff).
      Golden sources: the closed-form GBM moments (cite
      Glasserman, Monte Carlo Methods in Financial
      Engineering, 2003) checked within a stated number of
      standard errors at the fixture's seed, and Efron and
      Tibshirani (1993) for the bootstrap, recomputed.
    </requirement>

    <requirement>
      Every model: ModelSpec complete (formula, assumptions,
      limitations, at least one primary reference, evidence
      `standard`, cost class, examples, invariants,
      changelog at version 1); a golden file with at least
      three cited cases including an edge case from the
      README's categories; tests/models/foundations/ with an
      `invariant`-marked property test per invariant and
      `oracle` tests where named above. Add
      tests/models/test_registry_is_not_empty.py, so an
      empty registry now fails.
    </requirement>

    <requirement>
      Contract shakedown: when a contract gap blocks a
      model, apply the Overview's Contract-change rule — the
      smallest change, every toy and catalog test green, the
      owning step's <task> block patched in this roadmap, a
      line in the carry-over checklist, and a superseding
      ADR if an ADR-0008 decision changes — and list each in
      the PR body.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entries naming the five
      models; the PR body lists every golden source added.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 6 acceptance criteria

- `foundations.time_value`, `foundations.returns`,
  `foundations.risk_statistics`, `foundations.hypothesis_tests` and
  `foundations.simulation` are registered through the `foundations` entry
  point and `registry.validate()` passes in CI.
- Each has a golden file with at least three cited cases including an edge
  case, all passing within tolerance; each declared invariant has a
  passing `invariant`-marked property test; the named oracle tests pass.
- The contract suite fuzzes all five without an undocumented error; their
  schemas are valid 2020-12 schemas and their results round-trip.
- Branch coverage is at least 90% on `models/` and 95% on `core/`, and the
  registry-not-empty test passes.
- Each model's card renders, and `scripts/smoke.py` runs a foundations
  model in the clean-venv and Pyodide smokes, discovered through the
  wheel's `entry_points.txt`, which the artifact allowlist now admits
  (tested).
- Every contract change this step made is listed in the PR body, patched
  into its owning step's `<task>` block and recorded in the carry-over
  checklist.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the purity guards pass on
  `models/foundations/` with no suppression, every input is bounded, and
  the simulation entry's worst case is measured and recorded.

---

## Step 7 — Model Cards and Documentation Preview ✅

**Status:** Complete — PR #80 (2026-10-10)

> **Goal:** Stand up the documentation site ADR-0007 chose and publish it
> as a preview that never displaces 0.2.x. Add `docs/conf.py` (Sphinx with
> MyST-NB, sphinx-autoapi and the PyData Sphinx theme), a local extension
> `docs/_ext/model_pages.py` that writes one page per registered model
> from its `ModelCard` at build time and fails the build when the page
> count differs from the registry, and the site's pages: an index with the
> alpha-preview banner, installation (`pip install --pre`), a quickstart
> whose examples Sybil runs under pytest, a MyST-NB tutorial notebook
> executed during the build, conventions (ADR-0008 for readers), results
> and manifests, the generated model reference grouped by domain, the API
> reference, an errata page, legal notices (the CFA® marks notice and "not
> investment advice") and the changelog. Add a `docs` job to `ci.yml`
> (warnings as errors, notebooks executed) inside the `test` aggregate,
> `.readthedocs.yaml` on `main`, and Read the Docs version `main` as an
> active, non-default preview while `stable` and `latest` keep serving
> 0.2.x. Narrow Phase 1's check 19, which forbids a tracked
> `docs/conf.py`. Parent: ROADMAP §4 2.5; ADR-0007.

**Branch:** `feature/phase02-step7-docs-preview`

**Deploys:** Documentation → Read the Docs version `main` at
`https://pyeconomics.readthedocs.io/en/main/`, rebuilt on every merge to
`main`; `stable` (0.2.6) and `latest` (`legacy/0.2.x`) are unchanged.

| Setting      | Value                                           |
| ------------ | ----------------------------------------------- |
| Model        | GPT-6.1 Sol                                       |
| Backup       | Claude Sonnet 5.5 — Claude Code · Effort Medium |
| Platform     | Codex                                           |
| Intelligence | Medium                                          |
| Conversation | **New**                                         |

> Settings updated 2026-10-10: was GPT-6 Sol · Medium. GPT-6.1 Sol supersedes GPT-6 Sol; verified rollout effort medium.

**Model rationale:** Coding is PRIMARY — Sphinx configuration, a
page-generating extension, Sybil collection, a CI job and the Read the
Docs configuration — and agentic work SECONDARY: activating the preview
and verifying the deployed site. The stack is decided (ADR-0007) and every
tool is mature, so complexity is Medium, with an A floor in coding. The
claude.ai Max weekly pool reads `tight` until Tue 2026-10-13 20:00 EDT and
Codex is the lane with slack, so the operator's posture sends this
GPT-adequate Medium step to Codex on the ChatGPT Pro 5x plan, $0 marginal.
GPT-6 Sol is S in coding and agentic work and wins the coverage tie-break
over GPT-6 Astra (Terminal-Bench 4.0 43.9). Codex opens on its provider
default; set GPT-6 Sol at Intelligence Medium, the ladder value for Medium
work. The backup is Claude Sonnet 5.5 on Claude Code at Effort Medium — S
in coding and agentic work, winning the coverage tie-break over Opus 5.5.
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
       feature/phase02-step7-docs-preview`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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

    THIS STEP ALSO:
    - The docs build executes code (the tutorial notebook,
      each card's worked example, Sybil's examples): only
      this repository's own pages run, with no network
      access beyond installing pinned dependencies, and no
      secret exists in the build environment.
    - .readthedocs.yaml installs with `uv sync --locked`,
      so Read the Docs builds the audited lock, never a
      fresh resolution; it sets fail_on_warning.
    - Docs-group packages that GitHub's dependency graph
      files as runtime (certifi under MPL-2.0, docutils'
      GPL classifier and any other the scan flags) are
      exempted by purl in security.yml with a comment, only
      after the `licences` hook shows they are outside the
      runtime closure.
    - The site carries the required notices: the CFA® marks
      notice verbatim and "not investment advice".
  </security>

  <context>
    pyeconomics. Phase 2. Step 7: model cards and
    documentation preview.

    Current state (as of Phase 2 Step 6):

    - Five foundations models are registered; each spec
      renders a ModelCard (core/cards.py) to MyST Markdown
      with LaTeX formulas, a variables table, a worked
      example and references; registry.describe(id) returns
      the same content as JSON.
    - main has no Sphinx site. docs/ holds adr/, roadmap/,
      releases/ and phase01-qa-findings.md, none of which
      belongs in the site; .gitignore ignores docs/_build/.
    - Read the Docs project `pyeconomics`: default branch
      legacy/0.2.x, default version `stable` (tag v0.2.6),
      `latest` built from legacy/0.2.x with that branch's
      own .readthedocs.yml. A `main` version builds only
      once it is activated and main carries a config.
    - verify-phase01.sh static check 19 fails when
      docs/conf.py is tracked (0.2.x had one); check 38
      fails on a workflow named docs.yml or tests.yml.
    - The `docs` dependency group is empty; pytest's
      testpaths are tests and src.
    - Step 6 facts (2026-10-10): five foundations models
      are registered; tests/models/test_catalog_documents.py
      renders every installed model's card and checks its
      schemas against 2020-12, and
      tests/models/test_registry_is_not_empty.py fails an
      empty registry.

    Files to read (every file before drafting):
    - docs/adr/0007-documentation-tooling.md and this
      roadmap's Current State, Documentation surface (the
      preview mechanism this roadmap chose).
    - docs/roadmap/ROADMAP.md §4 2.5 and 5.6 and §5 "Legal
      & brand guardrails" (CFA Institute marks and the
      required notices).
    - src/pyeconomics/core/cards.py, schema.py and
      src/pyeconomics/registry.py.
    - README.md (the notices the site repeats),
      CHANGELOG.md, pyproject.toml, .gitignore,
      .github/workflows/ci.yml and security.yml.
    - scripts/verify-phase01.sh (checks 19 and 38) and the
      post-merge addendum at the end of
      docs/roadmap/phase01-roadmap.md.
    - Read the Docs' current documentation for building
      with uv in .readthedocs.yaml.
  </context>

  <goal>
    `sphinx-build -W` builds the site in CI with the
    notebook executed and one page per registered model;
    Sybil runs the Markdown examples under pytest; Read the
    Docs serves the build of main's HEAD at /en/main/ while
    /en/stable/ and /en/latest/ still serve 0.2.x; and
    verify-phase01.sh stays green with check 19 narrowed.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, one batched request to the operator: in the
      Read the Docs admin, activate version `main` (active,
      not hidden, not the default) after this PR merges, and
      leave the default branch (legacy/0.2.x) and default
      version (stable) unchanged.
    </requirement>

    <requirement>
      Dependencies: `uv add --no-config --group docs`
      sphinx, myst-nb, sphinx-autoapi and
      pydata-sphinx-theme, and `uv add --no-config --group
      test sybil`; every one installs on every CI cell and
      passes pip-audit. sphinx-gallery is not added (Phase
      5).
      Export pylock.toml with --all-groups and update the
      pylock-fresh hook's export command, so pip-audit also
      audits the code-executing docs toolchain, not only
      the default dev/test environment.
    </requirement>

    <requirement>
      docs/conf.py: MyST (dollarmath and amsmath for the
      cards' LaTeX), MyST-NB with notebook execution forced
      and an execution error failing the build,
      sphinx-autoapi over src/pyeconomics (static parsing,
      numpy-style docstrings), the PyData theme, the local
      extension, and exclude_patterns covering roadmap/,
      adr/, releases/, phase*-qa-findings.md and _build/.
      A warning silenced with suppress_warnings carries a
      comment naming why.
    </requirement>

    <requirement>
      docs/_ext/model_pages.py: on builder-inited, writes
      one MyST page per registered model from
      ModelCard.to_markdown() into the git-ignored
      docs/reference/models/<domain>/, plus a domain index
      page, and fails the build unless the number of pages
      equals len(registry.ids()) (ADR-0007's page-count
      check). Generated pages are never committed; add the
      directory to .gitignore. The module imports Sphinx
      only inside setup(), so its pure functions (writing
      the pages, checking the count) load without Sphinx:
      tests/docs/test_model_pages.py loads the module by
      path with importlib and tests them with toy
      registries, a deliberate count mismatch included, in
      the ordinary tests job.
    </requirement>

    <requirement>
      Pages: index.md (what 1.0 is, the alpha-preview banner,
      a link to 0.2.x's documentation on /en/stable/),
      installation.md, quickstart.md (examples run by
      Sybil), tutorials/first-model.md (a MyST-NB text
      notebook that runs a foundations model, renders its
      card and converts the result to pandas), conventions.md
      (ADR-0008 for readers: decimals, units, compounding,
      day counts, tolerances, seeds), results.md (Result,
      manifest, canonical JSON), the generated model
      reference, the autoapi reference, errata.md ("No
      errata yet", and how a model error is reported and
      recorded), notices.md (the CFA® marks notice verbatim
      from ROADMAP §5, "As is; not investment advice", and
      the Apache-2.0 licence) and changelog.md (including
      ../CHANGELOG.md). The theme's footer links notices.md
      on every page.
    </requirement>

    <requirement>
      Sybil: docs/conftest.py collects doctest-style and
      Python code-block examples from the site's own pages
      only (never roadmap/, adr/, releases/ or the QA
      findings), and pyproject.toml's testpaths gain docs so
      `uv run pytest` runs them. docs/conftest.py also lists
      conf.py and _ext/ in collect_ignore: with
      --doctest-modules, pytest would otherwise import them
      in the tests job, which installs no docs group.
    </requirement>

    <requirement>
      CI: a `docs` job in ci.yml (ubuntu-latest, harden-runner
      first, contents: read, SHA-pinned actions,
      persist-credentials: false) that runs `uv run --locked
      --group docs --all-extras sphinx-build -W --keep-going
      -b html docs docs/_build/html`, added to the `test`
      aggregate's needs. Never name a workflow docs.yml
      (verify-phase01.sh check 38).
    </requirement>

    <requirement>
      .readthedocs.yaml on main: build.os and Python pinned,
      uv installed at the version CI pins, the environment
      built with `uv sync --locked --group docs --all-extras`
      into Read the Docs' virtualenv path, sphinx
      configuration docs/conf.py with fail_on_warning: true.
      The file's name differs from legacy/0.2.x's
      .readthedocs.yml, which keeps building `stable` and
      `latest`.
    </requirement>

    <requirement>
      Cross-phase verification rule: narrow
      verify-phase01.sh static check 19 so docs/conf.py
      fails only when it is 0.2.x's (for example, when it
      names the 0.2.x package layout or lacks the 1.0
      extensions), keep its number and intent, and add a
      line to the post-merge addendum in
      docs/roadmap/phase01-roadmap.md.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entry for the
      documentation preview; the PR body states the
      preview's URL and how Read the Docs was configured.
    </requirement>

    <requirement>
      Filepath comment: docs/conf.py, docs/conftest.py and
      docs/_ext/model_pages.py get the three-line header;
      .readthedocs.yaml and workflow edits `# <path>`;
      Markdown pages follow the docs convention.
    </requirement>
  </requirements>
</task>
```

### Step 7 acceptance criteria

- `sphinx-build -W --keep-going` succeeds in the `docs` job with the
  tutorial notebook executed, and `tests/docs/test_model_pages.py` shows
  the page-count check failing on a deliberate mismatch (in the tests job,
  without Sphinx).
- One generated page per registered model exists in the built site, each
  rendering the card's formula, variables, worked example and references;
  no generated page is tracked.
- Sybil collects and passes the site's examples under `uv run pytest`,
  and collects nothing from `roadmap/`, `adr/` or `releases/`.
- The `docs` job is in the `test` aggregate's needs; no workflow is named
  `docs.yml` or `tests.yml`.
- `notices.md` carries the CFA® marks notice verbatim and "not investment
  advice", and every page links it.
- `verify-phase01.sh --fast` passes with check 19 narrowed, and the
  post-merge addendum names the change.
- **Deployed & verified:** the Read the Docs API shows version `main`
  active and not default, with its latest build passed for `main`'s merge
  commit; `https://pyeconomics.readthedocs.io/en/main/` answers 200 and
  shows the 1.0 preview with a page for each registered model; `/en/stable/`
  still serves 0.2.6 and `/en/latest/` still builds `legacy/0.2.x`.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the docs build installs only the
  locked environment, executes only this repository's pages, and every
  dependency-review exemption names its reason.

---

## Step 8 — Launch Catalog: Fixed Income ✅

**Status:** Complete — PR #82 (2026-10-10)

> **Goal:** Register the six fixed-income entries on Step 2's date layer.
> Add `src/pyeconomics/models/fixed_income/` with
> `fixed_income.bond_pricing` (full and flat price and accrued interest
> from yield, yield to maturity from price, yield to call and yield to
> worst over a call schedule), `fixed_income.money_market` (discount,
> money-market, bond-equivalent, effective annual and holding-period
> yields), `fixed_income.curve_bootstrap` (spot rates, discount factors,
> par and forward rates by bootstrapping), `fixed_income.duration`
> (Macaulay, modified, effective and key-rate durations and DV01),
> `fixed_income.convexity` (analytical and effective convexity and the
> price-change approximation) and `fixed_income.credit_spread` (expected
> loss, spread and hazard rate, survival and spread return); the
> `fixed_income` entry point; golden files citing the US Treasury's own
> worked examples (31 CFR Part 356, Appendix B, a public-domain work),
> identities and recomputed textbook values; property tests for every
> invariant; and QuantLib oracle tests for prices, yields, accrued
> interest, durations, convexity and bootstrapped curves. Parent: ROADMAP
> §4 2.6 (`fixed_income`).

**Branch:** `feature/phase02-step8-fixed-income`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence High         |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: bond math
is where conventions bite — street-convention yields with fractional first
periods, accrued interest by day count, yield to worst over a call
schedule, bootstrapped curves and key-rate durations — and every golden
value must come from an official or cited source. High complexity requires
S in coding; with knowledge secondary, Opus 5.5 (S in both) outranks Sonnet
5.5 (A in knowledge) and wins the cost tie-break against Fable 5.1 (HLE
61.4%). Claude Code on the claude.ai Max plan pays for it, $0 marginal
while the weekly pool has headroom; High work keeps its place while the
pool reads `tight`. Claude Code opens on Opus 5.5 at its Medium default;
High is the raise for correctness-sensitive, multi-convention numerics;
not Extra High, because the formulas are textbook and QuantLib checks
them. Thinking stays On. The backup is GPT-6 Sol on Codex under ChatGPT Pro
5x — S in coding, winning the coverage tie-break over GPT-6 Astra — at
Intelligence High. New conversation per phase-boundary hygiene.

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
       feature/phase02-step8-fixed-income`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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
    - The purity guards pass on
      src/pyeconomics/models/fixed_income/ with no
      suppression; dates are inputs, never "today".
    - Every array input (cash flows, call schedules, curve
      tenors) has a maximum length, and every iterative
      solver an iteration cap, so no input is an unbounded
      workload.
    - Golden values from the US Treasury and textbooks are
      cited with locators; no licensed market data (no
      vendor prices or curves) enters a fixture.
  </security>

  <context>
    pyeconomics. Phase 2. Step 8: launch catalog, fixed
    income.

    Current state (as of Phase 2 Step 7):

    - The contract and harness are proven on five
      foundations models; the docs preview builds a page
      per model; core/ holds the conventions, the date
      layer (DayCount, year_fraction, schedules, calendars)
      and the reusable cash-flow numerics Step 6 added.
    - QuantLib is in the test group (Step 2), with abi3
      wheels for every CI cell.
    - Each new model is held by validate(), the golden
      harness, the invariant meta-test, the contract
      suite, the coverage floors and the docs build's page
      count.
    - Step 6 facts (2026-10-10): core/cashflows.py
      (growth, annuity and perpetuity factors,
      present_value, internal_rate_of_return under
      IRR_POLICY, sign_changes) and core/descriptive.py
      (sample_mean and _variance, semideviations,
      sample_moments' G1 and G2, max_drawdown) are the
      shared numerics; reuse them. Where compounding makes
      an output's bounds impossible to size to the inputs,
      models/foundations/_common.py's bounded() raises
      DomainError, listed in limitations. A rule between
      fields is a model_validator plus a
      tests/strategies.py OVERRIDES entry built from its
      _one_omitted and _same_length helpers. Invariant and
      oracle markers take string literals, never a
      constant (the meta-test reads them with ast). Import
      scipy.stats inside compute: discovery imports every
      models module. gitleaks' generic-api-key rule flags
      long snake_case Reference keys (joanes_gill1998):
      keep keys short; never allowlist. The contract
      suite's 50/25/10 draws missed four boundary defects
      the Step 6 review found (an output rounding past
      its bound, NaN from an overflowing exponent, an
      underflowing variance): before the PR, run
      contract.check_model(model, max_examples=1500) on
      each new model and have an independent reviewer
      read the diff.

    Files to read (every file before drafting):
    - This roadmap's Overview (model contract, catalog
      table, Contract-change and Citation rules).
    - docs/adr/0008-numerical-conventions.md (decisions 3,
      4, 5, 10 and 11).
    - src/pyeconomics/core/ (daycount, schedule,
      compounding, numerics and the cash-flow helpers) and
      src/pyeconomics/models/foundations/ (the patterns).
    - tests/golden/README.md, tests/models/foundations/ and
      tests/unit/core/test_daycount.py.
    - 31 CFR Part 356, Appendix B (Treasury's price and
      yield formulas and worked examples), on ecfr.gov.
  </context>

  <goal>
    The six fixed-income models are registered through the
    `fixed_income` entry point and pass validate(), the
    golden harness, their invariant property tests, the
    contract suite and their QuantLib oracle tests, and
    their pages render in the docs preview.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Package and entry point: src/pyeconomics/models/
      fixed_income/ with one module per entry and an
      __init__.py whose __all__ lists the six Models;
      `fixed_income = "pyeconomics.models.fixed_income"` in
      the entry-point table. Bond cash-flow generation from
      terms (settlement, maturity, coupon rate, frequency,
      day count, face value, redemption) is a shared, pure
      helper inside the fixed_income package; general
      discounting and curve interpolation go in core/, where
      Step 9's swap valuation reuses them without importing
      another domain (Step 3's import allowlist).
    </requirement>

    <requirement>
      fixed_income.bond_pricing — a union on `calculation`:
      price_from_yield (full price, flat price and accrued
      interest at settlement, street convention with a
      fractional first period), yield_from_price (from full
      or flat price), yield_to_call (one call date and
      price) and yield_to_worst (the minimum over a bounded
      call schedule and maturity, naming the date that
      yields it). Regular coupons and a short or long first
      period are in scope. Invariants at least:
      price_decreases_with_yield, par_bond_prices_at_par (on
      a coupon date), full_equals_flat_plus_accrued and
      yield_to_worst_not_above_yield_to_maturity. Golden
      sources: 31 CFR Part 356 Appendix B's note and bond
      examples, identities, recomputed textbook cases.
      Oracle: QuantLib's FixedRateBond (clean and dirty
      price, accrued amount, yield).
    </requirement>

    <requirement>
      fixed_income.money_market — a union on `calculation`:
      discount yield to and from price (ACT/360), the
      money-market (CD-equivalent) yield, the
      bond-equivalent yield or investment rate (with
      Treasury's formula for bills longer than half a year),
      the effective annual yield and the holding-period
      yield. Invariants at least:
      discount_yield_below_investment_rate (positive
      rates), price_below_face_for_positive_yield and
      price_yield_round_trip. Golden sources: 31 CFR Part 356
      Appendix B's bill examples, and a published Treasury
      bill auction result (its discount rate, investment
      rate and price per $100) cited by auction date and
      CUSIP.
    </requirement>

    <requirement>
      fixed_income.curve_bootstrap — a union on
      `calculation`: from_par (par yields at regular tenors
      to spot rates, discount factors and one-period
      forwards), from_spot (spot rates to par yields and
      forwards) and forward_rate (between two maturities),
      with compounding and frequency from ADR-0008.
      Invariants at least: flat_curve_is_invariant,
      bootstrapped_curve_reprices_par_bonds,
      forwards_compose_to_spots and
      discount_factors_positive. Golden sources: identities
      and a recomputed textbook bootstrap. Oracle: a
      QuantLib curve built from the same instruments.
    </requirement>

    <requirement>
      fixed_income.duration — a union on `calculation`:
      macaulay_modified (from bond terms and yield),
      effective (central bump and reprice, bump size an
      input), key_rate (triangular shifts of a spot curve
      at key tenors) and dv01 (money duration per 0.0001).
      Invariants at least:
      zero_coupon_macaulay_equals_maturity,
      modified_equals_macaulay_over_periodic_factor,
      key_rates_sum_to_effective (for shifts spanning the
      curve), duration_falls_as_coupon_rises and
      dv01_positive. Golden sources: Macaulay (1938) for the
      definition, identities, recomputed textbook cases.
      Oracle: QuantLib's BondFunctions duration.
    </requirement>

    <requirement>
      fixed_income.convexity — a union on `calculation`:
      analytical, effective (bump and reprice) and
      price_change (the duration-and-convexity estimate of a
      yield change beside full repricing and their
      difference). Invariants at least:
      convexity_positive_for_option_free_bonds,
      approximation_error_is_third_order and the
      zero-coupon closed form. Oracle: QuantLib's
      BondFunctions convexity.
    </requirement>

    <requirement>
      fixed_income.credit_spread — a union on
      `calculation`: expected_loss (probability of default ×
      loss given default × exposure), hazard_from_spread and
      spread_from_hazard (the credit-triangle relation under
      continuous compounding, stating its assumption),
      survival (survival and cumulative default
      probabilities over a horizon) and spread_return (carry
      less spread duration × spread change less expected
      loss). Invariants at least: spread_hazard_round_trip,
      survival_decreases_with_horizon and
      expected_loss_within_exposure. Golden sources:
      identities and recomputed textbook examples.
    </requirement>

    <requirement>
      Every model: ModelSpec complete (evidence `standard`
      unless a convention is a rule of thumb, cost class,
      examples, invariants, changelog at version 1), a golden
      file with at least three cited cases and an edge case
      (a negative yield, a zero coupon, a maturity of 50
      years or more, settlement on a coupon date),
      `invariant`-marked property tests, and `oracle` tests
      in tests/models/fixed_income/.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entries naming the six
      models; the PR body lists every golden source.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 8 acceptance criteria

- The six `fixed_income.*` ids in the launch-catalog table are registered
  through the `fixed_income` entry point, and `registry.validate()` passes
  in CI.
- Each has a golden file with at least three cited cases including an edge
  case, all passing within tolerance; the Treasury cases reproduce 31 CFR
  Part 356 Appendix B's published values at their published precision.
- Every declared invariant has a passing `invariant`-marked property test,
  and the QuantLib oracle tests pass for prices, accrued interest, yields,
  durations, convexity and bootstrapped curves.
- The contract suite fuzzes all six without an undocumented error, the
  coverage floors hold, and the docs preview renders their pages.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the purity guards pass on
  `models/fixed_income/`, every array input and solver is bounded, and no
  vendor market data is in a fixture.

---

## Step 9 — Launch Catalog: Derivatives and International ✅

**Status:** Complete — PR #84 (2026-10-11)

> **Goal:** Register the five derivatives entries and the international
> parity entry. Add `src/pyeconomics/models/derivatives/` with
> `derivatives.forwards` (cost-of-carry forward prices and values, and FX
> forwards by covered interest parity), `derivatives.interest_rate_swap`
> (swap value, par swap rate and annuity factor from discount factors),
> `derivatives.black_scholes_merton` (European prices with a continuous
> dividend yield, the Greeks, implied volatility and the put-call parity
> check), `derivatives.binomial_tree` (CRR trees for European and
> American options) and `derivatives.futures_fx_options` (Black-76 and
> Garman-Kohlhagen, with Greeks and implied volatility), and
> `src/pyeconomics/models/international/` with
> `international.parity_conditions` (covered and uncovered interest parity,
> relative and absolute PPP, the international Fisher effect and real
> exchange rates); the `derivatives` and `international` entry points;
> golden files from the originating papers and recomputed textbook
> examples; property tests for every invariant, cross-entry consistency
> tests, and oracle tests against QuantLib and vollib. Parent: ROADMAP §4
> 2.6 (`derivatives`, `international`).

**Branch:** `feature/phase02-step9-derivatives`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence High         |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: closed-form
option pricing with a full set of Greeks, a robust implied-volatility
solver, American early exercise on a tree, swap valuation and parity
relations, each tied to its originating paper and checked against two
independent libraries. High complexity requires S in coding; with
knowledge secondary, Opus 5.5 (S in both) outranks Sonnet 5.5 (A in
knowledge) and wins the cost tie-break against Fable 5.1 (HLE 61.4%).
Claude Code on the claude.ai Max plan pays for it, $0 marginal while the
weekly pool has headroom; High work keeps its place while the pool reads
`tight`. Claude Code opens on Opus 5.5 at its Medium default; High is the
raise for numerics where a sign or carry error is silent; not Extra High,
because the formulas are standard and the oracles check them. Thinking
stays On. The backup is GPT-6 Sol on Codex under ChatGPT Pro 5x — S in
coding, winning the coverage tie-break over GPT-6 Astra — at Intelligence
High. New conversation per phase-boundary hygiene.

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
       feature/phase02-step9-derivatives`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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
    - vollib joins the test group: it and its closure pass
      pip-audit and install on every CI cell; a dependency
      that dependency-review flags is exempted by purl with
      a comment only after the `licences` hook shows it is
      outside the runtime closure.
    - The purity guards pass on models/derivatives/ and
      models/international/; the implied-volatility solver
      and the tree have bounded iterations and steps.
    - The option models are impersonal formula calculators:
      no card or output frames a result as a trade
      recommendation (ROADMAP §5 "Legal & brand
      guardrails", adviser posture).
  </security>

  <context>
    pyeconomics. Phase 2. Step 9: launch catalog,
    derivatives and international.

    Current state (as of Phase 2 Step 8):

    - Eleven models are registered (foundations and fixed
      income). fixed_income.curve_bootstrap produces
      discount factors and forwards; core/ holds the
      bracketed root finder, compounding conversions and
      the date layer.
    - QuantLib is the test oracle (abi3 wheels); vollib is
      not yet a dependency.
    - The harness, invariant meta-test, contract suite,
      coverage floors and docs page count hold every new
      model.
    - Step 6 facts (2026-10-10): core/cashflows.py
      (growth, annuity and perpetuity factors,
      present_value, internal_rate_of_return under
      IRR_POLICY, sign_changes) and core/descriptive.py
      (sample_mean and _variance, semideviations,
      sample_moments' G1 and G2, max_drawdown) are the
      shared numerics; reuse them. Where compounding makes
      an output's bounds impossible to size to the inputs,
      models/foundations/_common.py's bounded() raises
      DomainError, listed in limitations. A rule between
      fields is a model_validator plus a
      tests/strategies.py OVERRIDES entry built from its
      _one_omitted and _same_length helpers. Invariant and
      oracle markers take string literals, never a
      constant (the meta-test reads them with ast). Import
      scipy.stats inside compute: discovery imports every
      models module. gitleaks' generic-api-key rule flags
      long snake_case Reference keys (joanes_gill1998):
      keep keys short; never allowlist. The contract
      suite's 50/25/10 draws missed four boundary defects
      the Step 6 review found (an output rounding past
      its bound, NaN from an overflowing exponent, an
      underflowing variance): before the PR, run
      contract.check_model(model, max_examples=1500) on
      each new model and have an independent reviewer
      read the diff.
    - Step 8 facts (2026-10-10): core/curves.py holds
      interpolate_rate and interpolate_rates (linear in zero
      rates, flat beyond the nodes; the second checks the
      nodes once for many times), curve_discount_factors,
      forward_rate (in log space; its
      frequency is keyword-only) and par_rate, (1 - d_n) /
      sum(alpha_i d_i), which is also a par swap rate: reuse
      them for swap valuation. A date field needs both ge
      and le (validate()'s field-bounds rule). A numeric
      Literal passes validate() but fails the schema test
      (issue #81): use a unit-typed field with bounds.
      QuantLib's dates run from 1901 to 2199, and its bond
      functions time the first payment as the period less
      the part accrued, which differs from a direct count
      under 30/360. When inputs must agree across fields,
      the tests/strategies.py _accepts(cls) filter keeps a
      composite draw valid; tests/fixed_income_draws.py
      builds the same bond in QuantLib. A DomainError branch
      no valid input reaches is dead code: size the bound
      instead (a bond priced at -10% for a century stays
      below 1e15).

    Files to read (every file before drafting):
    - This roadmap's Overview (model contract, catalog
      table, Contract-change and Citation rules).
    - docs/adr/0008-numerical-conventions.md (decisions 3,
      4, 10 and 11).
    - src/pyeconomics/core/ (the discounting and curve
      helpers Step 8 placed there, to reuse; a domain never
      imports another domain's package) and
      src/pyeconomics/models/fixed_income/ (the patterns).
    - tests/golden/README.md and tests/models/fixed_income/
      (the patterns).
    - QuantLib's Python documentation for
      AnalyticEuropeanEngine, BinomialVanillaEngine,
      blackFormula, GarmanKohlagenProcess and VanillaSwap,
      and vollib's implied-volatility API.
  </context>

  <goal>
    The six models are registered through the
    `derivatives` and `international` entry points and pass
    validate(), the golden harness, their invariant property
    tests, the cross-entry consistency tests, the contract
    suite and their QuantLib and vollib oracle tests.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Packages and entry points: src/pyeconomics/models/
      derivatives/ and international/, each with one module
      per entry and an __init__.py whose __all__ lists its
      Models; `derivatives = "pyeconomics.models.derivatives"`
      and `international = "pyeconomics.models.international"`
      in the entry-point table. `uv add --no-config --group
      test vollib`. FX quotes are units of the quote
      currency per unit of the base currency, stated in every
      FX field's description.
    </requirement>

    <requirement>
      derivatives.forwards — a union on `calculation`:
      cost_of_carry (forward price with income yield,
      storage and convenience yield under continuous
      compounding, or discrete known income), forward_value
      (the value of an existing long or short forward), and
      fx_forward (covered interest parity with
      money-market compounding and each currency's day
      count, and the forward points). Invariants at least:
      forward_value_zero_at_inception and
      fx_forward_matches_parity. Golden sources: identities
      and recomputed textbook examples.
    </requirement>

    <requirement>
      derivatives.interest_rate_swap — from discount factors
      or a zero curve and a payment schedule (accrual
      fractions or dates with a day count): the value to the
      fixed payer and receiver, the par swap rate (one minus
      the final discount factor over the annuity) and the
      annuity factor. Invariants at least:
      value_zero_at_par_rate,
      payer_and_receiver_values_offset and
      value_linear_in_notional. Oracle: QuantLib's
      VanillaSwap on a flat curve.
    </requirement>

    <requirement>
      derivatives.black_scholes_merton — European calls and
      puts with a continuous dividend yield (Black and
      Scholes 1973; Merton 1973): price, delta, gamma, vega,
      theta, rho and dividend rho, a put-call parity residual,
      and an implied_volatility calculation with a bracketed
      solver over a bounded volatility range that returns
      None with a warning when the price is outside the
      no-arbitrage bounds. Invariants at least:
      put_call_parity, price_within_no_arbitrage_bounds,
      gamma_and_vega_nonnegative,
      call_increases_with_spot and
      implied_volatility_round_trip. Golden sources: the
      original papers' formulas, recomputed textbook
      examples (published to two decimals, tolerance to
      match), identities. Oracles: QuantLib's
      AnalyticEuropeanEngine for prices and Greeks; vollib
      for implied volatility.
    </requirement>

    <requirement>
      derivatives.binomial_tree — Cox, Ross and Rubinstein
      (1979): European and American calls and puts with a
      continuous dividend yield, steps bounded (cost class
      LIGHT up to the bound), with price, delta and gamma
      from the tree. Invariants at least:
      american_put_at_least_european,
      american_call_equals_european_without_dividends,
      european_parity_holds and
      converges_to_black_scholes (European, error falling as
      steps grow). Golden sources: a recomputed textbook
      American-put tree and identities. Oracle: QuantLib's
      BinomialVanillaEngine with the CRR tree.
    </requirement>

    <requirement>
      derivatives.futures_fx_options — a union on
      `calculation`: black_76 (options on futures and
      forwards; Black 1976) and garman_kohlhagen (FX
      options; Garman and Kohlhagen 1983), each with price,
      Greeks (foreign rho for FX) and implied volatility.
      Invariants at least: black_76_equals_bsm_with_carry_zero
      and garman_kohlhagen_equals_bsm_with_foreign_yield
      (cross-entry tests against
      derivatives.black_scholes_merton), and put_call_parity.
      Golden sources: the original papers' formulas and
      recomputed textbook examples. Oracles: QuantLib's
      blackFormula and Garman-Kohlhagen process.
    </requirement>

    <requirement>
      international.parity_conditions — a union on
      `calculation`: covered_interest_parity (forward rate
      and premium), uncovered_interest_parity (expected
      spot), relative_ppp and absolute_ppp,
      international_fisher, and real_exchange_rate (level
      and change). A spec carries one evidence status: use
      `standard`, because the relations are textbook
      consensus as formulas (ROADMAP §5 classes the CAPM
      formula the same way), and state in the limitations
      that uncovered parity and PPP fail empirically over
      short horizons while covered parity holds up to
      transaction costs. Invariants at least:
      parity_forward_matches_derivatives_forwards (a
      cross-entry test with derivatives.forwards) and
      real_rate_identity.
    </requirement>

    <requirement>
      Every model: ModelSpec complete, a golden file with at
      least three cited cases and an edge case (a zero or
      negative rate, a volatility of 2.0 or more, a very
      short or very long expiry, deep in or out of the
      money), `invariant`-marked property tests, and
      `oracle` tests in tests/models/derivatives/ and
      tests/models/international/. Cards state that results
      are formula outputs for the inputs given, not trading
      advice.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entries naming the six
      models; the PR body lists every golden source.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 9 acceptance criteria

- The five `derivatives.*` ids and `international.parity_conditions` are
  registered through their entry points, and `registry.validate()` passes
  in CI.
- Each has a golden file with at least three cited cases including an edge
  case, all passing within tolerance.
- Every declared invariant has a passing `invariant`-marked property test;
  the cross-entry tests (Black-76 and Garman-Kohlhagen against BSM, the
  parity forward against `derivatives.forwards`) pass; the QuantLib and
  vollib oracle tests pass.
- Implied volatility round-trips across the bounded volatility range and
  returns None with a warning outside the no-arbitrage bounds.
- The contract suite fuzzes all six without an undocumented error, the
  coverage floors hold, and the docs preview renders their pages.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and vollib's closure is audited, the
  purity guards pass on both packages, and every solver and tree is
  bounded.

---

## Step 10 — Launch Catalog: Equity, Corporate and Accounting ✅

**Status:** Complete — PR #86 (2026-10-11)

> **Goal:** Register the seven valuation, corporate-finance and accounting
> entries. Add `equity.dividend_discount` (Gordon growth, two-stage, the
> H-model, PVGO and the implied required return), `equity.free_cash_flow`
> (FCFF and FCFE from their components, and one- and two-stage valuation
> of the firm and its equity), `corporate.cost_of_capital` (CAPM, WACC,
> Hamada unlevering and relevering, and a country risk premium),
> `corporate.capital_budgeting` (NPV, IRR, MIRR, payback, discounted
> payback, the profitability index and the equivalent annual annuity, on
> Step 6's cash-flow numerics), `corporate.leverage` (DOL, DFL, DTL and
> breakeven quantities), `accounting.financial_ratios` (liquidity,
> activity, solvency and profitability ratios, and the three- and
> five-step DuPont decompositions) and `accounting.scoring_models` (Altman
> Z, Beneish M and Piotroski F), in three new domain packages with their
> entry points, golden files, property tests and an identity check per
> decomposition. Parent: ROADMAP §4 2.6 (`equity`, `corporate`,
> `accounting`).

**Branch:** `feature/phase02-step10-equity-corporate-accounting`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | GPT-6.1 Sol                                   |
| Backup       | Claude Opus 5.5 — Claude Code · Effort Medium |
| Platform     | Codex                                         |
| Intelligence | Medium                                        |
| Conversation | **New**                                       |

> Settings updated 2026-10-11: was GPT-6 Sol · Medium. GPT-6.1 Sol supersedes it on Codex; session effort Medium.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: seven
closed-form entries whose formulas are short and well documented, reusing
Step 6's discounting and IRR, with the knowledge load in choosing and
stating ratio definitions and citing the originating papers. Ambiguity and
novelty are low and the contract is settled, so complexity is Medium, with
an A floor in coding, though seven golden sets make the step long. The
claude.ai Max weekly pool reads `tight` until Tue 2026-10-13 20:00 EDT and
Codex is the lane with slack, so the operator's posture sends this
GPT-adequate Medium step to Codex on the ChatGPT Pro 5x plan, $0 marginal.
GPT-6 Sol is S in coding and wins the coverage tie-break over GPT-6 Astra
(SciCode 57.6). Codex opens on its provider default; set GPT-6 Sol at
Intelligence Medium, the ladder value for Medium work. The backup is Claude
Opus 5.5 on Claude Code at Effort Medium, its default, S in coding and
knowledge. New conversation per phase-boundary hygiene.

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
       feature/phase02-step10-equity-corporate-accounting`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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
    - The purity guards pass on models/equity/,
      models/corporate/ and models/accounting/ with no
      suppression; financial-statement inputs are bounded
      money fields.
    - Scores and valuations are impersonal formula outputs:
      no card frames a zone, a value or a score as a buy,
      sell or credit recommendation (ROADMAP §5 adviser
      posture).
    - Coefficients come from the original papers, cited;
      no proprietary scoring service or licensed dataset is
      used.
  </security>

  <context>
    pyeconomics. Phase 2. Step 10: launch catalog, equity,
    corporate and accounting.

    Current state (as of Phase 2 Step 9):

    - Seventeen models are registered (foundations, fixed
      income, derivatives, international). core/ holds the
      reusable cash-flow numerics (NPV, IRR, annuity
      factors) Step 6 added and the root finder.
    - The harness, invariant meta-test, contract suite,
      coverage floors and docs page count hold every new
      model.
    - Step 6 facts (2026-10-10): core/cashflows.py
      (growth, annuity and perpetuity factors,
      present_value, internal_rate_of_return under
      IRR_POLICY, sign_changes) and core/descriptive.py
      (sample_mean and _variance, semideviations,
      sample_moments' G1 and G2, max_drawdown) are the
      shared numerics; reuse them. Where compounding makes
      an output's bounds impossible to size to the inputs,
      models/foundations/_common.py's bounded() raises
      DomainError, listed in limitations. A rule between
      fields is a model_validator plus a
      tests/strategies.py OVERRIDES entry built from its
      _one_omitted and _same_length helpers. Invariant and
      oracle markers take string literals, never a
      constant (the meta-test reads them with ast). Import
      scipy.stats inside compute: discovery imports every
      models module. gitleaks' generic-api-key rule flags
      long snake_case Reference keys (joanes_gill1998):
      keep keys short; never allowlist. The contract
      suite's 50/25/10 draws missed four boundary defects
      the Step 6 review found (an output rounding past
      its bound, NaN from an overflowing exponent, an
      underflowing variance): before the PR, run
      contract.check_model(model, max_examples=1500) on
      each new model and have an independent reviewer
      read the diff.
    - Step 9 facts (2026-10-11): a model whose input is a
      single class (not a union) must not give that class
      a docstring, or the input schema's description
      replaces the summary and test_schema fails (issue
      #83). run_model records warnings in Result.warnings;
      an outer collect_warnings() sees none. In property
      tests, discard a documented DomainError with
      hypothesis' reject() (assume(False) trips FBT003),
      and make many-argument @given tests keyword-only
      (PLR0917). models/derivatives/_options.py holds a
      bounded() like foundations' (a domain never imports
      another's). Size Greek-like bounds from the inputs'
      extremes and widen a unit default with a comment
      (ADR-0008 decision 3). QuantLib 1.43's binomial
      engine can price an American option below its own
      European; its FD engine is the sound American
      oracle.

    Files to read (every file before drafting):
    - This roadmap's Overview (model contract, catalog
      table, Contract-change and Citation rules).
    - docs/adr/0008-numerical-conventions.md (decisions 2,
      3, 10 and 11).
    - src/pyeconomics/core/ (cash-flow numerics, root
      finder) and src/pyeconomics/models/foundations/
      time_value (the IRR and NPV conventions to match).
    - tests/golden/README.md and tests/models/foundations/
      (the patterns).
  </context>

  <goal>
    The seven models are registered through the `equity`,
    `corporate` and `accounting` entry points and pass
    validate(), the golden harness, their invariant
    property tests and the contract suite, and their pages
    render in the docs preview.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Packages and entry points: src/pyeconomics/models/
      equity/, corporate/ and accounting/, each with one
      module per entry and an __init__.py whose __all__
      lists its Models; `equity`, `corporate` and
      `accounting` lines in the entry-point table.
    </requirement>

    <requirement>
      equity.dividend_discount — a union on `calculation`:
      gordon (Gordon 1959, 1962: value from next dividend,
      required return and growth, a DomainError when the
      return does not exceed growth), two_stage, h_model
      (Fuller and Hsia 1984), pvgo (value split into
      no-growth value and present value of growth
      opportunities) and implied_return. Invariants at
      least: two_stage_reduces_to_gordon (equal growth
      rates), h_model_reduces_to_gordon (zero half-life) and
      value_decreases_with_required_return.
    </requirement>

    <requirement>
      equity.free_cash_flow — a union on `calculation`:
      fcff and fcfe from their components (stating the
      formula variant in the card), and valuation (one- and
      two-stage firm value at the WACC and equity value at
      the cost of equity, with equity equal to firm value
      less net debt). Invariants at least:
      fcfe_equals_fcff_less_after_tax_interest_plus_net_borrowing
      and single_stage_matches_gordon_form.
    </requirement>

    <requirement>
      corporate.cost_of_capital — a union on `calculation`:
      capm (Sharpe 1964; Lintner 1965), wacc (with the tax
      shield on debt and an optional preferred tranche),
      unlever_beta and relever_beta (Hamada 1972), and
      country_risk_premium (sovereign spread scaled by the
      ratio of equity to bond volatility, citing its
      source). Invariants at least:
      unlever_relever_round_trip,
      wacc_between_component_costs and
      capm_linear_in_beta.
    </requirement>

    <requirement>
      corporate.capital_budgeting — from a project's cash
      flows: NPV, IRR, MIRR (finance and reinvestment
      rates), payback and discounted payback (fractional,
      None with a warning when never reached), the
      profitability index and the equivalent annual
      annuity. NPV and IRR call core/'s cash-flow numerics,
      so they agree exactly with foundations.time_value
      (a cross-entry test). Invariants at least:
      npv_positive_iff_pi_above_one,
      mirr_between_reinvestment_rate_and_irr
      (conventional cash flows) and
      discounted_payback_not_shorter_than_payback.
    </requirement>

    <requirement>
      corporate.leverage — DOL, DFL, DTL and the operating
      and total breakeven quantities from price, variable
      cost, fixed costs, interest and quantity; a measure
      that is undefined at the inputs (DOL and DTL at zero
      operating income) is None with a warning, the others
      still returned (ADR-0008 decision 10). Invariants at
      least: dtl_equals_dol_times_dfl and
      dol_above_one_with_fixed_costs.
    </requirement>

    <requirement>
      accounting.financial_ratios — from financial-statement
      line items (bounded money fields, one currency):
      liquidity (current, quick, cash), activity
      (receivables, inventory and payables turnover and
      days, asset turnover), solvency (debt-to-equity,
      debt-to-assets, interest coverage, financial
      leverage), profitability (gross, operating and net
      margins, ROA, ROE), and the three- and five-step
      DuPont decompositions. The card defines every ratio
      and notes where definitions vary between sources.
      Invariants at least: dupont_three_step_equals_roe and
      dupont_five_step_equals_roe. The cash conversion cycle
      is a Phase 7 entry and is not added.
    </requirement>

    <requirement>
      accounting.scoring_models — a union on `calculation`:
      altman_z (Altman 1968, the original public
      manufacturing model, with its zone cut-offs),
      beneish_m (Beneish 1999, eight variables) and
      piotroski_f (Piotroski 2000, nine binary signals),
      each with its component values. Evidence
      `practitioner`; the limitations state each model's
      sample and period. Invariants at least:
      z_score_linear_in_ratios, f_score_between_zero_and_nine
      and m_score_matches_coefficients (an identity on unit
      inputs).
    </requirement>

    <requirement>
      Every model: ModelSpec complete, a golden file with at
      least three cited cases and an edge case (zero growth,
      a return barely above growth, a project never paying
      back, a ratio with a zero denominator returning None
      with a warning),
      and `invariant`-marked property tests in
      tests/models/<domain>/. Golden sources: identities,
      the originating papers' coefficients and examples,
      published spreadsheet-function examples (for MIRR),
      and recomputed textbook values.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entries naming the seven
      models; the PR body lists every golden source.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 10 acceptance criteria

- The seven `equity.*`, `corporate.*` and `accounting.*` ids in the
  launch-catalog table are registered through their entry points, and
  `registry.validate()` passes in CI.
- Each has a golden file with at least three cited cases including an edge
  case, all passing within tolerance.
- Every declared invariant has a passing `invariant`-marked property test,
  including the DuPont identities, and capital budgeting's NPV and IRR
  agree exactly with `foundations.time_value` (cross-entry test).
- The contract suite fuzzes all seven without an undocumented error, the
  coverage floors hold, and the docs preview renders their pages.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the purity guards pass on the three
  packages, every statement input is bounded, and no card frames a score
  or value as a recommendation.

---

## Step 11 — Launch Catalog: Portfolio and Performance ✅

**Status:** Complete — PR #87 (2026-10-11)

> **Goal:** Register the two portfolio and three performance entries. Add
> `portfolio.mean_variance` (portfolio return and risk, the closed-form
> efficient frontier with short sales allowed, and the minimum-variance
> and tangency portfolios), `portfolio.utility` (mean-variance utility, the
> optimal risky share, the certainty equivalent and the Kelly fraction),
> `performance.return_measurement` (time-weighted and money-weighted
> returns and Modified Dietz), `performance.risk_adjusted` (Sharpe,
> Sortino, Treynor, Jensen's alpha, information ratio and tracking error,
> M², Calmar and capture ratios) and `performance.brinson_attribution`
> (Brinson-Hood-Beebower and Brinson-Fachler effects, single-period and
> linked over periods with Carino's method), in two new domain packages
> with their entry points, golden files, property tests, identity checks
> that attribution effects sum to the active return, and an independent
> numerical check of the minimum-variance portfolio. Parent: ROADMAP §4
> 2.6 (`portfolio`, `performance`).

**Branch:** `feature/phase02-step11-portfolio-performance`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence High         |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: matrix
closed forms for the frontier, a dozen performance ratios whose definitions
differ between sources and must each be stated and cited, and multi-period
attribution linking whose effects must still sum exactly. High complexity
requires S in coding; with knowledge secondary, Opus 5.5 (S in both)
outranks Sonnet 5.5 (A in knowledge) and wins the cost tie-break against
Fable 5.1 (HLE 61.4%). Claude Code on the claude.ai Max plan pays for it,
$0 marginal while the weekly pool has headroom; High work keeps its place
while the pool reads `tight`. Claude Code opens on Opus 5.5 at its Medium
default; High is the raise for definitional precision and linking
identities; not Extra High, because each formula is published and the
identities check it. Thinking stays On. The backup is GPT-6 Sol on Codex
under ChatGPT Pro 5x — S in coding, winning the coverage tie-break over
GPT-6 Astra — at Intelligence High. New conversation per phase-boundary
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
       feature/phase02-step11-portfolio-performance`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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
    - Adviser posture (ROADMAP §5 "Legal & brand
      guardrails"): frontier, tangency, optimal-share and
      Kelly outputs are formula results for the parameters
      the user supplies, the same for every user; cards say
      so and never call a portfolio "recommended".
    - Matrix inputs are bounded (assets, periods, sectors),
      the covariance matrix is checked symmetric and
      positive definite, and no solver runs unbounded.
    - empyrical-reloaded, if added, joins the test group
      only, after its closure passes pip-audit and installs
      on every CI cell.
  </security>

  <context>
    pyeconomics. Phase 2. Step 11: launch catalog,
    portfolio and performance.

    Current state (as of Phase 2 Step 10):

    - Twenty-four models are registered. core/ holds the
      cash-flow numerics (NPV, IRR) and moment statistics
      Step 6 added; foundations.risk_statistics computes
      maximum drawdown; foundations.returns the return
      means and annualization.
    - The harness, invariant meta-test, contract suite,
      coverage floors and docs page count hold every new
      model.
    - Step 6 facts (2026-10-10): core/cashflows.py
      (growth, annuity and perpetuity factors,
      present_value, internal_rate_of_return under
      IRR_POLICY, sign_changes) and core/descriptive.py
      (sample_mean and _variance, semideviations,
      sample_moments' G1 and G2, max_drawdown) are the
      shared numerics; reuse them. Where compounding makes
      an output's bounds impossible to size to the inputs,
      models/foundations/_common.py's bounded() raises
      DomainError, listed in limitations. A rule between
      fields is a model_validator plus a
      tests/strategies.py OVERRIDES entry built from its
      _one_omitted and _same_length helpers. Invariant and
      oracle markers take string literals, never a
      constant (the meta-test reads them with ast). Import
      scipy.stats inside compute: discovery imports every
      models module. gitleaks' generic-api-key rule flags
      long snake_case Reference keys (joanes_gill1998):
      keep keys short; never allowlist. The contract
      suite's 50/25/10 draws missed four boundary defects
      the Step 6 review found (an output rounding past
      its bound, NaN from an overflowing exponent, an
      underflowing variance): before the PR, run
      contract.check_model(model, max_examples=1500) on
      each new model and have an independent reviewer
      read the diff.

    Files to read (every file before drafting):
    - This roadmap's Overview (model contract, catalog
      table, Contract-change and Citation rules).
    - docs/roadmap/ROADMAP.md §5 "Legal & brand guardrails"
      (the adviser-posture table) and §4 7.2–7.3 (what
      Phase 7 adds: constrained optimization, other linking
      methods).
    - docs/adr/0008-numerical-conventions.md (decisions 3,
      4, 8 and 10).
    - src/pyeconomics/core/ and
      src/pyeconomics/models/foundations/ (returns,
      risk_statistics, time_value).
    - tests/golden/README.md and tests/models/foundations/.
  </context>

  <goal>
    The five models are registered through the `portfolio`
    and `performance` entry points and pass validate(), the
    golden harness, their invariant property tests, the
    attribution identities and the contract suite, and
    their pages render in the docs preview.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Packages and entry points: src/pyeconomics/models/
      portfolio/ and performance/, each with one module per
      entry and an __init__.py whose __all__ lists its
      Models; `portfolio` and `performance` lines in the
      entry-point table. Drawdown and return statistics come
      from core/; a helper Step 6 left inside a model module
      moves to core/ under the Contract-change rule.
    </requirement>

    <requirement>
      portfolio.mean_variance — a union on `calculation`:
      portfolio (expected return, variance and volatility
      from weights and either a covariance matrix or
      volatilities and correlations), frontier (Merton
      1972's closed form with short sales allowed, a
      bounded number of points), minimum_variance and
      tangency (with a risk-free rate, and the capital
      market line's slope). A covariance matrix that is not
      symmetric positive definite is a DomainError.
      Invariants at least: weights_sum_to_one,
      minimum_variance_has_lowest_variance,
      frontier_variance_quadratic_in_return and
      tangency_maximizes_sharpe. Golden sources: Markowitz
      (1952) and Merton (1972) closed forms, recomputed
      two- and three-asset examples. Oracle:
      scipy.optimize's constrained minimizer finds the same
      minimum-variance weights. Long-only and other
      constrained optimization stay in Phase 7.
    </requirement>

    <requirement>
      portfolio.utility — a union on `calculation`:
      mean_variance_utility, optimal_risky_share,
      certainty_equivalent and kelly (the discrete-bet
      fraction from win probability and odds, the
      continuous fraction from drift, rate and volatility,
      and a fractional multiplier). Invariants at least:
      utility_falls_as_aversion_rises,
      optimal_share_inverse_in_aversion and
      kelly_zero_without_edge. Golden sources: Kelly (1956),
      identities and recomputed textbook values.
    </requirement>

    <requirement>
      performance.return_measurement — a union on
      `calculation`: time_weighted (sub-period returns from
      valuations around external flows, linked
      geometrically), money_weighted (the IRR of the flows,
      periodic or dated, through core/'s numerics) and
      modified_dietz (day-weighted flows: the refinement of
      Dietz's 1966 midpoint method, as Bacon 2008 ch. 2
      sets it out; spec corrected in Step 11), each
      optionally annualized with an explicit
      periods_per_year. Invariants at least:
      time_and_money_weighted_agree_without_flows and
      modified_dietz_equals_simple_return_without_flows.
    </requirement>

    <requirement>
      performance.risk_adjusted — from portfolio,
      benchmark and risk-free series with an explicit
      periods_per_year: Sharpe (Sharpe 1966, 1994), Sortino
      (Sortino and Price 1994, stating the minimum
      acceptable return and downside-deviation convention),
      Treynor (1965), Jensen's alpha (1968), information
      ratio and tracking error, M² (Modigliani and
      Modigliani 1997), Calmar (annualized return over
      maximum drawdown) and up- and down-capture ratios. A
      zero denominator returns None with a warning
      (ADR-0008 decision 10). Invariants at least:
      sharpe_invariant_to_positive_scaling,
      tracking_error_zero_for_identical_series and
      capture_ratios_one_for_identical_series. Oracle:
      empyrical-reloaded for the ratios it implements, added
      to the test group only when its closure (bottleneck,
      peewee) installs on every CI cell; otherwise those
      cases use values recomputed independently, and the PR
      body and the QA findings record the substitution.
    </requirement>

    <requirement>
      performance.brinson_attribution — a union on
      `calculation`: bhb (Brinson, Hood and Beebower 1986:
      allocation, selection and interaction) and
      brinson_fachler (Brinson and Fachler 1985: allocation
      against the total benchmark return), each from bounded
      arrays of sector weights and returns per period,
      single-period and linked across periods with Carino's
      (1999) logarithmic method. Invariants at least:
      effects_sum_to_active_return (each period),
      linked_effects_sum_to_geometric_active_return and
      zero_effects_for_identical_portfolios. Other linking
      methods (Menchero, GRAP) stay in Phase 7.
    </requirement>

    <requirement>
      Every model: ModelSpec complete, a golden file with at
      least three cited cases and an edge case (no external
      flows, a single period, zero volatility, negative
      returns, identical portfolio and benchmark), and
      `invariant`-marked property tests and the named
      oracle tests in tests/models/portfolio/ and
      tests/models/performance/. Cards of the two portfolio
      entries state that outputs follow from the user's
      inputs and are not investment advice.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entries naming the five
      models; the PR body lists every golden source and the
      empyrical-reloaded decision.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 11 acceptance criteria

- The two `portfolio.*` and three `performance.*` ids in the
  launch-catalog table are registered through their entry points, and
  `registry.validate()` passes in CI.
- Each has a golden file with at least three cited cases including an edge
  case, all passing within tolerance.
- Every declared invariant has a passing `invariant`-marked property test;
  attribution effects sum to the active return each period and, linked, to
  the geometric active return; the minimum-variance oracle agrees.
- The empyrical-reloaded decision (oracle added, or recomputed values) is
  recorded in the PR body and carried to the QA findings.
- The contract suite fuzzes all five without an undocumented error, the
  coverage floors hold, and the docs preview renders their pages.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and every matrix input is bounded and
  validated, and no portfolio output is framed as a recommendation.

---

## Step 12 — Launch Catalog: Risk and Econometrics ✅

**Status:** Complete — PR #88 (2026-10-12)

> **Goal:** Register the last three entries and fill the first extra a
> model's computation needs. Add
> `risk.value_at_risk` (VaR and expected shortfall by the parametric,
> Cornish-Fisher, historical, Monte Carlo and EWMA methods),
> `risk.var_backtest` (Kupiec's proportion-of-failures test,
> Christoffersen's independence and conditional-coverage tests, and the
> Basel traffic light) and `econometrics.ols` (OLS with classical, HC0–HC3
> and HAC standard errors and the 0.2.x diagnostics — Breusch-Pagan,
> Durbin-Watson, normality, Ramsey RESET and VIF — over statsmodels behind
> the `[econometrics]` extra), in two new domain packages with their entry
> points; golden files including NIST's certified regression results and
> the Basel Committee's published zones; an independent NumPy check of
> every robust covariance and diagnostic; and a smoke that proves both
> paths of the extra: `econometrics.ols` names `pyeconomics[econometrics]`
> when statsmodels is absent and runs when it is present. The catalog is
> then complete at 32 entries. Parent: ROADMAP §4 2.6 (`risk`,
> `econometrics`); ADR-0002.

**Branch:** `feature/phase02-step12-risk-econometrics`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6 Sol — Codex · Intelligence High         |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: five VaR
methods with expected shortfall and their conventions (sign, horizon,
interpolation), likelihood-ratio backtests and the Basel zones, a
regression adapter whose robust covariances and diagnostics must match
independent computations, and the first extra a model's computation
needs, with both install paths proven. High complexity requires S in
coding; with knowledge
secondary, Opus 5.5 (S in both) outranks Sonnet 5.5 (A in knowledge) and
wins the cost tie-break against Fable 5.1 (HLE 61.4%). Claude Code on the
claude.ai Max plan pays for it, $0 marginal while the weekly pool has
headroom; High work keeps its place while the pool reads `tight`. Claude
Code opens on Opus 5.5 at its Medium default; High is the raise for
statistical conventions where a silent choice changes the number; not
Extra High, because every method is published and checked independently.
Thinking stays On. The backup is GPT-6 Sol on Codex under ChatGPT Pro 5x —
S in coding, winning the coverage tie-break over GPT-6 Astra — at
Intelligence High. New conversation per phase-boundary hygiene.

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
       feature/phase02-step12-risk-econometrics`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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
       complete. You can now move
       on to Step 13." That
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
       one before Step 13.
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
    - statsmodels joins the `econometrics` extra: its
      closure passes pip-audit and the `licences` hook (the
      `licences` hook syncs every extra), with a reviewed
      exception for any package it fails (patsy's
      `2-clause BSD` metadata is expected), and installs on
      every CI cell, Python 3.15 included once issue #65
      lands.
    - statsmodels is imported lazily inside compute only;
      the import allowlist admits it for
      models/econometrics/ alone.
    - Regression inputs are bounded (rows, columns, lags),
      Monte Carlo VaR (cost class HEAVY) bounds its
      simulations, and the NIST datasets in fixtures are
      small US-government public-domain works.
  </security>

  <context>
    pyeconomics. Phase 2. Step 12: launch catalog, risk
    and econometrics.

    Current state (as of Phase 2 Step 11):

    - Twenty-nine models are registered.
      foundations.simulation provides seeded generation and
      foundations.risk_statistics the moment estimators,
      through core/; foundations.hypothesis_tests uses
      SciPy's χ² distribution.
    - The `econometrics` extra exists as an empty list (ADR-
      0002); ci.yml's tests job syncs every extra;
      scripts/smoke.py runs one model per domain without
      extras in the package and pyodide jobs, and
      release-smoke.yml runs it against every release.
    - The import allowlist (tests/registry/
      test_model_imports.py) admits an extra's library only
      lazily and per domain.
    - Step 6 facts (2026-10-10): core/cashflows.py
      (growth, annuity and perpetuity factors,
      present_value, internal_rate_of_return under
      IRR_POLICY, sign_changes) and core/descriptive.py
      (sample_mean and _variance, semideviations,
      sample_moments' G1 and G2, max_drawdown) are the
      shared numerics; reuse them. Where compounding makes
      an output's bounds impossible to size to the inputs,
      models/foundations/_common.py's bounded() raises
      DomainError, listed in limitations. A rule between
      fields is a model_validator plus a
      tests/strategies.py OVERRIDES entry built from its
      _one_omitted and _same_length helpers. Invariant and
      oracle markers take string literals, never a
      constant (the meta-test reads them with ast). Import
      scipy.stats inside compute: discovery imports every
      models module. gitleaks' generic-api-key rule flags
      long snake_case Reference keys (joanes_gill1998):
      keep keys short; never allowlist. The contract
      suite's 50/25/10 draws missed four boundary defects
      the Step 6 review found (an output rounding past
      its bound, NaN from an overflowing exponent, an
      underflowing variance): before the PR, run
      contract.check_model(model, max_examples=1500) on
      each new model and have an independent reviewer
      read the diff.
    - Step 11 facts (2026-10-11): core/descriptive.py
      adds compound_return, annualized_return (both return
      infinity on overflow) and has_spread (more than
      rounding error, the zero-volatility test for a
      ratio's null). A matrix input is a tuple of rows,
      each row Annotated with Field(max_length=...), the
      outer field bounded too; a BeforeValidator in the
      domain's _common.py turns a 2-D NumPy array or a
      DataFrame into rows (portfolio/_common.py has the
      covariance version, with its symmetric
      positive-definite check, which raises DomainError).
      Models may not import across domains, so each
      domain keeps its own _common.py. A field another
      field makes required stays Optional and the compute
      reads it with typing.cast, which mypy and ty both
      accept. Ruff's ERA001 reads a header path such as
      `# .../return_measurement.py` as code: exempt the
      file in pyproject.toml, as foundations/returns.py is.
      The contract strategies draw at most 12 items, so a
      model that compounds over a series never meets the
      overflow or the rounding to -100% that hundreds of
      periods reach: the Step 11 review found four such
      defects at 1,500 draws. Give such a model's
      OVERRIDES entry long-series and extreme-run draws
      (tests/strategies.py's _LONG and _EXTREME_RUN), and
      annualize from core's log_return, never from a
      compound return.

    Files to read (every file before drafting):
    - This roadmap's Overview (model contract, catalog
      table, Dependency, Contract-change and Citation
      rules).
    - docs/adr/0002-distributions-and-extras.md and
      docs/adr/0008-numerical-conventions.md.
    - docs/roadmap/ROADMAP.md §2 (the 0.2.x diagnostics) and
      §4 7.3 ("wrap, don't rewrite").
    - src/pyeconomics/core/, src/pyeconomics/models/
      foundations/ (simulation, risk_statistics,
      hypothesis_tests) and scripts/smoke.py.
    - .github/workflows/ci.yml (package job) and
      release-smoke.yml.
    - NIST's Statistical Reference Datasets for linear
      regression (Norris, Pontius, Longley, Wampler1 and
      Wampler2): data and certified values.
  </context>

  <goal>
    The three models are registered through the `risk` and
    `econometrics` entry points and pass validate(), the
    golden harness, their invariant property tests, the
    independent NumPy checks and the contract suite; the
    `econometrics` extra installs and runs, and its absence
    is reported by name; validate() sees 32 models.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Packages and entry points: src/pyeconomics/models/
      risk/ and econometrics/, each with an __init__.py
      whose __all__ lists its Models; `risk` and
      `econometrics` lines in the entry-point table.
    </requirement>

    <requirement>
      risk.value_at_risk — a union on `calculation`, VaR and
      expected shortfall reported as positive losses (as
      decimals of position value, and as money when a
      position value is given), for a confidence level and a
      horizon: parametric (normal, square-root-of-time
      scaling stated as an i.i.d. assumption),
      cornish_fisher (Zangari 1996's modified VaR from
      skewness and excess kurtosis, and the matching
      modified ES of Boudt, Peterson and Croux 2008),
      historical (the empirical quantile of a return series
      with its interpolation rule stated; ES as the mean
      loss beyond VaR), monte_carlo (seeded, normal or
      Student-t, bounded simulations, cost class HEAVY, with
      the standard error) and ewma (J.P. Morgan and Reuters'
      RiskMetrics Technical Document 1996, decay 0.94 by
      default, volatility forecast and normal VaR and ES).
      Invariants at least: es_at_least_var,
      var_increases_with_confidence,
      parametric_var_scales_with_sqrt_horizon and
      cornish_fisher_reduces_to_normal (zero skewness and
      excess kurtosis). Golden sources: normal-quantile
      identities, the RiskMetrics Technical Document,
      recomputed textbook values, and the Basel Committee's
      2019 market-risk framework for the 97.5% ES against
      99% VaR comparison.
    </requirement>

    <requirement>
      risk.var_backtest — a union on `calculation`, from a
      bounded series of exceptions (or of P&L and VaR):
      kupiec (Kupiec 1995's proportion-of-failures
      likelihood ratio with its χ²(1) p-value, using 0·log 0
      = 0 for zero exceptions), christoffersen
      (Christoffersen 1998's independence and conditional
      coverage ratios) and basel_traffic_light (the zone and
      plus factor for 250 observations at 99% from the Basel
      Committee's 1996 backtesting framework, Table 2, and,
      for other sizes, the cumulative-binomial thresholds the
      framework defines). Invariants at least:
      likelihood_ratios_nonnegative,
      conditional_coverage_is_sum_of_parts and
      traffic_light_monotone_in_exceptions.
    </requirement>

    <requirement>
      econometrics.ols — `uv add --no-config --optional
      econometrics statsmodels` and `uv add --no-config
      --group test statsmodels` (Dependency rule), and add
      econometrics to the `all` extra; the spec sets
      `extra="econometrics"`, and a narrow mypy override
      covers statsmodels if it ships no type information.
      Inputs: a bounded response array, a
      bounded design table with column names, whether to add
      a constant, the covariance type (nonrobust, HC0, HC1,
      HC2, HC3 or HAC with a bounded lag count) and α.
      Outputs: coefficients, standard errors, t statistics,
      p-values and confidence intervals per regressor; R²,
      adjusted R², the F statistic and its p-value, the
      residual standard error and degrees of freedom; and
      the 0.2.x diagnostics: Durbin-Watson, Breusch-Pagan,
      Jarque-Bera and omnibus normality, Ramsey RESET and a
      VIF per regressor; a residuals-against-fitted ChartSpec
      for Result.plot(). statsmodels is imported inside
      compute; without it, the model raises
      MissingOptionalDependencyError naming
      `pyeconomics[econometrics]`. Golden sources: NIST's
      certified coefficients, standard errors, residual
      standard deviation and R² for Norris, Pontius,
      Longley, Wampler1 and Wampler2, inlined (each is a
      few dozen rows of public-domain data) with tolerances
      no tighter than statsmodels attains. Oracle tests
      recompute HC0–HC3 (MacKinnon and White 1985), HAC with
      Bartlett weights (Newey and West 1987) and every
      diagnostic independently with NumPy. Invariants at
      least: residuals_orthogonal_to_regressors,
      r_squared_in_unit_interval and
      coefficients_invariant_to_row_order.
    </requirement>

    <requirement>
      Both paths of the extra:
      - tests simulate statsmodels' absence and assert the
        error names the extra, and that validate() still
        passes (Step 3's rule for an absent extra);
      - scripts/smoke.py, by Step 4's rule, covers the
        econometrics domain in an extra-less environment by
        asserting that error, counts it toward
        --min-domains, and with `--extras` runs
        econometrics.ols to outputs;
      - ci.yml's package job adds a second clean venv with
        the wheel and its `econometrics` and `plot` extras
        and runs `scripts/smoke.py --extras` there;
      - release-smoke.yml, after the no-extras smoke,
        installs the `econometrics` extra's requirements
        from PyPI (read from the installed metadata) and
        runs `scripts/smoke.py --extras`.
    </requirement>

    <requirement>
      Every model: ModelSpec complete, a golden file with at
      least three cited cases and an edge case (zero
      exceptions, all exceptions, a confidence level near
      its bound, a perfectly collinear design rejected as a
      DomainError, the smallest valid sample), and
      `invariant`-marked property tests and `oracle` tests
      in tests/models/risk/ and tests/models/econometrics/.
    </requirement>

    <requirement>
      Catalog complete: a test asserts that the registry
      holds exactly the 32 ids in this roadmap's
      launch-catalog table (a later phase replaces it with
      "at least"), and docs build with 32 model pages.
      CHANGELOG [Unreleased] "Added" entries naming the
      three models and the econometrics extra; the PR body
      lists every golden source and licence exception.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 12 acceptance criteria

- `risk.value_at_risk`, `risk.var_backtest` and `econometrics.ols` are
  registered through their entry points; the registry holds exactly the
  32 launch-catalog ids, and `registry.validate()` passes in CI.
- Each has a golden file with at least three cited cases including an edge
  case; `econometrics.ols` reproduces NIST's certified values for Norris,
  Pontius, Longley, Wampler1 and Wampler2 within its stated tolerances, and
  `basel_traffic_light` reproduces the Basel Committee's published zones
  and plus factors.
- Every declared invariant has a passing `invariant`-marked property test,
  and the independent NumPy checks of HC0–HC3, HAC and every diagnostic
  pass.
- The `econometrics` extra names statsmodels and `all` includes it; its
  closure passes the `licences` hook (with any reviewed exception) and
  pip-audit on every CI cell.
- Without statsmodels, `econometrics.ols` raises
  `MissingOptionalDependencyError` naming `pyeconomics[econometrics]`, and
  `registry.validate()` and the extra-less smokes (package job, `pyodide`
  job) still pass with the econometrics domain covered by that error; with
  the extra it runs, in the package job's second clean venv and in
  `release-smoke.yml`'s extras pass.
- The contract suite fuzzes all three, the coverage floors hold, and the
  docs build renders 32 model pages.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and statsmodels is imported only lazily
  inside `econometrics.ols`, every regression and simulation input is
  bounded, and the extra's licence review is in the PR.

---

## Step 13 — 1.0.0a1 Readiness Gate ✅

**Status:** Complete — PR #93 (2026-10-12)

> **Goal:** Decide, with evidence, that publishing `1.0.0a1` to PyPI is
> safe — the first irreversible upload of 1.0, which ROADMAP §5 "Promotion
> path and cutovers" gives its own readiness-gate step. Rehearse the exact
> candidate: tag `main`'s HEAD `v1.0.0a1.devN` (the version `main` has
> carried since Step 1) and let `release.yml` publish it to TestPyPI with
> attestations and run the extended smoke. Add
> `scripts/checks/python_floor.py`, the ADR-0010 re-check of NumPy's and
> SciPy's `requires_python`, with tests. Write
> `docs/releases/1.0.0a1-readiness.md` and fill every section from
> commands run in this step: the catalog audit, access control, the
> rehearsal, the artifacts and their metadata, dependencies and the Python
> floor, the version and milestone tag, documentation and release notes,
> monitoring, the rollback procedure, attribution and legal, and the
> maintainer's recorded GO or NO-GO. Nothing reaches PyPI. Parent: ROADMAP
> §5 "Promotion path and cutovers" and §4 2.7; ADR-0003 and ADR-0010.

**Branch:** `feature/phase02-step13-release-gate`

**Deploys:** TestPyPI — `pyeconomics 1.0.0a1.devN`, tagged on `main`'s
HEAD at kickoff and published through `release.yml`'s `testpypi`
environment; the readiness document lands on merge; nothing reaches PyPI.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | GPT-6.1 Sol                                   |
| Backup       | Claude Opus 5.5 — Claude Code · Effort Medium |
| Platform     | Codex                                         |
| Intelligence | Medium                                        |
| Conversation | **New**                                       |

**Model rationale:** Knowledge is PRIMARY — an evidenced checklist an
irreversible upload is judged against, an artifact and metadata review, the
ADR-0010 floor re-check — and agentic work SECONDARY: the TestPyPI
rehearsal and its verification commands. Phase 1's 0.2.6 gate is the
pattern and the GO or NO-GO is the maintainer's, so complexity is Medium,
with an A floor in knowledge. The claude.ai Max weekly pool reads `tight`
until Tue 2026-10-13 20:00 EDT and Codex is the lane with slack, so the
operator's posture sends this GPT-adequate Medium step to Codex on the
ChatGPT Pro 5x plan, $0 marginal. GPT-6.1 Sol and GPT-6 Sol tie on every
rating (A in knowledge, S in agentic work), on coverage and on price;
GPT-6.1 Sol is the newer model with the higher AA Intelligence Index
(51.8). Codex opens on its provider default; set GPT-6.1 Sol at
Intelligence Medium, the ladder value for Medium work. The backup is Claude
Opus 5.5 on Claude Code at Effort Medium, its default, the cheapest catalog
model rated S in knowledge. New conversation per phase-boundary hygiene.

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
       feature/phase02-step13-release-gate`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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
       shape "Step 13 is
       complete. You can now move
       on to Step 14." That
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
       one before Step 14.
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
    - The rehearsal publishes through Trusted Publishing
      only: no token is created, stored or printed, and the
      tag push is the maintainer's approved action.
    - The readiness document records commands and results,
      never a token, a secret value or an environment
      listing; screenshots with personal data are not
      committed.
    - python_floor.py reads public PyPI JSON over HTTPS
      with a timeout, only when run by hand or by
      verify-phase02.sh --live; its tests use recorded
      responses with sockets disabled.
  </security>

  <context>
    pyeconomics. Phase 2. Step 13: 1.0.0a1 readiness gate.

    Gate attempt 2026-10-12 found release blocker #89:
    US 30/360 long-first coupon timing disagrees with
    QuantLib and fails the duration oracle. Python 3.15
    became final on 2026-10-09, so policy issue #65 is due.
    Do not reuse the candidate after a numerical fix:
    bump .devN and rehearse again. The first attempt's
    readiness draft records evidence and pending decisions;
    the maintainer approved NO-GO on 2026-10-12 and
    instructed the agent to implement the recommendations.
    Remediation: PR #91 corrects #89 in model version 2
    and dev2; PR #92 adds final Python 3.15 support for
    #65 and advances the candidate to dev3. Confirm both
    are merged, then run a fresh gate and rehearsal;
    preserve the rejected dev1 evidence. On 2026-10-12,
    the maintainer explicitly requested continuing this
    conversation. The fresh dev3 rehearsal is tag
    v1.0.0a1.dev3 at d697b0daffd3fd3c9e437a5c1fffe23eef5c5193;
    release run 38278124628 passed on TestPyPI.

    Current state (as of Phase 2 Step 12):

    - The catalog is complete: 32 models registered,
      validate(), the golden harness, invariant coverage,
      the contract suite and the coverage floors green; the
      docs preview renders 32 model pages on Read the Docs
      `main`.
    - main's version is 1.0.0a1.dev1 (Step 1), or a later
      .devN if a fix branch bumped it, and no
      v1.0.0a1.dev* tag exists for it. release.yml routes a
      .devN tag on main to TestPyPI through `testpypi`;
      release-smoke.yml runs scripts/smoke.py with
      --min-domains 11 and the extras pass.
    - Phase 1's precedent is docs/releases/
      0.2.6-readiness.md: numbered sections, each item with
      its command, its result and PASS or FAIL, ending in
      the maintainer's Decision line.
    - Step 12 facts (2026-10-12): the `econometrics` extra is
      statsmodels>=0.15.0, whose closure adds patsy (a
      reviewed licence exception), formulaic, interface-meta,
      wrapt and narwhals; `all` includes it. ci.yml's package
      job smokes the wheel twice, without extras (--all
      --min-domains 11, econometrics.ols covered by its
      MissingOptionalDependencyError) and in a second clean
      venv with [econometrics,plot] (--extras); the pyodide
      job runs --min-domains 11. release-smoke.yml's extras
      pass reads the requirements marked `extra ==
      "econometrics"` from the installed metadata and
      installs them from PyPI, so the TestPyPI rehearsal
      must show both passes green. statsmodels resets its
      own warning categories to "always", which bypasses
      pytest's warnings-as-errors: test_ols.py records
      warnings to prove none escapes the model.

    Files to read (every file before drafting):
    - docs/releases/0.2.6-readiness.md (the structure to
      follow).
    - docs/roadmap/ROADMAP.md §5 "Release & deployment
      strategy" (surfaces, cutovers, rollback) and
      "Release & tagging".
    - docs/adr/0003-versioning-and-deprecation.md (the
      milestone table) and 0010-python-support-policy.md
      (the floor rule).
    - .github/workflows/release.yml and release-smoke.yml,
      scripts/checks/dist_contents.py and scripts/smoke.py.
    - pyproject.toml, README.md, CHANGELOG.md and
      CITATION.cff.
  </context>

  <goal>
    The rehearsal is on TestPyPI with attestations and
    passes the smoke with and without extras;
    docs/releases/1.0.0a1-readiness.md is on main with every
    section evidenced and a GO or NO-GO line the maintainer
    wrote or approved; and python_floor.py exists with tests
    and has been run.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, one batched request to the maintainer: approve
      the tag push of v1.0.0a1.devN on origin/main's HEAD,
      confirm on PyPI and TestPyPI that the trusted
      publishers match release.yml and its environments,
      that no API token exists and that 2FA is on, and
      confirm GitHub emails failed workflow runs to them.
      After Stage 1, tag origin/main's HEAD (`git tag
      v1.0.0a1.devN origin/main`, then push the tag) and
      watch the release run.
    </requirement>

    <requirement>
      scripts/checks/python_floor.py: fetches the newest
      NumPy and SciPy releases' `requires_python` from PyPI's
      JSON API (HTTPS, timeout), computes the higher floor,
      compares it with pyproject.toml's `requires-python`,
      and exits 1 when the floor moved, naming what to raise
      (ADR-0010). tests/checks/test_python_floor.py covers
      it with recorded responses. Run it and record the
      result.
    </requirement>

    <requirement>
      Create docs/releases/1.0.0a1-readiness.md with eleven
      numbered sections — Catalog audit, Access control,
      Rehearsal, Artifacts, Dependencies and Python floor,
      Version and tag, Documentation and release notes,
      Monitoring, Rollback, Attribution and legal, Decision
      — where every item records the command run, the
      observed result, and PASS or FAIL.
    </requirement>

    <requirement>
      Catalog audit: validate() on the installed registry;
      the 32 ids against this roadmap's launch-catalog
      table; for each model, its card, golden case count
      and edge case, invariant coverage and oracle tests (a
      table); the coverage floors; the citation guard; and a
      read of five sampled cards against ROADMAP §5 "CFA
      Institute marks and content" (no curriculum text, no
      "official" or "approved" claims).
    </requirement>

    <requirement>
      Access control: `gh api` reads of the `pypi` and
      `testpypi` environments (reviewers, tag policy) and
      the `release-tags` ruleset; `gh secret list` (empty);
      main's protection and required checks; the operator's
      confirmations from the kickoff.
    </requirement>

    <requirement>
      Rehearsal: the release run's URL and its jobs (verify,
      build, publish-testpypi, smoke) green; TestPyPI's JSON
      for the version lists two files, and its integrity API
      returns a provenance for each; a clean venv made with
      `uv venv --no-config` installs the version from TestPyPI
      with `--no-deps --no-config`, its dependencies from
      PyPI, and runs `scripts/smoke.py --all` from outside
      the checkout, then `--extras` after installing the
      `econometrics` and `plot` extras' requirements; the
      `pyodide` job is green on the tagged commit.
    </requirement>

    <requirement>
      Artifacts: the wheel and sdist member lists against
      scripts/checks/dist_contents.py; the wheel is
      py3-none-any; METADATA's Requires-Python,
      Requires-Dist (the runtime set, the `plot` and
      `econometrics` extras, no URL and no non-PyPI package),
      Provides-Extra and licence fields; `twine check
      --strict`. List the differences the release commit will
      add to this artifact — the version, the Development
      Status classifier (3 - Alpha), the README banner,
      CHANGELOG, CITATION.cff, the release notes, the
      released-id ledger, NOTICE if the maintainer's
      decision below adds attributions, and requires-python
      with the classifiers if the floor moved — and nothing
      else; Step 14 verifies that list.
    </requirement>

    <requirement>
      Dependencies and Python floor: pip-audit over
      pylock.toml; the `licences` hook with each reviewed
      exception listed; open Dependabot alerts on main
      (none); python_floor.py's result, and if the floor
      moved, the change Step 14 makes (requires-python, the
      CI matrix, the classifiers, and verify-phase01.sh
      checks 21 and 35, per the Cross-phase verification
      rule).
    </requirement>

    <requirement>
      Version and tag: v1.0.0a1 is Phase 2's milestone in
      ADR-0003's table; release.yml's verify job accepts it
      and routes it to `pypi`; a pre-release is installed
      only with --pre or an exact pin, so plain
      `pip install pyeconomics` keeps resolving 0.2.6 (cite
      pip's documentation; Step 14 verifies on PyPI).
    </requirement>

    <requirement>
      Documentation and release notes: the Read the Docs
      API shows `main` built from main's HEAD and `stable`
      and `latest` unchanged; draft docs/releases/1.0.0a1.md
      (what the alpha contains, the 32 models by domain, the
      install command, the docs preview link, known
      limitations, and that pre-releases carry no stability
      promise under ADR-0003) for Step 14 to publish.
    </requirement>

    <requirement>
      Monitoring and rollback: the smoke's coverage (one
      model per domain, both extras paths) and the failure
      notification; the rollback procedure with its commands
      and owner — yank 1.0.0a1 with a reason, ship
      1.0.0a1.post1 through the same pipeline (release.yml's
      version pattern accepts .postN), edit the GitHub
      release.
    </requirement>

    <requirement>
      Attribution and legal: README and docs carry the CFA®
      marks notice verbatim and "not investment advice";
      the Apache-2.0 licence metadata; and NOTICE as a
      maintainer decision. ROADMAP §5 says NOTICE carries
      the runtime dependencies' attributions, and ADR-0004
      says it carries "the attributions its runtime
      dependencies require". The wheel bundles no
      dependency, so the recommendation is that none are
      required for this release; record the maintainer's
      decision, and if attributions are wanted, Step 14 adds
      them to NOTICE.
    </requirement>

    <requirement>
      Decision: the document ends with `Decision: GO —
      <YYYY-MM-DD> — Nathan Ramos, CFA` or `Decision: NO-GO —
      <blockers>`. The maintainer writes or explicitly
      approves that line in the PR; the agent never fills it
      in alone. A NO-GO stops the phase: each blocker becomes
      an issue fixed on its own `fix/` branch (bumping the
      `.devN` version), and this step runs again in a fresh
      conversation with a new rehearsal.
    </requirement>

    <requirement>
      Filepath comment: python_floor.py and its test get the
      three-line header; docs/releases/ Markdown follows the
      docs/ convention and carries no filepath line.
    </requirement>
  </requirements>
</task>
```

### Step 13 acceptance criteria

- `docs/releases/1.0.0a1-readiness.md` is on `main` with all eleven
  sections, every item showing its command, its result and PASS or FAIL,
  and no FAIL left unresolved.
- The catalog audit covers all 32 ids, and the artifact review lists the
  exact differences the release commit may add.
- `scripts/checks/python_floor.py` exists with passing tests and its live
  result is recorded.
- The maintainer's GO or NO-GO line is present and was written or approved
  by the maintainer in the PR conversation.
- **Deployed & verified:** TestPyPI's JSON lists `1.0.0a1.devN` with a wheel
  and an sdist, and its integrity API returns a provenance for each; the
  release run's smoke passed with and without extras; and a clean-venv
  install of that version from TestPyPI ran `scripts/smoke.py --all` and
  `--extras` green.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the rehearsal used Trusted Publishing
  with no token, and the readiness document holds no credential or
  environment listing.

---

## Step 14 — 1.0.0a1 Release ✅

**Status:** Complete — PR #96 (2026-10-13)

> **Goal:** Release what the gate approved. On the step branch, set the
> version to `1.0.0a1` and make exactly the changes the readiness
> document lists — the Development Status classifier (3 - Alpha),
> `CITATION.cff`, the README's status banner (the PyPI page), a dated
> `[1.0.0a1]` CHANGELOG section, the release notes
> `docs/releases/1.0.0a1.md`, and `core/_released.py` filled with the 32
> released ids by `scripts/release_ledger.py` — re-running the ADR-0010
> floor check and ADR-0003's milestone check first. After the merge, tag
> `v1.0.0a1` on `main`; `release.yml` builds, waits for the maintainer's
> approval in the `pypi` environment, publishes with attestations and runs
> the smoke from PyPI. Verify the release in clean environments, confirm
> that plain `pip install pyeconomics` still resolves 0.2.6, and publish
> the GitHub release, marked as a pre-release. Parent: ROADMAP §4 2.7;
> ADR-0003.

**Branch:** `feature/phase02-step14-release`

**Deploys:** PyPI — `pyeconomics 1.0.0a1` as a pre-release, from tag
`v1.0.0a1` on `main` through `release.yml`'s `pypi` environment after the
maintainer's approval; the GitHub release `v1.0.0a1`. Read the Docs
`stable` (0.2.6) and `latest` (`legacy/0.2.x`) do not change.

| Setting      | Value                                           |
| ------------ | ----------------------------------------------- |
| Model        | GPT-6.1 Sol                                     |
| Backup       | Claude Sonnet 5.5 — Claude Code · Effort Medium |
| Platform     | Codex                                           |
| Intelligence | Medium                                          |
| Conversation | **New**                                         |

> Settings updated 2026-10-13: was GPT-6 Sol · Medium. GPT-6.1 Sol supersedes it in the same line; verified session effort remains medium.

**Model rationale:** Agentic work is PRIMARY — executing a decided
release: the version change, the merge, the tag, the approval, the publish
and the verification — and coding SECONDARY, for the release edits and the
ledger script. The gate removed the judgement calls and each action is
verified by a command, so complexity is Medium, with an A floor in agentic
work. The claude.ai Max weekly pool reads `tight` until Tue 2026-10-13
20:00 EDT and Codex is the lane with slack, so the operator's posture sends
this GPT-adequate Medium step to Codex on the ChatGPT Pro 5x plan, $0
marginal. GPT-6 Sol is S in agentic work and coding and wins the coverage
tie-break over GPT-6 Astra (Terminal-Bench 4.0 43.9). Codex opens on its
provider default; set GPT-6 Sol at Intelligence Medium, the ladder value
for Medium work. The backup is Claude Sonnet 5.5 on Claude Code at Effort
Medium — S in agentic work and coding, winning the coverage tie-break over
Opus 5.5. New conversation per phase-boundary hygiene.

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
       feature/phase02-step14-release`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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
       shape "Step 14 is
       complete. You can now move
       on to Step 15." That
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
       one before Step 15.
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
    - Publishing runs only through Trusted Publishing from
      the `pypi` environment after the maintainer's
      approval: no token is created, stored or printed; the
      tag push is the maintainer's approved action.
    - The release commit's diff is exactly the gate's list;
      any other change to a file that ships in the wheel or
      sdist stops the release and returns it to the gate.
    - release_ledger.py writes one module deterministically
      from the registry and nothing else.
  </security>

  <context>
    pyeconomics. Phase 2. Step 14: 1.0.0a1 release.

    Before relying on the planned state below, confirm
    readiness blockers #89 (US 30/360 long-stub timing)
    and #65 (Python 3.15 policy) are resolved and that the
    gate evaluates a fresh, corrected .devN candidate.
    Step 13's first attempt on 2026-10-12 is not a GO.
    Replace README's stale "nothing to use yet" skeleton
    paragraph as well as its status banner in this step;
    the readiness artifact-difference list includes both.

    Release integration review (2026-10-13): populating the
    ledger requires isolated toy-registry tests to supply
    an empty ledger. The shipped core/registry.py doctest
    also needs empty.validate(released={}) instead of
    empty.validate(). Its executable AST is unchanged,
    and the maintainer approved this documentation-only
    gate addendum on 2026-10-13, replying "Approved" to
    the batched addendum/tag/PyPI/GitHub release request.
    The approval is recorded in PR #96 comment 6159078803
    and the readiness artifact list. No further approval
    request for these actions is needed.

    Current state (as of Phase 2 Step 13):

    - docs/releases/1.0.0a1-readiness.md is on main with
      `Decision: GO`; its Artifacts section lists the only
      changes the release commit may add, and its Rollback
      section the yank-and-post-release procedure.
    - v1.0.0a1.dev3 (d697b0daffd3fd3c9e437a5c1fffe23eef5c5193,
      release run 38278124628) is on TestPyPI with attestations and
      passed the smoke with and without extras; main's
      version is 1.0.0a1.devN.
    - core/_released.py is empty, so validate() checks no
      released id yet.
    - The `pypi` environment requires the maintainer's
      approval; the 1.x PyPI path has never run.

    Files to read (every file before drafting):
    - docs/releases/1.0.0a1-readiness.md and the draft
      docs/releases/1.0.0a1.md.
    - docs/adr/0003-versioning-and-deprecation.md and
      0010-python-support-policy.md.
    - .github/workflows/release.yml and release-smoke.yml.
    - pyproject.toml, README.md, CHANGELOG.md,
      CITATION.cff and src/pyeconomics/core/_released.py.
    - scripts/verify-phase01.sh (checks 21 and 35) and the
      post-merge addendum at the end of
      docs/roadmap/phase01-roadmap.md.
  </context>

  <goal>
    pyeconomics 1.0.0a1 is on PyPI as a pre-release with
    attestations, its smoke is green from PyPI with and
    without extras, plain `pip install pyeconomics` still
    installs 0.2.6, the GitHub release v1.0.0a1 is public
    as a pre-release, and validate() now guards the 32
    released ids.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff: Step 13 reads Complete and the readiness
      document reads `Decision: GO`. Batch one request to the
      maintainer: approve the push of tag v1.0.0a1, the
      `pypi` environment deployment it triggers, and the
      GitHub release. Re-run scripts/checks/python_floor.py;
      if NumPy or SciPy moved their floor since the gate,
      raise requires-python, drop the old version from the
      CI matrix and the classifiers in the same change
      (ADR-0010), narrow verify-phase01.sh checks 21 and 35
      under the Cross-phase verification rule (with their
      addendum lines), and record the change in the release
      notes. Confirm v1.0.0a1 is Phase 2's tag in ADR-0003's
      milestone table. Apply the gate's NOTICE decision.
    </requirement>

    <requirement>
      scripts/release_ledger.py writes
      src/pyeconomics/core/_released.py from the installed
      registry — every canonical id, sorted, with the first
      package version that ships it — and `--check` fails
      when a registered id is missing from the ledger;
      tests/checks/test_release_ledger.py covers it. Run it
      for 1.0.0a1, so the ledger lists the 32 ids, and show
      validate() passing with it. A ledger entry is
      Released(canonical_id, first_version) and holds no
      model identity, so validate() cannot see a released id
      that a different model took over; decide here whether
      an entry also records a fingerprint (a hash of the
      model's input and output schemas at release), and if
      so extend check_released in the same pull request.
    </requirement>

    <requirement>
      The release commit: `uv version 1.0.0a1 --no-config`;
      CITATION.cff `version: 1.0.0a1` with `date-released`;
      the classifier `Development Status :: 3 - Alpha`;
      README's status banner (1.0.0a1 is a pre-release on
      PyPI, installed with `pip install --pre
      pyeconomics==1.0.0a1`; what it contains; the docs
      preview link; 0.2.6 remains what plain `pip install
      pyeconomics` installs); CHANGELOG's [Unreleased]
      becomes `[1.0.0a1] - <YYYY-MM-DD>`; and
      docs/releases/1.0.0a1.md completed from the gate's
      draft. Before the PR merges, build the wheel and sdist
      and compare their members and contents with the
      TestPyPI rehearsal's: the only differences are the
      readiness document's list.
    </requirement>

    <requirement>
      Release: after the merge, tag main's merge commit
      `v1.0.0a1` and push the tag; watch release.yml's
      verify and build jobs; the maintainer approves the
      `pypi` deployment; watch publish-pypi and the smoke
      (one model per domain with --min-domains 11, then the
      extras pass) to green. A failure after publication
      follows the gated rollback (yank, then 1.0.0a1.post1),
      never a re-upload of the same version, which PyPI
      refuses.
    </requirement>

    <requirement>
      GitHub release: `gh release create v1.0.0a1
      --prerelease --verify-tag` with docs/releases/1.0.0a1.md
      as the notes, linking the docs preview and the PyPI
      page; nothing is announced elsewhere (Phase 5
      announces 1.0).
    </requirement>

    <requirement>
      Filepath comment: release_ledger.py and its test get
      the three-line header; the generated _released.py keeps
      the header and states that the script writes it.
    </requirement>
  </requirements>
</task>
```

### Step 14 acceptance criteria

- Tag `v1.0.0a1` is on `main`, equals the version in `pyproject.toml` at
  that commit, and is Phase 2's milestone in ADR-0003's table; the Python
  floor was re-checked and any move applied under ADR-0010.
- `CHANGELOG.md` has a dated `[1.0.0a1]` section, `CITATION.cff` reads
  1.0.0a1 with its release date, the classifier is `Development Status ::
  3 - Alpha`, and `docs/releases/1.0.0a1.md` exists and links the docs
  preview.
- `core/_released.py` lists the 32 ids, `scripts/release_ledger.py --check`
  passes, and `registry.validate()` enforces the ledger.
- The release commit's artifacts differ from the rehearsal's only as the
  readiness document listed.
- **Deployed & verified:** PyPI's JSON for `pyeconomics/1.0.0a1` lists a
  wheel and an sdist and its integrity API returns a provenance for each;
  the release run's publish and smoke jobs are green; in a fresh venv,
  `pip install --pre pyeconomics==1.0.0a1` runs `scripts/smoke.py --all`
  from outside a checkout, and `pip install --pre
  "pyeconomics[econometrics,plot]==1.0.0a1"` runs `--extras`; in another
  fresh venv, plain `pip install pyeconomics` installs 0.2.6; the GitHub
  release `v1.0.0a1` is published as a pre-release; Read the Docs `stable`
  still serves 0.2.6.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the release used Trusted Publishing
  with attestations and no stored token, and the maintainer approved the
  `pypi` deployment.

---

## Step 15 — QA and Verification Script ✅

**Status:** Complete — PR #97 (2026-10-14)

> **Goal:** Package the phase's verification into
> `scripts/verify-phase02.sh` — Phase 1's mode contract (`--fast`,
> `--python`, `--security`, `--live`, `--all`, `--post`) and output format,
> with 61 numbered static checks covering Steps 1–14, five Step 15
> self-checks and the V1–V15 matrix — plus `tests/repo/test_phase02.py`;
> append `02` to `.github/workflows/phase-verify.yml`'s matrix and require
> its two jobs on `main`; prove the changed release-smoke alarm fires with
> a synthetic failure; run `verify-phase01.sh --post` so Phase 1's ledger
> stays green; write `docs/phase02-qa-findings.md`; audit every Phase 2
> acceptance criterion in the project roadmap against the V-checks; and
> mark the phase complete in this roadmap and in the project roadmap.
> Parent: Phase 2 acceptance criteria.

**Branch:** `feature/phase02-step15-verify`

**Deploys:** nothing beyond merge — the CI matrix entry is live on merge.

| Setting      | Value                                           |
| ------------ | ----------------------------------------------- |
| Model        | GPT-6.1 Sol                                       |
| Backup       | Claude Sonnet 5.5 — Claude Code · Effort Medium |
| Platform     | Codex                                           |
| Intelligence | Medium                                          |
| Conversation | **New**                                         |

> Settings updated 2026-10-13: was GPT-6 Sol · Medium. GPT-6.1 Sol supersedes it in the same line; verified session effort remains medium.

**Model rationale:** Coding is PRIMARY — a Bash verification script, its
pytest twin and a matrix entry — and agentic work SECONDARY: running the
live checks against GitHub, PyPI, TestPyPI and Read the Docs and walking
every Phase 2 criterion. It translates `verify-phase01.sh`'s settled mode
contract into this phase's deliverables, so complexity is Medium, with an
A floor in coding. The claude.ai Max weekly pool reads `tight` until Tue
2026-10-13 20:00 EDT and Codex is the lane with slack, so the operator's
posture sends this GPT-adequate Medium step to Codex on the ChatGPT Pro 5x
plan, $0 marginal. GPT-6 Sol is S in coding and agentic work and wins the
coverage tie-break over GPT-6 Astra (Terminal-Bench 4.0 43.9). Codex opens
on its provider default; set GPT-6 Sol at Intelligence Medium, the ladder
value for numerous but mechanical checks. The backup is Claude Sonnet 5.5
on Claude Code at Effort Medium — S in coding and agentic work, winning the
coverage tie-break over Opus 5.5. New conversation per phase-boundary
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
       feature/phase02-step15-verify`
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
       Phase 2 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 2`
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
       shape "Step 15 is
       complete. Phase 2 is
       complete. You can now move
       on to Phase 3." That
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
       one before Phase 3.
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
    - The prek gate runs on every commit; no SKIP. This step
      also AUTHORS the --security verify mode, so its own
      diff must still pass the gate before commit.
    - `--live` reads GitHub, PyPI, TestPyPI and Read the
      Docs through the maintainer's authenticated gh
      session and public APIs, and never prints a token, a
      secret value or the environment; CI never runs
      `--live`.
    - The synthetic alarm test dispatches release-smoke.yml
      against a version that does not exist; it publishes
      nothing.
  </security>

  <context>
    pyeconomics. Phase 2. Step 15: QA and verification
    script.

    Steps 1 through 14 have been implemented. Now create the
    verification script, the QA findings document and the
    CI matrix entry, verify every Phase 2 criterion, and
    close the phase.

    Reference scripts (pattern templates):
    - scripts/verify-phase01.sh (the structural template:
      helpers, modes, PASS/FAIL lines, per-mode summary).
    - tests/repo/test_phase01.py (the pytest twin).

    Every static check states an invariant later phases
    keep — presence, structure, "at least" — never an exact
    version or count a later phase legitimately changes
    (Phase 1's check 44 had to be narrowed for that reason).

    Phase 2 deliverables to verify (61 static checks across
    Steps 1 through 14 plus 5 Step 15 self-checks):

    Step 1 (conventions) — checks 1-8:
    1.  docs/roadmap/phase02-roadmap.md is tracked.
    2.  docs/adr/0008-numerical-conventions.md reads
        `Status: Accepted`, and the ADR index lists 0008 as
        Accepted with the file's date.
    3.  ADR-0008's Decision outcome has a numbered
        subsection for each of its fourteen decisions, 1 to
        14 (decimals, units, bounds, frequency and
        compounding, day counts and calendars, tolerance,
        randomness, arrays and tabular data, pandas 3,
        non-finite results, root finding, canonical JSON
        numbers, errors and warnings, runtime dependencies
        and Pyodide).
    4.  [project].dependencies names pydantic, numpy, scipy
        and pandas, each with a `>=` lower bound and no
        upper bound.
    5.  Every licence_exceptions.toml entry has package,
        licence and a non-empty reason, and none names a
        package ADR-0004 excludes.
    6.  core/ holds units, rates, compounding, tolerance,
        random, numerics, errors and warnings modules, and
        PyeconomicsDeprecationWarning subclasses
        FutureWarning.
    7.  CITATION.cff's version equals pyproject.toml's, and
        its licence is Apache-2.0.
    8.  ci.yml has a `pyodide` job in the `test` aggregate's
        needs, and scripts/smoke.py exists and runs in the
        package job.

    Step 2 (dates) — checks 9-12:
    9.  DayCount names THIRTY_360_US, THIRTY_E_360,
        ACT_360, ACT_365_FIXED, ACT_ACT_ISDA and
        ACT_ACT_ICMA.
    10. BusinessDayConvention names UNADJUSTED, FOLLOWING,
        MODIFIED_FOLLOWING, PRECEDING and
        MODIFIED_PRECEDING, and core/schedule.py exists.
    11. The runtime dependencies name holidays; the test
        group names QuantLib.
    12. tests/unit/core/ holds day-count and calendar tests
        that import QuantLib.

    Step 3 (registry) — checks 13-18:
    13. src/pyeconomics/registry.py defines ids, get,
        models, domains, resolve and validate.
    14. core/spec.py defines ModelSpec, Reference,
        Invariant, Example and CostClass, and Evidence with
        standard, practitioner, contested, rejected and
        historical.
    15. core/registry.py loads the `pyeconomics.models`
        entry-point group.
    16. .semgrep/rules/model-purity.yaml and
        .semgrep/tests/model-purity.py exist.
    17. core/_released.py exists.
    18. tests/registry/ holds the validate() rule tests and
        the import-allowlist test.

    Step 4 (results) — checks 19-24:
    19. pyeconomics exports run and run_batch; core/
        results, manifest, canonical, schema and cards
        modules exist.
    20. The canonical-JSON tests cite RFC 8785's vectors.
    21. The `plot` extra names plotly, and `all` includes
        plot.
    22. The test group names jsonschema and rfc8785.
    23. release-smoke.yml runs scripts/smoke.py with
        --min-domains.
    24. core/schema.py names the JSON Schema 2020-12
        dialect URI.

    Step 5 (harness) — checks 25-30:
    25. tests/golden/README.md and tests/golden/
        test_golden.py exist.
    26. pyproject.toml registers the `invariant` and
        `oracle` markers, and the invariant-coverage
        meta-test exists.
    27. scripts/checks/coverage_floors.py exists with the 95
        (core) and 90 (models) floors, and ci.yml runs it.
    28. CONTRIBUTING's model definition of done names
        tests/golden/ and the invariant marker.
    29. The pull request template has a "Model checklist"
        section.
    30. tests/golden/test_sources.py (the citation guard)
        exists.

    Step 6 (foundations) — checks 31-33:
    31. pyproject.toml declares the `foundations` entry
        point, and scripts/checks/dist_contents.py admits
        the wheel's entry_points.txt.
    32. The five foundations ids are declared under
        src/pyeconomics/models/foundations/.
    33. tests/golden/foundations/ holds a file for each.

    Step 7 (docs preview) — checks 34-39:
    34. docs/conf.py, docs/index.md and .readthedocs.yaml
        exist, and .readthedocs.yaml sets fail_on_warning.
    35. ci.yml has a `docs` job in the `test` aggregate's
        needs that runs sphinx-build with -W.
    36. The docs group names sphinx, myst-nb, sphinx-autoapi
        and pydata-sphinx-theme; the test group names sybil.
    37. docs/conftest.py configures Sybil, and conf.py
        excludes roadmap/, adr/ and releases/.
    38. docs/errata.md exists, and docs/notices.md carries
        the CFA® marks notice verbatim and "not investment
        advice".
    39. docs/roadmap/phase01-roadmap.md ends with the Phase
        2 post-merge addendum naming checks 44 and 19.

    Steps 8-12 (catalog) — checks 40-55:
    40. pyproject.toml declares the `fixed_income` entry
        point.
    41. The six fixed_income ids are declared under
        src/pyeconomics/models/fixed_income/.
    42. tests/golden/fixed_income/ holds a file for each.
    43. pyproject.toml declares the `derivatives` and
        `international` entry points, and the test group
        names vollib.
    44. The five derivatives ids and
        international.parity_conditions are declared.
    45. tests/golden/derivatives/ and
        tests/golden/international/ hold a file for each.
    46. pyproject.toml declares the `equity`, `corporate`
        and `accounting` entry points.
    47. The seven equity, corporate and accounting ids are
        declared.
    48. Their golden files exist.
    49. pyproject.toml declares the `portfolio` and
        `performance` entry points.
    50. The five portfolio and performance ids are
        declared.
    51. Their golden files exist.
    52. pyproject.toml declares the `risk` and
        `econometrics` entry points.
    53. The three risk and econometrics ids are declared.
    54. Their golden files exist, and
        tests/golden/econometrics/ols.toml cites NIST's
        Statistical Reference Datasets.
    55. The `econometrics` extra names statsmodels, and
        `all` includes it.

    Steps 13-14 (gate and release) — checks 56-61:
    56. docs/releases/1.0.0a1-readiness.md has its eleven
        sections, no unresolved FAIL, and a `Decision: GO`
        line.
    57. scripts/checks/python_floor.py exists, and a
        v1.0.0a1.dev* tag is an ancestor of origin/main.
    58. Tag v1.0.0a1 exists and is an ancestor of
        origin/main.
    59. CHANGELOG.md has a dated [1.0.0a1] section.
    60. core/_released.py lists all 32 Phase 2 ids, and
        scripts/release_ledger.py exists.
    61. docs/releases/1.0.0a1.md exists and links the docs
        preview.

    Step 15 self-checks — checks 62-66:
    62. scripts/verify-phase02.sh exists with git index mode
        100755.
    63. docs/phase02-qa-findings.md exists.
    64. docs/roadmap/phase02-roadmap.md exists (this doc).
    65. .github/workflows/phase-verify.yml's matrix
        includes "02".
    66. Security backstop: no tracked file holds a private
        key's PEM header (the five-dash BEGIN line), an AWS
        access-key id prefix followed by 16 key characters,
        a GitHub token or a PyPI token; the prek config
        still runs gitleaks, bandit, semgrep, pip-audit,
        licences and zizmor, and security.yml exists.

    Files to read:
    - scripts/verify-phase01.sh and tests/repo/
      test_phase01.py (the templates).
    - Every file the checks above name.
    - docs/roadmap/ROADMAP.md §4 Phase 2 acceptance criteria
      and §5 "Operations & observability strategy".
    - This file's Post-Implementation Verification section
      (the V-check tables the script reports).
  </context>

  <goal>
    Create scripts/verify-phase02.sh with 61 static
    deliverable checks (Steps 1-14), 5 Step 15 self-checks
    and the V1-V15 matrix; create docs/phase02-qa-findings.md
    and tests/repo/test_phase02.py; append "02" to
    phase-verify.yml's matrix and require both of its jobs;
    prove the release-smoke alarm; keep verify-phase01.sh
    green; and mark Phase 2 complete in both roadmaps.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      scripts/verify-phase02.sh modes, mirroring
      verify-phase01.sh's helpers (record, check, vcheck,
      vstatic), output format and per-mode summary:
      - default (no flag) and --fast: static checks 1-66,
        CI-safe on Ubuntu, using grep, test -f, test -x,
        git ls-files, git show and python3 with tomllib
        only; under 30 seconds.
      - --python: static checks plus `uv sync --locked
        --all-extras`, ruff format --check, ruff check,
        mypy, `uv run pytest --cov` (golden, property,
        contract and Sybil suites), the coverage floors,
        registry.validate(), the docs build with -W,
        `uv build`, `twine check --strict`, the artifact
        allowlist, and the clean-venv smoke with and
        without extras.
      - --security: the gate over the whole tree — `uv run
        prek run --all-files` with SKIP=no-commit-to-branch
        on a main checkout, the semgrep-test hook, and
        gitleaks over the whole tree staged on an orphan
        branch in a scratch clone, as verify-phase01.sh
        does. CI-safe on Ubuntu; exits non-zero on any
        finding.
      - --live: local only, with the maintainer's gh
        session — the latest ci run on main is green with
        its pyodide and docs jobs (V1.3); the Read the Docs
        API shows `main` active, not default and built from
        main's HEAD, `stable` on 0.2.6 and `latest` on
        legacy/0.2.x (V7.3); TestPyPI's v1.0.0a1.devN lists
        two files with provenance (V13.2); python_floor.py
        passes (V13.3); PyPI's 1.0.0a1 lists two files with
        provenance and the GitHub release v1.0.0a1 is a
        pre-release (V14.2); and main's required checks
        include `phase-verify-fast (02)` and
        `phase-verify-security (02)`, strict (V15.7).
      - --all: --fast, --python and --security.
      - --post: --all, --live, a clean-venv install of
        `pyeconomics==1.0.0a1` from PyPI running
        `scripts/smoke.py --all` and, with its extras,
        `--extras`, and a fresh venv where plain `pip install
        pyeconomics` installs 0.2.6 (V14.3); the synthetic
        alarm's recorded run (V15.5); `verify-phase01.sh
        --post` (V15.6); the V1-V15 summary; and `gh pr
        checks` when gh is logged in and the branch has a
        PR.
      Each check is numbered, independent, and prints a
      clear PASS or FAIL line naming its deliverable.
    </requirement>

    <requirement>
      The script reports the V-checks by id (V1.1, V2.1, …)
      exactly as this file's Post-Implementation
      Verification section lists them, ends with a summary
      table of totals per mode, and records V15.3 as PASS
      only when no static check failed.
    </requirement>

    <requirement>
      tests/repo/test_phase02.py:
      - test_roadmap_doc_exists.
      - test_qa_findings_doc_exists.
      - test_verify_script_exists_and_executable (the git
        index mode is 100755; subprocess calls to git carry
        an inline `# noqa` with its justification).
      - test_phase_verify_matrix_includes_02.
    </requirement>

    <requirement>
      .github/workflows/phase-verify.yml: append "02" to both
      jobs' `phase` matrix and change nothing else. Once both
      `(02)` jobs have reported green on this PR, add them to
      main's required checks with a PATCH of
      required_status_checks that re-sends every existing
      check (strict stays on).
    </requirement>

    <requirement>
      Synthetic alarm (Operations acceptance): dispatch
      release-smoke.yml with index testpypi and a version
      that does not exist (for example 0.0.0.dev0); confirm
      the run fails and the maintainer receives GitHub's
      failed-workflow notification (the maintainer confirms;
      the session's mail connector reads a different inbox);
      record the run URL and the confirmation in the QA
      findings.
    </requirement>

    <requirement>
      Cross-phase: run `verify-phase01.sh --post` and make
      it pass; a check Phase 2 legitimately broke and no
      earlier step narrowed is narrowed now under the
      Cross-phase verification rule, with an addendum line.
    </requirement>

    <requirement>
      docs/phase02-qa-findings.md: one rollup section per step
      (1-14) listing every finding the step surfaced, its
      Triage class, its destination (fixed in PR #, issue #,
      or the phase that owns it) and the guard that now
      prevents the class; a Step 15 verify-script rollup;
      the synthetic alarm; a "Phase 2 acceptance audit
      (ROADMAP §4)" table mapping each project-roadmap
      criterion to its V-checks and result; and a "Pre-ship
      items" section with documented limitations and
      downstream follow-ups, each with its owner. Carry
      Step 11's empyrical-reloaded decision and every
      contract change in this roadmap's carry-over
      checklist into it.
    </requirement>

    <requirement>
      Mark the phase complete in the SAME Stage-3 commit
      that marks this step (Status rule):
      - In docs/roadmap/ROADMAP.md, `### Phase 2 — Model
        Engine & Core Catalog` gets `**Status:** Complete —
        <YYYY-MM-DD>; PR #<n>; v1.0.0a1;
        phase02-roadmap.md` directly under it and ✅ at the
        end of the heading; its §8 row reads `Complete`; the
        header `> **Status:**` line names Phase 2 as shipped
        (v1.0.0a1 on PyPI) and Phase 3 as next; and its
        Phase 2 acceptance criteria are audited against
        V1-V15 in the QA findings.
      - In this file: the phase-level Status reads
        `Complete — <YYYY-MM-DD>`; the title and every step
        heading end in ✅; every Summary Table Status cell
        reads `Complete — PR #<n>`.
    </requirement>

    <requirement>
      The script is executable (`git update-index
      --chmod=+x scripts/verify-phase02.sh` on Windows),
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

### Step 15 acceptance criteria

- `scripts/verify-phase02.sh` exists with git index mode 100755 and passes
  on a clean tree after implementation.
- The script has 61 deliverable checks plus 5 self-checks and the V1–V15
  post-implementation checks, and no static check pins a value a later
  phase legitimately changes.
- `--fast` runs in under 30 seconds on Ubuntu CI.
- `--post` runs cleanly on the maintainer's machine with every live check,
  both clean-venv installs from PyPI and `verify-phase01.sh --post` green,
  and every `--live` and `--post` item reports under its V-id.
- `docs/phase02-qa-findings.md` is complete, with every rollup section and
  the acceptance audit.
- `.github/workflows/phase-verify.yml`'s matrix includes `02`; its fast and
  security jobs appear on every PR and are required on `main`.
- `--security` exists and exits 0 (secret/PII scan, SAST, dependency
  audit and licence check clean over the phase's surface); V15.4 is
  green.
- `tests/repo/test_phase02.py` passes in the CI matrix.
- Branch protection still passes on the resulting PR.
- **Operations:** the publishing surface's changed health signal
  (`release-smoke.yml`, now running one model per domain and the extras
  pass) and its alarm (GitHub's failed-workflow notification to the
  maintainer) were seen to fire once, by dispatching the smoke against a
  version that does not exist; the run URL and the maintainer's
  confirmation are recorded in the QA findings.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff and the security workflow is
  green.
- **Phase closed, nothing carried.** Every finding recorded in
  `docs/phase02-qa-findings.md` has a destination (fixed, an issue number,
  or a named phase that owns it), the "Not in scope" section below is
  current, and no untracked item remains. Every step of this roadmap, this
  one included, reads `**Status:** Complete — PR #…` on `main` under a ✅
  heading, the Summary Table's Status column and this roadmap's
  phase-level Status line say `Complete` under a ✅ title, and the parent
  project roadmap's Phase 2 entry (under a ✅ heading), its summary-table
  row and its header status line say `Complete` — all landed in this
  step's PR. This step's final response ends with two lines and nothing
  after them: "Step 15 is complete. You can now move on to Step 16." is
  replaced by "Step 15 is complete. Phase 2 is complete. You can now move
  on to Phase 3." — same Stage 6 rule: no "Follow-ups", no trailer.

---

## Post-Implementation Verification

Every V1–V15 check below runs **automatically in CI** on every push and
pull request — no manual invocation required — except the `--live` and
`--post` checks. Those read state that needs the maintainer's
authenticated `gh` session (branch protection's required checks, the
latest runs on `main`, the GitHub release), external registries and
services (PyPI, TestPyPI and their integrity APIs, the Read the Docs API),
clean-venv installs from PyPI, and the operator-observed alarm
notification. They run on the maintainer's machine with
`./scripts/verify-phase02.sh --post` before Phase 2 is declared complete.

| Mode             | Workflow                                              | Runner                   | Coverage                                                                  |
| ---------------- | ----------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------- |
| `--fast`         | `phase-verify.yml` (matrix entry `02`, fast job)      | Ubuntu                   | Static checks 1–66; V1.1, V2.1, V3.1, V4.1, V5.1, V6.1, V7.1, V8.1, V9.1, V10.1, V11.1, V12.1, V13.1, V14.1, V15.1–V15.3 |
| `--python`       | `ci.yml` (lint, types, tests, package and docs jobs run the same commands); local | Ubuntu, Windows, macOS | V1.2, V2.2, V3.2, V4.2, V4.3, V5.2, V6.2, V7.2, V8.2, V9.2, V10.2, V11.2, V12.2, V12.3 |
| `--security`     | `phase-verify.yml` (security job); `security.yml`     | Ubuntu                   | V1.4, V3.3, V15.4 (secret/PII scan + SAST + dependency audit + licences)  |
| `--live`         | local only — the maintainer's `gh` session            | Maintainer's machine     | V1.3, V7.3, V13.2, V13.3, V14.2, V15.7                                    |
| `--all`          | local                                                 | Any                      | `--fast` + `--python` + `--security`                                      |
| `--post`         | local, before the phase is declared complete          | Maintainer's machine     | `--all` + `--live` + V14.3, V15.5, V15.6 + `gh pr checks`                 |

Local invocations remain available for ad-hoc runs and pre-release
sweeps:

```bash
./scripts/verify-phase02.sh --post   # static + V1-V15 + live + post checks
```

`--post` is the canonical command to run before declaring Phase 2
complete, and before tagging a later phase's release.

Other modes:

```bash
./scripts/verify-phase02.sh              # static checks (same as --fast)
./scripts/verify-phase02.sh --fast       # static checks only (Ubuntu CI)
./scripts/verify-phase02.sh --python     # static + lint, types, tests, docs, build
./scripts/verify-phase02.sh --security   # secrets, SAST, dep audit, licences
./scripts/verify-phase02.sh --live       # GitHub, PyPI, TestPyPI, RTD (local)
./scripts/verify-phase02.sh --all        # static + python + security
```

The script reports each V-check by id (V1.1, V2.1, …) so a failure in any
workflow above maps directly to the corresponding row below.

### V1 — ADR-0008 and core conventions

> **Automated in CI.** `phase-verify.yml` → V1.1; `ci.yml` → V1.2 and the
> `pyodide` job behind V1.3; `security.yml` → V1.4.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V1.1 | Static checks 1–8 all PASS (roadmap tracked; ADR-0008 Accepted with its fourteen decisions; runtime baseline with floors; reviewed exceptions; core modules; version and citation in step; `pyodide` job and smoke). | `phase-verify.yml` runs `verify-phase02.sh --fast` on every push/PR. |
| V1.2 | The core unit, property and doctest suites pass with sockets disabled on all supported OS/Python matrix cells (twelve after PR #92). | `ci.yml` tests matrix (`--python` locally).                       |
| V1.3 | The `pyodide` job is green on `main`'s HEAD: Pyodide installs the wheel and runs `scripts/smoke.py`. | `ci.yml` `pyodide` job on every push/PR; `--live` reads its latest run on `main`. |
| V1.4 | The `licences` hook passes with its reviewed exceptions, and `dependency-review` passes. | `security.yml` (gate-licences, dependency-review); `--security`.   |

### V2 — Dates, day counts and calendars

> **Automated in CI.** `phase-verify.yml` → V2.1; `ci.yml` → V2.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V2.1 | Static checks 9–12 all PASS (six day counts, five business-day conventions, `holidays` and QuantLib declared, oracle tests present). | `phase-verify.yml --fast`.                  |
| V2.2 | Day-count, schedule and calendar tests agree with the cited worked examples and with QuantLib. | `ci.yml` tests matrix (`--python` locally).               |

### V3 — Model specification and registry

> **Automated in CI.** `phase-verify.yml` → V3.1 and V3.3; `ci.yml` →
> V3.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V3.1 | Static checks 13–18 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V3.2 | `registry.validate()` passes on the installed registry and rejects each rule's toy spec; aliases warn with `PyeconomicsDeprecationWarning`. | `ci.yml` tests matrix (`--python` locally). |
| V3.3 | The `model-purity` rule passes `semgrep-test`, semgrep is clean over `src/pyeconomics/models/`, and the import allowlist holds. | `phase-verify.yml` security job; `security.yml` gate-sast; `ci.yml` tests. |

### V4 — Results, provenance and schemas

> **Automated in CI.** `phase-verify.yml` → V4.1; `ci.yml` → V4.2 and
> V4.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V4.1 | Static checks 19–24 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V4.2 | Canonical JSON passes RFC 8785's vectors and the `rfc8785` oracle; every registered model's schemas are valid 2020-12 schemas; round trips are lossless; results and manifests are deterministic. | `ci.yml` tests matrix (`--python` locally). |
| V4.3 | `scripts/smoke.py` runs one model per registered domain in the package job's clean venv. | `ci.yml` package job (`--python` locally).                      |

### V5 — Verification harness

> **Automated in CI.** `phase-verify.yml` → V5.1; `ci.yml` → V5.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V5.1 | Static checks 25–30 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V5.2 | The golden harness runs every registered model's cases; the invariant meta-test and the contract suite pass; branch coverage is at least 95% on `core/`, 90% on `models/` and 95% overall. | `ci.yml` tests matrix with `coverage_floors.py` (`--python` locally). |

### V6 — Launch catalog: foundations

> **Automated in CI.** `phase-verify.yml` → V6.1; `ci.yml` → V6.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V6.1 | Static checks 31–33 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V6.2 | The five foundations models pass their golden, property, contract and oracle tests. | `ci.yml` tests matrix (`--python` locally).                      |

### V7 — Model cards and documentation preview

> **Automated in CI.** `phase-verify.yml` → V7.1; `ci.yml` (docs and
> tests jobs) → V7.2; `--live` → V7.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V7.1 | Static checks 34–39 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V7.2 | `sphinx-build -W` succeeds with the tutorial executed and one page per registered model, and Sybil's examples pass. | `ci.yml` docs and tests jobs (`--python` locally). |
| V7.3 | Read the Docs serves `/en/main/` built from `main`'s HEAD, `/en/stable/` serves 0.2.6, and `/en/latest/` builds `legacy/0.2.x`. | `--live` (Read the Docs API and page text). |

### V8 — Launch catalog: fixed income

> **Automated in CI.** `phase-verify.yml` → V8.1; `ci.yml` → V8.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V8.1 | Static checks 40–42 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V8.2 | The six fixed-income models pass their golden (31 CFR Part 356 cases included), property, contract and QuantLib oracle tests. | `ci.yml` tests matrix (`--python` locally). |

### V9 — Launch catalog: derivatives and international

> **Automated in CI.** `phase-verify.yml` → V9.1; `ci.yml` → V9.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V9.1 | Static checks 43–45 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V9.2 | The six models pass their golden, property, cross-entry, contract, QuantLib and vollib tests. | `ci.yml` tests matrix (`--python` locally).                 |

### V10 — Launch catalog: equity, corporate and accounting

> **Automated in CI.** `phase-verify.yml` → V10.1; `ci.yml` → V10.2.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V10.1 | Static checks 46–48 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V10.2 | The seven models pass their golden, property and contract tests, the DuPont identities and the capital-budgeting cross-entry test. | `ci.yml` tests matrix (`--python` locally). |

### V11 — Launch catalog: portfolio and performance

> **Automated in CI.** `phase-verify.yml` → V11.1; `ci.yml` → V11.2.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V11.1 | Static checks 49–51 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V11.2 | The five models pass their golden, property and contract tests, the attribution identities and the minimum-variance oracle. | `ci.yml` tests matrix (`--python` locally). |

### V12 — Launch catalog: risk and econometrics

> **Automated in CI.** `phase-verify.yml` → V12.1; `ci.yml` → V12.2 and
> V12.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V12.1 | Static checks 52–55 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V12.2 | The three models pass their golden (NIST's certified regressions and the Basel zones included), property, contract and independent NumPy tests; the registry includes all 32 launch-catalog ids (later phases may add ids). | `ci.yml` tests matrix (`--python` locally). |
| V12.3 | Without extras, `econometrics.ols` names `pyeconomics[econometrics]`; with the extra, it runs. | `ci.yml` package job's two clean venvs (`--python` locally). |

### V13 — 1.0.0a1 readiness gate

> **Automated in CI.** `phase-verify.yml` → V13.1; `--live` → V13.2 and
> V13.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V13.1 | Static checks 56–57 PASS: the readiness document has eleven sections, no unresolved FAIL and a `Decision: GO` line; `python_floor.py` exists; a `v1.0.0a1.dev*` tag is on `main`. | `phase-verify.yml --fast`. |
| V13.2 | TestPyPI's `1.0.0a1.devN` lists a wheel and an sdist, each with a provenance. | `--live` (TestPyPI JSON and integrity APIs).                           |
| V13.3 | `python_floor.py` passes: `requires-python` matches the higher of NumPy's and SciPy's newest floors (ADR-0010). | `--live` (PyPI JSON API).                                    |

### V14 — 1.0.0a1 release

> **Automated in CI.** `phase-verify.yml` → V14.1; `--live` → V14.2;
> `--post` → V14.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V14.1 | Static checks 58–61 PASS (`v1.0.0a1` on `main`, the dated CHANGELOG section, the 32-id ledger, the release notes). | `phase-verify.yml --fast`.                  |
| V14.2 | PyPI's `1.0.0a1` lists a wheel and an sdist, each with a provenance, and the GitHub release `v1.0.0a1` is a published pre-release. | `--live` (PyPI JSON and integrity APIs; `gh release view`). |
| V14.3 | A clean-venv `pip install --pre pyeconomics==1.0.0a1` runs `scripts/smoke.py --all`, and with its extras `--extras`; plain `pip install pyeconomics` installs 0.2.6. | `--post`.                         |

### V15 — CI integration + security

> **Automated in CI.** `phase-verify.yml` → V15.1 through V15.4 and the
> `01` entry behind V15.6 on every push/PR; `--post` → V15.5 and V15.6;
> `--live` → V15.7.

| ID         | Check                                                          | Automation                                                                |
| ---------- | -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V15.1      | `verify-phase02.sh --fast` exits 0 on Ubuntu CI.               | `phase-verify.yml` matrix entry `02`.                                     |
| V15.2      | `phase-verify.yml` matrix includes `02`.                       | `phase-verify.yml --fast` static check 65.                                |
| V15.3      | All static checks in `verify-phase02.sh` pass.                 | `phase-verify.yml --fast` records PASS only when no static check failed. |
| V15.4      | `verify-phase02.sh --security` exits 0 (secret/PII scan + SAST + dependency audit + licences clean). | `phase-verify.yml` security job on every push/PR. |
| V15.5      | The changed release-smoke alarm fired once on a synthetic failure, and the notification reached the maintainer. | `--post` reads the recorded run's conclusion; the notification is recorded in `docs/phase02-qa-findings.md`. |
| V15.6      | Phase 1's ledger stays green: `verify-phase01.sh --fast` exits 0 on every PR, and `verify-phase01.sh --post` passes before the phase closes. | `phase-verify.yml` matrix entry `01` on every push/PR; `--post` runs `verify-phase01.sh --post`. |
| V15.7      | `main` requires `phase-verify-fast (02)` and `phase-verify-security (02)`, with strict status checks. | `--live` (`gh api .../required_status_checks`). |

---

## Summary Table

| Step | Scope                          | Model             | Status            |
| ---- | ------------------------------ | ----------------- | ----------------- |
| 1    | ADR-0008 + core conventions    | Claude Opus 5.5   | Complete — PR #71 |
| 2    | Dates, day counts, calendars   | GPT-6.1 Sol       | Complete — PR #73 |
| 3    | Spec + registry                | Claude Sonnet 5.5 | Complete — PR #76 |
| 4    | Results, provenance, schemas   | Claude Sonnet 5.5 | Complete — PR #77 |
| 5    | Verification harness           | Claude Sonnet 5.5 | Complete — PR #78 |
| 6    | Catalog: foundations           | Claude Opus 5.5   | Complete — PR #79 |
| 7    | Cards + docs preview           | GPT-6.1 Sol       | Complete — PR #80 |
| 8    | Catalog: fixed income          | Claude Opus 5.5   | Complete — PR #82 |
| 9    | Catalog: derivatives + intl    | Claude Opus 5.5   | Complete — PR #84 |
| 10   | Catalog: equity, corp., acct.  | GPT-6.1 Sol       | Complete — PR #86 |
| 11   | Catalog: portfolio + perf.     | Claude Opus 5.5   | Complete — PR #87 |
| 12   | Catalog: risk + econometrics   | Claude Opus 5.5   | Complete — PR #88 |
| 13   | 1.0.0a1 readiness gate         | GPT-6.1 Sol       | Complete — PR #93 |
| 14   | 1.0.0a1 release                | GPT-6.1 Sol       | Complete — PR #96 |
| 15   | QA + verify-phase02.sh         | GPT-6.1 Sol       | Complete — PR #97 |
| V1   | Conventions                    | CI                | --                |
| V2   | Dates and calendars            | CI                | --                |
| V3   | Spec + registry                | CI                | --                |
| V4   | Results + schemas              | CI                | --                |
| V5   | Verification harness           | CI                | --                |
| V6   | Foundations                    | CI                | --                |
| V7   | Docs preview                   | CI                | --                |
| V8   | Fixed income                   | CI                | --                |
| V9   | Derivatives + international    | CI                | --                |
| V10  | Equity, corporate, accounting  | CI                | --                |
| V11  | Portfolio + performance        | CI                | --                |
| V12  | Risk + econometrics            | CI                | --                |
| V13  | Readiness gate                 | CI                | --                |
| V14  | 1.0.0a1 release                | CI                | --                |
| V15  | CI integration                 | CI                | --                |

---

## Model selection blocks

```text
PROMPT: Step 1 — ADR-0008 Numerical Conventions and Core Types
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Astra
PLATFORM: Claude Code
EFFORT: XHigh
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: planning, knowledge secondary — fourteen numerical
conventions binding every model and surface, each resting on a cited
definition. PICK: Opus 5.5 is S in planning and knowledge and beats Fable
5.1 on the cost tie-break (AA Intelligence Index 57.6). EFFORT: XHigh —
High plus a rung for cross-cutting planning; every decision has a drafted
default, so neither Max nor Ultracode.

PROMPT: Step 2 — Dates, Day Counts and Calendars
MODEL: GPT-6 Sol
BACKUP: Claude Opus 5.5
PLATFORM: Codex
EFFORT: Medium
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — six day-count conventions,
coupon schedules and business-day calendars built to decided definitions.
PICK: GPT-6 Sol is S in coding and wins the coverage tie-break over GPT-6
Astra (SciCode 57.6). EFFORT: Medium, the ladder value, because ADR-0008
decided the definitions and QuantLib carries the verification; thinking
on.

PROMPT: Step 3 — Model Specification and Registry
MODEL: Claude Sonnet 5.5
BACKUP: GPT-6 Astra
PLATFORM: Claude Code
EFFORT: XHigh
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — the specification,
decorator, registry, validate() rules and purity guards every model and
surface depends on. PICK: Sonnet 5.5 is S in coding and planning and wins
the coverage tie-break, S or A in all seven categories (AA Intelligence
Index 56.0). EFFORT: XHigh — High plus a rung for novel API design across
many files; the contract's shape is fixed, so not Max.

PROMPT: Step 4 — Results, Provenance and Schemas
MODEL: Claude Sonnet 5.5
BACKUP: GPT-6 Astra
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — results, deterministic
manifests, RFC 8785 canonical JSON and 2020-12 schemas that later
surfaces compare byte for byte. PICK: Sonnet 5.5 is S in coding and
planning and wins the coverage tie-break (AA Intelligence Index 56.0).
EFFORT: High for cross-cutting contracts whose design is fixed and whose
hardest part an oracle checks; thinking on.

PROMPT: Step 5 — Verification Harness
MODEL: Claude Sonnet 5.5
BACKUP: GPT-6 Astra
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — the golden format, harness,
invariant meta-test, input strategies and coverage floors every catalog
model must pass. PICK: Sonnet 5.5 is S in coding and planning and wins the
coverage tie-break (AA Intelligence Index 56.0). EFFORT: High because a
vacuous check would pass 32 models unverified; the design is fixed, so not
Extra High.

PROMPT: Step 6 — Launch Catalog: Foundations
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — five foundations entries
with cited golden values, and the contract's first end-to-end use. PICK:
Opus 5.5 is S in coding and knowledge and beats Fable 5.1 on the cost
tie-break (HLE 61.4%). EFFORT: High for correctness-sensitive numerics and
citation research on textbook formulas; thinking on, single agent.

PROMPT: Step 7 — Model Cards and Documentation Preview
MODEL: GPT-6 Sol
BACKUP: Claude Sonnet 5.5
PLATFORM: Codex
EFFORT: Medium
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — a Sphinx site with generated
model pages, Sybil, a CI job and the Read the Docs preview. PICK: GPT-6
Sol is S in coding and agentic work and wins the coverage tie-break over
GPT-6 Astra (Terminal-Bench 4.0 43.9). EFFORT: Medium, the ladder value,
for mature tools in a decided stack; thinking on.

PROMPT: Step 8 — Launch Catalog: Fixed Income
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — six fixed-income entries on
the date layer, with Treasury-cited golden values and QuantLib oracles.
PICK: Opus 5.5 is S in coding and knowledge and beats Fable 5.1 on the
cost tie-break (SciCode 66.9). EFFORT: High for multi-convention bond
numerics; textbook formulas checked by an oracle, so not Extra High.

PROMPT: Step 9 — Launch Catalog: Derivatives and International
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — option pricing with Greeks
and implied volatility, trees, swaps and parity, checked by two oracles.
PICK: Opus 5.5 is S in coding and knowledge and beats Fable 5.1 on the
cost tie-break (SciCode 66.9). EFFORT: High because a carry or sign error
is silent; standard formulas under oracles, so not Extra High.

PROMPT: Step 10 — Launch Catalog: Equity, Corporate and Accounting
MODEL: GPT-6 Sol
BACKUP: Claude Opus 5.5
PLATFORM: Codex
EFFORT: Medium
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — seven closed-form
valuation, corporate-finance and accounting entries reusing existing
numerics. PICK: GPT-6 Sol is S in coding and wins the coverage tie-break
over GPT-6 Astra (SciCode 57.6). EFFORT: Medium, the ladder value, for
short documented formulas under a settled contract; thinking on.

PROMPT: Step 11 — Launch Catalog: Portfolio and Performance
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — frontier closed forms, a
dozen performance ratios with stated definitions, and linked attribution.
PICK: Opus 5.5 is S in coding and knowledge and beats Fable 5.1 on the
cost tie-break (HLE 61.4%). EFFORT: High for definitional precision and
linking identities; each formula is published, so not Extra High.

PROMPT: Step 12 — Launch Catalog: Risk and Econometrics
MODEL: Claude Opus 5.5
BACKUP: GPT-6 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — VaR and ES methods,
likelihood-ratio backtests, and an OLS adapter behind the econometrics
extra. PICK: Opus 5.5 is S in coding and knowledge and beats Fable 5.1 on
the cost tie-break (HLE 61.4%). EFFORT: High for statistical conventions
where a silent choice changes the number; the methods are published, so
not Extra High.

PROMPT: Step 13 — 1.0.0a1 Readiness Gate
MODEL: GPT-6.1 Sol
BACKUP: Claude Opus 5.5
PLATFORM: Codex
EFFORT: Medium
THINKING: On
CONVERSATION: New
RATIONALE: TASK: knowledge, agentic secondary — an evidenced release
checklist, a TestPyPI rehearsal and the ADR-0010 floor re-check. PICK:
GPT-6.1 Sol is A in knowledge and ties GPT-6 Sol on every rating and
price, with the higher AA Intelligence Index (51.8). EFFORT: Medium, the
ladder value, because the maintainer owns the GO and Phase 1's gate is the
pattern; thinking on.

PROMPT: Step 14 — 1.0.0a1 Release
MODEL: GPT-6 Sol
BACKUP: Claude Sonnet 5.5
PLATFORM: Codex
EFFORT: Medium
THINKING: On
CONVERSATION: New
RATIONALE: TASK: agentic, coding secondary — executing the gated release:
version, merge, tag, approval, publication and verification. PICK: GPT-6
Sol is S in agentic work and coding and wins the coverage tie-break over
GPT-6 Astra (Terminal-Bench 4.0 43.9). EFFORT: Medium, the ladder value,
because the gate removed the judgement calls and each action is verified;
thinking on.

PROMPT: Step 15 — QA and Verification Script
MODEL: GPT-6 Sol
BACKUP: Claude Sonnet 5.5
PLATFORM: Codex
EFFORT: Medium
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — the phase's verify script,
its pytest twin, the matrix entry and a live walk of every criterion.
PICK: GPT-6 Sol is S in coding and agentic work and wins the coverage
tie-break over GPT-6 Astra (Terminal-Bench 4.0 43.9). EFFORT: Medium, the
ladder value, for numerous but mechanical checks translated from Phase 1's
script; thinking on.
```

---

## Not in scope (from product roadmap)

The parent ROADMAP's Phase 2 section carries no separate "Not in scope"
list; these items are deferred by its phase boundaries and its §6 "Out of
Scope" ([`docs/roadmap/ROADMAP.md`](ROADMAP.md)):

- The data layer: providers, credentials and redaction, the licence-aware
  cache, vintages, the semantic catalog, live bindings, the 18 live-data
  entries, and the monetary-policy suite that must match the 0.2.x
  characterization fixtures. Phase 3 owns them; this phase reserves
  `ModelSpec.bindings` and the manifest's `data_sources` for them.
- Every generated surface: the CLI, the REST API, the MCP server,
  `registry.json` and `openapi.json`, the cross-surface parity suite,
  exports (CSV, XLSX, reproducibility bundles) and the optional AI
  narrative. Phase 4 builds them on the schemas, canonical JSON and
  `describe()` this phase delivers.
- The web app, the production documentation (tutorials, how-to guides,
  the 0.2.x → 1.0 migration guide, marimo examples, sphinx-gallery), Read
  the Docs' `stable` cutover and the 1.0.0 launch. Phase 5 owns them.
- Premium and bring-your-own-key data (Phase 6); syllabus crosswalks, the
  coverage matrix, the learning layer and every next-wave catalog entry
  (Phase 7); accounts and paid features (Phase 8).
- Personalised advice, trading features, licensed-data redistribution and
  the other §6 exclusions. They stay excluded in every phase.

Additionally not in scope for this phase:

- Constrained portfolio optimization (long-only, robust, resampled).
  Phase 7 adds it through an adapter (ROADMAP §4 7.3);
  `portfolio.mean_variance` is closed-form with short sales allowed.
- Attribution linking beyond Carino's method, fixed-income attribution
  and the cash conversion cycle. Phase 7's `performance` and `corporate`
  batches own them.
- quantstats as a test oracle. Its closure brings yfinance (a library-only
  data client whose terms bar automated collection) and matplotlib into
  the test environment for formulas SciPy/NumPy oracles and recomputed
  values already cover. Step 11 rejected empyrical-reloaded.
- linearmodels and arch as test oracles. They arrive with Phase 3's GARCH
  and estimator entries; Phase 2's OLS uses NIST's certified values and an
  independent NumPy recomputation.
- New extras for Polars or pyarrow. ADR-0008 keeps them caller-owned, and
  conversions import them lazily.
- Read the Docs pull-request builds and production documentation
  monitoring. The CI `docs` job is the gate; Phase 5 adds monitoring.
- A SIFMA US bond-market calendar. `holidays` does not provide one; a later
  step adds it with a source.
- Announcing `1.0.0a1`. Phase 5's launch announces 1.0.
- The GitHub Sponsors listing (issue #68,
  ROADMAP 8.1), the Scorecard dispositions (issue #62) and the 0.2.6 CVE
  id (issue #52). Each has its owner outside this phase.

Carried over during execution — the Triage rule's carry-over checklist:
each upstream gap or deferred finding, the step whose `<task>` was
patched, and the step or phase that owns it. Phase 3's roadmap carries
forward whatever is still open here.

- From Phase 1's carry-over list (Step 6's ADR confirmations), absorbed by
  this roadmap:
  - the Pyodide import smoke test of the core wheel (ADR-0002) — Step 1,
    extended to run models in Step 4;
  - the `FutureWarning`-based deprecation class (ADR-0003) — Step 1; and
    `registry.validate()` rejecting a released id that is missing or
    reused — Step 3, with the ledger filled in Step 14;
  - a docs build with warnings as errors, executed notebooks and Sybil
    collecting Markdown examples (ADR-0007) — Step 7;
  - every release step re-checking NumPy's and SciPy's `requires_python`
    and raising the floor if either moved (ADR-0010) — Steps 13 and 14;
  - every release step checking its tag against ADR-0003's milestone
    table — Steps 13 and 14.
- From Phase 1's Not-in-scope list: the model registry, ADR-0008 and the
  catalog (Steps 1–12); the documentation site and its preview (Step 7);
  the first PyPI upload of 1.0 and its readiness gate (Steps 13 and 14).
- From Step 1 (2026-10-09). Patched: Step 3's `core/context.py`
  requirement. Step 1 shipped `warn()` in `core/warnings.py`, which
  `find_root` already calls; Step 3 makes it the one collector-aware
  `warn()` instead of adding a second. Owned by Step 3.
- From Step 3 (2026-10-09). Done in the step: `warn()` is the one in
  `core/context.py`, and `find_root` records into the collector. Patched:
  Step 3's array-types requirement (an alias fixes no length, because stacked
  constraints do not narrow), Step 4's context (the Step 3 API it builds on) and
  Step 6's package layout (`models/__init__.py` exists) and Step 14's ledger
  requirement (a released id reused by another model is invisible without a
  fingerprint). Open: pydantic's lax mode accepts `True` for a float field and a
  number for a date, so `rate=True` runs as 100% and `when=86400` as
  1970-01-02; the fix belongs in the unit markers of Step 1 (issue #75, label
  `bug`).
- From Step 6 (2026-10-10). No contract change was needed: the five
  foundations models fit Steps 1-5 as built, with cross-field rules expressed
  as `model_validator`s plus `strategies.OVERRIDES` entries, as Step 5
  designed. Done in the step, as Step 5 planned for it: the `models/` coverage
  floor now fails when nothing is measured, and the contract and golden suites
  drop their empty-registry skips, guarded by
  `tests/models/test_registry_is_not_empty.py`. Patched: the context of Steps
  7-12 (the Step 6 facts: shared numerics, the out-of-bounds rule, overrides,
  literal markers, short reference keys).
- From Step 11 (2026-10-11). Contract change, the smallest that works: the
  annualization helper Step 6 left in `models/foundations/returns.py` moved to
  `core/descriptive.py` as `annualized_return`, beside the new
  `compound_return` and `has_spread`; `foundations.returns` calls it, and
  every golden case stays green. The one behaviour change: an annualized
  return within 1e-12 (relative) above 100 is now clamped to 100 rather than
  raised as DomainError. Patched: Step 6's `foundations.returns` requirement
  and Step 12's context. empyrical-reloaded was not added: 0.5.12, its latest
  release, imports `pytz` without declaring it (pandas 3 no longer installs
  it), pins `peewee<3.17.4` and rejects `annualization` in its capture
  functions. `performance.risk_adjusted`'s oracle tests use
  `scipy.stats.linregress` and an independent NumPy recomputation instead; a
  local, uncommitted overlay with `pytz` agreed with empyrical on all ten
  measures it implements within 7e-14 over 500 random series. Owned by Step
  15, which carries the decision into `docs/phase02-qa-findings.md`.

- From Step 13's first gate attempt (2026-10-12). High model-error #89:
  US 30/360 long-first coupon timing in shared `_bonds.py` disagrees with
  QuantLib; the full suite fails its duration oracle, and price also differs.
  Owner: Nathan Ramos, CFA; a dedicated `fix/` branch before the alpha,
  golden regression, public erratum and version review, bumped `.devN`,
  then a fresh readiness rehearsal. Policy issue #65 is now due because
  Python 3.15 became final. Step 13/14 task contexts are patched; neither
  step is marked complete by this attempt. Docs landing text is corrected
  in the gate; README correction remains in Step 14's permitted release diff.
  Remediation PRs: #91 (bond correction, model versions 2, dev2, public
  erratum and golden/oracle regressions) and #92 (Python 3.15 final on all
  three operating systems, matching classifier/verifier, dev3). A fresh
  Step 13 conversation must rehearse the resulting candidate and obtain
  its own maintainer decision; the dev1 NO-GO remains historical evidence.

- From Step 15 verification (2026-10-14). The randomized Phase 1 post run
  exposed finite-sample coverage assertions in Step 5's strategy tests.
  Fixed in this step's PR with valid-witness searches for optional/enum
  choices, union tags and examples; Step 5's task is patched above. No
  runtime model, draw strategy or numerical contract changes. Phase 1's
  clean-wheel environment now explicitly uses the project interpreter,
  preserving the check and recording the change in its post-merge addendum.

---

_This roadmap is the execution plan for Phase 2. Each step's
`**Status:**` line is flipped by that step's own PR (Status rule), so
this file on `main` is the phase's ledger — `grep -n '^\*\*Status:\*\*'`
reports progress. After all steps and verification pass, and every
finding has a destination, Phase 2 is complete — declared with the line
"Phase 2 is complete. You can now move on to Phase 3." and nothing after
it — and Phase 3 (Data Platform & Free Sources) inherits `pyeconomics
1.0.0a1` on PyPI: a registry whose `ModelSpec` reserves the `bindings` its
providers fill and whose manifests reserve the `data_sources` its vintages
populate, canonical JSON and 2020-12 schemas, the golden and property
harness its 18 live-data entries must pass, 32 verified data-free models
to build on, a documentation preview that renders every new model's card,
and `verify-phase02.sh` as the template for `verify-phase03.sh`._

## Post-merge addendum (2026-10-14) — Phase 3 changes to verify-phase02.sh

Phase 3's Cross-phase verification rule: a Phase 3 pull request that
legitimately invalidates one of this phase's checks narrows the check to the
invariant it protected, never deletes it, and adds one line here.

- V14.3 (`--post`, Phase 3 Step 2): the published-install check runs the
  `v1.0.0a1` tag's own `scripts/smoke.py` (`git show v1.0.0a1:scripts/smoke.py`)
  against PyPI's `1.0.0a1`, as `release-smoke.yml` checks out its tag's
  scripts, because the working tree's smoke script now imports
  `pyeconomics.data`, which `1.0.0a1` does not have. The core, extras and
  stable 0.2.6 installs and their assertions are unchanged.

## Post-merge addendum (2026-10-29) — Phase 5 changes to verify-phase02.sh

- Harness (Phase 5 Step 1, issue #217): the script refuses a bash older
  than 4 (exit 2, `verify needs bash >= 4`), because its associative
  arrays need bash 4 and macOS's `/bin/bash` 3.2 stopped at the first check
  and exited 0; its `EXIT` trap now keeps a crash's status. No check
  changes; `tests/repo/test_verify_portability.py` holds both.
