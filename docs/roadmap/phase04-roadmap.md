# Phase 4 Roadmap — Programmatic Surfaces: CLI, REST API, MCP & Exports

**Status:** In progress

## Overview

Phase 4 opens the surfaces gate. Phase 5 renders its model pages from the
`registry.json` this phase exports, calls the REST API this phase builds
through the generated TypeScript client, deploys this phase's container to
production, publishes the read-only MCP endpoint this phase mounts, and
runs the parity suite this phase writes through the deployed API; Phase 6's
premium providers and Phase 7's models reach every surface without a line
of surface code; Phase 8 puts API keys, quotas, remote MCP with OAuth and a
hosted AI ledger on top of the hosted mode defined here. None of that can
start until the generators are the only way a surface gains a model and a
parity suite proves that Python, the command line, the REST API and MCP
return the same bytes for every golden case. The phase builds the
`pyeconomics` command line, every export format and reproducibility
bundles, a versioned REST API in local and hosted modes, an MCP server over
stdio and stateless Streamable HTTP, the optional AI narrative, and a
staging service on Cloud Run behind Cloudflare, and releases them to PyPI
as the pre-release `1.0.0b1`. It adds no model and no provider (Phases 7
and 6), runs no production service, snapshot job or web page (Phase 5),
and takes no API key, account or payment (Phase 8). It is one phase because
a surface is proven only against the others: the parity suite is this
phase's acceptance test, as the monetary-policy suite was the data
layer's.

The phase lands in 16 layers:

1. **Surfaces baseline** — lands this roadmap and the refreshed planning
   kit, moves `main` to `1.0.0b1.dev1`, and makes the core safe for a
   surface that runs models concurrently in one process: issue #157's
   process-global `warnings.catch_warnings` in `core.library_warnings` is
   serialized, and every other process-global state a concurrent run could
   race on is audited and fixed or assigned.
2. **ADR-0012 and the surface core** — writes
   `docs/adr/0012-programmatic-surfaces.md`, twenty decisions the
   maintainer accepts or amends in the pull request, and builds the
   framework-free core every surface shares in `src/pyeconomics/surfaces/`:
   the one invocation path (`invoke`), the error table that maps every
   `PyeconomicsError` to a CLI exit code, an HTTP status and an RFC 9457
   problem type, the input codec, the canonical result envelope, the
   hosted budgets, and the layering test that keeps `core/` and `data/`
   free of every surface.
