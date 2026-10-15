# tests/data/cache/test_cache_fetch.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A fetch through the cache: hits, expiry, closed vintages and the licence gate.

The toy providers run the real pipeline over recorded responses
(``ReplayTransport``), whose ``served`` list counts the requests that reached a
"source", and a fake wall clock (the ``wall`` fixture) moves time. Sockets are
disabled in the suite.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from cache_support import (
    Forbidden,
    Storable,
    WallClock,
    latest,
    no_database,
    replay_case,
    revised,
    rows,
    scripted,
    toy_query,
)
from stubs import STUB_TERMS, Scripted, answer, series_for
from toys import ToyJson, ToyVintage

from pyeconomics.data import (
    CachePolicy,
    Fetched,
    LicenceClass,
    LicenceError,
    Query,
    Series,
    SeriesNotFoundError,
    Table,
    cache,
    config,
    configure,
)

if TYPE_CHECKING:
    from config_isolation import Isolation

    from pyeconomics.data.transport.replay import ReplayTransport

pytestmark = pytest.mark.usefixtures("wall")


def toy(transport: ReplayTransport, name: str = "fetch_ok") -> Fetched:
    query = toy_query(ToyJson, name)
    return ToyJson().fetch_with_origin(query, transport=transport)


def test_a_fetch_is_served_from_the_cache_within_its_time_to_live(
    wall: WallClock, isolated: Isolation
) -> None:
    transport = replay_case(ToyJson, "fetch_ok")
    first = toy(transport)
    asked = len(transport.served)
    assert asked >= 1
    assert first.origin.cache_hit is False
    assert cache.path().parent == isolated.cache_dir
    assert cache.path().is_file()
    wall.advance(seconds=3_599)
    second = toy(transport)
    assert len(transport.served) == asked  # no new request
    assert second.origin.cache_hit is True
    assert second.origin.served_offline is False
    assert second.frame == first.frame
    assert second.frame.meta.retrieved_at == first.frame.meta.retrieved_at
    record = second.source()
    assert (record.cache_hit, record.served_offline) == (True, False)
    assert record.retrieved_at == first.frame.meta.retrieved_at


def test_a_fetch_goes_to_the_source_again_after_its_time_to_live(
    wall: WallClock,
) -> None:
    transport = replay_case(ToyJson, "fetch_ok")
    toy(transport)
    asked = len(transport.served)
    wall.advance(seconds=3_601)
    again = toy(transport)
    assert again.origin.cache_hit is False
    assert len(transport.served) == 2 * asked
    (entry,) = cache.entries()
    assert entry.expires_at == wall.now + dt.timedelta(hours=1)  # replaced, renewed
    wall.advance(seconds=10)
    assert toy(transport).origin.cache_hit is True
    assert len(transport.served) == 2 * asked


