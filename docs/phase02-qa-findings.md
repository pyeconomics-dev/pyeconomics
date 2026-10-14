# Phase 2 QA findings

Phase 2 delivers the model engine and 32 data-free families in 11 domains,
released as `1.0.0a1`. This rollup records findings and their destinations;
the linked PRs retain the detailed review, sources and validation evidence.
No finding is deferred only in chat. Nathan Ramos, CFA owns the open issues
and future-phase work below. Historical decisions are preserved as history.

## Step 1 — Conventions (PR #71)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Decimal rates, fractional-period tolerance and finite bounds needed one policy | architecture | ADR-0008, accepted in #71 | Unit/tolerance tests and registry rules |
| NumPy/SciPy/pandas/dateutil licence metadata needs reviewed interpretation | process | Reviewed exceptions in #71 | Licence hook matches exact metadata and requires reasons |
| Pyodide baseline differs from newest PyPI dependencies | upstream-gap | #71 lower bounds and CI Pyodide smoke | V1.1, V1.3 |
| Phase 1 citation version, ADR index and clean-install checks pinned skeleton state | spec-rot | #71 verifier narrowing and Phase 1 addendum | Phase 1 verifier plus checks 2, 7, 39 |
| Warning emission needs a single collector-aware path | upstream-gap | Step 3 context patched; implemented in #76 | Warning-context and root-finding tests |
| Stale root package, Windows newline/quoting and file headers can mislead validation | process | AGENTS.md and shared toolchain memory | Executable pytest, formatter, header and hygiene hooks |

## Step 2 — Dates (PR #73; ledger correction #74)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| ICMA reference periods clamp February differently from independently anchored shifts | bug | #73 reference-period implementation | QuantLib and February regression |
| Calendar provider silently returns empty holidays outside supported years | spec-rot | #73 task and explicit provider bounds | Out-of-range InputError tests |
| QuantLib US calendar omits observed Juneteenth in 2021 | process | #73 documented OPM exception | Exact one-date difference and expected booleans |
| Pyodide lacks holidays; QuantLib date/sequence/type limits differ | upstream-gap | #73 pure-Python holidays install and oracle adaptation | Pyodide CI, supported date tests, strict types |
| PowerShell encoding damaged ledger separators | process | #74 correction; shared Windows memory | UTF-8 byte writes and reviewed ledger diff |

## Step 3 — Registry (PR #76)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Stacked array alias constraints can override a field's length | upstream-gap | #76 aliases carry elements only; Step 3/4/6 contexts patched | Registry rejects missing field max length |
| Computed fields, validators and weakened config bypass declared bounds | bug | #76 validation hardening | Negative toy specs for rule slugs |
| Allowed scientific libraries also expose I/O and global randomness | security | #76 purity rules and fixtures | Semgrep tests and import allowlist |
| Recursive discovery can deadlock; duplicate identities must remain reportable | bug | #76 loading guard and recorded conflicts | Discovery/reentrancy/conflict tests |
| Huge array conversion and datetime64 overflow precede normal validation | bug | #76 pre-conversion caps and date range checks | Array input regressions |
| Lax numeric/date coercion accepts booleans and epoch numbers | bug | Issue #75; owner Phase 3 core hardening | Open issue; explicit input guidance in release notes |
| Same canonical id with a replaced implementation cannot be detected by an identity ledger | architecture | Step 14 task patched; #96 records policy limitation | Released-id mapping tests and model-version review |
| Decorator shadows module import; asyncio conflicts with socket isolation | process | AGENTS.md and shared registry memory | Explicit imports, thread/context tests, strict types |

