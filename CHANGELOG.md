# Changelog

All notable changes to pyeconomics 1.0 and later are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and versions follow [PEP 440](https://peps.python.org/pep-0440/) with
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) meaning (ADR-0003).
Pre-releases of 1.0.0 carry no stability promise. Deprecations are listed under
"Deprecated" at least one minor release before their removal.

The 0.2.x history (0.1.0 to 0.2.6) is in the
[0.2.x changelog on `legacy/0.2.x`](https://github.com/pyeconomics-dev/pyeconomics/blob/legacy/0.2.x/markdown/CHANGELOG.md).

## [Unreleased]

### Added

- Seven models through the `equity`, `corporate` and `accounting` entry points:
  `equity.dividend_discount`, `equity.free_cash_flow`,
  `corporate.cost_of_capital`, `corporate.capital_budgeting`, `corporate.leverage`,
  `accounting.financial_ratios` and `accounting.scoring_models`, with cited
  golden cases, invariant tests and generated model cards.

- A Sphinx documentation preview with generated model cards, an executed
  tutorial, Sybil-tested examples and a warnings-as-errors CI build. Read the
  Docs version `main` previews 1.0 while `stable` and `latest` keep serving 0.2.x.

- The first catalog models, registered through the `foundations` entry point
  in the `pyeconomics.models` group:
  - `foundations.time_value`: present and future values of sums, level and
    growing annuities and perpetuities; the five-key solve for periods, rate,
    present value, payment or future value; NPV and IRR; XNPV and XIRR of
    dated cash flows (ACT/365 Fixed); and level-payment amortization
    schedules.
  - `foundations.returns`: holding-period returns; arithmetic, geometric and
    harmonic means; annualized, log and real (exact Fisher) returns.
  - `foundations.risk_statistics`: sample volatility and its annualization,
    semideviation below the mean and below a target, adjusted skewness (G1)
    and excess kurtosis (G2), and maximum drawdown with its peak and trough.
  - `foundations.hypothesis_tests`: one-sample, two-sample (pooled and Welch)
    and paired t tests, the z test, and chi-square and F tests of variances,
    from summary statistics, with p-values, critical values and confidence
    intervals.
  - `foundations.simulation`: seeded Monte Carlo of geometric Brownian motion,
    with antithetic variates, and the nonparametric bootstrap.
- The fixed-income catalog models, registered through the `fixed_income` entry
  point in the `pyeconomics.models` group, on the Step 2 date layer:
  - `fixed_income.bond_pricing`: full and flat price and accrued interest from
    a yield (street convention, or the Treasury's simple interest over the
    first fraction of a period), with regular, short-first and long-first
    coupon periods under ACT/ACT (ICMA), US 30/360 and 30E/360; the yield to
    maturity from a flat or full price; the yield to a call; and the yield to
    worst over a schedule of calls. It reproduces every price example in
    31 CFR Part 356, Appendix B, section II.
  - `fixed_income.money_market`: bank discount rate to and from price
    (ACT/360), the money-market (CD-equivalent) yield, the Treasury investment
    rate with its formula for bills of more than half a year, and the
    effective annual and holding-period yields.
  - `fixed_income.curve_bootstrap`: spot rates, discount factors and one-period
    forwards bootstrapped from par yields, par yields and forwards from spot
    rates, and the forward rate between two maturities.
  - `fixed_income.duration`: Macaulay and modified duration, effective and
    key-rate duration off a spot curve, and DV01.
  - `fixed_income.convexity`: analytical and effective convexity and the
    duration-and-convexity price-change estimate beside full repricing.
  - `fixed_income.credit_spread`: expected loss, the credit triangle between
    spread and hazard rate, survival probabilities and the approximate excess
    return from a spread.
- The derivatives catalog models, registered through the `derivatives` entry
  point in the `pyeconomics.models` group. Their outputs are formula values
  for the inputs given, not trading advice:
  - `derivatives.forwards`: forward prices by cost of carry (income and
    convenience yields, storage costs, and known income or storage as present
    values), the value of an existing long or short forward, and forward
    exchange rates by covered interest parity with money-market interest on
    each currency's day count, with the forward points.
  - `derivatives.interest_rate_swap`: the value to the fixed payer and
    receiver, par swap rate and annuity factor of a single-curve swap, from
    accrual fractions and discount factors, accrual fractions and a zero
    curve, or payment dates on a day count and a zero curve.
  - `derivatives.black_scholes_merton`: European calls and puts with a
    continuous dividend yield, with delta, gamma, vega, theta, rho, dividend
    rho and the put-call parity residual, and the implied volatility by a
    bracketed solver over [0.001, 5] that returns null with a warning outside
    the no-arbitrage bounds.
  - `derivatives.binomial_tree`: Cox-Ross-Rubinstein trees of up to 5,000
    steps for European and American calls and puts with a dividend yield, with
    delta and gamma from the tree.
  - `derivatives.futures_fx_options`: Black-76 options on futures and
    Garman-Kohlhagen currency options, each with Greeks (a rho for each
    currency's rate) and implied volatility.
- The international catalog model, registered through the `international`
  entry point: `international.parity_conditions`, with covered and uncovered
  interest parity, relative and absolute purchasing power parity, the
  international Fisher effect and the real exchange rate and its change.
- Golden files for the six models, citing Hull (2018), Haug (2007), Black and
  Scholes (1973), Black (1976), Garman and Kohlhagen (1983), Cox, Ross and
  Rubinstein (1979) and identities; property tests for every invariant,
  cross-entry tests against `derivatives.black_scholes_merton` and
  `derivatives.forwards`, and oracle tests against QuantLib and vollib, which
  joins the test dependency group.
- `pyeconomics.core.curves`: zero-rate interpolation (linear, flat beyond the
  nodes, one time or many), discount factors off a zero curve, forward rates and par rates, for
  the fixed-income models and Step 9's swap valuation.
- `pyeconomics.core.cashflows` (growth, annuity and perpetuity factors,
  present values summed without overflow, and the IRR) and
  `pyeconomics.core.descriptive` (corrected two-pass mean and variance,
  semideviations, G1 and G2, maximum drawdown), the numerics later domains
  share.
- Golden files for the five models, citing Microsoft's Excel function
  examples, NIST's StRD and e-Handbook, Glasserman (2003) and Efron and
  Tibshirani (1993); property tests for every invariant; SciPy oracle tests.

- Date arithmetic with end-of-month rules, six day-count conventions including
  irregular ICMA coupon periods, backward coupon schedules with short or long
  front stubs, and five holiday calendars with business-day adjustments.
- `holidays>=0.106` as an audited runtime dependency; QuantLib as a test-only
  oracle for day counts, schedules and calendars. The installed-wheel and
  Pyodide smoke checks exercise the date layer.
- Governance and community files: README with status banner and notices,
  CONTRIBUTING, Contributor Covenant 3.0 Code of Conduct, SECURITY policy,
  CITATION.cff, CODEOWNERS, issue forms, defect-class labels, `AGENTS.md` and
  `CLAUDE.md` for coding agents, and funding hooks (`.github/FUNDING.yml`,
  `funding.json`).
- ADR-0008, numerical conventions: decimal rates, the unit vocabulary and
  default bounds, compounding, day counts and calendars, tolerances, seeded
  randomness, arrays and tabular data, pandas 3 semantics, non-finite and
  undefined results, root finding, canonical JSON numbers, the error and
  warning taxonomy, and the runtime floors.
- `pyeconomics.core`, the date-free conventions: unit kinds with `Annotated`
  markers (`Rate`, `Money`, `Years` and the rest) that export `x-unit` and
  reject NaN and infinity; percent and basis-point converters and
  formatting; `Frequency`, `Compounding` and rate and discount-factor
  conversions; `Tolerance`; seeded `PCG64` generators; a bracketed Brent
  root finder; and the exceptions (`PyeconomicsError` and its subclasses)
  and warnings (`ModelWarning`, `PyeconomicsDeprecationWarning`, a
  `FutureWarning`).
- Runtime dependencies: pydantic 2.12, NumPy 2.4, SciPy 1.18 and pandas 3.0
  or later (floors Pyodide 314.0.7 can satisfy), with reviewed licence
  exceptions for numpy, scipy, pandas and python-dateutil.
- `scripts/smoke.py` and a `pyodide` CI job that installs the wheel in
  Pyodide 314.0.7 and runs it, beside the clean-venv run in the package job.
- The model specification: `ModelSpec` with `Reference`, `Evidence`,
  `CostClass`, `Invariant`, `Example`, `ChartSpec`, `ChangelogEntry` and
  `Alias`; the `@model` decorator; and `Model` objects that validate their
  inputs, run a pure `compute` and validate their outputs. `ModelInputs` and
  `ModelOutputs` are frozen, closed to unknown fields and reject NaN and
  infinity. Array fields (`RateArray`, `MoneyArray`, `DateArray` and the rest)
  accept lists, tuples, NumPy arrays, pandas and Polars columns and Arrow
  streams. A family of formulas is a discriminated union on `calculation`.
- `pyeconomics.registry` with `ids`, `get`, `models`, `domains`, `resolve` and
  `validate`. Models register through the `pyeconomics.models` entry-point
  group; discovery is lazy, ordered, and fails closed on a duplicate id or
  alias, a malformed entry point or a module that fails to import. An alias
  resolves to its canonical model and warns with
  `PyeconomicsDeprecationWarning`. `validate()` rejects an incomplete
  specification with one line per problem, each naming the model and the rule,
  and checks the released-id ledger (ADR-0003).
- `pyeconomics.core.collect_warnings`, which the runner installs so `warn()`
  records into the result; outside a run `warn()` still issues the warning.
- Purity guards for `src/pyeconomics/models/`: the `model-purity` semgrep rule
  (no I/O, clock, environment, network, print, logging or global randomness)
  and an import allowlist test.
- Results: `pyeconomics.run(model_id, inputs=None, /, **fields)` and
  `pyeconomics.run_batch(model_id, rows)` return an immutable `Result` (or
  `BatchResult`) holding the inputs, the outputs, the warnings the model
  recorded and a manifest. A batch takes a pandas or Polars DataFrame, an
  Arrow PyCapsule stream or an iterable of mappings, at most 100,000 rows.
  `Result` converts to a dict, canonical JSON, pandas, Polars, Arrow and
  Parquet; Polars and pyarrow stay optional and are named in the error when
  missing. A table has `inputs.<field>`, `outputs.<field>` and `result_sha256`
  columns, and a single result's Arrow and Parquet output carries its manifest
  in the schema metadata (`pyeconomics.manifest`).
- The manifest: schema version, model id and version, the versions of
  pyeconomics, NumPy, SciPy, pandas and pydantic, the seed and bit generator
  of a stochastic model, an empty `data_sources` list for Phase 3, and the
  SHA-256 of the canonical JSON of the inputs and of the result body. It holds
  no clock time, host, user, path or environment value, so two runs of the same
  inputs give the same bytes.
- `pyeconomics.core.canonical_json`: RFC 8785 canonical JSON, implemented with
  the standard library and checked against the RFC's number samples, its
  key-sorting example and the `rfc8785` package.
- `pyeconomics.core.input_schema` and `output_schema`: JSON Schema 2020-12 for
  every model, with a stable `urn:pyeconomics:model:<id>:<version>:input|output`
  `$id`, `x-unit` on every numeric field, bounds, descriptions, examples, and a
  `oneOf` with a `discriminator` mapping for families of calculations.
- `pyeconomics.registry.describe(id)`: one JSON-ready description of a model
  (specification, both schemas, the card's Markdown) for Phase 4's registry
  export.
- Model cards (`ModelCard`, `Result.card()`): title, formula, variables tables,
  assumptions, limitations, evidence status, a worked example, references, a
  curriculum-mapping placeholder, the changelog and a notice, rendered as MyST
  Markdown.
- `Result.plot()` builds Plotly figures from a model's chart specifications.
  Plotly is the new `plot` extra (also in `all`) and is imported on demand;
  without it the error names `pyeconomics[plot]`.
- `scripts/smoke.py` validates the registry and runs one model per registered
  domain twice, requiring identical results (`--all`, `--min-domains N`,
  `--extras`); `release-smoke.yml` runs it, from the release's own tag and
  outside the checkout, with `--min-domains 11`.
- Test-only dependencies: `rfc8785` and `jsonschema` (oracle and validator),
  `plotly`, and `polars` and `pyarrow` (so the conversions are tested against
  the real libraries).
- The verification harness every catalog model must pass (test-only, not part of
  the wheel). Golden files (`tests/golden/<domain>/<name>.toml`, format in
  `tests/golden/README.md`) hold cited cases with edge cases and per-output
  tolerances, are read with `tomllib` only and reject unknown keys; the harness
  requires a file for every registered model, three cases with an edge case or a
  recorded reason, a source and locator for each case, and outputs within
  ADR-0008's tolerance through `pyeconomics.run`. A citation guard rejects the
  CFA Program curriculum and allows the Financial Analysts Journal. The
  `invariant` and `oracle` pytest markers, and a meta-test that holds every
  declared invariant to a marked property test. `tests/strategies.py` generates
  valid inputs from a model's fields, and a contract suite fuzzes every
  registered model for bounds, documented errors, determinism and round trips.
  `scripts/checks/coverage_floors.py` holds branch coverage to 95% on `core/` and
  90% on `models/` in CI, and `scripts/new_model.py <id>` scaffolds a model, its
  golden file and its property test. CONTRIBUTING and the pull request template
  carry the mechanics and a model checklist.

### Changed

- The version on `main` is `1.0.0a1.dev1`, the milestone it builds towards
  (Phase 2's version rule); `CITATION.cff` names the same version.
- `import pyeconomics` exposes `pyeconomics.registry`, so it now imports
  `pyeconomics.core` (pydantic, NumPy, SciPy and pandas). It still discovers no
  model.
- `pyeconomics.core.warn` moved to `pyeconomics.core.context`; the import from
  `pyeconomics.core` is unchanged. `ModelNotFoundError` lists close matches, and
  `RegistryError` carries its `problems`.

## [1.0.0.dev1] - 2026-10-07

The 1.0 skeleton and its publishing pipeline, released to TestPyPI only.

### Added

- `src/pyeconomics/` package skeleton with a typed marker, version
  `1.0.0.dev1` read through `importlib.metadata`, and the ADR-0002 extras as
  empty placeholders.
- A PEP 621 `pyproject.toml` on the `uv_build` backend, requiring Python 3.12
  or later, with `uv.lock` and an exported `pylock.toml`.
- Architecture decision records ADR-0001 to ADR-0007, ADR-0009 and ADR-0010.
- Per-step security gate run by prek: gitleaks, bandit, semgrep with project
  rules, `pip-audit` and a runtime licence allowlist, mirrored in CI with
  trufflehog, CodeQL, zizmor, dependency review and OpenSSF Scorecard.
- Quality toolchain: ruff with every rule family, mypy strict, pytest with
  hypothesis, syrupy, pytest-benchmark, branch coverage, pytest-socket and
  doctests.
- CI on Ubuntu, Windows and macOS for Python 3.12 to 3.14, with package,
  lockfile, pull-request-title and DCO checks.
- Release workflow publishing through PyPI Trusted Publishing with
  attestations, and a post-publish install smoke test.

### Changed

- Licence: Apache-2.0 from 1.0. Releases up to and including 0.2.x remain MIT.
- The repository moved to `pyeconomics-dev/pyeconomics`.

### Removed

- The 0.2.x code from `main`; it continues on `legacy/0.2.x`.

[Unreleased]: https://github.com/pyeconomics-dev/pyeconomics/compare/v1.0.0.dev1...HEAD
[1.0.0.dev1]: https://github.com/pyeconomics-dev/pyeconomics/tree/v1.0.0.dev1
