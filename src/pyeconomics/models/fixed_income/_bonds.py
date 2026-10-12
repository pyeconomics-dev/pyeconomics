# src/pyeconomics/models/fixed_income/_bonds.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Bond terms, their cash flows and their prices: what the bond models share.

A bond's coupon dates step back from its maturity by whole periods (the
maturity anchors every date, so month ends do not drift). Interest accrues from
the previous coupon date, or from the issue date in the first coupon period,
which may be short (the stub before the first coupon date) or long (the stub
and the regular period after it). A regular coupon pays ``c / f`` of the face
value; the first coupon of an irregular period pays the year fraction of the
period under the bond's day count, so under ACT/ACT (ICMA) a short first coupon
is ``(r / s)(c / f)`` and a long one ``(1 + r / s)(c / f)``, as 31 CFR Part 356,
Appendix B, section I sets out for Treasury notes and bonds.

Time is counted in coupon periods from settlement. The time to the first
payment is its period less the part already accrued (``DSC = E - A``): under
ACT/ACT (ICMA), the days left over the days in the period. Its fractional part
:math:`w` is what remains of the period holding settlement; in the stub of a long
first period, the regular period after the stub is still to come in full. Each
later payment is a whole period after the one before. Two yield conventions
discount over those times, with :math:`v = 1 / (1 + y / f)`:

- **street**: :math:`P = \sum_j CF_j \, v^{t_j}`, compound over the fraction too;
- **treasury**: :math:`P = \sum_j CF_j \, v^{t_j - w} / (1 + w y / f)`, simple
  interest over the fraction, the formula of 31 CFR Part 356, Appendix B,
  section II.

Both agree when settlement falls on a coupon date. Nothing here does I/O.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, Annotated, Final, Literal, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    DEFAULT_DATE_BOUNDS,
    DateValue,
    DayCount,
    DomainError,
    Frequency,
    ModelInputs,
    Money,
    Rate,
    Years,
    add_months,
    find_root,
    interpolate_rates,
    year_fraction,
)
from pyeconomics.core.errors import ConvergenceError
from pyeconomics.core.model import ARRAY_INPUT

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = [
    "CURVE_MAX",
    "EARLIEST",
    "FACE_MAX",
    "FACE_MIN",
    "KEYS_MAX",
    "LATEST",
    "MAX_TERM_DAYS",
    "MONEY_OUT",
    "PAYMENTS_MAX",
    "YIELD_MAX",
    "YIELD_MIN",
    "BondTerms",
    "Convention",
    "CurveTerms",
    "DayCountName",
    "Flows",
    "FrequencyName",
    "bond_flows",
    "bounded",
    "convexity",
    "curve_price",
    "key_rate_shift",
    "macaulay_duration",
    "payment_dates",
    "price",
    "solve_yield",
]

#: The earliest date a bond input takes: two years after ADR-0008's lower date
#: bound, so the coupon dates the schedule looks back to are in bounds too.
EARLIEST: Final = dt.date(1902, 1, 1)
#: The latest date any input or output takes: ADR-0008's upper date bound.
LATEST: Final = DEFAULT_DATE_BOUNDS.upper
#: The longest time from settlement to maturity: 100 years of days.
MAX_TERM_DAYS: Final = 36_525
#: The most payments a bond has after settlement: 100 years of monthly coupons.
PAYMENTS_MAX: Final = 1_201
#: The yields the models take and solve for, per year, compounded at the
#: coupon frequency. The lower end keeps every discount factor finite.
YIELD_MIN: Final = -0.1
YIELD_MAX: Final = 1.0
#: The smallest and largest face values, and the most money an output holds.
FACE_MIN: Final = 0.01
FACE_MAX: Final = 1e9
MONEY_OUT: Final = 1e15

type FrequencyName = Literal["annual", "semiannual", "quarterly", "monthly"]
type DayCountName = Literal["act_act_icma", "thirty_360_us", "thirty_e_360"]
type Convention = Literal["street", "treasury"]

