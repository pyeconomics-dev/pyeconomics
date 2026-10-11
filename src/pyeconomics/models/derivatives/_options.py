# src/pyeconomics/models/derivatives/_options.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""European option prices, Greeks and implied volatility: what the option models share.

One closed form covers the three lognormal models of the catalog. With an
underlying :math:`S` that pays a continuous yield :math:`q`, a strike :math:`K`,
a time to expiry :math:`T`, a continuously compounded rate :math:`r` and a
volatility :math:`\sigma`,

.. math::

    d_1 = \frac{\ln(S/K) + (r - q + \sigma^2/2) T}{\sigma\sqrt{T}}, \quad
    d_2 = d_1 - \sigma\sqrt{T},

    c = S e^{-qT} N(d_1) - K e^{-rT} N(d_2), \quad
    p = K e^{-rT} N(-d_2) - S e^{-qT} N(-d_1).

Black and Scholes (1973) is :math:`q = 0`; Merton (1973) adds the dividend
yield; Black (1976) prices an option on a forward or futures price :math:`F` as
:math:`S = F`, :math:`q = r`; Garman and Kohlhagen (1983) price a currency
option with the foreign rate as :math:`q`. The Greeks are the partial
derivatives of the price: delta and gamma in the underlying, vega in the
volatility, theta in calendar time (the negative of the derivative in
:math:`T`), rho in :math:`r` and the yield rho in :math:`q`, each per unit
(per 1.00 of volatility or rate, per year of time). Nothing here does I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final, Literal

from pydantic import Field

from pyeconomics.core import DomainError, find_root, warn

__all__ = [
    "DELTA_MAX",
    "GAMMA_MAX",
    "MONEY_OUT",
    "PRICE_IN_MAX",
    "RATE_MAX",
    "RATE_MIN",
    "VOL_MAX",
    "VOL_MIN",
    "YEARS_MAX",
    "YEARS_MIN",
    "Greeks",
    "OptionType",
    "black_scholes",
    "bounded",
    "implied_volatility",
    "no_arbitrage_bounds",
    "option_type",
]

type OptionType = Literal["call", "put"]

#: The volatilities a model prices at and an implied volatility is solved over.
VOL_MIN: Final = 0.001
VOL_MAX: Final = 5.0
#: The time to expiry: about nine hours to a century.
YEARS_MIN: Final = 0.001
YEARS_MAX: Final = 100.0
#: Continuously compounded rates and yields. The lower end keeps e^(-rT) at
#: most e^10 over a century.
RATE_MIN: Final = -0.1
RATE_MAX: Final = 1.0
#: The largest option price an implied-volatility input takes.
PRICE_IN_MAX: Final = 1e12
#: The bound on every money output. With an underlying and strike of at most
#: 1e7 and discounting of at most e^10, prices stay below 2.3e11, vega below
#: 9e11, rho below 2.3e13 and theta below 5e10.
MONEY_OUT: Final = 1e15
#: |delta| is at most e^(-qT) <= e^10.
DELTA_MAX: Final = 1e5
#: Gamma, e^(-qT) n(d1) / (S sigma sqrt(T)), grows as the underlying, the
#: volatility and the time shrink: at most 879 / (S sigma) over the input
#: ranges, 8.8e9 for a currency at 1e-4 and a volatility of 0.001. The bound is
#: wider than a ratio's default of 1e6 for that reason (ADR-0008 decision 3).
GAMMA_MAX: Final = 1e12

_SQRT_2: Final = math.sqrt(2.0)
_SQRT_2PI: Final = math.sqrt(2.0 * math.pi)


def _cdf(x: float) -> float:
    """Return the standard normal distribution function, accurate in both tails."""
    return 0.5 * math.erfc(-x / _SQRT_2)


def _pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def option_type() -> Any:  # noqa: ANN401 - pydantic's Field
    """Return the ``option_type`` field every option input shares."""
    return Field("call", description="A call (the right to buy) or a put (to sell)")


def bounded(value: float, low: float, high: float, what: str) -> float:
    """Return ``value`` if it is finite and within ``[low, high]``.

    Raises
    ------
    DomainError
        Otherwise, naming the output and its bounds.

    """
    if not (math.isfinite(value) and low <= value <= high):
        msg = (
            f"the {what} is {value!r}, outside its bounds [{low:g}, {high:g}]; "
            "the inputs have no answer this model can represent"
        )
        raise DomainError(msg)
    return value


@dataclass(frozen=True, slots=True)
class Greeks:
    """A European option's price and its sensitivities, each per unit."""

    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    """The derivative in the discount rate ``r``."""
    yield_rho: float
    """The derivative in the yield ``q`` (dividend yield or foreign rate)."""


