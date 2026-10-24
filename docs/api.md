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
a key, a file path, a host or an upstream URL. A busy server, and an upstream
rate limit that said how long to wait, add `Retry-After`.

## Workers and budgets

Runs and series fetches execute in worker processes, started when the server
starts, each running one task at a time. `PYECONOMICS_WORKERS` (or `--workers`)
sets how many; `0` runs every task in the server's own process. A task waits in
a queue for a free worker, and when the queue is full the server answers `503
server-busy` with `Retry-After`.

Local mode gives a run all the time it takes. Hosted mode holds each run to its
model's cost class, and a run past its budget is stopped, its worker replaced,
and answered `422 budget-exceeded`:

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

## Hosted mode

`create_app(mode="hosted")` is the public service's app: the data layer in
hosted mode, so only sources classed hosted-safe or user-supplied, every run
held to its budget, and a body above 1 MiB refused with `input-too-large`. The
hosted service's rate limits, caching and edge, and its container, follow in
the 1.0 beta; `pyeconomics serve` never starts hosted mode.
