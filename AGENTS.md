# AGENTS.md

The rules every coding-agent session in this repository follows: Claude Code,
Codex, Cursor, Antigravity or any other. `CLAUDE.md` imports this file. Humans
follow the same rules through [CONTRIBUTING.md](CONTRIBUTING.md).

The project roadmap is [docs/roadmap/ROADMAP.md](docs/roadmap/ROADMAP.md); each
phase has its own roadmap beside it (`docs/roadmap/phaseNN-roadmap.md`). When a
rule here and the roadmap disagree, the roadmap wins; fix this file in the same
pull request.

## Never print secrets

- Never print, echo, log or paste environment variables, tokens, API keys or
  passwords in a session: no `env`, `printenv`, `set`, `Get-ChildItem Env:`,
  `echo $SOME_TOKEN`, `gh auth token` or `cat .env`. Check that a variable
  exists by name only (for example `test -n "${VAR+x}"`), never by value.
- Never write a real credential into a file, test, fixture, commit message,
  issue or pull request. The gate blocks even fake credentials in docs; refer
  to a test key by its location instead.
- Session transcripts can leak. Treat everything you print as public.

## Repository layout

```
src/pyeconomics/   the package (src layout); py.typed
tests/             unit · golden · property · contract · parity · e2e
  checks/          tests for scripts/checks
  providers/       the provider contract suite, the toy providers and the
                   cassettes under cassettes/<provider>/
  fixtures/legacy/ 0.2.x characterization fixtures, byte-exact: never edit
  parity/          the cross-surface parity suite and its stand-in world
  ai/              the AI narrative's tests and synthetic cassettes
  web/             tests for scripts/web (the site data export), and e2e_api.py,
                   the API the web app's Playwright tests run against
scripts/checks/    the gate's own checks (licences, lock index, dist contents …)
scripts/clients/   the clients job's helpers (retitle, smoke, compare)
scripts/mcp/       the mcp-inspector job's helper (the Inspector's checks)
scripts/parity/    the parity job's helper (the installed wheel's surfaces) and
                   check_deployed.py (a deployed API against the wheel)
scripts/docs/      export_wasm.py, which the documentation build runs, and
                   pin_wasm.py, which writes the in-browser lockfile by hand
scripts/web/       the site data export the web app builds from, the
                   calculators' validator compiler, their MCP snippet runner,
                   syllabi.py, the one loader of syllabi/, and
                   package_site.py, which copies a build into the app wheel
scripts/record_cassettes.py  records a provider's cassettes live: a local act
tools/node/        the one Node workspace: the TypeScript client's generator and
                   the MCP Inspector
scripts/legacy/    the 0.2.x fixture recorder, byte-exact: never edit
.semgrep/          project semgrep rules and their tests
docs/adr/          architecture decision records
docs/roadmap/      the project and phase roadmaps: the ledger of what is done
docs/tutorials/    the ordered tutorial track; docs/how-to/ the recipes; both,
                   and docs/migration.md, run as sessions under Sybil;
                   docs/tutorials/finance/ the Python-for-finance notebooks
docs/examples/     the gallery's scripts, which the documentation build runs
docs/wasm/         the in-browser marimo notebooks and their pinned lockfile
web/               the Astro site (Phase 5, ADR-0013 decision 2): its own Node
                   project and lockfile beside tools/node/, its build data only
                   from scripts/web/export_site_data.py; csp.config.ts holds
                   the one policy, scripts/ the build's checks, tests/unit
                   Vitest and tests/e2e Playwright
syllabi/           syllabus crosswalks: a JSON Schema and one TOML file per
                   syllabus version; Phase 5 seeds the 2027 CFA Program
                   (decision 12), Phase 7 adds the rest
packages/pyeconomics-app/  the uv workspace member whose wheel carries only
                   the built site, behind the [app] extra (decision 16)
planning/          roadmodel's planning kit, re-exported by its updater: never edit
```

The target layout, as phases add it, is in ROADMAP §3: `core/`, `models/`,
`data/`, `cli/`, `server/` and `mcp/` under `src/pyeconomics/`, with
`surfaces/` (Phase 4 Step 2, ADR-0012) beneath the last three, and `ai/`
(Phase 4 Step 11), the optional narrative, beside them.

## Registry rules

From Phase 2, which builds the registry (ROADMAP §3; ADR-0001):

- A model is a pure function with typed inputs and outputs plus metadata. It
  never does I/O: no data fetching, printing, plotting, file access or LLM
  calls. Live data reaches it through a declared binding the data layer
  resolves.
- One registry feeds every surface. Never hand-write a CLI command, endpoint,
  MCP tool or page for a model; generate it from the registry.
- A model meets the definition of done in ROADMAP §5 "Model quality &
  governance" (CONTRIBUTING lists it): a model card, citations, at least three
  cited golden cases, property tests, units and bounds.
- Model ids are permanent (ADR-0003). Never copy CFA Program curriculum text,
  questions or worked examples.
- Declare a model with `@model` from `pyeconomics.core`, list the `Model` object
  in its module's `__all__`, and name the module in
  `[project.entry-points."pyeconomics.models"]`. `registry.validate()` must pass
  (`uv run python -c "from pyeconomics import registry; registry.validate()"`);
  it reports every problem as `<model>: [<rule>] <detail>`.
- Bound every array field's length on the field, with `Field(max_length=...)`.
  Its elements come from the `RateArray` family or `ARRAY_INPUT`; stacked
  constraints on one type do not narrow, so those aliases fix no length.
- Under `src/pyeconomics/models/`, imports are held to an allowlist
  (`tests/registry/test_model_imports.py`) and the `model-purity` semgrep rule
  bans I/O, the clock, the environment, the network and global randomness.
  Import an extra's library only inside `compute`.
- A model that wraps a library (statsmodels, arch) reports the library's
  warnings with `core.library_warnings`, because those libraries reset their
  own warning filters, and reads the library's lazily computed statistics
  (standard errors, covariances) inside that block.
- An extra may gate a library with an environment marker only under the Wheel
  rule (no wheel for a CI cell yet, the maintainer's approval, a tracking
  issue). The registry then lists it in `Provider.excluded`; the model raises
  `MissingOptionalDependencyError(..., note=...)` naming the gap; and its tests
  assert that gap on those cells, never a skip (`needs_arch` in
  `tests/models/econometrics/test_garch.py`; `tests/extra_gaps.py` does it for
  the golden harness and the contract suite).
- `pyeconomics.core` exports the decorator as `model`, which hides the module
  of that name. Import by path (`from pyeconomics.core.model import Model`);
  `import pyeconomics.core.model as m` binds the decorator. Likewise
  `pyeconomics.core.provenance` is `core.random`'s function: import the data
  provenance record by path (`from pyeconomics.core.provenance import
  DataSource`) or from `pyeconomics.core`.

## Data layer rules

From Phase 3, which builds the data layer (ADR-0011):

- No module under `src/pyeconomics/core/` imports `pyeconomics.data`, and no
  model does; the vocabulary they need (`DataSource`, `RealtimePeriod`,
  `LicenceClass`, `LlmUse`, later `Binding` and `Bound`) lives in core
  (`tests/data/test_layering.py`).
- Only the data layer's transport, cache, configuration and credential
  modules touch the network, files, the environment or the clock. A new pure
  module joins `PURE_MODULES` in `tests/data/test_layering.py`.
- A frame indexes a period by its last day, marks a missing value `None`
  (never NaN) and holds rates as decimals, converted only in a provider's
  transform step with `percent_to_decimal`.
- A source whose terms forbid storage, FRED and ALFRED among them, is never
  written to disk: no cache path, no opt-in.
- No value type has a field for a URL, host, path or credential; the one URL
  is a source's terms page (`tests/data/test_value_security.py`).
- A key is read only through `pyeconomics.data.credentials` (`resolve_key`)
  and held as a `Secret`. Only `data/credentials/` and `data/transport/` call
  `.reveal()` (the `secret-reveal` semgrep rule). A failure that may hold a
  key or a URL is re-raised with `redaction.call_scrubbed`, never with
  `raise ... from`.
- Every test runs with its own configuration and cache directories, no
  `*_API_KEY` or `PYECONOMICS_*` variable and an in-memory keyring (the
  `isolated` fixture, `tests/config_isolation.py`). Plant keys with
  `tests/data/leakcheck.py`'s `canary()`, never a literal, and check sinks
  with `LeakCheck`: never assert on a key's value in a way pytest could print.
