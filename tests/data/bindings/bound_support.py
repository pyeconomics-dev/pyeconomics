# tests/data/bindings/bound_support.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Toy bound models over scripted providers, for the binding tests (Step 12).

The models bind to real catalog concepts, so the tests prove the catalog, the
resolver and the binding layer agree. The providers are scripted stand-ins with
the real providers' ids, so the resolver's own gates run for real: ``bls`` keeps
no vintages, ``fred`` keeps them (and is library-only), ``oecd`` keeps none and
is the only source of its concept, and ``bea`` serves current estimates only.

The data is invented. Unemployment is monthly; ``fred`` lists, for each month, the
first release and later revisions with their real-time periods (ALFRED's
semantics), so a bind as of a date reads what was published by then:

=========  ==============================  ===============
month      first release (from)            revised (from)
=========  ==============================  ===============
2024-01    0.037 (2024-02-02)              0.038 (03-01)
2024-02    0.039 (2024-03-08)              0.040 (04-05)
2024-03    0.038 (2024-04-05)
2024-04    0.039 (2024-05-03)
2024-05    0.040 (2024-06-07)
2024-06    0.041 (2024-07-05)
=========  ==============================  ===============
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING, Annotated, Any

from catalog_support import HOSTED_TERMS, LIBRARY_TERMS, period_ends
from pydantic import Field
from scripted import registry_of, scripted

from pyeconomics.core import (
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    Model,
    ModelInputs,
    ModelOutputs,
    Money,
    Rate,
    RateArray,
    Reference,
    Registry,
    UnitKind,
    VintagePolicy,
    model,
)
from pyeconomics.data import (
    Capability,
    ObservationFrequency,
    RealtimePeriod,
    SeasonalAdjustment,
    Series,
    UnitRecord,
)

if TYPE_CHECKING:
    from pyeconomics.data.providers.base import DataProvider
    from pyeconomics.data.registry import ProviderRegistry

#: When the scripted providers say they fetched.
FETCHED = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.UTC)

MONTHS = period_ends(ObservationFrequency.MONTHLY, (2024, 1), 6)

#: (month index, value, real-time start, real-time end or None).
VINTAGED = (
    (0, 0.037, dt.date(2024, 2, 2), dt.date(2024, 2, 29)),
    (0, 0.038, dt.date(2024, 3, 1), None),
    (1, 0.039, dt.date(2024, 3, 8), dt.date(2024, 4, 4)),
    (1, 0.040, dt.date(2024, 4, 5), None),
    (2, 0.038, dt.date(2024, 4, 5), None),
    (3, 0.039, dt.date(2024, 5, 3), None),
    (4, 0.040, dt.date(2024, 6, 7), None),
    (5, 0.041, dt.date(2024, 7, 5), None),
)
#: The values as they stand today: each month's last revision.
REVISED = (0.038, 0.040, 0.038, 0.039, 0.040, 0.041)

RATE = UnitRecord(text="Decimal", kind=UnitKind.RATE)
REFERENCE = Reference(
    key="toy2026",
    citation="A toy source for the binding tests (2026).",
    url="https://www.example.org/toy",
    locator="Table 1",
)


def _unemployment(provider: str, *, vintaged: bool, **changes: Any) -> Series:  # noqa: ANN401
    from catalog_support import meta  # noqa: PLC0415 - the shared meta builder

    base = meta(
        ObservationFrequency.MONTHLY,
        provider=provider,
        series_id="UNRATE" if vintaged else "LNS14000000",
        title="Unemployment rate",
        unit=RATE,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        terms=LIBRARY_TERMS if vintaged else HOSTED_TERMS,
    )
    base = replace(base, **changes)
    if vintaged:
        return Series(
            tuple(MONTHS[row] for row, *_ in VINTAGED),
            tuple(value for _, value, *_ in VINTAGED),
            base,
            tuple(RealtimePeriod(start, end) for *_, start, end in VINTAGED),
        )
    return Series(MONTHS, REVISED, base)


