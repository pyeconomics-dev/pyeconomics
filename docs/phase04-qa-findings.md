# Phase 4 QA findings

Phase 4 ships the programmatic surfaces in `1.0.0b1`: the `pyeconomics`
command line, exports and reproducibility bundles, the local and hosted REST
API with its generated clients, the MCP server with its chart app and MCP
Registry entry, the optional AI narrative, the service container and the
staging deployment on Cloud Run behind a Cloudflare Worker edge. The
permanent ledgers hold every earlier id unchanged (50 models, 31 providers,
171 concepts). This rollup preserves each step's findings, decisions and
guards. Nathan Ramos, CFA owns the remaining issues and future-phase work.
Linked PRs keep the detailed evidence, tradeoffs and validation.

## Step 1 - Surfaces baseline and concurrency ([PR #175](https://github.com/pyeconomics-dev/pyeconomics/pull/175))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| `core.library_warnings` swapped or lost warnings across threads | architecture | #157 closed by #175 (RLock and owner-thread routing) | Threaded regression, routing and nesting tests |
| Another thread's warnings pass the "always" filter during a block | architecture | #174 (open) | Documented on the function |
| `data.configure` is process-wide | architecture | #175 docstring and keys guide | Threaded settings tests |
| Registry, redaction, key chain, ContextVars, cache store and `core.random` audited | process | #175 audit table: safe | `test_core_concurrency.py`, `test_data_concurrency.py` |
| Local dev profile replays the OLS degenerate-design property | bug | #139 (open) | CI profile; tracked reproduction |
| ty needs its own ignore beside each `type: ignore` | process | Quality toolchain notes | ty job |

## Step 2 - ADR-0012 and the surface core ([PR #177](https://github.com/pyeconomics-dev/pyeconomics/pull/177))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Task's `tests/surfaces/test_layering.py` clashes with the data layer's basename | spec-rot | #177 task edit; `test_surface_layering.py` | Strict types and unique basenames |
| A 1 MiB codec limit refuses valid inputs (2.65-5.83 MiB) | spec-rot | ADR-0012: 16 MiB local, 1 MiB hosted | Codec limit tests |
| The error table needed `data-unavailable`, `input-too-large` and `budget-exceeded`; a strong ETag breaks RFC 9110 | architecture | ADR-0012 accepted additions; weak `W/"<result_sha256>"` | Error-table walk; envelope tests |
| urllib3 messages carry `host=` and redirect hosts | security | #177 provider-named details; the terms page in `terms` | `test_problem_canary.py` |
| A public `type` attribute makes AutoAPI cross-references ambiguous | process | #177 `type_uri` and `error_type` names | Strict Sphinx |
| ROADMAP named Upstash Valkey and promised hosted keys before Phase 8 | spec-rot | #177 ROADMAP amendments | Static check 8 |

## Step 3 - Registry export ([PR #178](https://github.com/pyeconomics-dev/pyeconomics/pull/178))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Syrupy's JSON extension writes CRLF on Windows | bug | #178 `tests/json_snapshots.py` LF extension | Snapshot suites on every cell |
| garch's first example cannot run on cp315 | upstream-gap | #154 (open); `example_result: null` for own-extra gaps only | `extra_gaps` assertion, never a skip |
| An unused snapshot fails the session while the summary says "passed" | process | #178 structural file-set test | Snapshot set equals the models |
| Results and figures hold versions and platform floats | architecture | #178 snapshots schemas and the index only | 102 snapshots; byte-identical exports |
| Dev profile replays known property failures | bug | #112/#137/#139/#143/#149/#152 (open) | CI profile |

## Step 4 - The pyeconomics CLI ([PR #179](https://github.com/pyeconomics-dev/pyeconomics/pull/179))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| rich-rst now declares `License-Expression: MIT` | spec-rot | #179 Dependency table and Step 4 requirement | Licence allowlist hook |
| Docs examples were wrong (window binds need `--as-of`; the policy rule needs `--calculation`) | bug | #179 docs fixes | `tests/cli/test_cli_docs.py` fences |
| Cyclopts reads `__annotations__` over `__signature__` | bug | #179 sets both; plain `Context` class | Generated-option and completion tests |
| Keys must never be arguments | security | #179 hidden prompt or `--stdin`, `Secret`, `store_key` | Keys LeakCheck canaries |
| bandit B604 on Cyclopts' `shell=` keyword | security | #179 inline `nosec` with its reason | Gate (bandit) |
| Pyodide lacks Cyclopts' closure | upstream-gap | #179 locked `--no-deps` installs | Pyodide job |

