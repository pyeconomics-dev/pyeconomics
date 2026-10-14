# src/pyeconomics/models/performance/return_measurement.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Portfolio returns with external cash flows: ``performance.return_measurement``.

Three calculations, discriminated on ``calculation``. A flow is external money:
positive when the client adds it, negative when the client withdraws it.

- ``time_weighted``: valuations :math:`V_0, \ldots, V_n` are taken just before
  each external flow, and flow :math:`F_k` enters just after valuation
  :math:`k`. Each sub-period returns :math:`r_k = V_k / (V_{k-1} + F_{k-1}) - 1`,
  and the time-weighted return links them geometrically:
  :math:`\prod (1 + r_k) - 1`. The flows' size and timing do not affect it.
- ``money_weighted``: the internal rate of return that makes the beginning
  value and the flows, compounded to the end, equal the ending value:
  :math:`V_0 (1 + r)^T + \sum F_k (1 + r)^{T - t_k} = V_T`. Flows are at times
  in periods, or on dates, when the rate is a year's under ACT/365 Fixed, as
  XIRR's is. It is :func:`~pyeconomics.core.internal_rate_of_return`.
- ``modified_dietz``: the day-weighted refinement of Dietz's (1966) method, the
  gain over the average capital invested, each flow weighted by the share of
  the period it was held:
  :math:`R = (V_1 - V_0 - \sum F_i) / (V_0 + \sum W_i F_i)` with
  :math:`W_i = (CD - D_i) / CD` for a flow :math:`D_i` days into a period of
  :math:`CD` calendar days.

Each is annualized when ``periods_per_year`` is given: a return :math:`R` over
:math:`k` periods becomes :math:`(1 + R)^{m / k} - 1`.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self, cast

from pydantic import Field, model_validator

from pyeconomics.core import (
    DEFAULT_DATE_BOUNDS,
    ChangelogEntry,
    CostClass,
    Count,
    DateArray,
    DateValue,
    DayCount,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Periods,
    PeriodsArray,
    Rate,
    Reference,
    Return,
    annualized_return,
    compound_return,
    internal_rate_of_return,
    log_return,
    model,
    warn,
    year_fraction,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.performance._common import (
    MONEY_IN,
    RETURN_MAX,
    SERIES_MAX,
    annualize,
    bounded,
    optional,
)

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable

__all__ = ["return_measurement"]

#: The most external flows a money-weighted or Dietz calculation takes.
_FLOWS_MAX: Final = 1_000
#: The longest span, in periods.
_SPAN_MAX: Final = 100_000.0
#: A compound return over a long span can pass 100 (10,000%): forty years at
#: 12.2% a year does. The span outputs widen the bound to 1e6 (100,000,000%).
_SPAN_RETURN_MAX: Final = 1e6
#: A Modified Dietz return is a ratio of a gain to an average capital, not a
#: compound return, so it can fall below -1 when withdrawals are weighted
#: lightly; it is held to [-100, 100].
_DIETZ_MIN: Final = -100.0

_Values = Annotated[
    tuple[Annotated[Money, Field(ge=0.0, le=MONEY_IN)], ...], ARRAY_INPUT
]
_Flows = Annotated[
    tuple[Annotated[Money, Field(ge=-MONEY_IN, le=MONEY_IN)], ...], ARRAY_INPUT
]
_SubReturns = Annotated[
    tuple[Annotated[Return, Field(ge=-1.0, le=RETURN_MAX)], ...], ARRAY_INPUT
]


def _value(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=MONEY_IN, description=description)


def _date(description: str, *default: None) -> Any:  # noqa: ANN401 - Field
    return Field(
        *default,
        ge=DEFAULT_DATE_BOUNDS.lower,
        le=DEFAULT_DATE_BOUNDS.upper,
        description=description,
    )


def _periods_per_year() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        None,
        gt=0,
        le=100_000,
        description="Periods in a year, such as 12, to annualize; omit not to",
    )


# --- inputs ------------------------------------------------------------------


