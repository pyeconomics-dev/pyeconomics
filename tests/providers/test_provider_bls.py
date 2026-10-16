# tests/providers/test_provider_bls.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""BLS's quirks, offline: keyed v2 and keyless v1, chunks, periods, footnotes, errors.

The bodies are BLS-shaped with invented numbers. The keyed and keyless paths
go through the real HTTPS transport over a fake pool, so the tests see which
API was asked and that the key travelled in the body, and only there.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import pytest
from canned import Canned, http, ok, rounded
from fakes import FakePool, FakeRaw
from leakcheck import LeakCheck, canary

from pyeconomics.data import (
    DataError,
    Query,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
    Table,
)
from pyeconomics.data.credentials import withheld
from pyeconomics.data.providers.bls import (
    BLS_NOTICE,
    KEYED_LIMITS,
    KEYLESS_LIMITS,
    V1_PATH,
    V2_PATH,
    Bls,
    period_day,
)
from pyeconomics.data.transport.base import Request
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment, Series

CATALOG = {
    "series_title": "(Seas) Unemployment Rate",
    "series_id": "LNS14000000",
    "seasonality": "Seasonally Adjusted",
    "survey_name": "Labor Force Statistics from the Current Population Survey",
    "measure_data_type": "Percent or rate",
}


def point(
    year: str, period: str, value: str, *notes: tuple[str, str]
) -> dict[str, Any]:
    footnotes = [{"code": code, "text": text} for code, text in notes] or [{}]
    return {"year": year, "period": period, "value": value, "footnotes": footnotes}


def body(
    *series: dict[str, Any],
    status: str = "REQUEST_SUCCEEDED",
    message: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "responseTime": 1,
        "message": message or [],
        "Results": {"series": list(series)},
    }


def entry(
    series_id: str, data: list[dict[str, Any]], catalog: dict[str, Any] | None = None
) -> dict[str, Any]:
    found: dict[str, Any] = {"seriesID": series_id, "data": data}
    if catalog is not None:
        found["catalog"] = catalog
    return found


def raw(document: dict[str, Any]) -> FakeRaw:
    return FakeRaw(
        200, json.dumps(document).encode(), {"Content-Type": "application/json"}
    )


QUERY = Query(
    series=("LNS14000000",), start=dt.date(2025, 1, 1), end=dt.date(2025, 12, 31)
)


# --- keyed and keyless ----------------------------------------------------------------


def test_a_key_sends_v2_with_the_key_in_the_body_and_reads_the_catalog() -> None:
    held = canary("bls")
    data = [
        point("2025", "M02", "4.1"),
        point("2025", "M01", "4.0"),
        point("2025", "M13", "4.05"),
    ]
    pool = FakePool(raw(body(entry("LNS14000000", data, CATALOG))))
    check = LeakCheck(held)
    series = check.run(lambda: Bls().fetch(QUERY, key=held.value, transport=http(pool)))
    assert isinstance(series, Series)
    (call,) = pool.calls
    assert call.url == f"https://api.bls.gov{V2_PATH}"
    sent = json.loads(call.body or b"{}")
    assert sent["registrationkey"] == held.value
    assert (sent["seriesid"], sent["startyear"], sent["endyear"], sent["catalog"]) == (
        ["LNS14000000"],
        "2025",
        "2025",
        True,
    )
    assert series.index == (dt.date(2025, 1, 31), dt.date(2025, 2, 28))
    assert rounded(series.values) == (0.040, 0.041)
    meta = series.meta
    assert meta.title == "(Seas) Unemployment Rate"
    assert meta.seasonal_adjustment is SeasonalAdjustment.SEASONALLY_ADJUSTED
    assert meta.unit.kind is not None
    assert meta.unit.kind.value == "rate"
    assert meta.notes == ()
    check.add("series", series.canonical_json())
    check.assert_clean()


def test_without_a_key_it_reads_v1_keyless_with_no_credential_error() -> None:
    pool = FakePool(raw(body(entry("LNS14000000", [point("2025", "M01", "4.0")]))))
    with withheld("bls"):
        series = Bls().fetch(QUERY, transport=http(pool))
    (call,) = pool.calls
    assert call.url == f"https://api.bls.gov{V1_PATH}"
    sent = json.loads(call.body or b"{}")
    assert "registrationkey" not in sent
    assert "catalog" not in sent
    assert isinstance(series, Series)
    assert series.values == (4.0,), (
        "without the catalog the unit is unknown: as published"
    )
    assert series.meta.unit.kind is None
    assert series.meta.notes[-1].startswith("bls_keyless: ")
    assert series.meta.title == "LNS14000000"


