# src/pyeconomics/data/cache/store.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The SQLite store behind the cache (ADR-0011 decision 14).

One database file in the cache directory, opened lazily: ``sqlite3`` is imported
when a store first opens a database, because it is a separate package in Pyodide,
and nothing is created until the first write. The file is created with user-only
permissions (``0600`` on POSIX, under the user profile on Windows), in WAL mode
with a busy timeout, so two processes can read and write at once.

``schema_version`` holds one row, the schema this code reads and writes
(:data:`SCHEMA_VERSION`); ``entries`` holds one row per
:class:`~pyeconomics.data.cache.policy.CacheKey`, with the payload (canonical
JSON, never a pickle), its SHA-256, the retrieval and expiry times and the licence
class. Every statement is parameterized: none is built by string formatting.

The store does no policy. It never decides whether a source may be cached and it
never parses a payload: the package asks :mod:`~pyeconomics.data.cache.policy`
first and validates what it reads. A least-recently-used eviction keeps the
payloads within ``max_bytes``; recency is a counter, not the clock.

Failures are :class:`StoreError`: the database is busy or cannot be opened right
now (:class:`StoreBusyError`, transient), it is not a pyeconomics cache or is
damaged (:class:`StoreCorruptError`), a newer pyeconomics wrote it
(:class:`NewerSchemaError`, which this code never modifies), or one entry's row is
malformed (:class:`BadEntryError`). A missing ``sqlite3`` is
:class:`SqliteMissingError`. No message holds a path.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Generator
    from pathlib import Path
    from types import ModuleType

    from pyeconomics.data.cache.policy import CacheKey

__all__ = [
    "BUSY_SECONDS",
    "DEFAULT_MAX_BYTES",
    "FILE_NAME",
    "SCHEMA_VERSION",
    "BadEntryError",
    "EntryRow",
    "Listing",
    "NewerSchemaError",
    "SqliteMissingError",
    "Store",
    "StoreBusyError",
    "StoreCorruptError",
    "StoreError",
    "Summary",
]

#: The schema this code reads and writes.
SCHEMA_VERSION: Final = 1
#: The database file's name inside the cache directory.
FILE_NAME: Final = "cache.sqlite3"
#: The default cap on the payloads kept: 1 GiB.
DEFAULT_MAX_BYTES: Final = 1024**3
#: How long a connection waits for another's lock before giving up.
BUSY_SECONDS: Final = 10.0

#: Whether files can be made private to their owner here (not on Windows, where the
#: user profile's permissions apply). A constant so a test can exercise both ways.
_POSIX: Final = os.name == "posix"
_OWNER_ONLY: Final = 0o600
_PRIVATE_DIRECTORY: Final = 0o700
_OTHERS: Final = 0o077

_CREATE_VERSION: Final = "CREATE TABLE schema_version (version INTEGER NOT NULL)"
_SET_VERSION: Final = "INSERT INTO schema_version (version) VALUES (?)"
_CREATE_ENTRIES: Final = """
CREATE TABLE entries (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,
    dataset TEXT NOT NULL,
    series TEXT NOT NULL,
    query TEXT NOT NULL,
    vintage TEXT NOT NULL,
    kind TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    expires_at TEXT,
    licence TEXT NOT NULL,
    payload BLOB NOT NULL,
    payload_sha256 TEXT NOT NULL,
    size INTEGER NOT NULL,
    used_seq INTEGER NOT NULL,
    UNIQUE (provider, dataset, series, query, vintage)
)
"""
_CREATE_INDEX: Final = "CREATE INDEX entries_used ON entries (used_seq)"
_SELECT: Final = """
SELECT id, kind, payload, payload_sha256, retrieved_at, expires_at, licence
FROM entries
WHERE provider = ? AND dataset = ? AND series = ? AND query = ? AND vintage = ?
"""
_TOUCH: Final = """
UPDATE entries
SET used_seq = (SELECT COALESCE(MAX(used_seq), 0) + 1 FROM entries)
WHERE id = ?
"""
_UPSERT: Final = """
INSERT INTO entries (
    provider, dataset, series, query, vintage, kind, retrieved_at, expires_at,
    licence, payload, payload_sha256, size, used_seq
)
VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
    (SELECT COALESCE(MAX(used_seq), 0) + 1 FROM entries)
)
ON CONFLICT (provider, dataset, series, query, vintage) DO UPDATE SET
    kind = excluded.kind,
    retrieved_at = excluded.retrieved_at,
    expires_at = excluded.expires_at,
    licence = excluded.licence,
    payload = excluded.payload,
    payload_sha256 = excluded.payload_sha256,
    size = excluded.size,
    used_seq = excluded.used_seq
"""
_DELETE_ONE: Final = """
DELETE FROM entries
WHERE provider = ? AND dataset = ? AND series = ? AND query = ? AND vintage = ?
"""
_DELETE_PROVIDER: Final = "DELETE FROM entries WHERE ? IS NULL OR provider = ?"
_TOTAL: Final = "SELECT COALESCE(SUM(size), 0), COUNT(*) FROM entries"
_BY_AGE: Final = "SELECT id, size FROM entries ORDER BY used_seq ASC"
_EVICT: Final = "DELETE FROM entries WHERE id = ?"
_LIST: Final = """
SELECT provider, dataset, series, query, vintage, retrieved_at, expires_at,
       licence, size
FROM entries
WHERE ? IS NULL OR provider = ?
ORDER BY provider, series, vintage, id
"""
_TABLES: Final = "SELECT name FROM sqlite_master WHERE type = 'table'"
_VERSION: Final = "SELECT MAX(version) FROM schema_version"