_FREQUENCIES: Final[dict[str, Frequency]] = {
    "annual": Frequency.ANNUAL,
    "semiannual": Frequency.SEMIANNUAL,
    "quarterly": Frequency.QUARTERLY,
    "monthly": Frequency.MONTHLY,
}
_DAY_COUNTS: Final[dict[str, DayCount]] = {
    "act_act_icma": DayCount.ACT_ACT_ICMA,
    "thirty_360_us": DayCount.THIRTY_360_US,
    "thirty_e_360": DayCount.THIRTY_E_360,
}


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


class BondTerms(ModelInputs):
    """The terms of a fixed-coupon bond and the date it settles."""

    settlement: DateValue = Field(
        ge=EARLIEST,
        le=LATEST,
        description="Settlement date: the price is for this date",
    )
    maturity: DateValue = Field(
        ge=EARLIEST,
        le=LATEST,
        description="Maturity date: the last coupon and redemption",
    )
    coupon_rate: Rate = Field(
        ge=0.0, le=1.0, description="Annual coupon rate, paid in equal parts"
    )
    frequency: FrequencyName = Field(
        "semiannual", description="Coupons per year (also the yield's compounding)"
    )
    day_count: DayCountName = Field(
        "act_act_icma", description="Day count for accrued interest and stubs"
    )
    face_value: Money = Field(
        100.0, ge=FACE_MIN, le=FACE_MAX, description="Face (par) value held"
    )
    redemption: Money = Field(
        100.0,
        ge=1.0,
        le=200.0,
        description="Amount repaid at maturity per 100 of face value",
    )
    issue_date: DateValue | None = Field(
        None,
        ge=EARLIEST,
        le=LATEST,
        description=(
            "Date interest starts to accrue, when the first coupon period is "
            "irregular; omitted (null) for a regular schedule"
        ),
    )
    first_period: Literal["short", "long"] = Field(
        "short",
        description=(
            "Whether an irregular first period ends at the first coupon date "
            "after the issue date (short) or at the one after that (long)"
        ),
    )
    end_of_month: bool = Field(
        default=True,
        description="Keep coupon dates at month ends when the maturity is one",
    )

    @model_validator(mode="after")
    def _consistent_dates(self) -> Self:
        problem = _date_problem(self)
        if problem is not None:
            raise ValueError(problem)
        return self


@dataclass(frozen=True, slots=True)
class Flows:
    """A bond's payments after settlement, and what accrued before it."""

    dates: tuple[dt.date, ...]
    """Payment dates after settlement, in order."""
    amounts: tuple[float, ...]
    """Each payment: the coupon, and at the end the redemption too."""
    times: tuple[float, ...]
    """Each payment's time from settlement, in coupon periods."""
    fraction: float
    """The fraction of a period from settlement to the end of its period."""
    accrued: float
    """Interest accrued from the start of the period to settlement."""
    periods_per_year: int
    """Coupons per year."""


@dataclass(frozen=True, slots=True)
class _Schedule:
    grid: Callable[[int], dt.date]
    next_index: int
    """Index of the first coupon date after settlement (0 is the maturity)."""
    stub_index: int | None
    """Index of the first coupon date after the issue date, if irregular."""


def _period(terms: BondTerms) -> tuple[Frequency, int]:
    frequency = _FREQUENCIES[terms.frequency]
    return frequency, 12 // frequency.periods_per_year


def _schedule(terms: BondTerms) -> _Schedule:
    _, months = _period(terms)
    maturity, eom = terms.maturity, terms.end_of_month

    def grid(index: int) -> dt.date:
        return add_months(maturity, -index * months, end_of_month=eom)

    index = 0
    while grid(index + 1) > terms.settlement:
        index += 1
    stub = None
    issue = terms.issue_date
    # Only an issue date within two periods of settlement can leave settlement
    # inside the first coupon period; an earlier one changes nothing.
    if issue is not None and issue > grid(index + 2):
        before = index + 1
        while grid(before) > issue:
            before += 1
        if grid(before) != issue:
            stub = before - 1
    return _Schedule(grid, index, stub)


