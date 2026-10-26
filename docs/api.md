# The REST API

`pyeconomics serve` serves every registered model and every data source over
HTTP, on your own machine, so any language can use them. A run answers exactly
the bytes of the Python API's `Result.to_json()`; an error is an RFC 9457
problem from the same table the command line uses ({doc}`problems`); a download
is the same export the command line writes ({doc}`exports`). The routes are
generated from the registry, so every model, including one a plug-in package
adds, has its own run route and its own schemas in the OpenAPI document.

## Local mode quick start

The API is in the `server` extra (FastAPI and uvicorn):

```shell
pip install --pre "pyeconomics[server]"
pyeconomics serve
```

`--pre` is needed while 1.0 is in pre-release. The server listens on
`http://127.0.0.1:8000` until Ctrl+C. Its interactive documentation is at
`http://127.0.0.1:8000/docs`. From another shell:

```shell
curl http://127.0.0.1:8000/healthz
curl "http://127.0.0.1:8000/v1/models?q=present+value&limit=3"
curl -X POST http://127.0.0.1:8000/v1/models/foundations.time_value/run \
  -d '{"calculation": "present_value", "rate": 0.05, "periods": 10, "future_value": 100}'
curl "http://127.0.0.1:8000/v1/series/us.unemployment.rate?start=2024-01-01"
```

`pyeconomics serve` takes `--host` (default `127.0.0.1`), `--port` (default
`8000`), `--workers` (default: `PYECONOMICS_WORKERS`, else the number of CPUs)
and `--allow-remote`. Without the extra it exits with code 8, naming it.

## The routes

| Route | What it answers |
|-------|-----------------|
| `GET /v1/models` | Every model's entry, sorted by id; `?domain=` for one domain; `?q=` (and `?limit=`, 1 to 100, default 20) to search, best first |
| `GET /v1/models/{model_id}` | The model's description, as `pyeconomics models describe ID --format json` prints it |
| `POST /v1/models/{model_id}/run` | A run on the inputs in the body: the result's canonical JSON, or a download |
| `GET /v1/models/{model_id}/run` | The same run, its inputs in `?inputs=` |
| `GET /v1/series/{target}` | A concept's or a provider series' data, with its sources and attributions |
| `GET /v1/sources` | Every data provider, from its metadata |
| `GET /healthz` | `{"status":"ok"}` |
| `GET /version` | The package version, the commit (`PYECONOMICS_GIT_SHA`, else `unknown`) and the mode |
| `GET /openapi.json` | The OpenAPI 3.1 document |

Every answer is canonical JSON (RFC 8785) unless a download was asked for. A
query parameter a route does not take, or one named twice, is refused as
invalid input. A model's former id (an alias) redirects (308) to its route.

## Running a model

The body of a `POST` is the model's inputs as a JSON object, exactly as
`pyeconomics.run` takes them, and the answer is the bytes `Result.to_json()`
gives for them: validation, units and bounds are the model's own. A model with
several calculations names one in `calculation`. The `GET` form carries the
same inputs in `?inputs=`: their canonical JSON in base64url without padding
(RFC 4648 section 5), at most 8,192 characters. Both forms answer the same
bytes.

```python
import base64

from pyeconomics.core.canonical import canonical_json

inputs = {
    "calculation": "present_value",
    "rate": 0.05,
    "periods": 10,
    "future_value": 100,
}
text = base64.urlsafe_b64encode(canonical_json(inputs)).rstrip(b"=").decode()
url = f"/v1/models/foundations.time_value/run?inputs={text}"
assert "=" not in text
```

A run binds the model's data first when it is given any of these, and the
inputs in the body then override what is bound, as `pyeconomics.bind` does
({doc}`data/bindings`):

| Parameter | Meaning |
|-----------|---------|
| `as_of=YYYY-MM-DD` | Read each series as published on that date |
| `vintage=real_time` or `latest` | The vintage policy for every binding |
| `profile=NAME` | The named set of bindings (`default` alone binds the default profile at the latest data) |
| `concept=FIELD=ID` | Bind a field to another concept of the same unit and frequency; repeat for more |
| `param=NAME=VALUE` | A concept parameter, such as an SEP `meeting`; repeat for more |

