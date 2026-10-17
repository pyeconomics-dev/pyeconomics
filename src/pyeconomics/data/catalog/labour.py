# src/pyeconomics/data/catalog/labour.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""United States labour-market concepts: the unemployment rate and its natural rate."""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import Candidate, Concept, Tier
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS"]

_SECTION: Final = "Labour"

CONCEPTS: Final = (
    Concept(
        id="us.unemployment.rate",
        title="Unemployment rate",
        definition=(
            "The share of the civilian labour force aged 16 and over that is "
            "unemployed, monthly and seasonally adjusted, as a decimal."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal (0.042 is 4.2%)",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        candidates=(
            Candidate(
                provider="bls",
                series="LNS14000000",
                note=(
                    "BLS marks the unit of a rate only in its keyed (v2) API, so "
                    "this candidate needs a BLS key; without one the resolver "
                    "falls to FRED."
                ),
            ),
            Candidate(provider="fred", series="UNRATE", tier=Tier.AGGREGATOR),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.unemployment.noncyclical_rate",
        title="Noncyclical rate of unemployment",
        definition=(
            "The Congressional Budget Office's estimate of the unemployment "
            "rate that would prevail with no cyclical pressure on the labour "
            "market (its natural rate), quarterly, as a decimal. The series "
            "extends into CBO's projection years."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal (0.042 is 4.2%)",
        frequency=ObservationFrequency.QUARTERLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Candidate(
                provider="cbo",
                series="quarterly:noncyclical_rate_of_unemployment",
                note=(
                    "Each CBO report is a vintage, so a run as of a past date "
                    "reads the estimate CBO had published then."
                ),
            ),
            Candidate(provider="fred", series="NROU", tier=Tier.AGGREGATOR),
        ),
        section=_SECTION,
    ),
)