def bls(**changes: Any) -> type[DataProvider]:  # noqa: ANN401 - series metadata
    """The originator: current values only, and hosted-safe."""
    return scripted(
        "bls", {"LNS14000000": _unemployment("bls", vintaged=False, **changes)}
    )


def fred(*, keyed: bool = False, **changes: Any) -> type[DataProvider]:  # noqa: ANN401
    """The aggregator: every vintage, and library-only (optionally needing a key)."""
    from pyeconomics.core import LicenceClass  # noqa: PLC0415

    return scripted(
        "fred",
        {"UNRATE": _unemployment("fred", vintaged=True, **changes)},
        licence=LicenceClass.LIBRARY_ONLY,
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        keyed=keyed,
    )


UK_INFLATION = "OECD.SDD.TPS/DSD_PRICES@DF_PRICES_ALL/GBR.M.N.CPI.PA._T.N.GY"
REAL_GDP = "NIPA/T10106/Q/1"
#: Real GDP in billions of dollars, by quarter from 2023 Q4.
GDP_BILLIONS = (22_000.0, 22_100.0, 22_250.0, 22_400.0)


def oecd() -> type[DataProvider]:
    """The only source of UK inflation: current values, no vintages."""
    from catalog_support import meta  # noqa: PLC0415

    series = Series(
        MONTHS,
        (0.040, 0.034, 0.032, 0.023, 0.020, 0.020),
        meta(
            ObservationFrequency.MONTHLY,
            provider="oecd",
            series_id=UK_INFLATION,
            unit=RATE,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        ),
    )
    return scripted("oecd", {UK_INFLATION: series})


def bea() -> type[DataProvider]:
    """Real GDP in billions of dollars: BEA's API serves current estimates only."""
    from catalog_support import meta  # noqa: PLC0415

    series = Series(
        period_ends(ObservationFrequency.QUARTERLY, (2023, 12), 4),
        GDP_BILLIONS,
        meta(
            ObservationFrequency.QUARTERLY,
            provider="bea",
            series_id=REAL_GDP,
            unit=UnitRecord(
                text="Billions of chained 2017 dollars",
                kind=UnitKind.MONEY,
                scale=1e9,
                currency="USD",
            ),
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
            notes=("revised_data: BEA's API serves its current estimates",),
        ),
    )
    return scripted("bea", {REAL_GDP: series})


def world(*providers: type[DataProvider]) -> ProviderRegistry:
    """An isolated provider registry: the four scripted ones unless others are given."""
    return registry_of(*(providers or (bea(), bls(), fred(), oecd())))


# --- the toy models -----------------------------------------------------------------

_COMMON: dict[str, Any] = {
    "formula": (r"y = 2 u",),
    "assumptions": ("A toy: the unemployment rate stands for anything bound.",),
    "limitations": ("It models nothing.",),
    "references": (REFERENCE,),
    "evidence": Evidence.PRACTITIONER,
    "cost": CostClass.INSTANT,
    "changelog": (ChangelogEntry(version=1, note="First version."),),
}


class RateInputs(ModelInputs):
    unemployment: Rate = Field(ge=0, le=1, description="The unemployment rate")
    change: Rate = Field(0.0, ge=-1, le=1, description="Its change, bound or supplied")
    weight: Rate = Field(1.0, ge=0, le=10, description="A plain input, never bound")


class RateOutputs(ModelOutputs):
    score: Rate = Field(ge=-10, le=10, description="The weighted unemployment rate")


@model(
    id="macro.toy_unemployment",
    version=1,
    title="Toy unemployment score",
    summary="Weights the unemployment rate, which it reads from the catalog.",
    invariants=(
        Invariant(id="score_follows_input", statement="The score scales the input."),
    ),
    examples=(
        Example(
            name="four_percent",
            inputs={"unemployment": 0.04, "change": 0.0, "weight": 2.0},
        ),
    ),
    bindings=(
        Binding("unemployment", "us.unemployment.rate"),
        Binding(
            "unemployment",
            "us.unemployment.rate",
            vintage=VintagePolicy.LATEST,
            profile="revised",
        ),
        Binding("unemployment", "gb.inflation.cpi.yoy", profile="uk"),
    ),
    **_COMMON,
)
def unemployment(inputs: RateInputs) -> RateOutputs:
    return RateOutputs(score=inputs.unemployment * inputs.weight)


