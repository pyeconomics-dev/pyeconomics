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

- The `asset_pricing` domain, registered through its own entry point in the
  `pyeconomics.models` group, with two models.
- `asset_pricing.factor_regression`: an asset's excess returns regressed on the
  market (CAPM, with the security market line's expected return at a stated
  premium), the Fama-French three and five factors, Carhart's four or the
  six-factor model, through `core.least_squares`: alpha per period and annualized,
  each beta with Newey-West (default), HC1 or classical errors, R-squared and the
  residual volatility. Golden cases reproduce NIST's certified Norris, Longley and
  Wampler1 regressions; the oracle is statsmodels' OLS. It binds 60 months of the
  Ken French factors (the three-factor file by default, the five-factor file with
  profile `ff5`); the asset's returns are the user's own.
- `asset_pricing.factor_model_tests`: the Gibbons-Ross-Shanken F test that every
  alpha is zero (both covariances at divisor T, the p-value through the
  incomplete beta function) and Fama-MacBeth two-pass regressions with
  Fama-MacBeth and Shanken-corrected standard errors. The oracles are SciPy's F
  distribution and a period-by-period statsmodels recomputation. It binds ten
  years of the 25 size and book-to-market portfolios and the three or five
  factors.
- `portfolio.black_litterman`: equilibrium returns from market weights, views
  blended in with He and Litterman's or Idzorek's view uncertainty, the posterior
  returns and covariance, and the optimal weights against the covariance (the
  market's with no views) and against the posterior covariance (He and
  Litterman's). Golden cases reproduce He and Litterman's Tables 4, 6 and 7 and
  Idzorek's Tables 6 and 7; the oracle is Theil's mixed estimation by matrix
  inverses. It binds ten years of the 12 industry portfolios for the covariance.
- `portfolio.risk_based_allocation`: inverse-volatility, equal-risk-contribution
  (Newton's method on the convex log-barrier problem, to a relative tolerance of
  1e-12 in at most 200 steps) and hierarchical-risk-parity weights, with each
  asset's risk contribution and the volatility. Golden cases reproduce Maillard,
  Roncalli and Teiletche's example and López de Prado's Exhibit 7; the oracles
  are SciPy's L-BFGS-B on the same objective and a transcription of the paper's
  code. It binds ten years of the 12 industry portfolios.
- Matrix bindings: a field that is a tuple of rows, bound to a table concept with
  `AsOf.WINDOW`, reads one row per period with one value per column, and
  `Binding(..., columns=(...))` keeps only the named columns, in order. New series
  concepts for each Ken French factor, monthly: `factors.ff3_market`,
  `factors.ff3_smb`, `factors.ff3_hml`, `factors.risk_free`, `factors.ff5_market`,
  `factors.ff5_smb`, `factors.ff5_rmw`, `factors.ff5_cma` and `factors.mom`, each
  `.us.monthly`.
- SEC EDGAR (`sec_edgar`): recent filings as typed `Filing` records, and XBRL
  company concepts, company facts and frames as series, one value per calendar
  period of the chosen span (instant, quarter or year) at the filer's own period
  end. Requests carry the configured SEC contact in the User-Agent and keep to
  SEC's ten requests a second. A source that needs a contact now sends
  `pyeconomics/<version> <contact>` without the project URL, which EDGAR refuses.
- `fixed_income.curve_fitting`: Nelson-Siegel and Svensson yield curves, with an
  `evaluate` calculation (continuously compounded zero yields, instantaneous
  forwards, par yields at a stated coupon frequency and discount factors from given
  parameters) and a `fit` calculation (bounded least squares to observed zero or par
  yields from a fixed grid of starting decays, with an evaluation cap, returning
  the parameters, fitted yields and RMSE). Golden cases reproduce the Board's
  Gurkaynak-Sack-Wright file and the ECB's euro-area AAA curve, including its
  negative 2020 curve; oracles are an independent evaluation and QuantLib's
  Svensson curve. It binds the Board's GSW parameters and Treasury's par curve.
- `fixed_income.interest_rate_tree`: Kalotay, Williams and Fabozzi's (1993)
  lognormal binomial tree calibrated to a par curve, with the values of
  option-free, callable and putable bonds and their options, the option-adjusted
  spread and effective duration and convexity (the curve shifted and the tree
  recalibrated). Golden cases reproduce the paper's tree and bond values; oracles
  are KWF's own backward-induction calibration and QuantLib's curve. It calibrates
  to Treasury's par curve.
- `equity.implied_risk_premium`: the expected return at which an index level
  equals the present value of its dividends and buybacks growing for a number of
  years and then at the risk-free rate, and its premium over that rate. Golden
  cases reproduce Damodaran's published implied premiums from the inputs his
  spreadsheets state. It binds Damodaran's year-end S&P 500 inputs and Treasury's
  10-year yield.
- `equity.cape`: Shiller's cyclically adjusted price-to-earnings ratio (the real
  price over the average real earnings of the window before it), its earnings
  yield and the excess CAPE yield over a TIPS yield or the nominal yield less
  trailing inflation. It binds Shiller's price, earnings and CPI (library-only,
  fetched at run time) and Treasury's 10-year yields; a live test reproduces
  Shiller's published CAPE from his file without storing any of it.
