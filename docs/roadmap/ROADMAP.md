# pyeconomics 1.0 — Rebuild as an Open Economics & Finance Model Platform

> **Status:** Phases 1, 2, 3 and 4 Complete — Phase 4 shipped 2026-10-28 (`v1.0.0b1` on PyPI); Phase 5 in progress
> **Owner:** Nathan Ramos, CFA — founder and sole maintainer
> **Audience:** The maintainer and the AI coding agents that execute phase
> steps; public with the repository
> **Target environment:** Local-first — a PyPI library, CLI, local web app
> and MCP server on Windows, macOS and Linux; a hosted web app and API on
> Google Cloud Run behind Cloudflare from Phase 5
> **Last updated:** October 2026

pyeconomics 0.2.x was built in 2024 around one idea: compute the Taylor
rule and three related monetary-policy rules from live FRED data, print the
result, and have an LLM comment on it. It does that, but nothing has
shipped since 0.2.5 (May 2024), the test suite fails on its own pinned
dependencies, and the design — computation fused with data fetching,
printing, plotting and AI calls — cannot grow past a handful of models.

This roadmap rebuilds it as pyeconomics 1.0: a registry of tested, cited
models — every CFA Program formula family first, then the wider economics,
econometrics, risk and quant canon — written once and served identically
to Python, a command line, a REST API, a web app, AI assistants (MCP) and,
later, Excel. Free public data is the default; a user's own paid API keys
and a local Bloomberg Terminal are optional upgrades used on the user's own
machine. Every output carries a provenance manifest, so
it can be plugged into other models, pipelines and spreadsheets. A hosted
public site launches with 1.0.0 in Phase 5; paid features follow only when
evidence says people will pay for them.

Why now: the PyPI name is held, the 0.2.x code is two years stale, and 2026
tooling — uv, PyPI Trusted Publishing, the Model Context Protocol and AI
coding agents — makes a multi-surface platform maintainable by one person.
And the field has room (§1 "Where pyeconomics fits"): QuantEcon teaches
theory without data or finance, OpenBB moves data without models,
FinanceToolkit computes ticker ratios without fixed income or a curriculum
map, and no Python package implements monetary-policy rules at all. This
roadmap supersedes the 2024 wishlist in the README's "Roadmap" section and
`docs/roadmap*.rst`; their models carry into the Phase 7 catalog, and the
pages are retired in Phase 1.

---

## 1. Executive Summary

pyeconomics is a 0.2.x Python library: four monetary-policy rules over FRED
on PyPI, plus regression diagnostics, a Bitcoin stock-to-flow model and LLM
commentary on an unreleased branch. It is usable only from Python. It now
needs to become the reference open-source platform for economic and
financial models — broad (the CFA Program and well beyond), trustworthy
(every number tested against a cited source), reachable from every tool
quants, analysts and students use, and wired to real data — while
satisfying these constraints:

1. **Correct before broad.** No model merges without a model card, cited
   golden values and property tests. Trust is the product; breadth without
   it is a liability.
2. **One registry, every surface.** A model is written once. Its Python
   function, CLI command, API endpoint, web page, MCP tool and docs page are
   generated from it, and parity tests prove they agree.
3. **Data licences decide where data may flow.** Free sources are the
   default. The hosted service serves only sources whose terms allow it;
   yfinance, Bloomberg and bring-your-own-key data stay on the user's
   machine, save a per-request pass-through a vendor explicitly allows
   (Phase 8).
4. **One maintainer, near-zero fixed cost.** Every surface is operable by
   one person with AI coding agents, scales to zero when idle, and fits a
   hobby budget until revenue exists.
5. **Free core forever; charge only on evidence.** The library, CLI, local
   app and MCP server stay open source. Paid features are built only after
   the validation gates in §5 pass.

The path: **reset → engine → data → surfaces → launch → premium data ∥
catalog → monetize.** Phases 1–5 are strictly sequential and end with the
1.0.0 public launch; Phases 6 and 7 then run in parallel, and Phase 8
starts only when its evidence gate passes.

### Surfaces at a glance

| Surface                              | Serves                                 | Arrives         | Data it may use                         |
|--------------------------------------|----------------------------------------|-----------------|-----------------------------------------|
| Python library                       | Quants, researchers, students          | Phase 2         | Every source the user can access        |
| CLI (`pyeconomics …`)                | Scripts, pipelines, non-Python tools   | Phase 4         | Every source the user can access        |
| MCP server (stdio)                   | AI assistants and IDE agents           | Phase 4         | Every source the user can access        |
| REST API — local / hosted            | Apps, notebooks, other languages       | Phase 4 / 5     | Local: all · hosted: hosted-safe only   |
| Local web app (`pyeconomics serve`)  | Analysts, Bloomberg Terminal users     | Phase 5         | Every source the user can access        |
| Hosted web app                       | Everyone, nothing to install           | Phase 5         | Hosted-safe sources + in-browser uploads|
| Excel add-in, remote MCP, Pro plans  | Paying users                           | Phase 8 (gated) | Hosted-safe sources + uploads           |

### Where pyeconomics fits

| Neighbour | What it does well | What it leaves open | pyeconomics stance |
|---|---|---|---|
| QuantEcon (MIT library; CC BY-SA lectures) | Economic theory and teaching: dynamic programming, Markov chains, Kalman filters | No data connectors, no finance curriculum, no fixed income | Complement: link and cite, never adapt its text |
| OpenBB ODP v5 (Apache-2.0 since 2026-09-30; now stewarded by a non-profit) | Data plumbing across providers; one spec drives Python, CLI, REST and MCP | Few models: no bond or derivative pricing, no curriculum breadth; its Taylor rule passes through Atlanta Fed figures | Integrate: OpenBB as an optional meta-provider, pyeconomics as an OpenBB extension (Phase 6) |
| FinanceToolkit (MIT) | 500+ ratio, valuation, options and risk methods over tickers; a hosted MCP server | Tied to one data vendor and to tickers; basic fixed income; no policy rules, REST API, web calculators or curriculum map | Differentiate on breadth, verification and surfaces |
| Calculator sites (Omni, MetricGate) | Hundreds to thousands of single-formula web calculators | Not callable from code, not cited, not reproducible | Compete for search traffic with cited, callable, exportable pages |
| Fed tools (Atlanta Fed Taylor Rule Utility, Cleveland Fed simple rules) | Authoritative policy-rule prescriptions | Fixed menus and spreadsheets; no API | Reproduce their outputs in tests; go further with vintages and custom rules |
| FinancePy (GPL-3.0), rateslib (non-commercial) | Derivatives and rates pricing | Licences incompatible with a permissive core and a hosted service | Never depend on them; QuantLib serves as test oracle and optional engine |

Two similarly named projects — `davidrpugh/pyeconomics` (2013–14 course
code, dormant, no licence) and pyecon.org (a teaching site) — share only
the name; the README and ADR-0009 state the distinction.

---

## 2. Current State Assessment

Assessed on 2026-10-03 against `main` (0.2.5, last commit May 2024), `dev`
(0.2.6; 34 commits ahead of `main`, never released) and the uncommitted
working tree. Tests were run from a clean export of `dev` in a fresh Python
3.12 environment with the repository's own pins.

### What works today

- **Released in 0.2.5:** Taylor (1993, with an Okun factor),
  balanced-approach, balanced-approach with shortfalls and first-difference
  rules plus a combined rule table — each current and historical, with
  effective-lower-bound and inertia adjustments, over FRED series; a FRED
  client with key lookup from an argument, the environment or the OS
  keyring; a six-hour on-disk cache. PyPI holds seven releases (0.1.0 to
  0.2.5, all May 2024); traffic is about 25–30 organic downloads a month and
  the repository has 11 stars.
- **Unreleased on `dev`:** regression-diagnostic wrappers over statsmodels
  (Breusch-Pagan, Durbin-Watson, normality tests, Ramsey RESET, VIF,
  residual plots, a verbose summary); a Bitcoin stock-to-flow regression
  over Coin Metrics community data; LLM commentary on rule outputs and plot
  images through the OpenAI API.
- **Docs and examples:** a Sphinx site on Read the Docs, six example
  notebooks, and a Docker image that opens them in JupyterLab.
- **CI:** pytest on Python 3.10–3.12, a Sphinx build, and a tag-triggered
  PyPI release; tags `v0.2.0`–`v0.2.5`.
- **Tests:** 122, nearly all hermetic (FRED and the keyring are mocked).
- **History is clean:** `.env` (holding FRED and OpenAI keys) is
  git-ignored, was never committed, and no key-shaped string appears in
  any commit on any branch.

Present but on no branch:

- **Uncommitted work on `dev`:** Bloomberg consensus-forecast tickers
  (`ECCCUS` / `ECUPUS`) for a forward-looking Taylor rule, a migration to
  the OpenAI v1 client, and a `tia` (Bloomberg toolkit) git dependency.
- **44 local-only files** in the git-ignored `dev/` folder: prototypes for
  quantity-of-money and DCF models, Bitcoin factor work, and about a dozen
  stock-to-flow variants (OLS, WLS, GLS, RLM, GAM, ARIMA, random forest).
  No other copy exists.

### Gaps blocking pyeconomics 1.0

| #  | Gap                                                                                                                                                                                         | Severity |
|----|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| 1  | `FredClient` writes the FRED API key to the log at DEBUG level — in the published 0.2.5 as well as on `dev`                                                                                 | Critical |
| 2  | The suite is red on its own pins: 22 failed, 2 errors, 98 passed; coverage 77.7% against its own 80% floor                                                                                  | Critical |
| 3  | No lockfile: transitive drift breaks the AI module (`openai` 1.30 with `httpx` 0.28 raises a `proxies` TypeError)                                                                           | High     |
| 4  | The cache is `pickle`, written to a directory computed three levels above the package (outside `site-packages` once installed), created at import time, and holding FRED content that FRED's terms forbid caching | High |
| 5  | Release pipeline: a long-lived PyPI token, `gh-action-pypi-publish` v1.4.2, `setup.py sdist`, a three-way matrix publish, and a version written to a file `setup.py` never reads — so a tag and its package version can disagree | High |
| 6  | Computation fused with I/O, printing, plotting and AI calls; mutable default arguments that are then mutated, so values leak across calls; outputs rounded to 2 dp; plots saved outside the package | High |
| 7  | Historical rule estimates use today's revised data — look-ahead bias; no vintage (real-time) data support                                                                                   | High     |
| 8  | Runtime dependencies include dev tools (pytest, sphinx, jupyterlab, setuptools); the working tree adds a git URL dependency that PyPI rejects                                                | High     |
| 9  | No security gate: no secret scan, SAST or dependency audit, locally or in CI; actions pinned by tag; no `permissions:` blocks                                                                | High     |
| 10 | One API source (FRED) plus one CSV; no provider abstraction, licence metadata, credential policy or log redaction                                                                           | High     |
| 11 | No CLI, REST API, web app or MCP server; outputs are Python objects, console prints and PNG files                                                                                           | High     |
| 12 | About 10 models, against a 2024 wishlist of ~55 and a CFA-and-beyond ambition in the hundreds                                                                                               | High     |
| 13 | `setup.py` plus a stub `pyproject.toml`; the published package excludes Python 3.13 and 3.14, while CI still tests 3.10, which reached end of life on 2026-10-01                          | Medium   |
| 14 | Branch sprawl: `main` idle since May 2024; `dev` and `legacy-dev-0.2.6` unreleased; 25 open automated PRs (24 Snyk, 1 Dependabot) with their branches                                      | Medium   |
| 15 | Bitcoin stock-to-flow is empirically contested, and Coin Metrics community data is CC BY-NC 4.0 — no commercial use                                                                         | Medium   |
| 16 | The AI layer is OpenAI-only, with a hard-coded `gpt-4o` default and no cost cap, and it sends FRED-derived content to an LLM although FRED's terms restrict ML use (a counsel question) | Medium |
| 17 | Docs are a wishlist plus usage pages; no generated API reference; several README badges point at services that need re-verifying                                                            | Medium   |
| 18 | 44 research files exist only in one ignored local folder                                                                                                                                    | Medium   |
| 19 | Mixed line endings (CRLF warnings), non-conventional commit history, `CITATION.cff` still at 0.2.0, no `SECURITY.md`                                                                        | Low      |

These gaps drive the phase ordering below. Phase 1 closes gaps 1–5, 8, 9,
13, 14, 18 and 19 by patching 0.2.x, archiving it and starting clean;
Phase 2 closes gap 6; Phase 3 closes gaps 7, 10 and 15; Phases 4 and 5
close gaps 11, 16 and 17; Phases 2, 3 and 7 close gap 12.

---

## 3. Target Architecture

```
┌─ USER'S MACHINE — runs under the user's own credentials and licences ──┐
│  Python API · CLI · local web app (`pyeconomics serve`) · MCP (stdio)  │
│            └──────────────────────┬─────────────────────┘              │
│                                   ▼                                    │
│        core: model registry · conventions · results · manifests        │
│                                   │ live inputs                        │
│                                   ▼                                    │
│        data layer: providers · credentials (OS keyring) · cache        │
│      │              │              │              │              │     │
│      ▼              ▼              ▼              ▼              ▼     │
│  free public    yfinance       BYOK paid     Bloomberg DAPI   user's   │
│  APIs (FRED…)   (local only)   APIs (keys)   (Terminal only)  files    │
└────────────────────────────────────────────────────────────────────────┘
┌─ HOSTED (Phase 5+) — only hosted-safe data crosses into this box ──────┐
│  browser ──HTTPS──▶ Cloudflare: DNS · TLS · CDN · WAF · rate limits    │
│                       │ static, prerendered model pages                │
│                       │ /api · /mcp                                    │
│                       ▼                                                │
│  Cloud Run: FastAPI service — the same pyeconomics wheel, hosted mode  │
│        │ reads                                  │ Phase 8 only         │
│        ▼                                        ▼                      │
│  object storage: scheduled snapshots     Postgres · auth · billing     │
│  of originators (BLS, BEA, Treasury…)    (merchant of record)          │
└────────────────────────────────────────────────────────────────────────┘
```

Everything a user installs runs on the user's machine, under the user's own
credentials and data licences. The hosted service is the same wheel started
in hosted mode, which refuses any source not classed hosted-safe (see §5
"Data licensing policy"). The only public ingress is Cloudflare in front of
one Cloud Run service and a static site. There is no database until Phase
8, and the hosted data plane reads scheduled snapshots of the data's
originators — BLS, BEA, Census, Treasury, the Fed Board, the NY Fed, SEC,
the World Bank, OECD, ECB, BIS and Eurostat — instead of calling providers
per request. It never serves FRED: FRED's terms forbid caching and
redistributing its content, so FRED is a library-only convenience that
reaches the same public series through the user's own key.

Inside the repository, one registry feeds every surface:

```
src/pyeconomics/
  core/      model spec · registry · units & conventions · results · manifests
  models/    one subpackage per domain (Phase 7 lists the domains)
  data/      provider SDK · providers/ · credentials · cache · catalog · licences
  cli/       command line generated from the registry
  server/    FastAPI app factory — local and hosted modes        [server] extra
  mcp/       MCP server generated from the registry              [mcp] extra
web/         Astro + React (TypeScript) site shared by local and hosted modes
docs/        documentation site; docs/adr/ decisions; docs/roadmap/ this file
tests/       unit · golden · property · contract · parity · e2e
```

A model is a pure function with typed inputs and outputs plus metadata; it
never fetches data, prints, plots or calls an LLM. Live data reaches it
through a declared binding that the data layer resolves, and every result
carries a manifest: model id and version, package version, inputs, data
sources with vintages and retrieval times, and a hash.

---

## 4. Phased Roadmap

### Phase 1 — Reset & Foundation ✅

**Status:** Complete — 2026-10-08; PR #70; v1.0.0.dev1; phase01-roadmap.md

**Goal:** Patch and preserve 0.2.x, then stand up a clean, secure,
production-grade skeleton — packaging, toolchain, security gate, CI/CD and
the architecture decisions every later phase builds on.

**Complexity:** Medium · **Risk:** Low · **Cloud cost:** $0 ·
**Handles sensitive data:** Yes — FRED and OpenAI keys in a local `.env`;
PyPI publishing credentials

**Phase roadmap settings** — the session that writes
`phase01-roadmap.md` (`/roadmap-phase 1`):

| Setting      | Value                                    |
|--------------|------------------------------------------|
| Model        | Claude Opus 5.5                          |
| Backup       | GPT-6 Astra — Codex · Intelligence Max   |
| Platform     | Claude Code                              |
| Effort       | Max                                      |
| Thinking     | On                                       |
| Conversation | **New**                                  |

This roadmap must preserve every byte of 0.2.x before anything is deleted,
ship the security patch to existing users first, and settle the decisions
later phases cannot cheaply reverse (layout, licence, versioning, web
stack, data-licence model). Opus 5.5 leads `roadmodel score --category
planning --complexity high --budget best`; Max is the operator's standing
rung for roadmap sessions (user-context, 2026-10-01), a raise over Opus
5.5's Medium default, paid by the claude.ai Max subscription, with GPT-6
Astra on the ChatGPT Pro 5x pool as the cross-provider backup.

#### 1.1 Patch, then archive, 0.2.x

- Replace the old `release.yml` before pushing any tag: it publishes on
  every `v*` tag with a long-lived token. Archive tags use an `archive/`
  prefix so they can never trigger a release.
- Cut `legacy/0.2.x` from `v0.2.5`, remove every log statement that prints
  a credential, replace that branch's token-based release workflow with the
  hardened Trusted Publishing one (1.5), and publish 0.2.6 — a number PyPI
  never received. The release also restarts the no-release clock in PEP
  541's test for abandoned names, which 0.2.x currently meets.
- Publish a GitHub security advisory: affected versions 0.2.0–0.2.5 (0.1.0
  never logged the key; the 0.2.6 readiness gate read every sdist), the fixed
  version, and the advice to rotate a FRED key if DEBUG logs were stored or
  shared. Declare 0.2.x end-of-life at the 1.0.0 release.
- Commit the uncommitted working tree (Bloomberg forecast tickers, OpenAI
  v1 client, `tia` dependency) to `archive/0.2-dev-wip`; tag the heads of
  `dev` and `legacy-dev-0.2.6` as `archive/dev-2024-10` and
  `archive/legacy-dev-0.2.6`. Nothing archived merges to `main`.
- Record characterization fixtures: run the four 0.2.x rules on a
  deterministic grid of explicit inputs (no network) and store
  input-to-output pairs under `tests/fixtures/legacy/`. Phase 3's port must
  match them or document each intentional difference.
- Inventory the 44 files in `dev/`, secret-scan them (notebook outputs
  included — some may hold licensed Bloomberg output), and move the
  keepers to a private archive repository with an index of which
  prototypes feed Phase 7. Nothing from `dev/` enters the public repo
  unreviewed.
- Close the 25 open automated PRs (24 Snyk, 1 Dependabot) as superseded
  and delete their branches after confirming each holds only dependency
  bumps; then delete `dev` and `legacy-dev-0.2.6` (their heads live on as
  archive tags).

#### 1.2 Repository reset & package skeleton

- Remove from `main` the 0.2.x package with its examples, media and
  Sphinx pages, plus `setup.py`, `requirements.txt`, the root
  `__version__.py`, `pytest.ini`, the JupyterLab `Dockerfile` and
  `start.sh`, `generate_tests.py`, `render_readme.py` and
  `test_import.py` — all preserved by the archive tags; move
  `markdown/*.md` to the root.
- Create the §3 layout: `src/pyeconomics/`, `tests/`, `docs/`, and a
  `web/` placeholder until Phase 5.
- One `pyproject.toml` (PEP 621): metadata, classifiers,
  `requires-python` per ADR-0010, a minimal runtime dependency set,
  PEP 735 dependency groups for dev, test and docs, an extras skeleton, and
  the `uv_build` backend (the core stays pure Python, so it also runs in
  Pyodide and xlwings Lite). Commit `uv.lock` and export a PEP 751
  `pylock.toml` for tool-agnostic installs and audits.
- One version source: a static version in `pyproject.toml`, bumped with
  `uv version`, exposed as `pyeconomics.__version__` through
  `importlib.metadata`; the release workflow refuses any tag that does not
  equal it, so the 0.2.x tag/version mismatch cannot recur.
- `.gitattributes` normalising text to LF, `.editorconfig`, and a
  refreshed `.gitignore` (adds `.worktrees/`, keeps `planning/`).

