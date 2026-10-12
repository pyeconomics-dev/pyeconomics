# src/pyeconomics/models/fixed_income/convexity.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Convexity: ``fixed_income.convexity``.

Three calculations on a fixed-coupon bond, discriminated on ``calculation``:

- ``analytical``: the convexity ``P'' / P`` from the yield to maturity;
- ``effective``: the convexity from repricing off a spot curve shifted down and
  up in parallel (a central second difference);
- ``price_change``: the duration-and-convexity estimate of the relative price
  change for a change in yield, beside the change from repricing and their
  difference.

Bond terms and cash flows are those of ``fixed_income.bond_pricing``; yields and
spot rates compound at the coupon frequency, under street convention.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    ModelOutputs,
    Money,
    Rate,
    Ratio,
    Reference,
    Return,
    Years,
    model,
)
from pyeconomics.models.fixed_income._bonds import (
    MONEY_OUT,
    YIELD_MAX,
    YIELD_MIN,
    BondTerms,
    CurveTerms,
    bond_flows,
    bounded,
    curve_price,
    macaulay_duration,
    price,
)
from pyeconomics.models.fixed_income._bonds import (
    convexity as bond_convexity,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["convexity"]

#: The largest convexity an output holds, in years squared. A 100-year
#: zero-coupon bond at -10% compounded annually has 100 x 101 / 0.81, about
#: 12,500.
_CONVEXITY_MAX: Final = 1e5
#: The largest yield change ``price_change`` takes: 200 basis points.
_CHANGE_MAX: Final = 0.02
#: Bounds of the parts of a relative price change. A modified duration below
#: 115 years times 0.02 is below 2.3; half a convexity below 1e5 times 0.02
#: squared is below 20.
_EFFECT_MAX: Final = 1e3
_DURATION_MAX: Final = 200.0


def _yield() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=YIELD_MIN,
        le=YIELD_MAX,
        description="Yield to maturity per year, compounded at the coupon frequency",
    )


def _effect(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-_EFFECT_MAX, le=_EFFECT_MAX, description=description)


def _full() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=MONEY_OUT, description="Full (dirty) price at settlement")


# --- inputs ------------------------------------------------------------------


class AnalyticalInputs(BondTerms):
    """A bond and its yield to maturity."""

    calculation: Literal["analytical"] = Field(
        "analytical", description="Convexity from the yield"
    )
    yield_to_maturity: Rate = _yield()


class EffectiveInputs(CurveTerms):
    """A bond and a spot curve."""

    calculation: Literal["effective"] = Field(
        "effective", description="Effective convexity off a spot curve"
    )


class PriceChangeInputs(BondTerms):
    """A bond, its yield to maturity and a change in that yield."""

    calculation: Literal["price_change"] = Field(
        "price_change", description="Duration and convexity price-change estimate"
    )
    yield_to_maturity: Rate = _yield()
    yield_change: Rate = Field(
        ge=-_CHANGE_MAX,
        le=_CHANGE_MAX,
        description="Change in the yield, in decimals (0.01 is 100 basis points)",
    )