class TimeWeightedInputs(ModelInputs):
    """Valuations before each external flow, and the flows."""

    calculation: Literal["time_weighted"] = Field(
        "time_weighted", description="Time-weighted return, linked geometrically"
    )
    values: _Values = Field(
        min_length=2,
        max_length=SERIES_MAX + 1,
        description=(
            "Portfolio values V0, V1, ..., Vn, each taken just before that date's "
            "external flow"
        ),
    )
    flows: _Flows = Field(
        (),
        max_length=SERIES_MAX,
        description=(
            "External flow just after each valuation but the last (one fewer than "
            "the values); positive adds money. Omit for none"
        ),
    )
    periods: Periods | None = Field(
        None,
        gt=0,
        le=_SPAN_MAX,
        description="Length of the span in periods; by default one per sub-period",
    )
    periods_per_year: Periods | None = _periods_per_year()

    @model_validator(mode="after")
    def _one_flow_per_sub_period(self) -> Self:
        if self.flows and len(self.flows) != len(self.values) - 1:
            msg = (
                f"give one flow per valuation but the last: {len(self.values)} "
                f"values need {len(self.values) - 1} flows, not {len(self.flows)}"
            )
            raise ValueError(msg)
        return self


class MoneyWeightedInputs(ModelInputs):
    """A beginning and ending value, and external flows at times or on dates."""

    calculation: Literal["money_weighted"] = Field(
        "money_weighted", description="Money-weighted return, an IRR"
    )
    beginning_value: Money = _value("Portfolio value at the start")
    ending_value: Money = _value("Portfolio value at the end")
    flows: _Flows = Field(
        (),
        max_length=_FLOWS_MAX,
        description="External flows in between; positive adds money",
    )
    periods: Periods | None = Field(
        None,
        gt=0,
        le=_SPAN_MAX,
        description="Periodic flows: the length of the span in periods",
    )
    flow_times: PeriodsArray = Field(
        (),
        max_length=_FLOWS_MAX,
        description="Periodic flows: when each flow occurs, in periods from the start",
    )
    start_date: DateValue | None = _date("Dated flows: the start", None)
    end_date: DateValue | None = _date("Dated flows: the end", None)
    flow_dates: DateArray = Field(
        (), max_length=_FLOWS_MAX, description="Dated flows: the date of each flow"
    )
    periods_per_year: Periods | None = _periods_per_year()

    @model_validator(mode="after")
    def _times_or_dates(self) -> Self:
        if self.start_date is not None or self.end_date is not None:
            problem = self._dated()
        else:
            problem = self._periodic()
        if problem is not None:
            raise ValueError(problem)
        return self

    def _dated(self) -> str | None:
        if self.start_date is None or self.end_date is None:
            return "dated flows need both start_date and end_date"
        if self.periods is not None or self.flow_times or self.periods_per_year:
            return (
                "dated flows give an annual rate; do not also give periods, "
                "flow_times or periods_per_year"
            )
        return _check_dates(self.flows, self.flow_dates, self.start_date, self.end_date)

    def _periodic(self) -> str | None:
        if self.flow_dates:
            return "flow_dates need start_date and end_date"
        if self.periods is None:
            return "give periods (or start_date and end_date for dated flows)"
        if len(self.flow_times) != len(self.flows):
            return (
                f"give one time per flow: {len(self.flows)} flows, "
                f"{len(self.flow_times)} times"
            )
        if any(t > self.periods for t in self.flow_times):
            return "every flow time must lie within the span, at most periods"
        return None


def _check_dates(
    flows: tuple[float, ...],
    dates: tuple[dt.date, ...],
    start: dt.date,
    end: dt.date,
) -> str | None:
    if end <= start:
        return "end_date must be after start_date"
    if len(dates) != len(flows):
        return f"give one date per flow: {len(flows)} flows, {len(dates)} dates"
    if any(not start <= day <= end for day in dates):
        return "every flow date must lie between start_date and end_date"
    return None


