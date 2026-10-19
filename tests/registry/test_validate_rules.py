# tests/registry/test_validate_rules.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Registry validation: one toy specification per rule, each breaking just it."""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Callable
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

import pytest
import toy_models as tm
from pydantic import BaseModel, ConfigDict, Field

from pyeconomics.core import (
    Alias,
    AsOf,
    Binding,
    ChangelogEntry,
    ChartKind,
    ChartSpec,
    CostClass,
    DateValue,
    Evidence,
    Example,
    Invariant,
    Model,
    ModelInputs,
    ModelOutputs,
    MoneyArray,
    Rate,
    Reference,
    Registry,
    RegistryError,
    ReturnArray,
    Unit,
    UnitKind,
    model,
)
from pyeconomics.core.registry import RULES


def broken(base: Model[Any, Any], **changes: object) -> Registry:
    """A registry whose one model has a changed specification."""
    return tm.toy_registry(tm.variant(base, **changes))


def rules_of(registry: Registry) -> set[str]:
    return {problem.rule for problem in registry.problems(released={})}


# --- field classes that break one field rule ---------------------------------


class AnyField(tm.ZeroCouponInputs):
    note: Any = Field(None, description="Anything")


class ObjectField(tm.ZeroCouponInputs):
    note: object = Field(None, description="Anything")


class ListField(tm.ZeroCouponInputs):
    notes: list[float] = Field(default_factory=list, description="A mutable list")


class DictField(tm.ZeroCouponInputs):
    notes: dict = Field(default_factory=dict, description="An open dict")  # type: ignore[type-arg]


class BareTupleField(tm.ZeroCouponInputs):
    notes: tuple = Field((), description="A tuple of anything")  # type: ignore[type-arg]


class DatetimeField(tm.ZeroCouponInputs):
    when: dt.datetime = Field(dt.datetime(2026, 1, 1), description="A datetime")  # noqa: DTZ001


class DecimalField(tm.ZeroCouponInputs):
    amount: Decimal = Field(Decimal(0), description="A decimal")


class PlainRecord(BaseModel):
    value: int = 0


class OpenNestedField(tm.ZeroCouponInputs):
    record: PlainRecord | None = Field(None, description="A model that is not closed")


class NodeField(tm.ZeroCouponInputs):
    child: NodeField | None = Field(None, description="Contains its own type")


class NoUnitField(tm.ZeroCouponInputs):
    spread: float = Field(0.0, ge=0, le=1, description="No unit marker")


class NumericLiteralField(tm.ZeroCouponInputs):
    year: Literal[365, 366] = Field(365, description="No unit or bounds")


class WrongKindField(tm.ZeroCouponInputs):
    spread: Annotated[float, Unit(UnitKind.COUNT)] = Field(
        0.0, ge=0, le=1, description="A count held in a float"
    )


class WrongIntKindField(tm.ZeroCouponInputs):
    steps: Annotated[int, Unit(UnitKind.RATE)] = Field(
        0, ge=0, le=5, description="A rate held in an int"
    )


class NoUpperBoundField(tm.ZeroCouponInputs):
    spread: Rate = Field(0.0, ge=0, description="No upper bound")


class InfiniteBoundField(tm.ZeroCouponInputs):
    spread: Rate = Field(0.0, ge=0, le=math.inf, description="An infinite bound")


class InvertedBoundsField(tm.ZeroCouponInputs):
    spread: Rate = Field(0.5, ge=1, le=0.2, description="Inverted bounds")


class UnboundedDateField(tm.ZeroCouponInputs):
    when: DateValue = Field(dt.date(2026, 1, 1), description="A date with no bounds")


class UnmarkedDateField(tm.ZeroCouponInputs):
    when: dt.date = Field(
        dt.date(2026, 1, 1),
        ge=dt.date(1900, 1, 1),
        le=dt.date(2200, 12, 31),
        description="A date with no unit marker",
    )


