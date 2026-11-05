# tests/results/test_tables.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Results as pandas, Polars, Arrow and Parquet, with and without the libraries."""

from __future__ import annotations

import datetime as dt
import json
import sys
from typing import TYPE_CHECKING, Any

import pandas as pd
import pytest
import toy_models as tm
import toy_results_models as rm

from pyeconomics.core import (
    MissingOptionalDependencyError,
    run_model,
    run_model_batch,
)
from pyeconomics.core.tables import HASH_COLUMN, MANIFEST_METADATA_KEY, columns_of

if TYPE_CHECKING:
    from pathlib import Path

ZERO = {"face_value": 100, "rate": 0.05, "years": 10}


def zero() -> Any:  # noqa: ANN401 - a Result
    return run_model(tm.zero_coupon, **ZERO)


# --- the layout -----------------------------------------------------------------


def test_the_columns_mirror_the_dict_paths_and_end_with_the_hash() -> None:
    result = zero()
    columns = columns_of([result])
    assert list(columns) == [
        "inputs.face_value",
        "inputs.rate",
        "inputs.years",
        "outputs.price",
        HASH_COLUMN,
    ]
    assert columns[HASH_COLUMN] == [result.manifest.result_sha256]
    assert columns["inputs.face_value"] == [100.0]


def test_a_row_without_a_field_holds_none_there() -> None:
    batch = run_model_batch(
        tm.time_value,
        [
            {"calculation": "present_value", "future_value": 1, "rate": 0, "years": 1},
            {"calculation": "future_value", "present_value": 1, "rate": 0, "years": 1},
        ],
    )
    columns = columns_of(batch)
    assert columns["inputs.future_value"] == [1.0, None]
    assert columns["inputs.present_value"] == [None, 1.0]
    assert columns["outputs.calculation"] == ["present_value", "future_value"]


# --- pandas ---------------------------------------------------------------------


def test_to_pandas_has_one_row_with_typed_columns() -> None:
    frame = zero().to_pandas()
    assert frame.shape == (1, 5)
    assert frame["inputs.face_value"].dtype == "float64"
    assert frame.loc[0, "outputs.price"] == pytest.approx(100 / 1.05**10)
    assert len(frame.loc[0, HASH_COLUMN]) == 64


def test_pandas_keeps_integers_and_arrays() -> None:
    result = run_model(rm.growth, start=100, rate=0.1, periods=2)
    frame = result.to_pandas()
    assert frame["inputs.periods"].dtype == "int64"
    assert frame.loc[0, "outputs.period"] == [0, 1, 2]
    assert frame.loc[0, "outputs.balance"] == pytest.approx([100, 110, 121])


def test_pandas_dates_are_microsecond_datetimes() -> None:
    batch = run_model_batch(
        rm.dated,
        [{"start": "2026-01-31", "days": 30}, {"start": "2026-02-28", "days": 0}],
    )
    frame = batch.to_pandas()
    assert str(frame["inputs.start"].dtype) == "datetime64[us]"
    assert str(frame["outputs.end"].dtype) == "datetime64[us]"
    assert frame.loc[0, "outputs.end"] == pd.Timestamp("2026-03-02")
    # A null output is NaN in pandas, and the other row keeps its value.
    assert frame["outputs.per_day"].isna().loc[1]
    assert frame.loc[0, "outputs.per_day"] == pytest.approx(1 / 30)
    assert frame["outputs.per_day"].dtype == "float64"
    assert frame.loc[0, "outputs.dates"] == [dt.date(2026, 1, 31), dt.date(2026, 3, 2)]


def test_pandas_strings_and_missing_values() -> None:
    batch = run_model_batch(
        tm.time_value,
        [
            {"calculation": "present_value", "future_value": 1, "rate": 0, "years": 1},
            {"calculation": "future_value", "present_value": 1, "rate": 0, "years": 1},
        ],
    )
    frame = batch.to_pandas()
    assert frame["outputs.calculation"].tolist() == ["present_value", "future_value"]
    assert frame["inputs.future_value"].isna().loc[1]


def test_a_batch_frame_has_a_row_per_result() -> None:
    batch = run_model_batch(tm.zero_coupon, [ZERO, {**ZERO, "years": 5}])
    frame = batch.to_pandas()
    assert frame.shape == (2, 5)
    assert frame[HASH_COLUMN].tolist() == [r.manifest.result_sha256 for r in batch]


