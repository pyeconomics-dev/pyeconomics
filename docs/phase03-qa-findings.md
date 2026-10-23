# Phase 3 QA findings

Phase 3 ships the data platform and eighteen new model families in
`1.0.0a2`: 50 families, 13 domains, 31 providers and 171 concepts. SEC EDGAR
shipped in Step 7; there is no SEC deferral. This rollup preserves each
step's findings, decisions and guards. Nathan Ramos, CFA owns the remaining
issues and future-phase work. Linked PRs retain source citations, numerical
review, detailed tradeoffs and validation evidence.

## Step 1 - Core hardening ([PR #106](https://github.com/pyeconomics-dev/pyeconomics/pull/106))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Boolean/date coercion and numeric Literal unit detection | bug | #75/#81 closed in #106 | Unit coercion and registry negative tests |
| IRR inclusive endpoints and local-crossing guard | model-error | #85 closed in #106; model versions and public erratum | Endpoint goldens and 1e12-period regression |
| Schema normalization must preserve nested defaults and aliases | bug | #106 | 64-document compatibility comparison and schema regressions |

## Step 2 - Data contract ([PR #108](https://github.com/pyeconomics-dev/pyeconomics/pull/108))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Observation bounds must include pre-1900 history; FIGI/SEC return records | spec-rot | ADR-0011 and Steps 4/7 tasks, delivered | DATA_DATE_BOUNDS and typed-record tests |
| Terms page is the only permitted URL; period-end dates and None missingness | architecture | #108 contract and PR decisions | Value-security, frequency and canonical round-trip tests |
| JSON depth differs on Python 3.14+ | bug | #108 explicit MAX_DEPTH | Depth 100/101 boundary tests |
| URI credential examples evade local gitleaks | security | #108 generated examples; local backstop tracked #109 | Trufflehog over every PR commit |

## Step 3 - Credentials ([PR #111](https://github.com/pyeconomics-dev/pyeconomics/pull/111))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Exception/log/traceback/key-source representations can leak secrets | security | #111 Secret and call_scrubbed; later sink additions | LeakCheck canaries and secret-reveal semgrep |
| Tests and executable docs need isolated user config/cache/keyring | process | #111 fixture; root-plugin correction #129 | Subprocess privacy regressions |
| Platformdirs Windows path, key names and preview guide URL need one convention | architecture | #111 config and AGENTS.md | Settings/key-chain tests |
| Yanked soupsieve pin in docs closure | bug | #110; dependency maintenance owner | Locked audit and dependency-review |

## Step 4 - Provider SDK ([PR #115](https://github.com/pyeconomics-dev/pyeconomics/pull/115))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Token bucket can exceed a strict rolling limit | spec-rot | #115 sliding-window limiter and task amendment | Window-boundary/rate-limit tests |
| Redirect hops, slow bodies and request repr expose transport risks | security | #115 bounded duration, per-hop limit and hidden wire fields | Transport and canary tests |
| Pyodide index has urllib3 2.6.3 and no truststore | upstream-gap | #115 compatible floor and platform marker | Pyodide CI |
| Bloomberg spike needs session access, query subclasses and status mapping | architecture | #115 guide; Phase 6 adapter owns implementation | Spike contract and no-blpapi guard |
| Proxy and Pyodide transport support unverified | architecture | #113/#114 | Explicit limitations; future adapter tests |
| Existing binomial property failure | bug | #112, also #137 | CI profile plus tracked dev-profile reproduction |
| Duplicate test basenames confuse mypy | process | AGENTS.md and distinct provider suite names | Strict types |

## Step 5 - Cache ([PR #117](https://github.com/pyeconomics-dev/pyeconomics/pull/117))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Unanchored cache ignore hid package/tests from Git and Ruff | bug | #117 `/cache/` rule and lint fixes | Tracked package and whole-tree lint |
| Database creation race exposed a zero-byte file | bug | #117 treats it as an empty cache | Deterministic and concurrent-reader tests |
| Forbidden-storage data must never reach persistent store | security | #117 one may_store gate | No-storage and cache canary tests |
| SQLite unavailable/unverified under Pyodide; Windows ACLs follow directory | architecture | #116; cache guide | Platform refusal and permission tests |
| TTL changes affect subsequent stores | process | #117 cache guide | Expiry tests |