class StoreError(Exception):
    """Base class of the store's failures; the message holds no path."""


class SqliteMissingError(StoreError):
    """The ``sqlite3`` module is not available (Pyodide without its package)."""


class StoreBusyError(StoreError):
    """The database is locked, or cannot be opened or written right now."""


class StoreCorruptError(StoreError):
    """The file is not a pyeconomics cache, or is damaged."""


class NewerSchemaError(StoreError):
    """A newer pyeconomics wrote the database; this version never touches it."""

    def __init__(self, version: int) -> None:
        super().__init__(f"the database uses schema {version}, newer than this code")
        self.version = version


class BadEntryError(StoreError):
    """One entry's row is malformed (a column of the wrong type or a bad time)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class EntryRow:
    """One entry as stored: the payload and its checks, not yet validated."""

    kind: str
    payload: bytes
    sha256: str
    retrieved_at: dt.datetime
    expires_at: dt.datetime | None
    licence: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Listing:
    """One entry without its payload, for ``entries()``."""

    key: CacheKey
    retrieved_at: dt.datetime | None
    expires_at: dt.datetime | None
    licence: str
    size: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Summary:
    """What the database file holds, for ``info()``."""

    exists: bool
    usable: bool
    size_bytes: int
    payload_bytes: int
    entry_count: int
    schema_version: int | None


def _driver() -> ModuleType:
    """Import ``sqlite3`` when first needed."""
    try:
        import sqlite3 as driver  # noqa: PLC0415 - a separate package in Pyodide
    except ImportError:
        msg = "sqlite3 is not available"
        raise SqliteMissingError(msg) from None
    return driver


def _stamp(value: dt.datetime) -> str:
    return value.astimezone(dt.UTC).isoformat()


def _parse(value: object) -> dt.datetime:
    """Read a stored instant; anything but an aware ISO 8601 text is refused."""
    if not isinstance(value, str):
        msg = "a time is not text"
        raise BadEntryError(msg)
    try:
        moment = dt.datetime.fromisoformat(value)
    except ValueError:
        msg = "a time is not ISO 8601"
        raise BadEntryError(msg) from None
    if moment.tzinfo is None:
        msg = "a time has no zone"
        raise BadEntryError(msg)
    return moment


def _params(key: CacheKey) -> tuple[str, str, str, str, str]:
    return (key.provider, key.dataset, key.series, key.query, key.vintage)


def _classify(driver: ModuleType, error: Exception) -> StoreError:
    """Say whether a driver failure is transient or the file's fault."""
    if isinstance(error, driver.OperationalError):
        text = str(error).lower()
        if any(
            word in text for word in ("no such table", "malformed", "not a database")
        ):
            return StoreCorruptError("the database is not a pyeconomics cache")
        return StoreBusyError("the database is busy or cannot be written")
    return StoreCorruptError("the database is damaged")


