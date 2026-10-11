# src/pyeconomics/models/derivatives/forwards.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Forward prices and values, and currency forwards: ``derivatives.forwards``.

Three calculations, discriminated on ``calculation``:

- ``cost_of_carry``: the forward price of an asset from its spot price and the
  cost of carrying it, :math:`F = (S - I + U)\,e^{(r - q + u - y)T}`, with an
  income yield :math:`q`, storage costs :math:`u` and a convenience yield
  :math:`y` per year (continuously compounded), and the present values
  :math:`I` of known income and :math:`U` of known storage costs;
- ``forward_value``: the value of a forward contract entered earlier at a
  delivery price :math:`K`, :math:`(F - K)\,e^{-rT}` to the long side and its
  negative to the short side;
- ``fx_forward``: the outright forward exchange rate by covered interest parity
  with money-market (simple) interest, each currency's rate on its own day count,
  :math:`F = S\,(1 + r_q\,d/B_q) / (1 + r_b\,d/B_b)`, and the forward points.

An exchange rate is in units of the quote currency per unit of the base
currency. The outputs are the formulas' values for the inputs given, not
trading advice.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Days,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Rate,
    Ratio,
    Reference,
    Return,
    Years,
    model,
)
from pyeconomics.models.derivatives._options import MONEY_OUT, bounded

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["forwards"]

#: The largest spot price, present value of income or storage, and delivery price.
_MONEY_IN: Final = 1e9
#: The longest time to delivery of a cost-of-carry forward.
_YEARS_MAX: Final = 50.0
#: The carry rates. The lower end of the risk-free rate keeps e^(-rT) at most e^5.
_RATE_MIN: Final = -0.1
_RATE_MAX: Final = 1.0
#: An exchange rate, quote currency per unit of base currency.
_FX_MIN: Final = 1e-6
_FX_MAX: Final = 1e6
#: The longest currency forward: ten years of days.
_FX_DAYS_MAX: Final = 3_653
#: Money-market rates. Over ten years on ACT/360, 1 - 0.05 x 10.15 > 0.49, so
#: each currency's growth stays positive.
_MM_MIN: Final = -0.05
_MM_MAX: Final = 1.0
#: A forward rate is at most (1 + 10.15) / 0.49 = 22.8 times the spot, and at
#: least 0.49 / 11.15 = 0.044 times it. Its bound is wider than a ratio's
#: default of 1e6 for that reason (ADR-0008 decision 3).
_FX_OUT_MAX: Final = 1e8

_FX = "units of the quote currency per unit of the base currency"
_BASIS: Final = {"act_360": 360.0, "act_365_fixed": 365.0}

type MoneyMarketDayCount = Literal["act_360", "act_365_fixed"]


def _rate(description: str, default: float | None = None) -> Any:  # noqa: ANN401
    if default is None:
        return Field(ge=_RATE_MIN, le=_RATE_MAX, description=description)
    return Field(default, ge=_RATE_MIN, le=_RATE_MAX, description=description)


def _money_in(description: str, default: float | None = None) -> Any:  # noqa: ANN401
    if default is None:
        return Field(ge=0.0, le=_MONEY_IN, description=description)
    return Field(default, ge=0.0, le=_MONEY_IN, description=description)


# --- inputs ------------------------------------------------------------------


class _Carry(ModelInputs):
    spot: Money = Field(
        gt=0.0, le=_MONEY_IN, description="Price of the asset for delivery now"
    )
    years: Years = Field(
        ge=0.0, le=_YEARS_MAX, description="Time to delivery, in years"
    )
    risk_free_rate: Rate = _rate("Risk-free rate per year, continuously compounded")
    income_yield: Rate = _rate(
        "Income (dividend) yield per year, continuously compounded", 0.0
    )
    storage_cost_rate: Rate = Field(
        0.0,
        ge=0.0,
        le=_RATE_MAX,
        description="Storage costs per year as a yield on the price, continuously",
    )
    convenience_yield: Rate = Field(
        0.0,
        ge=0.0,
        le=_RATE_MAX,
        description="Convenience yield per year of holding the asset, continuously",
    )
    income_present_value: Money = _money_in(
        "Present value of known income paid before delivery", 0.0
    )
    storage_cost_present_value: Money = _money_in(
        "Present value of known storage costs paid before delivery", 0.0
    )


class CostOfCarryInputs(_Carry):
    """An asset's spot price and what it costs, or earns, to hold it."""

    calculation: Literal["cost_of_carry"] = Field(
        "cost_of_carry", description="Forward price by cost of carry"
    )


