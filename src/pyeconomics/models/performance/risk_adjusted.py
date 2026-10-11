# src/pyeconomics/models/performance/risk_adjusted.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Risk-adjusted performance measures: ``performance.risk_adjusted``.

From a portfolio's periodic returns :math:`r_t`, a benchmark's :math:`b_t`, the
risk-free returns :math:`f_t` (zero if omitted) and an explicit number of
periods in a year :math:`m`, with excess returns :math:`e_t = r_t - f_t`,
:math:`e^b_t = b_t - f_t` and active returns :math:`a_t = r_t - b_t`. Means are
arithmetic, standard deviations divide by :math:`n - 1`, and the ratios are
annualized by :math:`m` (means) and :math:`\sqrt{m}` (deviations):

- Sharpe (1966, 1994): :math:`\bar{e} / s_e \cdot \sqrt{m}`;
- Sortino and Price (1994): :math:`(\bar{r} - MAR) / DD \cdot \sqrt{m}`, with the
  downside deviation :math:`DD = \sqrt{\tfrac{1}{n}\sum \min(r_t - MAR, 0)^2}`
  below a minimum acceptable return per period;
- beta: :math:`\operatorname{cov}(e, e^b) / \operatorname{var}(e^b)`;
- Treynor (1965): :math:`m \bar{e} / \beta`;
- Jensen's (1968) alpha: :math:`m(\bar{e} - \beta \bar{e}^b)`, the regression
  intercept;
- tracking error :math:`s_a \sqrt{m}` and information ratio :math:`\bar{a} /
  s_a \cdot \sqrt{m}`;
- M² (Modigliani and Modigliani, 1997): :math:`m\bar{f} + S \cdot s_{e^b}
  \sqrt{m}`, the portfolio's return levered to the benchmark's volatility;
- Calmar: the compound annual growth rate over the maximum drawdown of the
  wealth index, which starts at 1 before the first return;
- up and down capture: the geometric mean return of the portfolio over the
  periods when the benchmark rose (fell), over the benchmark's in the same
  periods.

