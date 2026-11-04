# Data and keys

The {doc}`last lesson <first-model>` typed every number by hand. This one reads
a real series, then looks at the rules around it: which source it came from,
what that source's licence allows, how a key is stored, and what happens when
you work offline. It takes about fifteen minutes.

The output below comes from recorded responses of the US Treasury's own files,
so these pages can be checked without a network. On your machine the same calls
read the source live.

## A series that needs no key

Name what you want by its *concept*, one quantity under one permanent id, and
give a window. The US Treasury publishes its yield curve openly, so no key is
needed:

```python
>>> import datetime as dt
>>> from pyeconomics import data
>>> found = data.get(
...     "us.treasury.nominal_10y",
...     start=dt.date(2025, 1, 1),
...     end=dt.date(2025, 1, 31),
... )
>>> found.frame.index[0], round(found.frame.values[0], 4)
(datetime.date(2025, 1, 2), 0.0457)
>>> found.frame.meta.unit.kind.value
'rate'
```

The ten-year yield on 2 January 2025 was 4.57%. Rates are decimals everywhere
in pyeconomics, so it reads `0.0457`, and a date is its period's last day.

## Where the data came from

`found.source` is the record of that fetch. It travels with the data into any
result or export, and you should keep it there:

```python
>>> found = data.get(
...     "us.treasury.nominal_10y",
...     start=dt.date(2025, 1, 1),
...     end=dt.date(2025, 1, 31),
... )
>>> found.source.provider, found.source.series_id
('treasury', 'par_nominal:BC_10YEAR')
>>> found.source.licence.value
'hosted-safe'
>>> found.source.attribution
'Source: U.S. Department of the Treasury.'
>>> found.source.terms_url
'https://home.treasury.gov/footer/privacy-act'
```

Show the attribution wherever the data appears. The resolver chose Treasury
because it is the concept's *originator*, listed first among its candidates:

```python
>>> info = data.describe("us.treasury.nominal_10y")
>>> [(c.provider, c.tier.value) for c in info.candidates]
[('treasury', 'originator'), ('fred', 'aggregator')]
```

## Licence classes

Every source declares a class, read from its own terms, and the class decides
where its data may flow. These are the three you will meet first; {doc}`/data/index`
lists the two for paid sources:

| Class | Meaning | Hosted service |
|-------|---------|----------------|
| `hosted-safe` | The terms let a third-party service show the data, with attribution | Served |
| `library-only` | Personal-use, non-commercial, no-caching or scraped terms: the data stays on your machine, under your own key | Refused |
| `user-supplied` | Your own files | Served |

Treasury is `hosted-safe`. FRED is `library-only`, so you may read it with your
own key on your own machine, while a hosted service refuses it before any
request is sent:

```python
>>> try:
...     data.get("fred:UNRATE", mode=data.Mode.HOSTED)
... except data.LicenceError as error:
...     print("refused:", "library-only" in str(error))
refused: True
```

`pyeconomics data sources` lists every source with its class, and
{doc}`/reference/sources` has each one's terms and required notice.

## Setting a key

FRED, BEA and the Census Bureau ask for a free key. A key is yours: pyeconomics
reads it only through its key chain, and never prints, logs, caches or exports
it. Core PCE inflation comes from BEA, or from FRED after it, and both want a
key. Without one the resolver stops before any request, and the error names
what to set, never a value:

```python
>>> data.has_key("fred")
False
>>> try:
...     data.get("us.inflation.pce_core.yoy")
... except data.CredentialError as error:
...     print("BEA_API_KEY" in str(error), "FRED_API_KEY" in str(error))
True True
```

Get a key from [the St. Louis Fed](https://fredaccount.stlouisfed.org/apikeys),
then store it in your operating system's keyring. The keyring needs an extra,
and `keys set` asks for the key with a hidden prompt, so it never reaches your
shell history or this screen:

```text
pip install --pre "pyeconomics[keyring]"
pyeconomics keys set fred
```

`keys list` shows where each key would be read from, and never the key. Before
you have stored one, FRED's source is `none`; afterwards it is `keyring`:

```console
$ pyeconomics keys list
Provider    Variable            Required  Source
fred        FRED_API_KEY        yes       none
```

{doc}`/data/keys` covers the other places a key can live, and what to do if one
leaks.

## The cache

A source whose terms allow storage is cached on your machine. The first fetch
above filled the cache, so asking again answers from there with no request sent,
and the record says so:

```python
>>> again = data.get(
...     "us.treasury.nominal_10y",
...     start=dt.date(2025, 1, 1),
...     end=dt.date(2025, 1, 31),
... )
>>> again.source.cache_hit
True
>>> again.frame.values == found.frame.values
True
>>> [entry.provider for entry in data.cache.entries()]
['treasury']
```

Data whose terms forbid storage, FRED's among it, is never written to disk: it
is fetched fresh in every process. `pyeconomics cache info` shows where the
cache lives, and {doc}`/data/cache` explains how long each source is kept.

## Working offline

Offline mode sends no request and serves the cache only. It is how you make a
script repeatable on a train, or prove it reads nothing new. Anything the cache
does not hold fails plainly, and never turns into a guess:

```python
>>> _ = data.configure(offline=True)
>>> kept = data.get(
...     "us.treasury.nominal_10y",
...     start=dt.date(2025, 1, 1),
...     end=dt.date(2025, 1, 31),
... )
>>> kept.source.served_offline
True
>>> try:
...     data.get(
...         "us.treasury.nominal_10y",
...         start=dt.date(2024, 1, 1),
...         end=dt.date(2024, 1, 31),
...     )
... except data.DataError as error:
...     print("no cached copy" in str(error))
True
>>> _ = data.configure(offline=False)
```

## Where next

You have read a source, seen its licence and its attribution, stored a key and
used the cache. {doc}`command-line` does the same from a shell, and
{doc}`/data/index` is the full guide to the data layer.