## Step 5 - Exports and bundles ([PR #180](https://github.com/pyeconomics-dev/pyeconomics/pull/180))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| openpyxl's `%.16g` drops the last bit | bug | #180 shortest round-trip number cells | 0.1+0.2, 2**-1074 and 17-digit pins |
| openpyxl spools sheets to temporary files | security | #180 validates cells before the workbook | No-tempfile regression; read-only container smoke |
| openfigi serves records, not frames | spec-rot | #180 task: records are exportable | `test_export_notices.py` |
| Frames carry series-level terms (BLS/OECD dates, World Bank, NY Fed) | architecture | #180 per-frame attribution in every format | Per-provider notice test, 31 providers |
| Formula injection in CSV and XLSX text | security | #180 `escape_text`; strings typed as strings | Read-back escaping tests |
| A bundle archive could carry hostile members | security | #180 `check_bundle` limits; reads JSON only | Bundle refusal tests; package-job rerun |

## Step 6 - REST API ([PR #181](https://github.com/pyeconomics-dev/pyeconomics/pull/181))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Starlette 1.10 deprecates httpx in TestClient | spec-rot | #181 `httpx2`; Dependency table | Warnings-as-errors suite |
| asyncio needs a socket pair under `--disable-socket` | process | AGENTS.md `LOOPBACK_ONLY` | Server tests refuse non-loopback |
| XLSX records its write second; byte comparison flaked | bug | #181; AGENTS.md | `xlsx_sheet` value comparison |
| Unknown route or method, foreign Host and full queue had no rows | architecture | #181 four serving rows | A problem per table row |
| DNS rebinding against a local server | security | #181 loopback-only `Host` unless `--allow-remote` | Host-check tests; package job |
| FastAPI `exclude_none` strips meaningful schema nulls | bug | #181 merges components after `get_openapi` | Component round-trip; OpenAPI snapshot |

## Step 7 - Hosted mode, fuzzing and clients ([PR #183](https://github.com/pyeconomics-dev/pyeconomics/pull/183))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| No provider disable switch | architecture | #162 closed by #183 (`disabled_providers`, `source-disabled`) | Gate-first tests; resolver failover |
| TypeScript 7 has no JS API; openapi-ts crashes | spec-rot | #183 pins 6.0.3; Dependency table | `clients` job (Dependabot #187 fails it, as expected) |
| openapi-ts pulls js-yaml with High advisories | security | #183 `overrides` js-yaml 4.3.2 | `npm-audit` hook |
| openapi-python-client silently drops colliding titles | bug | #183 retitle script, `--fail-on-warning` | `clients` job |
| Configuration refused `PYECONOMICS_EDGE_CREDENTIAL` | bug | #183 `_SERVER_SECRETS` exemption; AGENTS.md | Edge and settings tests |
| Hosted default limits silently answered the SSRF probe 429 | process | AGENTS.md `RateLimits.off()` rule | SSRF baseline proof |
| PyYAML has no cp315 wheel; soupsieve 3.0 yanked transitively | upstream-gap, bug | #182 (open); #184 (open, duplicates #110) | Wheel-rule marker on schemathesis; locked audit |
| `not live and not fuzz` broke Phase 3 check 17 | spec-rot | Check 17 narrowed; Phase 3 addendum | phase-verify (03) |

## Step 8 - MCP server ([PR #191](https://github.com/pyeconomics-dev/pyeconomics/pull/191))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| MCPServer derives schemas from signatures | spec-rot | Low-level `Server` (maintainer agreed) | Tool schema snapshots; SDK client validation |
| The stateless SDK still holds a GET SSE stream open | bug | #191 POST-only `/mcp` | 405 tests |
| MCP must refuse data whose terms forbid LLM use | security | #191 `LlmUsePolicy`, `llm-use-forbidden`, `surfaces.gate` | Gate tests through every tool |
| pywin32's adodbapi is LGPL-2.1 | process | Maintainer-reviewed licence exception | Licence allowlist |
| A job-level `env:` using the `runner` context silently broke ci.yml | process | #212 (open): actionlint in the gate | zizmor until #212 lands |
| Roadmap ladder PRs #190/#192/#193 forced rebases and check-16 races | process | Rebase before merge; rerun after the PR exists | phase-verify (01) |

