# src/pyeconomics/models/fixed_income/curve_bootstrap.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Spot, par and forward rates: ``fixed_income.curve_bootstrap``.

Three calculations, discriminated on ``calculation``:

- ``from_par``: bootstrap par yields at regular tenors (one per coupon period,
  1/f, 2/f, ... years) into discount factors, spot rates and one-period
  forward rates;
- ``from_spot``: the reverse, spot rates at regular tenors into discount
  factors, par yields and forward rates;
- ``forward_rate``: the forward rate between two maturities implied by their
  spot rates.

Par yields are coupon rates paid f times a year. Spot and forward rates are
quoted with periodic compounding at the same frequency, or continuously
(ADR-0008 decision 4); the discount factor at tenor k/f is the same either way.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    ChangelogEntry,
    Compounding,
    CostClass,
    DomainError,
    Evidence,
    Example,
    Frequency,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Rate,
    Reference,
    Symbol,
    Years,
    forward_rate,
    model,
    par_rate,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.core.units import Ratio
from pyeconomics.models.fixed_income._bonds import (  # noqa: TC001 - pydantic reads it
    FrequencyName,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = ["curve_bootstrap"]

#: The most tenors a curve takes: 50 years of semiannual periods, or 200 periods.
_TENORS_MAX: Final = 200
#: The rates an input curve holds, and an output may.
_RATE_MIN: Final = -0.1
_RATE_IN_MAX: Final = 1.0
_RATE_OUT_MIN: Final = -0.99
_RATE_OUT_MAX: Final = 10.0
#: The largest discount factor an output holds: 0.9^-200, the factor at -10%
#: compounded annually for 200 years, is about 1.4e9.
_FACTOR_MAX: Final = 1e12
#: The longest horizon of a forward rate.
_YEARS_MAX: Final = 100.0

_FREQUENCIES: Final[dict[str, Frequency]] = {
    "annual": Frequency.ANNUAL,
    "semiannual": Frequency.SEMIANNUAL,
    "quarterly": Frequency.QUARTERLY,
    "monthly": Frequency.MONTHLY,
}

type QuoteCompounding = Literal["periodic", "continuous"]

_RatesIn = Annotated[
    tuple[Annotated[Rate, Field(ge=_RATE_MIN, le=_RATE_IN_MAX)], ...], ARRAY_INPUT
]
_RatesOut = Annotated[
    tuple[Annotated[Rate, Field(ge=_RATE_OUT_MIN, le=_RATE_OUT_MAX)], ...],
    ARRAY_INPUT,
]
_Factors = Annotated[
    tuple[Annotated[Ratio, Field(gt=0.0, le=_FACTOR_MAX)], ...], ARRAY_INPUT
]
# 200 annual tenors reach 200 years.
_Tenors = Annotated[tuple[Annotated[Years, Field(gt=0.0, le=200.0)], ...], ARRAY_INPUT]


def _frequency() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        "semiannual",
        description="Coupons per year of the par bonds, and the tenor spacing",
    )


def _compounding() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        "periodic",
        description=(
            "How spot and forward rates compound: at the frequency (periodic) "
            "or continuously"
        ),
    )


# --- inputs ------------------------------------------------------------------


class FromParInputs(ModelInputs):
    """Par yields at regular tenors."""

    calculation: Literal["from_par"] = Field(
        "from_par", description="Bootstrap spot rates from par yields"
    )
    par_yields: _RatesIn = Field(
        min_length=1,
        max_length=_TENORS_MAX,
        description="Par yield at each tenor 1/f, 2/f, ... years",
    )
    frequency: FrequencyName = _frequency()
    compounding: QuoteCompounding = _compounding()


class FromSpotInputs(ModelInputs):
    """Spot rates at regular tenors."""

    calculation: Literal["from_spot"] = Field(
        "from_spot", description="Par yields and forwards from spot rates"
    )
    spot_rates: _RatesIn = Field(
        min_length=1,
        max_length=_TENORS_MAX,
        description="Spot (zero) rate at each tenor 1/f, 2/f, ... years",
    )
    frequency: FrequencyName = _frequency()
    compounding: QuoteCompounding = _compounding()