## Step 6 - Keyed providers ([PR #118](https://github.com/pyeconomics-dev/pyeconomics/pull/118))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Census invalid-key redirect/cookie echoed credentials | security | #118 refuses redirects and cookies | Redirect/contact canary tests |
| Real sources require key slots, sends_key, notes, pagination and simulation seams | upstream-gap | #118 SDK/guide and later tasks | Provider contracts and record/replay parity |
| Invalid-key tests and live user cache were not isolated | bug | #118 cache bypass and replay-key corrections | Live/offline contract and privacy tests |
| FRED terms moved; Census requires a key | spec-rot | #118 metadata and guides | Terms/notice tests and live contracts |
| setup-uv egress and BLS REQUEST_FAILED | bug | Follow-up #120/#123 | Workflow and BLS classification regressions |
| Rate limits/outages must be simulated rather than provoked | process | AGENTS.md Recording rule | Cassette/simulation tests |

## Step 7 - Rates and SEC ([PR #124](https://github.com/pyeconomics-dev/pyeconomics/pull/124))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| SEC edge rejects URL-bearing User-Agent despite valid contact | bug | #124 contact-only User-Agent, live verified | SEC contact canary and five live cases |
| SEC frame tags require span series ids | upstream-gap | #124 typed SEC records and frame parser | Filing/facts/frame contracts |
| SEC exception became historical after delivery | spec-rot | Release/readiness exact 31-id set; Step 20 text amended | Static 30/72 and installed registry validation |
| Existing changelog mojibake, Svensson property failure and Drive quota page | bug | #148/#149/#150 | Named issue reproductions; live provider monitoring |

## Step 8 - International providers ([PR #125](https://github.com/pyeconomics-dev/pyeconomics/pull/125))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| certifi MPL and sdmx1 classifier require reviewed exceptions | process | Explicit maintainer approvals in #125 | Exact licence metadata/closure hook |
| OECD/Eurostat/World Bank rights vary by dataset | architecture | #125 series-level restrictions and notices | Hosted-refusal and series-licence tests |
| Independent provider work waited on external SEC access | process | Sequencing PRs #126/#128; resolved by #124 delivery | Status/prerequisite gates |

## Step 9 - Research macro data ([PR #127](https://github.com/pyeconomics-dev/pyeconomics/pull/127))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| CBO directs automation to CSV repository; archive begins February 2024 | spec-rot | #127 task and guide | Exact publication dates and vintage-matrix tests |
| SPF release timing, annual horizons, employment/housing units and sentinels differ | architecture | #127 source-specific parsers and PR decisions | Unit, vintage and missingness regressions |
| Atlanta ZIP size and PWT inflated dimensions; openpyxl writes temporary files | security | #127 finite archive bounds and memory-only writer | ZIP/XML bounds and no-tempfile regressions |

## Step 10 - Research finance data ([PR #129](https://github.com/pyeconomics-dev/pyeconomics/pull/129))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Source formats mix annual/monthly/daily, weighting and percentage/decimal units | architecture | #129 parser-specific decisions and guides | Provider contracts and source-unit regressions |
| Root source doctests bypassed isolated config/cache fixture | bug | #129 root-loaded pytest plugin | Subprocess preserves external user files |
| Yahoo client errors could reveal private paths | security | #129 generic scrubbed failures | Yahoo canary tests |
| Yahoo automation and library-only storage forbidden | security | #129 opt-in and synthetic recordings | Live harness excludes Yahoo; no Yahoo egress; cassette scanner |

