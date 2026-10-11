# src/pyeconomics/models/derivatives/binomial_tree.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""European and American options on a binomial tree: ``derivatives.binomial_tree``.

The life of the option is cut into :math:`n` steps of :math:`\Delta t = T / n`.
Each step the price moves up by :math:`u = e^{\sigma\sqrt{\Delta t}}` or down by
:math:`d = 1/u`, with the risk-neutral probability of a move up

.. math:: p = \frac{e^{(r - q)\Delta t} - d}{u - d},

so the expected price grows at :math:`r - q` (Cox, Ross and Rubinstein, 1979).
The option is worth its payoff at expiry and, one step back at a time, the
discounted expectation :math:`e^{-r\Delta t}[p V_u + (1 - p) V_d]`; an American
option is worth the larger of that and its payoff now. Delta and gamma are the
tree's own differences at the first and second steps. The outputs are the
tree's values for the inputs given, not trading advice.
"""

from __future__ import annotations

import math
from typing import Final, Literal

import numpy as np
from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Probability,
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
    RATE_MAX,
    RATE_MIN,
    VOL_MAX,
    YEARS_MAX,
    YEARS_MIN,
    OptionType,
    option_type,
)

__all__ = ["binomial_tree"]

#: The underlying's price and the strike.
_PRICE_MIN: Final = 0.01
_PRICE_MAX: Final = 1e7
#: The lowest volatility a tree takes.
_VOL_MIN: Final = 0.01
#: The most steps: about 12.5 million node values, well under a second.
_STEPS_MAX: Final = 5_000
#: The largest exponent of a node's price: e^700 is near a double's limit.
_EXPONENT_MAX: Final = 700.0
#: Up factors run from e^(0.01 sqrt(0.001 / 5000)) to e^(5 sqrt(100 / 2)).
_UP_MAX: Final = 1e16


class BinomialTreeInputs(ModelInputs):
    # No docstring: the input schema's description is the model's summary.
    option_type: OptionType = option_type()
    exercise: Literal["european", "american"] = Field(
        "american",
        description="European (at expiry only) or American (at any step) exercise",
    )
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
    volatility: Volatility = Field(
        ge=_VOL_MIN, le=VOL_MAX, description="Volatility of the asset's return per year"
    )
    steps: Count = Field(
        100, ge=2, le=_STEPS_MAX, description="Number of time steps in the tree"
    )


class BinomialTreeOutputs(ModelOutputs):
    price: Money = Field(ge=0.0, le=MONEY_OUT, description="Option price")
    delta: Ratio = Field(
        ge=-DELTA_MAX,
        le=DELTA_MAX,
        description="Change in price per unit of spot, across the first step",
    )
    gamma: Ratio = Field(
        ge=-GAMMA_MAX,
        le=GAMMA_MAX,
        description="Change in delta per unit of spot, across the second step",
    )
    up_factor: Ratio = Field(
        gt=1.0, le=_UP_MAX, description="Price ratio of a move up: e^(sigma sqrt(dt))"
    )
    up_probability: Probability = Field(
        gt=0.0, lt=1.0, description="Risk-neutral probability of a move up"
    )


def _payoff(kind: OptionType, prices: np.ndarray, strike: float) -> np.ndarray:
    if kind == "call":
        return np.maximum(prices - strike, 0.0)
    return np.maximum(strike - prices, 0.0)


def _tree(inputs: BinomialTreeInputs) -> BinomialTreeOutputs:
    n = inputs.steps
    dt = inputs.years / n
    jump = inputs.volatility * math.sqrt(dt)
    if math.log(inputs.spot) + n * jump > _EXPONENT_MAX:
        msg = (
            f"the tree's top node, e^{n * jump:.0f} times the spot, overflows; "
            "use fewer steps, or a shorter or less volatile option"
        )
        raise DomainError(msg)
    growth = math.expm1((inputs.risk_free_rate - inputs.dividend_yield) * dt)
    # p = (e^(b dt) - d) / (u - d), formed from expm1 so a tiny step keeps its digits.
    p = (growth - math.expm1(-jump)) / (math.expm1(jump) - math.expm1(-jump))
    if not 0.0 < p < 1.0:
        msg = (
            f"the up-probability is {p!r}, outside (0, 1): the drift "
            f"{inputs.risk_free_rate - inputs.dividend_yield:g} per year outruns "
            "the volatility over a step, so the tree admits arbitrage; use more steps"
        )
        raise DomainError(msg)
    discount = math.exp(-inputs.risk_free_rate * dt)
    up, down = discount * p, discount * (1.0 - p)
    # Node j of step i (j = 0 at the bottom) is S u^(2j - i): every power from
    # -n to n, read with a stride of two.
    prices = inputs.spot * np.exp(jump * np.arange(-n, n + 1, dtype=float))
    values = _payoff(inputs.option_type, prices[::2], inputs.strike)
    american = inputs.exercise == "american"
    # The first two steps carry delta and gamma; with two steps, the second is expiry.
    kept: dict[int, np.ndarray] = {n: values}
    for step in range(n - 1, -1, -1):
        values = up * values[1:] + down * values[:-1]
        if american:
            nodes = prices[n - step : n + step + 1 : 2]
            values = np.maximum(
                values, _payoff(inputs.option_type, nodes, inputs.strike)
            )
        if step <= 2:  # noqa: PLR2004 - the steps delta and gamma read
            kept[step] = values
    s1 = prices[n - 1 : n + 2 : 2]
    s2 = prices[n - 2 : n + 3 : 2]
    v1, v2 = kept[1], kept[2]
    delta = float((v1[1] - v1[0]) / (s1[1] - s1[0]))
    delta_up = (v2[2] - v2[1]) / (s2[2] - s2[1])
    delta_down = (v2[1] - v2[0]) / (s2[1] - s2[0])
    gamma = float((delta_up - delta_down) / (0.5 * (s2[2] - s2[0])))
    return BinomialTreeOutputs(
        price=float(kept[0][0]),
        delta=delta,
        gamma=gamma,
        up_factor=math.exp(jump),
        up_probability=p,
    )


_CRR = Reference(
    key="cox1979",
    citation=(
        "Cox, J. C., Ross, S. A. and Rubinstein, M. (1979). Option Pricing: A "
        "Simplified Approach. Journal of Financial Economics, 7(3), 229-263."
    ),
    doi="10.1016/0304-405X(79)90015-1",
    locator=(
        "The multiplicative binomial model, its risk-neutral probability and the "
        "limit u = e^(sigma sqrt(dt))"
    ),
)
_HULL = Reference(
    key="hull2018",
    citation=(
        "Hull, J. C. (2018). Options, Futures, and Other Derivatives, 10th ed. Pearson."
    ),
    url="https://openlibrary.org/isbn/9780134472089",
    isbn="9780134472089",
    locator=(
        "Chapters 13 and 21 (binomial trees; the five-step American put and its "
        "delta and gamma from the tree)"
    ),
)


@model(
    id="derivatives.binomial_tree",
    version=1,
    title="Binomial option tree",
    summary=(
        "Cox-Ross-Rubinstein binomial prices of European and American calls and "
        "puts with a dividend yield, with delta and gamma from the tree."
    ),
    formula=(
        (
            r"u = e^{\sigma\sqrt{\Delta t}}, \quad d = 1/u, \quad "
            r"p = \frac{e^{(r - q)\Delta t} - d}{u - d}"
        ),
        r"V_{i,j} = e^{-r\Delta t}\left[p V_{i+1,j+1} + (1 - p) V_{i+1,j}\right]",
        r"V_{i,j}^{American} = \max\left(V_{i,j}, \text{payoff}(S u^{2j - i})\right)",
        (
            r"\Delta = \frac{V_{1,1} - V_{1,0}}{S u - S d}, \quad \Gamma = "
            r"\frac{\Delta_{2,up} - \Delta_{2,down}}{(S u^2 - S d^2)/2}"
        ),
    ),
    assumptions=(
        (
            "The asset's price moves up by u or down by d = 1/u each step; in the "
            "limit of many steps it follows geometric Brownian motion."
        ),
        (
            "The risk-free rate, dividend yield and volatility are constant; rates "
            "and the yield are continuously compounded."
        ),
        "An American option may be exercised at any node, the first included.",
    ),
    limitations=(
        (
            "Results are the tree's outputs for the inputs given, not a valuation "
            "of a traded contract or trading advice."
        ),
        (
            "The price converges to the continuous-time value as the steps grow, "
            "with an error that oscillates; it is not exact for any finite tree."
        ),
        (
            "A drift r - q that outruns the volatility over a step puts the "
            "up-probability outside (0, 1), and a top node above e^700 overflows; "
            "both raise DomainError."
        ),
        "Discrete dividends and time-varying rates or volatility are out of scope.",
    ),
    references=(_CRR, _HULL),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    tags=("options", "binomial tree", "american options", "cox-ross-rubinstein"),
    invariants=(
        Invariant(
            id="american_put_at_least_european",
            statement="An American put is worth at least the European put.",
        ),
        Invariant(
            id="american_call_equals_european_without_dividends",
            statement=(
                "With no dividend yield and a rate of zero or more, an American "
                "call is worth the same as the European call."
            ),
        ),
        Invariant(
            id="european_parity_holds",
            statement=(
                "On the same tree, a European call less a European put is "
                "S e^-qT - K e^-rT."
            ),
        ),
        Invariant(
            id="converges_to_black_scholes",
            statement=(
                "As the steps grow, a European price approaches the "
                "Black-Scholes-Merton price, its error falling."
            ),
        ),
    ),
    examples=(
        Example(
            name="five_step_american_put",
            inputs={
                "option_type": "put",
                "spot": 50,
                "strike": 50,
                "years": 0.4167,
                "risk_free_rate": 0.10,
                "volatility": 0.40,
                "steps": 5,
            },
        ),
        Example(
            name="american_call_with_dividend_yield",
            inputs={
                "option_type": "call",
                "spot": 100,
                "strike": 100,
                "years": 1.0,
                "risk_free_rate": 0.05,
                "dividend_yield": 0.06,
                "volatility": 0.25,
                "steps": 500,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def binomial_tree(inputs: BinomialTreeInputs) -> BinomialTreeOutputs:
    """Price the option on the tree."""
    return _tree(inputs)