#### 1.3 Quality toolchain

- ruff for lint and format with a strict rule set (including the bandit,
  NumPy and pandas rule families).
- mypy in strict mode with the pydantic plugin as the CI gate, pyright in
  the editor, and Astral's ty as a non-blocking check until it reaches 1.0.
- pytest with hypothesis, syrupy snapshots, pytest-benchmark, branch
  coverage and `pytest-socket` (unit tests may not touch the network);
  doctests run on every public docstring.
- prek (a drop-in, faster runner for pre-commit configurations) for format,
  lint, types and the security gate (1.4), so every check runs the same
  way on Windows, macOS and Linux.
- Conventional Commits enforced on pull-request titles, which become the
  squash-merge messages.

#### 1.4 Per-step security gate

- Pre-commit, fail-closed: gitleaks (secrets), bandit plus semgrep (SAST,
  with project rules that forbid `pickle`, `eval`, `yaml.load`, and
  logging any variable named like a key, token or secret), `pip-audit
  --locked` (known vulnerabilities) plus a licence allowlist check (§5
  "Legal & brand guardrails"), and the sensitive-data checklist in the PR
  template.
- The same four checks run in CI as required status checks, plus
  trufflehog, CodeQL, zizmor (workflow security), step-security
  harden-runner, OpenSSF Scorecard and the dependency-review action on
  pull requests.
- GitHub settings: secret scanning with push protection, Dependabot alerts
  and security updates (uv and github-actions ecosystems), private
  vulnerability reporting; 2FA confirmed on the GitHub and PyPI accounts.

#### 1.5 CI/CD and publishing

- `ci.yml`: lint, types and tests on Ubuntu, Windows and macOS across every
  supported Python; coverage report.
- `release.yml`: build once with `uv build`, check the artifacts, and
  publish with PyPI Trusted Publishing (OIDC) through
  `pypa/gh-action-pypi-publish`, which generates PEP 740 attestations:
  TestPyPI for `.devN` rehearsals, PyPI behind a protected `pypi`
  environment that requires the maintainer's approval; tags from `main`
  only.
- Every action pinned to a commit SHA, enforced by GitHub's SHA-pinning
  policy; `permissions: {}` at workflow level and the minimum per job;
  `id-token: write` only on the publish job; `persist-credentials: false`
  on checkout; no `pull_request_target`; concurrency groups.
- Delete the old workflows; revoke the `PYPI_API_TOKEN` and delete the
  secret; remove the Codecov token if the replacement does not need it.
- Rehearse: tag `v1.0.0.dev1` and publish to TestPyPI only.

#### 1.6 Architecture decision records

Each ADR lands in `docs/adr/` with a recommended default; the maintainer
accepts or amends it before Phase 2 starts.

