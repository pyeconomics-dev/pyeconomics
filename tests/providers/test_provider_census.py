# tests/providers/test_provider_census.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Census's quirks, offline: the geography allowlist, ACS years, annotations, errors.

The bodies are Census-shaped with invented numbers. The key-refusal test goes
through the real HTTPS transport: Census answers a bad key with a redirect to a
page that echoes the request, and the provider must not follow it.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from canned import Canned, http, ok, param
from fakes import BANNED, FakePool, FakeRaw
from leakcheck import LeakCheck, canary

from pyeconomics.core.errors import InputError
from pyeconomics.data import (
    DataError,
    ResponseError,
    SeriesNotFoundError,
)
from pyeconomics.data.providers.census import Census, CensusQuery, acs_years
from pyeconomics.data.transport.base import Request
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment, Series


def acs(series: str = "acs/acs1/B19013_001E", **fields: Any) -> CensusQuery:
    base: dict[str, Any] = {
        "start": dt.date(2019, 1, 1),
        "end": dt.date(2022, 12, 31),
        "geography": "state:06",
    }
    return CensusQuery(series=(series,), **{**base, **fields})


def acs_answer(value: Any, variable: str = "B19013_001E") -> Any:
    return ok([["NAME", variable, "state"], ["California", value, "06"]])


# --- the geography allowlist -------------------------------------------------------


@pytest.mark.parametrize(
    "geography",
    [
        "us:1",
        "state:06",
        "county:037",
        "metropolitan statistical area/micropolitan statistical area:31080",
        "zip code tabulation area:90210",
    ],
)
def test_a_listed_level_and_numeric_code_are_accepted(geography: str) -> None:
    assert acs(geography=geography).geography == geography


@pytest.mark.parametrize(
    "geography",
    [
        "state:*",
        "state:06&key=x",
        "planet:3",
        "state:06 county:037",
        "state:",
        "STATE:06",
        "state:06\n",
    ],
)
def test_anything_else_is_refused_before_a_request(geography: str) -> None:
    with pytest.raises(InputError):
        Census().fetch({"series": ("acs/acs1/B19013_001E",), "geography": geography})


def test_within_takes_parent_clauses_separated_by_one_space() -> None:
    assert (
        acs(geography="tract:000100", within="state:06 county:037").within
        == "state:06 county:037"
    )
    with pytest.raises(InputError):
        Census().fetch(
            {
                "series": ("acs/acs5/B01001_001E",),
                "geography": "county:037",
                "within": "state:06;x",
            }
        )


# --- ACS ------------------------------------------------------------------------------


def test_the_acs1_skips_2020_and_asks_one_year_at_a_time() -> None:
    assert acs_years("acs1", acs()) == [2019, 2021, 2022]
    assert acs_years("acs5", acs(start=dt.date(2000, 1, 1))) == list(range(2009, 2023))
    with pytest.raises(DataError):
        acs_years("acs1", CensusQuery(series=("acs/acs1/B19013_001E",)))
    with pytest.raises(DataError):
        acs_years("acs1", acs(start=dt.date(2020, 1, 1), end=dt.date(2020, 12, 31)))


def test_an_acs_estimate_is_one_value_a_year_for_one_place() -> None:
    values = iter(["91905", "-666666666", None])
    transport = Canned(lambda _: acs_answer(next(values)))
    series = Census().fetch(acs(), transport=transport)
    assert isinstance(series, Series)
    assert series.index == (
        dt.date(2019, 12, 31),
        dt.date(2021, 12, 31),
        dt.date(2022, 12, 31),
    )
    assert series.values == (91905.0, None, None)
    assert series.meta.frequency is ObservationFrequency.ANNUAL
    assert series.meta.title == "B19013_001E, California"
    assert series.meta.notes == (
        "annotation: -666666666: too few sample observations to compute (2021-12-31)",
        "annotation: null: no data for this geography (2022-12-31)",
    )
    assert [request.path for request in transport.sent] == [
        "/data/2019/acs/acs1",
        "/data/2021/acs/acs1",
        "/data/2022/acs/acs1",
    ]
    first = transport.sent[0]
    assert (param(first, "get"), param(first, "for"), param(first, "in")) == (
        "NAME,B19013_001E",
        "state:06",
        None,
    )


def test_a_controlled_margin_of_error_is_zero_and_subject_tables_have_their_path() -> (
    None
):
    query = acs(
        "acs/acs5/subject/S1901_C01_012M",
        start=dt.date(2022, 1, 1),
        within="state:06",
        geography="county:037",
    )
    transport = Canned(lambda _: acs_answer("-555555555", "S1901_C01_012M"))
    series = Census().fetch(query, transport=transport)
    assert isinstance(series, Series)
    assert series.values == (0.0,)
    assert series.meta.notes[0].startswith("annotation: -555555555: controlled")
    assert transport.sent[0].path == "/data/2022/acs/acs5/subject"
    assert param(transport.sent[0], "in") == "state:06"


def test_no_data_for_any_year_is_not_found() -> None:
    with pytest.raises(SeriesNotFoundError):
        Census().fetch(
            acs(end=dt.date(2019, 12, 31)),
            transport=Canned(lambda _: ok(b"", status=204)),
        )


# --- time series ----------------------------------------------------------------------


