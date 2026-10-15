# The cache and offline mode

pyeconomics keeps what a source's terms let it keep, for as long as is useful, and
nothing else. A fetch from a source that allows storage is cached on your machine
and served from the cache until it goes stale; a source that forbids storage, FRED
and ALFRED among them, is fetched live every time and never written to disk, with
no setting that changes that. [ADR-0011](https://github.com/pyeconomics-dev/pyeconomics/blob/main/docs/adr/0011-data-platform.md)
decision 14 and ADR-0005 rule 4 are the rules; this page is how they behave.

## What is cached, and what never is

| Data | Cached? |
|------|---------|
| A source whose terms allow storage | Yes, for its time-to-live |
| A source whose terms forbid storage (`CachePolicy.FORBIDDEN`) | **Never.** No read, no write, no file |
| One series a source marks restricted, in a source that otherwise allows storage | Never; the series carries its own terms |
| `user-supplied` data | Never: processed in memory for one run |
| A query with a field named like a credential | Never |

The database is one SQLite file, `cache.sqlite3`, in the cache directory:
`PYECONOMICS_CACHE_DIR`, the `cache_dir` setting, or your user cache directory
(`~/.cache/pyeconomics` on Linux, `~/Library/Caches/pyeconomics` on macOS,
`%LOCALAPPDATA%\pyeconomics\Cache` on Windows). It is created on the first write,
never when pyeconomics is imported and never inside a repository, with
permissions for your user only: mode `0600` on Linux and macOS, and on Windows the
permissions of its directory, which under your profile are yours alone (if you
point `cache_dir` elsewhere on Windows, protect that directory yourself). It
holds canonical JSON, never a pickle, and it never holds a key.

```python
>>> from pyeconomics.data import cache
>>> cache.info().exists, cache.info().entry_count
(False, 0)
>>> cache.entries(), cache.clear()
((), 0)
```

## How long an entry lives

Each provider declares a time-to-live for its open data: one hour unless it says
otherwise (`ProviderInfo.ttl_seconds`). You can override it per provider, in
seconds, with `PYECONOMICS_TTL_<PROVIDER>` or the `[ttl]` table of
`pyeconomics.toml`; `0` turns that provider's cache off. An override applies to
entries stored after it.

A **closed past vintage** never expires. A request `as_of` a date more than a
day in the past asks for data a source will not rewrite, so its entry stays
until the size cap evicts it. `latest`, `first_release`, `all` and a recent
`as_of` are open: they go stale after the time-to-live and are fetched again.

The cache keeps at most 1 GiB of payload. Beyond that it removes the least
recently used entries first.

## Offline mode

```python
>>> from pyeconomics.data import configure
>>> configure(offline=True).offline
True
```

`configure(offline=True)` or `PYECONOMICS_OFFLINE=1` serves cached entries only,
whatever their age, and sends no request at all:

- Every record that came this way says so: `served_offline` is true, the warning
  code `served_offline` is on it, and its retrieval time is when the data was
  originally fetched, not when the cache answered.
- A fetch the cache cannot answer raises `OfflineError`, naming the provider and
  the series. For a source that forbids storage the message says why it can never
  be served offline.
- `search`, `describe` and `vintages` are not cached, so they raise
  `OfflineError` too.

## A bad entry is a miss

Every entry is checked when it is read: its SHA-256 must match, its payload must
validate back into a series or table of the right provider, and its terms must
still allow storage. An entry that fails is deleted, `cache_entry_discarded` is
reported as a warning and on the record, and the data is fetched again.

A database written by a newer pyeconomics is not touched: it is reported once,
and caching is off for the process. A file that is not a pyeconomics cache is
reported once and left alone. A locked or unwritable cache costs the cache, never
the fetch. Where `sqlite3` is missing, as in a Pyodide build without its package,
caching is off.

## Inspecting and clearing it

`pyeconomics.data.cache` has four functions, none of which creates anything or
returns a payload:

| Function | Returns |
|----------|---------|
| `info()` | The path, size, entry count, schema version and size cap |
| `entries(provider=None)` | Each entry's key, retrieval and expiry times, licence and size |
| `clear(provider=None)` | Deletes a provider's entries, or all of them; returns how many |
| `path()` | The database file's path |

`pyeconomics cache ls` and `pyeconomics cache clear` will wrap them in Phase 4.

## Reading where a result came from

`DataProvider.fetch` returns the frame. `fetch_with_origin` returns a `Fetched`: the
frame, an `Origin` (whether the cache or offline mode served it) and the vintage,
and `Fetched.source()` turns them into the `DataSource` record a manifest carries:

```text
fetched = provider.fetch_with_origin(query)
fetched.origin.cache_hit        # True when the cache answered
fetched.source().retrieved_at   # when the data was originally fetched
```

Within one call a repeat fetch can be served from memory with `cache.memo()`.
That is not storage: the memo never leaves the process and ends with its block,
which is how a bind can read one series twice without asking a source twice, even
a source that forbids storage.