class ForwardValueInputs(_Carry):
    """A forward contract entered earlier, and the asset's carry now."""

    calculation: Literal["forward_value"] = Field(
        "forward_value", description="Value of an existing forward contract"
    )
    delivery_price: Money = _money_in("Delivery price agreed in the contract")
    position: Literal["long", "short"] = Field(
        "long", description="The side valued: long (buyer) or short (seller)"
    )


class FxForwardInputs(ModelInputs):
    """A spot exchange rate and each currency's money-market rate."""

    calculation: Literal["fx_forward"] = Field(
        "fx_forward", description="Forward exchange rate by covered interest parity"
    )
    spot: Ratio = Field(
        ge=_FX_MIN, le=_FX_MAX, description=f"Spot exchange rate, in {_FX}"
    )
    days: Days = Field(
        ge=1, le=_FX_DAYS_MAX, description="Actual days from spot to delivery"
    )
    quote_rate: Rate = Field(
        ge=_MM_MIN,
        le=_MM_MAX,
        description="Money-market rate of the quote currency per year, simple",
    )
    base_rate: Rate = Field(
        ge=_MM_MIN,
        le=_MM_MAX,
        description="Money-market rate of the base currency per year, simple",
    )
    quote_day_count: MoneyMarketDayCount = Field(
        "act_360", description="Day count of the quote currency's rate"
    )
    base_day_count: MoneyMarketDayCount = Field(
        "act_360", description="Day count of the base currency's rate"
    )


ForwardsInputs = Annotated[
    CostOfCarryInputs | ForwardValueInputs | FxForwardInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


def _forward_price() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=MONEY_OUT, description="Forward price for delivery at T")


class CostOfCarryOutputs(ModelOutputs):
    calculation: Literal["cost_of_carry"] = Field(
        "cost_of_carry", description="Forward price by cost of carry"
    )
    forward_price: Money = _forward_price()


class ForwardValueOutputs(ModelOutputs):
    calculation: Literal["forward_value"] = Field(
        "forward_value", description="Value of an existing forward contract"
    )
    forward_price: Money = _forward_price()
    value: Money = Field(
        ge=-MONEY_OUT,
        le=MONEY_OUT,
        description="Value of the contract to the side given: +/-(F - K) e^-rT",
    )


class FxForwardOutputs(ModelOutputs):
    calculation: Literal["fx_forward"] = Field(
        "fx_forward", description="Forward exchange rate by covered interest parity"
    )
    forward_rate: Ratio = Field(
        gt=0.0, le=_FX_OUT_MAX, description=f"Outright forward rate, in {_FX}"
    )
    forward_points: Ratio = Field(
        ge=-_FX_OUT_MAX,
        le=_FX_OUT_MAX,
        description=(
            "Forward less spot, in units of the quote currency; quoted points "
            "scale this by the pair's pip size"
        ),
    )
    forward_premium: Return = Field(
        ge=-1.0,
        le=100.0,
        description="Forward over spot, less one: the base currency's premium",
    )