class DatedField(tm.ZeroCouponInputs):
    when: DateValue = Field(
        dt.date(2026, 1, 1),
        ge=dt.date(1900, 1, 1),
        le=dt.date(2200, 12, 31),
        description="A sound date",
    )


class NoDescriptionField(tm.ZeroCouponInputs):
    spread: Rate = Field(0.0, ge=0, le=1)


class UnboundedStringField(tm.ZeroCouponInputs):
    label: str = Field("", description="A string with no maximum length")


class UnboundedArrayField(tm.ZeroCouponInputs):
    series: ReturnArray = Field((), description="An array with no maximum length")


class UnboundedItemsField(tm.ZeroCouponInputs):
    series: Annotated[tuple[float, ...], Field(max_length=5)] = Field(
        (), description="Items with no unit or bounds"
    )


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class Leg(ModelInputs):
    side: Side = Field(Side.BUY, description="Buy or sell")
    weight: Rate = Field(0.0, ge=0, le=1, description="Weight")


class SoundFields(tm.ZeroCouponInputs):
    """Every kind of field a model may declare."""

    maybe: Rate | None = Field(None, ge=0, le=1, description="Optional rate")
    flag: bool = Field(default=False, description="A switch")
    label: str = Field("", max_length=20, description="A label")
    mode: Literal["fast", "slow"] = Field("fast", description="A choice")
    side: Side = Field(Side.BUY, description="An enumeration")
    when: DateValue = Field(
        dt.date(2026, 1, 1),
        ge=dt.date(1900, 1, 1),
        le=dt.date(2200, 12, 31),
        description="A date",
    )
    series: MoneyArray = Field(default=(), max_length=10, description="An array")
    legs: tuple[Leg, ...] = Field(default=(), max_length=4, description="Nested rows")
    pair: tuple[
        Annotated[Rate, Field(ge=0, le=1)], Annotated[Rate, Field(ge=0, le=1)]
    ] = Field((0.0, 1.0), description="A fixed-length pair")
    weights: dict[
        Annotated[str, Field(max_length=10)], Annotated[Rate, Field(ge=-1, le=1)]
    ] = Field(default_factory=dict, max_length=5, description="A bounded dict")


class BadOutputs(tm.ZeroCouponOutputs):
    extra_price: float = Field(0.0, ge=0, le=1, description="No unit marker")


class Series(ModelOutputs):
    series: ReturnArray = Field(max_length=10, description="A series")


class Echo(tm.ZeroCouponInputs):
    """Inputs of the chart model."""


RETURNS_CHART = ChartSpec(
    id="returns", title="Returns", kind=ChartKind.LINE, x="series", y=("series",)
)


@model(
    id="foundations.toy_chart",
    version=1,
    title="Chart",
    summary="Echoes a series.",
    formula=("x",),
    assumptions=("a",),
    limitations=("l",),
    references=(tm.FISHER,),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    no_invariants_reason="A toy.",
    examples=(Example(name="one", inputs=tm.with_inputs(tm.zero_coupon)),),
    changelog=(ChangelogEntry(version=1, note="First."),),
    charts=(RETURNS_CHART,),
)
def echo(inputs: Echo) -> Series:
    return Series(series=(0.0, inputs.rate))


# --- the table ---------------------------------------------------------------

ZC = tm.zero_coupon
TV = tm.time_value
LONG = "x" * 2000

Build = Callable[[], Registry]
Case = tuple[Build, frozenset[str]]


def case(build: Build, *also: str) -> Case:
    """A case, with the other rules it may report beside its own."""
    return build, frozenset(also)


def _with_inputs(cls: type[ModelInputs]) -> Callable[[], Registry]:
    return lambda: broken(ZC, inputs=cls)


def _reference(**changes: object) -> Callable[[], Registry]:
    fields = {
        "key": "a",
        "citation": "A citation",
        "url": "https://example.org/a",
        "locator": "p. 1",
    }
    return lambda: broken(
        ZC,
        references=(Reference(**{**fields, **changes}),),  # type: ignore[arg-type]
    )