class ModifiedDietzInputs(ModelInputs):
    """A beginning and ending value, and dated external flows in between."""

    calculation: Literal["modified_dietz"] = Field(
        "modified_dietz", description="Modified Dietz return, day-weighted flows"
    )
    beginning_value: Money = _value("Portfolio value at the start")
    ending_value: Money = _value("Portfolio value at the end")
    start_date: DateValue = _date("Start of the period")
    end_date: DateValue = _date("End of the period")
    flows: _Flows = Field(
        (), max_length=_FLOWS_MAX, description="External flows; positive adds money"
    )
    flow_dates: DateArray = Field(
        (), max_length=_FLOWS_MAX, description="The date of each flow"
    )
    periods: Periods = Field(
        1.0,
        gt=0,
        le=_SPAN_MAX,
        description="Length of the period in periods, for annualizing",
    )
    periods_per_year: Periods | None = _periods_per_year()

    @model_validator(mode="after")
    def _dates_in_period(self) -> Self:
        problem = _check_dates(
            self.flows, self.flow_dates, self.start_date, self.end_date
        )
        if problem is not None:
            raise ValueError(problem)
        return self


ReturnMeasurementInputs = Annotated[
    TimeWeightedInputs | MoneyWeightedInputs | ModifiedDietzInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


def _annualized() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=-1.0,
        le=_SPAN_RETURN_MAX,
        description="Return compounded to a year; null without periods_per_year",
    )


class TimeWeightedOutputs(ModelOutputs):
    calculation: Literal["time_weighted"] = Field(
        "time_weighted", description="Time-weighted return, linked geometrically"
    )
    sub_period_returns: _SubReturns = Field(
        max_length=SERIES_MAX, description="Return of each sub-period, in order"
    )
    time_weighted_return: Return = Field(
        ge=-1.0, le=_SPAN_RETURN_MAX, description="Linked return over the whole span"
    )
    annualized_return: Return | None = _annualized()


class MoneyWeightedOutputs(ModelOutputs):
    calculation: Literal["money_weighted"] = Field(
        "money_weighted", description="Money-weighted return, an IRR"
    )
    rate: Rate | None = Field(
        ge=-0.99,
        le=10.0,
        description=(
            "Money-weighted rate per period, or a year for dated flows; null when "
            "no rate in [-0.99, 10] solves it"
        ),
    )
    money_weighted_return: Return | None = Field(
        ge=-1.0,
        le=_SPAN_RETURN_MAX,
        description="The rate compounded over the whole span",
    )
    annualized_return: Return | None = Field(
        ge=-1.0,
        le=_SPAN_RETURN_MAX,
        description=(
            "Rate compounded to a year: the rate itself for dated flows; null for "
            "periodic flows without periods_per_year"
        ),
    )
    flow_count: Count = Field(ge=0, le=_FLOWS_MAX, description="Number of flows")


class ModifiedDietzOutputs(ModelOutputs):
    calculation: Literal["modified_dietz"] = Field(
        "modified_dietz", description="Modified Dietz return, day-weighted flows"
    )
    modified_dietz_return: Return = Field(
        ge=_DIETZ_MIN, le=RETURN_MAX, description="Gain over day-weighted capital"
    )
    # At most 1,000 flows of at most 1e12 on a beginning value of at most 1e12:
    # just past ADR-0008's money bound of 1e15.
    average_capital: Money = Field(
        gt=0.0,
        le=MONEY_IN * (1 + _FLOWS_MAX),
        description="Beginning value plus day-weighted flows: the denominator",
    )
    annualized_return: Return | None = _annualized()