## Step 11 - Semantic catalog ([PR #130](https://github.com/pyeconomics-dev/pyeconomics/pull/130))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Resolved values need source records; derived operands need add/alignment | upstream-gap | #130 Resolved and shared transforms | Offline concept/transform/alignment tests |
| Candidate unit/frequency/seasonality must match; PWT rkna is services, not stock | bug | #130 exact candidate definitions | Deep catalog validation and live concepts |
| FRED daily rates lack ALFRED vintages; BLS keyless units incomplete | upstream-gap | #140 vintage metadata and keyed/fallback policy | Vintage refusal and unit-kind tests |
| Parameter/window inputs cannot be guessed; lazy imports must stay lazy | architecture | #130 definitions and resolver rules | Parameter and import-isolation tests |
| Providers disagree on empty windows; ECB daily history exceeds response cap | upstream-gap | #131; maintainer and next provider parser work | Resolver no-observation fallback and bounded request windows |

## Step 12 - Live bindings ([PR #132](https://github.com/pyeconomics-dev/pyeconomics/pull/132))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| SEP table could not bind a scalar field | upstream-gap | Step 13 task; #140 series concepts | SEP binding tests |
| Missing key/offline cache must not turn into revised-data fallback | bug | #132 resolver failure and provenance rules | Bound error/canary tests |
| Manifest sort, overrides and parameterized concepts need stable contracts | architecture | #132 schema 2, bind_model seams and AGENTS.md | Deterministic manifests and override provenance |
| Core cannot import catalog for cards | architecture | #132 CandidateNote/lazy facade | Layering and lazy-import tests |

## Step 13 - Monetary policy ([PR #140](https://github.com/pyeconomics-dev/pyeconomics/pull/140))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Period-end cap, wrong neutral-rate estimate and filtered union field shapes | bug | #140 | Quarter-end, estimate-identity and calculation-filter regressions |
| Adjusted rule floor, ignored path inputs and card calculation | bug | #140 consistent policy and validation | Scalar/path goldens, bounds and card tests |
| Lag transform, parameterized columns and band charts missing | upstream-gap | #140 shared vocabulary and later-step context | Transform/registry/chart tests |
| Legacy parity has three intentional convention differences | process | #140 explicit per-case classifier | Every immutable legacy fixture case checked; static hashes |
| NYFed history, cache parser version and pre-existing properties | bug / architecture | #135/#136/#137/#139 | Named issues, fallback and CI-profile coverage |

## Step 14 - Macroeconomics ([PR #144](https://github.com/pyeconomics-dev/pyeconomics/pull/144))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Windows ended on different dates/calendars; converted lookback and short source history | bug | #144 alignment/min_observations | Window/calendar/convert regressions |
| Robust covariance multiplication lost precision | bug | #144 QR sandwich and validation | Exact arithmetic and statsmodels oracles |
| Okun regression direction in task was reversed | spec-rot | #144 task and cited source convention | Published estimate golden |
| Ratio/output bounds and conditional/vacuous tests | bug | #144 review corrections | Negative cases and invariant/contract suite |
| BLS/CBO limited histories and annuity dev-profile property | upstream-gap / bug | #141/#142/#143 | Short-history fallback and named issue reproductions |
| Missing October 2025 BLS data; printed Solow slips | process | #144 cards and source recomputation | No gap filling; cited data-column goldens |

## Step 15 - Fixed income and equity ([PR #146](https://github.com/pyeconomics-dev/pyeconomics/pull/146))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Curve row bindings need paired tenors and column-specific units | upstream-gap | #146 binding contract and guide | Registry, curve-row and pairing tests |
| Calibration precision, underflow, schedules and premium roots | bug | #146 stable arithmetic and bounds | QuantLib/oracle/boundary regressions |
| Tiny shifts, negative forwards, lagged Shiller earnings and printed KWF rounding | process | #146 explicit cards and PR decisions | Guarded shifts and cited tolerances |
| Brinson Carino log ratio rounded past domain | bug | #145 closed by blocking #146 fix | Regression, contracts and CHANGELOG |
| Independent scalar observations may have different dates | architecture | #146 documented provenance; future binding alignment | Each DataSource records observation_end |

