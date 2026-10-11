# src/pyeconomics/models/derivatives/black_scholes_merton.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""European options on a dividend-paying asset: ``derivatives.black_scholes_merton``.

Two calculations, discriminated on ``calculation``:

- ``price``: the Black-Scholes-Merton price of a European call or put on an
  asset with a continuous dividend yield, its delta, gamma, vega, theta, rho
  and dividend rho, and the residual of put-call parity between the two
  closed forms;
- ``implied_volatility``: the volatility whose price is a given price, solved
  over a bounded range, or ``None`` with a warning when no volatility in it
  gives the price.

Rates and yields are continuously compounded decimals per year; Greeks are per
unit (per 1.00 of volatility or rate, per year for theta). The outputs are the
formula's values for the inputs given, not trading advice.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Rate,
    Ratio,
    Reference,
    Volatility,
    Years,
    model,
)
from pyeconomics.models.derivatives._options import (
    DELTA_MAX,
    GAMMA_MAX,
    MONEY_OUT,
    PRICE_IN_MAX,
    RATE_MAX,
    RATE_MIN,
    VOL_MAX,
    VOL_MIN,
    YEARS_MAX,
    YEARS_MIN,
    OptionType,
    black_scholes,
    implied_volatility,
    no_arbitrage_bounds,
    option_type,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["black_scholes_merton"]

#: The underlying's price and the strike.
_PRICE_MIN: Final = 0.01
_PRICE_MAX: Final = 1e7


def _money(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-MONEY_OUT, le=MONEY_OUT, description=description)


# --- inputs ------------------------------------------------------------------


class _Option(ModelInputs):
    option_type: OptionType = option_type()
    spot: Money = Field(
        ge=_PRICE_MIN, le=_PRICE_MAX, description="Price of the underlying asset now"
    )
    strike: Money = Field(ge=_PRICE_MIN, le=_PRICE_MAX, description="Strike price")
    years: Years = Field(
        ge=YEARS_MIN, le=YEARS_MAX, description="Time to expiry, in years"
    )
    risk_free_rate: Rate = Field(
        ge=RATE_MIN,
        le=RATE_MAX,
        description="Risk-free rate per year, continuously compounded",
    )
    dividend_yield: Rate = Field(
        0.0,
        ge=RATE_MIN,
        le=RATE_MAX,
        description="Dividend yield per year, continuously compounded",
    )


class PriceInputs(_Option):
    """A European option and the volatility to price it at."""

    calculation: Literal["price"] = Field(
        "price", description="Price, Greeks and the put-call parity residual"
    )
    volatility: Volatility = Field(
        ge=VOL_MIN, le=VOL_MAX, description="Volatility of the asset's return per year"
    )


class ImpliedVolatilityInputs(_Option):
    """A European option and its price."""

    calculation: Literal["implied_volatility"] = Field(
        "implied_volatility", description="Volatility implied by a price"
    )
    option_price: Money = Field(
        ge=0.0, le=PRICE_IN_MAX, description="The option's price"
    )


BlackScholesMertonInputs = Annotated[
    PriceInputs | ImpliedVolatilityInputs, Field(discriminator="calculation")
]


# --- outputs -----------------------------------------------------------------


class PriceOutputs(ModelOutputs):
    calculation: Literal["price"] = Field(
        "price", description="Price, Greeks and the put-call parity residual"
    )
    price: Money = Field(ge=0.0, le=MONEY_OUT, description="Option price")
    delta: Ratio = Field(
        ge=-DELTA_MAX, le=DELTA_MAX, description="Change in price per unit of spot"
    )
    gamma: Ratio = Field(
        ge=0.0, le=GAMMA_MAX, description="Change in delta per unit of spot"
    )
    vega: Money = Field(
        ge=0.0, le=MONEY_OUT, description="Change in price per 1.00 of volatility"
    )
    theta: Money = _money("Change in price per year that passes")
    rho: Money = _money("Change in price per 1.00 of the risk-free rate")
    dividend_rho: Money = _money("Change in price per 1.00 of the dividend yield")
    put_call_parity_residual: Money = _money(
        "Call less put less (S e^-qT - K e^-rT): zero up to rounding"
    )


class ImpliedVolatilityOutputs(ModelOutputs):
    calculation: Literal["implied_volatility"] = Field(
        "implied_volatility", description="Volatility implied by a price"
    )
    implied_volatility: Volatility | None = Field(
        ge=VOL_MIN,
        le=VOL_MAX,
        description=(
            "Volatility whose price is the price given; null when the price is "
            "outside the no-arbitrage bounds or the solver's range"
        ),
    )
    lower_bound: Money = Field(
        ge=0.0, le=MONEY_OUT, description="No-arbitrage lower bound on the price"
    )
    upper_bound: Money = Field(
        ge=0.0, le=MONEY_OUT, description="No-arbitrage upper bound on the price"
    )


BlackScholesMertonOutputs = Annotated[
    PriceOutputs | ImpliedVolatilityOutputs, Field(discriminator="calculation")
]


# --- calculations ------------------------------------------------------------


def _price(inputs: PriceInputs) -> PriceOutputs:
    args = (
        inputs.spot,
        inputs.strike,
        inputs.years,
        inputs.risk_free_rate,
        inputs.dividend_yield,
        inputs.volatility,
    )
    greeks = black_scholes(inputs.option_type, *args)
    call, put = black_scholes("call", *args).price, black_scholes("put", *args).price
    forward_gap = inputs.spot * math.exp(
        -inputs.dividend_yield * inputs.years
    ) - inputs.strike * math.exp(-inputs.risk_free_rate * inputs.years)
    return PriceOutputs(
        price=greeks.price,
        delta=greeks.delta,
        gamma=greeks.gamma,
        vega=greeks.vega,
        theta=greeks.theta,
        rho=greeks.rho,
        dividend_rho=greeks.yield_rho,
        put_call_parity_residual=call - put - forward_gap,
    )


def _implied_volatility(inputs: ImpliedVolatilityInputs) -> ImpliedVolatilityOutputs:
    args = (
        inputs.spot,
        inputs.strike,
        inputs.years,
        inputs.risk_free_rate,
        inputs.dividend_yield,
    )
    low, high = no_arbitrage_bounds(inputs.option_type, *args)
    return ImpliedVolatilityOutputs(
        implied_volatility=implied_volatility(
            inputs.option_type, inputs.option_price, *args
        ),
        lower_bound=low,
        upper_bound=high,
    )


# --- the model ---------------------------------------------------------------

_BLACK_SCHOLES = Reference(
    key="black1973",
    citation=(
        "Black, F. and Scholes, M. (1973). The Pricing of Options and Corporate "
        "Liabilities. Journal of Political Economy, 81(3), 637-654."
    ),
    doi="10.1086/260062",
    locator="Equation (13), the value of a European call",
)
_MERTON = Reference(
    key="merton1973",
    citation=(
        "Merton, R. C. (1973). Theory of Rational Option Pricing. The Bell "
        "Journal of Economics and Management Science, 4(1), 141-183."
    ),
    doi="10.2307/3003143",
    locator="The extension of the call formula to a continuous dividend yield",
)
_HULL = Reference(
    key="hull2018",
    citation=(
        "Hull, J. C. (2018). Options, Futures, and Other Derivatives, 10th ed. Pearson."
    ),
    url="https://openlibrary.org/isbn/9780134472089",
    isbn="9780134472089",
    locator=(
        "Chapters 15, 17 and 19 (the Black-Scholes-Merton model, options on "
        "assets with a dividend yield, the Greek letters)"
    ),
)


@model(
    id="derivatives.black_scholes_merton",
    version=1,
    title="Black-Scholes-Merton options",
    summary=(
        "Price, Greeks and implied volatility of European calls and puts on an "
        "asset with a continuous dividend yield."
    ),
    formula=(
        (
            r"d_1 = \frac{\ln(S/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}, "
            r"\quad d_2 = d_1 - \sigma\sqrt{T}"
        ),
        r"c = S e^{-qT} N(d_1) - K e^{-rT} N(d_2)",
        r"p = K e^{-rT} N(-d_2) - S e^{-qT} N(-d_1)",
        r"c - p = S e^{-qT} - K e^{-rT}",
        (
            r"\Delta_c = e^{-qT} N(d_1), \quad "
            r"\Gamma = \frac{e^{-qT} n(d_1)}{S \sigma \sqrt{T}}, \quad "
            r"\nu = S e^{-qT} n(d_1) \sqrt{T}"
        ),
    ),
    assumptions=(
        (
            "The asset's price follows geometric Brownian motion with a constant "
            "volatility, and pays a continuous dividend yield."
        ),
        (
            "The risk-free rate is constant and continuously compounded; trading "
            "is continuous, frictionless and free of arbitrage."
        ),
        "The option is European: it can be exercised only at expiry.",
        (
            "Greeks are per unit: vega and the rhos per 1.00 of volatility or "
            "rate, theta per year of calendar time."
        ),
    ),
    limitations=(
        (
            "Results are the formula's outputs for the inputs given, not a "
            "valuation of a traded contract or trading advice."
        ),
        (
            "A constant volatility ignores the smile and skew of traded options; "
            "an implied volatility is the one number that reproduces one price."
        ),
        (
            "The implied volatility is searched for in [0.001, 5]; a price outside "
            "the no-arbitrage bounds, or one only a volatility outside that range "
            "gives, returns null with a warning."
        ),
        "American exercise is out of scope (derivatives.binomial_tree prices it).",
    ),
    references=(_BLACK_SCHOLES, _MERTON, _HULL),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("options", "black-scholes", "greeks", "implied volatility", "dividends"),
    invariants=(
        Invariant(
            id="put_call_parity",
            statement="A call less a put with the same terms is S e^-qT - K e^-rT.",
        ),
        Invariant(
            id="price_within_no_arbitrage_bounds",
            statement=(
                "A call is worth between max(S e^-qT - K e^-rT, 0) and S e^-qT, "
                "a put between max(K e^-rT - S e^-qT, 0) and K e^-rT."
            ),
        ),
        Invariant(
            id="gamma_and_vega_nonnegative",
            statement="Gamma and vega are never negative.",
        ),
        Invariant(
            id="call_increases_with_spot",
            statement="A call's price does not fall as the spot price rises.",
        ),
        Invariant(
            id="implied_volatility_round_trip",
            statement=(
                "Solving for the volatility of a price computed at a volatility in "
                "the solver's range gives that volatility back, wherever the price "
                "moves with volatility."
            ),
        ),
    ),
    examples=(
        Example(
            name="six_month_call",
            inputs={
                "calculation": "price",
                "spot": 42,
                "strike": 40,
                "years": 0.5,
                "risk_free_rate": 0.10,
                "volatility": 0.20,
            },
        ),
        Example(
            name="index_put_with_dividend_yield",
            inputs={
                "calculation": "price",
                "option_type": "put",
                "spot": 100,
                "strike": 95,
                "years": 0.5,
                "risk_free_rate": 0.10,
                "dividend_yield": 0.05,
                "volatility": 0.20,
            },
        ),
        Example(
            name="implied_volatility_of_a_call",
            inputs={
                "calculation": "implied_volatility",
                "option_price": 1.875,
                "spot": 21,
                "strike": 20,
                "years": 0.25,
                "risk_free_rate": 0.10,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def black_scholes_merton(
    inputs: BlackScholesMertonInputs,
) -> BlackScholesMertonOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[ModelInputs], Callable[[Any], BlackScholesMertonOutputs]]
] = {
    PriceInputs: _price,
    ImpliedVolatilityInputs: _implied_volatility,
}
