# tests/registry/test_binding_declarations.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Binding declarations: the decorator, sound bindings and the field reader.

``test_validate_rules`` shows each structural problem with a toy specification;
this file shows what is *accepted*, and how a binding reads its field.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

import bound_support as bs
import pytest
import toy_models as tm
from pydantic import Field

from pyeconomics.core import (
    DEFAULT_PROFILE,
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Rate,
    RateArray,
    Registry,
    Unit,
    UnitKind,
    VintagePolicy,
    model,
)
from pyeconomics.core.binding import field_shapes
from pyeconomics.core.model import ModelInputs

CONCEPT = "us.unemployment.rate"


def problems(*bindings: Binding, base: Any = tm.zero_coupon) -> list[str]:  # noqa: ANN401
    registry = tm.toy_registry(tm.variant(base, bindings=bindings))
    return [str(p) for p in registry.problems(released={}) if p.rule == "bindings"]


def test_the_toy_bound_models_validate_with_the_whole_registry() -> None:
    bs.model_registry().validate(released={})


def test_a_sound_set_of_profiles_passes() -> None:
    assert (
        problems(
            Binding("rate", CONCEPT),
            Binding("rate", "gb.inflation.cpi.yoy", profile="uk"),
            Binding("years", "us.unemployment.rate", transform="diff", profile="uk"),
            Binding("face_value", "us.output.real_gdp", as_of=AsOf.PERIOD),
            Binding("rate", CONCEPT, vintage=VintagePolicy.LATEST, profile="revised"),
        )
        == []
    )


def test_an_array_field_with_a_window_within_its_length_passes() -> None:
    assert (
        problems(
            Binding("returns", CONCEPT, as_of=AsOf.WINDOW, window=252),
            base=tm.mean_return,
        )
        == []
    )


def test_a_family_of_calculations_binds_a_field_its_members_share() -> None:
    assert problems(Binding("rate", CONCEPT), base=tm.time_value) == []
    shared = problems(Binding("present_value", CONCEPT), base=tm.time_value)
    assert shared == []  # a field of only one calculation is still a field


def test_a_field_unknown_to_every_calculation_is_named_with_the_known_ones() -> None:
    (found,) = problems(Binding("nothing", CONCEPT), base=tm.time_value)
    assert "not an input field" in found
    assert "future_value" in found
    assert "foundations.toy_time_value" in found


def test_the_decorator_takes_bindings_and_a_model_without_them_has_none() -> None:
    assert bs.unemployment.spec.bindings[0].field == "unemployment"
    assert bs.plain.spec.bindings == ()
    assert tm.zero_coupon.spec.bindings == ()
    assert {b.profile for b in bs.unemployment.spec.bindings} == {
        DEFAULT_PROFILE,
        "revised",
        "uk",
    }


def test_a_binding_never_changes_how_a_model_computes() -> None:
    free = bs.plain({"unemployment": 0.04, "weight": 2.0})
    bound = bs.unemployment({"unemployment": 0.04, "weight": 2.0})
    assert free.score == bound.score == pytest.approx(0.08)


def test_a_bound_model_can_be_declared_on_a_fresh_function() -> None:
    @model(
        id="macro.toy_declared",
        version=1,
        title="Toy declared",
        summary="Declares a binding on the decorator.",
        formula=(r"y = u",),
        assumptions=("None.",),
        limitations=("None.",),
        references=(bs.REFERENCE,),
        evidence=Evidence.PRACTITIONER,
        cost=CostClass.INSTANT,
        examples=(Example(name="one", inputs={"unemployment": 0.04}),),
        changelog=(ChangelogEntry(version=1, note="First version."),),
        no_invariants_reason="A toy.",
        bindings=[Binding("unemployment", CONCEPT)],
    )
    def declared(inputs: bs.RateInputs) -> bs.RateOutputs:
        return bs.RateOutputs(score=inputs.unemployment)

    assert declared.spec.bindings == (Binding("unemployment", CONCEPT),)
    Registry.from_models(declared, distribution="toy-dist").validate(released={})


# --- reading a model's fields -------------------------------------------------------


def test_field_shapes_tell_scalar_from_array_and_give_the_unit_and_length() -> None:
    shapes = field_shapes(bs.WindowInputs)
    (history,) = shapes["history"]
    assert (history.kind, history.array, history.max_length) == (
        UnitKind.RATE,
        True,
        12,
    )
    (unemployment,) = field_shapes(bs.RateInputs)["unemployment"]
    assert (unemployment.kind, unemployment.array) == (UnitKind.RATE, False)


def test_field_shapes_look_through_optional_fields_and_type_aliases() -> None:
    class Wide(ModelInputs):
        maybe: Optional[Rate] = Field(None, ge=0, le=1, description="Optional")  # noqa: UP045
        many: Annotated[RateArray, Field(max_length=3)] = Field(
            (), description="Capped"
        )
        count: Annotated[int, Unit(UnitKind.COUNT)] = Field(
            0, ge=0, le=9, description="A count"
        )
        label: str = Field("", max_length=4, description="Text")

    shapes = field_shapes(Wide)
    assert shapes["maybe"][0].kind is UnitKind.RATE
    assert (shapes["many"][0].array, shapes["many"][0].max_length) == (True, 3)
    assert shapes["count"][0].kind is UnitKind.COUNT
    assert shapes["label"][0].kind is None


def test_field_shapes_of_a_union_list_one_shape_per_member_that_has_the_field() -> None:
    shapes = field_shapes(tm.TimeValueInputs)
    assert len(shapes["rate"]) == len(shapes["years"]) == 2
    assert len(shapes["future_value"]) == 1


def test_field_shapes_ignore_what_is_not_an_input_model() -> None:
    assert field_shapes(int) == {}
