# tests/registry/test_validate_hardening.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""validate() refuses a model whose declared bounds are not the ones enforced."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import pytest
import toy_models as tm
from pydantic import (
    AllowInfNan,
    ConfigDict,
    Field,
    InstanceOf,
    PlainValidator,
    SkipValidation,
    WrapValidator,
    computed_field,
    field_validator,
    model_validator,
)

from pyeconomics.core import Example, Rate, Reference, Registry, Unit, UnitKind

if TYPE_CHECKING:
    from collections.abc import Callable

ZC = tm.zero_coupon


def rules_of(registry: Registry) -> set[str]:
    return {problem.rule for problem in registry.problems(released={})}


def details_of(registry: Registry, rule: str) -> list[str]:
    return [p.detail for p in registry.problems(released={}) if p.rule == rule]


def keep(value: object) -> object:
    return value


def keep_wrapped(value: object, _handler: object) -> object:
    return value


# --- metadata and validators that skip the bounds ----------------------------


class PlainField(tm.ZeroCouponInputs):
    spread: Annotated[Rate, PlainValidator(keep)] = Field(
        0.0, ge=0, le=1, description="Validated by nothing"
    )


class SkippedField(tm.ZeroCouponInputs):
    spread: Annotated[Rate, SkipValidation] = Field(
        0.0, ge=0, le=1, description="Not validated"
    )


class WrappedField(tm.ZeroCouponInputs):
    spread: Annotated[Rate, WrapValidator(keep_wrapped)] = Field(
        0.0, ge=0, le=1, description="Wrapped past its bounds"
    )


class InstanceField(tm.ZeroCouponInputs):
    spread: Annotated[Rate, InstanceOf()] = Field(
        0.0, ge=0, le=1, description="Only an instance check"
    )


class NestedBypass(tm.ZeroCouponInputs):
    spreads: tuple[Annotated[Rate, PlainValidator(keep), Field(ge=0, le=1)], ...] = (
        Field((), max_length=3, description="Items that skip their bounds")
    )


class PlainFieldValidator(tm.ZeroCouponInputs):
    @field_validator("rate", mode="plain")
    @classmethod
    def anything(cls, value: object) -> object:
        return value


class WrapFieldValidator(tm.ZeroCouponInputs):
    @field_validator("rate", mode="wrap")
    @classmethod
    def anything(cls, value: object, handler: Callable[[object], object]) -> object:
        return handler(value)


class WrapModelValidator(tm.ZeroCouponInputs):
    @model_validator(mode="wrap")  # type: ignore[misc]
    @classmethod
    def anything(cls, value: object, handler: Callable[[object], object]) -> object:
        return handler(value)


class AfterFieldValidator(tm.ZeroCouponInputs):
    @field_validator("rate", mode="after")
    @classmethod
    def checked(cls, value: float) -> float:
        return value


class AfterModelValidator(tm.ZeroCouponInputs):
    @model_validator(mode="after")
    def checked(self) -> AfterModelValidator:
        return self


class BeforeFieldValidator(tm.ZeroCouponInputs):
    @field_validator("rate", mode="before")
    @classmethod
    def coerced(cls, value: object) -> object:
        return value


@pytest.mark.parametrize(
    "inputs",
    [
        PlainField,
        SkippedField,
        WrappedField,
        InstanceField,
        NestedBypass,
        PlainFieldValidator,
        WrapFieldValidator,
        WrapModelValidator,
    ],
)
def test_a_model_that_can_skip_its_bounds_is_rejected(inputs: type) -> None:
    registry = tm.toy_registry(tm.variant(ZC, inputs=inputs))
    assert rules_of(registry) == {"field-type"}
    assert "skip" in details_of(registry, "field-type")[0]


@pytest.mark.parametrize(
    "inputs", [AfterFieldValidator, BeforeFieldValidator, AfterModelValidator]
)
def test_validators_that_run_with_the_bounds_are_accepted(inputs: type) -> None:
    assert tm.toy_registry(tm.variant(ZC, inputs=inputs)).problems(released={}) == []


def test_the_skipped_bound_really_is_skipped() -> None:
    # The reason for the rule: these models accept what their Field forbids.
    assert PlainField(face_value=1, rate=0.1, years=1, spread=1e9).spread == 1e9
    assert SkippedField(face_value=1, rate=0.1, years=1, spread=1e9).spread == 1e9


# --- computed fields and configuration ---------------------------------------