def test_the_isolated_environment_has_no_key_so_a_plain_fetch_is_keyless() -> None:
    pool = FakePool(raw(body(entry("LNS14000000", [point("2025", "M01", "4.0")]))))
    Bls().fetch(QUERY, transport=http(pool))
    assert pool.calls[0].url.endswith(V1_PATH)


@pytest.mark.parametrize(
    ("keyed", "limits"), [(True, KEYED_LIMITS), (False, KEYLESS_LIMITS)]
)
def test_a_large_query_is_split_into_chunks_bls_accepts(
    keyed: bool,  # noqa: FBT001 - a parametrized flag
    limits: tuple[int, int],
) -> None:
    series_cap, year_cap = limits
    ids = tuple(f"CUUR0000SA{i:03d}" for i in range(series_cap + 1))
    query = Query(
        series=ids, start=dt.date(2000, 1, 1), end=dt.date(2000 + year_cap, 12, 31)
    )
    transport = Canned(lambda request: ok(body()))
    table = Bls().fetch(query, key="k" * 32 if keyed else None, transport=transport)
    assert isinstance(table, Table)
    assert len(table.columns) == series_cap + 1
    assert len(transport.sent) == 4
    sizes = {len(request.body["seriesid"]) for request in transport.sent}
    assert sizes == {series_cap, 1}
    windows = {
        (request.body["startyear"], request.body["endyear"])
        for request in transport.sent
    }
    assert windows == {
        ("2000", str(2000 + year_cap - 1)),
        (str(2000 + year_cap), str(2000 + year_cap)),
    }


def test_without_dates_bls_chooses_its_latest_years() -> None:
    transport = Canned(
        lambda request: ok(body(entry("LNS14000000", [point("2025", "M01", "4.0")])))
    )
    Bls().fetch(Query(series=("LNS14000000",)), transport=transport)
    assert "startyear" not in transport.sent[0].body
    start_only = Canned(lambda request: ok(body(entry("LNS14000000", []))))
    Bls().fetch(
        Query(series=("LNS14000000",), start=dt.date(2020, 1, 1)), transport=start_only
    )
    assert (
        start_only.sent[0].body["startyear"],
        start_only.sent[0].body["endyear"],
    ) == ("2020", "2029")


# --- periods, missing values and footnotes --------------------------------------------


@pytest.mark.parametrize(
    ("period", "day"),
    [
        ("M01", dt.date(2026, 1, 31)),
        ("M12", dt.date(2026, 12, 31)),
        ("Q01", dt.date(2026, 3, 31)),
        ("Q04", dt.date(2026, 12, 31)),
        ("S01", dt.date(2026, 6, 30)),
        ("S02", dt.date(2026, 12, 31)),
        ("A01", dt.date(2026, 12, 31)),
    ],
)
def test_a_period_is_indexed_by_its_last_day(period: str, day: dt.date) -> None:
    assert period_day("2026", period) == day


@pytest.mark.parametrize("period", ["M14", "Q00", "X01", "M1", "S04"])
def test_an_undocumented_period_is_refused(period: str) -> None:
    with pytest.raises(ResponseError):
        period_day("2026", period)


def test_missing_values_and_footnotes_are_recorded() -> None:
    data = [
        point("2026", "M09", "159.1", ("P", "preliminary")),
        point("2026", "M08", "159.0", ("P", "preliminary")),
        point("2026", "M07", "-", ("X", "Data unavailable")),
        point("2026", "M06", "158.8"),
    ]
    transport = Canned(
        lambda _: ok(
            body(
                entry(
                    "CES0000000001",
                    data,
                    {
                        "series_title": "All employees",
                        "seasonality": "Not Seasonally Adjusted",
                    },
                )
            )
        )
    )
    series = Bls().fetch(
        Query(
            series=("CES0000000001",),
            start=dt.date(2026, 1, 1),
            end=dt.date(2026, 12, 31),
        ),
        transport=transport,
    )
    assert isinstance(series, Series)
    assert series.values == (158.8, None, 159.0, 159.1)
    assert series.meta.notes == (
        "footnote: P preliminary (2026-08-31, 2026-09-30)",
        "footnote: X Data unavailable (2026-07-31)",
    )
    assert isinstance(series, Series)
    assert series.meta.seasonal_adjustment is SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED


