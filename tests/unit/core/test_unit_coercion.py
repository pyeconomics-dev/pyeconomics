# tests/unit/core/test_unit_coercion.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Flags and epoch numbers never become financial values or calendar dates."""

from __future__ import annotations

import datetime as dt
from typing import Any, cast

import numpy as np
import pytest
from pydantic import Field, TypeAdapter, create_model

from pyeconomics.core import InputError, Model, ModelInputs, ModelOutputs, units
from pyeconomics.core.model import ARRAY_KINDS
from pyeconomics.core.units import UnitKind
from pyeconomics.models.foundations import time_value

NUMERIC = tuple(kind for kind in UnitKind if kind is not UnitKind.DATE)
MARKERS: dict[UnitKind, Any] = {
    kind: getattr(units, "".join(word.title() for word in kind.value.split("_")))
    for kind in NUMERIC
}
MARKERS[UnitKind.DATE] = units.DateValue


def field_model(annotation: Any) -> Model[Any, Any]:  # noqa: ANN401
    """Reuse a sound spec with one field, testing the public InputError path."""
    inputs = create_model(
        "CoercionInputs",
        __base__=ModelInputs,
        value=(
            annotation,
            Field(description="Value", max_length=3)
            if annotation in ARRAY_KINDS.values()
            else Field(description="Value"),
        ),
    )
    from dataclasses import replace  # noqa: PLC0415

    return Model(replace(time_value.spec, inputs=inputs), lambda _: ModelOutputs())


@pytest.mark.parametrize("kind", NUMERIC)
@pytest.mark.parametrize("bad", [True, False, np.bool_(1), np.bool_(0)])
def test_numeric_scalar_refuses_flags(kind: UnitKind, bad: object) -> None:
    with pytest.raises(InputError, match="boolean"):
        field_model(MARKERS[kind]).validate_inputs({"value": bad})


@pytest.mark.parametrize("kind", NUMERIC)
@pytest.mark.parametrize(
    "bad", [[True], (False,), [np.bool_(1)], np.array([True, False])]
)
def test_numeric_array_refuses_flags(kind: UnitKind, bad: object) -> None:
    with pytest.raises(InputError, match="boolean"):
        field_model(ARRAY_KINDS[kind]).validate_inputs({"value": bad})


@pytest.mark.parametrize(
    "bad", [86400, 86400.0, np.int64(86400), np.float64(86400), np.float32(86400)]
)
def test_date_scalar_refuses_epoch_numbers(bad: object) -> None:
    with pytest.raises(InputError, match="epoch"):
        field_model(units.DateValue).validate_inputs({"value": bad})


@pytest.mark.parametrize(
    "bad", [[86400], [86400.0], np.array([86400]), np.array([86400.0])]
)
def test_date_array_refuses_epoch_numbers(bad: object) -> None:
    with pytest.raises(InputError, match="epoch"):
        field_model(ARRAY_KINDS[UnitKind.DATE]).validate_inputs({"value": bad})


@pytest.mark.parametrize("kind", NUMERIC)
def test_marker_schema_has_only_its_original_type_and_unit(kind: UnitKind) -> None:
    expected = "integer" if kind in {UnitKind.DAYS, UnitKind.COUNT} else "number"
    assert TypeAdapter(MARKERS[kind]).json_schema() == {
        "type": expected,
        "x-unit": kind.value,
    }
    item = TypeAdapter(cast("Any", ARRAY_KINDS[kind])).json_schema()["items"]
    bounds = units.DEFAULT_BOUNDS[kind]
    assert item == {
        "type": expected,
        "x-unit": kind.value,
        "minimum" if bounds.lower_inclusive else "exclusiveMinimum": bounds.lower,
        "maximum": bounds.upper,
    }
    for value in [1, 1.0, np.int64(1), np.float64(1)]:
        assert TypeAdapter(MARKERS[kind]).validate_python(value) == 1
    for values in [[1], (1,), np.array([1]), np.array([1.0])]:
        assert TypeAdapter(cast("Any", ARRAY_KINDS[kind])).validate_python(values) == (
            1,
        )


@pytest.mark.parametrize(
    "value",
    [
        dt.date(2026, 1, 1),
        dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        "2026-01-01",
        b"2026-01-01",
    ],
)
def test_date_keeps_calendar_forms(value: object) -> None:
    assert TypeAdapter(units.DateValue).validate_python(value) == dt.date(2026, 1, 1)
    assert TypeAdapter(units.DateValue).json_schema() == {
        "type": "string",
        "format": "date",
        "x-unit": "date",
    }


def test_date_array_keeps_numpy_datetime_forms() -> None:
    adapter: TypeAdapter[Any] = TypeAdapter(cast("Any", ARRAY_KINDS[UnitKind.DATE]))
    for unit in ["D", "s", "us", "ns"]:
        assert adapter.validate_python(
            np.array(["2026-01-01"], dtype=f"datetime64[{unit}]")
        ) == (dt.date(2026, 1, 1),)