@model(
    id="macro.toy_unemployment_change",
    version=1,
    title="Toy unemployment change",
    summary="Binds one concept to two fields, level and change.",
    invariants=(
        Invariant(id="score_follows_input", statement="The score scales the input."),
    ),
    examples=(Example(name="rising", inputs={"unemployment": 0.04, "change": 0.001}),),
    bindings=(
        Binding("unemployment", "us.unemployment.rate"),
        Binding("change", "us.unemployment.rate", transform="diff"),
    ),
    **_COMMON,
)
def unemployment_change(inputs: RateInputs) -> RateOutputs:
    return RateOutputs(score=inputs.unemployment + inputs.change)


class WindowInputs(ModelInputs):
    history: RateArray = Field(min_length=1, max_length=12, description="Recent rates")


class WindowOutputs(ModelOutputs):
    mean: Rate = Field(ge=-1, le=1, description="The mean of the window")


@model(
    id="macro.toy_unemployment_window",
    version=1,
    title="Toy unemployment window",
    summary="Averages the last four unemployment rates, read as a window.",
    invariants=(
        Invariant(id="mean_within_range", statement="The mean lies in the window."),
    ),
    examples=(Example(name="flat", inputs={"history": [0.04, 0.04, 0.04, 0.04]}),),
    bindings=(Binding("history", "us.unemployment.rate", as_of=AsOf.WINDOW, window=4),),
    **_COMMON,
)
def unemployment_window(inputs: WindowInputs) -> WindowOutputs:
    return WindowOutputs(mean=sum(inputs.history) / len(inputs.history))


class MoneyInputs(ModelInputs):
    output: Annotated[Money, Field(ge=0, le=1e15, description="Real GDP in dollars")]


class MoneyOutputs(ModelOutputs):
    doubled: Money = Field(ge=0, le=1e16, description="Twice the output")


@model(
    id="macro.toy_output",
    version=1,
    title="Toy output doubling",
    summary="Doubles real GDP, which it reads in billions and takes in dollars.",
    invariants=(Invariant(id="doubles", statement="The output is twice the input."),),
    examples=(Example(name="trillion", inputs={"output": 1e12}),),
    bindings=(Binding("output", "us.output.real_gdp", as_of=AsOf.PERIOD),),
    **_COMMON,
)
def output(inputs: MoneyInputs) -> MoneyOutputs:
    return MoneyOutputs(doubled=2 * inputs.output)


@model(
    id="macro.toy_plain",
    version=1,
    title="Toy model that reads no data",
    summary="Weights a rate; it declares no bindings.",
    invariants=(
        Invariant(id="score_follows_input", statement="The score scales the input."),
    ),
    examples=(Example(name="plain", inputs={"unemployment": 0.04}),),
    **_COMMON,
)
def plain(inputs: RateInputs) -> RateOutputs:
    return RateOutputs(score=inputs.unemployment * inputs.weight)


def bound_to(concept: str, *, model_id: str = "macro.toy_bound_to") -> Model[Any, Any]:
    """A toy model whose ``unemployment`` field is bound to any concept id."""

    @model(
        id=model_id,
        version=1,
        title="Toy model bound to a concept",
        summary="Weights a rate, which it reads from the concept given.",
        invariants=(
            Invariant(
                id="score_follows_input", statement="The score scales the input."
            ),
        ),
        examples=(Example(name="plain", inputs={"unemployment": 0.04}),),
        bindings=(Binding("unemployment", concept),),
        **_COMMON,
    )
    def bound(inputs: RateInputs) -> RateOutputs:
        return RateOutputs(score=inputs.unemployment * inputs.weight)

    return bound


BOUND_MODELS: tuple[Model[Any, Any], ...] = (
    output,
    plain,
    unemployment,
    unemployment_change,
    unemployment_window,
)


def model_registry(*models: Model[Any, Any]) -> Registry:
    """An isolated model registry of the toy bound models."""
    return Registry.from_models(*(models or BOUND_MODELS), distribution="toy-dist")