## Step 4 — Results and manifests (PR #77)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Result hashes must exclude manifest and include model identity/version | architecture | #77 canonical hash contract | Determinism and round-trip tests |
| ECMAScript JSON number rendering differs from Python int/float parsing | bug | #77 bounded integers and float-aware round trips | RFC 8785 Appendix B and independent oracle |
| Optional exports/plots must not pull libraries into core | architecture | #77 lazy conversions, extras and test-only Arrow/Polars | Missing-dependency tests and clean core/extras smoke |
| Schemas must avoid computing outputs; cards tolerate absent extras | process | #77 input-only examples and card fallback | Schema/card tests |
| Release smoke must use scripts from the tagged release outside a checkout | upstream-gap | #77 release workflow and smoke | Installed-wheel tests; V4.3, V12.3, V14.3 |
| Root package/egg-info shadow imports and metadata; secret assertions can leak values | process | Shared results/toolchain memory | Outside-checkout smoke and name-only credential checks |

## Step 5 — Harness (PR #78)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Vacuous registry, golden, invariant or coverage checks can falsely pass | bug | #78 rule tests; #79 removes empty-catalog skips | Negative toys, invariant meta-test, nonempty-registry guard |
| Cross-field validators need valid strategies; errors need documented limitations | architecture | #78 OVERRIDES and contract policy | Contract and strategy-rule tests |
| Nonliteral/class/module markers or skipped properties defeat invariant coverage | bug | #78 AST scanner | Invalid marker regression cases |
| Golden tolerances, id mapping, minimum cases and citation sources need a format | process | #78 golden README and loader | Loader negative tests and curriculum citation guard |
| Test helper imports must avoid repository root | process | #78 pytest/mypy/ty paths | Three type tools and executable pytest |

## Step 6 — Foundations (PR #79)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Extreme compounding, tiny rates, moments and payment/period solves leak overflow or cancellation | bug | #79 stable arithmetic and bounded-output policy | Golden/property/contract boundary regressions |
| Amortization and annualization round beyond output bounds | bug | #79 sized bounds and endpoint clamp | Focused regressions and contract draws |
| Empty model coverage and empty contract/golden registries were vacuous | upstream-gap | #79 harness tightening; later contexts patched | Coverage floors and nonempty registry test |
| Long citation keys resemble secrets; property markers require literals | process | #79 short reference keys and literal markers | Gitleaks and invariant meta-test |
| NIST rounded example and spreadsheet page descriptions are imperfect | process | #79 cited precision and independent recomputation | Per-case tolerances and locator notes |

## Step 7 — Documentation preview (PR #80)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Sphinx config name collision and duplicate AutoAPI/Napoleon fields fail -W | bug | #80 aliased version and use_ivar | Fresh warnings-as-errors docs build |
| Docs dependencies were missing from default lock export audit | security | #80 all-groups export and reasoned docs-only licence purls | Pylock freshness, audit and runtime closure check |
| Roadmap/ADR/generated examples must not be collected as authored examples | bug | #80 scoped Sybil collection | Sybil suite and notebook execution |
| Notebook execution needs loopback while external networking stays blocked | security | #80 audit hook and kernel socket policy | Offline docs build and socket-isolated examples |
| Ignored build output can masquerade as new preview | process | #80 fresh output builds | V7.2 |
| RTD activation/defaults and successful exact-commit deployment require separate proof | upstream-gap | #80 deployment verified, build 35066062 | V7.3 API plus live pages |
| RTD query filter, canonical host, User-Agent and Windows token paste were traps | process | Shared docs-preview memory | Version-specific build query; no credential logging |
| Phase 1 forbade docs/conf.py | spec-rot | #80 narrow verifier exception and addendum | Phase 1 check 19 retains all other exclusions |

## Step 8 — Fixed income (PR #82; correction #91)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Treasury Appendix B uses first-fraction simple interest and rounded printed values | spec-rot | #82 explicit street/treasury convention and tolerances | Cited Treasury golden cases |
| Coupon timing is period less accrued; QuantLib range/EOM differs | bug | #82 timing and oracle inputs; long-stub defect separately below | Calendar and QuantLib tests |
| Face/bump underflow and bootstrap cancellation | bug | #82 meaningful floors and stable recurrence | Boundary and flat-curve regressions |
| Numeric Literal fields can evade unit validation | bug | Issue #81; owner Phase 3 registry hardening | Schema checks currently catch catalog omissions |

