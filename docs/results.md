# Results and manifests

`pyeconomics.run()` returns a frozen `Result` holding validated inputs,
validated outputs, recorded warnings and a provenance manifest. `run_batch()`
returns a `BatchResult` for a table or iterable of mappings (at most 100,000 rows).

The manifest records the schema version (2), model id and version, package and
numerical-library versions, and the seed and bit generator when applicable.
Its `data_sources` list is empty for a model that reads no data; for a bound run
(see [Binding models to data](data/bindings.md)) it holds one record per bound
input field: the series, vintage, observation window, transforms, retrieval time,
licence, attribution and notice. It includes no clock of the run, filesystem path,
host, username or environment value, and no request URL or key: a record's
retrieval time is a fact about the data, recorded where it was fetched.

`inputs_sha256` hashes canonical JSON of the model id, model version and inputs.
`result_sha256` hashes those values plus outputs and warnings. The manifest
itself is outside the hashed body. Canonical JSON follows RFC 8785: key ordering,
number formatting and UTF-8 bytes are deterministic; NaN and infinity are refused.

```python
import pyeconomics

fields = dict(
    calculation="holding_period", beginning_value=100, ending_value=108, income=2
)
first = pyeconomics.run("foundations.returns", **fields)
second = pyeconomics.run("foundations.returns", **fields)
assert first.to_json() == second.to_json()
assert first.manifest.result_sha256 == second.manifest.result_sha256
assert first.to_pandas().shape[0] == 1
```

Use `to_dict()`, `to_json()` or `to_pandas()` for ordinary exports. Optional
integrations provide `to_polars()`, `to_arrow()` and `to_parquet()`; missing
libraries produce an error naming the required package. Table columns use
`inputs.<field>` and `outputs.<field>`, with arrays in list-valued cells.
Single-result Arrow and Parquet exports preserve manifest metadata.

`result.card()` explains the model. `result.plot()` uses its declared chart
specifications and requires the `plot` extra.

## Same bytes everywhere

Every surface returns the same canonical bytes for the same inputs and data:
the Python API's `Result.to_json()`, the command line's `models run --format json`
(followed by one newline), the REST API's run body and the MCP server's
`run_model` text and structured content. They are generated from one registry
and run through one invocation path, so a difference between them is a bug in
the surface that changed the bytes. A failure reaches every surface as the same
problem: one slug, HTTP status, exit code and detail from the error table (see
[Problems](problems.md)).

The parity suite in `tests/parity/` proves it on every CI cell:

- every golden case of every model gives byte-identical results on the four
  surfaces, and each model's invalid input the same problem;
- every model that reads data, bound with its default profile at a fixed date
  over stand-ins for every provider, gives identical bytes, its data records
  included, and no planted key reaches any surface's output;
- every export format (CSV, XLSX, Parquet, Arrow, JSON), written by the Python
  API, the command line and the REST API, reads back to the Python API's values
  and manifest;
- no module of the command line, the REST API or the MCP server names a model,
  and a model only a toy registry holds reaches every surface with no code
  change.

The `parity` job in CI repeats the comparison out of process: the built wheel in
a clean environment, its console script, a real `pyeconomics serve` with worker
processes and `pyeconomics mcp` over standard input and output, for one golden
case per domain.

A new model joins the suite with no edit: its golden cases are read from its
golden file. To run the suite, or one model's cases:

```sh
uv run pytest tests/parity
uv run pytest tests/parity -k "fixed_income.duration"
```
