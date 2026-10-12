# src/pyeconomics/models/fixed_income/bond_pricing.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Bond prices and yields: ``fixed_income.bond_pricing``.

Four calculations share one model, discriminated on ``calculation``:

- ``price_from_yield``: the full (dirty) price, the flat (clean) price and the
  accrued interest at settlement, from a yield to maturity;
- ``yield_from_price``: the yield to maturity from a flat or a full price;
- ``yield_to_call``: the yield if the bond is called on one coupon date at a
  call price;
- ``yield_to_worst``: the lowest of the yield to maturity and the yields to a
  schedule of calls, and the date that gives it.

Bond terms, cash flows and the two yield conventions (street, and the
Treasury's simple interest over the first fraction of a period) are in
:mod:`pyeconomics.models.fixed_income._bonds`. Money is for the face value held:
with the default face value of 100, prices are per 100.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Count,
    DateArray,
    DateValue,
    Evidence,
    Example,
    Invariant,
    ModelOutputs,
    Money,
    Rate,
    Reference,
    model,
    warn,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.fixed_income._bonds import (
    EARLIEST,
    FACE_MAX,
    LATEST,
    MONEY_OUT,
    PAYMENTS_MAX,
    YIELD_MAX,
    YIELD_MIN,
    BondTerms,
    Convention,
    Flows,
    bond_flows,
    bounded,
    payment_dates,
    price,
    solve_yield,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["bond_pricing"]

#: The most call dates a yield-to-worst takes.
_CALLS_MAX: Final = 50

_CallPrices = Annotated[
    tuple[Annotated[Money, Field(ge=1.0, le=200.0)], ...], ARRAY_INPUT
]


def _yield(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=YIELD_MIN, le=YIELD_MAX, description=description)


def _convention() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        "street",
        description=(
            "Discounting over the first fraction of a period: compound (street) "
            "or simple interest (treasury, 31 CFR Part 356 Appendix B)"
        ),
    )


def _price() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(gt=0.0, le=MONEY_OUT, description="Price of the face value held")


def _price_type() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        "flat",
        description=(
            "Whether the price excludes (flat) or includes (full) accrued interest"
        ),
    )


# --- inputs ------------------------------------------------------------------


class PriceFromYieldInputs(BondTerms):
    """A bond and its yield to maturity."""

    calculation: Literal["price_from_yield"] = Field(
        "price_from_yield", description="Full and flat price from a yield"
    )
    yield_to_maturity: Rate = _yield(
        "Yield to maturity per year, compounded at the coupon frequency"
    )
    convention: Convention = _convention()


class YieldFromPriceInputs(BondTerms):
    """A bond and its price."""

    calculation: Literal["yield_from_price"] = Field(
        "yield_from_price", description="Yield to maturity from a price"
    )
    price: Money = _price()
    price_type: Literal["flat", "full"] = _price_type()
    convention: Convention = _convention()


class _Called(BondTerms):
    def _check_calls(self, dates: tuple[Any, ...]) -> None:
        coupons = set(payment_dates(self))
        stray = [day.isoformat() for day in dates if day not in coupons]
        if stray:
            msg = (
                "a call date must be a coupon date after settlement, up to the "
                f"maturity; these are not: {', '.join(stray)}"
            )
            raise ValueError(msg)


class YieldToCallInputs(_Called):
    """A bond, its price, and a call on one coupon date."""

    calculation: Literal["yield_to_call"] = Field(
        "yield_to_call", description="Yield to a call date"
    )
    price: Money = _price()
    price_type: Literal["flat", "full"] = _price_type()
    call_date: DateValue = Field(
        ge=EARLIEST, le=LATEST, description="Coupon date on which the bond is called"
    )
    call_price: Money = Field(
        ge=1.0, le=200.0, description="Amount paid on the call, per 100 of face value"
    )
    convention: Convention = _convention()

    @model_validator(mode="after")
    def _call_on_a_coupon_date(self) -> Self:
        self._check_calls((self.call_date,))
        return self