## Step 9 — Derivatives and international (PR #84)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| QuantLib American binomial can fall below European; its CRR probability is approximate | process | #84 finite-difference American oracle and exact-probability transformation | Cross-library and Greeks tests |
| Implied volatility endpoint prices differ by rounding | bug | #84 endpoint tolerance | Endpoint regression |
| Input docstring overwrites schema summary | bug | Issue #83, fixed in #87 | Schema summary regression |
| Derandomized CI exposed Step 8 bootstrap/curve property draws outside valid conditions | bug | #84 valid-domain filters | CI-profile full suite |
| Vollib Greeks use per-percent/per-day units; simplejson licence differs in GitHub | process | #84 explicit conversion and test-only purl | Oracle tests and runtime licence closure |
| Recalled GK example did not reproduce | process | #84 excluded example; verified alternate cases | Golden citations and independently reproduced values |

## Step 10 — Equity, corporate and accounting (PR #86)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Tiny cash-flow perpetuity factor overflows despite finite valuation | bug | #86 divide cash by spread first | DDM/H-model/FCF regressions |
| MIRR log subtraction rounds inclusive endpoints outside range | bug | #86 slack and clamp | Endpoints and scaled-project tests |
| Shared IRR misses roots at inclusive bracket endpoints | bug | Issue #85; owner Phase 3 shared numerics | Exact cross-model parity retained; release limitation |
| DCF timing, PI/payback, ratios and scoring use competing conventions | process | #86 precise cards/schemas and PR citations | Cited goldens, DuPont and NPV/IRR parity |
| Original Altman/Beneish/Piotroski definitions need exact coefficient/denominator descriptions | spec-rot | #86 metadata and TATA clarification | Source-specific cases |
| NumPy Financial 1.0 lacks typing on Python 3.12 | process | #86 narrow external-module mypy override | Full supported-version CI |