class ForwardRateInputs(ModelInputs):
    """Two spot rates and their maturities."""

    calculation: Literal["forward_rate"] = Field(
        "forward_rate", description="Forward rate between two maturities"
    )
    near_rate: Rate = Field(
        ge=_RATE_MIN, le=_RATE_IN_MAX, description="Spot rate to the near maturity"
    )
    near_years: Years = Field(
        ge=0.0, le=_YEARS_MAX, description="Near maturity, in years (0 for now)"
    )
    far_rate: Rate = Field(
        ge=_RATE_MIN, le=_RATE_IN_MAX, description="Spot rate to the far maturity"
    )
    far_years: Years = Field(
        gt=0.0, le=_YEARS_MAX, description="Far maturity, in years"
    )
    frequency: FrequencyName = Field(
        "annual", description="Compounding frequency of periodic rates"
    )
    compounding: QuoteCompounding = _compounding()

    @model_validator(mode="after")
    def _far_after_near(self) -> Self:
        if self.far_years <= self.near_years:
            msg = (
                f"the far maturity ({self.far_years}) must be after the near one "
                f"({self.near_years})"
            )
            raise ValueError(msg)
        return self


CurveBootstrapInputs = Annotated[
    FromParInputs | FromSpotInputs | ForwardRateInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


def _tenors() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(max_length=_TENORS_MAX, description="Tenor of each point, in years")


def _factors() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(max_length=_TENORS_MAX, description="Discount factor at each tenor")


def _forwards() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        max_length=_TENORS_MAX,
        description="Forward rate over each period, ending at its tenor",
    )


class FromParOutputs(ModelOutputs):
    calculation: Literal["from_par"] = Field(
        "from_par", description="Bootstrap spot rates from par yields"
    )
    tenors: _Tenors = _tenors()
    discount_factors: _Factors = _factors()
    spot_rates: _RatesOut = Field(
        max_length=_TENORS_MAX, description="Spot (zero) rate at each tenor"
    )
    forward_rates: _RatesOut = _forwards()


class FromSpotOutputs(ModelOutputs):
    calculation: Literal["from_spot"] = Field(
        "from_spot", description="Par yields and forwards from spot rates"
    )
    tenors: _Tenors = _tenors()
    discount_factors: _Factors = _factors()
    par_yields: _RatesOut = Field(
        max_length=_TENORS_MAX, description="Par yield at each tenor"
    )
    forward_rates: _RatesOut = _forwards()


class ForwardRateOutputs(ModelOutputs):
    calculation: Literal["forward_rate"] = Field(
        "forward_rate", description="Forward rate between two maturities"
    )
    forward_rate: Rate = Field(
        ge=_RATE_OUT_MIN,
        le=_RATE_OUT_MAX,
        description="Rate from the near to the far maturity",
    )