```shell
curl -X POST "http://127.0.0.1:8000/v1/models/macro.policy_rule/run?as_of=2019-06-28" \
  -d '{"calculation": "taylor_1993"}'
```

A bound run reads data with the keys this machine holds ({doc}`data/keys`),
and its manifest records every series, vintage and retrieval time. No route
accepts a key: a key reaches the data layer only from the key chain.

A body above 16 MiB (the input codec's limit) is refused with
`input-too-large` before it is decoded.

## Series

`GET /v1/series/{target}` answers what `pyeconomics data get TARGET --format
json` prints: the frame, the concept it answers (`null` for a provider series),
one record per source read, the candidates passed over and the attributions and
notices the data must be shown with ({doc}`notices`). A target is a concept id
(`us.unemployment.rate`) or a provider series (`fred:UNRATE`; a provider's key
may hold slashes), never a URL. It takes `start`, `end`, `as_of`, `vintage` and
`provider`, as the command line does.

## Formats

`?format=` turns a run or a series into a download, with an attachment
`Content-Disposition` naming the model or the series:

| `format` | Media type | What it is |
|----------|------------|------------|
| `json` (default) | `application/json` | The canonical JSON, shown inline |
| `csv` | `text/csv; charset=utf-8` | CSV with its `#` metadata block |
| `xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | A workbook with `data` and `manifest` sheets |
| `parquet` | `application/vnd.apache.parquet` | Parquet with the manifest in its metadata; needs pyarrow |
| `arrow` | `application/vnd.apache.arrow.file` | An Arrow IPC file; needs pyarrow |
| `bundle` | `application/zip` | A run's reproducibility bundle, its bind request recorded (runs only) |

pyarrow is never installed with pyeconomics: without it, `parquet` and `arrow`
answer `501 missing-extra`, naming it.

## Problems

Every error answers `application/problem+json`, an RFC 9457 problem whose
`type` is `https://pyeconomics.dev/problems/<slug>` ({doc}`problems` lists each
slug with its status): invalid inputs (422, with each field's error and never
its value), an unknown model (404, naming close matches), a licence refusal
(403, with the source's licence class and terms page), an upstream failure (502
or 503, naming only the provider), an unknown route (404) or method (405, with
`Allow`), and anything unexpected (500, with fixed text). A problem never holds
a key, a file path, a host or an upstream URL, and is never cached
(`Cache-Control: no-store`). A busy server, a rate limit (the client's own or
an upstream source's) and an unreachable limiter add `Retry-After`.

## Workers and budgets

Runs and series fetches execute in worker processes, started when the server
starts, each running one task at a time. `PYECONOMICS_WORKERS` (or `--workers`)
sets how many; `0` runs every task in the server's own process. A task waits in
a queue for a free worker, and when the queue is full the server answers `503
server-busy` with `Retry-After`.

Local mode gives a run all the time it takes. Hosted mode holds each run to its
model's cost class, and a run past its budget is stopped, its worker replaced,
and answered `422 budget-exceeded`, naming the command that runs it locally:

| Cost class | Hosted budget |
|------------|---------------|
| `instant` | 2 s |
| `light` | 10 s |
| `heavy` | 30 s |

A series fetch is held to the `heavy` budget, since its time is the source's.

## Local mode and other machines

Local mode reads every source this machine can access, with its keys, so it
listens on a loopback address and answers only requests addressed to one
(`127.0.0.1`, `localhost` or `::1`): a web page that points its own domain name
at 127.0.0.1 cannot read the answers. `pyeconomics serve --host 0.0.0.0` is
refused (exit code 2) unless `--allow-remote` is passed, which serves every
such source to whoever can reach the machine, and the server says so in its
log.

The server logs one line per request, naming the method, the route's template
(never the path or query sent), the status and the time taken, and one line per
problem with its slug, status and scrubbed detail: never a traceback, a key or a
path.

## The OpenAPI document

`GET /openapi.json` is the OpenAPI 3.1 document, as canonical JSON. Each model
has a `POST` and a `GET` run operation, named `run_<domain>_<name>` and
`run_<domain>_<name>_get`, tagged with its domain. Its request body is the
model's own input schema and its result's `inputs` and `outputs` are its own
input and output schemas, those of `pyeconomics.core.schema`, units (`x-unit`),
bounds and examples included. `pyeconomics registry export --out DIR` writes
the same document to `DIR/openapi.json` beside `registry.json`
({doc}`registry`).

```python
from pyeconomics.server import ServerSettings, create_app

app = create_app(settings=ServerSettings(workers=0))
document = app.openapi()
assert document["openapi"] == "3.1.0"
run = document["paths"]["/v1/models/foundations.time_value/run"]["post"]
assert run["operationId"] == "run_foundations_time_value"
assert run["requestBody"]["content"]["application/json"]["schema"] == {
    "$ref": "#/components/schemas/foundations.time_value.input"
}
```

`create_app(mode="local", settings=...)` builds the app for any ASGI server;
`pyeconomics serve` runs it with uvicorn. The interactive documentation, which
loads its scripts from a CDN, is served in local mode only.

## Caching

A run's `GET` form is cacheable. Its answer carries a weak entity tag,
`ETag: W/"<result_sha256>"` (the result's own hash, so two answers with the
same inputs and outputs share it), and `Cache-Control`:

| Run | `Cache-Control` |
|-----|-----------------|
| Reads no data | `public, max-age=86400` |
| Bound, every data record hosted-safe under terms that allow storage | `public, max-age=300` |
| Bound to anything else (a library-only source such as FRED, in local mode) | `no-store` |
| Any `POST` run | `no-store` |
| Any problem | `no-store` |

A request whose `If-None-Match` names the tag is answered `304 Not Modified`
with no body. The server also keeps answered `GET` runs in memory, least
recently used first out (1,024 runs and 64 MiB by default,
`ServerSettings(cache_entries=..., cache_bytes=...)`), and serves a repeat with
an `Age` header and without running the model again. The key is the model's id
and version, the package's version, the inputs' canonical JSON, the bind
request and the format; a bound run's entry lives five minutes at most, since
its data can be revised. A `POST` run, which may carry values from your own
file, is processed in memory for that one run and never kept.

## Hosted mode

`create_app(mode="hosted")` is the public service's app (the container runs
it; `pyeconomics serve` never does). It differs from local mode in what it
serves, whom it trusts and what a request may cost.

