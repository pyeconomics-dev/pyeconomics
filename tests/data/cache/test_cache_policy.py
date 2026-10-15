# tests/data/cache/test_cache_policy.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The cache's rules: the licence gate, expiry, keys and what a fetch reports.

The policy module is pure, so every case here is a function of its arguments.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

import pytest
from cache_support import replay_case, toy_query
from stubs import STUB_TERMS, series_for
from toys import ToyJson

from pyeconomics.data import (
    CachePolicy,
    DataSource,
    Fetched,
    LicenceClass,
    Origin,
    Query,
    Table,
)
from pyeconomics.data.cache.policy import (
    CLOSED_AFTER,
    DISCARDED_WARNING,
    OFFLINE_WARNING,
    CacheKey,
    expiry,
    is_closed,
    may_store,
    offline_message,
)

NOON = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.UTC)


@pytest.mark.parametrize("licence", list(LicenceClass))
@pytest.mark.parametrize("policy", list(CachePolicy))
def test_the_licence_gate_stores_only_what_the_terms_and_class_allow(
    licence: LicenceClass, policy: CachePolicy
) -> None:
    terms = replace(STUB_TERMS, licence=licence, cache=policy)
    expected = (
        policy is CachePolicy.ALLOWED and licence is not LicenceClass.USER_SUPPLIED
    )
    assert may_store(terms) is expected


def test_a_series_override_can_close_a_storable_provider() -> None:
    terms = STUB_TERMS.with_overrides(cache=CachePolicy.FORBIDDEN)
    assert may_store(STUB_TERMS)
    assert not may_store(terms)


@pytest.mark.parametrize(
    ("vintage", "closed"),
    [
        ("as_of:2020-03-31", True),
        ("as_of:2026-10-13", True),
        ("as_of:2026-10-14", False),  # yesterday may still change in the source's zone
        ("as_of:2026-10-15", False),
        ("as_of:2027-01-01", False),
        ("latest", False),
        ("first_release", False),
        ("all", False),
    ],
)
def test_only_an_as_of_vintage_in_the_past_is_closed(
    vintage: str, *, closed: bool
) -> None:
    assert is_closed(vintage, today=NOON.date()) is closed
    assert dt.timedelta(days=1) == CLOSED_AFTER


def test_an_open_entry_expires_after_its_time_to_live_and_a_closed_one_never() -> None:
    assert expiry("latest", now=NOON, ttl=3_600) == NOON + dt.timedelta(hours=1)
    assert expiry("all", now=NOON, ttl=0) == NOON
    assert expiry("as_of:2020-03-31", now=NOON, ttl=3_600) is None


def test_a_key_is_the_provider_dataset_series_query_and_vintage() -> None:
    query = Query(series=("A", "B"), start=dt.date(2020, 1, 1), vintage="first_release")
    key = CacheKey.of("demo", query)
    assert key is not None
    assert (key.provider, key.dataset, key.series, key.vintage) == (
        "demo",
        "",
        "A,B",
        "first_release",
    )
    assert key.query.startswith("{")
    assert '"start":"2020-01-01"' in key.query
    assert key == CacheKey.of("demo", query)
    assert key != CacheKey.of("other", query)
    assert key != CacheKey.of("demo", query.model_copy(update={"series": ("B", "A")}))
    assert key != CacheKey.of("demo", Query(series=("A", "B"), vintage="latest"))


def test_a_query_with_a_field_named_like_a_credential_has_no_key() -> None:
    class Keyed(Query):
        api_key: str = "x"

    class Plain(Query):
        dataset: str = "NIPA"

    assert CacheKey.of("demo", Keyed(series=("A",))) is None
    plain = CacheKey.of("demo", Plain(series=("A",)))
    assert plain is not None
    assert plain.dataset == "NIPA"


def test_a_query_without_canonical_json_has_no_key() -> None:
    class Odd(Query):
        ratio: float = float("nan")

    assert CacheKey.of("demo", Odd(series=("A",))) is None


def test_the_offline_message_names_the_provider_and_the_series_and_the_reason() -> None:
    forbidden = offline_message("fred", ["GDPC1"], forbidden=True)
    assert "fred cannot be served offline" in forbidden
    assert "forbid storing" in forbidden
    assert "series GDPC1" in forbidden
    miss = offline_message("bls", ["A", "B"], forbidden=False)
    assert miss.startswith("offline mode has no cached copy of bls series A, B")
    broken = offline_message("bls", ["A"], forbidden=False, reason="no sqlite3")
    assert broken.endswith("no sqlite3")


def test_the_offline_message_shortens_a_long_series_list() -> None:
    names = [f"S{n}" for n in range(30)]
    text = offline_message("bls", names, forbidden=False)
    assert "S0, S1, S2, S3, S4 and 25 more" in text
    assert "S29" not in text


def test_a_live_origin_is_not_a_hit() -> None:
    assert Origin() == Origin(cache_hit=False, served_offline=False, warnings=())
    assert (OFFLINE_WARNING, DISCARDED_WARNING) == (
        "served_offline",
        "cache_entry_discarded",
    )


def test_a_fetch_becomes_a_data_source_record() -> None:
    when = dt.datetime(2026, 10, 14, 9, 30, tzinfo=dt.UTC)
    series = series_for(retrieved_at=when)
    origin = Origin(cache_hit=True, served_offline=True, warnings=(OFFLINE_WARNING,))
    record = Fetched(series, origin, "as_of:2020-03-31").source()
    assert isinstance(record, DataSource)
    assert (record.provider, record.series_id) == ("stub", "S")
    assert record.retrieved_at == when  # the original time, not the cache hit's
    assert (record.observation_start, record.observation_end) == (
        series.index[0],
        series.index[-1],
    )
    assert record.vintage == "as_of:2020-03-31"
    assert (record.cache_hit, record.served_offline) == (True, True)
    assert record.warnings == (OFFLINE_WARNING,)
    assert record.licence is series.meta.terms.licence
    assert record.attribution == series.meta.terms.attribution
    assert record.terms_url == series.meta.terms.terms_url
    assert DataSource.from_json(record.canonical_json()) == record


def test_a_table_and_an_empty_frame_have_records_too() -> None:
    table = ToyJson().fetch(
        toy_query(ToyJson, "fetch_table"), transport=replay_case(ToyJson, "fetch_table")
    )
    assert isinstance(table, Table)
    record = Fetched(table, Origin(), "latest").source()
    assert record.series_id == table.meta.table_id
    assert record.cache_hit is False
    assert record.warnings == ()
    empty = replace(series_for(), index=(), values=())
    nothing = Fetched(empty, Origin(), "latest").source()
    assert (nothing.observation_start, nothing.observation_end) == (None, None)
