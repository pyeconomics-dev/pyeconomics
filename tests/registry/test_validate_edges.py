# tests/registry/test_validate_edges.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""More ways a specification can be wrong, and a few it can be right."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Annotated, Any, Literal

import pytest
import toy_models as tm
from annotated_types import Interval, Len
from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    ChartKind,
    ChartSpec,
    MissingOptionalDependencyError,
    Model,
    ModelOutputs,
    Rate,
    Registry,
    RegistryError,
    ReturnArray,
    Unit,
    UnitKind,
)

if TYPE_CHECKING:
    from collections.abc import Callable

ZC = tm.zero_coupon
TV = tm.time_value


def rules_of(registry: Registry) -> set[str]:
    return {problem.rule for problem in registry.problems(released={})}


def details_of(registry: Registry, rule: str) -> list[str]:
    return [p.detail for p in registry.problems(released={}) if p.rule == rule]


def custom(
    base: Model[Any, Any], compute: Callable[[Any], Any], **changes: object
) -> Registry:
    """A registry of one model with a different specification and compute."""
    spec = dataclasses.replace(base.spec, **changes)  # type: ignore[arg-type]
    return tm.toy_registry(Model(spec, compute))


# --- grouped constraints and dicts -------------------------------------------


class GroupedFields(tm.ZeroCouponInputs):
    bounded: Annotated[float, Unit(UnitKind.RATE), Interval(ge=0, le=1)] = Field(
        0.5, description="Bounds as an interval"
    )
    series: Annotated[
        tuple[Annotated[float, Unit(UnitKind.RATE), Interval(ge=0, le=1)], ...],
        Len(max_length=3),
    ] = Field((), description="Length as a grouped constraint")


class UnboundedDict(tm.ZeroCouponInputs):
    weights: dict[
        Annotated[str, Field(max_length=10)], Annotated[Rate, Field(ge=-1, le=1)]
    ] = Field(default_factory=dict, description="A dict with no maximum length")


def test_grouped_constraints_count_as_bounds_and_lengths() -> None:
    assert (
        tm.toy_registry(tm.variant(ZC, inputs=GroupedFields)).problems(released={})
        == []
    )


def test_a_dict_needs_a_maximum_length() -> None:
    registry = tm.toy_registry(tm.variant(ZC, inputs=UnboundedDict))
    assert rules_of(registry) == {"field-length"}
    assert (
        "weights is a dict with no maximum length"
        in details_of(registry, "field-length")[0]
    )


# --- identity ----------------------------------------------------------------


def test_version_zero_is_reported_with_its_changelog_entry() -> None:
    registry = tm.toy_registry(
        tm.variant(ZC, version=0, changelog=(ChangelogEntry(version=0, note="Zero."),))
    )
    assert rules_of(registry) == {"version", "changelog"}
    assert details_of(registry, "version") == ["version 0 is below 1"]
    assert details_of(registry, "changelog") == ["entry version 0 is below 1"]


def test_a_boolean_is_not_a_version() -> None:
    assert rules_of(tm.toy_registry(tm.variant(ZC, version=True))) == {"version"}


# --- calculations ------------------------------------------------------------


class NetValueOutputs(ModelOutputs):
    calculation: Literal["net_value"] = Field("net_value", description="Net value")
    net_value: float = Field(0.0, description="Unused")


class PresentValueCopy(tm.PresentValueInputs):
    """Another member claiming the same calculation."""


def test_the_input_and_output_calculations_must_match() -> None:
    outputs = Annotated[
        tm.PresentValueOutputs | tm.FutureValueOutputs | NetValueOutputs,
        Field(discriminator="calculation"),
    ]
    registry = tm.toy_registry(tm.variant(TV, outputs=outputs))
    messages = details_of(registry, "calculation")
    assert any("differ from output calculations" in message for message in messages)


def test_two_members_may_not_share_a_calculation() -> None:
    inputs = Annotated[
        tm.PresentValueInputs | PresentValueCopy | tm.FutureValueInputs,
        Field(discriminator="calculation"),
    ]
    registry = tm.toy_registry(tm.variant(TV, inputs=inputs))
    assert any(
        "repeat the calculation 'present_value'" in message
        for message in details_of(registry, "calculation")
    )
    # pydantic cannot build a validator for it either, and the registry says so.
    assert "io-types" in rules_of(registry)


class TwoCalculations(tm.PresentValueInputs):
    calculation: Literal["one", "two"] = Field("one", description="Two at once")  # type: ignore[assignment]


class ShoutedCalculation(tm.FutureValueInputs):
    calculation: Literal["Future Value"] = Field("Future Value", description="Caps")  # type: ignore[assignment]


BAD_UNIONS = [
    pytest.param(
        Annotated[
            tm.PresentValueInputs | TwoCalculations, Field(discriminator="calculation")
        ],
        "TwoCalculations",
        id="two literals",
    ),
    pytest.param(
        Annotated[
            tm.PresentValueInputs | ShoutedCalculation,
            Field(discriminator="calculation"),
        ],
        "ShoutedCalculation",
        id="not snake_case",
    ),
]


@pytest.mark.parametrize(("inputs", "name"), BAD_UNIONS)
def test_a_calculation_is_one_snake_case_literal(inputs: object, name: str) -> None:
    registry = tm.toy_registry(tm.variant(TV, inputs=inputs))
    messages = details_of(registry, "calculation")
    assert any(f"{name} needs a 'calculation' field" in m for m in messages)


def test_a_compute_that_answers_the_wrong_calculation_is_reported() -> None:
    registry = custom(TV, lambda _inputs: tm.FutureValueOutputs(future_value=1.0))
    [message] = details_of(registry, "examples")
    assert "example 'discount'" in message
    assert "the output calculation differs from the input calculation" in message


