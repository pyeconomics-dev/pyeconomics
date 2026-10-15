# ADR-0011: Data platform

- Status: Accepted
- Date: 2026-10-14
- Deciders: Nathan Ramos, CFA (maintainer)
- Parent: ROADMAP §3 Target Architecture and §4 3.1–3.8; §5 "Security &
  privacy strategy", "Data licensing policy" and "Legal & brand guardrails"

## Context and problem

Phase 3 builds the data layer: providers for 31 free sources, credentials,
a cache, vintages, a semantic catalog and live bindings into the model
registry. Every later surface reads what this phase defines. Phase 4
generates the `pyeconomics data`, `keys` and `cache` commands, the REST
`series` routes and the MCP `get_series` and `list_sources` tools from the
provider metadata, and gates MCP and AI-narrative output on it. Phase 5's
hosted snapshot job reads only sources classed `hosted-safe` here. Phase 6
adds bring-your-own-key vendors and Bloomberg on the same contract.

Without one recorded answer, each provider would choose its own shape for a
series, its own missing-value marker, its own dating of a month, its own
percent or decimal, its own idea of a vintage, its own cache and its own way
of holding a key. 0.2.x shows what that costs: it cached FRED responses in a
pickle file, against FRED's terms, filled gaps forward without saying so,
evaluated historical rules on revised data (ROADMAP §2, gaps 4 and 7), and
logged a FRED key. Once `1.0.0` ships, the value types, the manifest and the
provider and concept ids become public API that only a major release can
change (ADR-0003).

The facts the decisions rest on, all read on 2026-10-14:

- **httpx has had no release since 0.28.1** (2024-12-06), and it requires
  certifi [S1]. requests also requires certifi [S2]. **certifi is MPL-2.0**
  [S2], outside ADR-0004's allowlist.
- **urllib3 2.8.0** (2026-09-15) is MIT and pure Python with no
  dependencies; **truststore 0.10.5** (2026-10-12), which verifies TLS
  against the operating system's trust store, is MIT and pure Python;
  platformdirs 4.13.0 is MIT [S3].
- **No CPython 3.15 wheel** exists for duckdb 1.5.6 or PyYAML 6.0.3 [S4].
  CI tests Python 3.12–3.15 on three operating systems (ADR-0010), so
  neither can be a dependency. pyarrow has a 3.15 wheel, but ADR-0008
  decision 8 bars it, even through an extra.
- **Clients that would break those rules:** wbgapi 1.0.14 requires PyYAML
  and requests; edgartools 5.62.0 requires pyarrow and httpx; the DBnomics
  client 1.2.7 is AGPL-3.0, excluded by ADR-0004 [S5]. sdmx1 2.27.0 is
  Apache-2.0 and requires requests, so certifi with it; yfinance 1.7.0 is
  Apache-2.0 and requires requests, peewee and curl_cffi [S6]. keyring 25.7.0
  is MIT; on Linux it pulls in SecretStorage and jeepney [S6].
- **FRED API v2 takes its key in an `Authorization: Bearer` header**, v1 in
  the `api_key` query parameter [S7]. A v1 request URL therefore carries the
  key, the 0.2.x leak path.
- **ALFRED's real-time periods** are closed at both ends; the earliest
  real-time date is 1776-07-04 and 9999-12-31 means "still current" [S8].
  Long-run series also predate ADR-0008's 1900 floor for model dates:
  Shiller's monthly market data start in January 1871 [S9].
- **The Federal Reserve Board removes the Data Download Program's "Build
  Your Package" option the week of 2026-11-09**, "in preparation for the
  eventual retirement of the DDP", and now posts each release as XML on its
  release page (its notice of 2026-07-16) [S10]. No end date for the DDP
  itself is announced.
- **pandas 3** deprecates business-day periods: `pd.Period(..., "B")` warns
  that it will be removed (checked with pandas 3.0.6). It has no
  semiannual period-end offset; core's `Frequency` already uses `6ME`
  (ADR-0008 decision 4).
- **In the repository:** `pyeconomics.core.Provider` names the distribution
  that registered a model, and core's `Frequency` is ADR-0008's compounding
  enum, not an observation frequency. Models may import only
  `pyeconomics.core` and an allowlist (`tests/registry/test_model_imports.py`,
  the `model-purity` semgrep rule), so the vocabulary a binding or a
  manifest needs must live in core. `core/manifest.py` is schema 1 with an
  always-empty `data_sources`.
