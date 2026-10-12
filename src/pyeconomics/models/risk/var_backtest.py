# src/pyeconomics/models/risk/var_backtest.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Backtests of a VaR model's exceptions: ``risk.var_backtest``.

Three calculations, discriminated on ``calculation``, each from a series of
exceptions, given directly or as P&L against VaR (an exception is a loss
greater than the VaR, as MAR32.5 has it):

- ``kupiec``: Kupiec's (1995) proportion-of-failures likelihood ratio, with its
  chi-square(1) p-value; ``0 log 0`` is taken as 0, so zero exceptions and all
  exceptions are defined;
- ``christoffersen``: Christoffersen's (1998) tests of independence and of
  conditional coverage, from the first-order Markov transitions of the
  exception series, conditioning on its first observation;
- ``basel_traffic_light``: the green, yellow and red zones of the Basel
  Committee's 1996 backtesting framework, with Table 2's plus factor for 250
  observations at 99%, and, for other samples, the zones the framework defines
  by the cumulative binomial probability (yellow from 95%, red from 99.99%).
"""

from __future__ import annotations

import itertools
import math
from statistics import NormalDist
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Count,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    MoneyArray,
    Probability,
    Ratio,
    Reference,
    model,
    warn,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.risk._common import SERIES_MAX, confidence_field

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["var_backtest"]

#: A likelihood ratio from 10,080 observations at a 0.01% exception rate is at
#: most about 186,000.
_LR_MAX: Final = 1e6
#: Table 2 of the 1996 framework: the plus factor for each yellow-zone count
#: of exceptions, for 250 observations at 99% coverage.
_TABLE_2_PLUS: Final = {5: 0.40, 6: 0.50, 7: 0.65, 8: 0.75, 9: 0.85}
_TABLE_2_OBSERVATIONS: Final = 250
_TABLE_2_CONFIDENCE: Final = 0.99
_YELLOW_FROM: Final = 0.95
_RED_FROM: Final = 0.9999

_Exceptions = Annotated[tuple[bool, ...], ARRAY_INPUT]


def _alpha() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        0.05, ge=0.001, le=0.5, description="Size of the test (rejection probability)"
    )


def _ratio(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0, le=_LR_MAX, description=description)


# --- inputs ------------------------------------------------------------------


class _Series(ModelInputs):
    """Exceptions, or P&L and VaR from which to count them."""

    _MIN_OBSERVATIONS: ClassVar[int] = 1

    exceptions: _Exceptions | None = Field(
        None,
        max_length=SERIES_MAX,
        description="Whether each period's loss exceeded its VaR, in time order",
    )
    profit_and_loss: MoneyArray | None = Field(
        None,
        max_length=SERIES_MAX,
        description="Profit (+) or loss (-) per period, in time order",
    )
    value_at_risk: MoneyArray | None = Field(
        None,
        max_length=SERIES_MAX,
        description="Each period's VaR as a positive loss, in money",
    )
    confidence: Probability = confidence_field()

    @model_validator(mode="after")
    def _one_series(self) -> Self:
        pair = (self.profit_and_loss, self.value_at_risk)
        if self.exceptions is not None:
            if pair != (None, None):
                msg = "give exceptions, or profit_and_loss and value_at_risk, not both"
                raise ValueError(msg)
            size = len(self.exceptions)
        elif self.profit_and_loss is None or self.value_at_risk is None:
            msg = "give exceptions, or both profit_and_loss and value_at_risk"
            raise ValueError(msg)
        elif len(self.profit_and_loss) != len(self.value_at_risk):
            msg = "profit_and_loss and value_at_risk must have the same length"
            raise ValueError(msg)
        else:
            size = len(self.profit_and_loss)
        if size < self._MIN_OBSERVATIONS:
            msg = f"the backtest needs at least {self._MIN_OBSERVATIONS} observations"
            raise ValueError(msg)
        return self

    def hits(self) -> list[bool]:
        """Return the exception series."""
        if self.exceptions is not None:
            return list(self.exceptions)
        pnl = self.profit_and_loss or ()
        var = self.value_at_risk or ()
        return [-p > v for p, v in zip(pnl, var, strict=True)]


class KupiecInputs(_Series):
    """An exception series, its VaR's confidence level and the test's size."""

    calculation: Literal["kupiec"] = Field(
        "kupiec", description="Kupiec's proportion-of-failures test"
    )
    alpha: Probability = _alpha()


class ChristoffersenInputs(_Series):
    """An exception series of at least two observations."""

    _MIN_OBSERVATIONS: ClassVar[int] = 2

    calculation: Literal["christoffersen"] = Field(
        "christoffersen",
        description="Christoffersen's independence and conditional coverage tests",
    )
    alpha: Probability = _alpha()


class TrafficLightInputs(_Series):
    """An exception series and its VaR's confidence level."""

    calculation: Literal["basel_traffic_light"] = Field(
        "basel_traffic_light", description="The Basel Committee's traffic light"
    )


