# src/pyeconomics/models/macro/recession_probability.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The yield-curve recession probability: ``macro.recession_probability``.

The New York Fed's probit (Estrella and Mishkin 1998; Estrella and Trubin 2006)
gives the probability that the United States is in recession twelve months
ahead from the term spread this month:

.. math:: P(\text{recession}_{t+12}) = \Phi(\alpha + \beta S_t),

with :math:`S_t` the 10-year Treasury yield less the 3-month bill rate on a
bond-equivalent basis, monthly averages, **in percentage points**, and the
coefficients the New York Fed publishes, :math:`\alpha = -0.5333` and
:math:`\beta = -0.6330` (estimated over 1959 to 2009). Rates are decimals
everywhere else, so the spread is converted with
:func:`~pyeconomics.core.decimal_to_percent`, the one converter ADR-0008 allows.
A bill rate quoted on a discount basis :math:`d` is first put on a
bond-equivalent basis, :math:`365 d / (360 - 91 d)`, as the New York Fed does.
"""

from __future__ import annotations

import math
from typing import Final, Literal

from pydantic import Field

from pyeconomics.core import (
    Binding,
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Probability,
    Rate,
    Reference,
    decimal_to_percent,
    model,
)

__all__ = ["recession_probability"]

#: The New York Fed's published probit coefficients, per percentage point.
INTERCEPT: Final = -0.5333
SLOPE: Final = -0.6330
#: A 91-day bill over a 360-day discount year and a 365-day bond year.
_BILL_DAYS: Final = 91.0
_DISCOUNT_YEAR: Final = 360.0
_BOND_YEAR: Final = 365.0
#: Treasury yields from -5% to 50%: deeper than any negative yield and above the
#: 1981 peak of about 16%.
_YIELD_MIN: Final = -0.05
_YIELD_MAX: Final = 0.5

type BillBasis = Literal["bond_equivalent", "discount"]


class RecessionProbabilityInputs(ModelInputs):
    ten_year_yield: Rate = Field(
        ge=_YIELD_MIN,
        le=_YIELD_MAX,
        description="The 10-year Treasury yield, a monthly average",
    )
    three_month_yield: Rate = Field(
        ge=_YIELD_MIN,
        le=_YIELD_MAX,
        description="The 3-month Treasury bill rate, a monthly average",
    )
    bill_basis: BillBasis = Field(
        "bond_equivalent",
        description=(
            "How the bill rate is quoted: 'bond_equivalent' (an investment yield, "
            "as Treasury's par curve gives it) or 'discount' (as H.15 publishes "
            "secondary-market bills)"
        ),
    )


class RecessionProbabilityOutputs(ModelOutputs):
    probability: Probability = Field(
        ge=0.0,
        le=1.0,
        description="The probability of a recession twelve months ahead",
    )
    spread: Rate = Field(
        ge=-1.0,
        le=1.0,
        description="The 10-year yield less the bond-equivalent bill rate",
    )
    bill_bond_equivalent: Rate = Field(
        ge=-1.0,
        le=1.0,
        description="The bill rate on a bond-equivalent basis",
    )


def bond_equivalent(discount: float) -> float:
    """Return a 91-day bill's bond-equivalent yield from its discount rate."""
    return _BOND_YEAR * discount / (_DISCOUNT_YEAR - _BILL_DAYS * discount)