## Step 16 - Asset pricing and portfolio ([PR #153](https://github.com/pyeconomics-dev/pyeconomics/pull/153))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Panel models require matrix bindings and ordered columns | upstream-gap | #153 shared bindings contract | Matrix shape, gaps and alignment tests |
| FF3/FF5 factors differ and must not share SMB/market series | bug | #153 separate concept profiles | File-specific binding tests |
| Subnormal least squares/covariances, tiny p-values and ERC/HRP cancellation | bug | #153 eight review fixes | Fuzz, scale regressions and independent oracles |
| certifi dependency advisory found by the gate | security | #153 updated certifi for PYSEC-2026-4320 | Locked dependency audit and reviewed licence closure |
| Shanken divisors, Idzorek closed form and He-Litterman edition | process | #153 PR decisions/cards/citations | Identity and published-table goldens |
| Mean-variance frontier overflow and HP dev-profile property | bug | #151/#152 | Named issue reproductions |

## Step 17 - Econometrics ([PR #160](https://github.com/pyeconomics-dev/pyeconomics/pull/160))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| arch has no cp315 wheel | upstream-gap | Maintainer-approved marker; #154 | Provider.excluded, needs_arch, extra_gaps; no silent skip |
| Third-party warnings reset filters; lazy statistics compute later | bug | #160 core.library_warnings | Captured-warning/contract tests |
| Ken French pre-1952 Saturdays rejected as business daily | bug | #160 DAILY parser and concepts | Historical Saturday regression |
| VAR order/term names, clipping/backcast and numerical edge cases | bug | #160 review fixes and documented conventions | arch/statsmodels oracles and 1500-draw contracts |
| MacKinnon coefficient and Johansen lag-zero implementation | bug | #155/#156 | Source-specific documented refusals/conventions |
| Warning concurrency, BLS gap profile and other daily sources | architecture / bug | #157/#158/#159 | Named issue reproduction and card limits |

## Step 18 - Readiness ([PR #165](https://github.com/pyeconomics-dev/pyeconomics/pull/165))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| FRED maintenance returned HTTP 200 HTML; key rotation needed | bug | #163 and approved rotation | Authenticated live rerun; heartbeat |
| No provider disable switch and local Yahoo harness wrong transport | architecture / bug | #162/#164, explicitly accepted GO | Rollback runbook; manual Yahoo verification |
| Candidate and dependency churn need a freeze | process | #165 GO/allowlist; freeze lifted after #166 verification | Byte-identical rehearsal/provenance and protected publishing |
| Randomized dev profile replays known property defects | bug | #112/#139/#143/#149/#152 | Explicit issue owners; canonical CI profile preserved |

## Step 19 - Production release ([PR #166](https://github.com/pyeconomics-dev/pyeconomics/pull/166))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Populated provider/concept ledgers break isolated toy registries | upstream-gap | #166 explicit released={} for toys | Production validation plus ledger completeness tests |
| Release comparison needs decoded UTF-8 metadata; stable import needs a key | process | #166 comparison and metadata-only stable check | Independent archive/install verification |
| PyPI JSON precedes simple-index propagation | process | #166 bounded retry and no-cache project lookup | Fresh PyPI core/extras/stable smokes |
| BLS keyless v1 upstream 503 | upstream-gap | #166 supported v2 through tester keyring | 12 observations without FRED; historical ALFRED recipe |