CONCEPT = "us.unemployment.rate"


def _bound(*bindings: object, base: Model[Any, Any] = ZC) -> Callable[[], Registry]:
    """A model with these bindings, which only the bindings rule should object to."""
    return lambda: broken(base, bindings=bindings)


def _alias_clash() -> Registry:
    clashing = tm.variant(TV, aliases=("fixed_income.toy_zero_coupon",))
    return tm.toy_registry(ZC, clashing)


def _alias_twice() -> Registry:
    one = tm.variant(ZC, aliases=("foundations.shared_alias",))
    two = tm.variant(tm.mean_return, aliases=("foundations.shared_alias",))
    return tm.toy_registry(one, two)


def _duplicate_id() -> Registry:
    return Registry.from_models(ZC, ZC, distribution="toy-dist")


def _union_without_discriminator() -> Registry:
    plain = tm.PresentValueInputs | tm.FutureValueInputs
    return broken(TV, inputs=plain)


def _union_with_missing_calculation() -> Registry:
    class NoCalculation(ModelInputs):
        rate: Rate = Field(0.0, ge=0, le=1, description="A rate")

    union = Annotated[
        tm.PresentValueInputs | NoCalculation, Field(discriminator="calculation")
    ]
    return broken(TV, inputs=union)


CASES: dict[str, list[Case]] = {
    "id-format": [
        case(lambda: broken(ZC, id="fixed_income")),
        case(lambda: broken(ZC, id="A.b")),
    ],
    "domain": [case(lambda: broken(ZC, id="astrology.toy_zero_coupon"))],
    "no-cfa": [
        case(lambda: broken(ZC, id="fixed_income.cfa_toy")),
        case(lambda: broken(ZC, aliases=("fixed_income.old_cfa",))),
    ],
    "version": [case(lambda: broken(ZC, version="1"))],
    "changelog": [
        case(lambda: broken(ZC, changelog=())),
        case(
            lambda: broken(
                ZC,
                changelog=(
                    ChangelogEntry(version=1, note="First."),
                    ChangelogEntry(version=1, note="Again."),
                ),
            )
        ),
        case(lambda: broken(ZC, changelog=(ChangelogEntry(version=1, note=" "),))),
    ],
    "title": [
        case(lambda: broken(ZC, title="")),
        case(lambda: broken(ZC, title="x" * 81)),
    ],
    "summary": [
        case(lambda: broken(ZC, summary=" ")),
        case(lambda: broken(ZC, summary="x" * 301)),
    ],
    "tags": [
        case(lambda: broken(ZC, tags=("Upper Case",))),
        case(lambda: broken(ZC, tags=("a", "a"))),
    ],
    "formula": [
        case(lambda: broken(ZC, formula=())),
        case(lambda: broken(ZC, formula=(LONG,))),
    ],
    "assumptions": [case(lambda: broken(ZC, assumptions=()))],
    "limitations": [case(lambda: broken(ZC, limitations=()))],
    "references": [case(lambda: broken(ZC, references=()))],
    "reference": [
        case(_reference(locator=None)),
        case(_reference(url=None)),
        case(_reference(doi="not-a-doi", url=None)),
        case(_reference(url="javascript:alert(1)")),
        case(_reference(isbn="12345")),
        case(lambda: broken(ZC, references=(tm.FISHER, tm.FISHER))),
    ],
    "extra": [case(lambda: broken(ZC, extra="undeclared"))],
    "evidence": [
        case(lambda: broken(ZC, evidence=None)),
        case(lambda: broken(ZC, evidence="x")),
    ],
    "cost": [case(lambda: broken(ZC, cost=None))],
    "io-types": [
        case(lambda: broken(ZC, inputs=dict)),
        case(lambda: broken(ZC, outputs=int)),
    ],
    "calculation": [
        case(_union_without_discriminator),
        case(_union_with_missing_calculation, "io-types"),
        case(lambda: broken(TV, outputs=tm.ZeroCouponOutputs), "examples"),
    ],
    "field-type": [
        case(_with_inputs(AnyField)),
        case(_with_inputs(ObjectField)),
        case(_with_inputs(ListField)),
        case(_with_inputs(DictField)),
        case(_with_inputs(BareTupleField)),
        case(_with_inputs(DatetimeField)),
        case(_with_inputs(DecimalField)),
        case(_with_inputs(OpenNestedField)),
        case(_with_inputs(NodeField)),
    ],
    "field-unit": [
        case(_with_inputs(NumericLiteralField), "field-bounds"),
        case(_with_inputs(NoUnitField)),
        case(_with_inputs(WrongKindField)),
        case(_with_inputs(WrongIntKindField)),
        case(_with_inputs(UnmarkedDateField)),
        case(lambda: broken(ZC, outputs=BadOutputs), "examples"),
    ],
    "field-bounds": [
        case(_with_inputs(NumericLiteralField), "field-unit"),
        case(_with_inputs(NoUpperBoundField)),
        case(_with_inputs(InfiniteBoundField)),
        case(_with_inputs(InvertedBoundsField), "examples"),
        case(_with_inputs(UnboundedDateField)),
    ],
    "field-description": [case(_with_inputs(NoDescriptionField))],
    "field-length": [
        case(_with_inputs(UnboundedStringField)),
        case(_with_inputs(UnboundedArrayField)),
    ],
    "examples": [
        case(lambda: broken(ZC, examples=())),
        case(
            lambda: broken(
                ZC, examples=(Example(name="bad", inputs=tm.with_inputs(ZC, rate=5)),)
            )
        ),
        case(
            lambda: broken(
                ZC, examples=(Example(name="Bad Name", inputs=tm.with_inputs(ZC)),)
            )
        ),
        case(lambda: broken(ZC, examples=(ZC.spec.examples[0], ZC.spec.examples[0]))),
    ],
    "example-calculations": [case(lambda: broken(TV, examples=TV.spec.examples[:1]))],
    "invariants": [
        case(lambda: broken(ZC, invariants=())),
        case(lambda: broken(ZC, invariants=ZC.spec.invariants * 2)),
        case(
            lambda: broken(ZC, invariants=(Invariant(id="Not Snake", statement="x"),))
        ),
        case(lambda: broken(ZC, invariants=(Invariant(id="ok_id", statement=" "),))),
    ],
    "charts": [
        case(
            lambda: broken(
                ZC,
                charts=(
                    ChartSpec(
                        id="c", title="t", kind=ChartKind.LINE, x="price", y=("price",)
                    ),
                ),
            )
        ),
        case(
            lambda: broken(
                ZC,
                charts=(
                    ChartSpec(id="c", title="t", kind=ChartKind.BAR, x="price", y=()),
                ),
            )
        ),
    ],
    "aliases": [
        case(lambda: broken(ZC, aliases=("Not An Id",))),
        case(lambda: broken(ZC, aliases=("fixed_income.toy_zero_coupon",))),
        case(
            lambda: broken(ZC, aliases=(Alias("fixed_income.old", removed_in="1.5.0"),))
        ),
        case(_alias_clash),
        case(_alias_twice),
    ],
    "bindings": [
        case(lambda: broken(ZC, bindings=(object(),))),
        # a field that does not exist, or is not a field a number can fill
        case(_bound(Binding("no_such_field", CONCEPT))),
        case(_bound(Binding("Bad Field", CONCEPT))),
        case(
            lambda: broken(ZC, inputs=DatedField, bindings=(Binding("when", CONCEPT),))
        ),
        # one field bound twice in one profile (the same field in two is fine)
        case(_bound(Binding("rate", CONCEPT), Binding("rate", CONCEPT))),
        # a window on a scalar field, an array field without one
        case(_bound(Binding("rate", CONCEPT, as_of=AsOf.WINDOW, window=4))),
        case(_bound(Binding("returns", CONCEPT), base=tm.mean_return)),
        case(
            _bound(
                Binding("returns", CONCEPT, as_of=AsOf.WINDOW, window=253),
                base=tm.mean_return,
            )
        ),
        # a window given without the window rule, or the rule without a window
        case(_bound(Binding("rate", CONCEPT, window=4))),
        case(_bound(Binding("rate", CONCEPT, as_of=AsOf.WINDOW))),
        case(
            _bound(
                Binding("returns", CONCEPT, as_of=AsOf.WINDOW, window=0),
                base=tm.mean_return,
            )
        ),
        # bindings but no default profile
        case(_bound(Binding("rate", CONCEPT, profile="forecast"))),
        # a concept id outside decision 15's grammar
        case(_bound(Binding("rate", "Not A Concept"))),
        case(_bound(Binding("rate", "us.rate"))),
        # a transform the vocabulary does not declare, with bad parameters, that
        # reads two series, or that picks observations (the as-of rule's job)
        case(_bound(Binding("rate", CONCEPT, transform="no_such_transform"))),
        case(_bound(Binding("rate", CONCEPT, transform="pct_change(periods=0)"))),
        case(_bound(Binding("rate", CONCEPT, transform="pct_change(speed=2)"))),
        case(_bound(Binding("rate", CONCEPT, transform="ratio"))),
        case(_bound(Binding("rate", CONCEPT, transform="asof(date=2020-01-01)"))),
        # an as-of rule or vintage policy that is not one
        case(_bound(Binding("rate", CONCEPT, as_of="sometimes"))),  # type: ignore[arg-type]
        case(_bound(Binding("rate", CONCEPT, vintage="eventually"))),  # type: ignore[arg-type]
        case(_bound(Binding("rate", CONCEPT, profile="Not Snake"))),
    ],
    "duplicate-id": [case(_duplicate_id)],
    "spec": [case(lambda: broken(ZC, references=(object(),)))],
}


