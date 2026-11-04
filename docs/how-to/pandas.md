# Get outputs into pandas

pandas comes with pyeconomics, and every result, batch and series turns into a
pandas object.

## One result

`Result.to_pandas()` gives one row: `inputs.<field>`, then `outputs.<field>`,
then the result's hash, so the numbers and what produced them stay together.

```python
>>> import pyeconomics
>>> result = pyeconomics.run(
...     "foundations.time_value",
...     calculation="present_value",
...     rate=0.05,
...     periods=10,
...     future_value=100,
... )
>>> table = result.to_pandas()
>>> float(table.loc[0, "inputs.rate"])
0.05
>>> round(float(table.loc[0, "outputs.present_value"]), 2)
61.39
```

## Many runs

`pyeconomics.run_batch` runs a model once per row of a DataFrame, whose columns
name the input fields. The answer has one row per run, in the same order:

```python
>>> import pandas as pd
>>> rows = pd.DataFrame(
...     {
...         "calculation": ["present_value"] * 3,
...         "rate": [0.03, 0.05, 0.07],
...         "periods": [10, 10, 10],
...         "future_value": [100, 100, 100],
...     }
... )
>>> batch = pyeconomics.run_batch("foundations.time_value", rows)
>>> batch.to_pandas()["outputs.present_value"].round(2).tolist()
[74.41, 61.39, 50.83]
```

## A data series

`frame.to_pandas()` gives a pandas Series indexed by date, where a missing value
is `pd.NA`, never a filled one. Treasury data is `hosted-safe` and carries an
attribution, which pandas will not keep for you: hold on to `found.source`, and
show the attribution wherever the data appears.

```python
>>> import datetime as dt
>>> from pyeconomics import data
>>> found = data.get(
...     "us.treasury.nominal_10y",
...     start=dt.date(2025, 1, 1),
...     end=dt.date(2025, 1, 31),
... )
>>> yields = found.frame.to_pandas()
>>> len(yields), round(float(yields.iloc[0]), 4)
(21, 0.0457)
>>> found.source.attribution
'Source: U.S. Department of the Treasury.'
```

This output comes from a recorded response of Treasury's own file; on your
machine the call reads it live. To keep the record with the data, export it:

```python
>>> from pyeconomics.exports import export
>>> export(found, "csv", "yields.csv")
>>> table = pd.read_csv("yields.csv", comment="#", float_precision="round_trip")
>>> list(table.columns), len(table)
(['date', 'value'], 21)
```

The file's `#` lines hold the attribution and any notice ({doc}`/exports`), and
`comment="#"` skips them. Keep them with the data.

## From the command line

Parquet keeps types exactly and works across a pipe, so another program can hand
a result to pandas. It needs pyarrow, which pyeconomics never installs:
`pip install pyarrow`. Write a file with `--out`:

```console
$ pyeconomics models run foundations.time_value --calculation present_value --rate 0.05 --periods 10 --future-value 100 --format parquet --out present-value.parquet
```

```python
>>> table = pd.read_parquet("present-value.parquet")
>>> round(float(table.loc[0, "outputs.present_value"]), 2)
61.39
```

Or pipe it, which writes no file. `--format parquet` goes to standard output
whenever that is not a terminal:

```text
pyeconomics models run foundations.time_value --calculation present_value --rate 0.05 --periods 10 --future-value 100 --format parquet | python -c "import io, sys, pandas; print(pandas.read_parquet(io.BytesIO(sys.stdin.buffer.read())))"
```

A table read this way leaves the file's metadata behind. The manifest and any
attributions are in its schema, for pyarrow to read:

```python
>>> import json
>>> import pyarrow.parquet as pq
>>> metadata = pq.read_schema("present-value.parquet").metadata
>>> json.loads(metadata[b"pyeconomics.manifest"])["model_id"]
'foundations.time_value'
>>> json.loads(metadata[b"pyeconomics.attributions"])
[]
```

This run read no data, so it has no attributions to keep.
