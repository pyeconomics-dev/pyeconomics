# src/pyeconomics/data/catalog/factors.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Factor and portfolio return sets from the Ken French Data Library.

The ids follow the dataset-family grammar ``<family>.<set>.<economy>.<frequency>``:
``factors.ff5.us.monthly`` is the five-factor monthly set for the United States.
Returns are decimals per period (0.01 is 1%); the library converts the source's
percent. The source is library-only and fetched at run time, never bundled.

Each factor is also one series, monthly and daily, so a model can bind it to an
input field: ``factors.ff3_smb.us.monthly`` is the size factor of the
three-factor file, and ``factors.ff3_market.us.daily`` its daily market excess
return. The
series name their file, because the files differ: the five-factor file's SMB
averages three sorts and differs from the three-factor file's in almost every
month, and its market excess return differs by up to a few hundredths of a
percentage point in some. HML and the risk-free return are the same in both, and
are read from the three-factor file.
"""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import Candidate, Concept, Shape
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS", "FACTOR_SERIES", "FACTOR_SETS", "PORTFOLIO_SETS"]

_SECTION: Final = "Factors and portfolios"
_FREQUENCIES: Final = (
    ("monthly", ObservationFrequency.MONTHLY),
    ("daily", ObservationFrequency.DAILY),
)
#: The factor sets: (id part, source id part, title, what its columns are).
FACTOR_SETS: Final = (
    (
        "ff3",
        "ff3",
        "Fama-French three factors",
        (
            "the market excess return (Mkt-RF), size (SMB) and value (HML) factors "
            "and the risk-free return (RF)"
        ),
    ),
    (
        "ff5",
        "ff5",
        "Fama-French five factors",
        (
            "the market excess return (Mkt-RF), size (SMB), value (HML), "
            "profitability (RMW) and investment (CMA) factors and the risk-free "
            "return (RF)"
        ),
    ),
    (
        "momentum",
        "momentum",
        "Momentum factor",
        "the momentum factor (Mom): winners minus losers",
    ),
)
#: The portfolio sets, as (id part, source id part, title, what they are).
PORTFOLIO_SETS: Final = (
    (
        "industry12",
        "industry12",
        "Twelve industry portfolios",
        "value-weighted returns of twelve US industry portfolios",
    ),
    (
        "size_bm25",
        "size_bm25",
        "Twenty-five size and book-to-market portfolios",
        "value-weighted returns of the 5 by 5 sort on size and book-to-market",
    ),
)
#: The factor series, at each frequency: (id part, source set, source column,
#: title, what).
FACTOR_SERIES: Final = (
    (
        "ff3_market",
        "ff3",
        "Mkt-RF",
        "Market excess return, three-factor file",
        (
            "the value-weighted return of all CRSP firms incorporated in the US and "
            "listed on the NYSE, AMEX or NASDAQ, less the one-month Treasury bill rate"
        ),
    ),
    (
        "ff3_smb",
        "ff3",
        "SMB",
        "Size factor (SMB), three-factor file",
        (
            "small minus big: the average return of three small portfolios less that "
            "of three big ones, from the six sorts on size and book-to-market"
        ),
    ),
    (
        "ff3_hml",
        "ff3",
        "HML",
        "Value factor (HML)",
        (
            "high minus low: the average return of the two value portfolios less that "
            "of the two growth portfolios, from the six sorts on size and "
            "book-to-market"
        ),
    ),
    (
        "risk_free",
        "ff3",
        "RF",
        "Risk-free return",
        "the one-month Treasury bill return the factors are measured over",
    ),
    (
        "ff5_market",
        "ff5",
        "Mkt-RF",
        "Market excess return, five-factor file",
        (
            "the market excess return as the five-factor file publishes it, which "
            "differs from the three-factor file's by up to a few hundredths of a "
            "percentage point in some months"
        ),
    ),
    (
        "ff5_smb",
        "ff5",
        "SMB",
        "Size factor (SMB), five-factor file",
        (
            "small minus big: the average of the size factors of the sorts on "
            "book-to-market, operating profitability and investment"
        ),
    ),
    (
        "ff5_rmw",
        "ff5",
        "RMW",
        "Profitability factor (RMW)",
        (
            "robust minus weak: the average return of the two robust operating "
            "profitability portfolios less that of the two weak ones"
        ),
    ),
    (
        "ff5_cma",
        "ff5",
        "CMA",
        "Investment factor (CMA)",
        (
            "conservative minus aggressive: the average return of the two "
            "conservative investment portfolios less that of the two aggressive ones"
        ),
    ),
    (
        "mom",
        "momentum",
        "Mom",
        "Momentum factor (Mom)",
        (
            "winners minus losers: the average return of the two high prior-return "
            "portfolios less that of the two low ones, prior returns over months "
            "t-12 to t-2"
        ),
    ),
)
_NOTE: Final = (
    "Copyright Eugene Fama and Kenneth French; fetched at run time, never stored "
    "in the repository."
)


#: What a return is per, at each frequency.
_PERIOD: Final = {"monthly": "month", "daily": "trading day"}


def _factor_series() -> tuple[Concept, ...]:
    return tuple(
        Concept(
            id=f"factors.{part}.us.{label}",
            title=f"{title}, {label}",
            definition=(
                f"{title} for the United States, {label}: {what}. Returns are "
                f"decimals per {_PERIOD[label]}."
            ),
            unit_kind=UnitKind.RETURN,
            unit_text=f"decimal return per {_PERIOD[label]} (0.01 is 1%)",
            frequency=frequency,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            candidates=(
                Candidate(
                    provider="ken_french",
                    series=f"{source}:{label}",
                    column=column,
                    note=_NOTE,
                ),
            ),
            section=_SECTION,
        )
        for label, frequency in _FREQUENCIES
        for part, source, column, title, what in FACTOR_SERIES
    )


def _concepts() -> tuple[Concept, ...]:
    built: list[Concept] = []
    for family, sets in (("factors", FACTOR_SETS), ("portfolios", PORTFOLIO_SETS)):
        for part, source, title, what in sets:
            for label, frequency in _FREQUENCIES:
                built.append(
                    Concept(
                        id=f"{family}.{part}.us.{label}",
                        title=f"{title}, {label}",
                        definition=(
                            f"{title} for the United States at {label} frequency: "
                            f"{what}. Returns are decimals per period."
                        ),
                        unit_kind=UnitKind.RETURN,
                        unit_text="decimal return per period (0.01 is 1%)",
                        frequency=frequency,
                        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
                        shape=Shape.TABLE,
                        candidates=(
                            Candidate(
                                provider="ken_french",
                                series=f"{source}:{label}",
                                note=_NOTE,
                            ),
                        ),
                        section=_SECTION,
                    )
                )
    return (*built, *_factor_series())


CONCEPTS: Final = _concepts()
