# ADR-0012: Programmatic surfaces

- Status: Accepted
- Date: 2026-10-23
- Deciders: Nathan Ramos, CFA (maintainer)
- Parent: ROADMAP §4 4.1–4.7; §5 "Model quality & governance" ("Parity"),
  "Security & privacy strategy" and "Cost projection"

## Context and problem

Phase 4 serves the model registry and the data layer through four new
surfaces: the `pyeconomics` command line, a versioned REST API in local and
hosted modes, an MCP server over stdio and stateless Streamable HTTP, and
the export formats with reproducibility bundles, plus an optional AI
narrative and a staging service on Cloud Run. Phase 5 then renders its web
pages from this phase's registry export, calls its API through a generated
client and deploys its container to production.

Four earlier decisions constrain the answer:

- **ADR-0003** makes CLI commands and options, REST paths and schemas, MCP
  tool names and schemas, and the canonical JSON result public API at
  1.0.0. A shape chosen now can only change in a major release after
  Phase 5.
- **ADR-0002** places `cli/` in the core distribution: its required
  dependencies must be pure Python, or have a Pyodide build, and pass the
  ADR-0004 allowlist. `server`, `mcp` and `ai` are extras, held empty since
  Phase 1 so their names are stable.
- **ADR-0008 decision 8** bars Polars and pyarrow as dependencies, even
  through an extra, so the Parquet and Arrow exports import pyarrow lazily.
  Decision 12 fixes the canonical JSON every surface must return unchanged.
- **ADR-0006** puts the API on Cloud Run behind Cloudflare, and allows no
  Worker code in the page path "unless a later ADR adds it".

Each surface, written on its own, would pick its own invocation path, its
own error codes, its own input parsing and its own serialization. The
parity promise (ROADMAP §5) would then fail on the first float a surface
re-serialized, and a key, a path or an upstream URL could leak through
whichever error message a surface forgot to scrub. Phase 4 also opens the
project's first network listeners, deploy pipeline and hosted ingress, so
its exposures are new: cost exhaustion through expensive inputs, server-side
request forgery through request bodies, licensed data reaching the hosted
service, and MCP output steering an assistant (ROADMAP §5 threats 1–7).

The facts the decisions rest on, read on 2026-10-23:

- **Cloudflare's Origin Rules host-header override**, which a plain CNAME
  to a `run.app` origin needs, is available only on the Enterprise plan
  [S1]. **Cloud Run domain mapping** is a Preview feature, "not
  production-ready and not supported at General Availability", in ten
  regions including `us-central1` [S2]. A **global external Application
  Load Balancer**, Google's recommended path, charges $0.025 an hour for
  up to five forwarding rules, about $18 a month [S3], outside this phase's
  $0 budget. **Cloudflare Workers' free plan** serves 100,000 requests a
  day [S4].
- **Upstash sells Upstash Redis** and no Valkey product: 500,000 commands a
  month free, then $0.20 per 100,000 [S5]. The parent roadmap's "Upstash
  Valkey" is therefore wrong. `limits[redis]` pins `redis<8` [S11].
- **MCP specification 2026-07-28 is stateless**: the `initialize`
  handshake and `Mcp-Session-Id` sessions are gone, a server must
  implement `server/discover`, and the version and capabilities travel on
  every request [S6]. Tool names should be 1–128 characters of `A–Z`,
  `a–z`, `0–9`, `_`, `-` and `.` [S7]. The Python SDK `mcp` 2.3.0
  (2026-10-02, MIT) renames FastMCP to `MCPServer` [S8].
- **The official MCP Registry** grants `io.github.<owner>/*` to a GitHub
  Actions OIDC login from that owner's repository, and an organization
  namespace through OAuth only to an organization Owner. It proves a PyPI
  package's ownership by an `mcp-name:` line in the package's README.
  `server.json`'s latest released schema is 2025-12-11. The registry is
  still in preview [S9].
- **RFC 9457** (obsoleting RFC 7807) defines `application/problem+json`
  and the `type`, `title`, `status`, `detail` and `instance` members, and
  allows extension members [S10]. **RFC 9110** requires a strong entity tag
  to change whenever the representation's bytes change; a weak one marks
  semantic equivalence [S14].