def _date_problem(terms: BondTerms) -> str | None:
    """Say why the dates cannot describe a bond, or return ``None``."""
    if terms.settlement >= terms.maturity:
        return "settlement must be before maturity"
    if (terms.maturity - terms.settlement).days > MAX_TERM_DAYS:
        return "maturity must be at most 100 years after settlement"
    if terms.issue_date is not None and terms.issue_date > terms.settlement:
        return "the issue date must not be after settlement"
    schedule = _schedule(terms)
    if terms.first_period == "long" and schedule.stub_index == 0:
        return (
            "a long first period needs a regular coupon period after the stub; "
            "the first coupon date after the issue date is the maturity"
        )
    return None


def _fraction(
    start: dt.date,
    end: dt.date,
    day_count: DayCount,
    reference: tuple[dt.date, dt.date],
    frequency: Frequency,
) -> float:
    """Return the coupon periods from ``start`` to ``end`` within one period."""
    if day_count is DayCount.ACT_ACT_ICMA:
        fraction = year_fraction(
            start,
            end,
            day_count,
            reference_start=reference[0],
            reference_end=reference[1],
            frequency=frequency,
        )
    else:
        fraction = year_fraction(start, end, day_count)
    return frequency.periods_per_year * fraction


def _span(
    start: dt.date,
    end: dt.date,
    cuts: Sequence[dt.date],
    fraction: Callable[..., float],
) -> float:
    """Sum the period fractions from ``start`` to ``end`` across grid dates.

    ``cuts`` are increasing grid dates; each piece is measured against the
    regular period it lies in, so a long stub counts notional periods exactly.
    """
    total = 0.0
    edges = [start, *(c for c in cuts if start < c < end), end]
    for left, right in pairwise(edges):
        total += fraction(left, right)
    return total


def bond_flows(
    terms: BondTerms,
    *,
    until: dt.date | None = None,
    redemption: float | None = None,
) -> Flows:
    """Return the bond's payments after settlement and its accrued interest.

    Parameters
    ----------
    terms
        The bond.
    until
        A payment date to end the flows at instead of the maturity (a call
        date); :func:`payment_dates` lists the dates it may be.
    redemption
        The amount repaid at the last date, per 100 of face value; the bond's
        own redemption by default.
    """
    frequency, _ = _period(terms)
    f = frequency.periods_per_year
    day_count = _DAY_COUNTS[terms.day_count]
    schedule = _schedule(terms)
    grid = schedule.grid
    face, coupon = terms.face_value, terms.coupon_rate
    regular = face * coupon / f
    settlement = terms.settlement

    def piece(left: dt.date, right: dt.date) -> float:
        # The grid period that holds [left, right] is its reference period.
        index = 0
        while grid(index + 1) > left:
            index += 1
        return _fraction(
            left, right, day_count, (grid(index + 1), grid(index)), frequency
        )

    first = schedule.next_index
    issue, stub = terms.issue_date, schedule.stub_index
    long_first = terms.first_period == "long"
    first_coupon = None if stub is None else stub - 1 if long_first else stub
    if (
        stub is not None
        and first_coupon is not None
        and issue is not None
        and settlement < grid(first_coupon)
    ):
        # Settlement falls in an irregular first period, which accrues from the
        # issue date; a long one spans the stub and the period after it.
        first = first_coupon
        # ICMA needs each notional reference period. 30/360 measures the whole
        # accrual interval: its endpoint adjustments need not be additive at
        # an intervening grid date (for example May 30 -> May 31).
        cuts = [grid(stub)] if day_count is DayCount.ACT_ACT_ICMA else []
        period = _span(issue, grid(first), cuts, piece)
        elapsed = _span(issue, settlement, cuts, piece)
        first_amount = face * coupon * period / f
        accrued = face * coupon * elapsed / f
        # In the stub of a long first period, the regular period after it is
        # still to run in full before the first payment.
        regular_part = (
            piece(grid(stub), grid(first))
            if long_first and settlement < grid(stub)
            else 0.0
        )
    else:
        start = grid(first + 1)
        first_amount = regular
        period = piece(start, grid(first))
        elapsed = piece(start, settlement)
        accrued = face * coupon * elapsed / f
        regular_part = 0.0
    # The time to the first payment is the period less the part accrued (DSC = E
    # - A); under ACT/ACT that is the days left over the days in the period.
    # Under 30/360, E is the period's own 30/360 count, as QuantLib takes it;
    # the SIA rule fixes E at 360/f, which differs only for a period touching a
    # February month end.
    first_time = period - elapsed
    return _assemble(
        terms,
        grid=grid,
        first=first,
        first_amount=first_amount,
        regular=regular,
        first_time=first_time,
        fraction=first_time - regular_part,
        accrued=accrued,
        until=until,
        redemption=redemption,
    )