def _normal_cdf(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


_ESTRELLA_TRUBIN = Reference(
    key="estrella2006",
    citation=(
        "Estrella, A. and Trubin, M. R. (2006). The Yield Curve as a Leading "
        "Indicator: Some Practical Issues. Current Issues in Economics and "
        "Finance, 12(5). Federal Reserve Bank of New York."
    ),
    url="https://www.newyorkfed.org/research/current_issues/ci12-5.html",
    locator=(
        "The probit of a recession twelve months ahead on the spread, and "
        "footnote 4's bond-equivalent conversion of the bill rate"
    ),
)
_ESTRELLA_MISHKIN = Reference(
    key="estrella1998",
    citation=(
        "Estrella, A. and Mishkin, F. S. (1998). Predicting U.S. Recessions: "
        "Financial Variables as Leading Indicators. Review of Economics and "
        "Statistics, 80(1), 45-61."
    ),
    doi="10.1162/003465398557320",
    locator="The term spread as the leading probit predictor of recessions",
)
_NYFED = Reference(
    key="nyfed_yield_curve",
    citation=(
        "Federal Reserve Bank of New York. The Yield Curve as a Leading "
        "Indicator: probability of US recession predicted by the Treasury spread."
    ),
    url="https://www.newyorkfed.org/research/capital_markets/ycfaq",
    locator=(
        "The data file allmonth.xls and its chart notes: alpha -0.5333 and beta "
        "-0.6330, estimated over 1959 to 2009"
    ),
)


@model(
    id="macro.recession_probability",
    version=1,
    title="Yield-curve recession probability",
    summary=(
        "The New York Fed's probit of a US recession twelve months ahead from the "
        "spread of the 10-year Treasury yield over the 3-month bill."
    ),
    formula=(
        r"P = \Phi(-0.5333 - 0.6330\,S), \quad S = 100\,(y_{10} - y_{3m})",
        r"y_{3m} = \frac{365\,d}{360 - 91\,d} \ \text{(from a discount rate } d)",
    ),
    assumptions=(
        (
            "The coefficients are the New York Fed's, fixed; they apply to the "
            "spread in percentage points, so the decimal spread is converted with "
            "decimal_to_percent."
        ),
        (
            "Both yields are monthly averages. The New York Fed uses the 10-year "
            "constant-maturity yield and the 3-month secondary-market bill on a "
            "bond-equivalent basis; Treasury's par curve gives the 3-month rate as "
            "an investment yield already."
        ),
        (
            "Profile: default binds the monthly averages of Treasury's 10-year and "
            "3-month par yields (the last complete month by the date)."
        ),
    ),
    limitations=(
        (
            "A probability from one spread, not a forecast of the economy: the "
            "model was fitted to 1959-2009 and says nothing about why a curve "
            "inverts."
        ),
        (
            "The default profile's 3-month rate is Treasury's constant-maturity "
            "yield, close to but not the New York Fed's converted secondary-market "
            "rate; pass the H.15 discount rate with bill_basis='discount' to "
            "reproduce its file."
        ),
    ),
    references=(_ESTRELLA_TRUBIN, _ESTRELLA_MISHKIN, _NYFED),
    evidence=Evidence.PRACTITIONER,
    cost=CostClass.INSTANT,
    tags=("recession", "yield curve", "term spread", "probit", "leading indicator"),
    invariants=(
        Invariant(
            id="probability_falls_as_spread_rises",
            statement=(
                "With the bill rate fixed, a higher 10-year yield never raises the "
                "probability."
            ),
        ),
        Invariant(
            id="probability_is_one_half_at_the_threshold",
            statement=(
                "At a spread of 0.5333 / -0.6330 percentage points (about -84 basis "
                "points) the probability is one half."
            ),
        ),
    ),
    examples=(
        Example(
            name="inverted_curve",
            inputs={"ten_year_yield": 0.0357, "three_month_yield": 0.0528},
            note="An inverted curve, as in May 2023.",
        ),
        Example(
            name="discount_basis_bill",
            inputs={
                "ten_year_yield": 0.0499,
                "three_month_yield": 0.0394,
                "bill_basis": "discount",
            },
        ),
    ),
    bindings=(
        Binding(
            "ten_year_yield",
            "us.treasury.nominal_10y",
            transform="convert(to=monthly,method=mean)",
        ),
        Binding(
            "three_month_yield",
            "us.treasury.nominal_3m",
            transform="convert(to=monthly,method=mean)",
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def recession_probability(
    inputs: RecessionProbabilityInputs,
) -> RecessionProbabilityOutputs:
    """Return the probability of a recession twelve months ahead."""
    bill = inputs.three_month_yield
    if inputs.bill_basis == "discount":
        bill = bond_equivalent(bill)
    spread = inputs.ten_year_yield - bill
    probability = _normal_cdf(INTERCEPT + SLOPE * decimal_to_percent(spread))
    return RecessionProbabilityOutputs(
        probability=probability, spread=spread, bill_bond_equivalent=bill
    )