class YieldToWorstInputs(_Called):
    """A bond, its price, and a schedule of calls."""

    calculation: Literal["yield_to_worst"] = Field(
        "yield_to_worst", description="Lowest yield over the calls and maturity"
    )
    price: Money = _price()
    price_type: Literal["flat", "full"] = _price_type()
    call_dates: DateArray = Field(
        min_length=1,
        max_length=_CALLS_MAX,
        description="Coupon dates on which the bond may be called",
    )
    call_prices: _CallPrices = Field(
        min_length=1,
        max_length=_CALLS_MAX,
        description="Amount paid on each call, per 100 of face value",
    )
    convention: Convention = _convention()

    @model_validator(mode="after")
    def _one_price_per_call_date(self) -> Self:
        if len(self.call_dates) != len(self.call_prices):
            msg = (
                f"give one call price per call date: {len(self.call_dates)} dates, "
                f"{len(self.call_prices)} prices"
            )
            raise ValueError(msg)
        self._check_calls(self.call_dates)
        return self


BondPricingInputs = Annotated[
    PriceFromYieldInputs
    | YieldFromPriceInputs
    | YieldToCallInputs
    | YieldToWorstInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


def _full() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=MONEY_OUT, description="Full (dirty) price at settlement")


def _flat() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=-MONEY_OUT,
        le=MONEY_OUT,
        description="Flat (clean) price: the full price less accrued interest",
    )


def _accrued() -> Any:  # noqa: ANN401 - pydantic's Field
    # At most two periods of a 100% coupon (a long first period) on the face.
    return Field(
        ge=0.0, le=2 * FACE_MAX, description="Interest accrued up to settlement"
    )


class PriceFromYieldOutputs(ModelOutputs):
    calculation: Literal["price_from_yield"] = Field(
        "price_from_yield", description="Full and flat price from a yield"
    )
    full_price: Money = _full()
    flat_price: Money = _flat()
    accrued_interest: Money = _accrued()
    next_coupon_date: DateValue = Field(
        ge=EARLIEST, le=LATEST, description="First payment after settlement"
    )
    payments: Count = Field(
        ge=1, le=PAYMENTS_MAX, description="Payments remaining after settlement"
    )


class YieldFromPriceOutputs(ModelOutputs):
    calculation: Literal["yield_from_price"] = Field(
        "yield_from_price", description="Yield to maturity from a price"
    )
    yield_to_maturity: Rate = _yield("Yield to maturity that gives the price")
    full_price: Money = _full()
    flat_price: Money = _flat()
    accrued_interest: Money = _accrued()


class YieldToCallOutputs(ModelOutputs):
    calculation: Literal["yield_to_call"] = Field(
        "yield_to_call", description="Yield to a call date"
    )
    yield_to_call: Rate = _yield("Yield if the bond is called on the call date")
    full_price: Money = _full()


class YieldToWorstOutputs(ModelOutputs):
    calculation: Literal["yield_to_worst"] = Field(
        "yield_to_worst", description="Lowest yield over the calls and maturity"
    )
    yield_to_worst: Rate = _yield("Lowest of the yield to maturity and to each call")
    worst_date: DateValue = Field(
        ge=EARLIEST, le=LATEST, description="Call or maturity date that gives it"
    )
    yield_to_maturity: Rate = _yield("Yield to maturity")
    full_price: Money = _full()


