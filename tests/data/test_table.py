# tests/data/test_table.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""pyeconomics.data.Table: columns over one index, bounds and lossless round trips."""

from __future__ import annotations

import json
from typing import Any

import pytest
from frame_builders import (
    HISTORY,
    column,
    month_ends,
    quarterly_meta,
    table_meta,
    two_column_table,
)

from pyeconomics.core import InputError
from pyeconomics.data import (
    MAX_COLUMNS,
    ColumnMeta,
    ObservationFrequency,
    RealtimePeriod,
    Series,
    Table,
    TableMeta,
)


def test_a_table_round_trips_through_canonical_json() -> None:
    table = two_column_table()
    text = table.canonical_json()
    back = Table.from_json(text)
    assert back == table
    assert back.canonical_json() == text
    data = json.loads(text)
    assert data["data"] == [[0.01, None, 0.03], [None, 0.05, 0.06]]
    assert [c["name"] for c in data["columns"]] == ["short", "long"]


def test_a_table_round_trips_through_pandas() -> None:
    table = two_column_table()
    frame = table.to_pandas()
    assert list(frame.columns) == ["short", "long"]
    assert [str(dtype) for dtype in frame.dtypes] == ["Float64", "Float64"]
    assert frame.index.dtype == "datetime64[us]"
    assert frame.isna().sum().tolist() == [1, 1]
    assert Table.from_pandas(frame) == table


def test_metadata_can_be_passed_when_attrs_are_gone() -> None:
    table = two_column_table()
    frame = table.to_pandas()
    frame.attrs.clear()
    with pytest.raises(InputError, match="no table metadata"):
        Table.from_pandas(frame)
    assert Table.from_pandas(frame, meta=table.meta, columns=table.columns) == table
    frame.attrs.update(table.to_pandas().attrs)
    assert Table.from_pandas(frame, meta=table.meta) == table
    assert Table.from_pandas(frame, columns=table.columns) == table


def test_the_frame_columns_must_match_their_metadata() -> None:
    table = two_column_table()
    frame = table.to_pandas()[["long", "short"]]
    with pytest.raises(InputError, match="are not"):
        Table.from_pandas(frame, meta=table.meta, columns=table.columns)


def test_a_column_is_a_series_with_the_tables_terms() -> None:
    table = two_column_table()
    series = table.column("long")
    assert isinstance(series, Series)
    assert series.values == (None, 0.05, 0.06)
    assert series.meta.series_id == "long_ID"
    assert series.meta.dataset == "EXAMPLE_TABLE"
    assert series.meta.title == "The long column"
    assert series.meta.terms == table.meta.terms
    assert series.index == table.index


def test_a_column_without_an_id_or_title_takes_its_name() -> None:
    table = Table(
        month_ends(1),
        (column("Mkt-RF", series_id=None, title=None),),
        ((0.01,),),
        table_meta(),
    )
    series = table.column("Mkt-RF")
    assert series.meta.series_id == series.meta.title == "Mkt-RF"
    with pytest.raises(KeyError, match="no column 'SMB'"):
        table.column("SMB")


def test_a_real_time_table_round_trips_and_its_columns_keep_their_periods() -> None:
    meta = quarterly_meta()
    table = Table(
        tuple(row[0] for row in HISTORY),
        (column("growth"),),
        (tuple(row[3] for row in HISTORY),),
        table_meta(frequency=ObservationFrequency.QUARTERLY, terms=meta.terms),
        tuple(RealtimePeriod(row[1], row[2]) for row in HISTORY),
    )
    assert table.has_realtime
    assert Table.from_json(table.canonical_json()) == table
    assert Table.from_pandas(table.to_pandas()) == table
    assert table.column("growth").realtime == table.realtime
    assert [str(p) for p in table.periods()][:2] == ["2008Q1", "2008Q1"]


def test_an_empty_table_round_trips() -> None:
    table = Table((), (), (), table_meta())
    assert len(table) == 0
    assert table.column_names == ()
    assert Table.from_json(table.canonical_json()) == table