def test_all_none_and_integer_columns_with_missing_values() -> None:
    from pyeconomics.core.tables import to_pandas  # noqa: PLC0415

    frame = to_pandas(
        {
            "empty": [None, None],
            "ints": [1, None],
            "flags": [True, None],
            "all_flags": [True, False],
            "mixed": [1, "a"],
        }
    )
    assert frame["empty"].dtype == "object"
    assert str(frame["ints"].dtype) == "Int64"
    assert str(frame["flags"].dtype) == "boolean"
    assert frame["all_flags"].dtype == "bool"
    assert frame["mixed"].dtype == "object"


# --- Polars and Arrow, when installed -------------------------------------------


def test_to_polars() -> None:
    polars = pytest.importorskip("polars")
    frame = run_model(rm.growth, start=100, rate=0.1, periods=2).to_polars()
    assert isinstance(frame, polars.DataFrame)
    assert frame.shape == (1, 7)
    assert frame["outputs.period"].to_list() == [[0, 1, 2]]
    batch = run_model_batch(
        rm.dated,
        [{"start": "2026-01-31", "days": 30}, {"start": "2026-02-28", "days": 0}],
    ).to_polars()
    assert batch["outputs.end"].dtype == polars.Date
    assert batch["outputs.per_day"].to_list() == [pytest.approx(1 / 30), None]


def test_to_arrow_carries_the_manifest_in_the_schema_metadata() -> None:
    pyarrow = pytest.importorskip("pyarrow")
    result = zero()
    table = result.to_arrow()
    assert isinstance(table, pyarrow.Table)
    assert table.num_rows == 1
    assert table.column_names == list(columns_of([result]))
    stored = json.loads(table.schema.metadata[MANIFEST_METADATA_KEY.encode()])
    assert stored == result.manifest.to_dict()
    assert table.column("outputs.price").to_pylist() == [result.outputs.price]


def test_a_batch_table_has_no_single_manifest() -> None:
    pyarrow = pytest.importorskip("pyarrow")
    table = run_model_batch(tm.zero_coupon, [ZERO, ZERO]).to_arrow()
    assert isinstance(table, pyarrow.Table)
    assert table.num_rows == 2
    assert not table.schema.metadata


def test_arrow_types() -> None:
    pyarrow = pytest.importorskip("pyarrow")
    table = run_model_batch(
        rm.dated,
        [{"start": "2026-01-31", "days": 30}, {"start": "2026-02-28", "days": 0}],
    ).to_arrow()
    assert table.schema.field("outputs.end").type == pyarrow.date32()
    assert table.column("outputs.per_day").null_count == 1
    assert table.schema.field("outputs.dates").type == pyarrow.list_(pyarrow.date32())


def test_parquet_round_trips_with_the_manifest(tmp_path: Path) -> None:
    pyarrow = pytest.importorskip("pyarrow")
    parquet = pytest.importorskip("pyarrow.parquet")
    result = run_model(rm.growth, start=100, rate=0.1, periods=2)
    path = tmp_path / "result.parquet"
    result.to_parquet(path)
    table = parquet.read_table(path)
    assert isinstance(table, pyarrow.Table)
    assert table.to_pylist()[0]["outputs.final"] == pytest.approx(121.0)
    stored = json.loads(parquet.read_schema(path).metadata[b"pyeconomics.manifest"])
    assert stored["result_sha256"] == result.manifest.result_sha256


def test_a_null_only_column_survives_parquet(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    parquet = pytest.importorskip("pyarrow.parquet")
    result = run_model(rm.dated, start="2026-01-31", days=0)
    path = tmp_path / "null.parquet"
    result.to_parquet(path)
    assert parquet.read_table(path).to_pylist()[0]["outputs.per_day"] is None


# --- the libraries are optional ---------------------------------------------------


@pytest.mark.parametrize(
    ("package", "call"),
    [
        ("polars", lambda r: r.to_polars()),
        ("pyarrow", lambda r: r.to_arrow()),
        ("pyarrow", lambda r: r.to_parquet("never-written.parquet")),
    ],
)
def test_a_missing_library_is_named(
    monkeypatch: pytest.MonkeyPatch,
    package: str,
    call: Any,  # noqa: ANN401
) -> None:
    monkeypatch.setitem(sys.modules, package, None)
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", None)
    with pytest.raises(MissingOptionalDependencyError) as caught:
        call(zero())
    assert caught.value.package == package
    assert package in str(caught.value)
    assert isinstance(caught.value, ImportError)


def test_a_missing_library_is_named_for_a_batch_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = run_model_batch(tm.zero_coupon, [ZERO])
    monkeypatch.setitem(sys.modules, "polars", None)
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    with pytest.raises(MissingOptionalDependencyError, match="polars"):
        batch.to_polars()
    with pytest.raises(MissingOptionalDependencyError, match="pyarrow"):
        batch.to_arrow()
    assert batch.to_pandas().shape == (1, 5)  # pandas is a dependency
