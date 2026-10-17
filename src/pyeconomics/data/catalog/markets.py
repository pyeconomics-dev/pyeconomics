# src/pyeconomics/data/catalog/markets.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Long-run US equity market series from Shiller and Damodaran."""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import Candidate, Concept, Shape
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS"]

_SECTION: Final = "Equity markets"
_NA: Final = SeasonalAdjustment.NOT_APPLICABLE

CONCEPTS: Final = (
    Concept(
        id="equity.shiller.us.monthly",
        title="Shiller US equity data, monthly",
        definition=(
            "Robert Shiller's monthly US stock market series from 1871: the "
            "S&P composite price, dividends and earnings, the consumer price "
            "index, the long-term interest rate and the cyclically adjusted "
            "price-to-earnings ratio, each as the source publishes it."
        ),
        unit_kind=None,
        unit_text=(
            "mixed: prices and index levels in source units, the long rate as a decimal"
        ),
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=_NA,
        shape=Shape.TABLE,
        candidates=(
            Candidate(
                provider="shiller",
                series="us_equity",
                note="Library-only: no stated licence; fetched at run time.",
            ),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.equity.cape",
        title="Cyclically adjusted price-to-earnings ratio",
        definition=(
            "Shiller's CAPE: the real S&P composite price over the average of "
            "its real earnings for the previous ten years, monthly."
        ),
        unit_kind=UnitKind.RATIO,
        unit_text="ratio (price to ten-year average earnings)",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=_NA,
        candidates=(Candidate(provider="shiller", series="us_equity", column="cape"),),
        section=_SECTION,
    ),
    Concept(
        id="us.equity.implied_erp",
        title="Implied equity risk premium",
        definition=(
            "Aswath Damodaran's implied equity risk premium for the S&P 500 at "
            "the end of each year, from the free cash flow to equity model, as "
            "a decimal."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.045 is 4.5%)",
        frequency=ObservationFrequency.ANNUAL,
        seasonal_adjustment=_NA,
        candidates=(
            Candidate(
                provider="damodaran",
                series="implied_erp",
                column="implied_erp_fcfe_15",
                note=(
                    "Credit Aswath Damodaran; the source publishes aggregates, "
                    "not a bulk mirror."
                ),
            ),
        ),
        section=_SECTION,
    ),
)