## Step 9 - MCP Apps, the MCP Registry and evaluations ([PR #198](https://github.com/pyeconomics-dev/pyeconomics/pull/198))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| The stand-in world had written synthetic data into the real cache | bug | #198 deleted seven entries; refuses without `PYECONOMICS_CACHE_DIR` | `test_catalog_world_guard.py`; AGENTS.md |
| A gated as-of bind before 2024-02 cannot resolve CBO's NROU | bug | #195 (open) | The bound eval task is dated 2025-06-30 |
| NY Fed's EFFR history holds a Sunday | bug | #196 (open) | Live gated Taylor bind deferred |
| The tool list costs an agent about 69k tokens | architecture | #197 (open) | Measured in the evaluation page |
| The agent omitted `calculation` on family tools | process | #198 description sentence | Live eval 9/9; tools/list snapshot |
| mcp-publisher moved to v1.8.4 | spec-rot | Step 9 context | Version and SHA-256 pin |
| providers-live #194 is #150's Drive quota again | process | Triaged on #194; #150 (open) | Weekly providers-live |

## Step 10 - Cross-surface parity ([PR #199](https://github.com/pyeconomics-dev/pyeconomics/pull/199))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| A noise-free stand-in made VAR NaN on Linux and macOS | bug | #199 seeded noise | Bound parity requires bytes on every cell |
| MCP's `llm_use` policy changes bound bytes | spec-rot | Step 10 task: compare under the same policy | `test_parity_bound.py`; `test_mcp_gate.py` |
| `cache.bypass()` never reaches pool or portal threads | process | `cache.clear()` per surface; AGENTS.md | No record says `cache_hit` |
| Binomial convergence counterexample under the dev profile | bug | #137 (open) | CI profile |
| No surface disagreed | process | No surface change | Parity suite; `parity` job on the wheel |

## Step 11 - AI narrative ([PR #200](https://github.com/pyeconomics-dev/pyeconomics/pull/200))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Full-precision floats broke cross-platform cassette hashes | bug | #200 ten significant digits | Cassette replay on every cell |
| The roadmap said `[ai]` joins `[all]`; the extra stays empty | spec-rot | #200 cross-phase table and Step 16 checks | Static check 43; `test_ai_layering.py` |
| semgrep reads `input_tokens` as a credential | security | #200 renamed log fields, no suppression | `credential-logging` rule |
| OpenRouter added; Google's id is `gemini` | process | Maintainer kickoff decision | Provider tests |
| Prices go stale | process | Dated `ai/prices.py` | 180-day staleness test |
| The server problem test lacked the two new rows | bug | #200 | `test_server_problems.py` |

## Step 12 - Service container ([PR #201](https://github.com/pyeconomics-dev/pyeconomics/pull/201))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Phase 1 check 19 forbade any Dockerfile | spec-rot | Narrowed to hosted-mode markers; Phase 1 addendum | verify-phase01 check 19 |
| `grep -qF "$p"` read `--require-hashes` as an option | bug | `grep -qF --` in check 19 | verify-phase01 |
| Hosted Parquet and Arrow need pyarrow | process | Maintainer-approved locked hashes | Container smoke |
| `.dockerignore` must keep `src/pyeconomics/data/cache/` | bug | #201 negation rule | Container smoke |
| `rglob` walks `.venv` and `.git` on Windows | process | `os.walk` with pruning | Container test timing |
| Check 16 reads CRLF from `gh` on Windows | bug | #213 (open) | Ubuntu CI unaffected |