def test_quarterly_and_semiannual_series_and_the_access_date() -> None:
    data = [
        point("2025", "S01", "300.0"),
        point("2025", "S02", "305.0"),
        point("2025", "S03", "302.0"),
    ]
    series = Bls().fetch(
        QUERY, transport=Canned(lambda _: ok(body(entry("LNS14000000", data))))
    )
    assert series.meta.frequency is ObservationFrequency.SEMIANNUAL
    assert series.index == (dt.date(2025, 6, 30), dt.date(2025, 12, 31))
    notice = series.meta.terms.notice or ""
    assert notice.startswith(BLS_NOTICE)
    assert notice.endswith("on 2026-10-15.")


def test_two_series_make_a_table_and_mixed_frequencies_are_refused() -> None:
    monthly = entry("A1", [point("2025", "M01", "1")])
    other = entry("B2", [point("2025", "M02", "2")])
    table = Bls().fetch(
        Query(
            series=("A1", "B2"), start=dt.date(2025, 1, 1), end=dt.date(2025, 12, 31)
        ),
        transport=Canned(lambda _: ok(body(monthly, other))),
    )
    assert isinstance(table, Table)
    assert table.data == ((1.0, None), (None, 2.0))
    quarterly = entry("B2", [point("2025", "Q01", "2")])
    with pytest.raises(DataError, match="one frequency"):
        Bls().fetch(
            Query(
                series=("A1", "B2"),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 11, 30),
            ),
            transport=Canned(lambda _: ok(body(monthly, quarterly))),
        )


# --- errors in an HTTP 200 body ------------------------------------------------------


def test_a_refused_key_is_a_credential_error_that_never_repeats_the_key() -> None:
    held = canary("bls")
    refusal = body(
        status="REQUEST_NOT_PROCESSED",
        message=[
            (
                f"The key:{held.value} provided by the User is invalid. "
                "Please provide a proper key"
            )
        ],
    )
    check = LeakCheck(held)
    check.run(
        lambda: Bls().fetch(
            QUERY, key=held.value, transport=Canned(lambda _: ok(refusal))
        )
    )
    assert any(name == "exception:CredentialError" for name in check.sinks)
    check.assert_clean()


@pytest.mark.parametrize(
    ("message", "error"),
    [
        (
            (
                "daily threshold for total number of requests allocated to the "
                "user has been reached"
            ),
            RateLimitError,
        ),
        ("Something unexpected", ResponseError),
    ],
)
def test_a_request_not_processed_maps_to_the_taxonomy(
    message: str, error: type[Exception]
) -> None:
    refusal = body(status="REQUEST_NOT_PROCESSED", message=[message])
    with pytest.raises(error):
        Bls().fetch(QUERY, transport=Canned(lambda _: ok(refusal)))


def test_an_invalid_series_is_not_found() -> None:
    answer = body(
        entry("ZZZNOTASERIES1", []),
        message=["Invalid Series for Series ZZZNOTASERIES1"],
    )
    with pytest.raises(SeriesNotFoundError, match="ZZZNOTASERIES1"):
        Bls().fetch(
            Query(
                series=("ZZZNOTASERIES1",),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 12, 31),
            ),
            transport=Canned(lambda _: ok(answer)),
        )


def test_the_keyless_daily_limit_counts_only_keyless_requests() -> None:
    from fakes import FakeClock  # noqa: PLC0415

    from pyeconomics.data.transport.ratelimit import ProviderLimiter  # noqa: PLC0415

    clock = FakeClock()
    limiter = ProviderLimiter("bls", Bls.info.rate_limits, clock.monotonic)
    for _ in range(25):
        limiter.acquire(clock.sleep)
    with pytest.raises(RateLimitError):
        limiter.acquire(clock.sleep)
    assert limiter.acquire(clock.sleep, keyed=True) >= 0.0


def test_requests_name_only_the_series_they_concern() -> None:
    (one,) = Bls().build_requests(QUERY)
    assert isinstance(one, Request)
    assert one.series == "LNS14000000"
    (two,) = Bls().build_requests(
        Query(series=("A1", "B2"), start=dt.date(2025, 1, 1), end=dt.date(2025, 2, 1))
    )
    assert two.series is None