def test_an_economic_indicator_is_a_monthly_series_with_its_filters() -> None:
    rows = [
        [
            "cell_value",
            "time_slot_id",
            "error_data",
            "category_code",
            "data_type_code",
            "seasonally_adj",
            "time",
            "us",
        ],
        ["700,123", "0", "no", "44X72", "SM", "yes", "2025-01", "1"],
        ["701,000", "0", "no", "44X72", "SM", "yes", "2025-02", "1"],
    ]
    transport = Canned(lambda _: ok(rows))
    query = CensusQuery(
        series=("eits/marts/44X72/SM/yes",),
        start=dt.date(2025, 1, 1),
        end=dt.date(2025, 2, 28),
    )
    series = Census().fetch(query, transport=transport)
    assert isinstance(series, Series)
    assert series.values == (700123.0, 701000.0)
    assert series.meta.frequency is ObservationFrequency.MONTHLY
    assert isinstance(series, Series)
    assert series.meta.seasonal_adjustment is SeasonalAdjustment.SEASONALLY_ADJUSTED
    request = transport.sent[0]
    assert request.path == "/data/timeseries/eits/marts"
    assert [
        param(request, name)
        for name in ("category_code", "data_type_code", "seasonally_adj", "for", "time")
    ] == [
        "44X72",
        "SM",
        "yes",
        "us:*",
        "from 2025-01 to 2025-02",
    ]


def test_a_quarterly_indicator_and_trade_values() -> None:
    quarterly = [["cell_value", "time"], ["1.5", "2025-Q1"], ["1.7", "2025-Q2"]]
    series = Census().fetch(
        CensusQuery(series=("eits/qss/X/Y/no",), start=dt.date(2025, 1, 1)),
        transport=Canned(lambda _: ok(quarterly)),
    )
    assert series.index == (dt.date(2025, 3, 31), dt.date(2025, 6, 30))
    trade = [
        ["GEN_VAL_MO", "CTY_NAME", "CTY_CODE", "time"],
        ["4000000", "CHINA", "5700", "2025-01"],
    ]
    transport = Canned(lambda _: ok(trade))
    imports = Census().fetch(
        CensusQuery(series=("intltrade/imports/hs/5700",), end=dt.date(2025, 1, 31)),
        transport=transport,
    )
    assert isinstance(imports, Series)
    assert imports.values == (4000000.0,)
    assert isinstance(imports, Series)
    assert imports.meta.unit.currency == "USD"
    assert param(transport.sent[0], "get") == "GEN_VAL_MO,CTY_NAME"
    assert param(transport.sent[0], "time") == "to 2025-01"


@pytest.mark.parametrize(
    "rows",
    [
        [["x", "time"], ["1", "2025-01"]],
        [["cell_value", "time"], ["1", "2025"]],
        [["cell_value", "time"], ["1", "2025-01"], ["1", "2025-Q1"]],
    ],
    ids=["no-value-column", "undocumented-time", "mixed-frequencies"],
)
def test_a_malformed_time_series_is_refused(rows: list[list[str]]) -> None:
    with pytest.raises(ResponseError):
        Census().fetch(
            CensusQuery(series=("eits/marts/A/B/yes",), start=dt.date(2025, 1, 1)),
            transport=Canned(lambda _: ok(rows)),
        )


@pytest.mark.parametrize(
    "fields",
    [
        {"series": ("bogus/series",)},
        {"series": ("eits/marts/A/B/yes",)},
        {
            "series": ("acs/acs1/B01001_001E", "acs/acs1/B01001_002E"),
            "start": dt.date(2024, 1, 1),
            "end": dt.date(2024, 1, 1),
        },
    ],
    ids=["unknown-form", "no-time-window", "two-ids"],
)
def test_a_query_census_cannot_answer_is_refused_before_a_request(
    fields: dict[str, Any],
) -> None:
    transport = Canned(lambda _: ok([]))
    with pytest.raises(DataError):
        Census().fetch(fields, transport=transport)
    assert transport.sent == []


# --- errors ---------------------------------------------------------------------------


def test_a_refused_key_is_a_redirect_the_transport_does_not_follow() -> None:
    held = canary("census")
    redirect = FakeRaw(
        302,
        b"",
        {
            "Location": "https://api.census.gov/data/invalid_key.html",
            "Set-Cookie": f"originalReferer=https://api.census.gov/data?key={held.value}",
        },
    )
    pool = FakePool(redirect, BANNED)
    check = LeakCheck(held)
    check.run(
        lambda: Census().fetch(
            acs(end=dt.date(2019, 12, 31)), key=held.value, transport=http(pool)
        )
    )
    assert len(pool.calls) == 1, "the redirect was not followed"
    assert any(name == "exception:CredentialError" for name in check.sinks)
    check.assert_clean()


def test_an_unknown_variable_is_not_found() -> None:
    answer = ok(b"error: unknown variable 'B99999_999E'", status=400)
    with pytest.raises(SeriesNotFoundError):
        Census().fetch(
            acs("acs/acs1/B99999_999E", end=dt.date(2019, 12, 31)),
            transport=Canned(lambda _: answer),
        )
    with pytest.raises(ResponseError):
        Census().fetch(
            acs(end=dt.date(2019, 12, 31)),
            transport=Canned(lambda _: ok(b"other", status=400)),
        )


def test_a_body_that_is_not_rows_is_refused() -> None:
    with pytest.raises(ResponseError):
        Census().fetch(
            acs(end=dt.date(2019, 12, 31), geography="state:01"),
            transport=Canned(lambda _: ok({"a": 1})),
        )
    with pytest.raises(SeriesNotFoundError):
        Census().fetch(
            acs(end=dt.date(2019, 12, 31), geography="state:02"),
            transport=Canned(lambda _: ok([["NAME"], ["X"]])),
        )


def test_build_requests_accepts_a_plain_query() -> None:
    from pyeconomics.data import Query  # noqa: PLC0415

    (request,) = Census().build_requests(
        Query(series=("eits/marts/A/B/yes",), start=dt.date(2025, 1, 1))
    )
    assert isinstance(request, Request)
    assert param(request, "for") == "us:*"
