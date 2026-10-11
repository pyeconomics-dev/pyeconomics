# src/pyeconomics/models/derivatives/interest_rate_swap.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Fixed-for-floating swaps on one curve: ``derivatives.interest_rate_swap``.

A swap exchanges fixed coupons :math:`c\,\alpha_i N` on each payment date for
floating ones. On a single curve the floating leg is worth the notional at the
start less the notional at the end, :math:`N (d_0 - d_n)`, and the fixed leg
:math:`c N A` with the annuity factor :math:`A = \sum_i \alpha_i d_i`. The par
swap rate, which makes them equal, is :math:`(d_0 - d_n) / A`; it is
:math:`(1 - d_n) / A` for a swap that starts now (:func:`pyeconomics.core.par_rate`).

Three calculations, discriminated on ``calculation``, differ in how they give
the schedule and the discount factors:

- ``discount_factors``: accrual fractions and the discount factor at each
  payment date;
- ``zero_curve``: accrual fractions and a zero curve; payment ``i`` falls at
  the start plus the first ``i`` accruals;
- ``dated``: payment dates, accrued on a day count from the start date, and a
  zero curve read at ACT/365 (Fixed) years from the valuation date.

The payer pays fixed and receives floating; the receiver the reverse. The
outputs are the formulas' values for the inputs given, not trading advice.
"""

from __future__ import annotations

import math
from itertools import pairwise
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    DEFAULT_DATE_BOUNDS,
    ChangelogEntry,
    Compounding,
    CostClass,
    DateValue,
    DayCount,
    DomainError,
    Evidence,
    Example,
    Frequency,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Rate,
    Ratio,
    Reference,
    Years,
    curve_discount_factors,
    model,
    year_fraction,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.derivatives._options import MONEY_OUT, bounded

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable, Sequence

__all__ = ["interest_rate_swap"]

#: The most payments a swap has: 50 years of monthly payments.
_PAYMENTS_MAX: Final = 600
#: The most nodes a zero curve has.
_NODES_MAX: Final = 200
#: The largest notional.
_NOTIONAL_MAX: Final = 1e12
#: Fixed rates and zero rates.
_RATE_MIN: Final = -0.1
_RATE_MAX: Final = 1.0
#: The par swap rate's bounds, ADR-0008's for a rate.
_PAR_MIN: Final = -0.99
_PAR_MAX: Final = 10.0
#: Discount factors an input gives: a negative rate lifts them above one.
_FACTOR_MAX: Final = 10.0
#: The annuity factor's bound: 600 accruals of a year at a factor of 10 is 6,000.
_ANNUITY_MAX: Final = 1e6

_FREQUENCIES: Final[dict[str, Frequency]] = {
    "annual": Frequency.ANNUAL,
    "semiannual": Frequency.SEMIANNUAL,
    "quarterly": Frequency.QUARTERLY,
    "monthly": Frequency.MONTHLY,
}
_DAY_COUNTS: Final[dict[str, DayCount]] = {
    "act_360": DayCount.ACT_360,
    "act_365_fixed": DayCount.ACT_365_FIXED,
    "act_act_isda": DayCount.ACT_ACT_ISDA,
    "thirty_360_us": DayCount.THIRTY_360_US,
    "thirty_e_360": DayCount.THIRTY_E_360,
}

type FrequencyName = Literal["annual", "semiannual", "quarterly", "monthly"]
type SwapDayCount = Literal[
    "act_360", "act_365_fixed", "act_act_isda", "thirty_360_us", "thirty_e_360"
]

_Accruals = Annotated[tuple[Annotated[Years, Field(gt=0.0, le=1.0)], ...], ARRAY_INPUT]
_Factors = Annotated[
    tuple[Annotated[Ratio, Field(gt=0.0, le=_FACTOR_MAX)], ...], ARRAY_INPUT
]
_Tenors = Annotated[tuple[Annotated[Years, Field(gt=0.0, le=100.0)], ...], ARRAY_INPUT]
_Rates = Annotated[
    tuple[Annotated[Rate, Field(ge=_RATE_MIN, le=_RATE_MAX)], ...], ARRAY_INPUT
]
_Dates = Annotated[
    tuple[
        Annotated[
            DateValue,
            Field(ge=DEFAULT_DATE_BOUNDS.lower, le=DEFAULT_DATE_BOUNDS.upper),
        ],
        ...,
    ],
    ARRAY_INPUT,
]


def _date(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=DEFAULT_DATE_BOUNDS.lower,
        le=DEFAULT_DATE_BOUNDS.upper,
        description=description,
    )


def _accruals() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        min_length=1,
        max_length=_PAYMENTS_MAX,
        description="Accrual fraction of each fixed period, in years",
    )


# --- inputs ------------------------------------------------------------------


class _Swap(ModelInputs):
    notional: Money = Field(
        1.0, ge=0.0, le=_NOTIONAL_MAX, description="Notional principal"
    )
    fixed_rate: Rate = Field(
        ge=_RATE_MIN, le=_RATE_MAX, description="Fixed rate per year of the fixed leg"
    )


class _Curve(ModelInputs):
    curve_tenors: _Tenors = Field(
        min_length=1,
        max_length=_NODES_MAX,
        description="Tenors of the zero curve's nodes in years, increasing",
    )
    curve_rates: _Rates = Field(
        min_length=1,
        max_length=_NODES_MAX,
        description="Zero rate at each node: linear between nodes, flat outside",
    )
    compounding: Literal["simple", "periodic", "continuous"] = Field(
        "continuous", description="How the zero rates compound"
    )
    frequency: FrequencyName = Field(
        "annual", description="Compounding frequency of periodic zero rates"
    )

    @model_validator(mode="after")
    def _one_rate_per_tenor(self) -> Self:
        if len(self.curve_tenors) != len(self.curve_rates):
            msg = (
                f"the curve has {len(self.curve_tenors)} tenors and "
                f"{len(self.curve_rates)} rates; give one rate per tenor"
            )
            raise ValueError(msg)
        if any(b <= a for a, b in pairwise(self.curve_tenors)):
            msg = "the curve's tenors must be strictly increasing"
            raise ValueError(msg)
        return self

    def factors(self, times: Sequence[float]) -> list[float]:
        """Return the curve's discount factor at each time, in years."""
        compounding = Compounding(self.compounding)
        frequency = (
            _FREQUENCIES[self.frequency]
            if compounding is Compounding.PERIODIC
            else None
        )
        return curve_discount_factors(
            self.curve_tenors, self.curve_rates, times, compounding, frequency
        )


