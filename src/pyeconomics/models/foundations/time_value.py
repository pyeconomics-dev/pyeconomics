# src/pyeconomics/models/foundations/time_value.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The time-value-of-money engine: ``foundations.time_value``.

Eight calculations share one model, discriminated on ``calculation``:

- ``present_value`` and ``future_value``: a single sum, a level annuity in
  arrears or in advance, a growing annuity, or (for a present value) a
  perpetuity, in any combination;
- ``solve``: the five-key equation in periods, rate, present value, payment and
  future value, for whichever one is omitted, with the cash-flow sign
  convention of financial calculators and spreadsheets;
- ``npv`` and ``irr`` of periodic cash flows, the first at time 0;
- ``xnpv`` and ``xirr`` of dated cash flows, in years of 365 days from the
  first date (ACT/365 Fixed, as spreadsheet XNPV and XIRR count);
- ``amortization``: a level-payment loan schedule.

Rates are decimals per period (per year for ``xnpv`` and ``xirr``).
``present_value`` and ``future_value`` give values, so money paid and received
share a sign there; ``solve`` balances cash flows, so money paid out is negative.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    IRR_POLICY,
    ChangelogEntry,
    ChartKind,
    ChartSpec,
    CostClass,
    Count,
    DateArray,
    DayCount,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Periods,
    Rate,
    Reference,
    accumulated_annuity_factor,
    accumulated_growing_annuity_factor,
    annuity_factor,
    find_root,
    growing_annuity_factor,
    growing_perpetuity_factor,
    growth_factor,
    internal_rate_of_return,
    model,
    present_value,
    present_value_factor,
    sign_changes,
    year_fraction,
)
from pyeconomics.core.errors import ConvergenceError
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.foundations._common import (
    LOG_MAX,
    MONEY_IN,
    MONEY_OUT,
    PERIODS_MAX,
    RATE_MAX,
    RATE_MIN,
    bounded,
    scaled,
)

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable

__all__ = ["time_value"]

#: The largest periodic rate the annuity calculations take: 100% a period.
_PERIODIC_RATE_MAX: Final = 1.0
#: The most cash flows an ``npv`` or ``irr`` takes, and dated flows ``xnpv`` takes.
_FLOWS_MAX: Final = PERIODS_MAX + 1
_DATED_MAX: Final = 1_000

_CashFlows = Annotated[
    tuple[Annotated[Money, Field(ge=-MONEY_IN, le=MONEY_IN)], ...], ARRAY_INPUT
]
_MoneyOut = Annotated[
    tuple[Annotated[Money, Field(ge=-MONEY_OUT, le=MONEY_OUT)], ...], ARRAY_INPUT
]
_PeriodNumbers = Annotated[
    tuple[Annotated[Count, Field(ge=1, le=PERIODS_MAX)], ...], ARRAY_INPUT
]


def _rate(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=RATE_MIN, le=_PERIODIC_RATE_MAX, description=description)


def _money_in(description: str, default: float | None = 0.0) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(default, ge=-MONEY_IN, le=MONEY_IN, description=description)


def _money_out(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-MONEY_OUT, le=MONEY_OUT, description=description)


# --- inputs ------------------------------------------------------------------


class PresentValueInputs(ModelInputs):
    """The present value of a sum, an annuity and a growing annuity together."""

    calculation: Literal["present_value"] = Field(
        "present_value", description="Discount a sum and a stream of payments"
    )
    rate: Rate = _rate("Discount rate per period")
    periods: Periods | None = Field(
        None,
        ge=0,
        le=PERIODS_MAX,
        description="Number of periods; omitted (null) for a perpetuity",
    )
    payment: Money = _money_in("First payment of the stream (0 for none)")
    growth: Rate = Field(
        0.0,
        ge=RATE_MIN,
        le=_PERIODIC_RATE_MAX,
        description="Growth of each payment over the last, per period",
    )
    future_value: Money = _money_in(
        "Single sum at the end of the last period (0 for none)"
    )
    due: bool = Field(
        default=False,
        description="Payments at the start of each period (an annuity due)",
    )