- Curve bindings: `Binding(..., tenors=...)` reads a table concept whose columns
  are tenors (`1m` to `30y`) at its last row on or before the date, filling an
  array of values and an array of their tenors in years and leaving out a tenor
  the row lacks. New series concepts: the Board's six GSW parameters
  (`us.treasury.gsw_beta0` to `us.treasury.gsw_tau2`), Shiller's
  `us.equity.sp_composite_price`, `us.equity.sp_composite_earnings` and
  `us.prices.cpi_long_run`, and Damodaran's `us.equity.sp500_year_end`,
  `us.equity.sp500_dividends_buybacks` and `us.equity.sp500_expected_growth`.
- `macro.output_gap`: the output gap from a published potential output (CBO's,
  for the United States) or by the Hodrick-Prescott (lambda by Ravn and Uhlig's
  rule), Hamilton (h and p by frequency), Baxter-King and Christiano-Fitzgerald
  filters, on the log of output; it returns the trend, the cycle and the latest
  gap as a ratio or a log difference. Golden cases reproduce CBO's published gap;
  oracles are statsmodels' filters and QuantEcon's Hamilton filter. Its card shows
  the gap chained into `macro.policy_rule` as a user-supplied override.
- `macro.phillips_curve`: the inflation surprise regressed on the unemployment gap
  with optional supply-shock controls and Newey-West errors; golden cases
  reproduce Stock and Watson's (2018) core PCE slopes from public-domain data.
- `macro.okun_law`: Okun's law in its gap form and its first-difference form (the
  change in unemployment on output growth, annualized if asked, with the growth
  that holds unemployment constant); golden cases reproduce Knotek (2007).
