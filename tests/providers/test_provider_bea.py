# tests/providers/test_provider_bea.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""BEA's quirks, offline: series ids, periods, separators, markers, errors.

The bodies are BEA-shaped with invented numbers.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from canned import Canned, ok, param, rounded
from leakcheck import LeakCheck, canary

from pyeconomics.data import (
    CredentialError,
    DataError,
    Query,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
    Table,
)
from pyeconomics.data.providers.bea import (
    BEA_TERMS,
    REVISED_NOTE,
    Bea,
    Selection,
    parse_id,
    time_period,
)
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment, Series

NOTES = [
    {
        "NoteRef": "T10101",
        "NoteText": "Table 1.1.1. Percent Change From Preceding Period",
    },
    {"NoteRef": "T10101.1", "NoteText": "Seasonally adjusted at annual rates."},
]


def nipa(
    line: str,
    period: str,
    value: str,
    unit: str = "Percent change, annual rate",
    mult: str = "0",
) -> dict[str, Any]:
    return {
        "TableName": "T10101",
        "SeriesCode": f"A{line}",
        "LineNumber": line,
        "LineDescription": "Gross domestic product" if line == "1" else f"Line {line}",
        "TimePeriod": period,
        "METRIC_NAME": "Fisher Quantity Index",
        "CL_UNIT": unit,
        "UNIT_MULT": mult,
        "DataValue": value,
        "NoteRef": "T10101",
    }


def results(rows: list[dict[str, Any]], notes: list[dict[str, str]] = NOTES) -> Any:
    return ok(
        {
            "BEAAPI": {
                "Request": {"RequestParam": []},
                "Results": {"Data": rows, "Notes": notes},
            }
        }
    )


def error(code: str, text: str) -> Any:
    return ok(
        {
            "BEAAPI": {
                "Request": {},
                "Results": {
                    "Error": {"APIErrorCode": code, "APIErrorDescription": text}
                },
            }
        }
    )


# --- series ids and periods -----------------------------------------------------------


@pytest.mark.parametrize(
    ("series_id", "selection"),
    [
        ("NIPA/T10101/Q/1", Selection("NIPA", "T10101", "Q", "1", None)),
        ("NIPA/T10101/A", Selection("NIPA", "T10101", "A", None, None)),
        (
            "NIUnderlyingDetail/U20305/M/2",
            Selection("NIUnderlyingDetail", "U20305", "M", "2", None),
        ),
        (
            "Regional/SAINC1/3/06000",
            Selection("Regional", "SAINC1", None, "3", "06000"),
        ),
        (
            "Regional/CAINC1/1/STATE",
            Selection("Regional", "CAINC1", None, "1", "STATE"),
        ),
        (
            "ITA/BalGds/AllCountries/QSA",
            Selection("ITA", "BalGds", "QSA", None, "AllCountries"),
        ),
    ],
)
def test_a_series_id_names_dataset_and_selection(
    series_id: str, selection: Selection
) -> None:
    assert parse_id(series_id) == selection


@pytest.mark.parametrize(
    "series_id",
    [
        "GDP",
        "NIPA/T10101/W/1",
        "Regional/SAINC1/3/COUNTY",
        "Regional/SAINC1/3/0600",
        "ITA/x/y/Q",
        "NIPA/T1 0/Q",
        "NIPA//Q",
    ],
)
def test_an_id_outside_the_forms_is_refused(series_id: str) -> None:
    with pytest.raises(DataError):
        parse_id(series_id)


@pytest.mark.parametrize(
    ("text", "day"),
    [
        ("2024", dt.date(2024, 12, 31)),
        ("2024Q1", dt.date(2024, 3, 31)),
        ("2024M02", dt.date(2024, 2, 29)),
        ("2024M11", dt.date(2024, 11, 30)),
    ],
)
def test_a_time_period_is_indexed_by_its_last_day(text: str, day: dt.date) -> None:
    assert time_period(text) == day


@pytest.mark.parametrize("text", ["2024Q5", "2024M13", "24Q1", "2024W1"])
def test_an_undocumented_time_period_is_refused(text: str) -> None:
    with pytest.raises(ResponseError):
        time_period(text)


# --- values ---------------------------------------------------------------------------