class FutureValueInputs(ModelInputs):
    """The future value of a sum, an annuity and a growing annuity together."""

    calculation: Literal["future_value"] = Field(
        "future_value", description="Compound a sum and a stream of payments"
    )
    rate: Rate = _rate("Interest rate per period")
    periods: Periods = Field(ge=0, le=PERIODS_MAX, description="Number of periods")
    payment: Money = _money_in("First payment of the stream (0 for none)")
    growth: Rate = Field(
        0.0,
        ge=RATE_MIN,
        le=_PERIODIC_RATE_MAX,
        description="Growth of each payment over the last, per period",
    )
    present_value: Money = _money_in("Single sum invested now (0 for none)")
    due: bool = Field(
        default=False,
        description="Payments at the start of each period (an annuity due)",
    )


type Solvable = Literal["periods", "rate", "present_value", "payment", "future_value"]
_SOLVABLE: Final[tuple[Solvable, ...]] = (
    "periods",
    "rate",
    "present_value",
    "payment",
    "future_value",
)


class SolveInputs(ModelInputs):
    """The five-key equation, with exactly one of its five terms omitted."""

    calculation: Literal["solve"] = Field(
        "solve", description="Solve the time-value equation for the omitted term"
    )
    periods: Periods | None = Field(
        None, ge=0, le=PERIODS_MAX, description="Number of periods (N)"
    )
    rate: Rate | None = Field(
        None,
        ge=RATE_MIN,
        le=_PERIODIC_RATE_MAX,
        description="Interest rate per period (I/Y)",
    )
    present_value: Money | None = _money_in(
        "Cash flow now (PV); negative when paid out", None
    )
    payment: Money | None = _money_in(
        "Level cash flow each period (PMT); negative when paid out", None
    )
    future_value: Money | None = _money_in(
        "Cash flow at the end (FV); negative when paid out", None
    )
    due: bool = Field(default=False, description="Payments at the start of each period")

    @model_validator(mode="after")
    def _one_omitted(self) -> Self:
        omitted = [name for name in _SOLVABLE if getattr(self, name) is None]
        if len(omitted) != 1:
            msg = (
                "give four of periods, rate, present_value, payment and "
                f"future_value and omit the one to solve for; omitted: {omitted}"
            )
            raise ValueError(msg)
        return self


class NpvInputs(ModelInputs):
    """Periodic cash flows and a discount rate."""

    calculation: Literal["npv"] = Field("npv", description="Net present value")
    rate: Rate = _rate("Discount rate per period")
    cash_flows: _CashFlows = Field(
        min_length=1,
        max_length=_FLOWS_MAX,
        description=(
            "Cash flows at times 0, 1, 2, ... periods; the first is not discounted"
        ),
    )


class IrrInputs(ModelInputs):
    """Periodic cash flows."""

    calculation: Literal["irr"] = Field("irr", description="Internal rate of return")
    cash_flows: _CashFlows = Field(
        min_length=1,
        max_length=_FLOWS_MAX,
        description="Cash flows at times 0, 1, 2, ... periods",
    )


class _Dated(ModelInputs):
    cash_flows: _CashFlows = Field(
        min_length=1, max_length=_DATED_MAX, description="Cash flows, one per date"
    )
    dates: DateArray = Field(
        min_length=1,
        max_length=_DATED_MAX,
        description="The date of each cash flow; the first is the base date",
    )

    @model_validator(mode="after")
    def _one_date_per_flow(self) -> Self:
        if len(self.dates) != len(self.cash_flows):
            msg = (
                f"give one date per cash flow: {len(self.cash_flows)} cash flows, "
                f"{len(self.dates)} dates"
            )
            raise ValueError(msg)
        return self


class XnpvInputs(_Dated):
    """Dated cash flows and an annual discount rate."""

    calculation: Literal["xnpv"] = Field(
        "xnpv", description="Net present value of dated cash flows"
    )
    rate: Rate = Field(ge=RATE_MIN, le=RATE_MAX, description="Annual discount rate")


class XirrInputs(_Dated):
    """Dated cash flows."""

    calculation: Literal["xirr"] = Field(
        "xirr", description="Internal rate of return of dated cash flows"
    )