def test_a_users_time_to_live_overrides_the_providers(
    wall: WallClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYECONOMICS_TTL_TOY_JSON", "60")
    config.reset()
    transport = replay_case(ToyJson, "fetch_ok")
    toy(transport)
    wall.advance(seconds=59)
    assert toy(transport).origin.cache_hit is True
    wall.advance(seconds=2)
    assert toy(transport).origin.cache_hit is False


def test_a_time_to_live_of_zero_turns_a_providers_cache_off(
    isolated: Isolation, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYECONOMICS_TTL_TOY_JSON", "0")
    config.reset()
    no_database(monkeypatch)
    transport = replay_case(ToyJson, "fetch_ok")
    toy(transport)
    asked = len(transport.served)
    assert toy(transport).origin.cache_hit is False
    assert len(transport.served) == 2 * asked
    assert not isolated.cache_dir.exists()


def test_a_closed_past_vintage_stays_cached_until_evicted(wall: WallClock) -> None:
    provider = Storable()
    provider.parsed = lambda _r, _q: revised()
    transport = Scripted(answer(), answer())
    closed = latest(provider, transport, vintage="as_of:2020-03-31")
    assert isinstance(closed.frame, Series)
    assert closed.frame.values == (0.02,)
    wall.advance(days=3_650)  # ten years
    again = latest(provider, transport, vintage="as_of:2020-03-31")
    assert again.origin.cache_hit is True
    assert len(transport.sent) == 1
    (entry,) = cache.entries()
    assert (entry.vintage, entry.expires_at) == ("as_of:2020-03-31", None)


@pytest.mark.parametrize(
    "vintage", ["latest", "first_release", "all", "as_of:2026-10-15"]
)
def test_an_open_vintage_expires(wall: WallClock, vintage: str) -> None:
    provider = Storable()
    provider.parsed = lambda _r, _q: revised()
    transport = Scripted(answer(), answer())
    latest(provider, transport, vintage=vintage)
    (entry,) = cache.entries()
    assert entry.expires_at == wall.now + dt.timedelta(hours=1)
    wall.advance(seconds=3_601)
    assert latest(provider, transport, vintage=vintage).origin.cache_hit is False
    assert len(transport.sent) == 2


def test_each_vintage_and_query_is_its_own_entry() -> None:
    provider = Storable()
    provider.parsed = lambda _r, _q: revised()
    transport = Scripted(*(answer() for _ in range(4)))
    latest(provider, transport)
    latest(provider, transport, vintage="as_of:2020-03-31")
    latest(provider, transport, vintage="as_of:2010-03-31")
    latest(provider, transport, max_observations=5)
    assert len(transport.sent) == 4
    assert len(cache.entries()) == 4


def test_a_table_is_cached_and_read_back_whole() -> None:
    transport = replay_case(ToyJson, "fetch_table")
    first = toy(transport, "fetch_table")
    assert isinstance(first.frame, Table)
    again = toy(transport, "fetch_table")
    assert again.origin.cache_hit is True
    assert again.frame == first.frame


def test_fetch_returns_the_frame_fetch_with_origin_returns() -> None:
    transport = replay_case(ToyJson, "fetch_ok")
    query = toy_query(ToyJson, "fetch_ok")
    frame = ToyJson().fetch(query, transport=transport)
    assert isinstance(frame, Series)
    kept = ToyJson().fetch_with_origin(query, transport=transport)
    assert kept.frame == frame
    assert kept.origin.cache_hit is True


# --- the licence gate: a source that forbids storage has no cache path ------------


def test_a_provider_whose_terms_forbid_storage_never_creates_the_database(
    isolated: Isolation, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ADR-0005's Confirmation: nothing is written, not even the file.
    no_database(monkeypatch)
    transport = replay_case(ToyVintage, "fetch_all")
    query = toy_query(ToyVintage, "fetch_all")
    first = ToyVintage().fetch_with_origin(query, transport=transport)
    asked = len(transport.served)
    second = ToyVintage().fetch_with_origin(query, transport=transport)
    assert (first.origin.cache_hit, second.origin.cache_hit) == (False, False)
    assert len(transport.served) == 2 * asked > 0
    assert not isolated.cache_dir.exists()
    assert not cache.path().exists()
    info = cache.info()
    assert (info.exists, info.entry_count) == (False, 0)


def test_a_forbidding_stub_has_no_code_path_to_the_store(
    isolated: Isolation, monkeypatch: pytest.MonkeyPatch
) -> None:
    no_database(monkeypatch)
    provider, transport = Forbidden(), Scripted(answer(), answer())
    latest(provider, transport)
    latest(provider, transport, vintage="all")
    assert len(transport.sent) == 2
    assert not isolated.cache_dir.exists()


def test_a_series_whose_terms_forbid_storage_is_not_stored_either(
    isolated: Isolation,
) -> None:
    # toy_json allows storage, but marks one series restricted (FRED-style).
    transport = replay_case(ToyJson, "fetch_restricted")
    fetched = toy(transport, "fetch_restricted")
    assert fetched.frame.meta.terms.cache is CachePolicy.FORBIDDEN
    assert fetched.frame.meta.terms.licence is LicenceClass.LIBRARY_ONLY
    asked = len(transport.served)
    assert toy(transport, "fetch_restricted").origin.cache_hit is False
    assert len(transport.served) == 2 * asked
    assert not cache.path().exists()
    assert not isolated.cache_dir.exists()


def test_user_supplied_data_is_never_stored(isolated: Isolation) -> None:
    terms = replace(STUB_TERMS, licence=LicenceClass.USER_SUPPLIED)
    provider = Storable()
    provider.parsed = lambda _r, _q: series_for(terms=terms)
    transport = Scripted(answer(), answer())
    latest(provider, transport)
    latest(provider, transport)
    assert len(transport.sent) == 2
    assert not isolated.cache_dir.exists()


def test_a_storable_provider_whose_series_forbids_storage_writes_nothing(
    isolated: Isolation,
) -> None:
    terms = STUB_TERMS.with_overrides(cache=CachePolicy.FORBIDDEN)
    provider = Storable()
    provider.parsed = lambda _r, _q: series_for(terms=terms)
    latest(provider, scripted(200))
    assert not isolated.cache_dir.exists()


def test_a_failed_fetch_is_not_cached(isolated: Isolation) -> None:
    with pytest.raises(SeriesNotFoundError):
        latest(Storable(), scripted(404))
    assert not isolated.cache_dir.exists()


def test_a_result_larger_than_the_size_cap_is_not_stored(isolated: Isolation) -> None:
    with cache.override(max_bytes=100):
        latest(Storable(), scripted(200))
    assert not isolated.cache_dir.exists()


# --- the memo: in the process, within one call, never storage ---------------------


def test_a_memo_serves_a_repeat_fetch_of_a_source_that_may_not_be_stored(
    isolated: Isolation, monkeypatch: pytest.MonkeyPatch
) -> None:
    no_database(monkeypatch)
    provider, transport = Forbidden(), Scripted(*(answer() for _ in range(3)))
    with cache.memo():
        first = latest(provider, transport)
        second = latest(provider, transport)
        with cache.memo():  # a nested block shares the outer one
            third = latest(provider, transport)
        other = latest(provider, transport, vintage="all")
    assert len(transport.sent) == 2  # the repeats were served from memory
    assert first.frame == second.frame == third.frame
    assert (second.origin.cache_hit, third.origin.cache_hit) == (False, False)
    assert other.frame is not None
    latest(provider, transport)  # the block ended with its memo
    assert len(transport.sent) == 3
    assert not isolated.cache_dir.exists()


def test_a_memo_does_not_outlive_its_block(wall: WallClock) -> None:
    provider, transport = Storable(), Scripted(answer(), answer(), answer())
    with cache.memo():
        latest(provider, transport)
        wall.advance(days=1)  # past the time to live: the memo answers, not the store
        assert latest(provider, transport).origin.cache_hit is False
    assert len(transport.sent) == 1
    assert latest(provider, transport).origin.cache_hit is False  # the store expired
    assert len(transport.sent) == 2


# --- bypass -----------------------------------------------------------------------


def test_a_bypassed_fetch_reaches_the_source_and_leaves_the_cache_alone(
    wall: WallClock,
) -> None:
    provider, transport = Storable(), Scripted(answer(), answer())
    latest(provider, transport)
    (before,) = cache.entries()
    wall.advance(seconds=100)
    with cache.bypass():
        fetched = latest(provider, transport)
    assert fetched.origin.cache_hit is False
    assert len(transport.sent) == 2
    assert cache.entries() == (before,)  # neither read nor written


# --- a query that must not be cached ----------------------------------------------


def test_a_query_with_a_credential_field_is_never_cached(isolated: Isolation) -> None:
    class KeyedQuery(Query):
        api_key: str = "x"

    class Keyed(Storable):
        query_type = KeyedQuery

    provider, transport = Keyed(), Scripted(answer(), answer())
    latest(provider, transport)
    latest(provider, transport)
    assert len(transport.sent) == 2
    assert not isolated.cache_dir.exists()


# --- hosted mode ------------------------------------------------------------------


def test_hosted_mode_refuses_a_cached_series_it_may_not_serve() -> None:
    library_only = replace(STUB_TERMS, licence=LicenceClass.LIBRARY_ONLY)
    provider = Storable()
    provider.parsed = lambda _r, _q: series_for(terms=library_only)
    transport = Scripted(answer(), answer())
    latest(provider, transport)
    assert len(cache.entries()) == 1
    configure(mode="hosted")
    with pytest.raises(LicenceError):
        latest(provider, transport)
    assert len(transport.sent) == 1


def test_a_database_file_another_process_has_just_created_is_an_empty_cache(
    isolated: Isolation,
) -> None:
    # No warning is expected (warnings are errors in the suite): the file is empty,
    # not damaged, because its creator has not written the schema yet.
    isolated.cache_dir.mkdir(parents=True)
    cache.path().write_bytes(b"")
    provider, transport = Storable(), Scripted(answer(), answer())
    assert latest(provider, transport).origin.cache_hit is False
    assert latest(provider, transport).origin.cache_hit is True
    assert len(transport.sent) == 1


def test_the_database_stays_in_the_cache_directory(isolated: Isolation) -> None:
    latest(Storable(), scripted(200))
    assert cache.path().is_relative_to(isolated.cache_dir)
    assert rows(cache.path(), "SELECT provider FROM entries") == [("stub",)]