# --- charts ------------------------------------------------------------------


class SeriesOutputs(ModelOutputs):
    series: ReturnArray | None = Field(None, max_length=10, description="A series")
    total: float = Field(0.0, description="Unused")


def series_chart(**changes: object) -> ChartSpec:
    fields: dict[str, Any] = {
        "id": "series",
        "title": "Series",
        "kind": ChartKind.LINE,
        "x": "series",
        "y": ("series",),
    }
    return ChartSpec(**{**fields, **changes})


def series_registry(*charts: ChartSpec) -> Registry:
    def compute(_inputs: Any) -> SeriesOutputs:  # noqa: ANN401
        return SeriesOutputs(series=(0.1, 0.2))

    return custom(ZC, compute, outputs=SeriesOutputs, charts=charts)


def test_an_optional_array_output_can_be_charted() -> None:
    registry = series_registry(series_chart())
    assert "charts" not in rules_of(registry)


def test_chart_ids_must_be_unique_and_snake_case() -> None:
    twice = series_registry(series_chart(), series_chart())
    assert details_of(twice, "charts") == ["chart ids are not unique"]
    bad = series_registry(series_chart(id="Bad Id"))
    assert details_of(bad, "charts") == ["chart id 'Bad Id' is not snake_case"]


def test_a_chart_cannot_name_a_field_the_output_lacks() -> None:
    registry = series_registry(series_chart(y=("missing",)))
    assert details_of(registry, "charts") == [
        "chart 'series': 'missing' is not an array output"
    ]


def test_a_chart_for_a_calculation_a_single_model_lacks_is_reported() -> None:
    registry = series_registry(series_chart(calculation="net_value"))
    assert "needs y fields and a known calculation" in details_of(registry, "charts")[0]


def test_a_chart_may_name_the_calculation_it_belongs_to() -> None:
    chart = ChartSpec(
        id="c",
        title="t",
        kind=ChartKind.SCATTER,
        x="future_value",
        y=("future_value",),
        calculation="future_value",
    )
    registry = tm.toy_registry(tm.variant(TV, charts=(chart,)))
    assert details_of(registry, "charts") == [
        "chart 'c': 'future_value' is not an array output"
    ]


# --- extras ------------------------------------------------------------------


def raises_other_extra(_inputs: Any) -> Any:  # noqa: ANN401
    msg = "lib"
    raise MissingOptionalDependencyError(msg, extra="other")


def test_an_example_naming_a_different_extra_is_reported() -> None:
    registry = custom(tm.needs_extra, raises_other_extra)
    [message] = details_of(registry, "examples")
    assert "naming extra 'other', not 'toy'" in message


def test_a_missing_package_in_a_model_with_no_extra_is_reported() -> None:
    registry = custom(ZC, raises_other_extra)
    [message] = details_of(registry, "examples")
    assert "needs a package that is not installed" in message


def test_a_model_that_runs_without_its_missing_extra_is_reported() -> None:
    registry = custom(tm.needs_extra, ZC.compute)
    [message] = details_of(registry, "examples")
    assert "ran although the extra 'toy' is not installed" in message


def test_a_model_whose_extra_is_installed_must_run() -> None:
    registry = Registry.from_models(
        tm.needs_extra, distribution="toy-dist", extras={"toy": ("pydantic",)}
    )
    [message] = details_of(registry, "examples")
    assert "needs a package that is not installed" in message
    spec = dataclasses.replace(tm.needs_extra.spec, id="econometrics.toy_installed")
    working = Registry.from_models(
        Model(spec, ZC.compute), distribution="toy-dist", extras={"toy": ("pydantic",)}
    )
    assert working.problems(released={}) == []


def test_a_failing_validate_names_every_extra_problem() -> None:
    registry = custom(tm.needs_extra, ZC.compute)
    with pytest.raises(RegistryError, match=r"\[examples\]"):
        registry.validate(released={})


# --- a package an extra's marker leaves out of this Python (Phase 3 Step 17) -------


def test_a_model_naming_a_package_its_extra_excludes_here_passes() -> None:
    spec = dataclasses.replace(tm.needs_extra.spec, id="econometrics.toy_gap")
    gap = Registry.from_models(
        Model(spec, tm.needs_extra.compute),
        distribution="toy-dist",
        extras={"toy": ("pydantic",)},
        excluded={"toy": ("toy_library",)},
    )
    assert gap.problems(released={}) == []


def test_a_missing_package_its_extra_should_install_is_still_a_problem() -> None:
    spec = dataclasses.replace(tm.needs_extra.spec, id="econometrics.toy_gap")
    wrong = Registry.from_models(
        Model(spec, tm.needs_extra.compute),
        distribution="toy-dist",
        extras={"toy": ("pydantic",)},
        excluded={"toy": ("another_library",)},
    )
    [message] = details_of(wrong, "examples")
    assert "needs a package that is not installed" in message


def test_an_excluded_package_named_under_another_extra_is_a_problem() -> None:
    def other(_inputs: Any) -> Any:  # noqa: ANN401
        library = "toy_library"
        raise MissingOptionalDependencyError(library, extra="other")

    spec = dataclasses.replace(tm.needs_extra.spec, id="econometrics.toy_gap")
    wrong = Registry.from_models(
        Model(spec, other),
        distribution="toy-dist",
        extras={"toy": ("pydantic",)},
        excluded={"toy": ("toy_library",)},
    )
    [message] = details_of(wrong, "examples")
    assert "needs a package that is not installed" in message