@pytest.mark.parametrize(
    ("columns", "data", "message"),
    [
        ((column("a"), column("a")), ((1.0,), (2.0,)), "unique"),
        ((column("a"),), ((1.0,), (2.0,)), "2 columns of values for 1"),
        ((column("a"),), ((1.0, 2.0),), "2 values for 1 dates"),
        ((column("a"),), ((float("nan"),),), "never NaN"),
        (("a",), ((1.0,),), "must be a ColumnMeta"),
    ],
)
def test_columns_and_data_must_agree(
    columns: tuple[Any, ...], data: tuple[Any, ...], message: str
) -> None:
    with pytest.raises(InputError, match=message):
        Table(month_ends(1), columns, data, table_meta())


def test_a_table_holds_at_most_1000_columns() -> None:
    assert MAX_COLUMNS == 1_000
    names = [f"c{i}" for i in range(MAX_COLUMNS + 1)]
    columns = tuple(column(name, series_id=None, title=None) for name in names)
    widest = Table(
        month_ends(1), columns[:MAX_COLUMNS], ((0.0,),) * MAX_COLUMNS, table_meta()
    )
    assert len(widest.columns) == MAX_COLUMNS
    with pytest.raises(InputError, match="at most 1000"):
        Table(month_ends(1), columns, ((0.0,),) * (MAX_COLUMNS + 1), table_meta())


def test_a_table_refuses_more_than_100000_rows() -> None:
    days = month_ends(1) * 100_001
    with pytest.raises(InputError, match="at most 100000"):
        Table(days, (), (), table_meta())


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.update(type="series"), "not a table"),
        (lambda d: d.update(columns={"name": "short"}), "list or tuple"),
        (lambda d: d["columns"][0].update(unit="Percent"), "must be a JSON object"),
        (lambda d: d["columns"][0].pop("title"), "missing keys"),
        (lambda d: d["meta"].update(table_id=""), "must not be empty"),
        (lambda d: d["meta"].pop("terms"), "missing keys"),
    ],
)
def test_reading_refuses_any_other_form(
    change: Any,  # noqa: ANN401 - a mutator
    message: str,
) -> None:
    data = json.loads(two_column_table().canonical_json())
    change(data)
    with pytest.raises(InputError, match=message):
        Table.from_dict(data)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"provider": "Example Agency"}, "snake_case"),
        ({"frequency": "biweekly"}, "must name week_ends_on"),
        ({"frequency": "quarterly", "year_ends_in": 6}, None),
        ({"terms": "hosted-safe"}, "must be a Terms"),
        ({"source_dating": "midpoint"}, "must be one of"),
    ],
)
def test_table_metadata_is_checked(
    changes: dict[str, Any], message: str | None
) -> None:
    if message is None:
        assert table_meta(**changes).pandas_alias == "QE-JUN"
        return
    with pytest.raises(InputError, match=message):
        table_meta(**changes)


def test_table_metadata_round_trips() -> None:
    meta = table_meta(frequency="weekly", week_ends_on="friday", retrieved_at=None)
    assert TableMeta.from_dict(json.loads(json.dumps(meta.to_dict()))) == meta
    assert meta.pandas_alias == "W-FRI"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"name": ""}, "must not be empty"),
        ({"name": "x" * 129}, "at most 128"),
        ({"unit": None}, "must be a UnitRecord"),
        ({"seasonal_adjustment": "SA"}, "must be one of"),
        ({"series_id": "https://api.example.org/x"}, "must not contain a URL"),
    ],
)
def test_column_metadata_is_checked(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InputError, match=message):
        column(changes.pop("name", "a"), **changes)


def test_column_metadata_round_trips() -> None:
    meta = column("Mkt-RF", series_id=None, title=None)
    assert ColumnMeta.from_dict(json.loads(json.dumps(meta.to_dict()))) == meta
