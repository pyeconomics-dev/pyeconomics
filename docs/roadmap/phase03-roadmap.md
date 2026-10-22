# Phase 3 Roadmap — Data Platform & Free Sources

**Status:** In progress

## Overview

Phase 3 opens the data gate. Phase 4 generates the `pyeconomics data`,
`keys` and `cache` commands, the REST API's `series` routes and the MCP
server's `get_series` and `list_sources` tools from the provider metadata
this phase defines, keys its result cache on the data vintages manifests
record, and withholds every source whose `llm_use` flag forbids it; Phase 5
renders the data explorer and the "Data sources & licences" page from the
same metadata and points its snapshot job at the originators classed
`hosted-safe` here; Phase 6 adds bring-your-own-key vendors and Bloomberg on
the same provider contract. None of that can start until the data contract
is fixed and proven: the data model, licence classes as enforced metadata,
credentials that never leak, a cache that follows each source's terms,
vintages, a semantic catalog and live bindings into the model registry. The
phase targets 31 free sources (30 required if SEC access remains blocked,
under the release-set exception below), completes the 50-entry launch
catalog with its 18 live-data entries — led by a vintage-aware
monetary-policy suite, the clearest white space the project has — and
releases them to PyPI as the pre-release `1.0.0a2`. It runs no service
(Phases 4 and 5), adds no paid or bring-your-own-key vendor and no Bloomberg
code (Phase 6; Step 4 only spikes the contract against a mocked Desktop API
session), and generates no command, endpoint or MCP tool (Phase 4). It is
one phase because a data contract is proven only by the models that consume
it: the policy suite's real-time evaluation is the data layer's acceptance
test, as the catalog was the engine's in Phase 2.

The phase lands in 20 layers:

1. **Core hardening and the `1.0.0a2` baseline** — lands this roadmap and
   the refreshed planning kit, moves `main` to `1.0.0a2.dev1`, and closes
   the three contract bugs Phase 2 handed on: the unit markers stop
   accepting booleans and epoch numbers (issue #75), `registry.validate()`
   requires a unit on numeric `Literal` fields (#81), and the shared IRR
   finds roots that sit on its bracket's ends (#85), with the affected
   models' versions bumped and a public erratum.
2. **ADR-0011 and the data model** — writes
   `docs/adr/0011-data-platform.md`, eighteen decisions the maintainer
   accepts or amends in the pull request (the data model, missing values,
   vintages, licence classes and `llm_use`, the provider contract, the HTTP
   stack, extras, credentials, redaction, the cache store, the catalog,
   bindings and manifests, recorded responses and live verification), and
   builds the value types of `src/pyeconomics/data/` (`Series`, `Table`,
   their metadata, licence terms and vintage selectors) and the provenance
   vocabulary a manifest carries (`DataSource`, real-time periods, licence
   classes) in `pyeconomics.core`, with the percent-to-decimal boundary
   and a `data` coverage floor.
3. **Credentials, configuration and redaction** — the `Secret` type; the
   key lookup chain (argument → environment → a `.env` file in the user's
   config directory → the OS keyring through a `[keyring]` extra); a
   layered `pyeconomics.toml` that refuses secrets; redaction of every log
   record, URL, header, warning and exception; and canary tests proving no
   key reaches a log, an error, a warning, a manifest, a cache file or an
   export.
4. **Provider SDK, transport and contract suite** — the provider base class
   and its validated metadata, the typed fetch pipeline (query → request →
   raw response → `Series` or `Table`), `search`, `describe`, `vintages`
   and declared capabilities, discovery through the `pyeconomics.providers`
   entry-point group, the HTTPS transport (urllib3 and truststore, host
   allowlists, timeouts, size caps, retries and per-provider rate limits),
   library and hosted modes, recorded responses with scrubbing, the shared
   contract suite, generated per-provider documentation and the Bloomberg
   contract spike.
5. **Cache and offline mode** — a licence-aware SQLite store in the user's
   cache directory, keyed by provider, series, parameters and vintage, with
   a time-to-live per provider, an offline mode that serves cached data
   with its as-of date, and a Python cache API; a source whose terms forbid
   storage, FRED and ALFRED among them, has no cache path at all.
6. **Providers: FRED and ALFRED, BLS, BEA, Census** — the four keyed US
   sources, ALFRED's vintages proven against a known revision, FRED's
   series-level copyright gates and required notice, and the weekly live
   contract run, `providers-live.yml`, with the phase's first secrets held
   in a protected environment.
7. **Providers: Treasury, Federal Reserve Board, New York Fed, SEC EDGAR,
   OpenFIGI** — the keyless rate, market and filing sources; the Board's
   provider reads stable release files, never the "Build Your Package"
   pages the Board removes the week of 2026-11-09.
8. **Providers: SDMX sources, World Bank, DBnomics** — IMF, OECD, ECB, BIS
   and Eurostat through sdmx1 behind an `[sdmx]` extra, and the World Bank
   and DBnomics through thin in-house clients, with the World Bank's
   `License_Type` and Eurostat's exceptions as series-level licence gates.
9. **Providers: regional Fed research, CBO, Penn World Table** — the
   Philadelphia Fed's Real-Time Data Set and Survey of Professional
   Forecasters, the Atlanta Fed's GDPNow, the Cleveland Fed's inflation
   expectations, CBO's projections and potential output, and the Penn
   World Table, with CBO and the Penn World Table classified before either
   can feed a hosted surface.
10. **Providers: asset-pricing and market research data** — Ken French,
    Shiller, Damodaran, AQR, Hou-Xue-Zhang, JKP, Open Source Asset Pricing,
    Cboe's VIX history, Coin Metrics and yfinance (off by default, behind a
    `[yfinance]` extra); also delivers the four unblocked Step 7
    providers before catalog work.
11. **Semantic catalog and resolver** — concept ids such as
    `us.inflation.pce_core.yoy`, declared transforms, explicit frequency
    alignment, the fallback order, originator-only resolution in hosted
    mode, series-level licence gates, and the generated data-sources and
    concept pages of the documentation preview.
12. **Live bindings and vintage-aware runs** — `ModelSpec.bindings` filled
    with `Binding` declarations, `pyeconomics.bind()` and
    `pyeconomics.run()` on bound inputs, real-time vintages by default and
    revised data as a labelled option, and manifest schema 2 with typed
    `data_sources`.
13. **Monetary-policy suite** — `macro.policy_rule` (Taylor 1993 and 1999,
    the balanced approach with and without shortfalls, inertial,
    first-difference, ELB-adjusted and forecast-based rules) and
    `macro.neutral_rate`, golden cases from the Atlanta Fed's Taylor Rule
    Utility and the Cleveland Fed's simple rules, and parity with the 0.2.x
    characterization fixtures or a documented reason for each difference.
14. **Launch catalog: macroeconomics** — six entries: output-gap filters,
    the Phillips curve, Okun's law, the Solow model and growth accounting,
    debt dynamics, and the New York Fed's yield-curve recession probit.
15. **Launch catalog: fixed income and equity** — four entries:
    Nelson-Siegel and Svensson curve fitting, the binomial interest-rate
    tree with OAS, the implied equity risk premium, and CAPE.
16. **Launch catalog: asset pricing and portfolio** — four entries: factor
    regressions (CAPM through FF6), factor-model tests (GRS and
    Fama-MacBeth), Black-Litterman, and risk-based allocation (inverse
    volatility, risk parity and hierarchical risk parity).
17. **Launch catalog: econometrics** — two entries behind the
    `[econometrics]` extra: the GARCH family over arch, and ARIMA/SARIMA,
    VAR and cointegration over statsmodels.
18. **1.0.0a2 readiness gate** — a TestPyPI rehearsal of the exact
    candidate, a live end-to-end run of the rehearsed package with the
    maintainer's own keys, and `docs/releases/1.0.0a2-readiness.md`, ending
    in the maintainer's GO or NO-GO.
19. **1.0.0a2 release** — `v1.0.0a2` on PyPI as a pre-release with
    attestations, the released-id ledger extended to 50 ids, release notes,
    the data-sources guide on the documentation preview, and a GitHub
    release.
20. **QA + `verify-phase03.sh`** — `scripts/verify-phase03.sh` (`--fast`,
    `--python`, `--security`, `--live`, `--all`, `--post`),
    `docs/phase03-qa-findings.md`, matrix entry `03` in
    `.github/workflows/phase-verify.yml`, and a synthetic failure that
    proves the live run's alarm.

**External-approval exception (maintainer, 2026-10-17).** Neither pending
GitHub Sponsors approval (issue #68, submitted again on 2026-10-12) nor SEC
access may hold up the remaining roadmap. Sponsors is a separate funding
follow-up, not a data prerequisite. Step 7 stays unfinished until its own
acceptance criteria pass. Step 10 delivers its four unblocked providers
(`treasury`, `fed_board`, `nyfed`, `openfigi`) before the catalog needs them;
only `sec_edgar` may remain deferred. No launch-model binding requires EDGAR.

The **Phase 3 release provider set** is the exact source-plan set below minus
`sec_edgar` while SEC access is unresolved: 30 required provider ids, including
the opt-in yfinance provider. If Step 7 completes before the release candidate
is frozen, the set is all 31. Step 18 records the exact ids, evidence and SEC
deferral in the readiness document; Steps 19 and 20 use that recorded set.
A changed candidate requires a fresh rehearsal and maintainer GO. Deferral
permits no partial EDGAR registration, fabricated recording, passing skip or
relaxed check for any shipped provider. The four recovered providers must
pass their original Step 7 requirements in Step 10, including offline and
post-merge live proof. Step 7's later PR must pass all five providers' original
criteria and update release ledgers and verification without dropping ids.

Steps 10–20 and Phase 3 may complete with this one named external deferral;
Step 7's own Status and Summary Table cell remain unfinished. Step 20 records
it in QA findings and Phase 4's carry-over, owned by the maintainer for SEC
access and the Step 7 follow-up PR for implementation and verification. Phase 4
may start without SEC or Sponsors approval; it exposes only verified registered
sources. This exception supersedes earlier blanket joins and completion text.

The ship test for Phase 3 is straightforward: issues #75, #81 and #85 are
closed with regression tests; ADR-0011 is Accepted; every provider in the
Phase 3 release provider set is registered through the `pyeconomics.providers`
entry-point group, declares its licence class, terms URL, terms-checked
date, attribution and `llm_use` flag, and passes the shared contract suite
offline in CI against recorded responses that are scrubbed, secret-scanned
and synthetic wherever its terms forbid storage; a weekly live run against
the real APIs passes, opens an issue when it fails, and has fired its alarm
once on a synthetic failure; canary tests prove no key reaches a log, an
error, a warning, a manifest, a cache file or an export, and the semgrep
rules against `pickle`, `eval` and credential logging stay green; FRED and
ALFRED are never written to disk; hosted mode refuses every library-only,
bring-your-own-key and premium-local source (tested); an ALFRED vintage
request returns the values as first published, verified against a known
later revision; the policy-rule suite reproduces the Atlanta Fed and
Cleveland Fed reference figures within documented tolerances and matches the
0.2.x characterization fixtures or documents each intentional difference;
all 50 launch-catalog entries pass `registry.validate()` and their golden
and property suites; `pip install --pre pyeconomics==1.0.0a2` in a clean
venv fetches a BLS series without a FRED key and, with the tester's own FRED
key, runs the Taylor rule for a past date on ALFRED vintages, while plain
`pip install pyeconomics` still resolves 0.2.6; and
`scripts/verify-phase03.sh --fast` exits 0 on Ubuntu CI with the
`phase-verify.yml` matrix entry `03` green.

**Pre-requisite:** Phase 2 is closed — V1–V15 green on 2026-10-14 (PR #97),
`1.0.0a1` on PyPI with attestations, and `main` protected with 20 strict
required checks. Its registry reserves `ModelSpec.bindings` and its
manifests reserve `data_sources` for this phase; its canonical JSON,
schemas, golden harness, property strategies and contract suite are what
every new provider value and model passes through; and `verify-phase02.sh`
is the template for `verify-phase03.sh`. Phase 1's characterization
fixtures (`tests/fixtures/legacy/`) are the contract the rebuilt policy
rules must match. The operator holds admin on the GitHub repository
(environments and their secrets), owner rights with 2FA on the PyPI
project, the `pypi` environment's review and admin on the Read the Docs
project; holds, or registers at Step 6's kickoff, free API keys for FRED,
BLS, BEA and Census; and has the GitHub CLI authenticated with the `repo`
and `workflow` scopes.

**Dependency:** Phase 4 does not start until V1–V20 are green and `1.0.0a2`
is on PyPI. It generates `pyeconomics data search|get|vintages`, `keys` and
`cache` commands, REST `series` routes and MCP `get_series` and
`list_sources` from this phase's provider metadata and Python APIs; keys
its result cache on the vintages manifests record; runs its parity suite
through bound runs; builds hosted mode on the resolver's mode switch; and
withholds or gates MCP and AI-narrative results on `llm_use`. Phase 5's
snapshot job reads only providers classed `hosted-safe` here, and its "Data
sources & licences" page renders their metadata. Phase 6's
bring-your-own-key vendors and Bloomberg provider implement the same
contract, which Step 4's spike shaped around a session-based source.

**Design rationale (licence first, vintages by default).** The order inside
the phase is the design. Core hardening comes first (Step 1), so the three
known contract bugs are closed before provider values start flowing into
model inputs. ADR-0011 then fixes the data contract — the value types,
missing values, vintages, licence classes, the HTTP stack, the cache store,
bindings and the manifest — before any code bakes in a choice (Step 2).
Credentials and redaction (Step 3) come before the transport (Step 4), so
the first HTTP request 1.0 ever makes is built redaction-first: the 0.2.x
defect, a FRED key written to a log, is designed out rather than tested
out. The cache (Step 5) follows the SDK and enforces each source's terms
before any provider can ask it to store anything. Five provider steps
(Steps 6–10) apply a settled SDK to 31 sources, grouped by client
technology and licence class; the first is the hardest — FRED and ALFRED's
vintages and terms, the four keyed agencies, and the phase's first secrets
in a scheduled live run — so the pattern is set where it is hardest. The
catalog (Step 11) and bindings (Step 12) sit on the providers, the
monetary-policy suite (Step 13) is their end-to-end proof, where upstream
gaps surface while they are still cheap, and Steps 14–17 apply a settled
contract domain by domain. Real-time vintages are the default for every
historical evaluation, because 0.2.x's look-ahead bias (ROADMAP §2, gap 7)
is the error this phase exists to remove; revised data is an explicit,
labelled option. The release repeats Phase 2's gate-then-release pattern
(Steps 18–19): a published version can never be reused, only yanked.

**The data contract.** One provider is one registered class: a permanent
snake_case id, metadata the provider registry validates (licence class,
terms URL, terms-checked date, attribution, required notice, `llm_use`,
cache policy, host allowlist, rate limits, declared capabilities and the
extra it needs, if any) and a typed fetch pipeline that turns a query into
a `Series` or a `Table` — transform the query, extract, transform the data,
the pattern OpenBB's platform proved. Every value a provider returns is a
decimal where its unit is a rate (ADR-0008 decision 1), carries its units,
frequency, seasonal adjustment, source, licence class, attribution,
retrieval time and real-time period, and marks a missing observation as
`None`, never NaN. A model never imports the data layer: it declares
`Binding`s in its `ModelSpec`, `pyeconomics.bind()` resolves them through
the catalog as of a date — on the vintages the source kept, wherever it
kept them — and `compute` stays pure, while the manifest records every
series, vintage and retrieval time it read. The data layer's base class is
`DataProvider`, because `pyeconomics.core.Provider` already names the
distribution that registered a model; the entry-point group is
`pyeconomics.providers`, as ROADMAP §4 3.1 fixes it. The shape, as Steps 2,
4 and 12 build it (illustrative; ADR-0011 and those steps fix the real API):

```python
import pyeconomics
from pyeconomics.core import Binding, model
from pyeconomics.data import (
    DataProvider,
    LicenceClass,
    LlmUse,
    ProviderInfo,
    Terms,
)


class TreasuryProvider(DataProvider):
    info = ProviderInfo(
        id="treasury",
        name="US Department of the Treasury",
        terms=Terms(
            licence=LicenceClass.HOSTED_SAFE,
            url="https://home.treasury.gov/",
            checked="2026-10-20",
            attribution="Source: US Department of the Treasury.",
            llm_use=LlmUse.ALLOWED,
        ),
        hosts=("home.treasury.gov",),
    )


@model(
    id="macro.policy_rule",
    bindings=(
        Binding(field="inflation", concept="us.inflation.pce_core.yoy"),
        Binding(field="output_gap", concept="us.output_gap.cbo"),
    ),
)
def policy_rule(inputs: PolicyRuleInputs) -> PolicyRuleOutputs:
    return taylor_family(inputs)  # pure: no I/O, no clock


bound = pyeconomics.bind("macro.policy_rule", as_of="2008-12-16")
result = pyeconomics.run("macro.policy_rule", bound)
```

**Launch catalog, part two — the final list.** ROADMAP §4 3.7 lists the
live-data families and leaves the count at 18; these 18 ids are final and
become permanent when Step 19 releases them. Read by its semicolons, the
parent's table holds 19 families. This roadmap splits "Phillips curve and
Okun's law estimators" into two ids, because each is its own relationship
with its own literature, data and golden sources; folds CAPM into the
multifactor regressions, because both are one time-series estimator whose
factor set is the only difference (CAPM's security market line is that
entry's own output); and folds risk parity, inverse volatility and
hierarchical risk parity into one risk-based allocation family over a
covariance matrix. Each entry's formulas are the ones its catalog step
names.

| #  | Model id                           | Entry (ROADMAP §4 3.6–3.7)                                              | Step |
|----|------------------------------------|-------------------------------------------------------------------------|------|
| 33 | `macro.policy_rule`                | Taylor 1993 and 1999, balanced approach with and without shortfalls, inertial, first-difference, ELB-adjusted and forecast-based rules, with pluggable r* and gap measures | 13 |
| 34 | `macro.neutral_rate`               | r*: the published Laubach-Williams and Holston-Laubach-Williams estimates, or a constant | 13 |
| 35 | `macro.output_gap`                 | Output gap from potential output (CBO) or the HP, Hamilton, Baxter-King and Christiano-Fitzgerald filters | 14 |
| 36 | `macro.phillips_curve`             | Expectations-augmented Phillips curve estimator                         | 14   |
| 37 | `macro.okun_law`                   | Okun's law estimator, gap and first-difference forms                    | 14   |
| 38 | `macro.solow_growth`               | Solow model steady state and growth accounting                          | 14   |
| 39 | `macro.debt_dynamics`              | Public debt dynamics: r − g, the primary balance and the debt-stabilizing balance | 14 |
| 40 | `macro.recession_probability`      | The New York Fed's yield-curve recession probit                         | 14   |
| 41 | `fixed_income.curve_fitting`       | Nelson-Siegel and Svensson curve fitting and evaluation                 | 15   |
| 42 | `fixed_income.interest_rate_tree`  | Binomial interest-rate tree calibrated to a par curve; option-embedded bond values and OAS | 15 |
| 43 | `equity.implied_risk_premium`      | Implied equity risk premium from index level and expected cash flows    | 15   |
| 44 | `equity.cape`                      | CAPE (cyclically adjusted P/E), its earnings yield and the excess CAPE yield | 15 |
| 45 | `asset_pricing.factor_regression`  | CAPM beta, alpha and SML; FF3, Carhart, FF5 and FF6 time-series regressions | 16 |
| 46 | `asset_pricing.factor_model_tests` | The GRS test and Fama-MacBeth two-pass regressions                      | 16   |
| 47 | `portfolio.black_litterman`        | Black-Litterman equilibrium returns, posterior returns and weights      | 16   |
| 48 | `portfolio.risk_based_allocation`  | Inverse volatility, risk parity (equal risk contribution) and hierarchical risk parity | 16 |
| 49 | `econometrics.garch`               | GARCH, GJR-GARCH and EGARCH estimation and forecasts, over arch         | 17   |
| 50 | `econometrics.time_series`         | ARIMA/SARIMA, VAR with IRF and FEVD, Engle-Granger and Johansen, over statsmodels | 17 |

**The source plan.** Classes are ROADMAP §4 3.4's, read from each
provider's own terms on 2026-10-03; each provider's step re-reads its terms
page and records the URL and date before the provider merges (Licence
rule). "In-house" means a thin client on the phase's transport. A provider
id is permanent once released, as a model id is (ADR-0003).

| Id                          | Source and data                                                         | Client               | Class (to verify at merge)                    | Key or contact                       | Step |
|-----------------------------|-------------------------------------------------------------------------|----------------------|-----------------------------------------------|--------------------------------------|------|
| `fred`                      | FRED and ALFRED: 850k+ series, their vintages, v2 bulk release observations | in-house         | library-only, on the user's own key; never stored | FRED key (v1 query string; v2 header) | 6 |
| `bls`                       | BLS API v2: CPI, employment, JOLTS, PPI, ECI                            | in-house             | hosted-safe                                   | BLS registration key                 | 6    |
| `bea`                       | BEA API: NIPA (GDP, PCE prices), regional, international               | in-house             | hosted-safe                                   | BEA UserID                           | 6    |
| `census`                    | Census API: ACS, economic indicators, trade                             | in-house             | hosted-safe                                   | Census key                           | 6    |
| `treasury`                  | Treasury: daily par nominal and real curves; FiscalData                 | in-house             | hosted-safe                                   | none                                 | 7    |
| `fed_board`                 | Federal Reserve Board: H.15, SEP projections, GSW curve parameters      | in-house             | hosted-safe (public domain unless marked)     | none                                 | 7    |
| `nyfed`                     | New York Fed: Markets API, ACM term premia, LW and HLW r*, Staff Nowcast | in-house            | hosted-safe, with notices                     | none                                 | 7    |
| `sec_edgar`                 | SEC EDGAR: submissions, company facts, XBRL frames                      | in-house (edgartools rejected) | hosted-safe                         | the user's configured contact        | 7    |
| `openfigi`                  | OpenFIGI: identifier mapping                                            | in-house             | hosted-safe                                   | optional key                         | 7    |
| `imf`                       | IMF (SDMX): IFS, BOP, DOTS, WEO                                         | sdmx1 `[sdmx]`       | library-only until the IMF grants permission  | none                                 | 8    |
| `oecd`                      | OECD (SDMX): public datasets                                            | sdmx1 `[sdmx]`       | hosted-safe minus marked exceptions (terms checked 2026-10-16) | none                           | 8    |
| `ecb`                       | ECB (SDMX): FX reference rates, €STR, monetary statistics              | sdmx1 `[sdmx]`       | hosted-safe                                   | none                                 | 8    |
| `bis`                       | BIS (SDMX): policy rates, credit, property prices, effective FX rates  | sdmx1 `[sdmx]`       | hosted-safe, never paywalled                  | none                                 | 8    |
| `eurostat`                  | Eurostat (SDMX): public datasets                                        | sdmx1 `[sdmx]`       | hosted-safe minus listed exceptions           | none                                 | 8    |
| `world_bank`                | World Bank: WDI and about 45 databases                                  | in-house (wbgapi rejected) | hosted-safe where `License_Type` is CC BY | none                          | 8    |
| `dbnomics`                  | DBnomics: an aggregator of about 100 providers                          | in-house REST (its client is AGPL) | library-only                    | none                                 | 8    |
| `philadelphia_fed`          | Philadelphia Fed: Real-Time Data Set, Survey of Professional Forecasters | in-house            | library-only                                  | none                                 | 9    |
| `atlanta_fed`               | Atlanta Fed: GDPNow                                                     | in-house             | library-only                                  | none                                 | 9    |
| `cleveland_fed`             | Cleveland Fed: inflation expectations                                   | in-house             | library-only                                  | none                                 | 9    |
| `cbo`                       | CBO: budget and economic projections, potential output                  | in-house             | hosted-safe (public domain; read 2026-10-17)                     | none                                 | 9    |
| `penn_world_table`          | Penn World Table: national accounts, capital, TFP                       | in-house             | hosted-safe (CC BY 4.0; read 2026-10-17)                     | none                                 | 9    |
| `ken_french`                | Ken French Data Library: factors and portfolios                         | in-house             | library-only; fetched at runtime, never bundled | none                               | 10   |
| `shiller`                   | Robert Shiller: long-run US equity data                                 | in-house             | library-only                                  | none                                 | 10   |
| `damodaran`                 | Damodaran Online: industry aggregates (ERP, betas, multiples)          | in-house             | hosted-safe for aggregates, with credit; no bulk mirror | none                       | 10   |
| `aqr`                       | AQR data sets: factor returns                                           | in-house             | library-only                                  | none                                 | 10   |
| `hou_xue_zhang`             | Hou-Xue-Zhang q-factors                                                 | in-house             | library-only                                  | none                                 | 10   |
| `jkp`                       | Jensen-Kelly-Pedersen global factors                                    | in-house             | library-only (CC BY-NC)                       | none                                 | 10   |
| `open_source_asset_pricing` | Open Source Asset Pricing: anomaly signals and portfolios              | in-house (its client is GPL-2.0) | library-only                      | none                                 | 10   |
| `cboe`                      | Cboe: VIX history                                                       | in-house             | library-only                                  | none                                 | 10   |
| `coin_metrics`              | Coin Metrics community data: crypto network data                        | in-house             | library-only (CC BY-NC 4.0)                   | none                                 | 10   |
| `yfinance`                  | Yahoo Finance through yfinance: prices, fundamentals, options           | yfinance `[yfinance]` | library-only, off by default                 | none                                 | 10   |

Not built: Stooq (behind a bot challenge, terms unknown) and Nasdaq Data
Link, which Phase 6 adds as a bring-your-own-key source (ROADMAP §4 3.4).

**Licence rule.** A source's licence class is code, not prose. Every
provider declares its class, its terms URL, the date its terms were last
read, its attribution and required notice, its `llm_use` flag and its cache
policy, and the provider registry refuses a provider without them. Where
one source mixes classes, the class is decided per series from the
source's own markers — FRED's copyright tags, the World Bank's
`License_Type`, Eurostat's listed exceptions — and Moody's series on FRED
count as pre-approval whatever their label says. Hosted mode refuses every
source not classed `hosted-safe` or `user-supplied`, in the resolver and
again in the provider, so no route bypasses it. A source's terms are read
from its own terms page before its provider merges, and a test fails when a
provider's terms-checked date is more than 13 months old, which turns
ROADMAP §5's yearly review into a check. A source whose terms forbid
storage is fetched live and never written to disk — no opt-in — as ADR-0005
rule 4 and ROADMAP §5 "Data licensing policy" rule 4 require; this
withdraws ROADMAP §4 3.3's opt-in FRED cache, and Step 2 amends that
sentence and the matching acceptance criterion in the parent roadmap.

**Recording rule.** Every provider's offline tests replay recorded
responses ("cassettes") under `tests/providers/cassettes/<provider>/`, made
by the recorder Step 4 builds:

- The recorder scrubs credentials as it writes — every registered secret's
  value, every `api_key`, `registrationkey`, `UserID`, `key` and
  `Authorization` value, every cookie — and a contract test scans every
  cassette for the gitleaks rules, the project's own key patterns and any
  unscrubbed credential parameter, failing on a hit. A cassette never holds
  a placeholder that looks like a key: the gate blocks literal fake keys.
- A cassette keeps the real structure of the response (status, the headers
  the client reads, the body's shape) and a handful of observations: at
  most 24 per series and 32 KiB per file.
- For a source classed anything but `hosted-safe`, or whose terms forbid
  storage, the recorder replaces every observed value with a deterministic
  synthetic one and marks the cassette `"synthetic": true`; a test fails if
  such a cassette is not synthetic. No dataset, and no value from a
  library-only source, is mirrored into the repository (ROADMAP §5 "Data
  terms"). A golden case for a model may still cite the handful of
  published values it needs, each with its source and locator (Citation
  rule).
- Recording is a deliberate, local act (`scripts/record_cassettes.py
  <provider>`), never part of a test run: tests run with sockets disabled,
  and the live suite (`pytest -m live`) only reads.

**Credential rule.** This is the first phase that handles credentials, and
the 0.2.x defect it replaces was a key in a log. No session prints, echoes,
logs or pastes a key or an environment value (AGENTS.md "Never print
secrets"): a key's presence is checked by name only, and a test that needs
one reads it through the credential chain and never asserts on its value in
a way that would print it — collect the names of the sinks where a canary
appears and assert that list is empty. Canary values are generated at run
time (`secrets.token_hex`), never written as literals. Keys used in CI live
only as environment secrets of the `providers-live` GitHub environment,
never as repository secrets (Phase 1's V10.5 requires none to exist), and
reach only the scheduled and dispatched live run on `main`, never a pull
request. The maintainer sets them with commands the step prints
(`gh secret set <NAME> --env providers-live`, which prompts for the value);
a value never transits chat, a PR or a log. Listing a secret's name shows
only that it is configured; its value is proven by an authenticated
round-trip — a green live run. Tests isolate the user's configuration (a
temporary config, cache and `.env` directory per test), so no test ever
reads the maintainer's real keys except the opt-in live suite, and none
ever reads the repository root's ignored `.env`.

**Version rule.** Step 1 moves `main` from `1.0.0a1` to `1.0.0a2.dev1`: the
version records the milestone `main` is building towards, and `release.yml`
already routes a `.devN` tag to TestPyPI. Step 18 tags `main`'s HEAD
`v1.0.0a2.devN` to rehearse the exact candidate on TestPyPI (a failed
rehearsal is a NO-GO: the fix lands on a `fix/` branch that bumps `N`, and
the gate runs again). Step 19 sets `1.0.0a2` and tags the release.
`CITATION.cff` carries the same version as `pyproject.toml` at every
commit. A model whose outputs change gets a new model version and a
changelog entry (ADR-0003), and a provider or concept id never changes
once released.

**Dependency rule.** Every dependency Phase 3 adds — runtime, extra, test or
docs — is added with `uv add --no-config` (and `uv lock --no-config`, `uv
export --no-config`), so the maintainer's private index never reaches the
lock files, and passes `pip-audit`. A runtime dependency, or any package an
extra pulls in, must also pass the ADR-0004 licence allowlist (the
`licences` hook) or carry a reviewed entry in
`scripts/checks/licence_exceptions.toml` that the maintainer approves in
the pull request, with `tests/checks/test_licences.py`'s pin of the reviewed
set updated in the same change; such a package is also exempted by purl in
`security.yml`'s `dependency-review`, with a comment naming why. A required
runtime dependency is pure Python or has a Pyodide build (ADR-0002), and
the core still imports in Pyodide: the data layer imports its transport,
`sqlite3` and every third-party client lazily, inside the function that
needs it. A package an extra pulls in also joins the `test` dependency
group, so CI's default environment tests the code that needs it. Polars and
pyarrow are never dependencies, not even through an extra (ADR-0008
decision 8). Facts this roadmap relies on, read from PyPI on 2026-10-14;
the `licences` hook and the wheel listing at step time are the authority:

| Package | Latest | Licence metadata | Predicted `licences` result | CPython 3.15 wheel | Planned use |
|---------|--------|------------------|-----------------------------|--------------------|-------------|
| urllib3 | 2.8.0 | `MIT` | Passes | pure Python | runtime: the HTTPS transport (Step 4) |
| truststore | 0.10.5 | `MIT` | Passes | pure Python | runtime: the OS trust store for TLS (Step 4) |
| platformdirs | 4.13.0 | `MIT` | Passes | pure Python | runtime: config and cache directories (Step 3) |
| openpyxl, et-xmlfile | 3.1.5, 2.0.0 | `MIT` | Passes | pure Python | runtime: `.xlsx` sources (Step 7 first) |
| defusedxml | 0.7.1 | `PSFL`; classifier `Python Software Foundation License` | Expected to pass as PSF-2.0; otherwise a reviewed exception | pure Python | runtime: safe XML and spreadsheet parsing, which openpyxl uses when present (Step 7) |
| xlrd | 2.0.2 | `BSD` and classifier `BSD License` | Fails (ambiguous): reviewed exception | pure Python | runtime: legacy `.xls` sources (Step 10) |
| keyring | 25.7.0 | `MIT`; Linux closure: SecretStorage, jeepney, cryptography, cffi (`MIT-0`); also jaraco.*, more-itertools, pywin32-ctypes | Fails on Linux until cffi's `MIT-0` carries a reviewed exception | pure Python; cryptography and cffi abi3 | `[keyring]` extra (Step 3) |
| sdmx1 | 2.27.0 | classifier `Apache Software License` | Passes by classifier; its requests closure brings certifi | pure Python; lxml abi3 | `[sdmx]` extra (Step 8) |
| certifi | 2026.7.22 | `MPL-2.0` | Fails: reviewed exception, reached only through `[sdmx]` and `[yfinance]` | pure Python | transitive |
| yfinance | 1.7.0 | `Apache-2.0`; closure: curl_cffi (with cffi, `MIT-0`, on every OS), peewee (no licence metadata), protobuf, websockets, lxml, beautifulsoup4, multitasking, pytz | Fails until peewee and certifi carry reviewed exceptions (cffi's comes from Step 3) | pure Python; compiled parts abi3 | `[yfinance]` extra (Step 10) |
| arch | 8.0.0 (2025-10-21) | `NCSA` | Passes | none (cp310–cp314 only) | `[econometrics]` (Step 17, under the Wheel rule) |
| linearmodels | 7.1 (2026-10-16) | `NCSA` | outside the allowlist's scope (test only) | yes, every OS (from 7.1) | not used: statsmodels and SciPy are Step 16's oracles |
| quantecon | 0.13.0 | no licence metadata (BSD-3-Clause in its repository) | outside the allowlist's scope (test only) | pure Python; numba has cp315 | test oracle for the Hamilton filter (Step 14) |
| statsmodels | 0.15.0 | `BSD-3-Clause` | Passes (already in `[econometrics]`) | yes | adapter and oracle (Steps 14–17) |
| httpx | 0.28.1 (2024-12-06) | `BSD-3-Clause`; requires certifi | — | pure Python | not used (ADR-0011 decision 10) |
| duckdb | 1.5.6 | classifier `MIT License` | — | none | not used (ADR-0011 decision 14) |
| wbgapi | 1.0.14 | `MIT`; requires PyYAML (no cp315 wheel) and requests | — | — | not used: in-house client (Step 8) |
| edgartools | 5.62.0 | `MIT`; requires pyarrow and 19 more packages | — | — | not used: ADR-0008 decision 8 (Step 7) |
| PyPortfolioOpt | 1.6.0 | `MIT`; requires cvxpy (no cp315 wheel) and scikit-base < 0.14, which needs Python < 3.15 | — | — | not used: it cannot install on CPython 3.15 (Step 16) |
| openassetpricing | 0.0.2 | `GPLv2` | Excluded by licence | — | not used: in-house client (Step 10) |

**Wheel rule.** CI runs every cell of Python 3.12–3.15 on Ubuntu, Windows
and macOS (twelve, Phase 1 check 35 and V10.2), so a dependency must
install from a wheel, or be pure Python, on all of them. On 2026-10-14
duckdb, arch, linearmodels, cvxpy and PyYAML publish no CPython 3.15
wheel. A candidate without one at its step's kickoff is never added on
hope: the step uses a replacement that has one, implements the piece
natively against an oracle that installs, or — only for an optional extra,
with the maintainer's approval in the pull request — gates the package with
the environment marker `python_version < "3.15"`, makes the model raise
`MissingOptionalDependencyError` naming the gap on the uncovered cells, has
a test assert exactly that there (never a skip), and opens an issue to drop
the marker when the wheels ship.

**Cross-phase verification rule.** `phase-verify.yml` runs
`verify-phase01.sh` and `verify-phase02.sh` (`--fast` and `--security`) on
every Phase 3 pull request, and those checks were written against earlier
trees. When a Phase 3 change legitimately invalidates one of them, the same
pull request narrows the check to the invariant it was protecting, never
deletes it, and appends a line to a `## Post-merge addendum (<YYYY-MM-DD>)
— Phase 3 changes to verify-phase0N.sh` section at the end of that phase's
roadmap, the pattern Phase 2 used at the end of `phase01-roadmap.md`. Unit
tests that pinned Phase 2's reservations change in the step that fills
them. The ones this roadmap foresees:

| Check or test | What it pins today | Step that narrows it |
|---------------|--------------------|----------------------|
| `tests/registry/test_spec.py` and `test_validate_rules.py` (the `bindings` rule) | `bindings` must be empty | Step 12 |
| `tests/results/test_manifest.py` | schema 1, an empty `data_sources`, no `date` or `time` key, no `:` in a value | Step 12 (schema 2; the run-level manifest stays clock-free) |
| `tests/results/test_runner.py` (an empty `data_sources`) and `test_cards.py` (`DESCRIPTION_KEYS`) | no data source; no binding key | Step 12 |
| `verify-phase02.sh --post`'s published install (V14.3) | runs the working tree's `scripts/smoke.py` against PyPI's `1.0.0a1` | Step 2 (run the `v1.0.0a1` copy of `smoke.py`, as `release-smoke.yml` already checks out its tag's scripts) |
| `tests/models/test_registry_is_not_empty.py` | exactly Phase 2's 32 ids | Step 13 (at least those 32, plus this roadmap's ids as they land) |
| `tests/registry/test_released_ledger.py` | `len(RELEASED) == 32`, and the ledger equals `registry.ids()` | Step 13 (every released id registered; unreleased ids allowed until Step 19 extends the ledger) |
| `docs/index.md` | "32 model families across 11 domains" | Step 19 |
| `scripts/smoke.py --min-domains 11` (CI, release-smoke, `verify-phase02.sh`) | at least 11 domains | unchanged, a floor; Phase 3's own checks require 13 from Step 16 |
| Phase 1 V10.5 | no repository secret exists | unchanged: the live run's keys are environment secrets |
| Phase 1 checks 37 and 38 | workflow hardening (`permissions: {}` at the top of every workflow, SHA pins, `persist-credentials: false`); no `tests.yml` or `docs.yml` | unchanged: `providers-live.yml` and `providers-heartbeat.yml` comply |
| Phase 2 check 4 | runtime floors of pydantic, NumPy, SciPy and pandas, no upper bound | unchanged: new runtime dependencies carry no upper bound either |

**Contract-change rule.** Steps 6–10 build on the contract Steps 1–5 fix,
and Steps 13–17 on the catalog and bindings Steps 11–12 add. A step that
cannot be completed without a contract change makes the change in-step
(Triage rule: an upstream gap that blocks the step): the smallest change
that works, every registered model, golden case, provider and cassette kept
green, the owning step's `<task>` block patched and the change added to the
carry-over checklist in this file's last section. A change to a decision
ADR-0008 or ADR-0011 records is a superseding ADR in the same pull request,
because an Accepted ADR is never edited (`docs/adr/README.md`).

**Citation rule.** A golden case cites an independent source with a locator
(page, table, section, equation, or file and row) and, for a web page or a
data release, an access date. Official publications come first — the
Federal Reserve Board's Monetary Policy Report, H.15 and
Gürkaynak-Sack-Wright files, BEA and BLS news releases, the Atlanta Fed's
Taylor Rule Utility, the Cleveland Fed's simple monetary policy rules, the
New York Fed's r* and recession-probability files, the ECB's published
Svensson parameters — then peer-reviewed papers, textbook values recomputed
independently, and closed-form identities. A golden case built on a
dataset keeps only the values it needs, each cited by file, table, row and
access date. CFA Program curriculum examples, questions and text are never
used, and no source's prose is copied: numbers and formulas only, in our
own words. Each step's pull request lists every new source in its body.

**Branch strategy.** Every step in this phase lands on its own short-lived
feature branch (`feature/phase03-step<M>-<slug>`), opens a pull request
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
git checkout -b feature/phase03-step<M>-<slug>
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
feature/phase03-step<M>-<slug> <worktree-path> origin/main`, the worktree
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
done, exactly like its tests. Phase 3 is the first phase to handle
credentials — users' provider keys on their machines and the maintainer's
keys in one protected CI environment — and the first to make network
requests, so its exposures are a key leaking through a log, an exception,
a warning, a manifest, a cache file, a cassette or an export (ROADMAP §5
threat 1, the 0.2.x defect); server-side request forgery and unsafe
deserialization through data paths (threat 3); licensed data reaching a
fixture or, later, the hosted service (threat 4); and the supply chain of
new data clients.

**Deploy-and-verify rule.** Merged is not deployed, and deployed is not
released. Every step header carries a `**Deploys:**` line naming the surface
and environment the step's merge reaches — or `nothing beyond merge` — and
when going live needs a release, a version-floor bump, a migration, or a
redeploy, the line says so and this step (or a named follow-on step) owns that
event. For a step whose Deploys line names a surface, Stage 4 of the lifecycle
does not end at the squash-merge: the step's acceptance criteria carry a
**Deployed & verified** bullet (the surface's version/health endpoint reports
this build, and the changed behaviour is exercised in the target environment
with real authentication via the hands-off recipe the step names), and that
bullet must be green before the step is declared complete. In Phase 3 the
surfaces are the scheduled live run (`providers-live.yml` in the
`providers-live` environment, from Step 6; every provider step extends what it
covers), the Read the Docs `main` preview (the data guide and the generated
source and concept pages, verified live at Step 11), TestPyPI (Step 18) and
PyPI (Step 19); their hands-off recipes are a `workflow_dispatch` run on
`main` read back with `gh run view`, the Read the Docs API and page text, and
a clean-venv install of the exact version followed by `scripts/smoke.py` and
the live recipe each release step names. A step that introduces a required
environment variable or shared secret verifies at kickoff that it exists in
every target environment and proves shared values by an authenticated
round-trip — never by listing env names. See the parent ROADMAP "Release &
deployment strategy" for the surfaces table, promotion path, staged-rollout
rule, migrations, and rollback.

**Triage rule.** Findings surfaced while executing a step are classified
before they are acted on, per the parent ROADMAP "Defect handling &
triage": spec rot → edit this roadmap's affected `<task>` block now;
upstream gap → patch the earlier step's prompt and add it to the
carry-over checklist (the last list in this file's Not-in-scope section);
implementation bug → fix in-step only if it blocks this step's acceptance
criteria, otherwise an issue and its own branch in a fresh conversation;
model error (a published model returns a wrong number) → a High defect: a
`fix/` branch, the failing case added as a golden test, and an entry on
the errata page; a provider whose source changed its terms → a High defect
(ROADMAP §5 "Data licensing policy" rule 7): reclassify it and record the
change in the changelog; architectural question → an issue for a future
phase; process improvement → recorded where the next conversation will
read it; security finding → jumps the queue by severity. A step's PR
contains the step plus blocking fixes only, and lists the issues it
opened. When a merged PR auto-closes an issue, the environment check is
what earns the close — reopen or follow up if a gap remains.
`docs/phase03-qa-findings.md` is the rollup: every finding, its class, and
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
step's heading (`## Step 4 — Provider SDK, Transport and Contract Suite ✅`)
so the completion shows in the rendered preview, the outline, and the table
of contents, sets the step's Summary Table Status cell to `Complete — PR
#<n>`, commits that edit on the step branch, and pushes. The PR therefore
carries its own completion mark, and the roadmap on `main` says a step is
complete exactly when that step's PR merges — never before. This file's
phase-level `**Status:**` line (under the title) and the parent project
roadmap are marked the same way, in the same commit: Step 1's PR flips
both from `Not started` to `In progress` (the parent's `### Phase 3` line
reads `In progress — phase03-roadmap.md`, and its "Phase Complexity
Summary" row reads `In progress`), and the final step's PR flips both to
`Complete — …` (the parent's with its row in the "Phase Complexity
Summary" table and the header `> **Status:**` line) and appends ` ✅` to
this file's `# ` title and to the parent's `### Phase 3` heading, so the
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
   `git checkout -b feature/phase03-step<M>-<slug>` from a clean,
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
   on the step branch (`docs: mark Phase 3 Step M complete`), and push —
   the PR now carries its own completion mark, so the roadmap on `main`
   will say the step is complete exactly when the PR merges (Status rule).
   On the phase's first step, the same commit sets this roadmap's
   phase-level `**Status:**` (under its title) and the parent project
   roadmap's Phase 3 `**Status:**` to `In progress`; on the final step,
   both to `Complete`, with ` ✅` appended to this roadmap's `# ` title and
   to the parent's `### Phase 3` heading.

4. **Wait for green checks, then squash-merge.** Every required status
   check must report success: the 20 Phase 2 left required (lint, types,
   the aggregate `test` gate — which needs the twelve-cell test matrix,
   `pyodide` and `docs` — package, lockfile, pr-title, dco, the nine
   security checks, and both `phase-verify` jobs for `01` and `02`), plus
   both `phase-verify` jobs for `03` once Step 20 adds them. If the PR goes
   BEHIND main while waiting, refresh with `gh pr update-branch --rebase` —
   never merge `main` into the branch; `required_linear_history: true`
   enforces rebase. Once every check is green:

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

## Current State (as of Phase 2)

### Package and contract surface

- `src/pyeconomics/` holds `core/` (31 modules), `models/` (11 domain
  packages, 32 models) and the `registry.py` facade; `pyeconomics.__all__`
  is `__version__`, `registry`, `run` and `run_batch`. No `data/`, `cli/`,
  `server/` or `mcp/` package exists, and four of the fifteen `DOMAINS` in
  `core/spec.py` — `macro`, `micro`, `alternatives` and `asset_pricing` —
  have no package or entry point yet. `pyproject.toml` declares version
  `1.0.0a1` and one entry-point group, `pyeconomics.models`, with eleven
  entries.
- Phase 2 reserved this phase's hooks without plumbing them:
  `ModelSpec.bindings` is a `tuple[object, ...]` documented as "Reserved
  for Phase 3's data bindings" (`core/spec.py`), and the `bindings` rule
  among `validate()`'s 32 rule slugs rejects any non-empty value
  (`core/_rules.py`); the `@model` decorator has no `bindings` parameter;
  `Manifest` is schema 1 with `data_sources = ()`, "always empty until
  Phase 3", and its docstring promises no wall-clock time, host, user,
  path or environment value, "and none is ever added"; `Manifest.create`
  takes no data sources; `run(model_id, inputs=None, /, **fields)` has no
  as-of or vintage parameter, and `**fields` is the model's own input
  namespace; `describe()`'s 22 `DESCRIPTION_KEYS` and the model card's
  sections have no binding or data entry.
- `pyeconomics.core.Provider` already names the distribution that
  registered a model, with its declared extras (`core/registry.py`), so the
  data layer's provider class needs another name (ADR-0011). Core's
  `Frequency` is the compounding enum ADR-0008 decision 4 defines (annual
  to daily, period-end pandas aliases, no business-daily member), not an
  observation frequency; FRED, BLS and BEA date a monthly or quarterly
  observation by its period's start.
- Models may import only `pyeconomics.core` (minus the registry's
  internals), their own domain package, a stdlib subset, NumPy, SciPy,
  pandas and pydantic, and an extra's library inside `compute`
  (`tests/registry/test_model_imports.py`, whose `EXTRA_DOMAINS` maps
  `econometrics` to its domain); the `model-purity` semgrep rule bans I/O,
  the clock, the environment and the network in `src/pyeconomics/models/`.
  A model therefore cannot import a data layer, and a `Binding`
  declaration must live in core.
- The three open bugs this phase owns sit in shared core: the unit markers
  in `core/units.py` accept `True` and epoch numbers (#75); `_rules.py`
  lets a numeric `Literal` field go without a unit (#81); and the IRR in
  `core/cashflows.py`, on `core/numerics.py`'s root policy (ADR-0008
  decision 11), misses roots that sit exactly on its bracket's ends (#85),
  which `foundations.time_value`, `corporate.capital_budgeting` and
  `performance.return_measurement` share.
- `scripts/new_model.py` scaffolds a model, a golden file and a test file
  with no binding; `scripts/smoke.py` picks one model per registered domain
  from an installed wheel's registry and runs it (CI passes
  `--min-domains 11`; the default is 0); `scripts/release_ledger.py`
  extends `core/_released.py`, which holds the 32 ids first released in
  `1.0.0a1`. `scripts/checks/dist_contents.py` admits only `.py` files,
  `py.typed` and dist-info metadata in the wheel, so every package resource
  — the concept catalog included — stays a Python module unless a step
  extends the allowlist in the same change.

### Data and legacy surface

- No data layer exists: no provider, credential, cache, vintage, catalog
  or binding code, and no error class for a data, provider, credential or
  network failure; "vintage", "as_of", "llm_use" and "licence class" have
  no hit in `src/`. `core/rates.py` already names the boundary: sources
  such as FRED publish percent, so the data layer converts them with
  `percent_to_decimal`.
- 0.2.x lives on `legacy/0.2.x` (`v0.2.6`, security fixes only until
  1.0.0). Its `FredClient` took the key from an argument, `FRED_API_KEY`
  or the keyring, and cached every response in a pickle file under the
  repository's `cache/`, created at import — FRED content stored against
  FRED's terms. Its rules read `PCETRIM12M159SFRBDAL`, `NROU`, `DFII10` and
  `UNRATE`, spliced `DFEDTAR` and `DFEDTARU` at 2008-12-15, computed
  `rho·fed_rate + (1 − rho)·max(rule, elb)` when the lower bound applied,
  rounded every result to two decimals, and filled historical gaps
  forward. Nothing archived merges to `main`.
- `tests/fixtures/legacy/` (thirteen byte-exact files, never edited) is
  this phase's contract: `taylor_rule.json` (1,040 cases: 720 on the base
  grid and 80 for each of the `alpha`, `beta`, `okun_factor` and
  `inflation_target` corners), the balanced-approach rule without and with
  shortfalls (960 cases each), `first_difference_rule.json` (1,040),
  `calculate_policy_rule_estimates.json` (48), a synthetic monthly panel
  (2000-01 to 2024-12, month-start dates) and four historical tables plus
  their combination, each in two configurations (`rho` 0 without the lower
  bound; `rho` 0.7 with it). Values are percent rounded to two decimals;
  inertia is every rule's `rho`, not a separate rule; FRED fetching and
  caching were stubbed, not characterized. No test loads them yet, and
  their README says the rebuilt rules "must match every output here or
  document each intentional difference".
- `docs/releases/1.0.0a1.md` tells users the FRED-backed rules arrive in
  Phase 3. ADR-0005's Confirmation table assigns the provider contract and
  the cache policy to this phase, and its decision text leaves OECD's
  class TBD until its provider merges.
- The maintainer's machine keeps git-ignored 0.2.x leftovers — a stale
  package tree at the repository root, `cache/` and a `.env` — so tests run
  with `uv run pytest`, never `python -m pytest`, and no test may read the
  root `.env` (Credential rule).

### Dependency and licence surface

- Runtime dependencies are `holidays>=0.106`, `numpy>=2.4`, `pandas>=3.0`,
  `pydantic>=2.12` and `scipy>=1.18`, floors Pyodide 314.0.7 satisfies
  (ADR-0008 decision 14). Extras: `econometrics = [statsmodels>=0.15.0]`,
  `plot = [plotly>=7.1.0]`, `all` with both, and `server`, `mcp` and `ai`
  empty; no provider extra exists. The `test` group adds hypothesis,
  jsonschema, numpy-financial, plotly, polars, pyarrow, pytest and its
  plugins (pytest-socket among them), QuantLib, rfc8785, statsmodels,
  Sybil, syrupy and vollib.
- `scripts/checks/licence_exceptions.toml` holds five reviewed entries
  (numpy, scipy, pandas, python-dateutil and patsy), pinned by
  `tests/checks/test_licences.py`; `licences.py` excludes `financepy`,
  `rateslib`, `getfactormodels`, `dbnomics` and `full-fred` by name, and
  `verify-phase02.sh` check 5 refuses a licence exception naming any of
  them or `openbb`. `dependency-review` allows MIT, BSD-2-Clause,
  BSD-3-Clause, Apache-2.0, ISC, NCSA and PSF-2.0, with fourteen purl
  exemptions.
- No data client is in the lock: httpx, sdmx1, wbgapi, duckdb, keyring,
  pydantic-settings, python-dotenv and edgartools are absent, and
  requests, urllib3 and platformdirs arrive only transitively through the
  `docs` group. The Dependency rule's table predicts what each candidate
  will need.

### Toolchain and test surface

- pytest runs with `--strict-markers --strict-config -ra --doctest-modules
  --import-mode=importlib --disable-socket --benchmark-disable`,
  `xfail_strict` and `filterwarnings = ["error"]`, over `tests`, `src` and
  `docs`; the markers are `invariant(model_id, invariant_id)` and
  `oracle(model_id)`. Nothing enables sockets:
  `tests/unit/test_network_blocked.py` says a test that needs the network
  opts in with `enable_socket`. Hypothesis has a derandomized `ci` profile
  and a `dev` profile. Coverage measures branches with `fail_under = 95`,
  and `scripts/checks/coverage_floors.py` holds `core/` at 95% and
  `models/` at 90% (Phase 2 closed at 99.89%, 99.65% and 99.75% overall).
- `tests/` holds `checks/`, `docs/`, `fixtures/legacy/`, `golden/` (one
  TOML file per model; source kinds `certified`, `official`, `paper`,
  `textbook` and `identity`; at least three cited cases with an edge case;
  no datasets), `models/` (the contract suite, invariant coverage, the
  registry-not-empty test and per-domain property and oracle tests),
  `property/`, `registry/`, `repo/` (the phase twins and the smoke test),
  `results/` and `unit/`. No recorded-HTTP tooling exists: no vcrpy, respx,
  pytest-recording or cassette directory.
- mypy is strict with the pydantic plugin over `src` and `tests`; ruff
  selects `ALL` at line length 88, `CPY001` included, and formats Python
  code blocks in Markdown, roadmaps included; ty is informational. Phase 2's
  lessons hold: search for valid witnesses with Hypothesis's `find` rather
  than asserting every branch appears in a finite random batch; statsmodels
  resets warning filters, so record its warnings explicitly; `@model`'s
  `extra=` is a string literal that `EXTRA_DOMAINS` maps; run every
  lock-changing uv command with `--no-config`; and write files as LF bytes,
  never through Python's `write_text` on Windows.

### CI/CD and publishing surface

- `ci.yml`: `lint`, `types`, `ty` (informational), `tests` (Ubuntu, Windows
  and macOS × Python 3.12–3.15, twelve cells, `HYPOTHESIS_PROFILE=ci`, the
  `licences` hook on each OS), `package` (build, `twine check --strict`, the
  artifact allowlist, `smoke.py --all --min-domains 11` in a clean venv and
  again with extras), `pyodide` (Pyodide 314.0.7 runs `smoke.py`), `docs`
  (`sphinx-build -W`), `lockfile`, `pr-title`, `dco` and the aggregate `test`.
  `security.yml`: `gate-secrets`, `gate-sast`, `gate-deps`, `gate-licences`,
  `trufflehog`, `zizmor` and `dependency-review`. `codeql.yml` runs on every
  pull request and push and weekly, and its `codeql (python)` and
  `codeql (actions)` contexts are required; `scorecard.yml` runs on push and
  weekly. `phase-verify.yml` runs `verify-phase<NN>.sh --fast` and
  `--security` for the matrix `["01", "02"]`.
- `release.yml` publishes a `v*` tag on `main` whose name equals the
  project version — a `.devN` to TestPyPI, anything else to PyPI behind the
  `pypi` environment's approval — with PEP 740 attestations, then calls
  `release-smoke.yml`, which installs the exact version in a fresh venv
  and runs the smoke. `main` requires 20 checks, strict: lint, types, test,
  package, lockfile, pr-title, dco, the nine security contexts, and
  `phase-verify-fast` and `phase-verify-security` for `01` and `02`.
- Every workflow sets `permissions: {}` at the top, starts each job with
  harden-runner (`egress-policy: audit`), sets `persist-credentials:
  false`, pins actions to commit SHAs and runs on GitHub-hosted runners,
  as a public repository's do. No workflow references a secret or holds
  `issues: write`, and the repository has no repository or environment
  secret: the `testpypi` and `pypi` environments only gate tag
  deployments. Dependabot updates the `uv` and `github-actions` ecosystems
  weekly; its PR #61 (`uv_build`) is open and owned outside this phase.

### Security and sensitive-data surface

- This is the first phase that handles credentials: users' FRED, BLS, BEA,
  Census and OpenFIGI keys on their own machines, a contact address for
  SEC EDGAR's User-Agent, and the maintainer's keys in the `providers-live`
  environment from Step 6. ROADMAP §5 classifies provider keys as
  user-machine-only — never logged and never in a manifest, cache,
  exception or export — and its threat model leads with exactly that leak.
- The prek gate runs gitleaks (staged changes; CI scans the whole tree;
  a custom `fred-api-key` rule; no allowlists), bandit, semgrep with the
  project rules `credential-logging` (printing or logging a name like a
  key, token, secret, password or credential, repository-wide),
  `dynamic-code` (`eval`, `exec`), `unsafe-deserialization` (`pickle`,
  `marshal`, `shelve`, `pandas.read_pickle`, `numpy.load` with pickles) and
  `unsafe-yaml`, plus `model-purity` for `models/` and the `semgrep-test`
  hook; then `pip-audit --locked`, `lock-index`, `licences`, zizmor and
  `no-commit-to-branch`. ROADMAP §4 3.2's "no `pickle`, no `eval`
  anywhere" already holds, repository-wide; this phase keeps it green.
- `src/pyeconomics/data/` will do I/O by design — network, files, the
  environment, the clock for retrieval times — so neither `model-purity`
  nor the import allowlist covers it. Its guards are this phase's to
  build: host allowlists and no user-supplied URL (server-side request
  forgery), HTTPS only, response size and iteration caps, parsers that
  never execute data (no `pickle`, no `eval`, no `yaml.load`, XML parsed
  with external entities and network access off), and the redaction and
  canary tests of Step 3.
- `.gitignore` already ignores `.env`, `.env.*`, `secrets.py` and
  `cache/`; Phase 1 check 24 requires `.env` there and forbids
  blanket-ignoring `*.json`, so JSON cassettes stay trackable. Patterns
  every step mirrors: refer to a fake credential by its location, never
  quote it; treat a workflow change as a security-relevant diff (SHA pins,
  least-privilege `permissions:`, `persist-credentials: false`, no
  `pull_request_target`, zizmor clean); keep the private uv index out of
  the lock files with `--no-config`.

### Documentation surface

- Read the Docs builds the 1.0 preview from `main` as version `main`
  (`/en/main/`) through `.readthedocs.yaml` (`uv sync --locked --group docs
  --all-extras`, warnings as errors), while `stable` and `latest` serve
  0.2.6 until Phase 5. `docs/conf.py` uses MyST-NB, sphinx-autoapi,
  Napoleon and the local `model_pages` extension, which generates
  `reference/models/<domain>/<name>.md` from each card at build time; an
  audit hook blocks every non-loopback socket during the build, so a
  generated data page must come from metadata, never from a fetch; the
  roadmaps, ADRs, release documents and QA findings are excluded from the
  site; Sybil tests eight Markdown pages.
- Pages: `index` (whose text says "32 model families across 11 domains"),
  installation, quickstart, the first-model tutorial, conventions,
  results, errata, notices (no provider notice yet) and the changelog. No
  data-sources-and-keys guide exists: ROADMAP §4 3.8 asks for one, and
  Phase 1 left it to this phase when it removed the 0.2.x FRED page.
- `CHANGELOG.md` (Keep a Changelog) ends at `[1.0.0a1] - 2026-10-13` with no
  `[Unreleased]` section; `docs/releases/1.0.0a1.md` lists #75, #81 and #85
  as known limitations; `CITATION.cff` names `1.0.0a1`.

### Operations and observability surface

- No runtime service exists. Package publishing is the one live surface:
  its health signal is `release-smoke.yml`, its alarm GitHub's
  failed-workflow email, proven twice (Phase 1 run 37866605106; Phase 2 run
  38503796017, a dispatch against the nonexistent `0.0.0.dev0`, which
  proves the notification, not model execution), and its rollback a yank
  and a `.postN` release.
- ROADMAP §5 "Health signals" lists the free-source providers' weekly live
  contract run — a scheduled CI workflow that opens an issue — and its
  "Rules" give scheduled automation a heartbeat (an alarm when it has NOT
  succeeded within its cadence) and a staleness policy (the newest issue
  supersedes older ones, which are closed). Phase 3 adds that surface:
  `providers-live.yml` (the weekly live run), `providers-heartbeat.yml` (a
  daily check that a live run succeeded within eight days), the
  `providers-live` environment and its secrets, and one issue per failing
  run under a `provider-live` label. It is the project's first scheduled
  automation that holds secrets or writes issues; Step 20 proves its alarm
  with a synthetic failure. Its runbooks are ROADMAP §5's "Upstream source
  down or changed" (open an issue, re-record the provider's cassettes) and
  "User reports a leaked provider key".
- No metered dependency arrives: every source is free, and the live run
  uses GitHub-hosted minutes on a public repository.

### Verification surfaces

- `scripts/verify-phase01.sh` (50 static checks, V1–V12) and
  `scripts/verify-phase02.sh` (66 static checks, V1–V15) share the mode
  contract `--fast`, `--python`, `--security`, `--live`, `--all` and
  `--post`, the `record` / `check` / `vcheck` / `vstatic` helpers, the
  `PASS  12     <description>` line format and the per-mode summary
  ending in `RESULT: PASS`. Phase 2's static checks 1–65 are one
  standard-library Python program and check 66 a Bash secret-pattern scan;
  `--fast` takes about three seconds on Ubuntu, and `--post` took 1,753
  seconds. `verify-phase02.sh` is the template for `verify-phase03.sh`, and
  `tests/repo/test_phase02.py` the template for its pytest twin.
- `.github/workflows/phase-verify.yml` runs the matrix `phase: ["01",
  "02"]`, both jobs required; Phase 3 appends `"03"`. Phase 2's verifier
  rules hold: no static check pins a value a later phase legitimately
  changes (state "at least" invariants); clean wheel venvs use the
  project's interpreter (`uv python find --no-config`); and nobody edits a
  Bash verifier while it runs.

---

## Execution Order

```
Step 1  (core hardening)              #75, #81, #85 closed; main at
                                      1.0.0a2.dev1; roadmap and kit
                                      landed → implement
  ↓
Step 2  (ADR-0011 + data model)       docs/adr/0011, data/ value types:
                                      Series, Table, Terms, vintages
                                      → implement
  ↓
Step 3  (credentials + redaction)     Secret, the key chain, [keyring],
                                      pyeconomics.toml, redaction, canary
                                      tests → implement
  ↓
Step 4  (provider SDK + transport)    DataProvider, registry, transport,
                                      modes, cassettes, contract suite,
                                      Bloomberg spike → implement
  ↓
Step 5  (cache + offline mode)        SQLite store, licence-aware policy,
                                      time-to-live, offline mode
                                      → implement
  ↓
Step 6  (FRED and ALFRED, BLS, BEA,   4 keyed providers, vintages,
         Census)                      providers-live.yml and its secrets
                                      -> implement
  |
  +--> Step 7 (parked SEC follow-up; NOT a join for Steps 10-20)
  |          Completes only after all five original providers pass
  |
  +--> Step 8 (SDMX, World Bank, DBnomics)
             7 providers, [sdmx] -> Complete
             |
             v
       Step 9 (regional Feds, CBO, PWT)
              5 providers; bounded XLSX reader -> Complete
             |
             v
Step 10 (finance research data +      10 finance providers, [yfinance],
         four unblocked providers)    Treasury, Fed Board, NY Fed, OpenFIGI
                                      -> implement
  ↓
Step 11 (catalog + resolver)          concepts, transforms, alignment,
                                      fallback, hosted gates → implement
  ↓
Step 12 (bindings + vintage runs)     Binding, bind(), run(bound),
                                      manifest schema 2 → implement
  ↓
Step 13 (monetary-policy suite)       macro.policy_rule,
                                      macro.neutral_rate; Atlanta and
                                      Cleveland goldens; 0.2.x parity
                                      → implement
  ↓
Step 14 (catalog: macro)              6 entries → implement
  ↓
Step 15 (catalog: fixed income +      4 entries → implement
         equity)
  ↓
Step 16 (catalog: asset pricing +     4 entries → implement
         portfolio)
  ↓
Step 17 (catalog: econometrics)       2 entries, arch → implement
  ↓
Step 18 (1.0.0a2 readiness gate)      v1.0.0a2.devN on TestPyPI, a live
                                      end-to-end run, readiness document,
                                      GO / NO-GO → implement
  ↓
Step 19 (1.0.0a2 release)             v1.0.0a2 on PyPI, ledger at 50 ids,
                                      GitHub release → operate
  ↓
Step 20 (QA + verify-phase03.sh)      scripts/verify-phase03.sh
                                      + docs/phase03-qa-findings.md
                                      + phase-verify.yml matrix entry
                                      → create

--- post-implementation ---

V1   #75, #81 and #85 closed with regression tests; affected models
     re-versioned with an erratum; main reads 1.0.0a2.dev1.
V2   ADR-0011 Accepted; the data value types tested; the data coverage
     floor holds; the core still imports in Pyodide.
V3   Keys resolve in the declared order; canaries reach none of six
     sinks; config files refuse secrets.
V4   The provider registry validates; the transport refuses foreign
     hosts; the contract suite and hosted refusal pass offline.
V5   The cache follows each source's terms: no-storage sources are
     never written; time-to-live and offline mode are tested.
V6   Four keyed providers pass; ALFRED's first release is verified;
     the live run is green on main.
V7   Four recovered providers pass offline and live; SEC passes too
     if included, otherwise the named external deferral is recorded.
V8   Seven SDMX and international providers pass, with series-level
     licence gates.
V9   Five regional-Fed and research providers pass; CBO and the Penn
     World Table are classified.
V10  Ten finance research providers pass; yfinance is off by default.
V11  Concepts resolve; hosted mode resolves to originators only;
     alignment is explicit.
V12  Bound runs record every series, vintage and retrieval time.
V13  The policy rules match the Atlanta and Cleveland Fed figures and
     the 0.2.x fixtures, or document each difference.
V14  Six macro entries meet the definition of done.
V15  Four fixed-income and equity entries meet it.
V16  Four asset-pricing and portfolio entries meet it.
V17  Two econometrics entries meet it; the extra installs and runs.
V18  Readiness evidenced, with the maintainer's GO; the rehearsal is on
     TestPyPI with attestations.
V19  1.0.0a2 on PyPI fetches BLS without a FRED key and runs the Taylor
     rule on ALFRED vintages with the tester's key; plain pip install
     still resolves 0.2.6.
V20  verify-phase03.sh --fast and --security exit 0 in phase-verify.yml;
     the live-run alarm fired; Phases 1 and 2 stay green.
```

Steps follow the dependencies above. Step 7 may proceed independently of
Steps 8–20. Step 8 follows completed Step 6; Step 9 follows completed Step 8
and supplies its own spreadsheet prerequisite. Step 10 follows completed
Step 9 and owns delivery of the four unblocked Step 7 providers and legacy
XLS support. No later step waits for Step 7's Status. Step 1 closes the
input-validation and numerics bugs that provider values would otherwise
flow through, and moves
the version every later step builds towards. Step 2's ADR fixes the value
types, vintages, licence terms and stack choices that every later layer
encodes, and its `Series` and `Table` are what Step 3's redaction protects
in manifests and exports, what Step 4's providers return and what Step 5
stores. Step 3's secret type and redaction must exist before Step 4's
transport sends its first request, and Step 4's SDK, cassettes and contract
suite are what every provider step uses. Step 5 follows Step 4 because its
policy reads the provider metadata Step 4 defines, and it precedes the
provider steps so none can store what its terms forbid. Step 6 sets the
provider pattern on the hardest sources and adds the live run with its
secrets, which Steps 7–10 then extend. Step 11's catalog maps concepts onto
the providers of Steps 6–10, Step 12's bindings resolve through it, and
Step 13's policy suite is the first consumer of both; Steps 14–17 reuse its
patterns and each other's shared numerics. Step 18 rehearses the tree Steps
1–17 leave on `main`, Step 19 releases it only after the maintainer's GO,
and Step 20 follows Step 19, applying the named SEC deferral when needed.

**Sequencing update (2026-10-16).** Step 7's remaining SEC access rejection is
an external verification blocker. Step 8 uses the SDK, transport, cache and
live workflow already shipped in Steps 4-6; it does not consume the Step 7
providers or spreadsheet readers. Waiting for SEC is therefore unnecessary
for Step 8 implementation, testing or its own merge.

- Steps 7 and 8 each use their own branch, worktree and conversation, both
  cut from `origin/main`. Step 8's prerequisite is completed Step 6, even
  while Step 7 remains unfinished. Carry this roadmap-only sequencing
  amendment onto Step 8's branch at kickoff if it has not reached main;
  do not carry Step 7's incomplete provider implementation onto that branch.
- Either step may merge first once its required pre-merge checks pass; each
  then performs its own post-merge live verification before completion.
  A blocked step stays unfinished; this exception waives no fixture, licence,
  security, CI or deployed-verification requirement.
- The providers share `pyproject.toml`, `uv.lock`, source documentation, the
  live workflow, registry tests and this roadmap. Rebase the second branch
  onto current main before merge, resolve shared-file conflicts explicitly,
  regenerate locks/exports and rerun affected checks. Preserve both steps'
  provider registrations, hosts, notices and status entries. Regenerate the
  provider registry expectations from the providers actually present.
- The original join before Step 9 is superseded by the 2026-10-17 amendment
  below; the remaining reconciliation and acceptance rules still apply.

**Sequencing update (2026-10-17).** The maintainer authorized reviewing and
removing Step 9's unnecessary wait for SEC access. Its five research providers
use the completed SDK, transport, cache, recording contracts and FRED vintage
pattern on main. They do not consume SEC EDGAR or another Step 7 provider.
The concrete missing prerequisite is Step 7's bounded spreadsheet reader and
its dependencies; Step 9 must supply and verify the subset it needs itself.

- Step 9 may start after Step 8 is Complete, even while Step 7 is blocked.
  Use its own branch, worktree and new conversation from current `origin/main`.
  Step 7 remains unfinished with all original acceptance criteria, including
  real SEC recordings and successful post-merge live verification.
- Step 9 may reuse only the necessary shared reader functions and regression
  tests from Step 7's branch, with provenance recorded in its PR body. Do not
  cherry-pick the whole Step 7 implementation or register its providers.
  Recheck parser bounds, XML protections, dependency licences and any existing
  maintainer-approved exceptions; add only dependencies the sources require.
  A new licence decision still requires maintainer review.
- Step 9 may merge independently once its own offline, live, licence, security
  and deployed checks pass. No acceptance check is waived by this amendment.
- Whichever branch merges second rebases onto current main, reconciles shared
  readers, dependencies, locks, exports, registry expectations, workflow hosts
  and roadmap marks, and reruns affected checks. Preserve both implementations.
- The former join before Step 10 is superseded by the external-approval
  amendment below. Step 9's own requirements and completion remain unchanged.

**Further sequencing update (maintainer, 2026-10-17).** The maintainer directed
that the rest of development and the roadmap must not wait for external
responses. The Overview's external-approval exception is authoritative:

- Step 10 may start now, from completed Step 9. It ports only the four
  unblocked providers and necessary shared SDK/records/XML/XLS prerequisites
  from the parked Step 7 branch, documents provenance, rebases against the
  stronger reader already on main, and verifies them under the original
  Step 7 source, licence, recording, security and deployment requirements.
  It also delivers its ten finance providers. Never copy the whole branch
  or its completion marks, and never enable incomplete EDGAR code in main.
- Steps 11–20 keep their normal sequential prerequisites. Their catalog,
  bindings and model data dependencies are satisfied by the four recovered
  providers; none requires EDGAR. No EDGAR-only concept or binding is promised
  while its provider is absent. All other required concepts remain in scope.
- Each active step uses its own conversation, branch and worktree from
  current main. The parked Step 7 branch and draft PR remain preserved.
  A returning Step 7 rebases, retains all merged providers and shared code,
  and verifies the complete five-provider contract before its own merge.
- Readiness, release and QA use the exact release provider set, not a false
  31-provider claim. SEC is an explicit carry-over, not a green test or a
  completed Step 7. Sponsors remains issue #68, independent of engineering.

---

## Step 1 — Core Hardening and the 1.0.0a2 Baseline ✅

**Status:** Complete — PR #106 (2026-10-14)

> **Goal:** Close the three contract bugs Phase 2 handed on before any
> provider value flows into a model input, and set the baseline the phase
> builds towards. Land this roadmap and the refreshed planning kit as the
> branch's first two commits; move `main` to `1.0.0a2.dev1` with
> `CITATION.cff` in step and open an `[Unreleased]` section in
> `CHANGELOG.md`; make the unit markers in `src/pyeconomics/core/units.py`
> and the array aliases in `core/model.py` refuse booleans for every
> numeric kind and numbers for every date (issue #75); make
> `registry.validate()` treat a numeric `Literal` field as numeric, so it
> needs a unit and bounds (#81); and make the root scan in
> `core/numerics.py` and the IRR in `core/cashflows.py` find a root that
> sits exactly on a bracket end (#85), with the versions of the models
> whose outputs change bumped, changelog entries on their cards, golden
> regressions and an entry on the errata page. No dependency, provider or
> data code arrives yet. Parent: `docs/phase02-qa-findings.md` "Pre-ship
> items"; ADR-0003; ADR-0008 decisions 2, 3, 10 and 11.

**Branch:** `feature/phase03-step1-core-hardening`

**Deploys:** nothing beyond merge — the version moves to `1.0.0a2.dev1`,
but this step pushes no tag and publishes nothing. Step 18 rehearses on
TestPyPI; Step 19 publishes the PyPI release.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | GPT-6.1 Sol                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort High        |
| Platform     | Codex                                         |
| Intelligence | Medium                                        |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: three
bounded fixes in shared core — a validator on the unit markers, a
`validate()` rule and the root scan's handling of its bracket's ends — each
specified in its issue, with every catalog model's golden, property and
contract suites as the safety net. Complexity is Medium, so A in coding
suffices, and the operator's posture sends Medium, GPT-adequate work to
Codex on the ChatGPT Pro 5x plan, the lane with slack, $0 marginal. GPT-6.1
Sol is the pick: at Intelligence Medium, where this step runs, it leads
GPT-6 Sol, at the same price, on Terminal-Bench 4.0 (48.0% vs 18.7%), HLE
(49.9% vs 41.0%) and the AA Intelligence Index (47.8 vs 39.8), with SciCode
level (53.2 vs 53.8); GPT-6 Astra is within noise of it on the AA
Intelligence Index (49.6) at five times the price. Codex opens on its
provider default; set GPT-6.1 Sol at Intelligence Medium, the ladder value
for Medium work, because the issues fix the approach and the suites check
every model. The backup is Sonnet 5.5 on Claude Code at Effort High, the
cell `roadmodel backup` prints: at High, Sonnet 5.5 stands level with
GPT-6.1 Sol at Medium (AA Intelligence Index 46.8 vs 47.8). New conversation
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
       feature/phase03-step1-core-hardening`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - The fixes only tighten input validation: a test per
      marker and per array alias proves a boolean and an
      epoch number are refused, and no valid input changes
      its result.
    - Model versions move, model ids never do (ADR-0003); the
      erratum names the affected versions and the fix, and
      quotes no credential, real or fake.
  </security>

  <context>
    pyeconomics. Phase 3. Step 1: core hardening and the
    1.0.0a2 baseline.

    Current state (as of Phase 2; no Phase 3 step has run):

    - main is at c0954f7 (PR #105, after Phase 2 PR #97);
      pyproject.toml and
      CITATION.cff read 1.0.0a1; CHANGELOG.md ends at
      [1.0.0a1] with no [Unreleased] section.
    - This roadmap (docs/roadmap/phase03-roadmap.md) is
      untracked, and planning/ holds roadmodel 0.2.83's kit
      (four files modified by /roadmap-phase 3 on
      2026-10-14). Both carry over to the step branch.
    - Issue #75: pydantic's lax mode lets the numeric unit
      markers accept True and False (rate=True runs as
      100%), DateValue accepts 86400 as 1970-01-02, numeric
      arrays pass into DateArray as epoch seconds, and a
      NumPy bool array becomes (1.0, 0.0). The issue
      suggests a BeforeValidator on the markers, the int
      markers Days and Count included, with no JSON Schema
      change.
    - Issue #81: validate() accepts Literal[365, 366] with no
      unit marker; tests/results/test_schema.py catches the
      missing x-unit today. validate()'s 32 rule slugs are
      core.registry.RULES, and
      tests/registry/test_validate_rules.py holds one toy
      spec per slug and fails if a slug has none.
    - Issue #85: the shared IRR returns None with
      no_root_in_range for the cash flows [-100, 1] (root
      -0.99, the rate's lower bound) and [-1e6, 11e6] (root
      10.0, its upper bound). foundations.time_value,
      corporate.capital_budgeting and
      performance.return_measurement share it, and
      time_value and capital_budgeting must keep exact
      parity. ADR-0008 decision 11 says the scan "sees sign
      changes only"; a value of exactly zero at a bracket
      end is a root the policy never addressed.
    - docs/releases/1.0.0a1.md lists all three as known
      limitations, and docs/phase02-qa-findings.md assigns
      them to Phase 3. docs/errata.md holds #89's erratum,
      the pattern for a new entry.

    Files to read (every file before drafting):
    - This roadmap's Overview (Version and Cross-phase
      verification rules) and Current State.
    - Issues #75, #81 and #85, with their comments
      (`gh issue view <n> --comments`).
    - src/pyeconomics/core/units.py, model.py (the array
      aliases and ARRAY_INPUT), _rules.py, numerics.py and
      cashflows.py.
    - src/pyeconomics/models/foundations/time_value.py,
      corporate/capital_budgeting.py and
      performance/return_measurement.py, with their golden
      files and tests.
    - tests/registry/test_validate_rules.py,
      tests/strategies.py, tests/results/test_schema.py and
      the core unit tests for units and numerics.
    - docs/errata.md, CHANGELOG.md, CITATION.cff,
      docs/releases/1.0.0a1.md and docs/adr/0008 (decisions
      2, 3, 10 and 11).
  </context>

  <goal>
    The roadmap and kit are on main; main reads 1.0.0a2.dev1;
    a boolean is refused by every numeric field and a number
    by every date field, scalars and arrays alike, with every
    JSON Schema unchanged; validate() requires a unit on a
    numeric Literal; the IRR finds endpoint roots in all
    three models that share it; and issues #75, #81 and #85
    close with regression tests, model version bumps and an
    erratum.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Land the roadmap first. After Stage 1, commit planning/
      as /roadmap-step §5 instructs (`chore(planning): refresh
      the roadmodel kit to 0.2.83`), then this file
      (`docs(roadmap): add the Phase 3 roadmap`), each signed
      off and gated, before any other change.
    </requirement>

    <requirement>
      Kickoff, one batched question to the maintainer: (a)
      whether treating an exact zero at a bracket end as a
      root is a clarification of ADR-0008 decision 11
      (recommended: the decision is silent on it, so the
      code documents it and no ADR changes) or needs a
      superseding ADR; (b) the model-version bumps and the
      erratum's text. Record the answers in the PR body.
    </requirement>

    <requirement>
      Issue #75, in core/units.py: one shared
      BeforeValidator on every numeric marker (Rate, Return,
      Money, Years, Days, Periods, Count, Ratio, Probability,
      Volatility, Correlation, IndexLevel) that refuses bool
      and numpy.bool_, and one on DateValue that refuses int,
      float and their NumPy forms while keeping every
      accepted date form; the *Array aliases apply the same
      element rules, NumPy bool arrays and numeric date
      arrays included. The refusal is an ordinary InputError
      from pydantic's validation. No JSON Schema changes: a
      test pins each marker's schema fragment (type, bounds
      and x-unit, nothing added), and the PR body records a
      before-and-after comparison of every registered model's
      schemas with `$id`, which carries the model version, set
      aside. Tests: one per marker and per array alias, for
      Python and NumPy values.
    </requirement>

    <requirement>
      Issue #81, in core/_rules.py: a Literal whose values are
      all int or float (never bool) counts as numeric, so the
      existing field-unit and field-bounds rules apply to it.
      Add the toy spec (Literal[365, 366] with no unit) under
      those slugs in tests/registry/test_validate_rules.py;
      if a new slug proves necessary, add it to RULES with its
      own toy spec. Every registered model still validates.
    </requirement>

    <requirement>
      Issue #85, in core/numerics.py: the scan records a
      root wherever the function is exactly zero — at either
      bracket end or a scan point — besides sign changes;
      find_root and bracket_roots return it; IRR_POLICY's
      choice among several roots is unchanged. Regressions:
      [-100, 1] gives -0.99 and [-1e6, 11e6] gives 10.0 in
      foundations.time_value and corporate.capital_budgeting
      with exact parity, and return_measurement's
      money-weighted return finds an endpoint root; a
      property test builds cash flows whose IRR is a chosen
      rate inside the bounds, the bounds themselves
      included, and recovers it.
    </requirement>

    <requirement>
      Versions, cards and errata: #75 and #81 change no valid
      result, so they bump nothing. Every model whose outputs
      change under #85 (at least the three IRR users) gets
      version + 1 and a ChangelogEntry naming the fix, and
      its golden file gains the endpoint cases (source kind
      identity, marked edge). docs/errata.md gains one entry:
      the affected model ids and versions, what was wrong (a
      null where a root exists), the fixed versions and the
      issue.
    </requirement>

    <requirement>
      Version (Version rule): `uv version 1.0.0a2.dev1
      --no-config`, CITATION.cff's version to match;
      tests/unit/test_version.py passes, and so do
      verify-phase01.sh check 44 and verify-phase02.sh check
      7, which hold the two in step.
    </requirement>

    <requirement>
      CHANGELOG.md: add `## [Unreleased]` above [1.0.0a1]
      with "Fixed" entries for #75, #81 and #85 and a
      "Changed" entry for the version and the model versions.
      The PR body says `Closes #75`, `Closes #81` and `Closes
      #85`.
    </requirement>

    <requirement>
      Cross-phase verification rule: run
      `scripts/verify-phase01.sh --fast` and
      `scripts/verify-phase02.sh --fast` and `--python`
      before the PR; a check this step legitimately breaks is
      narrowed with an addendum line, never deleted.
    </requirement>

    <requirement>
      Stage 3, the phase's first step (Status rule): the same
      commit that marks this step sets this roadmap's
      phase-level Status line and the parent's `### Phase 3`
      Status line to `In progress` (the parent's as `In
      progress — phase03-roadmap.md`), and the parent's
      "Phase Complexity Summary" row for Phase 3 to
      `In progress`.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001); golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 1 acceptance criteria

- This roadmap and the refreshed planning kit reached `main` as the step
  branch's first two commits.
- A boolean (Python or NumPy) in any numeric field and an int or float in
  any date field raise `InputError`, for scalars and arrays alike; a test
  per marker and per array alias proves it, and no JSON Schema changes
  beyond the `$id` of a re-versioned model. Issue #75 is closed.
- `registry.validate()` rejects a numeric `Literal` field without a unit,
  shown by its toy spec, and every registered model still validates. Issue
  #81 is closed.
- The cash flows `[-100, 1]` and `[-1e6, 11e6]` return `-0.99` and `10.0`
  from `foundations.time_value` and `corporate.capital_budgeting` with exact
  parity, `performance.return_measurement` finds an endpoint root, and the
  property test recovers chosen rates including the bounds. Issue #85 is
  closed.
- Each model whose outputs changed has a new version, a changelog entry and
  endpoint golden cases, and `docs/errata.md` records the fix.
- `pyproject.toml` and `CITATION.cff` read `1.0.0a2.dev1`, `CHANGELOG.md`
  has an `[Unreleased]` section, the full suite and the coverage floors pass
  on all twelve CI cells, and `verify-phase01.sh --fast` and
  `verify-phase02.sh --fast` pass in `phase-verify.yml`.
- The phase is marked started: this roadmap's phase-level Status line and
  the parent's `### Phase 3` Status line read `In progress`, and the
  parent's "Phase Complexity Summary" row for Phase 3 reads `In progress`.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and input validation is only tightened:
  no field accepts a value it refused before.

---

## Step 2 — ADR-0011 Data Platform and the Data Model ✅

**Status:** Complete — PR #108 (2026-10-14)

> **Goal:** Fix the data contract every later step encodes, and build its
> value types. Write `docs/adr/0011-data-platform.md` from the eighteen
> recommended defaults in this step's task, and have the maintainer accept
> or amend it in the pull request; add `src/pyeconomics/core/provenance.py`
> (`DataSource`, the record a manifest will carry, with `RealtimePeriod`,
> `LicenceClass` and `LlmUse`, in core because the manifest is core and
> core never imports the data layer) and create `src/pyeconomics/data/`
> with `types.py` (`Series`, `Table` and their metadata,
> `ObservationFrequency`, `SeasonalAdjustment` and the unit record),
> `vintage.py` (the `Vintage` selector), `terms.py` (`CachePolicy` and
> `Terms`) and `errors.py` (the data error taxonomy), each with
> canonical-JSON and pandas round trips and unit, property and doctest
> coverage; add a `data` coverage floor; keep `import pyeconomics` and
> `import pyeconomics.data` working in Pyodide; narrow `verify-phase02.sh
> --post` so its published-install check keeps running `1.0.0a1`'s own
> smoke script; and amend ROADMAP §4 3.3, 3.4, 3.7 and 3.8 to the accepted
> decisions in the same pull request. Steps 3–5 build credentials,
> providers and the cache on these types.
> Parent: ROADMAP §3 and §4 3.1; §5 "Data licensing policy"; ADR-0002,
> ADR-0004, ADR-0005 and ADR-0008.

**Branch:** `feature/phase03-step2-data-adr`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6.1 Sol — Codex · Intelligence XHigh      |
| Platform     | Claude Code                                   |
| Effort       | Extra High                                    |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Planning is PRIMARY — ADR-0011 settles the value types,
vintages, licence enforcement, stack choices, cache, bindings and manifest
that every provider, model and later surface will encode — and knowledge
SECONDARY, because each decision rests on a source's terms, a library's
release facts or ALFRED's real-time semantics. Complexity is High on every
axis: many interacting decisions, trade-offs to judge, scope across the
whole platform, and no precedent in the repository. High requires S in
planning; Opus 5.5 is S in planning and knowledge, ties Fable 5.1 on both
and wins the cost tie-break (AA Intelligence Index 57.6). Claude Code on the
claude.ai Max plan pays for it, $0 marginal while the weekly pool has
headroom; its dated `tight` row expired at Tue 2026-10-13 20:00 EDT, so the
pool reads `headroom` as this roadmap is written. Claude Code opens on Opus
5.5 at its Medium default; Extra High is the recommended raise — High for
the complexity, one rung more for planning with cross-cutting scope — and
not Max, because this roadmap already gives every decision a recommended
default for the maintainer to accept or amend. Thinking stays On. The backup
is GPT-6.1 Sol on Codex under ChatGPT Pro 5x at Intelligence XHigh, the cell
`roadmodel backup` prints: it costs what GPT-6 Sol does and beats it on the
AA Intelligence Index at every effort, and GPT-6 Astra is within noise of it
at five times the price. New conversation per phase-boundary hygiene.

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
       feature/phase03-step2-data-adr`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - The value types hold no secret by construction: no
      field of Series, Table, Terms or DataSource can carry a
      URL, a host, a path or a credential, and a test proves
      the canonical JSON of each has none of those keys.
    - Canonical JSON and pandas are the only serializations;
      nothing pickles, evals or YAML-loads a frame.
    - The ADR and its tests quote no credential, real or
      fake, and name no real person's contact.
  </security>

  <context>
    pyeconomics. Phase 3. Step 2: ADR-0011, the data platform,
    and the data model.

    Current state (as of Phase 3 Step 1):

    - main reads 1.0.0a2.dev1; #75, #81 and #85 are closed;
      this roadmap is tracked. No src/pyeconomics/data/
      exists, and no error class covers data, providers,
      credentials or the network.
    - ADR-0010 is the newest ADR; 0011 is the next free
      number. The format is docs/adr/template.md, and the
      accepted ADRs show the house style: context with
      sourced, dated facts; decision drivers; considered
      options; the decision; consequences; a Confirmation
      table. ADR-0008 (fourteen numbered decisions) is the
      closest precedent.
    - Facts the decisions rest on, read on 2026-10-14 (this
      roadmap's Dependency rule table): httpx's latest
      release is 0.28.1 (2024-12-06) and it requires
      certifi (MPL-2.0); duckdb 1.5.6, arch 8.0.0,
      linearmodels 7.0, cvxpy 1.9.3 and PyYAML 6.0.3 have no
      CPython 3.15 wheel; edgartools 5.62.0 requires
      pyarrow; FRED API v2 takes its key in an Authorization
      header, v1 in the query string; the Federal Reserve
      Board removes the Data Download Program's "Build Your
      Package" option the week of 2026-11-09 and posts XML
      files on each release page (its notice of
      2026-07-16).
    - ROADMAP §4 3.3 plans Parquet indexed by DuckDB with an
      opt-in FRED cache; ADR-0005 rule 4 and ROADMAP §5
      "Data licensing policy" rule 4 say a source whose
      terms forbid storage is never written to disk; ADR-0008
      decision 8 bars pyarrow as a dependency, even through
      an extra.
    - pyeconomics.core.Provider names the distribution that
      registered a model; core's Frequency is ADR-0008
      decision 4's compounding enum; core/canonical.py
      serializes None, bool, int, float, str, date and
      datetime, mappings and sequences.
    - core/manifest.py is schema 1 and types data_sources as
      tuple[object, ...], always empty until Step 12; core's
      __init__.py exports Manifest. scripts/smoke.py runs in
      CI, in release-smoke.yml (from its release tag's
      checkout) and in verify-phase02.sh --post, whose
      published-install check (V14.3) copies the working
      tree's smoke.py and runs it against PyPI's 1.0.0a1.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §3, §4 3.1–3.8 and §5 "Security
      & privacy strategy", "Data licensing policy", "Legal &
      brand guardrails" ("Data terms" and "Required
      notices").
    - docs/adr/README.md, docs/adr/template.md, and ADR-0002,
      ADR-0003, ADR-0004, ADR-0005 and ADR-0008.
    - This roadmap's Overview (the data contract, the source
      plan and every rule) and Current State.
    - src/pyeconomics/core/__init__.py, canonical.py,
      rates.py, compounding.py, units.py, errors.py,
      manifest.py and tables.py.
    - scripts/checks/coverage_floors.py, scripts/smoke.py,
      the pyodide job in .github/workflows/ci.yml,
      .github/workflows/release-smoke.yml,
      scripts/verify-phase02.sh (published_install) and the
      post-merge addendum at the end of
      docs/roadmap/phase01-roadmap.md (the pattern to
      follow).
  </context>

  <goal>
    ADR-0011 is merged as Accepted with the eighteen
    decisions below; pyeconomics.core.provenance holds the
    DataSource record and its vocabulary, and
    src/pyeconomics/data/ the value types, terms, vintages
    and the error taxonomy, all tested and round-tripping
    through canonical JSON (and the frames through pandas);
    the data floor holds; the core still imports in Pyodide;
    verify-phase02.sh --post still proves the published
    1.0.0a1 with that release's own smoke script; and the
    parent roadmap's 3.3, 3.4, 3.7 and 3.8 text matches the
    accepted decisions.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, one batched question to the maintainer: the
      eighteen ADR-0011 decisions below, each to accept or
      amend. Record the answers in the PR body; never fill in
      the ADR's acceptance alone. An amendment that changes a
      later step's task is patched into that step's <task>
      block in this PR (Triage rule: spec rot).
    </requirement>

    <requirement>
      Write docs/adr/0011-data-platform.md from
      docs/adr/template.md, facts sourced and dated, with
      these decisions as its recommended defaults:
      1. Layout. src/pyeconomics/data/ is core, pure Python
         (ADR-0002): types, terms, vintages and errors (this
         step); credentials, config and redaction (Step 3);
         the provider base, registry, transport, modes and
         built-in providers (Step 4 on); the cache (Step 5);
         the catalog (Step 11); bindings (Step 12). core/
         stays I/O-free, models never import
         pyeconomics.data, and core never imports it either:
         the vocabulary a model or a manifest needs lives in
         pyeconomics.core — the provenance record
         (DataSource, RealtimePeriod, LicenceClass, LlmUse;
         this step), the Binding declaration, the Bound
         result and the transform names (Steps 11 and 12) —
         and the data layer re-exports it. The data layer may
         use the network, files, the environment and the
         clock only in its transport, cache, config and
         credential modules.
      2. Value types and errors. A Series is immutable: an
         index of dates, a tuple of float-or-None values and
         SeriesMeta, at most 100,000 observations (ADR-0008's
         array bound). A Table shares one index across named
         columns, each with column metadata, at most 100,000
         rows and 1,000 columns. Both convert to pandas
         (a datetime64[us] index, metadata in attrs) and to
         canonical JSON and back losslessly; Polars and Arrow
         stay caller-owned (ADR-0008 decision 8). Errors:
         DataError (a PyeconomicsError) and its subclasses
         ProviderNotFoundError and SeriesNotFoundError
         (LookupError), CredentialError and LicenceError
         (PermissionError), RateLimitError (RuntimeError),
         TransportError and OfflineError (ConnectionError)
         and ResponseError and ConfigError (ValueError); no
         message carries a credential, a URL with its query
         or a path.
      3. Dates and frequency. ObservationFrequency is its own
         enum — daily, business_daily, weekly (with its anchor
         day), biweekly, monthly, quarterly, semiannual,
         annual, irregular — separate from core's compounding
         Frequency. A period observation is indexed by its
         period's last day, ADR-0008 decision 4's period-end
         aliases; the source's own convention (period start
         for FRED, BLS and BEA) is recorded in metadata, and
         Series.periods() returns pandas Periods.
      4. Units and the decimal boundary. Metadata carries the
         source's unit text as published, an ADR-0008 unit
         kind where one applies, the scale and the currency.
         A provider converts percent to decimals with
         core.rates.percent_to_decimal in its transform step
         (ADR-0008 decision 1); no other code changes a
         rate's scale.
      5. Missing observations. A missing value is None (JSON
         null, pandas NA), never NaN; each provider maps its
         source's markers to None and records the count.
         Nothing fills a gap silently: alignment and bindings
         use explicit, recorded rules (decisions 15 and 16).
      6. Vintages. An observation from a source that keeps
         vintages carries its real-time period
         (RealtimePeriod in core: realtime_start,
         realtime_end), ALFRED's semantics. Vintage is
         latest, as_of(date), first_release or all.
         Historical evaluation defaults to as_of(the
         evaluation date) wherever the source keeps vintages;
         otherwise it uses latest, records revised_data and
         warns.
      7. Licence classes and terms. ADR-0005's five classes
         as LicenceClass (in core); Terms per provider:
         class, terms URL (https), terms-checked date,
         attribution, required notice, llm_use and
         CachePolicy; a series may override class, llm_use
         and caching from the source's own markers (FRED's
         copyright tags, the World Bank's License_Type,
         Eurostat's exceptions; Moody's on FRED is
         pre-approval). A provider without complete terms
         never registers, and a test fails when a
         terms-checked date is more than 13 months old.
      8. llm_use (LlmUse, in core): allowed, forbidden or
         unclear, read from the source's terms; it travels
         with every frame and DataSource record, and Phase
         4's MCP server and AI narrative gate on it.
      9. Provider contract. One DataProvider subclass per
         source, with a ProviderInfo (id, name, homepage,
         terms, authentication, host allowlist, rate limits,
         capabilities, required extra, platforms) and a typed
         fetch pipeline — query model → requests → raw
         responses → Series or Table — plus search, describe
         and vintages where declared. Discovery through the
         pyeconomics.providers entry-point group; ids
         permanent once released. The name DataProvider
         avoids pyeconomics.core.Provider.
      10. HTTP stack. urllib3 2.x (MIT) with truststore (MIT)
          for the operating system's trust store, behind a
          Transport protocol, imported lazily; not httpx (no
          release since 0.28.1 on 2024-12-06; requires
          certifi, MPL-2.0) and not requests (certifi too).
          The transport builds URLs only from a provider's
          allowlisted hosts over HTTPS, never from user input;
          it sets timeouts and a response-size cap, retries
          with exponential backoff and jitter within each
          provider's published limits (honouring
          Retry-After), and sends a User-Agent naming
          pyeconomics and its version, plus the user's
          configured contact where a source requires one.
      11. Clients and extras. sdmx1 (Apache-2.0) for IMF,
          OECD, ECB, BIS and Eurostat behind [sdmx], its
          requests closure bringing certifi under a reviewed
          MPL-2.0 exception; in-house clients for the World
          Bank (wbgapi needs PyYAML, which has no CPython 3.15
          wheel) and SEC EDGAR (edgartools needs pyarrow);
          DBnomics through its REST API (its client is AGPL,
          excluded by ADR-0004); yfinance behind [yfinance],
          off by default; the OS keyring behind [keyring];
          urllib3, truststore, platformdirs, openpyxl,
          defusedxml and xlrd as pure-Python runtime
          dependencies. This extends ADR-0002's extras table
          with sdmx, yfinance and keyring, all of which `all`
          includes.
      12. Credentials. Per provider: explicit argument → the
          provider's environment variable (FRED_API_KEY,
          BLS_API_KEY, BEA_API_KEY, CENSUS_API_KEY,
          OPENFIGI_API_KEY) → a .env file in the user's config
          directory, parsed strictly by pyeconomics and never
          overriding a real environment variable → the OS
          keyring (service pyeconomics, user = provider id).
          A key is a Secret from the moment it is read.
          pyeconomics.toml (user config directory, then the
          working directory, then PYECONOMICS_* variables)
          holds settings only and refuses any key named like a
          secret; the SEC contact address is personal data,
          never logged or recorded.
      13. Redaction. A chained log-record factory scrubs every
          registered secret (and its URL-encoded form) from
          every record of every logger; URLs and headers are
          scrubbed before an exception, warning or log line
          carries them; transport errors are raised outside
          the except block that caught them, so no traceback
          chains the original; Secret's repr, str and format
          show only that a value is set, and it refuses
          pickling and canonical JSON. Canary tests cover
          logs, exceptions and tracebacks, warnings,
          manifests, cache files and exports.
      14. Cache store. SQLite (standard library) in the
          user's cache directory, user-only permissions,
          payloads as canonical JSON, keyed by provider,
          dataset, series, credential-free query and vintage;
          a time-to-live per provider (long for closed past
          vintages); an offline mode; a Python cache API that
          Phase 4's commands wrap. A source whose terms forbid
          storage — FRED and ALFRED among them — has no cache
          path and no opt-in (ADR-0005 rule 4); an in-process
          memo, never shared and gone at exit, is not
          storage. Rejected: Parquet indexed by DuckDB (duckdb
          1.5.6 has no CPython 3.15 wheel; pyarrow is barred by
          ADR-0008 decision 8). Parquet stays the export and
          hosted-snapshot format of Phases 4 and 5.
      15. Catalog. Concept ids are dotted snake_case that
          starts with an economy (a lowercase ISO 3166 code,
          or ea for the euro area) or a dataset family:
          <economy>.<topic>.<measure>[.<transform>]
          (us.inflation.pce_core.yoy) or
          <family>.<set>.<economy>.<frequency>
          (factors.ff5.us.monthly). They are permanent once
          released, each mapping to provider series in
          fallback order — the originator, then a library-only
          aggregator on the user's own key, then premium-only
          (Phase 6) — with declared transforms and an explicit
          alignment rule. Hosted mode resolves only to
          originators; a vintage request prefers a source that
          keeps vintages. Mixed frequencies align by explicit,
          recorded rules, never a silent forward-fill. The
          catalog ships as Python modules.
      16. Bindings and manifests. A Binding (in core:
          field, concept, transform, as_of, window, vintage,
          profile) names one input field's concept, transform,
          as-of rule (the last observation on or before the
          date, one period's value, or a window of N
          observations) and vintage policy, within a named
          profile — one complete set of bindings, such as
          realized data, a forecast source or another
          economy. pyeconomics.bind(model_id, /, *, as_of,
          vintage, mode, profile, concepts, **overrides)
          resolves a profile, concepts= rebinding a field to
          another concept of the same unit kind and
          frequency, and returns a Bound (in core) — values
          plus DataSource records — and
          pyeconomics.run(model_id, bound) runs it. The
          manifest moves to schema 2: data_sources holds
          DataSource records (provider, dataset, series,
          concept, vintage or real-time period, observation
          window, transforms, retrieval time from the fetch,
          licence class, attribution, terms URL, llm_use,
          cache hit, served offline, the fallback chain
          tried) and never a URL, path, host or key;
          result_sha256 keeps its definition; a manifest is
          byte-identical for identical inputs and identical
          data-source records.
      17. Recorded responses: this roadmap's Recording rule,
          as the contract.
      18. Live verification: providers-live.yml runs the
          contract suite live weekly and on dispatch, on main
          only, in the providers-live environment
          (deployment branch main, environment secrets only),
          with harden-runner's egress blocked to the declared
          hosts and the installer's, contents: read for the
          run and issues: write only for the reporting job;
          one issue per failing run under the provider-live
          label, older ones closed; a separate daily
          providers-heartbeat.yml fails, and opens an issue,
          when no successful live run is younger than eight
          days. A source whose terms bar automated collection
          (yfinance) runs live only on the maintainer's
          machine, on demand.
      The Decision outcome has one numbered subsection per
      decision, 1 to 18 in this order; the Confirmation table
      names each decision's check and the Phase 3 step that
      builds it. Add the ADR to docs/adr/README.md's index.
      It reads `Status: Accepted`, with the acceptance date,
      only after the maintainer accepts or amends it in this
      PR.
    </requirement>

    <requirement>
      Implement, each module with the three-line header and
      numpy-style docstrings whose examples run as doctests:
      src/pyeconomics/core/provenance.py (DataSource and its
      canonical-JSON form, RealtimePeriod, LicenceClass,
      LlmUse; exported from pyeconomics.core) and, in
      src/pyeconomics/data/, types.py (Series, Table,
      SeriesMeta, ColumnMeta, TableMeta, ObservationFrequency
      with its pandas aliases, SeasonalAdjustment, the unit
      record), vintage.py (Vintage), terms.py (CachePolicy,
      Terms) and errors.py (decision 2's taxonomy);
      data/__init__.py re-exports the public names, core's
      provenance names included, in __all__. No module here
      opens a socket, reads a file or the environment, or
      reads the clock, and nothing in core imports
      pyeconomics.data.
    </requirement>

    <requirement>
      Tests, sockets disabled, in tests/data/ and (for
      core/provenance.py) tests/unit/core/: canonical JSON
      and pandas round trips for Series and Table (None stays
      None; dates keep their period-end index;
      Series.periods() agrees); bounds (100,000 observations,
      1,000 columns) refuse with InputError; Vintage and
      RealtimePeriod semantics on hand-built ALFRED-style
      observations (as_of picks the value whose real-time
      period covers the date; first_release the earliest);
      Terms validation (https URL, attribution present, a
      13-month freshness helper); DataSource round-trips
      through canonical JSON and has no URL, path, host or
      key field; a test that no module under
      src/pyeconomics/core imports pyeconomics.data; property
      tests for the round trips and the as_of selection.
    </requirement>

    <requirement>
      Coverage and Pyodide: add `data` with a 95% floor to
      scripts/checks/coverage_floors.py (and its test);
      extend scripts/smoke.py to import pyeconomics.data and
      build a Series, and keep the pyodide job green.
    </requirement>

    <requirement>
      Phase 2's verifier, same PR (this roadmap's
      Cross-phase verification rule): once scripts/smoke.py
      imports pyeconomics.data, verify-phase02.sh --post's
      published_install (V14.3) would run it against PyPI's
      1.0.0a1, which has no data layer. Narrow it to the
      invariant it protects — the published alpha installs
      and passes its own smoke script — by running the
      v1.0.0a1 tag's copy (`git show v1.0.0a1:scripts/smoke.py`,
      under MSYS_NO_PATHCONV=1), as release-smoke.yml already
      checks out its tag's scripts; keep the core, extras and
      stable 0.2.6 installs and their assertions unchanged.
      Append to docs/roadmap/phase02-roadmap.md a `##
      Post-merge addendum (<YYYY-MM-DD>) — Phase 3 changes to
      verify-phase02.sh` section after its closing
      paragraph, opening with the rule's sentence as
      phase01-roadmap.md's addendum does, with one line for
      this change; later Phase 3 steps add their lines there.
      Run `verify-phase02.sh --fast` before the PR and record
      a `--post` run's V14.3 result in the PR body.
    </requirement>

    <requirement>
      Parent roadmap, same PR: amend ROADMAP §4 3.3's cache
      bullets to the accepted store, to "FRED and ALFRED are
      never written to disk", and from "`pyeconomics cache`
      commands" to a Python cache API that Phase 4's commands
      wrap; 3.4's clients bullet to the accepted HTTP stack
      and clients; 3.8's criterion "FRED caching stays off
      unless the user opts in" to "FRED and ALFRED are never
      written to disk"; the Fed Board bullet to the Board's
      2026-07-16 notice (the option it removes is "Build Your
      Package"; the Data Download Program itself has no
      announced end date); and add one sentence under 3.7's
      table: its entries ship as the eighteen model ids of
      the Phase 3 roadmap's launch-catalog table, where one
      id carries a family's variants as a method input (the
      output-gap filters, the factor models, the GARCH
      variants, the risk-based allocations).
    </requirement>

    <requirement>
      CHANGELOG [Unreleased]: "Added" entries for ADR-0011
      and the data value types.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001); the ADR follows docs/adr/'s
      convention and carries no filepath line.
    </requirement>
  </requirements>
</task>
```

### Step 2 acceptance criteria

- `docs/adr/0011-data-platform.md` reads `Status: Accepted` with the
  maintainer's acceptance date, carries the eighteen decisions and a
  Confirmation table, and `docs/adr/README.md` lists it as Accepted.
- `src/pyeconomics/core/provenance.py` holds `DataSource`, `RealtimePeriod`,
  `LicenceClass` and `LlmUse`, exported from `pyeconomics.core`;
  `src/pyeconomics/data/` holds `types.py`, `vintage.py`, `terms.py`,
  `errors.py` and its `__init__.py`; no core module imports
  `pyeconomics.data`, which a test proves; mypy strict and ruff are clean;
  the unit, property and doctest suites pass on all twelve CI cells.
- `Series` and `Table` round-trip losslessly through canonical JSON and
  pandas, missing values stay `None`, and the size bounds refuse oversized
  frames.
- `Vintage.as_of`, `first_release` and `latest` select the expected values
  on hand-built real-time data, and `DataSource` has no field that can hold
  a URL, a path, a host or a key.
- The `data` coverage floor (95%) holds, `scripts/smoke.py` imports
  `pyeconomics.data`, and the `pyodide` job is green.
- `verify-phase02.sh --post`'s V14.3 runs the `v1.0.0a1` tag's
  `scripts/smoke.py` against PyPI's `1.0.0a1` and passes, and
  `phase02-roadmap.md` ends with a Phase 3 post-merge addendum naming the
  change.
- ROADMAP §4 3.3, 3.4, 3.7 and 3.8 match the accepted decisions.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and no value type can carry a URL, a
  path, a host or a credential, which a test proves.

---

## Step 3 — Credentials, Configuration and Redaction ✅

**Status:** Complete — PR #111 (2026-10-15)

> **Goal:** Make a key leak impossible before the first request is ever
> sent. Build `src/pyeconomics/data/credentials/` — the `Secret` type, the
> per-provider key chain of ADR-0011 decision 12 (explicit argument → the
> provider's environment variable → the user's config-directory `.env` →
> the OS keyring through a new `[keyring]` extra) and `CredentialError` —;
> `data/config.py`, the layered `pyeconomics.toml` that refuses secrets and
> carries the mode, offline, cache and contact settings, with
> `pyeconomics.data.configure()` for session overrides; and
> `data/redaction.py`, the chained log-record factory, the URL and header
> scrubbers and the raise-outside-the-except discipline of decision 13.
> Add `platformdirs` as a runtime dependency; add a semgrep rule that lets
> only the transport and the credential modules reveal a secret's value;
> write the canary harness `tests/data/leakcheck.py` and canary tests over
> every sink that exists now — log records from every logger, exceptions
> and their formatted tracebacks, warnings, manifests and `Result` exports
> — with hooks Steps 4, 5 and 12 extend to the transport, the cache file
> and bound manifests; and write the "Keys and configuration" guide in the
> documentation preview. Parent: ROADMAP §4 3.2; §5 "Data
> classification", "Threat model" and "Security controls by layer";
> ADR-0011 decisions 12 and 13.

**Branch:** `feature/phase03-step3-credentials`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6.1 Sol — Codex · Intelligence XHigh      |
| Platform     | Claude Code                                   |
| Effort       | Extra High                                    |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: the step
writes the code that holds users' keys, and getting it right takes exact
knowledge of where Python leaks a value — logging's lazy formatting,
urllib3's debug lines, exception chaining, warnings, `repr` and pickling. It
is security-sensitive and cross-cutting, which the operator's ladder rates
High, and proving that a canary reaches none of six sinks is multi-step
verification across many files, which earns Extra High. High requires S in
coding; with knowledge secondary, Opus 5.5 (S in both) outranks Sonnet 5.5
(A in knowledge) and wins the cost tie-break against Fable 5.1 (HLE 61.4%).
Claude Code on the claude.ai Max plan pays for it, $0 marginal while the
weekly pool reads `headroom`. Claude Code opens on Opus 5.5 at its Medium
default; Extra High is the raise this step's proof burden earns, and not
Max, because ADR-0011 has already fixed the design. Thinking stays On. The
backup is GPT-6.1 Sol on Codex under ChatGPT Pro 5x at Intelligence XHigh,
the cell `roadmodel backup` prints: it costs what GPT-6 Sol does and beats
it on the AA Intelligence Index at every effort, and GPT-6 Astra is within
noise of it at five times the price. New conversation per phase-boundary
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
       feature/phase03-step3-credentials`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - This step is the phase's key-handling core, so every
      requirement below is a security requirement; a canary
      that reaches any sink fails the build.
    - No key literal anywhere, real or fake: canaries come
      from secrets.token_hex at run time, and no test prints
      or asserts on a value in a way that would print it.
    - .env parsing never executes, interpolates or expands
      anything, and an error names the line number, never
      its content.
    - Tests isolate configuration: every test runs against a
      temporary config, cache and .env directory, never the
      maintainer's real files or the repository root's
      ignored .env.
    - The [keyring] extra's closure passes the licences hook
      on all three operating systems (cffi's MIT-0 with a
      reviewed exception) and pip-audit.
  </security>

  <context>
    pyeconomics. Phase 3. Step 3: credentials, configuration
    and redaction.

    Current state (as of Phase 3 Step 2):

    - ADR-0011 is Accepted; pyeconomics.core.provenance
      holds DataSource and its vocabulary, and
      src/pyeconomics/data/ the value types, terms, vintages
      and the error taxonomy, CredentialError and ConfigError
      among them. Nothing reads a key, a file or the
      environment yet.
    - 0.2.x read FRED_API_KEY and keyring("fred", "api_key")
      and logged the key at DEBUG (GHSA-j6rp-vwwv-jrr8,
      fixed in 0.2.6). The semgrep rule credential-logging
      (repository-wide) refuses printing or logging a name
      like a key, token, secret, password or credential;
      gitleaks carries a custom fred-api-key rule.
    - urllib3's connection-pool logger writes the request
      path and query string at DEBUG, so a key in a query
      string reaches a log unless every record is scrubbed;
      `raise X from Y` and even `from None` keep the
      original exception in __context__, so a transport must
      raise outside the except block.
    - Known traps (Phase 2 memory): never assert
      `value not in text` on a secret (pytest prints both
      sides) — collect the names of the sinks where it
      appears and assert that list is empty; the gate blocks
      literal fake keys, docs included.
    - pyeconomics.core.manifest, results and tables are the
      export paths that exist now; the cache (Step 5) and
      bound manifests (Step 12) arrive later.

    Files to read (every file before drafting):
    - docs/adr/0011-data-platform.md (decisions 12 and 13)
      and this roadmap's Credential rule.
    - docs/roadmap/ROADMAP.md §4 3.2 and §5 "Data
      classification", "Threat model", "Security controls by
      layer" and "Runbooks".
    - .semgrep/rules/credential-logging.yaml and its tests,
      scripts/checks/semgrep_tests.py and .gitleaks.toml.
    - src/pyeconomics/core/manifest.py, results.py,
      tables.py and _optional.py (import_optional).
    - scripts/checks/licences.py,
      scripts/checks/licence_exceptions.toml and
      tests/checks/test_licences.py.
    - docs/index.md, docs/installation.md and docs/conf.py
      (where the guide goes and how pages are listed).
  </context>

  <goal>
    A key is read only through the chain, held only as a
    Secret, revealed only in the transport and credential
    modules, and scrubbed from every log record, URL, header,
    warning and exception; configuration never holds a
    secret; canary tests prove no key reaches a log, an
    exception or its traceback, a warning, a manifest or an
    export; and the keys guide tells users how to supply,
    store and rotate their keys.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Secret (data/credentials/secret.py): wraps one key for
      one provider; reveal() returns the value; repr, str and
      format return a fixed mask naming the provider; pickling
      (__reduce__, __getstate__) and copying to JSON raise
      TypeError, and core/canonical.py refuses it; equality
      uses hmac.compare_digest. Creating a Secret registers
      its value and URL-encoded form in a process-wide,
      in-memory registry that redaction reads; forget()
      removes them. A value shorter than 8 characters is
      refused (scrubbing a short string would mangle logs).
    </requirement>

    <requirement>
      Key chain (data/credentials/chain.py):
      resolve_key(provider_id, explicit=None) -> Secret walks
      ADR-0011 decision 12's order and logs at DEBUG only
      which kind of source answered (argument, environment,
      dotenv, keyring); has_key(provider_id) -> bool answers
      the same question without creating a Secret, so a
      presence check prints only True or False. The .env
      reader is strict: KEY=VALUE lines, optional quotes, #
      comments, no export, no interpolation, no multiline
      values; it never overrides a variable set in the real
      environment; on POSIX a file readable by group or
      others draws a credentials_file_permissions warning.
      The keyring step uses import_optional("keyring",
      extra="keyring"): no extra means the step is skipped
      with a DEBUG note; a backend error is skipped with a
      warning naming the backend. No source →
      CredentialError naming the provider, its environment
      variable, the guide's URL and `keyring set pyeconomics
      <provider>`, and never a value.
    </requirement>

    <requirement>
      Configuration (data/config.py): read pyeconomics.toml
      from the user config directory
      (platformdirs.user_config_dir("pyeconomics")), then the
      working directory, then PYECONOMICS_* environment
      variables (MODE, OFFLINE, CONFIG_DIR, CACHE_DIR,
      SEC_CONTACT and per-provider time-to-live overrides),
      with tomllib, validated by a frozen pydantic model
      (extra="forbid"). Any key whose name matches the
      credential pattern raises ConfigError naming the key,
      never its value. pyeconomics.data.configure(mode=...,
      offline=...) sets process-wide overrides; tests reset
      them. The SEC contact is personal data: never logged,
      never written to a manifest, a cache or a cassette.
    </requirement>

    <requirement>
      Redaction (data/redaction.py): install() chains
      logging.setLogRecordFactory once, idempotently and
      keeping any factory already installed; each record's
      formatted message is scrubbed of every registered value
      and its URL-encoded form, and its args cleared.
      scrub_url() removes the credential query parameters
      (api_key, registrationkey, UserID, key, token) by name
      and every registered value; scrub_headers() drops
      Authorization, Cookie and any key header. A helper
      gives the transport its pattern: catch, keep only a
      scrubbed message, leave the except block, then raise,
      so __context__ is empty. The chain installs redaction
      the first time it resolves a key.
    </requirement>

    <requirement>
      Semgrep: a new rule secret-reveal refusing `$X.reveal()`
      outside src/pyeconomics/data/credentials/ and
      src/pyeconomics/data/transport/, with `# ruleid:` and
      `# ok:` tests that semgrep-test runs; credential-logging
      stays green and gains a case for logging a revealed
      value.
    </requirement>

    <requirement>
      Canary harness (tests/data/leakcheck.py): canary()
      makes a random 40-character secret registered for a toy
      provider; the harness collects named sinks — every log
      record at DEBUG on the root and the pyeconomics and
      urllib3 loggers (urllib3's line format simulated
      without the network), exceptions with
      traceback.format_exception (context and cause
      included), warnings, a manifest's canonical JSON, and
      Result.to_dict, to_json, to_pandas and to_parquet
      bytes — and assert_clean() fails with the list of sink
      names where the canary appears, never the canary.
      Steps 4, 5 and 12 add their sinks to it.
    </requirement>

    <requirement>
      Tests (tests/data/credentials/): the chain at every
      level and in every combination; the environment beats
      .env; keyring with and without the extra (a fake
      backend); CredentialError's message; .env parsing edge
      cases; config refusal of secret-like keys; Secret's
      refusals; the record factory with and without a
      prior factory; scrub_url and scrub_headers; an
      exception raised through the helper has no context; and
      the canary suite over every sink above.
    </requirement>

    <requirement>
      Dependencies (Dependency rule): `uv add --no-config
      "platformdirs>=4.13"` (lower the floor if Pyodide
      bundles an older one) and an optional `keyring` extra
      (`keyring>=25.7`) that `all` includes and the test group
      joins; uv lock and uv export with --no-config. Run the
      licences hook on each operating system's closure; add a
      reviewed exception for cffi's MIT-0 (Linux, through
      SecretStorage and cryptography) and anything else it
      reports, update tests/checks/test_licences.py's pin, and
      exempt each by purl in security.yml with a comment.
    </requirement>

    <requirement>
      Documentation: docs/data/keys.md, "Keys and
      configuration", linked from the index: where to register
      each key (FRED, BLS, BEA, Census, OpenFIGI), the lookup
      order, the .env location on each operating system, the
      keyring command, the pyeconomics.toml settings, what is
      never logged or stored, and how to rotate a leaked key
      (ROADMAP §5 "Runbooks"). A key is named by its
      environment variable, never shown, not even as a fake.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased]: "Added" entries for the key
      chain, configuration, redaction and the [keyring]
      extra.
    </requirement>

    <requirement>
      Filepath comment: every new Python, YAML and TOML file
      gets its repo-relative path as the first line, Python
      files the full three-line header; Markdown pages follow
      docs/'s convention.
    </requirement>
  </requirements>
</task>
```

### Step 3 acceptance criteria

- `resolve_key` returns the first key in ADR-0011 decision 12's order, a
  real environment variable beats the `.env` file, the keyring is optional
  and its absence or failure is reported without a value, and
  `CredentialError` names the provider, the variable and the guide.
- `pyeconomics.toml` refuses any secret-like key, and every test runs
  against isolated configuration directories.
- The canary suite proves no key reaches a log record from any logger
  (urllib3's debug format included), an exception or its formatted
  traceback, a warning, a manifest or a `Result` export, and reports only
  sink names on failure.
- `Secret`'s `repr`, `str` and formatting show only a mask naming the
  provider, and it refuses pickling and canonical JSON; the
  `secret-reveal` rule and its tests pass `semgrep-test`;
  `credential-logging` stays green.
- `platformdirs` and the `[keyring]` extra are locked to PyPI only,
  audited, and pass the `licences` hook on all three operating systems
  with reviewed exceptions; the `pyodide` job stays green.
- `docs/data/keys.md` builds with warnings as errors and shows no key.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and no key, real or fake, appears in the
  code, tests, docs or logs of this step.

---

## Step 4 — Provider SDK, Transport and Contract Suite ✅

**Status:** Complete — PR #115 (2026-10-15)

> **Goal:** Build the contract every provider implements and the harness
> that proves it, before any real provider exists. Add
> `src/pyeconomics/data/providers/base.py` (`DataProvider`, `ProviderInfo`,
> the typed fetch pipeline, `search`, `describe` and `vintages`, declared
> capabilities); `data/registry.py` (discovery through the
> `pyeconomics.providers` entry-point group, and the facade
> `pyeconomics.data.registry` with `ids()`, `get()`, `installed()` and
> `validate()`, one rule per contract requirement); `data/transport/` (the
> `Transport` protocol, `HttpTransport` on urllib3 and truststore — host
> allowlists, HTTPS only, timeouts, size caps, retries, per-provider rate
> limits and scrubbed errors — and `ReplayTransport` for tests); `data/modes.py`
> (library and hosted modes, the hosted refusal at fetch); the cassette
> format and `scripts/record_cassettes.py`; the shared contract suite
> `tests/providers/provider_contract.py` with the `live` marker; two toy providers;
> the generated per-provider documentation pages and the "Writing a
> provider" guide; and the Bloomberg contract spike — a test-only provider
> over a mocked Desktop API session proving a session-based, non-HTTP
> source fits the contract unchanged. Parent: ROADMAP §4 3.1; ADR-0011
> decisions 7–11 and 17.

**Branch:** `feature/phase03-step4-provider-sdk`

**Deploys:** nothing beyond merge — the Read the Docs `main` preview
rebuilds with the generated provider pages, as it does on every merge;
Step 11 verifies the data documentation live.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Sonnet 5.5                             |
| Backup       | GPT-6.1 Sol — Codex · Intelligence XHigh      |
| Platform     | Claude Code                                   |
| Effort       | Extra High                                    |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and planning SECONDARY: the step
designs the API that 31 free providers, Phase 6's vendors and Bloomberg, and
third-party packages will implement, and the transport every request in the
project passes through. Complexity is High — a novel contract across many
files, with security properties (host allowlists, scrubbing, hosted refusal)
that must hold for every future provider — and designing an API across many
files is the ladder's Extra High condition. High requires S in coding;
Sonnet 5.5, Opus 5.5, Fable 5.1 and GPT-6 Astra are S in both coding and
planning, and Sonnet 5.5 wins the coverage tie-break, S or A in all seven
categories (AA Intelligence Index 56.0). Claude Code on the claude.ai Max
plan pays for it, $0 marginal while the weekly pool reads `headroom`. Claude
Code opens on Opus 5.5 at its Medium default; set Sonnet 5.5 (`/model
sonnet`) at Extra High, a raise over its Medium default, and not Max,
because ADR-0011 fixes the contract's shape. Thinking stays On. The backup
is GPT-6.1 Sol on Codex under ChatGPT Pro 5x at Intelligence XHigh, the cell
`roadmodel backup` prints: it costs what GPT-6 Sol does and beats it on the
AA Intelligence Index at every effort, and GPT-6 Astra is within noise of it
at five times the price. New conversation per phase-boundary hygiene.

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
       feature/phase03-step4-provider-sdk`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - The transport is the only code that opens a socket,
      reveals a Secret (the secret-reveal rule) or builds a
      request URL. It refuses any scheme but https and any
      host outside the provider's allowlist, on redirects
      too, so no input can point it elsewhere (server-side
      request forgery).
    - Responses are size-capped and parsed without executing
      data: JSON with the standard library, XML through
      defusedxml or lxml with entity resolution and network
      access off; never pickle, eval or yaml.load.
    - Cassettes pass the scrubbing scan; the recorder never
      runs inside a test and prints no key; recording uses
      the maintainer's keys only through the chain.
    - Hosted mode refuses a non-hosted-safe source at fetch,
      whatever called it.
    - urllib3 and truststore pass pip-audit and the licences
      hook.
  </security>

  <context>
    pyeconomics. Phase 3. Step 4: provider SDK, transport and
    contract suite.

    Current state (as of Phase 3 Step 3):

    - src/pyeconomics/data/ holds the value types, terms,
      vintages, DataSource and errors (Step 2), and the
      Secret, key chain, configuration and redaction (Step
      3), with a canary harness in tests/data/leakcheck.py.
      No provider, transport or network code exists; tests
      run with sockets disabled, and nothing enables them.
    - core/registry.py is the pattern for discovery: entry
      points, a cached installed() registry, validate()
      reporting `<id>: [<rule>] <detail>` lines, and a
      released-id ledger (core/_released.py) that validate()
      enforces. pyeconomics.core.Provider is the distribution
      record, not a data provider.
    - tests/contract.py is the pattern for a fuzzed,
      per-entry contract suite.
    - ROADMAP §4 6.2 asks Phase 6 for a BloombergTransport
      protocol so a fake can stand in for the Desktop API
      session; nothing may import blpapi.
    - docs/_ext/model_pages.py generates one page per model
      at build time, offline; the build blocks the network.

    Files to read (every file before drafting):
    - docs/adr/0011-data-platform.md (decisions 7–11, 17 and
      18) and this roadmap's Licence, Recording and
      Credential rules and source plan.
    - src/pyeconomics/data/ (all of it) and
      tests/data/leakcheck.py.
    - src/pyeconomics/core/registry.py, _rules.py,
      _released.py and scripts/release_ledger.py.
    - tests/contract.py and tests/strategies.py.
    - docs/_ext/model_pages.py, docs/conf.py and
      .gitleaks.toml (the patterns the cassette scan reuses).
    - pyproject.toml ([tool.pytest.ini_options] and the
      entry-point tables).
  </context>

  <goal>
    A provider is a DataProvider subclass with validated
    ProviderInfo, registered through pyeconomics.providers;
    every request goes through a transport that enforces
    hosts, HTTPS, timeouts, size caps, retries and rate
    limits and scrubs everything it reports; recorded
    responses replay offline; one contract suite holds every
    provider to the contract offline and, under `-m live`,
    against the real API; hosted mode refuses what it must;
    and the Bloomberg spike shows a session-based source fits
    without a contract change.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      ProviderInfo and the base class
      (data/providers/base.py): id, name, homepage, Terms,
      authentication (none; a key with its environment
      variable, sent as a query parameter, a body field or a
      header; or a required contact), hosts (exact names,
      https only), rate limits (requests per second, minute
      or day), capabilities (fetch, search, describe,
      vintages, bulk), the extra it needs (a string literal),
      platforms, and whether its terms allow automated
      collection (the scheduled live run skips a source whose
      terms bar it). The fetch pipeline: a frozen pydantic
      Query (bounded: series ids, at most 100,000
      observations, dates inside the data layer's
      DATA_DATE_BOUNDS, 1700-01-01 to 2200-12-31, ADR-0011
      decision 3) →
      build_requests(query) (method, path on an allowlisted
      host, parameters; credentials are attached by the
      transport from the authentication spec, never by
      provider code) → parse(responses, query) → Series or
      Table with full metadata; search, describe and
      vintages where declared. Source error codes map to the
      taxonomy: 401 and 403 → CredentialError naming the
      provider, 404 → SeriesNotFoundError, 429 → retry, then
      RateLimitError, 5xx → retry, then TransportError, a
      malformed body → ResponseError.
    </requirement>

    <requirement>
      Registry (data/registry.py, imported as
      pyeconomics.data.registry, so it never shadows
      pyeconomics.registry, the model registry): discovery
      through the pyeconomics.providers group (an entry point
      names a module whose __all__ lists DataProvider
      subclasses); installed() cached like the model
      registry; ids(); get(id); and validate() with one slug
      per rule (provider-id, terms, attribution, notice,
      llm-use, cache-policy, hosts, rate-limit, capabilities,
      auth, extra, released) reporting `<id>: [<rule>]
      <detail>`. The released ledger, data/_released.py,
      gets its providers section here, empty until Step 19,
      which validate() enforces as core does for models
      (Step 11 adds its concepts section). The 13-month terms
      freshness is a test (tests/providers/test_provider_terms.py),
      never a validate() rule, so validate() reads no clock.
      Add the empty `[project.entry-points."pyeconomics.providers"]`
      table; built-in providers register from Step 6.
    </requirement>

    <requirement>
      Transport (data/transport/): a Transport protocol;
      HttpTransport on one urllib3 PoolManager per process
      with a truststore SSLContext on native platforms,
      imported lazily; connect and read timeouts; a
      per-provider body cap (default 50 MiB); retries with
      exponential backoff and full jitter on connection
      errors, 429 and 5xx, honouring Retry-After up to a cap,
      at most five attempts; a thread-safe sliding-window
      limiter per provider that never lets more than a
      declared limit into any window (a token bucket that
      starts full lets through twice that: the bucket, then
      its refill); redirects followed
      only to https on the same allowlist; a User-Agent of
      `pyeconomics/<version>
      (+https://github.com/pyeconomics-dev/pyeconomics)` plus
      the configured contact where the provider requires one.
      It attaches credentials from the chain, reveals them
      only here, and reports every failure through Step 3's
      scrubbed, context-free raise. ReplayTransport serves
      cassettes by a key of method, scrubbed URL, sorted
      parameters and, for a request with a body (BLS and
      OpenFIGI send POST requests), the SHA-256 of its
      scrubbed canonical body; a request with no cassette
      fails naming the key.
    </requirement>

    <requirement>
      Modes (data/modes.py): Mode.LIBRARY by default and
      Mode.HOSTED from configure(mode="hosted") or
      PYECONOMICS_MODE=hosted; in hosted mode every fetch of a
      source (or series) not classed hosted-safe or
      user-supplied raises LicenceError naming the class and
      the terms URL, before any request. Step 11's resolver
      checks the same rule earlier.
    </requirement>

    <requirement>
      Cassettes and the recorder (Recording rule): the format
      is canonical JSON — provider, recorded_on, synthetic,
      and requests (method, scrubbed URL, parameters, the
      scrubbed request body where one is sent, then the
      response's status, the headers the client reads and its
      body). scripts/record_cassettes.py <provider>
      [<case>...] records live through the real transport (run
      it with `uv run --no-config`; it is a script, never a
      test), scrubs every registered secret, credential
      parameter, header and cookie and the SEC contact, trims
      to 24 observations per series and 32 KiB per file,
      replaces every observed value through the provider's
      synthesize() hook when the source is not hosted-safe or
      forbids storage (marking synthetic: true), and writes LF
      bytes under tests/providers/cassettes/<provider>/.
    </requirement>

    <requirement>
      Contract suite (tests/providers/provider_contract.py),
      parametrized over every registered provider and the toy
      providers: ProviderInfo validates; every declared
      capability has a cassette that replays into a valid
      Series or Table with units, frequency, seasonal
      adjustment, licence class, attribution, retrieval time
      (from recorded_on, so offline runs are deterministic)
      and real-time periods where the source keeps vintages;
      rate units are decimals; missing markers become None;
      error cassettes map to the taxonomy; the transport
      refuses a foreign host and http://; the rate limiter
      holds on a fake clock; hosted mode refuses every class
      but hosted-safe and user-supplied; and every cassette
      passes the scan (gitleaks' rules, the project's key
      patterns, credential parameters, synthetic: true where
      the Recording rule requires it, the size caps). Register
      a `live` marker, deselected by default (`-m "not live"`
      added to addopts, keeping --disable-socket); `uv run
      pytest -m live --force-enable-socket tests/providers`
      runs the same suite against the real APIs. The canary
      harness gains the transport as a sink: a request with a
      canary key leaves no trace in any sink.
    </requirement>

    <requirement>
      Notice tests (ADR-0005's Confirmation: "a test per
      provider checks the exact wording"):
      tests/providers/test_notices.py pins, per registered
      provider, the exact attribution and required-notice
      text and the terms URL, each quoted from the terms page
      read on its terms-checked date, so a change to a
      notice is a reviewed diff. Every provider step adds its
      providers' rows; the suite fails for a registered
      provider without one.
    </requirement>

    <requirement>
      Toy providers (tests only, never shipped): toy_json, a
      hosted-safe, keyed JSON source, and toy_vintage, a
      library-only source that keeps vintages and forbids
      storage, each with cassettes, so every rule above is
      exercised before Step 6.
    </requirement>

    <requirement>
      Bloomberg spike (tests/providers/test_bloomberg_spike.py
      and the guide): a SessionTransport protocol (open a
      service, send a request, iterate its events) with a
      fake Desktop API session, and a premium-local,
      Windows-only, local-only provider with a hit budget
      over it, built on DataProvider with no change to the
      contract; nothing imports blpapi. If the spike needs a
      contract change, make the smallest one now and record
      it (Contract-change rule).
    </requirement>

    <requirement>
      Documentation: docs/_ext/provider_pages.py generates
      reference/providers/<id>.md from each ProviderInfo at
      build time, offline — class, terms link and checked
      date, attribution, required notice, llm_use, key
      setup, capabilities, rate limits and extra — and an
      index page; docs/data/writing-a-provider.md documents
      the contract, the entry-point group, cassettes, the
      contract suite and session-based sources (the spike's
      findings, which Phase 6 reuses).
    </requirement>

    <requirement>
      Dependencies (Dependency rule): `uv add --no-config`
      urllib3 (>=2.6.3: Pyodide 314.0.7 bundles 2.6.3, the
      first release with the streaming decompression-bomb
      fixes) and truststore (>=0.10, with the marker
      `sys_platform != "emscripten"`: Pyodide's index has no
      truststore and the browser does TLS), pure Python,
      floors no higher than Pyodide bundles; lock and export
      with --no-config; licences and pip-audit pass. The
      pyodide job stays green: importing pyeconomics.data
      imports neither.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added"; filepath comment on
      every new file (three-line header for Python; `# <path>`
      for YAML and TOML; cassettes are JSON and carry none).
    </requirement>
  </requirements>
</task>
```

### Step 4 acceptance criteria

- `DataProvider`, `ProviderInfo`, the fetch pipeline and the provider
  registry exist; `pyeconomics.data.registry.validate()` reports each
  rule's toy violation under its slug and passes on both toy providers;
  the released-provider ledger exists and is enforced.
- `HttpTransport` refuses `http://` and every host outside a provider's
  allowlist (redirects included), caps bodies, retries and rate-limits as
  declared on a fake clock, and raises scrubbed errors with no exception
  context; `ReplayTransport` replays cassettes offline, keying a request
  with a body by its scrubbed canonical body's hash.
- The contract suite passes offline for both toy providers, and every
  cassette passes the scan; `tests/providers/test_notices.py` pins each
  toy provider's exact attribution, notice and terms URL and fails for a
  provider without a row; `-m live` is registered and deselected by
  default, with `--disable-socket` still in `addopts`.
- Hosted mode refuses every source not classed `hosted-safe` or
  `user-supplied` before any request (tested per class).
- The Bloomberg spike's provider fits `DataProvider` with no contract
  change, or the change it needed is recorded; nothing imports `blpapi`.
- The generated provider pages and the "Writing a provider" guide build
  with warnings as errors; the `data` coverage floor holds; the `pyodide`
  job is green.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the transport is the only code that
  reveals a key or opens a socket, which the `secret-reveal` rule and the
  canary suite prove.

---

## Step 5 — Cache and Offline Mode ✅

**Status:** Complete — PR #117 (2026-10-15)

> **Goal:** Store what each source's terms allow, and nothing else. Build
> `src/pyeconomics/data/cache/`: a SQLite store (standard library) at
> `platformdirs.user_cache_dir("pyeconomics")` or the configured
> directory, created with user-only permissions on the first write and
> never at import; entries keyed by provider, dataset, series, the
> canonical query without credentials, and vintage, each holding a
> canonical-JSON payload, its retrieval time, its licence class and its
> expiry; a time-to-live per provider from `ProviderInfo` (long for closed
> past vintages, short for `latest`) with configuration overrides; the
> licence gate of ADR-0011 decision 14 — no cache path at all for a
> provider or series whose terms forbid storage, and a test proving not
> even the database file is created; offline mode
> (`configure(offline=True)` or `PYECONOMICS_OFFLINE=1`), which serves only
> cached entries, carries each entry's retrieval time into its `DataSource`
> record with a `served_offline` warning code, and raises `OfflineError` on
> a miss; corruption and schema-version handling (a bad entry is a miss and
> a warning, never a crash, never trusted); and the Python cache API
> `pyeconomics.data.cache` (`info`, `entries`, `clear`, `path`) that Phase
> 4's `pyeconomics cache` commands wrap. The canary suite gains the cache
> file as a sink. Parent: ROADMAP §4 3.3; §5 "Data licensing policy" rule
> 4; ADR-0005 rule 4; ADR-0011 decision 14.

**Branch:** `feature/phase03-step5-cache`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Sonnet 5.5                             |
| Backup       | GPT-6.1 Sol — Codex · Intelligence High       |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and planning SECONDARY: the store's
keys, expiry, offline semantics and licence gate interact, and they must
behave identically on three operating systems with concurrent processes and
a database a user can corrupt. Complexity is High for the number of
interacting concerns and the security properties (no storage where the terms
forbid it, user-only permissions, no deserialization of untrusted bytes),
but ADR-0011 fixed the design, so it is not the Extra High case. High
requires S in coding; Sonnet 5.5 ties Opus 5.5, Fable 5.1 and GPT-6 Astra at
S in coding and planning and wins the coverage tie-break (AA Intelligence
Index 56.0). Claude Code on the claude.ai Max plan pays for it, $0 marginal
while the weekly pool reads `headroom`. Set Sonnet 5.5 at High, a raise over
its Medium default for the step's cross-platform and security edges.
Thinking stays On. The backup is GPT-6.1 Sol on Codex under ChatGPT Pro 5x
at Intelligence High, the cell `roadmodel backup` prints: it costs what
GPT-6 Sol does and beats it on the AA Intelligence Index at every effort,
and GPT-6 Astra is within noise of it at five times the price. New
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
       feature/phase03-step5-cache`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - No pickle: payloads are canonical JSON, validated back
      into Series and Table on read; a tampered or corrupt
      entry is discarded with a warning and never trusted.
    - The database file is created with user-only
      permissions (0600 on POSIX; under the user profile on
      Windows), never at import and never inside the
      repository.
    - Every SQL statement is parameterized; none is built by
      string formatting (bandit B608 stays clean).
    - A provider whose terms forbid storage has no code path
      to the store: a test proves the database file is not
      created and no row is written, and the canary suite
      proves no key reaches the file.
  </security>

  <context>
    pyeconomics. Phase 3. Step 5: cache and offline mode.

    Current state (as of Phase 3 Step 4):

    - Providers are DataProvider subclasses with Terms
      (licence class, CachePolicy) in their ProviderInfo;
      the transport, ReplayTransport, modes, cassettes and
      the contract suite exist; two toy providers exercise
      them (toy_json, hosted-safe; toy_vintage, library-only,
      vintage-keeping, no storage). No provider writes
      anything to disk.
    - Configuration (Step 3) exposes the cache directory,
      the offline switch and per-provider time-to-live
      overrides; tests isolate the directories.
    - 0.2.x's cache was a pickle file in the repository's
      cache/, created at import, holding FRED content its
      terms forbid storing; `.gitignore` still ignores
      cache/. ADR-0005's Confirmation table assigns this
      step's test: "a provider whose class or terms forbid
      storage has no cache path, and a test proves nothing is
      written".
    - sqlite3 is in the standard library but is a separate
      package in Pyodide, so the cache imports it lazily.

    Files to read (every file before drafting):
    - docs/adr/0011-data-platform.md (decisions 5, 6, 14 and
      16) and docs/adr/0005-data-licence-model.md (rule 4 and
      the Confirmation table).
    - src/pyeconomics/data/ (terms, sources, config,
      providers/base.py, registry.py, modes.py, transport/)
      and tests/data/leakcheck.py.
    - src/pyeconomics/core/canonical.py.
    - The toy providers and tests/providers/provider_contract.py.
  </context>

  <goal>
    Fetches from storable sources are cached and reused within
    their time-to-live, closed past vintages for long;
    no-storage sources are never written; offline mode serves
    only the cache and says so in every DataSource record; a
    corrupt or foreign entry is a miss; and the cache API
    lists, inspects and clears entries.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Store (data/cache/store.py): one SQLite database file in
      the configured cache directory, opened lazily (sqlite3
      imported inside the opener) in WAL mode with a busy
      timeout; created on the first write with user-only
      permissions; a schema-version table; an entries table
      keyed by provider, dataset, series, the canonical-JSON
      query without credentials, and the vintage key, with
      retrieved_at (UTC), expires_at, licence class, payload
      (canonical JSON) and payload SHA-256; parameterized SQL
      only. A size cap (default 1 GiB) evicts the least
      recently used entries. Where sqlite3 is unavailable
      (Pyodide without its package), caching is off with a
      DEBUG note.
    </requirement>

    <requirement>
      Policy (data/cache/policy.py): the transport-side read
      path asks the policy first. CachePolicy.FORBIDDEN (the
      provider's or a series' terms forbid storage) means no
      read, no write, no file; otherwise the time-to-live is
      the provider's declared value or its configured
      override, and a vintage whose real-time period is
      closed lives until the size cap evicts it. A cached
      entry's DataSource record carries cache_hit: true and
      its original retrieved_at. An in-process memo for
      no-storage sources, within one bind or fetch call and
      never beyond the process, is allowed and never touches
      the store.
    </requirement>

    <requirement>
      Offline mode: configure(offline=True) or
      PYECONOMICS_OFFLINE=1 serves cached entries only,
      whatever their expiry, adds the served_offline warning
      code to the DataSource record, and raises OfflineError
      on a miss, naming the provider and series and, for a
      no-storage source, why it can never be served offline.
    </requirement>

    <requirement>
      Integrity: on read, the payload's SHA-256 must match and
      the payload must validate back into a Series or Table;
      otherwise the entry is deleted, a cache_entry_discarded
      warning recorded, and the fetch proceeds as a miss. A
      database from a newer schema version is not touched; it
      is reported once and caching is off for the process.
    </requirement>

    <requirement>
      API (pyeconomics.data.cache): info() (path, size, entry
      count, schema version), entries(provider=None) (keys,
      retrieval and expiry times, sizes — no payloads),
      clear(provider=None) and path(). Phase 4 wraps these as
      `pyeconomics cache ls|clear`; this step adds no CLI.
    </requirement>

    <requirement>
      Tests (tests/data/cache/), sockets disabled, with the
      toy providers through ReplayTransport and a fake clock:
      a hit within the time-to-live, a miss after it; closed
      vintages kept; the no-storage toy provider never creates
      the database file or a row (ADR-0005's Confirmation);
      offline hits, misses and the warning code; a corrupt
      payload, a hash mismatch and a newer schema version;
      two connections writing at once; permissions on POSIX;
      the size cap's eviction; clear by provider; and the
      canary suite with the database file as a sink.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added"; filepath comment and
      three-line header on every new Python file.
    </requirement>
  </requirements>
</task>
```

### Step 5 acceptance criteria

- A storable fetch is served from the cache within its time-to-live and
  refetched after it, and a closed past vintage stays cached until
  evicted, all shown on a fake clock.
- A provider or series whose terms forbid storage never creates the
  database file or a row — ADR-0005's Confirmation test — and offline mode
  explains why it cannot serve one.
- Offline mode serves only cached entries, marks each `DataSource` record
  with `served_offline` and its original retrieval time, and raises
  `OfflineError` on a miss.
- A corrupt entry, a hash mismatch and a newer schema version are handled
  without a crash or a trusted payload; two writers do not corrupt the
  store; POSIX permissions are `0600`.
- `pyeconomics.data.cache.info`, `entries`, `clear` and `path` work and
  expose no payload; the `data` coverage floor holds; the `pyodide` job is
  green.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the cache stores no key (canary),
  no `pickle` payload and nothing a source's terms forbid.

---

## Step 6 — Providers: FRED and ALFRED, BLS, BEA, Census ✅

**Status:** Complete — PR #118 (2026-10-16)

> **Goal:** Register the four keyed US providers and the automation that
> watches every provider. Add `src/pyeconomics/data/providers/fred.py`
> (FRED v1 series metadata, observations and search with the key in the
> query string; ALFRED vintages through `realtime_start`, `realtime_end`
> and `vintage_dates`, with `vintages()` from the series' vintage dates;
> FRED v2's bulk release observations with the key in the `Authorization`
> header; series-level copyright gates from FRED's tags, Moody's counted
> as pre-approval; FRED's required notice; no cache path; `llm_use` from
> the terms), `bls.py` (API v2 with the registration key in the request
> body, or keyless API v1 at its lower limits when no key is configured;
> per-query and daily limits, preliminary-value footnotes and BLS's
> notice with the access date), `bea.py` (NIPA, Regional and
> International datasets on the UserID, BEA's rate limits and required
> notice) and `census.py` (the key on every query, Census's required
> notice); their cassettes (FRED's synthetic), contract and
> provider-specific tests; the ALFRED first-release proof against a cited
> later revision; `.github/workflows/providers-live.yml` (the weekly live
> run, its failure report and a dispatch input for synthetic failures) and
> `providers-heartbeat.yml` (the daily staleness check); the
> `providers-live` environment, its four secrets and the `provider-live`
> label; and the `pyeconomics.providers` entry points. Parent: ROADMAP §4
> 3.4; §5 "Operations & observability strategy"; ADR-0011 decisions 6, 7,
> 12 and 18.

**Branch:** `feature/phase03-step6-providers-keyed`

**Deploys:** GitHub Actions — `providers-live.yml` (weekly, and on
dispatch) and `providers-heartbeat.yml` (daily) on `main`, in the
`providers-live` environment whose secrets the maintainer sets at kickoff;
a `workflow_dispatch` run on `main` after merge is the authenticated
round-trip that proves them.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Opus 5.5                               |
| Backup       | GPT-6.1 Sol — Codex · Intelligence XHigh      |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: ALFRED's
real-time periods and output types, FRED's copyright tags and v2 bulk
endpoint, BLS's query limits and BEA's dataset shapes must be implemented
exactly as each source documents them, and the step also wires the project's
first secrets into a scheduled workflow. Complexity is High — the hardest
sources, vintage semantics, licence gates and a security-sensitive workflow
— but the SDK fixes the pattern and the live run checks the semantics, so it
is not the Extra High case. High requires S in coding; with knowledge
secondary, Opus 5.5 (S in both) outranks Sonnet 5.5 (A in knowledge) and
wins the cost tie-break against Fable 5.1 (SciCode 66.9). Claude Code on the
claude.ai Max plan pays for it, $0 marginal while the weekly pool reads
`headroom`. Claude Code opens on Opus 5.5 at its Medium default; High is the
raise for exact source semantics and a secrets-bearing workflow. Thinking
stays On. The backup is GPT-6.1 Sol on Codex under ChatGPT Pro 5x at
Intelligence XHigh, the cell `roadmodel backup` prints: it costs what GPT-6
Sol does and beats it on the AA Intelligence Index at every effort, and
GPT-6 Astra is within noise of it at five times the price. New conversation
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
       feature/phase03-step6-providers-keyed`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - The four keys exist only on the maintainer's machine
      and as environment secrets of providers-live; never as
      repository secrets (Phase 1's V10.5). The maintainer
      sets them with `gh secret set <NAME> --env
      providers-live`, which prompts for the value; no value
      transits chat, a PR or a log, and none is listed or
      echoed.
    - providers-live.yml runs only on schedule and
      workflow_dispatch from main, never on pull_request or
      pull_request_target; the environment's deployment
      branch policy is main only. Top-level permissions: {};
      the live job holds contents: read; only the report job
      holds issues: write; the secrets reach only the pytest
      step's environment; harden-runner blocks egress except
      the providers' declared hosts and the installer's;
      actions are SHA-pinned; zizmor is clean.
    - FRED's cassettes are synthetic and FRED is never
      written to disk; the FRED key travels in the query
      string (v1) or the Authorization header (v2) and is
      scrubbed from both everywhere.
    - BLS's key travels in the POST body and is scrubbed from
      cassettes and errors like any other.
  </security>

  <context>
    pyeconomics. Phase 3. Step 6: providers — FRED and
    ALFRED, BLS, BEA and Census.

    Current state (as of Phase 3 Step 5):

    - The provider SDK, transport, modes, cassettes,
      recorder, contract suite (offline and `-m live`), cache
      and offline mode exist, exercised by two toy
      providers; no real provider is registered and the
      pyeconomics.providers entry-point table is empty.
    - A provider writes no cache code. The base class's final
      fetch asks pyeconomics.data.cache first and keeps a
      result for ProviderInfo.ttl_seconds (default 3600; a
      user's PYECONOMICS_TTL_<PROVIDER> overrides it), so each
      provider sets ttl_seconds from how often its source
      publishes and gives a restricted series
      terms.with_overrides(cache=CachePolicy.FORBIDDEN) in
      parse. A FRED test proves the store is unreachable the
      way tests/data/cache/cache_support.py's no_database
      does, besides checking that no file exists; the
      recorder already runs inside cache.bypass().
    - No workflow uses a secret, opens an issue or runs on a
      schedule except CodeQL and Scorecard; Phase 1's V10.5
      requires that no repository secret exists; release.yml
      and release-smoke.yml are the hardening pattern
      (top-level permissions: {}, harden-runner first,
      persist-credentials: false, SHA pins).
    - FRED API facts to verify against FRED's own
      documentation at kickoff: v1 takes api_key as a query
      parameter; series/observations accepts realtime_start,
      realtime_end, vintage_dates and output_type;
      series/vintagedates lists vintages; series/tags carries
      the copyright tags; v2's release/observations takes the
      key in an Authorization header (FRED's v2 api_key page).
      ROADMAP §5 "Data terms": FRED is library-only; 14,128
      series need pre-approval before non-personal use;
      Moody's series count as pre-approval whatever their
      label; the required notice is "This product uses the
      FRED® API but is not endorsed or certified by the
      Federal Reserve Bank of St. Louis."
    - The parent roadmap's acceptance criterion: "An ALFRED
      vintage request returns the values as first published,
      verified against a known later revision." A first
      release and its later revision are public facts in
      BEA's news releases (for example an advance estimate of
      quarterly real GDP growth and the same quarter after a
      later annual update), so the test cites BEA for each
      value it pins.

    Files to read (every file before drafting):
    - docs/adr/0011-data-platform.md (decisions 6, 7, 12 and
      18) and this roadmap's Licence, Recording and
      Credential rules and source plan.
    - src/pyeconomics/data/ (providers/base.py, registry.py,
      transport/, modes.py, cache/) and the toy providers.
    - tests/providers/provider_contract.py and
      scripts/record_cassettes.py.
    - .github/workflows/release.yml, release-smoke.yml and
      security.yml (the hardening pattern and zizmor's
      configuration).
    - Each source's API documentation and terms page: FRED
      and ALFRED (the API docs, the v2 api_key page, the
      terms of use), BLS API v1 and v2 (their limits and the
      features only v2 offers), BEA API (and its terms of
      service), Census Data API (and its terms of service).
  </context>

  <goal>
    fred, bls, bea and census are registered, validated and
    pass the contract suite offline and live; ALFRED's first
    release is proven against a cited later revision; the
    weekly live run and the daily heartbeat run on main in a
    locked-down environment; and a failing live run opens one
    issue.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, one batched request to the maintainer (secret
      writes and environment changes need their approval):
      confirm the FRED, BLS, BEA and Census keys are on this
      machine, by name only (the chain's presence check
      prints True or False, never a value), and register any
      missing key at its source; create the providers-live
      environment (deployment branches: main only; nothing at
      repository level); set FRED_API_KEY, BLS_API_KEY,
      BEA_API_KEY and CENSUS_API_KEY with `gh secret set
      <NAME> --env providers-live -R
      pyeconomics-dev/pyeconomics`; and create the
      provider-live label. Once each provider exists, `uv run
      pytest -m live --force-enable-socket -k <provider>
      tests/providers` proves the local key by an
      authenticated call that prints nothing. Record what was
      done, never a value, in the PR body.
    </requirement>

    <requirement>
      fred: series metadata, observations, search, vintages
      (series/vintagedates) and v2 bulk release observations;
      Vintage.as_of, first_release and all through ALFRED's
      real-time parameters and output types, every
      observation carrying its RealtimePeriod; FRED's "."
      becomes None; percent becomes a decimal through
      percent_to_decimal where the series' units are percent;
      period-start dates become period-end indexes with the
      convention recorded (ADR-0011 decision 3); copyright
      tags set each series' notice and redistribution status
      (pre-approval series and every Moody's series marked
      pre-approval); Terms: library-only, the terms URL and
      date, the required notice, llm_use as the terms read,
      CachePolicy.FORBIDDEN; rate limits as FRED documents
      them; the synthesize() hook for cassettes.
    </requirement>

    <requirement>
      bls: POST to API v2 with the registration key in the
      JSON body, at most 50 series and 20 years per query
      (split and merged transparently), the daily limit
      declared; with no key configured, keyless API v1 at its
      lower series, year and daily limits (verify them
      against BLS's documentation at kickoff), with a
      bls_keyless note in the frame's metadata and no
      CredentialError, so a user without a key still gets
      data; BLS's "-" and footnote codes (preliminary values)
      recorded in metadata; monthly, quarterly, semiannual
      and annual periods; Terms: hosted-safe, the notice that
      BLS cannot vouch for data or analyses after retrieval,
      with the access date.
    </requirement>

    <requirement>
      bea: GetData for NIPA (and NIUnderlyingDetail), Regional
      and ITA; table and line selection; numbers with
      thousands separators and "(NA)" markers parsed; the
      UserID as the key; 100 requests a minute and BEA's other
      published limits; Terms: hosted-safe, BEA's required
      notice. BEA serves only current estimates: every frame
      records revised_data.
    </requirement>

    <requirement>
      census: the key on every query; ACS (1- and 5-year),
      the economic indicators time series and international
      trade; geography parameters validated against an
      allowlist, never passed through raw; Terms: hosted-safe,
      Census's required notice.
    </requirement>

    <requirement>
      Entry points: `fred`, `bls`, `bea` and `census` in
      `[project.entry-points."pyeconomics.providers"]`;
      pyeconomics.data.registry.validate() passes; the
      generated provider pages render.
    </requirement>

    <requirement>
      Cassettes and tests: record each capability with
      scripts/record_cassettes.py (FRED synthetic; the others
      real within the caps), plus error cassettes (401, 404,
      429); the contract suite passes offline; per-provider
      tests cover each source's quirks above, BLS's keyed and
      keyless paths both; tests/providers/test_notices.py
      gains the four providers' rows, each notice quoted
      exactly from its terms page; a FRED test proves no
      cache file is created; the canary suite runs a FRED
      fetch with a canary key through the URL and the header
      paths.
    </requirement>

    <requirement>
      ALFRED first release (ROADMAP §4 3.8): an offline test
      on synthetic ALFRED-shaped cassettes proves as_of,
      first_release and later vintages select the right
      values; a live test fetches one BEA-published quarterly
      value as first published and after a later revision
      from ALFRED and asserts both, each pinned value cited in
      the test to BEA's news release (title, date and table).
    </requirement>

    <requirement>
      .github/workflows/providers-live.yml: on schedule
      (weekly) and workflow_dispatch (inputs: a
      simulate_failure boolean, default false, which makes one
      dedicated live test fail, for Step 20's alarm proof);
      top-level permissions: {}; concurrency without cancel.
      Job live: ubuntu-latest (a public repository's
      GitHub-hosted runner), environment providers-live,
      permissions contents: read, harden-runner with
      egress-policy block and an allowed-endpoints list of the
      providers' hosts plus what uv, PyPI and the actions
      need, checkout with persist-credentials: false,
      setup-uv pinned, `uv sync --locked --all-extras`, then
      `uv run --locked pytest -m live --force-enable-socket
      -q` over the whole suite (so the live tests later steps
      add beside their bindings and models run too) with the
      four secrets in that step's env only, and a JUnit
      report of test ids as an artifact. Job report: needs
      live, runs on failure, permissions issues: write; opens
      one issue labelled provider-live with the run URL and
      the failing test ids (no log text) and closes older
      open provider-live issues as superseded.
      .github/workflows/providers-heartbeat.yml: daily
      schedule and workflow_dispatch (input max_age_days,
      default 8; 0 forces a failure, for Step 20's alarm
      proof); top-level permissions: {}; one job with
      permissions actions: read and issues: write, the same
      hardening and no secret; fails, and opens a
      provider-live issue, when the newest successful
      providers-live run on main is older than max_age_days.
      A test asserts the hosts of every registered provider
      whose terms allow automated collection appear in the
      live job's allowed endpoints, and that neither
      workflow has a pull_request trigger.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added"; filepath comment on
      every new Python and YAML file.
    </requirement>
  </requirements>
</task>
```

### Step 6 acceptance criteria

- `fred`, `bls`, `bea` and `census` are registered through the
  `pyeconomics.providers` group, `pyeconomics.data.registry.validate()`
  passes, and each declares its class, terms URL and date, attribution,
  required notice and `llm_use` flag.
- The contract suite passes offline for all four; FRED's cassettes are
  synthetic, and a test proves FRED never creates a cache file.
- An ALFRED request returns the value as first published and a different,
  later-revised value at a later vintage, both cited to BEA's news releases
  (live), and the offline vintage tests pass.
- `providers-live.yml` and `providers-heartbeat.yml` exist, trigger only on
  schedule and dispatch, hold the permissions named above, and pass zizmor;
  every registered provider whose terms allow automated collection has its
  hosts in the live job's egress allowlist; `bls` serves data keyless
  through API v1, and the four providers' exact notices are pinned.
- **Deployed & verified:** after merge, a `workflow_dispatch` run of
  `providers-live.yml` on `main` succeeds against the real APIs with the
  environment's four secrets (`gh run view <id>` reads `success`), which
  proves each secret by an authenticated round-trip, and a dispatched
  `providers-heartbeat.yml` run succeeds.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the four keys exist only as environment
  secrets of `providers-live` (no repository secret; Phase 1's V10.5 still
  passes), no cassette or log holds a key, and FRED is never stored.

---

## Step 7 — Providers: Treasury, Fed Board, New York Fed, EDGAR, OpenFIGI ✅

**Status:** Complete — PR #124 (2026-10-20)

> **Goal:** Register the five keyless rate, market and filing providers on
> the pattern Step 6 set. Add `src/pyeconomics/data/providers/treasury.py`
> (the daily par nominal and real yield curves as `Table`s by tenor, and
> FiscalData's debt, statement and average-interest-rate datasets),
> `fed_board.py` (H.15 selected interest rates, the FOMC Summary of
> Economic Projections' medians, central tendencies and ranges by meeting,
> and the Gürkaynak-Sack-Wright curve parameters and fitted yields, all
> from stable release-page files, never the Data Download Program's "Build
> Your Package" option, which the Board removes the week of 2026-11-09),
> `nyfed.py` (the Markets Data API's reference rates and operations, ACM
> term premia, the Laubach-Williams and Holston-Laubach-Williams r*
> estimates and the Staff Nowcast, with the New York Fed's copyright and
> reference-rate notices), `sec_edgar.py` (submissions, company facts,
> company concepts and XBRL frames, with a User-Agent carrying the user's
> configured contact and SEC's fair-access limit; edgartools evaluated and
> not used) and `openfigi.py` (identifier mapping with an optional key);
> add openpyxl, et-xmlfile and defusedxml as runtime dependencies for the
> spreadsheet sources; record real, trimmed cassettes; and extend the live
> run, with the `SEC_CONTACT` environment secret. Parent: ROADMAP §4 3.4;
> ADR-0011 decisions 10 and 11.

**Branch:** `feature/phase03-step7-providers-rates`

**Resumption:** This step may stay parked while Steps 10–20 and Phase 4
proceed under the external-approval exception. Rebase its draft PR onto
current main before resuming; retain the four providers delivered by Step 10
and every newer provider, reader limit, dependency approval and ledger entry.
Its remaining implementation may be SEC-only, but completion still requires
all five original providers' acceptance checks. Do not restart finished steps.

**Deploys:** GitHub Actions — the next scheduled `providers-live` run
covers this step's providers; a `workflow_dispatch` run on `main` after
merge proves them, and the `SEC_CONTACT` secret, live.

| Setting      | Cost                                     | Balanced                                | Quality                                 |
| ------------ | ---------------------------------------- | --------------------------------------- | --------------------------------------- |
| Model        | GPT-6.1 Sol                              | Opus 5.5                                | Opus 5.5                                |
| Backup       | Sonnet 5.5 — Claude Code · Effort Medium | GPT-6.1 Sol — Codex · Intelligence High | GPT-6.1 Sol — Codex · Intelligence High |
| Platform     | Codex                                    | Claude Code                             | Claude Code                             |
| Effort       | Intelligence Low                         | Effort Medium                           | Effort High                             |
| Thinking     | —                                        | On                                      | On                                      |
| Conversation | **New**                                  | **New**                                 | **New**                                 |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

> Settings updated 2026-10-18 (refresh): was GPT-6.1 Sol · Intelligence
> Medium. Coding PRIMARY, knowledge SECONDARY, Medium, not novel: five
> documented keyless sources on a proven SDK. The ladder's Balanced column
> (the user-context's budget) is Opus 5.5 at Medium on Claude Code; the old
> single-column pick was Codex.

> Ran 2026-10-20: Balanced — Claude Opus 5.5 on Claude Code (effort as the
> operator set it). The **Runs:** column; the Claude weekly pool's `tight` row
> had passed its reset, so it read as headroom.

**Model rationale:** Coding is PRIMARY and knowledge or agentic work SECONDARY; complexity is Medium and the step is not novel. The ladder's Balanced column runs: Claude Opus 5.5 on Claude Code at Medium, backup GPT-6.1 Sol. The Cost and Quality columns, and the Backup under a tight or exhausted pool, are read off the table on the day. New conversation per phase-boundary hygiene.

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
       feature/phase03-step7-providers-rates`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
       complete. Continue from the
       roadmap's current unfinished step." That
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
    - The SEC contact is personal data: it reaches only the
      User-Agent header, is never logged, never written to a
      manifest, a cache entry or a cassette (the recorder
      replaces it), and in CI comes from the SEC_CONTACT
      environment secret of providers-live, set by the
      maintainer with `gh secret set SEC_CONTACT --env
      providers-live`. No contact is hard-coded anywhere.
    - FiscalData, the Markets Data API and EDGAR take only
      parameters from allowlists (dataset ids, rate types,
      CIKs as ten digits, XBRL tags as identifiers), never a
      raw path or URL from the caller.
    - Spreadsheets are read in memory with openpyxl (which
      uses defusedxml when present) in read-only mode, with a
      size cap; nothing is written to disk but cache entries.
    - openpyxl, et-xmlfile and defusedxml pass pip-audit and
      the licences hook (defusedxml's PSF licence, or a
      reviewed exception).
  </security>

  <context>
    pyeconomics. Phase 3. Step 7: providers — Treasury, the
    Federal Reserve Board, the New York Fed, SEC EDGAR and
    OpenFIGI.

    Current state (as of Phase 3 Step 6):

    - fred, bls, bea and census are registered and pass the
      contract suite offline and live; providers-live.yml
      and providers-heartbeat.yml run on main in the
      providers-live environment; the pattern for a
      provider, its cassettes, its tests and its entry point
      is set.
    - Step 6 added seams the contract lacked
      (docs/data/writing-a-provider.md): a source that pages
      (FiscalData) overrides DataProvider.next_page; an
      optional key that only raises limits (OpenFIGI) is
      required=False, the hooks read self.sends_key, and a
      limit that holds only without a key is
      RateLimit(without_key=True); a frame's notes carry what
      a source says about its data (Treasury's December 2021
      methodology change is a note); a source answering a bad
      key with a redirect sets follow_redirects=False; the
      recorder records a 429 or 5xx case with
      Case(simulate=429), never by provoking one; and an
      entry-point module's __all__ lists provider classes
      only. tests/providers/canned.py routes canned answers
      for per-provider tests.
    - The Board's notice of 2026-07-16 says the Data Download
      Program's "Build Your Package" option goes the week of
      2026-11-09 and points users to FRED or each release
      page's XML file; the program itself has no announced
      end date. The GSW parameters and yields are a separate
      file the Board publishes with its paper.
    - SEC EDGAR's fair-access policy asks for a declared
      User-Agent with contact details and at most 10
      requests a second in total. edgartools 5.62.0 requires
      pyarrow (ADR-0008 decision 8) and nineteen more
      packages, so ADR-0011 chose an in-house client.
    - ROADMAP §4 3.4 classes all five hosted-safe; the New
      York Fed requires its copyright notice and terms
      reference, and its reference rates carry their own
      terms line.

    Files to read (every file before drafting):
    - docs/adr/0011-data-platform.md (decisions 3, 4, 10 and
      11) and this roadmap's source plan and Recording rule.
    - src/pyeconomics/data/providers/ (fred.py and bls.py as
      the pattern) and tests/providers/.
    - Each source's documentation and terms page: Treasury's
      interest-rate data and FiscalData API, the Board's H.15,
      SEP and GSW pages, the New York Fed's Markets Data API,
      r* and term-premium pages and terms of use, SEC's
      EDGAR API and fair-access pages, and OpenFIGI's API
      documentation.
  </context>

  <goal>
    treasury, fed_board, nyfed, sec_edgar and openfigi are
    registered, validated and pass the contract suite offline
    and live, with each source's units, dating and notices
    exact, and the spreadsheet stack in place for Steps 9 and
    10.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff: the maintainer sets the SEC_CONTACT
      environment secret of providers-live and configures a
      contact locally (pyeconomics.toml or
      PYECONOMICS_SEC_CONTACT); presence is checked by name
      only.
    </requirement>

    <requirement>
      treasury: the daily par nominal and par real yield
      curves as Tables (one column per tenor, rates as
      decimals, the methodology change of December 2021
      recorded in metadata) from Treasury's published data
      files; FiscalData's Debt to the Penny, Monthly Treasury
      Statement and average interest rates as Series or
      Tables, with its pagination. Terms: hosted-safe,
      attribution to the Treasury.
    </requirement>

    <requirement>
      fed_board: H.15 series (the effective federal funds
      rate, Treasury constant maturities, the target range)
      from the release's XML or CSV files; the SEP's median,
      central tendency and range for each variable and
      horizon, each meeting's release a vintage; the GSW
      file's daily parameters (BETA0 to BETA3, TAU1, TAU2)
      and fitted yields as Tables. Nothing calls a "Build
      Your Package" URL; a test asserts none is built. Terms:
      hosted-safe unless a series is marked third-party,
      which the provider records.
    </requirement>

    <requirement>
      nyfed: the Markets Data API's SOFR, EFFR, OBFR, TGCR and
      BGCR (rates, percentiles, volumes) and its repo and
      SOMA endpoints; ACM term premia; the Laubach-Williams
      (United States) and Holston-Laubach-Williams (United
      States, Canada, euro area) estimates, each file release
      a vintage; the Staff Nowcast. Terms: hosted-safe with
      the New York Fed's copyright notice and terms reference,
      and each reference rate's own terms line.
    </requirement>

    <requirement>
      sec_edgar: submissions, company facts, company concepts
      and frames from data.sec.gov; CIKs zero-padded to ten
      digits; the configured contact in the User-Agent, and
      CredentialError naming the setting when it is missing;
      the 10-requests-a-second limit shared across the
      process. Terms: hosted-safe. Record in the PR body why
      edgartools was not used.
    </requirement>

    <requirement>
      openfigi: the mapping endpoint (POST jobs, batched to
      its limit), with OPENFIGI_API_KEY optional through the
      chain and the rate limits for each case. Terms:
      hosted-safe.
    </requirement>

    <requirement>
      Records that are not frames (ADR-0011 decision 2):
      OpenFIGI's identifier mappings and EDGAR's submissions
      and filing lists are neither dated nor numeric, so
      their providers return typed, bounded records of their
      own (frozen, canonical-JSON round trips, the value
      types' no-URL text rule), which no binding reads; EDGAR
      company facts and frames that are dated numbers stay
      Series or Tables.
    </requirement>

    <requirement>
      Dependencies (Dependency rule): `uv add --no-config`
      openpyxl, et-xmlfile and defusedxml (pure Python,
      floors no higher than Pyodide bundles, no upper bound);
      lock and export with --no-config; licences, pip-audit
      and dependency-review pass, with a reviewed exception
      only if the hook asks for one; the pyodide job stays
      green (nothing imports openpyxl at module import).
    </requirement>

    <requirement>
      Cassettes, tests and entry points: real, trimmed
      cassettes for every capability plus error cassettes;
      the contract suite offline; per-provider tests for
      dates, units, missing markers and notices, and the five
      providers' rows in tests/providers/test_notices.py,
      quoted exactly from each terms page; the canary suite
      with a canary contact; entry points for all five;
      every new host in the live job's egress allowlist; and
      SEC_CONTACT passed to the live run's pytest step as
      PYECONOMICS_SEC_CONTACT.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added"; filepath comment on
      every new Python file.
    </requirement>
  </requirements>
</task>
```

### Step 7 acceptance criteria

- `treasury`, `fed_board`, `nyfed`, `sec_edgar` and `openfigi` are
  registered, `pyeconomics.data.registry.validate()` passes, and each
  declares its class, terms URL and date, attribution, notices and
  `llm_use` flag.
- The contract suite passes offline for all five, with real, trimmed,
  scrubbed cassettes; the Treasury curves are `Table`s of decimal rates by
  tenor, the GSW parameters and yields match the file's columns, and no
  code builds a "Build Your Package" URL.
- EDGAR requests carry the configured contact, never a hard-coded one, and
  respect 10 requests a second; a missing contact raises
  `CredentialError` naming the setting.
- openpyxl, et-xmlfile and defusedxml are locked to PyPI only, audited and
  licence-checked; the `pyodide` job is green.
- **Deployed & verified:** after merge, a `workflow_dispatch` run of
  `providers-live.yml` on `main` succeeds with this step's providers
  included and the `SEC_CONTACT` secret in use (`gh run view <id>` reads
  `success`).
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the SEC contact appears in no log,
  manifest, cache entry or cassette, and no request is built from a
  caller's URL.

---

## Step 8 — Providers: SDMX Sources, World Bank, DBnomics ✅

**Status:** Complete — PR #125 (2026-10-16)

> **Goal:** Register the international providers. Add the `[sdmx]` extra
> (sdmx1) and, on it, `src/pyeconomics/data/providers/imf.py`, `oecd.py`,
> `ecb.py`, `bis.py` and `eurostat.py` — dataflow search, structure-aware
> series keys, data as `Series` or `Table`, and each source's notices —
> with sdmx1's HTTP session confined to the providers' hosts and the
> operating system's trust store; `world_bank.py`, a thin in-house client
> for the World Bank's v2 API with each series' `License_Type` deciding
> its class (wbgapi is not used); and `dbnomics.py`, a thin in-house client
> for DBnomics's REST API, library-only, with its upstream provider's
> attribution (its AGPL client is excluded). Settle OECD's class from its
> terms (ADR-0005 left it TBD), apply Eurostat's listed exceptions as
> series-level gates, record cassettes (synthetic for library-only
> sources), and extend the live run. Parent: ROADMAP §4 3.4; §5 "Data
> licensing policy" and "Required notices"; ADR-0005; ADR-0011 decisions
> 7 and 11.

**Branch:** `feature/phase03-step8-providers-international`

**Prerequisite exception:** Completed Step 6 is sufficient to start this step
under the Execution Order's declared parallelism with Step 7. Use a separate
worktree and conversation, starting from `origin/main`; carry the roadmap-only
sequencing amendment if needed. Step 7's SEC blocker does not transfer to this
step. Each step keeps its own acceptance criteria and completion mark.

**Deploys:** GitHub Actions — the next scheduled `providers-live` run
covers this step's providers; a `workflow_dispatch` run on `main` after
merge proves them live.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | GPT-6.1 Sol                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort High        |
| Platform     | Codex                                         |
| Intelligence | Medium                                        |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: five SDMX
sources share one client library, and the World Bank and DBnomics are simple
JSON APIs; the knowledge is SDMX's structure and each source's terms and
notices, applied on a settled SDK. Complexity is Medium, so A in coding
suffices, and the operator's posture sends Medium, GPT-adequate work to
Codex on the ChatGPT Pro 5x plan, the lane with slack, $0 marginal. GPT-6.1
Sol is the pick: at Intelligence Medium, where this step runs, it leads
GPT-6 Sol, at the same price, on Terminal-Bench 4.0 (48.0% vs 18.7%), HLE
(49.9% vs 41.0%) and the AA Intelligence Index (47.8 vs 39.8), with SciCode
level (53.2 vs 53.8); GPT-6 Astra is within noise of it on the AA
Intelligence Index (49.6) at five times the price. Codex opens on its
provider default; set GPT-6.1 Sol at Intelligence Medium, the ladder value
for well-specified work the contract suite checks. The backup is Sonnet 5.5
on Claude Code at Effort High, the cell `roadmodel backup` prints: at High,
Sonnet 5.5 stands level with GPT-6.1 Sol at Medium (AA Intelligence Index
46.8 vs 47.8). New conversation per phase-boundary hygiene.

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
       feature/phase03-step8-providers-international`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - sdmx1 makes its own requests: mount an adapter on its
      requests session that refuses any host outside the
      provider's allowlist and any scheme but https, uses
      truststore's context and the transport's timeouts, and
      turn off any response caching of its own, so the
      licence-aware cache stays the only store.
    - The [sdmx] closure (sdmx1, lxml, requests, certifi)
      passes pip-audit; certifi's MPL-2.0 carries a reviewed
      exception the maintainer approves in this PR, with the
      test pin and a purl exemption.
    - XML from SDMX sources is parsed with lxml's entity
      resolution and network access off; nothing evals or
      unpickles a response.
    - IMF and DBnomics cassettes are synthetic; the World
      Bank's class is decided per series, never assumed.
  </security>

  <context>
    pyeconomics. Phase 3. Step 8: providers — the SDMX
    sources, the World Bank and DBnomics.

    Baseline: completed Phase 3 Step 6. Step 7 may still be
    in progress under the Execution Order's parallelism.

    - The SDK, transport, cache and live workflow are shipped;
      four keyed providers pass offline and live. If Step 7
      has merged, its five providers and spreadsheet stack
      are also present. Neither is required by this step.
      No extra pulls in a data client yet. Read the actual
      registry and dependency state at kickoff.
    - sdmx1 2.27.0 (Apache-2.0 classifier) depends on lxml,
      requests, pandas, platformdirs, python-dateutil and
      packaging; requests brings certifi (MPL-2.0), outside
      ADR-0004's allowlist. wbgapi 1.0.14 needs PyYAML, which
      has no CPython 3.15 wheel; DBnomics's own client is
      AGPL and excluded by name.
    - ROADMAP §4 3.4 classes the ECB, BIS and Eurostat
      hosted-safe (Eurostat minus its listed exceptions), the
      IMF library-only until it grants permission, DBnomics
      library-only, and the World Bank hosted-safe only where
      License_Type is CC BY; ADR-0005 left OECD's class TBD
      because its terms page refused automated access on
      2026-10-05. Notices: the ECB's "free of charge" line in
      any paid tier, no added charge for BIS data, and each
      source's prescribed source line with the dataset and
      access date.

    Files to read (every file before drafting):
    - docs/adr/0005-data-licence-model.md and
      docs/adr/0011-data-platform.md (decisions 7, 10 and
      11).
    - src/pyeconomics/data/providers/ and tests/providers/.
    - sdmx1's documentation (sources, the Client, its
      session options) and each source's terms: the IMF's
      copyright and usage page, OECD's terms and conditions,
      the ECB's legal notice, BIS's data portal terms,
      Eurostat's copyright notice and exceptions, the World
      Bank's dataset terms and the API's License_Type
      metadata, and DBnomics's terms.
  </context>

  <goal>
    imf, oecd, ecb, bis, eurostat, world_bank and dbnomics are
    registered, validated and pass the contract suite offline
    and live; OECD carries a class read from its own terms;
    the World Bank and Eurostat classes are decided per
    series; and the [sdmx] extra is locked, audited and
    licence-checked.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, one batched question to the maintainer: the
      reviewed licence exception for certifi (MPL-2.0, a
      certificate bundle used unmodified) and OECD's class as
      this step reads its terms. Record the answers in the
      PR body.
    </requirement>

    <requirement>
      [sdmx] extra: `uv add --no-config --optional sdmx
      "sdmx1>=2.27"`, joined to `all` and the test group;
      lock and export with --no-config; the licences hook on
      all three operating systems; reviewed exceptions for
      certifi and anything else it reports, the test pin and
      purl exemptions updated. The five providers import
      sdmx1 inside their fetch functions, and each declares
      extra="sdmx", so a missing extra raises
      MissingOptionalDependencyError naming it.
    </requirement>

    <requirement>
      SDMX providers: imf (the IMF's current SDMX service:
      IFS, BOP, DOTS and the WEO where served), oecd, ecb
      (exchange-rate references, €STR, monetary statistics,
      HICP), bis (central bank policy rates, credit, property
      prices, effective exchange rates) and eurostat; each
      with search over dataflows, describe from structures,
      fetch by series key with dimension values validated
      against the structure, and the source's notice. Terms:
      as each source's terms read today — imf library-only,
      ecb and bis hosted-safe, eurostat hosted-safe with its
      listed exceptions as series-level overrides, oecd as
      settled at kickoff.
    </requirement>

    <requirement>
      world_bank: the v2 API's indicator data with
      pagination, country and indicator codes validated, and
      each series' License_Type from the source metadata
      endpoint: CC BY 4.0 → hosted-safe with the prescribed
      source line; anything else → library-only, recorded
      per series. Record in the PR body why wbgapi was not
      used.
    </requirement>

    <requirement>
      dbnomics: series and dataset search and series fetch
      through the REST API; library-only; attribution to the
      upstream provider and to DBnomics; nothing imports
      DBnomics's client.
    </requirement>

    <requirement>
      Cassettes, tests and entry points: cassettes for every
      capability (synthetic for imf and dbnomics, and for
      oecd if its class is not hosted-safe), error cassettes;
      the contract suite offline; tests for series-level
      class decisions (a CC BY World Bank series and one with
      another licence; a Eurostat exception); the seven
      providers' rows in tests/providers/test_notices.py,
      quoted exactly from each terms page (ECB's and the
      IMF's notices among them); the adapter refusing a
      foreign host; entry points for all seven; every new
      host in the live job's egress allowlist.
    </requirement>

    <requirement>
      ADR-0005 left OECD TBD; record the settled class with
      its terms URL and access date in the provider, in this
      roadmap's source plan (replacing its TBD) and in the PR
      body. ADR-0005 is not edited: its decision text already
      defers OECD's class until the provider merges in Phase
      3. ROADMAP §4 3.4's table and §5's licence-class table
      list OECD as hosted-safe; if the settled class differs,
      amend both in this PR.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added"; filepath comment on
      every new Python file.
    </requirement>
  </requirements>
</task>
```

### Step 8 acceptance criteria

- `imf`, `oecd`, `ecb`, `bis`, `eurostat`, `world_bank` and `dbnomics`
  are registered, `pyeconomics.data.registry.validate()` passes, and each
  declares its class, terms URL and date, attribution, notices and
  `llm_use` flag; OECD's class is read from its own terms and recorded.
- The contract suite passes offline for all seven; the World Bank's class
  follows each series' `License_Type`, Eurostat's exceptions override the
  provider class, and IMF and DBnomics cassettes are synthetic.
- sdmx1's session refuses foreign hosts and plain HTTP, uses the trust
  store, and keeps no cache of its own; without `[sdmx]`, the five
  providers raise `MissingOptionalDependencyError` naming the extra.
- The `[sdmx]` extra is locked to PyPI only, audited, and passes the
  `licences` hook on all three operating systems with reviewed exceptions.
- **Deployed & verified:** after merge, a `workflow_dispatch` run of
  `providers-live.yml` on `main` succeeds with this step's providers
  included (`gh run view <id>` reads `success`).
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and no third-party client can reach a
  host outside its provider's allowlist.

---

## Step 9 — Providers: Regional Fed Research, CBO, Penn World Table ✅

**Status:** Complete — PR #127 (2026-10-17)

> **Goal:** Register the research sources the monetary-policy suite and
> the macro entries need for real-time and forecast inputs. Add
> `src/pyeconomics/data/providers/philadelphia_fed.py` (the Real-Time Data
> Set for Macroeconomists, whose vintage matrices map onto real-time
> periods so `Vintage.as_of` selects the data as published, and the Survey
> of Professional Forecasters' mean and median forecasts by variable and
> horizon, each survey a vintage), `atlanta_fed.py` (GDPNow's current
> estimate and history), `cleveland_fed.py` (its inflation-expectations
> term structure), `cbo.py` (the economic projections and potential output
> of each Budget and Economic Outlook, each report a vintage) and
> `penn_world_table.py` (the current release's national-accounts, capital,
> employment, human-capital and productivity series); classify CBO and the
> Penn World Table from their own terms before either can feed a hosted
> surface; record cassettes (synthetic wherever the class requires, as
> minimal spreadsheets with the real layout); and extend the live run.
> Parent: ROADMAP §4 3.4 and 3.7 (the classification note); ADR-0011
> decisions 6 and 7.

**Branch:** `feature/phase03-step9-providers-research-macro`

**Prerequisites:** Step 8 must be Complete on main. Step 9 may proceed in a
separate worktree while Step 7 remains unfinished under the Execution Order's
2026-10-17 amendment. Supply the bounded spreadsheet prerequisite below;
Step 7's SEC access blocker does not transfer to this step.

**Deploys:** GitHub Actions — the next scheduled `providers-live` run
covers this step's providers; a `workflow_dispatch` run on `main` after
merge proves them live.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | GPT-6.1 Sol                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort High        |
| Platform     | Codex                                         |
| Intelligence | Medium                                        |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: five
spreadsheet-based research sources on the settled SDK, where the knowledge
is the Real-Time Data Set's vintage timing, the SPF's layout and each
source's terms. Complexity is Medium — the vintage mapping is the only
subtle part, and the Real-Time Data Set documents it — so A in coding
suffices, and the operator's posture sends Medium, GPT-adequate work to
Codex on the ChatGPT Pro 5x plan, the lane with slack, $0 marginal. GPT-6.1
Sol is the pick: at Intelligence Medium, where this step runs, it leads
GPT-6 Sol, at the same price, on Terminal-Bench 4.0 (48.0% vs 18.7%), HLE
(49.9% vs 41.0%) and the AA Intelligence Index (47.8 vs 39.8), with SciCode
level (53.2 vs 53.8); GPT-6 Astra is within noise of it on the AA
Intelligence Index (49.6) at five times the price. Codex opens on its
provider default; set GPT-6.1 Sol at Intelligence Medium, the ladder value;
the vintage tests and Step 13's golden cases check the mapping. The backup
is Sonnet 5.5 on Claude Code at Effort High, the cell `roadmodel backup`
prints: at High, Sonnet 5.5 stands level with GPT-6.1 Sol at Medium (AA
Intelligence Index 46.8 vs 47.8). New conversation per phase-boundary
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
       feature/phase03-step9-providers-research-macro`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
       complete. Step 10 can start
       once Step 7 is complete." That
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
    - Spreadsheets are read in memory, read-only, size-capped
      and parsed through openpyxl with defusedxml; a
      workbook's formulas are never evaluated, only cached
      values read.
    - Cassettes for library-only sources hold minimal
      synthetic workbooks with the real sheet and column
      layout, never the published values; a cassette's body
      stays under the size cap.
    - A provider's class is read from its source's terms at
      this step, never assumed from the expected class in
      this roadmap.
  </security>

  <context>
    pyeconomics. Phase 3. Step 9: providers — the
    Philadelphia, Atlanta and Cleveland Feds' research data,
    CBO and the Penn World Table.

    Baseline: completed Step 8; Step 7 may remain blocked.

    - Eleven providers are registered after Step 8, unless
      Step 7 has since merged. The SDK, transport, cache,
      [sdmx] extra and FRED/ALFRED vintage pattern exist.
      Read the actual registry and dependency state.
    - The shared spreadsheet reader is on Step 7's branch
      until either step ships it. Step 9 must bring the
      necessary reader subset, dependencies and regression
      tests itself if absent on main; no Step 7 provider is
      a prerequisite. NY Fed and Fed Board implementations
      are reference material, not assumed shipped code.
    - "Recorded in metadata" means a frame's notes (Step 6):
      a snake_case code and a detail, such as the Penn World
      Table's release version.
    - ROADMAP §4 3.4 classes the Philadelphia, Atlanta and
      Cleveland Fed products library-only (research or
      non-commercial terms); §4 3.7 says "CBO and Penn World
      Table data are classified in Phase 3 before either
      feeds the hosted site". CBO's projections are US
      government works; the Penn World Table publishes its
      own licence and asks for a citation of Feenstra,
      Inklaar and Timmer (2015).
    - The Real-Time Data Set stores, for each variable, a
      matrix whose columns are vintages and whose rows are
      observation dates; its documentation defines each
      vintage's date. Step 13's forecast-based rules read the
      SPF's median forecasts by horizon, and its real-time
      evaluation can read this data set where ALFRED has no
      vintage.

    Files to read (every file before drafting):
    - docs/adr/0011-data-platform.md (decisions 3, 6 and 7).
    - src/pyeconomics/data/providers/ (fred.py for vintages)
      and tests/providers/. If present, nyfed.py and
      data/transport/files.py provide spreadsheet examples;
      otherwise read them and their tests from Step 7's
      branch using git show, without switching worktrees.
    - Each source's documentation and terms: the Real-Time
      Data Set's and SPF's documentation, GDPNow's page and
      data file, the Cleveland Fed's inflation-expectations
      page, CBO's "Budget and Economic Data" page and
      copyright note, and the Penn World Table's release page
      and licence.
  </context>

  <goal>
    philadelphia_fed, atlanta_fed, cleveland_fed, cbo and
    penn_world_table are registered, validated and pass the
    contract suite offline and live; the Real-Time Data Set's
    and CBO's vintages behave like ALFRED's under
    Vintage.as_of; and CBO and the Penn World Table carry
    classes read from their own terms.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Own the spreadsheet prerequisite when Step 7 has not
      merged: port only the necessary bounded in-memory
      reader functions from its data/transport/files.py and
      their regression tests, or implement an equivalent
      shared reader. Record provenance in the PR body.
      Add openpyxl and defusedxml with --no-config, and
      et-xmlfile or xlrd only when required by actual source
      formats; regenerate the lock and export. Recheck
      installed licences and previously approved exceptions,
      retain required notices and test pins, and obtain
      review for any new exception. Keep the XML/ZIP size,
      entry, row and column bounds, read-only cached values,
      disabled external links and scrubbed parser errors.
      Include the reader in the layering checks and verify
      supported Python/OS and Pyodide compatibility. Do not
      carry Step 7 providers or its completion mark into
      this PR. Reconcile duplicate shared code when Step 7
      later rebases onto main.
    </requirement>

    <requirement>
      philadelphia_fed: for each Real-Time Data Set variable
      (real output, the price index, the unemployment rate
      and the others the catalog will need), parse the
      vintage matrix, give each column its vintage date from
      the documentation's rule, and expose as_of,
      first_release and all; for the SPF, the mean and median
      forecasts by variable and horizon (quarterly and annual
      horizons, the 10-year expectations), each survey's
      release date a vintage. Terms: library-only as read,
      the attribution the Philadelphia Fed asks for.
    </requirement>

    <requirement>
      atlanta_fed (GDPNow, each update a vintage),
      cleveland_fed (expected inflation, real interest rates
      and the inflation risk premium by horizon): Terms as
      read; both library-only unless their terms say
      otherwise.
    </requirement>

    <requirement>
      cbo: from each Budget and Economic Outlook's data files,
      using CBO's own machine-readable CSV repository where
      the current Budget and Economic Data page directs
      automated users (verified 2026-10-17). Retain every
      report available in that official archive, record its
      coverage and exact publication date, not its month label:
      potential GDP, potential labour force, the noncyclical
      rate of unemployment, the output gap and the ten-year
      economic projections, each report's release date a
      vintage. Classify from CBO's own terms and record the
      class, URL and date.
    </requirement>

    <requirement>
      penn_world_table: the current release's rgdpna, rkna,
      emp, hc, labsh, rtfpna and their companions by country,
      each release a version recorded in metadata, with the
      citation the authors require. Classify from the
      release's own licence and record the class, URL and
      date.
    </requirement>

    <requirement>
      Parent roadmap, same PR: replace ROADMAP §4 3.7's
      sentence "CBO and Penn World Table data are classified
      in Phase 3 before either feeds the hosted site" with
      the classes this step recorded, and fill the source
      plan's two TBD cells in this roadmap.
    </requirement>

    <requirement>
      Cassettes, tests and entry points: cassettes for every
      capability (synthetic, minimal workbooks for every
      source not classed hosted-safe), error cassettes; the
      contract suite offline; vintage tests on synthetic
      matrices (as_of picks the column published by the date;
      first_release the first column holding an observation);
      the five providers' rows in
      tests/providers/test_notices.py, quoted exactly from
      each terms page; entry points for all five; every new
      host in the live job's egress allowlist.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added"; filepath comment on
      every new Python file.
    </requirement>
  </requirements>
</task>
```

### Step 9 acceptance criteria

- `philadelphia_fed`, `atlanta_fed`, `cleveland_fed`, `cbo` and
  `penn_world_table` are registered, `pyeconomics.data.registry.validate()`
  passes, and each declares its class, terms URL and date, attribution and
  `llm_use` flag.
- CBO and the Penn World Table carry classes read from their own terms;
  ROADMAP §4 3.7's note and this roadmap's source plan record them.
- The contract suite passes offline for all five; `Vintage.as_of`,
  `first_release` and `all` select the right columns of the Real-Time Data
  Set's matrices and the right CBO reports on synthetic data.
- Library-only cassettes are synthetic minimal workbooks under the size
  cap; no workbook formula is evaluated.
- The required spreadsheet reader and dependency closure ship in this PR if
  absent on main, with bounded-parser regressions, licence checks and platform
  compatibility verified; Step 7's unfinished providers remain separate.
- **Deployed & verified:** after merge, a `workflow_dispatch` run of
  `providers-live.yml` on `main` succeeds with this step's providers
  included (`gh run view <id>` reads `success`).
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and no published value from a
  library-only source is committed.

---

## Step 10 — Providers: Asset-Pricing and Market Research Data ✅

**Status:** Complete — PR #129 (2026-10-17)

> **Goal:** Register the ten asset-pricing and market research sources the
> finance entries need. Add `src/pyeconomics/data/providers/ken_french.py`
> (factors and portfolios from the Data Library's zipped CSV files,
> monthly, annual and daily sections, percent returns as decimals),
> `shiller.py` (the long-run US equity data file), `damodaran.py` (the
> implied equity risk premium history, country risk premiums, industry
> betas and multiples — aggregates only, with credit), `aqr.py`,
> `hou_xue_zhang.py`, `jkp.py` and `open_source_asset_pricing.py` (factor
> and anomaly data sets, through thin in-house clients; the GPL-licensed
> client of Open Source Asset Pricing is not used), `cboe.py` (VIX
> history), `coin_metrics.py` (community network data, CC BY-NC 4.0) and
> `yfinance.py` behind a new `[yfinance]` extra, off by default and never in
> the scheduled live run, because Yahoo's terms bar automated collection;
> add xlrd as a runtime dependency for the legacy `.xls` sources; record
> synthetic cassettes for every library-only source; and extend the live
> run. First recover Treasury, Fed Board, NY Fed and OpenFIGI from Step 7
> if absent on main, including their original verification requirements.
> Parent: ROADMAP §4 3.4; §5 "Data terms"; ROADMAP §2 gap 15 (its data
> half); ADR-0011 decisions 7 and 11.

**Branch:** `feature/phase03-step10-providers-research-finance`

**Prerequisites:** Step 9 must be Complete on main. Step 7 may remain parked
for SEC access. This step must first deliver `treasury`, `fed_board`, `nyfed`
and `openfigi` and their shared prerequisites if absent on main, with the
original Step 7 criteria for those four sources. No SEC dependency transfers
to this step. See the Overview's external-approval exception.

**Deploys:** GitHub Actions — the next scheduled `providers-live` run
covers this step's providers except yfinance; a `workflow_dispatch` run on
`main` after merge proves them live.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | GPT-6.1 Sol                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort High        |
| Platform     | Codex                                         |
| Intelligence | Medium                                        |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: ten file- or
API-based sources on the settled SDK — the largest provider step, but
mechanical once the zip, CSV and spreadsheet patterns of Steps 7 and 9 exist
— where the knowledge is each file's layout and each source's terms.
Complexity is Medium, so A in coding suffices, and the operator's posture
sends Medium, GPT-adequate work to Codex on the ChatGPT Pro 5x plan, the
lane with slack, $0 marginal. GPT-6.1 Sol is the pick: at Intelligence
Medium, where this step runs, it leads GPT-6 Sol, at the same price, on
Terminal-Bench 4.0 (48.0% vs 18.7%), HLE (49.9% vs 41.0%) and the AA
Intelligence Index (47.8 vs 39.8), with SciCode level (53.2 vs 53.8); GPT-6
Astra is within noise of it on the AA Intelligence Index (49.6) at five
times the price. Codex opens on its provider default; set GPT-6.1 Sol at
Intelligence Medium, the ladder value for numerous but patterned providers
the contract suite checks. The backup is Sonnet 5.5 on Claude Code at Effort
High, the cell `roadmodel backup` prints: at High, Sonnet 5.5 stands level
with GPT-6.1 Sol at Medium (AA Intelligence Index 46.8 vs 47.8). New
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
       feature/phase03-step10-providers-research-finance`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - Zip archives are read in memory with a cap on each
      member's uncompressed size and on the member count;
      nothing is extracted to disk, so no path in an archive
      is ever followed.
    - Of the ten finance sources, every source except
      Damodaran's aggregates is
      library-only: its cassettes are synthetic, nothing from
      it is bundled in the wheel, and no published value is
      committed except a golden case's cited handful (Steps
      15 and 16).
    - yfinance is off by default, needs the user's explicit
      enabling and shows Yahoo's terms on first use; it never
      runs in CI against Yahoo; its extra's closure passes
      pip-audit and the licences hook with reviewed
      exceptions (peewee's missing metadata, certifi's
      MPL-2.0).
    - xlrd reads only the legacy .xls files it is given, in
      memory; it passes the licences hook with a reviewed
      exception for its ambiguous BSD metadata.
  </security>

  <context>
    pyeconomics. Phase 3. Step 10: providers — asset-pricing
    and market research data.

    Current state (as of Phase 3 Step 9):

    - Sixteen providers are registered after Step 9, or more
      if Step 7 has since merged. Inspect actual main; never
      assume its five providers are already present.
      Spreadsheet parsing (openpyxl, defusedxml)
      and vintage-keeping research sources exist; the
      [sdmx] extra carries certifi's reviewed exception.
    - ROADMAP §5 "Data terms": the Ken French Data Library is
      copyright Eugene F. Fama and Kenneth R. French, fetched
      at runtime with attribution and never bundled; Yahoo
      data through yfinance is for personal use only; Coin
      Metrics community data is CC BY-NC 4.0, never part of
      a paid feature; Cboe VIX history, AQR, JKP (CC BY-NC)
      and Hou-Xue-Zhang data have research or non-commercial
      terms; Damodaran's aggregates may be displayed with
      credit, never mirrored in bulk.
    - ROADMAP §2 gap 15 (Bitcoin stock-to-flow is contested;
      Coin Metrics data is non-commercial) is closed in two
      halves: this step carries the data half — Coin Metrics
      classed library-only with its licence enforced in
      code — and Phase 7's alternatives batch keeps the
      stock-to-flow model with evidence status rejected.
    - yfinance 1.7.0 depends on curl_cffi, peewee (no licence
      metadata), protobuf, websockets, lxml, beautifulsoup4,
      multitasking, pytz, platformdirs and requests;
      curl_cffi brings cffi (`MIT-0`) on every operating
      system, which Step 3's reviewed exception (made for
      keyring's Linux closure) already covers; the
      openassetpricing package is GPL-2.0 and excluded.

    Files to read (every file before drafting):
    - docs/adr/0011-data-platform.md (decisions 7, 10 and
      11) and this roadmap's Licence and Recording rules.
    - src/pyeconomics/data/providers/ and tests/providers/.
      Read Step 7's complete task and its parked branch's
      four unblocked providers, tests, real recordings,
      SDK records capability, XML/XLS readers, recorder,
      licence notices/exceptions, live hosts and Pyodide
      support. Compare each with current main before reuse;
      preserve Step 9's stronger reader and memory-only
      workbook writer. Do not import SEC implementation.
    - Each source's data page and terms: the Ken French Data
      Library, Robert Shiller's data page, Damodaran Online,
      AQR's data sets, global-q.org, jkpfactors.com, Open
      Source Asset Pricing, Cboe's VIX history, Coin
      Metrics's community data and terms, and yfinance's
      README and Yahoo's terms.
  </context>

  <goal>
    The four recovered providers and ten finance providers
    are registered, validated and pass the
    contract suite offline; all but yfinance pass live in the
    scheduled run; yfinance works only once enabled; every
    library-only cassette is synthetic; and the [yfinance]
    extra and xlrd are locked, audited and licence-checked.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, one batched question to the maintainer: the
      new licence exceptions for peewee and any other
      package the hook reports, and the yfinance enabling
      mechanism below. Existing approvals for xlrd and
      defusedxml persist; verify and retain their exact
      notices and conditions, without asking again. Record
      existing approvals and any new answers in the PR body.
    </requirement>

    <requirement>
      First deliver treasury, fed_board, nyfed and openfigi
      if absent from main, satisfying their full source
      contracts in Step 7, its non-EDGAR records capability,
      source-specific real recordings and error cases,
      canaries, attribution, units, vintage semantics,
      hosted gates, entry points and offline contract tests.
      Port only their needed shared SDK and bounded XML/XLS
      reader/recorder closure; retain main's XLSX limits,
      safe XML, memory-only writes and all current providers.
      Preserve the approved xlrd legacy acknowledgement and
      check the entire dependency closure on all platforms.
      Document the parked branch/commit provenance and exact
      reused files in this PR. No sec_edgar entry point,
      live case or host is added until Step 7 verifies it.
      The four recovered providers join this step's main
      post-merge live proof, with no skip for SEC access.
      If they already merged, verify them rather than
      duplicate implementation. Do not mark Step 7 complete here.
    </requirement>

    <requirement>
      ken_french: the research factors (three-factor,
      five-factor 2x3, momentum, their daily versions) and
      portfolios (industry portfolios, 25 size and
      book-to-market portfolios) as Tables; each zipped CSV's
      monthly and annual sections split; YYYYMM and YYYYMMDD
      dates to period ends; percent to decimals; the
      library's missing markers (-99.99, -999) to None; the
      copyright notice. Terms: library-only.
    </requirement>

    <requirement>
      shiller (the long-run US equity data file through xlrd:
      price, dividend, earnings, CPI, the long rate and
      CAPE) and damodaran (implied ERP history, country risk
      premiums, industry betas and multiples, each file's
      update a version; Terms: hosted-safe for these
      aggregates, with the credit he asks for and "no bulk
      mirror" recorded as conditions, as ROADMAP §4 3.4's
      "hosted display of aggregates, with credit" reads).
    </requirement>

    <requirement>
      aqr, hou_xue_zhang, jkp and open_source_asset_pricing:
      the factor or portfolio series each publishes, as
      Tables with their frequencies; Terms as read, each
      library-only unless its terms say otherwise; nothing
      imports the openassetpricing package.
    </requirement>

    <requirement>
      cboe (daily VIX open, high, low and close) and
      coin_metrics (community asset metrics through its
      public API): both library-only; Coin Metrics carries CC
      BY-NC 4.0 and a never-paid flag the Phase 8 paywall
      checks will read.
    </requirement>

    <requirement>
      yfinance: an extra `[yfinance]` (`uv add --no-config
      --optional yfinance "yfinance>=1.7"`, joined to `all`
      and the test group); the provider imports yfinance
      inside its fetch functions, refuses to run until the
      user enables it (a pyeconomics.toml setting or
      configure(), as agreed at kickoff), and warns once per
      process with Yahoo's personal-use terms; prices,
      fundamentals and option chains as Tables; Terms:
      library-only, automated collection barred, so the
      scheduled run skips it and its live test runs only
      when the maintainer sets PYECONOMICS_LIVE_YFINANCE=1
      on their own machine.
    </requirement>

    <requirement>
      Dependencies: `uv add --no-config "xlrd>=2.0"` (pure
      Python); lock and export with --no-config; the licences
      hook on all three operating systems; reviewed
      exceptions for xlrd, peewee and whatever else it
      reports, with the test pin and purl exemptions;
      pip-audit and dependency-review green.
    </requirement>

    <requirement>
      Cassettes, tests and entry points: synthetic cassettes
      for every library-only source (minimal zips,
      workbooks or CSVs with the real layout), real trimmed
      ones for Damodaran's aggregates; error cassettes; the
      contract suite offline; tests for each file layout,
      date convention and missing marker; a zip-bomb and a
      path-traversal archive refused; yfinance refused until
      enabled; the ten providers' rows in
      tests/providers/test_notices.py, quoted exactly from
      each terms or data page (Damodaran's credit and Coin
      Metrics' CC BY-NC 4.0 notice among them); entry points
      for all ten; every new host except Yahoo's in the live
      job's egress allowlist.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added"; filepath comment on
      every new Python file.
    </requirement>
  </requirements>
</task>
```

### Step 10 acceptance criteria

- `treasury`, `fed_board`, `nyfed` and `openfigi` are present and meet
  their original Step 7 criteria: source contracts, real trimmed recordings,
  offline tests, canaries, notices, units/vintages, safe readers and Pyodide.
  Their shared prerequisites and licences pass the gate; all four are included
  in the successful post-merge live run. No partial SEC provider is registered
  and no Step 7 completion mark is carried. The minimum registry is now 30 ids
  (31 only if Step 7 independently completes).
- The ten providers are registered, `pyeconomics.data.registry.validate()`
  passes, and each declares its class, terms URL and date, attribution,
  notices and `llm_use` flag; Coin Metrics carries CC BY-NC 4.0 and its
  never-paid flag.
- The contract suite passes offline for all ten; every library-only
  cassette is synthetic; Ken French returns are decimals with period-end
  dates and missing markers as `None`.
- yfinance raises until enabled, warns with Yahoo's terms on first use,
  and is absent from the scheduled run; without `[yfinance]` it raises
  `MissingOptionalDependencyError` naming the extra.
- An oversized archive member and a path-traversal member are refused, and
  nothing is extracted to disk.
- xlrd and the `[yfinance]` extra are locked to PyPI only, audited, and
  pass the `licences` hook with reviewed exceptions.
- **Deployed & verified:** after merge, a `workflow_dispatch` run of
  `providers-live.yml` on `main` succeeds with this step's providers other
  than yfinance included (`gh run view <id>` reads `success`).
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and no library-only dataset is
  committed, bundled or fetched from CI against its terms.

---

## Step 11 — Semantic Catalog and Resolver ✅

**Status:** Complete — PR #130 (2026-10-17)

> **Goal:** Give users and models one vocabulary for data, and one place where
> licence and mode decide which source answers. Add
> `src/pyeconomics/data/catalog/` (concept definitions as Python modules — id,
> title, unit kind, frequency, seasonal adjustment, definition, and candidate
> series in fallback order, each with its provider, series key and declared
> transforms), `src/pyeconomics/core/transforms.py` (the transform names, a
> vocabulary core can validate a binding against) and `catalog/transforms.py`
> (their implementations: percent change, year-over-year, difference, log, ratio
> of two concepts, frequency conversion by mean, sum, first, last or period end,
> and as-of alignment), `resolver.py` (resolution by mode, credentials,
> installed extras, vintage capability and series-level licence gates, with
> `strict=True` to disable fallback and the chain tried recorded in every
> `DataSource`), and the public data API — `pyeconomics.data.get`, `search`,
> `describe`, `vintages` and `sources` — that Phase 4's `data` commands will
> wrap; define the concepts Steps 13–17 bind (US prices, labour, output, policy
> rates, Treasury curves, r*, the SEP and SPF, fiscal series, Penn World Table
> series, factor and portfolio sets, and the euro-area and two other economies'
> policy-rule inputs); add the concepts section of the released ledger; and
> publish the "Data sources and keys" guide, the generated concept pages and the
> sources summary on the documentation preview. Parent: ROADMAP §4 3.5; §5 "Data
> licensing policy" rules 1 and 3; ADR-0011 decisions 6, 7 and 15.

**Branch:** `feature/phase03-step11-catalog`

**Prerequisites:** Step 10 Complete on main, including the four recovered
providers. Step 7's SEC deferral does not block this step. Do not add an
EDGAR-only catalog candidate while that provider is absent.

**Deploys:** Documentation → the Read the Docs `main` preview, rebuilt
from `main` on merge with the data guide, the sources summary and the
generated concept pages; `stable` stays on 0.2.6.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Sonnet 5.5                             |
| Backup       | GPT-6.1 Sol — Codex · Intelligence High       |
| Platform     | Claude Code                                   |
| Effort       | High                                          |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and planning SECONDARY: the step
designs the concept vocabulary and its fallback, alignment and licence
rules, and implements the resolver every binding and Phase 4 surface will
call. Complexity is High — many interacting rules (mode, credentials,
extras, vintages, series-level licences, frequency alignment) and a
vocabulary that becomes permanent at release — but ADR-0011 fixed its shape,
so High rather than Extra High. High requires S in coding; Sonnet 5.5 ties
Opus 5.5, Fable 5.1 and GPT-6 Astra at S in coding and planning and wins the
coverage tie-break (AA Intelligence Index 56.0). Claude Code on the
claude.ai Max plan pays for it, $0 marginal while the weekly pool reads
`headroom`. Set Sonnet 5.5 at High, a raise over its Medium default.
Thinking stays On. The backup is GPT-6.1 Sol on Codex under ChatGPT Pro 5x
at Intelligence High, the cell `roadmodel backup` prints: it costs what
GPT-6 Sol does and beats it on the AA Intelligence Index at every effort,
and GPT-6 Astra is within noise of it at five times the price. New
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
       feature/phase03-step11-catalog`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - Hosted mode resolves only to hosted-safe or
      user-supplied candidates, checked here before any
      fetch and again in the provider (Step 4); a concept
      with no such candidate refuses with LicenceError naming
      the classes it found, never a quiet fallback to FRED.
    - A series-level licence decided by the source's own
      markers (FRED's copyright tags, the World Bank's
      License_Type, Eurostat's exceptions, Moody's as
      pre-approval) overrides the provider's class in every
      resolution.
    - Concept ids and transform names come from the catalog;
      user input selects among them and never reaches a
      provider unvalidated.
    - The docs build stays offline: the concept and source
      pages render from metadata only.
  </security>

  <context>
    pyeconomics. Phase 3. Step 11: semantic catalog and
    resolver.

    Current state (as of Phase 3 Step 10):

    - DataProvider.fetch_with_origin(query) returns
      Fetched(frame, origin, vintage); Fetched.source()
      builds the DataSource record (provider, series or table
      id, dataset, vintage label, observation window,
      retrieval time, licence, attribution, notice, terms
      page, llm_use, cache_hit, served_offline and the
      served_offline / cache_entry_discarded warning codes),
      and the resolver adds the concept, the field, the
      transforms and the fallback chain with
      dataclasses.replace. cache.memo() makes a repeat fetch
      within its block free even for a source that forbids
      storage; offline mode raises OfflineError for a miss,
      which the resolver reports or tries the next source on,
      and search, describe and vintages refuse to run offline.
    - The Phase 3 release provider set (30 ids if SEC is
      deferred, otherwise 31) is registered and passes the
      contract suite offline and live (yfinance on demand);
      each declares its class, terms, notices, llm_use, cache
      policy and capabilities; the sources with vintages are
      fred (ALFRED), fed_board (the SEP), nyfed (r* and term
      premia), philadelphia_fed (the Real-Time Data Set and
      the SPF), atlanta_fed (GDPNow) and cbo (each report);
      hosted mode refuses non-hosted-safe sources at fetch.
      data/_released.py has its providers section, empty
      until Step 19.
    - Nothing maps a concept to series yet, and nothing
      aligns frequencies; 0.2.x forward-filled quarterly NROU
      into monthly rows and dropped the rest silently.
    - The catalog must ship as Python modules (the wheel
      allowlist admits only .py files); concept ids are
      permanent once released (ADR-0011 decision 15).
    - ROADMAP §4 3.5's examples: us.inflation.pce_core.yoy,
      us.unemployment.rate, us.policy_rate.target_upper,
      us.treasury.par_curve and factors.ff5.us.monthly; a
      concept resolves to its originator in hosted mode (core
      PCE prices from BEA, unemployment from BLS, yields from
      Treasury, the effective federal funds rate from the New
      York Fed) and may resolve to FRED in library mode.

    Files to read (every file before drafting):
    - docs/adr/0011-data-platform.md (decisions 3, 5, 6, 7,
      15 and 16) and ROADMAP §4 3.5–3.7.
    - src/pyeconomics/data/ (types, terms, vintage, registry,
      _released.py, modes, providers/), tests/providers/, and
      src/pyeconomics/core/__init__.py and provenance.py.
    - This roadmap's Steps 13–17 (the bindings each model
      will declare) and the launch-catalog table.
    - docs/_ext/provider_pages.py, docs/data/keys.md,
      docs/index.md and docs/conf.py.

    Step 10 integration: the four unblocked rates/identifier providers
    and ten finance providers are delivered without SEC. Exact query
    ids, native units, file-update semantics and source restrictions
    are documented in docs/data/research-finance.md. OpenFIGI returns
    Records rather than binding inputs. Damodaran requires an explicit
    country/industry category and has no invented as-of history. Coin
    Metrics declares ProviderInfo.never_paid=True; retain this flag
    for the paid-feature gate. Yahoo remains off until explicit TOML
    or configure(enable_yfinance=True) opt-in and never runs live in CI.
  </context>

  <goal>
    Every concept Steps 13–17 bind resolves in library mode,
    and in hosted mode wherever an originator publishes it;
    transforms and frequency alignment are explicit and
    recorded; the resolver's choice and the chain it tried
    are in every DataSource record; pyeconomics.data.get and
    its siblings work on concepts and on provider series; and
    the documentation preview shows the guide, the sources
    and the concepts.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Concepts (data/catalog/): one module per topic; each
      Concept has an id (decision 15's grammar), a title, a
      definition in our own words, the unit kind, frequency
      and seasonal adjustment it guarantees, and candidates
      in fallback order — originator first, then a
      library-only aggregator on the user's key, with a
      placeholder for Phase 6's premium sources — each a
      provider, a series key and the transforms that make it
      match the definition exactly (ROADMAP §4 6.5: fail over
      only between identical definitions). A derived concept
      (an output gap from real and potential GDP) declares
      its formula over other concepts. Ids are validated at
      import, and a test lists every concept and checks each
      candidate's provider is registered.
    </requirement>

    <requirement>
      Released concepts: add the concepts section to
      data/_released.py beside Step 4's providers section,
      empty until Step 19 fills it, and a
      pyeconomics.data.registry.validate() rule (slug
      released-concept) that reports a released concept id
      missing from the installed catalog, so a concept id,
      once released, cannot be renamed or removed (ADR-0011
      decision 15). A toy ledger entry proves the rule.
    </requirement>

    <requirement>
      The minimum concept set, each with its originator and
      FRED (or other library) candidates where they exist: US
      PCE and core PCE prices, CPI and core CPI (levels and
      year-over-year), the Dallas Fed trimmed-mean PCE
      (library-only, with no originator provider, so hosted
      mode refuses it), the unemployment rate, CBO's
      noncyclical rate, real and potential GDP and the CBO
      output gap, nominal GDP growth, the effective federal
      funds rate, the target range (with the 2008-12-16
      switch from a target to a range recorded), Treasury
      3-month and 10-year nominal and 10-year real yields,
      the par curves, the GSW parameters, the LW and HLW r*
      estimates, the SEP medians, the SPF medians by horizon,
      federal debt to GDP and the average interest rate on
      federal debt, the primary balance, Penn World Table
      series by economy, the Ken French factor and portfolio
      sets (factors.ff3, ff5 and momentum; the 25 and
      industry portfolios; monthly and daily), Shiller's and
      Damodaran's market series, and euro-area, UK and
      Canadian inflation, policy rates and output gaps
      through ECB, Eurostat, OECD and BIS. Add others only
      when a later step binds them.
    </requirement>

    <requirement>
      Transform names (src/pyeconomics/core/transforms.py):
      the names and parameter schemas of every transform, as
      plain data with no implementation, so Step 12's
      validate() can check a binding's transform without core
      importing the data layer; exported from
      pyeconomics.core. A test asserts the names
      catalog/transforms.py implements equal the names core
      declares, in both directions. The names are pct_change,
      yoy, diff, log, changes_only (the dates a step series
      moved), ratio and add (two concepts, the primary balance
      needs the sum), convert, align_to, asof, period and
      window; the text form is `name` or `name(key=value,
      ...)` with one canonical spelling.
    </requirement>

    <requirement>
      Transforms and alignment (catalog/transforms.py): each
      transform is a named, pure function on a Series with
      its parameters recorded in the DataSource record;
      frequency conversion takes an explicit method (mean,
      sum, first, last, period end) and never fills;
      alignment for a binding is explicit: the last
      observation on or before a date, one period's value,
      or a window of N observations, each refusing with a
      clear error when the data cannot satisfy it — never a
      silent forward-fill.
    </requirement>

    <requirement>
      Resolver (data/resolver.py): resolve(concept, *, start,
      end, as_of, vintage, mode, strict=False) walks the
      candidates, skipping one whose class the mode refuses,
      whose provider's extra is missing, whose key is absent
      (has_key), or which cannot honour the requested vintage,
      and records why each was skipped; strict=True tries
      only the first. The result is a Series or Table whose
      DataSource records carry the concept, the provider and
      series, the transforms, the vintage and the chain
      tried. Library mode prefers a vintage-keeping candidate
      when a vintage is requested.
    </requirement>

    <requirement>
      Public API (pyeconomics.data): get(concept_or_series,
      *, start=None, end=None, as_of=None, vintage=None,
      provider=None, mode=None), search(text, limit=20) over
      concepts and providers' series, describe(...),
      vintages(...) and sources() (the providers with their
      classes and notices). A provider series is addressed as
      `<provider>:<series key>`. Phase 4's `pyeconomics data
      search|get|vintages` will wrap these unchanged.
    </requirement>

    <requirement>
      Tests (tests/data/catalog/), offline through
      ReplayTransport: every concept resolves in library
      mode with the cassettes recorded in Steps 6–10; hosted
      mode resolves the originator or refuses (one test per
      class); a missing key, a missing extra and an
      unsatisfiable vintage each fall to the next candidate
      and are recorded; strict=True does not fall back;
      every transform and alignment rule against hand
      computations; a property test that converting monthly
      to quarterly by mean and back by period end never
      invents a value; series-level licence overrides.
    </requirement>

    <requirement>
      Documentation: docs/data/index.md, "Data sources and
      keys" (fetching data, concepts and provider series,
      licence classes and what each allows, hosted versus
      library mode, attribution and required notices, keys,
      the cache and offline mode), linked from the index; a
      generated sources summary (each provider's class,
      notice and key, from metadata); and
      docs/_ext/concept_pages.py generating one page per
      concept with its definition and candidates by mode.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added"; filepath comment on
      every new Python file.
    </requirement>
  </requirements>
</task>
```

### Step 11 acceptance criteria

- Every concept in the minimum set resolves offline in library mode, and
  in hosted mode resolves to an originator or refuses with `LicenceError`
  naming the classes it found; the trimmed-mean PCE refuses in hosted
  mode.
- Fallback skips a candidate for a refused class, a missing extra, a
  missing key or an unsatisfiable vintage, records why, and stops at the
  first candidate under `strict=True`.
- Transforms and alignment rules match hand computations, never fill a
  gap, and record their parameters in each `DataSource`; the transform
  names in `pyeconomics.core.transforms` equal the catalog's
  implementations.
- `data/_released.py` has its concepts section, and the `released-concept`
  rule reports a released concept missing from the catalog.
- `pyeconomics.data.get`, `search`, `describe`, `vintages` and `sources`
  work on concepts and on `<provider>:<series key>` addresses.
- The data guide, the sources summary and the concept pages build with
  warnings as errors and without the network.
- **Deployed & verified:** after merge, the Read the Docs API reports the
  `main` version's latest build succeeded at the merge commit,
  `/en/main/data/` serves the guide with a link to every provider's page,
  a concept page shows its candidates by mode, and `/en/stable/` still
  serves 0.2.6.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and hosted mode cannot resolve any source
  but a hosted-safe or user-supplied one (tested per class).

---

## Step 12 — Live Bindings and Vintage-Aware Runs ✅

**Status:** Complete — PR #132 (2026-10-18)

> **Goal:** Connect the data layer to the model registry without making a single
> model impure. Add `src/pyeconomics/core/binding.py` (`Binding`, its as-of
> rules and vintage policies — declarations only, importable by models); give
> `@model` a `bindings` parameter and replace `validate()`'s "must be empty"
> rule with structural binding rules; add `pyeconomics.bind()` (resolution in
> the data layer, returning a `Bound` — defined in core beside `DataSource` — of
> input values and their records) and let `pyeconomics.run()` take a `Bound`;
> move the manifest to schema 2 with typed `data_sources` and narrow its
> determinism claim to identical inputs and identical data-source records; add a
> `bindings` key to `describe()`, a "Data" section to the model card,
> `Result.attributions()` for exports, and `--bound` to `scripts/new_model.py`;
> prove the mechanism end to end on toy models over toy providers, real-time
> vintages by default and revised data as a labelled option; extend the canary
> suite to bound manifests; and narrow the Phase 2 tests the Cross-phase
> verification rule lists. Parent: ROADMAP §3; §4 3.6 (its first bullet);
> ADR-0011 decisions 6 and 16.

**Branch:** `feature/phase03-step12-bindings`

**Deploys:** nothing beyond merge.

| Setting      | Value                                         |
| ------------ | --------------------------------------------- |
| Model        | Claude Sonnet 5.5                             |
| Backup       | GPT-6.1 Sol — Codex · Intelligence XHigh      |
| Platform     | Claude Code                                   |
| Effort       | Extra High                                    |
| Thinking     | On                                            |
| Conversation | **New**                                       |

**Model rationale:** Coding is PRIMARY and planning SECONDARY: the step
changes the core contract Phase 2 fixed — `ModelSpec`, `validate()`, the
runner, the manifest, `describe()` and the card — and connects it to the
data layer, so a design flaw here reaches every surface Phases 4 and 5
generate. Complexity is High, and a novel API across many files with a
determinism property to preserve is the ladder's Extra High condition. High
requires S in coding; Sonnet 5.5 ties Opus 5.5, Fable 5.1 and GPT-6 Astra at
S in coding and planning and wins the coverage tie-break (AA Intelligence
Index 56.0). Claude Code on the claude.ai Max plan pays for it, $0 marginal
while the weekly pool reads `headroom`. Set Sonnet 5.5 at Extra High, a
raise over its Medium default, and not Max, because ADR-0011 decision 16
fixes the design. Thinking stays On. The backup is GPT-6.1 Sol on Codex
under ChatGPT Pro 5x at Intelligence XHigh, the cell `roadmodel backup`
prints: it costs what GPT-6 Sol does and beats it on the AA Intelligence
Index at every effort, and GPT-6 Astra is within noise of it at five times
the price. New conversation per phase-boundary hygiene.

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
       feature/phase03-step12-bindings`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - Models stay pure: Binding is data in pyeconomics.core;
      resolution happens in pyeconomics.data before compute
      runs; model-purity and the import allowlist pass with
      no change for models/.
    - Manifest schema 2's data_sources records hold no URL,
      path, host, key or contact; the canary suite runs a
      bound run with a canary key and finds it in no manifest,
      export or log.
    - A Bound records whether each value was revised data;
      nothing passes revised data off as real-time.
  </security>

  <context>
    pyeconomics. Phase 3. Step 12: live bindings and
    vintage-aware runs.

    Current state (as of Phase 3 Step 11):

    - ModelSpec.bindings is a reserved, empty
      tuple[object, ...]; the bindings rule rejects any
      value; @model has no bindings parameter; run() takes a
      model id, an input object or mapping, or keyword
      fields; Manifest is schema 1 with data_sources = () and
      a docstring promising no clock "and none is ever
      added"; Manifest.create takes no data sources;
      describe() has 22 DESCRIPTION_KEYS; the card has no
      data section.
    - Tests pinning that state (Cross-phase verification
      rule): tests/registry/test_spec.py and
      test_validate_rules.py (bindings),
      tests/results/test_manifest.py (schema 1, empty
      data_sources, no `date` or `time` key, no `:` in a
      value), tests/results/test_runner.py (an empty
      data_sources) and tests/results/test_cards.py
      (DESCRIPTION_KEYS).
    - pyeconomics.core already holds the provenance record
      (provenance.py: DataSource, RealtimePeriod,
      LicenceClass, LlmUse; Step 2) and the transform names
      (transforms.py; Step 11), so core can type and check
      bindings and records without importing the data layer.
    - A frame's metadata carries notes (Step 6): each a
      snake_case code and a detail. BEA's frames note
      revised_data (its API serves only current estimates),
      BLS's keyless frames bls_keyless, footnotes and FRED's
      copyright status are notes too. Fetched.source() does
      not yet copy note codes into DataSource.warnings: this
      step decides which codes become warnings (revised_data
      at least) and copies them there.
    - pyeconomics.data resolves concepts (Step 11) with
      vintages, transforms, alignment and DataSource records,
      and its public get() works offline through
      ReplayTransport. bind() wraps its fetches in
      pyeconomics.data.cache.memo(), takes each record from
      Fetched.source() so cache_hit, served_offline and the
      original retrieval time reach the manifest, and lets
      OfflineError propagate when offline mode has no cached
      answer.
    - result_sha256 covers {inputs, model_id, model_version,
      outputs, warnings} and not the manifest; inputs_sha256
      covers the inputs; tables.py stores the manifest under
      the Arrow schema key "pyeconomics.manifest".

    Files to read (every file before drafting):
    - docs/adr/0011-data-platform.md (decisions 1, 6 and 16)
      and this roadmap's data contract and Cross-phase
      verification rule.
    - src/pyeconomics/core/spec.py, model.py, _rules.py,
      runner.py, results.py, manifest.py, describe.py,
      cards.py and tables.py, and scripts/new_model.py.
    - src/pyeconomics/core/provenance.py and transforms.py,
      src/pyeconomics/data/ (resolver, catalog, vintage) and
      tests/data/leakcheck.py.
    - The tests named above, tests/registry/toy_models.py and
      tests/contract.py.

    Step 11 integration (as built): data.resolve(concept, *,
    start, end, as_of, vintage, mode, strict, provider,
    parameters, max_observations, transport, registry) returns
    a Resolved(frame, sources, concept, skipped): one DataSource
    per source read (a derived concept has one per operand, each
    naming the derived concept and ending its transforms with
    the combining transform), and a Skip(provider, series,
    reason, detail, licence) for each candidate passed over, the
    reason one of data.resolver.REASONS and recorded in the
    record's warnings as skipped_<provider>_<reason>. A
    DataSource carries the concept, the canonical transform
    texts, the vintage label, the real-time period of the last
    row, the window and the fallback_chain; its `field` is None,
    for bind() to set with dataclasses.replace. A concept that
    needs a window (Treasury curves) or a parameter (the SEP
    `meeting`) says so (Concept.needs_window, .parameters); bind
    passes parameters= through. The resolver fails over only
    between answers that match the concept's frequency, seasonal
    adjustment and unit kind (a decimal kind must be known
    exactly), skips a candidate that cannot honour the vintage
    (so a LATEST policy passes vintage="latest" itself and adds
    revised_data), and applies the explicit mode to a series'
    own terms. get/search/describe/vintages/sources are in
    data/api.py. The frame's `notes` are untouched: copying
    revised_data and the others into DataSource.warnings is this
    step's.
  </context>

  <goal>
    A model declares bindings; validate() checks them;
    pyeconomics.bind() resolves them as of a date on
    real-time vintages by default; pyeconomics.run() runs the
    result and records every series, vintage and retrieval
    time in a schema-2 manifest; describe() and the card show
    each model's data; and every Phase 2 contract test is
    narrowed, not deleted, with the whole catalog still green.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      core/binding.py: Binding(field, concept, transform=None,
      as_of=AsOf.LAST_ON_OR_BEFORE, window=None,
      vintage=VintagePolicy.REAL_TIME, profile="default"),
      frozen, with AsOf (last on or before the date, one
      period's value, a window of N observations for an array
      field) and VintagePolicy (REAL_TIME, the default;
      LATEST, which is revised data and labelled so). A
      profile names one complete set of bindings — realized
      data, a forecast source, another economy — so one model
      can be bound several documented ways. Bound, in the
      same module, is frozen: the bound values by field, the
      profile, and one DataSource per binding, plus the
      overrides recorded as user-supplied; run() accepts it
      without core importing the data layer. Both exported
      from pyeconomics.core. ModelSpec.bindings becomes
      tuple[Binding, ...] and @model takes bindings=().
    </requirement>

    <requirement>
      validate(): the bindings rule now reports a binding
      whose field does not exist, is bound twice in one
      profile, or whose kind cannot take it (a scalar field
      for a window, an array field without one); a model
      with bindings but no "default" profile; a concept id
      that breaks decision 15's grammar; and a transform
      name pyeconomics.core.transforms does not declare, or
      parameters its schema refuses. Whether a concept
      exists in the installed catalog is checked by
      pyeconomics.data.validate_bindings() and a test over
      the registry, because core never imports the data
      layer. Add toy specs for every new problem under the
      bindings slug.
    </requirement>

    <requirement>
      pyeconomics.bind(model_id, /, *, as_of=None,
      vintage=None, mode=None, profile="default",
      concepts=None, **overrides) -> Bound: resolves the
      profile's bindings through the catalog as of the date
      (today's latest data when as_of is None), applies each
      transform and as-of rule, converts to the field's unit,
      and returns the values with one DataSource per binding;
      concepts={field: concept} rebinds a field to another
      concept of the same unit kind and frequency (refused
      otherwise); an override replaces a bound value and is
      recorded as user-supplied. Exported from pyeconomics.
      run(model_id, bound) and run_model accept a Bound as
      their inputs, and the Result's manifest carries its
      records; a Bound with revised data adds the
      revised_data warning code to the result.
    </requirement>

    <requirement>
      Manifest schema 2 (core/manifest.py):
      MANIFEST_SCHEMA_VERSION = 2; data_sources is a tuple of
      DataSource records in canonical form, sorted by field;
      Manifest.create takes data_sources; the docstring's
      promise becomes "no clock of the run, host, user, path
      or environment value; a data source's retrieval time is
      a fact about the data, recorded where it was fetched";
      result_sha256's definition is unchanged, so identical
      bound values give identical result hashes; two runs on
      identical inputs and data-source records give identical
      manifest bytes. tables.py and every export carry the
      new manifest unchanged.
    </requirement>

    <requirement>
      Describe and cards: describe() gains a bindings key
      (field, concept, transform, as-of rule, vintage policy)
      in a fixed position; the card gains a "Data" section
      listing each binding's concept and the classes and
      notices of its candidates; Result.attributions()
      returns the de-duplicated attribution and required
      notices of the data a result read, which Phase 4's
      exports will print. The model-page extension renders
      the new section.
    </requirement>

    <requirement>
      scripts/new_model.py gains --bound, which scaffolds one
      example Binding on a catalog concept and a bound
      example; its test covers the option.
    </requirement>

    <requirement>
      Tests: toy models with bindings over the toy providers
      and synthetic cassettes, run offline: a real-time bind
      as of a past date reads the vintage published by then;
      LATEST reads revised data and warns; an override is
      recorded; a binding whose concept cannot be satisfied
      raises with the concept named; schema-2 manifests are
      deterministic; the canary suite on a bound run. Narrow,
      never delete, the Phase 2 tests the Cross-phase rule
      lists, each to the invariant it protected (schema
      version, field set, no run clock, no path or
      environment value), and note each in the PR body.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased]: "Added" for bindings, bind() and
      the Data card section; "Changed" for manifest schema 2
      (a breaking change for anyone parsing manifests,
      recorded under its own heading in the release notes
      Step 19 writes).
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header.
    </requirement>
  </requirements>
</task>
```

### Step 12 acceptance criteria

- `Binding` lives in `pyeconomics.core`, `@model` accepts `bindings`, and
  `validate()` reports every structural binding problem under the
  `bindings` slug, each shown by a toy spec; the whole catalog still
  validates.
- `pyeconomics.bind()` resolves a toy model's bindings as of a past date on
  real-time vintages, `VintagePolicy.LATEST` reads revised data with the
  `revised_data` warning, and an override is recorded as user-supplied.
- `pyeconomics.run(model_id, bound)` records one `DataSource` per binding
  in a schema-2 manifest; identical inputs and records give identical
  manifest bytes and identical `result_sha256`.
- `describe()` carries `bindings`, the card's "Data" section renders on
  the documentation preview, `Result.attributions()` lists every notice,
  and `scripts/new_model.py --bound` scaffolds a bound model.
- The Phase 2 tests the Cross-phase verification rule lists are narrowed,
  none deleted; the full suite and the coverage floors pass on all twelve
  CI cells, and both earlier verifiers pass in `phase-verify.yml`.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — models stay pure (model-purity and the
  import allowlist unchanged for `models/`), and a bound run's manifest,
  exports and logs hold no key (canary).

---

## Step 13 — Monetary-Policy Suite ✅

**Status:** Complete — PR #140 (2026-10-19)

> **Goal:** Rebuild 0.2.x's four FRED-bound rules as the project's flagship: a
> cited, vintage-aware family that reproduces the Federal Reserve's own
> reference figures. Add `src/pyeconomics/models/macro/` with
> `macro.policy_rule` (a union on `calculation`: Taylor 1993 and 1999, the
> balanced approach with and without shortfalls, the ELB-adjusted Taylor 1993
> rule and the first-difference rule, each with optional smoothing (the inertial
> form) and an effective lower bound, a resource gap measured as an output gap
> or an Okun-scaled unemployment gap, and a `path` calculation over forecast
> horizons) and `macro.neutral_rate` (r* from the published Laubach-Williams and
> Holston-Laubach-Williams estimates, the SEP's longer-run rate, or a constant),
> with binding profiles for realized US data (an Okun-scaled unemployment gap or
> CBO's output gap), the FOMC's SEP, the SPF, and the euro area, the United
> Kingdom and Canada; the `macro` entry point; golden files citing the Board's
> Monetary Policy Report formulas, the Atlanta Fed's Taylor Rule Utility and the
> Cleveland Fed's simple monetary policy rules; a parity test over every 0.2.x
> characterization fixture, with each intentional difference documented beside
> the test that allows it; real-time evaluation on ALFRED vintages by default,
> revised data as a labelled option; and a fan chart from SPF and CBO inputs.
> Parent: ROADMAP §4 3.6; `tests/fixtures/legacy/README.md` "The Phase 3
> contract"; ADR-0011 decision 16.

**Branch:** `feature/phase03-step13-policy-rules`

**Deploys:** nothing beyond merge.

| Setting      | Cost                                    | Balanced                                 | Quality                                  |
| ------------ | --------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| Model        | GPT-6.1 Sol                             | Opus 5.5                                 | Opus 5.5                                 |
| Backup       | Sonnet 5.5 — Claude Code · Effort XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh |
| Platform     | Codex                                   | Claude Code                              | Claude Code                              |
| Effort       | Intelligence High                       | Effort High                              | Effort XHigh                             |
| Thinking     | —                                       | On                                       | On                                       |
| Conversation | **New**                                 | **New**                                  | **New**                                  |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

> Settings updated 2026-10-18 (refresh): was Claude Opus 5.5 · Extra High.
> Coding PRIMARY, knowledge SECONDARY, High, not novel. The ladder's Balanced
> column is Opus 5.5 at High; the Quality column (XHigh) is the raise if the
> verification burden or a tight pool says so.

> Ran 2026-10-19: Balanced — Claude Opus 5.5 on Claude Code (effort as the
> operator set it). The **Runs:** column; the Claude weekly pool's `tight` row
> had passed its reset, so it read as headroom.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY; complexity is High and the step is not novel (the methods are published and oracles check them). The ladder's Balanced column runs: Claude Opus 5.5 on Claude Code at High, backup GPT-6.1 Sol. The Cost and Quality columns, and the Backup under a tight or exhausted pool, are read off the table on the day. New conversation per phase-boundary hygiene.

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
       feature/phase03-step13-policy-rules`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - The models stay pure: model-purity and the import
      allowlist pass on src/pyeconomics/models/macro/ with no
      suppression; dates are inputs or binding as-of dates,
      never "today".
    - Golden files keep only the published values each case
      needs, cited by publication, table or file, row and
      access date; no dataset from a library-only source is
      committed, and the legacy fixtures are read, never
      edited.
    - Every array input (forecast paths) has a maximum
      length.
  </security>

  <context>
    pyeconomics. Phase 3. Step 13: the monetary-policy suite.

    Current state (as of Phase 3 Step 12):

    - Models can declare bindings with profiles;
      pyeconomics.bind() resolves them through the catalog
      on real-time vintages by default; run() records every
      series, vintage and retrieval time in a schema-2
      manifest; the catalog holds the US inflation, labour,
      output, policy-rate, Treasury, r*, SEP and SPF
      concepts and the euro-area, UK and Canadian inputs.
    - Step 12 as built: bind(model_id, /, *, as_of, vintage,
      mode, profile, concepts, parameters, **overrides)
      returns a Bound (run(model_id, bound) takes it); a
      concept's parameters (the SEP `meeting`) go in
      `parameters={"meeting": ...}` and nothing guesses them;
      an override of a bound field is recorded as
      user-supplied and a plain input is carried unrecorded.
      A binding reads a SERIES concept: a table concept is
      refused, so us.sep.medians (a table), the Treasury curves
      and the factor sets cannot be bound, and this step adds
      the series concepts its us_sep profile reads (ids are
      permanent: dotted snake_case of three or four parts).
      Binding.transform is one more one-series
      transform before the as-of rule; AsOf.PERIOD reads past
      the date because a period is dated by its last day. A
      date with nothing published raises; a source usable in
      the mode that keeps no vintages is read as revised data
      with the revised_data warning. The toy bound models and
      scripted providers are tests/data/bindings/bound_support.py;
      `scripts/new_model.py <id> --bound` scaffolds a bound model.
    - No macro package, entry point or golden directory
      exists; the registry holds Phase 2's 32 ids;
      tests/models/test_registry_is_not_empty.py pins
      exactly those 32 and tests/registry/
      test_released_ledger.py asserts len(RELEASED) == 32 and
      that the ledger equals registry.ids(), which the first
      new id breaks.
    - tests/fixtures/legacy/ (read its README): taylor_rule
      (1,040 cases), balanced_approach_rule and its
      shortfalls variant (960 each), first_difference_rule
      (1,040), the combined estimates (48), a synthetic
      monthly panel and four historical tables plus their
      combination, each in two configurations. 0.2.x
      parameters: alpha, beta, okun_factor, inflation_target,
      rho (inertia in every rule) and elb with apply_elb;
      values in percent rounded to two decimals; historical
      tables forward-filled quarterly NROU and cut DFII10 to
      its coverage; the target splices DFEDTAR and DFEDTARU at
      2008-12-15. The 0.2.x source is on the legacy/0.2.x
      branch, which a fresh clone has only as a remote branch
      (`git show origin/legacy/0.2.x:<path>` with
      MSYS_NO_PATHCONV=1 in Git Bash).
    - Reference figures: the Board's Monetary Policy Report
      sets out the Taylor (1993), balanced-approach (with and
      without shortfalls), adjusted Taylor (1993) and
      first-difference rules in a recurring box; the Atlanta
      Fed's Taylor Rule Utility publishes prescriptions with
      the inputs it used, updated with its release calendar;
      the Cleveland Fed's simple monetary policy rules page
      publishes quarterly prescriptions from seven rules on
      SPF, CBO and its own BVAR forecasts, with a
      spreadsheet. Each is read at kickoff and cited by
      edition, table and access date.

    Files to read (every file before drafting):
    - docs/roadmap/ROADMAP.md §4 3.6 and this roadmap's
      Overview (launch-catalog table, Citation rule).
    - tests/fixtures/legacy/README.md, manifest.json and one
      case of each fixture file; the 0.2.x rule modules and
      data/economic_indicators.py on origin/legacy/0.2.x.
    - src/pyeconomics/core/binding.py, spec.py and the toy
      bound models; src/pyeconomics/data/catalog/ (the
      concepts this step binds) and resolver.py.
    - src/pyeconomics/models/fixed_income/ (a recent
      domain's layout), tests/golden/README.md and
      tests/contract.py.
    - The Monetary Policy Report box, the Atlanta Fed's
      Taylor Rule Utility and the Cleveland Fed's simple
      monetary policy rules page and spreadsheet.

    Step 11 concept ids (as built) for the profiles: us.inflation.
    pce_core.yoy, us.unemployment.rate, us.unemployment.
    noncyclical_rate, us.neutral_rate.hlw (and .laubach_williams),
    us.policy_rate.effective, .target_upper and .target_lower,
    us.output_gap.cbo and us.output_gap.real_potential, the SEP
    as us.sep.medians and us.sep.policy_rate_longer_run (both take
    the `meeting` parameter: nothing guesses the latest meeting),
    the SPF as us.spf.<cpi|core_cpi|pce|core_pce|unemployment>.
    median_h0..h4 (survey quarter to four quarters ahead) and
    us.spf.<cpi|pce>.median_10y, and ea/gb/ca inflation
    (<economy>.inflation.<hicp|cpi>.yoy), policy rates
    (<economy>.policy_rate.headline), output gaps
    (<economy>.output_gap.oecd) and ea/ca neutral_rate.hlw. No
    gb r* exists: use a constant.
  </context>

  <goal>
    macro.policy_rule and macro.neutral_rate are registered
    through the macro entry point and pass validate(), their
    golden, property, contract and parity tests; bound runs
    reproduce the Atlanta and Cleveland Fed figures within
    documented tolerances; real-time evaluation is the
    default; every 0.2.x fixture matches or has a documented
    difference; and their pages render in the docs preview.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Package, entry point and registry pins:
      src/pyeconomics/models/macro/ with one module per entry
      and an __init__.py whose __all__ lists both Models;
      `macro = "pyeconomics.models.macro"` in the entry-point
      table. Narrow (Cross-phase verification rule) the
      registry-not-empty test to "at least Phase 2's 32 ids
      and every id of this roadmap's table that has landed",
      reading both roadmaps' tables, and the ledger test to
      "every released id is registered; registered ids not
      yet released are allowed until Step 19".
      scripts/smoke.py needs no change: it runs registered
      models' own examples (one model per domain, every
      model with --all), so the macro models join it, and
      the domain count it reports, as they register.
    </requirement>

    <requirement>
      macro.policy_rule — a union on calculation:
      taylor_1993, taylor_1999, balanced_approach,
      balanced_approach_shortfalls, adjusted_taylor_1993 and
      first_difference, as the Monetary Policy Report and the
      original papers define them, every rate a decimal.
      Shared inputs: inflation, inflation_target (default
      0.02), neutral_real_rate, the resource gap as an output
      gap or as unemployment and its natural rate with an
      Okun coefficient (a gap_measure field with a
      model_validator), weights that default to each rule's
      published values and may be overridden (0.2.x's alpha
      and beta), smoothing (rho, 0 to 1, with the previous
      policy rate: the inertial form), and an optional
      effective lower bound. first_difference takes the
      previous rate and the gap four quarters earlier;
      adjusted_taylor_1993 takes the cumulative shortfall it
      makes up. A seventh calculation, path, names one of the
      six rules and takes bounded arrays of its inputs by
      forecast horizon, returning the prescribed path.
      Outputs of the six: the prescribed rate, the
      unconstrained rate, the inflation-gap and resource-gap
      terms and the implied nominal neutral rate, with an
      elb_binding warning code. Evidence practitioner.
      Invariants at least:
      prescription_never_falls_as_inflation_rises,
      prescription_never_rises_with_unemployment,
      smoothing_zero_is_the_plain_rule,
      elb_floors_the_prescription and
      shortfalls_rule_never_exceeds_balanced_approach.
    </requirement>

    <requirement>
      macro.neutral_rate — a union on calculation:
      laubach_williams and holston_laubach_williams (the New
      York Fed's published estimate for the economy and
      quarter, bound with the file release as its vintage),
      sep_longer_run (the SEP's longer-run federal funds
      median less the longer-run inflation objective) and
      constant; outputs the real neutral rate and the nominal
      neutral rate (plus the inflation target), and the real
      policy-rate gap when a policy rate and inflation are
      given. Evidence contested (ROADMAP §5 names r*
      estimates as the example).
    </requirement>

    <requirement>
      Bindings and profiles (ADR-0011 decision 16):
      policy_rule's default profile binds core PCE inflation,
      the unemployment rate and CBO's noncyclical rate, the
      HLW r* and the effective federal funds rate, with the
      gap as Okun-scaled unemployment; profile us_output_gap
      binds the same inputs but the CBO output gap (real
      against potential GDP) for the gap; profile us_sep binds
      series concepts for the SEP medians this step adds to the
      catalog (a binding reads a series, and us.sep.medians is a
      table) and the longer-run rate; us_spf the SPF
      medians; ea, gb and ca bind each economy's inflation,
      gap, r* where the New York Fed publishes one (a constant
      otherwise) and policy rate through ECB, Eurostat, OECD
      and BIS concepts. Real-time vintages are the default;
      the result of a LATEST bind carries revised_data.
      Document every profile on the card.
    </requirement>

    <requirement>
      Golden files (tests/golden/macro/), at least three
      cited cases each with an edge case: identity cases from
      the Monetary Policy Report's formulas with round inputs
      (kind identity, the box cited by edition); Atlanta Fed
      Taylor Rule Utility prescriptions with the inputs and
      settings it states (kind official, cited by page,
      settings and access date, at its published precision);
      Cleveland Fed simple-rule prescriptions with their SPF
      and CBO inputs (kind official, edition, table and row);
      for neutral_rate, published LW and HLW estimates (kind
      official, file, sheet, row and access date) and the
      identity nominal = real + target. Edge cases: an ELB
      that binds, negative inflation, a zero gap.
    </requirement>

    <requirement>
      Legacy parity (tests/models/macro/test_legacy_parity.py):
      load every fixture, map each case's inputs and
      parameters onto policy_rule (percent to decimal through
      percent_to_decimal; alpha, beta and okun_factor onto the
      weights and the Okun coefficient; rho onto smoothing;
      elb with apply_elb onto the lower bound), run it, and
      compare after converting back and rounding to two
      decimals; reproduce the historical tables by binding
      the synthetic panel's series with explicit alignment
      (the last observation on or before each date in place
      of a silent forward-fill). Every case matches, or falls
      under a named difference recorded beside the test with
      its reason (for example: results are no longer rounded;
      alignment is explicit), and the PR body tabulates the
      counts per difference.
    </requirement>

    <requirement>
      Real-time evaluation: an offline test binds the default
      profile as of a past date on synthetic ALFRED-shaped
      cassettes and checks the real-time period of each
      DataSource whose source keeps vintages covers that date,
      and that the rest carry revised_data (the New York Fed's
      r* and funds rate keep none, and ALFRED keeps none of
      FRED's daily EFFR); a live test (marked live, run by the
      weekly run with the FRED key) runs the Taylor (1993)
      rule for a past date on ALFRED vintages and checks the
      manifest records the vintages and that a LATEST run of
      the same date differs and warns.
    </requirement>

    <requirement>
      Fan chart: a ChartSpec drawing path outputs for the SPF
      median and interquartile forecasts or CBO's
      projections; if ChartKind lacks a band, add the
      smallest one (Contract-change rule). Property tests
      cover path's agreement with the scalar rules.
    </requirement>

    <requirement>
      Every model: ModelSpec complete (cost class, examples,
      invariants, changelog at version 1), invariant-marked
      property tests, contract.check_model with 1,500
      examples, and an independent reviewer of the diff
      before the PR (Phase 2 Step 6's practice).
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entries naming both
      models; the PR body lists every golden source and the
      legacy-difference counts. Filepath comment and
      three-line header on every new Python file; golden
      TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 13 acceptance criteria

- `macro.policy_rule` and `macro.neutral_rate` are registered through the
  `macro` entry point, `registry.validate()` passes in CI, and the
  narrowed registry and ledger tests accept the new unreleased ids.
- Each has a golden file with at least three cited cases including an edge
  case; the Atlanta Fed and Cleveland Fed cases reproduce their published
  prescriptions within documented tolerances at the stated inputs.
- Every 0.2.x characterization case matches after percent conversion and
  rounding, or falls under a named, reasoned difference beside the parity
  test; the PR body tabulates the counts.
- A bound run as of a past date reads real-time vintages by default and
  records them in its manifest; a `LATEST` run warns `revised_data` (both
  offline; the live variant is in the weekly run).
- Every declared invariant has a passing property test, the contract suite
  fuzzes both models without an undocumented error, the coverage floors
  hold, and the docs preview renders both pages with their profiles.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the purity guards pass on
  `models/macro/`, and golden files hold only cited published values.

---

## Step 14 — Launch Catalog: Macroeconomics ✅

**Status:** Complete — PR #144 (2026-10-19)

> **Goal:** Register the six remaining macro entries on the patterns Step 13
> proved. Add `macro.output_gap` (from potential output, or by the HP,
> Hamilton, Baxter-King and Christiano-Fitzgerald filters),
> `macro.phillips_curve` (an expectations-augmented estimator),
> `macro.okun_law` (gap and first-difference estimators),
> `macro.solow_growth` (the Solow steady state and growth accounting),
> `macro.debt_dynamics` (the debt-ratio path, r − g and the
> debt-stabilizing primary balance) and `macro.recession_probability` (the
> New York Fed's yield-curve probit) to `src/pyeconomics/models/macro/`,
> each with bindings to the catalog's concepts; add `core/regression.py`, a
> shared native least-squares helper with classical, HC1 and Newey-West
> standard errors that Step 16 reuses; golden files citing official
> releases, papers and identities; property tests for every invariant; and
> oracle tests against statsmodels' filters and regressions and QuantEcon's
> Hamilton filter. Parent: ROADMAP §4 3.7 (`macro`).

**Branch:** `feature/phase03-step14-macro`

**Deploys:** nothing beyond merge.

| Setting      | Cost                                    | Balanced                                 | Quality                                  |
| ------------ | --------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| Model        | GPT-6.1 Sol                             | Opus 5.5                                 | Opus 5.5                                 |
| Backup       | Sonnet 5.5 — Claude Code · Effort XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh |
| Platform     | Codex                                   | Claude Code                              | Claude Code                              |
| Effort       | Intelligence High                       | Effort High                              | Effort XHigh                             |
| Thinking     | —                                       | On                                       | On                                       |
| Conversation | **New**                                 | **New**                                  | **New**                                  |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

> Settings updated 2026-10-18 (refresh): was Claude Opus 5.5 · Effort High.
> Model and effort unchanged (Balanced column); the single-column table
> becomes the full ladder, and the backup is now GPT-6.1 Sol at Intelligence
> XHigh.

> Ran 2026-10-19: Balanced — Claude Opus 5.5 on Claude Code (effort as the
> operator set it). The **Runs:** column; the Claude weekly pool's `tight` row
> had passed its reset, so it read as headroom.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY; complexity is High and the step is not novel (the methods are published and oracles check them). The ladder's Balanced column runs: Claude Opus 5.5 on Claude Code at High, backup GPT-6.1 Sol. The Cost and Quality columns, and the Backup under a tight or exhausted pool, are read off the table on the day. New conversation per phase-boundary hygiene.

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
       feature/phase03-step14-macro`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
    - The purity guards pass on src/pyeconomics/models/macro/
      with no suppression; statsmodels and QuantEcon are
      test-only here, never imported by a model.
    - Every array input has a maximum length and every
      iterative or matrix computation a bound on its size,
      so no input is an unbounded workload.
    - Golden values from CBO, the New York Fed and papers are
      cited with locators; no library-only dataset is
      committed.
    - quantecon (a test-group oracle) passes pip-audit and
      has a wheel or a pure-Python install on all twelve
      cells.
  </security>

  <context>
    pyeconomics. Phase 3. Step 14: launch catalog,
    macroeconomics.

    Current state (as of Phase 3 Step 13):

    - The macro package, its entry point and two bound models
      (macro.policy_rule, macro.neutral_rate) exist and pass
      their golden, property, contract and parity tests;
      binding profiles and real-time vintages work end to
      end.
    - Step 13 as built: a bind of a model with several
      calculations needs calculation=... and reads only that
      calculation's fields; lag(periods=n) binds a value n
      periods back; an AsOf.PERIOD binding reads up to the end
      of the period containing the date, so a source without
      that period is passed over. Real-time facts: ALFRED keeps
      no vintages of FRED's daily EFFR, target range, DGS10,
      DGS3MO or DFII10 (catalog candidates vintages=False, read
      as revised data), the New York Fed's files keep none, and
      CBO's archive starts 2024-02, so a CBO-only concept
      (us.output_gap.cbo) cannot be read as published before
      then: bind us.output_gap.real_potential (GDPC1 over
      GDPPOT, both in ALFRED) with the default
      LAST_ON_OR_BEFORE rule (the quarter's GDP comes after it)
      for a historical gap. Issue #135: nyfed effr fails on a
      whole-history or end-only request (FRED answers instead in
      library mode).
    - The catalog holds real and potential GDP, CBO's output
      gap and noncyclical rate, the unemployment rate,
      inflation and SPF expectations, nominal GDP growth,
      federal debt, the average interest rate on the debt,
      the primary balance, Treasury 3-month and 10-year
      yields, and Penn World Table series by economy.
    - statsmodels 0.15.0 (in [econometrics] and the test
      group) provides hpfilter, bkfilter, cffilter and OLS
      with HAC errors; QuantEcon 0.13.0 provides a Hamilton
      filter (no licence metadata; BSD-3-Clause in its
      repository; numba has CPython 3.15 wheels).
      econometrics.ols wraps statsmodels behind the extra;
      this step's estimators stay native so the macro domain
      needs no extra.
    - Step 6 facts on shared numerics (core/cashflows.py,
      core/descriptive.py), the out-of-bounds rule, overrides
      and literal markers still hold (Phase 2's Step 6
      context).

    Files to read (every file before drafting):
    - This roadmap's Overview (launch-catalog table,
      Contract-change and Citation rules) and
      docs/adr/0008-numerical-conventions.md (decisions 3, 6,
      10 and 11).
    - src/pyeconomics/models/macro/ and its tests and golden
      files; src/pyeconomics/core/ (descriptive, numerics,
      rates, binding).
    - src/pyeconomics/models/econometrics/ols.py and its
      tests (the statsmodels oracle patterns).
    - The papers each entry cites: Hodrick and Prescott
      (1997), Ravn and Uhlig (2002), Hamilton (2018), Baxter
      and King (1999), Christiano and Fitzgerald (2003),
      Okun (1962), Solow (1956, 1957), and Estrella and
      Trubin (2006) with the New York Fed's probability file.
  </context>

  <goal>
    The six macro models are registered and pass validate(),
    the golden harness, their invariant property tests, the
    contract suite and their oracle tests; their bindings
    resolve through the catalog; core/regression.py agrees
    with statsmodels; and their pages render in the docs
    preview.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      core/regression.py: ordinary least squares by QR or a
      least-squares solve, with classical, HC1 and
      Newey-West (Bartlett kernel, the lag rule an input)
      covariances, returning coefficients, standard errors,
      t statistics, R² and the residuals; bounded inputs; an
      oracle test against statsmodels' OLS for each
      covariance type. Shared numerics belong in core (Step
      16 reuses it), and adding it is a contract addition
      under the Contract-change rule.
    </requirement>

    <requirement>
      macro.output_gap — a union on calculation:
      from_potential (actual over potential less one, or the
      log difference, stated), hp (λ by frequency, 1,600
      quarterly, with Ravn and Uhlig's rule for others),
      hamilton (h = 8 and p = 4 for quarterly data, scaled by
      frequency), baxter_king (6 to 32 quarters, K = 12) and
      christiano_fitzgerald (the same band, its asymmetric
      random-walk form); outputs trend, cycle and the latest
      gap. Invariants at least: trend_plus_cycle_equals_series
      (HP), hp_cycle_zero_for_linear_series,
      band_pass_removes_linear_trend and
      gap_zero_when_actual_equals_potential. Golden sources:
      identities, CBO's published output gap for from_potential
      (official, file and row), recomputed textbook cases.
      Oracles: statsmodels' hpfilter, bkfilter and cffilter;
      QuantEcon's hamilton_filter. Evidence standard.
    </requirement>

    <requirement>
      macro.phillips_curve: inflation less expected inflation
      regressed on the unemployment gap (with optional
      supply-shock controls), Newey-West errors by default;
      outputs the slope, intercept, standard errors, R² and
      sample size. Invariant at least:
      exact_linear_data_recovers_slope. Golden sources: an
      identity, and a published estimate reproduced from
      public-domain inputs or a recomputed textbook value.
      Oracle: statsmodels OLS with HAC. Evidence contested
      (the curve's stability is an active debate).
    </requirement>

    <requirement>
      macro.okun_law — a union on calculation: gap (the output
      gap on the unemployment gap) and difference (Okun's
      first-difference form: the change in unemployment on
      output growth, annualized by compounding when asked, with
      the implied growth that holds unemployment constant,
      -a/b; the form Okun 1962 and Knotek 2007 estimate); same outputs
      and oracle as the Phillips curve. Invariant at least:
      exact_linear_data_recovers_coefficient. Golden sources:
      an identity and a published US estimate reproduced from
      public-domain BLS and BEA inputs. Evidence practitioner.
    </requirement>

    <requirement>
      macro.solow_growth — a union on calculation:
      steady_state (Cobb-Douglas with labour-augmenting
      technology: capital and output per effective worker,
      consumption, the golden-rule saving rate, the speed of
      convergence and its half-life) and growth_accounting
      (output growth split into capital, labour, human capital
      and the TFP residual, the capital share from the Penn
      World Table's labour share or an input). Invariants at
      least: steady_state_capital_rises_with_saving,
      golden_rule_maximizes_steady_state_consumption and
      contributions_sum_to_output_growth. Golden sources:
      identities and recomputed values from Solow (1956,
      1957). Evidence standard.
    </requirement>

    <requirement>
      macro.debt_dynamics: the debt-to-GDP path from an
      initial ratio and bounded paths of the effective
      nominal interest rate, nominal growth and the primary
      balance; r − g; and the primary balance that holds the
      ratio constant. Invariants at least:
      stabilizing_balance_holds_the_ratio,
      zero_balance_and_r_equal_g_hold_the_ratio and
      debt_rises_with_the_interest_rate. Golden sources: the
      identity, and a CBO projection whose published debt
      path the identity reproduces from CBO's own rates,
      growth and primary balances (official, report and
      table). Evidence standard.
    </requirement>

    <requirement>
      macro.recession_probability: the probability of a
      recession twelve months ahead from the spread between
      the 10-year Treasury yield and the 3-month bill, with
      the New York Fed's published coefficients, which apply
      to the spread in percentage points: convert with
      core.rates.decimal_to_percent, the only converter
      allowed (ADR-0008 decision 1). Invariant at least:
      probability_falls_as_spread_rises. Golden sources: the
      New York Fed's published monthly probabilities (official,
      file, month and access date) and the identity at which
      the probability is one half. Evidence practitioner.
    </requirement>

    <requirement>
      Bindings for all six through catalog concepts (the
      default profile for the United States; Penn World Table
      and debt profiles for other economies where the catalog
      has them), documented on each card; scripts/smoke.py
      still runs one model per domain.
    </requirement>

    <requirement>
      Chaining models: a test and a card example (on
      macro.output_gap's card) run macro.output_gap's hp
      calculation on bound real GDP and feed its latest gap
      into macro.policy_rule through a bind() override of the
      rule's gap input; the override is recorded as
      user-supplied in the manifest, beside the DataSource
      records of the rule's other bindings, so a filtered gap
      and a published one stay distinguishable. Offline,
      through cassettes.
    </requirement>

    <requirement>
      Every model: ModelSpec complete, a golden file with at
      least three cited cases and an edge case (a series of
      minimum length, a negative spread, r below g, a zero
      saving rate), invariant-marked property tests, oracle
      tests that never skip (add quantecon to the test group
      with --no-config), contract.check_model with 1,500
      examples, and an independent reviewer of the diff.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entries naming the six
      models and core/regression.py; the PR body lists every
      golden source. Filepath comment and three-line header
      on every new Python file; golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 14 acceptance criteria

- The six `macro.*` ids in the launch-catalog table are registered, and
  `registry.validate()` passes in CI.
- Each has a golden file with at least three cited cases including an edge
  case, all passing within tolerance; the CBO and New York Fed cases
  reproduce their published values at their published precision.
- Every declared invariant has a passing property test; the oracle tests
  agree with statsmodels' HP, Baxter-King and Christiano-Fitzgerald filters
  and OLS with HAC errors and with QuantEcon's Hamilton filter, and
  `core/regression.py` agrees with statsmodels for every covariance type.
- Each model's bindings resolve through the catalog offline, the contract
  suite fuzzes all six without an undocumented error, the coverage floors
  hold, and the docs preview renders their pages.
- An HP-filtered gap from `macro.output_gap` feeds `macro.policy_rule`
  through a `bind()` override, tested offline and shown on the card, with
  the override recorded as user-supplied in the manifest.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the purity guards pass on
  `models/macro/`, every array input is bounded, and no library-only
  dataset is committed.

---

## Step 15 — Launch Catalog: Fixed Income and Equity ✅

**Status:** Complete — PR #146 (2026-10-19)

> **Goal:** Register the four live-data entries for curves and market
> valuation. Add `fixed_income.curve_fitting` (Nelson-Siegel and Svensson
> zero, forward and par yields from parameters, and least-squares fits to
> observed yields) and `fixed_income.interest_rate_tree` (a lognormal
> binomial tree calibrated to a par curve, values of option-free, callable
> and putable bonds, option values, OAS and effective duration and
> convexity) to `src/pyeconomics/models/fixed_income/`, and
> `equity.implied_risk_premium` (the expected return and premium implied by
> an index level and its expected cash flows) and `equity.cape`
> (cyclically adjusted P/E, its earnings yield and the excess CAPE yield)
> to `src/pyeconomics/models/equity/`, each with bindings to the Treasury,
> GSW, Damodaran and Shiller concepts; golden files citing the Board's GSW
> file, the ECB's Svensson parameters, Kalotay, Williams and Fabozzi (1993)
> and Damodaran's published estimates; property tests for every
> invariant; QuantLib and independent oracles where they exist; and a live
> test that recomputes Shiller's published CAPE from his file at run time,
> since none of it may be committed. Parent: ROADMAP §4 3.7
> (`fixed_income`, `equity`).

**Branch:** `feature/phase03-step15-fixed-income-equity`

**Deploys:** nothing beyond merge.

| Setting      | Cost                                    | Balanced                                 | Quality                                  |
| ------------ | --------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| Model        | GPT-6.1 Sol                             | Opus 5.5                                 | Opus 5.5                                 |
| Backup       | Sonnet 5.5 — Claude Code · Effort XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh |
| Platform     | Codex                                   | Claude Code                              | Claude Code                              |
| Effort       | Intelligence High                       | Effort High                              | Effort XHigh                             |
| Thinking     | —                                       | On                                       | On                                       |
| Conversation | **New**                                 | **New**                                  | **New**                                  |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

> Settings updated 2026-10-18 (refresh): was Claude Opus 5.5 · Effort High.
> Model and effort unchanged (Balanced column); the single-column table
> becomes the full ladder, and the backup is now GPT-6.1 Sol at Intelligence
> XHigh.

> Ran 2026-10-19: Balanced — Claude Opus 5.5 on Claude Code (effort as the
> operator set it). The **Runs:** column; the Claude weekly pool's `tight` row
> had passed its reset, so it read as headroom.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY; complexity is High and the step is not novel (the methods are published and oracles check them). The ladder's Balanced column runs: Claude Opus 5.5 on Claude Code at High, backup GPT-6.1 Sol. The Cost and Quality columns, and the Backup under a tight or exhausted pool, are read off the table on the day. New conversation per phase-boundary hygiene.

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
       feature/phase03-step15-fixed-income-equity`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
       complete. You can now move
       on to Step 16." That
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
       one before Step 16.
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
    - The purity guards pass on the touched model packages
      with no suppression; dates are inputs, never "today".
    - Every solver (curve fitting, tree calibration, OAS,
      the implied return) has an iteration cap and every
      array input (maturities, call schedules, earnings
      histories, tree steps) a maximum length.
    - Shiller's data is library-only: no value from his file
      is committed; the CAPE check against his published
      column runs live, at test time, and stores nothing.
  </security>

  <context>
    pyeconomics. Phase 3. Step 15: launch catalog, fixed
    income and equity.

    Current state (as of Phase 3 Step 14):

    - The fixed_income package holds Phase 2's six models,
      its shared bond helpers (_bonds.py) and core's curve
      and cash-flow numerics (core/curves.py,
      core/cashflows.py); the equity package holds the DDM
      and FCF models (_valuation.py). QuantLib is in the test
      group with abi3 wheels for every cell.
    - The catalog holds the Treasury par curves, the GSW
      parameters and fitted yields, the 10-year nominal and
      real yields, Damodaran's implied ERP inputs and
      Shiller's price, earnings and CPI series;
      core/regression.py and core/numerics.py are the shared
      fitting and root-finding tools. (Corrected in this
      step: the GSW parameters and Shiller's series were
      table columns only, Damodaran's file exposed no index
      level, cash or growth, and a binding read only a
      series; Step 15 added the series concepts, the
      providers' columns and curve bindings, recorded in
      the carry-over checklist.)
    - The GSW file publishes, for each day, BETA0 to BETA3,
      TAU1 and TAU2 and the zero yields, par yields and
      forwards they imply; the ECB publishes its euro-area
      Svensson parameters with the spot rates they imply.
    - Damodaran's aggregates may be displayed with credit
      (not library-only), so a golden case may cite a handful
      of his published values; Shiller's may not.
    - From Step 13: no source keeps vintages of the Treasury
      yields (Treasury keeps none and ALFRED none of FRED's
      DGS10, DGS3MO or DFII10), so a bind of them as of a date
      reads revised data and says so; a bind of a model with
      several calculations needs calculation=...; ChartKind
      has a band kind for a range around a line.

    Files to read (every file before drafting):
    - This roadmap's Overview (launch-catalog table, Citation
      and Recording rules) and docs/adr/0008 (decisions 4, 6,
      10 and 11).
    - src/pyeconomics/models/fixed_income/ and equity/ with
      their tests and golden files; core/curves.py,
      cashflows.py, numerics.py and regression.py.
    - The Board's GSW paper and file description, the ECB's
      yield-curve methodology note, Kalotay, Williams and
      Fabozzi (1993), Damodaran's equity-risk-premium paper
      (the current edition) and his implied-ERP file, and
      Campbell and Shiller (1998) with Shiller's data notes.
  </context>

  <goal>
    The four models are registered and pass validate(), the
    golden harness, their invariant property tests, the
    contract suite and their oracle tests; their bindings
    resolve through the catalog; the live CAPE check passes in
    the weekly run; and their pages render in the docs
    preview.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      fixed_income.curve_fitting — a union on calculation:
      evaluate (Nelson-Siegel or Svensson parameters to zero
      yields, instantaneous forwards and par yields at
      bounded maturities, with the compounding stated) and fit
      (bounded least squares to observed zero or par yields,
      several deterministic starting points, an iteration
      cap, the fitted parameters, fitted yields and RMSE).
      Invariants at least: long_end_tends_to_beta0,
      short_end_tends_to_beta0_plus_beta1,
      svensson_with_zero_beta3_is_nelson_siegel and
      fit_recovers_noise_free_curve (compared on yields, not
      parameters, which are not unique). Golden sources: GSW
      file rows (official, date and columns, at the file's
      precision) and the ECB's published parameters and spot
      rates (official). Oracle: an independent NumPy
      evaluation, and QuantLib's fitted curves where its
      method matches. Evidence standard.
    </requirement>

    <requirement>
      fixed_income.interest_rate_tree — a union on
      calculation: calibrate (the lognormal tree to a bounded
      par curve and a volatility, returning its node rates),
      value (an option-free, callable or putable bond by
      backward induction over the calibrated tree, with the
      option's value), oas (the constant spread over every
      node that reprices to a market price, through
      core.numerics) and effective (duration and convexity by
      shifting the curve and recalibrating). Invariants at
      least: calibrated_tree_prices_par_bonds_at_par,
      callable_below_straight_below_putable,
      zero_volatility_oas_equals_zero_volatility_spread and
      oas_falls_as_price_rises. Golden sources: Kalotay,
      Williams and Fabozzi (1993)'s worked example (paper)
      and the identities. Evidence standard.
    </requirement>

    <requirement>
      equity.implied_risk_premium: the discount rate at which
      an index level equals the present value of expected
      cash flows (dividends and buybacks) growing for a
      bounded number of years and then at a terminal rate
      (the risk-free rate by default), solved with
      core.numerics; outputs the implied expected return and
      the premium over the risk-free rate. Invariants at
      least: premium_rises_as_the_index_falls and
      implied_return_exceeds_terminal_growth. Golden sources:
      Damodaran's published implied premiums with the inputs
      he states (paper or his file, edition and row, with
      credit) and identities. Evidence practitioner.
    </requirement>

    <requirement>
      equity.cape: the real price over the average of real
      earnings over a bounded window (ten years by default),
      the CAPE earnings yield, and the excess CAPE yield over
      a real 10-year rate (a TIPS yield, or the nominal yield
      less trailing inflation, as an input states).
      Invariants at least:
      constant_real_earnings_give_price_over_earnings and
      cape_yield_is_the_reciprocal. Golden sources:
      identities and a recomputed definition from Campbell
      and Shiller (1998). A live test (marked live) fetches
      Shiller's file through the shiller provider and checks
      the model reproduces his published CAPE for several
      months within his rounding; it commits nothing.
      Evidence practitioner.
    </requirement>

    <requirement>
      Bindings for all four through catalog concepts (the GSW
      parameters and Treasury par curve; the Treasury curve
      for calibration; Damodaran's inputs and the 10-year
      yield; Shiller's series and the real 10-year yield),
      documented on each card.
    </requirement>

    <requirement>
      Every model: ModelSpec complete, a golden file with at
      least three cited cases and an edge case (a negative
      short rate, a bond callable at the next date, a
      terminal growth near the discount rate, a window at its
      minimum), invariant-marked property tests, oracle tests
      where an oracle exists (never skipped),
      contract.check_model with 1,500 examples, and an
      independent reviewer of the diff.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entries naming the four
      models; the PR body lists every golden source.
      Filepath comment and three-line header on every new
      Python file; golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 15 acceptance criteria

- `fixed_income.curve_fitting`, `fixed_income.interest_rate_tree`,
  `equity.implied_risk_premium` and `equity.cape` are registered, and
  `registry.validate()` passes in CI.
- Each has a golden file with at least three cited cases including an edge
  case, all passing within tolerance; the GSW and ECB cases reproduce the
  published yields at their published precision.
- Every declared invariant has a passing property test; the calibrated tree
  prices its calibration bonds at par; the oracle tests pass where an
  oracle exists.
- The live CAPE check reproduces Shiller's published values in the weekly
  run without committing any of his data.
- Bindings resolve offline, the contract suite fuzzes all four without an
  undocumented error, the coverage floors hold, and the docs preview
  renders their pages.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — every solver and array input is bounded,
  and no library-only value is committed.

---

## Step 16 — Launch Catalog: Asset Pricing and Portfolio ✅

**Status:** Complete — PR #153 (2026-10-20)

> **Goal:** Open the `asset_pricing` domain and finish the portfolio
> entries. Add `src/pyeconomics/models/asset_pricing/` with
> `asset_pricing.factor_regression` (CAPM beta, alpha and the security
> market line, and the FF3, Carhart, FF5 and FF6 time-series regressions on
> `core/regression.py`) and `asset_pricing.factor_model_tests` (the
> Gibbons-Ross-Shanken test and Fama-MacBeth two-pass regressions with the
> Shanken correction), and the `asset_pricing` entry point; add
> `portfolio.black_litterman` (equilibrium returns, posterior returns and
> covariance, and weights, with He-Litterman or Idzorek view confidence)
> and `portfolio.risk_based_allocation` (inverse volatility, equal risk
> contribution and hierarchical risk parity) to
> `src/pyeconomics/models/portfolio/`; bind them to the Ken French factor
> and portfolio concepts (demonstration inputs, library-only) and to the
> user's own returns; golden files citing papers and identities; property
> tests for every invariant; and oracle tests against statsmodels and
> independent recomputations. Parent: ROADMAP §4 3.7 (`asset_pricing`,
> `portfolio`).

**Branch:** `feature/phase03-step16-asset-pricing-portfolio`

**Deploys:** nothing beyond merge.

| Setting      | Cost                                    | Balanced                                 | Quality                                  |
| ------------ | --------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| Model        | GPT-6.1 Sol                             | Opus 5.5                                 | Opus 5.5                                 |
| Backup       | Sonnet 5.5 — Claude Code · Effort XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh |
| Platform     | Codex                                   | Claude Code                              | Claude Code                              |
| Effort       | Intelligence High                       | Effort High                              | Effort XHigh                             |
| Thinking     | —                                       | On                                       | On                                       |
| Conversation | **New**                                 | **New**                                  | **New**                                  |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

> Settings updated 2026-10-18 (refresh): was Claude Opus 5.5 · Effort High.
> Model and effort unchanged (Balanced column); the single-column table
> becomes the full ladder, and the backup is now GPT-6.1 Sol at Intelligence
> XHigh.

> Ran 2026-10-20: Balanced — Claude Opus 5.5 on Claude Code (effort as the
> operator set it). The **Runs:** column; the Claude weekly pool's `tight` row
> had passed its reset, so it read as headroom.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY; complexity is High and the step is not novel (the methods are published and oracles check them). The ladder's Balanced column runs: Claude Opus 5.5 on Claude Code at High, backup GPT-6.1 Sol. The Cost and Quality columns, and the Backup under a tight or exhausted pool, are read off the table on the day. New conversation per phase-boundary hygiene.

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
       feature/phase03-step16-asset-pricing-portfolio`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
       shape "Step 16 is
       complete. You can now move
       on to Step 17." That
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
       one before Step 17.
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
    - The purity guards pass on src/pyeconomics/models/
      asset_pricing/ and portfolio/ with no suppression; the
      import allowlist covers the new domain.
    - Every matrix input is bounded (assets, factors and
      periods each capped), and every solver has an
      iteration cap, so no input is an unbounded workload.
    - The Ken French data stays library-only: golden files
      hold no value from it; bound runs fetch it at run time
      on the user's machine.
    - An oracle library considered for the test group
      (linearmodels, PyPortfolioOpt, skfolio) is added only
      under the Wheel rule.
  </security>

  <context>
    pyeconomics. Phase 3. Step 16: launch catalog, asset
    pricing and portfolio.

    Current state (as of Phase 3 Step 15):

    - core/regression.py (Step 14) gives OLS with classical,
      HC1 and Newey-West errors; the portfolio package holds
      Phase 2's mean_variance and utility models and its
      _common.py; no asset_pricing package exists.
    - Step 14 as built: pyeconomics.core.least_squares(response,
      design, constant=, covariance="classical"|"hc1"|
      "newey_west", lags=) returns LeastSquares (coefficients,
      standard_errors, t_statistics or None for a fit exact to
      rounding, r_squared, fitted, residuals, lags); at most
      10,000 rows, 20 coefficients and 100 lags; the design is
      equilibrated and refused (DomainError) past a scaled
      condition number of 1e7; Newey-West has no small-sample
      correction (statsmodels' HAC default). The sandwich is
      built from the rows of R^-1 Q', not by multiplying
      (X'X)^-1 into the middle, which lost five digits on
      near-collinear designs. models/macro/_estimates.py shows
      a model wrapping it (bounds, exact-fit and near-exact
      warnings). Window bindings of one frequency end on one
      date, so factor returns and a portfolio's returns bound
      as windows pair by period, and a window passes over a
      source too short for it (resolve(min_observations=)); a
      growth rate bound through pct_change is a Return.
    - The catalog holds the Ken French factor sets
      (factors.ff3, ff5 and momentum, monthly and daily) and
      portfolio sets (the 25 size and book-to-market and the
      industry portfolios), library-only.
    - On 2026-10-14 linearmodels 7.0 and cvxpy 1.9.3 have no
      CPython 3.15 wheel, so neither linearmodels'
      FamaMacBeth nor PyPortfolioOpt (which needs cvxpy) can
      be a never-skipped oracle on every cell unless their
      wheels arrive first; statsmodels and SciPy can.
    - Adding asset_pricing makes thirteen registered domains;
      scripts/smoke.py runs one model per domain.

    Files to read (every file before drafting):
    - This roadmap's Overview (launch-catalog table, Wheel
      and Citation rules).
    - src/pyeconomics/core/regression.py,
      src/pyeconomics/models/portfolio/ and their tests and
      golden files, and tests/registry/test_model_imports.py.
    - The papers: Sharpe (1964) and Lintner (1965) for the
      CAPM; Fama and French (1993, 2015, 2018); Carhart
      (1997); Gibbons, Ross and Shanken (1989); Fama and
      MacBeth (1973); Shanken (1992); Black and Litterman
      (1992); He and Litterman (1999); Idzorek (2005);
      Maillard, Roncalli and Teiletche (2010); López de Prado
      (2016).
  </context>

  <goal>
    The four models are registered and pass validate(), the
    golden harness, their invariant property tests, the
    contract suite and their oracle tests; asset_pricing is a
    registered domain with an entry point, which smoke.py's
    per-domain run covers; and their pages render in the
    docs preview.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Package and entry point:
      src/pyeconomics/models/asset_pricing/ with one module
      per entry; `asset_pricing =
      "pyeconomics.models.asset_pricing"` in the entry-point
      table; the domain added to the import allowlist test's
      expectations. scripts/smoke.py needs no change: its
      per-domain run picks up the new domain from the
      registry.
    </requirement>

    <requirement>
      asset_pricing.factor_regression — a union on
      calculation: capm, ff3, carhart, ff5 and ff6, regressing
      an asset's excess returns on the factor set through
      core/regression.py (Newey-West errors by default, the
      lag rule an input); outputs alpha per period and
      annualized (an explicit periods_per_year), each beta,
      their standard errors and t statistics, R² and residual
      volatility, and for capm the security market line's
      expected return at a stated market premium. Invariants
      at least: exact_factor_data_recovers_betas and
      capm_beta_equals_covariance_over_variance. Golden
      sources: identities and recomputed textbook examples.
      Oracle: statsmodels OLS. Evidence standard.
    </requirement>

    <requirement>
      asset_pricing.factor_model_tests — a union on
      calculation: grs (the F statistic and p-value for N
      test assets on L factors over T periods, requiring
      T > N + L) and fama_macbeth (time-series betas, then a
      cross-sectional regression per period; the average
      premia with Fama-MacBeth errors and, optionally, the
      Shanken correction). Invariants at least:
      grs_zero_when_alphas_are_zero,
      fama_macbeth_recovers_premia_on_exact_data and
      shanken_correction_never_narrows_errors. Golden sources:
      identities and recomputed examples from the papers.
      Oracles: SciPy's F distribution and an independent
      per-period statsmodels recomputation; linearmodels only
      under the Wheel rule. Evidence standard.
    </requirement>

    <requirement>
      portfolio.black_litterman: from a bounded covariance
      (or returns window), market weights and risk aversion,
      the equilibrium returns; from a pick matrix, view
      returns and a confidence convention (He-Litterman's
      Ω = diag(P τΣ Pᵀ) by default, or Idzorek's
      confidence levels), the posterior returns and
      covariance and the unconstrained optimal weights.
      Invariants at least: no_views_return_equilibrium,
      certain_view_holds_exactly and
      no_views_weights_equal_market_weights. Golden sources:
      He and Litterman (1999)'s and Idzorek (2005)'s worked
      examples (paper) and identities. Oracle: an independent
      NumPy recomputation. Evidence standard.
    </requirement>

    <requirement>
      portfolio.risk_based_allocation — a union on
      calculation: inverse_volatility,
      equal_risk_contribution (a convex formulation solved to
      a stated tolerance with an iteration cap) and
      hierarchical_risk_parity (correlation distance,
      single-linkage clustering through SciPy, quasi-
      diagonalization and recursive bisection); outputs
      weights, each asset's risk contribution and the
      portfolio's volatility. Invariants at least:
      weights_sum_to_one, erc_contributions_are_equal,
      inverse_volatility_equals_erc_for_uncorrelated_assets and
      hrp_weights_are_positive. Golden sources: Maillard,
      Roncalli and Teiletche (2010)'s example and López de
      Prado (2016)'s (paper) where their inputs are published,
      and identities. Oracle: an independent recomputation.
      Evidence practitioner.
    </requirement>

    <requirement>
      Bindings: the factor sets and portfolio sets as
      library-only demonstration inputs (a window of monthly
      observations), the user's own returns as the asset
      side; documented on each card with the Ken French
      notice.
    </requirement>

    <requirement>
      Every model: ModelSpec complete, a golden file with at
      least three cited cases and an edge case (a single
      factor, T just above N + L, a singular-looking
      covariance, two perfectly correlated assets),
      invariant-marked property tests, oracle tests that never
      skip, contract.check_model with 1,500 examples, and an
      independent reviewer of the diff.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entries naming the four
      models and the new domain; the PR body lists every
      golden source. Filepath comment and three-line header
      on every new Python file; golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 16 acceptance criteria

- `asset_pricing.factor_regression`, `asset_pricing.factor_model_tests`,
  `portfolio.black_litterman` and `portfolio.risk_based_allocation` are
  registered, `asset_pricing` is a registered domain with its entry point,
  and `registry.validate()` passes in CI.
- Each has a golden file with at least three cited cases including an edge
  case, all passing within tolerance.
- Every declared invariant has a passing property test, and the oracle
  tests (statsmodels, SciPy and independent recomputations) pass on all
  twelve CI cells without a skip.
- `scripts/smoke.py` runs one model in each of 13 domains, the contract
  suite fuzzes all four without an undocumented error, the coverage floors
  hold, and the docs preview renders their pages.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — every matrix input and solver is
  bounded, and no Ken French value is committed.

---

## Step 17 — Launch Catalog: Econometrics ✅

**Status:** Complete — PR #160 (2026-10-21)

> **Goal:** Complete the 50-entry launch catalog with the two econometrics
> entries behind the `[econometrics]` extra. Add `econometrics.garch`
> (GARCH, GJR-GARCH and EGARCH estimation with normal or Student-t errors,
> volatility forecasts and their annualization, over arch) and
> `econometrics.time_series` (ARIMA and SARIMA fits and forecasts, VARs
> with lag selection, impulse responses and variance decompositions, and
> the Engle-Granger and Johansen cointegration tests, over statsmodels) to
> `src/pyeconomics/models/econometrics/`; add arch to the extra under the
> Wheel rule — on 2026-10-14 arch 8.0.0 had no CPython 3.15 wheel; bind
> both to catalog series (any of the bound field's unit kind and frequency,
> through `concepts=`), with the Ken French daily market factor as
> the demonstration input; golden files built from identities, seeded
> simulations with known parameters and published tables recomputed on
> data a dependency already ships; property tests for every invariant; and
> independent oracle recomputations. Parent: ROADMAP §4 3.7
> (`econometrics`); ROADMAP §4 7.3 ("wrap, don't rewrite").

**Branch:** `feature/phase03-step17-econometrics`

**Deploys:** nothing beyond merge.

| Setting      | Cost                                    | Balanced                                 | Quality                                  |
| ------------ | --------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| Model        | GPT-6.1 Sol                             | Opus 5.5                                 | Opus 5.5                                 |
| Backup       | Sonnet 5.5 — Claude Code · Effort XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh |
| Platform     | Codex                                   | Claude Code                              | Claude Code                              |
| Effort       | Intelligence High                       | Effort High                              | Effort XHigh                             |
| Thinking     | —                                       | On                                       | On                                       |
| Conversation | **New**                                 | **New**                                  | **New**                                  |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

> Settings updated 2026-10-18 (refresh): was Claude Opus 5.5 · Effort High.
> Model and effort unchanged (Balanced column); the single-column table
> becomes the full ladder, and the backup is now GPT-6.1 Sol at Intelligence
> XHigh.

> Ran 2026-10-21: Balanced — Claude Opus 5.5 on Claude Code (Effort High). The
> **Runs:** column; the Claude weekly pool's `tight` row had passed its reset,
> so it read as headroom.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY; complexity is High and the step is not novel (the methods are published and oracles check them). The ladder's Balanced column runs: Claude Opus 5.5 on Claude Code at High, backup GPT-6.1 Sol. The Cost and Quality columns, and the Backup under a tight or exhausted pool, are read off the table on the day. New conversation per phase-boundary hygiene.

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
       feature/phase03-step17-econometrics`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
       shape "Step 17 is
       complete. You can now move
       on to Step 18." That
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
       one before Step 18.
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
    - arch joins [econometrics] and the test group only after
      pip-audit and the licences hook (NCSA, on the
      allowlist); if it still lacks a CPython 3.15 wheel, it
      is gated by `python_version < "3.15"` with the
      maintainer's approval in this PR, and an issue tracks
      the marker (Wheel rule).
    - arch and statsmodels are imported only inside compute
      (EXTRA_DOMAINS keeps them to the econometrics domain);
      the purity guards pass with no suppression.
    - Every series input, lag order, horizon and parameter
      count is bounded, so no fit is an unbounded workload.
    - No dataset is committed: golden cases use identities,
      seeded simulations, and data a dependency already
      ships.
  </security>

  <context>
    pyeconomics. Phase 3. Step 17: launch catalog,
    econometrics.

    Current state (as of Phase 3 Step 16):

    - econometrics.ols (Phase 2) wraps statsmodels behind
      `@model(extra="econometrics")`; EXTRA_DOMAINS maps the
      extra to its domain; smoke.py --extras runs it in a
      clean venv with the extra; the package job and
      release-smoke install the extra.
    - Phase 2 lessons (memory, Step 12): statsmodels resets
      warning filters to "always", so a model records its
      warnings explicitly instead of trusting pytest's
      error filter; `extra=` must be a string literal.
    - arch 8.0.0 (NCSA) had wheels for CPython 3.10 to 3.14
      only on 2026-10-14; statsmodels 0.15.0 has CPython 3.15
      wheels. The catalog holds the Ken French daily factors
      and every macro series as bindable inputs.

    Files to read (every file before drafting):
    - This roadmap's Overview (launch-catalog table, Wheel
      and Dependency rules).
    - src/pyeconomics/models/econometrics/ols.py, its tests
      and golden file, tests/registry/test_model_imports.py
      and scripts/smoke.py.
    - arch's and statsmodels' documentation for the
      estimators wrapped; Bollerslev (1986), Glosten,
      Jagannathan and Runkle (1993), Nelson (1991), Box and
      Jenkins, Lütkepohl (2005), Engle and Granger (1987) and
      Johansen (1991).
  </context>

  <goal>
    econometrics.garch and econometrics.time_series are
    registered behind [econometrics] and pass validate(), the
    golden harness, their invariant property tests, the
    contract suite and their oracle tests; without the extra
    they name it; and on any cell arch cannot install, the
    GARCH model names the gap, as a test asserts.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff: check arch's wheels for every CI cell. If
      CPython 3.15 is still missing, ask the maintainer to
      approve the Wheel rule's marker path and record the
      answer in the PR body; open the tracking issue.
    </requirement>

    <requirement>
      econometrics.garch — a union on calculation: garch,
      gjr and egarch, with p, o and q bounded, normal or
      Student-t errors and a zero or constant mean, fitted by
      arch on returns the model rescales to percent and
      reports back in decimals; outputs each parameter with
      its standard error, the log-likelihood, AIC and BIC,
      persistence, the unconditional volatility where it
      exists, the last conditional volatility and variance
      forecasts by horizon (annualized with an explicit
      periods_per_year). Invariants at least:
      forecast_converges_to_unconditional_variance (when
      persistence is below one) and
      conditional_variance_is_positive. Golden sources: the
      forecast recursion as an identity, a seeded simulation
      whose estimates fall within a stated sampling tolerance
      of the generating parameters, and a published benchmark
      only if its data's licence allows a fixture. Oracle: an
      independent SciPy log-likelihood at arch's estimates and
      the forecast recursion recomputed. Evidence standard.
    </requirement>

    <requirement>
      econometrics.time_series — a union on calculation:
      arima (orders and seasonal orders bounded; fit,
      information criteria and forecasts with intervals), var
      (lag selection by AIC, BIC or HQ; coefficients;
      orthogonalized impulse responses with the Cholesky
      ordering stated, and the forecast-error variance
      decomposition by horizon), engle_granger (the two-step
      test with MacKinnon's p-values) and johansen (trace and
      maximum-eigenvalue statistics with critical values, the
      deterministic terms an input). Invariants at least:
      var_irf_at_horizon_zero_is_the_cholesky_factor,
      fevd_rows_sum_to_one and
      cointegrated_simulation_rejects_no_cointegration.
      Golden sources: identities, seeded simulations and
      published tables (Lütkepohl and others) recomputed on
      datasets statsmodels ships. Oracles: independent NumPy
      recomputations (equation-by-equation OLS for the VAR,
      companion-matrix impulse responses, an eigenvalue
      problem for Johansen). Evidence standard.
    </requirement>

    <requirement>
      Extra and warnings: `uv add --no-config --optional
      econometrics "arch>=8.0"` (with the approved marker if
      needed), joined to the test group; lock and export with
      --no-config; licences, pip-audit and dependency-review
      green. Both models declare extra="econometrics", import
      their library inside compute, and record the library's
      warnings as result warnings explicitly.
    </requirement>

    <requirement>
      Bindings: any catalog series of the bound field's unit
      kind and frequency through the concepts= override (the
      Step 12 contract refuses a rebind to another kind or
      frequency), with a default demonstration profile on the
      Ken French daily market factor (GARCH) and US inflation
      and unemployment (the VAR), documented on each card.
    </requirement>

    <requirement>
      Every model: ModelSpec complete, a golden file with at
      least three cited cases and an edge case (a minimum-
      length series, persistence near one, a VAR with one
      lag, a near-unit-root series), invariant-marked property
      tests, oracle tests that never skip, contract.check_model
      with 1,500 examples, the extras smoke covering both, and
      an independent reviewer of the diff.
    </requirement>

    <requirement>
      CHANGELOG [Unreleased] "Added" entries naming the two
      models and arch; the PR body lists every golden source.
      Filepath comment and three-line header on every new
      Python file; golden TOML files `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 17 acceptance criteria

- `econometrics.garch` and `econometrics.time_series` are registered,
  `registry.validate()` passes in CI, and the registry holds all 50
  launch-catalog ids.
- Each has a golden file with at least three cited cases including an edge
  case, all passing within tolerance, and every declared invariant has a
  passing property test; the independent oracles agree.
- Without `[econometrics]`, both raise `MissingOptionalDependencyError`
  naming the extra; with it, `smoke.py --extras` runs both in the package
  job's clean venv; on any cell where arch cannot install, the GARCH model
  names the gap and a test asserts it, under an approved marker and an open
  tracking issue.
- The contract suite fuzzes both without an undocumented error, the
  coverage floors hold, and the docs preview renders their pages.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — arch passed the licence and audit
  review, and every input to a fit is bounded.

---

## Step 18 — 1.0.0a2 Readiness Gate ✅

**Status:** Complete — PR #165 (2026-10-22)

> **Goal:** Decide, with evidence, that publishing `1.0.0a2` to PyPI is
> safe — an upload that can never be reused, only yanked, and the first
> release that handles users' keys and fetches their data. Rehearse the
> exact candidate: tag `main`'s HEAD `v1.0.0a2.devN` (the version `main`
> has carried since Step 1) and let `release.yml` publish it to TestPyPI
> with attestations and run the smoke; install the rehearsal in clean
> environments on the maintainer's machine and run the live end-to-end
> recipe Step 19 must pass — a BLS series fetched without a FRED key, and
> the Taylor rule for a past date on ALFRED vintages with the maintainer's
> own FRED key, printing no key. Write `docs/releases/1.0.0a2-readiness.md`
> and fill every section from commands run in this step — the catalog,
> provider, credential and access-control audits, the rehearsal, the
> artifacts, dependencies and licences and the Python floor, the version
> and milestone tag, documentation and the release-notes draft,
> monitoring, rollback, attribution and legal, and the maintainer's
> recorded GO or NO-GO. Nothing reaches PyPI. Parent: ROADMAP §5
> "Promotion path and cutovers" and §4 3.8; ADR-0003 and ADR-0010.

**Branch:** `feature/phase03-step18-release-gate`

**Prerequisites:** Step 17 Complete on main. Step 7 and Sponsors approval
may remain pending under the Overview's exception. Freeze and audit the exact
release provider set in this step; the maintainer's GO is still required.

**Deploys:** TestPyPI — `pyeconomics 1.0.0a2.devN`, tagged on `main`'s
HEAD at kickoff and published through `release.yml`'s `testpypi`
environment; the readiness document lands on merge; nothing reaches PyPI.

| Setting      | Cost                                        | Balanced                                 | Quality                                  |
| ------------ | ------------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| Model        | GPT-6 Luna                                  | Opus 5.5                                 | Opus 5.5                                 |
| Backup       | Gemini 3.8 Flash — Antigravity · Effort Low | GPT-6.1 Sol — Codex · Intelligence XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh |
| Platform     | Codex                                       | Claude Code                              | Claude Code                              |
| Effort       | Intelligence XHigh                          | Effort High                              | Effort XHigh                             |
| Thinking     | —                                           | On                                       | On                                       |
| Conversation | **New**                                     | **New**                                  | **New**                                  |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

> Settings updated 2026-10-18 (refresh): was GPT-6.1 Sol · Intelligence
> Medium. Knowledge PRIMARY, agentic SECONDARY, Medium: the ladder's Balanced
> column is Opus 5.5 at High on Claude Code, with GPT-6.1 Sol at Intelligence
> XHigh as backup; the old pick was Codex.

> Ran 2026-10-21 to 2026-10-22: Balanced — Claude Opus 5.5 on Claude Code
> (Effort High). The **Runs:** column; the Claude weekly pool's `tight` row had
> passed its reset, so it read as headroom.

**Model rationale:** Knowledge is PRIMARY and agentic work SECONDARY; complexity is Medium. The ladder's Balanced column runs: Claude Opus 5.5 on Claude Code at High, backup GPT-6.1 Sol. The Cost and Quality columns, and the Backup under a tight or exhausted pool, are read off the table on the day. New conversation per phase-boundary hygiene.

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
       feature/phase03-step18-release-gate`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
       shape "Step 18 is
       complete. You can now move
       on to Step 19." That
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
       one before Step 19.
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
    - The rehearsal publishes only through Trusted Publishing
      in the testpypi environment; no token is created or
      stored; the tag push is the maintainer's approved
      action.
    - The live recipe reads the maintainer's keys only
      through the credential chain, in a clean venv with an
      isolated configuration directory; nothing prints,
      logs or records a key, and the readiness document
      records outcomes, never values.
    - The credential audit runs the whole-tree secret scan
      and trufflehog, confirms no repository secret exists
      and that only providers-live holds environment
      secrets, and re-runs the canary suite.
  </security>

  <context>
    pyeconomics. Phase 3. Step 18: 1.0.0a2 readiness gate.

    Current state (as of Phase 3 Step 17):

    - All 50 launch-catalog ids are registered; the Phase 3
      release provider set (30 ids, or 31 with verified SEC)
      passes the contract suite offline and (except yfinance)
      in the weekly live run; the catalog, bindings and
      schema-2 manifests work end to end; main reads
      1.0.0a2.dev1 unless a fix bumped it.
    - docs/releases/1.0.0a1-readiness.md is the pattern: its
      eleven sections, its evidence style and its
      `Decision: GO — <date> — <name>` line; Phase 2's first
      gate attempt ended in a NO-GO that found a model error
      (#89), so a NO-GO is a valid outcome, not a failure of
      this step.
    - release.yml routes a .devN tag to TestPyPI and runs
      release-smoke.yml; scripts/checks/python_floor.py
      re-checks ADR-0010's floor; ADR-0003's milestone table
      names v1.0.0a2 for Phase 3.
    - The ROADMAP's release check (§4 3.8): a clean `pip
      install --pre pyeconomics==1.0.0a2` fetches a BLS
      series without a FRED key and, with the tester's own
      FRED key, runs the Taylor rule for a past date on
      ALFRED vintages.

    Files to read (every file before drafting):
    - docs/releases/1.0.0a1-readiness.md and
      docs/releases/1.0.0a1.md.
    - docs/roadmap/ROADMAP.md §4 3.8 and §5 "Release &
      deployment strategy" and "Data licensing policy".
    - docs/adr/0003, 0005, 0010 and 0011.
    - .github/workflows/release.yml, release-smoke.yml,
      providers-live.yml and providers-heartbeat.yml.
    - scripts/checks/python_floor.py, dist_contents.py,
      licences.py and licence_exceptions.toml; the
      registered providers' ProviderInfo.
  </context>

  <goal>
    v1.0.0a2.devN is on TestPyPI with attestations and passes
    the smoke; the live recipe passes from the rehearsed
    package; docs/releases/1.0.0a2-readiness.md has every
    section filled from evidence and ends in the maintainer's
    recorded decision; and the release notes are drafted for
    Step 19.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff: Step 17 reads Complete. Batch one request to
      the maintainer: approve the push of tag
      v1.0.0a2.devN on main's HEAD and the live recipe on
      their machine with their keys. Push the tag; watch
      release.yml's verify, build, publish-testpypi and
      smoke jobs to green.
    </requirement>

    <requirement>
      docs/releases/1.0.0a2-readiness.md, every section from
      commands run in this step, each with its command and
      outcome:
      1. Catalog audit: 50 ids registered and validated, each
         with a card, cited goldens, invariant tests and a
         docs page; models re-versioned in this phase listed
         with their changelog entries.
      2. Provider audit: for each release-set provider, its
         class, terms URL and checked date (none older than
         13 months), attribution, required notice, llm_use,
         cache policy and whether its cassettes are
         synthetic; the classes this phase settled (OECD,
         CBO, the Penn World Table). List the exact required
         30 ids from the source plan, plus sec_edgar only
         after Step 7 completes and its proof is verified.
         Compare this independent expected set to installed
         entry points; never derive the expected set merely
         from whatever happens to be installed. Record SEC's
         external blocker, owner and carry-over when absent;
         state explicitly that Step 7 is not complete.
         Do not block rehearsal or GO solely for that named
         deferral or pending Sponsors approval. Every shipped
         provider retains its full acceptance requirements.
      3. Credentials and redaction: the canary suite, the
         secret-reveal and credential-logging rules, the
         whole-tree secret scan, no repository secret, the
         providers-live environment's secrets by name.
      4. Access control: main's protection and its 20
         required checks; the testpypi, pypi and
         providers-live environments' deployment policies;
         the release-tags ruleset.
      5. Rehearsal: the tag, the release run, both files and
         their provenances on TestPyPI, the smoke.
      6. Live end-to-end: from a clean venv on TestPyPI's
         rehearsal (dependencies from PyPI), with an isolated
         configuration and no FRED key, a BLS series fetched
         (keyless through API v1, or through v2 when the
         maintainer's BLS_API_KEY is set; the record names
         which); with the maintainer's FRED key through the
         chain, the Taylor (1993) rule for a past date on
         ALFRED vintages, the manifest's data sources naming
         the vintages; no key printed.
      7. Artifacts: wheel and sdist members against
         dist_contents.py, METADATA's extras and
         Requires-Dist with no URL, the version.
      8. Dependencies, licences and the Python floor:
         python_floor.py, pip-audit, the licences hook and
         every reviewed exception, any Wheel-rule marker and
         its issue.
      9. Version and milestone tag: v1.0.0a2 is Phase 3's tag
         in ADR-0003's milestone table.
      10. Documentation and release notes: the data guide,
          keys guide, provider and concept pages on the
          preview; the draft docs/releases/1.0.0a2.md with
          the breaking change (manifest schema 2), model
          re-versions and known limitations.
      11. Monitoring: the latest providers-live and
          providers-heartbeat runs, the release smoke.
      12. Rollback: yank, then 1.0.0a2.post1 through the same
          pipeline; disabling a failing provider by
          configuration.
      13. Attribution and legal: every required notice in
          metadata and on its provider page; the FRED
          notice; the CFA® marks notice unchanged.
      14. Decision: the maintainer's GO or NO-GO, recorded
          as `Decision: GO — <YYYY-MM-DD> — <name>` (or
          NO-GO with its blockers), never filled in by the
          agent alone.
    </requirement>

    <requirement>
      A NO-GO: each blocker becomes an issue with its class
      (a model error is a High defect on a fix/ branch that
      bumps .devN); this step's PR records the NO-GO and its
      evidence, and a fresh Step 18 conversation rehearses
      the corrected candidate.
    </requirement>

    <requirement>
      Filepath comment: the readiness document and release
      notes follow docs/releases/'s convention.
    </requirement>
  </requirements>
</task>
```

### Step 18 acceptance criteria

- The readiness document lists the independently checked exact release
  provider set, with SEC's blocker, owner and follow-up if deferred. Every
  required non-SEC provider passes; no EDGAR capability is promised while
  absent. The rehearsed artifacts and maintainer decision cover this set.
- `v1.0.0a2.devN` is tagged on `main`, and TestPyPI lists its wheel and
  sdist, each with a provenance; the release smoke passed with and without
  extras.
- The live recipe passed from the rehearsed package: BLS without a FRED
  key (keyless through API v1, or with the maintainer's BLS key through
  v2, as recorded), and the Taylor rule for a past date on ALFRED vintages
  with the maintainer's FRED key, its manifest naming the vintages, with
  no key printed.
- `docs/releases/1.0.0a2-readiness.md` has all fourteen sections filled
  from commands run in this step, no unresolved FAIL, and the maintainer's
  recorded decision line; the draft release notes exist.
- **Deployed & verified:** TestPyPI's JSON and integrity APIs report both
  files of `1.0.0a2.devN` with provenances, and `release-smoke.yml`'s run
  for the tag reads `success`.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the whole-tree secret scan is clean, no
  repository secret exists, and the readiness document records no key or
  contact.

---

## Step 19 — 1.0.0a2 Release ✅

**Status:** Complete — PR #166 (2026-10-22)

> **Goal:** Release what the gate approved. On the step branch, set the
> version to `1.0.0a2` and make exactly the changes the readiness document
> lists — `CITATION.cff`, the README's status banner (the PyPI page), the
> documentation index's count (50 model families across 13 domains), a
> dated `[1.0.0a2]` CHANGELOG section, the release notes
> `docs/releases/1.0.0a2.md` (the data platform, 30 providers while SEC is
> deferred, otherwise 31; 18 new
> models, the manifest's schema 2 as a breaking change, the re-versioned
> models and the known limitations), `core/_released.py` extended to 50
> ids and `data/_released.py` filled with the release provider set and the
> released concept ids — re-running the ADR-0010 floor check and ADR-0003's
> milestone check first. After the merge, tag `v1.0.0a2` on `main`;
> `release.yml` builds, waits for the maintainer's approval in the `pypi`
> environment, publishes with attestations and runs the smoke from PyPI.
> Verify the release in clean environments with the ROADMAP's live recipe,
> confirm plain `pip install pyeconomics` still resolves 0.2.6, and publish
> the GitHub release as a pre-release. Parent: ROADMAP §4 3.8; ADR-0003.

**Branch:** `feature/phase03-step19-release`

**Prerequisites:** Step 18 Complete with a GO for this exact candidate and
release provider set. A still-deferred Step 7 or pending Sponsors application
adds no prerequisite. Release notes must disclose EDGAR's absence if deferred;
the ledger must match the rehearsed set, never the planned count alone.

**Deploys:** PyPI — `pyeconomics 1.0.0a2` as a pre-release, from tag
`v1.0.0a2` on the merged release commit, through the `pypi` environment's
approval; the GitHub release `v1.0.0a2`; the Read the Docs `main` preview
rebuilt at the merge commit with the release's guide. Plain `pip install
pyeconomics` keeps resolving 0.2.6.

| Setting      | Cost                                     | Balanced                               | Quality                                 |
| ------------ | ---------------------------------------- | -------------------------------------- | --------------------------------------- |
| Model        | GPT-6.1 Sol                              | GPT-6.1 Sol                            | Opus 5.5                                |
| Backup       | Sonnet 5.5 — Claude Code · Effort Medium | Opus 5.5 — Claude Code · Effort Medium | GPT-6.1 Sol — Codex · Intelligence High |
| Platform     | Codex                                    | Codex                                  | Claude Code                             |
| Effort       | Intelligence Low                         | Intelligence High                      | Effort High                             |
| Thinking     | —                                        | —                                      | On                                      |
| Conversation | **New**                                  | **New**                                | **New**                                 |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

> Settings updated 2026-10-18 (refresh): was GPT-6.1 Sol · Intelligence
> Medium. Agentic PRIMARY, coding SECONDARY, Medium: the ladder's Balanced
> column keeps GPT-6.1 Sol on Codex but at Intelligence High, with Opus 5.5 at
> Medium as backup.

> Ran 2026-10-22: Balanced — gpt-6.1-sol · high. Runs selected Balanced; the Codex pool has headroom.

**Model rationale:** Agentic work is PRIMARY and coding SECONDARY; complexity is Medium. The ladder's Balanced column runs: GPT-6.1 Sol on Codex at High, backup Claude Opus 5.5. The Cost and Quality columns, and the Backup under a tight or exhausted pool, are read off the table on the day. New conversation per phase-boundary hygiene.

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
       feature/phase03-step19-release`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
       shape "Step 19 is
       complete. You can now move
       on to Step 20." That
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
       one before Step 20.
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
      the pypi environment after the maintainer's approval:
      no token is created, stored or printed; the tag push
      is the maintainer's approved action.
    - The release commit's diff is exactly the gate's list;
      any other change to a file that ships in the wheel or
      sdist stops the release and returns it to the gate.
    - The live recipe reads the tester's keys only through
      the credential chain in an isolated configuration;
      the PR body and release notes record outcomes, never a
      key or a contact.
    - release_ledger.py writes its modules deterministically
      from the registries and nothing else.
  </security>

  <context>
    pyeconomics. Phase 3. Step 19: 1.0.0a2 release.

    Current state (as of Phase 3 Step 18):

    - docs/releases/1.0.0a2-readiness.md is on main with
      `Decision: GO`; its sections list the only changes the
      release commit may add and the rollback procedure; the
      rehearsal v1.0.0a2.devN is on TestPyPI with
      attestations and passed the smoke and the live recipe.
    - core/_released.py lists Phase 2's 32 ids;
      data/_released.py (Steps 4 and 11) is empty; validate()
      and pyeconomics.data.registry.validate() enforce
      whatever the ledgers hold.
    - The `pypi` environment requires the maintainer's
      approval; release.yml's smoke runs `smoke.py
      --min-domains 11`, a floor the 13 domains clear.
    - Phase 2's Step 14 is the pattern for every action
      below, including its review of the built artifacts
      against the rehearsal's.
    - Step 18 (PR #165, GO 2026-10-22) recorded the exact
      release provider set as all 31 source-plan ids
      (sec_edgar included, no deferral) and rehearsed
      1.0.0a2.dev1 at 610da6f. Its §7 lists the only
      release-commit changes allowed. The maintainer froze
      Dependabot PRs #98-#103 and #161 until 1.0.0a2
      publishes: merging any of them before the release
      changes the candidate. After the Deployed & verified
      check passes, rebase them and let them merge. The FRED
      key was rotated on 2026-10-22, in the keyring and in
      providers-live.

    Files to read (every file before drafting):
    - docs/releases/1.0.0a2-readiness.md, the draft
      docs/releases/1.0.0a2.md and docs/releases/1.0.0a1.md.
    - docs/adr/0003-versioning-and-deprecation.md and
      0010-python-support-policy.md.
    - .github/workflows/release.yml and release-smoke.yml.
    - pyproject.toml, README.md, CHANGELOG.md, CITATION.cff,
      docs/index.md, scripts/release_ledger.py,
      src/pyeconomics/core/_released.py and
      src/pyeconomics/data/_released.py.
  </context>

  <goal>
    pyeconomics 1.0.0a2 is on PyPI as a pre-release with
    attestations; its smoke is green from PyPI with and
    without extras; the live recipe passes from a clean
    install; plain `pip install pyeconomics` still installs
    0.2.6; the GitHub release v1.0.0a2 is a public
    pre-release; and the ledgers guard 50 model ids, the
    Phase 3 release provider set (30 or 31 ids) and the
    released concept ids.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff: Step 18 reads Complete and the readiness
      document reads `Decision: GO`. Batch one request to the
      maintainer: approve the push of tag v1.0.0a2, the
      `pypi` deployment it triggers, the GitHub release, and
      the live recipe with their keys. Re-run
      scripts/checks/python_floor.py; if NumPy or SciPy moved
      their floor since the gate, raise requires-python and
      update the matrix and classifiers in the same change
      (ADR-0010), narrowing earlier verifier checks with
      addendum lines. Confirm v1.0.0a2 is Phase 3's tag in
      ADR-0003's milestone table.
    </requirement>

    <requirement>
      Ledgers: extend scripts/release_ledger.py so it also
      writes src/pyeconomics/data/_released.py from the
      installed provider registry and catalog (provider and
      concept ids, each with its first version), with
      `--check` failing when a registered id is missing;
      cover it in tests/checks/test_release_ledger.py. Run it
      for 1.0.0a2: core/_released.py lists 50 ids (the 18
      new ones first released in 1.0.0a2) and
      data/_released.py the exact release provider set and the released
      concepts; validate() and
      pyeconomics.data.registry.validate() pass.
    </requirement>

    <requirement>
      The release commit: `uv version 1.0.0a2 --no-config`;
      CITATION.cff's version and date-released; README's
      status banner (1.0.0a2 is a pre-release installed with
      `pip install --pre pyeconomics==1.0.0a2`, what it adds,
      the data guide and keys guide links, and that 0.2.6
      remains what plain `pip install pyeconomics` installs);
      docs/index.md's count; CHANGELOG's [Unreleased] becomes
      `[1.0.0a2] - <YYYY-MM-DD>`; and docs/releases/1.0.0a2.md
      completed from the gate's draft. Before the PR merges,
      build the wheel and sdist and compare their members and
      contents with the rehearsal's: the only differences are
      the readiness document's list.
    </requirement>

    <requirement>
      Release: after the merge, tag main's merge commit
      v1.0.0a2 and push the tag; watch release.yml's verify
      and build jobs; the maintainer approves the `pypi`
      deployment; watch publish-pypi and the smoke (one model
      per domain, then the extras pass) to green. A failure
      after publication follows the gated rollback (yank,
      then 1.0.0a2.post1), never a re-upload of the same
      version.
    </requirement>

    <requirement>
      Verification, from outside the checkout with the
      project's interpreter: a fresh venv with
      `pip install --pre pyeconomics==1.0.0a2` runs
      `scripts/smoke.py --all --min-domains 13`; a second with
      `[econometrics,plot]` runs `--extras` and `pip check`
      (on CPython 3.15 the extras pass reports
      econometrics.garch's named arch gap, issue #154, and
      passes);
      with an isolated configuration and no FRED key, a BLS
      series is fetched (keyless through API v1, or through v2
      when the tester's BLS_API_KEY is set; record which);
      with the tester's FRED key through the chain, the Taylor
      (1993) rule runs for a past date on ALFRED vintages and
      its manifest names them; a third, plain
      `pip install pyeconomics`, installs 0.2.6. Record each
      outcome in the PR body, never a key.
    </requirement>

    <requirement>
      GitHub release: `gh release create v1.0.0a2
      --prerelease --verify-tag` with docs/releases/1.0.0a2.md
      as the notes, linking the docs preview's data guide and
      the PyPI page; nothing is announced elsewhere (Phase 5
      announces 1.0).
    </requirement>

    <requirement>
      Filepath comment: release_ledger.py's changes and its
      test keep the three-line header; each generated
      _released.py keeps the header and states that the
      script writes it.
    </requirement>
  </requirements>
</task>
```

### Step 19 acceptance criteria

- `v1.0.0a2` is tagged on `main`'s merge commit; `pyproject.toml`,
  `CITATION.cff` and the dated `[1.0.0a2]` CHANGELOG section agree; the
  release notes and README describe the pre-release and its limitations.
- `core/_released.py` lists the 50 launch-catalog ids and
  `data/_released.py` the exact release provider set and the released concept ids;
  `validate()`, `pyeconomics.data.registry.validate()` and
  `release_ledger.py --check` pass.
- The built artifacts differ from the rehearsal's only by the readiness
  document's list.
- **Deployed & verified:** PyPI's `1.0.0a2` lists a wheel and an sdist,
  each with a provenance; a clean `pip install --pre
  pyeconomics==1.0.0a2` runs the smoke across 13 domains, with extras too;
  with no FRED key it fetches a BLS series (keyless or with the tester's
  BLS key, as recorded), and with the tester's own FRED key it runs the
  Taylor rule for a past date on ALFRED vintages, the manifest naming
  them; plain `pip install pyeconomics` installs 0.2.6; the GitHub release
  `v1.0.0a2` is a published pre-release; and Read the Docs' `main` preview
  serves the data guide at the merge commit.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — publication used Trusted Publishing
  only, and no key or contact appears in the PR, the release or its
  notes.

---

## Step 20 — QA and Verification Script

**Status:** Not started

> **Goal:** Package the phase's verification matrix into
> `scripts/verify-phase03.sh` — the same `--fast`, `--python`,
> `--security`, `--live`, `--all` and `--post` modes as
> `verify-phase02.sh`, with independent static checks for every Step 1–19
> deliverable, Step 20 self-checks and the V1–V20 matrix — plus its pytest
> twin `tests/repo/test_phase03.py`; produce `docs/phase03-qa-findings.md`,
> the rollup of every finding, its class, its destination and its guard;
> add `"03"` to `.github/workflows/phase-verify.yml`'s matrix and make both
> `phase-verify` jobs for `03` required; prove the providers-live alarm
> and the heartbeat alarm with synthetic failures that reach the
> maintainer; run `verify-phase01.sh --post` and `verify-phase02.sh --post`
> to show the earlier ledgers still hold; and mark Phase 3 complete here
> and in the parent roadmap. Parent: ROADMAP §5 "Operations &
> observability strategy" ("Acceptance") and this roadmap's Post-
> Implementation Verification.

**Branch:** `feature/phase03-step20-verify`

**Prerequisites:** Step 19 Complete. Step 7 delivered SEC EDGAR in PR #124;
all 31 source-plan providers are required. No SEC deferral remains active.

**Deploys:** nothing beyond merge — the CI matrix entry is live on merge;
the required-check update and the synthetic alarms are part of the step.

| Setting      | Cost                                     | Balanced                                | Quality                                 |
| ------------ | ---------------------------------------- | --------------------------------------- | --------------------------------------- |
| Model        | GPT-6.1 Sol                              | Opus 5.5                                | Opus 5.5                                |
| Backup       | Sonnet 5.5 — Claude Code · Effort Medium | GPT-6.1 Sol — Codex · Intelligence High | GPT-6.1 Sol — Codex · Intelligence High |
| Platform     | Codex                                    | Claude Code                             | Claude Code                             |
| Effort       | Intelligence Low                         | Effort Medium                           | Effort High                             |
| Thinking     | —                                        | On                                      | On                                      |
| Conversation | **New**                                  | **New**                                 | **New**                                 |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

> Settings updated 2026-10-18 (refresh): was GPT-6.1 Sol · Intelligence
> Medium. Coding PRIMARY, agentic SECONDARY, Medium: the ladder's Balanced
> column is Opus 5.5 at Medium on Claude Code, with GPT-6.1 Sol at
> Intelligence High as backup; the old pick was Codex.

**Model rationale:** Coding is PRIMARY and knowledge or agentic work SECONDARY; complexity is Medium and the step is not novel. The ladder's Balanced column runs: Claude Opus 5.5 on Claude Code at Medium, backup GPT-6.1 Sol. The Cost and Quality columns, and the Backup under a tight or exhausted pool, are read off the table on the day. New conversation per phase-boundary hygiene.

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
       feature/phase03-step20-verify`
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
       Phase 3 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 3`
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
       shape "Step 20 is
       complete. Phase 3 is
       complete. You can now move
       on to Phase 4." That
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
       one before Phase 4.
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
    - This step authors the --security mode, so its own diff
      must still pass the gate before commit. --security runs
      the whole-tree gate, semgrep-test, the import
      allowlist, an orphan-clone secret scan and a cassette
      scan; it exits non-zero on any finding.
    - The verifier never prints a key, a contact or an
      environment value: --live checks secrets by name only
      (`gh secret list --env providers-live --json name`),
      never by value, and --post's live recipe reads keys
      only through the credential chain.
    - The synthetic alarms are dispatched runs with the
      documented inputs; nothing weakens a workflow's
      permissions or triggers to stage them.
    - The phase-verify change keeps permissions: {} and the
      existing per-job permissions; zizmor stays clean.
  </security>

  <context>
    pyeconomics. Phase 3. Step 20: QA and verification
    script.

    Steps 1 through 19 have been implemented, including SEC
    EDGAR in PR #124: 1.0.0a2 is on PyPI; the exact
    31-id release provider set, catalog, bindings and 18 new
    models are on main; providers-live.yml and
    providers-heartbeat.yml run on schedule.

    Reference scripts (pattern templates):
    - scripts/verify-phase02.sh (the structural template: the
      mode contract, record / check / vcheck / vstatic, the
      `PASS  12     <description>` format, the per-mode
      summary, the stdlib-only Python static checks and the
      Bash secret-pattern check).
    - scripts/verify-phase01.sh (the --live and --post
      patterns, the planted-finding proof) and
      tests/repo/test_phase02.py (the pytest twin).

    Phase 3 deliverables to verify — static checks 1–73
    across Steps 1–19 and self-checks 74–78, numbered as
    below so the script, its V-matrix and this roadmap
    agree; each an independent, "at least" invariant a later
    phase will not break:

    Step 1 (checks 1–3): the roadmap and kit tracked; the
    regression tests for #75, #81 and #85 present; the
    errata entry for the IRR fix.
    Step 2 (4–8): ADR-0011 Accepted with eighteen numbered
    decisions; core/provenance.py and data/'s value modules;
    the data coverage floor; smoke imports pyeconomics.data;
    ROADMAP §4 3.3, 3.4, 3.7 and 3.8 amended (no opt-in FRED
    cache) and phase02-roadmap.md's Phase 3 addendum present.
    Step 3 (9–14): the credential, config and redaction
    modules; the secret-reveal rule and its tests; the
    [keyring] extra; platformdirs; the keys guide; the
    canary harness.
    Step 4 (15–21): the provider base, registry, transport
    and modes; the pyeconomics.providers group; the live
    marker deselected by default with --disable-socket kept;
    the recorder and the contract suite; the Bloomberg spike
    and no blpapi import anywhere; the provider pages and
    the writing-a-provider guide; the notice tests.
    Step 5 (22–23): the cache modules; ADR-0005's no-storage
    test.
    Step 6 (24–29): fred, bls, bea and census and their
    entry points; synthetic FRED cassettes;
    providers-live.yml with schedule and dispatch triggers
    only; providers-heartbeat.yml likewise; permissions: {}
    at the top of both and issues: write only in the report
    job and the heartbeat job; the ALFRED test's citations.
    Step 7 (30–32): the four recovered keyless providers;
    EDGAR only when verified and released; otherwise the
    named SEC deferral recorded in readiness and QA, with
    no SEC entry point or catalog candidate. No "Build Your
    Package" URL; openpyxl and defusedxml. These checks
    must fail for any missing required provider or partial
    EDGAR registration; report the SEC deferral explicitly
    rather than reporting its provider tests as passed.
    Step 8 (33–35): the [sdmx] extra; the seven providers;
    certifi's reviewed exception.
    Step 9 (36–38): the five research providers; no TBD class
    left in the source plan; ROADMAP §4 3.7's classification
    note updated.
    Step 10 (39–43): the ten providers; the [yfinance] extra;
    yfinance barred from automation; Yahoo absent from the
    egress allowlist; xlrd.
    Step 11 (44–47): the catalog and resolver; the public
    data API; the data guide and concept pages;
    core/transforms.py and the ledger's concepts section.
    Step 12 (48–52): core/binding.py; @model's bindings
    parameter; manifest schema 2 or later; describe()'s
    bindings key; new_model.py --bound.
    Step 13 (53–56): the macro package and entry point; both
    models' golden files; the legacy parity test reading
    tests/fixtures/legacy/; those files matching their
    manifest's SHA-256 values.
    Step 14 (57–59): the six macro modules; their golden
    files; core/regression.py.
    Step 15 (60–61): the four modules; their golden files.
    Step 16 (62–64): the asset_pricing package and entry
    point; the four modules; their golden files.
    Step 17 (65–66): the two modules and their golden files;
    arch in [econometrics] (with any approved marker).
    Step 18 (67–68): the readiness document's fourteen
    sections and its `Decision: GO` line; a v1.0.0a2.dev*
    tag on main.
    Step 19 (69–73): the v1.0.0a2 tag; the dated CHANGELOG
    section; the model ledger holding every id of this
    roadmap's table; the provider ledger holding the exact
    release provider set recorded by readiness; the release
    notes disclose SEC when deferred.
    Step 20 self-checks (74–78): verify-phase03.sh exists
    and is executable; docs/phase03-qa-findings.md exists;
    docs/roadmap/phase03-roadmap.md exists; phase-verify.yml's
    matrix includes "03" (77); and the security backstop —
    the gate's hooks configured, the security workflow
    present, no private-key, AWS, GitHub or PyPI token
    pattern in the tree (patterns assembled at run time),
    and no workflow but providers-live.yml reading a secret.

    Files to read:
    - scripts/verify-phase02.sh end to end, then
      scripts/verify-phase01.sh's --live and --post sections.
    - tests/repo/test_phase02.py, .github/workflows/
      phase-verify.yml, providers-live.yml and
      providers-heartbeat.yml.
    - docs/phase02-qa-findings.md (the rollup's shape) and
      every Phase 3 PR body (findings and their
      destinations).
  </context>

  <goal>
    scripts/verify-phase03.sh with the static checks, the
    self-checks and the V1–V20 matrix in six modes;
    tests/repo/test_phase03.py; docs/phase03-qa-findings.md;
    "03" in phase-verify.yml's matrix and required; both
    alarms proven; the earlier phases' --post green; and
    Phase 3 marked complete in both roadmaps.
  </goal>

  <requirements>
    <requirement>
      Read scripts/verify-phase02.sh end to end for its
      structure, flag parsing, output format, helpers and
      summary, and mirror them exactly so the Phase 3 script
      is visually continuous with Phase 2's in CI logs.
    </requirement>

    <requirement>
      scripts/verify-phase03.sh modes:
      - --fast (default): the static checks only, CI-safe on
        Ubuntu, standard-library Python and Bash, no network,
        no package import; under 30 seconds.
      - --python: static checks plus `uv sync --locked
        --all-extras --group docs`, ruff, mypy, the full
        suite with coverage and the floors (core, models,
        data), registry and provider validation, the docs
        build with every model, provider and concept page,
        the build and artifact checks, and the clean-wheel
        smoke across 13 domains with and without extras, on
        the project's interpreter.
      - --security: the whole-tree gate, semgrep-test, the
        import allowlist, an orphan-clone secret scan and the
        cassette scan.
      - --live: the maintainer's gh session: the newest
        successful providers-live run on main is younger
        than eight days (V6.3, which proves the secrets'
        values) and the newest providers-heartbeat run on
        main succeeded; providers-live's deployment policy is
        main and its secrets exist by name (configuration
        only); no repository secret exists; main requires
        phase-verify-fast (03) and phase-verify-security (03)
        strictly; PyPI and TestPyPI list 1.0.0a2 and the
        rehearsal with provenances; the GitHub pre-release;
        Read the Docs serves the data guide on main and 0.2.6
        on stable.
      - --all: --fast, --python and --security.
      - --post: --all and --live, plus the published
        installs (V19.3) with scripts/verify_phase03_live.py
        (isolated configuration/cache, ambient keys removed,
        credential-chain reads, fixed verdict output), the alarm
        evidence (V20.5), verify-phase01.sh --post and
        verify-phase02.sh --post (V20.6), and `gh pr checks`
        for the current branch.
      Every static check uses grep, test, git ls-files or the
      standard library, prints one PASS or FAIL line with its
      number, and is independent of the others.
    </requirement>

    <requirement>
      The V-matrix mirrors this roadmap's Post-Implementation
      Verification section exactly: Vn.1 aggregates Step n's
      static checks; Vn.2 onward are the command checks each
      V table names; V20.1–V20.8 cover --fast in CI, the
      matrix entry, all static checks, --security, the
      alarms, the earlier phases, the required checks and the
      providers-live environment.
    </requirement>

    <requirement>
      tests/repo/test_phase03.py, the twin of the
      self-checks: test_roadmap_doc_exists,
      test_qa_findings_doc_exists,
      test_verify_script_exists_and_executable (mode 100755
      in the index) and test_phase_verify_matrix_includes_03.
    </requirement>

    <requirement>
      .github/workflows/phase-verify.yml: append "03" to both
      matrix lists, nothing else. Once both jobs pass on this
      PR, the maintainer (batched at kickoff) adds
      phase-verify-fast (03) and phase-verify-security (03)
      to main's required checks, re-sending every existing
      context, strict.
    </requirement>

    <requirement>
      Alarms (ROADMAP §5 "Acceptance"): dispatch
      providers-live.yml on main with simulate_failure: true;
      the run fails, the report job opens one provider-live
      issue and closes older ones, and GitHub's failure
      notification reaches the maintainer, who confirms it;
      dispatch providers-heartbeat.yml with a zero maximum
      age (its documented test input) and see it fail and
      open its issue. Record both runs' URLs and the line
      `Notification received: confirmed by the maintainer` in
      docs/phase03-qa-findings.md, then close the synthetic
      issues with a comment pointing at the QA document.
      Finally dispatch both workflows again with their
      default inputs and see both succeed, so the newest
      runs on main are green before --live and --post run.
    </requirement>

    <requirement>
      docs/phase03-qa-findings.md: one rollup per step (Steps
      1–19) as a table of finding, class, destination and
      guard; a Step 20 verification rollup; the synthetic
      alarms; a Phase 3 acceptance audit against ROADMAP §4
      3's acceptance criteria; Pre-ship items with an owner
      for every open issue (and the Wheel-rule markers); and
      the final verification evidence.
    </requirement>

    <requirement>
      Cross-phase: run verify-phase01.sh --post and
      verify-phase02.sh --post; a check Phase 3 legitimately
      broke is narrowed under the Cross-phase verification
      rule with an addendum line at the end of that phase's
      roadmap, never deleted.
    </requirement>

    <requirement>
      Mark the phase complete in the parent project roadmap
      (docs/roadmap/ROADMAP.md) in the SAME Stage-3 commit
      that marks this step (Status rule):
      - `### Phase 3` gets `**Status:** Complete —
        <YYYY-MM-DD>; PR #<n>; v1.0.0a2;
        phase03-roadmap.md` directly under its heading, and
        the heading ends in ✅.
      - Its row in the "Phase Complexity Summary" table reads
        `Complete` (Step 1's PR set it to `In progress`).
      - The header `> **Status:**` line names Phase 3 as
        shipped and Phase 4 as next.
      - Consistency audit: the Phase 3 "Acceptance criteria"
        there match this roadmap's V1–V20 checks, as amended
        by Steps 2 and 9 and the external-approval exception.
      And in THIS roadmap, same commit: its phase-level
      `**Status:**` line reads `Complete — <YYYY-MM-DD>`, the
      title and every required step heading end in ✅, and
      their Summary Table Status cells read `Complete — PR #<n>`.
      If SEC remains deferred, preserve Step 7's unfinished
      heading, Status line and Summary Table cell; carry its
      named blocker and follow-up into QA and Phase 4.
    </requirement>

    <requirement>
      The script is executable (`git update-index
      --chmod=+x`), prints a clear PASS or FAIL per check,
      exits 0 on success and 1 on any failure, and mirrors
      verify-phase02.sh's output format, numbering and summary
      table. --fast completes in under 30 seconds on Ubuntu
      CI. Never edit the script while a run of it is in
      progress (Phase 2's lesson).
    </requirement>

    <requirement>
      Filepath comment: the script `# scripts/verify-phase03.sh`
      after its shebang; the test file the three-line header;
      the QA document follows docs/'s convention.
    </requirement>
  </requirements>
</task>
```

### Step 20 acceptance criteria

- The verifier compares the exact 31-id source-plan set, including SEC
  EDGAR delivered in PR #124, with the readiness record, installed providers
  and released-id ledger. Any omission or partial EDGAR registration fails.
  QA records SEC access as resolved; there is no SEC blocker or follow-up
  to carry into Phase 4. Phase completion preserves Step 7's Complete status.
- `scripts/verify-phase03.sh` exists, is executable, and passes on a clean
  tree post-implementation, with its static checks, Step 20 self-checks and
  the V1–V20 matrix in all six modes.
- `--fast` runs in under 30 seconds on Ubuntu CI, and `--post` passes on
  the maintainer's machine with every live check and published install
  green.
- `docs/phase03-qa-findings.md` is complete with every rollup section, the
  alarm evidence, the acceptance audit and the pre-ship owners.
- `.github/workflows/phase-verify.yml`'s matrix includes `03`, both jobs
  pass on every PR, and `main` requires them, strictly.
- `--security` exists and exits 0 (secret/PII scan, SAST, dependency audit
  and the cassette scan clean over the phase's surface); V20.4 is green.
- Branch protection still passes on the resulting PR, and
  `verify-phase01.sh --post` and `verify-phase02.sh --post` pass.
- **Operations:** the providers-live run and the heartbeat are this
  phase's runtime surface; each failed once on a synthetic dispatch, each
  opened its `provider-live` issue, and the maintainer confirmed the
  failure notification, recorded in `docs/phase03-qa-findings.md` with
  both run URLs (ROADMAP §5 "Operations & observability strategy").
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff and the security workflow is
  green.
- **Phase closed, every finding assigned.** Every finding recorded in
  `docs/phase03-qa-findings.md` has a destination (fixed, an issue number,
  or a named phase that owns it), the "Not in scope" section below is
  current, and no un-tracked item remains. Every required step of this roadmap,
  this one included, reads `**Status:** Complete — PR #…` on `main` under a ✅
  heading. If SEC is deferred, Step 7 alone keeps its unfinished status,
  heading and Summary Table cell, with its named carry-over recorded. All
  other Summary Table Status cells and this roadmap's
  phase-level Status line say `Complete` under a ✅ title, and the parent
  project roadmap's Phase 3 entry (under a ✅ heading), its summary-table
  row, and its header status line say `Complete` — all landed in this
  step's PR. This step's final response ends with two lines and nothing
  after them: "Step 20 is complete. Phase 3 is complete. You can now move
  on to Phase 4." — same Stage 6 rule: no "Follow-ups", no trailer.

---

## Post-Implementation Verification

Every V1–V20 check below runs **automatically in CI** on every push and
pull request — no manual invocation required — except three kinds. The
`--live` and `--post` checks read state that needs the maintainer's
authenticated `gh` session (branch protection, environments and their
secrets by name, the latest scheduled runs, the GitHub release), external
registries and services (PyPI, TestPyPI and their integrity APIs, the Read
the Docs API), clean-venv installs from PyPI with the maintainer's own
keys, and the operator-observed alarm notification; they run on the
maintainer's machine with `./scripts/verify-phase03.sh --post` before Phase
3 is declared complete. The live provider suite runs on schedule, weekly,
in `providers-live.yml`, and `--live` reads its latest result.

| Mode             | Workflow                                              | Runner                   | Coverage                                                                  |
| ---------------- | ----------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------- |
| `--fast`         | `phase-verify.yml` (matrix entry `03`, fast job)      | Ubuntu                   | Static checks 1–78; V1.1–V19.1, V20.1–V20.3                               |
| `--python`       | `ci.yml` (lint, types, tests, package, pyodide and docs jobs run the same commands); local | Ubuntu, Windows, macOS | V1.2, V2.2, V3.2, V4.2, V5.2, V6.2, V7.2, V8.2, V9.2, V10.2, V11.2, V12.2, V13.2, V14.2, V15.2, V16.2, V17.2, V17.3 |
| `--security`     | `phase-verify.yml` (security job); `security.yml`     | Ubuntu                   | V3.3, V4.3, V20.4 (secret/PII scan + SAST + dependency audit + licences + cassette scan) |
| `--live`         | local only — the maintainer's `gh` session            | Maintainer's machine     | V1.3, V2.3, V6.3, V11.3, V13.3, V15.3, V18.2, V19.2, V20.7, V20.8         |
| `--all`          | local                                                 | Any                      | `--fast` + `--python` + `--security`                                      |
| `--post`         | local, before the phase is declared complete          | Maintainer's machine     | `--all` + `--live` + V19.3, V20.5, V20.6 + `gh pr checks`                 |

Local invocations remain available for ad-hoc runs and pre-release
sweeps:

```bash
./scripts/verify-phase03.sh --post   # static + V1-V20 + live + post checks
```

`--post` is the canonical command to run before declaring Phase 3
complete, and before tagging a later phase's release.

Other modes:

```bash
./scripts/verify-phase03.sh              # static checks (same as --fast)
./scripts/verify-phase03.sh --fast       # static checks only (Ubuntu CI)
./scripts/verify-phase03.sh --python     # static + lint, types, tests, docs, build
./scripts/verify-phase03.sh --security   # secrets, SAST, dep audit, licences, cassettes
./scripts/verify-phase03.sh --live       # GitHub, PyPI, TestPyPI, RTD (local)
./scripts/verify-phase03.sh --all        # static + python + security
```

The script reports each V-check by id (V1.1, V2.1, …) so a failure in any
workflow above maps directly to the corresponding row below.

### V1 — Core hardening and the 1.0.0a2 baseline

> **Automated in CI.** `phase-verify.yml` → V1.1; `ci.yml` → V1.2;
> `--live` → V1.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V1.1 | Static checks 1–3 all PASS (roadmap and kit tracked; the #75, #81 and #85 regression tests; the IRR erratum). | `phase-verify.yml` runs `verify-phase03.sh --fast` on every push/PR. |
| V1.2 | The unit-marker, validate() and root-finding regressions pass, with the endpoint golden cases, on every CI cell. | `ci.yml` tests matrix (`--python` locally). |
| V1.3 | Issues #75, #81 and #85 are closed.                                | `--live` (`gh issue view`).                                               |

### V2 — ADR-0011 and the data model

> **Automated in CI.** `phase-verify.yml` → V2.1; `ci.yml` → V2.2 and the
> `pyodide` job behind V2.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V2.1 | Static checks 4–8 all PASS (ADR-0011 Accepted with eighteen decisions; `core/provenance.py` and the value modules; the data floor; the smoke imports `pyeconomics.data`; ROADMAP §4 3.3, 3.4, 3.7 and 3.8 amended, and `phase02-roadmap.md`'s Phase 3 addendum). | `phase-verify.yml --fast`. |
| V2.2 | The value-type unit, property and doctest suites pass, and the `data` coverage floor holds. | `ci.yml` tests matrix with `coverage_floors.py` (`--python` locally). |
| V2.3 | The `pyodide` job is green on `main`'s HEAD: the wheel imports `pyeconomics.data` and builds a `Series`. | `ci.yml` `pyodide` job; `--live` reads its latest run on `main`. |

### V3 — Credentials, configuration and redaction

> **Automated in CI.** `phase-verify.yml` → V3.1 and V3.3; `ci.yml` →
> V3.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V3.1 | Static checks 9–14 all PASS.                                       | `phase-verify.yml --fast`.                                                |
| V3.2 | The key chain, configuration and redaction tests and the canary suite pass on all twelve cells. | `ci.yml` tests matrix (`--python` locally).          |
| V3.3 | The `secret-reveal` rule passes `semgrep-test`, and `credential-logging` stays green over the tree. | `phase-verify.yml` security job; `security.yml` gate-sast. |

### V4 — Provider SDK, transport and contract suite

> **Automated in CI.** `phase-verify.yml` → V4.1 and V4.3; `ci.yml` →
> V4.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V4.1 | Static checks 15–21 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V4.2 | The contract suite passes offline for every registered provider; the transport, rate-limit and hosted-refusal tests pass. | `ci.yml` tests matrix (`--python` locally). |
| V4.3 | Every cassette passes the scan: no credential, synthetic where the Recording rule requires, within the size caps. | `ci.yml` tests; `phase-verify.yml` security job (`--security`). |

### V5 — Cache and offline mode

> **Automated in CI.** `phase-verify.yml` → V5.1; `ci.yml` → V5.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V5.1 | Static checks 22–23 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V5.2 | The cache tests pass, ADR-0005's no-storage test and the cache-file canary included. | `ci.yml` tests matrix (`--python` locally).            |

### V6 — Providers: FRED and ALFRED, BLS, BEA, Census

> **Automated in CI.** `phase-verify.yml` → V6.1; `ci.yml` → V6.2;
> `providers-live.yml` and `providers-heartbeat.yml` on schedule, read by
> `--live` → V6.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V6.1 | Static checks 24–29 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V6.2 | Their contract and provider tests pass offline, with the ALFRED vintage tests. | `ci.yml` tests matrix (`--python` locally).                 |
| V6.3 | The newest successful `providers-live` run on `main` is younger than eight days — an authenticated round-trip that proves the environment's secret values — and the newest heartbeat run on `main` succeeded. | `--live` (`gh run list`). |

### V7 — Providers: Treasury, Fed Board, New York Fed, EDGAR, OpenFIGI

> **Automated in CI.** `phase-verify.yml` → V7.1; `ci.yml` → V7.2.

Apply the Overview's named SEC exception: checks 30–32 and the four recovered
providers remain mandatory. When EDGAR is deferred, verify its recorded
deferral and absence from the shipped entry points and catalog; report its
unrun tests as deferred, never PASS. Include its contact canary and full
contract only when Step 7 delivers it. This is not a generic optional-provider
skip: any other missing source, or partially enabled EDGAR, fails verification.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V7.1 | Static checks 30–32 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V7.2 | Shipped providers' contract and provider tests pass offline; the SEC-contact canary is required when EDGAR is delivered, otherwise its named deferral is verified. | `ci.yml` tests matrix (`--python` locally). |

### V8 — Providers: SDMX sources, World Bank, DBnomics

> **Automated in CI.** `phase-verify.yml` → V8.1; `ci.yml` → V8.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V8.1 | Static checks 33–35 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V8.2 | Their contract and series-level licence tests pass offline, and the `[sdmx]` closure passes the `licences` hook. | `ci.yml` tests matrix; `security.yml` gate-licences. |

### V9 — Providers: regional Fed research, CBO, Penn World Table

> **Automated in CI.** `phase-verify.yml` → V9.1; `ci.yml` → V9.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V9.1 | Static checks 36–38 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V9.2 | Their contract tests and the vintage-matrix tests pass offline.    | `ci.yml` tests matrix (`--python` locally).                               |

### V10 — Providers: asset-pricing and market research data

> **Automated in CI.** `phase-verify.yml` → V10.1; `ci.yml` → V10.2.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V10.1 | Static checks 39–43 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V10.2 | Their contract and archive-safety tests pass offline, and yfinance refuses until enabled. | `ci.yml` tests matrix (`--python` locally).     |

### V11 — Semantic catalog and resolver

> **Automated in CI.** `phase-verify.yml` → V11.1; `ci.yml` → V11.2;
> `--live` → V11.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V11.1 | Static checks 44–47 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V11.2 | Every concept resolves offline; hosted mode refuses each class it must; transforms and alignment match hand computations. | `ci.yml` tests matrix (`--python` locally). |
| V11.3 | Read the Docs serves the data guide and concept pages from `main`'s HEAD, and `/en/stable/` still serves 0.2.6. | `--live` (Read the Docs API and page text). |

### V12 — Live bindings and vintage-aware runs

> **Automated in CI.** `phase-verify.yml` → V12.1; `ci.yml` → V12.2.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V12.1 | Static checks 48–52 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V12.2 | The binding, bind/run and manifest-schema-2 tests and the narrowed Phase 2 tests pass; bound manifests are deterministic. | `ci.yml` tests matrix (`--python` locally). |

### V13 — Monetary-policy suite

> **Automated in CI.** `phase-verify.yml` → V13.1; `ci.yml` → V13.2;
> `providers-live.yml`, read by `--live` → V13.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V13.1 | Static checks 53–56 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V13.2 | The policy-rule and neutral-rate golden cases (the Monetary Policy Report, the Atlanta Fed and the Cleveland Fed), property, contract and legacy-parity tests pass. | `ci.yml` tests matrix (`--python` locally). |
| V13.3 | The live Taylor-rule test on ALFRED vintages passed in the latest scheduled run. | `providers-live.yml`; `--live` reads it.                  |

### V14 — Launch catalog: macroeconomics

> **Automated in CI.** `phase-verify.yml` → V14.1; `ci.yml` → V14.2.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V14.1 | Static checks 57–59 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V14.2 | The six models pass their golden, property, contract and oracle tests, and `core/regression.py` agrees with statsmodels. | `ci.yml` tests matrix (`--python` locally). |

### V15 — Launch catalog: fixed income and equity

> **Automated in CI.** `phase-verify.yml` → V15.1; `ci.yml` → V15.2;
> `providers-live.yml`, read by `--live` → V15.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V15.1 | Static checks 60–61 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V15.2 | The four models pass their golden (the GSW and ECB curves included), property, contract and oracle tests. | `ci.yml` tests matrix (`--python` locally). |
| V15.3 | The live CAPE check reproduced Shiller's published values in the latest scheduled run. | `providers-live.yml`; `--live` reads it.           |

### V16 — Launch catalog: asset pricing and portfolio

> **Automated in CI.** `phase-verify.yml` → V16.1; `ci.yml` → V16.2.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V16.1 | Static checks 62–64 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V16.2 | The four models pass their golden, property, contract and oracle tests, and `scripts/smoke.py` runs one model in each of 13 domains. | `ci.yml` tests matrix and package job (`--python` locally). |

### V17 — Launch catalog: econometrics

> **Automated in CI.** `phase-verify.yml` → V17.1; `ci.yml` → V17.2 and
> V17.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V17.1 | Static checks 65–66 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V17.2 | The two models pass their golden, property, contract and oracle tests, and the registry includes all 50 launch-catalog ids (later phases may add ids). | `ci.yml` tests matrix (`--python` locally). |
| V17.3 | Without extras, both models name `pyeconomics[econometrics]`; with it, they run; any Wheel-rule marker behaves as its test asserts. | `ci.yml` package job's two clean venvs (`--python` locally). |

### V18 — 1.0.0a2 readiness gate

> **Automated in CI.** `phase-verify.yml` → V18.1; `--live` → V18.2.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V18.1 | Static checks 67–68 PASS: the readiness document has fourteen sections, no unresolved FAIL and a `Decision: GO` line; a `v1.0.0a2.dev*` tag is on `main`. | `phase-verify.yml --fast`. |
| V18.2 | TestPyPI's `1.0.0a2.devN` lists a wheel and an sdist, each with a provenance. | `--live` (TestPyPI JSON and integrity APIs).                 |

### V19 — 1.0.0a2 release

> **Automated in CI.** `phase-verify.yml` → V19.1; `--live` → V19.2;
> `--post` → V19.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V19.1 | Static checks 69–73 PASS (`v1.0.0a2` on `main`, the dated CHANGELOG section, the model ledger with every id of this roadmap's table, the provider ledger with the exact 30- or 31-id release set, the release notes and any SEC deferral). | `phase-verify.yml --fast`. |
| V19.2 | PyPI's `1.0.0a2` lists a wheel and an sdist, each with a provenance, and the GitHub release `v1.0.0a2` is a published pre-release. | `--live` (PyPI JSON and integrity APIs; `gh release view`). |
| V19.3 | A clean `pip install --pre pyeconomics==1.0.0a2` runs `scripts/smoke.py --all --min-domains 13`, and with its extras `--extras`; with no FRED key it fetches a BLS series (keyless through API v1, or through v2 with the tester's BLS key, as recorded); with the tester's own FRED key it runs the Taylor rule for a past date on ALFRED vintages; plain `pip install pyeconomics` installs 0.2.6. | `--post`. |

### V20 — CI integration + security

> **Automated in CI.** `phase-verify.yml` → V20.1 through V20.4 and the
> `01` and `02` entries behind V20.6 on every push/PR; `--post` → V20.5
> and V20.6; `--live` → V20.7 and V20.8.

| ID         | Check                                                          | Automation                                                                |
| ---------- | -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V20.1      | `verify-phase03.sh --fast` exits 0 on Ubuntu CI.               | `phase-verify.yml` matrix entry `03`.                                     |
| V20.2      | `phase-verify.yml` matrix includes `03`.                       | `phase-verify.yml --fast` static check 77.                                |
| V20.3      | All static checks in `verify-phase03.sh` pass.                 | `phase-verify.yml --fast` records PASS only when no static check failed. |
| V20.4      | `verify-phase03.sh --security` exits 0 (secret/PII scan + SAST + dependency audit + licences + cassette scan clean). | `phase-verify.yml` security job on every push/PR. |
| V20.5      | The providers-live and heartbeat alarms each fired once on a synthetic failure, opened their issue, and the notification reached the maintainer. | `--post` reads the recorded runs' conclusions; the notification is recorded in `docs/phase03-qa-findings.md`. |
| V20.6      | Phases 1 and 2 stay green: `verify-phase01.sh` and `verify-phase02.sh --fast` exit 0 on every PR, and both `--post` runs pass before the phase closes. | `phase-verify.yml` matrix entries `01` and `02`; `--post`. |
| V20.7      | `main` requires `phase-verify-fast (03)` and `phase-verify-security (03)`, with strict status checks. | `--live` (`gh api .../required_status_checks`). |
| V20.8      | The `providers-live` environment deploys from `main` only, its secrets exist by name (configuration only; V6.3 proves their values), and no repository secret exists. | `--live` (`gh api` environments; `gh secret list`). |

---

## Summary Table

| Step    | Scope                            | Model             | Platform     | Reasoning dial      | Thinking | Conv | Status      |
| ------- | -------------------------------- | ----------------- | ------------ | ------------------- | -------- | ---- | ----------- |
| 1       | Core hardening + baseline        | GPT-6.1 Sol       | Codex        | Intelligence Medium | --       | New  | Complete — PR #106 |
| 2       | ADR-0011 + data model            | Claude Opus 5.5   | Claude Code  | Effort XHigh        | On       | New  | Complete — PR #108 |
| 3       | Credentials + redaction          | Claude Opus 5.5   | Claude Code  | Effort XHigh        | On       | New  | Complete — PR #111 |
| 4       | Provider SDK + transport         | Claude Sonnet 5.5 | Claude Code  | Effort XHigh        | On       | New  | Complete — PR #115 |
| 5       | Cache + offline mode             | Claude Sonnet 5.5 | Claude Code  | Effort High         | On       | New  | Complete — PR #117 |
| 6       | FRED/ALFRED, BLS, BEA, Census    | Claude Opus 5.5   | Claude Code  | Effort High         | On       | New  | Complete — PR #118 |
| 7       | Treasury, Fed Board, NY Fed, EDGAR, OpenFIGI | Claude Opus 5.5 | Claude Code | Effort Medium | On | New  | Complete — PR #124 |
| 8       | SDMX, World Bank, DBnomics       | GPT-6.1 Sol       | Codex        | Intelligence Medium | --       | New  | Complete — PR #125 |
| 9       | Regional Feds, CBO, PWT          | GPT-6.1 Sol       | Codex        | Intelligence Medium | --       | New  | Complete — PR #127 |
| 10      | Finance research data            | GPT-6.1 Sol       | Codex        | Intelligence Medium | --       | New  | Complete — PR #129 |
| 11      | Catalog + resolver               | Claude Sonnet 5.5 | Claude Code  | Effort High         | On       | New  | Complete — PR #130 |
| 12      | Bindings + vintage runs          | Claude Sonnet 5.5 | Claude Code  | Effort XHigh        | On       | New  | Complete — PR #132 |
| 13      | Monetary-policy suite            | Claude Opus 5.5 | Claude Code | Effort High | On | New  | Complete — PR #140 |
| 14      | Catalog: macro                   | Claude Opus 5.5 | Claude Code | Effort High | On | New  | Complete — PR #144 |
| 15      | Catalog: fixed income + equity   | Claude Opus 5.5 | Claude Code | Effort High | On | New  | Complete — PR #146 |
| 16      | Catalog: asset pricing + portfolio | Claude Opus 5.5 | Claude Code | Effort High | On | New  | Complete — PR #153 |
| 17      | Catalog: econometrics            | Claude Opus 5.5 | Claude Code | Effort High | On | New  | Complete — PR #160 |
| 18      | 1.0.0a2 readiness gate           | Claude Opus 5.5 | Claude Code | Effort High | On | New  | Complete — PR #165 |
| 19      | 1.0.0a2 release                  | GPT-6.1 Sol | Codex | Intelligence High | -- | New  | Complete — PR #166 |
| 20      | QA + verify-phase03.sh           | Claude Opus 5.5 | Claude Code | Effort Medium | On | New  | Not started |
| V1      | Core hardening                   | CI: phase-verify.yml, ci.yml; live | -- | --             | --       | --   | --          |
| V2      | ADR-0011 + data model            | CI: phase-verify.yml, ci.yml; live | -- | --             | --       | --   | --          |
| V3      | Credentials + redaction          | CI: phase-verify.yml, ci.yml, security.yml | -- | --     | --       | --   | --          |
| V4      | Provider SDK + transport         | CI: phase-verify.yml, ci.yml, security.yml | -- | --     | --       | --   | --          |
| V5      | Cache + offline mode             | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V6      | Keyed providers + live run       | CI: phase-verify.yml, ci.yml, providers-live.yml; live | -- | -- | -- | -- | --         |
| V7      | Keyless providers                | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V8      | International providers          | CI: phase-verify.yml, ci.yml, security.yml | -- | --     | --       | --   | --          |
| V9      | Research macro providers         | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V10     | Research finance providers       | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V11     | Catalog + resolver               | CI: phase-verify.yml, ci.yml; live | -- | --             | --       | --   | --          |
| V12     | Bindings                         | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V13     | Monetary-policy suite            | CI: phase-verify.yml, ci.yml, providers-live.yml; live | -- | -- | -- | -- | --         |
| V14     | Macro                            | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V15     | Fixed income + equity            | CI: phase-verify.yml, ci.yml, providers-live.yml; live | -- | -- | -- | -- | --         |
| V16     | Asset pricing + portfolio        | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V17     | Econometrics                     | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V18     | Readiness gate                   | CI: phase-verify.yml; live | --    | --                  | --       | --   | --          |
| V19     | 1.0.0a2 release                  | CI: phase-verify.yml; live, post | -- | --              | --       | --   | --          |
| V20     | CI integration                   | CI: phase-verify.yml; live, post | -- | --              | --       | --   | --          |

---

## Model selection blocks

```text
PROMPT: Step 1 — Core Hardening and the 1.0.0a2 Baseline
MODEL: GPT-6.1 Sol
BACKUP: Claude Sonnet 5.5
PLATFORM: Codex
EFFORT: Medium
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — three issue-specified fixes
to shared core validation and root finding, held by every model's suites.
PICK: GPT-6.1 Sol leads GPT-6 Sol at Medium at the same price
(Terminal-Bench 4.0 48.0% vs 18.7%, AA Intelligence Index 47.8 vs 39.8);
GPT-6 Astra is within noise at five times the price. EFFORT: Medium, the
ladder value, because each fix is specified and the full suite checks it;
thinking on.

PROMPT: Step 2 — ADR-0011 Data Platform and the Data Model
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: XHigh
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: planning, knowledge secondary — eighteen data-platform
decisions every provider, model and surface will encode. PICK: Opus 5.5 is
S in planning and knowledge and beats Fable 5.1 on the cost tie-break (AA
Intelligence Index 57.6). EFFORT: XHigh — High plus a rung for
cross-cutting planning; every decision has a drafted default, so not Max.

PROMPT: Step 3 — Credentials, Configuration and Redaction
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: XHigh
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — the key chain, secret type
and redaction that must keep users' keys out of six sinks. PICK: Opus 5.5
is S in coding and knowledge and beats Fable 5.1 on the cost tie-break
(HLE 61.4%). EFFORT: XHigh because proving no leak across six sinks is
multi-step verification over many files; the design is fixed, so not Max.

PROMPT: Step 4 — Provider SDK, Transport and Contract Suite
MODEL: Claude Sonnet 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: XHigh
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — the provider contract,
transport, cassettes and contract suite every data source will implement.
PICK: Sonnet 5.5 is S in coding and planning and wins the coverage
tie-break (AA Intelligence Index 56.0). EFFORT: XHigh for novel API design
across many files with security properties; ADR-0011 fixes the shape, so
not Max.

PROMPT: Step 5 — Cache and Offline Mode
MODEL: Claude Sonnet 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — a licence-aware SQLite store
with expiry, offline mode and integrity checks on three operating systems.
PICK: Sonnet 5.5 is S in coding and planning and wins the coverage
tie-break (AA Intelligence Index 56.0). EFFORT: High for interacting
cross-platform and security edges under a fixed design; thinking on.

PROMPT: Step 6 — Providers: FRED and ALFRED, BLS, BEA, Census
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — four keyed sources with
real-time vintages and licence gates, and the first secrets-bearing
workflow. PICK: Opus 5.5 is S in coding and knowledge and beats Fable 5.1
on the cost tie-break (SciCode 66.9). EFFORT: High for exact source
semantics on a settled SDK; the live run checks them, so not Extra High.

PROMPT: Step 7 — Providers: Treasury, Fed Board, New York Fed, EDGAR, OpenFIGI
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: Medium
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: see Model rationale. PICK/EFFORT: the Balanced column of `roadmodel ladder` (refresh 2026-10-18).

PROMPT: Step 8 — Providers: SDMX Sources, World Bank, DBnomics
MODEL: GPT-6.1 Sol
BACKUP: Claude Sonnet 5.5
PLATFORM: Codex
EFFORT: Medium
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — five SDMX sources over one
client plus two JSON APIs, with series-level licence gates. PICK: GPT-6.1
Sol leads GPT-6 Sol at Medium at the same price (Terminal-Bench 4.0 48.0%
vs 18.7%, AA Intelligence Index 47.8 vs 39.8); GPT-6 Astra is within noise
at five times the price. EFFORT: Medium, the ladder value, for
well-specified work the contract suite checks; thinking on.

PROMPT: Step 9 — Providers: Regional Fed Research, CBO, Penn World Table
MODEL: GPT-6.1 Sol
BACKUP: Claude Sonnet 5.5
PLATFORM: Codex
EFFORT: Medium
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — five spreadsheet research
sources, two with documented vintage matrices, and two classifications.
PICK: GPT-6.1 Sol leads GPT-6 Sol at Medium at the same price
(Terminal-Bench 4.0 48.0% vs 18.7%, AA Intelligence Index 47.8 vs 39.8);
GPT-6 Astra is within noise at five times the price. EFFORT: Medium, the
ladder value; vintage tests and Step 13's goldens check the mapping;
thinking on.

PROMPT: Step 10 — Providers: Asset-Pricing and Market Research Data
MODEL: GPT-6.1 Sol
BACKUP: Claude Sonnet 5.5
PLATFORM: Codex
EFFORT: Medium
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — ten file- or API-based
research sources on established zip, CSV and spreadsheet patterns. PICK:
GPT-6.1 Sol leads GPT-6 Sol at Medium at the same price (Terminal-Bench
4.0 48.0% vs 18.7%, AA Intelligence Index 47.8 vs 39.8); GPT-6 Astra is
within noise at five times the price. EFFORT: Medium, the ladder value,
for numerous but patterned providers under one contract suite; thinking
on.

PROMPT: Step 11 — Semantic Catalog and Resolver
MODEL: Claude Sonnet 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — a permanent concept
vocabulary and a resolver ruled by mode, licence, keys, extras and
vintages. PICK: Sonnet 5.5 is S in coding and planning and wins the
coverage tie-break (AA Intelligence Index 56.0). EFFORT: High for many
interacting rules inside ADR-0011's fixed frame; thinking on.

PROMPT: Step 12 — Live Bindings and Vintage-Aware Runs
MODEL: Claude Sonnet 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: XHigh
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — bindings, bind(), run() on
bound inputs and manifest schema 2 across Phase 2's core contract. PICK:
Sonnet 5.5 is S in coding and planning and wins the coverage tie-break (AA
Intelligence Index 56.0). EFFORT: XHigh for a novel API across many files
that must keep results deterministic; decision 16 fixes it, so not Max.

PROMPT: Step 13 — Monetary-Policy Suite
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: see Model rationale. PICK/EFFORT: the Balanced column of `roadmodel ladder` (refresh 2026-10-18).

PROMPT: Step 14 — Launch Catalog: Macroeconomics
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: see Model rationale. PICK/EFFORT: the Balanced column of `roadmodel ladder` (refresh 2026-10-18).

PROMPT: Step 15 — Launch Catalog: Fixed Income and Equity
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: see Model rationale. PICK/EFFORT: the Balanced column of `roadmodel ladder` (refresh 2026-10-18).

PROMPT: Step 16 — Launch Catalog: Asset Pricing and Portfolio
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: see Model rationale. PICK/EFFORT: the Balanced column of `roadmodel ladder` (refresh 2026-10-18).

PROMPT: Step 17 — Launch Catalog: Econometrics
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: see Model rationale. PICK/EFFORT: the Balanced column of `roadmodel ladder` (refresh 2026-10-18).

PROMPT: Step 18 — 1.0.0a2 Readiness Gate
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: High
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: see Model rationale. PICK/EFFORT: the Balanced column of `roadmodel ladder` (refresh 2026-10-18).

PROMPT: Step 19 — 1.0.0a2 Release
MODEL: GPT-6.1 Sol
BACKUP: Opus 5.5
PLATFORM: Codex
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: see Model rationale. PICK/EFFORT: the Balanced column of `roadmodel ladder` (refresh 2026-10-18).

PROMPT: Step 20 — QA and Verification Script
MODEL: Claude Opus 5.5
BACKUP: GPT-6.1 Sol
PLATFORM: Claude Code
EFFORT: Medium
THINKING: On
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: see Model rationale. PICK/EFFORT: the Balanced column of `roadmodel ladder` (refresh 2026-10-18).

---

## Not in scope (from product roadmap)

The parent ROADMAP's Phase 3 section names two sources it does not build
(§4 3.4, "Not built"); every other item below is deferred by its phase
boundaries and its §6 "Out of Scope"
([`docs/roadmap/ROADMAP.md`](ROADMAP.md)):

- Stooq, which sits behind a bot challenge with unknown terms, and Nasdaq
  Data Link, which Phase 6 adds as a bring-your-own-key source.
- Every generated surface over this phase's data layer: the `pyeconomics
  data`, `keys` and `cache` commands, the REST API's `series` routes, the
  MCP server's `get_series` and `list_sources` tools and its `llm_use`
  gate, exports and reproducibility bundles that print attributions, and
  the optional AI narrative. Phase 4 builds them on the Python APIs this
  phase ships.
- The hosted service and everything that serves data publicly: hosted
  mode's API, the scheduled snapshot job and its Parquet snapshots, the
  data explorer, the "Data sources & licences" page, counsel's review of
  the licence classes, and the permissions programme with the St. Louis,
  Philadelphia, Atlanta and Cleveland Feds, Ken French, Robert Shiller and
  the IMF. Phase 5 owns them.
- Bring-your-own-key vendors, the Bloomberg provider, the OpenBB bridge,
  premium-only datasets and the fallback to them. Phase 6 builds them on
  the contract Step 4's spike shaped.
- Next-wave models: estimating r* (a Laubach-Williams port), McCallum,
  Orphanides and Friedman rules, Kalman NAIRU, term-premium models, SVAR,
  VECM, local projections and the rest of ROADMAP §4 7.2; Bitcoin
  stock-to-flow, kept with evidence status `rejected`, which closes gap
  15's model half. Phase 7 owns them.
- Alerts on a policy-rule gap, scheduled runs and every paid feature.
  Phase 8 owns them, behind Gate G3.
- Real-time streaming quotes, tick and intraday data, licensed-data
  redistribution and personalised advice, which stay excluded in every
  phase (ROADMAP §6).

Additionally not in scope for this phase:

- A Parquet or DuckDB cache. ADR-0011 decision 14 chooses SQLite;
  Parquet stays the export and hosted-snapshot format of Phases 4 and 5.
- httpx and an asynchronous transport. Phase 4 revisits async only if its
  server must fetch providers per request; hosted mode reads snapshots.
- A `pyeconomics keys` command. Until Phase 4 adds it, users store keys in
  the environment, the config-directory `.env` or `keyring set pyeconomics
  <provider>`.
- The yearly terms review as a scheduled process and the reclassification
  runbook. ADR-0005's Confirmation assigns them to Phase 5; this phase
  adds the 13-month freshness test that makes a stale review fail.
- linearmodels, PyPortfolioOpt, skfolio and Riskfolio-Lib as additional
  test oracles. Step 16 verified linearmodels 7.1's CPython 3.15 wheels but
  did not need it; other candidates had incompatible dependency closures.
  Statsmodels, SciPy and independent recomputations cover this release.
  Adding an oracle requires a fresh licence and supported-wheel review.
- Fuzzing the provider parsers. It remains with issue #62's Scorecard
  dispositions and its owner; the parsers are the natural target if that
  issue takes it up.
- Issues #52 (the 0.2.6 CVE id), #62 (Scorecard dispositions) and #68
  (GitHub Sponsors, ROADMAP 8.1). Each keeps its owner outside this phase.
  Dependabot PR #61 is closed; ordinary dependency maintenance continues
  independently after Step 19 lifted the release freeze.
- A SIFMA US bond-market calendar. `docs/phase02-qa-findings.md` assigns
  it to Phase 7's fixed-income batch.

Carried over during execution — the Triage rule's carry-over checklist:

- Step 17 (launch catalog: econometrics, 2026-10-21): `models/econometrics/`
  adds `econometrics.garch` (over arch) and `econometrics.time_series` (over
  statsmodels); the registry holds all 50 launch-catalog ids. arch 8.0.0 still
  had no CPython 3.15 wheel at kickoff, so it joins `[econometrics]`, `[all]`
  and the test group behind `python_full_version < '3.15'` (maintainer-approved
  in PR, issue #154 to drop it). Contract changes made in-step under the
  Contract-change rule, the smallest that work: `Provider.from_distribution`
  evaluates an extra's environment markers (with `packaging`, taken to apply
  when it is absent) and lists a left-out package in `Provider.excluded`
  (`Provider.excludes`, `Registry.from_models(excluded=)`); validation's
  example rule and `scripts/smoke.py` accept the
  `MissingOptionalDependencyError` a model raises for such a package;
  `MissingOptionalDependencyError` takes a `note`; `core.library_warnings`
  reports a wrapped library's warnings as result warnings (the model-import
  allowlist admits no `warnings` module); `smoke.py --extras` runs every model
  that names an extra; release-smoke keeps a requirement's environment marker
  for pip. The golden harness and the contract suite assert the gap through
  `tests/extra_gaps.py`. Blocking upstream gap fixed in-step: the Ken French
  daily files hold Saturday sessions before 1952, so the provider dates them
  `daily`, not `business_daily` (Step 10), and the daily concepts follow; nine
  daily factor series concepts (`factors.*.us.daily`) were added for the GARCH
  profile. Spec rot fixed: the bindings requirement asked for "any catalog
  series", which Step 12's rebind rule (same unit kind and frequency) does not
  allow. Facts for later steps: arch's forecasts start their recursion from a
  backcast of the residuals at the estimated mean, its fit from the demeaned
  returns (the paths differ only while the start has not decayed); BLS
  published no October 2025 CPI or unemployment rate, so a window spanning it
  cannot be bound; statsmodels' MacKinnon (2010) coefficient for N = 2 at 1%
  differs from the paper (issue #155) and `coint_johansen` with no lagged
  difference regresses on the current level (issue #156; the model requires
  one).

- Step 16 (launch catalog: asset pricing and portfolio, 2026-10-20):
  `models/asset_pricing/` (a new domain with its own entry point) adds
  `asset_pricing.factor_regression` and `asset_pricing.factor_model_tests`, and
  `models/portfolio/` adds `portfolio.black_litterman` and
  `portfolio.risk_based_allocation`. Contract change made in-step under the
  Contract-change rule, the smallest that works: a matrix binding (Step 12). A
  field that is a tuple of rows, bound to a table concept with `AsOf.WINDOW`,
  reads one row per period of the window and one value per column, and
  `Binding(..., columns=...)` keeps only the named columns, in order; its window
  ends with the other windows of its frequency. `FieldShape` gains `matrix` and
  `width`, `Binding.to_dict()` and `describe()` gain `columns`, and the card names
  them. A test of N assets on L factors needs a panel, and a binding read only a
  series or a curve's row (ADR-0011 decision 16 stands: a window of N
  observations, which for a table are its rows; `columns` is an addition, as
  `tenors` was). New series concepts for the nine monthly Ken French factors
  (Step 11's catalog had them only as table columns). Facts for later steps: the
  five-factor file's SMB differs from the three-factor file's in 743 of 758 months
  (by 0.38 percentage points on average) and its Mkt-RF by up to 0.08 in 167,
  while HML and RF are identical; the 25 size and book-to-market portfolios reach
  148% in a month; He and Litterman's numeric tables are in the 2002 SSRN version
  (334304), which optimizes against Sigma + M, not the 1999 Goldman Sachs paper,
  which prints only inputs and charts and optimizes against Sigma; Idzorek's
  printed results use lambda = 0.03 / (w' Sigma w) = 3.0658, not the 3.07 he
  quotes, and his numerical confidence calibration has the exact solution
  omega = (1 - c) / c p tau Sigma p'; Lopez de Prado's Exhibit 7 reproduces only
  with Python 2's `random.randint`; the GRS factor covariance takes divisor T
  (Cochrane 2005, eq. 12.6; Kamstra and Shi 2021); Fama and MacBeth (1973) state
  no divisor for their standard deviation. Step 12 reads Complete, so its task
  stands as history and the change is recorded here.

- Step 15 (launch catalog: fixed income and equity, 2026-10-19):
  `models/fixed_income/` adds `fixed_income.curve_fitting` and
  `fixed_income.interest_rate_tree`, `models/equity/` adds
  `equity.implied_risk_premium` and `equity.cape`. Contract changes made in-step
  under the Contract-change rule, each the smallest that works: a curve binding,
  `Binding(..., tenors=...)` (Step 12), which reads a table concept whose columns
  are tenors (`1m` to `30y`) at its last row on or before the date and fills an
  array of values and an array of their tenors in years, leaving out a tenor the
  row lacks, because a fit or a tree calibration needs one date's curve and a
  binding read only a series (ADR-0011 decision 16 stands: the curve's observation
  is its row, read by the last-observation rule; `tenors` is an addition, as
  Step 12's `parameters=` was); series concepts for the Board's six GSW parameters,
  Shiller's price, earnings and CPI, and Damodaran's year-end S&P 500 level,
  dividends plus buybacks and expected growth (Step 11's catalog had the first two
  as table columns and the third not at all); the `damodaran` provider's implied
  premium file now carries those three columns with their own units (Step 10); and
  the `fed_board` provider labels the GSW betas `ratio`, not unlabelled (Step 7's
  provider, built in Step 10). The catalog world's stand-in tables give each
  column its own concept's unit kind (Step 11's test helper). Facts for later
  steps: the GSW betas are coefficients in decimal rate units, not rates (the
  Board's fits offset humps of several hundred percentage points on near-collinear
  days, 3,407 as a decimal on 2011-08-03, and TAU2 reaches 181 years), and the
  file's 2011-08-03 par yields disagree with its own zero yields; the ECB's par
  yields have monthly coupons until 2023-05-18 and continuous coupons from
  2023-05-19; Damodaran's histimpl.xls rounds its premiums to four decimals and
  its year-end inputs reproduce them only for 2016-2019 (he normalized the base
  cash flow in 2011-12, adjusted it for COVID in 2020 and grows estimated
  earnings at the trailing payout since 2021), while his January spreadsheets
  carry the full-precision premium; Shiller's CAPE for a month averages the real
  earnings of the 120 months before it (not the month itself), and his excess
  CAPE yield is 1/CAPE less GS10 less (CPI_t / CPI_t-120)^(1/10) - 1; Kalotay,
  Williams and Fabozzi's printed callable value (101.432) is 0.0013 high against
  their own tree. Steps 7, 10, 11 and 12 read Complete, or are Step 7's parked
  branch, so their tasks stand as history and the changes are recorded here.

- Step 14 (launch catalog: macroeconomics, 2026-10-19): `models/macro/` adds
  `macro.output_gap`, `macro.phillips_curve`, `macro.okun_law`,
  `macro.solow_growth`, `macro.debt_dynamics` and `macro.recession_probability`,
  and `core/regression.py` adds `least_squares` (Step 16 reuses it; its task
  carries the facts). Contract changes made in-step under the Contract-change
  rule, each the smallest that works: window bindings of one frequency end on one
  date, the earliest last observation on or before the date (Step 12's bind read
  each window to its own series' end, so real GDP and CBO's potential, or monthly
  unemployment averaged to quarters and CBO's natural rate, came back a quarter
  apart and a model pairing them by position paired the wrong quarters); a window
  read through `convert` is sized in the target frequency (a monthly average of
  the Treasury's daily curve asked 33 days back and never held a whole month);
  the `us.fiscal.primary_balance_to_gdp` concept (Step 11's catalog had the
  primary balance in dollars only); a window passes over a candidate with too
  short a history (`resolve(min_observations=)`, propagated to derived operands,
  and a second pass up to the windows' shared end for a source that runs years
  ahead), because live, BLS answers a whole-history request with about three
  years and CBO's current projection file starts in 2023, so every 60- or
  120-quarter window failed on the originator while FRED held the history (in
  hosted mode, where FRED is refused, such a window still has no source: issues
  #141 for BLS and #142 for CBO's history, owned by later data-layer work); and
  the live derived-concept test counts a nested derived operand's own operands. Spec rot fixed in this step's task:
  Okun's difference form is the change in unemployment on growth, the form Okun
  (1962) and Knotek (2007) estimate, not growth on the change. Facts for later
  steps: a growth rate bound through `pct_change` is a `Return`, not a `Rate`; a
  Penn World Table count (persons engaged, millions in float32 precision) never
  scales to a whole number, so bind its growth, not its level, to avoid a `Count`
  field; FRED's UNRATE and CPIAUCNS hold no October 2025 value (BLS collected no
  data in the shutdown), so a quarter's average of them is missing and the
  Phillips and Okun bindings read each quarter's last month; the catalog world's
  stand-ins space an irregular source 45 days apart, so
  a test that averages the Treasury curve gives them business days
  (`tests/models/macro/test_launch_bindings.py`). Steps 11 and 12 read Complete,
  so their tasks stand as history.

- Step 13 (monetary-policy suite, 2026-10-18): `models/macro/` holds
  `macro.policy_rule` and `macro.neutral_rate` behind the `macro` entry point.
  Contract changes made in-step under the Contract-change rule, each the smallest
  that works: the `lag(periods=n)` transform (Step 11's vocabulary); a candidate
  `column` that takes `{parameter}` placeholders, for the SEP's year-keyed columns
  (Step 11); a candidate `vintages` flag (Step 11), because ALFRED refuses a
  real-time request for FRED's daily `EFFR`, `DFEDTARU`, `DFEDTARL`, `DGS10`,
  `DGS3MO` and `DFII10` (probed live for every FRED candidate), which made every
  real-time bind of the funds rate raise (the resolver now refuses a vintage a
  source can never serve before it asks for a key, so a missing key is not
  blamed for it); `bind` of a union model needs
  `calculation=` and reads only its fields, and an `AsOf.PERIOD` bind reads up to
  the end of the period containing the date, so a source without it is passed over
  (both Step 12, found when CBO's as-of-2019 read held nothing before 2021);
  `ChartKind.BAND` (Phase 2's chart contract); the Board's SEP parser dropped row
  footnote numbers from column names (Step 10's `fed_board`); concept search weighs
  a token in the id's topic (Step 11). Steps 11 and 12 read Complete, so their
  tasks stand as history and the changes are recorded here; Steps 14 and 15's
  tasks carry the facts they need. Facts for later steps: the New York Fed's r* and
  funds rate keep no vintages and CBO's archive starts 2024-02, so a real-time bind
  reads them as revised data, labelled (a CBO-only concept cannot be read as
  published before 2024-02); a quarterly GDP-based gap is read at the last quarter
  published (`LAST_ON_OR_BEFORE`), not the date's quarter. Deferred: issue #135
  (`nyfed` effr fails a whole-history or end-only request; FRED answers in library
  mode, so a hosted bind of the funds rate has no source) and issue #136 (cached
  frames outlive a provider's parse fix), both owned by later work, not Step 13.
  The narrowed registry and ledger pins accept unreleased ids until Step 19.

- Step 12 (live bindings and vintage-aware runs, 2026-10-18): `core/binding.py`
  holds `AsOf`, `VintagePolicy`, `Binding`, `Bound`, `CandidateNote`,
  `field_shapes` and `user_supplied` (annotation reading shared with the
  validator through `core/_annotations.py`), and `data/bindings.py` holds `bind`,
  `bind_model`, `validate_bindings` and `candidate_notes`. `pyeconomics.bind` is
  exported lazily (PEP 562), because `import pyeconomics` must load no data module
  (`tests/data/test_layering.py`). Contract additions made in-step: `bind` takes
  `parameters=` (a concept's parameters, which Step 13's SEP concepts need and the
  ADR's summary signature omits); a `Bound` carries `model_id` (`run` refuses
  another model's) and `as_of`; `bind_model` takes the `transport` and `registry`
  seams so an override field may have any name; `Fetched.source()` copies the notes
  in `cache.policy.NOTE_WARNINGS` (`revised_data`, `bls_keyless`) into a record's
  warning codes; and the resolver's final error ignores a `vintage_unsupported`
  skip when naming the cause, so a missing key or an empty offline cache still
  raises `CredentialError` or `OfflineError`. Facts for later steps: a binding reads
  a series concept, never a table, so Step 13 adds the SEP series concepts its
  `us_sep` profile binds (its task is patched); `AsOf.PERIOD` reads past the date,
  because a period is dated by its last day; a real-time bind is skipped to revised
  data only when no source usable in the mode declares `vintages`; the card's "Data"
  section appears only for a model with bindings (`BOUND_SECTION_TITLES`) and
  `registry.describe` / the model-page generator import the data layer only for
  such a model. The Phase 2 tests the Cross-phase rule lists were narrowed, none
  deleted (`test_spec`, `test_validate_rules`, `test_manifest`, `test_runner`,
  `test_cards`); `verify-phase01.sh` and `verify-phase02.sh` needed no change.
  The toy bound models and scripted providers are `tests/data/bindings/`.

- Step 11 (catalog and resolver, 2026-10-17): the catalog is 136 concepts in
  `data/catalog/` (its shapes in `definitions.py`, deliberately not
  `concepts.py`, which a `catalog.concepts()` function would shadow). Contract
  additions made in-step: the `add` transform (the primary balance is the sum of
  net lending and interest); `ConceptNotFoundError`; `sources(check_keys=False)`
  so the documentation build looks at no key; `registry.validate()` takes
  `released_concepts=` and runs the `concept-*` rules of
  `data/catalog/checks.py` (its `deep=True` series check, which builds requests
  for extra-gated providers and so imports the HTTP stack, runs in a test, not in
  `validate()`); the resolver judges a series' own terms by the mode it was asked
  for, as the provider judges them by the configured one. Two catalog facts for
  later steps: keyless BLS (API v1) reports a rate with no unit kind, so a rate
  concept needs a BLS key to use BLS and otherwise falls to FRED; and PWT's `rkna`
  is a capital-services index (`rnna` is the capital stock in 2021 dollars), both
  carried as concepts. The weekly live run now also resolves every candidate of
  every concept (`tests/data/catalog/test_live_concepts.py`). The Treasury curve
  files answer in about 20 seconds per request (the source's speed), so the live
  windows for them are 12 days.

- Step 10 blocking upstream gap: test isolation is loaded from the repository
  root through tests/isolation_plugin.py, so source-module doctests cannot
  inspect or clear the user cache. Preserve this scope in later test changes.
each upstream gap or deferred finding, the step whose `<task>` was
patched, and the step or phase that owns it. Phase 4's roadmap carries
forward whatever is still open here.

- External access: resolved 2026-10-20. SEC's 403 came from its User-Agent
  filter (it refused the configured address and any User-Agent holding a URL),
  not from an IP block. Step 10 delivered the four unblocked providers; the
  rebased Step 7 PR (#124) delivers `sec_edgar` with real recordings, the
  five-provider validation and the live proof. Step 18 therefore checks the
  31-id release set, and Step 20 has no SEC deferral to hand over. Sponsors issue #68 is a separate
  maintainer-owned funding follow-up and does not gate either phase.

- From Phase 2's carry-over list, Not-in-scope list and QA findings,
  absorbed by this roadmap:
  - issue #75 (booleans and epoch numbers pass the unit markers; Phase 2's
    checklist named Step 1's markers, its QA findings "Phase 3 core
    hardening") — Step 1;
  - issues #81 (a numeric `Literal` without a unit) and #85 (IRR roots on
    the bracket's ends), absent from Phase 2's checklist but assigned to
    this phase by its QA findings and release notes — Step 1;
  - filling `ModelSpec.bindings` and the manifest's `data_sources` — Step
    12;
  - the 0.2.x characterization contract — Step 13;
  - replacing the exact-32 registry and ledger pins with "at least" —
    Step 13;
  - linearmodels and arch as test oracles with the estimator entries —
    Steps 16 and 17, under the Wheel rule;
  - every release re-checking ADR-0010's floor and ADR-0003's milestone
    tag — Steps 18 and 19.
- From Phase 1: the 1.0 data-sources guide that replaces 0.2.x's FRED
  page — Steps 3 and 11; the replacement of 0.2.x's pickle cache — Step 5.
- From the parent ROADMAP: gap 15's data half (Coin Metrics classed and
  enforced) — Step 10, its model half Phase 7; OECD's class, left TBD by
  ADR-0005 — Step 8; the classes of CBO and the Penn World Table — Step 9.
- From execution:
  - Step 2 (ADR-0011, accepted 2026-10-14): a frame's dates span
    `DATA_DATE_BOUNDS` (1700-01-01 to 2200-12-31), wider than a model
    field's, so Step 4's `Query` bounds its dates by them (Step 4's task
    patched); OpenFIGI mappings and EDGAR filing lists are provider-typed
    records, not frames (Step 7's task patched); `DataSource` carries the
    bound `field` and data `warnings` codes that Steps 5 and 12 fill.
  - Step 3 (credentials, configuration and redaction, 2026-10-15): the
    chain names a provider's variable `<PROVIDER>_API_KEY`
    (`key_variable`), so Step 4's `ProviderInfo` authentication declares
    that variable, or extends `resolve_key` for a source that needs
    another. The transport reveals a `Secret` and raises every failure
    through `redaction.call_scrubbed`. Steps 4, 5 and 12 add their sinks
    to `tests/data/leakcheck.py` with `LeakCheck.add`. Steps 4 and 5 read
    `settings().mode`, `.offline` and `.ttl` and `config.cache_dir()`.
    Step 7 reads the SEC contact from `settings().sec_contact`, a pydantic
    `SecretStr`, in the transport only. `platformdirs`'s floor is 4.9.4,
    the version Pyodide 314.0.7 bundles, not 4.13.
  - Step 4 (provider SDK, transport and contract suite, 2026-10-15):
    `DataProvider`'s public operations are final (`fetch`, `search`,
    `describe`, `vintages`, `run_case`), so a provider overrides only
    its `build_*` and `parse_*` hooks, `classify_error`, `exchange` and
    `synthesize`; a provider lists its recorded interactions in
    `DataProvider.cases` (`Case`), which the recorder and the contract
    suite share, and adds its row to `tests/providers/test_notices.py`
    (Steps 6 to 10's tasks read this). A final response status maps to
    the error taxonomy in the base class, not the transport, so
    `HttpTransport` returns 429 and 5xx responses after its retries.
    The limiter is a sliding window, not a token bucket (it must never
    admit twice a limit in one window). `urllib3>=2.6.3` and
    `truststore>=0.10; sys_platform != "emscripten"` replace the
    task's `urllib3>=2.8`, because Pyodide's index has urllib3 2.6.3 and
    no truststore. The contract suite is
    `tests/providers/provider_contract.py` and its tests are
    `test_provider_*.py`, because mypy maps test basenames to top-level
    modules and `contract.py`, `test_contract.py`, `test_terms.py` and
    `test_validate_rules.py` were taken. The Bloomberg spike needed no
    change to the contract: `Access.SESSION`, an empty `hosts` and an
    `exchange()` override, a `*.localhost` request host, a `Query`
    subclass for tickers with spaces and the session owning the clock
    are how a session source uses the seams Step 4 built (Phase 6
    reuses them; `docs/data/writing-a-provider.md` records them).
    `scripts/release_ledger.py` still writes only the model ledger:
    Step 19 extends it to `data/_released.py`'s providers section (and
    Step 11's concepts section).
  - Step 5 (cache and offline mode, 2026-10-15): the cache lives in
    `pyeconomics.data.cache` (`policy.py` is pure; `store.py` and the
    package are I/O), and the final `DataProvider.fetch` now asks it first
    through a new final `fetch_with_origin`, which returns `Fetched(frame,
    origin, vintage)`; `Fetched.source()` is the `DataSource` record Steps
    11 and 12 start from (their tasks patched). `ProviderInfo` gained
    `ttl_seconds` (default 3600; the `cache-policy` rule checks it), so
    Steps 6 to 10 set it per provider. Offline mode refuses every operation
    the cache does not serve (`search`, `describe`, `vintages`) and the
    HTTPS transport (`modes.require_online`). `cache.bypass()` keeps the
    cassette recorder away from the cache; `cache.memo()` is the
    in-process reuse for sources that may not be stored. A closed past
    vintage is an `as_of` more than a day old; `user-supplied` data is never
    stored. `PYECONOMICS_TTL_<PROVIDER>=0` turns a provider's cache off, and
    an override applies to entries stored afterwards.
  - Step 6 (providers FRED and ALFRED, BLS, BEA, Census, 2026-10-15): the
    first real sources needed seams the contract lacked, added in-step
    (`upstream-gap`, Steps 2 and 4): frame metadata `notes` (`SeriesMeta`
    and `TableMeta`; Steps 7, 9 and 12 patched to use them); a key slot per
    placement (`KeySlot`, `Authentication.alternates`,
    `Request.key_placement`) for FRED's v1 query key and v2 header key;
    `DataProvider.sends_key`, `credentials.withheld()`, `Case.keyless` and
    `RateLimit.without_key` for BLS's optional key; `DataProvider.next_page`
    for paging (FRED v2, FiscalData); `ProviderInfo.follow_redirects` and
    `classify_error` for any status outside 2xx (Census answers a bad key with
    a redirect whose page and cookie echo the key: a `security` finding fixed
    in-step); and `Case.simulate`, so the recorder records a 429 or a 5xx
    without provoking one. The contract suite's replay now sends a stand-in key
    and its live run sends a made-up key for an `invalid_key` case (a latent
    Step 4 bug). FRED's current terms live at fred.stlouisfed.org/legal/ and
    forbid storage and AI or machine-learning use (`llm_use` forbidden); the
    old docs/api/terms_of_use.html page is stale. Census has required a key on
    every query since May 2026. An entry-point module's `__all__` lists
    provider classes only.

---

_This roadmap is the execution plan for Phase 3. Each step's
`**Status:**` line is flipped by that step's own PR (Status rule), so this
file on `main` is the phase's ledger — `grep -n '^\*\*Status:\*\*'`
reports progress. After the required steps and verification pass (with
only the named SEC exception permitted), and every finding
has a destination, Phase 3 is complete — declared with the line "Phase 3 is
complete. You can now move on to Phase 4." and nothing after it — and Phase
4 (Programmatic Surfaces: CLI, REST API, MCP & Exports) inherits
`pyeconomics 1.0.0a2` on PyPI: 50 verified models whose bindings resolve
live data on real-time vintages; 30 verified providers while SEC is deferred,
or 31 once Step 7 completes, with enforced licence
classes, attribution and `llm_use` flags behind a Python data API (`get`,
`search`, `describe`, `vintages`, `sources`) that its `data` commands,
`series` routes and MCP tools wrap; a credential chain and redaction its
`keys` commands build on; a licence-aware cache its `cache` commands wrap;
schema-2 manifests that record every series, vintage and retrieval time
for its exports and reproducibility bundles; hosted mode's refusal for its
hosted API; a weekly live run with a proven alarm; and `verify-phase03.sh`
as the template for `verify-phase04.sh`._