ForwardsOutputs = Annotated[
    CostOfCarryOutputs | ForwardValueOutputs | FxForwardOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _forward_price_of(inputs: _Carry) -> float:
    base = inputs.spot - inputs.income_present_value + inputs.storage_cost_present_value
    if base < 0:
        msg = (
            f"the income's present value ({inputs.income_present_value!r}) exceeds "
            "the spot price plus the storage costs', so no forward price is positive"
        )
        raise DomainError(msg)
    carry = (
        inputs.risk_free_rate
        - inputs.income_yield
        + inputs.storage_cost_rate
        - inputs.convenience_yield
    )
    exponent = carry * inputs.years
    # e^700 is finite; a larger exponent is far past the bound anyway.
    forward = base * math.exp(min(exponent, 700.0))
    return bounded(forward, 0.0, MONEY_OUT, "forward price")


def _cost_of_carry(inputs: CostOfCarryInputs) -> CostOfCarryOutputs:
    return CostOfCarryOutputs(forward_price=_forward_price_of(inputs))


def _forward_value(inputs: ForwardValueInputs) -> ForwardValueOutputs:
    forward = _forward_price_of(inputs)
    long_value = (forward - inputs.delivery_price) * math.exp(
        -inputs.risk_free_rate * inputs.years
    )
    value = long_value if inputs.position == "long" else -long_value
    return ForwardValueOutputs(
        forward_price=forward,
        value=bounded(value, -MONEY_OUT, MONEY_OUT, "forward value"),
    )


def _fx_forward(inputs: FxForwardInputs) -> FxForwardOutputs:
    quote = 1.0 + inputs.quote_rate * inputs.days / _BASIS[inputs.quote_day_count]
    base = 1.0 + inputs.base_rate * inputs.days / _BASIS[inputs.base_day_count]
    ratio = quote / base
    forward = inputs.spot * ratio
    return FxForwardOutputs(
        forward_rate=forward,
        forward_points=forward - inputs.spot,
        forward_premium=ratio - 1.0,
    )


# --- the model ---------------------------------------------------------------

_HULL = Reference(
    key="hull2018",
    citation=(
        "Hull, J. C. (2018). Options, Futures, and Other Derivatives, 10th ed. Pearson."
    ),
    url="https://openlibrary.org/isbn/9780134472089",
    isbn="9780134472089",
    locator=(
        "Chapter 5 (forward prices with known income, a known yield, storage "
        "costs and convenience yields; the value of a forward contract; "
        "currency forwards)"
    ),
)
_BIS = Reference(
    key="borio2016",
    citation=(
        "Borio, C., McCauley, R. N., McGuire, P. and Sushko, V. (2016). Covered "
        "interest parity lost: understanding the cross-currency basis. BIS "
        "Quarterly Review, September 2016."
    ),
    url="https://www.bis.org/publ/qtrpdf/r_qt1609e.htm",
    locator='Section "A framework" and Box A (the covered parity condition)',
)


@model(
    id="derivatives.forwards",
    version=1,
    title="Forward prices and values",
    summary=(
        "Forward prices by cost of carry, the value of an existing forward, and "
        "forward exchange rates by covered interest parity."
    ),
    formula=(
        r"F = (S - I + U)\,e^{(r - q + u - y)T}",
        r"f_{long} = (F - K)\,e^{-rT}, \quad f_{short} = -f_{long}",
        (
            r"F_{fx} = S\,\frac{1 + r_q\,d/B_q}{1 + r_b\,d/B_b}, "
            r"\quad \text{points} = F_{fx} - S"
        ),
    ),
    assumptions=(
        (
            "Markets are frictionless and free of arbitrage, and money can be "
            "borrowed and lent at the risk-free rate."
        ),
        (
            "Carry rates and the risk-free rate are continuously compounded and "
            "constant to delivery; known income and storage costs enter as their "
            "present values."
        ),
        (
            "A currency forward uses money-market (simple) interest on each "
            "currency's day count over the actual days to delivery."
        ),
    ),
    limitations=(
        (
            "Results are the formulas' outputs for the inputs given, not a quote "
            "for a traded contract or trading advice."
        ),
        (
            "For a consumption commodity the formula is an upper bound unless the "
            "convenience yield is known; the model takes it as given."
        ),
        (
            "Covered parity ignores the cross-currency basis, bid-offer spreads "
            "and credit, which open gaps between quoted and parity forwards."
        ),
        (
            "Income worth more than the spot price plus storage, and a forward "
            "price or value outside [-1e15, 1e15], raise DomainError."
        ),
    ),
    references=(_HULL, _BIS),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("forwards", "cost of carry", "covered interest parity", "fx forward"),
    invariants=(
        Invariant(
            id="forward_value_zero_at_inception",
            statement=(
                "A forward whose delivery price is today's forward price is worth "
                "zero to either side."
            ),
        ),
        Invariant(
            id="fx_forward_matches_parity",
            statement=(
                "The forward rate times the base currency's growth equals the spot "
                "times the quote currency's growth."
            ),
        ),
    ),
    examples=(
        Example(
            name="stock_with_known_dividends",
            inputs={
                "calculation": "cost_of_carry",
                "spot": 50,
                "years": 0.8333,
                "risk_free_rate": 0.08,
                "income_present_value": 2.162,
            },
        ),
        Example(
            name="long_forward_value",
            inputs={
                "calculation": "forward_value",
                "spot": 25,
                "years": 0.5,
                "risk_free_rate": 0.10,
                "delivery_price": 24,
            },
        ),
        Example(
            name="three_month_eur_usd",
            inputs={
                "calculation": "fx_forward",
                "spot": 1.08,
                "days": 91,
                "quote_rate": 0.045,
                "base_rate": 0.03,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def forwards(inputs: ForwardsInputs) -> ForwardsOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], ForwardsOutputs]]] = {
    CostOfCarryInputs: _cost_of_carry,
    ForwardValueInputs: _forward_value,
    FxForwardInputs: _fx_forward,
}