| ADR  | Decision                  | Recommended default                                                                                     |
|------|---------------------------|---------------------------------------------------------------------------------------------------------|
| 0001 | Product boundaries        | §6 Out of Scope. pyeconomics is the model layer: it complements OpenBB (data plumbing) and QuantEcon (theory teaching) rather than competing with them, and it may become a dependency of the maintainer's separate portfolio system, never the reverse |
| 0002 | Distributions & extras    | One `pyeconomics` distribution with extras (`server`, `mcp`, `ai`, `econometrics`, `plot`, one per provider, `all`); the built web app ships as a separate `pyeconomics-app` wheel behind the `[app]` extra; `blpapi` is not on PyPI, so `[bloomberg]` installs only the pure-Python side and the docs give Bloomberg's own install command |
| 0003 | Versioning & deprecation  | PEP 440 + SemVer: 0.x was initial development, and 1.0.0 — at the Phase 5 launch — is the first stable public API, after which any breaking change needs 2.0.0; one 1.0.0 pre-release per phase; model ids permanent; removals follow one minor release of warnings; 0.2.x end-of-life at 1.0.0 |
| 0004 | Licence & contributions   | Apache-2.0 for the public repository from 1.0 (an express patent grant; 0.2.x stays MIT, since relicensing is not retroactive, and the sole human author can relicense); hosted-only paid features (Phase 8) in a separate private repository; no AGPL or dual licensing; DCO sign-off on every commit, plus a CLA before any outside contribution only if contributed code might ever be relicensed; a permissive-only runtime dependency allowlist |
| 0005 | Data-licence model        | The five source classes and their enforcement in §5 "Data licensing policy"                             |
| 0006 | Web stack & hosting       | Astro (static output) with React islands, Tailwind and shadcn/ui; the static site on Cloudflare; FastAPI on Cloud Run (the maintainer's existing platform; Fly.io is the runner-up); Next.js only if a logged-in app ever becomes the main experience |
| 0007 | Documentation tooling     | Sphinx with MyST-NB, sphinx-autoapi and sphinx-gallery on Read the Docs; Sybil for Markdown doctests; revisit Zensical when it reaches 1.0 (Material for MkDocs is in maintenance mode) |
| 0009 | Name, domains & trademark | Register pyeconomics.com, .org, .io and .dev now — all appeared unregistered on 2026-10-03 — before any announcement. Commission a clearance search before filing: "PYECONOMICS" risks a merely-descriptive refusal, so a coined brand for the hosted product stays an option; a USPTO intent-to-use filing in classes 9 and 42 costs about $1,000 in government fees plus attorney fees (TBD). Move the repository to a neutral GitHub organization, `pyeconomics-dev` (`pyeconomics` belongs to a dormant account; ADR-0009), because the personal handle contains the CFA mark |
| 0010 | Python support policy     | `requires-python >=3.12` (NumPy 2.5 and SciPy 1.18 already require it); CI on 3.12, 3.13 and 3.14, plus 3.15 once final (due 2026-10-09); raise the floor with NumPy and SciPy, following SPEC 0 |

ADR-0008 (numerical conventions) is written in Phase 2, where it is first
needed.

#### 1.7 Governance, community & agent instructions

- Root files: README (1.0 status banner, a pointer to 0.2.x, and a note
  distinguishing this project from similarly named ones), CONTRIBUTING
  (DCO, the model definition of done from §5), CODE_OF_CONDUCT,
  SECURITY.md, CHANGELOG (Keep a Changelog), CITATION.cff, CODEOWNERS.
- Issue forms: bug; model request (a citation is required); data-source
  request (a terms-of-use URL is required). PR template: roadmap step,
  test plan, rollback plan, security checklist, licence check. Labels for
  the defect classes in §5.
- `CLAUDE.md` and `AGENTS.md` carrying the rules every coding-agent
  session follows: layout, registry rules, units, testing, the security
  gate and the step lifecycle.
- Funding hooks for Gate G1: GitHub Sponsors, thanks.dev and a
  `funding.json`. (Amended 2026-10-08 by the maintainer: Phase 1 closes
  with thanks.dev live; the GitHub Sponsors listing, blocked by a
  wrongly linked Stripe account, moves to 8.1 under issue #68.) The ® after the maintainer's name goes from `LICENSE`
  and the git author name — CFA Institute's rules put no ® after a name.
- Retire `docs/roadmap*.rst`, `docs/create_roadmap_files.bat` and the
  README "Roadmap" section in favour of this file; keep the Read the Docs
  project serving 0.2.x until Phase 5 replaces it.

**Acceptance criteria**
- The 0.2.x security patch is on PyPI without any credential logging, and
  a published GitHub security advisory names affected and fixed versions
  and the key-rotation advice.
- The archive tags and `archive/0.2-dev-wip` exist on `origin`, the WIP
  diff is intact, and the `dev/` research sits in a private archive with a
  clean secret scan and an index.
- Characterization fixtures for the four 0.2.x rules are committed.
- `uv sync --locked` and the full test run pass in CI on Ubuntu, Windows
  and macOS for every supported Python; `uv build` produces a wheel and an
  sdist that pass metadata checks.
- **Deployed & verified:** `v1.0.0.dev1` reached TestPyPI through Trusted
  Publishing with attestations, installs in a clean venv and reports its
  version, and 0.2.6 installs from PyPI; no PyPI API token exists in the
  repository or the PyPI account.
- A direct push to `main` is rejected (verified); `git branch -r` lists
  only `origin/main`, `legacy/0.2.x` and archive branches; ADRs 0001–0007,
  0009 and 0010 are merged as Accepted.
- **Security:** the pre-commit gate blocks a planted fake credential and a
  `pickle.loads` call in a throwaway commit; the same checks are required
  status checks on `main`; zizmor reports nothing above Low; CodeQL and
  Scorecard run on `main`; secret scanning with push protection and
  private vulnerability reporting are on.

---

### Phase 2 — Model Engine & Core Catalog ✅

**Status:** Complete — 2026-10-14; PR #97; v1.0.0a1; phase02-roadmap.md

**Goal:** Build the model registry and its contracts, and prove them end to
end with the data-free half of the 50-entry launch catalog — mostly CFA
Level I and II staples — in the Python API, released as `1.0.0a1`.

**Complexity:** High · **Risk:** Medium · **Cloud cost:** $0 ·
**Handles sensitive data:** No

**Phase roadmap settings** — the session that writes
`phase02-roadmap.md` (`/roadmap-phase 2`):

| Setting      | Value                                    |
|--------------|------------------------------------------|
| Model        | Claude Opus 5.5                          |
| Backup       | GPT-6 Astra — Codex · Intelligence Max   |
| Platform     | Claude Code                              |
| Effort       | Max                                      |
| Thinking     | On                                       |
| Conversation | **New**                                  |

This roadmap fixes the model contract that hundreds of later models and
every surface depend on, so a design flaw here compounds for years. Same
pick, rung and funding as Phase 1: Opus 5.5 at Max on the claude.ai Max
subscription, GPT-6 Astra on ChatGPT Pro 5x as backup.

#### 2.1 Conventions & core types (ADR-0008)

- Rates, returns and yields are decimals in every API (`0.05` is 5%).
  Percent exists only for display and at the data boundary, where sources
  such as FRED publish percent and the data layer converts.
- Every numeric field declares a unit (rate, money with currency, years,
  count, ratio, index level), bounds, and a frequency where one applies.
- Compounding (simple, periodic, continuous) and day-count conventions
  (30/360 US, 30E/360, ACT/360, ACT/365F, ACT/ACT ISDA, ACT/ACT ICMA) are
  typed enums; business-day calendars come from a maintained library.
- A numerical tolerance policy (absolute and relative, per output) and
  deterministic randomness: every stochastic model takes a seed, and the
  manifest records it.
- Scalars and arrays both work; tabular inputs accept pandas, Polars or
  Arrow through the Arrow PyCapsule interface (zero-copy), and outputs
  default to pandas with Polars and Arrow conversions.
- pandas 3 semantics throughout: Copy-on-Write, the default string dtype,
  `ME`/`QE`/`YE` offset aliases and explicit datetime resolution.

#### 2.2 Model specification & registry

- A `ModelSpec` carries: a permanent dotted id; a version; title, summary,
  domain and tags; references (DOI or URL plus page or table);
  assumptions; limitations; an evidence status (§5); typed inputs and
  outputs (pydantic) with units, bounds, defaults and examples; a pure
  `compute`; and optional data bindings (Phase 3) and chart specs.
- Syllabus mappings — CFA Program, FRM, CAIA, CIPM — live outside the
  spec, in versioned crosswalk data (7.1), at topic level and never in
  learning-outcome wording, so a curriculum change never touches model
  code.
- Models register through a `pyeconomics.models` entry-point group, so a
  third-party package can add models without forking. Renamed ids keep an
  alias; deprecations follow ADR-0003; `pyeconomics.registry.validate()`
  rejects any incomplete spec, and CI runs it.

An illustrative shape (the Phase 2 roadmap fixes the real API):

```python
@model(
    id="fixed_income.duration.macaulay",
    title="Macaulay duration",
    tags=["bonds", "interest-rate risk"],
    references=[Ref("Macaulay (1938), NBER")],
    evidence=Evidence.STANDARD,
)
def macaulay_duration(inputs: BondCashFlows) -> DurationResult:
    # pure: no I/O, no printing, no plotting
    ...
```

#### 2.3 Results & provenance

- A `Result` holds inputs, outputs, warnings and a manifest, and
  serializes to a dict, canonical JSON (stable key order and float
  formatting — the cross-surface parity tests compare these bytes),
  pandas, Polars, Arrow and Parquet. `.card()` returns the model card;
  plotting sits behind a `[plot]` extra built on Plotly, whose figure JSON
  renders unchanged in notebooks, the docs, the web app (Plotly.js) and
  MCP Apps.
- Every input and output model exports JSON Schema (2020-12). Phases 4 and
  5 generate CLI options, API schemas, MCP tool schemas and web forms from
  it.

#### 2.4 Verification harness

- Golden cases live in versioned fixture files. Each cites its source and
  carries its tolerance. Preferred sources are certified or official:
  NIST StRD certified regression values; the NY Fed recession-probit
  spreadsheet; the Fed Board's Gürkaynak-Sack-Wright and the ECB's
  published Svensson curve parameters; ISDA's CDS Standard Model test
  grids; the Atlanta Fed Taylor Rule Utility and the Cleveland Fed's
  simple-rule outputs; textbook values recomputed independently. CFA
  curriculum examples are never used.
- Property tests (hypothesis) for every invariant a domain guarantees: a
  bond's price falls as its yield rises; a zero-coupon bond's Macaulay
  duration equals its maturity; BSM prices satisfy put-call parity; NPV is
  linear in cash flows.
- Cross-library oracles as test-only dependencies: QuantLib (BSD-style)
  for bond and derivative math, vollib (MIT) for implied volatility,
  statsmodels, linearmodels and arch for estimators, empyrical-reloaded and
  quantstats for performance statistics.
- Edge-case suites: zero and negative rates, very long maturities, extreme
  volatilities, degenerate inputs.

#### 2.5 Model cards & reference docs

- One docs page per model, generated from its spec: formula (LaTeX),
  variables with units, assumptions, limitations, evidence status, a
  worked example, references, curriculum mapping and a changelog.
- The docs site skeleton per ADR-0007, deployed as a preview; Read the
  Docs keeps serving 0.2.x until Phase 5.

#### 2.6 Launch catalog, part one — data-free entries

Each entry is a family of closely related formulas exposed as one model.
These 32 need no data connector; Phase 3 adds the 18 live-data entries
that complete the 50-entry launch catalog. The Phase 2 roadmap fixes the
final list.

| Domain          | Entries                                                                                                 |
|-----------------|---------------------------------------------------------------------------------------------------------|
| `foundations`   | TVM engine (PV/FV, annuities, NPV/IRR/XIRR, amortization); return toolkit (holding-period, arithmetic/geometric/harmonic, annualized, log, real); risk statistics (volatility, semideviation, skew, kurtosis, maximum drawdown); tests and confidence intervals (t, z, χ², F); GBM Monte Carlo and bootstrap |
| `econometrics`  | OLS with HC/HAC standard errors and diagnostics (wraps statsmodels; carries the 0.2.x diagnostics forward) |
| `fixed_income`  | Bond price and yield (full/flat price, accrued interest, day counts, YTM/YTC/YTW); money-market yields; spot/par/forward bootstrapping; duration family (Macaulay, modified, effective, key-rate, DV01); convexity and price-change approximation; credit-spread toolkit (expected loss, spread ↔ hazard rate, spread return) |
| `derivatives`   | Cost of carry and covered-interest-parity FX forwards; swap valuation and par swap rate; BSM/Merton with Greeks and implied volatility; CRR binomial (European and American) with put-call parity; Black-76 and Garman-Kohlhagen |
| `equity`        | DDM family (Gordon, two-stage, H-model, PVGO); FCFF/FCFE DCF                                            |
| `corporate`     | Cost of capital (CAPM, WACC, Hamada, country risk premium); capital budgeting (NPV, IRR, MIRR, payback, PI, EAA); DOL/DFL/DTL and breakeven |
| `accounting`    | Ratio suite and DuPont (3- and 5-step); Altman Z, Beneish M, Piotroski F                                |
| `portfolio`     | Portfolio math, efficient frontier and tangency portfolio; mean-variance utility and Kelly              |
| `performance`   | TWR vs MWR and Modified Dietz; Sharpe, Sortino, Treynor, Jensen, information ratio and tracking error, M², Calmar, capture ratios; Brinson attribution (BHB and Brinson-Fachler, with linking) |
| `risk`          | VaR and ES (parametric, Cornish-Fisher, historical, Monte Carlo, EWMA); Kupiec, Christoffersen and Basel traffic-light backtests |
| `international` | Parity conditions and real exchange rates (covered and uncovered interest parity, PPP, international Fisher) |

#### 2.7 Release `1.0.0a1`

- Tag `v1.0.0a1`; publish to PyPI as a pre-release (plain
  `pip install pyeconomics` keeps resolving 0.2.x); release notes; docs
  preview link.

**Acceptance criteria**
- Every entry in 2.6 (as the Phase 2 roadmap finalizes it) is registered
  and `registry.validate()` passes in CI; each has a card, at least three
  cited golden cases (fewer only with a recorded reason, such as a
  closed-form identity) and a property test for each documented
  invariant.
- Every input and output model exports JSON Schema that validates against
  the 2020-12 meta-schema; canonical-JSON round trips are lossless.
- Strict type checking passes on `core/`; branch coverage is at least 95%
  on `core/` and 90% on `models/`.
- **Deployed & verified:** `pip install --pre pyeconomics==1.0.0a1` in a
  clean venv runs a smoke script that executes one model per domain;
  plain `pip install pyeconomics` still resolves 0.2.x.
- **Security:** the gate is green on every commit; unit tests run with
  sockets disabled, proving no model touches the network; every input
  declares bounds, so no model accepts an unbounded size (Phase 4's
  request limits build on this); the lockfile audit is clean.

---

### Phase 3 — Data Platform & Free Sources ✅

**Status:** Complete — 2026-10-22; PR #170; v1.0.0a2; phase03-roadmap.md

**Goal:** Build a licence-aware data layer — providers, credentials, cache,
vintages and a semantic catalog — over the free sources, then complete the
launch catalog with its 18 live-data entries, led by a vintage-aware
monetary-policy suite, released as `1.0.0a2`.

**External approvals (maintainer, 2026-10-17):** Pending GitHub Sponsors
approval (issue #68; resubmitted 2026-10-12) does not gate engineering or
releases. SEC access is a separate external blocker in Phase 3 Step 7.
Step 10 must recover Treasury, Fed Board, NY Fed and OpenFIGI with their full
original verification; Steps 10–20 then proceed without waiting for Step 7.
Phase 3 may release with the exact 30 non-SEC providers and complete while
Step 7 remains explicitly unfinished, carrying SEC access and its provider
verification to a follow-up. If verified before the release candidate is
frozen, SEC makes 31. Readiness, release notes, ledgers and QA must disclose
the exact set and deferral; no shipped provider's checks are waived. Phase 4
may start and expose verified sources without SEC or Sponsors approval. The
phase roadmap's external-approval exception defines the handoff and checks.

**Complexity:** High · **Risk:** Medium · **Cloud cost:** $0 ·
**Handles sensitive data:** Yes — users' provider API keys (FRED, BLS,
BEA and other free-but-keyed sources)

**Phase roadmap settings** — the session that writes
`phase03-roadmap.md` (`/roadmap-phase 3`):

| Setting      | Value                                    |
|--------------|------------------------------------------|
| Model        | Claude Opus 5.5                          |
| Backup       | GPT-6 Astra — Codex · Intelligence Max   |
| Platform     | Claude Code                              |
| Effort       | Max                                      |
| Thinking     | On                                       |
| Conversation | **New**                                  |

This roadmap must make a source's licence class a first-class, enforced
property and rebuild the 0.2.x rules on real-time vintages — the clearest
white space the project has. Same pick, rung and funding as Phase 1: Opus
5.5 at Max on the claude.ai Max subscription, GPT-6 Astra on ChatGPT Pro
5x as backup.

#### 3.1 Provider contract & data model

- `Series` and `Table` results carry metadata: units, frequency, seasonal
  adjustment, source, licence class, attribution text, retrieval time and
  vintage (real-time period).
- Each provider also declares an `llm_use` flag — allowed, forbidden or
  unclear — read from its terms (FRED bars use in ML or LLM development
  and training). The flag travels with every frame and gates the AI
  narrative and the MCP server (Phase 4).
- A provider implements a typed fetch pipeline — transform the query,
  extract, transform the data into standard models, the pattern OpenBB's
  platform proved — plus `search`, `describe`, `vintages` and declared
  capabilities, with retries and backoff inside each provider's published
  rate limits.
- Providers register through a `pyeconomics.providers` entry-point group,
  so a third party can add one without forking.
- A design spike checks the contract against a mocked Bloomberg Desktop
  API session, so Phase 6 adds Bloomberg without changing the contract.

#### 3.2 Credentials, configuration & redaction

- Key lookup order: explicit argument → environment variable → a `.env`
  file in the user's config directory (never overriding a real environment
  variable) → OS keyring. A layered `pyeconomics.toml` holds settings and
  never secrets. Keys are held in memory as a secret type, and upstream
  URLs are redacted before logging, since FRED carries its key in the
  query string.
- A redaction filter on every logger; tests fail if a key appears in a log
  line, an exception, a manifest, a cache file or an export.
- No `pickle`, no `eval`, anywhere — enforced by a semgrep rule.

#### 3.3 Cache & offline mode

- A SQLite store (the standard library's `sqlite3`) in the user's cache
  directory, with user-only permissions and payloads as canonical JSON,
  keyed by provider, dataset, series, credential-free parameters and
  vintage; a time-to-live per provider; an offline mode that serves the
  cache with as-of dates; a Python cache API that Phase 4's `pyeconomics
  cache` commands wrap (ADR-0011 decision 14). Parquet stays the export and
  hosted-snapshot format of Phases 4 and 5.
- Licence-aware: a source whose terms forbid storage is fetched live and
  never written to disk, with no opt-in (ADR-0005 rule 4). FRED's terms
  forbid caching its content, so FRED and ALFRED are never written to
  disk; an in-process memo that ends with the process is not storage.
  (0.2.x cached FRED silently, in a pickle file.)

#### 3.4 Free providers

Classified from each provider's own terms on 2026-10-03; counsel confirms
the classes before Phase 5 (§5 "Data licensing policy").

| Source                                   | Data                                                         | Class                                   | Notes                                                                                     |
|------------------------------------------|--------------------------------------------------------------|-----------------------------------------|-------------------------------------------------------------------------------------------|
| BLS API v2                               | CPI, employment, JOLTS, PPI, ECI                             | hosted-safe                             | Free key, renewed yearly; 500 queries a day; BLS notice plus access date                  |
| BEA API                                  | NIPA (GDP, PCE prices), regional, international accounts     | hosted-safe                             | Free UserID; 100 requests a minute; BEA notice                                            |
| Census API                               | ACS, economic indicators, trade                              | hosted-safe                             | A key is now required on every query; Census notice                                       |
| US Treasury                              | Daily par nominal and real yield curves; FiscalData (debt, statements, average rates) | hosted-safe              | No key; US government works                                                               |
| Federal Reserve Board                    | H.15 rates, FOMC SEP projections, Gürkaynak-Sack-Wright curve parameters | hosted-safe                 | Public domain unless marked third-party                                                    |
| NY Fed                                   | Markets API (SOFR, EFFR, OBFR, repo, SOMA); ACM term premia; HLW r*; Staff Nowcast | hosted-safe, with notices | Copyright and terms notices; pyeconomics' own terms pass the NY Fed's through             |
| SEC EDGAR                                | Submissions, company facts, XBRL frames                      | hosted-safe                             | 10 requests a second in total; a User-Agent with contact is required; nightly bulk files feed the hosted snapshot |
| World Bank                               | WDI and about 45 databases                                   | hosted-safe where `License_Type` is CC BY | Gated per series                                                                        |
| OECD, Eurostat (SDMX)                    | Public datasets                                              | hosted-safe, minus marked exceptions    | The acknowledgement duty flows down to users                                              |
| ECB (SDMX)                               | FX reference rates, €STR, monetary statistics                | hosted-safe                             | A "free of charge from the ECB" notice wherever a paid tier shows it                      |
| BIS (SDMX)                               | Policy rates, credit, property prices, effective FX rates    | hosted-safe, never paywalled            | Including BIS data may not add any charge                                                 |
| OpenFIGI                                 | Identifier mapping                                           | hosted-safe                             | Public-domain FIGIs; rate-limited                                                         |
| Damodaran Online                         | Industry aggregates (ERP, betas, multiples)                  | hosted display of aggregates, with credit | No bulk mirror                                                                          |
| IMF (SDMX)                               | IFS, BOP, DOTS, WEO                                          | library-only until permission granted   | Commercial reuse and bulk download need the IMF's permission                              |
| FRED and ALFRED                          | 850k+ series and their vintages                              | library-only, on the user's own key     | Terms bar caching, databases, redistribution and ML training; per-series copyright tags (14,128 series need pre-approval); hosted use only with the St. Louis Fed's written consent |
| Philadelphia Fed (RTDSM, SPF), Atlanta Fed (GDPNow), Cleveland Fed (inflation expectations) | Real-time vintages, forecasts, nowcasts | library-only | Research or non-commercial terms                                         |
| Ken French Data Library                  | Factors and portfolios                                       | library-only                            | Copyright Fama and French; fetched at runtime, never bundled                              |
| Shiller, AQR, Hou-Xue-Zhang, JKP, Open Source Asset Pricing | Long-run equity data, factor sets         | library-only                            | No stated licence, or non-commercial terms (JKP is CC BY-NC)                              |
| Cboe VIX history                         | Daily VIX                                                    | library-only                            | One personal, non-commercial copy                                                          |
| yfinance (Yahoo)                         | Prices, fundamentals, options                                | library-only, off by default            | Yahoo's terms bar automated collection and commercial reuse                               |
| Coin Metrics community data              | Crypto network data                                          | library-only                            | CC BY-NC 4.0                                                                               |
| DBnomics                                 | Aggregator of about 100 providers                            | library-only                            | Upstream terms plus ODbL; its client is AGPL, so call the REST API directly               |

- Clients are permissive and thin (ADR-0011 decisions 10 and 11): one HTTPS
  transport on urllib3 2.x with truststore for the operating system's trust
  store, imported lazily, never httpx or requests (both bring certifi,
  MPL-2.0); in-house clients for FRED (v2 with its bulk release endpoint),
  BLS, BEA, Census, Treasury, the Fed Board, the NY Fed, SEC EDGAR
  (edgartools requires pyarrow), the World Bank (wbgapi requires PyYAML,
  which has no CPython 3.15 wheel) and DBnomics (its client is AGPL); and
  sdmx1 (Apache-2.0), behind an `[sdmx]` extra, for IMF, OECD, ECB, BIS and
  Eurostat.
- The Fed Board provider reads the stable release files, including the XML
  now posted on each release page: the Board's notice of 2026-07-16 removes
  the Data Download Program's "Build Your Package" option the week of
  2026-11-09, in preparation for the program's eventual retirement, for
  which no date is announced.
- Not built: Stooq (behind a bot challenge, terms unknown); Nasdaq Data
  Link moves to Phase 6 as a bring-your-own-key source.

#### 3.5 Semantic catalog & resolver

- Concept ids such as `us.inflation.pce_core.yoy`, `us.unemployment.rate`,
  `us.policy_rate.target_upper`, `us.treasury.par_curve` and
  `factors.ff5.us.monthly` map to provider series with declared
  transforms (year-over-year, frequency conversion, alignment) and a
  fallback order: free source → the user's own key → premium-only.
- A concept resolves to its originator in hosted mode (core PCE prices
  from BEA, unemployment from BLS, yields from Treasury, the effective
  fed funds rate from the NY Fed) and may resolve to FRED in library mode,
  where one key reaches everything. Series-level licence gates read FRED's
  copyright tags, World Bank `License_Type` and Eurostat's exceptions;
  Moody's series count as pre-approval whatever FRED's label says.
- Mixed frequencies align by explicit, documented rules — never by a
  silent forward-fill, the 0.2.x habit.

#### 3.6 Live bindings & the monetary-policy suite

- A binding fills a model's inputs from the catalog as of a date, using
  vintages wherever the source keeps them; the manifest records every
  series, vintage and retrieval time.
- The suite grows from 0.2.x's four rules to the full family: Taylor
  (1993 and 1999), balanced-approach with and without shortfalls,
  inertial, first-difference, ELB-adjusted and forecast-based rules (FOMC
  Summary of Economic Projections, Survey of Professional Forecasters),
  with pluggable r* (the published Laubach-Williams and
  Holston-Laubach-Williams estimates, or a constant) and gap measures (an
  Okun-scaled unemployment gap, a CBO or filtered output gap).
- Historical evaluation uses ALFRED real-time vintages by default; revised
  data is an explicit option, labelled as such. Vintage evaluation runs on
  the user's machine (ALFRED and the Philadelphia Fed's real-time data are
  library-only); the hosted site shows current prescriptions computed from
  originator data, with forecast-based rules on the Fed Board's SEP.
- Golden tests reproduce published Atlanta Fed Taylor Rule Utility and
  Cleveland Fed simple-rule figures within documented tolerances, and
  match the Phase 1 characterization fixtures or document each intentional
  difference (no more rounding to two decimals, for one).
- Forecast fan charts from SPF and CBO inputs; multi-country rule inputs
  through SDMX sources where the rule is defined.

#### 3.7 Launch catalog, part two — live-data entries

| Domain          | Entries                                                                                     | Library data                       | Hosted site                                          |
|-----------------|---------------------------------------------------------------------------------------------|------------------------------------|------------------------------------------------------|
| `macro`         | Taylor-rule family (3.6); r* (published LW/HLW estimates); output gap with HP, Hamilton, Baxter-King and Christiano-Fitzgerald filters; Phillips curve and Okun's law estimators; Solow model and growth accounting; debt dynamics (r − g); NY Fed yield-curve recession probit | FRED/ALFRED, NY Fed, BEA, BLS, CBO, Penn World Table | Live from originators (BEA, BLS, Treasury, Fed Board, NY Fed, World Bank); vintage evaluation local only |
| `fixed_income`  | Nelson-Siegel / Svensson curve fitting; binomial interest-rate tree with OAS               | Treasury par curve; Fed Board GSW parameters | Live                                         |
| `asset_pricing` | CAPM beta, alpha and SML; FF3/FF5/Carhart/FF6 regressions; Fama-MacBeth with the GRS test  | Ken French Data Library            | The user's own data until the owners grant permission |
| `equity`        | Implied equity risk premium; CAPE and earnings yield                                        | Shiller data; Damodaran aggregates | Damodaran aggregates live; Shiller local only        |
| `portfolio`     | Black-Litterman; risk parity and inverse volatility; hierarchical risk parity               | Ken French industry portfolios as demo inputs | The user's own data                     |
| `econometrics`  | GARCH, GJR and EGARCH; ARIMA/SARIMA, VAR with IRF and FEVD, Engle-Granger and Johansen      | Any series; Ken French daily factors | Live on originator series; the user's own data     |

These entries ship as the eighteen model ids of the Phase 3 roadmap's
launch-catalog table, where one id carries a family's variants as a method
input (the output-gap filters, the factor models, the GARCH variants, the
risk-based allocations).

CBO data are **hosted-safe** as public-domain US government works
([copyright policy](https://www.cbo.gov/about/privacy)). Penn World Table
11.0 is **hosted-safe** under CC BY 4.0 with the authors' required citation
([release and licence](https://www.rug.nl/ggdc/productivity/pwt/)).
Both classifications were checked on 2026-10-17 in Phase 3 Step 9.

#### 3.8 Release `1.0.0a2`

- Tag `v1.0.0a2`; PyPI pre-release; a "data sources and keys" guide in the
  docs preview, including every source's terms and attribution.

**Acceptance criteria**
- Every provider passes a shared contract suite offline in CI against
  recorded responses (secrets scrubbed and the recordings secret-scanned),
  and a weekly live run against the real APIs opens an issue on failure.
- An ALFRED vintage request returns the values as first published,
  verified against a known later revision.
- The policy-rule suite reproduces the Atlanta Fed and Cleveland Fed
  reference figures within documented tolerances and matches the 0.2.x
  characterization fixtures, or documents each intentional difference.
- Every provider declares a licence class, attribution text and terms
  URL; the hosted-mode resolver refuses every library-only,
  bring-your-own-key and premium-local source, and FRED and ALFRED are
  never written to disk (both tested).
- All 50 launch-catalog entries pass `registry.validate()` and their golden
  and property suites.
- **Deployed & verified:** `pip install --pre pyeconomics==1.0.0a2` in a
  clean venv fetches a BLS series without a FRED key and, with the
  tester's own FRED key, runs the Taylor rule for a past date on ALFRED
  vintages.
- **Security:** redaction tests prove no key reaches a log, error,
  manifest, cache file or export; recorded fixtures pass the secret scan;
  the semgrep rule against `pickle` and `eval` is green; when SEC EDGAR is
  delivered, its User-Agent carries the user's configured contact, never a
  hard-coded address; no provider builds a request URL from unvalidated user input.

---

### Phase 4 — Programmatic Surfaces: CLI, REST API, MCP & Exports ✅

**Status:** Complete — 2026-10-28; PR #214; v1.0.0b1; phase04-roadmap.md

**Goal:** Generate the CLI, a versioned REST API and an MCP server from the
registry, plus every export format, so any model or series can flow into
other software — released as `1.0.0b1`.

**Complexity:** High · **Risk:** Medium · **Cloud cost:** $0 (staging
within Cloud Run's free tier) · **Handles sensitive data:** Yes — users'
provider keys in local mode; the hosted service's secrets

**Phase roadmap settings** — the session that writes
`phase04-roadmap.md` (`/roadmap-phase 4`):

| Setting      | Cost                                   | Balanced                                 | Quality                                  |
| ------------ | -------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| Model        | GPT-6.1 Sol                            | Opus 5.5                                 | Opus 5.5                                 |
| Backup       | Sonnet 5.5 — Claude Code · Effort High | GPT-6.1 Sol — Codex · Intelligence XHigh | GPT-6.1 Sol — Codex · Intelligence XHigh |
| Platform     | Codex                                  | Claude Code                              | Claude Code                              |
| Effort       | Intelligence Medium                    | Effort High                              | Effort Max                               |
| Thinking     | —                                      | On                                       | On                                       |
| Conversation | **New**                                | **New**                                  | **New**                                  |

**Runs:** Quality — a phase-roadmap session runs Quality (quality first). If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

> Settings updated 2026-10-14 (refresh): was Claude Opus 5.5 · Max, backup
> GPT-6 Astra. The backup is now GPT-6.1 Sol, the BACKUP line of `roadmodel
> score --category planning --complexity high --budget best` (0.2.84): where
> the benchmarks cannot tell two substitutes apart it takes the cheaper, and
> GPT-6 Astra costs five times as much.

> Settings updated 2026-10-18 (refresh): was Claude Opus 5.5 · Max, backup
> GPT-6.1 Sol · Intelligence Max. The single-column table becomes the full
> ladder (`roadmodel ladder --category planning --complexity high --phase`);
> Quality still runs Opus 5.5 at Max, and its backup is now GPT-6.1 Sol at
> Intelligence XHigh.

This roadmap must make the generators — not hand-written endpoints — the
only way a surface gains a model, and fix the parity suite that proves
four surfaces agree. Same pick, rung and funding as Phase 1: Opus 5.5 at
Max on the claude.ai Max subscription, GPT-6.1 Sol on ChatGPT Pro 5x as
backup.

#### 4.1 Registry export & generators

- `pyeconomics registry export` writes `registry.json` (per model: id,
  version, domain, card text, LaTeX, citations, input and output JSON
  Schema, examples and an example figure) and `openapi.json`. Snapshot
  tests (syrupy) fail CI on any unintended schema change.
- CLI commands, API routes and MCP tools are built from the registry at
  runtime; the TypeScript client (`@hey-api/openapi-ts`) and the Python
  client (`openapi-python-client`) are generated from `openapi.json`.
- A cross-surface parity suite runs every golden case through the Python
  API, the CLI (`--format json`), the REST API and MCP `run_model`; the
  canonical JSON must match byte for byte.

#### 4.2 CLI

- Cyclopts, which reads pydantic models natively:
  `pyeconomics models list|search|describe|run`,
  `pyeconomics data search|get|vintages`, `pyeconomics keys set|list|delete`
  (OS keyring), `pyeconomics cache ls|clear`, `pyeconomics serve`,
  `pyeconomics mcp`, `pyeconomics registry export`.
- `--format table|json|csv|parquet|xlsx|arrow`, stdout piping, `--out`,
  stable exit codes and shell completion — so a shell script, R or Excel
  Power Query can consume any result.

#### 4.3 Exports & reproducibility bundles

- CSV with formula-injection escaping; XLSX with a manifest sheet; Parquet
  and Arrow with the manifest in schema metadata; JSON with the manifest
  embedded.
- A reproducibility bundle (zip): inputs, outputs, manifest, data
  attributions, and a `reproduce.py` that reruns the result with the same
  package version and data vintages.

#### 4.4 REST API

- FastAPI under `/v1`: `models`, `models/{id}`, `models/{id}/run`,
  `series/...`, `healthz`, `version`; OpenAPI 3.1; RFC 9457 problem
  details; `?format=` content negotiation for downloads.
- Models are CPU-bound, so runs execute in a worker pool under per-model
  time budgets. In hosted mode an input above its model's budget is
  refused with a pointer to local mode; queued async jobs arrive with
  Postgres in Phase 8.
- Two modes from one app factory: `local` (every source the user can
  access, bound to 127.0.0.1) and `hosted` (hosted-safe sources only,
  anonymous access, per-IP limits with the `limits` library on Upstash
  Redis behind Cloudflare rate rules). API keys and plans wait for Phase
  8.
- Deterministic results are cached, keyed by model id and version,
  canonical inputs and data vintage, with `Cache-Control` headers so
  Cloudflare can serve repeats.

#### 4.5 MCP server

- The official `mcp` Python SDK (2.x, `MCPServer`) on the 2026-07-28
  specification: a stdio entry point (`pyeconomics mcp`, runnable through
  `uvx`) for local use, and stateless Streamable HTTP for a read-only
  hosted endpoint that Phase 5 deploys.
- Tool discovery instead of hundreds of tools: `search_models`,
  `describe_model` (schemas and card), `run_model`, `get_series` and
  `list_sources`, plus 10–20 headline tools; `outputSchema` with
  structured content; deterministic tool order; concise results with
  links for large data; namespaced names.
- The MCP Apps extension renders a result's chart inside clients that
  support it.
- Tool outputs are data, never instructions; no tool executes code or
  fetches an arbitrary URL. Results from a source whose `llm_use` is
  forbidden are withheld, and unclear ones need the user's opt-in, because
  an MCP result lands in an LLM's context. Tool descriptions are tested
  with real agent tasks, and a `server.json` is published to the official
  MCP Registry.

#### 4.6 Optional AI narrative

- The 0.2.x commentary returns as an optional `[ai]` extra:
  provider-agnostic, bring-your-own-key, off by default, with per-call cost
  shown. The default model is a config value, picked with the model
  selector when the step is implemented. It refuses inputs from any source
  whose `llm_use` is forbidden, and stays out of hosted mode until Phase 8
  adds a cost ledger and cap.

#### 4.7 Service container & staging

- A slim, non-root image with the `[server]` extra and hosted-safe
  providers only — no yfinance, no Bloomberg libraries in the image.
- Cloud Run staging (minimum 0 instances, capped maximum) behind a
  Cloudflare Worker on the staging hostname, with Cloudflare Access, that
  forwards to the Cloud Run origin with an origin credential the app
  verifies (ADR-0012 decision 20); deploys from GitHub through OIDC and
  Workload Identity Federation, so no service-account key exists; a budget
  alert; `/version` reports the package version and git SHA.

#### 4.8 Release `1.0.0b1`

- Tag `v1.0.0b1`; PyPI pre-release; the CLI and MCP quick-starts in the
  docs preview.

**Acceptance criteria**
- The parity suite is green across Python, CLI, REST and MCP for every
  golden case of every registered model.
- `pyeconomics models run … --format parquet` pipes into pandas; the XLSX
  export opens with its manifest sheet; the CSV export escapes
  formula prefixes (tested); a reproducibility bundle reruns to identical
  outputs in a fresh environment.
- Schemathesis property tests against `openapi.json` find no 5xx responses
  and no schema violations; oversized or over-budget inputs return 413 or
  422 with problem details.
- The MCP server passes MCP Inspector checks over stdio and Streamable
  HTTP; the `tools/list` snapshot is stable; scripted agent tasks (price a
  bond and report its duration; run a bound model for a past date)
  succeed through the tools. (Amended in Phase 4 Step 16: the past-date
  task binds the recession probability at 2025-06-30; a 2019 Taylor-rule
  task joins once #195 and #196 are fixed, as Step 9 recorded.)
- **Deployed & verified:** `pip install --pre pyeconomics==1.0.0b1` gives
  a working `pyeconomics` CLI and `pyeconomics mcp` server; staging
  `/version` reports this phase's SHA; a request with a Cloudflare Access
  service token runs a model and fetches a hosted-safe series; a request
  for a library-only source returns 403 with a licence explanation.
- **Security:** the image scan shows no Critical or High findings; no
  endpoint fetches a user-supplied URL (SSRF test); a burst test proves
  the rate limits; the service reads secrets only from Secret Manager;
  deploys use OIDC with no stored key; local mode refuses a non-loopback
  bind unless explicitly forced.

---

### Phase 5 — Web App, Docs & Public Launch (1.0.0)

**Status:** In progress — phase05-roadmap.md

**Goal:** Ship the web app — static, prerendered model pages with live
calculators, hosted and local — and the documentation site, then launch
pyeconomics 1.0.0 publicly behind a readiness gate.

**Complexity:** High · **Risk:** High (first public surface; a stable
PyPI release cannot be unpublished, only yanked) · **Cloud cost:** about
$0–10/month at hobby scale plus the domain (TBD) ·
**Handles sensitive data:** Yes — waitlist emails (PII), analytics, the
service's secrets

**Phase roadmap settings** — the session that writes
`phase05-roadmap.md` (`/roadmap-phase 5`):

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Opus 5.5**       | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | High               | Max                |
|               | AA       | 47.8               | 53.6               | 57.6               |
|               | Price    | $1.61/1M           | $6.02/1M           | $67.58/1M          |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | Max                |
|               | AA       | 46.8               | 50.2               | not measured       |
|               | Price    | $3.03/1M           | $2.18/1M           | $10.00/1M*         |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6.1 Sol**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | Max                |
|               | AA       | not measured       | not measured       | 51.8               |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $5.18/1M           |

Ranked for planning, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Quality — a phase-roadmap session runs Quality (quality first). If
that column's usage pool reads `tight` or `exhausted`, run the first of its
Runner-up and Backup whose pool has headroom; on a `tight` pool an option marked
↓ (the Pick one level lower) also runs. With none, a `tight` column runs the
Cost column and an `exhausted` one its Backup.

> Settings updated 2026-10-29 (rerank): was Opus 5.5 · Max, Quality's Backup
> GPT-6 Astra · Max. Quality's Backup is now GPT-6.1 Sol · Max: roadmodel
> 0.2.100 takes the cheaper of two same-maker models the benchmarks cannot
> tell apart (AA 51.8 at $5.18/1M against 52.7 at $24.80/1M). Every Pick and
> Runner-up is unchanged; `roadmodel ladder --category planning --complexity
> high --phase` prints the same table.

> Settings updated 2026-10-25 (rerank): each column's Runner-up and Backup now come from makers other than its Pick; every Pick is unchanged.

> Settings updated 2026-10-14 (refresh): was Claude Opus 5.5 · Max, backup
> GPT-6 Astra. The backup is now GPT-6.1 Sol, the BACKUP line of `roadmodel
> score --category planning --complexity high --budget best` (0.2.84): where
> the benchmarks cannot tell two substitutes apart it takes the cheaper, and
> GPT-6 Astra costs five times as much.

> Settings updated 2026-10-18 (refresh): was Claude Opus 5.5 · Max, backup
> GPT-6.1 Sol · Intelligence Max. The single-column table becomes the full
> ladder (`roadmodel ladder --category planning --complexity high --phase`);
> Quality still runs Opus 5.5 at Max, and its backup is now GPT-6.1 Sol at
> Intelligence XHigh.

This roadmap must stage the first public, partly irreversible launch —
layer by layer, with the readiness gate as its own step — and get the
legal, attribution and trademark obligations right on day one. Same pick,
rung and funding as Phase 1: Opus 5.5 at Max on the claude.ai Max
subscription, GPT-6.1 Sol on ChatGPT Pro 5x as backup.

#### 5.1 Frontend foundation (ADR-0006)

- `web/`: Astro with static output and React islands, in TypeScript, with
  Tailwind and shadcn/ui — the maintainer's existing React toolkit —
  KaTeX for formulas, Plotly.js for charts (the same figure JSON the
  library emits), RJSF for schema-driven forms and the generated
  TypeScript client; Vitest and Playwright; WCAG 2.2 AA.

#### 5.2 Generated model pages

- Astro content collections read `registry.json` and render
  `/models/<domain>/<slug>`: formula, explanation, variables and units,
  assumptions, limitations, evidence status, citations, syllabus tags, a
  worked example, JSON-LD and Open Graph images.
- A calculator island renders the input schema, calls the API, shows
  outputs, chart and warnings, and offers downloads (CSV, XLSX, Parquet,
  JSON, reproducibility bundle) plus "copy as Python / CLI / curl / MCP"
  snippets.

#### 5.3 Navigation & search

- Fifteen domain sections, syllabus filters driven by the crosswalk tags,
  static full-text search (Pagefind), related models, and the public
  coverage matrix.
- The filters' first data is a seed this phase creates in `syllabi/`, in
  7.1's format: the 2027 CFA® Program topic areas for Levels I to III,
  mapped to the launch catalog, factual names and links only, with neutral
  slugs (ADR-0013 decision 12). Phase 7 adds the other syllabi and the rest
  of the coverage.

#### 5.4 Data explorer & user data

- Search, transform, chart and download hosted-safe series from their
  originators, with the as-of date and the source's attribution on every
  chart and file. The explorer exists to feed models; it never replicates
  a provider's own product.
- Models whose data is library-only (Ken French factors, Shiller, AQR)
  run on the hosted site with the user's own data, and point to the local
  app for live inputs.
- User files (CSV/XLSX) are parsed in the browser; only the values a run
  needs reach the API, which processes them in memory and never stores or
  logs them.

#### 5.5 Local app

- `pyeconomics serve` (the `[app]` extra) serves the same built site and
  the API on 127.0.0.1 with every source the user can access — yfinance,
  bring-your-own-key providers and, from Phase 6, Bloomberg.

#### 5.6 Documentation site (ADR-0007)

- Sphinx with MyST-NB, sphinx-autoapi and sphinx-gallery on Read the Docs:
  tutorials (install, first model, data and keys, CLI, API, MCP), how-to
  guides (outputs into pandas, R and Excel; pyeconomics inside xlwings
  Lite), the generated model reference, syllabus study paths, and a 0.2.x
  → 1.0 migration guide.
- Examples execute in CI (doctests and Sybil); in-browser examples run on
  marimo's WebAssembly export.
- Python-for-finance tutorials that teach, through pyeconomics and in our
  own words, the skills CFA candidates' Python Practical Skills Module
  covers (pandas, return statistics, Monte Carlo, portfolio math) — a
  distribution channel that copies no curriculum content.

#### 5.7 Legal, trust & brand (ADR-0009)

- Terms of use (passing through the NY Fed's and OECD's conditions),
  privacy policy, disclaimers (educational; not investment advice; no
  warranty), a "Data sources & licences" page plus per-chart and per-file
  attributions carrying every required notice (§5 "Legal & brand
  guardrails"), the CFA® marks and non-affiliation notice, the licence
  page, `security.txt` and a status page; cookie-less analytics.
- A permissions programme: written requests to the St. Louis Fed (hosted
  FRED use), Ken French, Robert Shiller, the IMF and the Philadelphia,
  Atlanta and Cleveland Feds. Each answer is recorded in the provider's
  metadata; a grant moves a source to hosted-safe, and silence leaves it
  library-only.
- ADR-0009 executed: domains registered, the clearance search done, and
  a filing made if counsel advises one.

#### 5.8 Production hosting & operations

- Cloudflare: DNS, TLS, CDN, WAF, rate rules and static hosting for the
  site. Cloud Run: the production API service. A scheduled snapshot job
  (Cloud Run job + Cloud Scheduler) writes gzip-compressed canonical-JSON
  snapshots of the hosted-safe originators — the cache's frame codec, not
  Parquet — to a private Cloud Storage bucket, versioned by run, mounted
  into the job and, read-only, into the service, with a heartbeat (ADR-0013
  decision 6: a volume mount needs no long-lived access key and no signing
  code, which R2 would).
- Sentry (frontend and backend), OpenTelemetry to Grafana Cloud, Better
  Stack uptime checks; budget alerts and a capped maximum instance count;
  the §5 runbooks published.

#### 5.9 Launch readiness gate (its own step)

- Checklist: legal pages and attributions live; robots, sitemap and
  indexing; every alert seen to fire once; rollback rehearsed (previous
  Cloud Run revision and previous static deploy); a load test inside the
  budget; feedback channels (GitHub Discussions, a newsletter and a
  waitlist with one processor) live; a priced "Pro" preview page — a fake
  door that records intent and sells nothing; the §5 Gate G2 metrics
  recording; `1.0.0rc1` soaked in production, behind Cloudflare Access,
  for seven days against fixed criteria, during which only security fixes
  merge (ADR-0013 decision 18).
- Web quality on a fixed sample of thirteen pages (ADR-0013 decision 19):
  Lighthouse, the median of three mobile runs, at least 90 for
  performance, accessibility, best practices and SEO, and no WCAG 2.2 AA
  violation under axe.
- Going live is a decision recorded in the PR, not a side effect of a
  merge.

#### 5.10 Cutover & the 1.0.0 release

- Cut DNS to production, tag `v1.0.0` (stable on PyPI), point Read the
  Docs `stable` at 1.0, update the README and PyPI description, announce,
  and run the post-launch verification.

**Acceptance criteria**
- Every registered model has a prerendered page listed in the sitemap;
  Lighthouse scores at least 90 for performance, accessibility, best
  practices and SEO on the thirteen-page sample ADR-0013 decision 19
  fixes.
- Web calculator outputs equal the Python API's canonical outputs (the
  parity suite runs through the deployed API).
- `pip install pyeconomics` installs 1.0.0, and `pyeconomics serve` serves
  the same pages locally with library-only sources available.
- **Deployed & verified:** production `/version` reports the 1.0.0 SHA; a
  synthetic check runs one model per domain and downloads a CSV carrying
  its attribution; the snapshot heartbeat is green and an injected failure
  fired its alert once; Read the Docs `stable` serves 1.0.
- **Security:** an OWASP ZAP baseline scan finds no High issue; CSP, HSTS
  and frame-ancestors are verified by an observatory scan; uploaded files
  never reach storage (code check plus a network-log test); the privacy
  policy matches the actual data flows; waitlist PII sits only with its
  processor, under least privilege.

---

### Phase 6 — Premium Data: Bloomberg & BYOK Providers

**Status:** Not started

**Goal:** Let users who pay for data use it everywhere on their own
machine — a Bloomberg Terminal, commercial APIs on their own keys,
OpenBB's providers — under a clear fallback policy, without any licensed
data ever reaching the hosted service; released as the next minor
(expected `1.1.0`).

**Complexity:** Medium · **Risk:** Medium (vendor licensing) ·
**Cloud cost:** $0 · **Handles sensitive data:** Yes — paid-provider keys
and licensed market data

**Phase roadmap settings** — the session that writes
`phase06-roadmap.md` (`/roadmap-phase 6`):

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Opus 5.5**       | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | High               | Max                |
|               | AA       | 47.8               | 53.6               | 57.6               |
|               | Price    | $1.61/1M           | $6.02/1M           | $67.58/1M          |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | Max                |
|               | AA       | 46.8               | 50.2               | not measured       |
|               | Price    | $3.03/1M           | $2.18/1M           | $10.00/1M*         |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6.1 Sol**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | Max                |
|               | AA       | not measured       | not measured       | 51.8               |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $5.18/1M           |

Ranked for planning, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Quality — a phase-roadmap session runs Quality (quality first). If
that column's usage pool reads `tight` or `exhausted`, run the first of its
Runner-up and Backup whose pool has headroom; on a `tight` pool an option marked
↓ (the Pick one level lower) also runs. With none, a `tight` column runs the
Cost column and an `exhausted` one its Backup.

> Settings updated 2026-10-29 (rerank): was Opus 5.5 · Max, Quality's Backup
> GPT-6 Astra · Max. Quality's Backup is now GPT-6.1 Sol · Max: roadmodel
> 0.2.100 takes the cheaper of two same-maker models the benchmarks cannot
> tell apart (AA 51.8 at $5.18/1M against 52.7 at $24.80/1M). Every Pick and
> Runner-up is unchanged; `roadmodel ladder --category planning --complexity
> high --phase` prints the same table.

> Settings updated 2026-10-25 (rerank): each column's Runner-up and Backup now come from makers other than its Pick; every Pick is unchanged.

> Settings updated 2026-10-14 (refresh): was Claude Opus 5.5 · Max, backup
> GPT-6 Astra. The backup is now GPT-6.1 Sol, the BACKUP line of `roadmodel
> score --category planning --complexity high --budget best` (0.2.84): where
> the benchmarks cannot tell two substitutes apart it takes the cheaper, and
> GPT-6 Astra costs five times as much.

> Settings updated 2026-10-18 (refresh): was Claude Opus 5.5 · Max, backup
> GPT-6.1 Sol · Intelligence Max. The single-column table becomes the full
> ladder (`roadmodel ladder --category planning --complexity high --phase`);
> Quality still runs Opus 5.5 at Max, and its backup is now GPT-6.1 Sol at
> Intelligence XHigh.

This roadmap must turn each vendor's terms into enforceable rules rather
than prose, and design Bloomberg support around a Terminal that CI will
never have. Same pick, rung and funding as Phase 1: Opus 5.5 at Max on
the claude.ai Max subscription, GPT-6.1 Sol on ChatGPT Pro 5x as backup.

#### 6.1 Bring-your-own-key framework

- A provider capability matrix (coverage, rate limits, licence class,
  terms URL) generated from provider metadata and published in the docs.
- Key setup through `pyeconomics keys set <provider>` and the local app's
  settings page, stored in the OS keyring; quota awareness and warnings
  before a call would exceed a plan's limit; a terms notice on first use.

#### 6.2 Bloomberg provider

- **Install.** `blpapi` is not on PyPI: users install it from Bloomberg's
  own package index or conda-forge. `pyeconomics[bloomberg]` installs only
  the pure-Python side and never names Bloomberg's index — an extra index
  merged into pip's resolution invites dependency confusion. The
  maintainer's environment pins `blpapi` to that index through an explicit
  uv index. The import is lazy, with a clear message when it is missing.
- **Session.** Desktop API on `localhost:8194` only, never configurable to
  a remote host; it fails fast when no Terminal is logged in. The provider
  registers only on Windows — the Desktop API's platform — and never in
  hosted mode.
- **Requests.** Reference data (single and bulk fields, with overrides),
  historical data, intraday bars and ticks, field search and field info,
  instrument lookup; BQL through `//blp/bqlsvc` as experimental, because
  Bloomberg's public guide does not document it. Real-time subscriptions
  are out of scope.
- **Mapping.** A YAML registry maps semantic concepts to Bloomberg
  securities and fields, each verified on a Terminal (FLDS, SECF) before
  it ships; raw field codes pass straight through; ISIN, CUSIP and FIGI
  identifiers map through OpenFIGI.
- **Limits.** Bloomberg's data limits are private (university guides
  report a daily hit cap and monthly unique-security caps), so a hit
  counter estimates securities × fields before each request and refuses
  calls over a user-set budget unless forced; requests are batched and
  de-duplicated; limit errors are never retried; data is cached only
  locally, per user.
- **Testing without a Terminal.** `blpapi.test` builds synthetic responses
  in CI, since the wheels bundle the C++ SDK; real service schemas are
  captured once; record-and-replay on the maintainer's Terminal writes to a
  git-ignored folder and commits synthetic numbers only; a
  `BloombergTransport` protocol lets a fake stand in for the session; live
  tests run only when `PYECONOMICS_BBG_LIVE=1` is set and the local port
  answers.
- **0.2.x work.** The archived consensus-forecast tickers (`ECCCUS`,
  `ECUPUS`) become a Bloomberg-sourced variant of the forecast-based
  policy rules.
- **Backends.** The official `blpapi` is primary; xbbg (Apache-2.0) is an
  optional backend for users who already run it.
- **Forbidden.** Any Bloomberg path in the hosted app or API — Terminal or
  Bloomberg Anywhere credentials are never accepted; exposing port 8194
  beyond localhost (tunnels, container host networking, remote notebooks);
  Bloomberg data in the repository, docs, examples, fixtures, published
  notebooks or shared caches; feeding firm databases from the Desktop API;
  spreading load across Terminals to dodge limits; automating the Terminal
  login. Written confirmation from Bloomberg comes first before sending
  its data to an LLM, publicly displaying derived outputs, or bridging the
  hosted UI to locally fetched data. A trademark and non-affiliation notice
  accompanies the provider.

#### 6.3 Commercial and institutional providers

Terms and prices checked on 2026-10-03. Only Tiingo's public terms allow
a hosted app to pass a user's own key through; every other vendor is local
only unless it confirms otherwise in writing.

| Provider                     | Coverage                                          | Entry price                      | Hosted                                              | Batch |
|------------------------------|---------------------------------------------------|----------------------------------|-----------------------------------------------------|-------|
| Tiingo                       | End-of-day equities, IEX, crypto, news            | Free tier; $30/month             | Pass-through of the user's own token allowed        | 1     |
| Massive (formerly Polygon)   | US stocks, options, indices, FX, crypto, futures  | Free tier; $29/month             | No (business plans only)                            | 1     |
| Financial Modeling Prep      | Fundamentals, prices                              | 250 calls/day free; $19/month    | No                                                  | 1     |
| Alpha Vantage                | Equities, FX, crypto, fundamentals                | 25 calls/day free; $49.99/month  | Written agreement only                              | 1     |
| EODHD                        | Global end-of-day, intraday, fundamentals         | 20 calls/day free; $19.99/month  | Custom plan only                                    | 1     |
| Finnhub                      | Global prices, fundamentals, estimates            | Free personal tier; $49.99/month | Written approval only                               | 1     |
| Twelve Data                  | Stocks, FX, crypto, ETFs                          | Testing tier; $99/month          | Venture plan and above                              | 1     |
| Alpaca                       | US consolidated feed, options, crypto             | IEX real-time free; $99/month    | Through OAuth, with notice to Alpaca (Phase 8)      | 1     |
| Nasdaq Data Link             | Sharadar, Zacks and other datasets                | Free key; Sharadar from $69/month| No (no software-as-a-service use)                   | 1     |
| Databento                    | CME, Nasdaq, OPRA, ICE, Eurex                     | $125 credits; $199/month         | Plan plus exchange licences                         | 2     |
| Interactive Brokers          | Global multi-asset                                | With a funded account            | Written approval only                               | 2     |
| Trading Economics            | Macro indicators for 196 countries                | $199/month API plan              | Enterprise plan only                                | 2     |
| LSEG Workspace (`lseg-data`) | Multi-asset, fundamentals, news                   | Contract (trial available)       | No                                                  | 2     |
| FactSet (`fds.sdk`)          | Multi-asset, fundamentals                         | Contract                         | No                                                  | 2     |
| WRDS (`wrds`)                | CRSP, Compustat — academic, non-commercial        | Institutional                    | No; its terms also ban loading data into LLMs       | 2     |
| Macrobond                    | Macro and financial                               | Contract                         | No                                                  | 2     |
| Morningstar Direct           | Funds and portfolios                              | Contract                         | No                                                  | 2 (low priority) |

- Skipped: S&P Capital IQ (no general SDK), Intrinio (its terms count
  sending data to an LLM API as redistribution), Haver and CEIC
  (contract-only and restrictive), IEX Cloud (retired 2024-08-31), and
  Bloomberg's Server API, B-PIPE and Data License (enterprise contracts).
- Local credential lookup: explicit argument → a session setter holding
  the key as a secret type → the vendor's usual environment variable → a
  `.env` file in the user's config directory (never overriding a real
  environment variable) → the OS keyring → `pyeconomics.toml` with
  `${VAR}` placeholders. Nothing found falls back to the free provider.
