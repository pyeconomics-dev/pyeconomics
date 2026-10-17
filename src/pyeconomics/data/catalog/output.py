# src/pyeconomics/data/catalog/output.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""United States output concepts: GDP, potential GDP and the output gap."""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import (
    Candidate,
    Concept,
    Derived,
    Operand,
    Tier,
)
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS"]

_SECTION: Final = "Output"
_QUARTERLY: Final = ObservationFrequency.QUARTERLY
_BEA_NOTE: Final = (
    "BEA's API serves current estimates only, so a run on it records revised_data."
)

CONCEPTS: Final = (
    Concept(
        id="us.output.real_gdp",
        title="Real GDP",
        definition=(
            "US gross domestic product in chained 2017 dollars, quarterly at a "
            "seasonally adjusted annual rate."
        ),
        unit_kind=UnitKind.MONEY,
        unit_text="chained 2017 US dollars per year",
        frequency=_QUARTERLY,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
        candidates=(
            Candidate(provider="bea", series="NIPA/T10106/Q/1", note=_BEA_NOTE),
            Candidate(provider="fred", series="GDPC1", tier=Tier.AGGREGATOR),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.output.potential_gdp",
        title="Real potential GDP",
        definition=(
            "The Congressional Budget Office's estimate of the real output the "
            "US economy can produce at stable inflation, in chained 2017 "
            "dollars, quarterly. The series extends into CBO's projection years."
        ),
        unit_kind=UnitKind.MONEY,
        unit_text="chained 2017 US dollars per year",
        frequency=_QUARTERLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Candidate(
                provider="cbo",
                series="quarterly:real_potential_gdp",
                note="Each CBO report is a vintage.",
            ),
            Candidate(provider="fred", series="GDPPOT", tier=Tier.AGGREGATOR),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.output.nominal_gdp",
        title="Nominal GDP",
        definition=(
            "US gross domestic product in current dollars, quarterly at a "
            "seasonally adjusted annual rate."
        ),
        unit_kind=UnitKind.MONEY,
        unit_text="current US dollars per year",
        frequency=_QUARTERLY,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
        candidates=(
            Candidate(provider="bea", series="NIPA/T10105/Q/1", note=_BEA_NOTE),
            Candidate(provider="fred", series="GDP", tier=Tier.AGGREGATOR),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.output.nominal_gdp.yoy",
        title="Nominal GDP growth, year over year",
        definition=(
            "The change in nominal GDP over the same quarter a year earlier, as "
            "a decimal: the growth rate in the denominator of debt dynamics."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.05 is 5%)",
        frequency=_QUARTERLY,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
        candidates=(
            Candidate(
                provider="bea",
                series="NIPA/T10105/Q/1",
                transforms=("yoy",),
                note=_BEA_NOTE,
            ),
            Candidate(
                provider="fred",
                series="GDP",
                transforms=("yoy",),
                tier=Tier.AGGREGATOR,
            ),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.output_gap.cbo",
        title="Output gap, CBO",
        definition=(
            "The Congressional Budget Office's output gap: actual real GDP less "
            "potential real GDP, as a decimal share of potential, quarterly. The "
            "series extends into CBO's projection years."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal share of potential GDP (-0.01 is 1% below)",
        frequency=_QUARTERLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Candidate(
                provider="cbo",
                series="quarterly:output_gap",
                note="Each CBO report is a vintage.",
            ),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.output_gap.real_potential",
        title="Output gap, real GDP over potential",
        definition=(
            "Real GDP over CBO's real potential GDP, less one, quarterly, on the "
            "quarters both are published: a gap built from the two concepts "
            "rather than read from CBO's own gap series."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal share of potential GDP (-0.01 is 1% below)",
        frequency=_QUARTERLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Derived(
                operands=(
                    Operand("us.output.real_gdp"),
                    Operand("us.output.potential_gdp"),
                ),
                transform="ratio(excess=true)",
            ),
        ),
        section=_SECTION,
    ),
)