def _params() -> list[Any]:
    return [
        pytest.param(rule, build, also, id=f"{rule}-{position}")
        for rule, cases in CASES.items()
        for position, (build, also) in enumerate(cases)
    ]


@pytest.mark.parametrize(("rule", "build", "also"), _params())
def test_a_toy_spec_breaks_its_rule(
    rule: str, build: Build, also: frozenset[str]
) -> None:
    found = rules_of(build())
    assert rule in found
    assert found <= {rule} | also, found


@pytest.mark.parametrize(("rule", "build", "also"), _params())
def test_validate_names_the_model_and_the_rule(
    rule: str, build: Build, also: frozenset[str]
) -> None:
    registry = build()
    with pytest.raises(RegistryError) as caught:
        registry.validate(released={})
    assert also is not None
    expected = [str(p) for p in registry.problems(released={}) if p.rule == rule]
    assert expected
    for problem in registry.problems(released={}):
        assert f"{problem.model}: [{problem.rule}] " in str(caught.value)
    assert set(expected) <= set(caught.value.problems)


def test_every_rule_has_a_toy_spec() -> None:
    covered = set(CASES) | {"released"}
    assert covered == set(RULES)


def test_validate_lists_every_problem_at_once() -> None:
    registry = tm.toy_registry(
        tm.variant(ZC, title="", summary="", evidence=None, bindings=(object(),))
    )
    with pytest.raises(RegistryError) as caught:
        registry.validate(released={})
    rules = [line.split("[")[1].split("]")[0] for line in caught.value.problems]
    # The object is not a binding, and without one there is no default profile.
    assert rules == ["title", "summary", "evidence", "bindings", "bindings"]
    assert str(caught.value).startswith("the model registry has 5 problems:")