- Every new provider declares its `llm_use` flag (3.1) from its terms.

#### 6.4 OpenBB bridge

- OpenBB's Open Data Platform v5 (Apache-2.0) as an optional
  meta-provider, so OpenBB users reach their configured providers through
  pyeconomics bindings.
- pyeconomics models published as an OpenBB extension, so OpenBB and
  Workspace users can call cited pyeconomics models — distribution through
  the largest open finance platform, without competing on data plumbing.

#### 6.5 Fallback policy & premium-only datasets

- The resolver tries the free default, then the user's paid key, then a
  premium-only source; skips providers whose credentials are missing;
  fails over only between series with identical definitions; and honours
  `strict=True` to disable fallback. The manifest records the chain it
  tried.

| Need                   | Free default                                  | User's own key                        | Premium-only (local)             | Hosted site                    |
|------------------------|-----------------------------------------------|---------------------------------------|----------------------------------|--------------------------------|
| US CPI                 | BLS `CUUR0000SA0`                             | FRED / ALFRED (with vintages)         | Bloomberg `CPURNSA Index`        | BLS snapshot, BLS notice       |
| Treasury yield curve   | Treasury par curve; Fed GSW zero curve        | FRED `DGS1MO`…`DGS30`                 | Bloomberg `USGG*`                | Treasury and GSW snapshots     |
| Corporate spreads      | Fed GZ spread and excess bond premium (monthly) | —                                   | Bloomberg OAS indices            | GZ and EBP only                |
| Company fundamentals   | SEC EDGAR company facts and frames            | FMP, EODHD                            | Bloomberg; WRDS Compustat (academic) | EDGAR snapshot             |
| Equity prices          | yfinance (local, opt-in, with a terms warning) | Tiingo → Massive / Alpaca / EODHD    | Bloomberg `PX_LAST`              | User data; Tiingo pass-through from Phase 8 |
| S&P 500 total return   | None licensable; Shiller monthly as a local approximation | Tiingo SPY adjusted close (proxy) | Bloomberg `SPXT Index`          | User data                      |
| Options and implied vol| yfinance (local)                              | Massive, ORATS, IBKR, Databento OPRA  | Bloomberg option fields          | None                           |
| FX rates               | ECB reference rates; Fed H.10                 | Massive, Twelve Data                  | Bloomberg `EURUSD Curncy`        | ECB and H.10 snapshots         |

