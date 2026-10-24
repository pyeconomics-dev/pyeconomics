# The registry export

`registry.json` describes every registered model in one document. The command
line, the REST API, the MCP server and the Phase 5 web app are generated from
the same registry, and the web app reads this file to build its pages, forms
and charts without importing Python. It is a build artifact, written on demand
and never committed (ADR-0012 decision 8).

```python
import hashlib
import json
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from pyeconomics import registry
from pyeconomics.core.canonical import canonical_json
from pyeconomics.surfaces.registry_export import registry_document, write_registry
from pyeconomics.surfaces.registry_schema import REGISTRY_SCHEMA

document = registry_document()
assert document["format"] == 1
assert [entry["id"] for entry in document["models"]] == list(registry.ids())
Draft202012Validator(REGISTRY_SCHEMA).validate(document)

entry = document["models"][0]
assert entry["example_result"]["inputs"] == entry["examples"][0]["inputs"]

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "registry.json"
    write_registry(path)
    written = path.read_bytes()
assert written == canonical_json(document)
assert json.loads(written)["pyeconomics"] == document["pyeconomics"]
digest = hashlib.sha256(written).hexdigest()  # identifies this document
```

The command `pyeconomics registry export` (Step 4 of the 1.0 roadmap) writes
the same file.

## What it holds

The document is canonical JSON (RFC 8785, as for results): UTF-8, keys sorted,
no whitespace and no trailing newline, so its SHA-256 identifies it. At the top
level:

| Key | Value |
|-----|-------|
| `format` | `1`, the version of the document's shape |
| `pyeconomics` | the installed package version |
| `models` | one entry per registered model, sorted by id |

Each entry holds the keys of `registry.describe(id)`, plus two:

| Key | Value |
|-----|-------|
| `id`, `version`, `domain`, `title`, `summary`, `tags` | the model's identity |
| `formula` | the formula in LaTeX, one line per item |
| `assumptions`, `limitations`, `evidence`, `cost` | what the card states |
| `references` | the citations: key, citation, DOI, URL, locator and ISBN |
| `invariants`, `no_invariants_reason` | the properties the tests check |
| `examples` | each example's name, note and validated inputs |
| `charts` | the chart specifications a result can draw |
| `aliases`, `changelog` | former ids and the version history |
| `bindings` | the data each input field can be bound to, empty for most models |
| `extra` | the optional extra the model needs, or `null` |
| `input_schema`, `output_schema` | the model's JSON Schema 2020-12 documents |
| `card` | the model card in MyST Markdown |
| `example_result` | the result of the first example |
| `example_figure` | a Plotly figure of that result, or `null` |

`example_result` is the full result, manifest included, of the model's first
example, run through the same path every surface uses, on the example's
explicit inputs. The export never binds data, so it reads no source and no key,
and a bound model's example records no data sources. The value is `null` only
where the model's own extra is not installed, such as `econometrics.garch` on
Python 3.15, for which arch publishes no wheel yet. Any other failure of a first
example stops the export with a `RegistryError` naming the model.

`example_figure` is the Plotly figure of the result's first applicable chart,
as Plotly's JSON, with `layout.template` removed: a default template is tens of
kilobytes, and every consumer styles the figure itself. It is `null` without
the `plot` extra, for a result with no applicable chart, or when the document is
built with `figures=False`, which changes nothing else.

The document holds no clock, host name, user name, file path or environment
value, so two exports of one installation are byte-identical wherever they are
written. The manifests do record the versions of pyeconomics and its numerical
libraries, which describe the installation.

## Its schema

The document validates against `REGISTRY_SCHEMA` in
`pyeconomics.surfaces.registry_schema`, a JSON Schema 2020-12 document with the
`$id` `https://pyeconomics.dev/schemas/registry/1.json`. It lives in a Python
module because the wheel ships only Python files. Every key of an entry is
required and no other is allowed. A model's input and output schemas are
carried as objects: each is a complete 2020-12 document with its own `$id`,
`urn:pyeconomics:model:<id>:<version>:input` or `...:output`.

A change that adds a key keeps format 1 and updates the schema. Format 2, with
a new `$id`, would mean a key removed, renamed or changed in meaning.

## How the web app uses it

The Phase 5 build runs the export once with every extra installed and reads the
file. Each entry gives a model's page (the card), its form (the input schema,
with units under `x-unit` and bounds on every number), a worked example that
needs no server (`example_result`) and a chart Plotly.js draws as it is
(`example_figure`). The `pyeconomics` version and the file's SHA-256 tie a built
site to the library that described it.

## Schema snapshots

Model ids, input and output field names, units and their JSON Schemas are
public API from 1.0.0 (ADR-0003). `tests/surfaces/test_registry_snapshots.py`
holds a snapshot of every model's input schema and output schema, of
`REGISTRY_SCHEMA` and of the sorted (id, version, domain) index, as JSON files
under `tests/surfaces/__snapshots__/`. The suite fails when a model has no
snapshot, when a schema differs from its snapshot, and when a snapshot belongs
to no model.

After an intended change, such as a new model or a new field, rewrite the
snapshots, review the diff and commit it with the change:

```console
uv run pytest tests/surfaces --snapshot-update
```

Then name every changed schema in `CHANGELOG.md`. A change to a released
model's schema is a change to the public API, and its model version bumps when
its outputs change.