## Step 13 - Staging on Cloud Run ([PR #204](https://github.com/pyeconomics-dev/pyeconomics/pull/204), [#205](https://github.com/pyeconomics-dev/pyeconomics/pull/205), [#206](https://github.com/pyeconomics-dev/pyeconomics/pull/206))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Google Frontend reserves `/healthz` on `*.run.app` | spec-rot | #205 container startup probe; the Worker maps edge `/healthz` to `/version` | Worker tests; deploy verification |
| Probe payload keys did not match `/version` and results | bug | #205 | deploy-staging and staging-health probes |
| The wheel venv resolved unlocked dependencies, changing manifest bytes | bug | #206 locked `--require-hashes` | Deploy byte-equality check |
| A rollback pins traffic, so the next deploy's revision gets none | bug | #210 (open); runbook note added in Step 16 | Deploy `/version` SHA check fails loudly |
| The deploy service account holds project-level `roles/run.admin`; the runbook said service-level | security (low) | #211 (open); runbook corrected in Step 16 | OIDC limited to this repository's `main` |
| Phase 3 check 78 forbade non-token workflow secrets | spec-rot | Narrowed; Phase 3 addendum | verify-phase03 check 78; static check 64 |
| The primary billing account was at its five-project cap | process | Second billing account | $1 budget with Pub/Sub notifications |
| `ratelimit-url` was rotated to version 2 without a PR record | process | This record; the environment pins version 2 | V16.8; deploy verification |

## Step 14 - 1.0.0b1 readiness ([PR #207](https://github.com/pyeconomics-dev/pyeconomics/pull/207))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| Candidate and dependency churn need a freeze | process | Nine Dependabot PRs held; lifted after #208 | Byte-identical rehearsal |
| The Inspector comparison needs the target venv's Python | process | Step 15 context; V15.3 here | `inspector_checks.py` |
| `uv venv` defaults to CPython 3.15, where arch has no wheel | upstream-gap | #154 (open) | Wheel-rule marker |
| cmd.exe redirects `>=` passed through `npx` | process | Wrapper commands without flags | V15.3 |
| Staging needs both 429 layers proven | security | Readiness report; V13.3 here | Bounded two-layer burst |
| Readiness section 13 names `python_version` markers on arch and PyYAML; pyproject uses `python_full_version` on arch and schemathesis | spec-rot | This record (the GO record stays as signed) | Static check 59; pre-ship row for #154/#182 |

## Step 15 - 1.0.0b1 release ([PR #208](https://github.com/pyeconomics-dev/pyeconomics/pull/208))

| Finding | Class | Destination | Guard |
|---|---|---|---|
| uv_build writes `pyproject.toml.orig` into the sdist, missing from #208's list of changed files | process | This record (harmless copy of pyproject.toml) | Archive comparison |
| Cloudflare refuses Python's default User-Agent on Read the Docs | process | Step 16 verifier sends its own User-Agent | V15.2 |
| The Inspector's `--cli` reads `uvx --from` as its own flag | process | Step 16 verifier runs uvx through a wrapper | V15.3 |
| The release freeze was lifted | process | #208 comment on each Dependabot PR | Normal required checks |

## Step 16 - Verification rollup