#### 6.6 Release

- The next minor release (expected `1.1.0`) with a "premium data" guide
  per provider: setup, limits, terms, and what never leaves the user's
  machine.

**Acceptance criteria**
- Every new provider passes the shared contract suite against recorded
  responses, with recordings scrubbed and secret-scanned.
- An owner-run Bloomberg smoke script on a Terminal machine returns
  reference, historical and intraday data; the PR records that the run
  passed without committing any data.
- The Bloomberg provider registers only on Windows and only in local mode,
  its hit budget refuses an over-budget request, and the published package
  metadata names no extra index (all tested).
- Hosted mode refuses every bring-your-own-key and premium-local source,
  and the hosted image contains no Bloomberg or vendor SDK (verified by
  image inspection).
- The OpenBB extension installs alongside OpenBB 5.x and runs a
  pyeconomics model from OpenBB's Python API.
- **Deployed & verified:** the release installs from PyPI with each
  provider extra; a contract smoke run with a test key passes for every
  batch-1 provider; production `/version` still reports a build whose
  image contains none of these providers.
- **Security:** keys live only in the OS keyring or environment; the
  redaction suite covers every new provider; licensed data is cached only
  locally, opt-in, with a licence notice; a network test proves no key or
  licensed value is ever sent to pyeconomics' hosted service.

---

### Phase 7 — Catalog Completion: CFA Program & Beyond

**Status:** Not started

**Goal:** Cover every formula family in the CFA® Program — Levels I–III and
all three Level III pathways — then the FRM, CAIA and CIPM canons and the
wider econometrics, macro, micro and quant literature, shipped in domain
batches that surface everywhere automatically.

**Complexity:** High (volume, not novelty) · **Risk:** Medium ·
**Cloud cost:** $0 incremental (hosted compute caps apply) ·
**Handles sensitive data:** No

**Phase roadmap settings** — the session that writes
`phase07-roadmap.md` (`/roadmap-phase 7`):

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Opus 5.5**       | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | High               | Max                |
|               | AA       | 47.8               | 53.6               | 57.6               |
|               | Price    | $1.61/1M           | $6.02/1M           | $67.58/1M          |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | Max                |
|               | AA       | 46.8               | 50.2               | not measured       |
|               | Price    | $3.03/1M           | $2.18/1M           | $10.00/1M*         |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6.1 Sol**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | Max                |
|               | AA       | not measured       | not measured       | 51.8               |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $5.18/1M           |

Ranked for planning, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Quality — a phase-roadmap session runs Quality (quality first). If
that column's usage pool reads `tight` or `exhausted`, run the first of its
Runner-up and Backup whose pool has headroom; on a `tight` pool an option marked
↓ (the Pick one level lower) also runs. With none, a `tight` column runs the
Cost column and an `exhausted` one its Backup.

> Settings updated 2026-10-29 (rerank): was Opus 5.5 · Max, Quality's Backup
> GPT-6 Astra · Max. Quality's Backup is now GPT-6.1 Sol · Max: roadmodel
> 0.2.100 takes the cheaper of two same-maker models the benchmarks cannot
> tell apart (AA 51.8 at $5.18/1M against 52.7 at $24.80/1M). Every Pick and
> Runner-up is unchanged; `roadmodel ladder --category planning --complexity
> high --phase` prints the same table.

> Settings updated 2026-10-25 (rerank): each column's Runner-up and Backup now come from makers other than its Pick; every Pick is unchanged.

> Settings updated 2026-10-14 (refresh): was Claude Opus 5.5 · Max, backup
> GPT-6 Astra. The backup is now GPT-6.1 Sol, the BACKUP line of `roadmodel
> score --category planning --complexity high --budget best` (0.2.84): where
> the benchmarks cannot tell two substitutes apart it takes the cheaper, and
> GPT-6 Astra costs five times as much.

> Settings updated 2026-10-18 (refresh): was Claude Opus 5.5 · Max, backup
> GPT-6.1 Sol · Intelligence Max. The single-column table becomes the full
> ladder (`roadmodel ladder --category planning --complexity high --phase`);
> Quality still runs Opus 5.5 at Max, and its backup is now GPT-6.1 Sol at
> Intelligence XHigh.

This roadmap must turn an open-ended ambition into a finite, ordered batch
plan whose measure of done is the coverage matrix, with every batch held to
the model definition of done. Same pick, rung and funding as Phase 1: Opus
5.5 at Max on the claude.ai Max subscription, GPT-6.1 Sol on ChatGPT Pro 5x
as backup.

#### 7.1 Syllabus crosswalks & the coverage matrix

- Versioned crosswalk data in `syllabi/`: CFA Program 2026 and 2027 (topic
  names and weight ranges by level; the 2027 outline renames Corporate
  Issuers, Equity Investments, Derivatives and Portfolio Management at
  Levels I and II), FRM Parts I and II, CAIA, CIPM, CMT and CQF. Tags are
  factual and link to the issuing body; no learning-outcome wording is
  stored. Curricula change yearly, so the mapping is data, never package
  structure.
- Phase 5 creates `syllabi/` — its JSON Schema and one TOML file per
  syllabus version — with one seed, the 2027 CFA Program topic areas for
  Levels I to III mapped to the launch catalog (ADR-0013 decision 12).
  This phase extends the 2027 file, adds 2026 and the other syllabi in the
  same format, and completes the coverage matrix Phase 5 publishes.
- A coverage matrix generated from the registry — syllabus topic × model
  family → planned, implemented or verified — published in the docs and
  the web app as the public measure of progress.
- Scale, estimated: the complete canon is on the order of 1,000–1,500
  catalog entries (each a family of closely related formulas); the CFA
  Program alone is roughly 250–350; the first ~200 entries cover most
  demand. The Phase 7 roadmap orders batches by that demand.

#### 7.2 Domain batches

Each domain is a subpackage, a web-navigation section and, when a batch
lands, a minor release. Batches in different domains are declared
independent and may run in parallel worktrees (§5).

| Domain          | Next-wave entries (illustrative)                                                                                 |
|-----------------|------------------------------------------------------------------------------------------------------------------|
| `foundations`   | Day-count and compounding conventions, Ledoit-Wolf shrinkage, PCA, root-finding and optimizers, Sobol sequences, correlated paths, bootstrap intervals |
| `econometrics`  | WLS/FGLS, IV/2SLS with weak-IV tests, GMM, panel FE/RE with Hausman, clustered and Driscoll-Kraay errors, DiD and event studies, RD, logit/probit, Poisson, Tobit/Heckman, quantile regression, unit-root tests, Granger, SVAR, VECM, local projections, Markov switching, Kalman models, dynamic-factor nowcasting, break tests, LASSO, double ML |
| `macro`         | NK 3-equation simulator, IS-LM, AD-AS, Ramsey, OLG, RBC, fiscal multipliers, Beveridge curve, Sahm rule, quantity theory, breakeven inflation, Kalman NAIRU, term premia, McCallum / Orphanides / Friedman rules, Laubach-Williams port |
| `international` | Mundell-Fleming, Dornbusch overshooting, monetary and portfolio-balance FX models, BEER/FEER, balance of payments and NIIP, REER/NEER, carry trade |
| `micro`         | Elasticities and deadweight loss, Cobb-Douglas/CES, Cournot/Bertrand/Stackelberg, monopoly pricing, HHI and Lerner, Nash solver, auctions, Pigouvian tax, prospect theory, β-δ discounting, herding measures |
| `accounting`    | Inventory conversions, depreciation, deferred tax, diluted EPS, leases, pensions, FX translation, consolidation, accrual ratios, bank capital |
| `corporate`     | Modigliani-Miller I/II, APV, trade-off optimum, cash conversion cycle, payout effects, M&A exchange ratios, real options, EVA, LBO math |
| `equity`        | Residual income, justified multiples, private-company discounts, ERP build-ups (Grinold-Kroner, Singer-Terhaar), index weighting, three-stage DDM |
| `fixed_income`  | FRN discount margin, G/I/Z-spreads, roll-down, immunization, futures hedging and CTD, MBS prepayment, ABS waterfalls, TIPS breakevens, Vasicek/CIR/Ho-Lee/Hull-White/BDT trees, convertibles, Merton distance to default, CDS hazard bootstrapping, CreditMetrics, Basel IRB, CVA |
| `derivatives`   | Bachelier, American approximations, trinomial and Crank-Nicolson, Longstaff-Schwartz, barrier/Asian/lookback/digital options, Heston, SABR, Dupire, jump-diffusion, variance swaps and VIX replication, strategy payoffs, caps/floors/swaptions |
| `alternatives`  | IRR/TVPI/DPI/RVPI and J-curve, Takahashi-Alexander pacing, VC method, fee waterfalls, return unsmoothing, REIT NAV and FFO/AFFO, commodity return decomposition, NVT/MVRV, AMM math; stock-to-flow kept as `rejected` |
| `portfolio`     | Resampled and robust MVO, surplus/LDI optimization, CVaR optimization, maximum diversification, rebalancing bands, CPPI, goals-based Monte Carlo, after-tax returns and asset location, human capital, execution cost models |
| `asset_pricing` | APT and macro factors, q-factor, BAB/QMJ, Hansen-Jagannathan bounds, portfolio sorts, beta adjustments, the Open Source Asset Pricing anomaly library |
| `risk`          | Filtered historical simulation, EVT, component and incremental VaR, stress-scenario engine, liquidity-adjusted VaR, LCR/NSFR, operational-risk LDA, FRTB ES, DCC-GARCH, copulas, EE/PFE, EVE/NII |
| `performance`   | Attribution linking (Carino, Menchero, GRAP), fixed-income attribution, returns-based style analysis, Omega/Kappa, drawdown statistics, PME variants, composite dispersion |

Models that take personal circumstances — after-tax returns, goals-based
Monte Carlo, human capital, retirement income from the Private Wealth
pathway — ship as general calculators whose parameters the user controls,
never as recommendations, and counsel reviews them before the hosted site
offers them (§5 "Legal & brand guardrails").

#### 7.3 Wrap, don't rewrite

- Where a maintained, permissively licensed library already implements an
  estimator well, register an adapter instead of a rewrite: statsmodels
  (BSD-3), linearmodels and arch (NCSA) for econometrics; QuantLib
  (BSD-style) as an optional pricing engine; vollib (MIT) for implied
  volatility; skfolio (BSD-3) for numerical portfolio optimization, with
  Riskfolio-Lib or PyPortfolioOpt as alternatives. The adapter adds the
  model card, units, golden cases and parity — the value pyeconomics owns.
- Closed-form textbook formulas (performance statistics, bond math, BSM)
  are native, because they are the curriculum itself, and are
  cross-checked against the oracles in 2.4.
- Never a runtime dependency: FinancePy (GPL-3.0), rateslib
  (source-available, non-commercial), and AGPL packages such as
  getfactormodels, the DBnomics client and OpenBB's AGPL provider plugins
  (§5 "Legal & brand guardrails").
- Estimated models follow the scikit-learn protocol (`fit`, `predict`,
  `score`), as skfolio does for portfolios, so policy-rule estimation,
  factor models and volatility models compose with existing tooling.
- Heavy dependencies sit behind extras, so the core install stays small.

#### 7.4 Learning layer

- A worked-example generator: random but seeded parameters, a
  step-by-step solution built from the model's own intermediate values,
  and the formula — written in our own words.
- Study paths per syllabus: ordered lists of model pages and examples
  keyed to the crosswalk tags.