def black_scholes(  # noqa: PLR0913, PLR0917 - the closed form's six inputs and its kind
    kind: OptionType,
    spot: float,
    strike: float,
    years: float,
    rate: float,
    yield_: float,
    volatility: float,
) -> Greeks:
    """Return the price and Greeks of a European option (module docstring)."""
    root_t = math.sqrt(years)
    deviation = volatility * root_t
    d1 = (math.log(spot / strike) + (rate - yield_ + 0.5 * volatility**2) * years) / (
        deviation
    )
    d2 = d1 - deviation
    carry = math.exp(-yield_ * years)
    discount = math.exp(-rate * years)
    density = _pdf(d1)
    gamma = carry * density / (spot * deviation)
    vega = spot * carry * density * root_t
    decay = -spot * carry * density * volatility / (2.0 * root_t)
    if kind == "call":
        n1, n2 = _cdf(d1), _cdf(d2)
        price = spot * carry * n1 - strike * discount * n2
        delta = carry * n1
        theta = decay - rate * strike * discount * n2 + yield_ * spot * carry * n1
        rho = strike * years * discount * n2
        yield_rho = -spot * years * carry * n1
    else:
        n1, n2 = _cdf(-d1), _cdf(-d2)
        price = strike * discount * n2 - spot * carry * n1
        delta = -carry * n1
        theta = decay + rate * strike * discount * n2 - yield_ * spot * carry * n1
        rho = -strike * years * discount * n2
        yield_rho = spot * years * carry * n1
    return Greeks(
        # The difference of two terms can round a few ulps below zero.
        price=max(price, 0.0),
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta=theta,
        rho=rho,
        yield_rho=yield_rho,
    )


def no_arbitrage_bounds(  # noqa: PLR0913, PLR0917 - the closed form's inputs but volatility
    kind: OptionType,
    spot: float,
    strike: float,
    years: float,
    rate: float,
    yield_: float,
) -> tuple[float, float]:
    """Return the prices a European option must lie strictly between.

    A call is worth more than ``max(S e^-qT - K e^-rT, 0)`` and less than
    ``S e^-qT``; a put more than ``max(K e^-rT - S e^-qT, 0)`` and less than
    ``K e^-rT``. The ends are the limits as the volatility goes to zero and to
    infinity.
    """
    asset = spot * math.exp(-yield_ * years)
    cash = strike * math.exp(-rate * years)
    if kind == "call":
        return max(asset - cash, 0.0), asset
    return max(cash - asset, 0.0), cash


def implied_volatility(  # noqa: PLR0913, PLR0917 - the closed form's inputs and a price
    kind: OptionType,
    price: float,
    spot: float,
    strike: float,
    years: float,
    rate: float,
    yield_: float,
) -> float | None:
    """Return the volatility in ``[VOL_MIN, VOL_MAX]`` whose price is ``price``.

    The price rises with the volatility, so there is at most one root. It is
    found with :func:`~pyeconomics.core.find_root` (a 64-point scan, then at
    most 100 iterations of Brent's method) on the bounded range.

    Warns
    -----
    ModelWarning
        ``price_outside_no_arbitrage_bounds`` when the price is not strictly
        between the bounds of :func:`no_arbitrage_bounds`, and
        ``implied_volatility_out_of_range`` when it is but the volatility
        that gives it is below ``VOL_MIN`` or above ``VOL_MAX``; the result is
        then ``None``.

    """
    low, high = no_arbitrage_bounds(kind, spot, strike, years, rate, yield_)
    if not low < price < high:
        warn(
            "price_outside_no_arbitrage_bounds",
            f"the price {price!r} is not strictly between the no-arbitrage bounds "
            f"{low!r} and {high!r}, so no volatility gives it",
            stacklevel=3,
        )
        return None

    def gap(volatility: float) -> float:
        return (
            black_scholes(kind, spot, strike, years, rate, yield_, volatility).price
            - price
        )

    below, above = gap(VOL_MIN), gap(VOL_MAX)
    # A price within rounding of the price at an end of the range is that end:
    # a volatility a hair inside it can round to a price just beyond.
    slack = 1e-13 * high
    if 0 < below <= slack:
        return VOL_MIN
    if 0 < -above <= slack:
        return VOL_MAX
    if below > 0 or above < 0:
        side = "below" if below > 0 else "above"
        warn(
            "implied_volatility_out_of_range",
            f"the volatility that gives the price {price!r} is {side} the range "
            f"[{VOL_MIN}, {VOL_MAX}] the solver searches",
            stacklevel=3,
        )
        return None
    return find_root(gap, VOL_MIN, VOL_MAX).root
