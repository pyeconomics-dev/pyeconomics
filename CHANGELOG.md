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

- International data providers: IMF, OECD, ECB, BIS and Eurostat via the optional
  `sdmx` extra; World Bank v2 and DBnomics REST clients. Structure-validated
  SDMX keys, confined sessions, and series-specific licence restrictions.

- ADR-0011, the data platform: eighteen accepted decisions on the data
  model, missing values, vintages, licence classes and `llm_use`, the
  provider contract, the HTTP stack, extras, credentials, redaction, the
  cache (FRED and ALFRED are never written to disk), the catalog, bindings
  and manifest schema 2, recorded responses and live verification.
- `pyeconomics.data`, the data layer's value types: `Series` and `Table`
  with their metadata, `ObservationFrequency`, `SeasonalAdjustment` and the
  unit record, a source's `Terms` and `CachePolicy`, the `Vintage` selector
  and the `DataError` taxonomy. Frames index periods by their last day, mark
  missing values `None`, carry ALFRED-style real-time periods, and
  round-trip losslessly through canonical JSON and pandas.
- `pyeconomics.core.provenance`: `DataSource`, the record a manifest will
  carry for each data source, with `RealtimePeriod`, `LicenceClass` and
  `LlmUse`, exported from `pyeconomics.core`.
- The key chain: `pyeconomics.data.resolve_key` reads a provider's key from
  an argument, the provider's `<PROVIDER>_API_KEY` variable, a strictly
  parsed `.env` file in the user configuration directory (never overriding
  the real environment), or the OS keyring, and returns it as a `Secret`,
  which prints only a mask and refuses pickling and JSON. `has_key` checks
  for a key without reading it. A missing key raises `CredentialError`
  naming the variable, the keyring command and the new "Keys and
  configuration" guide.
- Configuration: `pyeconomics.data.settings()` and `configure()` read a
  layered `pyeconomics.toml` (the user configuration directory, then the
  working directory, then `PYECONOMICS_*` variables) holding the mode, the
  offline switch, the cache directory, the SEC contact and per-provider
  time-to-live overrides. A setting named like a credential is refused, and
  errors never repeat a value or a path.
- Redaction: `pyeconomics.data.redaction` scrubs every key read, and its
  URL-encoded forms, from the log records of every logger, from URLs and
  headers, and from data-layer errors and the new `DataWarning`; failures
  can be re-raised without the original exception attached.
- The `[keyring]` extra (keyring 25.7 or later), which `[all]` includes, and
  `platformdirs` as a runtime dependency.
- The provider contract: a source is a `pyeconomics.data.DataProvider` with a
  `ProviderInfo` (id, terms, authentication, exact HTTPS hosts, published rate
  limits, capabilities, extra, platforms) and a typed pipeline from a bounded
  `Query` through `build_requests`, an exchange and `parse` to a `Series` or a
  `Table`, plus `search`, `describe` and `vintages`. The public operations are
  final: they refuse a source hosted mode may not serve before any request, and
  map each final status to the error taxonomy (401 and 403 to
  `CredentialError`, 404 to `SeriesNotFoundError`, 429 to `RateLimitError`, 5xx
  to `TransportError`, anything else to `ResponseError`).
- `pyeconomics.data.registry` (`ids()`, `get()`, `installed()`, `validate()`):
  providers register through the `pyeconomics.providers` entry-point group, and
  `validate()` reports each broken rule as `<id>: [<rule>] <detail>`. The
  released-provider ledger exists and is enforced; it is empty until the first
  providers ship.
- The transport: `HttpTransport` on urllib3 and the operating system's trust
  store, the only code that opens a socket, builds a URL or reveals a key. It
  refuses `http://` and every host outside a provider's allowlist, redirects
  included; caps response sizes, including decompressed ones; retries with
  exponential backoff and full jitter, honouring `Retry-After`; holds each
  provider to its declared limits with a sliding-window limiter; and raises
  scrubbed errors with no exception context. `ReplayTransport` serves recorded
  cassettes offline.
- Library and hosted mode (`pyeconomics.data.Mode`, `configure(mode="hosted")`):
  hosted mode refuses every source not classed hosted-safe or user-supplied at
  fetch, whatever called it.