ConvexityInputs = Annotated[
    AnalyticalInputs | EffectiveInputs | PriceChangeInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class AnalyticalOutputs(ModelOutputs):
    calculation: Literal["analytical"] = Field(
        "analytical", description="Convexity from the yield"
    )
    convexity: Ratio = Field(
        ge=0.0,
        le=_CONVEXITY_MAX,
        description=(
            "Second derivative of the price in the yield, over the price "
            "(years squared)"
        ),
    )
    full_price: Money = _full()


class EffectiveOutputs(ModelOutputs):
    calculation: Literal["effective"] = Field(
        "effective", description="Effective convexity off a spot curve"
    )
    effective_convexity: Ratio = Field(
        ge=-_CONVEXITY_MAX,
        le=_CONVEXITY_MAX,
        description="(P_down + P_up - 2 P) / (P bump^2), in years squared",
    )
    full_price: Money = _full()


class PriceChangeOutputs(ModelOutputs):
    calculation: Literal["price_change"] = Field(
        "price_change", description="Duration and convexity price-change estimate"
    )
    modified_duration: Years = Field(
        ge=0.0, le=_DURATION_MAX, description="Modified duration at the yield"
    )
    convexity: Ratio = Field(
        ge=0.0, le=_CONVEXITY_MAX, description="Convexity at the yield (years squared)"
    )
    duration_effect: Ratio = _effect("-D_mod x the yield change")
    convexity_effect: Ratio = _effect("Half the convexity x the yield change squared")
    estimated_change: Ratio = _effect(
        "Relative price change estimated by duration and convexity"
    )
    actual_change: Return = Field(
        ge=-1.0, le=100.0, description="Relative change in the full price on repricing"
    )
    approximation_error: Ratio = _effect("Actual change less the estimate")


ConvexityOutputs = Annotated[
    AnalyticalOutputs | EffectiveOutputs | PriceChangeOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _analytical(inputs: AnalyticalInputs) -> AnalyticalOutputs:
    flows = bond_flows(inputs)
    y = inputs.yield_to_maturity
    full = bounded(price(flows, y), 0.0, MONEY_OUT, "full price")
    return AnalyticalOutputs(convexity=bond_convexity(flows, y), full_price=full)


def _effective(inputs: EffectiveInputs) -> EffectiveOutputs:
    flows = bond_flows(inputs)
    tenors, rates, h = inputs.curve_tenors, inputs.curve_rates, inputs.bump
    base = bounded(curve_price(flows, tenors, rates), 0.0, MONEY_OUT, "full price")
    down = curve_price(flows, tenors, rates, lambda _: -h)
    up = curve_price(flows, tenors, rates, lambda _: h)
    value = (down + up - 2 * base) / (base * h * h)
    return EffectiveOutputs(
        effective_convexity=bounded(
            value, -_CONVEXITY_MAX, _CONVEXITY_MAX, "effective convexity"
        ),
        full_price=base,
    )


def _price_change(inputs: PriceChangeInputs) -> PriceChangeOutputs:
    flows = bond_flows(inputs)
    y, change = inputs.yield_to_maturity, inputs.yield_change
    full, macaulay = macaulay_duration(flows, y)
    bounded(full, 0.0, MONEY_OUT, "full price")
    modified = macaulay / (1 + y / flows.periods_per_year)
    curvature = bond_convexity(flows, y)
    duration_effect = -modified * change
    convexity_effect = 0.5 * curvature * change * change
    estimated = duration_effect + convexity_effect
    actual = price(flows, y + change) / full - 1.0
    return PriceChangeOutputs(
        modified_duration=modified,
        convexity=curvature,
        duration_effect=duration_effect,
        convexity_effect=convexity_effect,
        estimated_change=estimated,
        actual_change=actual,
        approximation_error=actual - estimated,
    )


# --- the model ---------------------------------------------------------------

_FABOZZI = Reference(
    key="fabozzi2005",
    citation=(
        "Fabozzi, F. J. (2005). Fixed Income Mathematics: Analytical and "
        "Statistical Techniques, 4th ed. McGraw-Hill."
    ),
    url="https://openlibrary.org/isbn/9780071460736",
    isbn="9780071460736",
    locator=(
        "Chapter 13 (combining duration and convexity to measure price volatility)"
    ),
)
_QUANTLIB = Reference(
    key="quantlib",
    citation="QuantLib (2026). BondFunctions. QuantLib 1.43 reference.",
    url="https://www.quantlib.org/reference/struct_quant_lib_1_1_bond_functions.html",
    locator="BondFunctions::convexity",
)
_BOND = {
    "settlement": "2026-01-15",
    "maturity": "2036-01-15",
    "coupon_rate": 0.045,
}


@model(
    id="fixed_income.convexity",
    version=2,
    title="Bond convexity",
    summary=(
        "Convexity of a fixed-coupon bond from its yield, effective convexity "
        "off a spot curve, and the duration-and-convexity price-change estimate."
    ),
    formula=(
        (
            r"C = \frac{1}{P}\frac{\partial^2 P}{\partial y^2} = "
            r"\frac{1}{P f^2 (1 + y/f)^2}"
            r"\sum_j t_j (t_j + 1) \frac{CF_j}{(1 + y/f)^{t_j}}"
        ),
        r"C_{eff} = \frac{P(z - h) + P(z + h) - 2 P(z)}{P(z) h^2}",
        r"\frac{\Delta P}{P} \approx -D_{mod}\,\Delta y + \tfrac{1}{2} C\,(\Delta y)^2",
    ),
    assumptions=(
        (
            "Times t_j are counted in coupon periods from settlement, as in "
            "fixed_income.bond_pricing; the yield compounds at the coupon "
            "frequency, under street convention."
        ),
        (
            "The spot curve is linear in its rates between nodes and flat beyond "
            "them, and is shifted in parallel."
        ),
        "The bond has no embedded option, so its cash flows do not move with rates.",
    ),
    limitations=(
        (
            "Effective convexity is a second difference: its rounding error grows "
            "as the bump shrinks, and its truncation error as it grows."
        ),
        "Yield changes are limited to 200 basis points either way.",
    ),
    references=(_FABOZZI, _QUANTLIB),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    tags=("bond", "convexity", "interest rate risk"),
    invariants=(
        Invariant(
            id="convexity_positive_for_option_free_bonds",
            statement="An option-free bond's convexity is positive.",
        ),
        Invariant(
            id="approximation_error_is_third_order",
            statement=(
                "The error of the duration-and-convexity estimate shrinks with the "
                "cube of the yield change."
            ),
        ),
        Invariant(
            id="zero_coupon_closed_form",
            statement=(
                "A zero-coupon bond n periods from maturity has convexity "
                "n (n + 1) / (f^2 (1 + y/f)^2)."
            ),
        ),
    ),
    examples=(
        Example(
            name="ten_year_note",
            inputs={"calculation": "analytical", **_BOND, "yield_to_maturity": 0.045},
        ),
        Example(
            name="effective_off_a_curve",
            inputs={
                "calculation": "effective",
                **_BOND,
                "curve_tenors": [0.5, 1, 2, 5, 10, 30],
                "curve_rates": [0.043, 0.042, 0.041, 0.042, 0.045, 0.048],
                "bump": 0.001,
            },
        ),
        Example(
            name="a_hundred_basis_points",
            inputs={
                "calculation": "price_change",
                **_BOND,
                "yield_to_maturity": 0.045,
                "yield_change": 0.01,
            },
        ),
    ),
    changelog=(
        ChangelogEntry(version=1, note="First version."),
        ChangelogEntry(
            version=2,
            note="Correct US 30/360 long-stub accrual and discount times (#89).",
        ),
    ),
)
def convexity(inputs: ConvexityInputs) -> ConvexityOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[BondTerms], Callable[[Any], ConvexityOutputs]]] = {
    AnalyticalInputs: _analytical,
    EffectiveInputs: _effective,
    PriceChangeInputs: _price_change,
}