def test_a_single_problem_reads_in_the_singular() -> None:
    with pytest.raises(RegistryError, match=r"has 1 problem:\n"):
        broken(ZC, cost=None).validate(released={})


def test_the_toy_catalog_is_valid() -> None:
    tm.toy_registry().validate(released={})


def test_every_kind_of_field_is_accepted() -> None:
    broken(ZC, inputs=SoundFields).validate(released={})


# Float Literals are outside the static typing spec but pydantic accepts them;
# validate() must still guard their units and bounds at runtime.
FLOAT_LITERAL: Any = Literal
FLOAT_LITERAL = FLOAT_LITERAL[0.5, 1.5]


@pytest.mark.parametrize("annotation", [Literal[365, 366], FLOAT_LITERAL])
def test_numeric_literals_require_units_and_bounds(annotation: Any) -> None:  # noqa: ANN401
    from pydantic import create_model  # noqa: PLC0415

    inputs = create_model(
        "NumericLiteralInputs",
        __base__=tm.ZeroCouponInputs,
        choice=(
            annotation,
            Field(
                description="Numeric choice",
                default=365 if annotation == Literal[365, 366] else 0.5,
            ),
        ),
    )
    assert rules_of(broken(ZC, inputs=inputs)) == {"field-unit", "field-bounds"}