- Cassettes and `scripts/record_cassettes.py`: recorded responses as canonical
  JSON, scrubbed of every key, credential parameter, header and cookie, kept to
  24 observations per series and 32 KiB, synthetic for a source that is not
  hosted-safe or forbids storage, and scanned for secrets. The shared provider
  contract suite replays them, and `pytest -m live` runs it against the real
  APIs.
- "Writing a provider" and a generated reference page per provider, built
  offline; a design spike shows a session-based source (Bloomberg's Desktop API)
  fits the contract unchanged.
- `urllib3` and `truststore` as runtime dependencies (`truststore` is skipped on
  Emscripten, where the browser handles TLS).
- The licence-aware cache and offline mode, `pyeconomics.data.cache`: a fetch from
  a source whose terms allow storage is kept in one SQLite file in the cache
  directory (created on the first write, owner-only, canonical JSON, never a
  pickle) and served within the provider's `ProviderInfo.ttl_seconds` or the
  user's `PYECONOMICS_TTL_<PROVIDER>`; a closed past vintage is kept until the
  1 GiB cap evicts the least recently used. A source or series whose terms forbid
  storage (FRED and ALFRED among them), and `user-supplied` data, has no cache
  path at all: no read, no write, no file. `configure(offline=True)` or
  `PYECONOMICS_OFFLINE=1` serves cached entries only, marks each record
  `served_offline` with its original retrieval time, and raises `OfflineError` on
  a miss; `search`, `describe` and `vintages` refuse to run offline. An entry that
  fails its SHA-256 or does not validate back into a frame is deleted and
  reported as `cache_entry_discarded`; a newer or foreign database is left
  untouched. `info()`, `entries()`, `clear()` and `path()` inspect it without
  returning a payload, `DataProvider.fetch_with_origin` returns the frame with a
  `DataSource` record, and `cache.memo()` serves repeats from memory within one call.
- The first four providers, registered in the `pyeconomics.providers` group:
  - `fred`: FRED and ALFRED. Series metadata, observations, search and vintage
    dates through API v1 (the key in the query string); `as_of`,
    `first_release` and `all` vintages through ALFRED's real-time periods; a
    whole release as a table through API v2 (`release:<id>`, the key in an
    `Authorization` header, paged by cursor). Each series' copyright tags set
    its notice: a pre-approval series, and every series sourced from Moody's,
    says its owner's permission is needed beyond personal use. `library-only`,
    never stored, and `llm_use` forbidden, as FRED's terms read.
  - `bls`: the Bureau of Labor Statistics. API v2 with the registration key in
    the request body, or keyless API v1 at its lower limits when no key is set;
    queries split into 50 series and 20 years (25 and 10 keyless); footnotes
    such as preliminary values kept as notes; the access date in the notice.
  - `bea`: the Bureau of Economic Analysis. NIPA, NIUnderlyingDetail, Regional
    and ITA tables and lines; thousands separators and BEA's `(NA)`-style
    markers parsed; every frame notes `revised_data`, because the API serves
    only current estimates.
  - `census`: the Census Bureau. ACS 1- and 5-year estimates for one place,
    the economic indicators time series and international trade, with the
    geography checked against an allowlist; a refused key is never followed to
    the page that echoes it.
- Frame metadata carries `notes`: what the source says about the data, each a
  snake_case code and a detail.
- Provider seams: per-request key placements (`KeySlot`,
  `Request.key_placement`), `DataProvider.sends_key` and
  `credentials.withheld()` for a source whose key is optional, rate limits that
  hold only without a key, paging (`DataProvider.next_page`),
  `ProviderInfo.follow_redirects`, and keyless and simulated recorder cases.
- `providers-live.yml`, the weekly live run of every provider against its real
  API in the locked-down `providers-live` environment, which opens one
  `provider-live` issue when it fails, and `providers-heartbeat.yml`, the daily
  check that the live run keeps succeeding.

### Fixed

- Numeric unit markers reject Python and NumPy booleans; date fields reject
  numeric epoch timestamps, including array elements (#75).
- Registry validation requires units and bounds on numeric Literal fields (#81).
- Shared IRR recognizes roots at inclusive bracket endpoints without changing
  the smallest-root policy (#85); see the public erratum.

### Changed

- Begin the Phase 3 baseline at `1.0.0a2.dev1`.
- `foundations.time_value`, `corporate.capital_budgeting` and
  `performance.return_measurement` advance from model version 1 to 2 for the
  IRR endpoint correction. Permanent model ids remain unchanged.

## [1.0.0a1] - 2026-10-13

### Fixed

- US 30/360 long first-period accrual and discount times in bond pricing,
  duration and convexity (#89). The three models advance to version 2 and the
  development package to `1.0.0a1.dev2`; see the public erratum for affected
  results and a reproducible example.

### Added

- Release preparation for the first PyPI alpha, with a deterministic released-id
  ledger and read-only completeness check guarding all 32 permanent model ids.

- A fresh `1.0.0a1.dev3` TestPyPI rehearsal and readiness audit after the
  US 30/360 correction and Python 3.15 support; the rejected dev1 gate is
  preserved separately for traceability.
- The `1.0.0a1` readiness-gate evidence and draft release notes, plus an
  offline-tested `scripts/checks/python_floor.py` to re-check the newest
  NumPy and SciPy Python floors against ADR-0010 before a release.
- The documentation preview introduction now names all 32 models' domains.

- Three models through the `risk` and `econometrics` entry points, which
  complete the 32-entry data-free launch catalog:
  - `risk.value_at_risk`: VaR and expected shortfall as positive losses, as
    decimals and in money, by the parametric normal, Cornish-Fisher (modified
    VaR and the matching modified ES), historical (with a stated quantile
    rule), seeded Monte Carlo (normal or Student-t, with standard errors) and
    RiskMetrics EWMA methods, over a horizon by the square-root-of-time rule.
  - `risk.var_backtest`: Kupiec's proportion-of-failures test,
    Christoffersen's independence and conditional coverage tests, and the
    Basel Committee's traffic light with Table 2's plus factors, from a series
    of exceptions or from P&L against VaR.
  - `econometrics.ols`: ordinary least squares over statsmodels with
    classical, HC0-HC3 and Newey-West HAC standard errors, and the 0.2.x
    diagnostics (Durbin-Watson, Breusch-Pagan, Jarque-Bera, the omnibus test,
    Ramsey RESET and a VIF per regressor), with a residuals-against-fitted
    chart. Its golden cases reproduce NIST's certified results for Norris,
    Pontius, Longley, Wampler1 and Wampler2.
- The `econometrics` extra installs statsmodels (`pip install
  'pyeconomics[econometrics]'`), and `all` includes it. Without it,
  `econometrics.ols` raises `MissingOptionalDependencyError` naming the extra;
  importing pyeconomics never imports statsmodels.
- Five models through the `portfolio` and `performance` entry points:
  - `portfolio.mean_variance`: portfolio expected return and risk from weights
    and a covariance matrix (or volatilities and correlations), Merton's
    closed-form minimum-variance frontier with short sales, and the
    minimum-variance and tangency portfolios with the capital market line's
    slope. Covariance matrices are checked symmetric and positive definite.
  - `portfolio.utility`: mean-variance utility, the utility-maximizing risky
    share, the certainty equivalent of a gamble under constant relative risk
    aversion, and the Kelly fraction of a discrete bet or a continuous asset,
    with a fractional multiplier.
  - `performance.return_measurement`: time-weighted, money-weighted (periodic
    or dated flows) and Modified Dietz returns, optionally annualized.
  - `performance.risk_adjusted`: Sharpe, Sortino, Treynor, Jensen's alpha,
    beta, information ratio and tracking error, M², Calmar and up- and
    down-capture ratios, each convention stated on the model card.
  - `performance.brinson_attribution`: Brinson-Hood-Beebower and
    Brinson-Fachler allocation, selection and interaction effects, single
    period and linked over periods with Carino's method.

  Every output is a formula result for the inputs the user supplies, not
  investment advice. `pyeconomics.core` adds `compound_return`,
  `annualized_return` and `has_spread`.

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

- CI now tests Python 3.15 final on Ubuntu, Windows and macOS alongside
  Python 3.12-3.14, with its matching package classifier (ADR-0010, #65).
  CI pins uv 0.13.0 to obtain the final interpreter builds. The minimum
  Python floor remains 3.12; the development package advances to
  `1.0.0a1.dev3` for a fresh alpha readiness candidate.

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

[1.0.0a1]: https://github.com/pyeconomics-dev/pyeconomics/compare/v1.0.0.dev1...v1.0.0a1
[1.0.0.dev1]: https://github.com/pyeconomics-dev/pyeconomics/tree/v1.0.0.dev1