## Step 20 - Verification rollup

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Task still treated SEC as deferred and used stale module names | spec-rot | Step 20 task/V-matrix amended in this PR | Exact 31-id plan/readiness/entry/ledger checks |
| System Python 3.11 cannot parse Python 3.12 generic declarations | process | Stdlib textual import/definition checks where needed | Fast mode requires no project import/install |
| A successful live workflow alone could conceal a skipped Taylor/CAPE test | process | JUnit test-level verification in --live | V13.3/V15.3 refuse skipped/missing test cases |
| New required checks must preserve existing app-bound checks | process | Narrow strict required-status-check update after CI passes | V20.7 and protection snapshot comparison |
| FRED can serve latest EFFR beside genuine historical ALFRED inputs | process | Published recipe requires historical PCEPILFE/NROU/UNRATE and explicit revised labels | V19.3 checks vintages and real-time periods without hiding revised data |
| Known randomized properties are unsuitable as a canonical profile | process | Earlier --post invocations inherit the repository's required CI profile | All tests still collected; known dev-profile issues retain their owners |
| Not-in-scope text still referred to unavailable linearmodels wheels and open PR #61 | spec-rot | Phase roadmap updated from Step 16's recorded decision and closed PR state | Reviewed oracle admission policy; ordinary dependency maintenance |
| V8.2 and V16.2 must include every component named by their matrix rows | bug | Verifier combines suite/licence and suite/installed-smoke results before reporting PASS | A failed component fails its own V verdict and the overall run |
| Regex-only import checks miss comma-separated imports | bug | Standard-library tokenization in static check 19 | Import mutation proof; no package import or Python 3.12 parser needed |
| The legacy stable probe inherited Python 3.13 and pip correctly chose 0.1.0 | bug | Stable-only venv uses Python 3.12, matching 0.2.6's Requires-Python >=3.11,<3.13 | V19.3 checks ordinary pip on the historical release's supported interpreter |
| Phase 2 --post already executes Phase 1 --post | process | Run Phase 2 and require its fresh V15.6 PASS, executing both older commands once | V20.6 fails on either the Phase 2 exit or a missing/failed nested Phase 1 verdict |
| Native workflow alerts require personal Actions delivery settings; inbox title searches are unsupported | process | Maintainer enabled Actions notifications; use repo and reason:ci-activity filters | Fresh failure notifications verified through the read-only GitHub API; actual receipt still requires maintainer confirmation |

## Synthetic alarms

Synthetic providers-live alarm run: https://github.com/pyeconomics-dev/pyeconomics/actions/runs/39879057448

Synthetic providers-heartbeat alarm run: https://github.com/pyeconomics-dev/pyeconomics/actions/runs/39879059980

Synthetic providers-live issue: https://github.com/pyeconomics-dev/pyeconomics/issues/173

Synthetic providers-heartbeat issue: https://github.com/pyeconomics-dev/pyeconomics/issues/172

These fresh proofs followed the maintainer enabling personal Actions
notifications. Heartbeat failed with the documented zero-day maximum age
and opened #172. The provider suite had exactly the intended alarm-test
failure: 328 passed, 36 expected skips, one intended failure (365 cases).
Its first report job hit a GitHub GraphQL connection refusal; after a stale
run state cleared through cancellation, attempt 2 reran only the report
job successfully. It opened #173 and closed #172 as superseded. A queued
replacement, 39881751605, was cancelled once report-only retry became
available; it is not counted as another completed provider proof.

The read-only GitHub API now verifies both failure notifications in the
maintainer's inbox: heartbeat thread 26575049211 at 2026-10-23 00:36:30 UTC,
and providers-live attempt 2 thread 26575508968 at 01:07:26 UTC. The
separate success/cancellation notifications are not counted as failure
delivery. No notification was marked read or altered by the audit.

Default heartbeat 39879177317 succeeded. Default providers-live
39882191814 is running.

Notification received: confirmed by the maintainer on 2026-10-22 for both fresh failure alerts. The maintainer replied, "Yes, I received both."

### Earlier attempts and recovery

The initial synthetic runs were providers-live 39831272424 and heartbeat
39831277068, with issues #169 and #168 respectively. The notification
settings gap was discovered while auditing receipt, so the fresh proof
above supersedes these initial runs for the final acceptance record.