def test_boolean_literal_stays_a_flag() -> None:
    class Flag(tm.ZeroCouponInputs):
        flag: Literal[True, False] = Field(default=False, description="A flag")

    broken(ZC, inputs=Flag).validate(released={})


def test_bounded_unit_marked_numeric_literals_are_sound() -> None:
    class Choices(tm.ZeroCouponInputs):
        year: Annotated[Literal[365, 366], Unit(UnitKind.DAYS)] = Field(
            365, ge=365, le=366, description="Days in year"
        )

    broken(ZC, inputs=Choices).validate(released={})


def test_a_union_of_optional_models_is_walked() -> None:
    class Wrapper(tm.ZeroCouponInputs):
        legs: tuple[Leg, ...] | None = Field(None, max_length=4, description="Rows")

    broken(ZC, inputs=Wrapper).validate(released={})


def test_the_unbounded_item_type_reports_unit_and_bounds() -> None:
    found = rules_of(broken(ZC, inputs=UnboundedItemsField))
    assert found == {"field-unit", "field-bounds"}


def test_field_problems_name_the_field_path() -> None:
    registry = broken(ZC, inputs=UnboundedArrayField)
    [problem] = registry.problems(released={})
    assert "inputs: series is an array with no maximum length" in problem.detail


def test_nested_field_problems_name_the_path() -> None:
    class Row(ModelInputs):
        weight: float = Field(0.0, ge=0, le=1, description="No unit")

    class Table(tm.ZeroCouponInputs):
        rows: tuple[Row, ...] = Field((), max_length=3, description="Rows")

    [problem] = broken(ZC, inputs=Table).problems(released={})
    assert problem.rule == "field-unit"
    assert "rows[].weight" in problem.detail


def test_an_output_field_is_held_to_the_same_rules() -> None:
    problems = broken(ZC, outputs=BadOutputs).problems(released={})
    [problem] = [p for p in problems if p.rule == "field-unit"]
    assert problem.detail.startswith("outputs: extra_price")


def test_a_model_that_is_not_frozen_is_reported() -> None:
    class Loose(tm.ZeroCouponInputs):
        model_config = ConfigDict(frozen=False)

    found = broken(ZC, inputs=Loose).problems(released={})
    assert [p.rule for p in found] == ["io-types"]


def test_charts_of_array_outputs_are_accepted() -> None:
    tm.toy_registry(echo).validate(released={})


def test_the_chart_of_a_calculation_must_name_a_known_one() -> None:
    chart = ChartSpec(
        id="c", title="t", kind=ChartKind.LINE, x="a", y=("a",), calculation="nope"
    )
    assert rules_of(broken(TV, charts=(chart,))) == {"charts"}


def test_a_union_model_with_one_input_union_and_a_single_output_is_reported() -> None:
    found = broken(TV, outputs=tm.PresentValueOutputs).problems(released={})
    assert any("both be one model or both a union" in p.detail for p in found)