def _assemble(  # noqa: PLR0913 - the parts bond_flows has worked out
    terms: BondTerms,
    *,
    grid: Callable[[int], dt.date],
    first: int,
    first_amount: float,
    regular: float,
    first_time: float,
    fraction: float,
    accrued: float,
    until: dt.date | None,
    redemption: float | None,
) -> Flows:
    dates = [grid(index) for index in range(first, -1, -1)]
    if until is not None:
        dates = dates[: dates.index(until) + 1]
    amounts = [first_amount] + [regular] * (len(dates) - 1)
    repaid = terms.redemption if redemption is None else redemption
    amounts[-1] += terms.face_value * repaid / 100.0
    times = tuple(first_time + j for j in range(len(dates)))
    return Flows(
        dates=tuple(dates),
        amounts=tuple(amounts),
        times=times,
        fraction=fraction,
        accrued=accrued,
        periods_per_year=_FREQUENCIES[terms.frequency].periods_per_year,
    )


def payment_dates(terms: BondTerms) -> tuple[dt.date, ...]:
    """Return the bond's payment dates after settlement."""
    return bond_flows(terms).dates


def price(flows: Flows, yield_: float, convention: Convention = "street") -> float:
    """Return the full (dirty) price of the flows at a yield.

    The yield is per year, compounded at the coupon frequency, and above
    ``-f``; every bond model keeps it within ``[-0.15, 1.05]``.
    """
    f = flows.periods_per_year
    log_v = -math.log1p(yield_ / f)
    if convention == "street":
        return math.fsum(
            a * math.exp(t * log_v)
            for a, t in zip(flows.amounts, flows.times, strict=True)
        )
    w = flows.fraction
    total = math.fsum(
        a * math.exp((t - w) * log_v)
        for a, t in zip(flows.amounts, flows.times, strict=True)
    )
    return total / (1.0 + w * yield_ / f)


def macaulay_duration(flows: Flows, yield_: float) -> tuple[float, float]:
    """Return the full price and the Macaulay duration in years (street)."""
    f = flows.periods_per_year
    log_v = -math.log1p(yield_ / f)
    values = [
        a * math.exp(t * log_v) for a, t in zip(flows.amounts, flows.times, strict=True)
    ]
    full = math.fsum(values)
    weighted = math.fsum(t * pv for t, pv in zip(flows.times, values, strict=True))
    return full, weighted / full / f


def convexity(flows: Flows, yield_: float) -> float:
    """Return the convexity, ``P'' / P``, in years squared (street)."""
    f = flows.periods_per_year
    log_v = -math.log1p(yield_ / f)
    values = [
        a * math.exp(t * log_v) for a, t in zip(flows.amounts, flows.times, strict=True)
    ]
    weighted = math.fsum(
        t * (t + 1) * pv for t, pv in zip(flows.times, values, strict=True)
    )
    return weighted / math.fsum(values) / (f * f * (1 + yield_ / f) ** 2)


