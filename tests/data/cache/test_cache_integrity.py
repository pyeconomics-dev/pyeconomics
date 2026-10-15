# tests/data/cache/test_cache_integrity.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A tampered, foreign, damaged or newer cache is never trusted and never a crash.

A bad entry is deleted, reported as ``cache_entry_discarded`` and fetched again; a
newer schema is not touched and switches caching off for the process; a file that
is not a cache is reported once; a busy or missing database costs nothing but the
cache. In every case the fetch still returns the right data.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest
from cache_support import Storable, WallClock, execute, latest, rows
from stubs import NOW, STUB_TERMS, Scripted, answer, series_for

from pyeconomics.data import (
    CachePolicy,
    DataError,
    DataWarning,
    OfflineError,
    Series,
    cache,
    configure,
)
from pyeconomics.data.cache import store as store_module
from pyeconomics.data.cache.store import (
    SCHEMA_VERSION,
    SqliteMissingError,
    StoreBusyError,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from config_isolation import Isolation

    from pyeconomics.data import Terms

pytestmark = pytest.mark.usefixtures("wall")

DISCARD = "cache_entry_discarded"


def populated() -> tuple[Storable, Scripted, Series]:
    provider, transport = Storable(), Scripted(*(answer() for _ in range(6)))
    first = latest(provider, transport)
    assert isinstance(first.frame, Series)
    return provider, transport, first.frame


def stored_payload() -> bytes:
    (payload,) = rows(cache.path(), "SELECT payload FROM entries")[0]
    assert isinstance(payload, bytes)
    return payload


def swap_payload(payload: bytes, *, sha256: str | None = None) -> None:
    """Replace the stored payload (and by default its hash, to isolate the check)."""
    digest = hashlib.sha256(payload).hexdigest() if sha256 is None else sha256
    execute(
        cache.path(),
        "UPDATE entries SET payload = ?, payload_sha256 = ?",
        payload,
        digest,
    )


def sound_payload(provider: str = "stub", *, terms: Terms = STUB_TERMS) -> bytes:
    """A valid series' payload that agrees with the stored row's retrieval time."""
    return series_for(provider, retrieved_at=NOW, terms=terms).canonical_json()


def fetch_after_damage(provider: Storable, transport: Scripted) -> list[str]:
    """Fetch again, expecting one discard warning; return the origin's codes."""
    before = len(transport.sent)
    with pytest.warns(DataWarning, match=DISCARD) as caught:
        fetched = latest(provider, transport)
    assert fetched.origin.cache_hit is False
    assert len(transport.sent) == before + 1  # fetched again, from the source
    assert fetched.source().warnings == (DISCARD,)
    assert all(DISCARD in str(w.message) for w in caught)
    return list(fetched.origin.warnings)


DAMAGE: dict[str, Callable[[bytes], None]] = {
    "flipped-byte": lambda original: swap_payload(
        original.replace(b"0.01", b"0.99", 1),
        sha256=hashlib.sha256(original).hexdigest(),
    ),
    "wrong-hash": lambda original: swap_payload(original, sha256="0" * 64),
    "truncated": lambda original: swap_payload(original[: len(original) // 2]),
    "not-json": lambda _original: swap_payload(b"\x80\x81 definitely not json"),
    "empty": lambda _original: swap_payload(b""),
    "nan-value": lambda original: swap_payload(original.replace(b"0.01", b"NaN", 1)),
    "unknown-key": lambda original: swap_payload(
        original.replace(b'{"index"', b'{"extra":1,"index"', 1)
    ),
    "wrong-type": lambda _original: swap_payload(b"[1,2,3]"),
    "another-provider": lambda _original: swap_payload(sound_payload("someone_else")),
    "terms-now-forbid-storage": lambda _original: swap_payload(
        sound_payload(terms=STUB_TERMS.with_overrides(cache=CachePolicy.FORBIDDEN))
    ),
    "wrong-kind": lambda _original: execute(
        cache.path(), "UPDATE entries SET kind = 'table'"
    ),
    "unknown-kind": lambda _original: execute(
        cache.path(), "UPDATE entries SET kind = 'pickle'"
    ),
    "wrong-retrieval-time": lambda _original: execute(
        cache.path(), "UPDATE entries SET retrieved_at = '2001-01-01T00:00:00+00:00'"
    ),
    "wrong-licence": lambda _original: execute(
        cache.path(), "UPDATE entries SET licence = 'byok'"
    ),
    "unreadable-time": lambda _original: execute(
        cache.path(), "UPDATE entries SET retrieved_at = 'yesterday'"
    ),
    "wrong-column-type": lambda _original: execute(
        cache.path(), "UPDATE entries SET payload = 'text'"
    ),
}


@pytest.mark.parametrize("damage", sorted(DAMAGE))
def test_a_damaged_entry_is_discarded_and_the_data_fetched_again(damage: str) -> None:
    provider, transport, first = populated()
    DAMAGE[damage](stored_payload())
    codes = fetch_after_damage(provider, transport)
    assert codes == [DISCARD]
    # The replacement is sound: a plain fetch is a hit and equals the original data.
    again = latest(provider, transport)
    assert again.origin.cache_hit is True
    assert again.frame == first
    assert len(rows(cache.path())) == 1


def test_the_discard_warning_names_the_provider_and_no_path(
    isolated: Isolation,
) -> None:
    provider, transport, _ = populated()
    swap_payload(b"garbage")
    with pytest.warns(DataWarning) as caught:
        latest(provider, transport)
    (warning,) = caught
    assert isinstance(warning.message, DataWarning)
    assert warning.message.code == DISCARD
    text = str(warning.message)
    assert "stub" in text
    assert str(isolated.cache_dir) not in text
    assert "cache.sqlite3" not in text


def test_a_damaged_entry_is_a_miss_offline_too() -> None:
    provider, _transport, _ = populated()
    swap_payload(b"garbage")
    configure(offline=True)
    with pytest.warns(DataWarning, match=DISCARD), pytest.raises(OfflineError):
        latest(provider, Scripted())
    assert rows(cache.path()) == []


# --- a newer schema -----------------------------------------------------------------


def test_a_newer_schema_is_left_untouched_and_switches_caching_off() -> None:
    provider, transport, first = populated()
    execute(cache.path(), "UPDATE schema_version SET version = ?", SCHEMA_VERSION + 1)
    before = rows(cache.path(), "SELECT * FROM entries")
    with pytest.warns(DataWarning, match="cache_schema_newer"):
        fetched = latest(provider, transport)
    assert fetched.origin.cache_hit is False  # a newer cache is not read
    assert fetched.frame == first
    # Reported once: later fetches run silently (warnings are errors in the suite).
    latest(provider, transport)
    assert len(transport.sent) == 3
    assert rows(cache.path(), "SELECT * FROM entries") == before
    assert rows(cache.path(), "SELECT version FROM schema_version") == [
        (SCHEMA_VERSION + 1,)
    ]
    info = cache.info()
    assert (info.usable, info.schema_version) == (False, SCHEMA_VERSION + 1)
    for call in (cache.entries, cache.clear):
        with pytest.raises(DataError, match="newer pyeconomics"):
            call()


def test_a_newer_schema_is_reported_again_after_a_reset() -> None:
    provider, transport, _ = populated()
    execute(cache.path(), "UPDATE schema_version SET version = ?", SCHEMA_VERSION + 1)
    with pytest.warns(DataWarning, match="cache_schema_newer"):
        latest(provider, transport)
    cache.reset()
    with pytest.warns(DataWarning, match="cache_schema_newer"):
        latest(provider, transport)


def test_offline_mode_says_when_the_cache_is_unusable() -> None:
    provider, transport, _ = populated()
    execute(cache.path(), "UPDATE schema_version SET version = ?", SCHEMA_VERSION + 1)
    with pytest.warns(DataWarning, match="cache_schema_newer"):
        latest(provider, transport)
    configure(offline=True)
    with pytest.raises(OfflineError, match="no usable cache for stub"):
        latest(provider, Scripted())


# --- a file that is not our cache ----------------------------------------------------


def test_a_file_that_is_not_a_database_is_reported_once_and_left_alone(
    isolated: Isolation,
) -> None:
    isolated.cache_dir.mkdir(parents=True)
    junk = b"this is not a database " * 100
    cache.path().write_bytes(junk)
    provider, transport = Storable(), Scripted(answer(), answer(), answer())
    with pytest.warns(DataWarning, match="cache_unreadable"):
        latest(provider, transport)
    latest(provider, transport)
    assert len(transport.sent) == 2
    assert cache.path().read_bytes() == junk
    assert cache.info().usable is False
    with pytest.raises(DataError, match="not a usable pyeconomics cache"):
        cache.entries()
    with pytest.raises(DataError, match="not a usable pyeconomics cache"):
        cache.clear()


def test_a_database_with_other_tables_is_not_written_to(isolated: Isolation) -> None:
    isolated.cache_dir.mkdir(parents=True)
    with closing(sqlite3.connect(cache.path())) as connection:
        connection.execute("CREATE TABLE notes (text TEXT)")
        connection.commit()
    with pytest.warns(DataWarning, match="cache_unreadable"):
        latest(Storable(), Scripted(answer()))
    assert rows(cache.path(), "SELECT name FROM sqlite_master") == [("notes",)]


# --- a database that is busy, unwritable or missing --------------------------------


def test_a_locked_database_costs_the_write_not_the_fetch(
    wall: WallClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider, transport, _ = populated()
    (before,) = rows(cache.path(), "SELECT retrieved_at, expires_at FROM entries")
    wall.advance(seconds=7_200)
    monkeypatch.setattr(store_module, "BUSY_SECONDS", 0.05)
    with closing(sqlite3.connect(cache.path(), isolation_level=None)) as holder:
        holder.execute("BEGIN IMMEDIATE")
        fetched = latest(provider, transport)  # expired: refetched, write skipped
        holder.execute("ROLLBACK")
    assert fetched.origin.cache_hit is False
    assert rows(cache.path(), "SELECT retrieved_at, expires_at FROM entries") == [
        before
    ]
    assert latest(provider, transport).origin.cache_hit is False  # still expired
    assert latest(provider, transport).origin.cache_hit is True  # and now written


def test_an_unwritable_cache_directory_costs_nothing_but_the_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocker = tmp_path / "a-file"
    blocker.write_text("not a directory", encoding="utf-8")
    monkeypatch.setenv("PYECONOMICS_CACHE_DIR", str(blocker / "cache"))
    from pyeconomics.data import config  # noqa: PLC0415

    config.reset()
    provider, transport = Storable(), Scripted(answer(), answer())
    latest(provider, transport)
    assert latest(provider, transport).origin.cache_hit is False
    assert len(transport.sent) == 2


def test_a_missing_sqlite3_turns_caching_off_quietly(
    isolated: Isolation,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def missing() -> object:
        msg = "sqlite3 is not available"
        raise SqliteMissingError(msg)

    monkeypatch.setattr(store_module, "_driver", missing)
    provider, transport = Storable(), Scripted(answer(), answer())
    with caplog.at_level(logging.DEBUG, logger="pyeconomics.data.cache"):
        latest(provider, transport)
        latest(provider, transport)  # no warning: the suite makes any warning an error
    assert len(transport.sent) == 2
    assert not isolated.cache_dir.exists()
    assert any("caching is off" in record.message for record in caplog.records)
    assert cache.entries() == ()
    assert cache.clear() == 0
    info = cache.info()
    assert (info.exists, info.entry_count, info.usable) == (False, 0, True)
    configure(offline=True)
    with pytest.raises(OfflineError, match="sqlite3 is not available"):
        latest(provider, Scripted())


def test_the_inspection_api_copes_with_a_missing_sqlite3_and_a_busy_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    populated()  # a database file exists, so opening it needs the driver

    def missing() -> object:
        msg = "sqlite3 is not available"
        raise SqliteMissingError(msg)

    with monkeypatch.context() as patch:
        patch.setattr(store_module, "_driver", missing)
        info = cache.info()
        assert (info.exists, info.entry_count, info.usable) == (False, 0, True)
        assert cache.entries() == ()
        assert cache.clear() == 0

    def busy(*_args: object, **_kwargs: object) -> object:
        msg = "busy"
        raise StoreBusyError(msg)

    monkeypatch.setattr(store_module.Store, "listing", busy)
    monkeypatch.setattr(store_module.Store, "clear", busy)
    for call in (cache.entries, cache.clear):
        with pytest.raises(DataError, match="busy"):
            call()


def test_a_discard_that_cannot_be_written_is_still_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, transport, _ = populated()
    swap_payload(b"garbage")

    def busy(*_args: object, **_kwargs: object) -> None:
        msg = "busy"
        raise StoreBusyError(msg)

    monkeypatch.setattr(store_module.Store, "discard", busy)
    assert fetch_after_damage(provider, transport) == [DISCARD]


def test_a_replaced_entry_keeps_one_row(wall: WallClock) -> None:
    provider, transport, _ = populated()
    for _ in range(3):
        wall.advance(seconds=3_601)
        latest(provider, transport)
    assert len(rows(cache.path())) == 1