| Finding | Class | Destination | Guard |
|---|---|---|---|
| gcloud's Git Bash wrapper fails under `MSYS_NO_PATHCONV=1` | process | The verifier calls gcloud with the variable unset | V13.4 |
| The Budget API is disabled on gcloud's default quota project | process | Budget read billed to `pyeconomics-staging` | V13.4 |
| The budget is named `pyeconomics-staging-monthly-budget`, not the recorded `-monthly` | process | V13.4 finds the budget by its project scope and topic | V13.4 |
| Workflow comments name the permissions they explain | bug | Static checks read workflow YAML without comment lines | Static checks 37, 48, 49 |
| Pyodide needs a Linux cross-build environment | process | V4.3 reads ci.yml's pyodide job for the verified commit | V4.3 |
| `uv run --python 3.14` would rebuild the project's `.venv` | process | The fuzz group runs in its own project environment | V7.2 |
| `uv sync` with one group removes other extras from `.venv` | process | --node uses `uv run` (inexact) with every extra | V7.3, V8.3 |
| A Windows server stopped by its wrapper leaves workers behind | process | `serving` sends Ctrl+Break to a new process group | V7.3, V8.3 |
| The first canonical `--post` changed directory inside the package check, so every later check ran outside the repository | bug | Fixed in this PR: the check runs in a subshell, and each mode starts from the repository root | The rerun below; every mode passed alone first |
| A fixed port (8765) can belong to another program, whose `/healthz` then answers the smoke | bug | Fixed in this PR: the verifier picks a free loopback port per server | V7.3, V8.3, V12.3 |
| The second canonical `--post` failed V13.3 without detail: Cloudflare's rate rule let one sub-second burst of 100 `/version` requests through, because its counters lag (30-request waves 1.5 s apart trip it on the third wave), and the helper failed closed without naming the invariant | bug | Fixed in this PR: the edge layer is probed in up to six spaced waves within one window, and every failing invariant prints a fixed `{"<invariant>": "FAIL"}` verdict | V13.3 (passed three times in a row before the rerun) |
| The third canonical `--post` failed inside Phase 2's nested whole-tree gate: pip-audit began reporting CVE-2026-115927, CVE-2026-116577 and CVE-2026-116578 in tornado 6.5.10 on 2026-10-28 (fixed in 6.6). tornado is a docs and development dependency only (ipykernel, jupyter-client) | security | Fixed in this PR: tornado 6.6 in `uv.lock` and `pylock.toml` | pip-audit hook; V16.4; the nested phases' gates |
| The maintainer's `.venv` held a half-removed PyYAML (no `__init__.py`) since 2026-10-26, which stops myst-parser's front-matter read | process | Reinstalled with `uv sync --reinstall-package pyyaml`; an interrupted exact sync while an editor held `_yaml.pyd` is the likely cause | DOCS; `vscode-venv-lock` practice |
| The parent's acceptance criterion names a past-date Taylor-rule agent task; Step 9 deferred it | spec-rot | Parent criterion amended in this PR; #195/#196 (open) own the Taylor task | V9.2 (nine scripted tasks) |
| V9.2 said eight scripted tasks; there are nine | spec-rot | Phase 4 roadmap amended in this PR | Static check 38; `test_mcp_agent_tasks.py` |
| The roadmap's known property issues omitted #137 | spec-rot | Phase 4 roadmap amended in this PR | CI profile |
| Open issues carry no GitHub assignee | process | This record names the owner of each | Pre-ship table below |
| The tool-list size differs by source (about 370 KB, 390 KB, 69k tokens) | process | #197 keeps the evaluation page's measurement | `docs/mcp-evaluations.md` |

## Synthetic alarm

Synthetic staging-health alarm run: https://github.com/pyeconomics-dev/pyeconomics/actions/runs/40699025411

Synthetic staging-health issue: https://github.com/pyeconomics-dev/pyeconomics/issues/209

The run was dispatched on `main` at 13:43 UTC on 2026-10-28 with
`simulate_failure: true`. Its probe passed `/healthz`, `/version` and the
model run through the edge, then failed on the simulation flag alone. The
report job succeeded and opened #209 (label `staging-health`); no older
`staging-health` issue was open. The read-only GitHub API shows the failure
notification in the maintainer's inbox: thread 26722915913, reason
`ci_activity`, "staging-health workflow run failed for main branch", at
13:44:46 UTC. The audit did not mark it read.

Notification received: confirmed by the maintainer on 2026-10-28. Asked whether the 13:44 UTC failure notification arrived, the maintainer answered "Yes, I received it."

