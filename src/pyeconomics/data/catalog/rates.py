# src/pyeconomics/data/catalog/rates.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""United States policy rates, Treasury yield curves and neutral-rate estimates."""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import Candidate, Concept, Shape, Tier
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS"]

_POLICY: Final = "Policy rates"
_CURVES: Final = "Treasury curves"
_NEUTRAL: Final = "Neutral rates"
_DAILY: Final = ObservationFrequency.BUSINESS_DAILY
_NA: Final = SeasonalAdjustment.NOT_APPLICABLE
_TREASURY_NOTE: Final = (
    "Treasury labels its curve files by business day, which the data layer "
    "records as irregular; the concept's cadence is daily all the same."
)
#: ALFRED holds no vintages of FRED's daily rate series (checked 2026-10-18: a
#: real-time request for each is refused), so a binding reads them as revised data.
_NO_ALFRED: Final = (
    "ALFRED keeps no vintages of this daily series, so a real-time request skips "
    "it and a binding reads it as revised data."
)
_CURVE_WINDOW: Final = (
    "Treasury serves its curve files by date range, so a request needs both "
    "start and end."
)

#: The nominal tenors Treasury has published since 2008, as (concept, source).
_NOMINAL: Final = (
    ("1m", "BC_1MONTH"),
    ("2m", "BC_2MONTH"),
    ("3m", "BC_3MONTH"),
    ("4m", "BC_4MONTH"),
    ("6m", "BC_6MONTH"),
    ("1y", "BC_1YEAR"),
    ("2y", "BC_2YEAR"),
    ("3y", "BC_3YEAR"),
    ("5y", "BC_5YEAR"),
    ("7y", "BC_7YEAR"),
    ("10y", "BC_10YEAR"),
    ("20y", "BC_20YEAR"),
    ("30y", "BC_30YEAR"),
)
_REAL: Final = (
    ("5y", "TC_5YEAR"),
    ("7y", "TC_7YEAR"),
    ("10y", "TC_10YEAR"),
    ("20y", "TC_20YEAR"),
    ("30y", "TC_30YEAR"),
)


def _gsw(column: str, title: str, definition: str) -> Concept:
    """One Svensson parameter of the Board's GSW fit, as a daily series."""
    decay = column.startswith("TAU")
    return Concept(
        id=f"us.treasury.gsw_{column.lower()}",
        title=f"Gürkaynak-Sack-Wright curve: {title}",
        definition=(
            f"{definition} Of the Federal Reserve Board staff's daily Svensson fit "
            "of the Treasury yield curve (Gürkaynak, Sack and Wright), "
            + ("in years." if decay else "as a decimal (the Board prints percent).")
        ),
        unit_kind=UnitKind.YEARS if decay else UnitKind.RATIO,
        unit_text=(
            "years"
            if decay
            else "a coefficient in decimal rate units (0.04 is 4 percentage points)"
        ),
        frequency=_DAILY,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        candidates=(
            Candidate(
                provider="fed_board",
                series="gsw",
                column=column,
                delivers=ObservationFrequency.IRREGULAR,
                note=(
                    "Staff estimates, revised with the file. Before 1980 the fit "
                    "is Nelson-Siegel, and BETA3 and TAU2 are missing."
                    if column in {"BETA3", "TAU2"}
                    else "Staff estimates, revised with the file."
                ),
            ),
        ),
        section=_CURVES,
    )


_GSW_PARAMETERS: Final = (
    _gsw("BETA0", "level (beta0)", "The level: the yield as maturity grows."),
    _gsw(
        "BETA1",
        "slope (beta1)",
        "The slope: beta0 + beta1 is the instantaneous short rate.",
    ),
    _gsw("BETA2", "first hump (beta2)", "The size of the curve's first hump."),
    _gsw("BETA3", "second hump (beta3)", "The size of the curve's second hump."),
    _gsw("TAU1", "first decay (tau1)", "Where the first hump's loading peaks."),
    _gsw("TAU2", "second decay (tau2)", "Where the second hump's loading peaks."),
)


