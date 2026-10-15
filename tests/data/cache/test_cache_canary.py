# tests/data/cache/test_cache_canary.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The cache file is a canary sink: no key reaches it (ADR-0011 decision 13).

A random canary key goes through a real fetch (the HTTPS transport over a fake
pool, so the key is on the wire as it would be) and the cache stores the result.
The database, its write-ahead files, every row, the listings and the records a
fetch yields are searched for the key, with the logs and warnings of the run. A
query that carries a credential-named field is not cached at all. A failing
assertion names the sinks, never the key.
"""

from __future__ import annotations

import json
import secrets
from typing import TYPE_CHECKING, Any

import pytest
from cache_support import execute, rows
from fakes import FIXED_NOW, FakeClock, FakePool, FakeRaw
from leakcheck import LeakCheck, canary
from toys import ToyJson

from pyeconomics.data import DataWarning, Query, cache
from pyeconomics.data.transport.http import HttpTransport

if TYPE_CHECKING:
    from pathlib import Path

    from config_isolation import Isolation

pytestmark = pytest.mark.usefixtures("wall")

BODY = json.dumps(
    {
        "title": "Toy policy rate",
        "units": "Percent",
        "frequency": "monthly",
        "seasonal_adjustment": "NSA",
        "observations": [{"date": "2025-01-01", "value": "4.50"}],
    }
).encode()
QUERY = Query(series=("TOYRATE",))


def ok() -> FakeRaw:
    return FakeRaw(200, BODY, {"Content-Type": "application/json"})


def wire(pool: FakePool) -> HttpTransport:
    clock = FakeClock()
    return HttpTransport(
        pool=pool,
        clock=clock.monotonic,
        sleep=clock.sleep,
        now=lambda: FIXED_NOW,
        jitter=lambda ceiling: ceiling,
    )


def add_cache_sinks(check: LeakCheck, path: Path) -> None:
    """Add every place the cache keeps or shows anything."""
    assert path.is_file()
    for suffix in ("", "-wal", "-shm"):
        side = path.with_name(path.name + suffix)
        if side.exists():
            check.add(f"cache:file{suffix}", side.read_bytes())
    check.add("cache:rows", repr(rows(path)))
    check.add("cache:entries", repr(cache.entries()))
    check.add("cache:info", repr(cache.info()))


def test_a_key_used_in_a_fetch_reaches_neither_the_cache_file_nor_its_listings() -> (
    None
):
    held = canary("toy_json")
    check = LeakCheck(held)
    pool = FakePool(ok())
    with check.logs("pyeconomics.data.cache"), check.warnings():
        first = ToyJson().fetch_with_origin(QUERY, key=held.value, transport=wire(pool))
        again = ToyJson().fetch_with_origin(QUERY, key=held.value, transport=wire(pool))
    assert held.value in pool.calls[0].url  # the wire carried it, as it must
    assert len(pool.calls) == 1  # the second fetch was the cache's
    assert again.origin.cache_hit is True
    check.add("fetch:first", first.source().canonical_json())
    check.add("fetch:again", again.source().canonical_json())
    check.add("fetch:frames", repr(first.frame) + repr(again.frame))
    add_cache_sinks(check, cache.path())
    check.assert_clean()
    assert len(check.sinks) >= 6


def test_a_credential_field_in_a_query_is_not_cached_and_reaches_no_sink(
    isolated: Isolation,
) -> None:
    class KeyedQuery(Query):
        api_key: str = "unset"

    class Keyed(ToyJson):
        query_type = KeyedQuery

    held = canary("toy_json")
    check = LeakCheck(held)
    pool = FakePool(ok(), ok())
    query: dict[str, Any] = {"series": ("TOYRATE",), "api_key": held.value}
    with check.logs("pyeconomics.data.cache"), check.warnings():
        first = Keyed().fetch_with_origin(query, key=held.value, transport=wire(pool))
        second = Keyed().fetch_with_origin(query, key=held.value, transport=wire(pool))
    assert len(pool.calls) == 2  # never a hit: there is no key to look up
    assert (first.origin.cache_hit, second.origin.cache_hit) == (False, False)
    assert not isolated.cache_dir.exists()
    check.add(
        "fetch", first.source().canonical_json() + second.source().canonical_json()
    )
    check.add("cache:entries", repr(cache.entries()) + repr(cache.info()))
    check.assert_clean()


def test_a_discarded_entry_reports_without_a_key() -> None:
    held = canary("toy_json")
    check = LeakCheck(held)
    pool = FakePool(ok(), ok())
    with check.logs("pyeconomics.data.cache"), check.warnings():
        ToyJson().fetch_with_origin(QUERY, key=held.value, transport=wire(pool))
        execute(cache.path(), "UPDATE entries SET payload = x'00'")
        fetched = ToyJson().fetch_with_origin(
            QUERY, key=held.value, transport=wire(pool)
        )
    assert fetched.origin.warnings == ("cache_entry_discarded",)
    assert "warning:DataWarning" in check.sinks  # it was reported ...
    check.add("fetch", fetched.source().canonical_json())
    add_cache_sinks(check, cache.path())
    check.assert_clean()  # ... and said nothing of the key


def test_the_leak_check_finds_a_key_planted_in_the_cache_file() -> None:
    held = canary("toy_json")
    check = LeakCheck(held)
    ToyJson().fetch_with_origin(QUERY, key=held.value, transport=wire(FakePool(ok())))
    execute(cache.path(), "UPDATE entries SET dataset = ?", held.value)
    add_cache_sinks(check, cache.path())
    assert {"cache:rows", "cache:entries"} <= set(check.leaks())
    with pytest.raises(AssertionError, match="cache:rows"):
        check.assert_clean()


def test_the_discard_warning_is_a_data_warning() -> None:
    provider, pool, key = ToyJson(), FakePool(ok(), ok()), secrets.token_hex(16)
    provider.fetch_with_origin(QUERY, key=key, transport=wire(pool))
    execute(cache.path(), "UPDATE entries SET payload_sha256 = 'x'")
    with pytest.warns(DataWarning, match="cache_entry_discarded"):
        provider.fetch_with_origin(QUERY, key=key, transport=wire(pool))
