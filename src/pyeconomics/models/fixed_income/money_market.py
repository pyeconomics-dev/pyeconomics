# src/pyeconomics/models/fixed_income/money_market.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Money-market prices and yields: ``fixed_income.money_market``.

Six calculations on a discount instrument (a Treasury bill, commercial paper)
that pays its face value after a number of days, discriminated on
``calculation``:

- ``price_from_discount`` and ``discount_from_price``: the bank discount yield,
  which quotes the discount as a fraction of the face value per 360 days;
- ``money_market_yield``: the CD-equivalent yield, the return on the price per
  360 days;
- ``investment_rate``: the Treasury's bond-equivalent yield, the return on the
  price per 365 (or 366) days, with the semiannual-compounding formula for a
  bill of more than half a year (31 CFR Part 356, Appendix B, section VI.D);
- ``effective_annual_yield``: the return compounded to 365 days;
- ``holding_period_yield``: the return over the holding period.

Money is for the face value held: with the default face value of 100, prices are
per 100, as Treasury quotes them.
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
    Reference,
    Return,
    Symbol,
    model,
)
from pyeconomics.models.fixed_income._bonds import bounded

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["money_market"]

#: The largest face value or price an input takes.
_MONEY_IN: Final = 1e12
#: The longest instrument, in days: two years.
_DAYS_MAX: Final = 730
#: The yields an output may hold: ADR-0008's default rate bounds.
_RATE_MIN: Final = -0.99
_RATE_MAX: Final = 10.0
#: Days in the bank-discount and money-market year.
_BANK_YEAR: Final = 360
#: Days in the year an effective annual yield compounds to.
_YEAR: Final = 365


def _days(description: str, high: int = _DAYS_MAX) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=1, le=high, description=description)


def _face() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        100.0, ge=0.01, le=_MONEY_IN, description="Face value repaid at maturity"
    )


def _price(description: str = "Price paid for the face value") -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(gt=0.0, le=_MONEY_IN, description=description)


def _rate(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=_RATE_MIN, le=_RATE_MAX, description=description)


# --- inputs ------------------------------------------------------------------


class PriceFromDiscountInputs(ModelInputs):
    """A bank discount rate and the days to maturity."""

    calculation: Literal["price_from_discount"] = Field(
        "price_from_discount", description="Price from a bank discount rate"
    )
    discount_rate: Rate = Field(
        ge=-0.5, le=1.0, description="Bank discount rate, per 360 days"
    )
    days: Days = _days("Days from settlement to maturity")
    face_value: Money = _face()


class DiscountFromPriceInputs(ModelInputs):
    """A price and the days to maturity."""

    calculation: Literal["discount_from_price"] = Field(
        "discount_from_price", description="Bank discount rate from a price"
    )
    price: Money = _price()
    days: Days = _days("Days from settlement to maturity")
    face_value: Money = _face()


class MoneyMarketYieldInputs(ModelInputs):
    """A price and the days to maturity."""

    calculation: Literal["money_market_yield"] = Field(
        "money_market_yield", description="Money-market (CD-equivalent) yield"
    )
    price: Money = _price()
    days: Days = _days("Days from settlement to maturity")
    face_value: Money = _face()


class InvestmentRateInputs(ModelInputs):
    """A bill's price, its days to maturity, and the days in its year."""

    calculation: Literal["investment_rate"] = Field(
        "investment_rate", description="Treasury investment rate (bond-equivalent)"
    )
    price: Money = _price()
    days: Days = _days("Days from settlement to maturity", 366)
    face_value: Money = _face()
    days_in_year: Days = Field(
        365,
        ge=365,
        le=366,
        description=(
            "Days in the year after the issue date: 366 when it holds a February 29"
        ),
    )


class EffectiveAnnualYieldInputs(ModelInputs):
    """A price and the days to maturity."""

    calculation: Literal["effective_annual_yield"] = Field(
        "effective_annual_yield", description="Return compounded to a 365-day year"
    )
    price: Money = _price()
    days: Days = _days("Days from settlement to maturity")
    face_value: Money = _face()