def _yield(
    concept_id: str,
    title: str,
    definition: str,
    column: str,
    fred: str,
) -> Concept:
    return Concept(
        id=concept_id,
        title=title,
        definition=definition,
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.04 is 4%)",
        frequency=_DAILY,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        candidates=(
            Candidate(
                provider="treasury",
                series="par_real" if column.startswith("TC_") else "par_nominal",
                column=column,
                delivers=ObservationFrequency.IRREGULAR,
                note=_TREASURY_NOTE,
            ),
            Candidate(
                provider="fred",
                series=fred,
                tier=Tier.AGGREGATOR,
                vintages=False,
                note=_NO_ALFRED,
            ),
        ),
        needs_window=True,
        notes=(_CURVE_WINDOW,),
        section=_CURVES,
    )


CONCEPTS: Final = (
    Concept(
        id="us.policy_rate.effective",
        title="Effective federal funds rate",
        definition=(
            "The volume-weighted median rate on overnight federal funds "
            "transactions, published each business day by the Federal Reserve "
            "Bank of New York, as a decimal."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.04 is 4%)",
        frequency=_DAILY,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        candidates=(
            Candidate(provider="nyfed", series="effr", column="percentRate"),
            Candidate(
                provider="fred",
                series="EFFR",
                tier=Tier.AGGREGATOR,
                vintages=False,
                note=_NO_ALFRED,
            ),
        ),
        section=_POLICY,
    ),
    Concept(
        id="us.policy_rate.target_upper",
        title="Federal funds target, upper bound",
        definition=(
            "The upper bound of the FOMC's federal funds target range, observed "
            "on each date it changed, as a decimal. Before 2008-12-16 the FOMC "
            "set a single target rather than a range; that target is both "
            "bounds."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.04 is 4%)",
        frequency=ObservationFrequency.IRREGULAR,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        candidates=(
            Candidate(
                provider="fed_board",
                series="target_range",
                column="upper",
                note=(
                    "The Board's open-market page lists each change with its "
                    "effective date; there is no daily forward fill."
                ),
            ),
            Candidate(
                provider="fred",
                series="DFEDTARU",
                transforms=("changes_only",),
                tier=Tier.AGGREGATOR,
                vintages=False,
                note=(
                    "FRED's daily series starts on 2008-12-16, when the range "
                    "began; only the dates it changed are kept, as the Board "
                    "lists them. ALFRED keeps no vintages of it."
                ),
            ),
        ),
        notes=(
            (
                "To read the target in force on a date, align it explicitly with "
                "the asof transform; nothing here fills it forward."
            ),
        ),
        section=_POLICY,
    ),
    Concept(
        id="us.policy_rate.target_lower",
        title="Federal funds target, lower bound",
        definition=(
            "The lower bound of the FOMC's federal funds target range, observed "
            "on each date it changed, as a decimal. Before 2008-12-16 the FOMC "
            "set a single target rather than a range; that target is both "
            "bounds."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.04 is 4%)",
        frequency=ObservationFrequency.IRREGULAR,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        candidates=(
            Candidate(provider="fed_board", series="target_range", column="lower"),
            Candidate(
                provider="fred",
                series="DFEDTARL",
                transforms=("changes_only",),
                tier=Tier.AGGREGATOR,
                vintages=False,
                note=(
                    "FRED's daily series starts on 2008-12-16, when the range "
                    "began. ALFRED keeps no vintages of it."
                ),
            ),
        ),
        section=_POLICY,
    ),
    _yield(
        "us.treasury.nominal_3m",
        "Treasury 3-month yield",
        "The par yield on a three-month Treasury bill read from the Treasury's "
        "daily par yield curve, as a decimal per year.",
        "BC_3MONTH",
        "DGS3MO",
    ),
    _yield(
        "us.treasury.nominal_10y",
        "Treasury 10-year yield",
        "The par yield on a ten-year Treasury note read from the Treasury's "
        "daily par yield curve, as a decimal per year.",
        "BC_10YEAR",
        "DGS10",
    ),
    _yield(
        "us.treasury.real_10y",
        "Treasury 10-year real yield",
        "The ten-year real yield read from the Treasury's daily par real yield "
        "curve (inflation-protected securities), as a decimal per year.",
        "TC_10YEAR",
        "DFII10",
    ),
    Concept(
        id="us.treasury.par_curve",
        title="Treasury par yield curve",
        definition=(
            "The Treasury's daily par yield curve for nominal securities, one "
            "column per tenor from one month to thirty years, as decimals per "
            "year."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.04 is 4%)",
        frequency=_DAILY,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        shape=Shape.TABLE,
        candidates=(
            Candidate(
                provider="treasury",
                series="par_nominal",
                columns=_NOMINAL,
                delivers=ObservationFrequency.IRREGULAR,
                note=_TREASURY_NOTE,
            ),
        ),
        needs_window=True,
        notes=(
            _CURVE_WINDOW,
            (
                "Treasury adopted a monotone convex spline on 2021-12-06; the source "
                "notes the change on the frame."
            ),
        ),
        section=_CURVES,
    ),
    Concept(
        id="us.treasury.par_curve_real",
        title="Treasury par real yield curve",
        definition=(
            "The Treasury's daily par real yield curve for inflation-protected "
            "securities, five to thirty years, as decimals per year."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.02 is 2%)",
        frequency=_DAILY,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        shape=Shape.TABLE,
        candidates=(
            Candidate(
                provider="treasury",
                series="par_real",
                columns=_REAL,
                delivers=ObservationFrequency.IRREGULAR,
                note=_TREASURY_NOTE,
            ),
        ),
        needs_window=True,
        notes=(_CURVE_WINDOW,),
        section=_CURVES,
    ),
    Concept(
        id="us.treasury.gsw_curve",
        title="Gürkaynak-Sack-Wright yield curve",
        definition=(
            "The Federal Reserve Board staff's daily fit of the Treasury yield "
            "curve (Gürkaynak, Sack and Wright): the Svensson parameters, and "
            "the zero-coupon yields, par yields and forward rates they imply, "
            "as the Board publishes them."
        ),
        unit_kind=None,
        unit_text=(
            "decimal per year for yields and forwards; the Svensson betas and "
            "taus keep the Board's own units"
        ),
        frequency=_DAILY,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        shape=Shape.TABLE,
        candidates=(
            Candidate(
                provider="fed_board",
                series="gsw",
                delivers=ObservationFrequency.IRREGULAR,
            ),
        ),
        notes=(
            (
                "Staff estimates, subject to revision. The Svensson beta columns "
                "have no unit kind; the tau columns are in years."
            ),
        ),
        section=_CURVES,
    ),
    Concept(
        id="us.neutral_rate.laubach_williams",
        title="Natural rate of interest, Laubach-Williams",
        definition=(
            "The Laubach-Williams estimate of the real natural rate of interest "
            "(r-star) for the United States, quarterly, as published by the "
            "Federal Reserve Bank of New York, as a decimal."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.01 is 1%)",
        frequency=ObservationFrequency.QUARTERLY,
        seasonal_adjustment=_NA,
        candidates=(Candidate(provider="nyfed", series="lw", column="rstar"),),
        notes=(
            (
                "Each estimate is revised as data arrive; the New York Fed keeps "
                "earlier editions as separate files (`lw:2005q1`), not as vintages."
            ),
        ),
        section=_NEUTRAL,
    ),
    Concept(
        id="us.neutral_rate.hlw",
        title="Natural rate of interest, Holston-Laubach-Williams (United States)",
        definition=(
            "The Holston-Laubach-Williams estimate of the real natural rate of "
            "interest (r-star) for the United States, quarterly, as published "
            "by the Federal Reserve Bank of New York, as a decimal."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.01 is 1%)",
        frequency=ObservationFrequency.QUARTERLY,
        seasonal_adjustment=_NA,
        candidates=(Candidate(provider="nyfed", series="hlw", column="rstar_US"),),
        notes=("Earlier editions are separate files (`hlw:2025Q1`), not vintages.",),
        section=_NEUTRAL,
    ),
    *_GSW_PARAMETERS,
)