class ComputedOutputs(tm.ZeroCouponOutputs):
    @computed_field  # type: ignore[prop-decorator]
    @property
    def doubled(self) -> float:
        return self.price * 2


class LazyInputs(tm.ZeroCouponInputs):
    model_config = ConfigDict(revalidate_instances="never")


class NanInputs(tm.ZeroCouponInputs):
    model_config = ConfigDict(allow_inf_nan=True)


class OpenInputs(tm.ZeroCouponInputs):
    model_config = ConfigDict(extra="allow")


def test_a_computed_field_is_rejected() -> None:
    registry = tm.rebuilt(
        ZC,
        lambda _inputs: ComputedOutputs(price=1.0),
        outputs=ComputedOutputs,
    )
    assert rules_of(registry) == {"field-type"}
    assert "doubled is a computed field" in details_of(registry, "field-type")[0]


@pytest.mark.parametrize("inputs", [LazyInputs, NanInputs, OpenInputs])
def test_the_closed_finite_configuration_is_pinned(inputs: type) -> None:
    registry = tm.toy_registry(tm.variant(ZC, inputs=inputs))
    assert rules_of(registry) == {"io-types"}
    assert "re-validate" in details_of(registry, "io-types")[0]


def test_a_model_construct_instance_is_checked_whatever_the_config_says() -> None:
    sneaky = LazyInputs.model_construct(face_value=1, rate=9.0, years=1)
    assert sneaky.rate == 9.0  # why the rule exists: "never" lets this through


class FiniteOverride(tm.ZeroCouponInputs):
    spread: Annotated[float, Unit(UnitKind.RATE), AllowInfNan(allow_inf_nan=True)] = (
        Field(0.0, ge=0, le=1, description="Allows NaN")
    )


def test_a_field_that_allows_nan_is_rejected() -> None:
    registry = tm.toy_registry(tm.variant(ZC, inputs=FiniteOverride))
    assert rules_of(registry) == {"field-bounds"}
    assert "allows NaN and infinity" in details_of(registry, "field-bounds")[0]


# --- PEP 695 aliases ---------------------------------------------------------

type Share = Annotated[Rate, Field(ge=0, le=1)]
type Shares = tuple[Share, ...]


class AliasedFields(tm.ZeroCouponInputs):
    share: Share = Field(0.5, description="A share, through a type alias")
    shares: Shares = Field((), max_length=4, description="Shares")


def test_a_pep_695_type_alias_is_followed() -> None:
    assert (
        tm.toy_registry(tm.variant(ZC, inputs=AliasedFields)).problems(released={})
        == []
    )


type Loose = float


class LooseAlias(tm.ZeroCouponInputs):
    loose: Loose = Field(0.0, description="An alias to a bare float")


def test_a_type_alias_is_held_to_the_same_rules() -> None:
    registry = tm.toy_registry(tm.variant(ZC, inputs=LooseAlias))
    assert rules_of(registry) == {"field-unit", "field-bounds"}


# --- a mistyped spec reports, it does not crash ------------------------------


def test_mistyped_reference_values_are_reported_not_raised() -> None:
    bad = Reference(key="a", citation="c", doi=123, locator=5, isbn=9)  # type: ignore[arg-type]
    registry = tm.toy_registry(tm.variant(ZC, references=(bad,)))
    assert rules_of(registry) == {"reference"}
    assert len(details_of(registry, "reference")) == 3


def test_a_spec_with_the_wrong_kind_of_value_is_reported_as_such() -> None:
    registry = tm.toy_registry(tm.variant(ZC, references=(object(),)))
    [problem] = registry.problems(released={})
    assert problem.rule == "spec"
    assert "wrong type" in problem.detail


def test_one_malformed_model_does_not_hide_the_others() -> None:
    registry = tm.toy_registry(
        tm.variant(ZC, references=(object(),)),
        tm.variant(tm.mean_return, evidence=None),
    )
    assert {(p.model, p.rule) for p in registry.problems(released={})} == {
        (ZC.id, "spec"),
        (tm.mean_return.id, "evidence"),
    }


def test_an_example_calculation_that_is_not_a_string_is_reported() -> None:
    first = tm.time_value.spec.examples[0]
    bad = Example(name="listed", inputs={**first.inputs, "calculation": ["x"]})
    registry = tm.toy_registry(tm.variant(tm.time_value, examples=(bad,)))
    found = rules_of(registry)
    assert "examples" in found
    assert "example-calculations" in found