- **ADR-0005 rule 4** and ROADMAP §5 "Data licensing policy" rule 4: a
  source whose terms forbid storage is fetched live and never written to
  disk. FRED's terms forbid it (ADR-0005 [S1]). ROADMAP §4 3.3 had planned
  an opt-in FRED cache, which that rule does not allow.

## Decision drivers

- **Licence first.** A source's licence class, terms and `llm_use` are code
  that every layer reads, so no surface serves data its terms forbid.
- **No leaked key.** The 0.2.x defect is designed out: a key is a secret
  from the moment it is read, and no record, message, cache or export can
  hold one.
- **Reproducibility.** The same data gives the same bytes; a manifest says
  which series, vintage and retrieval time a result read; historical
  evaluation sees what was known then.
- **Parity with ADR-0008.** Decimals, units, bounds, canonical JSON and
  pandas 3 semantics hold for data exactly as for model fields.
- **Portability and licence.** The core still runs in Pyodide and on every
  Python 3.12–3.15 cell, with permissive dependencies (ADR-0002, ADR-0004,
  ADR-0010).
- **One contract.** Thirty-one providers, and Phase 6's vendors, apply the
  same rules without re-arguing them.

## Considered options

1. **A pyeconomics-owned data layer on the eighteen decisions below**: pure
   value types and provenance in core and `pyeconomics.data`, one provider
   contract, a thin urllib3 transport, a licence-aware SQLite cache, a
   Python-module catalog and bindings declared in core.
2. **The parent roadmap's first plan**: httpx clients, wbgapi and
   edgartools, and Parquet files indexed by DuckDB with an opt-in FRED
   cache. Rejected on the facts above: httpx and requests bring certifi,
   duckdb and PyYAML have no CPython 3.15 wheel, pyarrow is barred, and an
   opt-in FRED cache breaks ADR-0005 rule 4.
3. **OpenBB's platform as the data layer.** Its provider pattern is the one
   decision 9 follows, but many of its provider extensions are AGPL-3.0
   (ADR-0004 [S5]), it is far heavier than a pure-Python core, and its
   types carry no licence class or vintage.
4. **Each provider its own client and types**, with licence and vintage
   rules left to review. Cheapest at first, but nothing would stop a later
   provider from caching what its terms forbid or dating a month
   differently, and Phase 4 could not generate one surface from many shapes.

## Decision outcome

Chosen option: **1**, because it makes the licence class, the vintage and
the key's secrecy properties of the types, which the tests can prove, while
every dependency installs on every supported cell and in Pyodide. The
eighteen decisions below are rules a later step follows as written.

### 1. Layout

- `src/pyeconomics/data/` is core in ADR-0002's sense: pure Python, in the
  default install.
- It grows step by step: the value types, terms, vintages and errors (Phase
  3 Step 2); credentials, configuration and redaction (Step 3); the provider
  base class, registry, transport, modes and built-in providers (Step 4 on);
  the cache (Step 5); the catalog (Step 11); bindings (Step 12).
- `core/` stays I/O-free. **Models never import `pyeconomics.data`, and
  neither does any module under `core/`.** The vocabulary a model or a
  manifest needs lives in `pyeconomics.core` and the data layer re-exports
  it: the provenance record (`DataSource`, `RealtimePeriod`, `LicenceClass`,
  `LlmUse`, in `core/provenance.py`; Step 2), the transform names (Step 11),
  and the `Binding` declaration and `Bound` result (Step 12).
- The data layer uses the network, files, the environment and the clock
  only in its transport, cache, configuration and credential modules. Its
  value modules do none of these.

### 2. Value types and errors

- **`Series`** is immutable: an index of dates, a tuple of float-or-`None`
  values and its `SeriesMeta`, at most 100,000 observations (ADR-0008's
  array bound). **`Table`** shares one index across named columns, each with
  its `ColumnMeta`, under one `TableMeta`: at most 100,000 rows and 1,000
  columns. A larger frame is refused with `InputError`.
- Both convert to pandas and back losslessly: a `datetime64[us]` index
  (ADR-0008 decision 9), `Float64` values, and the metadata in
  `attrs["pyeconomics"]`. Both write canonical JSON (RFC 8785) and read it
  back losslessly and strictly: no NaN, no repeated key, no unknown key.
  These are the only serializations; nothing pickles, evaluates or
  YAML-loads a frame. Polars and Arrow stay the caller's (ADR-0008
  decision 8).