class AmortizationInputs(ModelInputs):
    """A loan repaid in level payments at the end of each period."""

    calculation: Literal["amortization"] = Field(
        "amortization", description="Level-payment amortization schedule"
    )
    principal: Money = Field(gt=0, le=MONEY_IN, description="Amount borrowed")
    rate: Rate = _rate("Interest rate per period")
    periods: Count = Field(ge=1, le=PERIODS_MAX, description="Number of payments")


TimeValueInputs = Annotated[
    PresentValueInputs
    | FutureValueInputs
    | SolveInputs
    | NpvInputs
    | IrrInputs
    | XnpvInputs
    | XirrInputs
    | AmortizationInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class PresentValueOutputs(ModelOutputs):
    calculation: Literal["present_value"] = Field(
        "present_value", description="Discount a sum and a stream of payments"
    )
    present_value: Money = _money_out("Present value of the sum and the payments")


class FutureValueOutputs(ModelOutputs):
    calculation: Literal["future_value"] = Field(
        "future_value", description="Compound a sum and a stream of payments"
    )
    future_value: Money = _money_out("Future value of the sum and the payments")


class SolveOutputs(ModelOutputs):
    calculation: Literal["solve"] = Field(
        "solve", description="Solve the time-value equation for the omitted term"
    )
    solved_for: Solvable = Field(description="The term that was omitted and solved")
    periods: Periods = Field(ge=0, le=PERIODS_MAX, description="Number of periods (N)")
    rate: Rate = Field(
        ge=RATE_MIN, le=_PERIODIC_RATE_MAX, description="Interest rate per period"
    )
    present_value: Money = _money_out("Cash flow now (PV)")
    payment: Money = _money_out("Level cash flow each period (PMT)")
    future_value: Money = _money_out("Cash flow at the end (FV)")


class NpvOutputs(ModelOutputs):
    calculation: Literal["npv"] = Field("npv", description="Net present value")
    npv: Money = _money_out("Net present value at time 0")


class IrrOutputs(ModelOutputs):
    calculation: Literal["irr"] = Field("irr", description="Internal rate of return")
    irr: Rate | None = Field(
        ge=RATE_MIN,
        le=RATE_MAX,
        description="Rate per period at which the NPV is zero; null when undefined",
    )
    sign_changes: Count = Field(
        ge=0, le=_FLOWS_MAX, description="Sign changes in the cash flows"
    )


class XnpvOutputs(ModelOutputs):
    calculation: Literal["xnpv"] = Field(
        "xnpv", description="Net present value of dated cash flows"
    )
    xnpv: Money = _money_out("Net present value at the first date")


class XirrOutputs(ModelOutputs):
    calculation: Literal["xirr"] = Field(
        "xirr", description="Internal rate of return of dated cash flows"
    )
    xirr: Rate | None = Field(
        ge=RATE_MIN,
        le=RATE_MAX,
        description="Annual rate at which the XNPV is zero; null when undefined",
    )
    sign_changes: Count = Field(
        ge=0, le=_DATED_MAX, description="Sign changes in the cash flows"
    )


class AmortizationOutputs(ModelOutputs):
    calculation: Literal["amortization"] = Field(
        "amortization", description="Level-payment amortization schedule"
    )
    level_payment: Money = Field(
        ge=0, le=2 * MONEY_IN, description="The level payment each period"
    )
    # n level payments less the principal: up to 1,200 payments of 2e12 above,
    # and at a negative rate never below -P (twice that, for rounding).
    total_interest: Money = Field(
        ge=-2 * MONEY_IN,
        le=2 * PERIODS_MAX * MONEY_IN,
        description="Interest paid over the loan",
    )
    period: _PeriodNumbers = Field(
        max_length=PERIODS_MAX, description="Payment numbers, 1 to n"
    )
    payment: _MoneyOut = Field(
        max_length=PERIODS_MAX, description="Payment in each period"
    )
    interest: _MoneyOut = Field(
        max_length=PERIODS_MAX, description="Interest part of each payment"
    )
    principal: _MoneyOut = Field(
        max_length=PERIODS_MAX, description="Principal part of each payment"
    )
    balance: _MoneyOut = Field(
        max_length=PERIODS_MAX, description="Balance after each payment"
    )


TimeValueOutputs = Annotated[
    PresentValueOutputs
    | FutureValueOutputs
    | SolveOutputs
    | NpvOutputs
    | IrrOutputs
    | XnpvOutputs
    | XirrOutputs
    | AmortizationOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _present_value(inputs: PresentValueInputs) -> PresentValueOutputs:
    rate, growth, due = inputs.rate, inputs.growth, inputs.due
    if inputs.periods is None:
        if inputs.future_value != 0:
            msg = "a perpetuity has no final sum; give future_value 0, or periods"
            raise DomainError(msg)
        stream = scaled(
            inputs.payment, growing_perpetuity_factor(rate, growth, due=due)
        )
        total = stream
    else:
        n = inputs.periods
        total = scaled(inputs.future_value, present_value_factor(rate, n)) + scaled(
            inputs.payment, growing_annuity_factor(rate, growth, n, due=due)
        )
    value = bounded(total, -MONEY_OUT, MONEY_OUT, "present value")
    return PresentValueOutputs(present_value=value)


def _future_value(inputs: FutureValueInputs) -> FutureValueOutputs:
    rate, n = inputs.rate, inputs.periods
    total = scaled(inputs.present_value, growth_factor(rate, n)) + scaled(
        inputs.payment,
        accumulated_growing_annuity_factor(rate, inputs.growth, n, due=inputs.due),
    )
    value = bounded(total, -MONEY_OUT, MONEY_OUT, "future value")
    return FutureValueOutputs(future_value=value)


def _balance(  # noqa: PLR0913 - the five keys and the timing
    rate: float, periods: float, pv: float, pmt: float, fv: float, *, due: bool
) -> float:
    """Evaluate the five-key equation, scaled so that no term overflows.

    ``PV (1+r)^n + PMT (1+r d) s(r, n) + FV`` has the same sign and roots as
    itself divided by ``max(1, (1+r)^n)``; that quotient is what is returned.
    """
    exponent = periods * math.log1p(rate)
    if exponent >= 0:
        return (
            pv + pmt * annuity_factor(rate, periods, due=due) + fv * math.exp(-exponent)
        )
    return (
        pv * math.exp(exponent)
        + pmt * accumulated_annuity_factor(rate, periods, due=due)
        + fv
    )


def _solve_rate(n: float, pv: float, pmt: float, fv: float, *, due: bool) -> float:
    if n == 0:
        msg = "over zero periods every rate, or none, balances the cash flows"
        raise DomainError(msg)
    try:
        found = find_root(
            lambda r: _balance(r, n, pv, pmt, fv, due=due),
            RATE_MIN,
            _PERIODIC_RATE_MAX,
            policy=IRR_POLICY,
        )
    except ConvergenceError as error:
        msg = (
            f"no rate in [{RATE_MIN}, {_PERIODIC_RATE_MAX}] per period balances "
            f"these cash flows: {error}"
        )
        raise DomainError(msg) from error
    return found.root


def _solve_periods(
    rate: float, pv: float, pmt: float, fv: float, *, due: bool
) -> float:
    if rate == 0:
        if pmt == 0:
            msg = "with no rate and no payment, the number of periods is undefined"
            raise DomainError(msg)
        return -(pv + fv) / pmt
    # (1 + r)^n = 1 + x with x = -r (PV + FV) / (PV r + PMT (1 + r d)): the
    # rate multiplies rather than divides, so a tiny rate keeps its digits.
    denominator = pv * rate + pmt * (1 + rate * due)
    growth = -rate * (pv + fv) / denominator if denominator else math.nan
    if not (math.isfinite(growth) and growth > -1):
        msg = "no number of periods balances these cash flows at this rate"
        raise DomainError(msg)
    return math.log1p(growth) / math.log1p(rate)


def _payment_factors(rate: float, periods: float, *, due: bool) -> tuple[float, float]:
    """Return ``1 / a`` and ``v^n / a``, the payment per unit of PV and of FV.

    Both are formed without the annuity factor ``a`` itself, which overflows
    at a strongly negative rate where the payment is still finite.
    """
    timing = (1 + rate) if due else 1.0
    if rate == 0:
        return 1 / (periods * timing), 1 / (periods * timing)
    exponent = periods * math.log1p(rate)
    per_present = 0.0 if -exponent > LOG_MAX else rate / -math.expm1(-exponent)
    per_future = 0.0 if exponent > LOG_MAX else rate / math.expm1(exponent)
    return per_present / timing, per_future / timing


def _solve(inputs: SolveInputs) -> SolveOutputs:
    target: Solvable = next(n for n in _SOLVABLE if getattr(inputs, n) is None)
    terms = {
        name: 0.0 if (value := getattr(inputs, name)) is None else float(value)
        for name in _SOLVABLE
    }
    n, rate, due = terms["periods"], terms["rate"], inputs.due
    pv, pmt, fv = terms["present_value"], terms["payment"], terms["future_value"]
    low, high = -MONEY_OUT, MONEY_OUT
    if target == "rate":
        solved = _solve_rate(n, pv, pmt, fv, due=due)
        low, high = RATE_MIN, _PERIODIC_RATE_MAX
    elif target == "periods":
        solved = _solve_periods(rate, pv, pmt, fv, due=due)
        low, high = 0.0, float(PERIODS_MAX)
    elif target == "future_value" and rate != 0:
        # PV g + L (g - 1) with L = PMT (1 + r d) / r, grouped as (PV + L) g - L
        # so that two infinite terms of opposite sign never meet.
        level = pmt * (1 + rate * due) / rate
        solved = -(scaled(pv + level, growth_factor(rate, n)) - level)
    elif target == "future_value":
        solved = -(pv + pmt * n)
    elif target == "present_value":
        solved = -(
            scaled(fv, present_value_factor(rate, n))
            + scaled(pmt, annuity_factor(rate, n, due=due))
        )
    else:
        if n == 0:
            msg = "over zero periods no payment is made"
            raise DomainError(msg)
        per_present, per_future = _payment_factors(rate, n, due=due)
        solved = -(pv * per_present + fv * per_future)
    terms[target] = bounded(solved, low, high, target.replace("_", " "))
    return SolveOutputs(
        solved_for=target,
        periods=terms["periods"],
        rate=terms["rate"],
        present_value=terms["present_value"],
        payment=terms["payment"],
        future_value=terms["future_value"],
    )


def _npv(inputs: NpvInputs) -> NpvOutputs:
    value = present_value(inputs.rate, inputs.cash_flows)
    return NpvOutputs(npv=bounded(value, -MONEY_OUT, MONEY_OUT, "npv"))


def _irr(inputs: IrrInputs) -> IrrOutputs:
    return IrrOutputs(
        irr=internal_rate_of_return(inputs.cash_flows),
        sign_changes=sign_changes(inputs.cash_flows),
    )


def _years(dates: tuple[dt.date, ...]) -> list[float]:
    return [year_fraction(dates[0], day, DayCount.ACT_365_FIXED) for day in dates]


def _xnpv(inputs: XnpvInputs) -> XnpvOutputs:
    value = present_value(inputs.rate, inputs.cash_flows, _years(inputs.dates))
    return XnpvOutputs(xnpv=bounded(value, -MONEY_OUT, MONEY_OUT, "xnpv"))


def _xirr(inputs: XirrInputs) -> XirrOutputs:
    return XirrOutputs(
        xirr=internal_rate_of_return(inputs.cash_flows, _years(inputs.dates)),
        sign_changes=sign_changes(inputs.cash_flows),
    )


def _remaining(rate: float, periods: int, elapsed: int) -> float:
    """Return the balance left after ``elapsed`` of ``periods`` payments, per unit.

    It is ``a(r, n - k) / a(r, n)``, the present value of the payments still
    due over that of all of them, formed so that neither factor overflows.
    """
    if rate == 0:
        return (periods - elapsed) / periods
    log_growth = math.log1p(rate)
    if rate > 0:
        return math.expm1(-(periods - elapsed) * log_growth) / math.expm1(
            -periods * log_growth
        )
    early, late = elapsed * log_growth, periods * log_growth
    return (math.expm1(early) - math.expm1(late)) / -math.expm1(late)


def _amortization(inputs: AmortizationInputs) -> AmortizationOutputs:
    principal, rate, n = inputs.principal, inputs.rate, inputs.periods
    level = principal / annuity_factor(rate, n)
    balances = [principal * _remaining(rate, n, k) for k in range(n + 1)]
    balances[-1] = 0.0
    interest = [rate * balances[k] for k in range(n)]
    repaid = [balances[k] - balances[k + 1] for k in range(n)]
    payments = [i + p for i, p in zip(interest, repaid, strict=True)]
    return AmortizationOutputs(
        level_payment=level,
        total_interest=math.fsum(interest),
        period=tuple(range(1, n + 1)),
        payment=tuple(payments),
        interest=tuple(interest),
        principal=tuple(repaid),
        balance=tuple(balances[1:]),
    )


# --- the model ---------------------------------------------------------------

_KELLISON = Reference(
    key="kellison2009",
    citation=(
        "Kellison, S. G. (2009). The Theory of Interest, 3rd ed. McGraw-Hill/Irwin."
    ),
    url="https://openlibrary.org/isbn/9780073382449",
    isbn="9780073382449",
    locator="Chapters 3-5 (annuities, varying annuities, amortization schedules)",
)
_XIRR = Reference(
    key="microsoft_xirr",
    citation="Microsoft (n.d.). XIRR function. Microsoft Support.",
    url="https://support.microsoft.com/en-us/office/xirr-function-de1242ec-6477-445b-b11b-a303ad9adc9d",
    locator="Remarks (the XIRR equation) and Example",
)
_XNPV = Reference(
    key="microsoft_xnpv",
    citation="Microsoft (n.d.). XNPV function. Microsoft Support.",
    url="https://support.microsoft.com/en-us/office/xnpv-function-1b42bbf6-370f-4532-a0eb-d67c16b664b7",
    locator="Description (the XNPV equation) and Example",
)


@model(
    id="foundations.time_value",
    version=2,
    title="Time value of money",
    summary=(
        "Present and future values of sums, annuities and perpetuities, the "
        "five-key solve, NPV, IRR, XNPV, XIRR and amortization schedules."
    ),
    formula=(
        (
            r"PV = \frac{FV}{(1+r)^n}"
            r" + PMT\,\frac{1 - \left(\frac{1+g}{1+r}\right)^n}{r - g}\,(1+r)^{d}"
        ),
        r"FV = PV (1+r)^n + PMT\,\frac{(1+r)^n - (1+g)^n}{r - g}\,(1+r)^{d}",
        r"PV_{\infty} = \frac{PMT}{r - g}\,(1+r)^{d}, \quad r > g",
        r"PV (1+r)^n + PMT (1 + r d) \frac{(1+r)^n - 1}{r} + FV = 0",
        r"NPV = \sum_{t=0}^{T} \frac{C_t}{(1+r)^t}, \quad NPV(IRR) = 0",
        r"XNPV = \sum_i \frac{C_i}{(1+r)^{(d_i - d_0)/365}}, \quad XNPV(XIRR) = 0",
        r"PMT = \frac{P\,r}{1 - (1+r)^{-n}}, \quad B_k = P\,\frac{a_{n-k}}{a_n}",
    ),
    assumptions=(
        (
            "The rate is constant and compounds once per period; payments fall at "
            "the end of each period, or at its start when due is true (d = 1)."
        ),
        (
            "A growing payment grows by the same rate each period, starting from "
            "the payment given for the first period."
        ),
        (
            "solve follows the cash-flow sign convention: money paid out is "
            "negative, and the equation balances to zero."
        ),
        (
            "npv and irr place the first cash flow at time 0, undiscounted; xnpv and "
            "xirr count years of 365 days from the first date (ACT/365 Fixed)."
        ),
        (
            "An IRR is the smallest root in its bracket (ADR-0008 decision 11); the "
            "scan steps by 0.01, so two roots closer than that can be seen as none."
        ),
    ),
    limitations=(
        (
            "A result outside its output's bounds (for example a sum compounded at "
            "100% a period for a thousand periods) raises DomainError."
        ),
        (
            "A perpetuity needs a rate above its growth rate and no final sum, or "
            "DomainError is raised."
        ),
        (
            "solve raises DomainError when no value of the omitted term balances "
            "the cash flows (no rate in [-0.99, 1] per period, no non-negative "
            "number of periods, or a payment over zero periods)."
        ),
        (
            "An IRR or XIRR is null with a warning when the cash flows never change "
            "sign or no root lies in [-0.99, 10]."
        ),
        (
            "Taxes, fees, inflation and day-count conventions other than ACT/365 "
            "Fixed are out of scope."
        ),
    ),
    references=(_KELLISON, _XNPV, _XIRR),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    tags=("time value", "annuity", "npv", "irr", "amortization"),
    invariants=(
        Invariant(
            id="pv_fv_inverse",
            statement=(
                "Compounding a present value for the same rate and periods "
                "returns the future value it was discounted from."
            ),
        ),
        Invariant(
            id="npv_zero_at_irr",
            statement="The NPV at the IRR is zero, within the root tolerance.",
        ),
        Invariant(
            id="npv_decreasing_in_rate",
            statement=(
                "For conventional cash flows (outflows, then inflows), the NPV "
                "falls as the rate rises."
            ),
        ),
        Invariant(
            id="annuity_due_ratio",
            statement=(
                "An annuity due is worth (1 + r) times the same annuity in arrears."
            ),
        ),
        Invariant(
            id="amortization_ends_at_zero",
            statement=(
                "An amortization schedule ends at a zero balance, and its "
                "principal repayments sum to the principal."
            ),
        ),
    ),
    examples=(
        Example(
            name="monthly_annuity",
            inputs={
                "calculation": "present_value",
                "rate": 0.08 / 12,
                "periods": 240,
                "payment": 500,
            },
            note="Twenty years of $500 a month at 8% a year.",
        ),
        Example(
            name="savings_with_deposits",
            inputs={
                "calculation": "future_value",
                "rate": 0.005,
                "periods": 10,
                "payment": 200,
                "present_value": 500,
                "due": True,
            },
        ),
        Example(
            name="loan_rate",
            inputs={
                "calculation": "solve",
                "periods": 48,
                "payment": -200,
                "present_value": 8000,
                "future_value": 0,
            },
            note="The monthly rate of a four-year loan of 8,000 repaid at 200.",
        ),
        Example(
            name="project_npv",
            inputs={
                "calculation": "npv",
                "rate": 0.1,
                "cash_flows": [-70000, 12000, 15000, 18000, 21000, 26000],
            },
        ),
        Example(
            name="project_irr",
            inputs={
                "calculation": "irr",
                "cash_flows": [-70000, 12000, 15000, 18000, 21000, 26000],
            },
        ),
        Example(
            name="dated_npv",
            inputs={
                "calculation": "xnpv",
                "rate": 0.09,
                "cash_flows": [-10000, 2750, 4250, 3250, 2750],
                "dates": [
                    "2008-01-01",
                    "2008-03-01",
                    "2008-10-30",
                    "2009-02-15",
                    "2009-04-01",
                ],
            },
        ),
        Example(
            name="dated_irr",
            inputs={
                "calculation": "xirr",
                "cash_flows": [-10000, 2750, 4250, 3250, 2750],
                "dates": [
                    "2008-01-01",
                    "2008-03-01",
                    "2008-10-30",
                    "2009-02-15",
                    "2009-04-01",
                ],
            },
        ),
        Example(
            name="car_loan",
            inputs={
                "calculation": "amortization",
                "principal": 10000,
                "rate": 0.08 / 12,
                "periods": 10,
            },
        ),
    ),
    charts=(
        ChartSpec(
            id="balance",
            title="Loan balance after each payment",
            kind=ChartKind.LINE,
            x="period",
            y=("balance",),
            x_label="Payment",
            y_label="Balance",
            calculation="amortization",
        ),
    ),
    changelog=(
        ChangelogEntry(version=1, note="First version."),
        ChangelogEntry(
            version=2, note="Recognize IRR roots at inclusive bracket endpoints (#85)."
        ),
    ),
)
def time_value(inputs: TimeValueInputs) -> TimeValueOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], TimeValueOutputs]]] = {
    PresentValueInputs: _present_value,
    FutureValueInputs: _future_value,
    SolveInputs: _solve,
    NpvInputs: _npv,
    IrrInputs: _irr,
    XnpvInputs: _xnpv,
    XirrInputs: _xirr,
    AmortizationInputs: _amortization,
}