CurveBootstrapOutputs = Annotated[
    FromParOutputs | FromSpotOutputs | ForwardRateOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _rate_of(
    factor: float, years: float, compounding: Compounding, f: Frequency
) -> float:
    """Return the rate whose discount factor over ``years`` is ``factor``."""
    log_growth = -math.log(factor)
    if compounding is Compounding.CONTINUOUS:
        rate = log_growth / years
    else:
        m = f.periods_per_year
        rate = m * math.expm1(log_growth / (m * years))
    if not (math.isfinite(rate) and _RATE_OUT_MIN <= rate <= _RATE_OUT_MAX):
        msg = (
            f"a rate of {rate!r} over {years:g} years is outside "
            f"[{_RATE_OUT_MIN}, {_RATE_OUT_MAX}]; the curve has no representable "
            "spot or forward rate there"
        )
        raise DomainError(msg)
    return rate


def _curve(
    factors: Sequence[float], f: Frequency, compounding: Compounding
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    """Return the tenors, spot rates and one-period forwards of the factors."""
    m = f.periods_per_year
    tenors = tuple((k + 1) / m for k in range(len(factors)))
    spots = tuple(
        _rate_of(d, t, compounding, f) for d, t in zip(factors, tenors, strict=True)
    )
    previous = (1.0, *factors[:-1])
    forwards = tuple(
        _rate_of(d / p, 1 / m, compounding, f)
        for d, p in zip(factors, previous, strict=True)
    )
    return tenors, spots, forwards


def _from_par(inputs: FromParInputs) -> FromParOutputs:
    f = _FREQUENCIES[inputs.frequency]
    m = f.periods_per_year
    factors: list[float] = []
    # Par bond k - 1 prices at par, so 1 - c_k A = d_{k-1} + (c_{k-1} - c_k) A
    # for the annuity A of the earlier factors: that form keeps the digits the
    # direct one loses to cancellation when the factors are small.
    previous_factor, previous_coupon, annuity = 1.0, 0.0, 0.0
    for k, par in enumerate(inputs.par_yields, start=1):
        coupon = par / m
        factor = (previous_factor + (previous_coupon - coupon) * annuity) / (
            1.0 + coupon
        )
        if not (factor > 0 and factor <= _FACTOR_MAX):
            msg = (
                f"the par yields give a discount factor of {factor!r} at tenor "
                f"{k / m:g} years; a curve needs positive factors"
            )
            raise DomainError(msg)
        factors.append(factor)
        annuity += factor
        previous_factor, previous_coupon = factor, coupon
    tenors, spots, forwards = _curve(factors, f, Compounding(inputs.compounding))
    return FromParOutputs(
        tenors=tenors,
        discount_factors=tuple(factors),
        spot_rates=spots,
        forward_rates=forwards,
    )


def _from_spot(inputs: FromSpotInputs) -> FromSpotOutputs:
    f = _FREQUENCIES[inputs.frequency]
    m = f.periods_per_year
    compounding = Compounding(inputs.compounding)
    factors = [
        1.0 / _growth(rate, (k + 1) / m, compounding, m)
        for k, rate in enumerate(inputs.spot_rates)
    ]
    accruals = [1.0 / m] * len(factors)
    par = tuple(
        _bounded_rate(par_rate(factors[: k + 1], accruals[: k + 1]), "par yield")
        for k in range(len(factors))
    )
    tenors, _, forwards = _curve(factors, f, compounding)
    return FromSpotOutputs(
        tenors=tenors,
        discount_factors=tuple(factors),
        par_yields=par,
        forward_rates=forwards,
    )


def _growth(rate: float, years: float, compounding: Compounding, m: int) -> float:
    """Return the growth of one unit at a rate compounded m times a year, or always."""
    if compounding is Compounding.CONTINUOUS:
        return math.exp(rate * years)
    return math.exp(m * years * math.log1p(rate / m))


def _bounded_rate(rate: float, what: str) -> float:
    if not (math.isfinite(rate) and _RATE_OUT_MIN <= rate <= _RATE_OUT_MAX):
        msg = f"the {what} {rate!r} is outside [{_RATE_OUT_MIN}, {_RATE_OUT_MAX}]"
        raise DomainError(msg)
    return rate


def _forward_rate(inputs: ForwardRateInputs) -> ForwardRateOutputs:
    compounding = Compounding(inputs.compounding)
    frequency = (
        _FREQUENCIES[inputs.frequency] if compounding is Compounding.PERIODIC else None
    )
    rate = forward_rate(
        inputs.near_rate,
        inputs.near_years,
        inputs.far_rate,
        inputs.far_years,
        compounding,
        frequency=frequency,
    )
    return ForwardRateOutputs(forward_rate=_bounded_rate(rate, "forward rate"))


# --- the model ---------------------------------------------------------------

_HULL = Reference(
    key="hull2018",
    citation=(
        "Hull, J. C. (2018). Options, Futures, and Other Derivatives, 10th ed. Pearson."
    ),
    url="https://openlibrary.org/isbn/9780134472089",
    isbn="9780134472089",
    locator="Chapter 4 (zero rates, par yields, bootstrapping and forward rates)",
)

_FABOZZI = Reference(
    key="fabozzi2005",
    citation=(
        "Fabozzi, F. J. (2005). Fixed Income Mathematics: Analytical and "
        "Statistical Techniques, 4th ed. McGraw-Hill."
    ),
    url="https://openlibrary.org/isbn/9780071460736",
    isbn="9780071460736",
    locator="Chapter 7 (the yield curve, spot rate curve and forward rates)",
)


@model(
    id="fixed_income.curve_bootstrap",
    version=1,
    title="Spot, par and forward curves",
    summary=(
        "Bootstrap spot rates and discount factors from par yields, par yields "
        "from spot rates, and forward rates between maturities."
    ),
    formula=(
        r"d_k = \frac{1 - \frac{c_k}{f}\sum_{j<k} d_j}{1 + \frac{c_k}{f}}",
        r"s_k = f\left(d_k^{-1/k} - 1\right), \quad s_k^{cont} = -\frac{f}{k}\ln d_k",
        r"c_k = f\,\frac{1 - d_k}{\sum_{j \le k} d_j}",
        (
            r"\left(1 + \frac{F_{1,2}}{f}\right)^{f (T_2 - T_1)} = "
            r"\frac{(1 + s_2/f)^{f T_2}}{(1 + s_1/f)^{f T_1}}"
        ),
    ),
    symbols=(
        Symbol(
            "d_k",
            "Discount factor for a payment k periods from now",
            "discount_factors",
        ),
        Symbol("c_k", "Par yield of the bond maturing in k periods", "par_yields"),
        Symbol("f", "Periods in a year", "frequency"),
        Symbol(
            "s_k",
            "Spot rate for k periods, compounded f times a year",
            "spot_rates",
        ),
        Symbol("s_k^{cont}", "The same spot rate, continuously compounded"),
        Symbol(
            "F_{1,2}",
            "Forward rate between the near and the far date",
            "forward_rate",
        ),
        Symbol("T_1", "Years to the near date", "near_years"),
        Symbol("T_2", "Years to the far date", "far_years"),
        Symbol("s_1", "Spot rate to the near date", "near_rate"),
        Symbol("s_2", "Spot rate to the far date", "far_rate"),
    ),
    assumptions=(
        (
            "The par yields are coupon rates of bonds paying f coupons a year, "
            "priced at par on a coupon date, one maturing at each tenor 1/f, "
            "2/f, ... years."
        ),
        (
            "Spot and forward rates compound at the frequency, or continuously; "
            "a forward rate shares the compounding of the spot rates it comes from."
        ),
    ),
    limitations=(
        (
            "Par yields whose bootstrapped discount factor is not positive, and "
            "any rate outside [-0.99, 10], raise DomainError."
        ),
        (
            "Tenors are regular; interpolating between irregular instruments is "
            "out of scope (pyeconomics.core.curves interpolates zero rates)."
        ),
    ),
    references=(_HULL, _FABOZZI),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("yield curve", "bootstrap", "spot rate", "forward rate", "par yield"),
    invariants=(
        Invariant(
            id="flat_curve_is_invariant",
            statement=(
                "A flat par curve bootstraps to spot and forward rates equal to "
                "it, with periodic compounding at its frequency."
            ),
        ),
        Invariant(
            id="bootstrapped_curve_reprices_par_bonds",
            statement=(
                "Discounting each par bond's coupons and principal with the "
                "bootstrapped discount factors gives its face value."
            ),
        ),
        Invariant(
            id="forwards_compose_to_spots",
            statement=(
                "Compounding the one-period forward rates to a tenor gives that "
                "tenor's spot rate."
            ),
        ),
        Invariant(
            id="discount_factors_positive",
            statement="Every discount factor returned is positive.",
        ),
    ),
    examples=(
        Example(
            name="treasury_par_curve",
            inputs={
                "calculation": "from_par",
                "par_yields": [0.040, 0.041, 0.042, 0.0425, 0.043, 0.0435],
            },
            note="Three years of semiannual par yields.",
        ),
        Example(
            name="par_yield_from_zeros",
            inputs={
                "calculation": "from_spot",
                "spot_rates": [0.05, 0.058, 0.064, 0.068],
                "compounding": "continuous",
            },
        ),
        Example(
            name="one_year_forward_in_one_year",
            inputs={
                "calculation": "forward_rate",
                "near_rate": 0.03,
                "near_years": 1.0,
                "far_rate": 0.04,
                "far_years": 2.0,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def curve_bootstrap(inputs: CurveBootstrapInputs) -> CurveBootstrapOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[ModelInputs], Callable[[Any], CurveBootstrapOutputs]]
] = {
    FromParInputs: _from_par,
    FromSpotInputs: _from_spot,
    ForwardRateInputs: _forward_rate,
}