The default probe, dispatched right after,
[40700695784](https://github.com/pyeconomics-dev/pyeconomics/actions/runs/40700695784),
succeeded, so the newest staging-health run on `main` was green before
`--live` and `--post` ran. #209 is closed with a comment pointing at this
record.

Budget notification received: 2026-10-28T13:35:23.133Z from the Pub/Sub subscription `staging-budget-alerts-sub` (message 22115757656926292): budget `1e2a0501-e932-43c4-bf39-0b95c895615d`, amount 1.0 USD, schema version 1.0.

Only the budget id, amount, timestamp and schema version were read out of
the message; it was pulled without acknowledgement and no billing account
detail is recorded.

## Phase 4 acceptance audit (ROADMAP section 4)

| Project criterion | Verification | Evidence |
|---|---|---|
| Parity across Python, CLI, REST and MCP for every golden case | V10.2, V10.3 | Parity suite on every cell; out-of-process sample on the wheel |
| Parquet pipes into pandas; XLSX opens with its manifest sheet; CSV escapes formula prefixes; a bundle reruns identically | V5.2, V5.3 | Format and read-back tests; bundle rerun from the clean wheel |
| Schemathesis finds no 5xx and no schema violation; oversized or over-budget inputs answer 413 or 422 | V7.2 | api-fuzz in both modes; codec and budget problem tests |
| Inspector over stdio and Streamable HTTP; stable tools/list snapshot; scripted agent tasks | V8.2, V8.3, V9.2 | Nine scripted tasks including bond duration and a past-date bound run (recession probability at 2025-06-30); the 2019 Taylor-rule task waits on #195/#196, as Step 9 recorded |
| Deployed and verified: the beta CLI and MCP server install; staging reports the phase's SHA; the edge runs a model, serves a hosted-safe series and refuses a library-only one | V13.2, V13.3, V15.2, V15.3 | Fresh PyPI installs and uvx Inspector; edge checks against main's deployed SHA |
| Security: image scan, SSRF, burst limits, Secret Manager only, OIDC without stored keys, loopback-only local bind | V7.2, V12.2, V13.3, V16.4, V16.8, static checks 22, 48, 64 | No fixable Critical or High; SSRF tests; both 429 layers; no repository secret; WIF by SHA |
| Operations: the staging health alarm and the budget notification | V13.4, V16.5 | Synthetic failure, issue #209, confirmed notification; budget notice pulled |

## Pre-ship items and owners

Nathan Ramos, CFA owns each open issue below. These are tracked limitations
with destinations, not waived verification criteria.

| Destination | Owned work / guard |
|---|---|
| #52/#62 | Security advisory CVE id and Scorecard dispositions |
| #68 | GitHub Sponsors listing; development continues |
| #109 | Mirror trufflehog's URI-credential detector in the local gate |
| #110/#184 | Yanked soupsieve 3.0 (one transitive pin, two issues) |
| #112/#137/#139/#143/#149/#152 | Dev-profile property failures; fix without weakening bounds |
| #113/#114/#116 | Proxy, Pyodide transport and SQLite; Phase 5 browser scope |
| #131/#135/#136/#141/#142 | Empty windows, NY Fed history, parser-aware cache key, BLS/CBO long history |
| #195/#196 | Gated live binds (CBO archive from 2024-02, EFFR Sunday); then the 2019 Taylor-rule agent task |
| #148/#150/#151 | Changelog dashes, Drive quota, mean-variance overflow; #194 is #150 recurring and closes on the next green run |
| #154/#182 | Wheel rule: `arch>=8.0 ; python_full_version < '3.15'` (econometrics, all) and `schemathesis>=4.32 ; python_full_version < '3.15'` (fuzz group, for PyYAML); remove after cp315 wheels and matrix verification |
| #155/#156/#158/#159 | MacKinnon/Johansen, BLS gap profile, pre-1952 daily sources |
| #163/#164 | Maintenance-page errors, local Yahoo harness |
| #174 | Cross-thread "always" filter window in `library_warnings` |
| #197 | MCP tool-list size; compact schemas or progressive discovery |
| #210/#211 | Staging rollback restore and deploy-account narrowing; before Phase 5 repeats the setup for production |
| #212 | actionlint in the gate |
| #213 | Phase 1 check 16 CRLF on Windows |
| Dependabot #101-#103, #185, #187-#189, #202, #203 | Ordinary maintenance after the freeze; #187 (TypeScript 7) stays unmerged while Step 7's 6.0.3 pin holds |
| Phase 5 | Website and docs, production deploy and hosted MCP endpoint, stable Read the Docs cutover |
| Phase 6 | Premium and BYOK providers, the Bloomberg adapter |
| Phase 7 | Next-wave catalog and synchronized scalar binding policy |
| Phase 8 | Hosted API keys, quotas, remote MCP with OAuth, hosted narrative |

No credential, token or billing account appears in this record.

## Final verification evidence

The canonical `./scripts/verify-phase04.sh --post` result, the Phase 3
`--post` it runs (with Phases 2 and 1), the CI checks and the required-check
update are recorded here once the run completes on the frozen branch.
