# src/pyeconomics/models/asset_pricing/factor_regression.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Time-series factor regressions: ``asset_pricing.factor_regression``.

An asset's excess return is regressed on the returns of a set of factors,

.. math:: r_t - r_{f,t} = \alpha + \sum_k \beta_k f_{k,t} + e_t,

by least squares (:func:`pyeconomics.core.least_squares`), with Newey-West
standard errors by default. Five factor sets are named by ``calculation``:

- ``capm``: the market's excess return alone (Sharpe 1964; Lintner 1965), with
  the security market line's expected return :math:`r_f + \beta\,\lambda_m` at
  a stated market premium :math:`\lambda_m`;
- ``ff3``: the market, size (SMB) and value (HML) factors (Fama and French
  1993);
- ``carhart``: the three and momentum (Carhart 1997);
- ``ff5``: the market, size, value, profitability (RMW) and investment (CMA)
  factors (Fama and French 2015);
- ``ff6``: the five and momentum (Fama and French 2018).

Alpha is reported per period and annualized by an explicit number of periods a
year, :math:`12\alpha` for monthly data: the arithmetic convention of the
factor literature, not compounding. The residual volatility is the regression's
standard error, :math:`\sqrt{e'e/(T-k)}`, and annualized by :math:`\sqrt{P}`.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    Count,
    Evidence,
    Example,
    Invariant,
    ModelOutputs,
    Ratio,
    Reference,
    Return,
    Volatility,
    least_squares,
    model,
    warn,
)
from pyeconomics.models.asset_pricing._common import (
    ESTIMATE_MAX,
    LAGS_MAX,
    PERIODS_MAX,
    RETURN_MAX,
    Inference,
    ReturnSeries,
    bounded,
    excess,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["factor_regression"]

#: A year has at most this many periods: calendar days.
_PERIODS_PER_YEAR_MAX: Final = 366
#: The residual volatility per period is at most the spread of the excess
#: returns (40) times the root of the periods (about 50): 1e4 is ample.
_RESIDUAL_MAX: Final = 1e4
_ANNUAL_RESIDUAL_MAX: Final = _RESIDUAL_MAX * math.sqrt(_PERIODS_PER_YEAR_MAX)
_ANNUAL_MAX: Final = ESTIMATE_MAX * _PERIODS_PER_YEAR_MAX
#: The security market line's expected return: a beta of at most 1e9 times a
#: premium of at most 10, plus a risk-free return of at most 10.
_SML_MAX: Final = ESTIMATE_MAX * RETURN_MAX + RETURN_MAX
#: The months of data a binding reads: five years, the usual estimation window.
_WINDOW: Final = 60

#: What each factor is, in the order a regression's coefficients list them.
FACTORS: Final = {
    "market": "the market's excess return (Mkt-RF)",
    "size": "the size factor (SMB)",
    "value": "the value factor (HML)",
    "profitability": "the profitability factor (RMW)",
    "investment": "the investment factor (CMA)",
    "momentum": "the momentum factor (Mom, UMD)",
}


def _series(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(min_length=3, max_length=PERIODS_MAX, description=description)


def _factor(name: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return _series(f"The return of {FACTORS[name]} each period")


# --- inputs ------------------------------------------------------------------


class _Regression(Inference):
    """An asset's returns and the factors' returns over the same periods."""

    FACTOR_NAMES: ClassVar[tuple[str, ...]] = ("market",)

    returns: ReturnSeries = _series(
        "The asset's return each period; its excess return when risk_free is left out"
    )
    risk_free: ReturnSeries | None = Field(
        None,
        min_length=3,
        max_length=PERIODS_MAX,
        description=(
            "The risk-free return each period, subtracted from returns; leave it "
            "out when returns are already excess returns"
        ),
    )
    market: ReturnSeries = _factor("market")
    periods_per_year: Count = Field(
        ge=1,
        le=_PERIODS_PER_YEAR_MAX,
        description=(
            "Periods in a year, to annualize alpha and the residual volatility: "
            "12 for months, 52 for weeks, 252 for trading days"
        ),
    )

    @model_validator(mode="after")
    def _one_sample(self) -> Self:
        periods = len(self.returns)
        series = {name: getattr(self, name) for name in self.FACTOR_NAMES}
        if self.risk_free is not None:
            series["risk_free"] = self.risk_free
        for name, values in series.items():
            if len(values) != periods:
                msg = f"{name} has {len(values)} periods; returns has {periods}"
                raise ValueError(msg)
        coefficients = 1 + len(self.FACTOR_NAMES)
        if periods <= coefficients:
            msg = f"{coefficients} coefficients need more than {coefficients} periods"
            raise ValueError(msg)
        if self.lags is not None and self.lags >= periods:
            msg = f"lags must be below the {periods} periods"
            raise ValueError(msg)
        return self


class CapmInputs(_Regression):
    """The market factor alone, and a market premium for the security market line."""

    calculation: Literal["capm"] = Field(
        "capm", description="CAPM: beta on the market and the security market line"
    )
    market_premium: Return = Field(
        ge=-RETURN_MAX,
        le=RETURN_MAX,
        description=(
            "The expected market excess return per period, at which the security "
            "market line prices the asset's beta"
        ),
    )
    risk_free_rate: Return = Field(
        0.0,
        ge=-1.0,
        le=RETURN_MAX,
        description=(
            "The risk-free return per period the security market line starts "
            "from; at 0 its expected return is the excess return"
        ),
    )


class Ff3Inputs(_Regression):
    """The Fama-French three factors."""

    FACTOR_NAMES: ClassVar[tuple[str, ...]] = ("market", "size", "value")

    calculation: Literal["ff3"] = Field(
        "ff3", description="Fama-French three factors: market, size and value"
    )
    size: ReturnSeries = _factor("size")
    value: ReturnSeries = _factor("value")


class CarhartInputs(_Regression):
    """The Fama-French three factors and momentum."""

    FACTOR_NAMES: ClassVar[tuple[str, ...]] = ("market", "size", "value", "momentum")

    calculation: Literal["carhart"] = Field(
        "carhart", description="Carhart four factors: the three and momentum"
    )
    size: ReturnSeries = _factor("size")
    value: ReturnSeries = _factor("value")
    momentum: ReturnSeries = _factor("momentum")


class Ff5Inputs(_Regression):
    """The Fama-French five factors."""

    FACTOR_NAMES: ClassVar[tuple[str, ...]] = (
        "market",
        "size",
        "value",
        "profitability",
        "investment",
    )

    calculation: Literal["ff5"] = Field(
        "ff5",
        description=(
            "Fama-French five factors: market, size, value, profitability and "
            "investment"
        ),
    )
    size: ReturnSeries = _factor("size")
    value: ReturnSeries = _factor("value")
    profitability: ReturnSeries = _factor("profitability")
    investment: ReturnSeries = _factor("investment")


class Ff6Inputs(_Regression):
    """The Fama-French five factors and momentum."""

    FACTOR_NAMES: ClassVar[tuple[str, ...]] = (
        "market",
        "size",
        "value",
        "profitability",
        "investment",
        "momentum",
    )

    calculation: Literal["ff6"] = Field(
        "ff6", description="Fama-French six factors: the five and momentum"
    )
    size: ReturnSeries = _factor("size")
    value: ReturnSeries = _factor("value")
    profitability: ReturnSeries = _factor("profitability")
    investment: ReturnSeries = _factor("investment")
    momentum: ReturnSeries = _factor("momentum")


FactorRegressionInputs = Annotated[
    CapmInputs | Ff3Inputs | CarhartInputs | Ff5Inputs | Ff6Inputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------

_Beta = Annotated[Ratio, Field(ge=-ESTIMATE_MAX, le=ESTIMATE_MAX)]
_Error = Annotated[Ratio, Field(ge=0.0, le=ESTIMATE_MAX)]


def _beta(name: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(description=f"The beta on {FACTORS[name]}")


def _beta_error(name: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(description=f"The standard error of the beta on {FACTORS[name]}")


def _beta_t(name: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        description=(
            f"The beta on {FACTORS[name]} over its standard error; None for a fit "
            "exact to rounding"
        )
    )


class _Fit(ModelOutputs):
    """Alpha, the market beta and the fit of the regression."""

    alpha: Return = Field(
        ge=-ESTIMATE_MAX,
        le=ESTIMATE_MAX,
        description="The intercept: the average excess return the factors leave",
    )
    alpha_annualized: Return = Field(
        ge=-_ANNUAL_MAX,
        le=_ANNUAL_MAX,
        description="Alpha times the periods in a year",
    )
    alpha_standard_error: Return = Field(
        ge=0.0, le=ESTIMATE_MAX, description="The standard error of alpha per period"
    )
    alpha_t_statistic: _Beta | None = Field(
        description="Alpha over its standard error; None for a fit exact to rounding"
    )
    market_beta: _Beta = _beta("market")
    market_beta_standard_error: _Error = _beta_error("market")
    market_beta_t_statistic: _Beta | None = _beta_t("market")
    r_squared: Ratio | None = Field(
        ge=0.0,
        le=1.0,
        description="R-squared; None when the excess return does not vary",
    )
    residual_volatility: Volatility = Field(
        ge=0.0,
        le=_RESIDUAL_MAX,
        description="The residuals' standard deviation per period, sqrt(e'e / (T - k))",
    )
    residual_volatility_annualized: Volatility = Field(
        ge=0.0,
        le=_ANNUAL_RESIDUAL_MAX,
        description="The residual volatility times the root of the periods in a year",
    )
    observations: Count = Field(
        ge=3, le=PERIODS_MAX, description="Periods in the regression"
    )
    hac_lags: Count = Field(
        ge=0, le=LAGS_MAX, description="Newey-West lags used; 0 for the others"
    )


class CapmOutputs(_Fit):
    calculation: Literal["capm"] = Field(
        "capm", description="CAPM: beta on the market and the security market line"
    )
    expected_excess_return: Return = Field(
        ge=-_SML_MAX,
        le=_SML_MAX,
        description=(
            "The security market line's excess return for the beta: beta times "
            "the market premium, per period"
        ),
    )
    expected_return: Return = Field(
        ge=-_SML_MAX - 1.0,
        le=_SML_MAX + RETURN_MAX,
        description=(
            "The security market line's expected return: the risk-free rate plus "
            "the excess return, per period"
        ),
    )


class _SizeValue(_Fit):
    """The size and value betas."""

    size_beta: _Beta = _beta("size")
    size_beta_standard_error: _Error = _beta_error("size")
    size_beta_t_statistic: _Beta | None = _beta_t("size")
    value_beta: _Beta = _beta("value")
    value_beta_standard_error: _Error = _beta_error("value")
    value_beta_t_statistic: _Beta | None = _beta_t("value")


class _ProfitabilityInvestment(_SizeValue):
    """The profitability and investment betas, with size and value."""

    profitability_beta: _Beta = _beta("profitability")
    profitability_beta_standard_error: _Error = _beta_error("profitability")
    profitability_beta_t_statistic: _Beta | None = _beta_t("profitability")
    investment_beta: _Beta = _beta("investment")
    investment_beta_standard_error: _Error = _beta_error("investment")
    investment_beta_t_statistic: _Beta | None = _beta_t("investment")


class Ff3Outputs(_SizeValue):
    calculation: Literal["ff3"] = Field(
        "ff3", description="Fama-French three factors: market, size and value"
    )


class CarhartOutputs(_SizeValue):
    calculation: Literal["carhart"] = Field(
        "carhart", description="Carhart four factors: the three and momentum"
    )
    momentum_beta: _Beta = _beta("momentum")
    momentum_beta_standard_error: _Error = _beta_error("momentum")
    momentum_beta_t_statistic: _Beta | None = _beta_t("momentum")


class Ff5Outputs(_ProfitabilityInvestment):
    calculation: Literal["ff5"] = Field(
        "ff5",
        description=(
            "Fama-French five factors: market, size, value, profitability and "
            "investment"
        ),
    )


class Ff6Outputs(_ProfitabilityInvestment):
    calculation: Literal["ff6"] = Field(
        "ff6", description="Fama-French six factors: the five and momentum"
    )
    momentum_beta: _Beta = _beta("momentum")
    momentum_beta_standard_error: _Error = _beta_error("momentum")
    momentum_beta_t_statistic: _Beta | None = _beta_t("momentum")


FactorRegressionOutputs = Annotated[
    CapmOutputs | Ff3Outputs | CarhartOutputs | Ff5Outputs | Ff6Outputs,
    Field(discriminator="calculation"),
]


# --- the calculation ---------------------------------------------------------


def _t_statistics(t: tuple[float, ...] | None, count: int) -> list[float | None]:
    """Return each t statistic, or ``None`` where the fit is exact to rounding."""
    if t is None:
        warn(
            "exact_fit",
            "the regression fits exactly: its standard errors are zero and it has "
            "no t statistics",
        )
        return [None] * count
    kept: list[float | None] = [v if abs(v) <= ESTIMATE_MAX else None for v in t]
    if None in kept:
        warn(
            "near_exact_fit",
            f"a t statistic passes {ESTIMATE_MAX:g}: the fit is exact but for "
            "rounding, so that t statistic is not reported",
        )
    return kept


def _regress(inputs: _Regression) -> dict[str, Any]:
    """Fit the regression and return the outputs every factor set shares."""
    names = inputs.FACTOR_NAMES
    response = excess(np.asarray(inputs.returns, dtype=np.float64), inputs.risk_free)
    design = np.column_stack(
        [np.asarray(getattr(inputs, name), dtype=np.float64) for name in names]
    )
    fit = least_squares(
        response, design, covariance=inputs.covariance, lags=inputs.lags
    )
    coefficients = bounded(fit.coefficients, "coefficient")
    errors = bounded(fit.standard_errors, "standard error")
    t = _t_statistics(fit.t_statistics, len(coefficients))
    if fit.r_squared is None:
        warn("no_variation", "the excess return does not vary: no R-squared")
    # sqrt(e'e / (T - k)), with e scaled first so tiny residuals keep their digits.
    largest = max(abs(e) for e in fit.residuals)
    residual = 0.0
    if largest > 0:
        rss = math.fsum((e / largest) ** 2 for e in fit.residuals)
        residual = largest * math.sqrt(rss / fit.degrees_of_freedom)
    periods = inputs.periods_per_year
    found: dict[str, Any] = {
        "alpha": coefficients[0],
        "alpha_annualized": coefficients[0] * periods,
        "alpha_standard_error": errors[0],
        "alpha_t_statistic": t[0],
        "r_squared": fit.r_squared,
        "residual_volatility": residual,
        "residual_volatility_annualized": residual * math.sqrt(periods),
        "observations": fit.observations,
        "hac_lags": fit.lags,
    }
    for position, name in enumerate(names, start=1):
        found[f"{name}_beta"] = coefficients[position]
        found[f"{name}_beta_standard_error"] = errors[position]
        found[f"{name}_beta_t_statistic"] = t[position]
    return found


def _capm(inputs: CapmInputs) -> CapmOutputs:
    found = _regress(inputs)
    premium = found["market_beta"] * inputs.market_premium
    return CapmOutputs(
        **found,
        expected_excess_return=premium,
        expected_return=inputs.risk_free_rate + premium,
    )


type _FactorOutputs = Ff3Outputs | CarhartOutputs | Ff5Outputs | Ff6Outputs

_OUTPUTS: Final[dict[type[_Regression], type[_FactorOutputs]]] = {
    Ff3Inputs: Ff3Outputs,
    CarhartInputs: CarhartOutputs,
    Ff5Inputs: Ff5Outputs,
    Ff6Inputs: Ff6Outputs,
}


def _factors(inputs: _Regression) -> _FactorOutputs:
    return _OUTPUTS[type(inputs)](**_regress(inputs))


# --- the model ---------------------------------------------------------------

_SHARPE = Reference(
    key="sharpe1964",
    citation=(
        "Sharpe, W. F. (1964). Capital Asset Prices: A Theory of Market "
        "Equilibrium under Conditions of Risk. The Journal of Finance, 19(3), "
        "425-442."
    ),
    doi="10.1111/j.1540-6261.1964.tb02865.x",
    locator="The expected return of an asset in equilibrium, linear in its beta",
)
_LINTNER = Reference(
    key="lintner1965",
    citation=(
        "Lintner, J. (1965). The Valuation of Risk Assets and the Selection of "
        "Risky Investments in Stock Portfolios and Capital Budgets. The Review of "
        "Economics and Statistics, 47(1), 13-37."
    ),
    doi="10.2307/1924119",
    locator="Expected returns linear in the covariance with the market",
)
_FAMA_FRENCH_1993 = Reference(
    key="ff1993",
    citation=(
        "Fama, E. F. and French, K. R. (1993). Common risk factors in the returns "
        "on stocks and bonds. Journal of Financial Economics, 33(1), 3-56."
    ),
    doi="10.1016/0304-405X(93)90023-5",
    locator="The three-factor time-series regressions of excess returns",
)
_CARHART = Reference(
    key="carhart1997",
    citation=(
        "Carhart, M. M. (1997). On Persistence in Mutual Fund Performance. The "
        "Journal of Finance, 52(1), 57-82."
    ),
    doi="10.1111/j.1540-6261.1997.tb03808.x",
    locator="The four-factor model: the three and one-year momentum",
)
_FAMA_FRENCH_2015 = Reference(
    key="ff2015",
    citation=(
        "Fama, E. F. and French, K. R. (2015). A five-factor asset pricing model. "
        "Journal of Financial Economics, 116(1), 1-22."
    ),
    doi="10.1016/j.jfineco.2014.10.010",
    locator="The five-factor time-series regression",
)
_FAMA_FRENCH_2018 = Reference(
    key="ff2018",
    citation=(
        "Fama, E. F. and French, K. R. (2018). Choosing factors. Journal of "
        "Financial Economics, 128(2), 234-252."
    ),
    doi="10.1016/j.jfineco.2018.02.012",
    locator="The six-factor model: the five and momentum",
)
_NEWEY_WEST = Reference(
    key="newey1987",
    citation=(
        "Newey, W. K. and West, K. D. (1987). A simple, positive semi-definite, "
        "heteroskedasticity and autocorrelation consistent covariance matrix. "
        "Econometrica, 55(3), 703-708."
    ),
    doi="10.2307/1913610",
    locator="Bartlett weights 1 - j / (L + 1)",
)
_KEN_FRENCH = Reference(
    key="french_library",
    citation=(
        "French, K. R. Data Library: the Fama/French factors and the momentum "
        "factor, monthly. Tuck School of Business, Dartmouth College."
    ),
    url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
    locator="Fama/French 3 Factors, Fama/French 5 Factors (2x3) and Momentum Factor",
)

_SAMPLE: Final = {
    "returns": [
        0.021,
        -0.013,
        0.034,
        0.008,
        -0.022,
        0.015,
        0.027,
        -0.004,
        0.012,
        0.019,
    ],
    "risk_free": [
        0.004,
        0.004,
        0.004,
        0.0045,
        0.0045,
        0.0045,
        0.0042,
        0.0042,
        0.0041,
        0.0041,
    ],
    "market": [0.018, -0.02, 0.03, 0.006, -0.025, 0.012, 0.022, -0.006, 0.009, 0.016],
    "periods_per_year": 12,
}
_SIZE_VALUE: Final = {
    "size": [0.004, -0.006, 0.011, -0.002, 0.003, 0.007, -0.005, 0.001, 0.002, -0.004],
    "value": [-0.003, 0.008, -0.004, 0.006, 0.01, -0.002, 0.004, -0.007, 0.005, 0.0],
}
_PROFITABILITY_INVESTMENT: Final = {
    "profitability": [
        0.002,
        0.004,
        -0.001,
        0.003,
        0.006,
        -0.002,
        0.001,
        0.005,
        -0.003,
        0.002,
    ],
    "investment": [
        0.001,
        0.005,
        -0.003,
        0.002,
        0.004,
        0.0,
        -0.002,
        0.003,
        0.001,
        -0.001,
    ],
}
_MOMENTUM: Final = {
    "momentum": [
        0.012,
        -0.018,
        0.006,
        0.009,
        -0.031,
        0.014,
        0.007,
        -0.002,
        0.011,
        0.004,
    ]
}


def _bindings(
    profile: str, market: str, size: str, extra: dict[str, str]
) -> tuple[Binding, ...]:
    fields = {
        "market": market,
        "size": size,
        "value": "factors.ff3_hml.us.monthly",
        **extra,
        "momentum": "factors.mom.us.monthly",
        "risk_free": "factors.risk_free.us.monthly",
    }
    return tuple(
        Binding(field, concept, as_of=AsOf.WINDOW, window=_WINDOW, profile=profile)
        for field, concept in fields.items()
    )


@model(
    id="asset_pricing.factor_regression",
    version=1,
    title="Factor regressions: CAPM to the six-factor model",
    summary=(
        "An asset's excess returns regressed on the market (CAPM), the "
        "Fama-French three or five factors, Carhart's four or the six-factor "
        "model: alpha per period and annualized, each beta with Newey-West "
        "errors, R-squared, residual volatility and the CAPM's security market "
        "line."
    ),
    formula=(
        r"r_t - r_{f,t} = \alpha + \sum_{k} \beta_k f_{k,t} + e_t",
        (
            r"\hat\beta = (X'X)^{-1} X'y, \quad V_{NW} = (X'X)^{-1} \hat S "
            r"(X'X)^{-1}, \quad \alpha_{\text{annual}} = P\,\alpha"
        ),
        (
            r"\text{CAPM: } \hat\beta_m = \frac{\widehat{\mathrm{Cov}}(r - r_f, f_m)}"
            r"{\widehat{\mathrm{Var}}(f_m)}, \quad E[r] = r_f + \hat\beta_m \lambda_m"
        ),
        (
            r"\sigma_e = \sqrt{e'e / (T - k)}, \quad "
            r"\sigma_{e,\text{annual}} = \sqrt{P}\,\sigma_e"
        ),
    ),
    assumptions=(
        (
            "The factors are excess returns of traded portfolios over the same "
            "periods as the asset's returns, and the betas are constant over the "
            "sample."
        ),
        (
            "The coefficients are least squares; Newey-West errors use Bartlett "
            "weights with no small-sample correction and, with no lag given, "
            "floor(4 (T/100)^(2/9)) lags."
        ),
        (
            "Alpha is annualized by multiplying it by the periods in a year, the "
            "residual volatility by their square root: arithmetic scaling, not "
            "compounding."
        ),
        (
            "Profiles: default binds 60 months of the Ken French three-factor "
            "file's market, size and value factors, the momentum factor and the "
            "risk-free return (capm, ff3 and carhart); ff5 binds the five-factor "
            "file's market, size, profitability and investment factors with the "
            "same value, momentum and risk-free series (ff5 and ff6). The asset's "
            "returns are the user's own: supply the same 60 months."
        ),
    ),
    limitations=(
        (
            "A factor that barely varies, or factors collinear to working "
            "precision, leave the betas unidentified: DomainError, as for an "
            "estimate beyond 1e9 in size."
        ),
        (
            "Alpha measures performance against the chosen factors only; it says "
            "nothing about factors left out, and the t statistics are only as "
            "good as the error model behind them."
        ),
        (
            "The Ken French factors are library-only: fetched at run time from the "
            "Data Library and never stored. A bound window ends at the library's "
            "latest month on or before the date; the asset's returns must cover "
            "the same months, which the data-source records name."
        ),
        (
            "A profile binds the files' factors only for the calculations it "
            "names: bind ff5 and ff6 with profile='ff5', whose size factor is the "
            "five-factor file's."
        ),
    ),
    references=(
        _SHARPE,
        _LINTNER,
        _FAMA_FRENCH_1993,
        _CARHART,
        _FAMA_FRENCH_2015,
        _FAMA_FRENCH_2018,
        _NEWEY_WEST,
        _KEN_FRENCH,
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    tags=(
        "capm",
        "beta",
        "alpha",
        "fama-french",
        "carhart",
        "factor model",
        "security market line",
    ),
    invariants=(
        Invariant(
            id="exact_factor_data_recovers_betas",
            statement=(
                "When the excess returns are exactly alpha plus the betas times the "
                "factors, the estimates are that alpha and those betas."
            ),
        ),
        Invariant(
            id="capm_beta_equals_covariance_over_variance",
            statement=(
                "The CAPM beta is the sample covariance of the excess return with "
                "the market over the market's sample variance."
            ),
        ),
        Invariant(
            id="annualized_alpha_is_alpha_times_periods",
            statement="The annualized alpha is alpha times the periods in a year.",
        ),
    ),
    examples=(
        Example(
            name="capm_ten_months",
            inputs={
                "calculation": "capm",
                **_SAMPLE,
                "market_premium": 0.005,
                "risk_free_rate": 0.004,
            },
            note="Ten months of returns, with a 0.5% monthly market premium.",
        ),
        Example(
            name="ff3_ten_months",
            inputs={
                "calculation": "ff3",
                **_SAMPLE,
                **_SIZE_VALUE,
                "covariance": "classical",
            },
        ),
        Example(
            name="carhart_ten_months",
            inputs={"calculation": "carhart", **_SAMPLE, **_SIZE_VALUE, **_MOMENTUM},
        ),
        Example(
            name="ff5_ten_months",
            inputs={
                "calculation": "ff5",
                **_SAMPLE,
                **_SIZE_VALUE,
                **_PROFITABILITY_INVESTMENT,
                "covariance": "hc1",
            },
        ),
        Example(
            name="ff6_ten_months",
            inputs={
                "calculation": "ff6",
                **_SAMPLE,
                **_SIZE_VALUE,
                **_PROFITABILITY_INVESTMENT,
                **_MOMENTUM,
                "covariance": "classical",
            },
        ),
    ),
    bindings=(
        *_bindings(
            "default", "factors.ff3_market.us.monthly", "factors.ff3_smb.us.monthly", {}
        ),
        *_bindings(
            "ff5",
            "factors.ff5_market.us.monthly",
            "factors.ff5_smb.us.monthly",
            {
                "profitability": "factors.ff5_rmw.us.monthly",
                "investment": "factors.ff5_cma.us.monthly",
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def factor_regression(inputs: FactorRegressionInputs) -> FactorRegressionOutputs:
    """Regress the asset's excess returns on the factor set the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[_Regression], Callable[[Any], FactorRegressionOutputs]]
] = {
    CapmInputs: _capm,
    Ff3Inputs: _factors,
    CarhartInputs: _factors,
    Ff5Inputs: _factors,
    Ff6Inputs: _factors,
}
