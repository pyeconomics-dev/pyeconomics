# tests/data/cache/test_cache_store.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The SQLite store: lazy creation, permissions, eviction and damage.

These tests use the store directly, with no provider or policy, so each property
is shown on its own: nothing is created until a write, the file is owner-only,
every statement is parameterized, recency decides eviction, and a newer, foreign
or damaged database is refused without being changed.
"""

from __future__ import annotations

import ast
import datetime as dt
import sqlite3
import stat
import sys
from contextlib import closing
from pathlib import Path

import pytest
from cache_support import execute, rows
from config_isolation import POSIX

from pyeconomics.data.cache import store as store_module
from pyeconomics.data.cache.policy import CacheKey
from pyeconomics.data.cache.store import (
    SCHEMA_VERSION,
    BadEntryError,
    NewerSchemaError,
    SqliteMissingError,
    Store,
    StoreBusyError,
    StoreCorruptError,
    StoreError,
)

WHEN = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.UTC)


def key(series: str = "A", provider: str = "demo", vintage: str = "latest") -> CacheKey:
    return CacheKey(
        provider=provider, dataset="", series=series, query="{}", vintage=vintage
    )


def put(
    store: Store, name: str = "A", payload: bytes = b"{}", *, provider: str = "demo"
) -> bool:
    return store.write(
        key(name, provider),
        kind="series",
        payload=payload,
        retrieved_at=WHEN,
        expires_at=WHEN + dt.timedelta(hours=1),
        licence="hosted-safe",
    )


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "cache" / "cache.sqlite3")


def test_nothing_exists_until_the_first_write(store: Store) -> None:
    assert not store.exists()
    assert store.read(key()) is None
    assert store.listing() == []
    assert store.clear() == 0
    store.discard(key())
    summary = store.summary()
    assert (summary.exists, summary.usable, summary.entry_count) == (False, True, 0)
    assert not store.path.parent.exists()
    assert put(store)
    assert store.exists()


@pytest.mark.skipif(not POSIX, reason="Windows has no owner-only mode bits")
def test_the_database_and_its_directory_are_owner_only(store: Store) -> None:
    put(store)
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.path.parent.stat().st_mode) == 0o700
    for suffix in ("-wal", "-shm"):
        side = store.path.with_name(store.path.name + suffix)
        if side.exists():
            assert stat.S_IMODE(side.stat().st_mode) & 0o077 == 0


@pytest.mark.parametrize("posix", [True, False])
def test_a_database_others_can_read_is_made_private_on_posix_only(
    store: Store, monkeypatch: pytest.MonkeyPatch, *, posix: bool
) -> None:
    put(store)
    monkeypatch.setattr(store_module, "_POSIX", posix)
    modes: list[int] = []
    real = Path.chmod

    def record(self: Path, mode: int, **kwargs: bool) -> None:
        modes.append(mode)
        real(self, mode, **kwargs)

    monkeypatch.setattr(Path, "chmod", record)
    if POSIX:
        store.path.chmod(0o644)
        modes.clear()
    assert store.read(key()) is not None
    # Windows reports mode 0o666 for any file, which others "can read" too.
    assert modes == ([0o600] if posix else [])
    if POSIX and posix:
        assert stat.S_IMODE(store.path.stat().st_mode) == 0o600


def test_the_schema_is_versioned_and_the_journal_is_wal(store: Store) -> None:
    put(store)
    assert rows(store.path, "SELECT version FROM schema_version") == [(SCHEMA_VERSION,)]
    assert rows(store.path, "PRAGMA journal_mode") == [("wal",)]
    summary = store.summary()
    assert (summary.usable, summary.schema_version) == (True, SCHEMA_VERSION)


def test_an_entry_is_read_back_with_its_checks(store: Store) -> None:
    put(store, payload=b'{"a":1}')
    entry = store.read(key())
    assert entry is not None
    assert (entry.kind, entry.payload, entry.licence) == (
        "series",
        b'{"a":1}',
        "hosted-safe",
    )
    assert (entry.retrieved_at, entry.expires_at) == (
        WHEN,
        WHEN + dt.timedelta(hours=1),
    )
    assert len(entry.sha256) == 64
    assert store.read(key("B")) is None
    assert store.read(key(provider="other")) is None


def test_a_closed_vintage_is_stored_without_an_expiry(store: Store) -> None:
    store.write(
        key(vintage="as_of:2020-03-31"),
        kind="series",
        payload=b"{}",
        retrieved_at=WHEN,
        expires_at=None,
        licence="hosted-safe",
    )
    entry = store.read(key(vintage="as_of:2020-03-31"))
    assert entry is not None
    assert entry.expires_at is None


def test_writing_a_key_again_replaces_its_entry(store: Store) -> None:
    put(store, payload=b"first")
    put(store, payload=b"second")
    entry = store.read(key())
    assert entry is not None
    assert entry.payload == b"second"
    assert store.summary().entry_count == 1


def test_the_least_recently_used_entry_goes_first(tmp_path: Path) -> None:
    store = Store(tmp_path / "cache.sqlite3", max_bytes=30)
    for name in ("A", "B", "C"):
        assert put(store, name, b"0123456789")
    assert store.read(key("A")) is not None  # A is now the most recently used
    assert put(store, "D", b"0123456789")
    kept = {entry.key.series for entry in store.listing()}
    assert kept == {"A", "C", "D"}
    assert store.summary().payload_bytes == 30


def test_a_result_larger_than_the_cap_is_not_stored(tmp_path: Path) -> None:
    store = Store(tmp_path / "cache.sqlite3", max_bytes=8)
    assert put(store, payload=b"123456789") is False
    assert not store.exists()
    assert put(store, payload=b"12345678") is True


def test_a_new_entry_is_never_the_one_evicted(tmp_path: Path) -> None:
    store = Store(tmp_path / "cache.sqlite3", max_bytes=10)
    assert put(store, "A", b"0123456789")
    assert put(store, "B", b"0123456789")
    assert [entry.key.series for entry in store.listing()] == ["B"]


def test_discard_and_clear_remove_entries(store: Store) -> None:
    put(store, "A")
    put(store, "B")
    put(store, "C", provider="other")
    store.discard(key("A"))
    assert store.read(key("A")) is None
    assert store.clear("demo") == 1
    assert [entry.key.provider for entry in store.listing()] == ["other"]
    assert store.clear() == 1
    assert store.listing() == []
    assert store.exists()  # the file stays; clearing empties it


def test_the_listing_is_sorted_filtered_and_holds_no_payload(store: Store) -> None:
    put(store, "B", b"12345")
    put(store, "A", b"123")
    put(store, "Z", provider="aaa")
    everything = store.listing()
    assert [(e.key.provider, e.key.series) for e in everything] == [
        ("aaa", "Z"),
        ("demo", "A"),
        ("demo", "B"),
    ]
    assert [entry.size for entry in store.listing("demo")] == [3, 5]
    assert not hasattr(everything[0], "payload")


def test_a_newer_schema_is_reported_and_left_untouched(store: Store) -> None:
    put(store, payload=b"keep me")
    execute(store.path, "UPDATE schema_version SET version = ?", SCHEMA_VERSION + 1)
    before = rows(store.path, "SELECT provider, payload FROM entries")
    for call in (
        lambda: store.read(key()),
        lambda: put(store, "B"),
        store.clear,
        lambda: store.discard(key()),
        store.listing,
    ):
        with pytest.raises(NewerSchemaError) as caught:
            call()
        assert caught.value.version == SCHEMA_VERSION + 1
    assert rows(store.path, "SELECT provider, payload FROM entries") == before
    summary = store.summary()
    assert (summary.usable, summary.schema_version) == (False, SCHEMA_VERSION + 1)


def test_a_database_that_is_not_ours_is_refused_not_written(tmp_path: Path) -> None:
    path = tmp_path / "foreign.sqlite3"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE notes (text TEXT)")
        connection.execute("INSERT INTO notes VALUES ('mine')")
        connection.commit()
    store = Store(path)
    with pytest.raises(StoreCorruptError):
        put(store)
    with pytest.raises(StoreCorruptError):
        store.read(key())
    assert rows(path, "SELECT text FROM notes") == [("mine",)]
    assert rows(path, "SELECT name FROM sqlite_master") == [("notes",)]
    assert store.summary().usable is False


def test_a_file_that_is_not_a_database_is_corrupt(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite3"
    path.write_bytes(b"this is not a database " * 50)
    store = Store(path)
    for call in (lambda: put(store), lambda: store.read(key()), store.listing):
        with pytest.raises(StoreCorruptError):
            call()
    assert path.read_bytes().startswith(b"this is not a database")
    assert store.summary().usable is False


def test_a_schema_with_the_wrong_version_or_no_entries_table_is_corrupt(
    store: Store,
) -> None:
    put(store)
    execute(store.path, "UPDATE schema_version SET version = 0")
    with pytest.raises(StoreCorruptError):
        store.read(key())
    execute(store.path, "UPDATE schema_version SET version = ?", SCHEMA_VERSION)
    execute(store.path, "DROP TABLE entries")
    with pytest.raises(StoreCorruptError):
        store.read(key())
    execute(store.path, "UPDATE schema_version SET version = 'one'")
    with pytest.raises(StoreCorruptError):
        store.read(key())


def test_an_empty_file_is_an_empty_cache_until_the_first_write(tmp_path: Path) -> None:
    # Another process creates the file a moment before it writes the schema.
    path = tmp_path / "cache.sqlite3"
    path.write_bytes(b"")
    store = Store(path)
    assert store.read(key()) is None
    assert store.listing() == []
    assert store.clear() == 0
    store.discard(key())
    summary = store.summary()
    assert (summary.exists, summary.usable, summary.entry_count) == (False, True, 0)
    assert put(store)
    assert store.summary().entry_count == 1
    assert store.read(key()) is not None


@pytest.mark.parametrize(
    "damage",
    [
        "UPDATE entries SET retrieved_at = 'yesterday'",
        "UPDATE entries SET retrieved_at = '2026-10-15T12:00:00'",
        "UPDATE entries SET expires_at = 'soon'",
        "UPDATE entries SET retrieved_at = 5",
        "UPDATE entries SET retrieved_at = x'00'",
        "UPDATE entries SET kind = x'00'",
        "UPDATE entries SET payload = 'text'",
        "UPDATE entries SET payload_sha256 = x'00'",
        "UPDATE entries SET licence = x'00'",
    ],
)
def test_a_malformed_row_is_a_bad_entry(store: Store, damage: str) -> None:
    put(store)
    execute(store.path, damage)
    with pytest.raises(BadEntryError):
        store.read(key())
    # A listing shows what it can, with a time it cannot read left empty.
    assert len(store.listing()) == 1


def test_the_listing_shows_a_bad_time_as_none(store: Store) -> None:
    put(store)
    execute(store.path, "UPDATE entries SET retrieved_at = 'yesterday'")
    (entry,) = store.listing()
    assert entry.retrieved_at is None
    assert entry.expires_at == WHEN + dt.timedelta(hours=1)


def test_a_locked_database_is_busy_not_corrupt(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    put(store)
    monkeypatch.setattr(store_module, "BUSY_SECONDS", 0.05)
    with closing(sqlite3.connect(store.path, isolation_level=None)) as holder:
        holder.execute("BEGIN IMMEDIATE")
        with pytest.raises(StoreBusyError):
            put(store, "B")
        with pytest.raises(StoreBusyError):
            store.discard(key())
        # A read does not wait for a writer in WAL mode, and a busy touch is ignored.
        assert store.read(key()) is not None
        holder.execute("ROLLBACK")
    assert put(store, "B")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (sqlite3.OperationalError("database is locked"), StoreBusyError),
        (sqlite3.OperationalError("unable to open database file"), StoreBusyError),
        (sqlite3.OperationalError("no such table: entries"), StoreCorruptError),
        (
            sqlite3.OperationalError("database disk image is malformed"),
            StoreCorruptError,
        ),
        (sqlite3.OperationalError("file is not a database"), StoreCorruptError),
        (sqlite3.DatabaseError("anything else"), StoreCorruptError),
        (sqlite3.IntegrityError("constraint"), StoreCorruptError),
    ],
)
def test_a_driver_failure_is_busy_or_the_files_fault(
    error: Exception, expected: type[Exception]
) -> None:
    assert type(store_module._classify(sqlite3, error)) is expected  # noqa: SLF001


def test_a_failed_write_is_rolled_back(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    put(store, "A")

    def broken(_self: Store, _connection: sqlite3.Connection) -> None:
        msg = "eviction failed"
        raise RuntimeError(msg)

    monkeypatch.setattr(Store, "_evict", broken)
    with pytest.raises(RuntimeError, match="eviction failed"):
        put(store, "B")
    monkeypatch.undo()
    assert [entry.key.series for entry in store.listing()] == ["A"]  # B was undone
    assert put(store, "B")


def test_a_failed_initialisation_leaves_an_empty_file_that_works_next_time(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "_CREATE_ENTRIES", "CREATE TABLE")
    with pytest.raises(StoreError):
        put(store)
    assert rows(store.path, "SELECT name FROM sqlite_master") == []  # rolled back
    monkeypatch.undo()
    assert put(store)
    assert store.summary().entry_count == 1


def test_an_unusable_directory_is_busy(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("not a directory", encoding="utf-8")
    with pytest.raises(StoreBusyError):
        put(Store(blocker / "cache.sqlite3"))


def test_a_missing_sqlite3_is_reported_only_when_a_database_must_be_opened(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "sqlite3", None)
    # Without a database file there is nothing to open: a read is a plain miss.
    assert store.read(key()) is None
    assert store.clear() == 0
    assert store.listing() == []
    with pytest.raises(SqliteMissingError):
        put(store)
    monkeypatch.undo()
    put(store)
    monkeypatch.setitem(sys.modules, "sqlite3", None)
    for call in (lambda: store.read(key()), store.clear, store.listing):
        with pytest.raises(SqliteMissingError):
            call()


def test_no_statement_is_built_by_string_formatting() -> None:
    source = Path(store_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    def constant(node: ast.expr) -> bool:
        return isinstance(node, ast.Constant) or (
            isinstance(node, ast.Name) and node.id.lstrip("_").isupper()
        )

    built = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
        and node.args
        and not constant(node.args[0])
    ]
    assert built == []
    words = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "PRAGMA")
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.JoinedStr)
        and any(word in ast.unparse(node).upper() for word in words)
    ]


def test_the_store_neither_pickles_nor_evaluates() -> None:
    tree = ast.parse(Path(store_module.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported & {"pickle", "marshal", "shelve", "dill", "yaml"}
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called & {"eval", "exec", "compile", "__import__"}
