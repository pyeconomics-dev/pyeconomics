# Read and transform a series

A *transform* turns a series into another before it reaches you: a change over
twelve months, a logarithm, a move from monthly to quarterly. The source is asked
for the history the transform needs, the result is cut to your window, and the
record of where the data came from lists the transform, so a file written from it
says what was done.

There are six: `pct_change`, `yoy`, `diff`, `lag`, `log` and `convert`. Every
surface takes the same text, and a table cannot be transformed this way.

## In Python

```python
>>> import datetime as dt
>>> from pyeconomics import data
>>> found = data.get(
...     "us.treasury.nominal_10y",
...     start=dt.date(2025, 1, 1),
...     end=dt.date(2025, 1, 31),
...     transform="log",
... )
>>> found.source.transforms
('log',)
>>> found.frame.meta.unit.text
'Natural log of Percent'
>>> found.source.licence.value, found.source.attribution
('hosted-safe', 'Source: U.S. Department of the Treasury.')
```

This output comes from a recorded response of Treasury's own file. Arguments go
in the text, as in `diff(periods=12)` or `convert(to=annual,method=mean)`.

## On the command line

`data get` takes the same text. A table prints the data's sources and attribution
below it:

```console
$ pyeconomics data get us.treasury.nominal_10y --start 2025-01-01 --end 2025-01-31 --transform log --format table
treasury  par_nominal:BC_10YEAR  latest   hosted-safe  yes
Source: U.S. Department of the Treasury.
```

This one reads live data from the Bureau of Labor Statistics, which needs no key,
so run it on your own machine:

```shell
$ pyeconomics data get us.unemployment.rate --start 2024-01-01 --transform "diff(periods=12)" --format csv
```

## Over REST and MCP

The series route takes `?transform=`, and every download carries the attribution:

```console
$ curl "http://127.0.0.1:8000/v1/series/us.treasury.nominal_10y?start=2025-01-01&end=2025-01-31&transform=log&format=csv"
# attribution: Source: U.S. Department of the Treasury.
"date","value"
```

MCP's `get_series` tool takes a `transform` argument with the same text. Data
whose terms keep it from a language model, FRED's among it, does not reach an
assistant, transformed or not ({doc}`/mcp`).

## In the data explorer

The site's `/data/` page lists every catalog concept, and each concept has a page
of its own. Pick your dates and a **Transform**, read the chart, then take the
same series as CSV, XLSX, Parquet or Arrow under **Download**. A chart draws its
source and its as-of date on itself, so a screenshot keeps them.

The public site serves the concepts its daily snapshot holds, which are those
whose originator allows a hosted service. For any other, the page gives the
command that reads it locally. The {doc}`local app <local-app>` offers every
concept.

## With your own data

A calculator that takes a list of values, such as a series of returns, offers
**Use my own data (CSV or XLSX)**. Choose a file, then say which column fills which
input.

Your browser reads the file, up to 5 MB. Only the values you choose are written
into the form, and only they travel, in the body of the run. The file, its name
and its other columns never leave the page, and a run on your values is never
cached. A formula counts only as the value the file saved, and links and macros
are ignored.
