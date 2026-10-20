# src/pyeconomics/models/fixed_income/interest_rate_tree.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The binomial interest-rate tree: ``fixed_income.interest_rate_tree``.

Kalotay, Williams and Fabozzi's (1993) lognormal tree of one-period rates. Each
period of :math:`\Delta = 1/m` years the rate moves to one of two equally likely
values, and the rates of one period differ by a constant factor,

.. math:: r_{t,j} = r_{t,0}\, e^{2 \sigma \sqrt{\Delta}\, j}, \qquad j = 0, \dots, t,

so their spread is lognormal with volatility :math:`\sigma` a year (KWF use
annual periods, :math:`e^{2\sigma}`). A node discounts one period at its rate,
:math:`1 / (1 + r \Delta)`. The tree is calibrated to a par curve: each period's
lowest rate is the one at which the tree prices that maturity's par bond, paying
its par yield :math:`m` times a year, at par. The model solves for it with the
state prices of the period (Jamshidian's forward induction), which gives the
same rates as KWF's repricing by backward induction, through
:func:`~pyeconomics.core.numerics.find_root`.

A bond is valued by backward induction: a node's value, after its coupon, is the
average of its two successors' values plus their coupons, discounted at the
node's rate plus a spread. Where the bond can be called (put), the value is the
lesser (greater) of that and the exercise price. Four calculations, on
``calculation``:

- ``calibrate``: the calibrated tree and its discount factors;
- ``value``: an option-free, callable or putable bond at a spread, with the value
  of its option;
- ``oas``: the option-adjusted spread, the constant spread over every node rate
  at which the tree reprices the bond to a market price;
- ``effective``: effective duration and convexity, from values with the par
  curve shifted down and up and the tree recalibrated, at a constant OAS.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
    Binding,
    ChangelogEntry,
    ConvergenceError,
    CostClass,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Rate,
    Reference,
    RootPolicy,
    Volatility,
    Years,
    find_root,
    interpolate_rates,
    model,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.core.units import Ratio
from pyeconomics.models.fixed_income._bonds import (  # noqa: TC001 - pydantic reads it
    FrequencyName,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from numpy.typing import NDArray

__all__ = ["interest_rate_tree"]

#: The most periods a tree spans (thirty years of quarters, or ten of months), and
#: the most points of the par curve it is calibrated to.
_STEPS_MAX: Final = 120
_TENORS_MAX: Final = 60
_TENOR_MAX: Final = 100.0
#: Par yields a curve may hold, the volatility a tree takes and the rates and
#: spreads it searches.
_PAR_MAX: Final = 1.0
_VOLATILITY_MAX: Final = 0.5
_RATE_MAX: Final = 10.0
_SPREAD_MIN: Final = -0.5
_SPREAD_MAX: Final = 1.0
_SHIFT_MIN: Final = 1e-6
_SHIFT_MAX: Final = 0.01
#: A face value and an exercise or market price, per bond: a face of at least
#: one cent keeps the values and their second differences representable.
_FACE_MIN: Final = 0.01
_FACE_MAX: Final = 1e9
_MONEY_OUT: Final = 1e15
_DURATION_MAX: Final = 200.0
_CONVEXITY_MAX: Final = 1e6
#: How close a time must be to a whole number of periods.
_WHOLE: Final = 1e-9
#: How far a discount factor may round past the last one before it is a negative
#: forward rate.
_ROUNDING: Final = 1e-14
#: Each period's lowest rate to full relative precision: a long, volatile tree's
#: lowest rates fall below 1e-9, where ADR-0008's absolute xtol of 2e-12 would
#: leave the tree's prices of its par bonds off par. The iteration cap stays.
_CALIBRATION: Final = RootPolicy(xtol=1e-300, maxiter=200)

_PERIODS: Final = {"annual": 1, "semiannual": 2, "quarterly": 4, "monthly": 12}

type Option = Literal["none", "call", "put"]

_Tenors = Annotated[
    tuple[Annotated[Years, Field(gt=0.0, le=_TENOR_MAX)], ...], ARRAY_INPUT
]
_ParYields = Annotated[
    tuple[Annotated[Rate, Field(ge=0.0, le=_PAR_MAX)], ...], ARRAY_INPUT
]
_Times = Annotated[
    tuple[Annotated[Years, Field(gt=0.0, le=_TENOR_MAX)], ...], ARRAY_INPUT
]
_Prices = Annotated[
    tuple[Annotated[Money, Field(gt=0.0, le=_FACE_MAX)], ...], ARRAY_INPUT
]
_RatesOut = Annotated[
    tuple[Annotated[Rate, Field(ge=0.0, le=_RATE_MAX)], ...], ARRAY_INPUT
]
_NodeRow = Annotated[
    tuple[Annotated[Rate, Field(ge=0.0, le=_RATE_MAX)], ...],
    Field(min_length=1, max_length=_STEPS_MAX),
    ARRAY_INPUT,
]
_Factors = Annotated[tuple[Annotated[Ratio, Field(gt=0.0, le=1.0)], ...], ARRAY_INPUT]


def _periods(years: float, frequency: str, what: str) -> int:
    """Return ``years`` in whole periods, or say why it is not a whole number."""
    m = _PERIODS[frequency]
    count = round(years * m)
    if abs(years * m - count) > _WHOLE * max(1.0, years * m) or count < 1:
        msg = f"{what} ({years:g} years) is not a whole number of {frequency} periods"
        raise ValueError(msg)
    if count > _STEPS_MAX:
        msg = f"{what} spans {count} periods; a tree takes at most {_STEPS_MAX}"
        raise ValueError(msg)
    return count


# --- inputs ------------------------------------------------------------------


class _CurveInputs(ModelInputs):
    """The par curve and volatility a tree is calibrated to."""

    curve_tenors: _Tenors = Field(
        min_length=1,
        max_length=_TENORS_MAX,
        description="Tenor of each par yield, in years, increasing",
    )
    par_yields: _ParYields = Field(
        min_length=1,
        max_length=_TENORS_MAX,
        description=(
            "Par yield at each tenor: the coupon rate, paid each period, of a bond "
            "priced at par; linear between tenors and flat before the first"
        ),
    )
    volatility: Volatility = Field(
        ge=0.0,
        le=_VOLATILITY_MAX,
        description=(
            "Volatility of the one-period rate a year (0.1 is 10%); zero gives the "
            "forward rates, so the bound is widened to include it"
        ),
    )
    frequency: FrequencyName = Field(
        "semiannual",
        description="Periods a year: the tree's step and the par bonds' coupons",
    )

    @model_validator(mode="after")
    def _curve(self) -> Self:
        if len(self.par_yields) != len(self.curve_tenors):
            msg = (
                f"give one par yield per tenor: {len(self.par_yields)} yields for "
                f"{len(self.curve_tenors)} tenors"
            )
            raise ValueError(msg)
        tenors = self.curve_tenors
        if any(b <= a for a, b in pairwise(tenors)):
            msg = "the curve tenors must be strictly increasing"
            raise ValueError(msg)
        return self

    def reach(self, years: float, what: str) -> int:
        """Return ``years`` in periods, refusing one beyond the curve's last tenor."""
        if years > self.curve_tenors[-1] * (1 + _WHOLE):
            msg = (
                f"{what} ({years:g} years) is beyond the par curve, which ends at "
                f"{self.curve_tenors[-1]:g} years"
            )
            raise ValueError(msg)
        return _periods(years, self.frequency, what)


class CalibrateInputs(_CurveInputs):
    """A par curve, a volatility and the years the tree spans."""

    calculation: Literal["calibrate"] = Field(
        "calibrate", description="Calibrate the tree to the par curve"
    )
    years: Years = Field(
        gt=0.0, le=_TENOR_MAX, description="How many years the tree spans"
    )

    @model_validator(mode="after")
    def _span(self) -> Self:
        self.reach(self.years, "the tree's span")
        return self


class _BondInputs(_CurveInputs):
    """A bond with an optional call or put schedule, valued on the tree."""

    maturity_years: Years = Field(
        gt=0.0,
        le=_TENOR_MAX,
        description="Years to maturity, a whole number of periods from a coupon date",
    )
    coupon_rate: Rate = Field(
        ge=0.0, le=_PAR_MAX, description="Annual coupon rate, paid each period"
    )
    face: Money = Field(
        100.0, ge=_FACE_MIN, le=_FACE_MAX, description="Face value, repaid at maturity"
    )
    option: Option = Field(
        "none",
        description=(
            "'none', 'call' (the issuer may redeem at the exercise price) or 'put' "
            "(the holder may sell back at it)"
        ),
    )
    exercise_years: _Times = Field(
        (),
        max_length=_STEPS_MAX,
        description=(
            "When the option may be exercised, in years: coupon dates, after the "
            "coupon is paid, before maturity"
        ),
    )
    exercise_prices: _Prices = Field(
        (),
        max_length=_STEPS_MAX,
        description=(
            "The exercise price at each of those dates, in the face value's units "
            "(100 for par on a face of 100)"
        ),
    )

    @model_validator(mode="after")
    def _bond(self) -> Self:
        steps = self.reach(self.maturity_years, "the maturity")
        times, prices = self.exercise_years, self.exercise_prices
        if len(times) != len(prices):
            msg = "give one exercise price per exercise date"
            raise ValueError(msg)
        if (self.option == "none") != (not times):
            msg = "a call or a put needs exercise dates, and an option-free bond none"
            raise ValueError(msg)
        if any(b <= a for a, b in pairwise(times)):
            msg = "the exercise dates must be strictly increasing"
            raise ValueError(msg)
        for when in times:
            if _periods(when, self.frequency, "an exercise date") >= steps:
                msg = f"an exercise date ({when:g} years) is not before maturity"
                raise ValueError(msg)
        return self

    def schedule(self) -> dict[int, float]:
        """Map each exercise date's period to its price."""
        m = _PERIODS[self.frequency]
        return {
            round(when * m): price
            for when, price in zip(
                self.exercise_years, self.exercise_prices, strict=True
            )
        }


def _spread(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(0.0, ge=_SPREAD_MIN, le=_SPREAD_MAX, description=description)


class ValueInputs(_BondInputs):
    calculation: Literal["value"] = Field(
        "value", description="Value the bond and its option on the tree"
    )
    oas: Rate = _spread("A constant spread added to every node rate (the OAS)")


class OasInputs(_BondInputs):
    calculation: Literal["oas"] = Field(
        "oas", description="The option-adjusted spread at a market price"
    )
    price: Money = Field(
        gt=0.0,
        le=_FACE_MAX,
        description="The bond's market price, in the face value's units",
    )


class EffectiveInputs(_BondInputs):
    calculation: Literal["effective"] = Field(
        "effective", description="Effective duration and convexity"
    )
    oas: Rate = _spread("The OAS held constant while the curve shifts")
    shift: Rate = Field(
        0.001,
        ge=_SHIFT_MIN,
        le=_SHIFT_MAX,
        description=(
            "How far the par curve shifts down and up (0.001 is 10 bp); at least "
            "0.01 bp, below which the second difference is rounding error"
        ),
    )


InterestRateTreeInputs = Annotated[
    CalibrateInputs | ValueInputs | OasInputs | EffectiveInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


def _money(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=_MONEY_OUT, description=description)


class CalibrateOutputs(ModelOutputs):
    calculation: Literal["calibrate"] = Field(
        "calibrate", description="Calibrate the tree to the par curve"
    )
    step_years: Years = Field(gt=0.0, le=1.0, description="Years in one period")
    rate_ratio: Ratio = Field(
        ge=1.0,
        le=math.exp(2 * _VOLATILITY_MAX),
        description="The ratio of adjacent rates in a period, e^(2 sigma sqrt(step))",
    )
    par_yields: _RatesOut = Field(
        max_length=_STEPS_MAX,
        description="The par yield at the end of each period, read off the curve",
    )
    lowest_rates: _RatesOut = Field(
        max_length=_STEPS_MAX, description="Each period's lowest one-period rate"
    )
    node_rates: tuple[_NodeRow, ...] = Field(
        max_length=_STEPS_MAX,
        description="Each period's one-period rates, lowest first, one row a period",
    )
    discount_factors: _Factors = Field(
        max_length=_STEPS_MAX,
        description="The tree's discount factor to the end of each period",
    )


class ValueOutputs(ModelOutputs):
    calculation: Literal["value"] = Field(
        "value", description="Value the bond and its option on the tree"
    )
    value: Money = _money("The bond's value, with its option")
    option_free_value: Money = _money("The value of the same bond with no option")
    option_value: Money = _money(
        "The option's value to its holder: option-free less callable, or "
        "putable less option-free"
    )


class OasOutputs(ModelOutputs):
    calculation: Literal["oas"] = Field(
        "oas", description="The option-adjusted spread at a market price"
    )
    oas: Rate = Field(
        ge=_SPREAD_MIN,
        le=_SPREAD_MAX,
        description="The spread over every node rate that reprices the bond",
    )
    model_value: Money = _money("The bond's value with no spread, the tree's own")
    option_free_value: Money = _money("The option-free bond's value at the OAS")
    option_value: Money = _money("The option's value to its holder at the OAS")


class EffectiveOutputs(ModelOutputs):
    calculation: Literal["effective"] = Field(
        "effective", description="Effective duration and convexity"
    )
    value: Money = _money("The bond's value on the unshifted tree")
    value_down: Money = _money("The value with the par curve shifted down")
    value_up: Money = _money("The value with the par curve shifted up")
    effective_duration: Years = Field(
        ge=-_DURATION_MAX,
        le=_DURATION_MAX,
        description="(V_down - V_up) / (2 V shift)",
    )
    effective_convexity: Ratio = Field(
        ge=-_CONVEXITY_MAX,
        le=_CONVEXITY_MAX,
        description="(V_down + V_up - 2 V) / (V shift^2)",
    )


InterestRateTreeOutputs = Annotated[
    CalibrateOutputs | ValueOutputs | OasOutputs | EffectiveOutputs,
    Field(discriminator="calculation"),
]


# --- the tree ----------------------------------------------------------------

type _Vector = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class _Tree:
    """A calibrated tree: each period's lowest rate and the ratio between rates."""

    step: float
    ratio: float
    par: tuple[float, ...]
    lowest: tuple[float, ...]
    factors: tuple[float, ...]

    def rates(self, period: int) -> _Vector:
        return np.asarray(
            self.lowest[period] * self.ratio ** np.arange(period + 1), dtype=np.float64
        )


def _calibrate(
    tenors: Sequence[float],
    par_yields: Sequence[float],
    volatility: float,
    frequency: str,
    steps: int,
) -> _Tree:
    """Fit each period's lowest rate so the tree prices that period's par bond at par.

    With the state prices ``q`` of a period (what one unit paid at each node is
    worth today), the discount factor to the period's end is
    ``sum(q / (1 + r_j step))``; the par bond maturing then fixes it, so the
    lowest rate is a root of one decreasing function.
    """
    m = _PERIODS[frequency]
    step = 1.0 / m
    par = interpolate_rates(tenors, par_yields, [(k + 1) / m for k in range(steps)])
    ratio = math.exp(2.0 * volatility * math.sqrt(step))
    states = np.ones(1)
    annuity = 0.0
    lowest: list[float] = []
    factors: list[float] = []
    previous = 1.0
    for period in range(steps):
        coupon = par[period] * step
        target = (1.0 - coupon * annuity) / (1.0 + coupon)
        end = (period + 1) * step
        if not target > 0:
            msg = f"the par curve gives no positive discount factor at {end:g} years"
            raise DomainError(msg)
        # The par bonds fix the discount factors, so a negative forward rate is
        # a factor above the last one, whatever the volatility.
        if target > previous * (1.0 + _ROUNDING):
            msg = (
                f"the par curve implies a negative forward rate before {end:g} "
                "years; a lognormal tree has none"
            )
            raise DomainError(msg)
        powers = np.asarray(ratio ** np.arange(period + 1), dtype=np.float64)

        def gap(
            rate: float,
            states: _Vector = states,
            powers: _Vector = powers,
            target: float = target,
        ) -> float:
            return math.fsum((states / (1.0 + rate * powers * step)).tolist()) - target

        # A zero forward rate rounds either side of zero: it is a rate of zero.
        rate = (
            0.0
            if gap(0.0) <= 0
            else find_root(
                gap, 0.0, 1.0, limits=(0.0, _RATE_MAX), policy=_CALIBRATION
            ).root
        )
        previous = target
        discounts = 1.0 / (1.0 + rate * powers * step)
        # The par bond fixes the factor; the tree's own sum of state prices
        # matches it to the root's tolerance, and may round past 1 at zero rates.
        lowest.append(rate)
        factors.append(target)
        annuity += target
        moved = 0.5 * states * discounts
        states = np.concatenate((moved, [0.0])) + np.concatenate(([0.0], moved))
    return _Tree(step, ratio, tuple(par), tuple(lowest), tuple(factors))


def _tree_of(inputs: _CurveInputs, years: float) -> _Tree:
    steps = _periods(years, inputs.frequency, "the span")
    return _calibrate(
        inputs.curve_tenors,
        inputs.par_yields,
        inputs.volatility,
        inputs.frequency,
        steps,
    )


def _value(
    tree: _Tree,
    inputs: _BondInputs,
    spread: float,
    *,
    option: bool = True,
) -> float:
    """Value the bond by backward induction at a spread over every node rate."""
    steps = _periods(inputs.maturity_years, inputs.frequency, "the maturity")
    coupon = inputs.coupon_rate * tree.step * inputs.face
    schedule = inputs.schedule() if option else {}
    exercise = np.minimum if inputs.option == "call" else np.maximum
    values = np.full(steps + 1, inputs.face)
    for period in range(steps - 1, -1, -1):
        rates = tree.rates(period) + spread
        values = (
            0.5 * (values[:-1] + values[1:] + 2.0 * coupon) / (1.0 + rates * tree.step)
        )
        price = schedule.get(period)
        if price is not None:
            values = exercise(values, price)
    return float(values[0])


def _bounded(value: float, low: float, high: float, what: str) -> float:
    if not (math.isfinite(value) and low <= value <= high):
        msg = f"the {what} {value!r} is outside [{low}, {high}]"
        raise DomainError(msg)
    return value


def _option_value(straight: float, value: float, option: str) -> float:
    """Return the option's value to its holder, clipped at zero against rounding."""
    difference = straight - value if option == "call" else value - straight
    return max(difference, 0.0) if option != "none" else 0.0


def _calibration(inputs: CalibrateInputs) -> CalibrateOutputs:
    tree = _tree_of(inputs, inputs.years)
    rows = [tree.rates(t) for t in range(len(tree.lowest))]
    if any(float(row[-1]) > _RATE_MAX for row in rows):
        # Only the output is bounded: a value weighs these nodes by 2^-t.
        msg = (
            f"the tree's highest node rates exceed {_RATE_MAX}, which the "
            "calibration cannot report: lower the volatility or the span"
        )
        raise DomainError(msg)
    return CalibrateOutputs(
        step_years=tree.step,
        rate_ratio=tree.ratio,
        par_yields=tree.par,
        lowest_rates=tree.lowest,
        node_rates=tuple(tuple(float(r) for r in row) for row in rows),
        discount_factors=tree.factors,
    )


def _valuation(inputs: ValueInputs) -> ValueOutputs:
    tree = _tree_of(inputs, inputs.maturity_years)
    value = _bounded(_value(tree, inputs, inputs.oas), 0.0, _MONEY_OUT, "value")
    straight = _bounded(
        _value(tree, inputs, inputs.oas, option=False), 0.0, _MONEY_OUT, "value"
    )
    return ValueOutputs(
        value=value,
        option_free_value=straight,
        option_value=_option_value(straight, value, inputs.option),
    )


def _oas(inputs: OasInputs) -> OasOutputs:
    tree = _tree_of(inputs, inputs.maturity_years)

    def gap(spread: float) -> float:
        return _value(tree, inputs, spread) - inputs.price

    try:
        spread = find_root(gap, -0.05, 0.2, limits=(_SPREAD_MIN, _SPREAD_MAX)).root
    except ConvergenceError as error:
        msg = (
            f"no spread in [{_SPREAD_MIN}, {_SPREAD_MAX}] reprices the bond to "
            f"{inputs.price!r}: {error}"
        )
        raise ConvergenceError(msg) from None
    value = _value(tree, inputs, spread)
    straight = _value(tree, inputs, spread, option=False)
    return OasOutputs(
        oas=spread,
        model_value=_bounded(_value(tree, inputs, 0.0), 0.0, _MONEY_OUT, "value"),
        option_free_value=_bounded(straight, 0.0, _MONEY_OUT, "value"),
        option_value=_option_value(straight, value, inputs.option),
    )


def _effective(inputs: EffectiveInputs) -> EffectiveOutputs:
    steps = _periods(inputs.maturity_years, inputs.frequency, "the maturity")
    values = []
    for shift in (0.0, -inputs.shift, inputs.shift):
        shifted = [y + shift for y in inputs.par_yields]
        try:
            tree = _calibrate(
                inputs.curve_tenors, shifted, inputs.volatility, inputs.frequency, steps
            )
        except DomainError as error:
            if shift == 0:
                raise
            # A curve near zero shifted down can imply a negative forward rate
            # that the curve itself does not: say which curve failed.
            msg = (
                f"the par curve shifted by {shift:+g} has no lognormal tree "
                f"({error}); pass a smaller shift"
            )
            raise DomainError(msg) from None
        values.append(
            _bounded(_value(tree, inputs, inputs.oas), 0.0, _MONEY_OUT, "value")
        )
    base, down, up = values
    h = inputs.shift
    if not base * h * h > 0:
        msg = "the bond is worth too little on the tree to measure its duration"
        raise DomainError(msg)
    return EffectiveOutputs(
        value=base,
        value_down=down,
        value_up=up,
        effective_duration=_bounded(
            (down - up) / (2.0 * base * h), -_DURATION_MAX, _DURATION_MAX, "duration"
        ),
        effective_convexity=_bounded(
            (down + up - 2.0 * base) / (base * h * h),
            -_CONVEXITY_MAX,
            _CONVEXITY_MAX,
            "convexity",
        ),
    )


# --- the model ---------------------------------------------------------------

_KWF = Reference(
    key="kalotay1993",
    citation=(
        "Kalotay, A. J., Williams, G. O. and Fabozzi, F. J. (1993). A Model for "
        "Valuing Bonds and Embedded Options. Financial Analysts Journal, 49(3), "
        "35-46."
    ),
    doi="10.2469/faj.v49.n3.35",
    locator=(
        "The lognormal tree, its calibration to the on-the-run par curve, and the "
        "valuation of option-free, callable and putable bonds, pp. 37-45"
    ),
)
_BDT = Reference(
    key="black1990",
    citation=(
        "Black, F., Derman, E. and Toy, W. (1990). A One-Factor Model of Interest "
        "Rates and Its Application to Treasury Bond Options. Financial Analysts "
        "Journal, 46(1), 33-39."
    ),
    doi="10.2469/faj.v46.n1.33",
    locator="The lognormal short-rate tree fitted to the term structure",
)
_JAMSHIDIAN = Reference(
    key="jamshidian1991",
    citation=(
        "Jamshidian, F. (1991). Forward Induction and Construction of Yield Curve "
        "Diffusion Models. Journal of Fixed Income, 1(1), 62-74."
    ),
    doi="10.3905/jfi.1991.692345",
    locator="Calibrating a tree period by period from its state prices",
)


@model(
    id="fixed_income.interest_rate_tree",
    version=1,
    title="Binomial interest-rate tree",
    summary=(
        "A lognormal binomial tree of rates calibrated to a par curve; values of "
        "option-free, callable and putable bonds, their options, the OAS and "
        "effective duration and convexity."
    ),
    formula=(
        r"r_{t,j} = r_{t,0}\, e^{2 \sigma \sqrt{\Delta} j}",
        (
            r"V_{t,j} = \frac{\tfrac12 (V_{t+1,j} + C) + \tfrac12 (V_{t+1,j+1} + C)}"
            r"{1 + (r_{t,j} + s) \Delta}, \quad V \leftarrow \min(V, K) "
            r"\text{ (call)}, \ \max(V, K) \text{ (put)}"
        ),
        (
            r"\sum_j \frac{q_{t,j}}{1 + r_{t,j}\Delta} = d_{t+1} = "
            r"\frac{1 - c_{t+1} \Delta \sum_{k \le t} d_k}{1 + c_{t+1} \Delta}"
        ),
        (
            r"D_{eff} = \frac{V_- - V_+}{2 V_0 \Delta y}, \quad "
            r"C_{eff} = \frac{V_- + V_+ - 2 V_0}{V_0 \Delta y^2}"
        ),
    ),
    assumptions=(
        (
            "Rates move each period to one of two equally likely values whose ratio "
            "is e^(2 sigma sqrt(step)); a node discounts one period at 1 / (1 + r "
            "step), so rates compound once a period."
        ),
        (
            "The par yields describe bonds paying a coupon each period; the curve "
            "is linear in par yield between its tenors and flat before the first."
        ),
        (
            "The bond is valued on a coupon date; an option is exercised on its "
            "dates after the coupon is paid, when exercise is worth more to its "
            "holder than continuing."
        ),
        (
            "Effective duration and convexity shift the whole par curve down and "
            "up, recalibrate the tree and hold the OAS."
        ),
        (
            "Profile: default binds the calibration to Treasury's par curve on the "
            "date (the tenors it publishes); the volatility is an input."
        ),
    ),
    limitations=(
        (
            "A lognormal tree has no negative rates: a par curve implying a "
            "negative forward rate, or no positive discount factor, raises "
            "DomainError, as does a value or duration outside its bounds. The "
            "calibrate calculation reports the node rates, so it refuses a tree "
            "whose highest rates exceed 10 (a long, volatile tree); the other "
            "calculations value on it, those nodes weighing 2^-t."
        ),
        (
            "Effective duration shifts the par curve down by the shift: a curve "
            "within the shift of zero (US bills in 2009-2015 and 2020-2021) can "
            "then imply a negative forward rate, and the calculation raises "
            "DomainError naming the shifted curve; pass a smaller shift."
        ),
        (
            "The volatility is constant across periods and the tree has one "
            "factor; it does not fit a volatility term structure."
        ),
        (
            "No spread in [-0.5, 1] repricing the bond to its price raises "
            "ConvergenceError."
        ),
        (
            "Accrued interest, call notice and lockout are not modelled: values "
            "are on a coupon date, at the exercise dates given."
        ),
    ),
    references=(_KWF, _BDT, _JAMSHIDIAN),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    tags=(
        "binomial tree",
        "interest rate tree",
        "callable bond",
        "putable bond",
        "option-adjusted spread",
        "effective duration",
    ),
    invariants=(
        Invariant(
            id="calibrated_tree_prices_par_bonds_at_par",
            statement=(
                "On the calibrated tree, an option-free bond paying the par yield of "
                "its maturity is worth its face value."
            ),
        ),
        Invariant(
            id="callable_below_straight_below_putable",
            statement=(
                "With the same coupon and exercise schedule, the callable bond is "
                "worth no more than the option-free bond, and that no more than "
                "the putable bond."
            ),
        ),
        Invariant(
            id="zero_volatility_oas_equals_zero_volatility_spread",
            statement=(
                "At zero volatility the tree holds the forward rates, and the OAS "
                "of an option-free bond is its zero-volatility spread over them."
            ),
        ),
        Invariant(
            id="oas_falls_as_price_rises",
            statement="A higher market price never gives a higher OAS.",
        ),
    ),
    examples=(
        Example(
            name="kwf_callable_bond",
            inputs={
                "calculation": "value",
                "curve_tenors": [1, 2, 3],
                "par_yields": [0.035, 0.04, 0.045],
                "volatility": 0.1,
                "frequency": "annual",
                "maturity_years": 3,
                "coupon_rate": 0.0525,
                "option": "call",
                "exercise_years": [1, 2],
                "exercise_prices": [100, 100],
            },
            note="Kalotay, Williams and Fabozzi's (1993) callable bond.",
        ),
        Example(
            name="calibrate_annual_tree",
            inputs={
                "calculation": "calibrate",
                "curve_tenors": [1, 2, 3],
                "par_yields": [0.035, 0.04, 0.045],
                "volatility": 0.1,
                "frequency": "annual",
                "years": 3,
            },
        ),
        Example(
            name="oas_at_a_market_price",
            inputs={
                "calculation": "oas",
                "curve_tenors": [1, 2, 3],
                "par_yields": [0.035, 0.04, 0.045],
                "volatility": 0.1,
                "frequency": "annual",
                "maturity_years": 3,
                "coupon_rate": 0.0525,
                "option": "call",
                "exercise_years": [1, 2],
                "exercise_prices": [100, 100],
                "price": 101.0,
            },
        ),
        Example(
            name="effective_duration_of_a_callable",
            inputs={
                "calculation": "effective",
                "curve_tenors": [0.5, 1, 2, 3, 5, 7, 10],
                "par_yields": [0.041, 0.040, 0.0385, 0.0378, 0.0381, 0.0392, 0.0410],
                "volatility": 0.15,
                "maturity_years": 10,
                "coupon_rate": 0.045,
                "option": "call",
                "exercise_years": [3, 4, 5, 6, 7, 8, 9],
                "exercise_prices": [101, 101, 100.5, 100.5, 100, 100, 100],
            },
            note="A ten-year semiannual bond callable each year after three.",
        ),
    ),
    bindings=(Binding("par_yields", "us.treasury.par_curve", tenors="curve_tenors"),),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def interest_rate_tree(inputs: InterestRateTreeInputs) -> InterestRateTreeOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[ModelInputs], Callable[[Any], InterestRateTreeOutputs]]
] = {
    CalibrateInputs: _calibration,
    ValueInputs: _valuation,
    OasInputs: _oas,
    EffectiveInputs: _effective,
}