BondPricingOutputs = Annotated[
    PriceFromYieldOutputs
    | YieldFromPriceOutputs
    | YieldToCallOutputs
    | YieldToWorstOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _full_price(
    inputs: YieldFromPriceInputs | YieldToCallInputs | YieldToWorstInputs,
    flows: Flows,
) -> float:
    accrued = flows.accrued if inputs.price_type == "flat" else 0.0
    return bounded(inputs.price + accrued, 0.0, MONEY_OUT, "full price")


def _price_from_yield(inputs: PriceFromYieldInputs) -> PriceFromYieldOutputs:
    flows = bond_flows(inputs)
    full = bounded(
        price(flows, inputs.yield_to_maturity, inputs.convention),
        0.0,
        MONEY_OUT,
        "full price",
    )
    return PriceFromYieldOutputs(
        full_price=full,
        flat_price=bounded(full - flows.accrued, -MONEY_OUT, MONEY_OUT, "flat price"),
        accrued_interest=flows.accrued,
        next_coupon_date=flows.dates[0],
        payments=len(flows.dates),
    )


def _yield_from_price(inputs: YieldFromPriceInputs) -> YieldFromPriceOutputs:
    flows = bond_flows(inputs)
    full = _full_price(inputs, flows)
    return YieldFromPriceOutputs(
        yield_to_maturity=solve_yield(flows, full, inputs.convention),
        full_price=full,
        flat_price=full - flows.accrued,
        accrued_interest=flows.accrued,
    )


def _yield_to_call(inputs: YieldToCallInputs) -> YieldToCallOutputs:
    flows = bond_flows(inputs)
    full = _full_price(inputs, flows)
    called = bond_flows(inputs, until=inputs.call_date, redemption=inputs.call_price)
    return YieldToCallOutputs(
        yield_to_call=solve_yield(called, full, inputs.convention), full_price=full
    )


def _yield_to_worst(inputs: YieldToWorstInputs) -> YieldToWorstOutputs:
    flows = bond_flows(inputs)
    full = _full_price(inputs, flows)
    to_maturity = solve_yield(flows, full, inputs.convention)
    worst, worst_date = to_maturity, inputs.maturity
    for day, call_price in zip(inputs.call_dates, inputs.call_prices, strict=True):
        called = bond_flows(inputs, until=day, redemption=call_price)
        if price(called, YIELD_MAX, inputs.convention) > full:
            # The yield to this call is above the range, so never the worst.
            warn(
                "call_yield_above_range",
                f"the yield to the call on {day.isoformat()} is above {YIELD_MAX}; "
                "it cannot be the worst and is skipped",
            )
            continue
        to_call = solve_yield(called, full, inputs.convention)
        if to_call < worst:
            worst, worst_date = to_call, day
    return YieldToWorstOutputs(
        yield_to_worst=worst,
        worst_date=worst_date,
        yield_to_maturity=to_maturity,
        full_price=full,
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
        "Section I (computation of interest) and section II, paragraphs A-G "
        "(non-indexed yield to price, with examples)"
    ),
)
_FABOZZI = Reference(
    key="fabozzi2005",
    citation=(
        "Fabozzi, F. J. (2005). Fixed Income Mathematics: Analytical and "
        "Statistical Techniques, 4th ed. McGraw-Hill."
    ),
    url="https://openlibrary.org/isbn/9780071460736",
    isbn="9780071460736",
    locator="Chapter 5 (the price of a bond, between coupon dates included)",
)
_QUANTLIB = Reference(
    key="quantlib",
    citation=(
        "QuantLib (2026). BondFunctions and FixedRateBond. QuantLib 1.43 reference."
    ),
    url="https://www.quantlib.org/reference/struct_quant_lib_1_1_bond_functions.html",
    locator="BondFunctions::cleanPrice, dirtyPrice, accruedAmount and yield",
)
_BOND = {
    "settlement": "2026-01-15",
    "maturity": "2036-01-15",
    "coupon_rate": 0.045,
}