class Store:
    """One cache database file.

    Parameters
    ----------
    path
        The database file. Nothing exists there until the first
        :meth:`write`.
    max_bytes
        The most payload bytes kept; the least recently used entries go first.
    """

    def __init__(self, path: Path, *, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        self.path = path
        self.max_bytes = max_bytes

    # --- opening ------------------------------------------------------------------

    def exists(self) -> bool:
        """Return whether the database file exists."""
        return self.path.is_file()

    def _create_file(self) -> None:
        """Make the directory and an empty, owner-only database file."""
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=_PRIVATE_DIRECTORY)
        flags = os.O_WRONLY | os.O_CREAT | getattr(os, "O_BINARY", 0)
        os.close(os.open(self.path, flags, _OWNER_ONLY))
        self._private()

    def _private(self) -> None:
        """Make an existing file owner-only on POSIX (Windows uses the profile)."""
        if _POSIX:
            with contextlib.suppress(OSError):
                if self.path.stat().st_mode & _OTHERS:
                    self.path.chmod(_OWNER_ONLY)

    @contextlib.contextmanager
    def _session(self, *, create: bool) -> Generator[sqlite3.Connection | None]:
        """Open the database for one operation, or yield ``None`` if absent.

        A read of a database that does not exist never imports ``sqlite3``.
        """
        if not create and not self.path.exists():
            yield None
            return
        driver = _driver()
        connection: sqlite3.Connection | None = None
        try:
            if not self.path.exists():
                self._create_file()
            else:
                self._private()
            connection = driver.connect(
                str(self.path), timeout=BUSY_SECONDS, isolation_level=None
            )
            if self._verify(connection, driver, create=create):
                yield connection
            else:  # a file another process made and has not yet filled
                yield None
        except OSError:
            msg = "the cache directory cannot be used"
            raise StoreBusyError(msg) from None
        except driver.Error as error:
            raise _classify(driver, error) from error
        finally:
            if connection is not None:
                connection.close()

    def _verify(
        self, connection: sqlite3.Connection, driver: ModuleType, *, create: bool
    ) -> bool:
        """Check the schema, or make it in a new file when ``create``.

        Returns ``False`` for a file with no tables at all when not creating: a
        writer made it a moment ago and has not written the schema yet, which is
        an empty cache, not a damaged one. Any other file without this code's
        schema is refused.
        """
        tables = {row[0] for row in connection.execute(_TABLES)}
        if "schema_version" in tables:
            version = connection.execute(_VERSION).fetchone()[0]
            if not isinstance(version, int):
                msg = "the schema version is not a number"
                raise StoreCorruptError(msg)
            if version > SCHEMA_VERSION:
                raise NewerSchemaError(version)
            if version != SCHEMA_VERSION or "entries" not in tables:
                msg = "the schema is not this code's"
                raise StoreCorruptError(msg)
            return True
        if tables:
            msg = "the database is not a pyeconomics cache"
            raise StoreCorruptError(msg)
        if not create:
            return False
        return self._initialise(connection, driver)

    def _initialise(self, connection: sqlite3.Connection, driver: ModuleType) -> bool:
        with contextlib.suppress(driver.OperationalError):
            connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("BEGIN IMMEDIATE")
        taken = connection.execute(_TABLES).fetchall()
        if taken:  # another process initialised it between our check and our lock
            connection.execute("ROLLBACK")
            return self._verify(connection, driver, create=False)
        try:
            connection.execute(_CREATE_VERSION)
            connection.execute(_SET_VERSION, (SCHEMA_VERSION,))
            connection.execute(_CREATE_ENTRIES)
            connection.execute(_CREATE_INDEX)
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        connection.execute("COMMIT")
        return True

    @contextlib.contextmanager
    def _transaction(self, connection: sqlite3.Connection) -> Generator[None]:
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        connection.execute("COMMIT")

    # --- reading --------------------------------------------------------------------

    def read(self, key: CacheKey) -> EntryRow | None:
        """Return the entry for a key and mark it recently used, or ``None``.

        Raises
        ------
        BadEntryError
            If the row's columns are not what this code wrote.
        """
        with self._session(create=False) as connection:
            if connection is None:
                return None
            driver = _driver()
            row = connection.execute(_SELECT, _params(key)).fetchone()
            if row is None:
                return None
            identifier, kind, payload, digest, retrieved, expires, licence = row
            if not (
                isinstance(kind, str)
                and isinstance(payload, bytes)
                and isinstance(digest, str)
                and isinstance(licence, str)
            ):
                msg = "a column has the wrong type"
                raise BadEntryError(msg)
            entry = EntryRow(
                kind=kind,
                payload=payload,
                sha256=digest,
                retrieved_at=_parse(retrieved),
                expires_at=None if expires is None else _parse(expires),
                licence=licence,
            )
            # Recency is a convenience: a busy database must not fail a read.
            with (
                contextlib.suppress(driver.OperationalError),
                self._transaction(connection),
            ):
                connection.execute(_TOUCH, (identifier,))
            return entry

    def summary(self) -> Summary:
        """Describe the file; a newer or damaged database is reported unusable."""
        if not self.exists():
            return Summary(
                exists=False,
                usable=True,
                size_bytes=0,
                payload_bytes=0,
                entry_count=0,
                schema_version=None,
            )
        size = sum(self._size(suffix) for suffix in ("", "-wal", "-shm"))
        try:
            with self._session(create=False) as connection:
                if connection is None:  # removed since the check above
                    return Summary(
                        exists=False,
                        usable=True,
                        size_bytes=0,
                        payload_bytes=0,
                        entry_count=0,
                        schema_version=None,
                    )
                payload, count = connection.execute(_TOTAL).fetchone()
        except NewerSchemaError as error:
            return Summary(
                exists=True,
                usable=False,
                size_bytes=size,
                payload_bytes=0,
                entry_count=0,
                schema_version=error.version,
            )
        except StoreCorruptError:
            return Summary(
                exists=True,
                usable=False,
                size_bytes=size,
                payload_bytes=0,
                entry_count=0,
                schema_version=None,
            )
        return Summary(
            exists=True,
            usable=True,
            size_bytes=size,
            payload_bytes=int(payload),
            entry_count=int(count),
            schema_version=SCHEMA_VERSION,
        )

    def _size(self, suffix: str) -> int:
        """Return the size of the database file or one of its write-ahead files."""
        try:
            return self.path.with_name(self.path.name + suffix).stat().st_size
        except OSError:  # absent, or removed since we looked
            return 0

    def listing(self, provider: str | None = None) -> list[Listing]:
        """Return the entries without their payloads, sorted."""
        with self._session(create=False) as connection:
            if connection is None:
                return []
            rows = connection.execute(_LIST, (provider, provider)).fetchall()
        return [
            Listing(
                key=_key(row[:5]),
                retrieved_at=_lenient(row[5]),
                expires_at=_lenient(row[6]),
                licence=str(row[7]),
                size=int(row[8]),
            )
            for row in rows
        ]

    # --- writing --------------------------------------------------------------------

    def write(  # noqa: PLR0913 - an entry's columns
        self,
        key: CacheKey,
        *,
        kind: str,
        payload: bytes,
        retrieved_at: dt.datetime,
        expires_at: dt.datetime | None,
        licence: str,
    ) -> bool:
        """Store or replace an entry, then evict to the size cap.

        Returns ``False`` without writing when the payload alone exceeds the cap.
        """
        if len(payload) > self.max_bytes:
            return False
        digest = hashlib.sha256(payload).hexdigest()
        values = (
            *_params(key),
            kind,
            _stamp(retrieved_at),
            None if expires_at is None else _stamp(expires_at),
            licence,
            payload,
            digest,
            len(payload),
        )
        with self._session(create=True) as opened:
            connection = cast("sqlite3.Connection", opened)  # create=True opens one
            with self._transaction(connection):
                connection.execute(_UPSERT, values)
                self._evict(connection)
        return True

    def _evict(self, connection: sqlite3.Connection) -> None:
        total = int(connection.execute(_TOTAL).fetchone()[0])
        if total <= self.max_bytes:
            return
        for identifier, size in connection.execute(_BY_AGE).fetchall():
            connection.execute(_EVICT, (identifier,))
            total -= int(size)
            if total <= self.max_bytes:
                break

    def discard(self, key: CacheKey) -> None:
        """Delete one entry; a missing database or entry is nothing to do."""
        with self._session(create=False) as connection:
            if connection is None:
                return
            with self._transaction(connection):
                connection.execute(_DELETE_ONE, _params(key))

    def clear(self, provider: str | None = None) -> int:
        """Delete a provider's entries, or all of them; return how many went."""
        with self._session(create=False) as connection:
            if connection is None:
                return 0
            driver = _driver()
            with self._transaction(connection):
                removed = connection.execute(_DELETE_PROVIDER, (provider, provider))
                count = max(removed.rowcount, 0)
            if provider is None:
                # Give the space back; a busy database keeps it until next time.
                with contextlib.suppress(driver.OperationalError):
                    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    connection.execute("VACUUM")
        return count


def _key(values: tuple[object, ...]) -> CacheKey:
    from pyeconomics.data.cache.policy import CacheKey  # noqa: PLC0415 - typing cycle

    provider, dataset, series, query, vintage = (str(value) for value in values)
    return CacheKey(
        provider=provider, dataset=dataset, series=series, query=query, vintage=vintage
    )


def _lenient(value: object) -> dt.datetime | None:
    """Read a stored instant for a listing; a bad one shows as ``None``."""
    if value is None:
        return None
    try:
        return _parse(value)
    except BadEntryError:
        return None