def test_a_nipa_line_is_a_decimal_rate_with_revised_data_recorded() -> None:
    rows = [
        nipa("1", "2025Q1", "-0.5"),
        nipa("1", "2025Q2", "3.8"),
        nipa("1", "2025Q3", "(NA)"),
        nipa("2", "2025Q1", "9.9"),
    ]
    transport = Canned(lambda _: results(rows))
    series = Bea().fetch(
        Query(
            series=("NIPA/T10101/Q/1",),
            start=dt.date(2025, 1, 1),
            end=dt.date(2025, 12, 31),
        ),
        transport=transport,
    )
    assert isinstance(series, Series)
    assert series.index == (
        dt.date(2025, 3, 31),
        dt.date(2025, 6, 30),
        dt.date(2025, 9, 30),
    )
    assert rounded(series.values) == (-0.005, 0.038, None)
    meta = series.meta
    assert meta.notes[0] == REVISED_NOTE
    assert meta.notes[1] == "missing: BEA marks (NA) (2025-09-30)"
    assert (
        meta.seasonal_adjustment is SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE
    )
    assert meta.frequency is ObservationFrequency.QUARTERLY
    assert meta.terms == BEA_TERMS
    request = transport.sent[0]
    assert [
        param(request, name)
        for name in ("method", "datasetname", "TableName", "Frequency", "Year")
    ] == [
        "GetData",
        "NIPA",
        "T10101",
        "Q",
        "2025",
    ]


def test_thousands_separators_and_unit_mult_set_the_scale() -> None:
    rows = [
        nipa("1", "2024", "29,184.9", unit="Level", mult="9"),
        nipa("1", "2025", "30,000.1", unit="Level", mult="9"),
    ]
    for row in rows:
        row["METRIC_NAME"] = "Current Dollars"
    series = Bea().fetch(
        Query(
            series=("NIPA/T10105/A/1",),
            start=dt.date(2024, 1, 1),
            end=dt.date(2025, 12, 31),
        ),
        transport=Canned(lambda _: results(rows)),
    )
    assert isinstance(series, Series)
    assert series.values == (29184.9, 30000.1)
    assert isinstance(series, Series)
    unit = series.meta.unit
    assert (unit.kind.value if unit.kind else None, unit.scale, unit.currency) == (
        "money",
        1e9,
        "USD",
    )


def test_a_table_without_a_line_holds_every_line() -> None:
    rows = [
        nipa("1", "2024", "2.8"),
        nipa("2", "2024", "2.5"),
        nipa("1", "2025", "2.0"),
        nipa("2", "2025", "(D)"),
    ]
    table = Bea().fetch(
        Query(
            series=("NIPA/T10101/A",),
            start=dt.date(2024, 1, 1),
            end=dt.date(2025, 12, 31),
        ),
        transport=Canned(lambda _: results(rows)),
    )
    assert isinstance(table, Table)
    assert [column.series_id for column in table.columns] == [
        "NIPA/T10101/A/1",
        "NIPA/T10101/A/2",
    ]
    assert tuple(rounded(column) for column in table.data) == (
        (0.028, 0.02),
        (0.025, None),
    )
    assert table.meta.title == "Table 1.1.1. Percent Change From Preceding Period"
    assert REVISED_NOTE in table.meta.notes


def test_a_regional_state_selection_is_a_table_of_places() -> None:
    rows = [
        {
            "Code": "SAINC1-3",
            "GeoFips": "01000",
            "GeoName": "Alabama",
            "TimePeriod": "2024",
            "CL_UNIT": "Dollars",
            "UNIT_MULT": "0",
            "DataValue": "52,000",
        },
        {
            "Code": "SAINC1-3",
            "GeoFips": "02000",
            "GeoName": "Alaska",
            "TimePeriod": "2024",
            "CL_UNIT": "Dollars",
            "UNIT_MULT": "0",
            "DataValue": "70,000",
        },
    ]
    transport = Canned(lambda _: results(rows, notes=[]))
    table = Bea().fetch(
        Query(
            series=("Regional/SAINC1/3/STATE",),
            start=dt.date(2024, 1, 1),
            end=dt.date(2024, 12, 31),
        ),
        transport=transport,
    )
    assert isinstance(table, Table)
    assert [column.name for column in table.columns] == ["Alabama", "Alaska"]
    assert table.data == ((52000.0,), (70000.0,))
    assert [
        param(transport.sent[0], name) for name in ("LineCode", "GeoFips", "Year")
    ] == ["3", "STATE", "2024"]