## Step 11 — Portfolio and performance (PR #87)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Compounding/linking overflow, loss underflow and cancellation | bug | #87 log-space returns and Carino linking | Long/extreme strategies and regressions |
| Tiny covariance matrices appear singular without scaling | bug | #87 scaled solves | Minimum-variance oracle and scale tests |
| CRRA near gamma=1 loses precision | bug | #87 expm1/log1p implementation | Near-log-utility regressions |
| PSD covariance is intentionally refused by the closed-form solver | process | #87 limitation and corrected message | Refusal regression and card |
| Shared annualization lived in a model domain | upstream-gap | #87 moves helper to core/descriptive.py, adds compound_return/has_spread; Step 6/12 contexts patched | Golden parity; annualization within 1e-12 above 100 clamps |
| Schema description overwritten by input docstring (#83) | bug | #87 removes adapter description before merge | Schema regression |
| empyrical-reloaded 0.5.12 imports undeclared pytz, pins old peewee and rejects capture annualization | architecture | #87 rejects dependency; SciPy/NumPy oracles; decision carried here | Independent recomputation; throwaway overlay agreed within 7e-14 |
| Modified Dietz differs from Dietz's original midpoint method; matrix coercion is domain-local | spec-rot | #87 precise citation and task; bounded row inputs | Cards, import allowlist and matrix tests |

## Step 12 — Risk and econometrics (PR #88)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Statsmodels resets warning filters, hiding warnings from warnings-as-errors | bug | #88 explicit warning recording | stray_warnings and contract draws |
| Unscaled OLS, tiny residuals, exact auxiliary fits and negative rounded statistics | bug | #88 equilibrated regressors, residual scaling, relative exactness and zero clamp | NIST, NumPy and diagnostic regressions |
| Signed zero changes LAPACK despite canonical equality | bug | #88 normalizes inputs before QR | Rerun-from-canonical-input regression |
| Extra import allowlist needed literal extra and domain restrictions | security | #88 allowlist hardening | Import AST tests and missing-extra smoke |
| SciPy tiny-scale expectation oracle loses precision | process | #88 standardized oracle | Independent risk tests |
| Catalog nonempty guard omitted prior step ids; patsy needs reviewed licence | upstream-gap | #88 roadmap-derived ids and reviewed patsy exception/purl | Catalog guard, audit and licences |
| Basel sources moved; recalled quantile/DOI was wrong | process | #88 corrected primary sources and high-precision recomputation | Golden source locators |

## Step 13 — Readiness (PR #90 NO-GO; #91/#92 fixes; #93 GO)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| US 30/360 long first coupon incorrectly split at notional dates (#89) | model-error | #91 whole-period accrual; model versions 2; dev2; public erratum; #89 closed | Three Decimal goldens and 72 deterministic QuantLib combinations |
| Python 3.15 became final (#65) | process | #92 twelve-cell CI, classifier, dev3 and Phase 1 addendum; #65 closed | Matrix verifier and final interpreter support |
| uv 0.12.15 resolves Python 3.15 to RC2 | bug | #92 CI uses uv 0.13.0 | Twelve final-interpreter cells |
| Initial candidate failed readiness; account/publisher facts and GO cannot be inferred | process | #90 archives NO-GO; #93 fresh dev3 rehearsal and explicit GO/all confirmed | Eleven-section readiness record and V13 checks |
| Docs landing and README skeleton wording stale (#94) | spec-rot | #90 docs; #96 approved README change; #94 closed | Release banner/content review |
| Zero marked library oracles do not imply skipped validation | process | #93 audit explicitly explains cited identities/recomputations | Full golden/invariant/contract suite |

## Step 14 — Production alpha (PR #96)

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Populated ledger invalidates empty toy registries and shipped doctest | upstream-gap | #96 isolated toy released={} and maintainer-approved documentation addendum | Registry/smoke/ledger regression tests and artifact comparison |
| Ledger fingerprints constrain schema evolution without proving implementation identity | architecture | #96 documented mapping-only decision | Permanent-id checks and review/model-version policy |
| Release differences must be only the GO artifact list | process | #96 exact member/content comparison against dev3 | Readiness allowlist; independent archive/provenance verification |
| Local extras transport stalled | process | #96 fresh environments, bounded retries and normal cache | Independent core/extras/stable installs completed |
| Production release needs protected deployment and independent published proof | process | #96 explicit approved tag/deployment/release; run 38498779970 | V14.2/V14.3; attestation, smoke and legacy docs checks |

## Step 15 — Verification rollup

The verifier keeps Phase 1's six modes, independent numbered checks, V-ids,
failure exit status and totals by mode. Static checks test minimum permanent
deliverables, not a moving package version or exact future catalog size.
The alpha tag, historical readiness decision and release evidence are immutable
milestone checks. Full-suite verdicts cover all collected domains together;
they do not claim that a local run reproduces the entire OS/Python CI matrix.

| Finding | Triage | Destination | Guard |
|---|---|---|---|
| Nine-cell language and pending #65 are stale after #92 | spec-rot | This PR updates V1.2 and scope text | Current CI matrix remains the supported-version authority |
| Synthetic nonexistent version fails at tag checkout before pip | process | Scope explicitly recorded below; production smoke proves healthy path | V15.5 checks failed dispatch; V14.3 runs actual installed models |
| Phase completion requires both 02 jobs required without dropping existing protection | process | This PR preserves all checks in narrow strict PATCH after both jobs pass | V15.7 |
| Fixed issue #83 remained open and lacked an explicit docstring toy | process | This PR adds input/output docstrings to the schema toy; closes #83 after regression verification | Existing parameterized schema-summary assertion now exercises both descriptions |
| uv's global default selected Python 3.15 for clean venvs after a Python 3.13 suite, requiring slow new wheel downloads | process | This PR selects the project's tested interpreter explicitly for local wheel smoke | Fresh venvs remain isolated; supported-version coverage is CI's twelve-cell matrix |

## Synthetic alarm

Synthetic alarm run: https://github.com/pyeconomics-dev/pyeconomics/actions/runs/38503796017

Notification received: confirmed by the maintainer 2026-10-13 (America/New_York) in this Step 15 conversation.

Dispatched `release-smoke.yml` on main with index `testpypi` and nonexistent
version `0.0.0.dev0`. Conclusion: failure. The checkout of that nonexistent
tag failed, so this proves the workflow failure notification route; it does
not claim the model execution step itself failed. It published nothing.
Production release run 38498779970 and V14.3 exercise the successful model
and extras paths. Maintainer response: “Yes, notification received”.

## Phase 2 acceptance audit (ROADMAP §4)

| Project criterion | V-checks | Result/evidence |
|---|---|---|
| Every finalized 2.6 entry registered, validated, card, at least three cited goldens and every invariant tested | V3.2, V5.2, V6.2, V7.2, V8.2–V12.2 | Local PASS: 3,039 tests; registry validation; fresh docs build; final CI/post pending |
| Input/output schemas validate against 2020-12; canonical JSON round trips lossless | V4.2 | Local PASS: full suite plus 304 schema tests; RFC vectors and independent oracle included |
| Strict core types; core ≥95%, models ≥90% branch coverage | V1.2, V5.2 | Local PASS: mypy; core 99.89%, models 99.65%, total 99.75% |
| Clean alpha install executes one model per domain; ordinary pip retains 0.2.x | V14.2, V14.3 | Pending final post run; #96 independent publication check passed |
| Security gate every commit; socket-isolated tests; bounded inputs; clean lock audit | V1.4, V3.2, V3.3, V15.4 | Local PASS: all nineteen all-file hooks and full socket-isolated suite; final CI/post pending; no bypass |
| Operations: health signal and alarm seen to fire with an owner/runbook | V14.3, V15.5 | Alarm PASS with maintainer confirmation; final health recheck pending |

## Pre-ship items

Each item has an existing issue or a named owner phase; these are documented
limitations, not untracked tasks or silently waived acceptance criteria.

| Item | Destination / owner |
|---|---|
| Boolean/date coercion | #75, Nathan Ramos, CFA; Phase 3 core hardening |
| Numeric Literal unit detection | #81, Nathan Ramos, CFA; Phase 3 registry hardening |
| Inclusive IRR bracket roots | #85, Nathan Ramos, CFA; Phase 3 shared numerics |
| Scorecard dispositions and legacy CVE allocation | #62 / #52, maintainer security backlog |
| Sponsors account linkage/listing | #68, ROADMAP 8.1; maintainer/GitHub Support |
| Data bindings, vintages and 18 live-data entries | Phase 3 |
| Generated CLI/REST/MCP, parity, bundles and AI narrative | Phase 4 |
| Production docs, migration guide, RTD stable cutover, monitoring, web and launch | Phase 5 |
| Premium/BYOK data | Phase 6 |
| Syllabus crosswalks, next-wave models, constrained optimization, attribution beyond Carino and cash conversion cycle | Phase 7 |
| GARCH/estimator independent libraries when their entries arrive | Phase 3 and Phase 7 adapters |
| US bond-market SIFMA calendar | Phase 7 fixed-income batch, with primary source review |
| Paid accounts/features | Phase 8 |
| Empyrical dependency and same-id implementation replacement | Decisions above; future changes require reviewed policy/dependency work |
| Polars/Arrow caller installation; quantstats/yfinance dependency closure | ADR-0008/0004; retained exclusions, future proposal requires review |

Personalized advice, trading features and licensed-data redistribution remain
excluded under ROADMAP §6. Pre-releases have no stability guarantee. Model
cards state convention, domain and bounded-output limitations.

## Final verification evidence

Pending: local `verify-phase02.sh --post`, final-head CI, strict required-check
update, merge and main HEAD deployment recheck. Phase completion is recorded
only by this step's merged ledger mark after all evidence is green.
