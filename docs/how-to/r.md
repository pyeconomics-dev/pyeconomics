# Get outputs into R

R reads pyeconomics in two ways: a Parquet export through
[arrow](https://arrow.apache.org/docs/r/), or a REST download through
[jsonlite](https://cran.r-project.org/package=jsonlite). Use Parquet for tables
and JSON for one result. Rates are decimals in both.

The R below is a recipe the test suite does not run. The Python and shell steps
that produce its files do run.

## A Parquet export

Parquet needs [pyarrow](https://arrow.apache.org/docs/python/) beside
pyeconomics: `pip install pyarrow`. Write the file from the command line:

```console
$ pyeconomics models run foundations.time_value --calculation present_value --rate 0.05 --periods 10 --future-value 100 --format parquet --out present-value.parquet
```

It holds one row, with its columns named as `Result.to_pandas()` names them:

```python
>>> import pyarrow.parquet as pq
>>> schema = pq.read_schema("present-value.parquet")
>>> "outputs.present_value" in schema.names, "result_sha256" in schema.names
(True, True)
```

Then read it in R. The column names hold dots, so ask for them with `[[`:

```text
library(arrow)

result <- read_parquet("present-value.parquet")
result[["outputs.present_value"]]
```

The manifest, and the attributions of any data the file holds, are in the file's
metadata. `as_data_frame = FALSE` keeps the Arrow table, which carries them:

```text
table <- read_parquet("present-value.parquet", as_data_frame = FALSE)
manifest <- jsonlite::fromJSON(table$metadata[["pyeconomics.manifest"]])
manifest$model_id
```

A data export works the same way. Its `pyeconomics.attributions` entry lists what
you must show beside the data. Treasury is a `hosted-safe` source, and this output
comes from a recorded response of its own file:

```console
$ pyeconomics data get us.treasury.nominal_10y --start 2025-01-01 --end 2025-01-31 --format parquet --out yields.parquet
```

```python
>>> import json
>>> metadata = pq.read_schema("yields.parquet").metadata
>>> json.loads(metadata[b"pyeconomics.attributions"])
['Source: U.S. Department of the Treasury.']
```

## A REST download

Start the server ({doc}`/tutorials/rest-api`), then run a model with a `GET`.
`?inputs=` holds the inputs' canonical JSON in base64url, which this prints:

```python
>>> import base64
>>> from pyeconomics.core.canonical import canonical_json
>>> inputs = {
...     "calculation": "present_value",
...     "rate": 0.05,
...     "periods": 10,
...     "future_value": 100,
... }
>>> base64.urlsafe_b64encode(canonical_json(inputs)).rstrip(b"=").decode()
'eyJjYWxjdWxhdGlvbiI6InByZXNlbnRfdmFsdWUiLCJmdXR1cmVfdmFsdWUiOjEwMCwicGVyaW9kcyI6MTAsInJhdGUiOjAuMDV9'
```

The answer is one JSON object, and jsonlite turns its parts into a list:

```console
$ curl "http://127.0.0.1:8000/v1/models/foundations.time_value/run?inputs=eyJjYWxjdWxhdGlvbiI6InByZXNlbnRfdmFsdWUiLCJmdXR1cmVfdmFsdWUiOjEwMCwicGVyaW9kcyI6MTAsInJhdGUiOjAuMDV9"
{"inputs":{"calculation":"present_value",...
..."outputs":{"calculation":"present_value","present_value":61.391325354075946}...
```

```text
library(jsonlite)

url <- paste0(
  "http://127.0.0.1:8000/v1/models/foundations.time_value/run?inputs=",
  "eyJjYWxjdWxhdGlvbiI6InByZXNlbnRfdmFsdWUiLCJmdXR1cmVfdmFsdWUiOjEwMCwicGVyaW9kcyI6MTAsInJhdGUiOjAuMDV9"
)
result <- fromJSON(url)
result$outputs$present_value
result$manifest$result_sha256
```

R prints seven significant digits by default, though the value holds them all:
`print(result$outputs$present_value, digits = 17)` shows the rest.

A series answers its frame beside its source records and its attributions. The
dates are in `frame$index` and the values in `frame$values`:

```console
$ curl "http://127.0.0.1:8000/v1/series/us.treasury.nominal_10y?start=2025-01-01&end=2025-01-31"
..."attributions":["Source: U.S. Department of the Treasury."]...
```

```text
series <- fromJSON(paste0(
  "http://127.0.0.1:8000/v1/series/us.treasury.nominal_10y",
  "?start=2025-01-01&end=2025-01-31"
))
yields <- data.frame(
  date = as.Date(series$frame$index),
  value = series$frame$values
)
series$attributions
```

Show those attributions wherever the data appears.

## Without a server

R can call the command line instead, which prints the same bytes:

```text
output <- system2(
  "pyeconomics",
  c("models", "run", "foundations.time_value", "--calculation", "present_value",
    "--rate", "0.05", "--periods", "10", "--future-value", "100"),
  stdout = TRUE
)
result <- jsonlite::fromJSON(paste(output, collapse = ""))
```