def test_an_ita_indicator_is_one_series() -> None:
    rows = [
        {
            "Indicator": "BalGds",
            "AreaOrCountry": "AllCountries",
            "Frequency": "QSA",
            "TimeSeriesId": "BalGds_AllCountries_QSA",
            "TimeSeriesDescription": "Balance on goods",
            "TimePeriod": "2025Q1",
            "CL_UNIT": "USD",
            "UNIT_MULT": "6",
            "DataValue": "-300,000",
        },
    ]
    transport = Canned(
        lambda _: results(
            rows,
            notes=[
                {
                    "NoteRef": "1",
                    "NoteText": "Quarterly estimates are seasonally adjusted.",
                }
            ],
        )
    )
    series = Bea().fetch(
        Query(series=("ITA/BalGds/AllCountries/QSA",)), transport=transport
    )
    assert isinstance(series, Series)
    assert series.values == (-300000.0,)
    assert series.meta.unit.scale == 1e6
    assert series.meta.seasonal_adjustment is SeasonalAdjustment.SEASONALLY_ADJUSTED
    assert [
        param(transport.sent[0], name)
        for name in ("Indicator", "AreaOrCountry", "Frequency", "Year")
    ] == [
        "BalGds",
        "AllCountries",
        "QSA",
        "All",
    ]


def test_a_missing_line_is_not_found_and_two_ids_are_refused() -> None:
    with pytest.raises(SeriesNotFoundError):
        Bea().fetch(
            Query(series=("NIPA/T10101/Q/99",)),
            transport=Canned(lambda _: results([nipa("1", "2025Q1", "1")])),
        )
    with pytest.raises(DataError, match="one series id"):
        Bea().fetch(
            Query(series=("NIPA/T10101/Q/1", "NIPA/T10101/Q/2")),
            transport=Canned(
                lambda _: results([nipa("1", "2025Q1", "1"), nipa("2", "2025Q1", "1")])
            ),
        )


# --- errors ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "text", "expected"),
    [
        ("1", "Invalid Request - Invalid API UserId.", CredentialError),
        ("7", "Request Denied - exceeded Requests per minute quota.", RateLimitError),
        ("40", "TableName entered is invalid", SeriesNotFoundError),
        ("99", "Something else", ResponseError),
    ],
)
def test_beas_error_object_maps_to_the_taxonomy(
    code: str, text: str, expected: type[Exception]
) -> None:
    with pytest.raises(expected):
        Bea().fetch(
            Query(series=("NIPA/T10101/Q/1",)),
            transport=Canned(lambda _: error(code, text)),
        )


def test_an_error_at_the_root_or_in_a_list_is_read_too() -> None:
    root = ok(
        {
            "BEAAPI": {
                "Error": [
                    {"APIErrorCode": "1", "APIErrorDescription": "Invalid API UserId"}
                ]
            }
        }
    )
    with pytest.raises(CredentialError):
        Bea().fetch(
            Query(series=("NIPA/T10101/A/1",)), transport=Canned(lambda _: root)
        )


def test_an_empty_body_or_a_foreign_one_is_refused() -> None:
    with pytest.raises(CredentialError):
        Bea().fetch(
            Query(series=("NIPA/T10101/M/1",)), transport=Canned(lambda _: ok(b""))
        )
    with pytest.raises(ResponseError):
        Bea().fetch(
            Query(series=("NIPA/T10101/M/2",)),
            transport=Canned(lambda _: ok({"other": 1})),
        )


def test_a_userid_echoed_in_the_body_reaches_no_sink() -> None:
    held = canary("bea")
    echoed = ok(
        {
            "BEAAPI": {
                "Request": {
                    "RequestParam": [
                        {"ParameterName": "USERID", "ParameterValue": held.value}
                    ]
                },
                "Results": {
                    "Error": {
                        "APIErrorCode": "1",
                        "APIErrorDescription": "Invalid API UserId.",
                    }
                },
            }
        }
    )
    check = LeakCheck(held)
    check.run(
        lambda: Bea().fetch(
            Query(series=("NIPA/T10101/A/3",)),
            key=held.value,
            transport=Canned(lambda _: echoed),
        )
    )
    check.assert_clean()