- Not exam prep: no learning-outcome text, no curriculum examples, no
  exam-style question banks, no pass claims. A paid study product is a
  Phase 8 decision with its own legal review (§5 "Legal & brand
  guardrails").

#### 7.5 The 0.2.x wishlist and local prototypes

- Every item on the 2024 wishlist maps to a domain above: quantity theory,
  exchange-rate models, fiscal models, the macro and micro canon, and the
  "other" list (behavioral, agent-based, environmental, trade, labor and
  health economics), each scheduled or explicitly deferred in the
  coverage matrix.
- The archived `dev/` prototypes (quantity of money, DCF, stock-to-flow
  variants, Bitcoin factors) are reviewed as reference material only;
  nothing ports without passing the model definition of done.

**Acceptance criteria**
- The coverage matrix shows every formula family in the 2027 CFA Program
  outline — all three levels and all three Level III pathways —
  implemented and verified; FRM, CAIA and CIPM targets are set in the
  Phase 7 roadmap (TBD until then).
- Every batch release passes `registry.validate()`, the golden and
  property suites and the cross-surface parity suite, and generates its
  docs and web pages.
- No golden case derives from a CFA curriculum example, and a sampled
  audit of model cards finds no copied curriculum text.
- **Deployed & verified:** after each batch release, the new models
  install from PyPI, appear in production's sitemap and in the hosted MCP
  server's `search_models`, and a synthetic check runs one of them
  through the production API.
- **Security:** each new dependency passes the licence and audit review
  before its batch merges; heavy models (Monte Carlo, PDE, DSGE) declare a
  cost class and run capped in hosted mode — queued once Phase 8 adds jobs
  — proven by tests.

---

### Phase 8 — Accounts, API Plans & Monetization (Gated)

**Status:** Not started

**Goal:** Only if Gate G3 passes: add accounts, API keys, paid plans and
the paid features users have asked for, through a merchant of record —
without taking away anything that is free.

**Complexity:** High · **Risk:** High (money, PII, tax and legal) ·
**Cloud cost:** about $0–31/month at pilot scale plus usage (TBD) and
merchant-of-record fees per transaction · **Handles sensitive data:**
Yes — account PII, authentication, billing metadata (never card data)

**Phase roadmap settings** — the session that writes
`phase08-roadmap.md` (`/roadmap-phase 8`):

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Opus 5.5**       | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | High               | Max                |
|               | AA       | 47.8               | 53.6               | 57.6               |
|               | Price    | $1.61/1M           | $6.02/1M           | $67.58/1M          |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | Max                |
|               | AA       | 46.8               | 50.2               | not measured       |
|               | Price    | $3.03/1M           | $2.18/1M           | $10.00/1M*         |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6.1 Sol**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | Max                |
|               | AA       | not measured       | not measured       | 51.8               |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $5.18/1M           |

Ranked for planning, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Quality — a phase-roadmap session runs Quality (quality first). If
that column's usage pool reads `tight` or `exhausted`, run the first of its
Runner-up and Backup whose pool has headroom; on a `tight` pool an option marked
↓ (the Pick one level lower) also runs. With none, a `tight` column runs the
Cost column and an `exhausted` one its Backup.

> Settings updated 2026-10-29 (rerank): was Opus 5.5 · Max, Quality's Backup
> GPT-6 Astra · Max. Quality's Backup is now GPT-6.1 Sol · Max: roadmodel
> 0.2.100 takes the cheaper of two same-maker models the benchmarks cannot
> tell apart (AA 51.8 at $5.18/1M against 52.7 at $24.80/1M). Every Pick and
> Runner-up is unchanged; `roadmodel ladder --category planning --complexity
> high --phase` prints the same table.

> Settings updated 2026-10-25 (rerank): each column's Runner-up and Backup now come from makers other than its Pick; every Pick is unchanged.

> Settings updated 2026-10-14 (refresh): was Claude Opus 5.5 · Max, backup
> GPT-6 Astra. The backup is now GPT-6.1 Sol, the BACKUP line of `roadmodel
> score --category planning --complexity high --budget best` (0.2.84): where
> the benchmarks cannot tell two substitutes apart it takes the cheaper, and
> GPT-6 Astra costs five times as much.

> Settings updated 2026-10-18 (refresh): was Claude Opus 5.5 · Max, backup
> GPT-6.1 Sol · Intelligence Max. The single-column table becomes the full
> ladder (`roadmodel ladder --category planning --complexity high --phase`);
> Quality still runs Opus 5.5 at Max, and its backup is now GPT-6.1 Sol at
> Intelligence XHigh.

This roadmap must sequence money, identity and PII so that nothing paid
ships before its legal, tax and security gates, and must honour the gate's
evidence about what to build first. Same pick, rung and funding as Phase
1: Opus 5.5 at Max on the claude.ai Max subscription, GPT-6.1 Sol on
ChatGPT Pro 5x as backup.

#### 8.1 Gate review & decision memo

- Gate G1 carry-over (issue #68): the `pyeconomics-dev` GitHub Sponsors
  listing goes live, and `.github/FUNDING.yml` and `funding.json` regain
  their Sponsors entries. Do it as soon as the listing is approved. If
  approval is still pending at 8.1, retain issue #68 as a maintainer-owned
  external follow-up and continue the roadmap; do not invent a live listing
  or block development, releases or a phase's completion on the response.
  `verify-phase01.sh` then requires the
  listing (V11.4), because FUNDING.yml names it.

- A memo in `docs/decisions/` records the Gate G3 metrics against their
  thresholds, the pricing tests run, and the decision. On no-go, the phase
  executes the fallback track (§5 "Monetization strategy & validation
  gates") and closes.

#### 8.2 Identity & accounts

- WorkOS AuthKit (free to 1M monthly active users): hosted login, MFA,
  HttpOnly session cookies set by the API; an account page as one React
  island; self-service data export and deletion.

#### 8.3 API keys, quotas & metering

- pyeconomics-issued API keys, stored hashed in Neon Postgres and cached
  in Valkey; per-plan rate limits and quotas through the same `limits`
  layer as Phase 4; a usage ledger; overage sold as one-off packs.
- The same keys serve REST, remote MCP and the Excel add-in, so every
  limit is enforced in the API, never in a client.
- Hosted pass-through of a user's own data key, only where the vendor
  allows it (Tiingo's terms; Alpaca through OAuth with notice; any other
  vendor only with written confirmation): keys arrive per request in
  headers, live in request-scoped context, are never logged or stored —
  or sit in an encrypted per-user vault if users ask to save them — and
  never fall back to the maintainer's own key. Cache keys include the
  provider, the licence class and the tenant.

#### 8.4 Billing

- A merchant of record, because a US seller owes EU and UK VAT from the
  first sale and US sales tax under economic nexus (California taxes
  remotely accessed software from 2027). First choice: Stripe Managed
  Payments (generally available since 2026-04-22; Stripe's fees plus
  3.5%); second: Paddle (5% + 50¢). Polar is avoided — its acceptable-use
  policy bars "insights platforms" — and Paddle's and Polar's policies
  both bar investment advice and trading signals, so the chosen processor
  approves the product description in writing before any build.
- Fixed plans whose quotas the rate limiter enforces; overage sold as
  one-off packs; plans priced for computation and features, never data;
  consulting and workshops invoiced directly, outside the merchant of
  record.

#### 8.5 Paid features, in evidence order

- Candidates, ordered by the gate's evidence: saved workspaces and scenarios;
  scheduled runs with alerts on user-defined thresholds over models and macro
  series (a policy-rule gap crossing a level, say) — never buy or sell signals
  on named securities; batch runs and queued jobs (Procrastinate on Postgres);
  higher export and API limits; the Excel add-in (Office.js custom functions
  over the API, free to download from Microsoft Marketplace and unlocked by the
  account); remote MCP with OAuth (protected-resource metadata, audience-bound
  tokens, PKCE and client ID metadata documents through WorkOS); AI explanations
  of results — which never recommend a security or an allocation — with included
  credits behind the cost ledger and hard cap; priority support.

#### 8.6 Education offering (separate decision)

- A study companion only if Gate G4 shows the demand: worked examples,
  formula explorers and practice generators written in our own words,
  with no CFA mark in its name, priced against $49–$79 formula sheets.
- Enrolment in CFA Institute's Prep Provider Program only if the product
  ever needs curriculum material; its terms require password-protected
  materials and bar AI use, which suits a closed product, never the open
  docs. Counsel reviews the marketing first (Standards VII(B) and VI(C)).

#### 8.7 Paid-launch readiness gate & cutover

- Counsel reviews the terms of service, privacy policy, refund policy and
  the adviser-exclusion posture; tax handling is confirmed with the
  merchant of record; a support process exists; then the cutover is its
  own step.

**Acceptance criteria**
- The gate memo is merged with its metrics and decision.
- An automated end-to-end test in the merchant of record's sandbox runs
  purchase → entitlement → paid feature → cancellation → entitlement
  revoked.
- **Deployed & verified:** production `/version` reports the release; the
  maintainer completes a real purchase and refund in production; an MCP
  client completes OAuth against the remote server and runs a model.
- **Security:** the threat model is updated for accounts and billing;
  webhook signatures are verified; PII is encrypted at rest; export and
  deletion work end to end; the OWASP ASVS Level 2 checklist is complete
  for authentication, sessions and access control; no card data touches
  pyeconomics systems; a forced overspend proves the AI cost cap trips.

---

## 5. Cross-Cutting Concerns

### Cost projection (monthly, USD, list prices)

Phases 1–4 run on free tiers: a public GitHub repository (Actions,
CodeQL, secret scanning), Read the Docs Community, and Cloud Run's free
tier for staging. The hosted site adds cost from Phase 5; accounts and
billing add more in Phase 8. Every figure below is a list price checked on
2026-10-03, except the rows naming ADR-0013, checked on 2026-10-29;
unknowns are TBD rather than guessed.

| Service                                   | Hobby (through Phase 7, pre-revenue) | Pilot (~1k MAU, Phase 8)       | Growth (~10k MAU)               |
|-------------------------------------------|--------------------------------------|--------------------------------|---------------------------------|
| GitHub, Read the Docs (open source)       | $0                                   | $0                             | $0                              |
| Domains (.com, .org, .io, .dev)           | TBD (annual)                         | TBD                            | TBD                             |
| Cloudflare (DNS, CDN, WAF, static site)   | $0                                   | $0–5                           | $5 + usage TBD                  |
| Cloud Run (API + snapshot job)            | $0 inside the free tier; production budget $10 with alerts and a $20 spend cap (ADR-0013 decision 5) | TBD                            | TBD                             |
| Cloud Storage (snapshots; ADR-0013 decision 6) | $0 (5 GB-months Always Free; read 2026-10-29) | ~$0                    | TBD (Standard storage per GB-month + operations) |
| Upstash Redis (rate limits, cache)        | $0 (500K commands/month; read 2026-10-23) | TBD ($0.20 per 100K commands; read 2026-10-23) | from $10                        |
| Neon Postgres (Phase 8)                   | —                                    | TBD (usage-based, no minimum)  | ≈ $81 if always on; else TBD    |
| WorkOS AuthKit (Phase 8)                  | —                                    | $0                             | $0 (+$125 per enterprise SSO connection) |
| Merchant of record (Phase 8)              | —                                    | Stripe Managed Payments: Stripe fees + 3.5%; or Paddle: 5% + $0.50 per transaction | Same                |
| Sentry                                    | $0                                   | $0–26                          | $26 + overage TBD               |
| Grafana Cloud                             | $0                                   | $0                             | $0–19 + usage TBD               |
| Better Stack (uptime)                     | $0                                   | $0                             | $29                             |
| Analytics: Umami Cloud (ADR-0013 decision 13) | $0 (Hobby: 100K events a month; read 2026-10-29) | $0–20 (Pro: 1M events, API) | $20 + usage TBD             |
| Email: Buttondown (ADR-0013 decision 14)  | $9 (Basic: to 1,000 subscribers; read 2026-10-29) | $9–29 (to 5,000)    | $79–139 (10,000–20,000)         |
| **Total, fixed**                          | **≈ $9 + domains**                   | **≈ $9–80 + usage TBD**        | **≈ $250–335 + Cloud Run and usage TBD** |

Three optional costs sit outside the table: a trademark filing (about $1,000 in
USPTO fees for two classes, plus attorney fees, TBD), counsel and CPA reviews
before the paid launch (TBD), and — only if a paid study product enrols — CFA
Institute's Prep Provider fee (US$3,100 a year at the lowest revenue band in the
2027 agreement). Metered AI calls exist only from Phase 8, behind a ledger and a
hard cap whose worst case is set before launch.

### Sequencing & dependencies

```
Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ Phase 4 ──▶ Phase 5 (1.0.0 launch)
                                                    │
                     ┌──────────────────────────────┼──────────────────┐
                     ▼                              ▼                  ▼
                 Phase 6                        Phase 7          Gate G3 (evidence)
           (premium data)               (catalog batches ∥)            │
                                                                       ▼
                                                                    Phase 8
```

- Phases 1–5 are strictly sequential: each consumes the previous phase's
  contracts (registry → data bindings → generated surfaces → generated
  pages).
- Phases 1–4 run locally at $0; Phase 4's staging service stays inside
  Cloud Run's free tier.
- The irreversible cutovers each get their own readiness-gate step: the
  0.2.6 security release and the first public PyPI artifacts of 1.0 (a
  published version cannot be reused, only yanked), the Phase 5 public
  launch (5.9) and the Phase 8 paid launch (8.7).
- After 1.0.0, Phases 6 and 7 are declared independent and may run in
  parallel worktrees, as may Phase 7's domain batches. These are the only
  concurrency the "Worktree strategy" permits.
- Phase 8 starts only when Gate G3 passes (§5 "Monetization strategy &
  validation gates") and may then overlap Phases 6 and 7.

### Branch management strategy

#### Branching model

`main` is the single source of truth; the long-lived `dev` branch is
retired in Phase 1. All work happens on short-lived branches (≤ 1 week)
that merge into `main` via pull request. `main` must always be:

- Green on CI.
- Releasable: a tag on any `main` commit produces a valid package.
- Tagged per "Release & tagging" below on every release.

`legacy/0.2.x` is the one exception: it receives security fixes only,
until 0.2.x reaches end-of-life at 1.0.0.

#### Branch naming convention

| Prefix     | Purpose                          | Example                                   |
|------------|----------------------------------|-------------------------------------------|
| `feature/` | Phase work or new feature        | `feature/phase-2-model-registry`          |
| `fix/`     | Non-urgent bug fix               | `fix/duration-negative-yield`             |
| `hotfix/`  | Urgent production fix from `main`| `hotfix/hosted-licence-filter`            |
| `chore/`   | Tooling, deps, housekeeping      | `chore/uv-lock-refresh`                   |
| `docs/`    | Documentation-only changes       | `docs/fred-key-setup`                     |
| `perf/`    | Performance work                 | `perf/vectorize-bond-pricing`             |
| `release/` | Pre-release stabilisation        | `release/v1.0.0`                          |
| `model/`   | One catalog model or model batch | `model/fixed-income-oas`                  |

#### Pull request rules
1. **Scope discipline.** One PR per phase sub-section or step.
2. **PR template.** Roadmap reference, summary, test plan, screenshots for
   UI, breaking-change notes, rollback plan, licence check for any new
   dependency or data source.
3. **CI green required.** Lint, type-check, tests, the parity suite and the
   security scans (secret scan, SAST, dependency audit) all pass before
   merge. CI re-runs the same security gate the pre-commit hook ran
   locally — defense in depth, so a bypassed or skipped local hook still
   cannot land an issue on `main`.
4. **No force-push to `main`.** Allowed on personal branches only before
   review opens.
5. **Squash-merge** to `main` so each step reads as one clean commit.
6. **Conventional Commits** on the squash message, with DCO sign-off.

#### Step lifecycle

Every step / sub-section of every phase follows the same six-stage
lifecycle, in order, with no exceptions. Each stage is a hard checkpoint —
if any stage is skipped, branch protection or the next step's Stage 1 will
fail loudly, and that is the safety net. AI coding agents executing a step
MUST complete all six stages before declaring the step done.

1. **Create the branch.** Before any Read / Edit / Bash, run
   `git checkout -b <prefix>/<slug>` from a clean, up-to-date `main` (e.g.
   `feature/phase-2-model-registry`). The branch name comes from the
   roadmap step's `**Branch:**` line, or from the naming convention above
   for ad-hoc work. When the step runs in its own working tree (one of the
   three cases in "Worktree strategy" below), the equivalent is
   `git fetch origin && git worktree add -b <prefix>/<slug>
   <worktree-path> origin/main`, followed by that worktree's bootstrap.

2. **Work on the branch, and pass the security gate before every
   commit.** All commits land here. Never push to `main` directly — branch
   protection rejects it. Before each `git commit`, the local security gate
   (see §5 "Security & privacy strategy" → "Per-step security gate") must
   run and pass: secret scan clean, SAST clean, dependency audit clean, and
   no sensitive data (PII, credentials, tokens) in the diff. The gate is
   wired into the pre-commit hook and is fail-closed — a finding blocks the
   commit, so a security issue introduced while implementing this step is
   caught here, before it ever reaches the branch, the PR, or `main`.

3. **Open the PR, then mark the step.** `gh pr create --base main --head
   <branch>` with a Conventional Commits title and a body referencing the
   roadmap step and its acceptance criteria. One PR per step. Then, with
   the PR number in hand, set the step's `**Status:**` line in its phase
   roadmap to `Complete — PR #<n> (<YYYY-MM-DD>)`, commit that edit on the
   step branch (`docs: mark Phase N Step M complete`), and push. The PR
   carries its own completion mark, so the roadmap on `main` says the step
   is complete exactly when the PR merges — never before, and never by a
   later conversation reconstructing history from `git log`. The same
   commit marks the phase here: on a phase's first step its `**Status:**`
   line becomes `In progress — <phase roadmap file>`; on its final step,
   `Complete — …` with ` ✅` appended to its `### Phase` heading, together
   with its §8 summary row and the header `> **Status:**` line.

4. **Wait for green checks, then squash-merge.** Every required status
   check must report success. If the PR goes BEHIND main, refresh with
   `gh pr update-branch --rebase` — never merge `main` into the branch when
   the repo enforces linear history. Once green:

   ```sh
   gh pr merge <PR_NUMBER> --squash --delete-branch
   ```

   Merged is not done for a step that touches a deployed or published
   surface: complete the post-deploy verification named in the step's
   acceptance criteria (see "Release & deployment strategy") before Stage
   6.

5. **Retire the branch (remote + local).** The `--delete-branch` flag and
   the repo's `delete_branch_on_merge: true` setting retire the remote
   automatically. Sync local state and prune the merged branch plus any
   other `[gone]` labels:

   ```sh
   git switch main
   git pull --ff-only origin main
   git fetch --prune origin
   git branch -vv | grep ': gone]' | awk '{print $1}' \
     | xargs -r git branch -D
   ```

   If the step ran in its own working tree, remove that worktree FIRST —
   `git worktree remove <worktree-path>`, then `git worktree prune` —
   because `git branch -D` refuses to delete a branch that is still checked
   out in a worktree. Between steps, `git worktree list` shows only the
   primary tree.

6. **Dispose of every finding, declare completion, then new
   conversation.** Before declaring anything, send every finding the step
   surfaced to its destination per "Defect handling & triage" below — a
   note for a later step is edited into that step's prompt now, a bug is
   fixed or is an issue number, a judgement call in the diff is explained
   in the PR body. A finding that is only described is not disposed of,
   and counts as an unmet acceptance criterion. Only once the PR is merged
   — and `main` therefore carries the step's `Complete` Status line —
   every acceptance criterion is affirmatively met, and every finding has a
   destination, end the final response with the verbatim line "Step N is
   complete. You can now move on to Step N+1." (or, on the phase's last
   step, "Phase N is complete. You can now move on to Phase N+1."). That
   line is the LAST line of the response. Nothing follows it — no
   "Follow-ups (non-blocking)", "Notes", "Next", or suggested
   improvements. If any criterion is unmet or any finding has no
   destination, say plainly that the step is NOT complete, name what is
   outstanding, and withhold the line. "Done" means done. Then, for
   phase-boundary hygiene, the operator closes the current Claude Code /
   Codex session and opens a fresh one before starting the next step. The
   new conversation begins again at Stage 1 with the next step's
   `**Branch:**` line driving the `git checkout -b` command. No work
   straddles two steps.

#### Worktree strategy

The default is one working tree — the primary checkout — and one step in
flight at a time; the six-stage lifecycle assumes it. A second working
tree is created only with `git worktree add` (never a second clone, which
would not share branches, hooks, or config), and only in these cases:

| Case                         | Rule                                                                 |
|------------------------------|----------------------------------------------------------------------|
| Hotfix interrupting a step   | A Critical/High finding (see "Vulnerability handling") gets its `hotfix/` branch in a worktree cut from `origin/main`. The in-flight step's tree is left untouched — nothing stashed, nothing half-committed. |
| Declared-independent steps   | Only steps the "Sequencing & dependencies" diagram (or a phase roadmap's Execution Order) draws in parallel — chiefly Phase 6 against Phase 7, and Phase 7's domain batches. Each gets its own worktree AND its own conversation; each branches from the same `origin/main` and rebases before merge. Undeclared parallelism is a lifecycle violation, not a shortcut. |
| Subagent isolation in a step | Multi-agent runs inside one step (an agent harness's worktree-isolated subagents) work in throwaway worktrees. Results merge back into the step branch locally; only the step branch opens a PR, and every subagent worktree is removed before Stage 3. |

Rules that apply to every worktree:

1. **Location.** This project uses a git-ignored `.worktrees/<branch-slug>/`
   inside the repo. Agent tooling that creates its own worktrees keeps its
   own location. Never nest a worktree under a tracked path.
2. **Bootstrap before use.** A new worktree has NONE of the primary tree's
   untracked state: the virtualenv, `node_modules`, local env files, build
   caches. Run `uv sync --locked` (and `npm ci` in `web/` once it exists)
   inside the worktree before any test or build. Never point a worktree at
   the primary tree's environment: tests in the worktree would silently
   import the primary tree's source.
3. **Hooks and config carry over.** `core.hooksPath` and the rest of the
   repo config are per-repository, so the pre-commit security gate and
   branch guard run in every worktree without setup. Confirm once per
   worktree with `git config core.hooksPath`.
4. **One conversation, one worktree.** Stage 6 still holds: each step (and
   each hotfix) is its own conversation, and a conversation never touches
   more than one worktree. Parallel steps run as parallel conversations,
   never as one conversation switching trees.
5. **Merge from the primary tree.** Run the Stage 4 merge command from the
   primary checkout. Inside a linked worktree, `--delete-branch` tries to
   check out `main` locally and fails (it is checked out in the primary
   tree); the merge itself still lands, but the local cleanup is left to
   Stage 5.
6. **Retire with the branch.** No worktree outlives its PR. Stage 5 removes
   it (`git worktree remove <path>`, then `git worktree prune`) BEFORE the
   branch prune, because `git branch -D` refuses a branch that is still
   checked out in a worktree. Between steps, `git worktree list` shows only
   the primary tree.

#### Release & tagging

Tags are PEP 440 versions that must equal the version in `pyproject.toml`;
the release workflow refuses any other tag (1.2). Under Semantic
Versioning, 0.x was initial development and 1.0.0 is the first stable
public API, so any breaking change after it requires 2.0.0. Pre-release
versions never install by default (`pip` needs `--pre`), which keeps 0.2.x
users safe until 1.0.0 ships.

| Milestone tag           | Marker                                                         |
|-------------------------|----------------------------------------------------------------|
| `v1.0.0.dev1`           | Phase 1 — skeleton and publishing pipeline proven on TestPyPI  |
| `v1.0.0a1`              | Phase 2 — model engine and core catalog (PyPI pre-release)     |
| `v1.0.0a2`              | Phase 3 — data platform and monetary-policy suite              |
| `v1.0.0b1`              | Phase 4 — CLI, REST API, MCP server and exports                |
| `v1.0.0rc1`             | Phase 5 — release candidate, run through the launch gate       |
| `v1.0.0`                | Phase 5 — public launch: stable on PyPI, hosted site live      |
| `v1.1.0` (expected)     | Phase 6 — Bloomberg and bring-your-own-key providers           |
| `v1.x.0`, one per batch | Phase 7 — catalog batches, in merge order                      |
| `v1.y.0` (expected)     | Phase 8 — client support for API keys and remote MCP; paid features ship from the private hosted repository (ADR-0004) |

Phases 6 and 7 run in parallel, so their minor numbers follow merge order;
the table records intent, not fixed numbers.

### Release & deployment strategy

**Merged is not deployed, and deployed is not released.** Three distinct
events with three distinct triggers. Every surface this project ships
names all three, so no step can mistake "the PR merged" for "the change is
live".

#### Deployable surfaces

| Surface                         | Environments                     | Deploy trigger                                                        | "Released" means                                   | Verify with                                                     |
|---------------------------------|----------------------------------|-----------------------------------------------------------------------|----------------------------------------------------|-----------------------------------------------------------------|
| PyPI packages (`pyeconomics`, `pyeconomics-app`) | TestPyPI, PyPI    | `v*` tag on `main` → release workflow, behind the protected `pypi` environment | The version installs from PyPI with attestations | Fresh-venv install, `pyeconomics --version`, smoke run          |
| Documentation                   | Read the Docs `latest`, `stable` | Merge to `main` builds `latest`; a release tag builds `stable`        | `stable` serves the tagged version                 | Version banner; the docs doctest job                            |
| Hosted web app (static)         | staging (the preview), production | A pull request builds and tests the site without deploying; merge to `main` deploys staging on `staging.pyeconomics.dev` behind Cloudflare Access; a release tag deploys production (Phase 5+; ADR-0013 decision 4) | Production serves the release's build        | `/version.json` reports the SHA; synthetic page check           |
| Hosted API (Cloud Run)          | staging, production              | Merge to `main` deploys staging; a release tag deploys production behind the protected `production` environment | `/version` reports the release | Synthetic model run — with a Cloudflare Access service token on staging |
| Snapshot job (Cloud Run job)    | staging, production              | Ships with the API image; Cloud Scheduler runs it daily (ADR-0013 decision 6) | The next scheduled run succeeds                    | Heartbeat check and per-dataset as-of dates                     |
| MCP server                      | PyPI (stdio), hosted endpoint, MCP Registry | Ships with the package and the API; registry entry updated per release | The registry lists the release            | MCP Inspector against the hosted endpoint                       |
| Database (Phase 8)              | staging, production              | The deploy job applies migrations before the new revision takes traffic | Schema version matches the code                  | Migration status query                                          |
| Excel add-in (Phase 8)          | Microsoft Marketplace            | Manual submission per release                                         | The marketplace lists the version                  | Install and run a function smoke test                           |

A change that lands in a surface whose trigger is not "merge to `main`"
needs its own step or explicit sub-step for the release — it is never
assumed to have happened.

#### Promotion path and cutovers

- Changes move staging → production; promotion is gated on CI green plus
  the phase's verification checks passing against staging.
- **Staged rollout.** A change that spans layers ships data first, then
  the API, then the static site, each verified before the next. Never all
  layers in one push: a failure in layer three with layers one and two
  unverified has no clean rollback.
- **Readiness gate before an irreversible cutover.** The 0.2.6 security
  release, the first stable 1.0.0 upload, the public launch's DNS cut and
  the paid launch each get an explicit readiness-gate step with a
  checklist (access control, indexing and robots, monitoring in place,
  rollback rehearsed, attribution and legal), separate from the cutover
  step itself. Going live is a decision, not a side effect of a merge.

#### Configuration and secrets provisioning

- A step that introduces a required environment variable or secret
  verifies at kickoff — before writing code that fails closed without it —
  that the value exists in every target environment (Secret Manager for
  Cloud Run, GitHub environments for workflows).
- A shared secret is proven by an **authenticated round-trip**: a real
  request from one system to the other that uses it. Listing names or
  hitting an unauthenticated health endpoint proves nothing.
- Sensitive values never transit chat or a PR. The operator gets a command
  to run, never a value to paste back.

#### Data and schema migrations

- There is no database before Phase 8; hosted data lives in versioned
  snapshots — gzip-compressed canonical JSON in the cache's frame codec,
  validated on read, one object per provider under each run's id, never
  overwritten, with `current.json` naming the run served — in a private
  Cloud Storage bucket, which the snapshot job writes and the API reads
  through a read-only volume mount (ADR-0013 decision 6).
- From Phase 8, migrations are part of the deploy path: applied by the
  deploy job in expand → deploy code → contract order, rehearsed on a Neon
  branch, and each with a written rollback. A merged migration that is not
  yet applied to production is a tracked gap, not a done step.

#### Post-deploy verification

A step that touches a deployed or published surface is not done at merge.
Its acceptance criteria include a check in the target environment, which
Stage 4 of the step lifecycle runs:

- The surface's version endpoint or registry listing reports the expected
  build, and
- The changed behaviour is exercised end to end through a hands-off recipe
  the roadmap names (a fresh-venv install, a synthetic model run, a
  Cloudflare Access service token, an MCP Inspector session) rather than an
  ad-hoc click-through.

Where a PR that references an issue auto-closes it on merge, verification
is what earns the close: if a gap remains after the environment check,
reopen the issue or open a follow-up.

#### Rollback

| Surface             | Rollback                                                          | Time to execute         |
|---------------------|-------------------------------------------------------------------|-------------------------|
| PyPI package        | Yank the version; publish a fixed patch; consumers pin            | Minutes to yank; patch TBD |
| Documentation       | Rebuild the previous version or revert the docs commit           | Minutes                 |
| Static site         | Redeploy the previous Cloudflare deployment                       | Minutes                 |
| API                 | Route all traffic to the previous Cloud Run revision             | Minutes                 |
| Snapshot job        | Re-run the previous image, or point `current.json` back at the last good run; each run's snapshots are kept under its own id in Cloud Storage (ADR-0013 decision 6) | Minutes |
| Database (Phase 8)  | Down-migration, or Neon point-in-time restore                     | TBD                     |
| Excel add-in        | Resubmit the previous manifest                                    | TBD (marketplace review) |

Every deploy has a named rollback the operator can run in minutes; the PR
body's "rollback plan" field names which one. Reversible behaviour changes
ship behind a configuration switch, so rollback is a config change rather
than a redeploy.

#### Versioning

Releases are tagged per "Release & tagging" above. A downstream project
that pins pyeconomics declares a minimum version and bumps it in its own
step when a change must reach it — the bump is its deploy trigger, not
pyeconomics' merge. Model versions are independent of the package
version: a model's own version bumps whenever its outputs change, and the
manifest records both.

### Security & privacy strategy

pyeconomics touches credentials from its first line of code (data-provider
API keys), runs a public service from Phase 5, and holds accounts and
payment metadata from Phase 8. Security is woven into every step: an issue
introduced while implementing a step is caught before the commit, the push
and the merge.

#### Data classification

| Data class                     | Present?          | Handling requirement                                  |
|--------------------------------|-------------------|-------------------------------------------------------|
| Provider API keys (FRED, BLS, BEA, BYOK commercial keys) | Yes — Phase 1+ | User's machine only: argument, environment or OS keyring; never logged, never in manifests, caches, exceptions or exports; never sent to the hosted service. |
| Hosted service secrets (snapshot-job keys, Sentry DSN, signing keys) | Yes — Phase 4+ | Google Secret Manager only; never in source, images, env files or client bundles; rotated on exposure. |
| PyPI publishing credentials    | Yes — Phase 1+    | Replaced by Trusted Publishing (OIDC); no stored token exists. |
| Licensed market data (Bloomberg, LSEG, BYOK vendors) | Yes — Phase 6+ | Stays on the licensed machine; never cached in shared locations by default, never sent to the hosted service, never committed (including notebook outputs and test fixtures). |
| User uploads (CSV/XLSX)        | Yes — Phase 5+    | Parsed in the browser; never uploaded to or stored by the hosted service. |
| Waitlist / feedback emails (PII) | Yes — Phase 5+  | One processor, least-privilege access, deletion on request; never in logs or analytics. |
| Accounts, auth, usage records (PII) | Phase 8 only | Encrypted in transit and at rest; managed auth provider; MFA available; data export and deletion. |
| Payment data                   | Phase 8 only      | Delegated to a merchant of record; card data never touches pyeconomics systems. |
| Analytics                      | Yes — Phase 5+    | Cookie-less, aggregate, no cross-site tracking; disclosed in the privacy policy. |
| Health / regulated data        | No                | — |

#### Threat model (one-paragraph)

The assets are users' provider keys, the hosted service's secrets and
cloud budget, licensed data, the integrity of published model outputs, the
PyPI package and, from Phase 8, account PII and billing state. The trust
boundaries are the user's machine versus the hosted service (§3),
Cloudflare at the edge, and the CI/CD pipeline that publishes to PyPI and
deploys to Cloud Run. Realistic adversaries are an external attacker
probing the public API, a compromised dependency or GitHub Action, a
typosquatted lookalike package, a prompt-injected AI assistant calling the
MCP server, and a leaked coding-agent transcript. The design must resist:
(1) a key leaking through logs, errors, manifests or exports — the exact
0.2.x bug; (2) cost exhaustion of the hosted service through expensive
inputs or request floods; (3) unsafe deserialization or server-side
request forgery through data paths; (4) licensed data escaping to the
hosted service; (5) a malicious release reaching PyPI; (6) CSV/Excel
formula injection in exports; (7) MCP tool output steering an assistant.

#### Per-step security gate

This is the core control. Every step of every phase runs the SAME local,
fail-closed security gate before any commit, so a security issue
introduced while implementing a step is caught in development — before it
reaches the branch, the PR, or `main`. A coding agent handed a phase step
treats this gate as part of the step's definition of done, exactly like
tests.

The gate is wired into the repo's pre-commit hook (1.3) so it runs
automatically, and it is re-run in CI so a bypassed hook cannot land an
issue on `main`. It has four checks; all must be clean:

| Check                 | What it catches                                   | Tooling in this repo                                   |
|-----------------------|---------------------------------------------------|--------------------------------------------------------|
| Secret / PII scan     | Committed credentials, tokens, keys, real PII, notebook outputs carrying either | gitleaks                                 |
| SAST (static a.)      | Injection, unsafe deserialization (`pickle`, `yaml.load`), `eval`, path traversal, SSRF, credential logging | bandit, semgrep (project rules), `eslint-plugin-security` in `web/` |
| Dependency audit      | Known-vulnerable, yanked or typo-squatted dependencies | pip-audit or osv-scanner on `uv.lock`; `npm audit --audit-level=high` in `web/` |
| Sensitive-data review | Keys in logs or manifests, licensed data in fixtures, secrets in client bundles, over-broad scopes | PR-template checklist against the table above |

Rules for the gate:

1. **Fail-closed.** Any finding blocks the commit. The bypass (an
   environment variable) is for genuine emergencies only, and every use is
   recorded in the PR body with a justification.
2. **Runs per commit, not per phase.** Because it is a pre-commit hook,
   the developer or agent cannot defer security to "the end" — the
   smallest unit of work is already gated.
3. **Mirrored in CI.** The same four checks run as required status checks,
   so the merge is blocked even if the local hook was skipped (PR rule 3).
4. **Owned by acceptance criteria.** Every phase's acceptance criteria name
   the concrete security check for its surface; the phase is not done
   until the gate is green on its work.
5. **The pipeline is a trust boundary.** Third-party actions are pinned to
   a commit SHA; each workflow gets the minimum `permissions:`; no secret
   is exposed to workflows triggered by untrusted pull requests; publish
   and deploy jobs sit behind protected environments; PyPI publishing and
   Google Cloud deploys use short-lived OIDC credentials, never stored
   tokens. A change to a workflow file is a security-relevant diff and gets
   the sensitive-data review.

#### Security controls by layer

| Layer               | Control                                                       |
|---------------------|--------------------------------------------------------------|
| Identity / auth     | Phases 4–7: anonymous hosted access with per-IP limits, no accounts; staging behind Cloudflare Access. Phase 8: managed auth, MFA available, short-lived sessions, least-privilege admin roles. |
| Transport           | TLS everywhere via Cloudflare; HSTS; strict CSP and security headers on the web app; local mode binds to 127.0.0.1 only. |
| Data at rest        | Google-managed encryption for object storage and (Phase 8) Postgres; local caches in the user's cache directory with user-only permissions. |
| Secrets             | Google Secret Manager for the service; OS keyring for users; never in source, images or `.env` files committed anywhere. |
| Network / edge      | Cloudflare WAF and rate limits; Cloud Run max instances capped; request body, array-length and compute-time limits per model; no endpoint fetches a user-supplied URL. |
| Dependencies        | `uv.lock` and `package-lock.json` committed; weekly automated updates; audit in the gate; new dependencies need a licence check. |
| CI/CD pipeline      | SHA-pinned actions; least-privilege `permissions:`; Trusted Publishing with attestations; OIDC to Google Cloud; protected `pypi` and `production` environments; zizmor on every workflow change. |
| Logging / audit     | A redaction filter on every logger; structured logs without PII or secrets; tests that fail if a key appears in logs, errors, manifests or exports. |
| Exports             | CSV/XLSX cells beginning with `=`, `+`, `-` or `@` are escaped; manifests contain no credentials. |
| MCP                 | Tools return data, never instructions; no tool executes code or fetches arbitrary URLs; hosted MCP is read-only until Phase 8 adds OAuth. |
| Incident response   | `SECURITY.md` disclosure path; GitHub security advisories; key-rotation runbook; PyPI yank procedure. |

#### Vulnerability handling

Security findings — from the gate, CI, a scanner, or a report — follow the
same discover → triage → track → fix → verify loop as any other defect,
but jump the queue by severity: Critical/High are fixed on a `hotfix/` or
`fix/` branch before new feature work continues; Medium/Low are tracked as
issues with an owner and a due date. Never silence a finding without a
recorded justification. A vulnerability in a released version gets a
GitHub security advisory and a patched release; a compromised release is
yanked from PyPI.

### Defect handling & triage

Executing a step surfaces findings that are not the step: a failing
adjacent test, a wrong assumption in the step's own spec, a gap an earlier
step left, a product question, a lesson about the process. Every finding is
classified before it is acted on, and each class has exactly one
destination. Never conflate classes in a single fix.

| Class                  | Definition                                                                                   | Destination                                                                                                            |
|------------------------|----------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| Spec rot               | The step's own prompt or spec was wrong (wrong API, wrong threshold, a prerequisite claimed but never done) | Edit the step's `<task>` block in the phase roadmap now, before the next conversation.                                  |
| Upstream gap           | An earlier step missed something that belonged to it                                         | Patch the earlier step's prompt so a re-run does not repeat it; add it to the phase's carry-over checklist.             |
| Implementation bug     | The code is wrong                                                                            | If it blocks this step's acceptance criteria, fix it in this step. Otherwise open an issue; fix on its own branch in a fresh conversation. |
| Model error            | A published model returns a wrong number (formula, convention or golden value)               | Treated as a High defect: fix on a `fix/` branch, add the failing case as a golden test, and record it in the public errata. |
| Architectural question | A broader product or design decision was exposed                                             | Open an issue for a future phase. Never fold it into the immediate fix.                                                |
| Process improvement    | A lesson about how the work is done                                                          | Record it where the next conversation will read it (this roadmap, `CLAUDE.md` / `AGENTS.md`). If it is a rule, make it a check. |
| Security finding       | Any of the four gate checks, or a threat-model abuse case                                    | Jumps the queue by severity — see "Vulnerability handling".                                                            |

Rules:

1. **Scope discipline.** A step's PR contains the step plus only the
   blocking fixes from the table. Everything else is tracked, not smuggled
   in. The PR body lists the issues it opened.
2. **Track before you defer.** A deferred finding exists as an issue with a
   class label, an owner, and the phase or step that will absorb it, before
   the current step is declared complete. "We'll remember" is not tracking.
3. **Verify the close.** A PR that references an issue with a closing
   keyword closes it on merge — the first such PR wins, even if it fixed
   only part. Verification in the target environment is what earns the
   close; reopen or open a follow-up if a gap remains.
4. **Prevent the class, not the instance.** Every defect that escaped a
   gate gets a guard in the same or the next step — a test, a lint rule, a
   CI check, a verify-script check — so the class cannot recur. The phase's
   QA findings doc records the finding and its guard together.
5. **Dispose before you declare.** The table above is the only place a
   finding may go. A step is not declared complete while any finding is
   merely described — in the chat, in a "follow-ups" note, in a "worth a
   glance" aside — rather than sitting at its destination. The completion
   line (Stage 6) is the last line of the response; a finding that would
   need to follow it means the step is not done yet.

### Operations & observability strategy

The library and CLI have no runtime footprint, but from Phase 4 the
project runs a service, a scheduled snapshot job and a published package
that others depend on. Every runtime surface is observable before it is
considered live, and every signal has an owner and a response.

#### Health signals

| Surface                    | Signal                                                   | Checked by                                       | Alerts          |
|----------------------------|----------------------------------------------------------|--------------------------------------------------|-----------------|
| Hosted API (Cloud Run)     | `/healthz` and `/version` (package version + git SHA); error rate; p95 latency | uptime probe every 5 min + post-deploy check     | Maintainer (email + push) |
| Hosted web app             | Synthetic run of one model per domain; Core Web Vitals; JS error rate | scheduled synthetic check; error tracker         | Maintainer      |
| Snapshot job               | Last successful run within its cadence; rows and dates per dataset | heartbeat check that fails loudly when stale      | Maintainer      |
| Free-source providers      | Weekly live contract run against real APIs               | scheduled CI workflow                            | Maintainer (issue opened automatically) |
| PyPI package               | Fresh install + smoke command after every release        | release workflow's final job                     | Maintainer      |
| Cloud spend                | Spend vs. monthly budget                                 | Google Cloud budget alerts at 50 / 90 / 100%     | Maintainer      |
| Metered AI calls (Phase 8) | Per-call cost ledger vs. hard cap                        | daily ledger check + kill switch                 | Maintainer      |

#### Rules

1. **Version + health on every deployed surface.** The health endpoint
   reports the running version; post-deploy verification (see "Release &
   deployment strategy") reads it, and so does the uptime check.
2. **Scheduled automation has a heartbeat.** The snapshot job and the
   weekly provider run each have an alarm that fires when they have NOT
   succeeded within their cadence. Automation that opens issues has a named
   owner (the maintainer) and a staleness policy: the newest supersedes
   older ones, which are closed.
3. **Metered dependencies have a ledger and a cap.** Any pay-per-use
   dependency (an LLM API in Phase 8, a metered data feed) records per-call
   cost to an audit ledger, enforces a hard cap with a kill switch, and
   shows the worst-case arithmetic in the cost projection above.
4. **Logs are safe by construction.** No PII or secrets in logs (see
   "Security controls by layer"); structured fields so an incident can be
   queried, not grepped.
5. **Every alert has a runbook.** An alert with no owner or no runbook is
   noise; delete it or complete it.
6. **Degrade, don't fail.** When an upstream source is down, the hosted
   service serves the last snapshot with its as-of date shown, rather than
   an error.

#### Runbooks

| Scenario                          | Runbook                                                                  |
|-----------------------------------|--------------------------------------------------------------------------|
| Deploy regressed                  | Roll back per "Release & deployment strategy"; open a `fix/` issue.      |
| Snapshot job silent               | Check the run log; re-run manually; fix the trigger; the site keeps serving the last good snapshot with its date. |
| Secret leaked                     | Rotate in Secret Manager, redeploy, prove with an authenticated round-trip; advisory if user-facing. |
| User reports a leaked provider key| Advise rotation at the provider; if pyeconomics leaked it, ship a patched release and an advisory. |
| Upstream source down or changed   | Degrade to snapshot; open an issue; update the provider's contract fixtures. |
| Data terms changed                | Reclassify the source (§5 "Data licensing policy"); purge hosted snapshots if it is no longer hosted-safe. |
| Bad release on PyPI               | Yank the version, publish a fixed patch, post an advisory or changelog note. |
| Model error reported              | Reproduce as a failing golden case; fix; publish errata (§5 "Model quality & governance"). |
| Cost spike                        | Lower Cloud Run max instances, tighten Cloudflare rate limits, inspect for abuse. |

**Acceptance.** A phase that adds a runtime surface is not done until the
surface's health signal and its alarm exist and have been seen to fire
once (or a synthetic failure was injected to prove they do). Put that in
the phase's acceptance criteria.

### Model quality & governance

The catalog is the product, so a model has its own definition of done,
enforced by `registry.validate()` and the PR template.

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

Evidence status tells users how much to trust a model's premise, separate
from whether the code is correct:

| Status        | Meaning                                                    | Example                         |
|---------------|------------------------------------------------------------|---------------------------------|
| `standard`    | Textbook consensus                                         | Bond duration, CAPM formula     |
| `practitioner`| Widely used rule of thumb or convention                    | Rule of 72, Fed-model yield gap |
| `contested`   | Active academic or policy debate                           | r-star estimates                |
| `rejected`    | Failed out of sample; kept for history and teaching        | Bitcoin stock-to-flow           |
| `historical`  | Superseded methodology kept for reproducibility            | Treasury's pre-December-2021 curve method |

### Data licensing policy

Every data source is classified before its provider merges, from the
provider's own terms page; the terms URL is stored with the provider and
re-checked yearly and whenever the source changes. This is engineering
policy, not legal advice — counsel reviews it before the Phase 5 launch.

| Class           | Meaning                                                        | Library, CLI, local app             | Hosted service                                   | Examples                                       |
|-----------------|----------------------------------------------------------------|-------------------------------------|--------------------------------------------------|------------------------------------------------|
| `hosted-safe`   | Terms allow display by a third-party service, with attribution | Yes                                 | Yes — snapshot, display, export with attribution | BLS, BEA, Census, Treasury, Fed Board, NY Fed, SEC EDGAR, World Bank (CC BY series), OECD, ECB, BIS, Eurostat, OpenFIGI |
| `library-only`  | Personal-use, non-commercial, no-caching or scraped terms      | Yes, under the user's own acceptance of the terms | Never, unless the owner grants written permission | FRED and ALFRED, Ken French, Shiller, AQR, JKP, Philadelphia, Atlanta and Cleveland Fed products, Cboe VIX, IMF, yfinance, Coin Metrics, DBnomics |
| `byok`          | The user's own paid subscription                               | Yes, on the user's key              | Never — except, from Phase 8, a per-request pass-through the vendor allows (Tiingo today) | Phase 6 commercial APIs |
| `premium-local` | Licensed to a machine or seat                                  | Yes, on the licensed machine only   | Never                                            | Bloomberg Desktop API, LSEG Workspace          |
| `user-supplied` | The user's own files                                           | Yes                                 | Processed in memory for one run; never stored    | CSV/XLSX uploads                               |

Rules:

1. **Enforced in code.** The class is metadata on every provider — and on
   every series where one source mixes classes, gated by FRED's copyright
   tags, World Bank `License_Type` and Eurostat's exceptions — and hosted
   mode refuses anything but `hosted-safe` and `user-supplied`.
2. **Attribution travels with the data.** Every chart, table, export and
   manifest carries the source's attribution and terms link, including
   FRED's required notice: "This product uses the FRED® API but is not
   endorsed or certified by the Federal Reserve Bank of St. Louis."
3. **Originators, not aggregators.** The hosted service snapshots public
   series from the agency that publishes them, never through FRED or
   DBnomics, and reads those snapshots instead of calling providers per
   request — which also keeps it inside every provider's rate limits.
   Relaying a user's own key through the hosted service is still
   redistribution, so it never happens.
4. **Caching follows the terms.** A source whose terms forbid storage is
   fetched live and never written to disk.
5. **Feed models, don't clone providers.** The hosted data explorer exists
   to feed models; it never replicates a provider's own product (FRED's API
   terms forbid replicating its essential user experience).
6. **Charge for compute and features, never for raw data.** BIS forbids
   any added charge for its data; ECB and IMF data in a paid product need
   a "free of charge from the source" notice.
7. **A terms change is a High defect.** Reclassify the source, purge any
   hosted snapshot it no longer allows, and record it in the changelog.

### Legal & brand guardrails

Engineering rules, not legal advice; counsel reviews them before the Phase
5 launch and again before the Phase 8 paid launch.

#### CFA Institute marks and content

| Do                                                                                                  | Don't                                                                                                    |
|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| Say "implements formulas commonly covered in the CFA® Program curriculum", with ® on first use and the mark used as an adjective | Put "CFA" in any package, module, command, repository, product, domain, subdomain or social-handle name |
| Carry this notice on the README, docs, PyPI page and web app: "CFA® and Chartered Financial Analyst® are trademarks owned by CFA Institute. pyeconomics is not affiliated with, endorsed by, or a Prep Provider of CFA Institute." | Use "official", "approved", "endorsed", "certified" or "Prep Provider"; use the CFA Institute logo or badges; make pass claims |
| Cite each formula's originators (Macaulay 1938; Black and Scholes 1973; Taylor 1993) and take golden values from independent sources | Copy learning outcome statements, readings, end-of-reading questions, mock-exam or Practical Skills Module content, or curriculum worked examples |
| Keep syllabus mappings as factual tags that link to cfainstitute.org                                 | Position anything as exam prep (question banks, "pass Level I") without enrolling as a Prep Provider     |
| Sign as "Nathan Ramos, CFA"                                                                          | Imply the designation guarantees accuracy ("CFA-grade") — Standard VII(B)                                |

- The Prep Provider Program is voluntary and does not apply to a model
  library. Its 2027 agreement charges from US$3,100 a year and requires
  password-protected materials and limits on AI use — incompatible with
  open documentation — so it is considered only for a separate paid study
  product (8.6).
- Before using the mark in a URL path, ask CFA Institute's legal team;
  until then, syllabus filters use neutral slugs.
- The same factual-reference, attribution and non-endorsement pattern
  applies to GARP (FRM®), CAIA®, CMT® and CQF, after checking each body's
  own usage rules.

#### Data terms

- FRED: library-only. Its terms bar caching, storing in a database,
  redistributing and ML training, and allow commercial use only internally or in
  client reports; hosted use needs the St. Louis Fed's written consent. No
  "FRED" in a hostname; 14,128 series also need their owner's permission before
  any non-personal use; ICE BofA series are cut to three years and S&P series to
  ten; Moody's series count as pre-approval whatever their label says. Whether
  FRED content may reach an LLM at inference time (the AI narrative, a user's
  assistant through MCP) is a counsel question; until answered the docs warn
  users and hosted AI features use hosted-safe data only.
- Ken French Data Library: copyright Eugene F. Fama and Kenneth R. French;
  fetched at runtime with attribution and never bundled in a wheel.
- Yahoo data through yfinance is for personal use only: `library-only`.
- Coin Metrics community data is CC BY-NC 4.0: `library-only`, never part
  of a paid feature.
- IMF: commercial reuse and automated bulk download need the IMF's
  explicit permission — library-only until granted.
- Philadelphia, Atlanta and Cleveland Fed products, Cboe VIX history,
  AQR, JKP (CC BY-NC) and Hou-Xue-Zhang data: research or non-commercial
  terms — library-only.
- Golden-test fixtures keep only the handful of published values a test
  needs, each cited; no dataset is mirrored into the repository.

#### Required notices

| Source        | Notice wherever its data appears                                                                                         |
|---------------|--------------------------------------------------------------------------------------------------------------------------|
| FRED          | "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis." (local surfaces) |
| BEA           | "This product uses the Bureau of Economic Analysis (BEA) Data API but is not endorsed or certified by BEA."               |
| Census        | "This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau."                     |
| BLS           | BLS's statement that it cannot vouch for data or analyses after retrieval, plus the access date                         |
| NY Fed        | "© [year] Federal Reserve Bank of New York" with its terms reference; reference rates carry their own terms line        |
| ECB           | In a paid tier: the information may be obtained free of charge from the ECB — before payment and on each access         |
| World Bank, OECD, Eurostat, IMF | Each source's prescribed source line, with the dataset name and access date                            |
| Everything    | "As is; not investment advice"                                                                                           |

#### Dependency licences

- Runtime dependencies are permissive only — MIT, BSD, Apache-2.0, ISC,
  NCSA, PSF — enforced by the licence check in the security gate; a
  `NOTICE` file carries their attributions.
- Excluded: FinancePy (GPL-3.0), rateslib (source-available,
  non-commercial), getfactormodels, the DBnomics client, OpenBB's AGPL
  provider plugins and AGPL MCP servers (the AGPL network clause would
  reach the hosted service); `full_fred` (conflicting licence metadata).
- `blpapi` is proprietary: users install it from Bloomberg's own index;
  pyeconomics never redistributes it and never names that index in its
  published metadata.

#### pyeconomics' own licence, name and posture

- **Licence.** Apache-2.0 for the public repository from 1.0; hosted-only
  paid features in a private repository (ADR-0004).
- **Name.** A PyPI name is not a trademark, and "PYECONOMICS" may be
  refused as merely descriptive; ADR-0009 governs the clearance search,
  any filing, and a possible coined brand for the hosted product. The
  "Py" prefix is not restricted by the PSF's trademark policy.
- **Adviser posture.** pyeconomics stays a publisher of impersonal,
  general tools — the publisher's exclusion as read in Lowe v. SEC —
  rather than an investment or commodity-trading adviser:

| Lower risk (build freely)                                       | Higher risk (counsel first)                                                  |
|-----------------------------------------------------------------|------------------------------------------------------------------------------|
| Formula calculators, pricing models, regressions, charts        | Buy, sell or hold signals, or pushed alerts on named securities or futures   |
| Simulations of user-defined rules, with hypothetical-results legends | Allocations generated from a user's risk profile; "recommended" portfolios |
| Screeners the user parameterizes; the same content for every user | Auto-trading or broker routing; an assistant answering "what should I buy" |

- **Disclaimers** on every surface: educational and informational use
  only; not personal advice; not registered with any regulator; provided
  as is, with a liability cap; data may be delayed or wrong; a
  hypothetical-results legend wherever simulated performance appears
  (FINRA Rule 2214's wording as the template; CFTC Rule 4.41's legend for
  futures); the data notices above; the CFA marks notice.
- **Affiliate disclosure.** Every referral link is labelled as one (FTC
  endorsement guides; Standard VI(C)).
- **Privacy.** GDPR applies to EU users whether or not they pay: a privacy
  policy, data-processing agreements with every processor, cookie-less
  analytics so no consent banner is needed, and encryption for any stored
  key; whether an EU or UK representative is required is a counsel
  question.
- **Tax.** Handled through the merchant of record (Phase 8); a CPA
  confirms nexus and VAT before the paid launch.
- **Counsel and CPA checklist** before the paid launch: securities and
  CFTC review of any alert, model-portfolio, risk-profile, AI Q&A or
  futures-backtest feature and of EU and UK marketing; data-licensing
  approvals (FRED commercial use, display rights, Bloomberg); the
  trademark strategy and CFA-mark usage; final licence and contributor
  texts; privacy representation and processor agreements; tax nexus, VAT
  and the merchant of record; an entity and insurance.

### Monetization strategy & validation gates

Distribution comes before revenue. pyeconomics starts from about 25–30
downloads a month and 11 stars, and the strongest comparable shows the
risk: OpenBB — 73.8k stars, venture-backed — said in August 2026 it
"couldn't find the product-market fit needed to build a sustainable
business around this vision within the time we had" and open-sourced its
whole suite. In this niche, money comes from
gated professional tiers, freemium SaaS split by personal and commercial
use, per-seat Excel add-ins and study products; donations alone pay little.

Principles:

1. **The open core is the distribution engine.** The library, CLI, local
   app and MCP server stay free and open source; nothing free today becomes
   paid later.
2. **Charge for computation, convenience and support — never for raw
   data.** Licensed data is never resold, BIS data is never paywalled, and
   ECB and IMF data in a paid product carry their "free from the source"
   notices.
3. **MCP is distribution, not revenue.** OpenAI bars selling subscriptions
   inside plugins, and Anthropic's directory has no billing. The MCP server
   stays free; paid features unlock through OAuth to an account billed on
   the web.
4. **Search traffic alone is fragile.** AI answers are eroding
   documentation traffic (Tailwind reports docs visits down about 40% and
   revenue down about 80% since early 2023), so assistants calling
   pyeconomics through MCP matter as much as ranking pages.
5. **Impersonal by design.** No buy/sell signals, no personalised
   allocations, no auto-trading — the line that keeps pyeconomics a
   publisher rather than an adviser (§5 "Legal & brand guardrails"), and
   that payment processors also draw.

#### Revenue lines, in gate order

| Line                     | What is sold                                                                    | 2026 price anchors                                              | Unlocked by |
|--------------------------|---------------------------------------------------------------------------------|-----------------------------------------------------------------|-------------|
| Sponsorship & grants     | GitHub Sponsors and thanks.dev now; FLOSS/fund ($10k–$100k) and GitHub's Secure Open Source Fund once usage grows | Supplementary only: the median Sponsors profile had two sponsors (2021 study) | G1 |
| Affiliate links          | Disclosed referral links in the data-provider docs                              | Finviz 30% recurring; TradingView $10–$400 per signup; IBKR $200 per referral | Phase 6 |
| Pro web tier             | Saved models and scenarios, batch runs and exports, higher API quotas, a commercial-use licence | Portfolio Visualizer $30 personal / $55 commercial a month; Koyfin $39–$79 a month | G3 |
| Metered API & remote MCP | Computation over hosted-safe data and the user's own inputs                    | Set against the Pro tier                                        | G3 |
| Excel add-in             | Office.js custom functions over the API; free download, unlocked by the account | Wisesheets $60–$120, Macabacus $200–$360, MarketXLS $850–$2,400 a year | G4 |
| `pyeconomics-pro`        | A closed package of advanced or convenience features                           | vectorbt PRO $25 a month or $240 a year                         | G4 |
| Study companion          | Worked examples, formula explorers and practice generators in our own words; no CFA mark in its name | Formula sheets $49–$79; prep courses $349–$1,599 | G4 |
| Enterprise               | Commercial licence, support SLAs, custom models, consulting (invoiced directly) | Anaconda Business $50 a user a month; Metabase Enterprise from $20k a year | G5 |
| Courses & books          | A cohort course and a book                                                     | Maven pays experts 90%; Leanpub pays 80%; finance-Python courses €2,999–$9,499 | G5 |

The study companion's market is real but price-anchored low: CFA candidates sat
roughly 157,000–163,000 exams a year in 2023–2025 (89,000–97,000 at Level I,
where 2026 is running 19% above 2025's same windows), and every candidate must
complete a Practical Skills Module — one of which teaches the same Python work
pyeconomics does. Nobody sells interactive formula tools standalone; formula
sheets sell for $49–$79 or are given away.

Avoided: advertising (EthicalAds pays around $2.50 per 1,000 pageviews and
needs 50k pageviews a month; OpenAI and Anthropic bar ads in plugins and
connectors), reselling or caching licensed data, advice-like features, the
CFA mark in any name, AGPL dual licensing (OpenBB tried it and reverted),
and an add-in built on PyXLL, which charges every end user $349 a year.

#### Gates

| Gate | When                       | Question                                         | Evidence required                                                                                     | Outcome |
|------|----------------------------|--------------------------------------------------|-------------------------------------------------------------------------------------------------------|---------|
| G1   | Phase 1                    | Do licence and brand keep every option open?     | ADR-0004 and ADR-0009 accepted; domains registered; thanks.dev and `funding.json` live; GitHub Sponsors deferred to 8.1 (issue #68; maintainer, 2026-10-08) | Proceed |
| G2   | Phase 5 launch             | Can demand be measured from day one?             | Cookie-less analytics, newsletter, waitlist with tier interest, a priced "Pro" preview (fake door), API and MCP usage, downloads and stars — all recording | Instrumentation verified live |
| G3   | The 90 days after the 1.0.0 announcement (ADR-0013 decision 19) | Will people pay, and for what? | At least 1,000 waitlist or newsletter sign-ups, or 1,000 activated users in 90 days; and at least 30 upgrade-intent clicks or pre-orders; and at least 10 interviews in which users confirm they would pay | Go: Phase 8 builds billing and the Pro tier. No-go: sponsorship, education content and consulting continue; the core is unaffected |
| G4   | Inside Phase 8             | Is there pull beyond the Pro tier?               | At least 50 paying accounts, three consecutive months of recurring-revenue growth, and repeated requests for Excel or offline use | Excel add-in, `pyeconomics-pro`, study companion |
| G5   | Inside Phase 8             | Is there enterprise demand?                      | At least three qualified enterprise requests, or one paid pilot                                        | Commercial licence, SLAs, courses |

The thresholds are the maintainer's judgement, not industry benchmarks; the
maintainer confirmed them and the window in ADR-0013 (decision 19) and
confirms or adjusts them again at the launch readiness gate. For scale, sourced
benchmarks put freemium free-to-paid conversion at 3–5% (good) with a 5%
median for developer products and an 8% median in a 2026 survey, and
developer-tool visitor-to-signup near 10%. Roughly 20,000 visitors, then,
yield about 2,000 sign-ups and about 100 payers within six months — an
estimate, not a forecast. Revenue is TBD: payers × a price set against the
anchors above.

### Risks & mitigations

| Risk                                                        | Mitigation                                                                                                   |
|-------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| "Every theory" scope stalls the launch                      | The launch catalog is fixed at 50 entries; everything else is a Phase 7 batch ordered by the coverage matrix; the model definition of done keeps breadth from outrunning trust |
| A published model returns a wrong number                    | Cited golden cases, property tests, cross-library oracles, the parity suite, public errata and the High-severity "model error" defect class |
| Data terms change or series disappear                       | Licence class as metadata, a yearly terms review, contract tests, degrade-to-snapshot, and the reclassification runbook |
| The hosted site cannot use FRED, Ken French or Shiller data  | Originator sourcing for public series; the user's own data for factor and equity models; the local app for everything else; the Phase 5 permissions programme |
| yfinance breaks or Yahoo blocks it                          | Library-only and optional; pinned; contract tests; bring-your-own-key alternatives in Phase 6                 |
| Licensed data reaches the hosted service                    | Hosted mode refuses those classes in code; the hosted image omits their libraries; tests prove both         |
| CFA Institute objects to trademark or curriculum use        | Marks only as adjectives in factual statements; the non-affiliation notice; no curriculum text or examples; counsel review before any paid study product |
| Investment-adviser regulation                               | Impersonal, general-purpose tools; no personalised recommendations; disclaimers; counsel review before the paid launch |
| Hosted cost blow-up or abuse                                | Cloudflare rate rules, per-IP limits, per-model compute budgets, a capped Cloud Run instance count, budget alerts |
| One maintainer's bandwidth                                  | Phase roadmaps executed by AI coding agents under the step lifecycle; strict scope; Phase 8 gated; parallel worktrees only where declared |
| Toolchain ownership shifts (OpenAI is acquiring Astral, maker of uv, ruff and ty) | Standards-based configuration (PEP 621, 735, 751) keeps tools swappable; mypy remains the type gate |
| Ecosystem churn (OpenBB's foundation transition, MCP spec revisions) | Integrate through stable seams (entry points, the official MCP SDK); spec-version tests; no hard dependency on OpenBB |
| Name confusion with similarly named projects                | Domains registered early, the trademark decision in ADR-0009, README disambiguation                         |
| Supply-chain compromise                                     | Trusted Publishing with attestations, SHA-pinned actions, harden-runner, 2FA, lockfile audits                |
| Monetization never pays                                     | The free core stands on its own; Gate G3 stops spending before evidence; the fallback track (sponsors, grants, education content, consulting) |
| AI assistants misuse outputs                                | MCP results carry manifests, units and limitations; tools are deterministic and cited                       |

---

## 6. Out of Scope

The following are deliberately deferred to a future version, or excluded:

- A portfolio-management, backtesting, order-management or trading system.
  The maintainer runs a separate system for that; pyeconomics may become
  its dependency, never the reverse.
- Reselling or redistributing licensed data, or any proprietary data
  business.
- Real-time streaming quotes, tick data and intraday terminal features.
- Personalised investment advice or recommendations.
- Exam-prep question banks and any reproduction of curriculum material.
- Full DSGE estimation suites (Dynare-class) and a symbolic algebra
  engine; small linear New Keynesian and RBC simulators are in scope
  (Phase 7).
- Native mobile and desktop apps beyond `pip`, `pipx` and `uv tool`.
- Non-English localisation.
- Self-hosted enterprise distributions and single sign-on, unless Phase 8
  evidence asks for them.

---

## 7. Glossary

| Term              | Meaning                                                                                   |
|-------------------|-------------------------------------------------------------------------------------------|
| ADR               | Architecture decision record, in `docs/adr/`                                              |
| ALFRED            | Archival FRED: past vintages of FRED series, as first published                           |
| BYOK              | Bring your own key: the user's own paid data subscription, used on the user's machine     |
| Catalog entry     | One registered model — a family of closely related formulas with one card and one id      |
| Coverage matrix   | Syllabus topics × catalog entries, with status; Phase 7's measure of done                 |
| DAPI              | Bloomberg's Desktop API, available only on a machine running a logged-in Terminal         |
| DCO               | Developer Certificate of Origin; a `Signed-off-by` line on every commit                   |
| ELB               | Effective lower bound on the policy rate                                                  |
| Evidence status   | How much a model's premise is trusted: standard, practitioner, contested, rejected, historical |
| FRED              | Federal Reserve Economic Data, from the Federal Reserve Bank of St. Louis                 |
| Golden case       | A cited input/output pair a model must reproduce within a stated tolerance                |
| Hosted-safe       | A data source whose terms allow pyeconomics' hosted service to display it                 |
| Library-only      | A data source a user may fetch locally but the hosted service never serves                |
| Manifest          | Provenance attached to every result: model and package versions, inputs, sources, vintages |
| MCP               | Model Context Protocol: how AI assistants discover and call external tools                |
| MoR               | Merchant of record: a reseller that handles payments, sales tax and VAT                   |
| Parity suite      | Tests proving Python, CLI, REST, MCP and web return identical outputs                     |
| PEP 740           | The standard for signed attestations on PyPI uploads                                      |
| r*                | The neutral real interest rate                                                            |
| SDMX              | Statistical Data and Metadata eXchange, the API standard of the IMF, OECD, ECB and BIS    |
| SEP / SPF         | The FOMC's Summary of Economic Projections / the Philadelphia Fed's Survey of Professional Forecasters |
| SPEC 0            | The Scientific Python ecosystem's schedule for dropping old Python and dependency versions |
| Trusted Publishing| Publishing to PyPI with short-lived OIDC credentials instead of a stored token            |
| Vintage           | A dataset exactly as it was published on a given date, before later revisions             |

---

## 8. Phase Complexity Summary

| Phase | Description                                            | Complexity | Status      |
|-------|--------------------------------------------------------|------------|-------------|
| 1     | Reset & Foundation                                     | Medium     | Complete    |
| 2     | Model Engine & Core Catalog                            | High       | Complete    |
| 3     | Data Platform & Free Sources                           | High       | Complete    |
| 4     | Programmatic Surfaces: CLI, REST API, MCP & Exports    | High       | Complete    |
| 5     | Web App, Docs & Public Launch (1.0.0)                  | High       | In progress |
| 6     | Premium Data: Bloomberg & BYOK Providers               | Medium     | Not started |
| 7     | Catalog Completion: CFA Program & Beyond               | High       | Not started |
| 8     | Accounts, API Plans & Monetization (Gated)             | High       | Not started |