- `macro.solow_growth`: the Solow steady state with Cobb-Douglas technology, the
  golden rule and the speed of convergence, and growth accounting into capital,
  labour, human capital and the TFP residual (log or Solow's discrete method).
- `macro.debt_dynamics`: the debt-to-GDP path from an initial ratio and paths of
  the effective interest rate, nominal growth and the primary balance, with r - g
  and the debt-stabilizing primary balance; a golden case reproduces CBO's 2026
  extended-baseline debt path.
- `macro.recession_probability`: the New York Fed's yield-curve probit of a
  recession twelve months ahead, from the 10-year and 3-month Treasury yields
  (a discount-basis bill rate converted to bond-equivalent); golden cases
  reproduce the New York Fed's published probabilities.
- `pyeconomics.core.least_squares` (`core/regression.py`): ordinary least squares
  by QR with classical, HC1 and Newey-West covariances (the lag an input, Newey
  and West's 1994 rule by default), returning coefficients, standard errors,
  t statistics, R² and residuals; bounded inputs; agrees with statsmodels.
- The `us.fiscal.primary_balance_to_gdp` concept (BEA's federal primary balance
  over nominal GDP). Window bindings of one frequency now end on one date, so a
  model can pair them by position; a window read through `convert` is sized in its
  target frequency; and a window passes over a source with too short a history
  for the next candidate (`resolve(..., min_observations=)`).
- `macro.policy_rule`, the monetary-policy suite: the Taylor (1993) and (1999),
  balanced-approach, balanced-approach (shortfalls), adjusted Taylor (1993) and
  first-difference rules as the Board's Monetary Policy Report and the original
  papers define them, each with its published weights (overridable), smoothing
  from the previous rate and an optional effective lower bound that floors the
  smoothed rate; the resource gap as an output gap or an Okun-scaled unemployment
  gap; the neutral rate real or nominal; and a `path` calculation over forecast
  horizons with an optional low-high band, drawn as a fan chart. Profiles bind
  realized US data (`default`, `us_output_gap`), the SEP (`us_sep`), the SPF
  (`us_spf`) and the euro area, the United Kingdom and Canada; golden cases
  reproduce the Atlanta Fed's Taylor Rule Utility and the Cleveland Fed's simple
  rules, and a parity test holds every 0.2.x characterization fixture.
- `macro.neutral_rate`: r* from the New York Fed's published Laubach-Williams and
  Holston-Laubach-Williams estimates, the SEP's longer-run rate less the inflation
  objective, or a constant, as real and nominal rates with the real policy-rate gap.
- The `macro` entry point, and series concepts for the SEP medians a binding reads:
  `us.sep.core_pce_inflation`, `us.sep.pce_inflation` and `us.sep.unemployment`
  for a meeting and a projection year, and `us.sep.unemployment_longer_run`.
- The `lag(periods=n)` transform (each date's value `n` periods back), a
  candidate `column` that takes concept parameters as its series key does, a
  candidate's `vintages` flag, and the `band` chart kind (a fan chart).
- The semantic catalog and resolver (ADR-0011 decision 15): 140 concepts
  with permanent ids such as `us.inflation.pce_core.yoy` (US prices, labour,
  output and the output gap, policy rates, Treasury curves, r*, the SEP and SPF,
  fiscal series, the Penn World Table, the Ken French factor and portfolio
  sets, Shiller and Damodaran, and euro-area, UK and Canadian inputs), each a
  definition, a fixed unit, frequency and seasonal adjustment, and candidate
  sources in fallback order. `pyeconomics.data.resolve` tries them by mode, key,
  extra and vintage, passes over a source with a recorded reason, fails over only
  between identical definitions (`strict=True` never falls back), and records the
  chain tried in every `DataSource`. Hosted mode resolves an originator or
  refuses with a `LicenceError` that names the classes it found.
- Explicit transforms, one vocabulary in `pyeconomics.core.transforms` and their
  implementations in `pyeconomics.data.catalog.transforms`: percent change,
  year over year, difference, logarithm, change dates, the ratio and sum of two
  concepts, frequency conversion by mean, sum, first, last or period end, and
  as-of, period and window alignment. Nothing fills a gap, invents a date or
  carries a value forward silently.
- The public data API: `pyeconomics.data.get`, `search`, `describe`, `vintages`
  and `sources`, working on concepts and on `provider:series` addresses.
  `registry.validate()` gains the `released-concept` rule and the `concept-*`
  checks, and `data/_released.py` its concepts section.
- Documentation: the "Data sources and keys" guide, a generated sources summary
  and one generated page per concept, built offline from metadata.
- Research-finance providers: Ken French, Shiller, Damodaran aggregates, AQR,
  Hou?Xue?Zhang, JKP, Open Source Asset Pricing, Cboe VIX and Coin Metrics;
  personal-use yfinance behind its extra and explicit opt-in.
- Treasury, Federal Reserve Board, New York Fed and OpenFIGI, with typed
  identifier mappings, bounded legacy XLS and selected-sheet XLSX readers.

- Research data providers for Philadelphia Fed real-time matrices and SPF,
  Atlanta Fed GDPNow, Cleveland Fed inflation expectations, CBO projections
  and Penn World Table 11.0, with bounded in-memory spreadsheet parsing.

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
- Live data bindings (ADR-0011 decision 16). A model declares
  `pyeconomics.core.Binding` values (an input field, a catalog concept, an optional
  transform, an as-of rule, a window and a vintage policy) in named profiles, and
  stays pure. `pyeconomics.bind(model_id, as_of=...)` resolves a profile through the
  catalog before the model runs, on real-time vintages by default, and returns a
  `Bound` of the values and one `DataSource` record per bound field, which
  `pyeconomics.run(model_id, bound)` puts in the result's manifest. Revised data
  (a policy that asks for the latest, or a source that keeps no vintages) is
  labelled `revised_data` on its record and in the result's warnings; an override
  replaces a bound value and is recorded as user-supplied; `concepts=` rebinds a
  field to a concept of the same unit kind and frequency. `registry.validate()`
  reports every structural binding problem under the `bindings` rule, and
  `pyeconomics.data.validate_bindings()` checks them against the catalog.
- The model card gains a "Data" section (each binding's concept, transform, as-of
  rule and vintage policy, and the licence classes and notices of the sources that
  can fill it), `registry.describe()` a `bindings` key, `Result.attributions()` the
  attribution and required notices of the data a result read, and
  `scripts/new_model.py --bound` a scaffold with an example binding.
- A frame note that describes the whole series (`revised_data`, `bls_keyless`) is
  repeated as a warning code on its `DataSource` record.

### Fixed

- `core.least_squares` no longer overflows when the response and the regressors
  are both tiny (subnormal): coefficients and errors scale back through the ratio
  of the scales, and a coefficient beyond the floating-point range raises
  DomainError. Ordinary inputs give the same results.
- `performance.brinson_attribution` no longer raises a math domain error when a
  period's portfolio return is within rounding of -100% beside a higher benchmark
  return: Carino's log ratio then comes from the two logarithms (#145). Inputs
  that ran before give the same results.
- Numeric unit markers reject Python and NumPy booleans; date fields reject
  numeric epoch timestamps, including array elements (#75).
- Registry validation requires units and bounds on numeric Literal fields (#81).
- Shared IRR recognizes roots at inclusive bracket endpoints without changing
  the smallest-root policy (#85); see the public erratum.
- A real-time bind of the funds rate, the target range or a Treasury yield no
  longer raises: ALFRED keeps no vintages of FRED's daily `EFFR`, `DFEDTARU`,
  `DFEDTARL`, `DGS10`, `DGS3MO` and `DFII10`, so those candidates are marked,
  skipped by a vintage request, and read by a binding as revised data, labelled.
- A binding read for the period containing a date now passes over a source that
  holds no observation up to that period's end, instead of picking it and failing.
- The Federal Reserve Board's SEP columns no longer carry a row label's footnote
  number (`core_pce_inflation_median_2026`, not `core_pce_inflation_4_...`).
- A concept search ranks a concept whose topic is a query word above one that
  only mentions it.

### Changed

- The `fed_board` provider labels the GSW betas as dimensionless decimals (they
  are coefficients in decimal rate units, some of several hundred percentage
  points), and the `damodaran` provider's implied premium file now also carries
  the S&P 500's year-end level, its dividends plus buybacks and the analysts'
  expected growth.
- A bind of a model with several calculations needs `calculation=...` and reads
  only the bindings that calculation's fields take.
- **Breaking for anything that parses manifests:** the manifest moves to schema 2.
  `schema_version` is 2 and `data_sources` is a list of `DataSource` records
  (always empty before) in canonical form, sorted by field. The manifest still holds
  no clock of the run, host, user, path or environment value; a record's retrieval
  time is a fact about the data. `result_sha256` and `inputs_sha256` keep their
  definitions, so a model that reads no data has the same hashes as before.
- `registry.describe()` and `describe()` gain a `bindings` key before `extra`; the
  model-pages generator and `registry.describe` list the sources of a bound model's
  concepts, importing the data layer only for such a model.
- When the resolver can read nothing, a candidate skipped because it keeps no
  vintage no longer hides why the one that could not answer: a missing key still
  raises `CredentialError` and an empty cache offline still raises `OfflineError`,
  where a request for a vintage raised a generic `DataError`.
- Begin the Phase 3 baseline at `1.0.0a2.dev1`.
- `foundations.time_value`, `corporate.capital_budgeting` and
  `performance.return_measurement` advance from model version 1 to 2 for the
  IRR endpoint correction. Permanent model ids remain unchanged.

### Security

- certifi, which the `sdmx` and `yfinance` extras install, moves to 2026.10.19
  for PYSEC-2026-4320; its MPL-2.0 licence is unchanged.

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