ReturnMeasurementOutputs = Annotated[
    TimeWeightedOutputs | MoneyWeightedOutputs | ModifiedDietzOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _time_weighted(inputs: TimeWeightedInputs) -> TimeWeightedOutputs:
    values = inputs.values
    flows = inputs.flows or (0.0,) * (len(values) - 1)
    returns: list[float] = []
    for k in range(1, len(values)):
        base = values[k - 1] + flows[k - 1]
        if base <= 0:
            msg = (
                f"sub-period {k} starts with {base!r} invested (value plus flow), "
                "so it has no return"
            )
            raise DomainError(msg)
        returns.append(
            bounded(
                values[k] / base - 1.0, -1.0, RETURN_MAX, f"return of sub-period {k}"
            )
        )
    total = bounded(
        compound_return(returns), -1.0, _SPAN_RETURN_MAX, "time-weighted return"
    )
    span = inputs.periods or float(len(returns))
    return TimeWeightedOutputs(
        sub_period_returns=tuple(returns),
        time_weighted_return=total,
        annualized_return=annualize(
            log_return(returns), span, inputs.periods_per_year, _SPAN_RETURN_MAX
        ),
    )


def _money_weighted(inputs: MoneyWeightedInputs) -> MoneyWeightedOutputs:
    dated = inputs.start_date is not None and inputs.end_date is not None
    if inputs.start_date is not None and inputs.end_date is not None:
        start = inputs.start_date
        span = year_fraction(start, inputs.end_date, DayCount.ACT_365_FIXED)
        times = [
            year_fraction(start, day, DayCount.ACT_365_FIXED)
            for day in inputs.flow_dates
        ]
    else:
        span = cast("float", inputs.periods)  # the validator set it
        times = list(inputs.flow_times)
    # The client's view: money in is paid out, the ending value received.
    cash = [-inputs.beginning_value, *(-f for f in inputs.flows), inputs.ending_value]
    rate = internal_rate_of_return(cash, [0.0, *times, span])
    total = annual = None
    if rate is not None:
        total = optional(
            annualized_return(rate, 1.0, span),
            -1.0,
            _SPAN_RETURN_MAX,
            "money-weighted return",
        )
        annual = (
            rate
            if dated
            else annualize(
                math.log1p(rate), 1.0, inputs.periods_per_year, _SPAN_RETURN_MAX
            )
        )
    return MoneyWeightedOutputs(
        rate=rate,
        money_weighted_return=total,
        annualized_return=annual,
        flow_count=len(inputs.flows),
    )


def _modified_dietz(inputs: ModifiedDietzInputs) -> ModifiedDietzOutputs:
    days = (inputs.end_date - inputs.start_date).days
    weights = [
        (days - (day - inputs.start_date).days) / days for day in inputs.flow_dates
    ]
    net = math.fsum(inputs.flows)
    capital = inputs.beginning_value + math.fsum(
        w * f for w, f in zip(weights, inputs.flows, strict=True)
    )
    if capital <= 0:
        msg = (
            f"the day-weighted capital is {capital!r}: with no money invested on "
            "average, the period has no Modified Dietz return"
        )
        raise DomainError(msg)
    gain = inputs.ending_value - inputs.beginning_value - net
    result = bounded(gain / capital, _DIETZ_MIN, RETURN_MAX, "Modified Dietz return")
    if result < -1:
        warn(
            "not_annualized",
            f"a return of {result!r}, below -100%, cannot be compounded to a year",
        )
        annual = None
    else:
        annual = annualize(
            log_return([result]),
            inputs.periods,
            inputs.periods_per_year,
            _SPAN_RETURN_MAX,
        )
    return ModifiedDietzOutputs(
        modified_dietz_return=result,
        average_capital=capital,
        annualized_return=annual,
    )


# --- the model ---------------------------------------------------------------

_BACON = Reference(
    key="bacon2008",
    citation=(
        "Bacon, C. R. (2008). Practical Portfolio Performance Measurement and "
        "Attribution, 2nd ed. Wiley."
    ),
    doi="10.1002/9781119206309.ch2",
    isbn="9780470059289",
    locator=(
        "Chapter 2, pp. 5-37: time-weighted and money-weighted returns, and "
        "the day-weighted (Modified) Dietz method"
    ),
)
_DIETZ = Reference(
    key="dietz1966",
    citation=(
        "Dietz, P. O. (1966). Pension Funds: Measuring Investment Performance. "
        "Free Press."
    ),
    url="https://openlibrary.org/works/OL159516W",
    locator=(
        "The return as gain over average capital invested, flows held for "
        "part of the period (LCCN 66012080)"
    ),
)
_XIRR = Reference(
    key="microsoft_xirr",
    citation="Microsoft. XIRR function (Excel), the dated internal rate of return.",
    url="https://support.microsoft.com/en-us/office/xirr-function-de1242ec-6477-445b-b11b-a303ad9adc9d",
    locator="Description and example",
)


@model(
    id="performance.return_measurement",
    version=2,
    title="Return measurement",
    summary=(
        "Time-weighted, money-weighted and Modified Dietz returns of a portfolio "
        "with external cash flows, optionally annualized."
    ),
    formula=(
        r"r_k = \frac{V_k}{V_{k-1} + F_{k-1}} - 1, \quad TWR = \prod_k (1 + r_k) - 1",
        r"V_0 (1 + r)^T + \sum_k F_k (1 + r)^{T - t_k} = V_T",
        (
            r"R_{MD} = \frac{V_1 - V_0 - \sum_i F_i}{V_0 + \sum_i W_i F_i}, \quad "
            r"W_i = \frac{CD - D_i}{CD}"
        ),
        r"R_{annual} = (1 + R)^{m / k} - 1",
    ),
    assumptions=(
        (
            "External flows are positive when money is added and negative when it "
            "is withdrawn; values are market values including income."
        ),
        (
            "Time-weighted valuations are taken just before each flow; by default "
            "every sub-period is one period long, for annualizing."
        ),
        (
            "Dated money-weighted flows count years as ACT/365 Fixed, as XIRR does, "
            "so their rate is already a year's. A Modified Dietz flow on a given "
            "day is held for the rest of the period from that day."
        ),
    ),
    limitations=(
        (
            "A sub-period that starts with no money invested, or a Modified Dietz "
            "period with no average capital, raises DomainError; so does a return "
            "beyond its bounds."
        ),
        (
            "The money-weighted rate is null, with a warning, when no rate in "
            "[-0.99, 10] solves it; with several, the smallest is reported."
        ),
        (
            "Modified Dietz approximates the true time-weighted return; it is "
            "exact only when no flows occur. Annualizing a span shorter than a "
            "year extrapolates it."
        ),
    ),
    references=(_BACON, _DIETZ, _XIRR),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("returns", "time-weighted", "money-weighted", "modified dietz", "irr"),
    invariants=(
        Invariant(
            id="time_and_money_weighted_agree_without_flows",
            statement=(
                "With no external flows, the time-weighted and money-weighted "
                "returns over a span are equal, both V_n / V_0 - 1."
            ),
        ),
        Invariant(
            id="modified_dietz_equals_simple_return_without_flows",
            statement=(
                "With no external flows, the Modified Dietz return is V_1 / V_0 - 1."
            ),
        ),
        Invariant(
            id="time_weighted_ignores_flow_size",
            statement=(
                "Scaling every value and flow by the same positive factor leaves "
                "the time-weighted return unchanged."
            ),
        ),
    ),
    examples=(
        Example(
            name="quarter_with_a_contribution",
            inputs={
                "calculation": "time_weighted",
                "values": [1000, 1050, 1180, 1250],
                "flows": [0, 100, 0],
                "periods_per_year": 12,
            },
        ),
        Example(
            name="dated_money_weighted",
            inputs={
                "calculation": "money_weighted",
                "beginning_value": 10000,
                "ending_value": 2750,
                "flows": [-2750, -4250, -3250],
                "start_date": "2008-01-01",
                "end_date": "2009-04-01",
                "flow_dates": ["2008-03-01", "2008-10-30", "2009-02-15"],
            },
        ),
        Example(
            name="month_with_a_contribution",
            inputs={
                "calculation": "modified_dietz",
                "beginning_value": 1000,
                "ending_value": 1300,
                "start_date": "2026-04-01",
                "end_date": "2026-05-01",
                "flows": [200],
                "flow_dates": ["2026-04-16"],
                "periods_per_year": 12,
            },
        ),
    ),
    changelog=(
        ChangelogEntry(version=1, note="First version."),
        ChangelogEntry(
            version=2, note="Recognize IRR roots at inclusive bracket endpoints (#85)."
        ),
    ),
)
def return_measurement(inputs: ReturnMeasurementInputs) -> ReturnMeasurementOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[ModelInputs], Callable[[Any], ReturnMeasurementOutputs]]
] = {
    TimeWeightedInputs: _time_weighted,
    MoneyWeightedInputs: _money_weighted,
    ModifiedDietzInputs: _modified_dietz,
}
