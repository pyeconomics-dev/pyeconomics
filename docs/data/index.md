# Data sources and keys

pyeconomics reads economic and market data from free public sources. This guide
explains how to ask for data, what you get back, which sources are open to which
uses, how the library and hosted modes differ, and where keys, attribution and
the cache fit in. The reference pages it links to are generated from the same
metadata the code reads, so they cannot disagree with it.

## Two ways to ask

Everything goes through `pyeconomics.data.get`. You name either a **concept** or
a **provider series**.

A *concept* is one quantity under one id, such as `us.unemployment.rate` or
`us.inflation.pce_core.yoy`. It has a definition, a fixed unit, a fixed
frequency and a fixed seasonal adjustment, and a list of sources that can answer
it in order of preference. You do not choose the source; the resolver does,
from your mode, your keys and the extras you have installed. Ids have three or
four dotted parts: an economy (`us`, `gb`, `ca`, or `ea` for the euro area) or a
dataset family (`factors`, `portfolios`, `pwt`), then the topic and the measure.

A *provider series* is a series you name yourself on a source you name: the
provider's id, a colon, and the provider's own key, as in `fred:UNRATE` or
`bls:LNS14000000`. It goes straight to that provider, which applies the same
licence, key and mode checks.

```pycon
>>> from pyeconomics import data
>>> import datetime as dt
>>> found = data.get("us.inflation.pce_core.yoy", start=dt.date(2024, 1, 1))
>>> found.frame.meta.unit.kind.value, found.frame.meta.frequency.value
('rate', 'monthly')
>>> found.source.provider, found.source.transforms, found.source.fallback_chain
('bea', ('yoy',), ('bea',))
>>> series = data.get("fred:UNRATE", start=dt.date(2024, 1, 1)).frame
```

You can search and look before you fetch. These run without a network, because
concepts are plain metadata:

```python
>>> from pyeconomics import data
>>> data.search("core inflation", 2, providers=()).hits[0].id
'us.inflation.pce_core.yoy'
>>> info = data.describe("us.inflation.pce_core.yoy")
>>> info.concept.title
'Core PCE inflation, year over year'
>>> [(c.provider, c.tier.value) for c in info.candidates]
[('bea', 'originator'), ('fred', 'aggregator')]
>>> len(data.catalog.ids()) > 100
True
```

Searching with the default `providers=None` also asks every source that can
search, which needs the network; `search` lists any it could not ask and why.

## What you get back

`get` returns a `Resolved`: the data as a `Series` or a `Table`, and the records
of where it came from.

- `frame` holds dates (each period's last day), values (`None` where the source
  has no value, never a filled one), the unit, the frequency and the terms the
  data came under. Rates and returns are decimals everywhere: 0.042, not 4.2.
- `sources` holds one `DataSource` per source read, naming the concept, the
  provider and series, the vintage, the window, the transforms applied, when the
  data was retrieved, the licence class, the attribution and notice, the
  providers the resolver tried and why it passed over the others.
- `skipped` lists each candidate passed over, with a reason such as
  `key_missing`, `extra_missing`, `vintage_unsupported` or `licence_refused`.

A concept's answer is exactly its definition. The resolver fails over only
between candidates that deliver the same thing, and checks each answer's
frequency, seasonal adjustment and unit against the concept before it accepts
one. `strict=True` tries only the first candidate and never falls back.

## Transforms, windows and alignment

A concept lists the transforms that make a source's series match its
definition: year-over-year change, percent change, difference, logarithm,
frequency conversion and the ratio or sum of two concepts. The vocabulary is in
`pyeconomics.core.transforms`; each transform is a named, pure function whose
parameters are written into the record, as `convert(to=quarterly,method=mean)`.

Nothing here fills a gap. A value that cannot be computed from the observations
that exist is missing. Aggregating to a lower frequency needs the period
complete, and going to a higher one with `period_end` leaves the periods between
missing. Aligning a quarterly series to monthly dates is an explicit choice: the
last observation on or before each date, with a limit on how old it may be. If
the data cannot satisfy the rule, you get an error that says why.

