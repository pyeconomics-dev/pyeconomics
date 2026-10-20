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
_CREDIT: Final = (
    "Credit Aswath Damodaran; the source publishes aggregates, not a bulk mirror."
)


def _damodaran(column: str) -> Candidate:
    """Return a column of Damodaran's implied equity risk premium file."""
    return Candidate(
        provider="damodaran",
        series="implied_erp",
        column=column,
        note=(
            f"{_CREDIT} He adjusts the base cash flow in some years (normalized "
            "in 2011 and 2012, for COVID in 2020, from estimated earnings since "
            "2021), so these year-end values reproduce his published premium "
            "only where he used them as they stand."
        ),
    )


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
    Concept(
        id="us.equity.sp_composite_price",
        title="S&P composite stock price, Shiller",
        definition=(
            "Robert Shiller's monthly S&P composite stock price index: the "
            "average of the month's daily closes (the latest month may be a "
            "single day's close), in index points."
        ),
        unit_kind=UnitKind.INDEX_LEVEL,
        unit_text="index points",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=_NA,
        candidates=(Candidate(provider="shiller", series="us_equity", column="price"),),
        section=_SECTION,
    ),
    Concept(
        id="us.equity.sp_composite_earnings",
        title="S&P composite earnings, Shiller",
        definition=(
            "Robert Shiller's monthly S&P composite earnings per share of the "
            "index: four-quarter totals interpolated between quarters (annual "
            "Cowles data before 1926), in index points; recent months are blank "
            "until the totals are published."
        ),
        unit_kind=UnitKind.MONEY,
        unit_text="index points (US dollars per unit of the index)",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=_NA,
        candidates=(
            Candidate(provider="shiller", series="us_equity", column="earnings"),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.prices.cpi_long_run",
        title="Consumer price index, Shiller's long-run series",
        definition=(
            "The monthly consumer price index Robert Shiller deflates his equity "
            "data with: the CPI-U, not seasonally adjusted, spliced to Warren and "
            "Pearson's index before 1913; the latest months are his estimates."
        ),
        unit_kind=UnitKind.INDEX_LEVEL,
        unit_text="index level",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        candidates=(Candidate(provider="shiller", series="us_equity", column="cpi"),),
        section=_SECTION,
    ),
    Concept(
        id="us.equity.sp500_year_end",
        title="S&P 500 at year end, Damodaran",
        definition=(
            "The S&P 500's level at the end of each year, as Aswath Damodaran's "
            "implied equity risk premium file records it, in index points."
        ),
        unit_kind=UnitKind.INDEX_LEVEL,
        unit_text="index points",
        frequency=ObservationFrequency.ANNUAL,
        seasonal_adjustment=_NA,
        candidates=(_damodaran("s_p_500_3"),),
        section=_SECTION,
    ),
    Concept(
        id="us.equity.sp500_dividends_buybacks",
        title="S&P 500 dividends plus buybacks, Damodaran",
        definition=(
            "The dividends and buybacks of the S&P 500's companies over each year, "
            "per unit of the index, as Aswath Damodaran's implied equity risk "
            "premium file records them at the year's end, in index points."
        ),
        unit_kind=UnitKind.MONEY,
        unit_text="index points (US dollars per unit of the index)",
        frequency=ObservationFrequency.ANNUAL,
        seasonal_adjustment=_NA,
        candidates=(_damodaran("dividends_buybacks_6"),),
        section=_SECTION,
    ),
    Concept(
        id="us.equity.sp500_expected_growth",
        title="S&P 500 expected earnings growth, Damodaran",
        definition=(
            "The analysts' top-down estimate of the S&P 500's annual earnings "
            "growth for the next five years, at each year's end, as Aswath "
            "Damodaran's implied equity risk premium file records it, as a "
            "decimal."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.06 is 6%)",
        frequency=ObservationFrequency.ANNUAL,
        seasonal_adjustment=_NA,
        candidates=(_damodaran("analyst_growth_estimate_14"),),
        section=_SECTION,
    ),
)