**Only hosted-safe data.** The data layer runs in hosted mode, so a series or a
bound run on a source whose licence class is not `hosted-safe` or
`user-supplied` is refused before any request is made, with `403
licence-refused` naming the class in `licence` and the source's terms page in
`terms` ({doc}`notices`, {doc}`reference/sources`). A concept falls back only to
another hosted-safe originator. No route accepts or reveals a key or reads the
cache, and `/v1/sources` never says whether a key is configured.

**The edge.** The hosted service sits behind a Cloudflare Worker that adds a
shared secret to each request it forwards. When `PYECONOMICS_EDGE_CREDENTIAL`
is set (from Secret Manager; at least 32 characters), every route but `/healthz`
and `/version` requires the `X-Pyeconomics-Edge` header to match it, compared
in constant time, and a request without it gets `403 edge-required` with fixed
text. Only after a match is the client's address read from `CF-Connecting-IP`;
a request sent straight to the origin can neither reach the API nor choose the
address its limits count. The credential is never logged or echoed. Local mode
never reads it.

**Rate limits.** Each client, by address (an IPv6 address by its `/64`), has a
limit per group of routes over a moving window:

| Group | Routes | Hosted limit |
|-------|--------|--------------|
| Runs | `POST` and `GET /v1/models/{model_id}/run` | 60 a minute |
| Series | `GET /v1/series/{target}` | 30 a minute |
| Metadata | every other route | 120 a minute |
| Probes | `/healthz`, `/version` | none |