class HoldingPeriodYieldInputs(ModelInputs):
    """What was paid, what was received, and any income."""

    calculation: Literal["holding_period_yield"] = Field(
        "holding_period_yield", description="Return over the holding period"
    )
    purchase_price: Money = _price("Price paid at the start")
    proceeds: Money = Field(
        ge=0.0,
        le=_MONEY_IN,
        description="Sale price, or the face value repaid at maturity",
    )
    income: Money = Field(
        0.0, ge=0.0, le=_MONEY_IN, description="Interest or other income received"
    )


MoneyMarketInputs = Annotated[
    PriceFromDiscountInputs
    | DiscountFromPriceInputs
    | MoneyMarketYieldInputs
    | InvestmentRateInputs
    | EffectiveAnnualYieldInputs
    | HoldingPeriodYieldInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class PriceFromDiscountOutputs(ModelOutputs):
    calculation: Literal["price_from_discount"] = Field(
        "price_from_discount", description="Price from a bank discount rate"
    )
    # At a discount rate of -50% over 730 days, the price is about 2.01 times
    # the face value.
    price: Money = Field(
        gt=0.0, le=3 * _MONEY_IN, description="Price for the face value"
    )
    discount: Money = Field(
        ge=-2 * _MONEY_IN,
        le=_MONEY_IN,
        description="Face value less price (negative at a negative rate)",
    )


class DiscountFromPriceOutputs(ModelOutputs):
    calculation: Literal["discount_from_price"] = Field(
        "discount_from_price", description="Bank discount rate from a price"
    )
    discount_rate: Rate = _rate("Bank discount rate, per 360 days")


class MoneyMarketYieldOutputs(ModelOutputs):
    calculation: Literal["money_market_yield"] = Field(
        "money_market_yield", description="Money-market (CD-equivalent) yield"
    )
    money_market_yield: Rate = _rate("Return on the price, per 360 days")


class InvestmentRateOutputs(ModelOutputs):
    calculation: Literal["investment_rate"] = Field(
        "investment_rate", description="Treasury investment rate (bond-equivalent)"
    )
    investment_rate: Rate = _rate("Bond-equivalent yield, per 365 or 366 days")


class EffectiveAnnualYieldOutputs(ModelOutputs):
    calculation: Literal["effective_annual_yield"] = Field(
        "effective_annual_yield", description="Return compounded to a 365-day year"
    )
    effective_annual_yield: Rate = _rate("Return compounded over 365 days")


class HoldingPeriodYieldOutputs(ModelOutputs):
    calculation: Literal["holding_period_yield"] = Field(
        "holding_period_yield", description="Return over the holding period"
    )
    holding_period_yield: Return = Field(
        ge=-1.0, le=100.0, description="Gain and income over the price paid"
    )


MoneyMarketOutputs = Annotated[
    PriceFromDiscountOutputs
    | DiscountFromPriceOutputs
    | MoneyMarketYieldOutputs
    | InvestmentRateOutputs
    | EffectiveAnnualYieldOutputs
    | HoldingPeriodYieldOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _price_from_discount(inputs: PriceFromDiscountInputs) -> PriceFromDiscountOutputs:
    face = inputs.face_value
    discount = face * inputs.discount_rate * inputs.days / _BANK_YEAR
    if discount >= face:
        msg = (
            f"a discount rate of {inputs.discount_rate!r} over {inputs.days} days "
            "takes the whole face value, leaving no positive price"
        )
        raise DomainError(msg)
    return PriceFromDiscountOutputs(price=face - discount, discount=discount)


def _discount_from_price(inputs: DiscountFromPriceInputs) -> DiscountFromPriceOutputs:
    face = inputs.face_value
    rate = (face - inputs.price) / face * _BANK_YEAR / inputs.days
    return DiscountFromPriceOutputs(
        discount_rate=bounded(rate, _RATE_MIN, _RATE_MAX, "discount rate")
    )


def _money_market_yield(inputs: MoneyMarketYieldInputs) -> MoneyMarketYieldOutputs:
    price = inputs.price
    rate = (inputs.face_value - price) / price * _BANK_YEAR / inputs.days
    return MoneyMarketYieldOutputs(
        money_market_yield=bounded(rate, _RATE_MIN, _RATE_MAX, "money-market yield")
    )


def _investment_rate(inputs: InvestmentRateInputs) -> InvestmentRateOutputs:
    price, days, year = inputs.price, inputs.days, inputs.days_in_year
    gain = (inputs.face_value - price) / price
    if 2 * days <= year:
        rate = gain * year / days
    else:
        # P [1 + (r - y/2)(i/y)](1 + i/2) = F, as a i^2 + b i + c = 0 with
        # a = r/(2y) - 1/4 > 0, b = r/y, c = -gain. The root is written
        # 2 gain / (b + sqrt(b^2 + 4 a gain)) so that no difference cancels. As
        # gain > -1 and a = (b - 1/2)/2, the discriminant exceeds (b - 1)^2 >= 0.
        a, b = days / (2 * year) - 0.25, days / year
        discriminant = b * b + 4 * a * gain
        rate = 2 * gain / (b + math.sqrt(discriminant))
    return InvestmentRateOutputs(
        investment_rate=bounded(rate, _RATE_MIN, _RATE_MAX, "investment rate")
    )


def _effective_annual_yield(
    inputs: EffectiveAnnualYieldInputs,
) -> EffectiveAnnualYieldOutputs:
    exponent = (
        _YEAR / inputs.days * (math.log(inputs.face_value) - math.log(inputs.price))
    )
    if exponent > math.log1p(_RATE_MAX):
        msg = (
            f"the effective annual yield exceeds {_RATE_MAX}: the price is far "
            "below the face value over few days"
        )
        raise DomainError(msg)
    return EffectiveAnnualYieldOutputs(
        effective_annual_yield=bounded(
            math.expm1(exponent), _RATE_MIN, _RATE_MAX, "effective annual yield"
        )
    )


def _holding_period_yield(
    inputs: HoldingPeriodYieldInputs,
) -> HoldingPeriodYieldOutputs:
    paid = inputs.purchase_price
    gain = inputs.proceeds + inputs.income - paid
    return HoldingPeriodYieldOutputs(
        holding_period_yield=bounded(gain / paid, -1.0, 100.0, "holding-period yield")
    )


# --- the model ---------------------------------------------------------------

_CFR = Reference(
    key="cfr356b",
    citation=(
        "US Department of the Treasury (2022). 31 CFR Part 356, Appendix B: "
        "Formulas and Tables. Electronic Code of Federal Regulations."
    ),
    url="https://www.ecfr.gov/current/title-31/subtitle-B/chapter-II/subchapter-B/part-356/appendix-Appendix%20B%20to%20Part%20356",
    locator=(
        "Section VI (purchase price, discount rate and investment rate of "
        "Treasury bills), paragraphs A-D"
    ),
)
_AUCTION = Reference(
    key="tbill_auction",
    citation=(
        "US Department of the Treasury, Bureau of the Fiscal Service (2026). "
        "Treasury Auction Results: 182-Day Bill, CUSIP 912797RF6, auctioned "
        "January 5, 2026."
    ),
    url="https://www.treasurydirect.gov/instit/annceresult/press/preanre/2026/R_20260105_2.pdf",
    locator="High rate, price and investment rate",
)


@model(
    id="fixed_income.money_market",
    version=1,
    title="Money-market yields",
    summary=(
        "Bank discount rate to and from price, money-market (CD-equivalent) "
        "yield, Treasury investment rate, effective annual yield and "
        "holding-period yield of a discount instrument."
    ),
    formula=(
        (
            r"P = F \left(1 - \frac{d\,t}{360}\right), \quad "
            r"d = \frac{F - P}{F}\,\frac{360}{t}"
        ),
        r"MMY = \frac{F - P}{P}\,\frac{360}{t}",
        r"i = \frac{F - P}{P}\,\frac{y}{t}, \quad t \le \tfrac{y}{2}",
        (
            r"P \left[1 + \left(t - \tfrac{y}{2}\right)\tfrac{i}{y}\right]"
            r"\left(1 + \tfrac{i}{2}\right) = F, \quad t > \tfrac{y}{2}"
        ),
        (
            r"EAY = \left(\frac{F}{P}\right)^{365/t} - 1, \quad "
            r"HPY = \frac{P_1 - P_0 + D}{P_0}"
        ),
    ),
    symbols=(
        Symbol("P", "Price", "price"),
        Symbol("F", "Face value", "face_value"),
        Symbol("d", "Bank discount rate", "discount_rate"),
        Symbol("t", "Days to maturity", "days"),
        Symbol("MMY", "Money-market yield, on a 360-day year", "money_market_yield"),
        Symbol("i", "Investment rate: the bond-equivalent yield", "investment_rate"),
        Symbol("y", "Days in the year: 365, or 366 in a leap year", "days_in_year"),
        Symbol("EAY", "Effective annual yield", "effective_annual_yield"),
        Symbol("HPY", "Holding-period yield", "holding_period_yield"),
        Symbol("P_0", "Purchase price", "purchase_price"),
        Symbol("P_1", "Proceeds at the end of the holding period", "proceeds"),
        Symbol("D", "Income received over the holding period", "income"),
    ),
    assumptions=(
        (
            "The instrument pays only its face value at maturity, t days after "
            "settlement; the bank discount and money-market yields count a "
            "360-day year (ACT/360)."
        ),
        (
            "The investment rate counts y = 365 days, or 366 when the year after "
            "the issue date holds a February 29, and for a bill of more than half "
            "a year compounds once at the half year, as Treasury does."
        ),
        "The effective annual yield compounds the return over t days to 365 days.",
    ),
    limitations=(
        (
            "A yield outside [-0.99, 10] (a price far from the face value over a "
            "few days), a holding-period yield above 100, and a discount that "
            "takes the whole face value raise DomainError."
        ),
        "Prices are not rounded; Treasury rounds prices per 100 to six decimals.",
    ),
    references=(_CFR, _AUCTION),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("treasury bill", "discount yield", "money market", "bond-equivalent yield"),
    invariants=(
        Invariant(
            id="discount_yield_below_investment_rate",
            statement=(
                "For a price below the face value, the bank discount rate is below "
                "the investment rate."
            ),
        ),
        Invariant(
            id="price_below_face_for_positive_yield",
            statement="A positive discount rate gives a price below the face value.",
        ),
        Invariant(
            id="price_yield_round_trip",
            statement=(
                "The discount rate of the price from a discount rate is that "
                "discount rate."
            ),
        ),
    ),
    examples=(
        Example(
            name="thirteen_week_bill",
            inputs={
                "calculation": "price_from_discount",
                "discount_rate": 0.0761,
                "days": 90,
            },
            note="31 CFR Part 356 Appendix B, section VI.A: 98.097500 per 100.",
        ),
        Example(
            name="discount_rate",
            inputs={
                "calculation": "discount_from_price",
                "price": 95.934567,
                "days": 182,
            },
        ),
        Example(
            name="cd_equivalent",
            inputs={
                "calculation": "money_market_yield",
                "price": 98.243194,
                "days": 182,
            },
        ),
        Example(
            name="fifty_two_week_bill",
            inputs={"calculation": "investment_rate", "price": 92.265, "days": 364},
            note="31 CFR Part 356 Appendix B, section VI.D.2: 0.082373244.",
        ),
        Example(
            name="effective_annual",
            inputs={
                "calculation": "effective_annual_yield",
                "price": 98.243194,
                "days": 182,
            },
        ),
        Example(
            name="held_to_maturity",
            inputs={
                "calculation": "holding_period_yield",
                "purchase_price": 98.243194,
                "proceeds": 100.0,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def money_market(inputs: MoneyMarketInputs) -> MoneyMarketOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], MoneyMarketOutputs]]] = {
    PriceFromDiscountInputs: _price_from_discount,
    DiscountFromPriceInputs: _discount_from_price,
    MoneyMarketYieldInputs: _money_market_yield,
    InvestmentRateInputs: _investment_rate,
    EffectiveAnnualYieldInputs: _effective_annual_yield,
    HoldingPeriodYieldInputs: _holding_period_yield,
}