A ratio over a zero denominator, or past its bounds, is null with a warning
(ADR-0008 decision 10). A series counts as having no spread when it varies by no
more than rounding error (:func:`~pyeconomics.core.has_spread`).
"""

from __future__ import annotations

import math
from typing import Any, Final, Self

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
    Periods,
    Ratio,
    Reference,
    Return,
    ReturnArray,
    Volatility,
    annualized_log_return,
    has_spread,
    log_return,
    max_drawdown,
    model,
    sample_mean,
    sample_variance,
    semideviation_below_target,
    warn,
)
from pyeconomics.models.performance._common import (
    RATIO_OUT,
    RETURN_MAX,
    SERIES_MAX,
    optional,
    ratio,
)

__all__ = ["risk_adjusted"]

#: An annualized return, alpha or M^2 beyond this is unrepresentable.
_RETURN_OUT: Final = 1e6
#: A deviation of returns in [-1, 100] is at most 101 * sqrt(2) per period, and
#: sqrt(100,000) periods a year makes that about 45,000; the volatility kind's
#: upper bound of 10 widens to 1e5.
_VOLATILITY_OUT: Final = 1e5


def _ratio(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-RATIO_OUT, le=RATIO_OUT, description=description)


def _return_out(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-_RETURN_OUT, le=_RETURN_OUT, description=description)


def _deviation(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=_VOLATILITY_OUT, description=description)


class RiskAdjustedInputs(ModelInputs):
    """Portfolio, benchmark and risk-free returns over the same periods."""

    returns: ReturnArray = Field(
        min_length=2, max_length=SERIES_MAX, description="Portfolio return each period"
    )
    benchmark_returns: ReturnArray = Field(
        min_length=2,
        max_length=SERIES_MAX,
        description="Benchmark return each period, aligned with the portfolio's",
    )
    risk_free_returns: ReturnArray = Field(
        (),
        max_length=SERIES_MAX,
        description="Risk-free return each period; omit for zero",
    )
    periods_per_year: Periods = Field(
        gt=0, le=100_000, description="Periods in a year, such as 12 or 252"
    )
    minimum_acceptable_return: Return = Field(
        0.0,
        ge=-1.0,
        le=RETURN_MAX,
        description="Minimum acceptable return per period, for the Sortino ratio",
    )

    @model_validator(mode="after")
    def _aligned(self) -> Self:
        size = len(self.returns)
        if len(self.benchmark_returns) != size or (
            self.risk_free_returns and len(self.risk_free_returns) != size
        ):
            msg = (
                "the portfolio, benchmark and risk-free returns must cover the same "
                f"periods: {size}, {len(self.benchmark_returns)} and "
                f"{len(self.risk_free_returns)} returns"
            )
            raise ValueError(msg)
        return self


class RiskAdjustedOutputs(ModelOutputs):
    observations: Count = Field(ge=2, le=SERIES_MAX, description="Number of periods")
    annualized_return: Return | None = Field(
        ge=-1.0,
        le=_RETURN_OUT,
        description="Compound annual growth rate of the portfolio",
    )
    annualized_volatility: Volatility = _deviation(
        "Standard deviation of the portfolio returns (n - 1) times sqrt(m)"
    )
    sharpe_ratio: Ratio | None = _ratio(
        "Mean excess return over its standard deviation, times sqrt(m)"
    )
    downside_deviation: Volatility = _deviation(
        "Root mean square shortfall below the minimum acceptable return (n), "
        "times sqrt(m)"
    )
    sortino_ratio: Ratio | None = _ratio(
        "Mean return less the minimum acceptable return, over the downside "
        "deviation, times sqrt(m)"
    )
    beta: Ratio | None = _ratio(
        "Covariance of portfolio and benchmark excess returns over the benchmark's "
        "variance"
    )
    treynor_ratio: Ratio | None = _ratio("Annualized mean excess return over beta")
    jensen_alpha: Return | None = _return_out(
        "Annualized intercept: m times (mean excess return - beta * benchmark's)"
    )
    tracking_error: Volatility = _deviation(
        "Standard deviation of the active returns (n - 1) times sqrt(m)"
    )
    information_ratio: Ratio | None = _ratio(
        "Mean active return over its standard deviation, times sqrt(m)"
    )
    m_squared: Return | None = _return_out(
        "Annualized risk-free return plus the Sharpe ratio times the benchmark's "
        "annualized excess volatility"
    )
    max_drawdown: Return = Field(
        ge=0.0, le=1.0, description="Largest decline of the wealth index from a peak"
    )
    calmar_ratio: Ratio | None = _ratio(
        "Compound annual growth rate over the maximum drawdown"
    )
    up_capture: Ratio | None = _ratio(
        "Geometric mean portfolio return over the benchmark's, in periods the "
        "benchmark rose"
    )
    down_capture: Ratio | None = _ratio(
        "Geometric mean portfolio return over the benchmark's, in periods the "
        "benchmark fell"
    )


def _covariance(x: np.ndarray[Any, Any], y: np.ndarray[Any, Any]) -> float:
    dx = x - sample_mean(x.tolist())
    dy = y - sample_mean(y.tolist())
    return math.fsum((dx * dy).tolist()) / (x.size - 1)


def _geometric_mean(returns: np.ndarray[Any, Any]) -> float:
    with np.errstate(divide="ignore"):
        logs = np.log1p(returns)
    return math.expm1(float(np.mean(logs)))


def _capture(
    portfolio: np.ndarray[Any, Any], benchmark: np.ndarray[Any, Any], *, up: bool
) -> float | None:
    chosen = benchmark > 0 if up else benchmark < 0
    direction = "rose" if up else "fell"
    if not chosen.any():
        warn(
            "no_periods",
            f"the benchmark never {direction}, so the capture ratio is undefined",
        )
        return None
    name = "up capture" if up else "down capture"
    return ratio(
        _geometric_mean(portfolio[chosen]), _geometric_mean(benchmark[chosen]), name
    )


def _drawdown(returns: np.ndarray[Any, Any]) -> float:
    gross = 1.0 + returns
    if np.any(gross == 0):
        return 1.0
    # The wealth index in log space, scaled so its peak is 1: no overflow, and
    # a value that underflows is a decline of all but nothing.
    logs = np.concatenate(([0.0], np.cumsum(np.log(gross))))
    wealth = np.maximum(np.exp(logs - logs.max()), np.finfo(np.float64).tiny)
    return max_drawdown(wealth.tolist()).depth


def _deviation_of(values: np.ndarray[Any, Any]) -> float:
    return math.sqrt(sample_variance(values.tolist()))


def _spread_ratio(
    numerator: float, values: np.ndarray[Any, Any], name: str, scale: float
) -> float | None:
    """Return ``numerator / s * scale``; None, with a warning, if ``values`` is flat."""
    if not has_spread(values.tolist()):
        warn("zero_volatility", f"the {name} divides by a series with no spread")
        return None
    return ratio(numerator * scale, _deviation_of(values), name)


def _risk_adjusted(inputs: RiskAdjustedInputs) -> RiskAdjustedOutputs:
    r = np.asarray(inputs.returns, dtype=np.float64)
    b = np.asarray(inputs.benchmark_returns, dtype=np.float64)
    f = (
        np.asarray(inputs.risk_free_returns, dtype=np.float64)
        if inputs.risk_free_returns
        else np.zeros_like(r)
    )
    m = inputs.periods_per_year
    root = math.sqrt(m)
    excess, benchmark_excess, active = r - f, b - f, r - b
    mean_excess = sample_mean(excess.tolist())

    sharpe = _spread_ratio(mean_excess, excess, "Sharpe ratio", root)
    downside = semideviation_below_target(r.tolist(), inputs.minimum_acceptable_return)
    sortino = ratio(
        (sample_mean(r.tolist()) - inputs.minimum_acceptable_return) * root,
        downside,
        "Sortino ratio",
    )
    beta: float | None = None
    if has_spread(benchmark_excess.tolist()):
        beta = ratio(
            _covariance(excess, benchmark_excess),
            sample_variance(benchmark_excess.tolist()),
            "beta",
        )
    else:
        warn("zero_volatility", "beta divides by a benchmark with no spread")
    treynor = alpha = None
    if beta is not None:
        treynor = ratio(mean_excess * m, beta, "Treynor ratio")
        intercept = mean_excess - beta * sample_mean(benchmark_excess.tolist())
        alpha = optional(intercept * m, -_RETURN_OUT, _RETURN_OUT, "Jensen's alpha")
    m_squared = None
    if sharpe is not None:
        level = (
            sample_mean(f.tolist()) * m
            + sharpe * _deviation_of(benchmark_excess) * root
        )
        m_squared = optional(level, -_RETURN_OUT, _RETURN_OUT, "M squared")
    growth = optional(
        annualized_log_return(log_return(r.tolist()), r.size, m),
        -1.0,
        _RETURN_OUT,
        "annualized return",
    )
    drawdown = _drawdown(r)
    calmar = None if growth is None else ratio(growth, drawdown, "Calmar ratio")
    return RiskAdjustedOutputs(
        observations=r.size,
        annualized_return=growth,
        annualized_volatility=_deviation_of(r) * root,
        sharpe_ratio=sharpe,
        downside_deviation=downside * root,
        sortino_ratio=sortino,
        beta=beta,
        treynor_ratio=treynor,
        jensen_alpha=alpha,
        tracking_error=_deviation_of(active) * root,
        information_ratio=_spread_ratio(
            sample_mean(active.tolist()), active, "information ratio", root
        ),
        m_squared=m_squared,
        max_drawdown=drawdown,
        calmar_ratio=calmar,
        up_capture=_capture(r, b, up=True),
        down_capture=_capture(r, b, up=False),
    )


# --- the model ---------------------------------------------------------------

_SHARPE_1966 = Reference(
    key="sharpe1966",
    citation=(
        "Sharpe, W. F. (1966). Mutual fund performance. The Journal of Business, "
        "39(1), 119-138."
    ),
    doi="10.1086/294846",
    locator="The reward-to-variability ratio",
)
_SHARPE_1994 = Reference(
    key="sharpe1994",
    citation=(
        "Sharpe, W. F. (1994). The Sharpe ratio. The Journal of Portfolio "
        "Management, 21(1), 49-58."
    ),
    doi="10.3905/jpm.1994.409501",
    locator=(
        "Eqs. (3)-(6), the ex post Sharpe ratio; eqs. (7)-(10), its annualization"
    ),
)
_SORTINO = Reference(
    key="sortino1994",
    citation=(
        "Sortino, F. A. and Price, L. N. (1994). Performance measurement in a "
        "downside risk framework. The Journal of Investing, 3(3), 59-64."
    ),
    doi="10.3905/joi.3.3.59",
    locator="The downside deviation below a minimum acceptable return",
)
_TREYNOR = Reference(
    key="treynor1965",
    citation=(
        "Treynor, J. L. (1965). How to rate management of investment funds. "
        "Harvard Business Review, 43(1), 63-75. Reprinted in Treynor on "
        "Institutional Investing (2008), Wiley, ch. 10, 69-87."
    ),
    doi="10.1002/9781119196679.ch10",
    locator="The characteristic line and the reward to volatility",
)
_JENSEN = Reference(
    key="jensen1968",
    citation=(
        "Jensen, M. C. (1968). The performance of mutual funds in the period "
        "1945-1964. The Journal of Finance, 23(2), 389-416."
    ),
    doi="10.1111/j.1540-6261.1968.tb00815.x",
    locator="Eq. (8), p. 393, alpha as the intercept of the excess-return regression",
)
_MODIGLIANI = Reference(
    key="modigliani1997",
    citation=(
        "Modigliani, F. and Modigliani, L. (1997). Risk-adjusted performance. "
        "The Journal of Portfolio Management, 23(2), 45-54."
    ),
    doi="10.3905/jpm.23.2.45",
    locator="The risk-adjusted performance (RAP) measure",
)
_BACON = Reference(
    key="bacon2008",
    citation=(
        "Bacon, C. R. (2008). Practical Portfolio Performance Measurement and "
        "Attribution, 2nd ed. Wiley."
    ),
    doi="10.1002/9781119206309.ch4",
    isbn="9780470059289",
    locator=(
        "Chapter 4, pp. 61-115: tracking error, information ratio, M2, "
        "Calmar and capture ratios"
    ),
)


@model(
    id="performance.risk_adjusted",
    version=1,
    title="Risk-adjusted performance",
    summary=(
        "Sharpe, Sortino, Treynor, Jensen's alpha, information ratio and tracking "
        "error, M², Calmar and up- and down-capture ratios from return series."
    ),
    formula=(
        (
            r"S = \frac{\bar{e}}{s_e}\sqrt{m}, \quad Sortino = \frac{\bar{r} - MAR}"
            r"{DD}\sqrt{m}, \quad DD = \sqrt{\tfrac{1}{n}\sum \min(r_t - MAR, 0)^2}"
        ),
        (
            r"\beta = \frac{\operatorname{cov}(e, e^b)}{\operatorname{var}(e^b)}, "
            r"\quad T = \frac{m\bar{e}}{\beta}, \quad \alpha = m(\bar{e} - \beta "
            r"\bar{e}^b)"
        ),
        r"TE = s_a \sqrt{m}, \quad IR = \frac{\bar{a}}{s_a}\sqrt{m}",
        r"M^2 = m\bar{f} + S \cdot s_{e^b}\sqrt{m}",
        (
            r"Calmar = \frac{(\prod (1 + r_t))^{m/n} - 1}{MDD}, \quad UC = "
            r"\frac{\bar{r}^{G}_{b > 0}}{\bar{b}^{G}_{b > 0}}"
        ),
    ),
    assumptions=(
        (
            "Returns are decimals over equal periods, aligned in time; "
            "periods_per_year is explicit and never inferred."
        ),
        (
            "Means and the annualized excess, active and alpha figures are "
            "arithmetic (times m); deviations divide by n - 1, except the downside "
            "deviation below a given minimum acceptable return, which divides by "
            "n; the annualized return and Calmar use compound growth."
        ),
        (
            "Capture ratios are geometric mean returns per period, not annualized, "
            "over the periods when the benchmark's return was above (below) zero."
        ),
    ),
    limitations=(
        (
            "A ratio over a zero denominator (a flat excess, benchmark or active "
            "series, no drawdown, no up or down periods) or past its bounds is "
            "null, with a warning."
        ),
        (
            "Ex post ratios from short samples are noisy; none corrects for "
            "autocorrelation, fat tails or the smoothing of illiquid returns."
        ),
    ),
    references=(
        _SHARPE_1966,
        _SHARPE_1994,
        _SORTINO,
        _TREYNOR,
        _JENSEN,
        _MODIGLIANI,
        _BACON,
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("sharpe", "sortino", "treynor", "alpha", "information ratio", "capture"),
    invariants=(
        Invariant(
            id="sharpe_invariant_to_positive_scaling",
            statement=(
                "Scaling every excess return by the same positive factor leaves "
                "the Sharpe ratio unchanged."
            ),
        ),
        Invariant(
            id="tracking_error_zero_for_identical_series",
            statement=(
                "A portfolio identical to its benchmark has zero tracking error."
            ),
        ),
        Invariant(
            id="capture_ratios_one_for_identical_series",
            statement=(
                "A portfolio identical to its benchmark captures exactly its up "
                "and down periods: both capture ratios are one."
            ),
        ),
        Invariant(
            id="beta_one_alpha_zero_for_identical_series",
            statement=(
                "A portfolio identical to its benchmark has a beta of one and "
                "a Jensen's alpha of zero."
            ),
        ),
    ),
    examples=(
        Example(
            name="twelve_months",
            inputs={
                "returns": [
                    0.021,
                    -0.013,
                    0.034,
                    0.008,
                    -0.022,
                    0.015,
                    0.027,
                    -0.005,
                    0.012,
                    0.019,
                    -0.031,
                    0.024,
                ],
                "benchmark_returns": [
                    0.018,
                    -0.010,
                    0.029,
                    0.011,
                    -0.025,
                    0.012,
                    0.022,
                    -0.002,
                    0.010,
                    0.016,
                    -0.028,
                    0.020,
                ],
                "risk_free_returns": [0.002] * 12,
                "periods_per_year": 12,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def risk_adjusted(inputs: RiskAdjustedInputs) -> RiskAdjustedOutputs:
    """Compute every measure from the return series."""
    return _risk_adjusted(inputs)