3. **Registry export** — `registry.json` (one entry per model: its
   description, card, formula, citations, schemas, examples, the first
   example's canonical result and an example figure) with its own JSON
   Schema, written deterministically, and syrupy snapshots of every
   model's input and output schemas that fail CI on an unintended change.
4. **The `pyeconomics` CLI** — Cyclopts in the core: `models
   list|search|describe|run` with run options generated from each model's
   inputs, bound runs (`--as-of`, `--vintage`, `--profile`), `data
   search|get|describe|vintages|sources`, `keys set|list|delete` on the OS
   keyring with the value read from a hidden prompt, `cache
   ls|info|clear|path`, `registry export`, stable exit codes, `--format
   table|json`, `--out` and shell completion.
5. **Exports and reproducibility bundles** — `pyeconomics.exports`: CSV
   with formula-injection escaping, XLSX with a manifest sheet, Parquet and
   Arrow with the manifest in schema metadata, JSON with the manifest
   embedded, each carrying the data's attributions and required notices;
   a deterministic reproducibility bundle (zip) whose `reproduce.py` reruns
   the result to identical bytes in a fresh environment; and the CLI's
   `csv`, `xlsx`, `parquet` and `arrow` formats and `--bundle`.
6. **REST API** — a FastAPI app factory behind the `[server]` extra:
   `/v1` routes generated from the registry, OpenAPI 3.1 exported as
   `openapi.json` with a snapshot, RFC 9457 problem details, `?format=`
   downloads through the exports, runs in a worker-process pool under
   per-model time budgets, `healthz` and `version`, and `pyeconomics serve`
   bound to 127.0.0.1 unless the operator forces otherwise.
7. **Hosted mode, API fuzzing and generated clients** — hosted mode's
   hosted-safe refusal with a licence explanation, per-IP limits with the
   `limits` library on Upstash Redis behind Cloudflare's rate rule,
   budget refusals (413 or 422), `Cache-Control` and `ETag`, the provider
   disable switch (issue #162), the SSRF and burst tests, Schemathesis
   against `openapi.json`, and the TypeScript and Python clients generated
   from it and smoke-tested.
8. **MCP server** — the official `mcp` SDK 2.x (`MCPServer`) behind the
   `[mcp]` extra, on the 2026-07-28 specification: `pyeconomics mcp` over
   stdio (runnable through `uvx`) and a stateless Streamable HTTP app
   mounted at `/mcp`; tool discovery (`search_models`, `describe_model`,
   `run_model`, `get_series`, `list_sources`) plus headline tools
   generated from a declared list; `outputSchema` with structured content,
   deterministic order and a `tools/list` snapshot; and the `llm_use`
   gate that skips forbidden sources at resolution and withholds what
   remains.
9. **MCP Apps, the MCP Registry entry and agent evaluations** — a chart
   rendered inside clients that support the MCP Apps extension, the
   `server.json` and README marker the official MCP Registry verifies, an
   OIDC publishing workflow that runs at the release, and tool
   descriptions tested with scripted and real agent tasks.
10. **Cross-surface parity** — every golden case of every registered
    model through the Python API, the CLI (`--format json`), the REST API
    and MCP `run_model`, with byte-identical canonical JSON; bound runs
    over recorded responses; export round-trips; and a guard that no
    surface module hand-writes a command, route or tool for a model.
11. **Optional AI narrative** — `pyeconomics.ai` behind the `[ai]` extra:
    provider-agnostic, bring-your-own-key through the credential chain,
    off by default, with the per-call cost shown; it refuses data whose
    `llm_use` forbids it and never runs in hosted mode. Its default model
    is a configuration value picked with the model selector in the step.
12. **Service container** — a slim, non-root image with the `[server]`,
    `[mcp]`, `[econometrics]`, `[plot]` and `[sdmx]` extras and no
    yfinance, keyring or Bloomberg code, built and scanned in CI (no
    Critical or High finding) and smoke-tested from the image itself.
13. **Staging on Cloud Run** — the staging service (minimum 0 instances,
    capped maximum) behind Cloudflare with Cloudflare Access on its
    hostname, deployed from `main` through OIDC and Workload Identity
    Federation with no service-account key, secrets read only from Secret
    Manager, a budget alert, and a scheduled health probe whose alarm
    opens an issue.
14. **1.0.0b1 readiness gate** — a TestPyPI rehearsal of the exact
    candidate, staging running the candidate's image, MCP Inspector over
    stdio and Streamable HTTP, the scripted and real agent tasks, a parity
    sample through staging, the burst and SSRF tests, and
    `docs/releases/1.0.0b1-readiness.md`, ending in the maintainer's GO or
    NO-GO.
15. **1.0.0b1 release** — `v1.0.0b1` on PyPI as a pre-release with
    attestations, release notes, the CLI and MCP quick-starts on the
    documentation preview, a GitHub pre-release and the MCP Registry
    entry.
16. **QA + `verify-phase04.sh`** — `scripts/verify-phase04.sh` (`--fast`,
    `--python`, `--node`, `--container`, `--security`, `--live`, `--all`,
    `--post`), `docs/phase04-qa-findings.md`, matrix entry `04` in
    `.github/workflows/phase-verify.yml`, and synthetic failures that
    prove the staging health alarm and the budget notification.

The ship test for Phase 4 is straightforward: issue #157 is closed with a
concurrency regression test; ADR-0012 is Accepted; `pyeconomics registry
export` writes `registry.json` and `openapi.json`, and syrupy snapshots
fail CI on any unintended schema change; the parity suite is green across
Python, the CLI, the REST API and MCP for every golden case of every
registered model; `pyeconomics models run … --format parquet` pipes into
pandas, the XLSX export opens with its manifest sheet, the CSV export
escapes formula prefixes (tested), and a reproducibility bundle reruns to
identical outputs in a fresh environment; Schemathesis property tests
against `openapi.json` find no 5xx response and no schema violation, and
oversized or over-budget inputs return 413 or 422 with problem details;
the MCP server passes MCP Inspector checks over stdio and Streamable HTTP,
its `tools/list` snapshot is stable, and the scripted agent tasks (price a
bond and report its duration; run the Taylor rule for a past date) succeed
through the tools; `pip install --pre pyeconomics==1.0.0b1` gives a
working `pyeconomics` CLI and, with the `[mcp]` extra, a working
`pyeconomics mcp` server; staging `/version` reports the release SHA, a
request with a Cloudflare Access service token runs a model and fetches a
hosted-safe series, and a request for a library-only source returns 403
with a licence explanation; the image scan shows no Critical or High
finding, no endpoint fetches a user-supplied URL, a burst test proves the
rate limits, the service reads secrets only from Secret Manager, deploys
use OIDC with no stored key, and local mode refuses a non-loopback bind
unless explicitly forced; the staging health alarm has fired once on a
synthetic failure; and `scripts/verify-phase04.sh --fast` exits 0 on
Ubuntu CI with the `phase-verify.yml` matrix entry `04` green.

**Pre-requisite:** Phase 3 is closed — V1–V20 green on 2026-10-23 (PR
#170), `1.0.0a2` on PyPI with attestations, and `main` protected with 22
strict required checks. Its public data API (`get`, `search`, `describe`,
`vintages`, `sources`), its credential chain (`resolve_key`, `has_key`,
`key_variable` and the keyring service `pyeconomics`), its cache API
(`info`, `entries`, `clear`, `path`), hosted mode's refusal
(`require_allowed`), bindings (`pyeconomics.bind`) and manifest schema 2
with its per-field `DataSource` records (which carry `llm_use`) are what
every surface wraps; `Result.to_json()`, `to_arrow()` and `to_parquet()`
(Phase 2) are the canonical bytes and the Arrow seam the exports extend;
and `verify-phase03.sh` is the template for `verify-phase04.sh`. The
operator holds admin on the GitHub repository and the Owner role in the
`pyeconomics-dev` organization (the MCP Registry grants
`io.github.pyeconomics-dev/*` only to an organization Owner), owner rights
with 2FA on the PyPI project, the `pypi` environment's review and admin on
the Read the Docs project; holds, or creates at Step 13's kickoff, a Google
Cloud account with a billing account (Cloud Run requires billing even
inside its free tier), the Cloudflare account that already holds the four
domains (ADR-0009) with Cloudflare Zero Trust's free plan enabled, and a
free Upstash account; has the GitHub CLI authenticated with the `repo` and
`workflow` scopes; and has Node.js 22.19 or later and Claude Code on the
machine that runs the `--node` checks and the real agent tasks.

**Dependency:** Phase 5 does not start until V1–V16 are green and
`1.0.0b1` is on PyPI. It renders its model pages from this phase's
`registry.json`, calls the API through the TypeScript client this phase
generates, deploys this phase's image to production behind the protected
`production` environment, replaces the hosted series route's per-request
originator fetch with its snapshot reader, publishes the hosted MCP
endpoint and its remote MCP Registry entry, makes the problem-type URIs
resolve, and runs the parity suite through the deployed API. Phase 6's
providers and Phase 7's models reach the CLI, REST API, MCP server and
exports with no surface change, because the surfaces are generated. Phase 8
adds API keys and quotas to the hosted mode defined here, remote MCP with
OAuth, and the AI narrative in hosted mode behind a cost ledger and a cap.

**Design rationale (generated, then proven).** The order inside the phase
is the design. The core is made safe for concurrent runs first (Step 1),
because the REST API and the MCP server both run models concurrently and
issue #157 is a known race. ADR-0012 then fixes the surface contract — the
invocation path, canonical bytes, the error table, the CLI grammar, the
export formats, the REST and MCP shapes, hosted mode and the staging
topology — before any framework code bakes in a choice, and the
framework-free surface core it describes is built in the same step (Step
2). The registry export (Step 3) comes before every surface, because it is
the description every surface and the Phase 5 web app are generated from.
The CLI (Step 4) is the first and simplest surface, so the error table,
the input codec and the formats meet real use before the server does; the
exports (Step 5) follow, so the REST API's downloads reuse them. The REST
API is built in two layers — the app factory and routes (Step 6), then
hosted mode, fuzzing and the clients that read its OpenAPI document (Step
7) — because hosted mode is where the security work concentrates. The MCP
server (Steps 8–9) reuses the same invocation path and adds the `llm_use`
gate. The parity suite (Step 10) runs only when all four surfaces exist,
and it is the phase's proof that "generated" means "identical". The AI
narrative (Step 11) is optional and isolated, so it comes after the
surfaces are proven. The container (Step 12) and staging (Step 13) deploy
a finished app, and from Step 13 every merge to `main` deploys staging, so
they come late. The release repeats Phase 3's gate-then-release pattern
(Steps 14–15): a published version can never be reused, only yanked.

**The surface contract.** One invocation path serves every surface: the
CLI, the REST API, the MCP server and the exports call
`pyeconomics.surfaces.invoke`, which resolves the model, decodes the
inputs, binds them through `pyeconomics.bind` when the request asks for
live data, runs the model and returns the `Result`; nothing else runs a
model. Every surface emits the result's canonical JSON (RFC 8785, ADR-0008
decision 12) unchanged: the REST API returns `Result.to_json()` bytes
without re-serializing them, the CLI writes them followed by one newline,
and MCP carries them as the tool's text content and their parsed object as
its structured content. One error table maps every `PyeconomicsError`
subclass, core's and the data layer's, to a CLI exit code, an HTTP status
and an RFC 9457 problem type, and a test fails when an error class has no
row. The shape, as Steps 2, 4, 6 and 8 build it (illustrative; ADR-0012
and those steps fix the real API):

```python
from pyeconomics.core import InputError
from pyeconomics.surfaces import BindRequest, invoke, problem_for

result = invoke(
    "macro.policy_rule",
    {"rule": "taylor_1993"},
    bind=BindRequest(as_of="2019-06-28"),
)
body = result.to_json().encode()  # the bytes every surface returns

problem = problem_for(InputError("coupon_rate: 5 is above its bound 1"))
problem.exit_code, problem.status, problem.type_uri  # 3, 422, ".../invalid-input"
```

**ADR-0012's decisions (drafted defaults).** Step 2 writes these as the
ADR's decisions with the defaults below; the maintainer accepts or amends
each in the pull request. A decision this roadmap's steps encode is never
reopened in a later step except by a superseding ADR.

| #  | Decision | Drafted default |
|----|----------|-----------------|
| 1  | Layering | `pyeconomics.surfaces` (framework-free) and `pyeconomics.exports` sit on `core` and `data`; `cli` (core runtime), `server` (`[server]`), `mcp` (`[mcp]`) and `ai` (`[ai]`) sit on them; nothing in `core/` or `data/` imports a surface, and `import pyeconomics` imports no framework |
| 2  | One invocation path | `surfaces.invoke(model_id, inputs, *, bind=None, mode=None) -> Result`, which Step 8 extends with decision 14's `llm_use` policy; a test proves no surface module calls `core.runner` or `pyeconomics.run` directly |
| 3  | Canonical bytes | Every surface returns `Result.to_json()`; the parity suite compares bytes; the CLI appends one `\n`, which the suite strips |
| 4  | Error table | One row per error class: slug, title, HTTP status, CLI exit code; problem `type` URIs `https://pyeconomics.dev/problems/<slug>` (Phase 5 makes them resolve); a problem body never holds a key, a path, a host or an upstream URL |
| 5  | CLI | Cyclopts in the core (ADR-0002 places `cli/` there); console script `pyeconomics`; run options generated from each model's input class at run time; `--inputs FILE` or `-` for JSON; exit codes 0 success, 1 internal error, 2 usage, 3 invalid input, 4 no defined result, 5 not found, 6 not permitted (licence), 7 data unavailable (credential, transport, upstream, offline, rate limit), 8 missing extra |
| 6  | Export formats | CSV (RFC 4180, UTF-8, LF, text cells quoted, cells starting with `=`, `+`, `-`, `@`, tab or carriage return prefixed with `'`, numbers never escaped, a leading `#` metadata block with attributions, notices, terms URLs and hashes); XLSX through openpyxl (already a runtime dependency) with `data` and `manifest` sheets and strings written as strings; Parquet and Arrow through pyarrow imported lazily (ADR-0008 decision 8: never a dependency, not even through an extra) with the manifest and attributions in schema metadata; JSON with the manifest embedded |
| 7  | Reproducibility bundle | A deterministic zip (stored, sorted entries, fixed timestamps): `result.json`, `inputs.json`, `request.json` (the bind request), `manifest.json`, `ATTRIBUTION.txt`, `requirements.txt` pinning `pyeconomics==<version>` and its extras, `reproduce.py` and `README.txt`; `reproduce.py` reruns from the recorded inputs and checks `result_sha256`, and `--refetch` re-binds at the recorded as-of date and vintages and reports agreement per field |
| 8  | Registry export | `registry.json`: a format version, the package version and one entry per model sorted by id (the `describe()` keys plus `example_result` and `example_figure`, a Plotly figure with no template, or null without `[plot]`); validated by its JSON Schema (2020-12), kept in `surfaces/registry_schema.py` because the wheel admits only `.py` files; no clock, host or path in it |
| 9  | REST shape | FastAPI under `/v1`: `GET /v1/models` (`?q=`, `?domain=`), `GET /v1/models/{id}`, `POST /v1/models/{id}/run` and a `GET` form for small inputs (`?inputs=` base64url of canonical JSON, at most 8 KiB) returning identical bytes, `GET /v1/series/{target}`, `GET /v1/sources`, `GET /healthz`, `GET /version`; OpenAPI 3.1; RFC 9457 `application/problem+json`; `?format=` with `json`, `csv`, `xlsx`, `parquet`, `arrow` or `bundle` |
| 10 | Execution | Runs execute in a pool of worker processes (spawned, never forked); hosted wall-clock budgets by `CostClass` (instant 2 s, light 10 s, heavy 30 s); a run past its budget is terminated and answered with a problem; inputs above a hosted size limit are refused before running; the data layer stays synchronous (no async transport, no httpx) |
| 11 | Modes | `local` (`pyeconomics serve`): every source the user can access, bound to 127.0.0.1, a non-loopback bind refused unless `--allow-remote` is passed; `hosted` (`PYECONOMICS_MODE=hosted`): hosted-safe and user-supplied data only, anonymous, no endpoint that accepts a provider key or a URL; in Phase 4 the hosted series route fetches hosted-safe originators per request in staging, and Phase 5 swaps in its snapshot reader |
| 12 | Limits and caching | `limits` with Redis storage on Upstash Redis over TLS in hosted mode (memory storage locally and in tests), keyed by client address; 429 with `Retry-After`; Cloudflare's free rate rule as the outer layer; a GET run is cacheable — an in-process cache keyed by model id and version, package version, canonical inputs and the data records, `ETag` = `result_sha256`, `Cache-Control: public` (longer for runs that read no data, shorter for bound runs); a POST run, which may carry values from a user's file, is processed in memory and never cached (`no-store`), nor is a problem |
| 13 | MCP server | `mcp` 2.x `MCPServer` on specification 2026-07-28 and the SDK's earlier supported revisions; stdio (`pyeconomics mcp`; `uvx --from "pyeconomics[mcp]" pyeconomics mcp`) and a stateless Streamable HTTP app mounted at `/mcp`; the five discovery tools by the names ROADMAP §4 4.5 gives and 10–20 headline tools generated from a declared list of model ids, named `<domain>_<name>` (`^[a-z0-9_]{1,64}$`); `outputSchema` on every tool; tools sorted; a large result returns a summary and a link to the REST download instead of the data |
| 14 | `llm_use` gate | MCP and the AI narrative pass an `llm_use` policy into binding and series resolution, so a `forbidden` source is skipped (a new resolver skip reason) and an `unclear` one only with the user's opt-in, set out of band in `pyeconomics.toml` or the environment and never through a tool argument; a result whose manifest still holds such a record is withheld (defence in depth) |
| 15 | MCP Apps | A `ui://pyeconomics/chart` resource (`text/html;profile=mcp-app`) renders a result's Plotly figure; run tools point to it with `_meta.ui.resourceUri`; its CSP names only the pinned script origin it loads; clients without the extension get the plain result |
| 16 | MCP Registry | Server name `io.github.pyeconomics-dev/pyeconomics`; `server.json` (registry schema 2025-12-11) committed; the README carries the `mcp-name:` marker PyPI's description then holds; `.github/workflows/mcp-registry.yml` publishes through GitHub OIDC from a protected `mcp-registry` environment with `mcp-publisher` pinned by version and checksum; the remote entry waits for Phase 5's production endpoint |
| 17 | AI narrative | `pyeconomics.ai`; AI providers are declared like data providers (hosts, key slot, `<PROVIDER>_API_KEY` through the credential chain) and called through the existing HTTPS transport, so `[ai]` adds no client library; off by default (the `ai_enabled` setting); the per-call cost from a dated price table; refuses forbidden `llm_use` data and hosted mode; CLI `models run --narrate` and `pyeconomics.ai.narrate(result)`, never an MCP tool or a hosted route |
| 18 | Generated clients | The TypeScript client from `openapi.json` with `@hey-api/openapi-ts` in `tools/node/` (pinned with a lockfile, generated output git-ignored, type-checked) and the Python client with `openapi-python-client`; both smoke-tested against a local server in CI; neither published in Phase 4 |
| 19 | Container | A multi-stage `Dockerfile`: a base image pinned by digest on Python 3.14 (every image dependency, arch included, has a wheel there), the wheel installed with the `[server,mcp,econometrics,plot,sdmx]` extras from the locked set, a non-root user, `PYECONOMICS_MODE=hosted`, the git SHA baked in for `/version`; no yfinance, keyring or Bloomberg code; scanned in CI |
| 20 | Staging and edge | Region `us-central1`; minimum 0 and maximum 2 instances; deploys from `main` through Workload Identity Federation bound to this repository and `main`; secrets only from Secret Manager; a billing budget with 50/90/100% alerts; the edge is a Cloudflare Worker on the staging hostname behind Cloudflare Access that forwards to the Cloud Run origin with an origin credential the app verifies (alternative: Cloud Run domain mapping, a Preview feature); a scheduled health probe through the edge opens an issue on failure |

Three facts behind decision 20 were read on 2026-10-23: Cloudflare's
Origin Rules host-header override (needed to proxy a plain CNAME to a
`run.app` origin) is available only on the Enterprise plan; Cloud Run
domain mapping is "not production-ready and not supported at General
Availability" and limited to ten regions, `us-central1` among them; and
a global external Application Load Balancer, Google's recommended path,
charges $0.025 an hour for its forwarding rule (about $18 a month),
outside this phase's $0 budget. A Worker on the free plan serves 100,000
requests a day, and ADR-0006 allows Worker code outside the page path
when an ADR adds it, which decision 20 does. ROADMAP §4 4.4 and the cost
table name "Upstash Valkey"; Upstash sells Upstash Redis (Redis protocol
over TLS; 500,000 commands a month free, then $0.20 per 100,000) and no
Valkey product, so Step 2 corrects that wording in the parent roadmap.

**Surface rules.** Three rules hold for every step from Step 2 on:

- **Generator rule.** A surface gains a model only through the registry.
  No module under `cli/`, `server/` or `mcp/` names a model id, and no
  command, route, tool or page is written by hand for one model; the
  headline MCP tools come from a declared list of ids, which is data.
  Step 10 makes the rule a check.
- **Parity rule.** The canonical bytes are the contract. A surface that
  cannot return them unchanged is wrong, not the parity test; a
  surface-specific presentation (a CLI table, an MCP text summary) is
  added beside the bytes, never in place of them.
- **Public-API rule.** ADR-0003 makes CLI commands and options, REST
  paths and schemas, and MCP tool names and schemas public API at 1.0.0.
  This phase may still change them, but every change after Step 15's
  release is listed in the next release notes, and Phase 5 freezes them.

**Licence rule.** Phase 3's licence classes reach every surface
unchanged. Hosted mode refuses every source not classed `hosted-safe` or
`user-supplied`, in the resolver and again in the provider, so no route
bypasses it, and the refusal reaches the caller as a 403 problem that
names the licence class and the terms page. Every export, bundle, CLI
table and API download of data carries the source's attribution and each
required notice (ADR-0005 rule 2), and a test per provider checks the
exact wording in each format. An export is the user's own file, written
at the user's request on the user's machine; pyeconomics still never
stores a source whose terms forbid storage, and the hosted service never
serves one. The image omits the libraries of library-only extras
(yfinance) and holds no Bloomberg code. Data whose `llm_use` is
`forbidden` never reaches an LLM through MCP or the AI narrative, and an
`unclear` source reaches one only with the user's out-of-band opt-in.

**Credential rule.** Users' keys never transit a surface: no REST route,
MCP tool or AI call accepts or returns a key, and none appears in a
problem body, a CLI message, a log line, an export or a bundle.
`pyeconomics keys set <provider>` reads the value from a hidden prompt or
from standard input, never from an argument (shell history) or an echo,
and `pyeconomics keys list` names each key's source, never its value.
The hosted service holds its own secrets only in Secret Manager. CI holds
secrets only as environment secrets of protected environments (`staging`
from Step 13, beside Phase 3's `providers-live`), never as repository
secrets (Phase 1 V10.5). The maintainer sets every value with a command
the step prints (`gh secret set <NAME> --env staging`, `gcloud secrets
versions add <name> --data-file=-`, `npx wrangler secret put <NAME>`),
each of which prompts for or pipes the value; a value never transits chat,
a pull request or a log. A shared secret is proven by an authenticated
round-trip, never by listing its name. No session prints, echoes, logs or
pastes a key or an environment value (AGENTS.md "Never print secrets").

**Version rule.** Step 1 moves `main` from `1.0.0a2` to `1.0.0b1.dev1`;
`release.yml` already routes a `.devN` tag to TestPyPI. Step 14 tags
`main`'s HEAD `v1.0.0b1.devN` to rehearse the exact candidate on TestPyPI
(a failed rehearsal is a NO-GO: the fix lands on a `fix/` branch that bumps
`N`, and the gate runs again). Step 15 sets `1.0.0b1` and tags the
release. `CITATION.cff` carries the same version as `pyproject.toml` at
every commit. This phase changes no model's outputs, so no model version
moves; a step that finds it must change one follows ADR-0003 (a new model
version, a changelog entry on the card and an erratum).

**Dependency rule.** Every dependency Phase 4 adds — runtime, extra, test
or docs — is added with `uv add --no-config` (and `uv lock --no-config`,
`uv export --no-config`), so the maintainer's private index never reaches
the lock files, and passes `pip-audit`. A runtime dependency, or any
package an extra pulls in, must also pass the ADR-0004 licence allowlist
(the `licences` hook) or carry a reviewed entry in
`scripts/checks/licence_exceptions.toml` that the maintainer approves in
the pull request, with `tests/checks/test_licences.py`'s pin of the
reviewed set updated in the same change; such a package is also exempted
by purl in `security.yml`'s `dependency-review`, with a comment naming
why. A required runtime dependency is pure Python or has a Pyodide build
(ADR-0002), and the core still imports in Pyodide: `pyeconomics.cli`
imports Cyclopts only when a command line is built, and `import
pyeconomics` imports no framework. A package an extra pulls in also joins
the `test` dependency group, so CI's default environment tests the code
that needs it. Polars and pyarrow stay out of every extra (ADR-0008
decision 8). Node tooling lives in one workspace, `tools/node/`, with a
committed lockfile, `npm audit --audit-level=high` in the gate and the
`npm` ecosystem in Dependabot. Facts this roadmap relies on, read from
PyPI and npm on 2026-10-23; the `licences` hook and the wheel listing at
step time are the authority:

| Package | Latest | Licence metadata | Predicted `licences` result | CPython 3.15 wheel | Planned use |
|---------|--------|------------------|-----------------------------|--------------------|-------------|
| cyclopts | 5.3.0 (2026-10-22) | `Apache-2.0` | Passes | pure Python | runtime: the CLI (Step 4) |
| rich, rich-rst, attrs, docstring-parser | 15.0.0, 2.2.0, 26.1.0, 0.18.0 | `MIT` (rich-rst by its License field only) | Passes; rich-rst no longer requires docutils, whose classifiers include the GPL | pure Python | runtime: Cyclopts' closure |
| markdown-it-py, mdurl, pygments | 4.2.0, 0.1.2, 2.21.0 | classifier `MIT License`; `BSD-2-Clause` | Passes | pure Python | runtime: rich's closure |
| fastapi | 0.162.0 (2026-10-23) | `MIT`; now requires `opentelemetry-api` | Passes | pure Python | `[server]` (Step 6) |
| starlette, anyio, idna, annotated-doc, typing-inspection, opentelemetry-api | 1.9.0, 4.15.1, 3.20, 0.0.5, 0.4.4, 1.45.1 | `BSD-3-Clause`, `MIT`, `BSD-3-Clause`, `MIT`, `MIT`, `Apache-2.0` | Passes | pure Python | `[server]`: FastAPI's closure |
| uvicorn, click, h11 | 0.54.0, 8.5.0, 0.16.0 | `BSD-3-Clause`, `BSD-3-Clause`, `MIT` | Passes | pure Python | `[server]`: the ASGI server, without its `[standard]` extra |
| limits, deprecated, wrapt, packaging | 5.8.0, 3.0.0, 2.5.1, 26.3 | `MIT`, `MIT`, `BSD-2-Clause`, `Apache-2.0 OR BSD-2-Clause` | Passes | pure Python (wrapt also cp315) | `[server]`: per-IP limits (Step 7) |
| redis | 8.1.0; `limits[redis]` pins `redis<8` | `MIT` | Passes | pure Python | `[server]`: the limiter's Redis storage (Step 7); `limits[valkey]` is the alternative |
| mcp, mcp-types | 2.3.0 (2026-10-02) | `MIT` | Passes | pure Python | `[mcp]` (Step 8) |
| httpx2, httpcore2 | 2.16.0 | `BSD-3-Clause`; they use truststore, not certifi | Passes | pure Python | `[mcp]`: the SDK's HTTP client |
| pyjwt, cryptography, cffi, pycparser | 2.15.1, 50.0.2, 2.1.1, 3.12 | `MIT`, `Apache-2.0 OR BSD-3-Clause`, `MIT-0`, `BSD-3-Clause` | Passes, except cffi's reviewed exception (Phase 3 Step 3), which now also covers `[mcp]` | cryptography abi3 and cp315; cffi cp315 | `[mcp]`: `pyjwt[crypto]` |
| jsonschema, referencing, jsonschema-specifications, rpds-py | 4.26.0, 0.37.0, 2025.9.1, 2026.9.1 | `MIT` | Passes | pure Python; rpds-py cp315 | `[mcp]`: the SDK's schema validation |
| sse-starlette, python-multipart | 3.5.0, 0.0.32 | `BSD-3-Clause`, `Apache-2.0` | Passes | pure Python | `[mcp]` |
| pywin32 | 312 (Windows only) | `PSF`; classifier `Python Software Foundation License` | Expected to fail as ambiguous: a reviewed exception after reading its licence file | cp315 | `[mcp]` on Windows |
| httpx | 0.28.1 | `BSD-3-Clause`; requires certifi | outside the allowlist's scope (test only) | pure Python | test: Starlette's `TestClient` (Step 6) |
| schemathesis | 4.32.4 (2026-10-22) | `MIT`; requires PyYAML | outside the allowlist's scope (test only) | PyYAML 6.0.3 has none | test: API fuzzing on Python 3.14, under the Wheel rule (Step 7) |
| openapi-python-client | 0.29.1 | `MIT`; requires httpx<0.29, ruff, typer | outside the allowlist's scope (dev tool) | pure Python | dev: the Python client (Step 7) |
| @hey-api/openapi-ts | 0.99.0 (npm) | `MIT`; Node 22.18 or later | npm audit only | — | dev: the TypeScript client (Step 7) |
| @modelcontextprotocol/inspector | 2.12.0 (npm, 2026-10-21) | its own licence file | npm audit only | — | dev: Inspector checks (Steps 8, 14) |
| @modelcontextprotocol/ext-apps | 2.0.3 (npm) | `MIT` | npm audit only | — | the MCP Apps chart (Step 9), if it is used |
| typescript | 7.0.2 (npm) | `Apache-2.0` | npm audit only | — | dev: type-checking the client |

**Wheel rule.** CI runs every cell of Python 3.12–3.15 on Ubuntu, Windows
and macOS, so a dependency must install from a wheel, or be pure Python, on
all of them. A candidate without one at its step's kickoff is never added
on hope: the step uses a replacement that has one, implements the piece
natively, or — only for an optional extra or a test-only tool, with the
maintainer's approval in the pull request — gates the package with the
environment marker `python_full_version < '3.15'`, has a test assert the
gap on the uncovered cells (never a skip), and opens an issue to drop the
marker when the wheels ship. On 2026-10-23 PyYAML, which Schemathesis
requires, publishes no CPython 3.15 wheel, so Step 7 runs Schemathesis in
a dedicated job on Python 3.14 from a dependency group gated that way
unless the wheels ship first. The container (Step 12) runs Python 3.14,
where arch, still gated in `[econometrics]` (issue #154), has wheels.

**Cross-phase verification rule.** `phase-verify.yml` runs
`verify-phase01.sh`, `verify-phase02.sh` and `verify-phase03.sh`
(`--fast` and `--security`) on every Phase 4 pull request, and those
checks were written against earlier trees. When a Phase 4 change
legitimately invalidates one of them, the same pull request narrows the
check to the invariant it was protecting, never deletes it, and appends a
line to a `## Post-merge addendum (<YYYY-MM-DD>) — Phase 4 changes to
verify-phase0N.sh` section at the end of that phase's roadmap, the pattern
Phase 3 used. The ones this roadmap foresees:

| Check or test | What it pins today | Step that narrows it |
|---------------|--------------------|----------------------|
| Phase 3 check 78 (the workflow secret boundary) | no workflow but `providers-live.yml` reads a secret other than `GITHUB_TOKEN` | Step 13 (also `staging-health.yml` and `deploy-staging.yml`, each only from the protected `staging` environment) |
| Phase 1 check 36 | `id-token: write` sits on exactly release.yml's two publish jobs | unchanged: the MCP Registry publish and the staging deploy live in their own workflows (`mcp-registry.yml`, `deploy-staging.yml`) |
| Phase 1 check 37 | every workflow: `permissions: {}`, SHA pins, `persist-credentials: false`, no `pull_request_target` | unchanged: every new workflow complies |
| Phase 1 V10.5 | no repository secret exists | unchanged: Phase 4's secrets are environment secrets |
| Phase 1 checks 17 and 18 | at least the listed ADRs, each Accepted and indexed | unchanged: ADR-0012 joins the index Accepted |
| Phase 2 check 4 | runtime floors only, no upper bound | unchanged: `cyclopts>=5.3` carries no upper bound |
| Phase 2 checks 21 and 55, Phase 3 checks 11, 33 and 40 | each named extra is included in `[all]` | unchanged: `[server]`, `[mcp]` and `[ai]` join `[all]` |
| `docs/index.md` and `README.md` | "the command line, REST API, MCP server and web app follow in later phases" | Step 15 (no earlier check pins the sentence) |

**Contract-change rule.** Steps 3–12 build on the contract ADR-0012 and
the surface core fix in Step 2. A step that cannot be completed without a
contract change makes the change in-step (Triage rule: an upstream gap
that blocks the step): the smallest change that works, every surface,
golden case and snapshot kept green, the owning step's `<task>` block
patched and the change added to the carry-over checklist in this file's
last section. A change to a data-layer contract Phase 3 fixed — such as
Step 8's `llm_use` skip in the resolver — follows the same rule and keeps
every provider, concept and binding test green. A change to a decision
ADR-0008, ADR-0011 or ADR-0012 records is a superseding ADR in the same
pull request, because an Accepted ADR is never edited
(`docs/adr/README.md`).

**Branch strategy.** Every step in this phase lands on its own short-lived
feature branch (`feature/phase04-step<M>-<slug>`), opens a pull request
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
git checkout -b feature/phase04-step<M>-<slug>
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
feature/phase04-step<M>-<slug> <worktree-path> origin/main`, the worktree
is bootstrapped before any test or build (fresh dependency install and env
files — a worktree has none of the primary tree's untracked state, and it
must never borrow the primary tree's editable install), the Stage 4 merge
runs from the primary tree, and Stage 5 removes the worktree BEFORE pruning
the branch. Undeclared parallelism is a lifecycle violation, not a
shortcut. Worktree location for this project: git-ignored
`.worktrees/<branch-slug>/` inside the repository, matching the parent
ROADMAP; bootstrap with `uv sync --locked` inside it, and `npm ci` in
`tools/node/` once Step 7 creates it.

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
done, exactly like its tests. Phase 4 opens the project's first network
listeners, its first deploy pipeline and its first hosted ingress, so its
exposures are a key leaking through a new sink — a CLI message, a problem
body, an MCP result, a server log, an export or a bundle (ROADMAP §5
threat 1); cost exhaustion of the hosted service through expensive inputs
or request floods (threat 2); server-side request forgery and unsafe
deserialization through request bodies, uploaded inputs and bundles
(threat 3); licensed data escaping to the hosted service (threat 4); a
malicious release or image (threat 5); CSV and Excel formula injection
(threat 6); MCP tool output steering an assistant (threat 7); and the
supply chain of the new frameworks, the Node tooling, the container base
image and the deploy pipeline's OIDC trust.

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
bullet must be green before the step is declared complete. In Phase 4 the
surfaces are the staging service on Cloud Run (from Step 13 every merge to
`main` deploys it through `deploy-staging.yml`, and the deploy job's own
post-deploy check reads `/version` and runs a model through the edge with
the Cloudflare Access service token), the scheduled `staging-health.yml`
probe (Step 13), the Read the Docs `main` preview (the surface guides,
verified live at Step 15), TestPyPI (Step 14), PyPI and the MCP Registry
(Step 15); their hands-off recipes are a `workflow_dispatch` or push run on
`main` read back with `gh run view`, a request through the edge with the
service token read from the maintainer's keyring, the Read the Docs API
and page text, a clean-venv install of the exact version followed by
`scripts/smoke.py` and the CLI and MCP recipes each release step names,
and the registry's public API. A step that introduces a required
environment variable or shared secret verifies at kickoff that it exists
in every target environment and proves shared values by an authenticated
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
the errata page; a parity failure between two surfaces → a bug in the
surface that changed the bytes, never a loosened comparison; a provider
whose source changed its terms → a High defect (ROADMAP §5 "Data licensing
policy" rule 7); architectural question → an issue for a future phase;
process improvement → recorded where the next conversation will read it;
security finding → jumps the queue by severity. A step's PR contains the
step plus blocking fixes only, and lists the issues it opened. When a
merged PR auto-closes an issue, the environment check is what earns the
close — reopen or follow up if a gap remains.
`docs/phase04-qa-findings.md` is the rollup: every finding, its class, and
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
step's heading (`## Step 4 — The pyeconomics CLI ✅`) so the completion
shows in the rendered preview, the outline, and the table of contents,
sets the step's Summary Table Status cell to `Complete — PR #<n>`, commits
that edit on the step branch, and pushes. The PR therefore carries its own
completion mark, and the roadmap on `main` says a step is complete exactly
when that step's PR merges — never before. This file's phase-level
`**Status:**` line (under the title) and the parent project roadmap are
marked the same way, in the same commit: Step 1's PR flips both from `Not
started` to `In progress` (the parent's `### Phase 4` line reads `In
progress — phase04-roadmap.md`, and its "Phase Complexity Summary" row
reads `In progress`), and the final step's PR flips both to `Complete — …`
(the parent's with its row in the "Phase Complexity Summary" table and the
header `> **Status:**` line) and appends ` ✅` to this file's `# ` title and
to the parent's `### Phase 4` heading, so the project roadmap shows a
finished phase the way this file shows a finished step. There is no
separate "update the roadmaps" chore: a step whose PR merged without its
Status line is a lifecycle violation, and the next step's Stage 1 (and
`/roadmap-step`) refuses to start until the previous step reads
`Complete`. If a post-merge check fails — a Deployed & verified bullet, an
alarm that never fired — the step is NOT complete despite the merged line;
say so, and the `hotfix/` PR that completes it appends its own number to
the line. `grep -n '^\*\*Status:\*\*'` on this file is the phase's progress
report, and the ✅ headings are the same report at a glance.

**Step lifecycle.** Every step in this phase follows the exact same
six-stage lifecycle, in order, with no exceptions. Each stage is a hard
checkpoint — if a stage is skipped, branch protection or the next step's
Stage 1 will fail loudly, and that is the safety net. AI coding agents MUST
execute all six stages before declaring a step complete.

1. **Create the branch.** Before any Read / Edit / Bash, run
   `git checkout -b feature/phase04-step<M>-<slug>` from a clean,
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
   on the step branch (`docs: mark Phase 4 Step M complete`), and push —
   the PR now carries its own completion mark, so the roadmap on `main`
   will say the step is complete exactly when the PR merges (Status rule).
   On the phase's first step, the same commit sets this roadmap's
   phase-level `**Status:**` (under its title) and the parent project
   roadmap's Phase 4 `**Status:**` to `In progress`; on the final step,
   both to `Complete`, with ` ✅` appended to this roadmap's `# ` title and
   to the parent's `### Phase 4` heading.

4. **Wait for green checks, then squash-merge.** Every required status
   check must report success: the 22 Phase 3 left required (lint, types,
   the aggregate `test` gate — which needs the twelve-cell test matrix,
   `pyodide`, `docs` and every job this phase adds to it — package,
   lockfile, pr-title, dco, the nine security checks, and both
   `phase-verify` jobs for `01`, `02` and `03`), plus both `phase-verify`
   jobs for `04` once Step 16 adds them. If the PR goes BEHIND main while
   waiting, refresh with `gh pr update-branch --rebase` — never merge
   `main` into the branch; `required_linear_history: true` enforces
   rebase. Once every check is green:

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

## Current State (as of Phase 3)

### Package and API surface

- `src/pyeconomics/` holds `core/` (38 modules), `models/` (13 domain
  packages, 50 models), `data/` (the data layer) and the `registry.py`
  facade; `pyeconomics.__all__` is `__version__`, `bind` (imported lazily,
  PEP 562), `registry`, `run` and `run_batch`. No `surfaces/`, `exports/`,
  `cli/`, `server/`, `mcp/` or `ai/` package exists, `pyproject.toml`
  declares no console script, and the `server`, `mcp` and `ai` extras are
  empty lists, held since Phase 1 Step 7 so their names are stable
  (ADR-0002). `pyproject.toml` reads `1.0.0a2`, with two entry-point groups:
  `pyeconomics.models` (13 entries) and `pyeconomics.providers` (31).
- `pyeconomics.registry` offers `ids`, `get`, `resolve`, `models`,
  `domains`, `describe`, `refresh` and `validate`. `describe(id)` returns
  JSON-ready values under the 23 `DESCRIPTION_KEYS` of
  `core/describe.py` (`id`, `version`, `domain`, `title`, `summary`,
  `tags`, `formula`, `assumptions`, `limitations`, `evidence`, `cost`,
  `references`, `invariants`, `no_invariants_reason`, `examples`, `charts`,
  `aliases`, `bindings`, `extra`, `changelog`, `input_schema`,
  `output_schema`, `card`), and its docstring already names Phase 4's
  `registry.json` as "a list of these". It imports the data layer only for
  a bound model, whose card lists the sources that can fill each concept.
- `Result` (`core/results.py`) is immutable and holds the validated inputs
  and outputs, warnings and a schema-2 `Manifest`. `to_json()` is the
  canonical RFC 8785 text the parity suite compares; `to_dict()`,
  `to_pandas()`, `to_polars()` and `to_arrow()` exist, `to_arrow()` puts the
  manifest's canonical JSON in the schema metadata under
  `pyeconomics.manifest`, `to_parquet(path)` writes that table, and
  `attributions()` returns the de-duplicated attribution and required
  notices of the data a run read (empty for a run that read none).
  `core/plotting.py` builds a Plotly figure from a model's `ChartSpec`s
  behind the `plot` extra. There is no CSV, XLSX or bundle export.
- The error taxonomy is ADR-0008 decision 13's: `PyeconomicsError` and its
  core subclasses `InputError`, `DomainError`, `ConvergenceError`,
  `ModelNotFoundError`, `RegistryError` and
  `MissingOptionalDependencyError` (`core/errors.py`), and the data layer's
  `DataError` with `ProviderNotFoundError`, `ConceptNotFoundError`,
  `SeriesNotFoundError`, `CredentialError`, `LicenceError`,
  `RateLimitError`, `TransportError`, `OfflineError`, `ResponseError` and
  `ConfigError` (`data/errors.py`). Each also derives from the built-in a
  Python caller expects. Nothing maps them to an exit code or an HTTP
  status yet.

### Data and credential surface

- The public data API (`data/api.py`) is `get(target, *, start, end, as_of,
  vintage, provider, mode, strict, parameters, max_observations)` returning
  a `Resolved`, `search(text, limit, *, providers, mode)`, `describe(target)`,
  `vintages(target, *, mode)` and `sources(*, check_keys=True)`; a target is
  a concept id or a `provider:series` key. `pyeconomics.bind(model_id, *,
  as_of, vintage, mode, profile, concepts, parameters, **overrides)` returns
  a `Bound` that `pyeconomics.run(model_id, bound)` runs, recording one
  `DataSource` per bound field; each record carries the source's licence
  class, attribution, notice, terms URL and `llm_use`.
- The key chain (`data/credentials/chain.py`) reads an argument, then
  `<PROVIDER>_API_KEY` (`key_variable`), then the configuration
  directory's `.env`, then the OS keyring (service `pyeconomics`, user the
  provider id, `KEYRING_SERVICE`) when the `keyring` extra is installed;
  `has_key` answers without creating a `Secret`, and `withheld` hides a
  provider's key in a block. Nothing writes to or deletes from the keyring:
  users run `keyring set pyeconomics <provider>` themselves until Phase 4's
  `keys` commands (Phase 3 Not-in-scope).
- The cache API (`data/cache/`) is `info()`, `entries(provider)`,
  `clear(provider)` and `path()`, which the module docstring reserves for
  Phase 4's `pyeconomics cache` commands; none returns a payload. Settings
  (`data/config.py`) layer `pyeconomics.toml` in the configuration and
  working directories under `PYECONOMICS_MODE`, `PYECONOMICS_OFFLINE`,
  `PYECONOMICS_CACHE_DIR`, `PYECONOMICS_SEC_CONTACT` and
  `PYECONOMICS_TTL_<PROVIDER>`, and refuse any key named like a credential.
- Hosted mode (`data/modes.py`) refuses every source not classed
  `hosted-safe` or `user-supplied` in `require_allowed`, which every public
  provider operation and every transport calls, and the resolver applies
  the same rule earlier to fail over. `llm_use` is a source's and series'
  metadata, but nothing yet consults it: FRED (and some SDMX series) is
  `forbidden`; BEA, BLS, CBO, Census, the Fed Board, the New York Fed,
  OpenFIGI, the Penn World Table, SEC EDGAR, Treasury and the World Bank are
  `allowed`; the regional Fed research sources, DBnomics and the finance
  research sources are `unclear`. No resolver skip reason exists for it.

### Execution and concurrency surface

- `run`, `run_batch` and `bind` are synchronous; the data layer's one HTTPS
  transport is urllib3 with truststore, imported lazily (ADR-0011
  decision 10), and Phase 3 left an asynchronous transport out of scope
  unless Phase 4's server must fetch per request.
- Every model declares a `CostClass` (`core/spec.py`): 33 are `instant`, 12
  `light` and 5 `heavy` ("a hosted service caps or queues it"). No budget
  or size limit beyond each array field's `max_length` exists.
- Issue #157: `core.library_warnings`, which the statsmodels and arch
  wrappers use to report a library's warnings, enters the process-global
  `warnings.catch_warnings`, so two models run concurrently in one process
  can lose or swap each other's warnings. The cache and configuration
  modules already guard their state with `threading` locks; the
  registry's lazy discovery, the redaction log-record factory and the
  context variables behind `withheld`, `cache.memo()` and `cache.bypass()`
  have never been exercised by concurrent callers.

### Dependency and licence surface

- Runtime dependencies are `defusedxml`, `holidays`, `numpy`, `openpyxl`,
  `pandas`, `platformdirs`, `pydantic`, `scipy`, `truststore` (not on
  Emscripten), `urllib3` and `xlrd`, floors only (Phase 2 check 4). Extras:
  `econometrics` (statsmodels; arch behind `python_full_version < '3.15'`,
  issue #154), `plot`, `keyring`, `sdmx`, `yfinance`, `all` (every extra
  with content) and the empty `server`, `mcp` and `ai`. The `test` group
  already holds hypothesis, jsonschema, polars, pyarrow, rfc8785, syrupy
  and pytest-socket; no web framework, ASGI server, MCP SDK, HTTP test
  client or API fuzzer is in the lock.
- ADR-0002 places `cli/` in the core distribution: its required
  dependencies must be pure Python or have a Pyodide build, and pass the
  ADR-0004 allowlist. ADR-0008 decision 8 forbids Polars and pyarrow as
  dependencies, even through an extra: a conversion imports them lazily
  and raises `MissingOptionalDependencyError` naming the package.
- `scripts/checks/licence_exceptions.toml` holds reviewed entries for numpy,
  scipy, pandas, python-dateutil, patsy, cffi (`MIT-0`, through `[keyring]`
  and `[yfinance]`), certifi (`MPL-2.0`), sdmx1, defusedxml, xlrd, peewee,
  multitasking and protobuf. No Node tooling exists; `web/` holds only a
  README, a placeholder for Phase 5.

### Toolchain and test surface

- pytest runs with `--strict-markers --strict-config --doctest-modules
  --import-mode=importlib --disable-socket`, `filterwarnings = ["error"]`
  and `-m "not live"`, over `tests`, `src` and `docs`. The offline suite
  passed 7,755 tests in about 16–19 minutes serially (no pytest-xdist);
  `HYPOTHESIS_PROFILE=ci` is the required profile, and the dev profile
  fails five known property issues (#112, #139, #143, #149, #152).
- `tests/golden/` holds one TOML file per model: 354 cited cases across 50
  files, the inputs every parity check will run. `tests/registry/toy_models.py`
  is the toy catalog, `tests/data/bindings/bound_support.py` the scripted
  providers for offline bound runs, and `tests/data/leakcheck.py` the
  `canary()` and `LeakCheck` harness every new sink joins.
- Branch coverage holds `fail_under = 95` overall, and
  `scripts/checks/coverage_floors.py` holds `core/` at 95%, `models/` at
  90% and `data/` at 95% (Phase 3 closed at 99.76%, 98.41% and 96.13%).
  mypy is strict with the pydantic plugin; ruff selects `ALL` and formats
  the Python blocks in Markdown, roadmaps included.

### CI/CD and publishing surface

- `ci.yml`: `lint`, `types`, `ty` (informational), `tests` (twelve cells),
  `package` (build, `twine check --strict`, the artifact allowlist and the
  clean-venv smoke with and without extras), `pyodide`, `docs`, `lockfile`,
  `pr-title`, `dco`, and the aggregate `test`, which needs every one but
  `ty`. `security.yml`, `codeql.yml`, `scorecard.yml`,
  `phase-verify.yml` (matrix `["01", "02", "03"]`), `release.yml` (a `v*`
  tag equal to the version: `.devN` to TestPyPI, else PyPI behind the
  `pypi` approval, with PEP 740 attestations), `release-smoke.yml`,
  `providers-live.yml` and `providers-heartbeat.yml`.
- `main` requires 22 checks, strict: gate-secrets, gate-sast, gate-deps,
  gate-licences, trufflehog, zizmor, dependency-review, codeql (python),
  codeql (actions), lint, types, test, package, lockfile, pr-title, dco and
  both `phase-verify` jobs for `01`, `02` and `03`. Every workflow sets
  `permissions: {}`, starts each job with harden-runner, sets
  `persist-credentials: false` and pins actions to commit SHAs; it runs on
  GitHub-hosted runners, as a public repository's must. `id-token: write`
  sits only on release.yml's two publish jobs and Scorecard's job.
- No repository secret exists. The `providers-live` environment holds the
  live run's provider keys and contact; `testpypi` and `pypi` only gate tag
  deployments. Dependabot updates `uv` and `github-actions` weekly; its
  maintenance PRs (#98–#103, #167) proceed under normal checks,
  independent of this phase.

### Security and sensitive-data surface

- Phase 4 adds the project's first listeners (a local server, an MCP stdio
  server and a hosted service), its first deploy pipeline (GitHub to Google
  Cloud through OIDC) and its first hosted secrets (ROADMAP §5 "Data
  classification": hosted service secrets from Phase 4, Secret Manager
  only). New input paths arrive with it: command-line arguments, input
  files and standard input, HTTP request bodies and query strings, MCP tool
  arguments, and bundles a user reruns.
- The prek gate runs gitleaks (staged changes; CI scans the whole tree),
  bandit, semgrep with the project rules `credential-logging`,
  `dynamic-code`, `unsafe-deserialization`, `unsafe-yaml`, `model-purity`
  and `secret-reveal`, the `semgrep-test` hook, `pip-audit`, `lock-index`,
  `licences`, zizmor and `no-commit-to-branch`. trufflehog's URI detector
  fails a PR on a literal URL carrying a user name and password anywhere in
  its commits, so a test builds such a value at run time.
- Patterns every step mirrors: only `data/credentials/` and
  `data/transport/` reveal a key (the `secret-reveal` rule); a failure that
  may hold a key or a URL is re-raised with `redaction.call_scrubbed`;
  tests run with the `isolated` fixture (their own configuration and cache
  directories, no `*_API_KEY` or `PYECONOMICS_*` variable, an in-memory
  keyring) and plant keys with `canary()`; refer to a fake credential by
  its location, never quote it; treat a workflow change as a
  security-relevant diff; keep the private uv index out of the lock files
  with `--no-config`.

### Documentation surface

- Read the Docs builds the 1.0 preview from `main` as version `main`
  (`/en/main/`) with warnings as errors, while `stable` serves 0.2.6 until
  Phase 5. `docs/conf.py` uses MyST-NB, sphinx-autoapi, Napoleon and the
  local `model_pages`, `provider_pages` and `concept_pages` extensions, and
  an audit hook blocks every non-loopback socket during the build. Sybil
  tests the Markdown pages' examples.
- `docs/index.md` and `README.md` say the command line, REST API, MCP server
  and web app follow in later phases; no CLI, API, MCP, exports or AI page
  exists. `docs/releases/` holds the `1.0.0a2` notes and the fourteen-section
  readiness record, the shape `1.0.0b1`'s follow.

### Operations and observability surface

- No runtime service exists. The live surfaces are package publishing
  (health signal `release-smoke.yml`; alarm GitHub's failed-workflow
  email; rollback a yank and a `.postN` release) and the weekly
  `providers-live.yml` with the daily `providers-heartbeat.yml`, each of
  which opens an issue when it fails; Phase 3 Step 20 proved both alarms
  and the maintainer confirmed the notifications.
- Phase 4 adds a runtime surface: the staging API on Cloud Run (health
  signal `/healthz` and `/version`; probe `staging-health.yml` through the
  edge; alarm an issue plus GitHub's notification), the deploy workflow,
  and a billing budget whose 50/90/100% alerts and programmatic
  notifications reach the maintainer. ROADMAP §5's runbooks "Deploy
  regressed", "Secret leaked" and "Cost spike" become live with it; the
  production uptime checks, Sentry and OpenTelemetry stay in Phase 5.
- The one metered dependency is Upstash Redis (500,000 commands a month
  free); Cloud Run, Artifact Registry, Secret Manager and Cloudflare stay
  inside their free tiers at staging scale, which Step 13 verifies.

### Verification surfaces

- `scripts/verify-phase01.sh` (50 static checks, V1–V12),
  `scripts/verify-phase02.sh` (66, V1–V15) and `scripts/verify-phase03.sh`
  (78, V1–V20) share the mode contract `--fast`, `--python`, `--security`,
  `--live`, `--all` and `--post`, the `record` / `check` / `vcheck` /
  `vstatic` helpers, the `PASS  12     <description>` line format and the
  per-mode summary ending in `RESULT: PASS`. Phase 3's static checks are a
  standard-library Python program plus a Bash credential backstop; its
  `--fast` takes about 4 seconds on Ubuntu, and its canonical `--post` took
  7,234 seconds. `verify-phase03.sh` is the template for
  `verify-phase04.sh`, `scripts/verify_phase03_live.py` for its live
  helper and `tests/repo/test_phase03.py` for its pytest twin.
- `.github/workflows/phase-verify.yml` runs the matrix `phase: ["01", "02",
  "03"]`, both jobs required; Phase 4 appends `"04"`. Phase 3's verifier
  lessons hold: no static check pins a value a later phase legitimately
  changes (state "at least" invariants); a check consumes its whole input
  (Phase 1 check 13's SIGPIPE false failure); clean wheel venvs use the
  project's interpreter; nobody edits a Bash verifier, or any tracked file,
  while it runs; and stopping a run verifies that its `uv` and `pytest`
  descendants stopped too.

---

## Execution Order

```
Step 1  (surfaces baseline)           #157 closed; concurrency audit;
                                      main at 1.0.0b1.dev1; roadmap and
                                      kit landed → implement
  ↓
Step 2  (ADR-0012 + surface core)     docs/adr/0012; surfaces/: invoke,
                                      error table, codec, envelope,
                                      budgets; layering test → implement
  ↓
Step 3  (registry export)             registry.json + schema; schema
                                      snapshots → implement
  ↓
Step 4  (CLI)                         pyeconomics models/data/keys/cache/
                                      registry; exit codes; completion
                                      → implement
  ↓
Step 5  (exports + bundles)           CSV, XLSX, Parquet, Arrow, JSON;
                                      reproducibility bundles → implement
  ↓
Step 6  (REST API)                    [server]; /v1 routes; OpenAPI 3.1;
                                      problems; worker pool; serve
                                      → implement
  ↓
Step 7  (hosted mode + fuzzing +      limits, budgets, caching, #162;
         clients)                     Schemathesis; TS + Python clients
                                      → implement
  ↓
Step 8  (MCP server)                  [mcp]; stdio + stateless HTTP;
                                      discovery + headline tools;
                                      llm_use gate → implement
  ↓
Step 9  (MCP Apps + registry entry +  chart UI; server.json; OIDC publish
         agent evaluations)           workflow; agent tasks → implement
  ↓
Step 10 (cross-surface parity)        354 golden cases × 4 surfaces;
                                      generator guard → implement
  ↓
Step 11 (AI narrative)                [ai]; BYOK; llm_use refusal; cost
                                      shown → implement
  ↓
Step 12 (service container)           Dockerfile; scan; image smoke
                                      → implement
  ↓
Step 13 (staging on Cloud Run)        WIF deploys, Secret Manager, edge,
                                      budget, health probe → implement
  ↓
Step 14 (1.0.0b1 readiness gate)      v1.0.0b1.devN on TestPyPI; staging,
                                      Inspector, agent tasks; GO / NO-GO
                                      → implement
  ↓
Step 15 (1.0.0b1 release)             v1.0.0b1 on PyPI; MCP Registry;
                                      quick-starts live → operate
  ↓
Step 16 (QA + verify-phase04.sh)      scripts/verify-phase04.sh
                                      + docs/phase04-qa-findings.md
                                      + phase-verify.yml matrix entry
                                      → create

--- post-implementation ---

V1   #157 closed with a concurrency regression; the audit recorded;
     main reads 1.0.0b1.dev1.
V2   ADR-0012 Accepted; every error class has a row; the surfaces core
     tested; core and data import no surface.
V3   registry.json validates against its schema and is deterministic;
     schema snapshots guard every model.
V4   The CLI runs, describes and binds every model; exit codes follow the
     table; keys never reach a sink.
V5   Each format carries attributions and the manifest; CSV and XLSX escape
     formula prefixes; a bundle reruns to identical bytes.
V6   /v1 routes cover every model; OpenAPI 3.1 snapshot stable; problems
     and budgets hold; local mode refuses a non-loopback bind.
V7   Hosted mode refuses library-only data with 403; limits, caching and
     the disable switch hold; Schemathesis finds no 5xx; clients build.
V8   MCP passes stdio and HTTP checks; tools/list snapshot stable;
     forbidden llm_use data never reaches a result.
V9   The chart renders in an MCP Apps client; server.json validates; agent
     tasks succeed.
V10  Every golden case returns identical bytes on four surfaces; no
     surface hand-writes a model.
V11  The narrative is off by default, refuses forbidden data and hosted
     mode, and shows its cost.
V12  The image builds, scans clean of Critical and High findings, and
     serves a model run as a non-root user.
V13  Staging /version reports main's SHA; the service token runs a model
     and fetches a hosted-safe series; library-only returns 403.
V14  Readiness evidenced, with the maintainer's GO; the rehearsal is on
     TestPyPI with attestations.
V15  1.0.0b1 on PyPI gives a working CLI and MCP server; the MCP Registry
     lists it; plain pip install still resolves 0.2.6.
V16  verify-phase04.sh --fast and --security exit 0 in phase-verify.yml;
     the staging alarm fired; Phases 1–3 stay green.
```

Steps are sequential by dependency, and this phase draws no steps in
parallel: every step after Step 2 edits `pyproject.toml`, `uv.lock` or the
shared surface modules, so concurrent branches would conflict, and the
Worktree rule's parallel case does not apply. Step 1 removes the one known
race before any surface runs models concurrently. Step 2's ADR fixes the
contract every later step encodes, and its surface core — `invoke`, the
error table, the codec and the envelope — is what Steps 4–11 call. Step 3's
`registry.json` is the description the CLI's help, the REST routes and the
MCP tools are generated from, and Phase 5's pages after them. Step 4's CLI
meets the error table and codec first; Step 5's exports give the CLI its
binary formats and the REST API its downloads. Step 6's app factory comes
before Step 7's hosted mode, whose clients and fuzzing read the
`openapi.json` Step 6 exports. Step 8's MCP server mounts in Step 6's app
and reuses `invoke`; Step 9 extends it. Step 10's parity suite needs all
four surfaces and the exports. Step 11's narrative consumes results only.
Step 12's image packages the finished app, Step 13 deploys it (after which
every merge to `main` redeploys staging), Step 14 rehearses the tree Steps
1–13 leave on `main`, Step 15 releases it only after the maintainer's GO,
and Step 16 follows Step 15.

---

## Step 1 — Surfaces Baseline and Concurrency Hardening ✅

**Status:** Complete — PR #175 (2026-10-23)

> **Goal:** Make the core safe for surfaces that run models concurrently in
> one process, and set the baseline the phase builds towards. Land this
> roadmap and the refreshed planning kit as the branch's first two commits;
> move `main` to `1.0.0b1.dev1` with `CITATION.cff` in step and an
> `[Unreleased]` section in `CHANGELOG.md`; close issue #157, so
> `core.library_warnings` (`src/pyeconomics/core/context.py`) attributes a
> wrapped library's warnings to the run that raised them and restores the
> global warning filters exactly, with a threaded regression test over the
> econometrics models; and audit the rest of the core and the data layer for
> process-global state that concurrent runs share — the registry's lazy
> discovery, `data.configure` overrides, the redaction log-record factory,
> the context variables behind `withheld`, `cache.memo()` and
> `cache.bypass()`, the cache store's connections and `core.random` —
> fixing in-step any race a Step 6 or Step 8 concurrent run would hit, and
> recording the audit in the PR body. No surface code and no dependency
> arrive yet, and no model's outputs change. Parent: issue #157; ROADMAP §4
> 4.4 ("runs execute in a worker pool") and 4.5; ADR-0008 decision 13.

**Branch:** `feature/phase04-step1-surfaces-baseline`

**Deploys:** nothing beyond merge — the version moves to `1.0.0b1.dev1`,
but this step pushes no tag and publishes nothing. Step 14 rehearses on
TestPyPI; Step 15 publishes the PyPI release.

| Setting      | Cost                                     | Balanced                             | Quality                                    |
| ------------ | ---------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                              | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort Medium | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                    | Antigravity                          | Claude Code                                |
| Effort       | Intelligence Low                         | Effort High                          | Effort High                                |
| AA Index     | 42.1                                     | 52.6                                 | 53.6                                       |
| Thinking     | —                                        | On                                   | —                                          |
| Conversation | **New**                                  | **New**                              | **New**                                    |

> Ran 2026-10-23: Quality column, also the Balanced column's Backup — Opus 5.5 · Effort High. The Runs rule selected Balanced (Antigravity pool headroom); the operator opened the step on Claude Code.

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: a version
move, a fix whose options issue #157 already lists, a threaded regression
test and a bounded audit of named modules, with every golden, property and
contract suite as the safety net. Complexity is Medium — the race is
understood and the audit's list is fixed — and the step is not novel. The
ladder's Balanced column runs: Gemini 4 Argon on Antigravity at Effort High
with Thinking on, funded by the Google AI Pro plan at $0 marginal. This is
Antigravity's first real use (`planning/user-context.md`): sign the `agy`
CLI into the funded personal account, not the Workspace account, before
starting, and record in the PR body which column ran. The Cost column is
GPT-6.1 Sol on Codex at Intelligence Low (ChatGPT Pro 5x, the lane with
slack; AA Intelligence Index 42.1 against Argon's 52.6), and Quality is
Opus 5.5 on Claude Code at Effort High (claude.ai Max; 53.6); each column's
backup comes from another maker. New conversation per phase-boundary
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
       feature/phase04-step1-surfaces-baseline`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - No dependency arrives. The concurrency fixes add no
      global state that an input could reach, and no lock
      is held across a network call or a cache write
      another thread waits on.
    - A library warning's text never carries a key: the
      threaded test plants canary keys in the environment
      and proves, with LeakCheck, that none reaches a
      result's warnings or a log record.
  </security>

  <context>
    pyeconomics. Phase 4. Step 1: surfaces baseline and
    concurrency hardening.

    Current state (as of Phase 3; no Phase 4 step has run):

    - main is at 42fdabd (PR #170) or later; ordinary
      Dependabot maintenance merges independently.
      pyproject.toml and CITATION.cff read 1.0.0a2;
      CHANGELOG.md's newest section is [1.0.0a2].
    - This roadmap (docs/roadmap/phase04-roadmap.md) is
      untracked, and planning/ holds roadmodel 0.2.92's kit
      (eight files modified by /roadmap-phase 4 on
      2026-10-23). Both carry over to the step branch.
    - Issue #157 (architecture, assigned to Phase 4):
      core.library_warnings wraps warnings.catch_warnings,
      which mutates process-global state, while
      collect_warnings keeps its collector in a ContextVar.
      econometrics.garch (over arch) and
      econometrics.time_series (over statsmodels) use it.
      The issue lists three options: serialize wrapped
      runs under a lock, run them in a process pool, or
      capture with a thread-local showwarning hook.
    - The REST API (Step 6) runs models in worker
      processes, but an MCP server over stdio runs tools in
      its own process, and a server may offload synchronous
      tools to threads, so two tool calls can run models
      concurrently in one process.
    - arch has no CPython 3.15 wheel (issue #154):
      econometrics.garch raises
      MissingOptionalDependencyError on the 3.15 cells, and
      tests/extra_gaps.py asserts that gap.

    Files to read (every file before drafting):
    - This roadmap's Overview (Version rule, Cross-phase
      verification rule) and Current State.
    - Issue #157 with its comments (`gh issue view 157
      --comments`).
    - src/pyeconomics/core/context.py, core/warnings.py,
      core/registry.py and core/random.py.
    - src/pyeconomics/models/econometrics/garch.py and
      time_series.py, with their tests and
      tests/extra_gaps.py.
    - src/pyeconomics/data/config.py, data/redaction.py,
      data/credentials/chain.py and data/cache/__init__.py
      and store.py.
    - tests/data/leakcheck.py and tests/config_isolation.py.
    - CHANGELOG.md, CITATION.cff and
      tests/unit/test_version.py.
  </context>

  <goal>
    The roadmap and kit are on main; main reads
    1.0.0b1.dev1; concurrent runs of the wrapped-library
    models keep their own warnings and leave the global
    filters as they found them; every other process-global
    state is audited, with each race a later step would hit
    fixed and tested; issue #157 closes with its regression
    test; no model's outputs change.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Land the roadmap first. After Stage 1, commit planning/
      as /roadmap-step §5 instructs (`chore(planning): refresh
      the roadmodel kit to 0.2.92`), then this file
      (`docs(roadmap): add the Phase 4 roadmap`), each signed
      off and gated, before any other change.
    </requirement>

    <requirement>
      Kickoff, one batched question to the maintainer: (a)
      the approach for #157 — recommended: a module-level
      re-entrant lock held for each library_warnings block,
      which serializes only wrapped library calls (a GARCH
      fit waits for another wrapped fit, never for an
      unwrapped model), documented on the function; the
      alternatives are Python 3.14's context-aware warnings
      (absent on 3.12 and 3.13, off by default on the
      standard build), a thread-local showwarning hook
      (which misses the filter changes a library makes) and
      a process per run; (b) whether audit findings beyond
      #157 that no Phase 4 step would hit are fixed here or
      issued (recommended: issued, with an owner). Record the
      answers in the PR body.
    </requirement>

    <requirement>
      Issue #157, in core/context.py: implement the chosen
      approach; collect_warnings is unchanged; a re-entrant
      lock means a nested wrapped call cannot deadlock.
      Add tests/unit/core/test_context_concurrency.py (a
      basename unique repo-wide): at least 8 threads run
      econometrics.time_series and, where arch installs,
      econometrics.garch, with inputs chosen so some runs
      raise a library warning and others do not; each
      result's warnings equal its single-threaded run, over
      at least 20 iterations; the warning filters after the
      threads equal those before. On the 3.15 cells the test
      asserts garch's gap through tests/extra_gaps.py, never
      a skip.
    </requirement>

    <requirement>
      The audit: for each item in this step's goal, state
      where the state lives, whether a concurrent run can
      observe it, and the verdict (safe, fixed here, or an
      issue with a number and the owning step). Fix in-step
      what Step 6's worker processes or Step 8's tool threads
      would hit, each with a threaded test under
      tests/unit/core/ or tests/data/ (the registry's first
      discovery from two threads at once; the redaction
      factory installed from two threads; resolve_key from
      several threads). data.configure's overrides are
      process-wide by design: document that a surface
      configures once at start (hosted mode, offline) and
      never per request. Put the audit table in the PR body.
    </requirement>

    <requirement>
      No output changes: every golden, property and contract
      suite passes unchanged, no model version moves, and
      `uv run --no-config python scripts/release_ledger.py
      --check` passes.
    </requirement>

    <requirement>
      Version (Version rule): `uv version 1.0.0b1.dev1
      --no-config`, CITATION.cff's version to match;
      tests/unit/test_version.py passes, and so do
      verify-phase01.sh check 44 and verify-phase02.sh check
      7, which hold the two in step.
    </requirement>

    <requirement>
      CHANGELOG.md: add `## [Unreleased]` above [1.0.0a2]
      with a "Fixed" entry for #157 and a "Changed" entry for
      the version. The PR body says `Closes #157`.
    </requirement>

    <requirement>
      Cross-phase verification rule: run
      `scripts/verify-phase01.sh --fast`,
      `scripts/verify-phase02.sh --fast` and
      `scripts/verify-phase03.sh --fast` before the PR; a
      check this step legitimately breaks is narrowed with an
      addendum line, never deleted.
    </requirement>

    <requirement>
      Stage 3, the phase's first step (Status rule): the same
      commit that marks this step sets this roadmap's
      phase-level Status line and the parent's `### Phase 4`
      Status line to `In progress` (the parent's as `In
      progress — phase04-roadmap.md`), and the parent's
      "Phase Complexity Summary" row for Phase 4 to
      `In progress`.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001).
    </requirement>
  </requirements>
</task>
```

### Step 1 acceptance criteria

- This roadmap and the refreshed planning kit reached `main` as the step
  branch's first two commits.
- Concurrent runs keep their own warnings: the threaded regression test (at
  least 8 threads, at least 20 iterations) passes on all twelve CI cells,
  the global warning filters are unchanged afterwards, and on the 3.15 cells
  garch's gap is asserted, not skipped. Issue #157 is closed.
- The PR body holds the audit table; every finding is fixed with a threaded
  test or exists as an issue with a number and an owning step.
- No model's outputs changed: every golden, property and contract suite
  passes, no model version moved, and the released-id ledger check passes.
- `pyproject.toml` and `CITATION.cff` read `1.0.0b1.dev1`, `CHANGELOG.md` has
  an `[Unreleased]` section, the full suite and the coverage floors pass on
  all twelve CI cells, and `verify-phase01.sh`, `verify-phase02.sh` and
  `verify-phase03.sh --fast` pass in `phase-verify.yml`.
- The phase is marked started: this roadmap's phase-level Status line and
  the parent's `### Phase 4` Status line read `In progress`, and the
  parent's "Phase Complexity Summary" row for Phase 4 reads `In progress`.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — no dependency was added, and the canary
  test proves no key reaches a result's warnings or a log record under
  concurrency.

---

## Step 2 — ADR-0012 Programmatic Surfaces and the Surface Core ✅

**Status:** Complete — PR #177 (2026-10-23)

> **Goal:** Fix the surface contract every later step encodes, and build the
> framework-free core the surfaces share. Write
> `docs/adr/0012-programmatic-surfaces.md` from the twenty decisions this
> roadmap's Overview drafts, each with its options, sources and access
> dates, for the maintainer to accept or amend in the pull request; build
> `src/pyeconomics/surfaces/` with `invoke.py` (the one invocation path:
> resolve the model, decode the inputs, bind through `pyeconomics.bind` when
> a `BindRequest` asks for live data, run), `problems.py` (the error table:
> every `PyeconomicsError` subclass, core's and the data layer's, to a slug,
> a title, an HTTP status and a CLI exit code, and an RFC 9457 `Problem`
> whose detail passes through redaction), `codec.py` (input decoding with
> size and depth limits), `envelope.py` (the canonical bytes and a short
> summary) and `budgets.py` (hosted budgets by `CostClass` and hosted size
> limits); add a `surfaces` coverage floor and a layering test that keeps
> `core/` and `data/` free of every surface and `import pyeconomics` free of
> every framework; generate `docs/problems.md` from the table at build time;
> and amend the parent roadmap where the ADR changes it — "Upstash Valkey"
> becomes Upstash Redis in §4 4.4 and the cost table, §4 4.7's staging
> sentence names the edge the ADR chooses, and §5 "Security controls by
> layer" stops promising hosted API keys in Phases 4–7, which §4 4.4 defers
> to Phase 8. No framework dependency arrives yet. Parent: ROADMAP §4
> 4.1–4.7; §5 "Model quality & governance" ("Parity") and "Security &
> privacy strategy"; ADR-0002, ADR-0003, ADR-0005, ADR-0006 and ADR-0008.

**Branch:** `feature/phase04-step2-adr-surface-core`

**Deploys:** nothing beyond merge — the Read the Docs `main` preview
rebuilds with `docs/problems.md`, as it does on every merge; Step 15
verifies the surface pages live.

| Setting      | Cost                                   | Balanced                                   | Quality                                    |
| ------------ | -------------------------------------- | ------------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                            | Opus 5.5                                   | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                  | Claude Code                                | Claude Code                                |
| Effort       | Intelligence Medium                    | Effort High                                | Effort XHigh                               |
| AA Index     | 47.8                                   | 53.6                                       | 56                                         |
| Thinking     | —                                      | —                                          | —                                          |
| Conversation | **New**                                | **New**                                    | **New**                                    |

> Ran 2026-10-23: Balanced column — Opus 5.5 · Effort High. The Runs line's column; the Claude weekly pool's dated reset (2026-10-13) had passed, so it read headroom.

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Planning is PRIMARY and coding SECONDARY: twenty
decisions that become public API at 1.0.0 (ADR-0003), from the CLI grammar
to the staging edge, plus the small framework-free modules that encode
them. Complexity is High — the decisions interact across four surfaces,
the data layer and the hosted service — but the step is not novel: every
decision has a drafted default and checked facts in this roadmap. The
ladder's Balanced column runs: Opus 5.5 on Claude Code at Effort High
(claude.ai Max), the strongest planning model the funded surfaces reach at
the rung this step needs (AA Intelligence Index 53.6). Quality raises it to
Effort XHigh (56.0) for the same model; Cost is GPT-6.1 Sol on Codex at
Intelligence Medium (ChatGPT Pro 5x; 47.8). The backup across columns is
Gemini 4 Argon on Antigravity at Effort High; Opus 5.5 always thinks, so
it has no Thinking toggle. New conversation per phase-boundary hygiene.

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
       feature/phase04-step2-adr-surface-core`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - A problem body never holds a key, a file path, a host
      or an upstream URL: a canary test raises each mapped
      error with a planted key, path and URL in its message
      and proves, with LeakCheck, that none survives into the
      problem's detail, the CLI message or a log record.
    - The codec is bounded: it refuses input above its size
      and depth limits before parsing further, refuses
      duplicate JSON keys, NaN and infinity, and never
      evaluates text (no eval, no YAML, no pickle); the
      semgrep rules stay green.
    - An exception that is not a PyeconomicsError maps to a
      generic internal-error problem whose detail is fixed
      text, never the exception's message, which may hold a
      path or a value.
  </security>

  <context>
    pyeconomics. Phase 4. Step 2: ADR-0012 programmatic
    surfaces and the surface core.

    Current state (post-Phase-4 Step 1):

    - main reads 1.0.0b1.dev1; #157 is closed and the
      concurrency audit is in Step 1's PR body.
    - No surfaces/ package exists. core/errors.py and
      data/errors.py hold the error taxonomy; core/runner.py
      holds run and run_model; data/bindings.py holds bind;
      core/results.py holds Result.to_json(); data/redaction.py
      holds the scrubbing every message passes through.
    - docs/adr/README.md lists ADR-0001 to ADR-0011, each
      Accepted; template.md is the format; an Accepted ADR is
      superseded, never edited.
    - This roadmap's Overview drafts the twenty decisions and
      records the facts behind them (PyPI and npm read on
      2026-10-23; the MCP 2026-07-28 changelog; the Python
      SDK's MCPServer; the MCP Registry's requirements;
      Cloudflare's plans; Cloud Run domain mapping; Upstash's
      pricing).

    Files to read (every file before drafting):
    - This roadmap's Overview (the surface contract, the
      drafted decisions, the surface, licence and credential
      rules) and Current State.
    - docs/adr/README.md, template.md, 0002, 0003, 0005,
      0006, 0008 and 0011.
    - src/pyeconomics/core/errors.py, data/errors.py,
      core/runner.py, data/bindings.py, core/results.py,
      core/canonical.py, core/spec.py (CostClass) and
      data/redaction.py.
    - scripts/checks/coverage_floors.py,
      tests/data/test_layering.py, docs/conf.py and
      docs/_ext/provider_pages.py (the generated-page
      pattern).
    - docs/roadmap/ROADMAP.md §4 4.4 and 4.7, §5 "Cost
      projection" and "Security controls by layer".
  </context>

  <goal>
    ADR-0012 Accepted with its decisions as the maintainer
    accepted or amended them; surfaces/ holds invoke, the
    error table, the codec, the envelope and the budgets,
    all tested and framework-free; the layering test and the
    surfaces coverage floor hold; docs/problems.md builds
    from the table; and the parent roadmap's three outdated
    sentences are amended.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Draft the ADR first (Status: Proposed), as this step's
      first commit after Stage 1. Then ask the maintainer ONE
      batched question listing every decision that needs a
      choice beyond its drafted default, each with the
      recommendation — at least decision 20 (the edge: a
      Cloudflare Worker, recommended, or Cloud Run domain
      mapping), decision 5 (the exit codes), decision 9 (the
      GET form of a run), decision 13 (the tool names) and
      decision 16 (the server name). Record amendments under
      "More information" while Proposed, then mark it
      Accepted with the date in its Date line and the index.
    </requirement>

    <requirement>
      docs/adr/0012-programmatic-surfaces.md follows
      template.md: context (Phase 4's surfaces; ADR-0003's
      public API at 1.0.0; ADR-0002's core cli/; ADR-0008
      decision 8; ADR-0006's Worker clause), decision
      drivers, the options per decision, the twenty numbered
      decisions, consequences, a Confirmation table naming
      the check and the Phase 4 step that builds each, and
      sources with access dates (the Overview's facts and
      dependency table). Facts that move carry a source and a
      date, or read TBD.
    </requirement>

    <requirement>
      src/pyeconomics/surfaces/invoke.py: `invoke(model_id,
      inputs=None, /, *, bind=None, mode=None) -> Result` and
      a frozen `BindRequest` (as_of, vintage, profile,
      concepts, parameters). It resolves aliases with the
      deprecation warning, decodes inputs through the codec,
      imports the data layer only when bind is given, and
      runs through core.runner. Tests over
      tests/registry/toy_models.py and the scripted providers
      of tests/data/bindings/bound_support.py: data-free and
      bound runs equal pyeconomics.run's bytes.
    </requirement>

    <requirement>
      src/pyeconomics/surfaces/problems.py: one table row per
      error class — slug, title, HTTP status, exit code —
      covering every subclass of PyeconomicsError in
      core/errors.py and data/errors.py, with the drafted
      mapping as ADR-0012 accepts it (InputError 422/3;
      DomainError and ConvergenceError 422/4; the not-found
      errors 404/5; LicenceError 403/6; CredentialError 503/7;
      TransportError and ResponseError 502/7; RateLimitError
      and OfflineError 503/7; MissingOptionalDependencyError
      501/8; anything else 500/1). `problem_for(error)`
      returns a Problem with `type`
      (https://pyeconomics.dev/problems/<slug>), `title`,
      `status`, a scrubbed `detail`, the exit code and, for
      InputError, the field errors without input values. A
      test walks every subclass and fails on a missing row.
    </requirement>

    <requirement>
      src/pyeconomics/surfaces/codec.py: decode a mapping,
      JSON text or bytes (limit 16 MiB locally, as ADR-0012
      accepts, because 1 MiB refuses valid full-length inputs;
      hosted mode passes 1 MiB; depth 32, duplicate keys
      refused), or `field=value` pairs typed by the
      model's input schema (numbers, strings, ISO dates, and
      arrays or objects as JSON literals; a boolean for a
      numeric field refused, as #75 fixed); validation is the
      model's own. envelope.py: the canonical bytes
      (`Result.to_json().encode()`), the weak ETag value
      (`W/"<result_sha256>"`) and a one-paragraph text summary.
      budgets.py: the hosted wall-clock budgets by CostClass
      (instant 2 s, light 10 s, heavy 30 s, as accepted), the
      hosted body limit and the 8 KiB limit for a run's GET
      form, in one place.
    </requirement>

    <requirement>
      Add tests/surfaces/test_surface_layering.py (a unique
      basename: tests/data/test_layering.py exists):
      no module under src/pyeconomics/core/ or data/ imports
      pyeconomics.surfaces, exports, cli, server, mcp or ai;
      surfaces/ imports no fastapi, starlette, uvicorn, mcp,
      cyclopts or rich; and a fresh interpreter's `import
      pyeconomics` loads none of them. Add ("surfaces",
      "/pyeconomics/surfaces/", 95.0) to
      scripts/checks/coverage_floors.py.
    </requirement>

    <requirement>
      docs/problems.md: generated at build time from the table
      by a docs extension beside provider_pages.py, offline;
      the page lists each slug, title, status and exit code
      under an anchor the type URI names.
    </requirement>

    <requirement>
      Parent roadmap amendments, in this PR: §4 4.4's "Upstash
      Valkey" and the cost table's row become Upstash Redis
      (with the 2026-10-23 pricing); §4 4.7's staging sentence
      names the accepted edge; §5 "Security controls by
      layer" reads "Phases 4–7: anonymous hosted access with
      per-IP limits, no accounts; staging behind Cloudflare
      Access", matching §4 4.4.
    </requirement>

    <requirement>
      Cross-phase verification rule: verify-phase01.sh checks
      17 and 18 must accept ADR-0012 in the index; run all
      three earlier verifiers' --fast before the PR.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001); the ADR follows docs/adr's
      convention.
    </requirement>
  </requirements>
</task>
```

### Step 2 acceptance criteria

- `docs/adr/0012-programmatic-surfaces.md` reads `Status: Accepted`, holds
  the numbered decisions as the maintainer accepted or amended them (each
  amendment recorded), and the ADR index lists it Accepted with its date.
- `surfaces/` holds `invoke`, `problems`, `codec`, `envelope` and `budgets`;
  `invoke` returns bytes equal to `pyeconomics.run`'s for data-free and bound
  toy runs; the surfaces coverage floor (95%) holds in CI.
- Every `PyeconomicsError` subclass has an error-table row, shown by the
  walking test; an unknown exception maps to a fixed-text internal error.
- The codec refuses oversized or over-deep JSON, duplicate keys, NaN,
  infinity and a boolean for a numeric field, and decodes `field=value`
  pairs by the model's schema.
- The layering test passes, and `docs/problems.md` builds offline in the
  `docs` job.
- The parent roadmap says Upstash Redis, names the accepted staging edge,
  and no longer promises hosted API keys before Phase 8.
- The full suite and the floors pass on all twelve cells, and the three
  earlier verifiers' `--fast` modes pass in `phase-verify.yml`.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the canary test proves no key, path,
  host or upstream URL survives into a problem body or a log record.

---

## Step 3 — Registry Export and Schema Snapshots

**Status:** Not started

> **Goal:** Publish the description every surface and the Phase 5 web app
> are generated from, and make an unintended schema change fail CI. Add
> `src/pyeconomics/surfaces/registry_export.py`, which builds and writes
> `registry.json` as canonical JSON: a format version, the package version
> and one entry per registered model, sorted by id, holding the
> `describe()` keys (the card's Markdown, the LaTeX formula, the citations,
> the input and output JSON Schemas, the examples, the bindings) plus
> `example_result` (the canonical result of the model's first example, run
> through `invoke` on its explicit inputs, never live data) and
> `example_figure` (the Plotly figure of that result's first applicable
> chart with its template removed, or null without the `plot` extra or a
> chart); add `surfaces/registry_schema.py`, the JSON Schema (2020-12) the
> document validates against, kept in a Python module because the wheel
> admits only `.py` files (`scripts/checks/dist_contents.py`); add syrupy
> snapshots of every model's input and output schemas, of the registry
> schema and of the id, version and domain index, so CI fails on any
> unintended change; and document the format in `docs/registry.md`. The CLI
> command arrives in Step 4 and `openapi.json` in Step 6. Parent: ROADMAP §4
> 4.1; ADR-0012 decision 8; ADR-0003 ("Model ids, input and output field
> names, units and their JSON Schemas" are public API at 1.0.0).

**Branch:** `feature/phase04-step3-registry-export`

**Deploys:** nothing beyond merge — `registry.json` is a build artifact,
written on demand and never committed; the Read the Docs `main` preview
rebuilds with `docs/registry.md`, and Step 15 verifies it live.

| Setting      | Cost                                     | Balanced                             | Quality                                    |
| ------------ | ---------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                              | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort Medium | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                    | Antigravity                          | Claude Code                                |
| Effort       | Intelligence Low                         | Effort High                          | Effort High                                |
| AA Index     | 42.1                                     | 52.6                                 | 53.6                                       |
| Thinking     | —                                        | On                                   | —                                          |
| Conversation | **New**                                  | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and planning SECONDARY: a
deterministic writer over `describe()`, a schema module and snapshot tests,
in a design ADR-0012 decision 8 fixes. Complexity is Medium — the work is
bounded, and determinism and the figure's size are the only subtle points
— and it is not novel. The ladder's Balanced column runs: Gemini 4 Argon on
Antigravity at Effort High with Thinking on (Google AI Pro; AA Intelligence
Index 52.6). Cost is GPT-6.1 Sol on Codex at Intelligence Low (ChatGPT Pro
5x; 42.1) and Quality Opus 5.5 on Claude Code at Effort High (claude.ai
Max; 53.6); each column's backup comes from another maker. New
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
       feature/phase04-step3-registry-export`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - registry.json holds no clock, host, user, path or
      environment value: a test exports into a temporary
      directory and scans the bytes for its path, the
      hostname and the user name, and two exports from
      different directories are byte-identical.
    - An example runs on its explicit inputs only, with
      sockets disabled: the export never binds live data and
      never reads a key.
  </security>

  <context>
    pyeconomics. Phase 4. Step 3: registry export and schema
    snapshots.

    Current state (post-Phase-4 Step 2):

    - ADR-0012 is Accepted; decision 8 fixes registry.json's
      shape. surfaces/ holds invoke, problems, codec,
      envelope and budgets.
    - core/describe.py returns the 23 DESCRIPTION_KEYS for a
      model; its docstring names registry.json "a list of
      these". pyeconomics.registry.describe imports the data
      layer only for a bound model's card.
    - core/plotting.py builds a Plotly figure from a result's
      ChartSpecs behind the plot extra. A default Plotly
      figure carries a template of tens of kilobytes.
    - syrupy and jsonschema are in the test group;
      scripts/checks/dist_contents.py admits only .py files,
      py.typed and dist-info metadata in the wheel.

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions 3 and
      8) and this roadmap's Surface rules.
    - src/pyeconomics/core/describe.py, core/cards.py,
      core/schema.py, core/plotting.py, core/canonical.py and
      surfaces/invoke.py.
    - scripts/checks/dist_contents.py, scripts/new_model.py,
      CONTRIBUTING.md and tests/golden/README.md.
    - tests/results/test_schema.py (the schema tests'
      pattern).
  </context>

  <goal>
    registry_document() and write_registry(path) produce a
    deterministic registry.json that validates against
    registry_schema.py; syrupy snapshots guard every model's
    schemas and the index; a new model without a snapshot,
    or a changed schema without an updated snapshot, fails
    CI; docs/registry.md documents the format.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      surfaces/registry_export.py: `registry_document(*,
      figures=True) -> dict` and `write_registry(path, *,
      figures=True) -> None`, writing canonical JSON bytes
      (core.canonical) as LF bytes, never through write_text.
      Top level: `format` (1), `pyeconomics` (the version),
      `models` (sorted by id). Each entry: the describe()
      keys, `example_result` (the first example's
      Result.to_dict() through invoke) and `example_figure`
      (core.plotting's figure for that result with
      layout.template removed, as JSON-ready values; null
      when plot is not installed or the model has no
      applicable chart). A model whose first example raises
      fails the export with its id named.
    </requirement>

    <requirement>
      surfaces/registry_schema.py: REGISTRY_SCHEMA, a JSON
      Schema 2020-12 dict with `$id`
      https://pyeconomics.dev/schemas/registry/1.json, every
      required key, and the per-model schemas referenced as
      objects; a test validates a fresh export against it
      with jsonschema.
    </requirement>

    <requirement>
      tests/surfaces/test_registry_snapshots.py (unique
      basename), with syrupy's JSON extension: one snapshot
      per registered model for its input schema and one for
      its output schema, one for REGISTRY_SCHEMA and one for
      the sorted (id, version, domain) index. A missing
      snapshot fails. CONTRIBUTING.md and new_model.py's
      closing message tell a contributor to run `uv run pytest
      tests/surfaces --snapshot-update` and to name a changed
      schema in CHANGELOG.md, since schemas are public API at
      1.0.0.
    </requirement>

    <requirement>
      Determinism tests: two exports in different temporary
      directories are byte-identical; the bytes contain no
      temporary path, hostname or user name; the export with
      figures=False omits nothing but the figures. A timing
      test records the export's wall time and keeps it under
      a generous bound (it runs every model's first example
      once).
    </requirement>

    <requirement>
      docs/registry.md: what registry.json holds, its format
      version, how Phase 5 consumes it, and the snapshot
      workflow; its Python example is Sybil-tested.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001); Markdown follows docs/'s
      convention.
    </requirement>
  </requirements>
</task>
```

### Step 3 acceptance criteria

- `registry_document()` covers every registered model, sorted by id, each
  with the `describe()` keys, `example_result` and `example_figure` (null
  where the extra or a chart is absent), and validates against
  `REGISTRY_SCHEMA`.
- Two exports from different directories are byte-identical and hold no
  path, hostname or user name.
- syrupy snapshots exist for every model's input and output schema, the
  registry schema and the index; deleting one, or changing a schema without
  updating it, fails the suite.
- `docs/registry.md` builds in the `docs` job, and its example passes
  Sybil.
- The full suite and the floors pass on all twelve cells.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the export reads no key and binds no
  live data (it runs with sockets disabled).

---

## Step 4 — The pyeconomics CLI

**Status:** Not started

> **Goal:** Give every model and every data source a command line that
> shell scripts, R and Excel Power Query can consume. Add Cyclopts as a core
> runtime dependency and `src/pyeconomics/cli/` with the console script
> `pyeconomics = "pyeconomics.cli:main"`: `models list|search|describe|run`,
> where `run`'s options are generated at run time from the model's input
> class (typed `--<field>` options, `--inputs FILE` or `-` for JSON, and
> `--as-of`, `--vintage`, `--profile`, `--concept FIELD=ID` and `--param
> NAME=VALUE` for a bound run) and every run goes through `surfaces.invoke`;
> `data search|get|describe|vintages|sources` over the Phase 3 data API,
> printing each frame's attribution and notices; `keys set|list|delete` on
> the OS keyring, with the value read from a hidden prompt or standard input
> and stored through new `data.credentials` functions, never an argument;
> `cache ls|info|clear|path`; `registry export --out DIR`; `--format
> table|json` (JSON being the canonical bytes plus one newline), `--out
> PATH`, UTF-8 output on every OS, stable exit codes from the error table,
> `--debug` and shell completion; and `docs/cli.md` with tested examples.
> The binary formats arrive in Step 5, `serve` in Step 6 and `mcp` in Step
> 8. Parent: ROADMAP §4 4.2; ADR-0012 decisions 1–5; ADR-0002 (the core
> includes `cli/`).

**Branch:** `feature/phase04-step4-cli`

**Deploys:** nothing beyond merge — the console script ships with the next
package build; Step 14 rehearses it on TestPyPI and Step 15 publishes it,
and the Read the Docs `main` preview rebuilds with `docs/cli.md`, which
Step 15 verifies live.

| Setting      | Cost                                    | Balanced                             | Quality                                    |
| ------------ | --------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                             | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort XHigh | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                   | Antigravity                          | Claude Code                                |
| Effort       | Intelligence High                       | Effort High                          | Effort XHigh                               |
| AA Index     | 50.2                                    | 52.6                                 | 56                                         |
| Thinking     | —                                       | On                                   | —                                          |
| Conversation | **New**                                 | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and planning SECONDARY: a command
tree generated from the registry at run time, typed options from pydantic
input classes, bound runs, five command groups, exit codes, completion and
a keyring write path that must never expose a key. Complexity is High —
many interacting concerns across the registry, the data layer and the
credential chain, and the grammar becomes public API at 1.0.0 — but the
patterns are known, so it is not novel. The ladder's Balanced column runs:
Gemini 4 Argon on Antigravity at Effort High with Thinking on (Google AI
Pro; AA Intelligence Index 52.6), backed by Opus 5.5 on Claude Code. Cost
is GPT-6.1 Sol on Codex at Intelligence High (ChatGPT Pro 5x; 50.2), and
Quality is Opus 5.5 on Claude Code at Effort XHigh (claude.ai Max; 56.0),
the column to choose if the key path's review needs the deepest rung. New
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
       feature/phase04-step4-cli`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - A key is never an argument, an option value or an
      environment echo: `keys set` reads it with getpass or
      from standard input (`--stdin`), wraps it in a Secret
      at once and stores it through data/credentials/ — the
      only code that reveals it (the secret-reveal rule).
      `keys list` prints each provider's key source by name
      (environment, dotenv, keyring or none), never a value.
      Canary tests with LeakCheck prove no key reaches
      stdout, stderr, a log record, an exception, a problem
      or shell completion output.
    - Error output is the problem's title and scrubbed
      detail; --debug adds a traceback that passes through
      the same redaction.
    - Input files and standard input are read through the
      codec's size limits; no command fetches a URL, runs a
      shell or evaluates text, and a data target is an id,
      never a URL.
    - Cyclopts and its closure pass the licences hook, and
      each is pure Python (ADR-0002's core rule).
  </security>

  <context>
    pyeconomics. Phase 4. Step 4: the pyeconomics CLI.

    Current state (post-Phase-4 Step 3):

    - surfaces/ holds invoke, the error table (exit codes),
      the codec, the envelope and registry_export;
      ADR-0012 decisions 1–5 fix the CLI's place, grammar
      and exit codes.
    - Step 3 built `registry_export.write_registry(path, *,
      figures=True)` (canonical bytes, no trailing newline),
      so `registry export --out DIR` writes
      `DIR/registry.json` with it and `--no-figures` passes
      `figures=False`; a failing first example raises
      `RegistryError` (`registry-error`, exit 1).
      Syrupy snapshots use `tests/json_snapshots.py`'s
      `LFJSONExtension`: the stock JSON extension writes
      CRLF on Windows.
    - No console script exists. The data API, the
      credential chain (KEYRING_SERVICE "pyeconomics",
      key_variable, has_key, the keyring extra) and the cache
      API (info, entries, clear, path) are Phase 3's; nothing
      writes to the keyring.
    - Facts read on 2026-10-23: cyclopts 5.3.0
      (Apache-2.0, pure Python) requires attrs,
      docstring-parser, rich and rich-rst (MIT), and rich
      requires markdown-it-py, mdurl and pygments; rich-rst
      2.2 no longer requires docutils. ci.yml's pyodide job
      installs the wheel and runs scripts/smoke.py in
      Pyodide 314.0.7.

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions 1–5,
      11) and this roadmap's Credential rule.
    - src/pyeconomics/surfaces/ (every module),
      registry.py, data/api.py, data/credentials/
      (chain.py, secret.py), data/cache/__init__.py and
      data/config.py.
    - tests/data/leakcheck.py, tests/config_isolation.py and
      tests/data/credentials/.
    - .github/workflows/ci.yml (package and pyodide jobs),
      scripts/smoke.py and scripts/checks/licences.py.
    - Cyclopts' documentation for dynamic commands, pydantic
      parameters and completion, read at kickoff.
  </context>

  <goal>
    `pyeconomics` runs, describes, searches and binds every
    registered model through surfaces.invoke; wraps the data
    API, the keyring and the cache; prints canonical JSON or
    a table; exits with the error table's codes; installs
    with the core wheel; and never exposes a key.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Dependency (Dependency rule): `uv add --no-config
      "cyclopts>=5.3"` as a runtime dependency (floor, no
      upper bound); its closure passes the licences hook and
      pip-audit; rich-rst's licence is read from its License
      field. `[project.scripts]` gains `pyeconomics =
      "pyeconomics.cli:main"`.
    </requirement>

    <requirement>
      src/pyeconomics/cli/: an app built on first use, so
      `import pyeconomics` imports neither Cyclopts nor rich
      (the layering test extends to say so). Commands:
      models list [--domain] [--format],
      models search TEXT [--limit], models describe ID
      [--format json|markdown], models run ID [--inputs
      FILE|-] [--<field> VALUE]... [--as-of DATE] [--vintage
      POLICY] [--profile NAME] [--concept FIELD=ID]...
      [--param NAME=VALUE]... [--format] [--out PATH];
      data search TEXT, data get TARGET [--start] [--end]
      [--as-of] [--vintage] [--provider], data describe
      TARGET, data vintages TARGET, data sources
      [--check-keys]; keys set|delete PROVIDER [--stdin],
      keys list; cache ls [--provider], cache info, cache
      clear [--provider], cache path; registry export --out
      DIR [--no-figures]; --version, --debug and completion.
      A model's run options are generated from its input
      class when `models run ID` is parsed, so `pyeconomics
      --help` stays fast.
    </requirement>

    <requirement>
      Output: --format json writes Result.to_json() bytes
      plus one newline (data commands write the frame's
      canonical JSON with its attributions); --format table
      renders a rich table on a terminal and plain text
      otherwise, with every attribution and notice below it;
      --out writes the exact bytes to a file. Output is UTF-8
      on every OS, including the Windows cells.
    </requirement>

    <requirement>
      Exit codes come only from surfaces.problems; usage
      errors exit 2; the problem's `cli_message` (its slug and
      scrubbed detail, ADR-0012 decision 5) goes to stderr,
      and `problems.report` is the only logging of a failure.
      A test drives one command into each code.
    </requirement>

    <requirement>
      Keys: add to data/credentials/ `store_key(provider,
      secret)`, `delete_key(provider) -> bool` and
      `key_source(provider) -> KeySource | None` (the source
      the chain would answer from, without returning the
      value); the CLI calls only these. set and delete need
      the keyring extra (exit 8 naming
      `pyeconomics[keyring]` otherwise); set validates with
      the existing key checks before storing. Tests run with
      the isolated fixture's in-memory keyring.
    </requirement>

    <requirement>
      Tests under tests/cli/ (unique basenames): in-process
      runs of every command group; `models run` over every
      registered model's first example equals
      Result.to_json(); a bound run over the scripted
      providers; one subprocess run of the installed console
      script per OS cell; the docs examples in docs/cli.md
      executed in-process; LeakCheck canaries over the keys
      commands; a startup-time test bounding `pyeconomics
      --version`. The pyodide job imports pyeconomics.cli
      and builds the app in Pyodide; ci.yml's package job and
      release-smoke.yml run `pyeconomics --version` and one
      `pyeconomics models run` from their clean venvs.
    </requirement>

    <requirement>
      docs/cli.md: installation (`pipx install --pre
      pyeconomics`, `uv tool install --prerelease allow
      pyeconomics`), the command tree, a data-free and a bound
      example, keys and cache, formats, exit codes and
      completion. Link it from docs/index.md's toctree.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001).
    </requirement>
  </requirements>
</task>
```

### Step 4 acceptance criteria

- `pyeconomics models run <id>` returns `Result.to_json()` bytes (plus one
  newline) for the first example of every registered model, and a bound run
  over recorded providers records its data sources.
- `models`, `data`, `keys`, `cache` and `registry export` work in-process
  and through the installed console script on every OS cell, with UTF-8
  output.
- Every exit code in the error table is produced by a test, and usage errors
  exit 2.
- `keys set` stores a key from a hidden prompt or standard input through
  `data.credentials`, `keys list` names sources only, and `keys delete`
  removes it; LeakCheck canaries find no key in any sink.
- `import pyeconomics` imports neither Cyclopts nor rich, the Pyodide job
  builds the CLI app, `pyeconomics --version` stays within its time bound,
  and the package job's clean venv runs the console script.
- `docs/cli.md` builds, and its examples pass.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, Cyclopts' closure through the licences
  hook — and no command accepts a key as an argument or prints one.

---

## Step 5 — Exports and Reproducibility Bundles

**Status:** Not started

> **Goal:** Let any result or series flow into other software with its
> provenance attached. Add `src/pyeconomics/exports/`: CSV (RFC 4180, UTF-8,
> LF, text cells quoted and prefixed with `'` when they start with `=`, `+`,
> `-`, `@`, a tab or a carriage return, numbers never escaped, and a leading
> `#` metadata block holding the attributions, required notices, terms URLs,
> versions and `result_sha256`), XLSX through openpyxl (already a runtime
> dependency) with `data` and `manifest` sheets and every string written as
> a string, Parquet and Arrow through pyarrow imported lazily with the
> manifest and attributions in schema metadata (ADR-0008 decision 8), and
> canonical JSON with the manifest embedded — for a `Result`, a
> `BatchResult` and a data frame alike; a deterministic reproducibility
> bundle (a stored, not deflated, zip with sorted entries and fixed
> timestamps) holding `result.json`, `inputs.json`, `request.json`,
> `manifest.json`, `ATTRIBUTION.txt`, `requirements.txt`, `reproduce.py`
> and `README.txt`, where `reproduce.py` reruns the result from the recorded
> inputs and checks `result_sha256`, and `--refetch` re-binds at the
> recorded as-of date and vintages; and the CLI's `--format
> csv|xlsx|parquet|arrow`, `--bundle PATH`, `models run --batch FILE` and
> `bundle check FILE`, which verifies a bundle without executing anything
> from it. A test per provider checks each required notice's exact wording
> in every format. Parent: ROADMAP §4 4.3; ADR-0012 decisions 6 and 7;
> ADR-0005 rule 2 and its Confirmation; ROADMAP §5 threat 6.

**Branch:** `feature/phase04-step5-exports-bundles`

**Deploys:** nothing beyond merge — the exports ship with the next package
build (Steps 14 and 15); the Read the Docs `main` preview rebuilds with
`docs/exports.md`, which Step 15 verifies live.

| Setting      | Cost                                     | Balanced                             | Quality                                    |
| ------------ | ---------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                              | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort Medium | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                    | Antigravity                          | Claude Code                                |
| Effort       | Intelligence Low                         | Effort High                          | Effort High                                |
| AA Index     | 42.1                                     | 52.6                                 | 53.6                                       |
| Thinking     | —                                        | On                                   | —                                          |
| Conversation | **New**                                  | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: five
writers over existing seams (`core.tables`, `Result.to_arrow()`,
`Result.attributions()`), a bundle format and its checker, with the rules
fixed by ADR-0012. Complexity is Medium — each format is well specified,
and the subtle parts (formula escaping that leaves numbers alone, bundle
determinism across zlib builds, a notice test per provider) are named here
— and it is not novel. The ladder's Balanced column runs: Gemini 4 Argon
on Antigravity at Effort High with Thinking on (Google AI Pro; AA
Intelligence Index 52.6). Cost is GPT-6.1 Sol on Codex at Intelligence Low
(ChatGPT Pro 5x; 42.1) and Quality Opus 5.5 on Claude Code at Effort High
(claude.ai Max; 53.6); each column's backup comes from another maker. New
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
       feature/phase04-step5-exports-bundles`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - Formula injection (ROADMAP §5 threat 6): a text cell
      starting with =, +, -, @, a tab or a carriage return is
      prefixed with ' in CSV and XLSX, a number is never
      escaped, and XLSX stores every string as a string,
      never a formula. Tests read each file back (pandas,
      openpyxl) and prove a hostile cell stays inert text and
      a negative number stays a number.
    - No export or bundle holds a key, a path, a host or the
      maintainer's environment: LeakCheck canaries cover
      every format and the bundle's members.
    - bundle check reads JSON members only, refuses a member
      name with a path separator or `..`, caps the member
      count and the uncompressed size before reading, and
      executes nothing from the bundle; docs/exports.md says
      that reproduce.py is code to read before running a
      bundle someone else made.
  </security>

  <context>
    pyeconomics. Phase 4. Step 5: exports and
    reproducibility bundles.

    Current state (post-Phase-4 Step 4):

    - The CLI prints table and json formats through
      surfaces.invoke; the error table maps
      MissingOptionalDependencyError to exit 8.
    - Result.to_arrow() puts the manifest's canonical JSON in
      the schema metadata (pyeconomics.manifest);
      to_parquet(path) writes it; Result.attributions()
      returns the attribution and notices of the data a run
      read; core.tables lays results out one row per run.
      pyarrow and polars are test-only (ADR-0008 decision 8).
    - openpyxl and defusedxml are runtime dependencies (Phase
      3 Step 7); xlrd reads legacy .xls.
    - tests/providers/test_notices.py holds each provider's
      exact notice; tests/providers/cassettes/ hold every
      provider's recorded responses.

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions 6
      and 7) and this roadmap's Licence rule.
    - src/pyeconomics/core/results.py, core/tables.py,
      core/manifest.py, core/runner.py (run_batch) and
      surfaces/invoke.py and codec.py.
    - src/pyeconomics/data/types.py (Series, Table, their
      metadata) and data/cache/policy.py (Fetched.source()).
    - tests/providers/test_notices.py,
      tests/providers/provider_contract.py and
      tests/data/leakcheck.py.
    - scripts/checks/dist_contents.py (the wheel admits only
      .py files: reproduce.py's text lives in a module).
  </context>

  <goal>
    pyeconomics.exports writes CSV, XLSX, Parquet, Arrow and
    JSON for results, batches and frames, each with its
    attributions, notices and manifest; bundles are
    deterministic and rerun to identical bytes in a fresh
    environment; the CLI exposes every format, --bundle,
    --batch and bundle check.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      src/pyeconomics/exports/ (module names that shadow no
      standard module, e.g. delimited.py, spreadsheet.py,
      columnar.py, document.py, bundle.py):
      `export(obj, format, target)` for a Result, a
      BatchResult or a data frame, where target is a path or
      a binary stream, and `write_bundle(result, target,
      request=None)`. Layout: core.tables' columns, arrays as
      canonical JSON text cells. Numbers in CSV use the
      shortest round-trip text, so a value reads back equal.
    </requirement>

    <requirement>
      CSV: the leading `#` block, one line each for the
      pyeconomics version, the model and its version (a
      result), result_sha256, every attribution, notice and
      terms URL; then the header row and the data, every text
      cell quoted. A test proves a text cell holding `#`, a
      comma, a quote, a newline and each formula prefix
      round-trips through `pandas.read_csv(path,
      comment="#")` exactly (prefix included) and that
      negative and exponent numbers stay numbers.
    </requirement>

    <requirement>
      XLSX: openpyxl's write-only workbook; the `data` sheet,
      and a `manifest` sheet listing the attributions and
      notices first, then the manifest's fields and each data
      record; strings stored with the string type and the
      same prefix escape; no formula anywhere (a test scans
      every cell's type).
    </requirement>

    <requirement>
      Parquet (.parquet) and Arrow IPC (.arrow): through
      pyarrow imported inside the writer; without it,
      MissingOptionalDependencyError names pyarrow (exit 8).
      Schema metadata holds pyeconomics.manifest,
      pyeconomics.attributions (canonical JSON list) and
      pyeconomics.version. The CLI writes a binary format to
      standard output only when it is not a terminal; a test
      pipes `pyeconomics models run <id> --format parquet`
      into pandas through io.BytesIO and gets the Python
      API's values and the manifest back.
    </requirement>

    <requirement>
      Bundles: ZIP_STORED members, sorted, with timestamp
      1980-01-01 and fixed permissions, so equal results give
      equal bytes on every OS; request.json records the bind
      request (as_of, vintage, profile, concepts,
      parameters); requirements.txt pins
      `pyeconomics==<version>` and the extras the model
      needs. reproduce.py (its text a string constant in a
      module) uses only the standard library until it imports
      pyeconomics, checks the installed version (printing the
      install command on a mismatch, exit 2), reruns
      pyeconomics.run(model_id, inputs) and compares
      result_sha256 (exit 0 or 1); `--refetch` re-binds from
      request.json and reports per field whether the value
      agrees, labelling revised data. A CI test builds a
      bundle, creates a fresh venv with the built wheel and
      runs reproduce.py there: identical bytes.
    </requirement>

    <requirement>
      CLI: --format csv|xlsx|parquet|arrow on models run and
      data get; --bundle PATH on models run; models run ID
      --batch FILE (CSV with a header of field names, or JSON
      Lines, through the codec's limits and an
      invoke_batch beside invoke); bundle check FILE.
    </requirement>

    <requirement>
      Notices (ADR-0005 Confirmation): for every registered
      provider, replay one recorded frame offline, export it
      in each format, and assert its attribution and each
      required notice appear verbatim (the CSV block, the
      XLSX manifest sheet, the schema metadata, the JSON
      manifest).
    </requirement>

    <requirement>
      docs/exports.md: each format, the CSV metadata block
      and how to read it, the escaping rule, Parquet and
      Arrow's pyarrow requirement, bundles and bundle check;
      examples Sybil-tested. Link it from docs/index.md.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001).
    </requirement>
  </requirements>
</task>
```

### Step 5 acceptance criteria

- `pyeconomics.exports` writes CSV, XLSX, Parquet, Arrow and JSON for a
  result, a batch and a data frame; every format carries the attributions,
  notices and manifest the decisions name.
- The CSV and XLSX exports escape formula prefixes in text cells and leave
  numbers alone, shown by read-back tests; no XLSX cell holds a formula.
- `pyeconomics models run … --format parquet` pipes into pandas with the
  Python API's values and the manifest in its metadata; without pyarrow, the
  binary formats exit 8 naming it.
- A bundle is byte-identical across runs and operating systems, and its
  `reproduce.py` reruns to identical bytes in a fresh environment built from
  the wheel; `bundle check` verifies a bundle while executing nothing from
  it and refuses unsafe member names and oversized archives.
- The per-provider notice test passes for every registered provider in every
  format.
- `docs/exports.md` builds, and its examples pass.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — formula injection is tested in CSV and
  XLSX, and LeakCheck finds no key in any export or bundle member.

---

## Step 6 — REST API: App Factory, Routes and Worker Pool

**Status:** Not started

> **Goal:** Serve every model and series over a versioned HTTP API that
> returns the Python API's bytes. Fill the `[server]` extra with FastAPI and
> uvicorn and add `src/pyeconomics/server/`: `create_app(*, mode, settings)`,
> one app factory for local and hosted modes; `/v1` routes generated from
> the registry at app creation — `GET /v1/models` (`?q=`, `?domain=`), `GET
> /v1/models/{id}`, a `POST /v1/models/{id}/run` per model whose request
> and response schemas are the model's own JSON Schemas (`core.schema`), the
> same run's `GET` form for small inputs (`?inputs=`, base64url canonical
> JSON, at most 8 KiB), `GET /v1/series/{target}`, `GET /v1/sources`, `GET
> /healthz` and `GET /version`; routes that read the raw body and pass it
> to `surfaces.invoke`, so validation and errors are the model's own;
> RFC 9457 problem details for every error through the error table;
> `?format=json|csv|xlsx|parquet|arrow|bundle` through the exports; runs
> executed in a pool of spawned worker processes under the budgets of
> `surfaces.budgets`, with a run past its budget terminated and answered
> with a problem; OpenAPI 3.1 written as `openapi.json` by `pyeconomics
> registry export` with a syrupy snapshot; `pyeconomics serve`, which binds
> 127.0.0.1 and refuses a non-loopback host unless `--allow-remote` is
> passed; and `docs/api.md`. Hosted mode's limits, caching and refusals
> arrive in Step 7. Parent: ROADMAP §4 4.1 and 4.4; ADR-0012 decisions
> 3, 4, 9, 10 and 11.

**Branch:** `feature/phase04-step6-rest-api`

**Deploys:** nothing beyond merge — the API ships in the `[server]` extra
with the next package build (Steps 14 and 15) and reaches staging in Step
13; the Read the Docs `main` preview rebuilds with `docs/api.md`, which
Step 15 verifies live.

| Setting      | Cost                                    | Balanced                             | Quality                                    |
| ------------ | --------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                             | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort XHigh | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                   | Antigravity                          | Claude Code                                |
| Effort       | Intelligence High                       | Effort High                          | Effort XHigh                               |
| AA Index     | 50.2                                    | 52.6                                 | 56                                         |
| Thinking     | —                                       | On                                   | —                                          |
| Conversation | **New**                                 | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and planning SECONDARY: routes
generated from the registry with each model's own schemas in an OpenAPI 3.1
document, canonical response bytes that bypass FastAPI's serializer,
problem details for every error, format negotiation, and a process pool
that enforces wall-clock budgets by terminating workers on every operating
system. Complexity is High — those concerns interact, and the paths and
schemas become public API at 1.0.0 — but each pattern is established, so
it is not novel. The ladder's Balanced column runs: Gemini 4 Argon on
Antigravity at Effort High with Thinking on (Google AI Pro; AA Intelligence
Index 52.6), backed by Opus 5.5 on Claude Code. Cost is GPT-6.1 Sol on
Codex at Intelligence High (ChatGPT Pro 5x; 50.2) and Quality Opus 5.5 on
Claude Code at Effort XHigh (claude.ai Max; 56.0). New conversation per
phase-boundary hygiene.

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
       feature/phase04-step6-rest-api`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - No route accepts a URL, a host or a provider key, and
      none fetches anything a caller names: a series target
      is a concept id or a provider:series key, resolved by
      the data layer's host allowlists.
    - Local mode binds 127.0.0.1 by default; a non-loopback
      host is refused unless --allow-remote is passed, and
      then the server logs a warning that every source the
      user can access is exposed. A test proves the refusal.
    - A problem body and a server log line hold no key, path,
      host or upstream URL (the error table's redaction,
      LeakCheck over the server's log records), and an
      unexpected exception answers 500 with fixed text.
    - Messages between the app and its worker processes hold
      only bytes, strings, numbers and plain mappings the app
      built; the unsafe-deserialization rule stays green.
    - The interactive API docs (which load scripts from a
      CDN) are served in local mode only.
    - FastAPI's and uvicorn's closures pass the licences hook
      and pip-audit.
  </security>

  <context>
    pyeconomics. Phase 4. Step 6: REST API, app factory,
    routes and worker pool.

    Current state (post-Phase-4 Step 5):

    - surfaces/ holds invoke (and invoke_batch), the error
      table, the codec, the envelope, the budgets and
      registry_export; the CLI and pyeconomics.exports exist.
    - The server extra is an empty list. Facts read on
      2026-10-23: fastapi 0.162.0 (MIT) requires starlette,
      pydantic, typing-extensions, typing-inspection,
      annotated-doc and now opentelemetry-api; uvicorn
      0.54.0 (BSD-3-Clause) requires click and h11; all pure
      Python. Starlette's TestClient needs httpx (test only).
    - core/schema.py builds each model's input and output
      JSON Schemas (2020-12); data.api.get resolves a series
      target; data.api.sources lists providers.
    - Step 1 audited the process-wide state concurrent runs
      share (its pull request holds the table) and closed
      #157: core.library_warnings' blocks take turns under a
      re-entrant lock and record only their own thread's
      warnings. data.configure's overrides are process-wide
      by design, so the app factory sets hosted mode and
      offline once, at start, and never per request.

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions 3,
      4, 9, 10 and 11) and this roadmap's Surface rules.
    - src/pyeconomics/surfaces/ (every module), exports/,
      cli/ and registry.py.
    - src/pyeconomics/core/schema.py, core/results.py and
      data/api.py.
    - tests/registry/toy_models.py and
      tests/data/bindings/bound_support.py.
    - FastAPI's and Starlette's documentation for
      lifespans, exception handlers, raw-body routes and
      openapi_extra, read at kickoff.
  </context>

  <goal>
    `pip install "pyeconomics[server]"` then `pyeconomics
    serve` gives a local /v1 API whose run responses are
    Result.to_json() bytes, whose errors are RFC 9457
    problems from the error table, whose downloads are the
    exports, whose runs execute in budgeted worker processes,
    and whose OpenAPI 3.1 document is exported and
    snapshotted.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Dependencies (Dependency rule): `[server]` gains
      `fastapi>=0.162` and `uvicorn>=0.54` (no [standard]);
      both join `[all]` and the test group; the test group
      gains `httpx` for TestClient. Every package passes the
      licences hook (a reviewed exception for any that does
      not, approved by the maintainer) and pip-audit.
    </requirement>

    <requirement>
      src/pyeconomics/server/: create_app(*, mode, settings)
      builds the routes from the registry at creation; a run
      route reads the raw body (or the decoded ?inputs=),
      calls invoke in the pool, and returns the canonical
      bytes with application/json, never re-serialized; the
      OpenAPI document carries each model's own request and
      response schemas (openapi_extra), one operation per
      model with an operationId derived from the id; GET
      /v1/models/{id} returns registry.describe's canonical
      JSON; /v1/series/{target} wraps data.get with start,
      end, as_of, vintage and provider; /healthz returns
      {"status": "ok"}; /version returns the package version,
      PYECONOMICS_GIT_SHA (or "unknown") and the mode.
    </requirement>

    <requirement>
      Problems: exception handlers send every error through
      surfaces.problems as application/problem+json,
      including FastAPI's own validation, unknown routes and
      methods; a test drives each table row.
    </requirement>

    <requirement>
      Formats: ?format= routes a run or a series through
      pyeconomics.exports with the right Content-Type and an
      attachment Content-Disposition; a missing pyarrow
      answers 501 naming it.
    </requirement>

    <requirement>
      Worker pool (server/pool.py): N spawned worker
      processes (PYECONOMICS_WORKERS, default the CPU count;
      0 runs inline, for tests), created in the app's
      lifespan, never at import; one task at a time per
      worker; a bounded queue that answers 503 when full; in
      hosted mode each run is held to its CostClass budget
      and a run past it is terminated, its worker replaced,
      and a problem returned; local mode has no budget unless
      configured. Tests on every OS cell prove the budget
      kill, the replacement and the queue limit with toy
      models that sleep.
    </requirement>

    <requirement>
      `pyeconomics serve [--host] [--port] [--workers]
      [--allow-remote]` (local mode): 127.0.0.1 by default;
      a host that is not a loopback address is refused (exit
      2) unless --allow-remote; the command needs the server
      extra (exit 8 otherwise). Hosted mode is never started
      by serve: the container runs uvicorn directly (Step 12).
    </requirement>

    <requirement>
      OpenAPI: `pyeconomics registry export --out DIR` also
      writes openapi.json (canonical bytes) when the server
      extra is installed; tests/server/test_openapi_snapshot.py
      snapshots it with syrupy (through `tests/json_snapshots.py`'s
      `LFJSONExtension`, as Step 3's schema snapshots do), and a
      Dependabot bump of
      FastAPI that changes it fails until the snapshot is
      updated in that PR.
    </requirement>

    <requirement>
      Tests under tests/server/ (unique basenames), with
      TestClient: every registered model's first example
      through POST and GET equals Result.to_json(); describe,
      search, series (over recorded responses), sources,
      healthz, version; each format; the bind guard; LeakCheck
      over the server's logs and problems.
    </requirement>

    <requirement>
      docs/api.md: local mode quick start (`pip install --pre
      "pyeconomics[server]"`, `pyeconomics serve`, curl
      examples), the routes, problems and their types,
      formats, budgets, and a pointer to hosted mode (Step 7).
      Link it from docs/index.md.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001).
    </requirement>
  </requirements>
</task>
```

### Step 6 acceptance criteria

- `pyeconomics serve` serves `/v1` locally; every registered model's first
  example through `POST` and the `GET` form returns `Result.to_json()`
  bytes, and describe, search, series, sources, `healthz` and `version`
  work.
- Every error reaches the caller as an RFC 9457 problem from the error
  table, including FastAPI's own validation errors and unknown routes.
- `?format=` returns each export with the right media type; Parquet and
  Arrow answer 501 naming pyarrow when it is absent.
- The worker pool terminates a run past its hosted budget, replaces the
  worker and answers with a problem, and a full queue answers 503, on every
  OS cell.
- `pyeconomics serve` refuses a non-loopback host without `--allow-remote`.
- `pyeconomics registry export` writes `openapi.json` (OpenAPI 3.1, each
  model's own schemas), and its syrupy snapshot is stable.
- `docs/api.md` builds; the full suite and the floors pass on all twelve
  cells.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, the `[server]` closure through the licences
  hook — no route accepts a URL or a key, and LeakCheck finds no key in a
  problem or a log record.

---

## Step 7 — Hosted Mode, API Fuzzing and Generated Clients

**Status:** Not started

> **Goal:** Make the API safe to host and prove its OpenAPI document is
> honest. In hosted mode (`PYECONOMICS_MODE=hosted`): the data layer's
> refusal reaches the caller as a 403 problem naming the licence class and
> the terms page; per-client limits use the `limits` library with Redis
> storage on Upstash Redis (the URL a secret, `PYECONOMICS_RATELIMIT_URL`)
> and memory storage locally and in tests, answering 429 with `Retry-After`;
> an edge credential (`PYECONOMICS_EDGE_CREDENTIAL`), when configured, is
> required on every `/v1` and `/mcp` request, and only then is the client
> address read from `CF-Connecting-IP`; oversized bodies answer 413 and
> over-budget inputs 422, each pointing to local mode; GET runs carry `ETag`
> and `Cache-Control` from an in-process cache, POST runs and problems are
> `no-store` and never cached; and a provider disable switch
> (`PYECONOMICS_DISABLED_PROVIDERS`, issue #162) is honoured before any
> cache read or request. Prove it with an SSRF test over every route, a
> burst test, and Schemathesis against `openapi.json` in both modes (a
> dedicated `api-fuzz` job on Python 3.14 under the Wheel rule); and
> generate the TypeScript client (`@hey-api/openapi-ts` in `tools/node/`)
> and the Python client (`openapi-python-client`) from the same document,
> each smoke-tested against a local server in a `clients` job. Parent:
> ROADMAP §4 4.1, 4.4 and §5 threats 2 and 3; ADR-0012 decisions 10–12 and
> 18; issue #162.

**Branch:** `feature/phase04-step7-hosted-mode-clients`

**Deploys:** nothing beyond merge — hosted mode reaches staging in Step 13;
the generated clients are CI artifacts, never committed or published in
this phase.

| Setting      | Cost                                    | Balanced                             | Quality                                    |
| ------------ | --------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                             | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort XHigh | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                   | Antigravity                          | Claude Code                                |
| Effort       | Intelligence High                       | Effort High                          | Effort XHigh                               |
| AA Index     | 50.2                                    | 52.6                                 | 56                                         |
| Thinking     | —                                       | On                                   | —                                          |
| Conversation | **New**                                 | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and agentic SECONDARY: rate limits,
an edge trust boundary, budget refusals, cache semantics, a data-layer
switch, fuzzing and two client generators driven from CI. Complexity is
High and security-sensitive — threats 2 and 3 concentrate here — but the
design is ADR-0012's, so it is not novel. The ladder's Balanced column
runs: Gemini 4 Argon on Antigravity at Effort High with Thinking on (Google
AI Pro; AA Intelligence Index 52.6), backed by Opus 5.5 on Claude Code.
Cost is GPT-6.1 Sol on Codex at Intelligence High (ChatGPT Pro 5x; 50.2)
and Quality Opus 5.5 on Claude Code at Effort XHigh (claude.ai Max; 56.0),
the column to prefer if the Redis and edge paths need a second review. New
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
       feature/phase04-step7-hosted-mode-clients`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - SSRF (threat 3): a test enumerates every operation and
      parameter in openapi.json, sends URL-shaped values
      (including link-local and loopback addresses) to each,
      and proves through a recording transport that no
      request leaves for a host outside the data layer's
      allowlists.
    - Cost exhaustion (threat 2): limits, the body limit, the
      GET-form limit, the hosted budgets and the queue limit
      each have a test; the burst test proves 429 with
      Retry-After once a limit is reached.
    - The edge credential and the Redis URL are secrets:
      read from the environment Cloud Run fills from Secret
      Manager, registered with redaction, compared in
      constant time, never logged or echoed; a request
      without the credential gets 403 with fixed text, and
      CF-Connecting-IP is ignored unless the credential
      matched, so a direct request cannot spoof its address.
    - A POST run's inputs are never cached, logged or stored
      (ADR-0005: user-supplied data is processed in memory
      for one run); a test proves the cache holds no POST
      result.
    - The Node workspace commits its lockfile, installs with
      `npm ci`, and passes `npm audit --audit-level=high`,
      added to the gate; Dependabot gains the npm ecosystem.
  </security>

  <context>
    pyeconomics. Phase 4. Step 7: hosted mode, API fuzzing
    and generated clients.

    Current state (post-Phase-4 Step 6):

    - server/ builds /v1 from the registry, returns canonical
      bytes, answers problems, runs in a budgeted pool, and
      exports openapi.json; `pyeconomics serve` guards
      loopback.
    - Hosted mode exists in the data layer (require_allowed,
      the resolver's originator-only rule); the app does not
      yet rate-limit, cache or trust an edge.
    - Issue #162 (architecture): providers have no switch to
      disable one failing source; check_configuration runs
      before a cache read and any request.
    - Facts read on 2026-10-23: limits 5.8.0 (MIT) with
      extras redis (redis-py below 8) and valkey; Upstash
      Redis speaks the Redis protocol over TLS (500,000
      commands a month free); Cloudflare's free plan has one
      rate rule (10-second window, per IP); schemathesis
      4.32.4 requires PyYAML, which has no CPython 3.15
      wheel; @hey-api/openapi-ts 0.99.0 (Node 22.18 or
      later); openapi-python-client 0.29.1 (MIT).

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions
      10–12, 18 and 20) and this roadmap's Wheel and
      Credential rules.
    - src/pyeconomics/server/ (every module),
      surfaces/budgets.py and problems.py.
    - src/pyeconomics/data/modes.py, data/config.py,
      data/providers/base.py (check_configuration),
      data/resolver.py and data/redaction.py.
    - Issue #162 with its comments.
    - .github/workflows/ci.yml, .github/dependabot.yml and
      .pre-commit-config.yaml.
  </context>

  <goal>
    Hosted mode refuses library-only data with a 403 that
    explains the licence, limits and caches as ADR-0012
    decides, trusts the edge only through its credential,
    honours the disable switch, survives Schemathesis with no
    5xx and no schema violation, and feeds two generated
    clients that call it successfully.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Dependencies: `[server]` gains `limits[redis]>=5.8`
      (its closure through the licences hook and pip-audit);
      a `fuzz` dependency group holds `schemathesis>=4.32` with
      the marker `python_full_version < '3.15'` under the
      Wheel rule (maintainer approval in the PR, an issue to
      drop the marker when PyYAML ships CPython 3.15 wheels);
      a `clients` group holds `openapi-python-client>=0.29`.
      tools/node/package.json pins @hey-api/openapi-ts and
      typescript with a committed package-lock.json.
    </requirement>

    <requirement>
      Hosted refusal: a series or bound run on a source not
      classed hosted-safe or user-supplied answers 403
      (LicenceError's row) with a detail naming the source's
      class and its terms page, and never fetches; a test per
      licence class (library-only, byok, premium-local)
      proves it, and hosted mode answers no route that
      exposes keys or the cache.
    </requirement>

    <requirement>
      Limits (server/limits.py): per-client limits on runs,
      series and metadata as ADR-0012 sets them; Redis
      storage from PYECONOMICS_RATELIMIT_URL in hosted mode,
      memory storage otherwise; 429 with Retry-After and the
      limit's reset; a Redis outage fails closed for runs and
      series (503) and is logged without the URL. The burst
      test drives a low limit concurrently and counts the
      429s.
    </requirement>

    <requirement>
      Edge trust (server/edge.py): when
      PYECONOMICS_EDGE_CREDENTIAL is set, /v1 and /mcp
      require the X-Pyeconomics-Edge header to match in
      constant time (403 otherwise), /healthz and /version
      stay open, and CF-Connecting-IP becomes the client
      address only after a match.
    </requirement>

    <requirement>
      Budgets and caching: bodies above the hosted limit
      (`surfaces.budgets.HOSTED_BODY_LIMIT`, 1 MiB) 413
      (`input-too-large`, raised as the codec's
      `InputTooLargeError`); inputs above a hosted budget 422
      with a detail that gives the local command; a run
      terminated at its budget 422 (`budget-exceeded`, raised
      as `surfaces.budgets.BudgetExceededError`, which Step 2
      added to the error table) with the same pointer. GET
      runs: an in-process cache bounded by entries and bytes,
      keyed as decision 12 says, with the weak ETag
      `envelope.etag` writes (`W/"<result_sha256>"`, as
      ADR-0012 accepts), If-None-Match → 304 and
      Cache-Control; POST runs and problems no-store and never
      cached.
    </requirement>

    <requirement>
      Issue #162 (Contract-change rule, data layer): a
      disabled_providers setting (PYECONOMICS_DISABLED_PROVIDERS)
      that check_configuration enforces before any cache read
      or request, that the resolver fails over from, and that
      sources() reports; a new SourceDisabledError(DataError)
      with its error-table row (503, source-disabled). Every
      provider, concept and binding test stays green. The PR
      body says `Closes #162`.
    </requirement>

    <requirement>
      Fuzzing: an api-fuzz job in ci.yml (Ubuntu, Python
      3.14, `uv sync --locked --group fuzz`) runs Schemathesis
      against the ASGI app in local and hosted modes (limits
      off, a fixed seed and example budget): no server error,
      response schema and status-code conformance, content
      type conformance. The job joins the test aggregate; a
      test asserts the fuzz group's 3.15 gap on those cells.
    </requirement>

    <requirement>
      Clients: a clients job (Ubuntu, Node 22, Python 3.14)
      exports openapi.json, generates the TypeScript client
      into tools/node/generated/ (git-ignored) and runs tsc
      --noEmit, generates the Python client into a temporary
      directory, then starts `pyeconomics serve` and calls one
      data-free model through each client, comparing the
      bytes with the Python API's. The job joins the test
      aggregate. Add the npm-audit hook to
      .pre-commit-config.yaml and the npm ecosystem
      (/tools/node) to .github/dependabot.yml.
    </requirement>

    <requirement>
      docs/api.md: a hosted-mode section (what it refuses,
      limits, caching, budgets) and a clients section.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001); YAML `# <path>`;
      package.json allows no comment.
    </requirement>
  </requirements>
</task>
```

### Step 7 acceptance criteria

- In hosted mode, a request for a library-only, bring-your-own-key or
  premium-local source answers 403 with a detail naming its licence class
  and terms page, and makes no request (a test per class).
- The burst test proves 429 with `Retry-After`; the body limit answers 413
  and over-budget inputs 422, each with a pointer to local mode; a run
  terminated at its budget answers 422.
- GET runs carry `ETag` and `Cache-Control` and answer 304 on a match; POST
  runs and problems are `no-store`, and the cache never holds a POST result.
- With the edge credential configured, a request without it answers 403, and
  `CF-Connecting-IP` is honoured only after a match.
- `PYECONOMICS_DISABLED_PROVIDERS` disables a source before any cache read
  or request, the resolver fails over, and issue #162 is closed.
- The `api-fuzz` job finds no server error and no schema, status-code or
  content-type violation in either mode, and the fuzz group's 3.15 gap is
  asserted.
- The `clients` job generates and type-checks the TypeScript client,
  generates the Python client, and both return the Python API's bytes from a
  local server.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, `npm audit` clean — the SSRF test finds no
  request to an unlisted host, and no secret appears in a log or a problem.

---

## Step 8 — MCP Server

**Status:** Not started

> **Goal:** Let AI assistants discover and run every model through the
> Model Context Protocol without hundreds of tools, and keep restricted data
> out of their context. Fill the `[mcp]` extra with the official SDK
> (`mcp>=2.3`, `MCPServer`) and add `src/pyeconomics/mcp/`: a server built
> from the registry on the 2026-07-28 specification, served over stdio by
> `pyeconomics mcp` (runnable as `uvx --from "pyeconomics[mcp]" pyeconomics
> mcp`) and as a stateless Streamable HTTP app the server factory mounts at
> `/mcp`; the discovery tools `search_models`, `describe_model` (schemas and
> card), `run_model`, `get_series` and `list_sources`, plus 10–20 headline
> tools generated from a declared list of model ids
> (`mcp/headline.py`), named `<domain>_<name>`; an `outputSchema` on every
> tool, results as structured content with the canonical JSON as text,
> tools in a deterministic order, and a large result returned as a summary
> with a link to the REST download; the `llm_use` gate — a policy threaded
> through `surfaces.invoke`, `pyeconomics.bind`, `data.get` and the resolver
> (a new skip reason), so a `forbidden` source is passed over at resolution
> and an `unclear` one is used only with the user's out-of-band opt-in, with
> a final check that withholds any result still carrying such a record; a
> syrupy snapshot of `tools/list`; MCP Inspector checks over stdio and
> HTTP in CI; the scripted agent tasks; and `docs/mcp.md`. Parent: ROADMAP
> §4 4.5 and §5 threat 7; ADR-0012 decisions 13 and 14; ADR-0005.

**Branch:** `feature/phase04-step8-mcp-server`

**Deploys:** nothing beyond merge — the server ships in the `[mcp]` extra
with the next package build (Steps 14 and 15), and `/mcp` reaches staging
with the app in Step 13; the Read the Docs `main` preview rebuilds with
`docs/mcp.md`, which Step 15 verifies live.

| Setting      | Cost                                       | Balanced                             | Quality                                    |
| ------------ | ------------------------------------------ | ------------------------------------ | ------------------------------------------ |
| Model        | Sonnet 5.5                                 | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Gemini 4 Argon — Antigravity · Effort High | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Claude Code                                | Antigravity                          | Claude Code                                |
| Effort       | Effort XHigh                               | Effort High                          | Effort XHigh                               |
| AA Index     | 51.9                                       | 52.6                                 | 56                                         |
| Thinking     | —                                          | On                                   | —                                          |
| Conversation | **New**                                    | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and planning SECONDARY: an MCP
server on a specification revision three months old (stateless, no
initialize handshake, `server/discover`, required cache hints), generated
tools with JSON Schema 2020-12 inputs and outputs, a data-layer policy seam
and its defence-in-depth check. Complexity is High and the step is novel:
the stateless revision, the discovery-tool design and the `llm_use` gate
have no precedent in this repository. The ladder's Balanced column runs:
Gemini 4 Argon on Antigravity at Effort High with Thinking on (Google AI
Pro; AA Intelligence Index 52.6), backed by Opus 5.5 on Claude Code. For
novel work the Cost column becomes Sonnet 5.5 on Claude Code at Effort
XHigh (claude.ai Max; 51.9), and Quality is Opus 5.5 on Claude Code at
Effort XHigh (56.0). New conversation per phase-boundary hygiene.

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
       feature/phase04-step8-mcp-server`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - Tool output is data, never instructions (ROADMAP §5
      threat 7): results are the canonical JSON and a fixed
      template summary; no result or description carries an
      imperative aimed at the assistant; a test scans every
      description and summary template.
    - No tool executes code, fetches a URL, writes a file,
      reads or stores a key, or changes the cache: targets
      are ids validated against the registry and the catalog.
    - The llm_use opt-in is configuration only
      (pyeconomics.toml or PYECONOMICS_ALLOW_UNCLEAR_LLM_USE),
      read at server start, never a tool argument, so an
      assistant cannot opt itself in; a test calls every tool
      with every argument it accepts and proves a forbidden
      source never reaches a result.
    - The [mcp] closure passes the licences hook: cffi's
      reviewed exception now names [mcp] in its reason, and
      pywin32's licence file is read for a reviewed exception
      the maintainer approves; pip-audit stays clean.
  </security>

  <context>
    pyeconomics. Phase 4. Step 8: MCP server.

    Current state (post-Phase-4 Step 7):

    - surfaces.invoke serves the CLI and the REST API;
      server/ mounts routes, limits, the edge check and the
      pool; hosted mode refuses library-only data.
    - DataSource records carry llm_use; the resolver has no
      llm_use skip reason. FRED (and some SDMX series) is
      forbidden; BEA, BLS, CBO, Census, the Fed Board, the
      New York Fed, OpenFIGI, the Penn World Table, SEC
      EDGAR, Treasury and the World Bank are allowed; the
      regional Fed research, DBnomics and finance research
      sources are unclear. macro.policy_rule binds FRED first
      in library mode, so without the gate's skip its
      past-date run would be withheld.
    - Facts read on 2026-10-23: mcp 2.3.0 (MIT) exports
      MCPServer and a Client; the 2026-07-28 revision
      removes the initialize handshake and sessions, adds
      server/discover, says tools/list SHOULD be
      deterministic, requires resultType and the ttlMs and
      cacheScope hints, and allows any JSON Schema 2020-12
      keyword in inputSchema and outputSchema. Its closure
      adds httpx2 and httpcore2 (on truststore, not
      certifi), pyjwt[crypto] with cryptography and cffi,
      jsonschema with rpds-py, sse-starlette,
      python-multipart, mcp-types, opentelemetry-api and, on
      Windows, pywin32; each has CPython 3.15 wheels or is
      pure Python. The MCP Inspector is 2.12.0 on npm.
    - Since Step 1 (#157), two tools may run models on
      threads of one process: core.library_warnings' blocks
      take turns under a re-entrant lock and record only
      their own thread's warnings, and while one runs,
      another thread's warnings pass the "always" filter
      (#174).
      data.configure is process-wide: the MCP server sets
      its mode once, at start, never per tool call.

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions 13
      and 14) and this roadmap's Licence rule.
    - src/pyeconomics/surfaces/ (every module), server/app.py
      and server/edge.py.
    - src/pyeconomics/data/bindings.py, data/api.py,
      data/resolver.py, core/provenance.py (LlmUse) and
      data/config.py.
    - tests/data/catalog/ and tests/data/bindings/ (the
      resolver and binding test harnesses).
    - The SDK's documentation (servers, tools, structured
      output, stateless Streamable HTTP, Client) and the
      2026-07-28 specification's tools and transport pages,
      read at kickoff.
  </context>

  <goal>
    `pyeconomics mcp` and /mcp expose the discovery and
    headline tools with output schemas in a stable order;
    run_model returns Result.to_json()'s object; the llm_use
    gate keeps forbidden data out of every result; the
    Inspector checks and the scripted agent tasks pass; the
    tools/list snapshot is stable.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Dependencies: `[mcp]` gains `mcp>=2.3`, joining `[all]`
      and the test group; tools/node gains
      @modelcontextprotocol/inspector pinned at 2.12.x. The
      licence exceptions follow this step's security block.
    </requirement>

    <requirement>
      The llm_use policy (planned here by ADR-0012 decision
      14; the data-layer change follows the Contract-change
      rule): an LlmUsePolicy in core's provenance vocabulary
      (allowed only; allow unclear); invoke, bind, data.get
      and resolve accept it; the resolver skips a candidate
      whose source or series is forbidden, or unclear without
      the opt-in, with the skip reason llm_use and fails
      over; when no candidate is left, a new
      LlmUseError(LicenceError) names the concept, with its
      error-table row (403, llm-use-forbidden). Without a
      policy, nothing changes: every resolver, binding and
      provider test stays green.
    </requirement>

    <requirement>
      src/pyeconomics/mcp/: build_server(*, mode, policy)
      registers the five discovery tools by ROADMAP §4 4.5's
      names and one tool per id in mcp/headline.py (a tuple
      the maintainer approves at kickoff: 10–20 widely used
      models across at least six domains, with the bond and
      policy-rule models among them), each named
      `<domain>_<name>` from the id (dots and the domain
      separator to underscores; ^[a-z0-9_]{1,64}$; a
      collision or overflow fails the build). Input schemas
      are each model's own; output schemas are the result
      envelope (inputs, outputs, warnings, manifest). Tools
      are sorted by name.
    </requirement>

    <requirement>
      Results: run tools call invoke with the server's
      policy and return the canonical result as structured
      content and Result.to_json() as text, plus a one-line
      summary; a result larger than the configured size
      returns the summary and a link to the REST download in
      hosted mode (local mode returns it whole). get_series
      returns at most the configured observations with its
      attribution and notices. list_sources returns each
      source's class, llm_use, attribution, terms URL and,
      locally, whether a key is configured (has_key, never
      the value). Every result passes the final check:
      withhold it with a problem if its manifest holds a
      forbidden record, or an unclear one without the
      opt-in.
    </requirement>

    <requirement>
      Transports: `pyeconomics mcp` serves stdio (the default)
      or, with --transport http, the local HTTP app on
      127.0.0.1 under the same bind guard as serve; the
      server factory mounts the stateless app at /mcp when
      the mcp extra is installed (hosted mode included, with
      Step 7's limits and edge check in front), and a tool
      call under /mcp runs its model through the same worker
      pool and budgets as /v1, so hosted MCP cannot bypass
      them (over stdio, runs execute in the server's own
      process, safe since Step 1). A test proves
      server/discover answers 2026-07-28 and the SDK's other
      supported revisions, and an older-revision client can
      list and call tools.
    </requirement>

    <requirement>
      Tests under tests/mcp/ (unique basenames), through the
      SDK's Client in memory: tools/list (syrupy snapshot
      through `tests/json_snapshots.py`'s `LFJSONExtension`, in
      local and hosted modes); every headline tool and
      run_model over each headline model's first example
      equal Result.to_json(); the gate (forbidden skipped,
      unclear only with the opt-in, the final check); the
      scripted agent tasks — "price a bond and report its
      duration" (search_models, describe_model, run_model
      or the headline tool, the Python API's duration) and
      "run the Taylor rule for a past date" (run_model on
      macro.policy_rule with as_of 2019-06-28 over recorded
      responses, FRED skipped by the gate, every record
      allowed, and revised data labelled where no source
      keeps vintages).
    </requirement>

    <requirement>
      Inspector: an mcp-inspector job in ci.yml (Ubuntu,
      Node 22) runs the Inspector's CLI mode from tools/node
      against `pyeconomics mcp` over stdio and against a
      local server's /mcp over Streamable HTTP: list tools,
      call a data-free headline tool, call run_model; any
      error fails the job, which joins the test aggregate.
    </requirement>

    <requirement>
      docs/mcp.md: install and run (uvx; Claude Code's `claude
      mcp add`; a client configuration file), the tools, the
      llm_use gate and its opt-in, local versus hosted, and
      what the tools never do. Link it from docs/index.md.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001).
    </requirement>
  </requirements>
</task>
```

### Step 8 acceptance criteria

- `pyeconomics mcp` (stdio) and the `/mcp` mount (Streamable HTTP) serve the
  five discovery tools and the approved headline tools, each with an
  `outputSchema`, sorted by name; the `tools/list` snapshot is stable in
  both modes.
- `run_model` and every headline tool return `Result.to_json()`'s object as
  structured content and its text, for each headline model's first example.
- A `forbidden` source never reaches a result through any tool, an
  `unclear` one only with the configuration opt-in, and the final check
  withholds a result that still carries one; without a policy, every
  existing resolver, binding and provider test passes unchanged.
- The scripted agent tasks succeed: the bond duration equals the Python
  API's, and the past-date Taylor rule runs on allowed originators with
  revised data labelled.
- `server/discover` answers the 2026-07-28 revision and the SDK's other
  supported revisions, and the `mcp-inspector` job passes over stdio and
  Streamable HTTP.
- `docs/mcp.md` builds; the full suite and the floors pass on all twelve
  cells.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, the `[mcp]` closure through the licences
  hook with its reviewed exceptions approved — and no tool argument can
  enable unclear data or reach a forbidden source.

---

## Step 9 — MCP Apps, the MCP Registry Entry and Agent Evaluations

**Status:** Not started

> **Goal:** Finish the MCP surface for real clients and real agents. Add a
> chart rendered inside clients that support the MCP Apps extension
> (`io.modelcontextprotocol/ui`): a `ui://pyeconomics/chart` resource
> (`text/html;profile=mcp-app`) kept as a string constant in a module, which
> renders the Plotly figure a run tool attaches in its result's `_meta` when
> the `plot` extra is installed, loading only one pinned script origin with
> Subresource Integrity that its CSP metadata declares, while run tools
> point to it with `_meta.ui.resourceUri` and clients without the extension
> get the plain result; prepare the official MCP Registry entry —
> `server.json` (schema 2025-12-11) naming
> `io.github.pyeconomics-dev/pyeconomics` and the PyPI package with its
> `uvx` invocation, the README's hidden `mcp-name:` marker that PyPI's
> description of `1.0.0b1` will carry, and
> `.github/workflows/mcp-registry.yml`, which publishes through GitHub OIDC
> from a protected `mcp-registry` environment with `mcp-publisher` pinned by
> version and checksum, and which Step 15 runs; and test the tool
> descriptions with agents: the scripted tasks gain a larger task set, and
> a live evaluation with a real agent (Claude Code headless against
> `pyeconomics mcp`) records each task's tool calls and answer in
> `docs/mcp-evaluations.md`, the descriptions revised until every task
> succeeds. Parent: ROADMAP §4 4.5; ADR-0012 decisions 13, 15 and 16.

**Branch:** `feature/phase04-step9-mcp-apps-registry`

**Deploys:** nothing beyond merge — the chart ships in the `[mcp]` extra
with the next build; `mcp-registry.yml` first runs at Step 15, after
`1.0.0b1` is on PyPI.

| Setting      | Cost                                     | Balanced                             | Quality                                    |
| ------------ | ---------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                              | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort Medium | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                    | Antigravity                          | Claude Code                                |
| Effort       | Intelligence Low                         | Effort High                          | Effort High                                |
| AA Index     | 42.1                                     | 52.6                                 | 53.6                                       |
| Thinking     | —                                        | On                                   | —                                          |
| Conversation | **New**                                  | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and agentic SECONDARY: a small
self-contained HTML page against the MCP Apps protocol, a registry manifest
and an OIDC workflow, and an evaluation loop that drives a real agent
through the tools. Complexity is Medium — the protocol, the manifest and
the workflow are each documented, and the evaluation's tasks are fixed
here — and it is not novel. The ladder's Balanced column runs: Gemini 4
Argon on Antigravity at Effort High with Thinking on (Google AI Pro; AA
Intelligence Index 52.6). Cost is GPT-6.1 Sol on Codex at Intelligence Low
(ChatGPT Pro 5x; 42.1) and Quality Opus 5.5 on Claude Code at Effort High
(claude.ai Max; 53.6). The live evaluation's agent runs on the
maintainer's Claude Code subscription whichever column runs the step. New
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
       feature/phase04-step9-mcp-apps-registry`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - The chart page loads exactly one external origin, pinned
      by version and Subresource Integrity, declared in its
      CSP metadata; it holds no inline event handler, never
      evaluates text, and renders only figure JSON (data, not
      markup) from the tool result.
    - mcp-registry.yml: permissions {} at the top and
      id-token: write plus contents: read on its one job, in
      the protected mcp-registry environment (maintainer
      review, deployments from tags only); mcp-publisher is
      downloaded at a pinned release and its SHA-256 checked
      against a value in the workflow before it runs; no
      secret is used (OIDC only); zizmor stays clean.
    - The evaluation record holds tool names, arguments and
      answers only: no key, no path, no environment value.
  </security>

  <context>
    pyeconomics. Phase 4. Step 9: MCP Apps, the MCP Registry
    entry and agent evaluations.

    Current state (post-Phase-4 Step 8):

    - mcp/ serves the discovery and headline tools over
      stdio and at /mcp, with the llm_use gate, a tools/list
      snapshot, the Inspector job and the scripted tasks.
    - core/plotting.py builds a Plotly figure behind the plot
      extra; the wheel admits only .py files.
    - Facts read on 2026-10-23: the MCP Apps extension
      (SEP-1865, revision 2026-01-26) declares ui:// resources
      of type text/html;profile=mcp-app, links a tool with
      _meta.ui.resourceUri, and denies external resources not
      named in the resource's CSP metadata; its SDK is
      @modelcontextprotocol/ext-apps 2.0.3 (MIT). The MCP
      Registry (preview) verifies a PyPI package by an
      `mcp-name: <server name>` string in its description,
      grants io.github.<org>/* only to an organization Owner,
      and publishes an organization namespace only through
      GitHub OIDC (`mcp-publisher login github-oidc`), not the
      device flow; its server.json schema is 2025-12-11 and
      its latest release v1.8.2.

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions 13,
      15 and 16).
    - src/pyeconomics/mcp/ (every module), core/plotting.py
      and README.md.
    - .github/workflows/release.yml (its environment and OIDC
      pattern) and providers-live.yml (a protected
      environment's pattern).
    - The MCP Apps specification and the MCP Registry's
      publishing, PyPI and GitHub Actions guides, read at
      kickoff (versions and schema dates confirmed then).
  </context>

  <goal>
    The chart renders in an MCP Apps host and degrades
    cleanly elsewhere; server.json validates and the README
    carries the marker; mcp-registry.yml is ready for Step
    15; the scripted task set passes in CI, and the live
    agent evaluation's every task succeeds, recorded.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, one batched request to the maintainer: create
      the `mcp-registry` environment (required reviewer: the
      maintainer; deployment tags only, v*), confirm the
      Owner role in pyeconomics-dev, and approve the server
      name and the headline list as they stand.
    </requirement>

    <requirement>
      MCP Apps: mcp/apps.py registers ui://pyeconomics/chart
      with the extension's MIME type and CSP metadata; its
      HTML (a string constant) speaks the extension's
      messages (with the ext-apps browser build or plain
      JavaScript, as the kickoff reading decides) and renders
      the figure from the result's _meta
      ("pyeconomics/figure"), which run tools add when plot is
      installed. structuredContent is unchanged, so parity
      holds. Tests: the resource, its MIME type and CSP, each
      run tool's resourceUri, no figure without plot. Render
      it once in an MCP Apps host (ext-apps' example host or a
      client that supports the extension) and put the
      screenshot in the PR body.
    </requirement>

    <requirement>
      server.json at the repository root: $schema (2025-12-11),
      name io.github.pyeconomics-dev/pyeconomics, title,
      description, version equal to the project version, and
      a pypi package (identifier pyeconomics, its version,
      stdio transport, the uvx runtime hint and the arguments
      that select the mcp extra). A test validates it against
      a vendored copy of the schema (source URL and access
      date recorded) and checks the version against
      pyproject.toml. README.md gains the hidden marker
      `<!-- mcp-name: io.github.pyeconomics-dev/pyeconomics -->`
      on its own line.
    </requirement>

    <requirement>
      .github/workflows/mcp-registry.yml: triggers
      `release: published` and workflow_dispatch (a version
      input); one job in the mcp-registry environment;
      harden-runner first; checkout with persist-credentials
      false; download mcp-publisher at the pinned release and
      verify its SHA-256; check server.json's version equals
      the release; wait until PyPI's JSON API shows that
      version with the mcp-name marker in its description;
      `mcp-publisher login github-oidc`; `mcp-publisher
      publish`; read the entry back from the registry's API.
      Phase 1 check 37 and zizmor pass; release.yml is not
      changed (Phase 1 check 36).
    </requirement>

    <requirement>
      Scripted tasks: extend tests/mcp's task set to at least
      eight tasks covering discovery, three headline tools, a
      bound run, get_series with attribution, list_sources and
      a refusal (a forbidden source named directly), each with
      its expected tool sequence and value.
    </requirement>

    <requirement>
      Live evaluation (local, the maintainer's machine, not
      CI): scripts/mcp_agent_eval.py runs each task's prompt
      through Claude Code headless with `pyeconomics mcp` from
      the working tree as its only MCP server (sockets
      allowed; FRED keys withheld so the gate is exercised),
      records the tool calls, arguments and final answer, and
      checks the value within the task's tolerance. Revise
      descriptions (and the tools/list snapshot) until every
      task succeeds; write docs/mcp-evaluations.md with the
      date, the agent and model, and each task's result.
      Step 14 reruns it on the candidate.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001); YAML `# <path>`; server.json
      allows no comment.
    </requirement>
  </requirements>
</task>
```

### Step 9 acceptance criteria

- `ui://pyeconomics/chart` is registered with the MCP Apps MIME type and CSP
  metadata, run tools link it, the page loads only its pinned origin, and a
  screenshot in the PR body shows it rendering a figure in an MCP Apps host;
  a client without the extension receives the plain result.
- `server.json` validates against the vendored 2025-12-11 schema, names
  `io.github.pyeconomics-dev/pyeconomics` and the PyPI package at the project
  version, and `README.md` carries the `mcp-name:` marker.
- `mcp-registry.yml` exists in the protected `mcp-registry` environment
  with OIDC only and a checksum-verified `mcp-publisher`; zizmor and Phase 1
  checks 36 and 37 pass.
- At least eight scripted tasks pass in CI, and the live evaluation records
  every task succeeding in `docs/mcp-evaluations.md`.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the workflow uses no stored secret, and
  the evaluation record holds no key, path or environment value.

---

## Step 10 — Cross-Surface Parity

**Status:** Not started

> **Goal:** Prove that "generated" means "identical". Add `tests/parity/`:
> every golden case of every registered model (354 cases across 50 files on
> 2026-10-23, and every case a later step adds) runs through the Python API,
> the CLI (`--format json`), the REST API and MCP `run_model`, and the four
> canonical byte strings must be equal — a case whose expected outcome is an
> error yields the same problem slug, HTTP status and exit code on every
> surface; bound runs of every model with bindings, over recorded responses,
> return equal bytes, data records included; exports round-trip to the
> Python API's values; a sample per domain also runs through the installed
> console script, the real worker pool and the stdio MCP server in a
> `parity` CI job; and the Generator rule becomes a check — no module under
> `cli/`, `server/` or `mcp/` names a model id (the declared headline list
> excepted), and a toy model registered only through a toy registry appears
> on every surface with no code change. Parent: ROADMAP §4 4.1 ("a
> cross-surface parity suite … must match byte for byte") and §5 "Model
> quality & governance" ("Parity"); ADR-0012 decisions 2 and 3.

**Branch:** `feature/phase04-step10-parity`

**Deploys:** nothing beyond merge.

| Setting      | Cost                                    | Balanced                             | Quality                                    |
| ------------ | --------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                             | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort XHigh | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                   | Antigravity                          | Claude Code                                |
| Effort       | Intelligence High                       | Effort High                          | Effort XHigh                               |
| AA Index     | 50.2                                    | 52.6                                 | 56                                         |
| Thinking     | —                                       | On                                   | —                                          |
| Conversation | **New**                                 | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and long-context SECONDARY: a suite
that drives four surfaces in-process and out of process over every golden
case, handles error cases through the error table, rebinds every bound
model over recorded responses, and enforces the Generator rule by static
analysis. Complexity is High — it reaches every surface and must stay fast
enough for twelve CI cells — but it applies established patterns, so it is
not novel. The ladder's Balanced column runs: Gemini 4 Argon on
Antigravity at Effort High with Thinking on (Google AI Pro; AA
Intelligence Index 52.6), backed by Opus 5.5 on Claude Code. Cost is
GPT-6.1 Sol on Codex at Intelligence High (ChatGPT Pro 5x; 50.2) and
Quality Opus 5.5 on Claude Code at Effort XHigh (claude.ai Max; 56.0). New
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
       feature/phase04-step10-parity`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - The bound parity runs replay recorded responses with
      sockets disabled and keys planted by canary(); LeakCheck
      proves no key reaches any surface's output.
    - A parity failure is a bug in the surface that changed
      the bytes (Triage rule); a comparison is never
      loosened to pass.
  </security>

  <context>
    pyeconomics. Phase 4. Step 10: cross-surface parity.

    Current state (post-Phase-4 Step 9):

    - surfaces.invoke serves the CLI (Step 4), the exports
      (Step 5), the REST API (Steps 6–7) and the MCP server
      (Steps 8–9); each returns Result.to_json() bytes by
      ADR-0012 decision 3, and the CLI appends one newline.
    - tests/golden/ holds one TOML file per model, read by
      tests/golden/_loader.py; tests/data/bindings/
      bound_support.py scripts providers for offline bound
      runs; the providers' cassettes replay every source.
    - The full offline suite runs serially in about 16–19
      minutes on a cell; the parity suite must not double it.

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions 2
      and 3) and this roadmap's Surface rules.
    - tests/golden/README.md, tests/golden/_loader.py and
      tests/contract.py.
    - src/pyeconomics/surfaces/, cli/, server/ and mcp/.
    - tests/cli/, tests/server/ and tests/mcp/ (their
      in-process harnesses), and
      tests/data/bindings/bound_support.py.
  </context>

  <goal>
    tests/parity/ proves byte-identical canonical JSON across
    Python, the CLI, the REST API and MCP for every golden
    case and every bound model, the same problem for every
    error case, export round-trips, and the Generator rule;
    the parity CI job proves a sample out of process.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      tests/parity/test_parity_golden.py (unique basenames
      throughout): parametrized over every golden case of
      every registered model, read through the golden loader;
      for each, the Python API's bytes; the CLI's stdout
      in-process with exactly one trailing newline removed;
      the REST response body through TestClient with an
      inline pool; MCP run_model's text content and the
      canonical JSON of its structured content through the
      SDK's in-memory Client. All equal. An error case
      compares problem slug, status and exit code instead.
      The parametrization is generated, so a new model's
      cases join with no edit.
    </requirement>

    <requirement>
      tests/parity/test_parity_bound.py: every model with
      bindings, its default profile at a fixed as-of date over
      scripted providers or replayed cassettes, through the
      four surfaces: equal bytes, data records included.
    </requirement>

    <requirement>
      tests/parity/test_parity_exports.py: for one case per
      domain and one bound model, each export format read
      back (pandas, openpyxl, pyarrow) equals the Python API's
      values exactly, and the manifest read back equals the
      result's.
    </requirement>

    <requirement>
      tests/parity/test_generator_guard.py: an AST scan of
      src/pyeconomics/cli/, server/ and mcp/ finds no string
      literal equal to a registered model id (mcp/headline.py,
      the declared list, excepted); a toy model in a toy
      registry, injected into each surface's factory, appears
      in the CLI's run options, an OpenAPI operation and an
      MCP run_model call with no code change.
    </requirement>

    <requirement>
      A parity job in ci.yml (Ubuntu, Python 3.14) installs
      the built wheel with server and mcp in a clean venv and,
      for one golden case per domain, compares the console
      script's stdout, a real `pyeconomics serve` with
      spawned workers over HTTP, and `pyeconomics mcp` over
      stdio against the Python API. It joins the test
      aggregate.
    </requirement>

    <requirement>
      Keep the suite's cost bounded: measure its time on the
      slowest cell and record it in the PR body; reuse one
      app, one MCP client and one CLI app per session.
    </requirement>

    <requirement>
      docs/results.md: a "Same bytes everywhere" section on
      parity and how a contributor runs the suite.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001).
    </requirement>
  </requirements>
</task>
```

### Step 10 acceptance criteria

- Every golden case of every registered model returns byte-identical
  canonical JSON from the Python API, the CLI, the REST API and MCP
  `run_model`, and every error case the same problem slug, status and exit
  code, on all twelve CI cells.
- Every model with bindings returns identical bytes, data records included,
  on the four surfaces over recorded responses.
- Each export format reads back to the Python API's values and manifest.
- The generator guard finds no hand-written model on any surface, and a
  toy-registry model appears on every surface with no code change.
- The `parity` job passes out of process on the installed wheel, and the
  suite's added time is recorded.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and LeakCheck finds no key in any
  surface's output during the bound runs.

---

## Step 11 — Optional AI Narrative

**Status:** Not started

> **Goal:** Bring back 0.2.x's commentary as an optional, honest feature.
> Add `src/pyeconomics/ai/` behind the `[ai]` extra: `narrate(result, *,
> provider=None, model=None)` returns a `Narrative` (the text, the provider
> and model, input and output tokens, the cost in US dollars from a dated
> price table, and the "not investment advice" notice); AI providers
> (Anthropic, OpenAI and Google to start) are declared like data providers —
> hosts, an `Authentication` key slot, the `<PROVIDER>_API_KEY` variable
> through the credential chain — and called through the data layer's HTTPS
> transport, so no client library arrives and no key leaves
> `data/credentials/` and `data/transport/`; it is off by default
> (`ai_enabled`), refuses a result whose data carries a `forbidden`
> `llm_use` (or an `unclear` one without the out-of-band opt-in), refuses
> hosted mode outright until Phase 8, and sends only the result's own facts
> through a fixed prompt; its default provider and model are configuration
> values picked with the model selector in this step and recorded with their
> date; the CLI gains `models run … --narrate`; and `docs/ai.md` documents
> it. No MCP tool or hosted route narrates. Parent: ROADMAP §4 4.6, §5
> "Data terms" (FRED at inference time is a counsel question) and
> "Operations & observability strategy" rule 3; ADR-0012 decisions 14 and
> 17.

**Branch:** `feature/phase04-step11-ai-narrative`

**Deploys:** nothing beyond merge — the narrative ships with the next
package build and never runs in the hosted service (Phase 8 adds it there
behind a ledger and a cap).

| Setting      | Cost                                     | Balanced                             | Quality                                    |
| ------------ | ---------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                              | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort Medium | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                    | Antigravity                          | Claude Code                                |
| Effort       | Intelligence Low                         | Effort High                          | Effort High                                |
| AA Index     | 42.1                                     | 52.6                                 | 53.6                                       |
| Thinking     | —                                        | On                                   | —                                          |
| Conversation | **New**                                  | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: three
provider declarations over an existing transport, a prompt, a cost
calculation and refusals, plus one model-selection decision recorded with
its evidence. Complexity is Medium — the transport, the credential chain
and the `llm_use` policy already exist — and it is not novel. The ladder's
Balanced column runs: Gemini 4 Argon on Antigravity at Effort High with
Thinking on (Google AI Pro; AA Intelligence Index 52.6). Cost is GPT-6.1
Sol on Codex at Intelligence Low (ChatGPT Pro 5x; 42.1) and Quality Opus
5.5 on Claude Code at Effort High (claude.ai Max; 53.6). The narrative's
own default model is a separate choice the step makes with `roadmodel` for
the narrative's task, not this table. New conversation per phase-boundary
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
       feature/phase04-step11-ai-narrative`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - A key is read only through the credential chain and
      revealed only in data/credentials/ and data/transport/
      (the secret-reveal rule); a Request never carries a
      key; LeakCheck canaries prove no key reaches the
      prompt, the narrative, a log record, an exception, a
      problem or a recorded cassette.
    - The prompt holds only the result's model, inputs,
      outputs with units, warnings and the card's assumptions
      and limitations: no key, path, host, environment value
      or manifest URL; a test renders it from a canary-laden
      result and scans it.
    - Data whose llm_use is forbidden never reaches a
      provider (a test per policy), and hosted mode refuses
      before any request.
    - Every request goes to a declared host over HTTPS with
      the transport's timeouts and size caps; recorded
      responses are synthetic and scrubbed (the Recording
      rule).
  </security>

  <context>
    pyeconomics. Phase 4. Step 11: optional AI narrative.

    Current state (post-Phase-4 Step 10):

    - The four surfaces are generated and proven identical;
      the llm_use policy exists in invoke, bind, data.get and
      the resolver (Step 8), and manifest records carry
      llm_use.
    - The ai extra is an empty list. The data layer's
      transport attaches a key from a provider's
      Authentication and refuses a Request that carries one;
      key_variable maps an id to <PROVIDER>_API_KEY.
    - 0.2.x's commentary called OpenAI with a hard-coded
      model and no cost cap, and sent FRED-derived content to
      an LLM (ROADMAP §2 gap 16).
    - planning/model-selector.txt and `roadmodel` are the
      model selector; the maintainer holds Anthropic, OpenAI
      and Google API keys for a live check
      (planning/user-context.md, git-ignored).

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions 14
      and 17) and this roadmap's Credential rule.
    - src/pyeconomics/data/transport/ (base.py, http.py),
      data/providers/base.py (Authentication, KeySlot,
      RateLimit), data/credentials/chain.py and data/config.py.
    - src/pyeconomics/surfaces/ and cli/ (the run command).
    - Each AI provider's current API reference (messages or
      chat endpoint, token usage fields, authentication
      header) and list prices, read at kickoff with their
      dates.
  </context>

  <goal>
    narrate() produces a narrative with its cost from the
    user's own key, only when enabled, only from data whose
    terms allow it, never in hosted mode; the CLI's
    --narrate exposes it; the default model is chosen with
    the selector and recorded.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Model selection: classify the narrative's task (a short
      plain-language explanation of one result; knowledge,
      low complexity) and run `roadmodel ladder --category
      knowledge --complexity low` (or the selector itself if
      roadmodel is unreachable); choose the default provider
      and model from the models the declared providers serve,
      record the command, its output and the date in the PR
      body, and put the choice in ai/defaults.py as
      configuration (ai_provider, ai_model), overridable in
      pyeconomics.toml or the environment.
    </requirement>

    <requirement>
      src/pyeconomics/ai/: provider declarations (host,
      path, Authentication slot, rate limit) for Anthropic,
      OpenAI and Google; requests built as the data layer's
      Request values and sent through its transport (the
      smallest seam if the transport needs one, under the
      Contract-change rule); responses parsed with
      Response.json(); the price table (per model, input and
      output per million tokens, its source URL and the date
      read) with a test that fails when the date is over 180
      days old; Narrative with the cost and the notice.
    </requirement>

    <requirement>
      Refusals, each an error-table row: disabled (ai_enabled
      false, the default) refuses before any request; hosted
      mode refuses; a result whose manifest holds a forbidden
      record, or an unclear one without the opt-in, raises
      LlmUseError; offline mode refuses; a missing key raises
      CredentialError naming the variable, never a value.
    </requirement>

    <requirement>
      CLI: `models run ID … --narrate` prints the narrative
      and its cost after a table, or to stderr with --format
      json so stdout stays the canonical bytes; the narrative
      is never written into an export, a bundle or a cache.
    </requirement>

    <requirement>
      Tests under tests/ai/ (unique basenames): recorded,
      synthetic responses per provider replayed offline; the
      cost arithmetic; every refusal; LeakCheck over every
      sink; the prompt's contents. One live run per provider
      the maintainer approves at kickoff (`-m live`, local
      only, the maintainer's own key through the chain),
      recorded in the PR body with its cost.
    </requirement>

    <requirement>
      docs/ai.md: enabling it, keys, the default model and
      how to change it, the cost line, what is sent, what is
      refused and why (FRED's terms and the counsel question),
      and that hosted mode waits for Phase 8. Link it from
      docs/index.md.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001).
    </requirement>
  </requirements>
</task>
```

### Step 11 acceptance criteria

- `narrate()` returns the narrative, provider, model, tokens, cost and
  notice from recorded responses for each declared provider, and the live
  run of each approved provider is recorded with its cost.
- The narrative is off by default, refuses hosted mode, offline mode and
  data whose `llm_use` forbids it (or is unclear without the opt-in), and
  names a missing key's variable without its value.
- The default provider and model come from a recorded `roadmodel` run, and
  the price table's staleness test passes.
- `models run … --narrate` keeps stdout canonical under `--format json`,
  and no narrative reaches an export, a bundle or a cache.
- `docs/ai.md` builds; the full suite and the floors pass on all twelve
  cells.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — no key reaches the prompt, the narrative,
  a log or a cassette, and no client library was added.

---

## Step 12 — Service Container

**Status:** Not started

> **Goal:** Package the hosted API as an image that holds only what hosted
> mode may serve. Add a multi-stage `Dockerfile` and `.dockerignore`: a
> build stage that builds the wheel and exports the locked requirements
> with hashes; a runtime stage on a Python 3.14 slim base pinned by digest,
> installing the wheel with the `[server]`, `[mcp]`, `[econometrics]`,
> `[plot]` and `[sdmx]` extras from the locked, hash-checked set and nothing
> else (no yfinance, keyring or AI provider, and no Bloomberg code), running
> as a non-root user with `PYECONOMICS_MODE=hosted`, a cache directory under
> `/tmp`, the git SHA baked in for `/version`, and an entry point
> (`python -m pyeconomics.server`) that reads Cloud Run's `PORT` and binds
> all interfaces only in hosted mode; and a `container` CI job that builds
> it, scans it with a scanner pinned by digest (failing on any fixable
> Critical or High finding), keeps its SBOM, and smoke-tests the running
> image (`/healthz`, `/version`, a model run equal to the wheel's bytes, a
> 403 for a library-only source, the non-root user, the absent libraries).
> The image is pushed nowhere until Step 13. Parent: ROADMAP §4 4.7 and §5
> "Security controls by layer"; ADR-0012 decision 19; ADR-0005's
> Confirmation ("the hosted image omits their client libraries"); ADR-0006.

**Branch:** `feature/phase04-step12-service-container`

**Deploys:** nothing beyond merge — the image is a CI artifact; Step 13
pushes it to Artifact Registry and deploys it to staging.

| Setting      | Cost                                     | Balanced                             | Quality                                    |
| ------------ | ---------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                              | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort Medium | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                    | Antigravity                          | Claude Code                                |
| Effort       | Intelligence Low                         | Effort High                          | Effort High                                |
| AA Index     | 42.1                                     | 52.6                                 | 53.6                                       |
| Thinking     | —                                        | On                                   | —                                          |
| Conversation | **New**                                  | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and agentic SECONDARY: a Dockerfile,
an ignore file, an entry point and a CI job that builds, scans and runs
the image. Complexity is Medium — the contents are fixed by ADR-0012 and
the checks by ROADMAP §4 4.7 — and it is not novel. The ladder's Balanced
column runs: Gemini 4 Argon on Antigravity at Effort High with Thinking on
(Google AI Pro; AA Intelligence Index 52.6). Cost is GPT-6.1 Sol on Codex
at Intelligence Low (ChatGPT Pro 5x; 42.1) and Quality Opus 5.5 on Claude
Code at Effort High (claude.ai Max; 53.6). New conversation per
phase-boundary hygiene.

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
       feature/phase04-step12-service-container`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - Nothing secret enters the build context: .dockerignore
      excludes .git, .env and .env.*, dev/, .roadmodel/,
      CLAUDE.local.md, .venv, caches, the planning kit's
      user context and every ignored path; a test builds the
      context listing and fails on any of them.
    - The image runs as a non-root user with no shell login,
      holds no key or secret (Cloud Run injects secrets at
      run time, Step 13), and its scan fails the job on any
      fixable Critical or High finding; the base image is
      pinned by digest and Dependabot's docker ecosystem
      updates it.
    - The image holds no library of a library-only extra
      (yfinance) and no Bloomberg code; the smoke test lists
      the installed distributions and fails on any of them.
    - The scanner and every action are pinned by SHA or
      digest; the job's permissions are contents: read only.
  </security>

  <context>
    pyeconomics. Phase 4. Step 12: service container.

    Current state (post-Phase-4 Step 11):

    - server/ serves /v1 and /mcp in local and hosted modes;
      hosted mode limits, caches, checks the edge credential
      and refuses library-only data; the AI narrative never
      runs in hosted mode.
    - pylock.toml and uv.lock pin the runtime set; release.yml
      builds the wheel; ci.yml has no container job; no
      Dockerfile exists.
    - ADR-0012 decision 19 fixes the image: Python 3.14 (arch
      has wheels there; issue #154 gates it on 3.15), the five
      extras, non-root, hosted mode, the SHA for /version.
      Parquet and Arrow downloads need pyarrow, which
      ADR-0008 decision 8 keeps out of the package's
      dependencies and extras.

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions 10,
      11 and 19) and this roadmap's Licence rule.
    - src/pyeconomics/server/ (every module) and
      surfaces/budgets.py.
    - pyproject.toml, uv.lock, pylock.toml,
      scripts/checks/dist_contents.py and
      .github/workflows/ci.yml, release.yml and dependabot.yml.
    - The base image's and the scanner's documentation, read
      at kickoff with the digests chosen then.
  </context>

  <goal>
    `docker build` produces a non-root hosted-mode image of
    this commit with exactly the five extras, scanned clean
    of fixable Critical and High findings, that serves a
    model run equal to the wheel's bytes and refuses
    library-only data, proven by the container job.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, one batched question to the maintainer:
      whether the image installs pyarrow as an image-level
      package, pinned and hash-checked, so hosted Parquet and
      Arrow downloads work (recommended: yes; ADR-0008
      decision 8 governs the package's metadata, not the
      image) or answers 501 for them; and the scanner (Trivy
      recommended; Grype the alternative).
    </requirement>

    <requirement>
      Dockerfile: the build stage uses uv at the version CI
      pins to build the wheel and `uv export --no-config
      --frozen --no-dev --extra server --extra mcp --extra
      econometrics --extra plot --extra sdmx --no-emit-project`
      with hashes; the runtime stage installs that set with
      `--require-hashes`, then the wheel without dependencies,
      creates the non-root user, sets PYECONOMICS_MODE=hosted,
      PYECONOMICS_CACHE_DIR under /tmp, PYTHONDONTWRITEBYTECODE
      and PYTHONUNBUFFERED, bakes the GIT_SHA build argument
      into PYECONOMICS_GIT_SHA, and runs `python -m
      pyeconomics.server`. .dockerignore per this step's
      security block.
    </requirement>

    <requirement>
      src/pyeconomics/server/__main__.py: reads PORT (default
      8080) and the worker count, binds 0.0.0.0 only when the
      mode is hosted (local mode keeps serve's loopback
      guard), and runs uvicorn programmatically without
      trusting forwarded headers (the client address comes
      from Step 7's edge check).
    </requirement>

    <requirement>
      ci.yml's container job (Ubuntu): build with
      --build-arg GIT_SHA; scan (fixable Critical or High
      fails the job); upload the SBOM as an artifact; run the
      image and check /healthz, /version's SHA, a data-free
      run equal to the wheel's Python API bytes, a 403 problem
      for a library-only series, the user id, the absence of
      yfinance, keyring and any blpapi; report the image's
      size. The job joins the test aggregate. Dependabot
      gains the docker ecosystem.
    </requirement>

    <requirement>
      docs/api.md: a "Running the container" section (build,
      run, the environment variables, what hosted mode
      refuses) for self-hosters, noting that the project's
      staging and production images come from CI.
    </requirement>

    <requirement>
      Filepath comment: the Dockerfile and .dockerignore start
      with `# <path>`; every new Python file gets the
      three-line header (CPY001).
    </requirement>
  </requirements>
</task>
```

### Step 12 acceptance criteria

- The image builds from this commit with exactly the `[server]`, `[mcp]`,
  `[econometrics]`, `[plot]` and `[sdmx]` extras (plus pyarrow if the
  maintainer approved it), runs as a non-root user in hosted mode, and
  reports this commit's SHA at `/version`.
- The scan finds no fixable Critical or High vulnerability, and the SBOM is
  kept as a job artifact.
- The running image serves a data-free model run equal to the wheel's bytes
  and answers 403 with a licence explanation for a library-only series.
- The installed distributions include no yfinance, keyring or Bloomberg
  library, and the build context holds no excluded path.
- The `container` job passes and is part of the `test` aggregate; Dependabot
  watches the base image.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, zizmor clean on the CI change — the image
  scan is clean of fixable Critical and High findings, and no secret enters
  the build context or the image.

---

## Step 13 — Staging on Cloud Run

**Status:** Not started

> **Goal:** Run the hosted API where it will live, privately, at $0. With
> the maintainer's approvals batched at kickoff, provision a Google Cloud
> project in `us-central1` with Artifact Registry (a cleanup policy that
> keeps storage inside the free tier), a runtime service account that can
> read only its two secrets, and Workload Identity Federation bound to this
> repository's numeric id and `main`, so no service-account key ever
> exists; put the rate-limit store's URL (a free Upstash Redis database) and
> the edge credential in Secret Manager; create the Cloud Run service
> `pyeconomics-api-staging` (minimum 0 and maximum 2 instances, request-based
> billing, secrets injected by pinned version); put Cloudflare in front of
> it on a staging hostname under `pyeconomics.dev` — the edge ADR-0012
> decision 20 chose (a Worker that forwards to the origin with the edge
> credential, recommended), Cloudflare Access with a service token and the
> maintainer's identity, and the free plan's rate rule; add
> `.github/workflows/deploy-staging.yml`, which on every push to `main`
> builds, scans and pushes the image, deploys it through OIDC, verifies it
> through the edge and rolls traffic back on failure; add a billing budget
> with 50/90/100% alerts and programmatic notifications; add
> `.github/workflows/staging-health.yml`, an hourly probe through the edge
> whose failure opens a `staging-health` issue; and write the staging
> runbooks in `docs/operations/staging.md`. Parent: ROADMAP §4 4.7, §5
> "Release & deployment strategy", "Security controls by layer" and
> "Operations & observability strategy"; ADR-0006; ADR-0012 decisions 11,
> 12, 19 and 20.

**Branch:** `feature/phase04-step13-staging`

**Deploys:** the staging API on Cloud Run (`us-central1`) behind Cloudflare
Access — this step's merge is the first push-to-`main` deploy, and from it
on every merge to `main` redeploys staging through `deploy-staging.yml`;
the Deployed & verified check runs through the edge with the service token
read from the maintainer's keyring, and `staging-health.yml` probes it
hourly.

| Setting      | Cost                                   | Balanced                                   | Quality                                    |
| ------------ | -------------------------------------- | ------------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                            | Sonnet 5.5                                 | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                  | Claude Code                                | Claude Code                                |
| Effort       | Intelligence Medium                    | Effort XHigh                               | Effort XHigh                               |
| AA Index     | 47.8                                   | 51.9                                       | 56                                         |
| Thinking     | —                                      | —                                          | —                                          |
| Conversation | **New**                                | **New**                                    | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Agentic is PRIMARY and coding SECONDARY: a long,
multi-step provisioning run across Google Cloud, Cloudflare, Upstash and
GitHub, driven by commands the step prints for the maintainer, plus two
workflows, a Worker and runbooks. Complexity is High and
security-sensitive — OIDC trust, least-privilege IAM, secret injection and
an edge trust boundary — though the topology is ADR-0012's, so it is not
novel. The ladder's Balanced column runs: Sonnet 5.5 on Claude Code at
Effort XHigh (claude.ai Max; AA Intelligence Index 51.9), backed by Gemini
4 Argon on Antigravity. Cost is GPT-6.1 Sol on Codex at Intelligence
Medium (ChatGPT Pro 5x; 47.8) and Quality Opus 5.5 on Claude Code at
Effort XHigh (56.0); Sonnet 5.5 and Opus 5.5 always think, so neither has a
Thinking toggle. New conversation per phase-boundary hygiene.

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
       feature/phase04-step13-staging`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - No service-account key exists: deploys authenticate
      with GitHub OIDC through Workload Identity Federation
      whose attribute condition names this repository's
      numeric id and refs/heads/main; a check lists each
      service account's keys and finds only Google-managed
      ones.
    - Least privilege: the runtime account reads only its two
      secret versions; the deploy identity can only push to
      the one repository and deploy the one service as the
      runtime account; nothing holds a project-wide role it
      does not need.
    - Secrets live in Secret Manager (the service) and in
      the protected `staging` environment (the Access service
      token for the deploy check and the probe); none is a
      repository secret, and none transits chat, a PR or a
      log: the maintainer runs commands that prompt for or
      pipe each value, and each is proven by an authenticated
      round-trip (a request through the edge), never by its
      name.
    - The Worker is reachable only through the
      Access-protected hostname (its workers.dev route
      disabled), adds the edge credential from a Worker
      secret, and strips hop-by-hop headers; the origin
      answers 403 to any /v1 or /mcp request without it.
    - deploy-staging.yml and staging-health.yml set
      permissions {} at the top, grant id-token: write only
      to the deploy job and issues: write only to the report
      job, pin every action by SHA, and pass zizmor; Phase 3
      check 78 is narrowed to allow exactly these two
      workflows to read `staging` secrets.
  </security>

  <context>
    pyeconomics. Phase 4. Step 13: staging on Cloud Run.

    Current state (post-Phase-4 Step 12):

    - The container job builds a non-root hosted-mode image,
      scans it and smoke-tests it; nothing is pushed or
      deployed. Hosted mode reads PYECONOMICS_RATELIMIT_URL
      and PYECONOMICS_EDGE_CREDENTIAL from the environment.
    - The four domains are on Cloudflare Registrar with
      Cloudflare DNS (ADR-0009); Cloudflare Zero Trust's free
      plan covers Access and service tokens (verify at
      kickoff); the free plan has one rate rule.
    - Facts read on 2026-10-23: Cloud Run's free tier is
      180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million
      requests a month (Tier 1 regions, request-based
      billing); google-github-actions/auth's current major
      is v3 and prefers direct Workload Identity Federation;
      Cloud Run domain mapping is Preview and not
      recommended for production; a Worker on the free plan
      serves 100,000 requests a day; Upstash Redis is free to
      500,000 commands a month.
    - Phase 3 check 78 allows only providers-live.yml to read
      a secret other than GITHUB_TOKEN; Phase 1 check 36 pins
      id-token: write to release.yml's two publish jobs.

    Files to read (every file before drafting):
    - docs/adr/0012-programmatic-surfaces.md (decisions 11,
      12, 19 and 20) and ADR-0006.
    - Dockerfile, src/pyeconomics/server/ (edge.py,
      limits.py, __main__.py) and docs/api.md.
    - .github/workflows/ci.yml (container job),
      providers-live.yml and providers-heartbeat.yml (a
      protected environment and an issue-opening alarm).
    - scripts/verify-phase03.sh (check 78) and the end of
      docs/roadmap/phase03-roadmap.md.
    - Google's Cloud Run, Artifact Registry, Secret Manager,
      Workload Identity Federation and budget documentation,
      and Cloudflare's Access, service token and Workers
      documentation, read at kickoff.
  </context>

  <goal>
    A merge to main builds, scans, pushes and deploys the
    image to staging through OIDC and verifies it through
    the edge; staging serves runs and hosted-safe series to
    the service token, refuses library-only data with 403,
    and refuses anyone without Access or the edge
    credential; a budget and an hourly probe watch it; the
    runbooks say how to roll back and rotate.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer with
      every command and its effect: create or choose the
      Google Cloud project and link billing; enable the Run,
      Artifact Registry, Secret Manager, IAM Credentials, STS
      and Billing Budgets APIs; create the repository with
      its cleanup policy, the runtime and deploy identities,
      the workload identity pool and provider (condition on
      the repository id and main) and the IAM bindings;
      create the Upstash database and store its URL with
      `gcloud secrets versions add ratelimit-url
      --data-file=-`; generate the edge credential once and
      pipe it into both Secret Manager and `npx wrangler
      secret put` without displaying it; create the
      Cloudflare DNS record, the Worker deployment, the
      Access application, its service token (and store its
      id and secret with `gh secret set CF_ACCESS_CLIENT_ID
      --env staging` and `... CF_ACCESS_CLIENT_SECRET`, and in
      the maintainer's keyring for local recipes) and the
      rate rule; create the `staging` GitHub environment
      (deployments from main only) with its variables
      (project, region, service, identity provider, deploy
      identity, staging host); create the budget and its
      Pub/Sub topic and subscription. Record what was done,
      never a value, in the PR body.
    </requirement>

    <requirement>
      The edge (decision 20; the maintainer chose the Worker
      when ADR-0012 was accepted on 2026-10-23):
      tools/node/edge/ holds it (forward method, path, query
      and body to ORIGIN_URL; add X-Pyeconomics-Edge from the
      EDGE_CREDENTIAL secret; pass CF-Connecting-IP; strip
      hop-by-hop headers; return the response) with a
      node:test suite over a stubbed fetch, a wrangler.toml
      with no workers.dev route, and the deploy command in
      the runbook.
    </requirement>

    <requirement>
      .github/workflows/deploy-staging.yml: on push to main
      and workflow_dispatch; concurrency that never cancels
      a running deploy; one job in the `staging` environment
      with contents: read and id-token: write;
      google-github-actions/auth (v3, by SHA) with the
      environment's variables and no key input; build with
      GIT_SHA, scan (fixable Critical or High fails), push by
      SHA, deploy by digest with secrets by pinned version;
      then verify: the origin's /healthz; through the edge
      with the service token, /version equals this commit,
      a data-free run equals the wheel's bytes computed in
      the job, a hosted-safe series answers 200 with its
      attribution, a library-only series 403; a direct /v1
      request without the edge credential 403. On any
      failure, route traffic to the previous revision and
      fail.
    </requirement>

    <requirement>
      Cloud Run: minimum 0 and maximum 2 instances,
      request-based billing, a memory size the kickoff
      measures for two workers, a 60-second request timeout,
      ingress from the internet (the Worker's), IAM allowing
      unauthenticated invocations because the edge credential
      is the origin's gate (the runbook says so), and
      revisions kept for rollback.
    </requirement>

    <requirement>
      .github/workflows/staging-health.yml: schedule (hourly)
      and workflow_dispatch with a simulate_failure input;
      a probe job in the `staging` environment calls
      /healthz, /version and one data-free run through the
      edge with the service token; a report job (the only one
      with issues: write) opens a `staging-health` issue on
      failure and closes older ones (the staleness policy),
      and the run fails so GitHub notifies the maintainer.
    </requirement>

    <requirement>
      docs/operations/staging.md (excluded from the
      documentation site, like the roadmaps): the topology,
      deploy and rollback (traffic to the previous revision),
      rotating the edge credential, the rate-limit URL and
      the service token (which expires: its date recorded),
      disabling a provider through
      PYECONOMICS_DISABLED_PROVIDERS, a cost spike (lower the
      maximum, tighten the rule), and the free-tier
      arithmetic for hourly probes and expected deploys.
    </requirement>

    <requirement>
      Cross-phase verification rule: narrow Phase 3 check 78
      to "no workflow but providers-live.yml,
      deploy-staging.yml and staging-health.yml reads a
      secret other than GITHUB_TOKEN, and those two read only
      `staging` environment secrets", and append the line to
      a `## Post-merge addendum (<YYYY-MM-DD>) — Phase 4
      changes to verify-phase03.sh` section at the end of
      docs/roadmap/phase03-roadmap.md.
    </requirement>

    <requirement>
      Filepath comment: YAML and TOML start with `# <path>`;
      JavaScript `// <path>`; every new Python file the
      three-line header (CPY001).
    </requirement>
  </requirements>
</task>
```

### Step 13 acceptance criteria

- The merge of this step deploys staging through `deploy-staging.yml` with
  OIDC and Workload Identity Federation; each service account lists only
  Google-managed keys, and no repository secret exists.
- The service reads its two secrets from Secret Manager by pinned version,
  runs with minimum 0 and maximum 2 instances, and keeps earlier revisions.
- Without the Access service token, the staging hostname refuses; without
  the edge credential, the origin answers 403 on `/v1` and `/mcp`.
- The budget exists with 50/90/100% alerts and its Pub/Sub notifications;
  `staging-health.yml` runs hourly and is green on `main`.
- Phase 3 check 78 is narrowed with its addendum line, and
  `docs/operations/staging.md` holds the runbooks and the free-tier
  arithmetic.
- **Deployed & verified:** through the edge with the service token from the
  maintainer's keyring, staging `/version` reports this step's merge SHA, a
  data-free run returns the bytes the wheel's Python API returns, a
  hosted-safe series (a keyless originator such as Treasury) answers 200
  with its attribution, and a library-only source answers 403 with a licence
  explanation; the deploy job's own verification passed on the same SHA.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, zizmor clean on both workflows — IAM is
  least-privilege, the workload identity condition names the repository and
  `main`, and no secret value appears in the repository, a log or the PR.

---

## Step 14 — 1.0.0b1 Readiness Gate

**Status:** Not started

> **Goal:** Decide, on evidence, whether the exact candidate may become
> `1.0.0b1`. Tag `main`'s HEAD `v1.0.0b1.devN` so `release.yml` publishes
> the rehearsal to TestPyPI with attestations, and prove the rehearsal is
> byte-identical to a local `uv build --no-config` of the same commit;
> confirm staging runs that commit (`/version` through the edge); from
> clean venvs on the rehearsal, prove the core install's `pyeconomics` CLI
> (one model per domain, a keyless hosted-safe series, `keys list`), the
> `[server]` install's `pyeconomics serve` and the `[mcp]` install's
> `pyeconomics mcp` through `uvx`; run MCP Inspector over stdio on the
> rehearsal and over Streamable HTTP on staging's `/mcp` through the edge,
> the scripted agent tasks, and Step 9's live agent evaluation on the
> candidate; run a parity sample (one golden case per domain) through
> staging against the local Python API, a burst test through the edge that
> shows both Cloudflare's rule and the app's limiter answering 429, and the
> SSRF test's URL-shaped requests against staging; read the candidate
> image's scan; and write `docs/releases/1.0.0b1-readiness.md` (fourteen
> sections, the `1.0.0a2-readiness.md` shape), ending in the maintainer's
> GO or NO-GO. Parent: ROADMAP §5 "Promotion path and cutovers"
> ("Readiness gate before an irreversible cutover"); this roadmap's Version
> rule.

**Branch:** `feature/phase04-step14-readiness`

**Deploys:** TestPyPI — `release.yml` publishes the `v1.0.0b1.devN` tag
(pushed on the merged `main` HEAD, with the maintainer's approval) to
TestPyPI with attestations; staging redeploys on this step's merge, as on
every merge.

| Setting      | Cost                                   | Balanced                                   | Quality                                    |
| ------------ | -------------------------------------- | ------------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                            | Sonnet 5.5                                 | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                  | Claude Code                                | Claude Code                                |
| Effort       | Intelligence Medium                    | Effort XHigh                               | Effort XHigh                               |
| AA Index     | 47.8                                   | 51.9                                       | 56                                         |
| Thinking     | —                                      | —                                          | —                                          |
| Conversation | **New**                                | **New**                                    | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Agentic is PRIMARY and planning SECONDARY: a long
verification run across TestPyPI, clean environments, staging, the MCP
Inspector and a live agent, ending in a written judgement the maintainer
signs. Complexity is High — many independent proofs, each with its own
failure modes, and an irreversible release behind them — but the pattern
is Phase 3 Step 18's, so it is not novel. The ladder's Balanced column
runs: Sonnet 5.5 on Claude Code at Effort XHigh (claude.ai Max; AA
Intelligence Index 51.9), backed by Gemini 4 Argon on Antigravity. Cost is
GPT-6.1 Sol on Codex at Intelligence Medium (ChatGPT Pro 5x; 47.8) and
Quality Opus 5.5 on Claude Code at Effort XHigh (56.0). New conversation
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
       feature/phase04-step14-readiness`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - Live recipes read keys and the service token only
      through the credential chain and the maintainer's
      keyring, in isolated configuration and cache
      directories with unrelated *_API_KEY variables removed;
      nothing prints a key, a token or an environment value,
      and the readiness record quotes none.
    - The burst test stays inside the free tiers (a bounded
      number of requests, recorded) and never targets a host
      but staging.
    - The candidate image's scan has no fixable Critical or
      High finding, and the TestPyPI files' provenances are
      verified before any GO.
  </security>

  <context>
    pyeconomics. Phase 4. Step 14: 1.0.0b1 readiness gate.

    Current state (post-Phase-4 Step 13):

    - Steps 1–13 are on main at 1.0.0b1.dev1: the CLI,
      exports, REST API, hosted mode, MCP server, parity,
      AI narrative and container; staging deploys on every
      merge and staging-health.yml probes it hourly.
    - release.yml routes a .devN tag to TestPyPI with PEP 740
      attestations and calls release-smoke.yml.
      docs/releases/1.0.0a2-readiness.md is the fourteen-
      section shape this record follows.
    - Phase 3's gate lessons hold: PyPI's JSON can list a
      version before the simple index serves it; a changed
      candidate (a maintenance merge included) needs a fresh
      rehearsal and a fresh GO; the full suite takes about
      16–19 minutes serially, and the required profile is
      HYPOTHESIS_PROFILE=ci.

    Files to read (every file before drafting):
    - docs/releases/1.0.0a2-readiness.md and 1.0.0a2.md.
    - .github/workflows/release.yml, release-smoke.yml,
      deploy-staging.yml and staging-health.yml.
    - docs/cli.md, docs/api.md, docs/mcp.md,
      docs/mcp-evaluations.md, docs/exports.md and docs/ai.md.
    - scripts/mcp_agent_eval.py and tests/parity/.
    - docs/operations/staging.md.
  </context>

  <goal>
    A v1.0.0b1.devN rehearsal on TestPyPI, byte-identical to
    a local build, proven end to end from clean installs and
    on staging, recorded in a fourteen-section readiness
    document that ends in the maintainer's GO or NO-GO.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, one batched request: approval to push the
      v1.0.0b1.devN tag; whether to hold maintenance merges
      until the release (recommended: hold, since any merge
      changes the candidate); and the live recipes' scope
      (which keys and the service token from the keyring).
    </requirement>

    <requirement>
      Rehearsal: version 1.0.0b1.devN on a fix/ branch only if
      a NO-GO forced one (otherwise main's version is
      already a dev release of 1.0.0b1); tag main's HEAD;
      the TestPyPI wheel and sdist each carry a provenance;
      a local `uv build --no-config` of the tagged commit is
      byte-identical (record both SHA-256 values).
    </requirement>

    <requirement>
      Clean installs from TestPyPI (`uv venv --no-config`,
      `uv pip install --no-config --index-url
      https://test.pypi.org/simple/ --extra-index-url
      https://pypi.org/simple/ ...`): the core install runs
      `pyeconomics --version`, `scripts/smoke.py --all
      --min-domains 13`, one `models run` per domain, a
      keyless hosted-safe `data get` and `keys list`; the
      server install answers on `pyeconomics serve`; the mcp
      install runs through `uvx --from` and passes the
      Inspector over stdio.
    </requirement>

    <requirement>
      Staging: /version through the edge equals the tagged
      SHA; the Inspector over Streamable HTTP on /mcp with the
      service token's headers (or the SDK's Client with them,
      if the Inspector cannot send headers); the parity sample
      equals the local Python API; the burst test records
      429s from Cloudflare's rule and from the app's limiter
      (Retry-After present); URL-shaped targets answer 4xx.
    </requirement>

    <requirement>
      Agents: the scripted task set passes against the
      rehearsal; scripts/mcp_agent_eval.py reruns Step 9's
      live evaluation on the candidate and every task
      succeeds; record the date, agent and model.
    </requirement>

    <requirement>
      docs/releases/1.0.0b1-readiness.md: fourteen sections —
      candidate and its digests; scope against ROADMAP §4 4;
      CI at the candidate; parity; the CLI; exports and
      bundles; the REST API and hosted mode; the MCP server
      and agents; the AI narrative; the container and its
      scan; staging and operations; security; known
      limitations and open issues with owners; the decision.
      No unresolved FAIL. Ask the maintainer for GO or NO-GO
      in chat (one question, with the evidence summarized)
      and record `Decision: GO` or `Decision: NO-GO` with the
      date. A NO-GO names the fix and the rerun.
    </requirement>

    <requirement>
      Filepath comment: the readiness document follows
      docs/releases' convention.
    </requirement>
  </requirements>
</task>
```

### Step 14 acceptance criteria

- `v1.0.0b1.devN` is on TestPyPI with a provenance for its wheel and sdist,
  byte-identical to a local build of the tagged commit.
- Clean installs prove the core CLI, `pyeconomics serve` and `pyeconomics
  mcp` through `uvx`, and the Inspector passes over stdio on the rehearsal
  and over Streamable HTTP on staging.
- Staging reports the tagged SHA, the parity sample matches the local
  Python API, and the burst test records 429s from both layers.
- The scripted tasks and the live agent evaluation succeed on the candidate.
- `docs/releases/1.0.0b1-readiness.md` has fourteen sections, no unresolved
  FAIL and the maintainer's `Decision: GO` line with its date.
- **Deployed & verified:** TestPyPI's `1.0.0b1.devN` lists a wheel and an
  sdist, each with a provenance, and a clean venv installs it and runs
  `pyeconomics --version` and the smoke across 13 domains.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the candidate image scans clean, and the
  readiness record quotes no key, token or environment value.

---

## Step 15 — 1.0.0b1 Release

**Status:** Not started

> **Goal:** Publish the approved candidate as `1.0.0b1` and every surface
> that ships with it. Move the version to `1.0.0b1` with `CITATION.cff` in
> step, date the `CHANGELOG.md` section, write `docs/releases/1.0.0b1.md`
> (what the CLI, exports, REST API, MCP server and AI narrative do; what
> changed from `1.0.0a2`; known limitations, among them the hosted series
> route's per-request fetch until Phase 5's snapshots; open issues with
> owners), update `README.md` and `docs/index.md` (the surfaces are here,
> the CLI and MCP quick-starts linked, the `mcp-name:` marker kept), and
> confirm `scripts/release_ledger.py --check` passes with the ledgers
> unchanged (this phase adds no model, provider or concept id); then, with
> the maintainer's one batched approval, merge, tag `v1.0.0b1` on the merged
> `main`, approve the protected `pypi` deployment, publish the GitHub
> pre-release, approve the `mcp-registry` deployment that registers
> `io.github.pyeconomics-dev/pyeconomics`, and verify everything in
> production: PyPI's files and provenances, clean installs of the CLI and
> the MCP server, plain `pip install pyeconomics` still resolving 0.2.6,
> the MCP Registry's entry, staging at the release SHA, and the surface
> guides on the Read the Docs `main` preview. Parent: ROADMAP §4 4.8;
> ADR-0003 (`v1.0.0b1` is Phase 4's pre-release); ADR-0012 decision 16.

**Branch:** `feature/phase04-step15-release`

**Deploys:** PyPI (`v1.0.0b1`, a pre-release, behind the protected `pypi`
environment), the GitHub pre-release, the MCP Registry (through
`mcp-registry.yml` behind the protected `mcp-registry` environment), the
Read the Docs `main` preview (the surface guides) and staging (redeployed
by the merge); the Deployed & verified check covers each.

| Setting      | Cost                                   | Balanced                               | Quality                                    |
| ------------ | -------------------------------------- | -------------------------------------- | ------------------------------------------ |
| Model        | Haiku 5.5                              | Gemini 4 Argon                         | Opus 5.5                                   |
| Backup       | GPT-6.1 Sol — Codex · Intelligence Low | Opus 5.5 — Claude Code · Effort Medium | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Claude Code                            | Antigravity                            | Claude Code                                |
| Effort       | Effort Medium                          | Effort High                            | Effort High                                |
| AA Index     | 34.5                                   | 52.6                                   | 53.6                                       |
| Thinking     | —                                      | On                                     | —                                          |
| Conversation | **New**                                | **New**                                | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Agentic is PRIMARY and coding SECONDARY: a release
checklist across version files, notes, a tag, two protected deployments,
a registry and a set of production checks, with every decision already
made by Step 14's GO. Complexity is Medium — Phase 3 Step 19 is the
pattern, and the only new surface is the MCP Registry — and it is not
novel. The ladder's Balanced column runs: Gemini 4 Argon on Antigravity at
Effort High with Thinking on (Google AI Pro; AA Intelligence Index 52.6),
backed by Opus 5.5 on Claude Code at Effort Medium. Cost is Haiku 5.5 on
Claude Code at Effort Medium (claude.ai Max; 34.5) and Quality Opus 5.5 on
Claude Code at Effort High (53.6). New conversation per phase-boundary
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
       feature/phase04-step15-release`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
    - Publishing uses Trusted Publishing (OIDC) with PEP 740
      attestations, and the MCP Registry uses GitHub OIDC; no
      upload token or registry token is created or stored.
    - The release changes only what Step 14's readiness
      record allows (the version, the dated changelog, the
      notes, the README and index text): a diff against the
      approved candidate proves it, or the gate reruns.
    - Release notes, the GitHub release and the registry entry
      quote no key, token, contact or environment value.
  </security>

  <context>
    pyeconomics. Phase 4. Step 15: 1.0.0b1 release.

    Current state (post-Phase-4 Step 14):

    - docs/releases/1.0.0b1-readiness.md records the
      maintainer's GO for v1.0.0b1.devN at its commit, and
      lists what the release may still change.
    - release.yml publishes a non-dev v* tag to PyPI behind
      the pypi environment, with attestations, then runs
      release-smoke.yml; mcp-registry.yml runs on a published
      GitHub release behind the mcp-registry environment.
    - README.md carries the mcp-name marker; server.json's
      version follows pyproject.toml.
    - Phase 3 Step 19's lessons: PyPI's JSON lists a version
      before the simple index serves it (retry a fresh
      lookup before calling an install failed); plain pip on
      Python 3.12 resolves 0.2.6, whose Requires-Python is
      >=3.11,<3.13.

    Files to read (every file before drafting):
    - docs/releases/1.0.0b1-readiness.md, 1.0.0a2.md and the
      CHANGELOG.
    - .github/workflows/release.yml, release-smoke.yml and
      mcp-registry.yml; server.json.
    - README.md, docs/index.md, CITATION.cff and
      scripts/release_ledger.py.
  </context>

  <goal>
    `pip install --pre pyeconomics==1.0.0b1` gives a working
    CLI and, with [mcp], a working MCP server; PyPI holds
    both files with provenances; the GitHub pre-release and
    the MCP Registry entry exist; staging runs the release
    SHA; the documentation preview serves the surface guides.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Prepare: `uv version 1.0.0b1 --no-config`, CITATION.cff
      and server.json to match; date the CHANGELOG section;
      write docs/releases/1.0.0b1.md; update README.md's
      status line and docs/index.md's text and toctree (the
      CLI, API, MCP, exports and AI guides; the Cross-phase
      table's sentence); `release_ledger.py --check` passes
      with no ledger change. Compare the archives' contents
      with the approved candidate's, allowing only the
      readiness record's list.
    </requirement>

    <requirement>
      ONE batched approval from the maintainer, in chat,
      for: the merge, the v1.0.0b1 tag, the pypi deployment
      review, the GitHub pre-release, the mcp-registry
      deployment review and the live recipes. Relay the
      approval to the PR as the maintainer's, given in the
      session; do not ask again for any of them.
    </requirement>

    <requirement>
      Release: merge; tag the merged commit; approve the pypi
      deployment; after release-smoke passes, publish the
      GitHub release as a pre-release (latest false); approve
      the mcp-registry deployment; read the registry entry
      back through its public API.
    </requirement>

    <requirement>
      Verify in production: both PyPI files with provenances
      and digests equal to the workflow's; clean venvs on
      Python 3.12 and 3.15 — `pip install --pre
      pyeconomics==1.0.0b1` runs `pyeconomics --version`,
      the smoke across 13 domains, one `models run` per
      domain and a keyless hosted-safe `data get`; `uvx
      --from "pyeconomics[mcp]==1.0.0b1" pyeconomics mcp`
      passes the Inspector's list and call; plain `pip
      install pyeconomics` on Python 3.12 installs 0.2.6;
      staging /version through the edge reports the release
      commit; the Read the Docs main build at that commit
      serves cli, api, mcp, exports and ai, and stable still
      serves 0.2.6.
    </requirement>

    <requirement>
      If maintenance merges were held at Step 14, release the
      hold only after every check above passes.
    </requirement>
  </requirements>
</task>
```

### Step 15 acceptance criteria

- `pyproject.toml`, `CITATION.cff` and `server.json` read `1.0.0b1`; the
  `CHANGELOG.md` section is dated; `docs/releases/1.0.0b1.md`, `README.md`
  and `docs/index.md` describe the shipped surfaces; the ledgers are
  unchanged and their check passes.
- `v1.0.0b1` is tagged on the merged `main`, PyPI lists a wheel and an sdist
  for it, each with a provenance, and the GitHub release is a published
  pre-release.
- The MCP Registry lists `io.github.pyeconomics-dev/pyeconomics` at
  `1.0.0b1`, read back through its public API.
- **Deployed & verified:** in clean venvs, `pip install --pre
  pyeconomics==1.0.0b1` gives a working `pyeconomics` CLI (version, the smoke
  across 13 domains, a run per domain, a keyless hosted-safe series) and
  `uvx --from "pyeconomics[mcp]==1.0.0b1" pyeconomics mcp` passes the
  Inspector; plain `pip install pyeconomics` on Python 3.12 still installs
  0.2.6; staging `/version` reports the release SHA through the edge; the
  Read the Docs `main` preview serves the CLI and MCP quick-starts and the
  API, exports and AI guides at the release commit.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — both publications used OIDC with no stored
  token, and no release text quotes a credential.

---

## Step 16 — QA and Verification Script

**Status:** Not started

> **Goal:** Package the phase's verification matrix into
> `scripts/verify-phase04.sh` — Phase 3's `--fast`, `--python`,
> `--security`, `--live`, `--all` and `--post` modes plus `--node` (the
> TypeScript client, the MCP Inspector and `npm audit`) and `--container`
> (the image build, scan and smoke), with independent static checks for
> every Step 1–15 deliverable, Step 16 self-checks and the V1–V16 matrix —
> plus its pytest twin `tests/repo/test_phase04.py` and its live helper
> `scripts/verify_phase04_live.py`; produce `docs/phase04-qa-findings.md`,
> the rollup of every finding, its class, its destination and its guard;
> add `"04"` to `.github/workflows/phase-verify.yml`'s matrix and make both
> `phase-verify` jobs for `04` required; prove the staging health alarm
> with a synthetic failure that reaches the maintainer, and the budget's
> programmatic notification; run `verify-phase03.sh --post` (which runs
> Phases 2 and 1's) to show the earlier ledgers still hold; and mark Phase 4
> complete here and in the parent roadmap. Parent: ROADMAP §5 "Operations &
> observability strategy" ("Acceptance") and this roadmap's
> Post-Implementation Verification.

**Branch:** `feature/phase04-step16-verify`

**Deploys:** nothing beyond merge — the CI matrix entry is live on merge;
the required-check update and the synthetic alarms are part of the step,
and staging redeploys on the merge as on every merge.

| Setting      | Cost                                     | Balanced                             | Quality                                    |
| ------------ | ---------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Model        | GPT-6.1 Sol                              | Gemini 4 Argon                       | Opus 5.5                                   |
| Backup       | Sonnet 5.5 — Claude Code · Effort Medium | Opus 5.5 — Claude Code · Effort High | Gemini 4 Argon — Antigravity · Effort High |
| Platform     | Codex                                    | Antigravity                          | Claude Code                                |
| Effort       | Intelligence Low                         | Effort High                          | Effort High                                |
| AA Index     | 42.1                                     | 52.6                                 | 53.6                                       |
| Thinking     | —                                        | On                                   | —                                          |
| Conversation | **New**                                  | **New**                              | **New**                                    |

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that column's usage pool reads `tight`, run its Backup when the Backup's pool has headroom, else the Cost column; if it reads `exhausted`, run its Backup.

**Model rationale:** Coding is PRIMARY and agentic SECONDARY: the
mechanical translation of `verify-phase03.sh` into this phase's
deliverables, two new modes, a QA rollup, two synthetic alarms and a
required-check update. Complexity is Medium — the template, the check list
and the V-matrix are fixed here — and it is not novel. The ladder's
Balanced column runs: Gemini 4 Argon on Antigravity at Effort High with
Thinking on (Google AI Pro; AA Intelligence Index 52.6). Cost is GPT-6.1
Sol on Codex at Intelligence Low (ChatGPT Pro 5x; 42.1) and Quality Opus
5.5 on Claude Code at Effort High (claude.ai Max; 53.6). New conversation
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
       feature/phase04-step16-verify`
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
       Phase 4 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 4`
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
       complete. Phase 4 is
       complete. You can now move
       on to Phase 5." That
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
       one before Phase 5.
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
      the whole-tree gate, semgrep-test, the layering and
      import tests, an orphan-clone secret scan, the cassette
      scan and npm audit; it exits non-zero on any finding.
    - The verifier never prints a key, a token or an
      environment value: --live checks secrets by name only,
      reads the service token through the keyring, and
      --post's recipes read keys only through the credential
      chain in isolated directories.
    - The synthetic alarm is a dispatched run with its
      documented input; nothing weakens a workflow's
      permissions or triggers to stage it.
    - The phase-verify change keeps permissions: {} and the
      existing per-job permissions; zizmor stays clean.
  </security>

  <context>
    pyeconomics. Phase 4. Step 16: QA and verification
    script.

    Steps 1 through 15 have been implemented: 1.0.0b1 is on
    PyPI and the MCP Registry; staging deploys on every merge
    and staging-health.yml probes it hourly.

    Reference scripts (pattern templates):
    - scripts/verify-phase03.sh (the structural template:
      the mode contract, record / check / vcheck / vstatic,
      the `PASS  12     <description>` format, the per-mode
      summary, the standard-library static checks and the
      Bash credential backstop).
    - scripts/verify_phase03_live.py (the isolated live
      helper) and tests/repo/test_phase03.py (the twin).

    Phase 4 deliverables to verify — static checks 1–59
    across Steps 1–15 and self-checks 60–64, numbered as
    below so the script, its V-matrix and this roadmap
    agree; each an independent, "at least" invariant a later
    phase will not break:

    Step 1 (checks 1–3): the roadmap and kit tracked; the
    concurrency regression test and core/context.py's
    mechanism; the audit's threaded tests.
    Step 2 (4–8): ADR-0012 Accepted and indexed with its
    decisions; surfaces/ (invoke, problems, codec, envelope,
    budgets); the surfaces coverage floor; the layering
    test; the parent amendments (Upstash Redis, no "Upstash
    Valkey", the staging edge, no hosted API keys before
    Phase 8).
    Step 3 (9–11): registry_export and registry_schema; the
    schema snapshot tests; docs/registry.md.
    Step 4 (12–16): the pyeconomics console script; cyclopts
    as a floor-only runtime dependency; cli/'s command
    groups; data.credentials' store_key, delete_key and
    key_source; docs/cli.md in the toctree.
    Step 5 (17–20): exports/ and its writers; bundle check
    and the reproduce template; the per-provider notice
    export test; docs/exports.md.
    Step 6 (21–24): [server] with fastapi and uvicorn, in
    [all]; server/ (app factory, pool, serve's loopback
    guard); the OpenAPI snapshot test; docs/api.md.
    Step 7 (25–29): limits[redis] in [server]; the fuzz group
    with its marker and the api-fuzz job in the aggregate;
    tools/node with its lockfile and the clients job; the
    npm-audit hook and the npm ecosystem; the disable switch
    and SourceDisabledError.
    Step 8 (30–34): [mcp] with mcp>=2.3, in [all]; mcp/ and
    its headline list; the tools/list snapshot test; the
    mcp-inspector job in the aggregate; the llm_use policy
    and its resolver skip reason, and docs/mcp.md.
    Step 9 (35–38): the MCP Apps resource; server.json at the
    project version and README's mcp-name marker;
    mcp-registry.yml (OIDC, its environment, the checksum
    pin, its permissions); docs/mcp-evaluations.md.
    Step 10 (39–41): tests/parity/; the generator guard; the
    parity job in the aggregate.
    Step 11 (42–44): ai/ with its providers and dated price
    table; [ai] in [all] and docs/ai.md; no AI client library
    in the runtime closure.
    Step 12 (45–47): the Dockerfile (base pinned by digest,
    non-root user, hosted mode) and .dockerignore's
    exclusions; the container job in the aggregate; the
    docker ecosystem.
    Step 13 (48–52): deploy-staging.yml (push to main and
    dispatch, the staging environment, id-token: write only
    on the deploy job, auth by SHA, no key input);
    staging-health.yml (schedule and dispatch only, issues:
    write only in the report job); docs/operations/staging.md;
    the edge's source and test; the Phase 3 addendum line.
    Step 14 (53–54): the readiness document's fourteen
    sections and its `Decision: GO` line; a v1.0.0b1.dev* tag
    on main.
    Step 15 (55–59): the v1.0.0b1 tag merged into main; the
    dated CHANGELOG section; the release notes; README and
    index text; the ledgers holding every id of earlier
    phases, unchanged.
    Step 16 self-checks (60–64): verify-phase04.sh exists and
    is executable; docs/phase04-qa-findings.md exists;
    docs/roadmap/phase04-roadmap.md exists; phase-verify.yml's
    matrix includes "04" (63); and the security backstop —
    the gate's hooks configured, the security workflow
    present, no private-key, AWS, GitHub or PyPI token
    pattern in the tree (patterns assembled at run time),
    and no workflow but providers-live.yml,
    deploy-staging.yml and staging-health.yml reading a
    secret.

    Files to read:
    - scripts/verify-phase03.sh end to end, and
      scripts/verify_phase03_live.py.
    - tests/repo/test_phase03.py and
      .github/workflows/phase-verify.yml,
      staging-health.yml and deploy-staging.yml.
    - docs/phase03-qa-findings.md (the rollup's shape) and
      every Phase 4 PR body (findings and their
      destinations).
  </context>

  <goal>
    scripts/verify-phase04.sh with the static checks, the
    self-checks and the V1–V16 matrix in eight modes;
    tests/repo/test_phase04.py; scripts/verify_phase04_live.py;
    docs/phase04-qa-findings.md; "04" in phase-verify.yml's
    matrix and required; the staging alarm and the budget
    notification proven; the earlier phases' --post green;
    and Phase 4 marked complete in both roadmaps.
  </goal>

  <requirements>
    <requirement>
      Read scripts/verify-phase03.sh end to end for its
      structure, flag parsing, output format, helpers and
      summary, and mirror them exactly so the Phase 4 script
      is visually continuous with Phase 3's in CI logs.
    </requirement>

    <requirement>
      scripts/verify-phase04.sh modes:
      - --fast (default): the static checks only, CI-safe on
        Ubuntu, standard-library Python and Bash, no network,
        no package import; under 30 seconds.
      - --python: static checks plus `uv sync --locked
        --all-extras --group docs`, ruff, mypy, the full suite
        with coverage and the floors (core, models, data,
        surfaces), registry, provider and binding validation,
        the parity suite, the fuzz group on a 3.14
        interpreter, the docs build, the build and artifact
        checks, and the clean-wheel smoke across 13 domains
        with and without extras, on the project's interpreter.
      - --node: `npm ci` and `npm audit --audit-level=high` in
        tools/node, the TypeScript client generated and
        type-checked, the edge Worker's tests, and the
        Inspector over stdio and Streamable HTTP.
      - --container: the image built, scanned (fixable
        Critical or High fails) and smoke-tested.
      - --security: the whole-tree gate, semgrep-test, the
        layering and import tests, an orphan-clone secret
        scan, the cassette scan and npm audit.
      - --live: the maintainer's gh session and keyring: main
        requires both 04 jobs strictly; the staging
        environment deploys from main only and its secrets
        exist by name; no repository secret exists; the
        newest deploy-staging and staging-health runs on main
        succeeded; staging through the edge reports main's
        deployed SHA, runs a model, serves a hosted-safe
        series and answers 403 for a library-only one; PyPI
        and TestPyPI list 1.0.0b1 and its rehearsal with
        provenances; the GitHub pre-release; the MCP
        Registry's entry; Read the Docs serves the surface
        guides on main and 0.2.6 on stable.
      - --all: --fast, --python, --node, --container and
        --security.
      - --post: --all and --live, plus the published installs
        (V15.3) through scripts/verify_phase04_live.py
        (isolated configuration and cache, ambient keys
        removed, credential-chain reads, fixed verdict
        output), the alarm evidence (V16.5),
        verify-phase03.sh --post, which runs Phases 2 and 1's
        (V16.6), and `gh pr checks` for the current branch.
      Every static check uses grep, test, git ls-files or the
      standard library, prints one PASS or FAIL line with its
      number, consumes its whole input, and is independent of
      the others.
    </requirement>

    <requirement>
      The V-matrix mirrors this roadmap's Post-Implementation
      Verification section exactly: Vn.1 aggregates Step n's
      static checks; Vn.2 onward are the command checks each
      V table names; V16.1–V16.8 cover --fast in CI, the
      matrix entry, all static checks, --security, the alarm,
      the earlier phases, the required checks and the staging
      environment.
    </requirement>

    <requirement>
      tests/repo/test_phase04.py, the twin of the
      self-checks: test_roadmap_doc_exists,
      test_qa_findings_doc_exists,
      test_verify_script_exists_and_executable (mode 100755
      in the index) and test_phase_verify_matrix_includes_04.
    </requirement>

    <requirement>
      .github/workflows/phase-verify.yml: append "04" to both
      matrix lists, nothing else. Once both jobs pass on this
      PR, the maintainer (batched at kickoff) adds
      phase-verify-fast (04) and phase-verify-security (04)
      to main's required checks, re-sending every existing
      context, strict: 24 in all.
    </requirement>

    <requirement>
      Alarms (ROADMAP §5 "Acceptance"): dispatch
      staging-health.yml on main with simulate_failure: true;
      the run fails, the report job opens one staging-health
      issue and closes older ones, and GitHub's failure
      notification reaches the maintainer, who confirms it;
      pull one programmatic budget notification from the
      budget's Pub/Sub subscription (budget id and amount
      only, no billing account details in the record). Record
      the run URL, the confirmation line `Notification
      received: confirmed by the maintainer` (only after an
      affirmative reply) and the notification's timestamp in
      docs/phase04-qa-findings.md, close the synthetic issue
      with a comment pointing at the QA document, and
      dispatch staging-health.yml again with its default
      input so the newest run on main is green before --live
      and --post run.
    </requirement>

    <requirement>
      docs/phase04-qa-findings.md: one rollup per step (Steps
      1–15) as a table of finding, class, destination and
      guard; a Step 16 verification rollup; the synthetic
      alarm; a Phase 4 acceptance audit against ROADMAP §4
      4's acceptance criteria; Pre-ship items with an owner
      for every open issue (and every Wheel-rule marker); and
      the final verification evidence.
    </requirement>

    <requirement>
      Cross-phase: run verify-phase03.sh --post (which runs
      verify-phase02.sh --post, which runs Phase 1's); a check
      Phase 4 legitimately broke is narrowed under the
      Cross-phase verification rule with an addendum line at
      the end of that phase's roadmap, never deleted.
    </requirement>

    <requirement>
      Mark the phase complete in the parent project roadmap
      (docs/roadmap/ROADMAP.md) in the SAME Stage-3 commit
      that marks this step (Status rule):
      - `### Phase 4` gets `**Status:** Complete —
        <YYYY-MM-DD>; PR #<n>; v1.0.0b1;
        phase04-roadmap.md` directly under its heading, and
        the heading ends in ✅.
      - Its row in the "Phase Complexity Summary" table reads
        `Complete` (Step 1's PR set it to `In progress`).
      - The header `> **Status:**` line names Phase 4 as
        shipped and Phase 5 as next.
      - Consistency audit: the Phase 4 "Acceptance criteria"
        there match this roadmap's V1–V16 checks, as amended
        by Step 2.
      And in THIS roadmap, same commit: its phase-level
      `**Status:**` line reads `Complete — <YYYY-MM-DD>`, the
      title and every step heading end in ✅, and every
      step's Summary Table Status cell reads `Complete — PR
      #<n>`.
    </requirement>

    <requirement>
      The script is executable (`git update-index
      --chmod=+x`), prints a clear PASS or FAIL per check,
      exits 0 on success and 1 on any failure, and mirrors
      verify-phase03.sh's output format, numbering and summary
      table. --fast completes in under 30 seconds on Ubuntu
      CI. Never edit the script, or any tracked file, while a
      run of it is in progress, and after stopping a run
      verify its uv and pytest descendants stopped too.
    </requirement>

    <requirement>
      Filepath comment: the script `# scripts/verify-phase04.sh`
      after its shebang; the Python files the three-line
      header; the QA document follows docs/'s convention.
    </requirement>
  </requirements>
</task>
```

### Step 16 acceptance criteria

- `scripts/verify-phase04.sh` exists, is executable, and passes on a clean
  tree post-implementation, with static checks 1–64 and the V1–V16 matrix in
  all eight modes.
- `--fast` runs in under 30 seconds on Ubuntu CI, and `--post` passes on the
  maintainer's machine with every live check and published install green.
- `docs/phase04-qa-findings.md` is complete with every rollup section, the
  alarm evidence, the acceptance audit and the pre-ship owners.
- `.github/workflows/phase-verify.yml`'s matrix includes `04`, both jobs
  pass on every PR, and `main` requires them, strictly (24 checks).
- `--security` exists and exits 0 (secret/PII scan, SAST, dependency audit,
  licences, cassette scan and `npm audit` clean over the phase's surface);
  V16.4 is green.
- Branch protection still passes on the resulting PR, and
  `verify-phase03.sh --post` passes, including its nested Phase 2 and Phase 1
  runs.
- **Operations:** the staging service is this phase's runtime surface; its
  health signal is `/healthz` and `/version` through the edge, probed hourly
  by `staging-health.yml`; the probe failed once on a synthetic dispatch,
  opened its `staging-health` issue, and the maintainer confirmed the
  notification; the budget's programmatic notification was received; both
  recorded in `docs/phase04-qa-findings.md` (ROADMAP §5 "Operations &
  observability strategy").
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff and the security workflow is
  green.
- **Phase closed, nothing carried.** Every finding recorded in
  `docs/phase04-qa-findings.md` has a destination (fixed, an issue number,
  or a named phase that owns it), the "Not in scope" section below is
  current, and no un-tracked item remains. Every step of this roadmap, this
  one included, reads `**Status:** Complete — PR #…` on `main` under a ✅
  heading, the Summary Table's Status column and this roadmap's phase-level
  Status line say `Complete` under a ✅ title, and the parent project
  roadmap's Phase 4 entry (under a ✅ heading), its summary-table row, and
  its header status line say `Complete` — all landed in this step's PR. This
  step's final response ends with two lines and nothing after them: "Step 16
  is complete. Phase 4 is complete. You can now move on to Phase 5." — same
  Stage 6 rule: no "Follow-ups", no trailer.

---

## Post-Implementation Verification

Every V1–V16 check below runs **automatically in CI** on every push and
pull request — no manual invocation required — except three kinds. The
`--live` and `--post` checks read state that needs the maintainer's
authenticated `gh` session and keyring (branch protection, the `staging`
environment and its secrets by name, the newest deploy and probe runs, the
staging edge through the Cloudflare Access service token, the GitHub
release), external registries and services (PyPI, TestPyPI and their
integrity APIs, the MCP Registry's API, the Read the Docs API), clean-venv
installs from PyPI, and the operator-observed alarm notification; they run
on the maintainer's machine with `./scripts/verify-phase04.sh --post`
before Phase 4 is declared complete. The live agent evaluation of Steps 9
and 14 runs on the maintainer's machine and is read back from
`docs/mcp-evaluations.md`. The staging service is deployed by
`deploy-staging.yml` on every merge and probed hourly by
`staging-health.yml`, and `--live` reads their latest results.

| Mode             | Workflow                                              | Runner                   | Coverage                                                                  |
| ---------------- | ----------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------- |
| `--fast`         | `phase-verify.yml` (matrix entry `04`, fast job)      | Ubuntu                   | Static checks 1–64; V1.1–V15.1, V16.1–V16.3                               |
| `--python`       | `ci.yml` (lint, types, tests, package, pyodide, docs, api-fuzz and parity jobs run the same commands); local | Ubuntu, Windows, macOS | V1.2, V2.2, V3.2, V4.2, V4.3, V5.2, V5.3, V6.2, V7.2, V8.2, V9.2, V10.2, V10.3, V11.2 |
| `--node`         | `ci.yml` (clients and mcp-inspector jobs); local      | Ubuntu                   | V7.3, V8.3 (and the edge Worker's tests)                                  |
| `--container`    | `ci.yml` (container job); local                       | Ubuntu                   | V12.2, V12.3                                                              |
| `--security`     | `phase-verify.yml` (security job); `security.yml`     | Ubuntu                   | V2.3, V16.4 (secret/PII scan + SAST + dependency audit + licences + cassette scan + npm audit) |
| `--live`         | local only — the maintainer's `gh` session and keyring | Maintainer's machine    | V1.3, V7.4, V13.2, V13.3, V13.4, V14.2, V15.2, V16.7, V16.8               |
| `--all`          | local                                                 | Any                      | `--fast` + `--python` + `--node` + `--container` + `--security`           |
| `--post`         | local, before the phase is declared complete          | Maintainer's machine     | `--all` + `--live` + V15.3, V16.5, V16.6 + `gh pr checks`                 |

Local invocations remain available for ad-hoc runs and pre-release
sweeps:

```bash
./scripts/verify-phase04.sh --post   # static + V1-V16 + live + post checks
```

`--post` is the canonical command to run before declaring Phase 4
complete, and before tagging a later phase's release.

Other modes:

```bash
./scripts/verify-phase04.sh              # static checks (= --fast)
./scripts/verify-phase04.sh --fast       # static checks only (CI)
./scripts/verify-phase04.sh --python     # + tests, parity, docs, build
./scripts/verify-phase04.sh --node       # TS client, Inspector, npm
./scripts/verify-phase04.sh --container  # image build, scan, smoke
./scripts/verify-phase04.sh --security   # gate, licences, cassettes
./scripts/verify-phase04.sh --live       # GitHub, staging, registries
./scripts/verify-phase04.sh --all        # all but --live and --post
```

The script reports each V-check by id (V1.1, V2.1, …) so a failure in any
workflow above maps directly to the corresponding row below.

### V1 — Surfaces baseline and concurrency hardening

> **Automated in CI.** `phase-verify.yml` → V1.1; `ci.yml` → V1.2;
> `--live` → V1.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V1.1 | Static checks 1–3 all PASS (roadmap and kit tracked; the concurrency regression test and its mechanism; the audit's threaded tests). | `phase-verify.yml` runs `verify-phase04.sh --fast` on every push/PR. |
| V1.2 | The concurrency regression and the audit's threaded tests pass on every cell, with garch's 3.15 gap asserted. | `ci.yml` tests matrix (`--python` locally). |
| V1.3 | Issue #157 is closed.                                              | `--live` (`gh issue view`).                                               |

### V2 — ADR-0012 and the surface core

> **Automated in CI.** `phase-verify.yml` → V2.1 and V2.3; `ci.yml` →
> V2.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V2.1 | Static checks 4–8 all PASS (ADR-0012 Accepted and indexed; the surfaces modules; the surfaces floor; the layering test; the parent amendments). | `phase-verify.yml --fast`. |
| V2.2 | The surfaces suite passes — invoke, the error-table walk, the codec's limits, the envelope, the budgets and the canary scrub — and the surfaces floor holds. | `ci.yml` tests matrix with `coverage_floors.py` (`--python` locally). |
| V2.3 | The layering test passes: `core/` and `data/` import no surface, and `import pyeconomics` loads no framework. | `ci.yml` tests; `phase-verify.yml` security job (`--security`). |

### V3 — Registry export

> **Automated in CI.** `phase-verify.yml` → V3.1; `ci.yml` → V3.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V3.1 | Static checks 9–11 all PASS.                                       | `phase-verify.yml --fast`.                                                |
| V3.2 | `registry.json` validates against its schema, two exports are byte-identical, and every schema snapshot matches. | `ci.yml` tests matrix (`--python` locally). |

### V4 — The CLI

> **Automated in CI.** `phase-verify.yml` → V4.1; `ci.yml` → V4.2 and
> V4.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V4.1 | Static checks 12–16 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V4.2 | The CLI suite passes in-process and through the installed console script on every cell, with every exit code and the keys canaries; the package job's clean venv runs it. | `ci.yml` tests matrix and package job (`--python` locally). |
| V4.3 | The `pyodide` job builds the CLI app in Pyodide.                   | `ci.yml` `pyodide` job.                                                   |

### V5 — Exports and reproducibility bundles

> **Automated in CI.** `phase-verify.yml` → V5.1; `ci.yml` → V5.2 and
> V5.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V5.1 | Static checks 17–20 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V5.2 | Every format's tests pass, with the formula-injection read-backs, the Parquet pipe into pandas and the per-provider notice test. | `ci.yml` tests matrix (`--python` locally). |
| V5.3 | A bundle built from the wheel reruns to identical bytes in a fresh venv. | `ci.yml` package job (`--python` locally).                          |

### V6 — REST API

> **Automated in CI.** `phase-verify.yml` → V6.1; `ci.yml` → V6.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V6.1 | Static checks 21–24 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V6.2 | The server suite passes — every model through POST and GET, a problem per table row, every format, the pool's budget kill and queue limit, the loopback guard — and the OpenAPI snapshot is stable. | `ci.yml` tests matrix (`--python` locally). |

### V7 — Hosted mode, API fuzzing and generated clients

> **Automated in CI.** `phase-verify.yml` → V7.1; `ci.yml` → V7.2 and
> V7.3; `--live` → V7.4.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V7.1 | Static checks 25–29 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V7.2 | The hosted-mode suite passes (the refusal per class, limits and the burst test, edge trust, budgets, caching, the disable switch, SSRF), and Schemathesis finds no 5xx and no schema violation in either mode. | `ci.yml` tests matrix and `api-fuzz` job (`--python` locally). |
| V7.3 | The TypeScript client generates and type-checks, the Python client generates, and both return the Python API's bytes. | `ci.yml` `clients` job (`--node` locally). |
| V7.4 | Issue #162 is closed.                                              | `--live` (`gh issue view`).                                               |

### V8 — MCP server

> **Automated in CI.** `phase-verify.yml` → V8.1; `ci.yml` → V8.2 and
> V8.3.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V8.1 | Static checks 30–34 all PASS.                                      | `phase-verify.yml --fast`.                                                |
| V8.2 | The MCP suite passes — the `tools/list` snapshot in both modes, every headline tool and `run_model` equal to `Result.to_json()`, the `llm_use` gate, the scripted tasks, `server/discover`'s revisions. | `ci.yml` tests matrix (`--python` locally). |
| V8.3 | MCP Inspector passes over stdio and Streamable HTTP.               | `ci.yml` `mcp-inspector` job (`--node` locally).                          |

### V9 — MCP Apps, the MCP Registry entry and agent evaluations

> **Automated in CI.** `phase-verify.yml` → V9.1; `ci.yml` → V9.2.

| ID   | Check                                                              | Automation                                                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| V9.1 | Static checks 35–38 all PASS, including `docs/mcp-evaluations.md` with no failed task. | `phase-verify.yml --fast`.                           |
| V9.2 | The MCP Apps resource tests, `server.json`'s schema validation and the eight scripted tasks pass. | `ci.yml` tests matrix (`--python` locally). |

### V10 — Cross-surface parity

> **Automated in CI.** `phase-verify.yml` → V10.1; `ci.yml` → V10.2 and
> V10.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V10.1 | Static checks 39–41 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V10.2 | Every golden case and every bound model return identical bytes on the four surfaces, exports round-trip, and the generator guard passes, on every cell. | `ci.yml` tests matrix (`--python` locally). |
| V10.3 | The out-of-process parity sample passes on the installed wheel.  | `ci.yml` `parity` job (`--python` locally).                               |

### V11 — Optional AI narrative

> **Automated in CI.** `phase-verify.yml` → V11.1; `ci.yml` → V11.2.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V11.1 | Static checks 42–44 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V11.2 | The narrative suite passes offline: recorded providers, the cost, every refusal, LeakCheck and the price table's staleness test. | `ci.yml` tests matrix (`--python` locally). |

### V12 — Service container

> **Automated in CI.** `phase-verify.yml` → V12.1; `ci.yml` → V12.2 and
> V12.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V12.1 | Static checks 45–47 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V12.2 | The image builds and its scan finds no fixable Critical or High vulnerability; the SBOM is kept. | `ci.yml` `container` job (`--container` locally). |
| V12.3 | The running image serves a run equal to the wheel's bytes, answers 403 for library-only data, runs as non-root and holds no excluded library. | `ci.yml` `container` job (`--container` locally). |

### V13 — Staging on Cloud Run

> **Automated in CI.** `phase-verify.yml` → V13.1; `deploy-staging.yml`
> and `staging-health.yml` on `main`, read by `--live` → V13.2–V13.4.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V13.1 | Static checks 48–52 all PASS.                                     | `phase-verify.yml --fast`.                                                |
| V13.2 | The newest `deploy-staging` run on `main` succeeded, its verification through the edge included, and staging `/version` reports the deployed SHA. | `--live` (`gh run list`; a request through the edge). |
| V13.3 | Through the edge with the service token, a run equals the Python API, a hosted-safe series answers 200 with its attribution and a library-only source 403; without the token the hostname refuses; without the edge credential the origin answers 403. | `--live`. |
| V13.4 | The newest `staging-health` run on `main` succeeded, and the budget exists with its 50/90/100% thresholds. | `--live` (`gh run list`; a read-only budget query). |

### V14 — 1.0.0b1 readiness gate

> **Automated in CI.** `phase-verify.yml` → V14.1; `--live` → V14.2.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V14.1 | Static checks 53–54 PASS: the readiness document has fourteen sections, no unresolved FAIL and a `Decision: GO` line; a `v1.0.0b1.dev*` tag is on `main`. | `phase-verify.yml --fast`. |
| V14.2 | TestPyPI's `1.0.0b1.devN` lists a wheel and an sdist, each with a provenance. | `--live` (TestPyPI JSON and integrity APIs).                 |

### V15 — 1.0.0b1 release

> **Automated in CI.** `phase-verify.yml` → V15.1; `--live` → V15.2;
> `--post` → V15.3.

| ID    | Check                                                             | Automation                                                                |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V15.1 | Static checks 55–59 PASS (`v1.0.0b1` on `main`, the dated CHANGELOG section, the release notes, the README and index text, the unchanged ledgers). | `phase-verify.yml --fast`. |
| V15.2 | PyPI's `1.0.0b1` lists a wheel and an sdist with provenances, the GitHub release `v1.0.0b1` is a published pre-release, the MCP Registry lists `io.github.pyeconomics-dev/pyeconomics` at `1.0.0b1`, and Read the Docs serves the surface guides on `main`. | `--live` (PyPI and registry APIs; `gh release view`; the Read the Docs API). |
| V15.3 | A clean `pip install --pre pyeconomics==1.0.0b1` runs the CLI and the smoke across 13 domains; `uvx --from "pyeconomics[mcp]==1.0.0b1" pyeconomics mcp` passes the Inspector; plain `pip install pyeconomics` on Python 3.12 installs 0.2.6. | `--post`. |

### V16 — CI integration + security

> **Automated in CI.** `phase-verify.yml` → V16.1 through V16.4 and the
> `01`, `02` and `03` entries behind V16.6 on every push/PR; `--post` →
> V16.5 and V16.6; `--live` → V16.7 and V16.8.

| ID         | Check                                                          | Automation                                                                |
| ---------- | -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| V16.1      | `verify-phase04.sh --fast` exits 0 on Ubuntu CI.               | `phase-verify.yml` matrix entry `04`.                                     |
| V16.2      | `phase-verify.yml` matrix includes `04`.                       | `phase-verify.yml --fast` static check 63.                                |
| V16.3      | All static checks in `verify-phase04.sh` pass.                 | `phase-verify.yml --fast` records PASS only when no static check failed. |
| V16.4      | `verify-phase04.sh --security` exits 0 (secret/PII scan + SAST + dependency audit + licences + cassette scan + npm audit clean). | `phase-verify.yml` security job on every push/PR. |
| V16.5      | The `staging-health` alarm fired once on a synthetic failure, opened its issue, and the notification reached the maintainer; the budget's programmatic notification was received. | `--post` reads the recorded run's conclusion; the notification is recorded in `docs/phase04-qa-findings.md`. |
| V16.6      | Phases 1–3 stay green: their `--fast` modes exit 0 on every PR, and `verify-phase03.sh --post` (which runs Phases 2 and 1's) passes before the phase closes. | `phase-verify.yml` matrix entries `01`–`03`; `--post`. |
| V16.7      | `main` requires `phase-verify-fast (04)` and `phase-verify-security (04)`, with strict status checks (24 in all). | `--live` (`gh api .../required_status_checks`). |
| V16.8      | The `staging` environment deploys from `main` only, its secrets exist by name (configuration only; V13.3 proves their values), and no repository secret exists. | `--live` (`gh api` environments; `gh secret list`). |

---

## Summary Table

| Step    | Scope                            | Model             | Platform     | Reasoning dial      | Thinking | Conv | Status      |
| ------- | -------------------------------- | ----------------- | ------------ | ------------------- | -------- | ---- | ----------- |
| 1       | Surfaces baseline + concurrency  | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Complete — PR #175 |
| 2       | ADR-0012 + surface core          | Opus 5.5          | Claude Code  | Effort High         | --       | New  | Complete — PR #177 |
| 3       | Registry export                  | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 4       | The pyeconomics CLI              | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 5       | Exports + bundles                | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 6       | REST API                         | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 7       | Hosted mode, fuzzing + clients   | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 8       | MCP server                       | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 9       | MCP Apps, registry + evaluations | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 10      | Cross-surface parity             | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 11      | AI narrative                     | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 12      | Service container                | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 13      | Staging on Cloud Run             | Sonnet 5.5        | Claude Code  | Effort XHigh        | --       | New  | Not started |
| 14      | 1.0.0b1 readiness gate           | Sonnet 5.5        | Claude Code  | Effort XHigh        | --       | New  | Not started |
| 15      | 1.0.0b1 release                  | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| 16      | QA + verify-phase04.sh           | Gemini 4 Argon    | Antigravity  | Effort High         | On       | New  | Not started |
| V1      | Concurrency hardening            | CI: phase-verify.yml, ci.yml; live | -- | --             | --       | --   | --          |
| V2      | ADR-0012 + surface core          | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V3      | Registry export                  | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V4      | CLI                              | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V5      | Exports + bundles                | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V6      | REST API                         | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V7      | Hosted mode + clients            | CI: phase-verify.yml, ci.yml; live | -- | --             | --       | --   | --          |
| V8      | MCP server                       | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V9      | MCP Apps + registry entry        | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V10     | Parity                           | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V11     | AI narrative                     | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V12     | Container                        | CI: phase-verify.yml, ci.yml | --  | --                  | --       | --   | --          |
| V13     | Staging                          | CI: phase-verify.yml, deploy-staging.yml, staging-health.yml; live | -- | -- | -- | -- | -- |
| V14     | Readiness gate                   | CI: phase-verify.yml; live | --    | --                  | --       | --   | --          |
| V15     | 1.0.0b1 release                  | CI: phase-verify.yml; live, post | -- | --              | --       | --   | --          |
| V16     | CI integration                   | CI: phase-verify.yml; live, post | -- | --              | --       | --   | --          |

---

## Model selection blocks

Each block restates the column its step's **Runs:** line names (Balanced,
the user context's budget priority); the step's own table holds the Cost
and Quality columns and the backups the runner switches to when a pool
reads `tight` or `exhausted`.

```text
PROMPT: Step 1 — Surfaces Baseline and Concurrency Hardening
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — a version move, issue #157's
fix with a threaded regression test, and a bounded concurrency audit. PICK:
the ladder's Balanced column for coding at Medium, Gemini 4 Argon (AA
Intelligence Index 52.6 at High), Antigravity's first real use. EFFORT:
High, the ladder's value, with thinking on.

PROMPT: Step 2 — ADR-0012 Programmatic Surfaces and the Surface Core
MODEL: Opus 5.5
BACKUP: Gemini 4 Argon
PLATFORM: Claude Code
EFFORT: High
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: planning, coding secondary — twenty surface decisions
that become public API at 1.0.0, and the framework-free core that encodes
them. PICK: the ladder's Balanced column for planning at High, Opus 5.5
(AA Intelligence Index 53.6 at High). EFFORT: High; every decision has a
drafted default, so not XHigh, and Opus 5.5 always thinks.

PROMPT: Step 3 — Registry Export and Schema Snapshots
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — a deterministic registry
document, its schema and snapshot tests. PICK: the ladder's Balanced
column for coding at Medium (AA Intelligence Index 52.6). EFFORT: High,
the ladder's value, with thinking on.

PROMPT: Step 4 — The pyeconomics CLI
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — a registry-generated
command tree, bound runs, exit codes and a keyring path that never exposes
a key. PICK: the ladder's Balanced column for coding at High (AA
Intelligence Index 52.6). EFFORT: High, the ladder's value, with thinking
on; Quality's Opus 5.5 at XHigh is the column for a deeper key-path review.

PROMPT: Step 5 — Exports and Reproducibility Bundles
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — five export writers with
formula escaping and notices, and deterministic bundles. PICK: the
ladder's Balanced column for coding at Medium (AA Intelligence Index
52.6). EFFORT: High, the ladder's value, with thinking on.

PROMPT: Step 6 — REST API: App Factory, Routes and Worker Pool
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — generated routes with each
model's schemas, canonical bytes, problems, formats and a budgeted
process pool. PICK: the ladder's Balanced column for coding at High (AA
Intelligence Index 52.6). EFFORT: High, the ladder's value, with thinking
on.

PROMPT: Step 7 — Hosted Mode, API Fuzzing and Generated Clients
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — limits, edge trust, budgets,
caching, the disable switch, fuzzing and two client generators. PICK: the
ladder's Balanced column for coding at High (AA Intelligence Index 52.6).
EFFORT: High, the ladder's value, with thinking on.

PROMPT: Step 8 — MCP Server
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, planning secondary — a server on the stateless
2026-07-28 revision, generated tools and the llm_use gate, novel here.
PICK: the ladder's Balanced column for novel coding at High (AA
Intelligence Index 52.6). EFFORT: High, the ladder's value, with thinking
on.

PROMPT: Step 9 — MCP Apps, the MCP Registry Entry and Agent Evaluations
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — an MCP Apps page, a registry
manifest and OIDC workflow, and agent evaluations. PICK: the ladder's
Balanced column for coding at Medium (AA Intelligence Index 52.6).
EFFORT: High, the ladder's value, with thinking on.

PROMPT: Step 10 — Cross-Surface Parity
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, long-context secondary — every golden case
through four surfaces, bound runs, exports and the generator guard. PICK:
the ladder's Balanced column for coding at High (AA Intelligence Index
52.6). EFFORT: High, the ladder's value, with thinking on.

PROMPT: Step 11 — Optional AI Narrative
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — provider declarations over
the existing transport, cost, refusals and a recorded model choice. PICK:
the ladder's Balanced column for coding at Medium (AA Intelligence Index
52.6). EFFORT: High, the ladder's value, with thinking on.

PROMPT: Step 12 — Service Container
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — a Dockerfile, an entry point
and a CI job that builds, scans and runs the image. PICK: the ladder's
Balanced column for coding at Medium (AA Intelligence Index 52.6).
EFFORT: High, the ladder's value, with thinking on.

PROMPT: Step 13 — Staging on Cloud Run
MODEL: Sonnet 5.5
BACKUP: Gemini 4 Argon
PLATFORM: Claude Code
EFFORT: XHigh
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: agentic, coding secondary — provisioning across Google
Cloud, Cloudflare, Upstash and GitHub with OIDC, least privilege and an
edge trust boundary. PICK: the ladder's Balanced column for agentic work
at High, Sonnet 5.5 (AA Intelligence Index 51.9 at XHigh). EFFORT: XHigh,
the ladder's value; Sonnet 5.5 always thinks.

PROMPT: Step 14 — 1.0.0b1 Readiness Gate
MODEL: Sonnet 5.5
BACKUP: Gemini 4 Argon
PLATFORM: Claude Code
EFFORT: XHigh
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: agentic, planning secondary — a rehearsal proven from
clean installs, on staging and with agents, ending in a written judgement.
PICK: the ladder's Balanced column for agentic work at High (AA
Intelligence Index 51.9). EFFORT: XHigh, the ladder's value; Sonnet 5.5
always thinks.

PROMPT: Step 15 — 1.0.0b1 Release
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: agentic, coding secondary — a release checklist with two
protected deployments, the MCP Registry and production checks. PICK: the
ladder's Balanced column for agentic work at Medium (AA Intelligence Index
52.6). EFFORT: High, the ladder's value, with thinking on.

PROMPT: Step 16 — QA and Verification Script
MODEL: Gemini 4 Argon
BACKUP: Opus 5.5
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: mechanical translation of the prior verify-script
template into this phase's deliverables, plus the alarm proofs. PICK:
known pattern, no novel reasoning — the ladder's Balanced column for
coding at Medium (AA Intelligence Index 52.6). EFFORT: High, the ladder's
value, with thinking on.
```

---

## Not in scope (from product roadmap)

The parent ROADMAP's Phase 4 section has no list of its own; every item
below is deferred by its phase boundaries and its §6 "Out of Scope"
([`docs/roadmap/ROADMAP.md`](ROADMAP.md)):

- Production: the production API and its protected `production`
  environment, the scheduled snapshot job and its Parquet snapshots in R2
  (which replace staging's per-request originator fetch), the hosted web
  app, the data explorer, the `[app]` wheel behind `pyeconomics serve`, the
  production MCP endpoint and its remote MCP Registry entry, Sentry,
  OpenTelemetry and uptime monitoring, the legal and trust pages, the
  permissions programme, and resolvable problem-type URIs. Phase 5 owns
  them.
- Bring-your-own-key vendors, the Bloomberg provider, the OpenBB bridge and
  premium-only datasets. Phase 6 builds them, and they reach every surface
  without surface code.
- New models: the rest of ROADMAP §4 7.2. Phase 7 owns them; this phase
  adds no model id.
- API keys, quotas and plans, accounts, billing, remote MCP with OAuth,
  queued asynchronous jobs on Postgres, the AI narrative in hosted mode
  behind a cost ledger and a cap, and the Excel add-in. Phase 8 owns them,
  behind Gate G3.
- Real-time streaming quotes, tick and intraday data, licensed-data
  redistribution and personalised advice, which stay excluded in every
  phase (ROADMAP §6).

Additionally not in scope for this phase:

- An asynchronous data transport and httpx in the runtime. ADR-0012
  decision 10 keeps the data layer synchronous: runs and series fetches
  execute in worker processes, and Phase 5's snapshot reader removes
  hosted per-request fetches.
- Publishing the generated TypeScript and Python clients. Phase 5's web app
  generates the TypeScript client from the same `openapi.json`; a published
  client waits for Phase 8's API keys.
- A shared, Redis-backed result cache and a Cloudflare cache rule for the
  API. Staging uses an in-process cache; Phase 5 decides production
  caching.
- Batch runs over the REST API and MCP. The CLI's `--batch` and
  `pyeconomics.run_batch` cover scripted batches in this phase.
- An arm64 image and images for other operating systems. Cloud Run runs the
  amd64 image built on GitHub-hosted runners.
- The MCP tasks extension, sampling and elicitation. The tools are
  stateless and read-only, so none is needed.
- Fuzzing the provider parsers. It stays with issue #62's Scorecard
  dispositions and its owner.
- Issues #52, #62 and #68, the security and dependency maintenance of #109
  and #110, the randomized property failures (#112, #137, #139, #143, #149,
  #152), the platform work of #113, #114 and #116, the data-layer gaps of
  #131, #135, #136, #141 and #142, #148, #150, #151, the Wheel-rule marker of
  #154, the statsmodels and data findings #155, #156, #158 and #159, and
  #163 and #164. Each keeps the owner `docs/phase03-qa-findings.md` gives
  it; this phase absorbs only #157 (Step 1) and #162 (Step 7).

Carried over during execution — the Triage rule's carry-over checklist:
each upstream gap or deferred finding, the step whose `<task>` was patched,
and the step or phase that owns it. Phase 5's roadmap carries forward
whatever is still open here.

- From Phase 3's Not-in-scope list, its QA findings and its closing line,
  absorbed by this roadmap:
  - the generated surfaces over the data layer — the `pyeconomics data`,
    `keys` and `cache` commands (Step 4), the REST API's `series` routes
    (Steps 6–7), the MCP server's `get_series` and `list_sources` and its
    `llm_use` gate (Step 8), exports and bundles that print attributions
    (Step 5), and the optional AI narrative (Step 11);
  - Parquet as an export format, which ADR-0011 decision 14 left to this
    phase — Step 5, under ADR-0008 decision 8;
  - the revisit of an asynchronous transport, which Phase 3 left open —
    ADR-0012 decision 10 (not needed);
  - issue #157, assigned to Phase 4 by its own text — Step 1;
  - issue #162, the first operational need for a provider switch — Step 7.

---

_This roadmap is the execution plan for Phase 4. Each step's
`**Status:**` line is flipped by that step's own PR (Status rule), so this
file on `main` is the phase's ledger — `grep -n '^\*\*Status:\*\*'`
reports progress. After all steps and verification pass, and every finding
has a destination, Phase 4 is complete — declared with the line "Phase 4 is
complete. You can now move on to Phase 5." and nothing after it — and
Phase 5 (Web App, Docs & Public Launch (1.0.0)) inherits `pyeconomics
1.0.0b1` on PyPI: a `registry.json` its model pages render from; a
versioned REST API in local and hosted modes, with an OpenAPI 3.1 document
and the TypeScript client generated from it, that its calculators call; a
parity suite it runs through the deployed API; every export format and
reproducibility bundles its downloads offer; an MCP server over stdio and
stateless Streamable HTTP, listed in the MCP Registry, whose hosted
endpoint it deploys; a non-root hosted image and a Cloudflare-fronted
staging service on Cloud Run, deployed through OIDC with secrets in Secret
Manager, that its production deploy promotes; a health probe and a budget
alert with a proven alarm; and `verify-phase04.sh` as the template for
`verify-phase05.sh`._
