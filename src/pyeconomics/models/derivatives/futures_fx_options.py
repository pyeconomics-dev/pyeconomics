# src/pyeconomics/models/derivatives/futures_fx_options.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Options on futures and on currencies: ``derivatives.futures_fx_options``.

Four calculations, discriminated on ``calculation``:

- ``black_76``: Black's (1976) price and Greeks of a European option on a
  futures or forward price;
- ``black_76_implied_volatility``: the volatility whose Black-76 price is a
  given price;
- ``garman_kohlhagen``: Garman and Kohlhagen's (1983) price and Greeks of a
  European currency option, with a rho for each currency's rate;
- ``garman_kohlhagen_implied_volatility``: the volatility whose
  Garman-Kohlhagen price is a given price.

Both are the Black-Scholes-Merton closed form with a yield: the futures price
grows at no cost of carry (the yield is the risk-free rate), and a currency
yields its own (foreign) interest rate. An exchange rate is in units of the
quote (domestic) currency per unit of the base (foreign) currency, and a
currency option's price in units of the quote currency per unit of the base.
Rates are continuously compounded decimals per year; Greeks are per unit. The
outputs are the formula's values for the inputs given, not trading advice.
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

__all__ = ["futures_fx_options"]

#: A futures price and its strike.
_PRICE_MIN: Final = 0.01
_PRICE_MAX: Final = 1e7
#: An exchange rate and its strike, quote currency per unit of base currency.
_FX_MIN: Final = 1e-4
_FX_MAX: Final = 1e6

_FX = "units of the quote (domestic) currency per unit of the base (foreign) currency"


def _money(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-MONEY_OUT, le=MONEY_OUT, description=description)


def _years() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=YEARS_MIN, le=YEARS_MAX, description="Time to expiry, in years")


def _rate(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=RATE_MIN, le=RATE_MAX, description=description)


def _volatility(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=VOL_MIN, le=VOL_MAX, description=description)


def _option_price() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=PRICE_IN_MAX, description="The option's price")


# --- inputs ------------------------------------------------------------------


class _Futures(ModelInputs):
    option_type: OptionType = option_type()
    futures_price: Money = Field(
        ge=_PRICE_MIN,
        le=_PRICE_MAX,
        description="Futures or forward price for delivery at expiry",
    )
    strike: Money = Field(ge=_PRICE_MIN, le=_PRICE_MAX, description="Strike price")
    years: Years = _years()
    risk_free_rate: Rate = _rate("Risk-free rate per year, continuously compounded")


class Black76Inputs(_Futures):
    """A European option on a futures price, and its volatility."""

    calculation: Literal["black_76"] = Field(
        "black_76", description="Black-76 price and Greeks"
    )
    volatility: Volatility = _volatility("Volatility of the futures price per year")


class Black76ImpliedInputs(_Futures):
    """A European option on a futures price, and its price."""

    calculation: Literal["black_76_implied_volatility"] = Field(
        "black_76_implied_volatility",
        description="Volatility implied by a Black-76 price",
    )
    option_price: Money = _option_price()


class _Currency(ModelInputs):
    option_type: OptionType = option_type()
    spot: Ratio = Field(
        ge=_FX_MIN, le=_FX_MAX, description=f"Spot exchange rate, in {_FX}"
    )
    strike: Ratio = Field(
        ge=_FX_MIN, le=_FX_MAX, description=f"Strike exchange rate, in {_FX}"
    )
    years: Years = _years()
    domestic_rate: Rate = _rate(
        "Interest rate of the quote (domestic) currency, continuously compounded"
    )
    foreign_rate: Rate = _rate(
        "Interest rate of the base (foreign) currency, continuously compounded"
    )


class GarmanKohlhagenInputs(_Currency):
    """A European currency option, and its volatility."""

    calculation: Literal["garman_kohlhagen"] = Field(
        "garman_kohlhagen", description="Garman-Kohlhagen price and Greeks"
    )
    volatility: Volatility = _volatility("Volatility of the exchange rate per year")


class GarmanKohlhagenImpliedInputs(_Currency):
    """A European currency option, and its price."""

    calculation: Literal["garman_kohlhagen_implied_volatility"] = Field(
        "garman_kohlhagen_implied_volatility",
        description="Volatility implied by a Garman-Kohlhagen price",
    )
    option_price: Money = Field(
        ge=0.0,
        le=PRICE_IN_MAX,
        description="The option's price, in the quote currency per unit of base",
    )


FuturesFxOptionsInputs = Annotated[
    Black76Inputs
    | Black76ImpliedInputs
    | GarmanKohlhagenInputs
    | GarmanKohlhagenImpliedInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


def _price() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=MONEY_OUT, description="Option price")


def _delta(what: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=-DELTA_MAX, le=DELTA_MAX, description=f"Change in price per unit of {what}"
    )


def _gamma(what: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=0.0, le=GAMMA_MAX, description=f"Change in delta per unit of {what}"
    )


def _vega() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=0.0, le=MONEY_OUT, description="Change in price per 1.00 of volatility"
    )


