# tests/data/cache/test_cache_concurrency.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Two writers at once do not corrupt the store.

Every operation opens its own connection, so threads here stand in for processes:
each has its own connections to the same file, WAL mode and a busy timeout
arbitrate between them, and the result is checked with SQLite's own integrity
check and by reading every entry back with its hash.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from typing import TYPE_CHECKING

from cache_support import Storable, latest, rows
from stubs import Scripted, answer

from pyeconomics.data import Series, cache
from pyeconomics.data.cache.policy import CacheKey
from pyeconomics.data.cache.store import Store

if TYPE_CHECKING:
    from pathlib import Path

WHEN = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.UTC)
WORKERS = 8
WRITES = 15


def key(series: str) -> CacheKey:
    return CacheKey(
        provider="demo", dataset="", series=series, query="{}", vintage="latest"
    )


def write(store: Store, series: str, payload: bytes) -> None:
    assert store.write(
        key(series),
        kind="series",
        payload=payload,
        retrieved_at=WHEN,
        expires_at=None,
        licence="hosted-safe",
    )


def writer(path: Path, worker: int) -> int:
    store = Store(path)  # its own connections, as another process would have
    for number in range(WRITES):
        write(store, f"W{worker}-{number}", f"{worker}:{number}".encode())
        write(store, "SHARED", f"{worker}:{number}".encode())
        store.read(key(f"W{worker}-{number}"))
    return worker


def test_concurrent_writers_leave_a_sound_complete_store(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite3"
    write(Store(path), "SHARED", b"first")  # the file exists before the race
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        finished = list(pool.map(lambda n: writer(path, n), range(WORKERS)))
    assert sorted(finished) == list(range(WORKERS))
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
    store = Store(path)
    assert store.summary().entry_count == WORKERS * WRITES + 1
    for worker in range(WORKERS):
        for number in range(WRITES):
            entry = store.read(key(f"W{worker}-{number}"))
            assert entry is not None
            assert entry.payload == f"{worker}:{number}".encode()
            assert entry.sha256 == hashlib.sha256(entry.payload).hexdigest()
    shared = store.read(key("SHARED"))
    assert shared is not None
    worker, number = (int(part) for part in shared.payload.decode().split(":"))
    assert 0 <= worker < WORKERS
    assert 0 <= number < WRITES  # one writer's last word, never a blend
    assert shared.sha256 == hashlib.sha256(shared.payload).hexdigest()


def test_concurrent_writers_that_create_the_store_together_agree_on_its_schema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "fresh" / "cache.sqlite3"

    def first_write(worker: int) -> None:
        write(Store(path), f"S{worker}", b"x")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(first_write, range(WORKERS)))
    assert Store(path).summary().entry_count == WORKERS
    assert rows(path, "SELECT COUNT(*) FROM schema_version") == [(1,)]


def test_concurrent_writers_respect_the_size_cap(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite3"
    cap = 20 * 10

    def fill(worker: int) -> None:
        store = Store(path, max_bytes=cap)
        for number in range(30):
            write(store, f"W{worker}-{number}", b"0123456789")

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(fill, range(4)))
    assert Store(path, max_bytes=cap).summary().payload_bytes <= cap


def test_concurrent_fetches_of_one_query_keep_one_entry() -> None:
    def fetch(_n: int) -> object:
        return latest(Storable(), Scripted(answer())).frame

    with ThreadPoolExecutor(max_workers=6) as pool:
        frames = list(pool.map(fetch, range(12)))
    assert all(isinstance(frame, Series) for frame in frames)
    assert len(set(map(repr, frames))) == 1
    assert len(cache.entries()) == 1
    assert cache.info().entry_count == 1
