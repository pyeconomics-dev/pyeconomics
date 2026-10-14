# tests/registry/toy_results_models.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""More toy models, for the result, schema, card and plotting tests (Step 4).

``toy_models`` covers the registry's shapes. These add what results need: array
outputs with a chart, dates and a nullable output, a seeded stochastic model, and
models that fail with each error a run lets through.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any, Literal

from pydantic import Field

from pyeconomics.core import (
    SEED_MAX,
    ChangelogEntry,
    ChartKind,
    ChartSpec,
    ConvergenceError,
    CostClass,
    Count,
    CountArray,
    DateValue,
    Days,
    DomainError,
    Evidence,
    Example,
    Invariant,
    Model,
    ModelInputs,
    ModelOutputs,
    Money,
    MoneyArray,
    Rate,
    Ratio,
    Reference,
    generator,
    model,
    warn,
)

BOOK = Reference(
    key="hull2022",
    citation="Hull, J. (2022). Options, Futures, and Other Derivatives. Pearson.",
    doi="10.1000/toy",
    locator="Chapter 4",
)

COMMON: dict[str, Any] = {
    "formula": (r"x_t = x_0 (1 + r)^t",),
    "assumptions": ("A constant rate.",),
    "limitations": ("A toy.",),
    "references": (BOOK,),
    "evidence": Evidence.STANDARD,
    "cost": CostClass.INSTANT,
    "changelog": (ChangelogEntry(version=1, note="First version."),),
}


class GrowthInputs(ModelInputs):
    """An input class description distinct from the model summary (#83)."""

    start: Money = Field(gt=0, le=1e9, description="Starting balance")
    rate: Rate = Field(ge=-0.5, le=1.0, description="Rate per period")
    periods: Count = Field(ge=1, le=40, description="Number of periods")


class GrowthOutputs(ModelOutputs):
    """An output class description distinct from the model summary (#83)."""

    period: CountArray = Field(max_length=41, description="Period numbers")
    balance: MoneyArray = Field(max_length=41, description="Balance at each period")
    final: Money = Field(ge=0, le=1e15, description="Final balance")


@model(
    id="foundations.toy_growth",
    version=1,
    title="Toy growth path",
    summary="A balance compounding at a constant rate, period by period.",
    invariants=(Invariant(id="final_is_last", statement="final is the last balance."),),
    examples=(
        Example(name="five_periods", inputs={"start": 100, "rate": 0.05, "periods": 5}),
    ),
    charts=(
        ChartSpec(
            id="path",
            title="Balance over time",
            kind=ChartKind.LINE,
            x="period",
            y=("balance",),
            x_label="Period",
            y_label="Balance",
        ),
        ChartSpec(
            id="bars",
            title="Balance by period",
            kind=ChartKind.BAR,
            x="period",
            y=("balance",),
        ),
        ChartSpec(
            id="dots",
            title="Balance points",
            kind=ChartKind.SCATTER,
            x="period",
            y=("balance",),
        ),
    ),
    **COMMON,
)
def growth(inputs: GrowthInputs) -> GrowthOutputs:
    balances = tuple(
        inputs.start * (1 + inputs.rate) ** t for t in range(inputs.periods + 1)
    )
    return GrowthOutputs(
        period=tuple(range(inputs.periods + 1)),
        balance=balances,
        final=balances[-1],
    )


class SingleChartInputs(ModelInputs):
    periods: Count = Field(ge=1, le=10, description="Number of periods")


class SingleChartOutputs(ModelOutputs):
    period: CountArray = Field(max_length=11, description="Period numbers")
    level: MoneyArray = Field(max_length=11, description="Level")


@model(
    id="foundations.toy_one_chart",
    version=1,
    title="Toy model with one chart",
    summary="A line that rises by one each period.",
    no_invariants_reason="A toy.",
    examples=(Example(name="three", inputs={"periods": 3}),),
    charts=(
        ChartSpec(
            id="line", title="Level", kind=ChartKind.LINE, x="period", y=("level",)
        ),
    ),
    **COMMON,
)
def one_chart(inputs: SingleChartInputs) -> SingleChartOutputs:
    steps = tuple(range(inputs.periods + 1))
    return SingleChartOutputs(period=steps, level=tuple(float(s) for s in steps))


