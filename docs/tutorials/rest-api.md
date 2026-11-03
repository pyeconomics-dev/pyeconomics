# The REST API and the local app

`pyeconomics serve` puts every model and every data source behind HTTP on your
own machine, so any language can use them, and with one more extra it serves
the whole web app too. This lesson takes about fifteen minutes.

## Start the server

Install the `server` extra and start it. It stays in the foreground until you
press Ctrl+C, so open a second shell for the rest of the lesson:

```text
pip install --pre "pyeconomics[server]"
pyeconomics serve
```

It listens on `127.0.0.1`, port 8000. That is on purpose: it reads every source
your machine can reach, with your keys, so it refuses to listen anywhere else
unless you pass `--allow-remote`. Check that it is up:

```console
$ curl http://127.0.0.1:8000/healthz
{"status":"ok"}
```

## Run a model with POST

The body of a `POST` is the model's inputs as JSON, exactly as `pyeconomics.run`
takes them:

```console
$ curl -X POST http://127.0.0.1:8000/v1/models/foundations.time_value/run \
  -d '{"calculation": "present_value", "rate": 0.05, "periods": 10, "future_value": 100}'
..."outputs":{"calculation":"present_value","present_value":61.391325354075946}...
```

The answer is the same bytes `Result.to_json()` gives in Python, so a result is
the same on every surface. A failure is a problem document, from the same table
the command line uses. It names its type and the field that failed, and it never
repeats the value you sent:

```console
$ curl -X POST http://127.0.0.1:8000/v1/models/foundations.time_value/run \
  -d '{"calculation": "present_value", "rate": 7, "periods": 10, "future_value": 100}'
..."loc":["present_value","rate"]...
..."status":422...
..."type":"https://pyeconomics.dev/problems/invalid-input"...
```

A failed request answers its HTTP status, here 422, but `curl` still exits 0
unless you pass `--fail`, so a script should check the status.

## Run a model with GET

A `GET` run carries the same inputs in `?inputs=`, so the whole request fits in a
link, and an answer can be cached. The value is the inputs' canonical JSON, in
base64url without padding:

```python
>>> import base64
>>> from pyeconomics.core.canonical import canonical_json
>>> inputs = {
...     "calculation": "present_value",
...     "rate": 0.05,
...     "periods": 10,
...     "future_value": 100,
... }
>>> text = base64.urlsafe_b64encode(canonical_json(inputs)).rstrip(b"=").decode()
>>> text
'eyJjYWxjdWxhdGlvbiI6InByZXNlbnRfdmFsdWUiLCJmdXR1cmVfdmFsdWUiOjEwMCwicGVyaW9kcyI6MTAsInJhdGUiOjAuMDV9'
```

Both forms answer the same bytes:

```console
$ curl "http://127.0.0.1:8000/v1/models/foundations.time_value/run?inputs=eyJjYWxjdWxhdGlvbiI6InByZXNlbnRfdmFsdWUiLCJmdXR1cmVfdmFsdWUiOjEwMCwicGVyaW9kcyI6MTAsInJhdGUiOjAuMDV9"
..."present_value":61.391325354075946...
```

## Download a file

Add `format` and the same run comes back as a download, with its `#` metadata
block:

```console
$ curl "http://127.0.0.1:8000/v1/models/foundations.time_value/run?inputs=eyJjYWxjdWxhdGlvbiI6InByZXNlbnRfdmFsdWUiLCJmdXR1cmVfdmFsdWUiOjEwMCwicGVyaW9kcyI6MTAsInJhdGUiOjAuMDV9&format=csv"
# model: foundations.time_value version 2
"inputs.calculation","inputs.rate",...,"outputs.present_value","result_sha256"
```

Series work the same way, and carry the attribution their data requires. This
one is the Treasury yield from {doc}`data-and-keys`, a `hosted-safe` source, and
its output here comes from a recorded response:

```console
$ curl "http://127.0.0.1:8000/v1/series/us.treasury.nominal_10y?start=2025-01-01&end=2025-01-31&format=csv"
# attribution: Source: U.S. Department of the Treasury.
```

Keep those `#` lines with the data, or show the attribution wherever it appears.

## Read the interactive documentation

Open <http://127.0.0.1:8000/docs> in a browser. It lists every route, with each
model's own input schema, and you can try a run from the page. It loads its
scripts from a CDN, so it needs the network.

## Serve the web app

Stop the server with Ctrl+C. The `app` extra adds the web app, so the same
command serves it at `/`:

```text
pip install --pre "pyeconomics[app]"
pyeconomics serve
```

Open <http://127.0.0.1:8000>. You now have the site on your own machine: every
model page, every calculator and the data explorer. Your keys and every source
your installation can reach are available to it, which the public site cannot
offer, and it loads no analytics. The {doc}`local app guide </how-to/local-app>`
shows what else changes.

## Next

{doc}`/api` is the full reference. {doc}`mcp` gives the same models to an AI
assistant.