- A source is a `DataProvider` subclass with a `ProviderInfo`, named in the
  `pyeconomics.providers` entry-point group and found through
  `pyeconomics.data.registry` (imported by that path, so it never shadows
  `pyeconomics.registry`). Override only the `build_*` and `parse_*` hooks of
  the declared capabilities; the public `fetch`, `search`, `describe` and
  `vintages` are final (they hold the hosted-mode, platform and status checks).
  A source's explicit opt-in belongs in `check_configuration`, which runs
  before a cache read as well as before any request; a cache hit must never
  bypass disabled-source or missing-extra checks.
  `uv run python -c "from pyeconomics.data import registry; registry.validate()"`
  must pass; it reports `<id>: [<rule>] <detail>`. "Writing a provider"
  (`docs/data/writing-a-provider.md`) is the contract.
- Only `data/transport/` opens a socket, builds a request URL or reveals a key
  (`tests/data/test_layering.py`). A provider builds `Request` values from its
  declared hosts with `request_path`; a `Request` refuses a credential
  parameter, body field or header, because the transport attaches the key from
  the provider's `Authentication`. Parse bodies with `Response.json()`; never
  pickle, `eval` or `yaml.load` a response, and parse XML only with defusedxml.
- Storage follows the terms (`pyeconomics.data.cache`). `cache.policy.may_store`
  is the one gate: a provider's or a series' terms with `CachePolicy.FORBIDDEN`,
  and `user-supplied` data, reach no store code at all (no read, no write, no
  file, no opt-in); `cache.memo()` is the only in-process reuse for them. The
  cache is one SQLite file created on the first write, owner-only, never at
  import or inside the repository; payloads are canonical JSON validated back
  into frames (never a pickle); every SQL statement is parameterized; a bad
  entry is deleted and reported, a newer schema left untouched. A new
  data-layer module that reads the clock or files joins `IO_MODULES`, a pure one
  `PURE_MODULES` (`tests/data/test_layering.py`). A provider writes no cache
  code: it declares `ProviderInfo.ttl_seconds` and a series' own terms.
  Offline mode (`configure(offline=True)`) serves the cache only; a recorder
  of cassettes runs inside `cache.bypass()`.
- Hosted mode (`PYECONOMICS_MODE=hosted`) refuses a source not classed
  `hosted-safe` or `user-supplied` before any request. A provider declares the
  source's published rate limits; the transport holds it to them.
- Offline tests replay cassettes under `tests/providers/cassettes/<provider>/`,
  recorded only by `uv run --no-config python scripts/record_cassettes.py`,
  never inside a test. A source that is not hosted-safe, or forbids storage,
  records synthetic values through its `synthesize()` hook, and its cassette
  says `"synthetic": true`. Each provider adds its row to
  `tests/providers/test_notices.py` and its cases to `DataProvider.cases`.
  Never provoke a rate limit or an outage to record one: a 429 or 5xx case is
  `Case(simulate=429)`, and a contact source's 403 is `Case(simulate=403)`. A provider module's `__all__` lists its provider
  classes only (the registry refuses anything else), and it joins
  `PURE_MODULES`.
- `providers-live.yml`'s report job runs on a failed or a timed-out job (a
  timeout ends `cancelled`, which `failure()` misses). A live check skips on a
  `RateLimitError` only for a source in `SHARED_QUOTA`
  (`tests/providers/test_provider_contract.py`), whose quota everyone fetching
  the file shares; a source joins it only with that evidence, because every
  other rate limit is an alarm.
- The `disabled_providers` setting (issue #162; `PYECONOMICS_DISABLED_PROVIDERS`)
  is enforced by `DataProvider._gate`, first, before `check_configuration` and
  any cache read, so no provider can override it; the resolver skips a
  disabled candidate as `disabled` before any request, and every candidate
  disabled is `SourceDisabledError` (503). Never re-implement it in a provider.
- `PYECONOMICS_EDGE_CREDENTIAL` and `PYECONOMICS_SNAPSHOT_HEARTBEAT` are the
  `PYECONOMICS_*` secrets the settings skip, because they are the hosted
  service's own (`config._SERVER_SECRETS`); provider keys never take the prefix.

## Snapshot rules

From Phase 5 Step 8, which builds the hosted data plane (ADR-0013 decision 6):

- Hosted mode with `PYECONOMICS_SNAPSHOT_DIR` reads every series from the
  snapshot (`data/snapshots/reader.py`), answered in
  `DataProvider.fetch_with_origin` after the licence gate and before the cache
  or any transport; the other operations are refused there, and the service
  never falls back to a live fetch. Without the directory, or inside
  `cache.bypass()`, hosted mode fetches per request as in Phase 4. The resolver
  does not skip a keyed candidate for a missing key while the snapshot answers.
- The set (`data/snapshots/set.py`, pure) is computed: every hosted-safe
  originator candidate of every catalog concept and bound-model profile whose
  terms allow storage. Never edit it by hand: change the catalog, or the
  declared `SEP_MEETINGS` and `HISTORY_STARTS` (a source that serves a series
  only by window). `tests/data/snapshots/test_snapshot_set.py` pins its size.
- The writer (`python -m pyeconomics.data.snapshots write`) runs only in hosted
  mode, inside `cache.bypass()`, checks the provider's and each series' own
  terms before it keeps anything, never overwrites an object, and writes
  `current.json` last. A failure keeps the last good data, marked with the
  failure's problem slug (`writer.FAILURE_SLUGS`, held equal to the error
  table, since `data/` imports no surface).
- Objects are gzip canonical JSON of the cache's frame codec, read back through
  `snapshots.codec` only: a size and an expansion cap, the SHA-256 in
  `current.json`, and names only of the form `<run-id>/<provider>.json.gz`.
- The heartbeat URL is a secret: read only by `config.snapshot_heartbeat()`,
  registered with redaction, sent through the transport to `writer.HEARTBEAT`'s
  one host. A series outside the snapshot is `SnapshotMissingError`
  (`not-in-snapshot`, 404, exit 7) with `errors.local_data_command`, the same
  text as `budgets.local_data_command`.
- Test with `tests/data/snapshots/snapshot_support.py` (scripted providers, a
  fixed clock, `reader.override`); `isolated_configuration` resets the reader.

## Catalog rules

From Phase 3 Step 11, which builds the semantic catalog and resolver (ADR-0011
decision 15):

- A concept is one `Concept` in a topic module under `src/pyeconomics/data/
  catalog/` (its shapes are in `definitions.py`). Its id is dotted snake_case
  of three or four parts and is permanent once released: the `released-concept`
  rule of `registry.validate()` fails on a released id the catalog lacks.
- A concept is exact. Every candidate must deliver the concept's unit kind,
  frequency and seasonal adjustment (with the declared transforms), and the
  resolver fails over only between candidates that do. List the originator
  first, then a library-only aggregator, then premium sources (Phase 6). A
  hosted-mode request resolves an originator or refuses with a `LicenceError`; it
  never falls back to an aggregator.
- Verify a new concept three ways: `uv run python -c "from pyeconomics.data
  import registry; registry.validate()"`, the offline suites under
  `tests/data/catalog/`, and its live resolution (`uv run pytest -m live
  --force-enable-socket tests/data/catalog/test_live_concepts.py`).
- A transform has its name and schema in `core/transforms.py` and its
  implementation in `data/catalog/transforms.py`; a test holds the two equal.
  A transform never fills a gap, invents a date or carries a value forward.
- A caller's transform (`data.get(..., transform=)`, Phase 5 Step 9) is one of
  `core.transforms.SERIES_TRANSFORMS`, read by `parse_series_transform`: the
  fetch starts at `resolver.widened_start`, the result is cut to the window and
  every source record lists the canonical text last. A table, or a transform
  that combines series or picks a binding's date, is `InputError`.
