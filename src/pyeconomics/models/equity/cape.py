# src/pyeconomics/models/equity/cape.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The cyclically adjusted price-to-earnings ratio: ``equity.cape``.

Campbell and Shiller (1988, 1998) smooth earnings over the business cycle by
averaging ten years of real earnings. With the price :math:`P_t` and the price
index :math:`I_t` of month :math:`t`, and the earnings :math:`E_k` and price index
:math:`I_k` of the :math:`n` months before it (Shiller's file: the previous 120
months, not the current one), every value in the dollars of month :math:`t`,

.. math::

    \mathrm{CAPE}_t = \frac{P_t}{\bar E_t}, \qquad
    \bar E_t = \frac{1}{n} \sum_{k=t-n}^{t-1} E_k \frac{I_t}{I_k}.

The CAPE yield is its reciprocal, :math:`\bar E_t / P_t`, and the excess CAPE
yield is that less a real 10-year rate: a TIPS yield, or the nominal yield less
trailing inflation, :math:`(I_t / I_{t-n})^{m/n} - 1` for :math:`m` periods a
year, as Shiller's file computes it.
"""

from __future__ import annotations

import math
from typing import Annotated, Final, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    IndexLevel,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Rate,
    Ratio,
    Reference,
    model,
    warn,
)
from pyeconomics.core.model import ARRAY_INPUT

__all__ = ["cape"]

#: The longest window: forty years of months.
_WINDOW_MAX: Final = 480
#: Shiller's window: the previous ten years of months.
_WINDOW: Final = 120
#: Index levels and earnings an input may hold.
_LEVEL_MIN: Final = 0.01
_LEVEL_MAX: Final = 1e9
_EARNINGS_MAX: Final = 1e9
#: A CAPE, or a yield, larger than this has no meaningful value.
_RATIO_MAX: Final = 1e6

_Earnings = Annotated[
    tuple[Annotated[Money, Field(ge=-_EARNINGS_MAX, le=_EARNINGS_MAX)], ...],
    ARRAY_INPUT,
]
_Levels = Annotated[
    tuple[Annotated[IndexLevel, Field(ge=_LEVEL_MIN, le=_LEVEL_MAX)], ...],
    ARRAY_INPUT,
]


class CapeInputs(ModelInputs):
    price: IndexLevel = Field(
        ge=_LEVEL_MIN, le=_LEVEL_MAX, description="The index level in month t"
    )
    price_cpi: IndexLevel = Field(
        ge=_LEVEL_MIN,
        le=_LEVEL_MAX,
        description="The price index (CPI) of month t, the dollars results are in",
    )
    earnings: _Earnings = Field(
        min_length=1,
        max_length=_WINDOW_MAX,
        description=(
            "Earnings of each period of the window before month t, oldest first "
            "(Shiller: the previous 120 months)"
        ),
    )
    cpi: _Levels = Field(
        min_length=1,
        max_length=_WINDOW_MAX,
        description="The price index of each period of the window",
    )
    real_yield: Rate | None = Field(
        None,
        ge=-0.05,
        le=0.5,
        description="A real 10-year yield (TIPS); give this or nominal_yield",
    )
    nominal_yield: Rate | None = Field(
        None,
        ge=-0.05,
        le=0.5,
        description=(
            "A nominal 10-year yield, less trailing inflation for the real rate; "
            "give this or real_yield"
        ),
    )
    inflation: Rate | None = Field(
        None,
        ge=-0.5,
        le=1.0,
        description=(
            "Trailing annual inflation to take from the nominal yield; left out, "
            "(price_cpi / cpi[0]) ** (periods_per_year / n) - 1 over the window"
        ),
    )
    periods_per_year: Count = Field(
        12, ge=1, le=12, description="Periods a year of the window (12 for months)"
    )

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if len(self.cpi) != len(self.earnings):
            msg = (
                f"give one price index per period: {len(self.cpi)} for "
                f"{len(self.earnings)} periods of earnings"
            )
            raise ValueError(msg)
        if (self.real_yield is None) == (self.nominal_yield is None):
            msg = "give one real rate: real_yield, or nominal_yield less inflation"
            raise ValueError(msg)
        if self.inflation is not None and self.nominal_yield is None:
            msg = "inflation is taken from nominal_yield; give it with that"
            raise ValueError(msg)
        return self


class CapeOutputs(ModelOutputs):
    cape: Ratio | None = Field(
        ge=0.0,
        le=_RATIO_MAX,
        description=(
            "Price over average real earnings; None when they average nothing "
            "positive, with a warning"
        ),
    )
    cape_yield: Ratio = Field(
        ge=-_RATIO_MAX,
        le=_RATIO_MAX,
        description="Average real earnings over price, a decimal: 1 / CAPE",
    )
    excess_cape_yield: Ratio = Field(
        ge=-_RATIO_MAX - 1,
        le=_RATIO_MAX + 1,
        description="The CAPE yield less the real 10-year rate, a decimal",
    )
    real_rate: Rate = Field(
        ge=-1.0, le=1.0, description="The real 10-year rate the excess is over"
    )
    average_real_earnings: Money = Field(
        ge=-1e18,
        le=1e18,
        description="The window's average earnings, in the dollars of month t",
    )


def _cape(inputs: CapeInputs) -> CapeOutputs:
    level = inputs.price_cpi
    average = math.fsum(
        e * (level / i) for e, i in zip(inputs.earnings, inputs.cpi, strict=True)
    ) / len(inputs.earnings)
    earnings_yield = average / inputs.price
    if not abs(earnings_yield) <= _RATIO_MAX:
        msg = f"the earnings yield {earnings_yield!r} is beyond {_RATIO_MAX}"
        raise DomainError(msg)
    ratio: float | None = None
    if earnings_yield >= 1.0 / _RATIO_MAX:
        ratio = 1.0 / earnings_yield
    else:
        warn(
            "no_positive_earnings",
            "the window's real earnings average to nothing positive (or nearly "
            "so), so the price has no meaningful multiple of them",
            stacklevel=2,
        )
    if inputs.real_yield is not None:
        real = inputs.real_yield
    else:
        nominal = inputs.nominal_yield if inputs.nominal_yield is not None else 0.0
        inflation = inputs.inflation
        if inflation is None:
            growth = math.log(level / inputs.cpi[0])
            exponent = growth * inputs.periods_per_year / len(inputs.cpi)
            if exponent > math.log(2.0):
                msg = "trailing inflation above 100% a year has no real rate here"
                raise DomainError(msg)
            inflation = math.expm1(exponent)
        real = nominal - inflation
    if not -1.0 <= real <= 1.0:
        msg = f"the real rate {real!r} is outside [-1, 1]"
        raise DomainError(msg)
    return CapeOutputs(
        cape=ratio,
        cape_yield=earnings_yield,
        excess_cape_yield=earnings_yield - real,
        real_rate=real,
        average_real_earnings=average,
    )


_CAMPBELL_SHILLER_1998 = Reference(
    key="campbell1998",
    citation=(
        "Campbell, J. Y. and Shiller, R. J. (1998). Valuation Ratios and the "
        "Long-Run Stock Market Outlook. Journal of Portfolio Management, 24(2), "
        "11-26."
    ),
    doi="10.3905/jpm.24.2.11",
    locator="p. 16: price over the average of the previous ten years' real earnings",
)
_CAMPBELL_SHILLER_1988 = Reference(
    key="campbell1988",
    citation=(
        "Campbell, J. Y. and Shiller, R. J. (1988). Stock Prices, Earnings, and "
        "Expected Dividends. Journal of Finance, 43(3), 661-676."
    ),
    doi="10.1111/j.1540-6261.1988.tb04598.x",
    locator="Smoothed real earnings over the previous ten years",
)
_SHILLER_DATA = Reference(
    key="shiller_ie_data",
    citation=(
        "Shiller, R. J. U.S. Stock Price, Earnings and Dividends, monthly since "
        "1871: ie_data.xls, the CAPE and Excess CAPE Yield columns."
    ),
    url="https://shillerdata.com/",
    locator="Sheet Data: CAPE (column M) and Excess CAPE Yield (column Q)",
)


@model(
    id="equity.cape",
    version=1,
    title="Cyclically adjusted price-to-earnings ratio (CAPE)",
    summary=(
        "Shiller's CAPE: the price over the average of real earnings over a "
        "window, its earnings yield and the excess CAPE yield over a real 10-year "
        "rate."
    ),
    formula=(
        (
            r"\mathrm{CAPE}_t = P_t \Big/ \tfrac{1}{n} \sum_{k=t-n}^{t-1} "
            r"E_k \frac{I_t}{I_k}"
        ),
        (
            r"y_{\mathrm{CAPE}} = 1 / \mathrm{CAPE}, \quad "
            r"\mathrm{ECY} = y_{\mathrm{CAPE}} - r_{\mathrm{real}}"
        ),
        (
            r"r_{\mathrm{real}} = y_{10} - \left[(I_t / I_{t-n})^{m/n} - 1\right]"
            r"\ \text{or a TIPS yield}"
        ),
    ),
    assumptions=(
        (
            "Earnings and prices are deflated by one price index into the dollars "
            "of the price's month; the window is the n periods before it."
        ),
        (
            "Shiller's monthly earnings are four-quarter totals interpolated "
            "between quarters; his window is the previous 120 months."
        ),
        (
            "Profile: default binds Shiller's S&P composite price and CPI on the "
            "date, the previous 120 months of his earnings and CPI (lagged one "
            "month), and Treasury's 10-year TIPS yield; 'nominal' binds Treasury's "
            "10-year yield, a monthly average, in place of TIPS, so the real rate "
            "is it less trailing inflation as in Shiller's file."
        ),
    ),
    limitations=(
        (
            "A valuation ratio, not a timing signal: high CAPEs have preceded low "
            "ten-year returns on average, with wide dispersion."
        ),
        (
            "When the window's real earnings average to nothing positive, CAPE is "
            "None with a warning; an earnings yield beyond 1e6, trailing inflation "
            "above 100% a year or a real rate outside [-1, 1] raise DomainError."
        ),
        (
            "Shiller publishes earnings months after prices: as of a recent date "
            "the earnings window ends at his last earnings, before the price's "
            "month. His file averages the earnings it has, so its latest CAPEs use "
            "fewer than 120 months. Trailing inflation then runs from the "
            "window's first price index to the price's month, more than the "
            "window's length, but is annualized over the window (about 0.15 "
            "percentage points too high at 3% inflation and a six-month lag): "
            "pass inflation to set it."
        ),
        (
            "Shiller's data are library-only: fetched at run time from his file "
            "and never stored."
        ),
    ),
    references=(_CAMPBELL_SHILLER_1998, _CAMPBELL_SHILLER_1988, _SHILLER_DATA),
    evidence=Evidence.PRACTITIONER,
    cost=CostClass.INSTANT,
    tags=("cape", "shiller pe", "valuation", "earnings yield", "excess cape yield"),
    invariants=(
        Invariant(
            id="constant_real_earnings_give_price_over_earnings",
            statement=(
                "When real earnings are the same in every period of the window, "
                "CAPE is the price over them."
            ),
        ),
        Invariant(
            id="cape_yield_is_the_reciprocal",
            statement="Where CAPE is defined, the CAPE yield is its reciprocal.",
        ),
    ),
    examples=(
        Example(
            name="annual_window",
            inputs={
                "price": 4000.0,
                "price_cpi": 300.0,
                "earnings": [
                    100.0,
                    105.0,
                    98.0,
                    120.0,
                    140.0,
                    150.0,
                    160.0,
                    170.0,
                    190.0,
                    210.0,
                ],
                "cpi": [
                    220.0,
                    225.0,
                    230.0,
                    236.0,
                    241.0,
                    246.0,
                    252.0,
                    260.0,
                    275.0,
                    290.0,
                ],
                "nominal_yield": 0.042,
                "periods_per_year": 1,
            },
            note="Ten years of annual earnings and a nominal 10-year yield.",
        ),
        Example(
            name="tips_real_rate",
            inputs={
                "price": 100.0,
                "price_cpi": 110.0,
                "earnings": [4.0, 4.4],
                "cpi": [100.0, 105.0],
                "real_yield": 0.018,
                "periods_per_year": 1,
            },
        ),
    ),
    bindings=(
        Binding("price", "us.equity.sp_composite_price"),
        Binding("price_cpi", "us.prices.cpi_long_run"),
        Binding(
            "earnings",
            "us.equity.sp_composite_earnings",
            transform="lag(periods=1)",
            as_of=AsOf.WINDOW,
            window=_WINDOW,
        ),
        Binding(
            "cpi",
            "us.prices.cpi_long_run",
            transform="lag(periods=1)",
            as_of=AsOf.WINDOW,
            window=_WINDOW,
        ),
        Binding("real_yield", "us.treasury.real_10y"),
        Binding("price", "us.equity.sp_composite_price", profile="nominal"),
        Binding("price_cpi", "us.prices.cpi_long_run", profile="nominal"),
        Binding(
            "earnings",
            "us.equity.sp_composite_earnings",
            transform="lag(periods=1)",
            as_of=AsOf.WINDOW,
            window=_WINDOW,
            profile="nominal",
        ),
        Binding(
            "cpi",
            "us.prices.cpi_long_run",
            transform="lag(periods=1)",
            as_of=AsOf.WINDOW,
            window=_WINDOW,
            profile="nominal",
        ),
        Binding(
            "nominal_yield",
            "us.treasury.nominal_10y",
            transform="convert(to=monthly,method=mean)",
            profile="nominal",
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def cape(inputs: CapeInputs) -> CapeOutputs:
    """Return CAPE, its yield and the excess CAPE yield."""
    return _cape(inputs)