- **The dependency closures** of Phase 4's candidates (PyPI and npm, read
  on 2026-10-23; the `licences` hook and the wheel listing at each step's
  kickoff are the authority) [S11][S12]: cyclopts 5.3.0 (Apache-2.0) and its
  closure are pure Python and pass the allowlist; fastapi 0.162.0 (MIT) now
  requires `opentelemetry-api`; mcp 2.3.0 brings `httpx2` on truststore, not
  certifi, and on Windows pywin32, whose `PSF` metadata needs a reviewed
  exception; schemathesis 4.32.4 requires PyYAML, which publishes no
  CPython 3.15 wheel (6.0.3); httpx 0.28.1 has had no release since
  2024-12-06.
- **In the repository** (Phase 4 Step 1): every model declares a
  `CostClass` (33 `instant`, 12 `light`, 5 `heavy`); the error taxonomy is
  ADR-0008 decision 13's in `core/errors.py` and ADR-0011 decision 2's in
  `data/errors.py`, mapped to nothing; the largest valid input a registered
  model accepts today, `asset_pricing.factor_model_tests` at full length,
  is 2.65 MiB of canonical JSON with six significant digits per value and
  5.83 MiB with seventeen.

## Decision drivers

- **Parity.** Every surface returns the same bytes for the same inputs and
  data, so one test proves all four (ROADMAP §5 "Parity").
- **Generated, not written.** A surface gains a model only through the
  registry, so Phases 6 and 7 add providers and models with no surface
  code.
- **No leaked secret.** No key, path, host or upstream URL reaches a CLI
  message, a problem body, a log line, an export or a bundle (ADR-0011
  decision 13; ROADMAP §5 threat 1).
- **Licence first.** Hosted mode serves only `hosted-safe` and
  `user-supplied` data, and `llm_use` gates what reaches a language model
  (ADR-0005; ADR-0011 decisions 7 and 8).
- **Bounded cost.** Every hosted request has a size limit and a time
  budget before it runs (ROADMAP §5 threat 2).
- **A light core.** `import pyeconomics` imports no framework, and the core
  still runs in Pyodide (ADR-0002).