Both failed and opened their issues; the live report job succeeded and closed
the older heartbeat issue as superseded. The live JUnit contains the intended
`test_live_the_alarm_fails_only_when_a_failure_is_simulated` failure, plus a
real BLS HTTP 503 after the harness's retry. This is recorded as an upstream
availability observation, not silently counted as a passing BLS test. A
default-input green run remains required. Default restoration runs were
dispatched: live 39836102739 and heartbeat 39836107089. The latter stalled
with contradictory pre-job/complete-job states beyond its ten-minute timeout;
it was cancelled normally. Fresh default heartbeat
[39838021877](https://github.com/pyeconomics-dev/pyeconomics/actions/runs/39838021877)
succeeded. Default live verification subsequently recovered as recorded below.

Default live run 39836102739 failed on three BLS HTTP 503 responses and opened
the real availability alarm #171, superseding #169. The same provider/catalog
requests passed through the unchanged published package's credential chain
locally, while a separate control query returned 503. This demonstrates
intermittent availability, not a justification to skip a source. Further
bounded default run 39840161120 stopped its live step at 19:39 UTC while its
run API remained in progress. Normal cancellation returned HTTP 502;
force-cancellation was accepted. It produced no completed provider verdict
and is not counted as green.

Fresh default providers-live
[39847835112](https://github.com/pyeconomics-dev/pyeconomics/actions/runs/39847835112)
succeeded: 329 passed, 36 expected skips, zero failures (365 JUnit cases).
ALFRED, historical Taylor and both Shiller CAPE model/binding cases each
passed. Both default workflows were green at that checkpoint. The real availability
alarm #171 was closed on this observed recovery, with evidence in comment
6350878000. No provider check, credential, permission or trigger changed.

Both synthetic issues are closed and now have comments pointing to this QA
record (comments 6349977166 and 6349977642). The real BLS availability alarm
has its own recovery evidence above.

No notification receipt is inferred from these earlier workflow conclusions.

## Phase 3 acceptance audit (ROADMAP section 4)

| Project criterion | Verification | Evidence |
|---|---|---|
| Every source in plan; metadata, licence, units, bounds and errors | V2-V10; static 30/72 | Exact 31 shipped ids including SEC; offline and restored default live runs pass |
| Catalog originator priority, hosted refusals and live resolution | V11 | Concept/transform/resolver suites; exact-HEAD RTD check |
| Declared bindings, overrides, vintages and manifest provenance | V12-V13 | Schema-2, canary, real-time/revised labels and published recipe |
| Eighteen new families with cards, cited goldens, invariants and contracts | V13-V17 | All 50 model ids; strict docs and clean core/extras smokes |
| Branch coverage floors and strict types | V1.2/V2.2; TYPES | Core 99.76%, data 96.13%, models 98.41%; strict types pass |
| No FRED disk storage or automated Yahoo; credentials stay local | V3-V5/V10/V20.4 | Gate, no-storage, layering, cassette and canary tests |
| Alpha publication with stable 0.2.6 unchanged | V18/V19 | Both index provenances, GitHub prerelease and fresh installs |
| Operations alarms and heartbeat, prior ledgers and required checks | V6.3/V20 | Fresh synthetic failures and maintainer-confirmed receipt; default restoration recorded above; both earlier --post audits and strict 22 checks pass |

## Pre-ship items and owners

Nathan Ramos, CFA owns each open issue below. These accepted limitations have
tracked destinations; they are not waived verification criteria.

| Destination | Owned work / guard |
|---|---|
| #52/#62 | Security advisory allocation and Scorecard backlog |
| #68 | GitHub Sponsors external approval; independent development continues |
| #109/#110 | Local URI-secret gate and yanked docs pin; security/dependency maintenance |
| #112/#137/#139/#143/#149/#152 | Existing randomized property failures; reproduce/fix without weakening contract bounds |
| #113/#114/#116 | Proxy, Pyodide transport and SQLite support; platform tests before enabling |
| #131 | Empty-window error consistency and bounded ECB history requests; next provider parser work |
| #135/#136/#141/#142 | NYFed history, parser-aware cache invalidation, long-history BLS/CBO support |
| #148/#150/#151 | Changelog encoding, Drive quota classification, mean-variance frontier overflow |
| #154 | Wheel rule: arch is marked python_full_version < 3.15; remove only after cp315 wheels and matrix verification |
| #155/#156/#157/#158/#159 | MacKinnon/Johansen discrepancies, warning concurrency, BLS-gap profile, other pre-1952 daily sources |
| #162/#163/#164 | Provider disable switch, maintenance-page errors and local Yahoo harness |
| Phase 4 | Generated CLI/REST/MCP, parity, bundles and AI narrative; preserve licensing, credential and deterministic binding contracts |
| Phase 5 | Production website/docs, migration guide, monitoring and stable RTD cutover |
| Phase 6 | Premium/BYOK providers and Bloomberg adapter; existing spike is contract evidence only |
| Phase 7 | Next-wave catalog, constrained optimization, synchronized scalar binding policy and SIFMA calendar |
| Phase 8 | Paid account features |

SEC access is resolved and has no carry-over. Personalized advice, trading
and redistribution of licensed data remain outside scope. No credential or
contact appears in this record.

## Final verification evidence

Initial frozen --python passed in 1346 seconds: 100 fast and 21 Python verdicts,
zero failures. The full suite passed 7755 tests with 3 Windows platform skips;
365 live tests were deselected. Coverage: core 99.76%, models 98.41%, data
96.13%. Ruff, strict mypy and ty pass. A fresh strict Sphinx build executes
the tutorial and verifies every model, provider and concept HTML page. Wheel
and sdist pass strict Twine and content allowlisting; separate core/extras
wheel installs smoke all families across 13 domains.

The latest complete audit and remaining closure criteria are recorded below.
Only completed checks are recorded as PASS.

The first full --security run passed in 710 seconds: 100 fast and 3 security
verdicts, zero failures. Semgrep rule tests, 291 import/layering tests, the
whole-tree gate, 221 cassette scans and the orphan-clone secret scan passed.
Both Phase 3 CI jobs passed at c37f3d2; Ubuntu's static step took 4 seconds.
Main now requires both 03 contexts, preserving all 20 previous app-bound
contexts: 22 strict checks in total. A before/after comparison confirms every
other protection field is unchanged.

All 38 CI checks passed at 6a47cb7. The first corrected-head --post attempt
passed its Python, security and all ten read-only live checks, then failed
the stable-install assertion on Python 3.13 and the unconfirmed notification
criterion. Its alpha core/extras smokes and historical live recipe passed.
That attempt was stopped before changing the verifier; it is not counted as
a passing --post or as completed earlier-phase evidence. The stable-only
interpreter fix leaves the alpha tests on the project's interpreter.

The complete corrected `--post` at 143f299 finished in 5455 seconds with
137 PASS and one FAIL: fast 100/0, Python 21/0, security 3/0, live 10/0,
post 3/1. The sole failure is V20.5, because the maintainer has not confirmed
receipt of the synthetic notifications. No receipt is inferred or invented.
Fresh published alpha core/extras, BLS/ALFRED recipe, ordinary stable 0.2.6
on Python 3.12, and current PR checks passed. All 38 CI checks passed at
143f299, including the twelve OS/Python cells and both Phase 3 jobs.

Phase 2's complete `--post` passed in 3264 seconds: 83 fast, 16 Python,
3 security, 6 live and 4 post verdicts, zero failures. Its fresh V15.6 proves
the actual nested Phase 1 `--post` also passed. Neither earlier command was
skipped or replaced by a saved result.

Both default workflows are restored as recorded above. The complete audit
started before that restoration finished; after actual notification receipt
is recorded, a final canonical `--post` must pass with the newest default
runs already green. The PR remains draft. Final evidence-head CI, a passing
canonical audit, notification confirmation, merge and exact-main validation
remain closure work; Phase 3 is not yet declared complete.