class NoChartInputs(ModelInputs):
    x: Ratio = Field(ge=-10, le=10, description="A number")


class NoChartOutputs(ModelOutputs):
    doubled: Ratio = Field(ge=-20, le=20, description="Twice the number")


@model(
    id="foundations.toy_no_chart",
    version=1,
    title="Toy model with no chart",
    summary="Doubles a number.",
    no_invariants_reason="A toy.",
    examples=(Example(name="three", inputs={"x": 3}),),
    **COMMON,
)
def no_chart(inputs: NoChartInputs) -> NoChartOutputs:
    return NoChartOutputs(doubled=2 * inputs.x)


class DatedInputs(ModelInputs):
    start: DateValue = Field(
        ge=dt.date(1900, 1, 1), le=dt.date(2200, 12, 31), description="Start date"
    )
    days: Days = Field(ge=0, le=3650, description="Days to add")


class DatedOutputs(ModelOutputs):
    end: DateValue = Field(
        ge=dt.date(1900, 1, 1), le=dt.date(2300, 1, 1), description="End date"
    )
    per_day: Ratio | None = Field(ge=-1e6, le=1e6, description="One over the days")
    dates: Annotated[
        tuple[DateValue, ...], Field(max_length=2, description="Both dates")
    ]


@model(
    id="foundations.toy_dated",
    version=1,
    title="Toy date arithmetic",
    summary="Adds days to a date; the daily ratio is undefined for zero days.",
    no_invariants_reason="A toy.",
    examples=(
        Example(name="thirty", inputs={"start": "2026-01-31", "days": 30}),
        Example(name="zero", inputs={"start": dt.date(2026, 1, 31), "days": 0}),
    ),
    **COMMON,
)
def dated(inputs: DatedInputs) -> DatedOutputs:
    end = inputs.start + dt.timedelta(days=inputs.days)
    per_day = None
    if inputs.days == 0:
        warn("zero_days", "the daily ratio is undefined for zero days")
    else:
        per_day = 1 / inputs.days
    return DatedOutputs(end=end, per_day=per_day, dates=(inputs.start, end))


class NoisyInputs(ModelInputs):
    seed: Count = Field(default=0, ge=0, le=SEED_MAX, description="Random seed")
    n: Count = Field(default=3, ge=1, le=100, description="Draws")


class NoisyOutputs(ModelOutputs):
    mean: Ratio = Field(ge=-1e6, le=1e6, description="Mean of the draws")


@model(
    id="foundations.toy_noisy",
    version=1,
    title="Toy seeded draws",
    summary="The mean of standard normal draws from a seeded generator.",
    no_invariants_reason="A toy.",
    examples=(Example(name="seed_seven", inputs={"seed": 7, "n": 5}),),
    **COMMON,
)
def noisy(inputs: NoisyInputs) -> NoisyOutputs:
    draws = generator(inputs.seed).standard_normal(inputs.n)
    return NoisyOutputs(mean=float(draws.mean()))


class FailingInputs(ModelInputs):
    x: Ratio = Field(ge=-10, le=10, description="Below zero is a domain error")
    mode: Literal["ok", "domain", "convergence", "bad_output"] = Field(
        "ok", description="What to do"
    )


class FailingOutputs(ModelOutputs):
    y: Ratio = Field(ge=0, le=1, description="Must lie in [0, 1]")


@model(
    id="foundations.toy_failing",
    version=1,
    title="Toy model that fails on request",
    summary="Raises each error a run lets through.",
    no_invariants_reason="A toy.",
    examples=(Example(name="fine", inputs={"x": 0.5}),),
    **COMMON,
)
def failing(inputs: FailingInputs) -> FailingOutputs:
    if inputs.mode == "domain":
        msg = "no defined result"
        raise DomainError(msg)
    if inputs.mode == "convergence":
        msg = "no root"
        raise ConvergenceError(msg)
    if inputs.mode == "bad_output":
        return FailingOutputs.model_construct(y=5.0)
    return FailingOutputs(y=inputs.x)


ALL_MODELS: tuple[Model[Any, Any], ...] = (
    dated,
    failing,
    growth,
    no_chart,
    noisy,
    one_chart,
)
