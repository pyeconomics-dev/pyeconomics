# Get outputs into Excel

Excel reads pyeconomics in two ways: an XLSX export, which you open like any
workbook, or Power Query over a REST download, which you refresh. To run models
inside the workbook itself, see {doc}`xlwings-lite`.

The Power Query below is a recipe the test suite does not run. The Python and
shell steps around it do run.

## An XLSX export

The command line writes a workbook directly, with no extra to install:

```console
$ pyeconomics models run foundations.time_value --calculation present_value --rate 0.05 --periods 10 --future-value 100 --format xlsx --out present-value.xlsx
```

From Python, `export` writes the same file:

```python
>>> import pyeconomics
>>> from pyeconomics.exports import export
>>> result = pyeconomics.run(
...     "foundations.time_value",
...     calculation="present_value",
...     rate=0.05,
...     periods=10,
...     future_value=100,
... )
>>> export(result, "xlsx", "from-python.xlsx")
```

The workbook has two sheets. `data` holds one row per run, with a column per
input and output. `manifest` says how the result was produced:

```python
>>> from openpyxl import load_workbook
>>> book = load_workbook("from-python.xlsx")
>>> book.sheetnames
['data', 'manifest']
>>> book["data"]["A1"].value
'inputs.calculation'
>>> book.close()
```

A number is a number, not text, so a formula can use it. Each text cell that a
spreadsheet would run as a formula is written with a leading `'`, so a file can
never run anything when you open it ({doc}`/exports`).

## The manifest sheet

When the data comes from a source, the `manifest` sheet lists its attributions
and notices first, then the manifest's fields and each data record. Those lines
are part of the data's terms, so keep the sheet with the data, and show them
wherever you copy the numbers:

```python
>>> import datetime as dt
>>> from pyeconomics import data
>>> found = data.get(
...     "us.treasury.nominal_10y",
...     start=dt.date(2025, 1, 1),
...     end=dt.date(2025, 1, 31),
... )
>>> export(found, "xlsx", "yields.xlsx")
>>> book = load_workbook("yields.xlsx")
>>> shown = [cell.value for row in book["manifest"].iter_rows() for cell in row]
>>> "Source: U.S. Department of the Treasury." in shown
True
>>> book.close()
```

This output comes from a recorded response of Treasury's own file; Treasury data
is `hosted-safe`.

## Power Query over a REST download

Power Query fetches a URL, so a refresh runs the model again, or reads the series
again, with no file to pass around. Start the server on the same machine
({doc}`/tutorials/rest-api`), and check the download first:

```console
$ curl "http://127.0.0.1:8000/v1/series/us.treasury.nominal_10y?start=2025-01-01&end=2025-01-31&format=csv"
# attribution: Source: U.S. Department of the Treasury.
"date","value"
```

In Excel, choose **Data > Get Data > From Other Sources > Blank Query**, open the
**Advanced Editor** and paste this. The CSV starts with a block of `#` lines that
has fewer columns than the table, so the query takes those lines out first:

```text
let
    Url = "http://127.0.0.1:8000/v1/series/us.treasury.nominal_10y?start=2025-01-01&end=2025-01-31&format=csv",
    Lines = Lines.FromBinary(Web.Contents(Url)),
    Rows = List.Select(Lines, each not Text.StartsWith(_, "#")),
    Data = Table.PromoteHeaders(Csv.Document(Text.Combine(Rows, "#(lf)"))),
    Typed = Table.TransformColumnTypes(
        Data,
        {{"date", type date}, {"value", type number}},
        "en-US"
    )
in
    Typed
```

`Csv.Document` reads every value as text, so the last step sets the types. Its
`"en-US"` reads a decimal point as one, whatever your own locale. The first time
it runs, Excel asks how to connect: choose **Anonymous**, because the local API
has no login.

Keep the `#` lines too. A second query can load them into a sheet beside the
table, so the attribution stays with the data:

```text
let
    Url = "http://127.0.0.1:8000/v1/series/us.treasury.nominal_10y?start=2025-01-01&end=2025-01-31&format=csv",
    Lines = Lines.FromBinary(Web.Contents(Url)),
    Notices = List.Select(Lines, each Text.StartsWith(_, "#"))
in
    Table.FromList(Notices, Splitter.SplitByNothing(), {"Notice"})
```

The same two steps can be checked from Python, which is what the query relies on:

```python
>>> from pyeconomics.exports import export_bytes
>>> lines = export_bytes(found, "csv").decode().splitlines()
>>> rows = [line for line in lines if not line.startswith("#")]
>>> rows[0]
'"date","value"'
>>> len(rows) - 1
21
>>> any(line == "# attribution: Source: U.S. Department of the Treasury." for line in lines)
True
```

A model run works the same way: its URL is the `GET` run with `&format=csv`
({doc}`/tutorials/rest-api`), and its columns are `inputs.<field>`,
`outputs.<field>` and `result_sha256`. Name the columns you need in the query's
last step.