- Records that are neither dated nor numeric, such as OpenFIGI's identifier
  mappings or EDGAR's filing lists, are not frames: their providers return
  typed, bounded records of their own (Phase 3 Step 7), which no binding
  reads.
- **Errors.** `DataError` is a `PyeconomicsError`. Its subclasses also
  derive from the built-in a caller would expect: `ProviderNotFoundError`
  and `SeriesNotFoundError` (`LookupError`); `CredentialError` and
  `LicenceError` (`PermissionError`); `RateLimitError` (`RuntimeError`);
  `TransportError` and `OfflineError` (`ConnectionError`); `ResponseError`
  and `ConfigError` (`ValueError`).
- No message carries a credential, a URL's query or a path. Messages name
  identifiers and settings; as a second line of defence, every `DataError`
  strips the user information, query and fragment from any URL in its
  message.

### 3. Dates and frequency

- `ObservationFrequency` is its own enum: `daily`, `business_daily`,
  `weekly`, `biweekly`, `monthly`, `quarterly`, `semiannual`, `annual` and
  `irregular`. It is separate from core's compounding `Frequency`.
- Weekly and biweekly data name the weekday a week ends on; quarterly,
  semiannual and annual data the month their year ends in, which is 12
  unless the source keeps a fiscal year (CBO's ends in September).
- **A period's observation is indexed by its period's last day**, ADR-0008
  decision 4's period-end convention. A frame refuses any other date. The
  source's own convention (period start for FRED, BLS and BEA) is recorded
  in the metadata as `source_dating`, and the provider converts it.
- `Series.periods()` and `Table.periods()` return pandas Periods, each of
  which ends on its index date. A business day's period is that day, because
  pandas deprecates business-day periods. An irregular series has none.
- Observation and real-time dates lie between 1700-01-01 and 2200-12-31
  (`DATA_DATE_BOUNDS`). The range is wider than a model field's because
  long-run series start in the nineteenth century and ALFRED's real-time
  origin is 1776-07-04 [S8][S9]. A binding still delivers each value inside
  its model field's own bounds.

### 4. Units and the decimal boundary

- A frame's unit record keeps the source's unit text as published, an
  ADR-0008 unit kind where one applies, the power of ten the values are in
  (1e9 for billions) and the ISO 4217 currency.
- A rate, return, probability or volatility is a decimal with scale 1. Its
  provider converts percent with `core.rates.percent_to_decimal` in its
  transform step (ADR-0008 decision 1). No other code changes a rate's
  scale.

### 5. Missing observations

- A missing value is `None`: JSON `null` and pandas `NA`, never NaN. Each
  provider maps its source's markers to `None` (FRED's `.`, for one), and a
  frame counts them.
- Nothing fills a gap silently. Alignment and bindings use explicit,
  recorded rules (decisions 15 and 16).

### 6. Vintages