@model(
    id="fixed_income.bond_pricing",
    version=2,
    title="Bond price and yield",
    summary=(
        "Full and flat price and accrued interest of a fixed-coupon bond from its "
        "yield, and its yield to maturity, to a call and to worst from its price."
    ),
    formula=(
        r"P_{full} = \sum_{j} \frac{CF_j}{(1 + y/f)^{w + j - 1}}",
        r"P_{full}^{treasury} = \frac{\sum_j CF_j (1 + y/f)^{-(j - 1)}}{1 + w y / f}",
        r"AI = F\,c\,\tau(t_{prev}, t_{settle}), \quad P_{flat} = P_{full} - AI",
        r"YTW = \min\left(YTM, \min_k YTC_k\right)",
    ),
    assumptions=(
        (
            "Coupons are fixed and paid f times a year on dates stepped back "
            "from the maturity; a regular coupon is c/f of the face value, and an "
            "irregular first coupon is the day count's fraction of it."
        ),
        (
            "The yield compounds at the coupon frequency. Street convention "
            "discounts the fraction w of a period to the first payment by "
            "(1 + y/f)^w; the treasury convention uses simple interest, 1 + w y/f, "
            "as 31 CFR Part 356 Appendix B does."
        ),
        (
            "Accrued interest runs from the previous coupon date, or from the "
            "issue date in an irregular first period, under the bond's day count."
        ),
        (
            "A call is exercised on a coupon date at the call price per 100 of "
            "face value, after that date's coupon is paid."
        ),
        "Payment dates are not adjusted for business days.",
    ),
    limitations=(
        (
            "Yields are solved in [-0.1, 1]. A price no yield in that range gives "
            "raises DomainError, including in yield_to_worst a call whose yield "
            "is below -0.1; a call whose yield is above 1 is skipped there, with "
            "a warning."
        ),
        (
            "Only a first period may be irregular; odd last periods, floating or "
            "step-up coupons, sinking funds, and ex-dividend periods are out of scope."
        ),
        (
            "Day counts are ACT/ACT (ICMA), US 30/360 and 30E/360. A regular "
            "coupon is c/f, and payments after the first are whole periods apart, "
            "even where a 30/360 count of a period touching a February month end "
            "is not 360/f; QuantLib, which sums each period's 30/360 fraction, "
            "differs there."
        ),
    ),
    references=(_CFR, _FABOZZI, _QUANTLIB),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    tags=("bond", "price", "yield", "accrued interest", "yield to worst"),
    invariants=(
        Invariant(
            id="price_decreases_with_yield",
            statement=(
                "For a bond with non-negative cash flows, the full price falls as "
                "the yield rises."
            ),
        ),
        Invariant(
            id="par_bond_prices_at_par",
            statement=(
                "On a coupon date of a regular schedule, a bond whose yield equals "
                "its coupon rate and that repays 100 prices at its face value."
            ),
        ),
        Invariant(
            id="full_equals_flat_plus_accrued",
            statement="The full price is the flat price plus the accrued interest.",
        ),
        Invariant(
            id="yield_to_worst_not_above_yield_to_maturity",
            statement="The yield to worst is never above the yield to maturity.",
        ),
    ),
    examples=(
        Example(
            name="treasury_thirty_year",
            inputs={
                "calculation": "price_from_yield",
                "settlement": "1990-05-15",
                "maturity": "2020-05-15",
                "coupon_rate": 0.0875,
                "yield_to_maturity": 0.0884,
                "convention": "treasury",
            },
            note="31 CFR Part 356 Appendix B, section II.A: a price of 99.057893.",
        ),
        Example(
            name="between_coupons",
            inputs={
                "calculation": "price_from_yield",
                **_BOND,
                "settlement": "2026-03-02",
                "yield_to_maturity": 0.05,
            },
        ),
        Example(
            name="yield_from_flat_price",
            inputs={"calculation": "yield_from_price", **_BOND, "price": 96.5},
        ),
        Example(
            name="yield_to_first_call",
            inputs={
                "calculation": "yield_to_call",
                **_BOND,
                "price": 103.0,
                "call_date": "2031-01-15",
                "call_price": 101.0,
            },
        ),
        Example(
            name="yield_to_worst",
            inputs={
                "calculation": "yield_to_worst",
                **_BOND,
                "price": 104.0,
                "call_dates": ["2029-01-15", "2031-01-15", "2033-01-15"],
                "call_prices": [102.0, 101.0, 100.0],
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
def bond_pricing(inputs: BondPricingInputs) -> BondPricingOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[BondTerms], Callable[[Any], BondPricingOutputs]]] = {
    PriceFromYieldInputs: _price_from_yield,
    YieldFromPriceInputs: _yield_from_price,
    YieldToCallInputs: _yield_to_call,
    YieldToWorstInputs: _yield_to_worst,
}