A request past its limit is answered `429 too-many-requests`, with
`Retry-After` and the problem's `retry_after`, the seconds until the window
takes a request again. The counts live in Redis at `PYECONOMICS_RATELIMIT_URL`
(Upstash Redis; a `rediss://` URL, TLS being required for any host but a
loopback one), shared by every instance; without it each process counts on its
own, and says so once at start. If Redis cannot be reached, runs and series
are refused with `503 limits-unavailable` rather than served unlimited, while
metadata is still served. Cloudflare's own rate rule is the outer layer. Local
mode has no limits unless `ServerSettings(rate_limits=RateLimits(...))` gives
some.

**Budgets.** A body above 1 MiB is refused with `413 input-too-large` before it
is read, and a run past its model's budget (2, 10 or 30 seconds by cost class)
is stopped with `422 budget-exceeded`; both details give the command that runs
the same on your own machine, where neither limit applies:

```text
budget-exceeded: risk.var ran past its hosted budget of 30 s; run it locally: pyeconomics models run risk.var --inputs FILE
```

## Disabling a source

An operator turns a failing source off with `PYECONOMICS_DISABLED_PROVIDERS`
({doc}`data/keys`), in either mode and without a release: its series answer
`503 source-disabled` before any cache read or request, a concept falls over
to its next candidate, and `/v1/sources` marks it `"disabled": true`.

## The MCP server at `/mcp`

With the `mcp` extra installed, the same server answers the Model Context
Protocol at `/mcp`, beside `/v1`, as stateless Streamable HTTP (POST only): the
tools {doc}`mcp` describes, for an AI assistant. A tool call that runs a model
or reads a series goes to the same worker pool, under the same budgets, as a
`/v1` request; it passes the host check, the edge check and the rate limits
first, counting as a run, a series or metadata by what it asks for; and its
answer is never kept in the run cache. A request from a browser origin other
than this machine's is refused (any origin, in hosted mode).

## Clients

The TypeScript and Python clients are generated from the same `openapi.json`,
so every model's run, with its own input and result types, reaches them with no
code of their own. Neither is published in this release; CI generates both on
every change, type-checks the TypeScript one, and calls a model through each
against a real `pyeconomics serve`, checking that the bytes equal the Python
API's `Result.to_json()`.

To generate the TypeScript client (with [@hey-api/openapi-ts](https://heyapi.dev),
pinned in the repository's `tools/node` workspace; Node 22.18 or later):

```shell
pyeconomics registry export --out tools/node/generated
cd tools/node
npm ci --ignore-scripts
npx openapi-ts      # writes generated/client
npx tsc --noEmit    # type-checks it
```

```typescript
import { client } from "./generated/client/client.gen.js";
import { runFoundationsTimeValue } from "./generated/client/sdk.gen.js";

client.setConfig({ baseUrl: "http://127.0.0.1:8000" });
const { data } = await runFoundationsTimeValue({
  body: { calculation: "present_value", rate: 0.05, periods: 10, future_value: 100 },
});
```

To generate the Python client (with
[openapi-python-client](https://github.com/openapi-generators/openapi-python-client)),
retitle the components first, because that generator names each class after a
schema's title and two models' definitions can share one:

```shell
pip install openapi-python-client
python scripts/clients/retitle_openapi.py openapi.json openapi-titled.json
openapi-python-client generate --path openapi-titled.json \
  --output-path pyeconomics_client --meta none
```

```text
from pyeconomics_client import Client
from pyeconomics_client.api.foundations import run_foundations_time_value
from pyeconomics_client.models.foundations_time_value_input_present_value_inputs import (
    FoundationsTimeValueInputPresentValueInputs,
)

body = FoundationsTimeValueInputPresentValueInputs.from_dict(
    {"calculation": "present_value", "rate": 0.05, "periods": 10, "future_value": 100}
)
with Client(base_url="http://127.0.0.1:8000") as client:
    response = run_foundations_time_value.sync_detailed(client=client, body=body)
```
