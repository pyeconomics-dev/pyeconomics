# src/pyeconomics/data/catalog/factors.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Factor and portfolio return sets from the Ken French Data Library.

The ids follow the dataset-family grammar ``<family>.<set>.<economy>.<frequency>``:
``factors.ff5.us.monthly`` is the five-factor monthly set for the United States.
Returns are decimals per period (0.01 is 1%); the library converts the source's
percent. The source is library-only and fetched at run time, never bundled.
"""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import Candidate, Concept, Shape
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS", "FACTOR_SETS", "PORTFOLIO_SETS"]

_SECTION: Final = "Factors and portfolios"
_FREQUENCIES: Final = (
    ("monthly", ObservationFrequency.MONTHLY),
    ("daily", ObservationFrequency.BUSINESS_DAILY),
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
                                note=(
                                    "Copyright Eugene Fama and Kenneth French; "
                                    "fetched at run time, never stored in the "
                                    "repository."
                                ),
                            ),
                        ),
                        section=_SECTION,
                    )
                )
    return tuple(built)


CONCEPTS: Final = _concepts()