class DiscountFactorInputs(_Swap):
    """A schedule of accrual fractions and the discount factor at each payment."""

    calculation: Literal["discount_factors"] = Field(
        "discount_factors", description="Swap value from discount factors"
    )
    accruals: _Accruals = _accruals()
    discount_factors: _Factors = Field(
        min_length=1,
        max_length=_PAYMENTS_MAX,
        description="Discount factor at each payment date",
    )
    start_discount_factor: Ratio = Field(
        1.0,
        gt=0.0,
        le=_FACTOR_MAX,
        description="Discount factor at the start date: 1 for a swap starting now",
    )

    @model_validator(mode="after")
    def _one_factor_per_payment(self) -> Self:
        if len(self.accruals) != len(self.discount_factors):
            msg = (
                f"the schedule has {len(self.accruals)} accruals and "
                f"{len(self.discount_factors)} discount factors; give one of each "
                "per payment"
            )
            raise ValueError(msg)
        return self


class ZeroCurveInputs(_Swap, _Curve):
    """A schedule of accrual fractions and a zero curve."""

    calculation: Literal["zero_curve"] = Field(
        "zero_curve", description="Swap value from a zero curve"
    )
    accruals: _Accruals = _accruals()
    start_years: Years = Field(
        0.0, ge=0.0, le=100.0, description="Years until the swap starts: 0 for now"
    )


class DatedInputs(_Swap, _Curve):
    """Payment dates on a day count, and a zero curve."""

    calculation: Literal["dated"] = Field(
        "dated", description="Swap value from payment dates and a zero curve"
    )
    valuation_date: DateValue = _date("Date the swap is valued on")
    start_date: DateValue = _date("Date the first period starts accruing")
    payment_dates: _Dates = Field(
        min_length=1,
        max_length=_PAYMENTS_MAX,
        description="Fixed payment dates, increasing, the last at maturity",
    )
    day_count: SwapDayCount = Field(
        "thirty_360_us", description="Day count of the fixed leg's accruals"
    )

    @model_validator(mode="after")
    def _dates_in_order(self) -> Self:
        if self.start_date < self.valuation_date:
            msg = (
                f"the start date {self.start_date} is before the valuation date "
                f"{self.valuation_date}; value a swap from its start or later"
            )
            raise ValueError(msg)
        dates = (self.start_date, *self.payment_dates)
        if any(b <= a for a, b in pairwise(dates)):
            msg = "the payment dates must be after the start date and increasing"
            raise ValueError(msg)
        return self