- An observation from a source that keeps vintages carries its
  `RealtimePeriod` (`realtime_start`, `realtime_end`), with ALFRED's
  semantics: both ends inclusive, and `None` for an end that is still
  current (ALFRED's 9999-12-31) [S8]. In such a frame a date repeats once
  per real-time period, sorted by real-time start, and one date's periods
  never overlap.
- `Vintage` is `latest()`, `as_of(date)`, `first_release()` or `all()`.
  `as_of` keeps, for each date, the value whose real-time period covers the
  date; `first_release` the earliest; `latest` the most recent; `all` every
  row. A selection keeps each row's real-time period.
- **Historical evaluation defaults to `as_of` the evaluation date wherever
  the source keeps vintages.** Where it does not, the binding layer reads
  the latest data, records `revised_data` and warns (Step 12). The selector
  itself never falls back: `as_of` or `first_release` on a frame without
  real-time periods raises `DataError`.
- A record names its vintage as a label: `latest`, `first_release`, `all`
  or `as_of:YYYY-MM-DD`.

### 7. Licence classes and terms

- `LicenceClass` holds ADR-0005's five classes, in core.
- Every provider declares `Terms`: its class; the `https` page its terms
  were read from; the date they were last read; its attribution; its
  required notice, if any; `llm_use`; and its `CachePolicy` (`allowed` or
  `forbidden`).
- A series may override the class, `llm_use`, the cache policy and the
  notice from the source's own markers: FRED's copyright tags, the World
  Bank's `License_Type`, Eurostat's listed exceptions. Moody's series on
  FRED count as pre-approval whatever their label says.
- A provider without complete terms never registers (Step 4). Terms read
  more than 13 months ago are stale, and a test fails on them; the check
  takes the date to judge against, because the value types read no clock.
- **The terms page is the only URL any value type holds.** It must be
  `https`, name a DNS host, and carry no user information, port, query or
  fragment, so it can hold neither a credential nor a request. Every other
  text field refuses `://`.

### 8. `llm_use`

- `LlmUse` is `allowed`, `forbidden` or `unclear`, read from the source's
  terms, in core.
- It travels with every frame (in its terms) and every `DataSource` record.
  Phase 4's MCP server and AI narrative gate on it: they withhold
  `forbidden` data, and `unclear` data needs the user's opt-in.

### 9. Provider contract

- One `DataProvider` subclass per source, named so because
  `pyeconomics.core.Provider` already names a model's distribution.
- Each declares a `ProviderInfo`: id, name, homepage, terms, authentication,
  host allowlist, rate limits, capabilities, the extra it needs and its
  platforms.
- A typed fetch pipeline: query model → requests → raw responses → `Series`
  or `Table`, plus `search`, `describe` and `vintages` where declared.
- Discovery is through the `pyeconomics.providers` entry-point group.
  Provider ids are permanent once released, as model ids are (ADR-0003).

### 10. HTTP stack

- **urllib3 2.x (MIT) with truststore (MIT)** for the operating system's
  trust store, behind a `Transport` protocol and imported lazily, so the
  core imports without it in Pyodide.
- Not httpx (no release since 0.28.1 on 2024-12-06, and it requires certifi,
  MPL-2.0) and not requests (certifi too) [S1][S2].
- The transport builds URLs only from a provider's allowlisted hosts, over
  HTTPS, never from user input. It sets timeouts and a response-size cap,
  retries with exponential backoff and jitter within each provider's
  published limits (honouring `Retry-After`), and sends a User-Agent naming
  pyeconomics and its version, plus the user's configured contact where a
  source requires one.

### 11. Clients and extras

- **sdmx1 (Apache-2.0)** for IMF, OECD, ECB, BIS and Eurostat, behind an
  `[sdmx]` extra. Its requests dependency brings certifi, which carries a
  reviewed MPL-2.0 exception reached only through that extra and
  `[yfinance]`.
- **In-house clients** for the World Bank (wbgapi needs PyYAML, which has no
  CPython 3.15 wheel) and SEC EDGAR (edgartools needs pyarrow). DBnomics is
  read through its REST API, because its client is AGPL [S5].
- yfinance behind `[yfinance]`, off by default; the OS keyring behind
  `[keyring]`.
- urllib3, truststore, platformdirs, openpyxl, defusedxml and xlrd join as
  pure-Python runtime dependencies, each in the step that first needs it.
- This extends ADR-0002's extras table with `sdmx`, `yfinance` and
  `keyring`, all of which `all` includes.

### 12. Credentials

- Per provider, a key is looked up in this order: an explicit argument; the
  provider's environment variable (`FRED_API_KEY`, `BLS_API_KEY`,
  `BEA_API_KEY`, `CENSUS_API_KEY`, `OPENFIGI_API_KEY`); a `.env` file in the
  user's configuration directory, parsed strictly by pyeconomics and never
  overriding a real environment variable; the OS keyring (service
  `pyeconomics`, user the provider id).
- A key is a `Secret` from the moment it is read.
- `pyeconomics.toml` (the user's configuration directory, then the working
  directory, then `PYECONOMICS_*` variables) holds settings only, and
  refuses any key named like a secret.
- The SEC contact address is personal data: it is sent in EDGAR's
  User-Agent and never logged or recorded.

### 13. Redaction

- A chained log-record factory scrubs every registered secret, and its
  URL-encoded form, from every record of every logger.
- URLs and headers are scrubbed before an exception, a warning or a log line
  carries them. Transport errors are raised outside the `except` block that
  caught them, so no traceback chains the original.
- `Secret`'s `repr`, `str` and `format` show only that a value is set; it
  refuses pickling and canonical JSON.
- Canary tests cover logs, exceptions and tracebacks, warnings, manifests,
  cache files and exports.

### 14. Cache store

