# tests/models/test_strategies.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``strategies.inputs`` draws inputs every model accepts, from its declared fields."""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Literal

import pytest
import toy_models as tm
import toy_results_models as rm
from hypothesis import find, given, settings
from hypothesis import strategies as st
from pydantic import Field
from strategies import MAX_ITEMS, OVERRIDES, inputs

from pyeconomics.core import (
    Count,
    DateValue,
    Model,
    ModelInputs,
    ModelOutputs,
    ModelSpec,
    Money,
    Probability,
    Rate,
    ReturnArray,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


class Colour(StrEnum):
    RED = "red"
    BLUE = "blue"


class Leg(ModelInputs):
    weight: Probability = Field(ge=0, le=1, description="Weight")
    name: str = Field(pattern=r"^[a-z]{1,5}$", max_length=5, description="Name")


class SinkInputs(ModelInputs):
    amount: Money = Field(gt=0, lt=10, description="Open on both ends")
    rate: Rate = Field(description="Bounds from the unit's defaults")
    count: Count = Field(gt=0, lt=5, description="Whole, open on both ends")
    flag: bool = Field(default=False, description="A switch")
    mode: Literal["a", "b"] = Field(default="a", description="A choice")
    colour: Colour = Field(default=Colour.RED, description="An enum")
    when: DateValue = Field(
        gt=dt.date(2020, 1, 1), lt=dt.date(2020, 1, 4), description="A date"
    )
    note: str | None = Field(default=None, max_length=8, description="Free text")
    legs: tuple[Leg, ...] = Field(min_length=2, max_length=3, description="Legs")
    series: ReturnArray = Field(min_length=3, max_length=50, description="Returns")
    pair: tuple[
        Annotated[Probability, Field(ge=0, le=1)],
        Annotated[Count, Field(ge=1, le=3)],
    ] = Field(description="A fixed-length tuple")
    tags: dict[str, Annotated[Count, Field(ge=0, le=9)]] = Field(
        default_factory=dict, max_length=3, description="Counts by name"
    )


class SinkOutputs(ModelOutputs):
    total: Money = Field(ge=-1e15, le=1e15, description="Total")


def sink_compute(inputs: SinkInputs) -> SinkOutputs:
    return SinkOutputs(total=inputs.amount)


SINK = Model(
    ModelSpec(
        id="foundations.sink",
        version=1,
        title="Every field type",
        summary="Strategy test.",
        inputs=SinkInputs,
        outputs=SinkOutputs,
    ),
    sink_compute,
)

CATALOG = (*tm.ALL_MODELS, *rm.ALL_MODELS)


@pytest.mark.parametrize("model", CATALOG, ids=lambda m: m.id)
@settings(max_examples=60, deadline=None)
@given(data=st.data())
def test_generated_inputs_are_valid_for_every_toy_model(
    model: Model[Any, Any], data: st.DataObject
) -> None:
    model.validate_inputs(data.draw(inputs(model)))


@settings(max_examples=150, deadline=None)
@given(raw=inputs(SINK))
def test_every_field_type_is_drawn_within_its_bounds(raw: Mapping[str, Any]) -> None:
    parsed = SINK.validate_inputs(raw)
    assert 0 < parsed.amount < 10
    assert 0 < parsed.count < 5
    assert dt.date(2020, 1, 1) < parsed.when < dt.date(2020, 1, 4)
    assert 2 <= len(parsed.legs) <= 3
    assert 3 <= len(parsed.series) <= MAX_ITEMS
    assert len(parsed.tags) <= 3
    assert all(leg.name.isalpha() for leg in parsed.legs)


def test_optional_fields_are_sometimes_left_out_and_sometimes_given() -> None:
    # A finite batch is not guaranteed to visit every optional/enum branch.
    # Search for a valid witness to each supported choice instead.
    predicates: tuple[Callable[[Mapping[str, Any]], bool], ...] = (
        lambda raw: "flag" in raw,
        lambda raw: "flag" not in raw,
        lambda raw: raw.get("note") is None,
        lambda raw: isinstance(raw.get("note"), str),
        lambda raw: raw.get("mode") == "a",
        lambda raw: raw.get("mode") == "b",
        lambda raw: raw.get("colour") == Colour.RED,
        lambda raw: raw.get("colour") == Colour.BLUE,
    )
    for predicate in predicates:
        raw = find(
            inputs(SINK),
            predicate,
            settings=settings(max_examples=1000, deadline=None, database=None),
        )
        SINK.validate_inputs(raw)


def test_a_union_draws_every_calculation_with_its_tag() -> None:
    for calculation in ("present_value", "future_value"):

        def selected(raw: Mapping[str, Any], calculation: str = calculation) -> bool:
            return bool(raw["calculation"] == calculation)

        raw = find(
            inputs(tm.time_value),
            selected,
            settings=settings(max_examples=1000, deadline=None, database=None),
        )
        tm.time_value.validate_inputs(raw)


def test_the_models_examples_are_in_the_mix() -> None:
    example = dict(tm.zero_coupon.spec.examples[0].inputs)
    raw = find(
        inputs(tm.zero_coupon),
        lambda raw: raw == example,
        settings=settings(max_examples=1000, deadline=None, database=None),
    )
    tm.zero_coupon.validate_inputs(raw)


def test_an_override_replaces_the_field_by_field_draw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed = {"face_value": 100, "rate": 0.05, "years": 10}
    monkeypatch.setitem(OVERRIDES, tm.zero_coupon.id, lambda: st.just(fixed))
    seen: list[Mapping[str, Any]] = []

    @settings(max_examples=5, deadline=None, database=None)
    @given(raw=inputs(tm.zero_coupon))
    def collect(raw: Mapping[str, Any]) -> None:
        seen.append(raw)

    collect()
    assert seen
    assert all(raw == fixed for raw in seen)


def test_a_type_with_no_strategy_is_an_error_not_a_silent_gap() -> None:
    class Odd(ModelInputs):
        thing: complex = Field(description="Not supported")

    odd = Model(
        ModelSpec(
            id="foundations.odd",
            version=1,
            title="Odd",
            summary="x",
            inputs=Odd,
            outputs=SinkOutputs,
        ),
        sink_compute,
    )
    with pytest.raises(TypeError, match="no strategy for the type"):
        inputs(odd)