A request for a window (`start`, `end`) asks the source for enough earlier
history that a year-over-year change at the first date has its year behind it,
then cuts the result to your window. The Treasury's curve files are served by
date range, so concepts built on them need both dates.

## Licence classes

Every source declares a class, read from its own terms, and the class decides
where its data may flow.

| Class | Meaning | Hosted mode |
|-------|---------|-------------|
| `hosted-safe` | The terms let a third-party service display the data, with attribution. | Served |
| `library-only` | Personal-use, non-commercial, no-caching or scraped terms. The data stays on your machine, under your own key. | Refused |
| `byok` | Your own paid subscription (arrives with the premium sources). | Refused |
| `premium-local` | Licensed to one machine or seat (arrives with the premium sources). | Refused |
| `user-supplied` | Your own files. | Served |

A series can be marked more strictly than its source: FRED tags each series'
copyright, the World Bank labels each indicator's licence, Eurostat lists
exceptions. The resolver honours the series' own terms in every resolution, and
a series whose terms forbid storage is never written to disk.

## Library mode and hosted mode

**Library mode** is the default: pyeconomics runs on your machine under your own
keys and your acceptance of each source's terms, and any source may answer.
**Hosted mode** (`PYECONOMICS_MODE=hosted` or `configure(mode="hosted")`) is for
a public service: it serves only `hosted-safe` and `user-supplied` data, so it
resolves a concept's originator or refuses. It never falls back to an aggregator
such as FRED, and it checks the class before any request is sent, again in the
provider, and again on the series' own terms.

When hosted mode finds no source it may serve, it raises a `LicenceError` that
names the classes it found, instead of quietly reading a library-only source:

```python
>>> from pyeconomics import data
>>> try:
...     data.get("us.inflation.pce_trimmed_mean.yoy", mode=data.Mode.HOSTED)
... except data.LicenceError as error:
...     print("refused:", "library-only" in str(error))
refused: True
```

## Attribution and required notices

A source's attribution and any notice it requires travel with its data, in the
frame's terms and in each `DataSource`. Show them wherever the data appears.
BLS asks for a statement that it cannot vouch for derived analyses and for the
date the data was accessed; the New York Fed asks for its notice on its rates;
FRED requires its notice on every application; the Penn World Table asks for a
citation. The [sources summary](../reference/sources.md) lists each provider's
class, key and notice, and each provider's own page has the rest.

## Keys

A few sources ask for a free key: FRED, BEA, Census and (optionally) BLS and
OpenFIGI. A key is read only through the key chain, held as a `Secret`, and
never logged, cached or exported. Where to register and how to set each one is
in [Keys and configuration](keys.md). A candidate whose required key is missing
is skipped and recorded; if keys were all that was missing, the error names the
variable to set.

## The cache and offline mode

Data a source's terms allow is cached on your machine, with a time-to-live per
source; data its terms forbid storing, FRED's among it, is fetched fresh in
every process and never written to disk. Offline mode serves the cache only and
raises `OfflineError` when it has nothing, which the resolver records and, for a
concept, tries the next candidate on. See [The cache](cache.md).

## Vintages and real-time data

Historical analysis should see the data as it was known. `as_of=` reads a source
that keeps vintages (FRED's ALFRED, the Philadelphia Fed's real-time data and
SPF, CBO's reports) as published on a date; a source that keeps none cannot
honour it, so the resolver skips it and records why. Revised data is a separate
choice, and a run that uses it says so.

## Reference

The concept pages list each concept's definition, its unit, and its candidates
for library mode and for hosted mode. The provider pages give each source's terms,
attribution, key setup, limits and hosts. Writing a provider is covered in
[Writing a provider](writing-a-provider.md).

```{toctree}
:maxdepth: 1
:caption: Sources

../reference/sources
```

```{toctree}
:maxdepth: 1
:caption: Concepts

../reference/concepts/index
```

```{toctree}
:maxdepth: 1
:glob:
:caption: Provider pages

../reference/providers/*
```
