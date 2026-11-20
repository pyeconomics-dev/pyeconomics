# Public API

This page lists everything pyeconomics promises from 1.0.0 on: the names
your code, scripts, agents and links may rely on. From 1.0.0, a change that
breaks one of them needs version 2.0.0, and a name is removed only after at
least one minor release has warned about it
([ADR-0003](https://github.com/pyeconomics-dev/pyeconomics/blob/main/docs/adr/0003-versioning-and-deprecation.md)).
The list was frozen at the release candidate, 1.0.0rc1, under
[ADR-0013 decision 17](https://github.com/pyeconomics-dev/pyeconomics/blob/main/docs/adr/0013-web-app-and-launch.md).

A test, `tests/repo/test_public_api.py`, derives every list below from the code
and fails when the two differ. It also requires this page's fingerprint, a
digest of every list, to appear in `CHANGELOG.md`, so a change to the public
surface is recorded here and in the changelog together.

Inventory fingerprint: `sha256:03888242a827b3a4`

## What is public

- The Python names in each module's `__all__` listed in section 1, together
  with their signatures and documented behaviour.
- Model ids, their input and output field names, units and JSON Schemas; the
  canonical JSON result and the manifest.
- The command line's commands and options, the REST API's paths, operation ids,
  query parameters and schemas, and the MCP server's tool names and schemas.
- The problem slugs and type URIs, HTTP statuses and exit codes.
- The `registry.json` format, the export formats and the reproducibility
  bundle's members.
- The settings, the files they are read from and the environment variables.
- The distributions, the extras, the console script and the plug-in
  entry-point groups.
- The web app's page addresses.

The schemas themselves are pinned by snapshot tests, reviewed whenever they
change: each model's input and output schema (`tests/surfaces/__snapshots__/`),
the OpenAPI document (`tests/server/__snapshots__/test_openapi_snapshot/`) and
the MCP tool list (`tests/mcp/__snapshots__/`).

## What is not

- Any name with a leading underscore, and any module not listed in section 1,
  even where the API reference documents it: reach a listed name through the
  module this page lists it under.
- Wording: descriptions, titles, help text, model cards, a problem's title and
  detail, log messages and the text of a web page. A page's address is public;
  what it says is not.
- The command line's `table` output, which is for people: `--format json`
  writes the canonical result.
- The hosted service's limits and budgets, its hosts and its deployment.
- Anything a pre-release changed before 1.0.0.

## 1. Python API

Every package of `pyeconomics` exports its public names in `__all__`. The
model packages under `pyeconomics.models` are not listed: a model is reached
through the registry by its permanent id (section 10), never by its module.
The modules below without a package of their own are the ones this
documentation tells you to import from by path. `pyeconomics_app` is the
second distribution's module.

### `pyeconomics`

<!-- inventory: python pyeconomics -->
```text
__version__ bind registry run run_batch
```

### `pyeconomics.ai`

<!-- inventory: python pyeconomics.ai -->
```text
DEFAULT_MODEL DEFAULT_PROVIDER NOT_ADVICE Narrative NarrativeDisabledError
NarrativeHostedError PROVIDERS PROVIDER_MODELS narrate
```

### `pyeconomics.cli`

<!-- inventory: python pyeconomics.cli -->
```text
build_app main
```

### `pyeconomics.core`

<!-- inventory: python pyeconomics.core -->
```text
ARRAY_INPUT Alias AsOf BASIS_POINTS_PER_UNIT BIT_GENERATOR BatchResult Binding
Bound Bounds BusinessDayConvention CALENDAR_IDS CalendarId CandidateNote
ChangelogEntry ChartKind ChartSpec Compounding ConvergenceError Correlation
CorrelationArray CostClass Count CountArray Covariance DEFAULT_BOUNDS
DEFAULT_DATE_BOUNDS DEFAULT_PROFILE DEFAULT_ROOT_POLICY DEFAULT_SEED
DEFAULT_TOLERANCES DOMAINS DataSource DateArray DateBounds DateValue DayCount
Days DaysArray DomainError Drawdown ENTRY_POINT_GROUP EXACT Evidence Example
Frequency IRR_LOWER IRR_POLICY IRR_UPPER IndexLevel IndexLevelArray InputError
Invariant LeastSquares LicenceClass LlmUse LlmUsePolicy MAX_ARRAY_LENGTH
MAX_BATCH_ROWS MAX_STRING_LENGTH Manifest MissingOptionalDependencyError Model
ModelCard ModelInputs ModelNotFoundError ModelOutputs ModelSpec ModelWarning
Moments Money MoneyArray PERCENT_PER_UNIT ParsedTransform Periods PeriodsArray
Probability ProbabilityArray Provider PyeconomicsDeprecationWarning
PyeconomicsError PyeconomicsWarning RandomProvenance Rate RateArray Ratio
RatioArray RealtimePeriod Reference Registry RegistryError Result ResultWarning
Return ReturnArray RootPolicy RootResult SEED_MAX SEED_MIN Schedule Symbol
TRANSFORMS TRANSFORM_NAMES Tolerance TransformParameter TransformParameterKind
TransformSpec UNIT_SCHEMA_KEY Unit UnitKind VintagePolicy Volatility
VolatilityArray Years YearsArray accumulated_annuity_factor
accumulated_growing_annuity_factor accumulation_factor actual_days
add_business_days add_months add_years adjust annualized_log_return
annualized_return annuity_factor basis_points_to_decimal bracket_roots
canonical_json canonical_sha256 canonical_transform check_transform
collect_warnings compound_return convert_rate curve_discount_factors
decimal_to_basis_points decimal_to_percent default_bounds default_tolerance
deprecated discount_factor discover effective_annual_rate find_root
format_basis_points format_percent format_transform forward_rate generate
generator growing_annuity_factor growing_perpetuity_factor growth_factor
has_spread implied_rate input_schema internal_rate_of_return interpolate_rate
interpolate_rates is_business_day is_end_of_month least_squares
library_warnings log_return max_drawdown model newey_west_lags output_schema
par_rate parse_transform percent_to_decimal present_value present_value_factor
provenance run run_batch run_model run_model_batch sample_mean sample_moments
sample_variance semideviation_below_mean semideviation_below_target
sign_changes validate_date warn year_fraction
```

### `pyeconomics.core.canonical`

<!-- inventory: python pyeconomics.core.canonical -->
```text
MAX_DEPTH MAX_EXACT_INTEGER canonical_json canonical_sha256
```

### `pyeconomics.data`

<!-- inventory: python pyeconomics.data -->
```text
Access AsOf AuthKind Authentication Binding Bound CachePolicy CandidateInfo
Capability Case ColumnMeta ConceptInfo ConceptNotFoundError ConfigError
CredentialError DATA_DATE_BOUNDS DataError DataProvider DataSource DataWarning
DateConvention Fetched FigiMapping Filing Hit KeyPlacement KeySlot KeySource
LicenceClass LicenceError LlmUse LlmUseError LlmUsePolicy MAX_COLUMNS
MAX_OBSERVATIONS Mode ObservationFrequency OfflineError Origin Platform
ProviderInfo ProviderNotFoundError Query RateLimit RateLimitError
RealtimePeriod Records Request Resolved Response ResponseError SearchHit
SearchResult SeasonalAdjustment Secret Series SeriesMeta SeriesNotFoundError
Settings Skip SnapshotMissingError SourceDisabledError SourceInfo
TERMS_MAX_AGE_MONTHS Table TableMeta Terms Transport TransportError UnitRecord
Vintage VintageKind VintagePolicy Weekday bind bind_model cache candidate_notes
candidates_by_mode catalog configure current_mode describe get has_key
key_variable registry require_allowed resolve resolve_key search settings
sources validate_bindings vintages
```

### `pyeconomics.data.cache`

<!-- inventory: python pyeconomics.data.cache -->
```text
CLOSED_AFTER CacheEntry CacheInfo CacheKey DEFAULT_MAX_BYTES
DEFAULT_TTL_SECONDS DISCARDED_WARNING FILE_NAME Fetched Lookup OFFLINE_WARNING
Origin SCHEMA_VERSION bypass bypassed clear entries expiry info is_closed
lookup may_store memo override path reset save
```

### `pyeconomics.data.catalog`

<!-- inventory: python pyeconomics.data.catalog -->
```text
CONCEPTS Candidate Concept Derived Operand Parameter Shape Tier concepts get
ids
```

### `pyeconomics.data.credentials`

<!-- inventory: python pyeconomics.data.credentials -->
```text
KEYRING_SERVICE KeySource MAX_KEY_LENGTH MIN_KEY_LENGTH Secret delete_key
has_key key_problem key_source key_variable parse_dotenv resolve_key store_key
withheld
```

### `pyeconomics.data.providers`

<!-- inventory: python pyeconomics.data.providers -->
```text
Access AuthKind Authentication Capability Case DataProvider KeyPlacement
KeySlot MAX_QUERY_SERIES MAX_SEARCH_RESULTS Platform ProviderInfo Query
RateLimit SERIES_ID_PATTERN SearchHit current_platform tail
```

### `pyeconomics.data.registry`

<!-- inventory: python pyeconomics.data.registry -->
```text
ENTRY_POINT_GROUP ProviderRegistry RULES Registration discover get ids
installed refresh validate
```

### `pyeconomics.data.transport`

<!-- inventory: python pyeconomics.data.transport -->
```text
DEFAULT_MAX_RESPONSE_BYTES Request Response Transport default_transport
request_key request_path
```

### `pyeconomics.data.transport.base`

<!-- inventory: python pyeconomics.data.transport.base -->
```text
DEFAULT_MAX_RESPONSE_BYTES HOST_PATTERN HTTP_METHODS KEPT_HEADERS
KEY_PLACEMENTS MAX_BODY_BYTES MAX_PARAMETERS MAX_REQUESTS_PER_OPERATION Request
Response Transport check_host declared_hosts request_key request_path
retry_after_seconds
```

### `pyeconomics.exports`

<!-- inventory: python pyeconomics.exports -->
```text
BINARY_FORMATS BundleReport ExportFormat FORMATS check_bundle export
export_bytes write_bundle
```

### `pyeconomics.exports.layout`

<!-- inventory: python pyeconomics.exports.layout -->
```text
ExportFormat FORMATS FORMULA_PREFIXES Subject cell_text escape_text subject
```

### `pyeconomics.mcp`

<!-- inventory: python pyeconomics.mcp -->
```text
build_server
```

### `pyeconomics.registry`

<!-- inventory: python pyeconomics.registry -->
```text
describe domains get ids models refresh resolve validate
```

### `pyeconomics.server`

<!-- inventory: python pyeconomics.server -->
```text
ServerSettings create_app
```

### `pyeconomics.surfaces`

<!-- inventory: python pyeconomics.surfaces -->
```text
BindRequest FieldError Problem invoke invoke_batch problem_for report
```

### `pyeconomics.surfaces.registry_export`

<!-- inventory: python pyeconomics.surfaces.registry_export -->
```text
REGISTRY_FORMAT registry_document write_registry
```

### `pyeconomics.surfaces.registry_schema`

<!-- inventory: python pyeconomics.surfaces.registry_schema -->
```text
REGISTRY_FORMAT REGISTRY_SCHEMA REGISTRY_SCHEMA_ID
```

### `pyeconomics_app`

<!-- inventory: python pyeconomics_app -->
```text
site_path
```

## 2. Command line

Each line is a command, its arguments in capitals, and its options; an
option's choices follow it in braces. The first line holds the flags every
command takes. `pyeconomics models run <model id>` also takes one option per
input field of that model, named after the field with each underscore a
hyphen (`--future-value` for `future_value`), so a model's fields, which are
public with its schema, are its options too. The exit codes are in section 5.

<!-- inventory: cli -->
```text
pyeconomics --debug --help --version -h
pyeconomics --install-completion --output --shell={bash,fish,powershell,zsh} -o
pyeconomics bundle check BUNDLE --format={json,table}
pyeconomics cache clear --provider
pyeconomics cache info --format={json,table} --out
pyeconomics cache ls --format={json,table} --out --provider
pyeconomics cache path
pyeconomics completion SHELL={bash,fish,powershell,zsh}
pyeconomics data describe TARGET --format={json,table} --out
pyeconomics data get TARGET --as-of --end --format={arrow,csv,json,parquet,table,xlsx} --out --provider --start --transform --vintage
pyeconomics data search TEXT --format={json,table} --limit --out
pyeconomics data sources --check-keys --format={json,table} --out
pyeconomics data vintages TARGET --format={json,table} --out
pyeconomics keys delete PROVIDER
pyeconomics keys list --format={json,table} --out
pyeconomics keys set PROVIDER --stdin
pyeconomics mcp --allow-remote --host --port --transport={http,stdio}
pyeconomics models describe MODEL_ID --format={json,markdown} --out
pyeconomics models list --domain --format={json,table} --out
pyeconomics models run MODEL_ID
pyeconomics models search TEXT --format={json,table} --limit --out
pyeconomics registry export --figures --no-figures --out
pyeconomics serve --allow-remote --host --port --workers
pyeconomics models run <model id> --as-of --batch --bundle --concept --format={arrow,csv,json,parquet,table,xlsx} --inputs --narrate --out --param --profile --vintage={latest,real_time}
```

## 3. REST API

`pyeconomics serve` (the `server` extra) and the hosted service answer these
routes. Each line is a method, a path, the operation id and the query
parameters the operation takes. Every model has the two run operations the
`<model id>` lines describe, its operation id spelled with each dot of the id
an underscore. A run for an id that is no model's answers on the route outside
the OpenAPI document: an alias redirects to its model's route (308), and
anything else is `model-not-found`. `/mcp` takes the MCP server's Streamable
HTTP requests by `POST` only.

<!-- inventory: rest -->
```text
GET /healthz healthz
GET /v1/models list_models domain,limit,q
GET /v1/models/{model_id} describe_model
GET /v1/series/{target} get_series as_of,end,format,provider,start,transform,vintage
GET /v1/sources list_sources
GET /version version
GET /v1/models/<model id>/run run_<model id>_get as_of,concept,format,inputs,param,profile,vintage
POST /v1/models/<model id>/run run_<model id> as_of,concept,format,param,profile,vintage
GET /docs (outside the OpenAPI document)
GET /openapi.json (outside the OpenAPI document)
GET /redoc (outside the OpenAPI document)
GET /v1/models/{model_id}/run (outside the OpenAPI document)
POST /mcp (MCP Streamable HTTP)
POST /v1/models/{model_id}/run (outside the OpenAPI document)
```

## 4. MCP server

`pyeconomics mcp` (the `mcp` extra) serves these tools over stdio, or over
Streamable HTTP with `--transport http` and at `/mcp` on the REST server. Its
name in the MCP Registry is `io.github.pyeconomics-dev/pyeconomics`. Five
tools are the discovery tools; each of the others runs one model, whose input
schema is the tool's.

<!-- inventory: mcp -->
```text
tool corporate_capital_budgeting
tool corporate_cost_of_capital
tool derivatives_binomial_tree
tool derivatives_black_scholes_merton
tool describe_model
tool equity_dividend_discount
tool equity_free_cash_flow
tool fixed_income_bond_pricing
tool fixed_income_curve_bootstrap
tool fixed_income_duration
tool foundations_returns
tool foundations_time_value
tool get_series
tool international_parity_conditions
tool list_sources
tool macro_policy_rule
tool performance_risk_adjusted
tool portfolio_mean_variance
tool risk_value_at_risk
tool run_model
tool search_models
resource ui://pyeconomics/chart text/html;profile=mcp-app
```

## 5. Problems and exit codes

Every failure on every surface is a problem from one table. Each line is a
slug, the HTTP status and the command line's exit code. A problem's `type` is
the URI on the first line with its slug, and the web app's page at that
address explains it. A command line written wrongly exits with code 2 and has
no problem; success is 0.

<!-- inventory: problems -->
```text
type https://pyeconomics.dev/problems/<slug>
invalid-input 422 3
input-too-large 413 3
no-defined-result 422 4
no-convergence 422 4
model-not-found 404 5
provider-not-found 404 5
concept-not-found 404 5
series-not-found 404 5
llm-use-forbidden 403 6
licence-refused 403 6
narrative-disabled 403 6
narrative-not-hosted 403 6
credential-unavailable 503 7
upstream-unavailable 502 7
upstream-invalid-response 502 7
upstream-rate-limited 503 7
offline-cache-miss 503 7
source-disabled 503 7
not-in-snapshot 404 7
data-unavailable 422 7
missing-extra 501 8
budget-exceeded 422 1
route-not-found 404 5
method-not-allowed 405 1
host-not-allowed 400 1
server-busy 503 1
edge-required 403 1
too-many-requests 429 1
limits-unavailable 503 1
registry-error 500 1
invalid-configuration 500 1
pyeconomics-error 500 1
internal-error 500 1
usage-error - 2
```

## 6. Formats

A result is canonical JSON (RFC 8785) holding its manifest. The lines give
`registry.json`'s format and the `$id` of its schema, the manifest's schema
version, the export formats, the REST API's `?format=` values and a
reproducibility bundle's members.

<!-- inventory: formats -->
```text
registry.json format 1 https://pyeconomics.dev/schemas/registry/1.json
manifest schema_version 2
exports arrow csv json parquet xlsx
rest run ?format= arrow bundle csv json parquet xlsx
rest series ?format= arrow csv json parquet xlsx
bundle members ATTRIBUTION.txt README.txt inputs.json manifest.json reproduce.py request.json requirements.txt result.json
```

## 7. Settings and environment variables

The settings are read from `pyeconomics.toml` in the configuration directory
and the working directory, then from the environment; a provider's key from its
own variable, a `.env` file in the configuration directory or the system
keyring. `PYECONOMICS_DEPLOYMENT`, `PYECONOMICS_EDGE_CREDENTIAL`,
`PYECONOMICS_GIT_SHA`, `PYECONOMICS_OTLP_*`, `PYECONOMICS_RATELIMIT_URL`,
`PYECONOMICS_SENTRY_DSN` and `PYECONOMICS_SNAPSHOT_HEARTBEAT` configure a
hosted deployment.

<!-- inventory: settings -->
```text
setting ai_enabled
setting ai_model
setting ai_provider
setting allow_unclear_llm_use
setting cache_dir
setting disabled_providers
setting enable_yfinance
setting mode
setting offline
setting sec_contact
setting snapshot_dir
setting ttl
file pyeconomics.toml
file .env
env PYECONOMICS_AI_ENABLED
env PYECONOMICS_AI_MODEL
env PYECONOMICS_AI_PROVIDER
env PYECONOMICS_ALLOW_UNCLEAR_LLM_USE
env PYECONOMICS_CACHE_DIR
env PYECONOMICS_CONFIG_DIR
env PYECONOMICS_DEPLOYMENT
env PYECONOMICS_DISABLED_PROVIDERS
env PYECONOMICS_EDGE_CREDENTIAL
env PYECONOMICS_GIT_SHA
env PYECONOMICS_MODE
env PYECONOMICS_OFFLINE
env PYECONOMICS_OTLP_ENDPOINT
env PYECONOMICS_OTLP_HEADERS
env PYECONOMICS_RATELIMIT_URL
env PYECONOMICS_SEC_CONTACT
env PYECONOMICS_SENTRY_DSN
env PYECONOMICS_SNAPSHOT_DIR
env PYECONOMICS_SNAPSHOT_HEARTBEAT
env PYECONOMICS_TTL_<PROVIDER>
env PYECONOMICS_WORKERS
key ANTHROPIC_API_KEY
key BEA_API_KEY
key BLS_API_KEY
key CENSUS_API_KEY
key FRED_API_KEY
key GEMINI_API_KEY
key OPENAI_API_KEY
key OPENFIGI_API_KEY
key OPENROUTER_API_KEY
```

## 8. Distributions, extras and plug-ins

A package registers models under the `pyeconomics.models` entry-point group and
data sources under `pyeconomics.providers`
({doc}`data/writing-a-provider`); every surface then serves them.

<!-- inventory: distribution -->
```text
distribution pyeconomics
distribution pyeconomics-app
extra ai
extra all
extra app
extra econometrics
extra keyring
extra mcp
extra plot
extra sdmx
extra server
extra yfinance
script pyeconomics pyeconomics.cli:main
entry-point group pyeconomics.models
entry-point group pyeconomics.providers
```

## 9. Web pages

The web app's addresses, from `web/released-pages.json`, the ledger of every
page a release has served. A page in it never disappears: a build fails when
one goes missing, and a retired page redirects to its successor. Each family
line is a generated family and the number of its pages; the other lines are
pages by address.

- `/models/<domain>/<model>/` is a model's id with each underscore a hyphen:
  `fixed_income.bond_pricing` is `/models/fixed-income/bond-pricing/`.
- `/data/<concept>/` is a catalog concept's id, each part a segment, each
  underscore a hyphen.
- `/problems/<slug>/` is the page a problem's `type` names.

<!-- inventory: pages -->
```text
family /models/<domain>/<model>/ 50
family /models/<domain>/ 15
family /data/<concept>/ 171
family /problems/<slug>/ 33
page /
page /about/
page /assistants/
page /coverage/
page /data/
page /legal/
page /legal/disclaimers/
page /legal/licence/
page /legal/privacy/
page /legal/terms/
page /models/
page /newsletter/
page /pro/
page /problems/
page /search/
page /sources/
```

## 10. Permanent ids

A released model, provider or concept id is never deleted or given to
something else; a renamed model keeps its old id as an alias that warns. The
ledgers below record every id a release shipped, and `registry.validate()`
fails on one that has gone missing or been reused.

<!-- inventory: ids -->
```text
models 50 src/pyeconomics/core/_released.py
providers 31 src/pyeconomics/data/_released.py
concepts 171 src/pyeconomics/data/_released.py
```

## Changing the public API

1. Change the code. `tests/repo/test_public_api.py` fails, printing the list the
   code now gives.
2. Paste that list here and set the fingerprint the test prints.
3. Add the change to `CHANGELOG.md` under Added, Changed, Deprecated or Removed,
   naming the new fingerprint.
4. From 1.0.0, follow ADR-0003: an addition is a minor release; a removal or an
   incompatible change waits for 2.0.0, after a minor release that warns about
   it with a `FutureWarning` naming the replacement.