VarBacktestInputs = Annotated[
    KupiecInputs | ChristoffersenInputs | TrafficLightInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class _Counts(ModelOutputs):
    observations: Count = Field(ge=1, le=SERIES_MAX, description="Periods tested")
    exceptions: Count = Field(
        ge=0, le=SERIES_MAX, description="Periods whose loss exceeded the VaR"
    )


class KupiecOutputs(_Counts):
    calculation: Literal["kupiec"] = Field(
        "kupiec", description="Kupiec's proportion-of-failures test"
    )
    exception_rate: Probability = Field(
        ge=0, le=1, description="Exceptions per observation"
    )
    expected_exceptions: Ratio = Field(
        ge=0, le=SERIES_MAX, description="Observations times (1 - confidence)"
    )
    likelihood_ratio: Ratio = _ratio("LR_POF, chi-square with one degree of freedom")
    p_value: Probability = Field(ge=0, le=1, description="P-value of LR_POF")
    critical_value: Ratio = Field(
        ge=0, le=100, description="Chi-square(1) quantile at 1 - alpha"
    )
    reject: bool = Field(description="Whether LR_POF rejects correct coverage")


class ChristoffersenOutputs(_Counts):
    calculation: Literal["christoffersen"] = Field(
        "christoffersen",
        description="Christoffersen's independence and conditional coverage tests",
    )
    n00: Count = Field(ge=0, le=SERIES_MAX, description="No exception, then none")
    n01: Count = Field(ge=0, le=SERIES_MAX, description="No exception, then one")
    n10: Count = Field(ge=0, le=SERIES_MAX, description="An exception, then none")
    n11: Count = Field(ge=0, le=SERIES_MAX, description="An exception, then another")
    lr_unconditional: Ratio = _ratio(
        "LR_UC over the transitions, chi-square with one degree of freedom"
    )
    lr_independence: Ratio = _ratio("LR_IND, chi-square with one degree of freedom")
    lr_conditional_coverage: Ratio = _ratio(
        "LR_CC, chi-square with two degrees of freedom"
    )
    p_value_unconditional: Probability = Field(ge=0, le=1, description="LR_UC p-value")
    p_value_independence: Probability = Field(ge=0, le=1, description="LR_IND p-value")
    p_value_conditional_coverage: Probability = Field(
        ge=0, le=1, description="LR_CC p-value"
    )
    reject_independence: bool = Field(description="Whether LR_IND rejects at alpha")
    reject_conditional_coverage: bool = Field(
        description="Whether LR_CC rejects at alpha"
    )


class TrafficLightOutputs(_Counts):
    calculation: Literal["basel_traffic_light"] = Field(
        "basel_traffic_light", description="The Basel Committee's traffic light"
    )
    zone: Literal["green", "yellow", "red"] = Field(description="The zone")
    cumulative_probability: Probability = Field(
        ge=0,
        le=1,
        description="Probability of this many exceptions or fewer for an accurate VaR",
    )
    yellow_from: Count = Field(
        ge=0, le=SERIES_MAX, description="Fewest exceptions in the yellow zone"
    )
    red_from: Count = Field(
        ge=0, le=SERIES_MAX, description="Fewest exceptions in the red zone"
    )
    plus_factor: Ratio | None = Field(
        ge=0,
        le=1,
        description="Increase in the scaling factor (Table 2); null where undefined",
    )


VarBacktestOutputs = Annotated[
    KupiecOutputs | ChristoffersenOutputs | TrafficLightOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _xlogy(count: float, probability: float) -> float:
    """Return ``count * log(probability)``, with ``0 log 0 = 0``."""
    return 0.0 if count == 0 else count * math.log(probability)


def _bernoulli(count: float, hits: float, probability: float) -> float:
    """Return the log-likelihood of ``hits`` in ``count`` trials."""
    return _xlogy(count - hits, 1 - probability) + _xlogy(hits, probability)


def _statistic(log_null: float, log_alternative: float) -> float:
    """Return ``-2 (log L0 - log L1)``, at least zero despite rounding."""
    return min(max(0.0, -2.0 * (log_null - log_alternative)), _LR_MAX)


def _p_one(statistic: float) -> float:
    """Return the chi-square(1) upper-tail probability."""
    return math.erfc(math.sqrt(statistic / 2))


def _p_two(statistic: float) -> float:
    """Return the chi-square(2) upper-tail probability."""
    return math.exp(-statistic / 2)


def _critical_one(alpha: float) -> float:
    return NormalDist().inv_cdf(1 - alpha / 2) ** 2


def _kupiec(inputs: KupiecInputs) -> KupiecOutputs:
    hits = inputs.hits()
    n, x = len(hits), sum(hits)
    p = 1 - inputs.confidence
    ratio = _statistic(_bernoulli(n, x, p), _bernoulli(n, x, x / n))
    critical = _critical_one(inputs.alpha)
    return KupiecOutputs(
        observations=n,
        exceptions=x,
        exception_rate=x / n,
        expected_exceptions=n * p,
        likelihood_ratio=ratio,
        p_value=_p_one(ratio),
        critical_value=critical,
        reject=ratio > critical,
    )


def _christoffersen(inputs: ChristoffersenInputs) -> ChristoffersenOutputs:
    hits = inputs.hits()
    counts = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
    for before, after in itertools.pairwise(hits):
        counts[int(before), int(after)] += 1
    n00, n01, n10, n11 = (counts[k] for k in ((0, 0), (0, 1), (1, 0), (1, 1)))
    transitions = n00 + n01 + n10 + n11
    later = n01 + n11
    p = 1 - inputs.confidence
    pi01 = n01 / (n00 + n01) if n00 + n01 else 0.0
    pi11 = n11 / (n10 + n11) if n10 + n11 else 0.0
    log_null = _bernoulli(transitions, later, p)
    log_rate = _bernoulli(transitions, later, later / transitions)
    log_markov = _bernoulli(n00 + n01, n01, pi01) + _bernoulli(n10 + n11, n11, pi11)
    unconditional = _statistic(log_null, log_rate)
    independence = _statistic(log_rate, log_markov)
    coverage = _statistic(log_null, log_markov)
    critical_one = _critical_one(inputs.alpha)
    critical_two = -2 * math.log(inputs.alpha)
    return ChristoffersenOutputs(
        observations=len(hits),
        exceptions=sum(hits),
        n00=n00,
        n01=n01,
        n10=n10,
        n11=n11,
        lr_unconditional=unconditional,
        lr_independence=independence,
        lr_conditional_coverage=coverage,
        p_value_unconditional=_p_one(unconditional),
        p_value_independence=_p_one(independence),
        p_value_conditional_coverage=_p_two(coverage),
        reject_independence=independence > critical_one,
        reject_conditional_coverage=coverage > critical_two,
    )


def _traffic_light(inputs: TrafficLightInputs) -> TrafficLightOutputs:
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    hits = inputs.hits()
    n, x = len(hits), sum(hits)
    p = 1 - inputs.confidence
    cumulative = np.asarray(stats.binom.cdf(np.arange(n + 1), n, p)).tolist()
    # Zero exceptions is never evidence against a VaR: in a short sample the
    # cumulative probability at zero can pass 95% already, and the zones then
    # start at one exception.
    yellow_from = max(1, sum(1 for c in cumulative if c < _YELLOW_FROM))
    red_from = max(yellow_from, sum(1 for c in cumulative if c < _RED_FROM))
    zone: Literal["green", "yellow", "red"]
    if x < yellow_from:
        zone, plus = "green", 0.0
    elif x >= red_from:
        zone, plus = "red", 1.0
    elif n == _TABLE_2_OBSERVATIONS and inputs.confidence == _TABLE_2_CONFIDENCE:
        zone, plus = "yellow", _TABLE_2_PLUS[x]
    else:
        zone, plus = "yellow", None
        warn(
            "plus_factor_undefined",
            "Table 2 sets yellow-zone plus factors for 250 observations at 99% "
            "only; the supervisor sets it for this sample",
        )
    return TrafficLightOutputs(
        observations=n,
        exceptions=x,
        zone=zone,
        cumulative_probability=min(1.0, cumulative[x]),
        yellow_from=yellow_from,
        red_from=red_from,
        plus_factor=plus,
    )


# --- the model ---------------------------------------------------------------

_KUPIEC = Reference(
    key="kupiec1995",
    citation=(
        "Kupiec, P. H. (1995). Techniques for verifying the accuracy of risk "
        "measurement models. The Journal of Derivatives, 3(2), 73-84."
    ),
    doi="10.3905/jod.1995.407942",
    locator="The proportion-of-failures likelihood ratio test",
)
_CHRISTOFFERSEN = Reference(
    key="christ1998",
    citation=(
        "Christoffersen, P. F. (1998). Evaluating interval forecasts. "
        "International Economic Review, 39(4), 841-862."
    ),
    doi="10.2307/2527341",
    locator=(
        "Section 3: the likelihood ratio tests of unconditional coverage, "
        "independence and conditional coverage"
    ),
)
_BASEL_1996 = Reference(
    key="bcbs1996",
    citation=(
        "Basel Committee on Banking Supervision (1996). Supervisory framework for "
        "the use of backtesting in conjunction with the internal models approach "
        "to market risk capital requirements. Bank for International Settlements."
    ),
    url="https://www.bis.org/publ/bcbs22.htm",
    locator="Section III and Table 2, p. 15 (zones, plus factors, other samples)",
)
_BASEL_2019 = Reference(
    key="bcbs2019",
    citation=(
        "Basel Committee on Banking Supervision (2019). Minimum capital "
        "requirements for market risk. Bank for International Settlements."
    ),
    url="https://www.bis.org/bcbs/publ/d457.htm",
    locator="MAR32.5 (an exception is a loss greater than the 99% VaR)",
)


@model(
    id="risk.var_backtest",
    version=1,
    title="VaR backtests",
    summary=(
        "Kupiec's proportion-of-failures test, Christoffersen's independence and "
        "conditional coverage tests, and the Basel traffic light, from a series "
        "of VaR exceptions."
    ),
    formula=(
        (
            r"LR_{POF} = -2\ln\frac{(1 - p)^{n - x} p^{x}}"
            r"{(1 - x/n)^{n - x}(x/n)^{x}}, \quad p = 1 - c"
        ),
        (
            r"LR_{IND} = -2\ln\frac{(1 - \hat\pi)^{n_{00} + n_{10}}\hat\pi^{n_{01} + "
            r"n_{11}}}{(1 - \hat\pi_{01})^{n_{00}}\hat\pi_{01}^{n_{01}}"
            r"(1 - \hat\pi_{11})^{n_{10}}\hat\pi_{11}^{n_{11}}}"
        ),
        r"LR_{CC} = LR_{UC} + LR_{IND} \sim \chi^2_2",
        (
            r"F(x) = \sum_{k \le x}\binom{n}{k}p^k(1 - p)^{n - k}: "
            r"\text{yellow from } F \ge 0.95, \text{ red from } F \ge 0.9999"
        ),
    ),
    assumptions=(
        (
            "An exception is a loss strictly greater than the VaR, with the VaR "
            "a positive loss."
        ),
        "0 log 0 is 0, so a series with no exception or only exceptions is tested.",
        (
            "Christoffersen's statistics condition on the first observation, so "
            "LR_UC there counts the n - 1 transitions and LR_CC = LR_UC + LR_IND "
            "exactly."
        ),
        (
            "The traffic light uses the binomial distribution at the VaR's "
            "confidence, as the framework does at 99%; zero exceptions is always "
            "green, so in a short sample the zones start at one exception."
        ),
    ),
    limitations=(
        (
            "The likelihood ratios are asymptotically chi-square; with few "
            "observations their p-values are approximate."
        ),
        (
            "Table 2's yellow-zone plus factors exist only for 250 observations "
            "at 99%; elsewhere the plus factor is null with a warning."
        ),
    ),
    references=(_KUPIEC, _CHRISTOFFERSEN, _BASEL_1996, _BASEL_2019),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("backtesting", "value at risk", "kupiec", "christoffersen", "basel"),
    invariants=(
        Invariant(
            id="likelihood_ratios_nonnegative",
            statement="Every likelihood ratio statistic is at least zero.",
        ),
        Invariant(
            id="conditional_coverage_is_sum_of_parts",
            statement="LR_CC equals LR_UC plus LR_IND.",
        ),
        Invariant(
            id="traffic_light_monotone_in_exceptions",
            statement=(
                "More exceptions in the same sample never move the traffic light "
                "to a better zone or lower its plus factor."
            ),
        ),
    ),
    examples=(
        Example(
            name="a_year_at_99",
            inputs={
                "calculation": "kupiec",
                "exceptions": [False] * 243 + [True] * 7,
                "confidence": 0.99,
            },
        ),
        Example(
            name="clustered_exceptions",
            inputs={
                "calculation": "christoffersen",
                "exceptions": [False] * 20 + [True, True, False, True] + [False] * 76,
                "confidence": 0.95,
            },
        ),
        Example(
            name="pnl_against_var",
            inputs={
                "calculation": "basel_traffic_light",
                "profit_and_loss": [1.2, -3.5, 0.4, -0.9, 2.1, -4.2],
                "value_at_risk": [3.0, 3.0, 3.1, 3.1, 3.2, 3.2],
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def var_backtest(inputs: VarBacktestInputs) -> VarBacktestOutputs:
    """Run the backtest the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], VarBacktestOutputs]]] = {
    KupiecInputs: _kupiec,
    ChristoffersenInputs: _christoffersen,
    TrafficLightInputs: _traffic_light,
}