class Black76Outputs(ModelOutputs):
    calculation: Literal["black_76"] = Field(
        "black_76", description="Black-76 price and Greeks"
    )
    price: Money = _price()
    delta: Ratio = _delta("the futures price")
    gamma: Ratio = _gamma("the futures price")
    vega: Money = _vega()
    theta: Money = _money("Change in price per year that passes")
    rho: Money = _money(
        "Change in price per 1.00 of the risk-free rate, the futures price fixed"
    )


class _ImpliedOutputs(ModelOutputs):
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


class Black76ImpliedOutputs(_ImpliedOutputs):
    calculation: Literal["black_76_implied_volatility"] = Field(
        "black_76_implied_volatility",
        description="Volatility implied by a Black-76 price",
    )


class GarmanKohlhagenOutputs(ModelOutputs):
    calculation: Literal["garman_kohlhagen"] = Field(
        "garman_kohlhagen", description="Garman-Kohlhagen price and Greeks"
    )
    price: Money = Field(
        ge=0.0,
        le=MONEY_OUT,
        description="Option price, in the quote currency per unit of base",
    )
    delta: Ratio = _delta("the spot rate")
    gamma: Ratio = _gamma("the spot rate")
    vega: Money = _vega()
    theta: Money = _money("Change in price per year that passes")
    domestic_rho: Money = _money("Change in price per 1.00 of the domestic rate")
    foreign_rho: Money = _money("Change in price per 1.00 of the foreign rate")


class GarmanKohlhagenImpliedOutputs(_ImpliedOutputs):
    calculation: Literal["garman_kohlhagen_implied_volatility"] = Field(
        "garman_kohlhagen_implied_volatility",
        description="Volatility implied by a Garman-Kohlhagen price",
    )