- A candidate a vintage-keeping provider serves without that series' vintages
  (FRED's daily rates, which ALFRED does not hold) is `vintages=False`: a
  vintage request skips it and a binding reads it as revised data. Probe a new
  FRED candidate as of a past date before you add it. A candidate's `column`
  takes `{parameter}` placeholders as its series key does.
- The resolver reads no clock and does no I/O; providers fetch. Concept pages
  and the sources summary are generated from metadata at documentation build
  time, offline, and read no key.

## Bindings rules

From Phase 3 Step 12, which binds models to data (ADR-0011 decision 16):

- A model reads data only through `bindings=(Binding(field, concept, ...),)` on
  `@model`: plain data from `pyeconomics.core`, never a fetch in `compute`. A
  model with bindings declares a `default` profile, binds a numeric field once
  per profile, gives an array field `AsOf.WINDOW` with a `window` within its
  `max_length` (or, for a curve's row of tenors, `tenors=` naming the array of
  years that pairs with it; a matrix field, a tuple of rows, reads a table
  concept's window of rows, with `columns=` to keep some columns in order), and
  names a catalog concept (permanent ids, decision 15).
  `registry.validate()` reports the structural problems under the `bindings`
  rule; `uv run python -c "from pyeconomics import data;
  data.validate_bindings()"` checks the concepts against the catalog.
- Resolution lives in `pyeconomics.data.bindings` (a pure module on
  `PURE_MODULES`); `pyeconomics.core.binding` imports nothing from the data
  layer. `pyeconomics.bind` is exported lazily, so `import pyeconomics` still
  loads no data module: keep any new package-root function that needs the data
  layer behind the same lazy import (`tests/data/test_layering.py`).
- Real time is the default. A bind with an `as_of` date reads the vintage
  published by then; where no source usable in the mode keeps vintages, or the
  policy is `LATEST`, it reads the latest data and records `revised_data` in the
  field's `DataSource` and in the result's warnings. Never pass revised data off
  as real-time, and never turn a missing key or an empty offline cache into
  revised data: those raise. A frame note that describes the whole series becomes
  a record's warning code only if `cache.policy.NOTE_WARNINGS` lists it.
- Manifest schema 2: `data_sources` holds one record per bound field, sorted by
  field. A record holds no URL but the terms page, no host, path or key, and a
  retrieval time that is a fact about the data; the manifest holds no clock of the
  run. `result_sha256` and `inputs_sha256` never cover the manifest. An override is
  recorded as user-supplied by field, never by value.
- Test a bind with `bind_model(model, registry=..., transport=...)` over scripted
  providers (`tests/data/bindings/bound_support.py`), offline, and prove a key
  reaches no sink with `LeakCheck.bound` and `LeakCheck.result`.
- A model with several calculations is bound with `calculation=...` and reads
  only that calculation's fields, so one profile serves the family. A value from
  periods back is bound with the `lag(periods=n)` transform; an `AsOf.PERIOD`
  binding reads up to the end of the period containing the date, no further.
- Window bindings of one frequency end on one date (the earliest last
  observation), so a model may pair array fields by position; a window read
  through `convert` is sized in the target frequency. A growth rate bound with
  `pct_change` is a `Return`; shared least squares is `core.least_squares`.

## Surface rules

From Phase 4 Step 2, which builds the surface core (ADR-0012):

- A surface (the CLI, the REST API, the MCP server, the exports) runs a model
  only through `pyeconomics.surfaces.invoke`, never `core.runner`,
  `pyeconomics.run` or `pyeconomics.bind`, and returns
  `envelope.canonical_bytes(result)` unchanged; a table or a summary goes beside
  those bytes, never in their place.
- No module under `core/` or `data/` imports a surface package, `surfaces/`
  imports no framework, and `import pyeconomics.surfaces` loads no data module
  (`tests/surfaces/test_surface_layering.py`).
- An error reaches a user only as `problems.problem_for(error)`, or through
  `problems.report`, which also logs one scrubbed record: the exit code, the
  HTTP status and the detail come from the table, never a raw message or a
  traceback. A new `PyeconomicsError` subclass in core, the data layer or the
  surfaces gets its own row in `problems.ROWS`, or the walking test fails; a new
  sink joins `tests/surfaces/test_problem_canary.py`.
- Decode a caller's inputs with `surfaces.codec`; hosted mode passes
  `budgets.HOSTED_BODY_LIMIT`. Validation stays the model's own.
- `pyeconomics.surfaces` exports the function `invoke`, which hides the module
  of that name: `import pyeconomics.surfaces.invoke as m` binds the function, so
  import from the module with `from pyeconomics.surfaces.invoke import ...`.
- The command line (`pyeconomics.cli`, Phase 4 Step 4) loads Cyclopts and rich
  only when it is built, and `--version` and `--help` discover no model
  (`tests/surfaces/test_surface_layering.py`). A command takes `context:
  ContextParameter`, writes UTF-8 bytes through `cli.output.Streams` (never
  `print`), imports the data layer inside its body, and raises: the exit code
  comes from the error table, and `cli.context.UsageError` (exit 2) is only for
  a command line written wrongly. A generated command sets both its
  `__signature__` and its `__annotations__`, because Cyclopts reads the latter.
- A key reaches the command line only in `keys set`, from a hidden prompt or
  `--stdin`, wrapped in a `Secret` at once and stored with
  `data.credentials.store_key`; never as an argument or an option.
- The exports (`pyeconomics.exports`, Phase 4 Step 5) read every value through
  `exports.layout.subject`, so each format carries the data's attributions,
  notices and manifest; a new format or exportable type adds its case there and
  to `tests/providers/test_export_notices.py`. A CSV or XLSX text cell goes
  through `escape_text`; a number never does. XLSX numbers are written as their
  shortest round-trip text (openpyxl's own `%.16g` drops a bit), and an XLSX
  file records the second it was written, so a test compares two by their
  sheets' values (`export_support.xlsx_sheet`), never their bytes. `check_bundle`
  reads the JSON members only and executes nothing; `reproduce.py`'s text is
  the `exports.reproduction.REPRODUCE_SCRIPT` constant (the wheel admits only
  `.py` files), standard library until it imports pyeconomics.
  `docs/cli.md`'s `console` examples run in the tests and exit 0, its `shell`
  examples read live data and must exit 7 offline, and `text` examples do not
  run (`tests/cli/test_cli_docs.py`).
- The REST API (`pyeconomics.server`, Phase 4 Step 6) builds every route from
  the registry in `create_app`. A run reads the raw body (or decodes
  `?inputs=`), runs `invoke` through the worker pool (`server.pool`) and answers
  its bytes unchanged; every error reaches the caller through the exception
  handlers or the guard middleware as `problem_response(problem)`. A serving
  error (a route, a method, a host, a full queue) is a class in
  `surfaces/service.py` with its own row. Messages to a worker are canonical
  JSON headers and raw bytes (`server.work`), never a pickle, and the modules a
  worker loads (`pool`, `work`, `formats`, `settings`, `logs`) import no web
  framework (`tests/server/test_server_layering.py`). The server logs route
  templates and problem records only (`server.logs`), never a path or a query.
- A server test uses `server_support.client()` (an inline pool, addressed to
  127.0.0.1, which a local server requires) and carries `pytestmark =
  LOOPBACK_ONLY`: asyncio's event loop needs a socket pair, which
  `--disable-socket` refuses, so loopback hosts are allowed and every other
  connection is still refused; a doctest cannot carry the mark, so no doctest
  starts an event loop. A toy a spawned worker runs lives in `server_support.py`
  (importable by name) and is installed through `ServerSettings.worker_setup`.
  The OpenAPI snapshot records each model's own schemas by digest; after an
  intended change, `uv run pytest tests/server --snapshot-update` and review.
- Hosted mode (Phase 4 Step 7): `_Guard` runs the edge check
  (`server.edge`) and the rate limits (`server.limits`) before any route.
  The edge credential and the Redis URL come only from the environment, are
  registered with redaction and never logged; the credential is held as its
  digest and compared in constant time, and only a matched request's
  `CF-Connecting-IP` is read (local mode never reads the credential). Limits
  key by `edge.client_key`, keep counts in Redis only from
  `PYECONOMICS_RATELIMIT_URL` (`rediss://` for a remote host), and fail closed
  for runs and series. A hosted-mode test that is not about limits passes
  `rate_limits=RateLimits.off()`, or the default limits answer its loop 429.
- A GET run answers through `server.run_cache` (`ETag: W/"<result_sha256>"`,
  `Cache-Control` from the worker's data records: a bound run is cacheable only
  when every record is hosted-safe under terms that allow storage); a POST run
  and every problem are `no-store` and never cached. A problem's text that
  points to local mode gives the command (`budgets.local_command`).
- The API fuzz (`tests/server/test_api_fuzz.py`, marker `fuzz`, the `fuzz`
  group) runs only in ci.yml's `api-fuzz` job, with keys present and every data
  request answered 404 by `server_support.install_fuzz_world`, so any 5xx it
  finds is a bug. The generated clients run only in the `clients` job; Node
  tooling lives in `tools/node` (`npm ci --ignore-scripts`, lockfile committed,
  `npm audit --audit-level=high` in the gate, a patched transitive version
  pinned through `overrides`).

## MCP rules

From Phase 4 Step 8, which builds the MCP server (ADR-0012 decisions 13 and 14):

- `pyeconomics.mcp` is built on the SDK's low-level `Server`, because every
  schema is generated (MCPServer derives schemas from Python signatures). Tools
  come from `mcp.tools.build_tools`, sorted by name; a model's own tool is named
  from its id (`^[a-z0-9_]{1,64}$`) and only `mcp/headline.py` names a model id
  (`tests/mcp/test_mcp_layering.py`). A tool's input schema is its model's own;
  every output schema is a self-contained 2020-12 document with an object root.
- A run answers `Result.to_json()` as text, its parsed object as structured
  content and `envelope.summary_of` as a second block; a failure answers its
  problem's JSON (`problems.report`); an unknown tool is a protocol error. No
  title, description or template addresses the assistant
  (`test_no_description_or_title_addresses_the_assistant` scans them).
- The `llm_use` gate: a tool that reads data passes the server's
  `LlmUsePolicy` (`llm_use=` on `invoke`, `bind`, `data.get`, `resolve`) and its
  answer goes through `surfaces.gate.check_document` before it is sent. The
  opt-in to unclear data is the `allow_unclear_llm_use` setting only, read when
  the server is built: never a tool argument, never `configure()`. Without a
  policy the data layer never reads `llm_use`, and `Skip.to_dict` keeps a skip's
  JSON as it was.
- `/mcp` in the REST server runs every run and series through
  `service.outcome(Task(..., llm_use=...))` (the pool and its budgets), never
  through the GET run cache; `route_kind` trusts `Mcp-Method` and `Mcp-Name`
  only on a 2026-07-28 request (the SDK checks them against the body there) and
  counts any other MCP request as a run. The endpoint takes POST only: a GET
  would hold an SSE stream open.
- Test through the SDK's `Client` in memory (`tests/mcp/mcp_support.py`, with
  `LOOPBACK_ONLY`); a protocol error needs `raise_exceptions=False` and a
  `try` inside the client's own work, or the task group wraps it. `stub_world`
  gives every real provider's metadata over canned frames from 2018. After an
  intended tool change, `uv run pytest tests/mcp --snapshot-update` and review.
  The Inspector checks run only in ci.yml's `mcp-inspector` job
  (`scripts/mcp/inspector_checks.py`).
- MCP Apps (Phase 4 Step 9, ADR-0012 decision 15): `mcp/apps.py` holds the
  chart page `ui://pyeconomics/chart` as a string constant. It loads one script,
  Plotly.js pinned by version and Subresource Integrity from the one origin its
  CSP metadata names, with no inline handler, no evaluation and no connection
  (`tests/mcp/test_mcp_apps.py`). `PLOTLY_JS_VERSION` and `PLOTLY_JS_INTEGRITY`
  follow the Plotly.js the `plot` extra's Plotly bundles: when a Plotly bump
  fails that test, check the CDN file is byte for byte the bundled one and move
  both. Every run tool carries `_meta.ui.resourceUri`; a run's figure travels
  only in the result's `_meta` (`pyeconomics/figure`), never in its structured
  content or text.
- The MCP Registry entry is `server.json` (Step 9, decision 16): its versions and
  its `--from "pyeconomics[mcp]==<version>"` follow pyproject.toml's version
  (`tests/mcp/test_mcp_registry_entry.py`), so a version bump edits it too.
  `.github/workflows/mcp-registry.yml` publishes it, through OIDC from the
  protected `mcp-registry` environment, on a published release or a dispatch on
  the release's tag; `mcp-publisher` moves only by version and SHA-256 together.
- The agent tasks are `scripts/mcp/agent_tasks.py`, one table for CI (their
  scripted calls, `tests/mcp/test_mcp_agent_tasks.py`) and the live evaluation
  (`scripts/mcp_agent_eval.py`, the maintainer's machine only), which writes
  `docs/mcp-evaluations.md`. After changing a tool's name, description or schema,
  rerun the evaluation and commit its page.
- The stand-in world (`tests/data/catalog/catalog_world.py`) answers synthetic
  data and refuses to unless `PYECONOMICS_CACHE_DIR` is set: never run it outside
  pytest, where its answers would land in the user's cache and be served later
  as live data.

## Parity rules

From Phase 4 Step 10, which proves the surfaces generated (ADR-0012 decisions 2
and 3):

- `tests/parity/` asks every golden case of every model, and every bound
  model's default profile, of the Python API, the CLI (`--format json`, one
  newline removed), the REST API and MCP `run_model` (its text and the canonical
  JSON of its structured content), and requires the same bytes, or the same
  problem slug, status, exit code and detail. A parity failure is a bug in the
  surface that changed the bytes: fix the surface, never loosen a comparison.
- The harness (`tests/parity/parity_support.py`) keeps one CLI application
  (`cli.app.run_line` with a prebuilt app), one REST app and one MCP client per
  module; a new parity module reuses them rather than starting a surface per
  case.
- Bound runs use `parity_world.py`'s stand-ins at `AS_OF`, with canary keys and
  `LeakCheck`, and empty the cache before each surface (a cached series would
  record `cache_hit`). MCP binds under its `llm_use` policy, so its answers are
  compared with the Python API's under the same policy. A new bound model whose
  default profile needs inputs that are not data adds them to
  `parity_world.GIVEN`; one the stand-ins cannot serve gets a frame there.
- `test_generator_guard.py` fails on a string literal (docstrings aside) in
  `cli/`, `server/` or `mcp/` that names a model id; `mcp/headline.py` is the
  one declared list.
- ci.yml's `parity` job repeats the comparison out of process on the built
  wheel (`scripts/parity/check_installed.py`), for one golden case per domain.

## AI narrative rules

From Phase 4 Step 11, which builds the optional AI narrative (ADR-0012
decision 17):

- `pyeconomics.ai` imports the standard library and pyeconomics only: an AI
  provider is an `AiProvider` with a `ProviderInfo` (one host, a header key
  slot, library-only terms with storage forbidden) whose request goes through
  the data layer's transport, never a client library; the `ai` extra stays
  empty and nothing in `ai/` calls `.reveal()` (`tests/ai/test_ai_layering.py`).
- `narrate` refuses hosted mode, the default `ai_enabled = false`, offline
  mode, records `surfaces.gate.check_records` refuses, and a missing key, in
  that order and before any request. No MCP tool and no REST route imports
  `pyeconomics.ai`; the command line's `--narrate` binds under the user's
  `llm_use` policy and keeps standard output the canonical bytes.
- The prompt holds the result's own facts only (`ai/prompt.py`), never the
  manifest; every string goes through `scrub_text` and `problems.scrub`. A
  narrative is never written into a result, an export, a bundle or the cache.
- The default provider and model live in `ai/defaults.py` with the selector run
  that chose them; a new default is a new selector run, recorded there and in
  the pull request. The price table (`ai/prices.py`) is read again within 180
  days (`test_the_price_table_is_no_more_than_180_days_old`): reread every page
  in `SOURCES`, move the dates, and add a dated row for a scheduled change.
- Offline tests replay `tests/ai/cassettes/<provider>/narrate.json`, synthetic
  answers in each API's shape, written by `tests/ai/build_ai_cassettes.py`;
  after changing the prompt, a request or the narrated card, rebuild them. The
  live run (`uv run pytest -m live --force-enable-socket tests/ai -s`) is the
  maintainer's, with their own keys, and its cost goes in the pull request.

## Web rules

From Phase 5 Step 3, which builds the site (ADR-0013). Each step that builds
a part of the site adds its rules here.

- No page is written by hand for one model. Every model page, calculator,
  problem page and source entry is generated from the site data that
  `scripts/web/export_site_data.py` exports from the registry and the
  catalog, so a new model or provider appears with no web code. A
  calculator renders the canonical bytes the API returns and downloads them
  unchanged; a table, chart or summary goes beside them, never in their
  place.
- One Content Security Policy for every page (decision 9), built from
  Astro's hashes and sent from `_headers` and by the local server. No page,
  island or vendor adds `'unsafe-inline'` or `'unsafe-eval'` or loosens it;
  `'wasm-unsafe-eval'` is the one exception, for search.
- No third-party script: the only script not built from `web/` is the
  analytics tracker decision 13 chose, served from our own origin at a
  pinned version, in production builds only. A page talks only to the
  origins decision 9 names.
- No key, token, secret, internal hostname or `*.run.app` origin reaches
  the bundle, a page or the generated client. The API is called on the
  same origin.
- A user's file is parsed in the browser (decision 11), and only the values
  a run needs travel, in the run's body. The site keeps no input in
  storage, the URL or analytics.

From Phase 5 Step 3, which builds the web foundation:

- Build the site with `npm ci && npm run data && npm run build` in `web/`
  (Node from `web/.nvmrc`). `npm run data` runs
  `scripts/web/export_site_data.py` through `uv run --locked --all-extras`
  and generates the TypeScript client; both outputs are git-ignored and the
  build refuses to start without them. Pages read the data only through
  `web/src/lib/site-data.ts` and the `models` content collection (Step 5).
  Install with `npm ci --ignore-scripts`.
- `web/csp.config.ts` is the one place a policy source is added, and only a
  source decision 9 allows (its `ALLOWED` table); Steps 14 and 15 add their
  origins there. `scripts/headers.ts` runs after every build, writes the
  union of every page's hashes into `dist/_headers` and fails on an unsafe
  source, an unhashed inline script or style, a `style` or `on*` attribute,
  a `javascript:` URL, another origin's script or stylesheet, a line over
  2,000 characters or a server route. Never put a `_headers` file in
  `web/public/`, and never loosen the policy for a page. Astro's policy does
  not run in `astro dev`: test it on a build.
- KaTeX renders MathML only, at build time, through `src/lib/math.ts`
  (`throwOnError`, strict, and every trusted command refused), so a formula
  ships no script or inline style. In an Astro attribute, write LaTeX as
  ``String.raw`...` ``: a quoted attribute reads `\f` as a form feed.
- `dependencies` in `web/package.json` are exactly what reaches browsers;
  build and test tools are `devDependencies`. `scripts/checks/web_licences.py`
  holds the production tree to MIT, BSD, Apache-2.0, ISC and 0BSD, and in
  the web job also fails on any package in the client bundle
  (`.astro/shipped-packages.json`) that is a development dependency.
- shadcn/ui components are copied into `src/components/ui/`
  (`components.json`, style `new-york`); a link styled as a button uses
  `buttonVariants()` on the `<a>`, because `asChild` does not cross from an
  Astro page into a React component. No web font, and the brand blue never
  carries text on white (`--link` does).
- Playwright (axe at WCAG 2.2 AA in light and dark, and a listener that fails
  on any CSP violation or console error) and `scripts/lighthouse.ts`
  (Lighthouse 13 directly: `@lhci/cli` fails `npm audit`) run against
  `wrangler dev` on 127.0.0.1:8788, so `_headers` applies as on Cloudflare.
  Stop any other server on that port first.
- TypeScript stays on 6.0 in both Node projects while `astro check` refuses
  7 (Dependabot ignores its major). ESLint uses `eslint-plugin-jsx-a11y-x`,
  the fork `eslint-plugin-astro` supports on ESLint 10, with no warning
  allowed; a suppression carries its reason.

From Phase 5 Step 4, which puts the site on staging:

- One edge Worker module, `tools/node/edge/worker.mjs`, serves both
  `staging-api.pyeconomics.dev` and the site. In `web/wrangler.jsonc` it runs
  first only on its `API_PATHS` (`run_worker_first`; `worker.test.mjs` holds
  the two equal), and with an `ASSETS` binding it sends no other path to the
  origin. It strips every cookie and `cf-access-*` header, adds the edge
  credential from a Worker secret and `nosniff` to what it returns. After a
  change to it merges, redeploy the API-only Worker from `main` by hand
  (`docs/operations/staging.md`).
- The env-less `web/wrangler.jsonc` is what `wrangler dev` serves: no origin,
  no secret. Env `staging` deploys only from `deploy-staging.yml`'s `site`
  job, with `wrangler versions upload` and `versions deploy` under
  `CLOUDFLARE_API_TOKEN`, which holds Workers Scripts: Edit on the account and
  no zone, DNS, route or Access permission (per-Worker roles grant nothing
  through the API yet: issue #231); `wrangler deploy` (which rewrites the
  custom domain) is the maintainer's. Only the steps that call Wrangler get the
  token.
- `SITE_FLAVOUR` names the deployment a build is for, read by
  `scripts/headers.ts`: unset is local (always indexable, for Lighthouse's
  SEO audit), `staging` is never indexed, `production` is indexed only when
  the site data's version is a final release (`indexable()`), and any other
  value fails the build. A build that must not be indexed sends
  `X-Robots-Tag: noindex` on every path and `scripts/indexing.ts` writes
  `Disallow: /` into `robots.txt`. A new flavour joins `FLAVOURS` and
  `indexable()` there with its tests.

From Phase 5 Step 5, which generates the model and problem pages:

- Model pages come from the `models` content collection
  (`src/content.config.ts`), each `registry.json` entry validated by
  `ModelSchema` (`src/lib/registry-schema.ts`, REGISTRY_SCHEMA's keys); a
  registry change the pages cannot render fails the build. A page's derived
  values (URLs, variables tables, bound data, evidence words) live in
  `src/lib/models.ts` and `src/lib/paths.ts`; `tests/unit/models.test.ts`
  holds every variables table equal to the model's card. A model's page is
  `ModelPage.astro`, the one place its sections are laid out; Step 6 adds the
  calculator island there.
- Card text reaches HTML only through Astro's escaping: never `set:html` a
  registry string. The two exceptions are a formula (`Math.astro`, KaTeX's
  MathML) and JSON-LD, written with `jsonLdText` so no text can close its
  `<script type="application/ld+json">`. `tests/unit/model-page.test.ts`
  renders a hostile toy card through Astro's container API and finds no
  element or handler from it.
- A problem page's text comes from `pyeconomics.surfaces.problem_guide`
  (`GUIDES`, one per row of `problems.ROWS`, held equal by a test), exported
  in `problems.json`; a new error-table row needs its guide.
- Every page, the 404 page aside, gets a canonical link, Open Graph and
  Twitter tags and a 1200x630 image drawn at build time
  (`src/pages/og/[...slug].ts`, astro-og-canvas, the Noto Sans files of
  `@fontsource/noto-sans` and the repository's mark: nothing is fetched); a
  generated page joins `sitePages()` in `src/lib/pages.ts`.
- `scripts/indexing.ts` runs after `headers.ts`: it writes `robots.txt` and
  `_redirects` (every model alias's page, 301 to its model's) and fails on a
  page the sitemap misses or a path in `web/released-pages.json` that neither
  builds nor redirects. A shipped page never disappears: retire one with a
  redirect, never by deleting it from the ledger. Never put `robots.txt` or
  `_redirects` in `web/public/`.
- `npm run test:dist` (Vitest, `tests/site/`) runs over the built `dist/`:
  page counts, sections, MathML, JSON-LD, social images, internal links and
  markup. A link to a page a later step builds goes in its `PLANNED` table
  with that step, which removes the row when the page exists. Playwright
  checks every page's headers and layout, and axe and the keyboard only on
  its `SAMPLE` (the calculator's states in `calculator.spec.ts`).
- Git Bash heredocs collapse `\\` and the editor tools may write ` ` as
  the character itself: check escapes in TypeScript written either way.

From Phase 5 Step 6, which builds the calculators:

- A model's calculator is one island, `src/components/calculator/
  Calculator.tsx`, `client:visible` in `ModelPage.astro`, with small props
  (`calculatorProps`). It loads its model's module from
  `src/data/generated/validators/` (`src/lib/validators.ts`): the validators
  `scripts/web/compile_validators.mjs` precompiled with RJSF's
  compileSchemaValidators on Ajv's 2020-12 class, the schema they were
  compiled from, a family's member schemas and the examples. Never compile a
  validator in the browser or import Ajv's compiler there; `require-data.ts`
  fails the build on a missing or stale validator. The compiled schema drops
  only `$schema` (RJSF rewrites a 2020-12 schema's $refs, which breaks the
  precompiled root check), each option RJSF validates while choosing a
  oneOf's or anyOf's option is compiled too, and a family's form validates
  against its calculation's member. `tests/unit/forms.test.tsx` renders every
  model's form with each example: a schema RJSF asks about without a
  compiled validator fails it.
- No page carries the form's code or styles before it renders: the island
  `Calculator.tsx` is a shell that imports `CalculatorForm.tsx` dynamically,
  and the form adopts `src/styles/calculator.css` (its and the theme's
  utilities only, imported `?inline`) as a constructed stylesheet, because
  Astro links a dynamic import's CSS in the page head. `global.css` leaves
  the calculator's sources out (`@source not`); never `@source` the theme
  there. `scripts/lighthouse.ts` gives each run a Chrome of its own: a
  shared Chrome reuses one renderer for the origin, and V8 walking its heap
  at each load showed in CI as a long unattributed task.
- A run goes through `src/lib/run-request.ts` (the generated client, POST, the
  inputs' JSON) and its bytes are kept as received; "copy JSON" and the JSON
  download hand them over, and every other download is the same POST with
  `?format=`. Server text reaches the page as React text only, and an
  `https://` terms page is the only link a result supplies.
- Charts are `src/lib/figure.ts` (held equal to every `example_figure`) on
  Plotly.js's basic bundle, imported only when a chart renders, with
  `plotly.css` as a same-origin link and the no-inline-styles marker in the
  island. `plotly.js` is a devDependency listed in `web_licences.py`'s
  `BUILD_OUTPUT`: only its prebuilt `dist/` files ship, and its source tree
  holds licences the allowlist refuses. Its version follows
  `PLOTLY_JS_VERSION` (`tests/unit/figure.test.ts`).
- Live data posts `?profile=` (and `?as_of=`) without the fields the profile
  binds, only where `surfaces.json`'s profiles say hosted mode serves every
  bound field of the chosen calculation; elsewhere the page names the fields.
- `golden.json` (the export) holds every golden case's inputs and the Python
  API's bytes; `npm run test:parity` sends each through `runModel` to a local
  `pyeconomics serve` and runs every snippet kind for one model per domain. A
  difference is a bug in the side that changed the bytes.
- Playwright's calculator tests forward `/v1/` to `tests/web/e2e_api.py`
  (hosted mode over the catalog world, port 8799); never point it at a real
  cache. `scripts/parity/check_deployed.py` checks a deployed API from the
  same commit's wheel with the container's extras (`deploy-staging.yml`):
  the same bytes, or the same JSON in which only numbers differ, within a
  relative 1e-9, with the result hash following them, because NumPy and
  OpenBLAS choose kernels by CPU. Everything else stays exact, and the web
  parity suite, on one machine, stays byte for byte.

From Phase 5 Step 7, which builds navigation, search and the syllabus seed:

- The fifteen domain sections are `DOMAINS` in `web/src/lib/paths.ts`, in
  ROADMAP §4 7.2's order; a registry domain it lacks fails the build, and a
  planned section (`planned: "Phase 7"`) gets an empty-state page. A new
  domain or a new generated page joins `DOMAINS` or `sitePages()` and the
  dist tests.
- `syllabi/` holds `schema.json` and one TOML file per syllabus version:
  factual topic names, levels, links to the issuing body and model ids only.
  `scripts/web/syllabi.py` is its one loader, for the site data export
  (`syllabi.json`) and `docs/_ext/model_pages.py`; it refuses an unknown or
  non-canonical model id, an unknown topic, a link off the issuer's `site`,
  any text over 40 characters and any id holding `cfa`. Never store a
  learning outcome, reading title or exam text, and change a mapping only
  with the maintainer's review, recorded in the pull request.
- No URL path or query value the site writes carries `cfa` (ROADMAP §5,
  until CFA Institute answers: Step 16); filter values are neutral slugs and
  `tests/site/` scans every page, the sitemap and `_redirects`. A page that
  names the Program writes "CFA® Program" on first use, as an adjective.
  The `/models/` filters read one syllabus; adding a second needs a syllabus
  filter first (`catalog.ts` refuses it).
- Filter state lives in the query string and is read only through
  `parseFilters` (`src/lib/filters.ts`), which keeps a value only when a
  facet offers it; the island renders it as React text. Facets, related
  models and the coverage matrix are computed at build time in
  `src/lib/catalog.ts`; `/coverage/` is never edited by hand.
- Search is Pagefind, run after the build by `scripts/search-index.ts`
  (which removes Pagefind's UI bundles and fails on a count mismatch). A page
  is searched only when `Base.astro` gets `searchable`, which marks its main
  landmark `data-pagefind-body`; give it `data-pagefind-meta="kind:..."`,
  and keep islands and other non-content `data-pagefind-ignore`. The islands
  load `/pagefind/pagefind.js` from the site's own origin through
  `src/lib/search.ts`, and an excerpt reaches the page only as text runs
  (`excerptParts`), never as HTML.
- The header's search box hydrates with `client:interaction`
  (`src/directives/interaction.ts`, registered in `astro.config.ts`), so no
  page loads a script until a visitor reaches for it. Every page therefore
  carries Astro's hashed island runtime. A container test that renders the
  layout passes the directive in a partial manifest (`model-page.test.ts`).

From Phase 5 Step 9, which builds the data explorer and user data:

- Every surface's series options live in `surfaces/series.py`
  (`SERIES_OPTIONS`, `series_arguments`), which the REST route, MCP's
  `get_series` and its executor share; a new option joins there, and
  `tests/surfaces/test_series_options.py` holds the OpenAPI parameters, the
  tool's input schema and the command's signature to it.
  `tests/parity/test_parity_series.py` holds one concept's bytes equal on the
  four surfaces, with and without each kind of transform.
- `/data/` and one page per concept (`conceptPath`: each id part a segment,
  `_` a hyphen) are generated from `concepts.json`. Its `snapshot` field comes
  from `snapshot_set()` (the export's `snapshot_concepts()`), never by hand.
  The explorer island (`SeriesExplorer.tsx`) fetches in hosted mode only a
  concept the snapshot serves, gives `local_command` for the rest, asks the
  server's mode from `GET /version` (local mode, Step 10, offers every
  concept), and gives the Python call for a concept with parameters, which the
  series route does not take.
- A chart draws its attribution and as-of date on itself
  (`explorer.ts seriesFigure`, the text escaped for Plotly's pseudo-HTML) and
  repeats them beneath it; every download is the same GET with `?format=`.
  `SERIES_TRANSFORMS`, `SERIES_FORMATS` and `CONVERT_METHODS` in `explorer.ts`
  are held equal to Python's by `tests/web/test_explorer_constants.py`.
- A user's file is read only in `src/workers/parse-file.ts` (Papa Parse,
  read-excel-file's `web-worker` build, fflate's declared-size check), one
  worker per file, stopped after 30 s, at most 5 MB and the calculation's
  largest `maxItems` in rows, as values only: no formula is evaluated and no
  link followed. Only the values mapped into the form travel, in the run's
  body; the file, its name and its other columns never leave the page. Never
  add the npm `xlsx` package. The worker's packages reach
  `.astro/shipped-packages.json` through `vite.worker.plugins`.
- The privacy proof is two tests: `user-data.spec.ts` (Playwright's `network`
  fixture logs every request: none to another origin, one same-origin POST,
  nothing of the file in it) and `tests/server/test_server_user_data.py` (only
  the run route's `_body` reads a body, no log call is handed one, POST runs
  are `no-store`). The server logs a run's problem on a caller's values
  without its detail (`problems.record(detail=False)`), which can quote one.
- A model whose bound data the hosted site may not serve says which sources
  and gives `LOCAL_APP` beside its calculator (`data-library-only`;
  `models.ts unservedSources`). A Playwright test that relies on `/v1/` or
  `/version` reaching the test API must ask for the `api` fixture, and an
  island the test drives must be hydrated first (`data-hydrated`).

From Phase 5 Step 10, which builds the local app and the pyeconomics-app
wheel (decision 16):

- The repository is a uv workspace. `packages/pyeconomics-app` builds a pure
  wheel with no dependency: `pyeconomics_app/__init__.py` (`site_path()` and
  nothing else), `py.typed`, and `site/`, which `scripts/web/package_site.py`
  copies from `web/dist/` (git-ignored; it refuses a build whose
  `version.json` is another version). `uv build` at the root builds
  pyeconomics alone, checked by `dist_contents.py`; `uv build --package
  pyeconomics-app --wheel --out-dir dist-app` builds the app, checked by
  `scripts/checks/app_contents.py` (static site files only: a new kind of
  site file needs an edit there). The member ships LICENSE and NOTICE as
  byte copies of the root's.
- One version for both: a bump moves `pyproject.toml`, the member's
  `pyproject.toml`, `[app]`'s pin, `CITATION.cff`, `server.json` and
  `uv.lock` (`uv lock --no-config`) together
  (`tests/unit/test_app_version.py`). `[app]` carries the `server` extra's
  requirements, which `serve` needs, and stays out of `[all]`.
- `pyeconomics serve` mounts the installed site through `ServerSettings.site`
  (`server/site.py`) after every route: only a GET or HEAD of a path no API
  route and nothing under `/v1/` claims reaches it. Its responses carry the
  packaged `_headers`, parsed (never a second copy of the policy), and
  `X-Robots-Tag: noindex`; `_headers` and `_redirects` are never served, and
  StaticFiles follows no link out of the site. A site whose `_headers` gives
  `/` no Content-Security-Policy is refused, and so is a site in hosted mode.
- The islands read the server's mode from `GET /version` through
  `series-request.ts serverMode()`: `"hosted" | "local"`, held to
  `server/settings.py MODES` by `tests/web/test_explorer_constants.py`. A
  local-only offer shows only when the mode is `local`, so it never runs
  against the hosted API.
- `SITE_FLAVOUR=app` is the app wheel's build (release.yml and ci.yml's
  package job): never indexed and, like a local build, carrying no analytics
  and no error tracking, which Steps 14 and 15 add to production builds only.
- The local Playwright run: `npm run build`, then `uv run --no-project python
  scripts/web/package_site.py`, then `npm run e2e:local` in `web/`. It drives
  `tests/local/` against `tests/web/e2e_api.py --local` (port 8798): the app
  `serve` builds, with the packaged site, over the catalog world's stand-ins.

## Documentation rules

From Phase 5 Step 11, which builds the tutorials, how-to guides, study paths and
migration guide (ADR-0007):

- A page under `docs/tutorials/` or `docs/how-to/` joins its index's toctree and
  the lists in `tests/docs/test_guides.py`. It and `docs/migration.md` run under
  `docs/conftest.py`'s `GUIDES` as one session (`guide_page`: settings, keys,
  cache, working directory and Treasury's recordings shared by the page), which
  is what a reader has. In such a page a `python` block runs; a `console` block
  runs each `$ pyeconomics` line in-process and each `$ curl` line against the
  real app, every line under a command must appear in what it printed (`...` for
  text left out) and `$ echo $?` gives its exit code; a `shell` block must stop at
  the data with exit 7 offline; a `text` block does not run. Any other program in
  a session fails, so an install line goes in `text`, as do R and Power Query. A
  block of Python never hides in `text`: 0.2.x's calls in `migration.md` are the
  one exception.
- No page shows a float to its last digit: `foundations.time_value`'s present
  value is `61.391325354075946` on Windows and `61.39132535407593` on Linux and
  in Pyodide, so an example that passes on one fails on another. Round it in a
  `python` block; in a `console` block, end the digits with `...`.
- Every `>>>` line is a Sybil example of its own. Elsewhere in `docs/` each
  example is isolated, so state does not carry between them; in `GUIDES` it does,
  and a series a page already fetched serves offline, so a `shell` block there
  must read something the page has not.
- An example that reads data says its output is recorded, and names the source's
  licence class and attribution (`tests/docs/test_guides.py`). No key appears in
  any example; one is set only with `keys set` and its hidden prompt, and a
  missing key is shown on a concept, whose resolver refuses before any request:
  a provider series reaches the check only in the real transport, which a replay
  skips. A recording answers only its own window, so of the series transforms
  only `log`, which needs no wider fetch, runs against one.
- Study paths are generated: `docs/_ext/study_paths.py` writes the git-ignored
  `docs/study-paths/` from `scripts/web/syllabi.py`, one page per level, each
  path carrying the syllabus's neutral id. Its pages hold only the crosswalk's
  names and links and our own pages; a new issuer's marks join `NOTICES`.
- Each model's documentation page links its web page (`model_pages.web_url`).
  `tests/docs/test_cross_links.py` reads the site's rules from the TypeScript and
  holds the two sets equal, and `web/tests/site/site.test.ts` proves each built
  page links back. `explorer.ts LOCAL_APP` is the command `docs/how-to/local-app.md`
  gives (`tests/web/test_explorer_constants.py`).
- `docs/migration.md`'s worked examples are held to `tests/fixtures/legacy/` by
  `tests/docs/test_migration_page.py`, which reads them and never edits them; use
  cases that match exactly, not a half-way value or a rate at the lower bound.
  Its table lists everything 0.2.x exported, and what it names in 1.0 must exist.
- Check a claim about another product (xlwings Lite, Power Query, R's arrow)
  against that product's documentation, or try it: micropip under Node with the
  `pyodide` npm package is what told `xlwings-lite.md` that a bare `pyeconomics`
  line fails, because it resolves to 0.2.6.

From Phase 5 Step 12, which builds the gallery, the in-browser examples and the
finance tutorials:

- A gallery script is `docs/examples/<domain>_<topic>.py`: the file header, a
  reStructuredText title and explanation in its docstring (sphinx-gallery's page),
  a link to a model's page, and `# %%` text blocks. Every registry domain needs one
  (`tests/docs/test_examples_gallery.py`, which also runs them under pytest's
  rules). A script reads no data, and one that runs a model with a chart draws it
  with `.plot()`. The build runs them in-process, under `conf.py`'s audit hook.
  sphinx-gallery skips a script whose text has not changed, so after changing
  `docs/_ext/gallery_figures.py` delete `docs/gallery/` to see the result.
- `gallery_figures.py` is what keeps a figure off every CDN and whole: Plotly's
  stock HTML renderer adds MathJax from one even when it embeds Plotly.js, and a
  figure drawn during page load is wider than the column, so the theme crops it
  unless it is resized on `load`. Look at a chart after changing this: every test
  and the strict build pass on a chart with no x-axis.
- An in-browser example is a marimo notebook in `docs/wasm/`, exported by
  `scripts/docs/export_wasm.py` into the build's `wasm/` directory at the end of the
  build, with `--mode run --no-show-code` (showing the code puts it, and the
  Markdown's source, before any result) and `--single-file`. That last one is not
  optional: without it a page is about 310 files, Read the Docs answers that burst
  429, and a reader sees an error. With it the files load from jsDelivr at marimo's
  exact version, and `MOST_FROM_OWN_HOST` in the browser check holds the page to a
  handful of requests to its host. Each pins `pyeconomics==<version>` in its PEP
  723 block, which must be a version on PyPI, says on its page that it runs
  entirely in the browser and needs no install, imports only `datetime`, `json`,
  `marimo` and `pyeconomics`, and runs only models that need no data: live data
  stays out until #114 and #116 close. A chart uses Vega-Lite through `_mime_`,
  which marimo's page already holds, so no chart library joins the download.
- marimo's export runs Pyodide 314.0.0, which bundles SciPy 1.17, below the wheel's
  floor, and asks `wasm.marimo.app` for its package list. So each page names
  `docs/wasm/pyodide-lock.json` through `<marimo-wasm data-pyodide-lockfile-url>`:
  the packages of the Pyodide `ci.yml`'s pyodide job proves (same
  `pyemscripten_2026_0` ABI), and what it lacks from PyPI, each with its SHA-256,
  which Pyodide checks, so `micropip` asks no index and a changed file is refused.
  After moving the notebooks' pin, marimo or that Pyodide, run `uv run --no-config
  --group docs python scripts/docs/pin_wasm.py` and commit the lockfile; it refuses
  a Pyodide below the pinned wheel's floors, which Pyodide would load unchecked. A
  marimo bump is made by hand (Dependabot ignores it): it also moves
  `__generated_with` in each notebook, and `RUNTIME` in
  `web/tests/wasm/in-browser.spec.ts` follows marimo's own Pyodide. The lockfile is
  never edited by hand or fetched during a build. `pyproject.toml`'s floors do not
  reach it: the pages run the published wheel, not this checkout.
- `npm run e2e:wasm` in `web/` drives each exported page in Chromium until a
  model's result shows, in ci.yml's docs job, and fails on any off-origin request
  that is not marimo's runtime or frontend or a URL in the lockfile, and on a typed
  value leaving the page. Build the documentation first. `WASM_BASE_URL` points it
  at a deployed copy, where it also allows the ad hosts of the script Read the Docs
  adds to every page it serves, which a local or CI run never sees: run it there,
  because that host's limits and additions show nowhere else. Read the Docs asks
  automated access to keep under 4 requests per second, so do not loop it.
- A finance tutorial is a MyST-NB notebook in `docs/tutorials/finance/`, a track of
  its own beside the six-part `TRACK`. It disables sockets first, uses numbers it
  says are invented, asserts what its prose claims, so a false claim fails the
  build, and ends with `## References` naming each method's originators, checked
  against the publisher or Crossref, not memory. It names no curriculum, reading
  or exam (`tests/docs/test_finance_tutorials.py`): teach the skill in our own
  words.

## Units

Rates, returns, yields and percentages are decimals in every API (`0.05`, not
`5`), as ADR-0008 fixes. Every numeric input and output declares its unit.

## Testing

- Run tests with `uv run pytest`, never `python -m pytest`: that puts the
  working directory on `sys.path` and can import a stale copy of the package.
- Sockets are disabled in tests (`pytest-socket`); no test touches the
  network. Warnings are errors. `-m "not live"` is in `addopts`; the opt-in
  live suite is `uv run pytest -m live --force-enable-socket tests/providers`.
- Test basenames stay unique repo-wide (mypy maps them to top-level modules):
  the provider contract suite is `tests/providers/provider_contract.py`,
  because `tests/contract.py` is the model contract.
- Golden tests (cited values with tolerances) and property tests (hypothesis)
  are required for every model from Phase 2. Start a model with
  `uv run python scripts/new_model.py <id>`; the golden format is in
  `tests/golden/README.md`, and CONTRIBUTING's "How it is checked" lists the
  checks a model meets.
- Mark a property test `@pytest.mark.invariant("<model id>", "<invariant id>")`
  for each invariant a model declares, and an independent-library comparison
  `@pytest.mark.oracle("<model id>")`. An oracle test never skips: a missing
  library must fail the suite.
- Never cite the CFA Program curriculum in a golden source or a reference.
- Coverage must stay at or above 95% (branch coverage), and `core/` at 95% and
  `models/` at 90% on their own (`scripts/checks/coverage_floors.py`). ci.yml's
  `tests` job measures it on Python 3.14 and later, where coverage's
  `sys.monitoring` core handles branches; 3.12 and 3.13 run every test without
  measuring. A branch that only those versions take needs its own check.

## File headers

- Python files open with three lines; ruff's `CPY001` requires the copyright
  line:
  ```python
  # <repo-relative path>
  # Copyright <year> Nathan Ramos, CFA
  # SPDX-License-Identifier: Apache-2.0
  ```
- YAML and TOML files start with `# <repo-relative path>`. Markdown and JSON
  follow their own conventions (JSON allows no comments).

## The security gate

The pre-commit hook (prek, `.pre-commit-config.yaml`) is the per-step security
gate: secret scan (gitleaks), SAST (bandit, semgrep with project rules),
dependency audits (`pip-audit`, and `npm audit` for `tools/node`) and the
runtime licence allowlist, beside the quality toolchain. CI re-runs the same
hooks as required checks.

- It is fail-closed. A finding blocks the commit: fix it in the same step.
- Never use `SKIP=` or `--no-verify` on your own judgement. A bypass is for a
  genuine emergency only, needs the maintainer's approval, and is recorded in
  the pull request body's "Security gate bypass" field with the hook, the
  commit and the justification.
- Before each commit, also review the diff for sensitive data: no key in a log,
  manifest, cache, exception or export; no licensed data in fixtures; least
  privilege for every token and workflow permission.
- The wheel's floors follow what Pyodide ships (`numpy`, `pandas`, `pydantic`
  and `platformdirs` above all; ci.yml's pyodide job installs the wheel there),
  so a floor moves only when the code needs it. `uv.lock` is what CI runs:
  Dependabot's uv updates use `versioning-strategy: increase-if-necessary`. They
  do not touch `pylock.toml`: regenerate it on the pull request.
- A new runtime dependency must pass the licence allowlist (ADR-0004). Run
  `uv add`, `uv lock` and `uv export` with `--no-config`, so a user-level
  private index never reaches `uv.lock`.

## The step lifecycle

Roadmap steps run one at a time unless the Execution Order explicitly permits
parallel steps. Each runs in its own conversation, following all six stages
(ROADMAP §5 "Step lifecycle"; the phase roadmap's Overview restates them):

1. **Create the branch first.** Before any other action, run
   `git checkout -b <the step's **Branch:** line>` from a clean, up-to-date
   `main`. `main` is protected with `enforce_admins`; a direct push fails.
2. **Work on the branch**, passing the security gate on every commit.
3. **Open the pull request, then mark the step.** `gh pr create --base main`
   with a Conventional Commits title and a body that references the step and
   its acceptance criteria. Then set the step's `**Status:**` line to
   `Complete — PR #<n> (<YYYY-MM-DD>)`, append ` ✅` to its heading, set its
   Summary Table cell, and commit (`docs: mark Phase N Step M complete`) and
   push on the same branch.
4. **Wait for every required check, then squash-merge**
   (`gh pr merge <n> --squash --delete-branch`). If the branch falls behind,
   `gh pr update-branch --rebase`; never merge `main` into it. A step that
   deploys or publishes is not done until its Deployed & verified check
   passes.
5. **Retire the branch**: `git switch main`, `git pull --ff-only`,
   `git fetch --prune`, and delete local branches whose upstream is gone.
6. **Dispose of every finding, then declare completion** with the exact line
   the roadmap gives, as the last line of the response.

**Status rule.** The phase roadmap on `main` is the ledger. A step is complete
exactly when its own pull request, carrying its `Complete` line, merges. Never
mark a step complete from your own reading of the git history. Start a step
only after its prerequisites read `Complete`, following any explicit parallelism
or prerequisite exception in the roadmap's Execution Order.

Phase 3's named external-approval exception permits Steps 10–20 and the
phase to complete with SEC EDGAR explicitly deferred, after Step 10 verifies
the four unblocked Step 7 providers. It does not mark Step 7 complete or waive
any shipped provider's checks. Use the roadmap's exact release provider set
and carry-over rules; neither SEC access nor GitHub Sponsors approval gates
independent development or Phase 4 entry.

**Triage rule.** Classify every finding that is not the step before acting on
it (ROADMAP §5 "Defect handling & triage"). Each class has one destination and
a label: `spec-rot` (edit the step's task now), `upstream-gap` (patch the
earlier step and the carry-over list), `bug` (fix in-step only if it blocks
the step, otherwise an issue), `model-error` (High: `fix/` branch, golden test,
errata), `architecture` (an issue for a future phase), `process` (write it
where the next session reads it; make it a check if it is a rule) and
`security` (jumps the queue by severity). A finding that is only described in
chat is not disposed of. A pull request holds its step plus blocking fixes
only, and lists the issues it opened.

## Commits and pull requests

- Commit with `git commit -s`. The `dco` check requires a `Signed-off-by:`
  trailer matching each commit's author name and email.
- Pull request titles are Conventional Commits:
  `<type>(<scope>)!: <description>`, with type one of `feat`, `fix`, `docs`,
  `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. The
  title becomes the squash commit on `main`.
- Fill in every section of the pull request template.
- Branch prefixes: `feature/`, `fix/`, `hotfix/`, `chore/`, `docs/`, `perf/`,
  `release/`, `model/`.

## Worktrees

One working tree and one step in flight is the default. A second tree is made
only with `git worktree add`, never a second clone, and only for a `hotfix/`
interrupting a step, steps a roadmap's Execution Order draws in parallel, or
worktree-isolated subagents inside a step (ROADMAP §5 "Worktree strategy").

- Location: the git-ignored `.worktrees/<branch-slug>/` inside the repository.
- Bootstrap before use: run `uv sync --locked` inside the new worktree. Never
  borrow the primary tree's environment.
- One conversation touches one worktree. Merge from the primary tree.
- Remove the worktree (`git worktree remove`, then `git worktree prune`)
  before deleting its branch.

## Windows notes

- Use Git Bash for POSIX shell commands. Set `MSYS_NO_PATHCONV=1` before a
  command with a `rev:path` argument (such as `git show origin/main:file`), or
  Git Bash rewrites it into a Windows path.
- Text is LF everywhere (`.gitattributes`, `.editorconfig`). Python's
  `write_text` writes CRLF on Windows; write bytes, or let an editor tool make
  the change.
- Windows has no executable bit. Mark a script executable in the index with
  `git update-index --chmod=+x <path>`.