def solve_yield(
    flows: Flows, full_price: float, convention: Convention = "street"
) -> float:
    """Return the yield in ``[YIELD_MIN, YIELD_MAX]`` that gives the full price.

    Raises
    ------
    DomainError
        If no yield in that range gives the price.
    """
    try:
        found = find_root(
            lambda y: price(flows, y, convention) - full_price, YIELD_MIN, YIELD_MAX
        )
    except ConvergenceError as error:
        msg = (
            f"no yield in [{YIELD_MIN}, {YIELD_MAX}] gives a full price of "
            f"{full_price!r}: {error}"
        )
        raise DomainError(msg) from error
    return found.root


# --- pricing off a spot curve ------------------------------------------------

#: The most nodes a spot curve, or a set of key rates, takes.
CURVE_MAX: Final = 100
KEYS_MAX: Final = 30

_CurveTenors = Annotated[
    tuple[Annotated[Years, Field(gt=0.0, le=100.0)], ...], ARRAY_INPUT
]
_CurveRates = Annotated[
    tuple[Annotated[Rate, Field(ge=YIELD_MIN, le=YIELD_MAX)], ...], ARRAY_INPUT
]


def _increasing(values: Sequence[float]) -> bool:
    return all(later > earlier for earlier, later in pairwise(values))


class CurveTerms(BondTerms):
    """A bond and the spot curve it is priced off."""

    curve_tenors: _CurveTenors = Field(
        min_length=1,
        max_length=CURVE_MAX,
        description="Tenors of the spot curve's nodes, in years, increasing",
    )
    curve_rates: _CurveRates = Field(
        min_length=1,
        max_length=CURVE_MAX,
        description=(
            "Spot rate at each tenor, compounded at the coupon frequency; "
            "linear between nodes and flat beyond them"
        ),
    )
    bump: Rate = Field(
        0.0001,
        ge=1e-6,
        le=0.01,
        description="Shift of the curve up and down for the central difference",
    )

    @model_validator(mode="after")
    def _a_curve(self) -> Self:
        if len(self.curve_tenors) != len(self.curve_rates):
            msg = (
                f"give one spot rate per tenor: {len(self.curve_tenors)} tenors, "
                f"{len(self.curve_rates)} rates"
            )
            raise ValueError(msg)
        if not _increasing(self.curve_tenors):
            msg = "the curve tenors must be strictly increasing"
            raise ValueError(msg)
        return self


def curve_price(
    flows: Flows,
    tenors: Sequence[float],
    rates: Sequence[float],
    shift: Callable[[float], float] | None = None,
) -> float:
    """Return the full price of the flows off a spot curve, optionally shifted.

    Each payment at ``t`` years is discounted at the interpolated spot rate
    ``z(t)``, plus ``shift(t)``, compounded at the coupon frequency.
    """
    f = flows.periods_per_year
    years = [periods / f for periods in flows.times]
    curve = interpolate_rates(tenors, rates, years)
    total = []
    for amount, periods, t, rate in zip(
        flows.amounts, flows.times, years, curve, strict=True
    ):
        shifted = rate if shift is None else rate + shift(t)
        total.append(amount * math.exp(-periods * math.log1p(shifted / f)))
    return math.fsum(total)


def key_rate_shift(keys: Sequence[float], index: int) -> Callable[[float], float]:
    """Return the triangular shift of ``keys[index]``: 1 there, 0 at its neighbours.

    Below the first key and above the last, the end keys' shifts stay at 1, so
    the shifts of all the keys sum to a parallel shift of 1 at every time.
    """
    key = keys[index]
    below = keys[index - 1] if index > 0 else None
    above = keys[index + 1] if index + 1 < len(keys) else None

    def shift(years: float) -> float:
        if years <= key:
            if below is None:
                return 1.0
            return max(0.0, (years - below) / (key - below))
        if above is None:
            return 1.0
        return max(0.0, (above - years) / (above - key))

    return shift