FuturesFxOptionsOutputs = Annotated[
    Black76Outputs
    | Black76ImpliedOutputs
    | GarmanKohlhagenOutputs
    | GarmanKohlhagenImpliedOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _black_76(inputs: Black76Inputs) -> Black76Outputs:
    # A futures price costs nothing to carry: the yield is the discount rate.
    rate = inputs.risk_free_rate
    greeks = black_scholes(
        inputs.option_type,
        inputs.futures_price,
        inputs.strike,
        inputs.years,
        rate,
        rate,
        inputs.volatility,
    )
    return Black76Outputs(
        price=greeks.price,
        delta=greeks.delta,
        gamma=greeks.gamma,
        vega=greeks.vega,
        theta=greeks.theta,
        # With F fixed, the price is e^-rT times a function of F: d/dr = -T price.
        rho=-inputs.years * greeks.price,
    )


def _black_76_implied(inputs: Black76ImpliedInputs) -> Black76ImpliedOutputs:
    args = (
        inputs.futures_price,
        inputs.strike,
        inputs.years,
        inputs.risk_free_rate,
        inputs.risk_free_rate,
    )
    low, high = no_arbitrage_bounds(inputs.option_type, *args)
    return Black76ImpliedOutputs(
        implied_volatility=implied_volatility(
            inputs.option_type, inputs.option_price, *args
        ),
        lower_bound=low,
        upper_bound=high,
    )


def _garman_kohlhagen(inputs: GarmanKohlhagenInputs) -> GarmanKohlhagenOutputs:
    greeks = black_scholes(
        inputs.option_type,
        inputs.spot,
        inputs.strike,
        inputs.years,
        inputs.domestic_rate,
        inputs.foreign_rate,
        inputs.volatility,
    )
    return GarmanKohlhagenOutputs(
        price=greeks.price,
        delta=greeks.delta,
        gamma=greeks.gamma,
        vega=greeks.vega,
        theta=greeks.theta,
        domestic_rho=greeks.rho,
        foreign_rho=greeks.yield_rho,
    )


def _garman_kohlhagen_implied(
    inputs: GarmanKohlhagenImpliedInputs,
) -> GarmanKohlhagenImpliedOutputs:
    args = (
        inputs.spot,
        inputs.strike,
        inputs.years,
        inputs.domestic_rate,
        inputs.foreign_rate,
    )
    low, high = no_arbitrage_bounds(inputs.option_type, *args)
    return GarmanKohlhagenImpliedOutputs(
        implied_volatility=implied_volatility(
            inputs.option_type, inputs.option_price, *args
        ),
        lower_bound=low,
        upper_bound=high,
    )


# --- the model ---------------------------------------------------------------

_BLACK = Reference(
    key="black1976",
    citation=(
        "Black, F. (1976). The Pricing of Commodity Contracts. Journal of "
        "Financial Economics, 3(1-2), 167-179."
    ),
    doi="10.1016/0304-405X(76)90024-6",
    locator="The closed-form value of a European option on a futures contract",
)
_GARMAN_KOHLHAGEN = Reference(
    key="garman1983",
    citation=(
        "Garman, M. B. and Kohlhagen, S. W. (1983). Foreign Currency Option "
        "Values. Journal of International Money and Finance, 2(3), 231-237."
    ),
    doi="10.1016/S0261-5606(83)80001-1",
    locator="The closed-form values of European currency calls and puts",
)
_HULL = Reference(
    key="hull2018",
    citation=(
        "Hull, J. C. (2018). Options, Futures, and Other Derivatives, 10th ed. Pearson."
    ),
    url="https://openlibrary.org/isbn/9780134472089",
    isbn="9780134472089",
    locator="Chapters 17 and 18 (currency options; Black's model for futures options)",
)


@model(
    id="derivatives.futures_fx_options",
    version=1,
    title="Futures and currency options",
    summary=(
        "Black-76 prices of options on futures and Garman-Kohlhagen prices of "
        "currency options, with Greeks and implied volatilities."
    ),
    formula=(
        (
            r"d_1 = \frac{\ln(F/K) + \sigma^2 T/2}{\sigma\sqrt{T}}, \quad "
            r"c = e^{-rT}\left[F N(d_1) - K N(d_2)\right]"
        ),
        r"p = e^{-rT}\left[K N(-d_2) - F N(-d_1)\right]",
        (
            r"d_1 = \frac{\ln(S/K) + (r_d - r_f + \sigma^2/2)T}{\sigma\sqrt{T}}, "
            r"\quad c = S e^{-r_f T} N(d_1) - K e^{-r_d T} N(d_2)"
        ),
        r"p = K e^{-r_d T} N(-d_2) - S e^{-r_f T} N(-d_1)",
    ),
    assumptions=(
        (
            "The futures price, or the exchange rate, follows geometric Brownian "
            "motion with a constant volatility."
        ),
        (
            "Rates are constant and continuously compounded; a currency earns its "
            "own risk-free rate; trading is frictionless and free of arbitrage."
        ),
        (
            "Options are European. A Black-76 option expires with the futures "
            "contract, or the futures is treated as a forward."
        ),
        (
            "Greeks are per unit: vega and the rhos per 1.00 of volatility or "
            "rate, theta per year of calendar time. The Black-76 rho holds the "
            "futures price fixed."
        ),
    ),
    limitations=(
        (
            "Results are the formula's outputs for the inputs given, not a "
            "valuation of a traded contract or trading advice."
        ),
        (
            "A constant volatility ignores the smile; currency markets quote by "
            "delta and strangle conventions this model does not translate."
        ),
        (
            "The implied volatility is searched for in [0.001, 5]; a price outside "
            "the no-arbitrage bounds, or one only a volatility outside that range "
            "gives, returns null with a warning."
        ),
        "American options on futures are out of scope.",
    ),
    references=(_BLACK, _GARMAN_KOHLHAGEN, _HULL),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("options", "futures", "currency", "black-76", "garman-kohlhagen", "greeks"),
    invariants=(
        Invariant(
            id="black_76_equals_bsm_with_carry_zero",
            statement=(
                "A Black-76 price and its Greeks equal those of "
                "derivatives.black_scholes_merton with the futures price as spot "
                "and a dividend yield equal to the risk-free rate."
            ),
        ),
        Invariant(
            id="garman_kohlhagen_equals_bsm_with_foreign_yield",
            statement=(
                "A Garman-Kohlhagen price and its Greeks equal those of "
                "derivatives.black_scholes_merton with the foreign rate as the "
                "dividend yield."
            ),
        ),
        Invariant(
            id="put_call_parity",
            statement=(
                "A call less a put is e^-rT (F - K) on futures, and "
                "S e^-rf T - K e^-rd T on a currency."
            ),
        ),
    ),
    examples=(
        Example(
            name="futures_put",
            inputs={
                "calculation": "black_76",
                "option_type": "put",
                "futures_price": 20,
                "strike": 20,
                "years": 0.3333,
                "risk_free_rate": 0.09,
                "volatility": 0.25,
            },
        ),
        Example(
            name="futures_implied_volatility",
            inputs={
                "calculation": "black_76_implied_volatility",
                "option_price": 1.7011,
                "futures_price": 19,
                "strike": 19,
                "years": 0.75,
                "risk_free_rate": 0.10,
            },
        ),
        Example(
            name="currency_call",
            inputs={
                "calculation": "garman_kohlhagen",
                "spot": 1.08,
                "strike": 1.10,
                "years": 0.5,
                "domestic_rate": 0.045,
                "foreign_rate": 0.03,
                "volatility": 0.08,
            },
        ),
        Example(
            name="currency_implied_volatility",
            inputs={
                "calculation": "garman_kohlhagen_implied_volatility",
                "option_type": "put",
                "option_price": 0.02,
                "spot": 1.08,
                "strike": 1.10,
                "years": 0.5,
                "domestic_rate": 0.045,
                "foreign_rate": 0.03,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def futures_fx_options(inputs: FuturesFxOptionsInputs) -> FuturesFxOptionsOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[ModelInputs], Callable[[Any], FuturesFxOptionsOutputs]]
] = {
    Black76Inputs: _black_76,
    Black76ImpliedInputs: _black_76_implied,
    GarmanKohlhagenInputs: _garman_kohlhagen,
    GarmanKohlhagenImpliedInputs: _garman_kohlhagen_implied,
}