InterestRateSwapInputs = Annotated[
    DiscountFactorInputs | ZeroCurveInputs | DatedInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


def _money(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-MONEY_OUT, le=MONEY_OUT, description=description)


class _SwapOutputs(ModelOutputs):
    annuity_factor: Years = Field(
        ge=0.0,
        le=_ANNUITY_MAX,
        description="Sum of accrual fraction times discount factor over payments",
    )
    par_swap_rate: Rate = Field(
        ge=_PAR_MIN,
        le=_PAR_MAX,
        description="Fixed rate at which the swap is worth zero",
    )
    fixed_leg_value: Money = _money("Value of the fixed leg: c N A")
    floating_leg_value: Money = _money("Value of the floating leg: N (d_0 - d_n)")
    payer_value: Money = _money("Value to the fixed payer: floating less fixed")
    receiver_value: Money = _money("Value to the fixed receiver: fixed less floating")


class DiscountFactorOutputs(_SwapOutputs):
    calculation: Literal["discount_factors"] = Field(
        "discount_factors", description="Swap value from discount factors"
    )


class ZeroCurveOutputs(_SwapOutputs):
    calculation: Literal["zero_curve"] = Field(
        "zero_curve", description="Swap value from a zero curve"
    )


class DatedOutputs(_SwapOutputs):
    calculation: Literal["dated"] = Field(
        "dated", description="Swap value from payment dates and a zero curve"
    )


InterestRateSwapOutputs = Annotated[
    DiscountFactorOutputs | ZeroCurveOutputs | DatedOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _values(
    inputs: _Swap,
    accruals: Sequence[float],
    factors: Sequence[float],
    start_factor: float,
) -> dict[str, float]:
    """Return the output fields of a swap with these accruals and factors."""
    annuity = bounded(
        math.fsum(a * d for a, d in zip(accruals, factors, strict=True)),
        0.0,
        _ANNUITY_MAX,
        "annuity factor",
    )
    if annuity == 0:
        msg = (
            "every discount factor underflows to zero, so the annuity is zero and "
            "the swap has no par rate"
        )
        raise DomainError(msg)
    floating = start_factor - factors[-1]
    par = bounded(floating / annuity, _PAR_MIN, _PAR_MAX, "par swap rate")
    fixed_value = bounded(
        inputs.notional * inputs.fixed_rate * annuity,
        -MONEY_OUT,
        MONEY_OUT,
        "fixed leg's value",
    )
    floating_value = bounded(
        inputs.notional * floating, -MONEY_OUT, MONEY_OUT, "floating leg's value"
    )
    payer = bounded(
        floating_value - fixed_value, -MONEY_OUT, MONEY_OUT, "payer's value"
    )
    return {
        "annuity_factor": annuity,
        "par_swap_rate": par,
        "fixed_leg_value": fixed_value,
        "floating_leg_value": floating_value,
        "payer_value": payer,
        "receiver_value": -payer,
    }


def _from_discount_factors(inputs: DiscountFactorInputs) -> DiscountFactorOutputs:
    return DiscountFactorOutputs.model_validate(
        _values(
            inputs,
            inputs.accruals,
            inputs.discount_factors,
            inputs.start_discount_factor,
        )
    )


def _from_zero_curve(inputs: ZeroCurveInputs) -> ZeroCurveOutputs:
    times = [inputs.start_years]
    for accrual in inputs.accruals:
        times.append(times[-1] + accrual)
    start, *factors = inputs.factors(times)
    return ZeroCurveOutputs.model_validate(
        _values(inputs, inputs.accruals, factors, start)
    )


def _years_from(valuation: dt.date, day: dt.date) -> float:
    return (day - valuation).days / 365.0


def _from_dates(inputs: DatedInputs) -> DatedOutputs:
    day_count = _DAY_COUNTS[inputs.day_count]
    dates = (inputs.start_date, *inputs.payment_dates)
    accruals = [year_fraction(a, b, day_count) for a, b in pairwise(dates)]
    times = [_years_from(inputs.valuation_date, day) for day in dates]
    start, *factors = inputs.factors(times)
    return DatedOutputs.model_validate(_values(inputs, accruals, factors, start))


# --- the model ---------------------------------------------------------------

_HULL = Reference(
    key="hull2018",
    citation=(
        "Hull, J. C. (2018). Options, Futures, and Other Derivatives, 10th ed. Pearson."
    ),
    url="https://openlibrary.org/isbn/9780134472089",
    isbn="9780134472089",
    locator=(
        "Chapters 4 and 7 (par yields; interest rate swaps and their valuation "
        "in terms of bonds)"
    ),
)
_ISDA = Reference(
    key="isda2006",
    citation=(
        "International Swaps and Derivatives Association (2006). 2006 ISDA "
        "Definitions. ISDA."
    ),
    url="https://www.isda.org/a/smMDE/Blackline-2000-v-2006-ISDA-Definitions.pdf",
    locator="Section 4.16, Day Count Fraction",
)


@model(
    id="derivatives.interest_rate_swap",
    version=1,
    title="Interest rate swap",
    summary=(
        "Value to the fixed payer and receiver, par swap rate and annuity factor "
        "of a fixed-for-floating swap, from discount factors or a zero curve."
    ),
    formula=(
        r"A = \sum_{i=1}^{n} \alpha_i d_i",
        r"V_{float} = N (d_0 - d_n), \quad V_{fixed} = c N A",
        r"s_{par} = \frac{d_0 - d_n}{A}",
        r"V_{payer} = V_{float} - V_{fixed} = N A (s_{par} - c) = -V_{receiver}",
    ),
    assumptions=(
        (
            "One curve both projects the floating rates and discounts every cash "
            "flow, and the floating leg pays the rate for its own accrual period "
            "with no spread, so it is worth the notional at the start less the "
            "notional at the end."
        ),
        (
            "The swap starts on or after the valuation date: no floating coupon "
            "has been fixed."
        ),
        (
            "Zero rates are interpolated linearly between the curve's nodes and "
            "held flat outside them; in the dated calculation they are read at "
            "ACT/365 (Fixed) years from the valuation date."
        ),
    ),
    limitations=(
        (
            "Results are the formulas' outputs for the inputs given, not a "
            "valuation of a traded swap or trading advice."
        ),
        (
            "Separate projection and discounting curves, a floating spread, "
            "business-day adjustment and seasoned swaps with a fixed coupon "
            "outstanding are out of scope."
        ),
        (
            "A par rate outside [-0.99, 10], an annuity factor of zero (every "
            "discount factor underflowing) or above 1e6, a leg "
            "worth more than 1e15, or a simple-interest curve with no positive "
            "growth, raises DomainError."
        ),
    ),
    references=(_HULL, _ISDA),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("swaps", "interest rate swap", "par swap rate", "annuity factor"),
    invariants=(
        Invariant(
            id="value_zero_at_par_rate",
            statement="A swap whose fixed rate is the par swap rate is worth zero.",
        ),
        Invariant(
            id="payer_and_receiver_values_offset",
            statement="The payer's value and the receiver's sum to zero.",
        ),
        Invariant(
            id="value_linear_in_notional",
            statement=(
                "Scaling the notional scales every value by the same factor and "
                "leaves the par rate and annuity unchanged."
            ),
        ),
    ),
    examples=(
        Example(
            name="two_year_semiannual",
            inputs={
                "calculation": "zero_curve",
                "notional": 100_000_000,
                "fixed_rate": 0.065,
                "accruals": [0.5, 0.5, 0.5, 0.5],
                "curve_tenors": [0.5, 1.0, 1.5, 2.0],
                "curve_rates": [0.05, 0.058, 0.064, 0.068],
            },
        ),
        Example(
            name="from_discount_factors",
            inputs={
                "calculation": "discount_factors",
                "notional": 1_000_000,
                "fixed_rate": 0.05,
                "accruals": [1.0, 1.0],
                "discount_factors": [0.95, 0.9],
            },
        ),
        Example(
            name="dated_five_year",
            inputs={
                "calculation": "dated",
                "notional": 10_000_000,
                "fixed_rate": 0.04,
                "valuation_date": "2026-01-15",
                "start_date": "2026-01-15",
                "payment_dates": [
                    "2027-01-15",
                    "2028-01-15",
                    "2029-01-15",
                    "2030-01-15",
                    "2031-01-15",
                ],
                "curve_tenors": [1.0, 5.0],
                "curve_rates": [0.035, 0.04],
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def interest_rate_swap(inputs: InterestRateSwapInputs) -> InterestRateSwapOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[ModelInputs], Callable[[Any], InterestRateSwapOutputs]]
] = {
    DiscountFactorInputs: _from_discount_factors,
    ZeroCurveInputs: _from_zero_curve,
    DatedInputs: _from_dates,
}