- **SQLite** (the standard library's `sqlite3`) in the user's cache
  directory, with user-only permissions. Payloads are canonical JSON, keyed
  by provider, dataset, series, the credential-free query and the vintage.
- A time-to-live per provider, long for closed past vintages; an offline
  mode; a Python cache API that Phase 4's commands wrap.
- **A source whose terms forbid storage has no cache path and no opt-in**
  (ADR-0005 rule 4). FRED and ALFRED are among them. An in-process memo,
  never shared and gone at exit, is not storage.
- Rejected: Parquet files indexed by DuckDB (duckdb 1.5.6 has no CPython
  3.15 wheel; pyarrow is barred by ADR-0008 decision 8). Parquet stays the
  export and hosted-snapshot format of Phases 4 and 5.

### 15. Catalog

- Concept ids are dotted snake_case of three or four parts that start with
  an economy (a lowercase ISO 3166 code, or `ea` for the euro area) or a
  dataset family: `<economy>.<topic>.<measure>[.<transform>]`
  (`us.inflation.pce_core.yoy`) or `<family>.<set>.<economy>.<frequency>`
  (`factors.ff5.us.monthly`).
- Concept ids are permanent once released. Each maps to provider series in
  fallback order (the originator, then a library-only aggregator on the
  user's own key, then premium-only, Phase 6), with declared transforms and
  an explicit alignment rule.
- Hosted mode resolves only to originators; a vintage request prefers a
  source that keeps vintages. Mixed frequencies align by explicit, recorded
  rules, never a silent forward fill.
- The catalog ships as Python modules, inside the wheel's allowlist.

### 16. Bindings and manifests

- A `Binding` (in core: field, concept, transform, as-of rule, window,
  vintage policy, profile) names one input field's concept, its transform,
  its as-of rule (the last observation on or before the date, one period's
  value, or a window of N observations) and its vintage policy, within a
  named profile: one complete set of bindings, such as realized data, a
  forecast source or another economy.
- `pyeconomics.bind(model_id, /, *, as_of, vintage, mode, profile, concepts,
  **overrides)` resolves a profile, with `concepts=` rebinding a field to
  another concept of the same unit kind and frequency, and returns a
  `Bound` (in core): the values plus their `DataSource` records.
  `pyeconomics.run(model_id, bound)` runs it.
- **The manifest moves to schema 2.** `data_sources` holds `DataSource`
  records: provider, series, dataset, concept, the bound field, vintage
  label or real-time period, observation window, transforms, the retrieval
  time from the fetch, licence class, attribution, notice, terms page,
  `llm_use`, whether the cache or offline mode served it, the fallback chain
  tried, and warning codes about the data (`revised_data`,
  `served_offline`). It never holds a request URL, a path, a host or a key.
- `result_sha256` keeps its definition. A manifest is byte-identical for
  identical inputs and identical data-source records.

### 17. Recorded responses

The Phase 3 roadmap's Recording rule is the contract. Every provider's
offline tests replay recorded responses under
`tests/providers/cassettes/<provider>/`, made by a deliberate local recorder
that scrubs every credential as it writes. A cassette keeps a response's
structure and a handful of observations (at most 24 per series and 32 KiB
per file). A source not classed `hosted-safe`, or whose terms forbid
storage, gets synthetic values, and a test fails on any such cassette that
is not marked synthetic. A contract test scans every cassette for the
gitleaks rules and any unscrubbed credential parameter.

### 18. Live verification

- `providers-live.yml` runs the contract suite against the real sources
  weekly and on dispatch, on `main` only, in the `providers-live`
  environment (deployment branch `main`, environment secrets only).
- Its egress is blocked by harden-runner to the declared hosts and the
  installer's. The run has `contents: read`; only the reporting job has
  `issues: write`. A failing run opens one issue under the `provider-live`
  label and closes older ones.
- A separate daily `providers-heartbeat.yml` fails, and opens an issue, when
  no successful live run is younger than eight days.
- A source whose terms bar automated collection (yfinance) runs live only on
  the maintainer's machine, on demand.

### Consequences

Good:

- A library-only or no-storage source cannot be served or cached by
  mistake: its class and cache policy are fields the code reads, and FRED
  and ALFRED have no path to disk at all.
- A key cannot reach a record, a frame, a message or the cache by
  construction: no field is named for one, the one URL refuses credentials
  and queries, and every other text refuses URLs.
- Historical evaluation sees the data as published, and every result says
  which vintage it read, closing 0.2.x's look-ahead bias.
- One shape for every series, so Phases 4 and 5 generate each surface once.
- Every dependency installs on all twelve CI cells and in Pyodide, under
  ADR-0004's licences or reviewed exceptions.

Bad:

- In-house clients for FRED, BLS, BEA, Census, Treasury, the Fed Board, the
  NY Fed, EDGAR, the World Bank and DBnomics are code to keep working as the
  sources change; the weekly live run is the alarm.
- FRED and ALFRED data are fetched again in every process. Users with large
  FRED workloads pay that in requests, inside FRED's rate limits.
- certifi, cffi and peewee need reviewed licence exceptions for the extras
  that pull them in.
- Two kinds of bounds now exist for dates: a model field's (1900–2200) and
  a frame's (1700–2200). A binding must check a value against its field.
- A frame's period-end rule makes a provider convert every period-start
  source. That is the point, but each conversion is a place to get wrong,
  which the contract suite checks.
- `pyeconomics.core.provenance` is also the name of a function that core
  exports (`core.random.provenance`), which hides the module there, as the
  `model` decorator hides `core.model`. Code imports the module by its path.

### Confirmation

| Decision | Check | Built in |
|----------|-------|----------|
| 1 Layout | `tests/data/test_layering.py`: no module under `core/` imports `pyeconomics.data`, statically or in a fresh interpreter with every model loaded; the value modules import no I/O library and call no clock or file function | Phase 3 Step 2 |
| 1 Layout | Each I/O module (transport, cache, configuration, credentials) is the only one of its kind; the purity list grows with every pure module | Phase 3 Steps 3–5 |
| 2 Value types | `tests/data/test_series.py` and `test_table.py`: canonical JSON and pandas round trips, strict reading, the 100,000-observation and 1,000-column bounds | Phase 3 Step 2 |
| 2 Errors | `tests/data/test_data_errors.py`: the taxonomy and URL scrubbing; the transport's status mapping | Phase 3 Steps 2 and 4 |
| 3 Dates | Period-end validation and `periods()` tests for every frequency and anchor; property tests; the contract suite checks each provider's conversion | Phase 3 Steps 2 and 4 |
| 4 Units | Decimal unit kinds keep scale 1; the contract suite checks rate units are decimals | Phase 3 Steps 2 and 4 |
| 5 Missing | `None` survives every round trip; the contract suite checks missing markers become `None`; alignment rules are recorded | Phase 3 Steps 2, 4 and 11 |
| 6 Vintages | `tests/data/test_vintage.py` on hand-built ALFRED-style data, and a property test against the definition | Phase 3 Step 2 |
| 6 Vintages | ALFRED's first release verified against a known later revision; bindings default to `as_of` | Phase 3 Steps 6 and 12 |
| 7 Licence and terms | `tests/data/test_terms.py`: https terms page, attribution, overrides and the 13-month horizon; `tests/data/test_value_security.py`: no field can carry a URL, host, path or credential | Phase 3 Step 2 |
| 7 Licence and terms | The provider registry refuses incomplete terms; a per-provider test fails on stale terms | Phase 3 Step 4 |
| 8 `llm_use` | Carried by every frame's terms and every `DataSource` record (Step 2); MCP and AI-narrative gating | Phase 3 Step 2; Phase 4 |
| 9 Provider contract | `ProviderInfo` validation, entry-point discovery and the shared contract suite | Phase 3 Step 4 |
| 10 HTTP stack | Transport tests: a foreign host and `http://` refused, timeouts, the size cap, backoff on a fake clock, the User-Agent; the `licences` hook | Phase 3 Step 4 |
| 11 Clients and extras | The `licences` hook and reviewed exceptions; extras in `pyproject.toml`; installs on all twelve CI cells | Phase 3 Steps 3, 7, 8 and 10 |
| 12 Credentials | Lookup-order tests; `pyeconomics.toml` refuses secrets | Phase 3 Step 3 |
| 13 Redaction | Canary tests across logs, exceptions, tracebacks, warnings, manifests, cache files and exports | Phase 3 Step 3 |
| 14 Cache | A no-storage provider creates no file and writes no row; time-to-live and offline-mode tests | Phase 3 Step 5 |
| 15 Catalog | Concept grammar (`CONCEPT_ID_PATTERN`, Step 2), resolution, hosted-mode originator-only, alignment tests | Phase 3 Steps 2 and 11 |
| 16 Bindings and manifests | Manifest schema 2 tests; identical bound values give identical result hashes | Phase 3 Step 12 |
| 17 Recorded responses | The cassette secret scan and the synthetic-value test | Phase 3 Step 4 |
| 18 Live verification | `providers-live.yml` green on `main`; the heartbeat; a synthetic failure fires the alarm | Phase 3 Steps 6 and 20 |

## More information

- Related: ADR-0001 (product boundaries), ADR-0002 (extras and the
  pure-Python core), ADR-0003 (permanent ids), ADR-0004 (licence
  allowlist), ADR-0005 (licence classes and rule 4), ADR-0008 (decimals,
  units, bounds, canonical JSON, pandas 3), ADR-0010 (Python floor); the
  Phase 3 roadmap's data contract, Licence, Recording, Credential and
  Dependency rules.
- The maintainer accepted the eighteen decisions, with the values in this
  record, in Phase 3 Step 2's pull request on 2026-10-14. With them the
  maintainer accepted the step's implementation calls: frequency anchors
  (decision 3), the 1700–2200 data date range (decision 3), selectors that
  never fall back (decision 6), the terms page as the one validated URL and
  per-series notice overrides (decision 7), the bound field and warning
  codes on `DataSource` (decision 16), provider-typed records for data that
  is not a frame (decision 2), and `core/provenance.py` keeping its name
  beside `core.random.provenance`.
- Sources, all accessed 2026-10-14:
  - [S1] PyPI JSON for httpx (0.28.1, uploaded 2024-12-06; requires
    `anyio`, `certifi`, `httpcore` and `idna`),
    https://pypi.org/pypi/httpx/json.
  - [S2] PyPI JSON for certifi (2026.7.22, `MPL-2.0`) and requests (2.34.2;
    requires `certifi>=2023.5.7`), https://pypi.org/pypi/certifi/json and
    https://pypi.org/pypi/requests/json.
  - [S3] PyPI JSON for urllib3 (2.8.0, 2026-09-15, `MIT`, no requirements),
    truststore (0.10.5, 2026-10-12, `MIT`) and platformdirs (4.13.0,
    `MIT`), https://pypi.org/pypi/<name>/json.
  - [S4] PyPI JSON for duckdb (1.5.6, 2026-09-28) and PyYAML (6.0.3): no
    `cp315` wheel among either release's files; pyarrow 26.0.0 has one,
    https://pypi.org/pypi/<name>/json.
  - [S5] PyPI JSON for wbgapi (1.0.14; requires `requests`, `PyYAML`,
    `tabulate`), edgartools (5.62.0; requires `pyarrow>=23.0.1` and
    `httpx`) and dbnomics (1.2.7; classifier "GNU Affero General Public
    License v3 or later"), https://pypi.org/pypi/<name>/json.
  - [S6] PyPI JSON for sdmx1 (2.27.0; classifier "Apache Software License";
    requires `requests`, `lxml`, `pandas`, `platformdirs`), yfinance (1.7.0,
    `Apache-2.0`; requires `requests`, `peewee`, `curl_cffi`) and keyring
    (25.7.0, `MIT`; `SecretStorage` and `jeepney` on Linux),
    https://pypi.org/pypi/<name>/json.
  - [S7] FRED API v2, "API Keys": the key is sent as
    `Authorization: Bearer <key>`,
    https://fred.stlouisfed.org/docs/api/fred/v2/api_key.html; v1, the
    `api_key` variable, https://fred.stlouisfed.org/docs/api/api_key.html.
  - [S8] FRED API, "Real-Time Periods": a (closed, closed) period;
    1776-07-04 is the first available real-time date and 9999-12-31 the
    last, https://fred.stlouisfed.org/docs/api/fred/realtime_period.html.
  - [S9] University of Florida Business Library, "U.S. Stock Markets 1871 -
    Present and CAPE Ratio" (Shiller's monthly data from January 1871),
    https://answers.businesslibrary.uflib.ufl.edu/faq/130581.
  - [S10] Board of Governors of the Federal Reserve System, "Updates to the
    Data Download Program (DDP) and DDP Data Releases", 2026-07-16, shown
    on the DDP's release pages, for example
    https://www.federalreserve.gov/datadownload/Choose.aspx?rel=H15, and on
    release pages such as
    https://www.federalreserve.gov/releases/h6/20260825/.