- **$0 at staging scale**, inside the free tiers (ROADMAP §5 "Cost
  projection").
- **Stable public names** chosen once, before 1.0.0 freezes them
  (ADR-0003).

## Considered options

The overall choice:

1. **One framework-free surface core with generated surfaces on top**: an
   invocation path, an error table, an input codec and an envelope in
   `pyeconomics.surfaces`, which the CLI, REST API, MCP server and exports
   share, each surface generated from the registry.
2. **One surface per framework, each self-contained.** Each surface parses,
   runs and serializes in its own idiom. Rejected: three ways to parse an
   input and three to report an error, and no structural reason for their
   bytes to agree.
3. **A REST API first, the other surfaces as its clients.** The CLI and MCP
   would call HTTP. Rejected: the CLI and stdio MCP must work offline with
   no server, and the core distribution (ADR-0002) cannot require a web
   framework.

The alternatives behind each numbered decision:

| # | Chosen | Alternatives and why they lost |
|---|--------|--------------------------------|
| 1 | Framework-free `surfaces` beneath framework packages | A surface package per framework with shared helpers copied: drift. Surfaces inside `core/`: puts I/O-adjacent code in the pure core |
| 2 | One `invoke` | Each surface calls `run` and `bind` itself: the bind, alias and decoding rules diverge |
| 3 | `Result.to_json()` bytes everywhere | Each surface serializes its own way (FastAPI's encoder, MCP's JSON): floats and key order differ |
| 4 | One table keyed by class | Codes chosen per surface: a CLI exit code and an HTTP status for one error disagree |
| 5 | Cyclopts in the core; exit codes 0–8 | Typer or Click: Click is BSD and fine, but Typer's options come from function signatures, not a schema read at run time. sysexits-style codes (64–78): fewer readers know them, and they do not separate "no defined result" from "invalid input" |
| 6 | CSV, XLSX, Parquet, Arrow, JSON | A pandas `to_csv` export: no formula escaping, no attribution block |
| 7 | Deterministic zip with `reproduce.py` | A notebook: not deterministic, and it executes on open in some tools |
| 8 | `registry.json` validated by a schema in a `.py` module | A `.json` schema file: the wheel admits only `.py` files (Phase 1's allowlist) |
| 9 | `GET` form with `?inputs=` base64url canonical JSON | One query parameter per field: ambiguous for arrays and matrices, and a second decoding path with its own cache key |
| 10 | Spawned worker processes with time budgets | Threads: a CPU-bound run cannot be stopped. Forked processes: unsafe with threads and the SQLite cache. An async transport: the data layer is synchronous by ADR-0011 decision 10 |
| 11 | `local` and `hosted` from one app factory | Two apps: the routes drift |
| 12 | `limits` on Upstash Redis, weak `ETag` | An in-process limiter only: two instances double the limit. A strong `ETag` of `result_sha256`: the bytes differ by data records and versions while the hash does not (RFC 9110) |
| 13 | `mcp` 2.x `MCPServer`; discovery tools plus 10–20 generated headline tools | One tool per model: hundreds of tools crowd a client's context. A third-party framework: more dependencies, and the official SDK tracks the specification |
| 14 | `llm_use` gate at resolution, plus withholding | Withholding only: a forbidden source is fetched and then discarded, and a fallback that is allowed is never tried |
| 15 | MCP Apps chart resource | An image: no hover or data, and a raster in the context window |
| 16 | `io.github.pyeconomics-dev/pyeconomics` | `dev.pyeconomics/pyeconomics`: DNS proof needs a signing key stored as a CI secret, where GitHub OIDC needs none |
| 17 | Providers declared like data providers, the existing transport | An SDK per AI vendor: a dependency each, outside the credential chain and the redaction |
| 18 | `@hey-api/openapi-ts` and `openapi-python-client` | Hand-written clients: they drift from `openapi.json` |
| 19 | Multi-stage image on Python 3.14 | Python 3.15: arch has no 3.15 wheel (issue #154). Distroless: no shell for the image smoke |
| 20 | Cloudflare Worker edge | Cloud Run domain mapping: Preview, unsupported at GA [S2]. Origin Rules host override: Enterprise only [S1]. A global load balancer: about $18 a month [S3] |

## Decision outcome

Chosen option: **1, one framework-free surface core with generated
surfaces**, because it makes parity structural (every surface returns the
bytes one function produces), puts every error through one scrubbed table,
keeps every framework out of `import pyeconomics`, and lets Phases 6 and 7
add sources and models with no surface code. The twenty decisions below are
rules a later step follows as written.

### 1. Layering

- `pyeconomics.surfaces` (this ADR's Step 2) and `pyeconomics.exports`
  (Step 5) sit on `core` and `data` and import no framework. `cli` (core
  runtime, Step 4), `server` (`[server]`, Step 6), `mcp` (`[mcp]`, Step 8)
  and `ai` (`[ai]`, Step 11) sit on them.
- No module under `core/` or `data/` imports `surfaces`, `exports`, `cli`,
  `server`, `mcp` or `ai`.
- `surfaces` imports none of fastapi, starlette, uvicorn, mcp, cyclopts or
  rich. `import pyeconomics` loads none of them, and `import
  pyeconomics.surfaces` loads no data module: the data layer arrives with
  the first bind.
- `cli` imports Cyclopts only when a command line is built, so the core
  still imports in Pyodide.

### 2. One invocation path

- `surfaces.invoke(model_id, inputs=None, /, *, bind=None, mode=None) ->
  Result` is the one way a surface runs a model. It resolves the id (an
  alias warns, ADR-0003), decodes the inputs through the codec (decision
  10), and, when `bind` is a `BindRequest`, imports the data layer and
  binds with the decoded inputs as overrides; then it runs through
  `core.runner`.
- `BindRequest` is frozen: `as_of` (a date or an ISO date), `vintage`,
  `profile` (`default`), `concepts` and `parameters`, as
  `pyeconomics.bind` takes them. `mode` applies to the bind; a run that
  reads no data reads no source.
- Step 8 adds decision 14's `llm_use` policy as a keyword of `invoke`.
- No surface module calls `core.runner`, `pyeconomics.run` or
  `pyeconomics.bind` directly.

### 3. Canonical bytes

- The bytes of a result are `Result.to_json().encode("utf-8")`
  (`surfaces.envelope.canonical_bytes`), the RFC 8785 text of ADR-0008
  decision 12.
- The REST API returns them without re-serializing; the CLI's
  `--format json` writes them followed by one `\n`; MCP carries them as the
  tool's text content and their parsed object as its structured content.
- The parity suite compares bytes, stripping only the CLI's newline.
- A presentation (a CLI table, an MCP summary) is added beside the bytes,
  never in their place. `envelope.summary` writes the one-paragraph text
  summary every surface shares.

### 4. The error table

- One row per error class in `surfaces.problems.ROWS`: a slug, a title, an
  HTTP status and a CLI exit code. A row is keyed by the class's module and
  name, and an error takes the row of the nearest class in its MRO that has
  one, so the table imports neither error module and a later subclass
  inherits its parent's row. A test walks every subclass of
  `PyeconomicsError` in `core/errors.py`, `data/errors.py` and `surfaces/`
  and fails on a class without its own row.
- The rows:

| Error | Slug | HTTP | Exit |
|-------|------|------|------|
| `InputError` | `invalid-input` | 422 | 3 |
| `InputTooLargeError` (surfaces) | `input-too-large` | 413 | 3 |
| `DomainError` | `no-defined-result` | 422 | 4 |
| `ConvergenceError` | `no-convergence` | 422 | 4 |
| `ModelNotFoundError` | `model-not-found` | 404 | 5 |
| `ProviderNotFoundError` | `provider-not-found` | 404 | 5 |
| `ConceptNotFoundError` | `concept-not-found` | 404 | 5 |
| `SeriesNotFoundError` | `series-not-found` | 404 | 5 |
| `LicenceError` | `licence-refused` | 403 | 6 |
| `CredentialError` | `credential-unavailable` | 503 | 7 |
| `TransportError` | `upstream-unavailable` | 502 | 7 |
| `ResponseError` | `upstream-invalid-response` | 502 | 7 |
| `RateLimitError` | `upstream-rate-limited` | 503 | 7 |
| `OfflineError` | `offline-cache-miss` | 503 | 7 |
| `DataError` (any other) | `data-unavailable` | 422 | 7 |
| `MissingOptionalDependencyError` | `missing-extra` | 501 | 8 |
| `BudgetExceededError` (surfaces) | `budget-exceeded` | 422 | 1 |
| `RegistryError` | `registry-error` | 500 | 1 |
| `ConfigError` | `invalid-configuration` | 500 | 1 |
| `PyeconomicsError` (any other) | `pyeconomics-error` | 500 | 1 |
| Any other exception | `internal-error` | 500 | 1 |

- `problem_for(error)` returns a `Problem`: `type`
  (`https://pyeconomics.dev/problems/<slug>`, which Phase 5 makes resolve;
  until then `docs/problems.md`, generated from the table, lists each slug
  under its own anchor), `title`, `status`, `detail` and the exit code,
  with three extension members: `errors` for an `InputError` (each field
  error's location, message and type, never its input value or pydantic's
  documentation link, at most 100), `licence` and `terms` for a
  `LicenceError` (the class and the source's terms page), and
  `retry_after` for a `RateLimitError` that knows it.
- **A problem never holds a key, a file path, a host or an upstream URL.**
  The detail of an exception that is not a `PyeconomicsError` is fixed
  text, never its message. The detail of a `TransportError`,
  `ResponseError` or `RateLimitError` is fixed text naming the provider,
  because their messages describe the upstream request. Any other detail
  is the message scrubbed: every registered secret and credential
  parameter replaced, every URL replaced except pyeconomics' own
  documentation, `host=` fragments removed, every file path replaced, and
  the result cut to 1,000 characters. An `InputError` from validation takes
  its detail from the field errors, without their values. The only URLs a
  problem holds are its `type` and a licence refusal's `terms`.
- A surface logs a problem with `problems.report`: one record holding the
  slug, the status, the scrubbed detail and the error's type name, never a
  traceback or a raw message.

### 5. The command line

- Cyclopts in the core distribution (ADR-0002 places `cli/` there); the
  console script `pyeconomics`.
- `models list`, `search`, `describe` and `run`, with run options generated
  from each model's input schema at run time, `--inputs FILE` or `-` for a
  JSON document, and `--as-of`, `--vintage` and `--profile` for a bound
  run; `data search`, `get`, `describe`, `vintages` and `sources`; `keys
  set`, `list` and `delete` (the value read from a hidden prompt or
  standard input, never an argument); `cache ls`, `info`, `clear` and
  `path`; `registry export`; `--format` `table` or `json` (Step 5 adds
  `csv`, `xlsx`, `parquet` and `arrow`); `--out`; shell completion.
- Exit codes: 0 success, 1 internal error, 2 usage, 3 invalid input, 4 no
  defined result, 5 not found, 6 not permitted (a licence refusal), 7 data
  unavailable (a credential, the transport, the upstream, offline mode, a
  rate limit or data that cannot answer), 8 missing extra. A failure
  prints its problem's `cli_message` on standard error.

### 6. Export formats

- **CSV**: RFC 4180, UTF-8, LF line ends, text cells quoted; a text cell
  that starts with `=`, `+`, `-`, `@`, a tab or a carriage return is
  prefixed with `'`; numbers are never escaped; a leading `#` metadata
  block holds the attributions, notices, terms URLs and hashes.
- **XLSX** through openpyxl (already a runtime dependency): `data` and
  `manifest` sheets, strings written as strings, never as formulas.
- **Parquet and Arrow** through pyarrow imported lazily (ADR-0008 decision
  8), with the manifest and the attributions in the schema metadata.
- **JSON** with the manifest embedded: the canonical bytes.
- Every format carries the data's attribution and each required notice
  (ADR-0005 rule 2), checked per provider and format.

### 7. Reproducibility bundle

- A deterministic zip (stored, sorted entries, fixed timestamps) holding
  `result.json`, `inputs.json`, `request.json` (the bind request),
  `manifest.json`, `ATTRIBUTION.txt`, `requirements.txt` pinning
  `pyeconomics==<version>` and its extras, `reproduce.py` and
  `README.txt`.
- `reproduce.py` reruns from the recorded inputs and checks
  `result_sha256`; `--refetch` binds again at the recorded as-of date and
  vintages and reports agreement field by field.

### 8. Registry export

- `registry.json`: a format version, the package version and one entry per
  model sorted by id, holding the `describe()` keys plus `example_result`
  (the first example's canonical result) and `example_figure` (a Plotly
  figure with no template, or `null` without `[plot]`).
- Validated by its JSON Schema (2020-12), kept in
  `surfaces/registry_schema.py` because the wheel admits only `.py` files;
  written deterministically, with no clock, host or path in it.

### 9. REST shape

- FastAPI under `/v1`: `GET /v1/models` (`?q=`, `?domain=`),
  `GET /v1/models/{id}`, `POST /v1/models/{id}/run`, `GET /v1/series/{target}`,
  `GET /v1/sources`, `GET /healthz` and `GET /version`; OpenAPI 3.1;
  RFC 9457 `application/problem+json`.
- A `GET` form of a run for small inputs: `?inputs=` holds the canonical
  JSON of the inputs in base64url without padding (RFC 4648 §5), at most
  8,192 characters, and returns bytes identical to the `POST` form.
- `?format=` takes `json`, `csv`, `xlsx`, `parquet`, `arrow` or `bundle`.

### 10. Execution and limits

- Runs execute in a pool of worker processes, spawned and never forked.
  The data layer stays synchronous: no async transport and no httpx.
- Hosted wall-clock budgets by `CostClass`: `instant` 2 s, `light` 10 s,
  `heavy` 30 s (`surfaces.budgets`). A run past its budget is terminated
  and answered with `budget-exceeded`.
- The codec decodes a mapping, JSON text or bytes, or `field=value` pairs
  typed by the model's input schema. It refuses, before parsing further,
  text above its size limit (16 MiB by default, above the largest valid
  input of any registered model) and nesting deeper than 32 levels; it
  refuses duplicate keys, NaN and infinity, and never evaluates text (no
  `eval`, no YAML, no pickle). Validation is the model's own.
- Hosted mode refuses a body above 1 MiB (`budgets.HOSTED_BODY_LIMIT`)
  with `input-too-large` (413) before decoding it, pointing to local mode.

### 11. Modes

- `local` (`pyeconomics serve`): every source the user can access, bound to
  127.0.0.1; a non-loopback bind is refused unless `--allow-remote` is
  passed.
- `hosted` (`PYECONOMICS_MODE=hosted`): hosted-safe and user-supplied data
  only, anonymous, with no endpoint that accepts a provider key or a URL.
- In Phase 4 the hosted series route fetches hosted-safe originators per
  request in staging; Phase 5 swaps in its snapshot reader.

### 12. Limits and caching

- Hosted rate limits: `limits` with Redis storage on Upstash Redis over TLS
  (memory storage locally and in tests), keyed by client address; 429 with
  `Retry-After`; Cloudflare's free rate rule as the outer layer.
- A `GET` run is cacheable: an in-process cache keyed by model id and
  version, package version, canonical inputs and the data records;
  `ETag: W/"<result_sha256>"` (`envelope.etag`), weak because the bytes can
  differ by data records and versions while the result does not;
  `Cache-Control: public`, longer for runs that read no data and shorter
  for bound runs.
- A `POST` run, which may carry values from a user's file, is processed in
  memory and never cached (`no-store`); neither is a problem.

### 13. MCP server

- `mcp` 2.x `MCPServer` on specification 2026-07-28 and the SDK's earlier
  supported revisions; stdio (`pyeconomics mcp`, and `uvx --from
  "pyeconomics[mcp]" pyeconomics mcp`) and a stateless Streamable HTTP app
  mounted at `/mcp`.
- The five discovery tools by the names ROADMAP §4 4.5 gives
  (`search_models`, `describe_model`, `run_model`, `get_series`,
  `list_sources`), plus 10–20 headline tools generated from a declared list
  of model ids, each named `<domain>_<name>` (a family's
  `<domain>_<family>_<name>`), matching `^[a-z0-9_]{1,64}$`. That is
  stricter than the specification's 1–128 characters [S7], so a name
  survives a client that maps tools onto a function-calling API with no
  dots or a 64-character limit. Names carry no `pyeconomics` prefix:
  clients already namespace a server's tools.
- `outputSchema` on every tool; tools sorted; a large result returns a
  summary and a link to the REST download instead of the data.

### 14. The `llm_use` gate

- MCP and the AI narrative pass an `llm_use` policy into binding and series
  resolution: a `forbidden` source is skipped (a new resolver skip reason)
  and an `unclear` one only with the user's opt-in.
- The opt-in is set out of band, in `pyeconomics.toml` or the environment,
  never through a tool argument.
- A result whose manifest still holds such a record is withheld (defence in
  depth).

### 15. MCP Apps

- A `ui://pyeconomics/chart` resource (`text/html;profile=mcp-app`) renders
  a result's Plotly figure; run tools point to it with
  `_meta.ui.resourceUri`; its CSP names only the pinned script origin it
  loads.
- A client without the extension gets the plain result.

### 16. MCP Registry

- Server name `io.github.pyeconomics-dev/pyeconomics`; `server.json`
  (schema 2025-12-11) committed; the README carries the `mcp-name:` marker
  that PyPI's description then holds.
- `.github/workflows/mcp-registry.yml` publishes through GitHub OIDC from a
  protected `mcp-registry` environment, with `mcp-publisher` pinned by
  version and checksum.
- The remote entry waits for Phase 5's production endpoint.

### 17. AI narrative

- `pyeconomics.ai`. AI providers are declared like data providers (hosts, a
  key slot, `<PROVIDER>_API_KEY` through the credential chain) and called
  through the existing HTTPS transport, so `[ai]` adds no client library.
- Off by default (the `ai_enabled` setting); the per-call cost from a dated
  price table; it refuses forbidden `llm_use` data and hosted mode.
- CLI `models run --narrate` and `pyeconomics.ai.narrate(result)`; never an
  MCP tool or a hosted route.

### 18. Generated clients

- The TypeScript client from `openapi.json` with `@hey-api/openapi-ts` in
  `tools/node/` (pinned with a lockfile, generated output git-ignored,
  type-checked) and the Python client with `openapi-python-client`.
- Both are smoke-tested against a local server in CI; neither is published
  in Phase 4.

### 19. Container

- A multi-stage `Dockerfile`: a base image pinned by digest on Python 3.14
  (every image dependency, arch included, has a wheel there); the wheel
  installed with the `[server,mcp,econometrics,plot,sdmx]` extras from the
  locked set; a non-root user; `PYECONOMICS_MODE=hosted`; the git SHA baked
  in for `/version`.
- No yfinance, keyring or Bloomberg code; scanned in CI with no Critical or
  High finding.

### 20. Staging and edge

- Region `us-central1`; minimum 0 and maximum 2 instances; deploys from
  `main` through Workload Identity Federation bound to this repository and
  `main`; secrets only from Secret Manager; a billing budget with 50, 90 and
  100% alerts.
- **The edge is a Cloudflare Worker** on the staging hostname, behind
  Cloudflare Access, that forwards to the Cloud Run origin with an origin
  credential the app verifies. This is the "later ADR" ADR-0006's clause
  asks for: the Worker sits in front of the API's staging hostname, not in
  the page path.
- A scheduled health probe through the edge opens an issue on failure.

### Consequences

Good:

- Parity is structural: one function produces the bytes, so a surface that
  differs has a bug the parity suite names.
- One table, one scrubber: an error reaches every surface with the same
  code and status, and no key, path, host or upstream URL in its body.
- Phases 6 and 7 reach every surface with no surface code, because the
  commands, routes and tools are generated.
- `import pyeconomics` and the Pyodide core stay framework-free; each
  framework arrives only with its extra.
- Hosted cost is bounded before a run starts: a body limit, a budget per
  cost class, rate limits at two layers.
- Staging costs $0: Cloud Run's free tier, a free Worker, free Upstash.

Bad:

- Every surface name in this ADR becomes public API at 1.0.0: a mistake
  lives until 2.0.0 behind a deprecation shim (ADR-0003).
- A worker-process pool costs a process start per worker and serialization
  of each run's inputs and result.
- The Worker is code to maintain outside Python, and the origin credential
  is a shared secret to rotate.
- Problem details are deliberately poorer than the raw messages: an
  upstream failure says only which provider failed.
- The MCP specification and SDK move fast; 2026-07-28 removed the
  handshake a year after sessions arrived, so Step 8 must expect another
  revision during the 1.x line.

### Confirmation

| Decision | Check | Built in |
|----------|-------|----------|
| 1 Layering | `tests/surfaces/test_surface_layering.py`: core and data import no surface; surfaces import no framework; a fresh `import pyeconomics` loads no framework | Phase 4 Step 2 |
| 2 One invocation path | `invoke` tests: data-free and bound toy runs equal `pyeconomics.run`'s bytes; the layering test's scan that no surface module calls the runner, `run` or `bind` | Phase 4 Steps 2 and 4; Step 10's generator guard |
| 3 Canonical bytes | The parity suite over every golden case on four surfaces | Phase 4 Step 10 |
| 4 Error table | The walking test; the canary test (a planted key, path and URL survive into no problem, CLI message or log record); `docs/problems.md` built in the `docs` job | Phase 4 Step 2 |
| 5 CLI | CLI tests per command and exit code; the `keys` prompt tests | Phase 4 Step 4 |
| 6 Exports | Formula-escaping and attribution tests per format and provider | Phase 4 Step 5 |
| 7 Bundles | A bundle reruns to identical bytes in a fresh environment | Phase 4 Step 5 |
| 8 Registry export | `registry.json` validates against its schema and is byte-stable; syrupy snapshots of every schema | Phase 4 Step 3 |
| 9 REST shape | The `openapi.json` snapshot; `GET` and `POST` forms return identical bytes | Phase 4 Step 6 |
| 10 Execution and limits | Codec tests (size, depth, duplicates, NaN, booleans); budget termination and 413 tests | Phase 4 Steps 2, 6 and 7 |
| 11 Modes | The non-loopback refusal; hosted 403 with a licence explanation | Phase 4 Steps 6 and 7 |
| 12 Limits and caching | The burst test; `ETag` and `Cache-Control` tests | Phase 4 Step 7 |
| 13 MCP server | MCP Inspector over stdio and HTTP; the `tools/list` snapshot | Phase 4 Steps 8 and 14 |
| 14 `llm_use` gate | A forbidden source never reaches a tool result; the resolver skip reason | Phase 4 Step 8 |
| 15 MCP Apps | The chart renders in an MCP Apps client | Phase 4 Step 9 |
| 16 MCP Registry | `server.json` validates; the OIDC publish at the release | Phase 4 Steps 9 and 15 |
| 17 AI narrative | Off by default; refusal tests for forbidden data and hosted mode | Phase 4 Step 11 |
| 18 Clients | Both clients generated and smoke-tested in CI | Phase 4 Step 7 |
| 19 Container | The image scan; the image smoke as a non-root user | Phase 4 Step 12 |
| 20 Staging and edge | `deploy-staging.yml`'s post-deploy check through the edge; `staging-health.yml` | Phase 4 Step 13 |

## More information

- Related: ADR-0002 (the core `cli/`, the extras), ADR-0003 (public API at
  1.0.0, aliases), ADR-0005 (licence classes, attribution), ADR-0006 (Cloud
  Run, Cloudflare, the Worker clause), ADR-0008 (decision 8's lazy pyarrow,
  decision 12's canonical JSON, decision 13's errors), ADR-0011 (redaction,
  `llm_use`, bindings, the synchronous transport); the Phase 4 roadmap's
  surface contract and its Surface, Licence, Credential and Dependency
  rules.
- The parent roadmap is amended in the same pull request: "Upstash Valkey"
  becomes Upstash Redis in §4 4.4 and §5 "Cost projection", §4 4.7 names the
  Worker edge, and §5 "Security controls by layer" no longer promises
  hosted API keys before Phase 8.
- The maintainer accepted the twenty decisions, with the values in this
  record, on 2026-10-23 in Phase 4 Step 2, answering one batched question:
  the Cloudflare Worker edge over Cloud Run domain mapping (decision 20);
  the drafted exit codes, `GET` form, tool names and server name (decisions
  5, 9, 13 and 16) as drafted; and the draft's four additions to the
  roadmap's table, each recommended in the question:
  - the error-table rows the roadmap left to "anything else": a plain
    `DataError` is `data-unavailable` (422, exit 7), because its raise
    sites mean the data cannot answer the request, while `ConfigError` and
    `RegistryError` keep 500 and exit 1 under their own slugs (decision 4);
  - two surface errors, `InputTooLargeError` (413, exit 3) and
    `BudgetExceededError` (422, exit 1) (decisions 4 and 10);
  - the codec's 16 MiB local limit beside the hosted 1 MiB, because 1 MiB
    refuses valid full-length inputs of 2.65 to 5.83 MiB (decision 10);
  - a weak `ETag` in place of the drafted strong one, which RFC 9110 does
    not allow when the bytes can change while `result_sha256` does not
    (decision 12).
- No decision was amended in place while the record read Proposed.
- Sources, all accessed 2026-10-23:
  - [S1] Cloudflare Origin Rules, availability by plan (the host-header,
    SNI and DNS-record overrides are Enterprise only),
    https://developers.cloudflare.com/rules/origin-rules/.
  - [S2] Cloud Run, "Mapping custom domains" (Preview; the ten regions),
    https://docs.cloud.google.com/run/docs/mapping-custom-domains.
  - [S3] Cloud Load Balancing pricing ($0.025 an hour for the first five
    forwarding rules, $0.01 for each further one),
    https://cloud.google.com/load-balancing/pricing.
  - [S4] Cloudflare Workers limits (the free plan's 100,000 requests a
    day), https://developers.cloudflare.com/workers/platform/limits/.
  - [S5] Upstash Redis pricing (500,000 commands a month free; $0.2 per
    100,000), https://upstash.com/pricing/redis.
  - [S6] Model Context Protocol, specification 2026-07-28, changelog,
    https://modelcontextprotocol.io/specification/2026-07-28/changelog.
  - [S7] Model Context Protocol 2026-07-28, "Tools", section "Tool Names",
    https://modelcontextprotocol.io/specification/2026-07-28/server/tools.
  - [S8] PyPI JSON for `mcp` (2.3.0, 2026-10-02, MIT),
    https://pypi.org/pypi/mcp/json; the SDK's migration guide (FastMCP
    renamed `MCPServer`), https://py.sdk.modelcontextprotocol.io/migration/.
  - [S9] MCP Registry: authentication,
    https://modelcontextprotocol.io/registry/authentication; publishing
    from GitHub Actions, https://modelcontextprotocol.io/registry/github-actions;
    package types (`mcp-name:`),
    https://modelcontextprotocol.io/registry/package-types; the
    organization-Owner rule in the registry's source,
    https://github.com/modelcontextprotocol/registry/blob/main/internal/api/handlers/v0/auth/github_at.go;
    the `server.json` schema versions,
    https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/CHANGELOG.md.
  - [S10] RFC 9457, Problem Details for HTTP APIs,
    https://www.rfc-editor.org/rfc/rfc9457.html.
  - [S11] PyPI JSON, https://pypi.org/pypi/<name>/json, for cyclopts
    5.3.0, fastapi 0.162.0, uvicorn 0.54.0, limits 5.8.0 (its `redis`
    extra requires `redis<8.0.0`), redis 8.1.0, schemathesis 4.32.4,
    PyYAML 6.0.3 (no `cp315` or `abi3` wheel), openapi-python-client 0.29.1
    (requires `httpx<0.29.0`) and httpx 0.28.1 (2024-12-06).
  - [S12] npm registry, https://registry.npmjs.org/<name>/latest, for
    `@hey-api/openapi-ts` 0.99.0 (MIT; Node 22.18 or later),
    `@modelcontextprotocol/inspector` 2.12.0 (its own licence file; Node
    22.19 or later), `@modelcontextprotocol/ext-apps` 2.0.3 (MIT) and
    `typescript` 7.0.2 (Apache-2.0).
  - [S13] Cloud Run minimum instances (0 is the default),
    https://docs.cloud.google.com/run/docs/configuring/min-instances;
    `google-github-actions/auth` (Workload Identity Federation, recommended
    over service-account keys), https://github.com/google-github-actions/auth.
  - [S14] RFC 9110, HTTP Semantics, §8.8.1 "Weak versus Strong" and §8.8.3
    "ETag", https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.
