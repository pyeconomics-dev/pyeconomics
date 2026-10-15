# src/pyeconomics/data/cache/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The licence-aware cache and offline mode (ADR-0011 decision 14, ADR-0005 rule 4).

A fetch from a source whose terms allow storage is cached in one SQLite file in
the cache directory (``PYECONOMICS_CACHE_DIR``, else the user's cache directory)
and served from it within the provider's time-to-live; a closed past vintage is
kept until the size cap evicts it. A source, or a series, whose terms forbid
storage has **no cache path at all**: nothing is read, written or created, and
there is no opt-in. FRED and ALFRED are among them. The database is created on
the first write, never at import, with user-only permissions, and holds
canonical JSON, never a pickle; an entry that fails its SHA-256 or does not
validate back into a frame is deleted, reported as ``cache_entry_discarded`` and
fetched again.

**Offline mode** (``configure(offline=True)`` or ``PYECONOMICS_OFFLINE=1``)
serves cached entries only, whatever their age, sends no request and marks the
record ``served_offline``. A miss raises
:class:`~pyeconomics.data.errors.OfflineError`, which says why a no-storage
source can never be served offline.

The functions people call are :func:`info`, :func:`entries`, :func:`clear` and
:func:`path`; Phase 4's ``pyeconomics cache`` commands wrap them. None returns a
payload. The functions :func:`lookup` and :func:`save` are the data layer's own
seam: :meth:`~pyeconomics.data.providers.base.DataProvider.fetch_with_origin`
calls them, and so does nothing else. :func:`memo` is the one in-process
exception for a source that may not be stored: within its ``with`` block a
repeated fetch is served from memory, which is not storage because it never
outlives the block.

This package reads the clock, the settings and the file system; its
:mod:`~pyeconomics.data.cache.policy` module is pure.

Examples
--------
>>> from pyeconomics.data import cache
>>> cache.info().entry_count, cache.entries(), cache.clear()
(0, (), 0)
>>> cache.path().name
'cache.sqlite3'
"""

from __future__ import annotations

import contextlib
import contextvars
import datetime as dt
import hashlib
import logging
import threading
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core import _fields as f
from pyeconomics.core.errors import PyeconomicsError
from pyeconomics.data import modes
from pyeconomics.data.cache.policy import (
    CLOSED_AFTER,
    DEFAULT_TTL_SECONDS,
    DISCARDED_WARNING,
    OFFLINE_WARNING,
    CacheKey,
    Fetched,
    Origin,
    expiry,
    is_closed,
    may_store,
    offline_message,
)
from pyeconomics.data.cache.store import (
    DEFAULT_MAX_BYTES,
    FILE_NAME,
    SCHEMA_VERSION,
    BadEntryError,
    EntryRow,
    NewerSchemaError,
    SqliteMissingError,
    Store,
    StoreBusyError,
    StoreCorruptError,
    StoreError,
    Summary,
)
from pyeconomics.data.config import cache_dir, settings
from pyeconomics.data.errors import DataError, DataWarning, OfflineError
from pyeconomics.data.types import Series, Table

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from pyeconomics.data.providers.base import ProviderInfo, Query

__all__ = [
    "CLOSED_AFTER",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_TTL_SECONDS",
    "DISCARDED_WARNING",
    "FILE_NAME",
    "OFFLINE_WARNING",
    "SCHEMA_VERSION",
    "CacheEntry",
    "CacheInfo",
    "CacheKey",
    "Fetched",
    "Lookup",
    "Origin",
    "bypass",
    "clear",
    "entries",
    "expiry",
    "info",
    "is_closed",
    "lookup",
    "may_store",
    "memo",
    "override",
    "path",
    "reset",
    "save",
]

_LOG: Final = logging.getLogger("pyeconomics.data.cache")
_PACKAGE_DIR: Final = str(Path(__file__).parents[2])
_LOCK: Final = threading.Lock()
_STATE: Final[dict[str, Any]] = {"disabled": None, "noticed": set()}
_OVERRIDES: Final[dict[str, Any]] = {}
_BYPASS: Final[contextvars.ContextVar[bool]] = contextvars.ContextVar(
    "pyeconomics_cache_bypass", default=False
)
_MEMO: Final[contextvars.ContextVar[dict[CacheKey, Fetched] | None]] = (
    contextvars.ContextVar("pyeconomics_cache_memo", default=None)
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CacheInfo:
    """What the cache holds, without any payload."""

    path: Path
    """The database file (which may not exist yet)."""
    exists: bool
    usable: bool
    """``False`` for a file a newer pyeconomics wrote, or one that is not a cache."""
    size_bytes: int
    """The database and its write-ahead files on disk."""
    payload_bytes: int
    """The payloads the entries hold; the size cap applies to this."""
    entry_count: int
    schema_version: int | None
    """The schema the file uses; ``None`` when it does not exist or is unreadable."""
    max_bytes: int
    """The size cap on the payloads."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CacheEntry:
    """One cached entry: its key, times and size. It holds no payload."""

    provider: str
    dataset: str
    series: str
    query: str
    """The canonical JSON of the query, without credentials."""
    vintage: str
    retrieved_at: dt.datetime | None
    """When the source was asked, in UTC; ``None`` if the entry is malformed."""
    expires_at: dt.datetime | None
    """When the entry stops being fresh; ``None`` for a closed past vintage."""
    licence: str
    size_bytes: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Lookup:
    """The answer to a cache lookup, and what :func:`save` needs afterwards."""

    key: CacheKey | None
    """The entry's key; ``None`` for a query that must not be cached."""
    fetched: Fetched | None = None
    """The cached (or memoized) result, or ``None`` for a miss."""
    warnings: tuple[str, ...] = ()
    """Warning codes the lookup raised, such as ``cache_entry_discarded``."""


# --- state ----------------------------------------------------------------------


def reset() -> None:
    """Forget the process's cache state: what was disabled, reported and overridden.

    The test suite calls this around every test.
    """
    with _LOCK:
        _STATE["disabled"] = None
        _STATE["noticed"] = set()
        _OVERRIDES.clear()


@contextlib.contextmanager
def override(
    *, clock: Callable[[], dt.datetime] | None = None, max_bytes: int | None = None
) -> Generator[None]:
    """Replace the clock or the size cap for the ``with`` block.

    A tool for tests and for Phase 4's cache commands, not a setting: the clock
    must return an aware time, and ``max_bytes`` is the cap on payload bytes.
    """
    with _LOCK:
        saved = dict(_OVERRIDES)
        if clock is not None:
            _OVERRIDES["clock"] = clock
        if max_bytes is not None:
            _OVERRIDES["max_bytes"] = max_bytes
    try:
        yield
    finally:
        with _LOCK:
            _OVERRIDES.clear()
            _OVERRIDES.update(saved)


@contextlib.contextmanager
def memo() -> Generator[None]:
    """Serve repeated fetches from memory within the ``with`` block.

    This is how one bind or one fetch call avoids asking a source twice for the
    same series without storing what its terms forbid storing: the memo lives in
    the process, is never shared between blocks and is gone when the block
    ends. It never touches the database.
    """
    if _MEMO.get() is not None:
        yield
        return
    token = _MEMO.set({})
    try:
        yield
    finally:
        _MEMO.reset(token)


@contextlib.contextmanager
def bypass() -> Generator[None]:
    """Neither read nor write the cache within the ``with`` block (online only).

    The recorder of provider cassettes uses it, because a fetch it records must
    reach the source whatever the cache holds. It changes nothing about offline
    mode, which sends no request.
    """
    token = _BYPASS.set(True)
    try:
        yield
    finally:
        _BYPASS.reset(token)


def _now() -> dt.datetime:
    with _LOCK:
        clock = _OVERRIDES.get("clock")
    moment: dt.datetime = clock() if clock is not None else dt.datetime.now(dt.UTC)
    return moment.astimezone(dt.UTC)


def _max_bytes() -> int:
    with _LOCK:
        cap = _OVERRIDES.get("max_bytes")
    return DEFAULT_MAX_BYTES if cap is None else int(cap)


def path() -> Path:
    """Return the database file's path. Nothing is created.

    It is ``cache.sqlite3`` in the cache directory: ``PYECONOMICS_CACHE_DIR``,
    the ``cache_dir`` setting, else the user's cache directory.
    """
    return cache_dir() / FILE_NAME


def _store() -> Store:
    return Store(path(), max_bytes=_max_bytes())


def _warn(code: str, message: str) -> None:
    warnings.warn(
        DataWarning(code, message), stacklevel=2, skip_file_prefixes=(_PACKAGE_DIR,)
    )


def _disable(code: str, message: str, *, quiet: bool = False) -> None:
    """Turn the cache off for the process, reporting it once."""
    with _LOCK:
        first = code not in _STATE["noticed"]
        _STATE["noticed"].add(code)
        _STATE["disabled"] = message
    if first:
        if quiet:
            _LOG.debug("caching is off: %s", message)
        else:
            _warn(code, f"caching is off for this process: {message}")


def _disabled() -> str | None:
    with _LOCK:
        reason = _STATE["disabled"]
    return reason if isinstance(reason, str) else None


def _handle(error: StoreError) -> None:
    """Act on a store failure: report, disable, or let a busy database pass."""
    if isinstance(error, SqliteMissingError):
        _disable("cache_sqlite_missing", "sqlite3 is not available", quiet=True)
    elif isinstance(error, NewerSchemaError):
        _disable(
            "cache_schema_newer",
            f"a newer pyeconomics wrote the cache (schema {error.version}) and "
            "this version leaves it untouched",
        )
    elif isinstance(error, StoreCorruptError):
        _disable(
            "cache_unreadable",
            "the cache file is not a usable pyeconomics cache; delete it to start "
            "again",
        )
    else:
        _LOG.debug("the cache database was busy or unavailable: skipped")


# --- the seam DataProvider.fetch_with_origin calls -------------------------------


def _ttl(info: ProviderInfo) -> int:
    """Return the provider's time-to-live, or the user's override, in seconds."""
    return settings().ttl.get(info.id, info.ttl_seconds)


def _storable(info: ProviderInfo) -> bool:
    return may_store(info.terms) and _ttl(info) > 0


def lookup(info: ProviderInfo, query: Query) -> Lookup:
    """Ask the cache for a fetch, before any request is built.

    Online, a fresh entry is a hit and anything else a miss; a source whose
    terms forbid storage is always a miss, without touching the file system. In
    offline mode only the cache answers, whatever an entry's age, and a miss
    raises :class:`~pyeconomics.data.errors.OfflineError`.

    Raises
    ------
    OfflineError
        In offline mode, when nothing cached answers.
    LicenceError
        In hosted mode, for a cached series the mode may not serve.
    """
    key = CacheKey.of(info.id, query)
    if settings().offline:
        return _offline(info, query, key)
    if key is None or _BYPASS.get():
        return Lookup(key=None)
    held = _MEMO.get()
    if held is not None and key in held:
        return Lookup(key=key, fetched=held[key])
    if not _storable(info):
        return Lookup(key=key)
    fetched, raised = _read(info, key, fresh_only=True)
    return Lookup(key=key, fetched=fetched, warnings=raised)


def _offline(info: ProviderInfo, query: Query, key: CacheKey | None) -> Lookup:
    series = query.series
    if not may_store(info.terms):
        raise OfflineError(
            offline_message(info.id, series, forbidden=True), provider=info.id
        )
    if key is None:
        raise OfflineError(
            offline_message(
                info.id, series, forbidden=False, reason="the query cannot be cached"
            ),
            provider=info.id,
        )
    fetched, _ = _read(info, key, fresh_only=False)
    if fetched is None:
        raise OfflineError(
            offline_message(info.id, series, forbidden=False, reason=_disabled()),
            provider=info.id,
        )
    origin = Origin(cache_hit=True, served_offline=True, warnings=(OFFLINE_WARNING,))
    return Lookup(key=key, fetched=Fetched(fetched.frame, origin, key.vintage))


def _read(
    info: ProviderInfo, key: CacheKey, *, fresh_only: bool
) -> tuple[Fetched | None, tuple[str, ...]]:
    """Read and validate an entry; a bad one is deleted and reported."""
    row: EntryRow | None = None
    if _disabled() is None:
        try:
            row = _store().read(key)
        except BadEntryError:
            return None, _discard(key)
        except StoreError as error:
            _handle(error)
    if row is None:
        return None, ()
    frame = _decode(info, key, row)
    if frame is None:
        return None, _discard(key)
    if fresh_only and row.expires_at is not None and _now() >= row.expires_at:
        return None, ()
    modes.require_allowed(frame.meta.terms, provider=info.id)
    return Fetched(frame, Origin(cache_hit=True), key.vintage), ()


def _decode(info: ProviderInfo, key: CacheKey, row: EntryRow) -> Series | Table | None:
    """Return the frame an entry holds, or ``None`` if it cannot be trusted.

    The payload's SHA-256 must match, it must validate back into the kind of
    frame the row names, and the frame must belong to the key's provider, carry
    the stored retrieval time and licence and still be storable.
    """
    if hashlib.sha256(row.payload).hexdigest() != row.sha256:
        return None
    frame: Series | Table
    try:
        if row.kind == "series":
            frame = Series.from_json(row.payload)
        elif row.kind == "table":
            frame = Table.from_json(row.payload)
        else:
            return None
    except (PyeconomicsError, ValueError, TypeError, RecursionError):
        return None
    meta = frame.meta
    if (
        meta.provider != key.provider
        or meta.provider != info.id
        or meta.retrieved_at != row.retrieved_at
        or meta.terms.licence.value != row.licence
        or not may_store(meta.terms)
    ):
        return None
    return frame


def _discard(key: CacheKey) -> tuple[str, ...]:
    """Delete an entry that failed its checks and say so."""
    try:
        _store().discard(key)
    except StoreError as error:
        _handle(error)
    _warn(
        DISCARDED_WARNING,
        f"a cached entry of {key.provider} failed its integrity checks and was "
        "deleted; the data is fetched again",
    )
    return (DISCARDED_WARNING,)


def save(info: ProviderInfo, found: Lookup, fetched: Fetched) -> None:
    """Keep a fresh fetch: in the memo if one is open, and in the store if allowed.

    The licence gate runs first, on the provider's terms and on the frame's own,
    and a source that forbids storage returns before the file system is touched.
    """
    key = found.key
    if key is None:
        return
    held = _MEMO.get()
    if held is not None:
        held[key] = fetched
    frame = fetched.frame
    retrieved = frame.meta.retrieved_at
    if (
        not _storable(info)
        or not may_store(frame.meta.terms)
        or retrieved is None
        or _disabled() is not None
    ):
        return
    try:
        stored = _store().write(
            key,
            kind="series" if isinstance(frame, Series) else "table",
            payload=frame.canonical_json(),
            retrieved_at=retrieved,
            expires_at=expiry(key.vintage, now=_now(), ttl=_ttl(info)),
            licence=frame.meta.terms.licence.value,
        )
    except StoreError as error:
        _handle(error)
        return
    if not stored:
        _LOG.debug("a result larger than the size cap was not cached")


# --- the API people call ---------------------------------------------------------


def _unusable(summary: Summary) -> DataError:
    if summary.schema_version is not None:
        msg = (
            f"the cache uses schema {summary.schema_version}, written by a newer "
            "pyeconomics; this version leaves it untouched"
        )
    else:
        msg = (
            "the cache file is not a usable pyeconomics cache; delete the file "
            "pyeconomics.data.cache.path() names to start again"
        )
    return DataError(msg)


def _checked(provider: str | None) -> str | None:
    return None if provider is None else f.identifier(provider, "provider")


def info() -> CacheInfo:
    """Describe the cache: its path, size, entry count and schema version.

    Nothing is created. A cache that does not exist yet has no entries.
    """
    where = path()
    try:
        summary = Store(where, max_bytes=_max_bytes()).summary()
    except SqliteMissingError:
        summary = Summary(
            exists=False,
            usable=True,
            size_bytes=0,
            payload_bytes=0,
            entry_count=0,
            schema_version=None,
        )
    return CacheInfo(
        path=where,
        exists=summary.exists,
        usable=summary.usable,
        size_bytes=summary.size_bytes,
        payload_bytes=summary.payload_bytes,
        entry_count=summary.entry_count,
        schema_version=summary.schema_version,
        max_bytes=_max_bytes(),
    )


def entries(provider: str | None = None) -> tuple[CacheEntry, ...]:
    """List the cached entries, optionally of one provider: keys, times and sizes.

    No payload is returned.

    Raises
    ------
    DataError
        If the cache was written by a newer pyeconomics or is not a cache.
    """
    wanted = _checked(provider)
    try:
        rows = Store(path(), max_bytes=_max_bytes()).listing(wanted)
    except SqliteMissingError:
        return ()
    except (NewerSchemaError, StoreCorruptError):
        raise _unusable(_summary()) from None
    except StoreBusyError:
        msg = "the cache is busy; try again"
        raise DataError(msg) from None
    return tuple(
        CacheEntry(
            provider=row.key.provider,
            dataset=row.key.dataset,
            series=row.key.series,
            query=row.key.query,
            vintage=row.key.vintage,
            retrieved_at=row.retrieved_at,
            expires_at=row.expires_at,
            licence=row.licence,
            size_bytes=row.size,
        )
        for row in rows
    )


def _summary() -> Summary:
    return Store(path(), max_bytes=_max_bytes()).summary()


def clear(provider: str | None = None) -> int:
    """Delete the cached entries of one provider, or all of them; return how many.

    Nothing is created, and a cache that does not exist has nothing to clear.

    Raises
    ------
    DataError
        If the cache was written by a newer pyeconomics or is not a cache.
    """
    wanted = _checked(provider)
    try:
        return Store(path(), max_bytes=_max_bytes()).clear(wanted)
    except SqliteMissingError:
        return 0
    except (NewerSchemaError, StoreCorruptError):
        raise _unusable(_summary()) from None
    except StoreBusyError:
        msg = "the cache is busy; try again"
        raise DataError(msg) from None
