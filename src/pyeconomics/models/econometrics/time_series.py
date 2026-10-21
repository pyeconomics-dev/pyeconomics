# src/pyeconomics/models/econometrics/time_series.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""ARIMA, VAR and cointegration tests: ``econometrics.time_series``.

An adapter over statsmodels (ROADMAP section 4 7.3, "wrap, don't rewrite"),
behind the ``econometrics`` extra: statsmodels is imported inside ``compute``,
and without it the model raises
:class:`~pyeconomics.core.MissingOptionalDependencyError` naming
``pyeconomics[econometrics]``. The ``calculation`` names the method:

- ``arima``: an ARIMA(p, d, q) or seasonal ARIMA(p, d, q)(P, D, Q, s) fitted by
  exact maximum likelihood (the state-space Kalman filter, Box and Jenkins'
  models), its information criteria, and forecasts with intervals;
- ``var``: a vector autoregression fitted equation by equation by least
  squares, its lag order chosen by AIC, BIC or Hannan-Quinn (Lütkepohl 2005),
  orthogonalized impulse responses under the Cholesky ordering of the inputs
  (``series`` first), and the forecast-error variance decomposition;
- ``engle_granger``: the two-step test of Engle and Granger (1987), an
  augmented Dickey-Fuller test on the residuals of the cointegrating
  regression with MacKinnon's (1994) p-values and (2010) critical values;
- ``johansen``: Johansen's (1991) trace and maximum-eigenvalue statistics with
  the critical values of MacKinnon, Haug and Michelis (1999), and the
  cointegrating rank each test selects.

The variables are ``series`` (the only one for ``arima``; the dependent one
for ``engle_granger``) and ``second`` to ``sixth``, all of one length, oldest
first, each in its own units.
"""

from __future__ import annotations

import math
from itertools import pairwise
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
    AsOf,
    Binding,
    ChangelogEntry,
    ChartKind,
    ChartSpec,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    Invariant,
    MissingOptionalDependencyError,
    ModelInputs,
    ModelOutputs,
    Probability,
    Ratio,
    Reference,
    generator,
    has_spread,
    library_warnings,
    model,
    warn,
)
from pyeconomics.core.model import ARRAY_INPUT

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

__all__ = ["time_series"]

#: The extra that installs statsmodels.
EXTRA: Final = "econometrics"
#: The most observations a series holds, and the most variables.
OBSERVATIONS_MAX: Final = 2_000
VARIABLES_MAX: Final = 6
#: A value of a series, in its own units (an index level, a rate, a count).
VALUE_MAX: Final = 1e9
#: ARIMA orders: p and q, d, the seasonal P and Q, D, and the season's length.
#: A 2,000-observation SARIMA(4, 2, 4)(2, 1, 2, 12) is the slowest fit, a few
#: seconds to a minute.
ARMA_MAX: Final = 4
DIFFERENCE_MAX: Final = 2
SEASONAL_ARMA_MAX: Final = 2
SEASONAL_DIFFERENCE_MAX: Final = 1
SEASON_MAX: Final = 12
#: The longest ARIMA forecast, and the longest impulse response and variance
#: decomposition.
FORECAST_MAX: Final = 120
RESPONSE_MAX: Final = 60
#: VAR lags and the lagged differences of the Johansen test.
LAGS_MAX: Final = 12
#: The ADF lags of the Engle-Granger test.
ADF_LAGS_MAX: Final = 24
#: The significance levels the published critical values cover.
LEVELS: Final = (0.1, 0.05, 0.01)
#: Outputs beyond this size raise DomainError.
OUT_MAX: Final = 1e300
_NAME_MAX: Final = 32
_TERMS_MAX: Final = 2 + VARIABLES_MAX * LAGS_MAX
_ARIMA_PARAMETERS_MAX: Final = 2 + 2 * ARMA_MAX + 2 * SEASONAL_ARMA_MAX + 1
#: An eigenvalue's imaginary part this small, relative to the largest
#: eigenvalue, is rounding error in a real symmetric-definite problem.
_IMAGINARY_SLACK: Final = 1e-8
#: The default demonstration window: twenty years of months.
_WINDOW: Final = 240
#: The variable fields, in the Cholesky ordering of a VAR.
FIELDS: Final = ("series", "second", "third", "fourth", "fifth", "sixth")

_Trend = Literal["n", "c", "t", "ct"]
_Value = Annotated[Ratio, Field(ge=-VALUE_MAX, le=VALUE_MAX)]
_Series = Annotated[tuple[_Value, ...], ARRAY_INPUT]
_Out = Annotated[Ratio, Field(ge=-OUT_MAX, le=OUT_MAX)]
_NonNegative = Annotated[Ratio, Field(ge=0, le=OUT_MAX)]
_Share = Annotated[Probability, Field(ge=0, le=1)]
_Name = Annotated[str, Field(min_length=1, max_length=_NAME_MAX)]


def _variable(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        None, min_length=3, max_length=OBSERVATIONS_MAX, description=description
    )


# --- inputs ------------------------------------------------------------------


class _Variables(ModelInputs):
    """The first variable, every calculation's."""

    series: _Series = Field(
        min_length=3,
        max_length=OBSERVATIONS_MAX,
        description="The first (or only) variable, oldest first, in its own units",
    )
    names: tuple[_Name, ...] | None = Field(
        None,
        max_length=VARIABLES_MAX,
        description="A name for each variable; the field names when null",
    )

    def variables(self) -> list[tuple[float, ...]]:
        """Return the variables given, in order."""
        given = [getattr(self, name, None) for name in FIELDS]
        return [values for values in given if values is not None]

    def labels(self) -> tuple[str, ...]:
        """Return the variables' names: the given ones, or the field names."""
        count = len(self.variables())
        return self.names if self.names is not None else FIELDS[:count]

    @model_validator(mode="after")
    def _one_length(self) -> Self:
        given = [getattr(self, name, None) for name in FIELDS]
        present = [values is not None for values in given]
        if any(later and not earlier for earlier, later in pairwise(present)):
            msg = "give the variables in order, from series to sixth, without a gap"
            raise ValueError(msg)
        lengths = {len(values) for values in given if values is not None}
        if len(lengths) != 1:
            msg = "every variable must have the same number of observations"
            raise ValueError(msg)
        if self.names is not None:
            if len(self.names) != sum(present):
                msg = f"names must name each of the {sum(present)} variables"
                raise ValueError(msg)
            if len(set(self.names)) != len(self.names):
                msg = "names must be unique"
                raise ValueError(msg)
        return self


class _Several(_Variables):
    """Two to six variables of one length."""

    second: _Series = Field(
        min_length=3,
        max_length=OBSERVATIONS_MAX,
        description="The second variable, in its own units",
    )
    third: _Series | None = _variable("The third variable, if any")
    fourth: _Series | None = _variable("The fourth variable, if any")
    fifth: _Series | None = _variable("The fifth variable, if any")
    sixth: _Series | None = _variable("The sixth variable, if any")


class ArimaInputs(_Variables):
    """One series and the orders of its seasonal ARIMA."""

    calculation: Literal["arima"] = Field(
        "arima", description="ARIMA or seasonal ARIMA (Box and Jenkins)"
    )
    ar: Count = Field(1, ge=0, le=ARMA_MAX, description="Autoregressive order, p")
    differences: Count = Field(
        0, ge=0, le=DIFFERENCE_MAX, description="Order of differencing, d"
    )
    ma: Count = Field(0, ge=0, le=ARMA_MAX, description="Moving-average order, q")
    seasonal_ar: Count = Field(
        0, ge=0, le=SEASONAL_ARMA_MAX, description="Seasonal autoregressive order, P"
    )
    seasonal_differences: Count = Field(
        0,
        ge=0,
        le=SEASONAL_DIFFERENCE_MAX,
        description="Order of seasonal differencing, D",
    )
    seasonal_ma: Count = Field(
        0, ge=0, le=SEASONAL_ARMA_MAX, description="Seasonal moving-average order, Q"
    )
    season: Count = Field(
        0,
        ge=0,
        le=SEASON_MAX,
        description="Periods in a season, s (12 for months); 0 for no seasonal part",
    )
    trend: _Trend | None = Field(
        None,
        description=(
            "Deterministic terms: none, a constant, a linear trend or both; null "
            "for a constant without differencing and none with it"
        ),
    )
    horizon: Count = Field(12, ge=1, le=FORECAST_MAX, description="Periods to forecast")
    alpha: Probability = Field(
        0.05, ge=0.001, le=0.5, description="1 - the forecast intervals' coverage"
    )

    def deterministic(self) -> _Trend:
        """Return the trend, resolving null as statsmodels does."""
        if self.trend is not None:
            return self.trend
        return "c" if self.differences + self.seasonal_differences == 0 else "n"

    def parameter_count(self) -> int:
        """Return the number of parameters the model estimates, sigma2 included."""
        trend = {"n": 0, "c": 1, "t": 1, "ct": 2}[self.deterministic()]
        arma = self.ar + self.ma + self.seasonal_ar + self.seasonal_ma
        return trend + arma + 1

    @model_validator(mode="after")
    def _orders(self) -> Self:
        seasonal = self.seasonal_ar + self.seasonal_differences + self.seasonal_ma
        if self.season == 1 or (self.season == 0 and seasonal > 0):
            msg = "a seasonal part needs a season of at least 2 periods"
            raise ValueError(msg)
        for kind, plain, seasonal_order in (
            ("autoregressive", self.ar, self.seasonal_ar),
            ("moving-average", self.ma, self.seasonal_ma),
        ):
            seasonal_lags = {self.season * i for i in range(1, seasonal_order + 1)}
            if seasonal_lags & set(range(1, plain + 1)):
                msg = (
                    f"a seasonal {kind} lag repeats a non-seasonal one: lower the "
                    "order or lengthen the season"
                )
                raise ValueError(msg)
        integrated = self.differences + self.seasonal_differences
        lowest = {"n": None, "c": 0, "t": 1, "ct": 0}[self.deterministic()]
        if lowest is not None and lowest < integrated:
            msg = (
                f"with {integrated} difference(s) a trend term of order below "
                f"{integrated} is differenced away; choose a higher trend or none"
            )
            raise ValueError(msg)
        lost = self.differences + self.seasonal_differences * self.season
        span = max(self.ar + self.seasonal_ar * self.season, 1)
        needed = lost + span + self.parameter_count() + 1
        if len(self.series) <= needed:
            msg = (
                f"these orders need more than {needed} observations; the series "
                f"has {len(self.series)}"
            )
            raise ValueError(msg)
        return self


class VarInputs(_Several):
    """Two to six variables, a lag order or a criterion to choose one."""

    calculation: Literal["var"] = Field(
        "var", description="A vector autoregression (Sims 1980; Lütkepohl 2005)"
    )
    lags: Count | None = Field(
        None,
        ge=1,
        le=LAGS_MAX,
        description="The lag order; null chooses it by criterion up to max_lags",
    )
    max_lags: Count = Field(
        4, ge=1, le=LAGS_MAX, description="The longest lag order the criterion tries"
    )
    criterion: Literal["aic", "bic", "hqic"] = Field(
        "aic", description="Lag selection: Akaike, Schwarz (BIC) or Hannan-Quinn"
    )
    trend: Literal["n", "c", "ct"] = Field(
        "c", description="Deterministic terms: none, a constant, or both and a trend"
    )
    horizon: Count = Field(
        10,
        ge=1,
        le=RESPONSE_MAX,
        description="Periods of the impulse responses and variance decomposition",
    )

    @model_validator(mode="after")
    def _enough(self) -> Self:
        k = len(self.variables())
        longest = self.lags if self.lags is not None else self.max_lags
        terms = {"n": 0, "c": 1, "ct": 2}[self.trend] + k * longest
        if len(self.series) - longest <= terms + 1:
            msg = (
                f"{longest} lags of {k} variables need more than "
                f"{terms + 1 + longest} observations; there are {len(self.series)}"
            )
            raise ValueError(msg)
        trend = {"n": 0, "c": 1, "ct": 2}[self.trend]
        estimable = (len(self.series) - k - trend) // (1 + k)
        if self.lags is None and estimable < self.max_lags:
            msg = (
                f"choosing among {self.max_lags} lags of {k} variables needs more "
                f"observations: at most {max(estimable, 0)} lags can be compared"
            )
            raise ValueError(msg)
        return self


class EngleGrangerInputs(_Several):
    """A dependent series and one to five regressors."""

    calculation: Literal["engle_granger"] = Field(
        "engle_granger", description="The Engle-Granger two-step test"
    )
    trend: Literal["c", "ct", "ctt"] = Field(
        "c",
        description=(
            "Deterministic terms of the cointegrating regression: a constant, a "
            "linear trend, or a quadratic one"
        ),
    )
    max_lags: Count | None = Field(
        None,
        ge=0,
        le=ADF_LAGS_MAX,
        description="The most ADF lags; null for min(24, ceil(12 (n / 100)^(1/4)))",
    )
    lag_criterion: Literal["aic", "bic"] | None = Field(
        "aic",
        description="Chooses the ADF lags up to max_lags; null uses max_lags",
    )

    def adf_lags(self) -> int:
        """Return the most ADF lags: the input, or Schwert's rule capped at 24."""
        if self.max_lags is not None:
            return self.max_lags
        rule = math.ceil(12 * math.pow(len(self.series) / 100, 0.25))
        return min(ADF_LAGS_MAX, rule)

    @model_validator(mode="after")
    def _enough(self) -> Self:
        regressors = len(self.variables()) - 1
        lags = self.adf_lags()
        needed = 3 * (regressors + 3) + 2 * lags + 2
        if len(self.series) <= needed:
            msg = (
                f"the test needs more than {needed} observations for these "
                f"regressors and lags; there are {len(self.series)}"
            )
            raise ValueError(msg)
        return self


class JohansenInputs(_Several):
    """Two to six variables and the deterministic terms of the VECM."""

    calculation: Literal["johansen"] = Field(
        "johansen", description="Johansen's trace and maximum-eigenvalue tests"
    )
    deterministic: Literal["none", "constant", "trend"] = Field(
        "constant",
        description=(
            "Deterministic terms: none, a constant or a linear trend (statsmodels' "
            "det_order -1, 0 and 1)"
        ),
    )
    lagged_differences: Count = Field(
        1,
        ge=1,
        le=LAGS_MAX,
        description=(
            "Lagged differences in the VECM, k (a VAR of order k + 1); at least "
            "one, because statsmodels pairs the differences with the current "
            "level when there are none"
        ),
    )
    significance: Probability = Field(
        0.05,
        ge=0.01,
        le=0.1,
        description="The level the ranks are chosen at: 0.10, 0.05 or 0.01",
    )

    @model_validator(mode="after")
    def _enough(self) -> Self:
        if not any(math.isclose(self.significance, level) for level in LEVELS):
            msg = "significance must be 0.10, 0.05 or 0.01, the published levels"
            raise ValueError(msg)
        k = len(self.variables())
        needed = k * (self.lagged_differences + 1) + 3 + self.lagged_differences
        if len(self.series) <= needed:
            msg = (
                f"{k} variables with {self.lagged_differences} lagged differences "
                f"need more than {needed} observations; there are {len(self.series)}"
            )
            raise ValueError(msg)
        return self


TimeSeriesInputs = Annotated[
    ArimaInputs | VarInputs | EngleGrangerInputs | JohansenInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


_Names = Annotated[tuple[_Name, ...], Field(max_length=VARIABLES_MAX), ARRAY_INPUT]
_Row = Annotated[tuple[_Out, ...], Field(max_length=VARIABLES_MAX), ARRAY_INPUT]
_Square = Annotated[tuple[_Row, ...], Field(max_length=VARIABLES_MAX)]
_ShareRow = Annotated[tuple[_Share, ...], Field(max_length=VARIABLES_MAX), ARRAY_INPUT]
_ShareSquare = Annotated[tuple[_ShareRow, ...], Field(max_length=VARIABLES_MAX)]
_Critical = Annotated[tuple[_Out, ...], Field(max_length=3), ARRAY_INPUT]
_ParameterNames = Annotated[
    tuple[_Name, ...], Field(max_length=_ARIMA_PARAMETERS_MAX), ARRAY_INPUT
]
_Parameters = Annotated[
    tuple[_Out, ...], Field(max_length=_ARIMA_PARAMETERS_MAX), ARRAY_INPUT
]
_Errors = Annotated[
    tuple[_NonNegative, ...], Field(max_length=_ARIMA_PARAMETERS_MAX), ARRAY_INPUT
]
_PValues = Annotated[
    tuple[_Share, ...], Field(max_length=_ARIMA_PARAMETERS_MAX), ARRAY_INPUT
]
_Horizons = Annotated[
    tuple[Annotated[Count, Field(ge=1, le=FORECAST_MAX)], ...],
    Field(max_length=FORECAST_MAX),
    ARRAY_INPUT,
]
_Path = Annotated[tuple[_Out, ...], Field(max_length=FORECAST_MAX), ARRAY_INPUT]
_PathErrors = Annotated[
    tuple[_NonNegative, ...], Field(max_length=FORECAST_MAX), ARRAY_INPUT
]
#: A VAR term's name: a variable's name behind its lag, "L12.".
_TermName = Annotated[str, Field(min_length=1, max_length=_NAME_MAX + 4)]
_TermNames = Annotated[tuple[_TermName, ...], Field(max_length=_TERMS_MAX), ARRAY_INPUT]
_Terms = Annotated[tuple[_Out, ...], Field(max_length=_TERMS_MAX), ARRAY_INPUT]
_TermErrors = Annotated[
    tuple[_NonNegative, ...], Field(max_length=_TERMS_MAX), ARRAY_INPUT
]
_Equations = Annotated[tuple[_Terms, ...], Field(max_length=VARIABLES_MAX)]
_EquationErrors = Annotated[tuple[_TermErrors, ...], Field(max_length=VARIABLES_MAX)]
_RegressionNames = Annotated[
    tuple[_Name, ...], Field(max_length=VARIABLES_MAX + 2), ARRAY_INPUT
]
_Regression = Annotated[
    tuple[_Out, ...], Field(max_length=VARIABLES_MAX + 2), ARRAY_INPUT
]


def _probability(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0, le=1, description=description)


class _Estimates(ModelOutputs):
    """A likelihood fit's parameters and their inference."""

    parameter_names: _ParameterNames = Field(
        description="Parameter names, as statsmodels gives them (ar.L1, sigma2)"
    )
    parameters: _Parameters = Field(
        description="Estimates, in the series' units (sigma2 in its square)"
    )
    standard_errors: _Errors | None = Field(
        description="Standard errors (outer product of gradients); null if undefined"
    )
    t_statistics: _Parameters | None = Field(
        description="Estimate over standard error; null without standard errors"
    )
    p_values: _PValues | None = Field(
        description="Two-sided p-values from the normal distribution"
    )


class ArimaOutputs(_Estimates):
    calculation: Literal["arima"] = Field("arima", description="ARIMA")
    trend: _Trend = Field(description="The trend fitted")
    log_likelihood: _Out = Field(description="Exact Gaussian log-likelihood")
    aic: _Out = Field(description="Akaike criterion, -2 LL + 2k")
    bic: _Out = Field(description="Schwarz criterion, -2 LL + k ln n")
    hqic: _Out = Field(description="Hannan-Quinn criterion, -2 LL + 2k ln ln n")
    observations: Count = Field(
        ge=3, le=OBSERVATIONS_MAX, description="Observations in the series"
    )
    horizons: _Horizons = Field(
        description="Forecast horizons, 1 to horizon periods ahead"
    )
    forecasts: _Path = Field(description="Forecast mean each period ahead")
    forecast_standard_errors: _PathErrors = Field(
        description="Standard error of each forecast"
    )
    forecast_lower: _Path = Field(
        description="Lower end of each 1 - alpha forecast interval"
    )
    forecast_upper: _Path = Field(
        description="Upper end of each 1 - alpha forecast interval"
    )


class VarOutputs(ModelOutputs):
    calculation: Literal["var"] = Field("var", description="A vector autoregression")
    variables: _Names = Field(
        description="The variables, in the Cholesky ordering of the responses"
    )
    lags: Count = Field(ge=1, le=LAGS_MAX, description="The lag order fitted, p")
    observations: Count = Field(
        ge=1, le=OBSERVATIONS_MAX, description="Observations in the fit, n - p"
    )
    coefficient_names: _TermNames = Field(
        description="Each equation's terms: const, trend, then L1.series and so on"
    )
    coefficients: _Equations = Field(
        description="One row per equation (variable), one value per term"
    )
    standard_errors: _EquationErrors = Field(
        description="The coefficients' standard errors, row by row"
    )
    residual_covariance: _Square = Field(
        description="Covariance of the residuals, with n - p - (terms) degrees"
    )
    log_likelihood: _Out = Field(description="Gaussian log-likelihood")
    aic: _Out = Field(description="ln det(Sigma_ML) + 2 m / n, m the coefficients")
    bic: _Out = Field(description="ln det(Sigma_ML) + m ln n / n")
    hqic: _Out = Field(description="ln det(Sigma_ML) + 2 m ln ln n / n")
    stable: bool = Field(
        description="Whether every lag-polynomial root lies outside the unit circle"
    )
    impulse_responses: Annotated[
        tuple[_Square, ...], Field(max_length=RESPONSE_MAX + 1)
    ] = Field(
        description=(
            "Orthogonalized responses at horizons 0 to horizon: [h][i][j] is "
            "variable i's response to a one-standard-deviation shock j"
        )
    )
    variance_decomposition: Annotated[
        tuple[_ShareSquare, ...], Field(max_length=RESPONSE_MAX)
    ] = Field(
        description=(
            "Forecast-error variance shares 1 to horizon periods ahead: [h][i][j] "
            "is the share of variable i's variance due to shock j"
        )
    )


class EngleGrangerOutputs(ModelOutputs):
    calculation: Literal["engle_granger"] = Field(
        "engle_granger", description="The Engle-Granger test"
    )
    coefficient_names: _RegressionNames = Field(
        description="The cointegrating regression's terms: const, trend, regressors"
    )
    coefficients: _Regression = Field(
        description="The cointegrating regression's least-squares coefficients"
    )
    statistic: _Out = Field(description="ADF t statistic of the residuals")
    p_value: Probability = _probability("MacKinnon's (1994, 2010) p-value")
    critical_levels: _Critical = Field(description="The levels: 0.01, 0.05, 0.10")
    critical_values: _Critical = Field(
        description="MacKinnon's (2010) critical values at those levels"
    )
    lags: Count = Field(ge=0, le=ADF_LAGS_MAX, description="ADF lags used")
    observations: Count = Field(ge=3, le=OBSERVATIONS_MAX, description="Observations")


class JohansenOutputs(ModelOutputs):
    calculation: Literal["johansen"] = Field("johansen", description="Johansen's tests")
    variables: _Names = Field(description="The variables, in order")
    eigenvalues: _Row = Field(description="The eigenvalues, largest first")
    trace_statistics: _Row = Field(
        description="Trace statistic for each null rank r = 0 to K - 1"
    )
    trace_critical_values: _Square = Field(
        description="Critical values per null rank, at 0.10, 0.05 and 0.01"
    )
    max_eigenvalue_statistics: _Row = Field(
        description="Maximum-eigenvalue statistic for each null rank r = 0 to K - 1"
    )
    max_eigenvalue_critical_values: _Square = Field(
        description="Critical values per null rank, at 0.10, 0.05 and 0.01"
    )
    rank_trace: Count = Field(
        ge=0, le=VARIABLES_MAX, description="The rank the trace test selects"
    )
    rank_max_eigenvalue: Count = Field(
        ge=0,
        le=VARIABLES_MAX,
        description="The rank the maximum-eigenvalue test selects",
    )
    observations: Count = Field(
        ge=1, le=OBSERVATIONS_MAX, description="Observations in the test's regressions"
    )


TimeSeriesOutputs = Annotated[
    ArimaOutputs | VarOutputs | EngleGrangerOutputs | JohansenOutputs,
    Field(discriminator="calculation"),
]


# --- the computation ---------------------------------------------------------


def _bounded(value: float, what: str, limit: float = OUT_MAX) -> float:
    if not (math.isfinite(value) and abs(value) <= limit):
        msg = (
            f"the {what} is {value!r}: the method has no answer this model can "
            "represent"
        )
        raise DomainError(msg)
    return value


def _values(array: Any, what: str) -> tuple[float, ...]:  # noqa: ANN401 - array-like
    return tuple(_bounded(float(v), what) for v in np.asarray(array).ravel())


def _rows(array: Any, what: str) -> tuple[tuple[float, ...], ...]:  # noqa: ANN401
    return tuple(_values(row, what) for row in np.asarray(array))


#: The result-warning codes of statsmodels' warning categories (others:
#: statsmodels_warning).
_CODES: Final = {"ConvergenceWarning": "optimizer_not_converged"}


def _recorded() -> Any:  # noqa: ANN401 - a context manager
    """Record statsmodels' warnings inside the block as the result's warnings."""
    return library_warnings("statsmodels", codes=_CODES)


def _data(inputs: _Variables) -> NDArray[np.float64]:
    """Return the variables as columns, refusing one that does not vary."""
    # Adding zero turns -0.0 into 0.0, which canonical JSON cannot tell apart.
    data = np.column_stack(inputs.variables()).astype(np.float64) + 0.0
    for index, label in enumerate(inputs.labels()):
        if not has_spread(data[:, index].tolist()):
            msg = f"{label!r} does not vary: no time-series model can use it"
            raise DomainError(msg)
    return np.asarray(data, dtype=np.float64)


def _inference(
    parameters: NDArray[np.float64], errors: NDArray[np.float64]
) -> dict[str, Any]:
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    none = {"standard_errors": None, "t_statistics": None, "p_values": None}
    if not np.all(np.isfinite(errors)):
        warn(
            "standard_errors_undefined",
            "the information matrix is singular at the estimates: no standard errors",
        )
        return none
    if np.any(errors <= 0):
        warn(
            "standard_errors_undefined",
            "a standard error is zero to working precision: no t statistics",
        )
        return {**none, "standard_errors": _values(errors, "standard error")}
    t = parameters / errors
    return {
        "standard_errors": _values(errors, "standard error"),
        "t_statistics": _values(t, "t statistic"),
        "p_values": tuple(min(1.0, float(p)) for p in 2 * stats.norm.sf(np.abs(t))),
    }


class _Statsmodels:
    """The statsmodels objects the calculations need, imported by ``compute``."""

    def __init__(self, **modules: Any) -> None:  # noqa: ANN401 - modules
        self.__dict__.update(modules)


def _arima(inputs: ArimaInputs, sm: Any) -> ArimaOutputs:  # noqa: ANN401
    y = _data(inputs)[:, 0]
    trend = inputs.deterministic()
    with _recorded():
        fitted = sm.ARIMA(
            y,
            order=(inputs.ar, inputs.differences, inputs.ma),
            seasonal_order=(
                inputs.seasonal_ar,
                inputs.seasonal_differences,
                inputs.seasonal_ma,
                inputs.season,
            ),
            trend=trend,
        ).fit()
        forecast = fitted.get_forecast(steps=inputs.horizon)
        mean = np.asarray(forecast.predicted_mean, dtype=np.float64)
        errors = np.asarray(forecast.se_mean, dtype=np.float64)
        interval = np.asarray(forecast.conf_int(alpha=inputs.alpha), dtype=np.float64)
        bse = np.asarray(fitted.bse, dtype=np.float64)
        criteria = (fitted.llf, fitted.aic, fitted.bic, fitted.hqic)
    llf, aic, bic, hqic = (float(v) for v in criteria)
    parameters = np.asarray(fitted.params, dtype=np.float64)
    return ArimaOutputs(
        parameter_names=tuple(str(n) for n in fitted.param_names),
        parameters=_values(parameters, "parameter"),
        **_inference(parameters, bse),
        trend=trend,
        log_likelihood=_bounded(llf, "log-likelihood"),
        aic=_bounded(aic, "AIC"),
        bic=_bounded(bic, "BIC"),
        hqic=_bounded(hqic, "HQIC"),
        observations=len(y),
        horizons=tuple(range(1, inputs.horizon + 1)),
        forecasts=_values(mean, "forecast"),
        forecast_standard_errors=_values(errors, "forecast standard error"),
        forecast_lower=_values(interval[:, 0], "forecast interval"),
        forecast_upper=_values(interval[:, 1], "forecast interval"),
    )


def _chosen_lags(inputs: VarInputs, model_: Any) -> int:  # noqa: ANN401
    """Return the lag order: the input's, or the criterion's best in 1 to max_lags."""
    if inputs.lags is not None:
        return inputs.lags
    selection = model_.select_order(inputs.max_lags, trend=inputs.trend)
    values = np.asarray(selection.ics[inputs.criterion], dtype=np.float64)
    # statsmodels tries lag 0 only with a deterministic term: the criteria are
    # for the last len(values) orders up to max_lags.
    orders = np.arange(inputs.max_lags + 1 - len(values), inputs.max_lags + 1)
    values, orders = values[orders >= 1], orders[orders >= 1]
    if not np.all(np.isfinite(values)):
        msg = "the lag-selection criterion is not finite: the variables are collinear"
        raise DomainError(msg)
    return int(orders[int(np.argmin(values))])


def _var(inputs: VarInputs, sm: Any) -> VarOutputs:  # noqa: ANN401
    data = _data(inputs)
    labels = inputs.labels()
    with _recorded():
        try:
            model_ = sm.VAR(data)
            lags = _chosen_lags(inputs, model_)
            fitted = model_.fit(lags, trend=inputs.trend)
            sigma = np.asarray(fitted.sigma_u, dtype=np.float64)
            np.linalg.cholesky(sigma)
            orthogonal = fitted.irf(inputs.horizon).orth_irfs
            responses = np.asarray(orthogonal, dtype=np.float64)
            shares = np.asarray(fitted.fevd(inputs.horizon).decomp, dtype=np.float64)
            stable = bool(fitted.is_stable())
            criteria = (fitted.llf, fitted.aic, fitted.bic, fitted.hqic)
            # statsmodels computes these lazily: read them while its warnings
            # are recorded.
            coefficients = np.asarray(fitted.params, dtype=np.float64).T
            errors = np.asarray(fitted.bse, dtype=np.float64).T
        except np.linalg.LinAlgError as error:
            msg = (
                "a moment or residual covariance matrix is singular: the variables "
                "are collinear, so the VAR or its orthogonal shocks are not identified"
            )
            raise DomainError(msg) from error
        except ValueError as error:
            if "constant" not in str(error):
                raise
            msg = (
                "a lagged variable is constant over the fitted sample, which "
                "statsmodels refuses beside the deterministic terms"
            )
            raise DomainError(msg) from error
    if not stable:
        warn(
            "unstable_var",
            "a root of the lag polynomial lies on or inside the unit circle: the "
            "impulse responses do not die out",
        )
    trend_names = {"n": (), "c": ("const",), "ct": ("const", "trend")}[inputs.trend]
    names = (
        *trend_names,
        *(f"L{lag}.{label}" for lag in range(1, lags + 1) for label in labels),
    )
    llf, aic, bic, hqic = (float(v) for v in criteria)
    return VarOutputs(
        variables=labels,
        lags=lags,
        observations=int(fitted.nobs),
        coefficient_names=names,
        coefficients=_rows(coefficients, "coefficient"),
        standard_errors=_rows(errors, "standard error"),
        residual_covariance=_rows(sigma, "residual covariance"),
        log_likelihood=_bounded(llf, "log-likelihood"),
        aic=_bounded(aic, "AIC"),
        bic=_bounded(bic, "BIC"),
        hqic=_bounded(hqic, "HQIC"),
        stable=stable,
        impulse_responses=tuple(_rows(h, "impulse response") for h in responses),
        # statsmodels orders the decomposition (variable, horizon, shock).
        variance_decomposition=tuple(
            tuple(
                tuple(min(1.0, max(0.0, float(v))) for v in row)
                for row in shares[:, h, :]
            )
            for h in range(shares.shape[1])
        ),
    )


def _engle_granger(inputs: EngleGrangerInputs, sm: Any) -> EngleGrangerOutputs:  # noqa: ANN401
    data = _data(inputs)
    y, x = data[:, 0], data[:, 1:]
    trend_names = {
        "c": ("const",),
        "ct": ("const", "trend"),
        "ctt": ("const", "trend", "trend_squared"),
    }[inputs.trend]
    design = sm.add_trend(x, trend=inputs.trend, prepend=True)
    if np.linalg.matrix_rank(design / np.max(np.abs(design), axis=0)) < design.shape[1]:
        msg = "the regressors are collinear with each other or the trend terms"
        raise DomainError(msg)
    with _recorded():
        regression = sm.OLS(y, design).fit()
        residuals = np.asarray(regression.resid, dtype=np.float64)
        if not has_spread(residuals.tolist()) or float(
            np.max(np.abs(residuals))
        ) <= 1e-10 * float(np.max(np.abs(y - np.mean(y)))):
            msg = (
                "the regressors fit the series exactly: the residuals have no "
                "unit root to test"
            )
            raise DomainError(msg)
        statistic, p_value, critical = sm.coint(
            y,
            x,
            trend=inputs.trend,
            method="aeg",
            maxlag=inputs.adf_lags(),
            autolag=inputs.lag_criterion,
        )
        adf = sm.adfuller(
            residuals,
            maxlag=inputs.adf_lags(),
            autolag=inputs.lag_criterion,
            regression="n",
            result_object=True,
        )
    return EngleGrangerOutputs(
        coefficient_names=(
            *trend_names,
            *inputs.labels()[1:],
        ),
        coefficients=_values(regression.params, "coefficient"),
        statistic=_bounded(float(statistic), "ADF statistic"),
        p_value=min(1.0, max(0.0, float(p_value))),
        critical_levels=(0.01, 0.05, 0.1),
        critical_values=_values(critical, "critical value"),
        lags=int(adf.lags),
        observations=len(y),
    )


def _rank(statistics: NDArray[np.float64], critical: NDArray[np.float64]) -> int:
    """Return the first null rank the test does not reject; K if it rejects all."""
    for rank, (statistic, value) in enumerate(zip(statistics, critical, strict=True)):
        if statistic <= value:
            return rank
    return len(statistics)


def _johansen(inputs: JohansenInputs, sm: Any) -> JohansenOutputs:  # noqa: ANN401
    data = _data(inputs)
    order = {"none": -1, "constant": 0, "trend": 1}[inputs.deterministic]
    with _recorded() as caught:
        try:
            result = sm.coint_johansen(data, order, inputs.lagged_differences)
        except np.linalg.LinAlgError as error:
            msg = (
                "the moment matrices of the test are singular: the variables are "
                "collinear"
            )
            raise DomainError(msg) from error
        eigenvalues = np.asarray(result.eig)
        # statsmodels solves a real symmetric-definite eigenproblem with a general
        # solver, which can return complex values with rounding-error imaginary
        # parts and warn while casting them to real. Those warnings are dropped
        # only when the imaginary parts are rounding error; anything more is not
        # a Johansen test.
        largest = float(np.max(np.abs(eigenvalues))) if eigenvalues.size else 0.0
        if np.iscomplexobj(eigenvalues):
            imaginary = float(np.max(np.abs(eigenvalues.imag)))
            if imaginary > _IMAGINARY_SLACK * max(1.0, largest):
                msg = "the test's eigenvalues are complex: the moments are degenerate"
                raise DomainError(msg)
            caught[:] = [
                w for w in caught if type(w.message).__name__ != "ComplexWarning"
            ]
            eigenvalues = eigenvalues.real
    if not np.all((eigenvalues >= 0) & (eigenvalues < 1)):
        msg = "an eigenvalue lies outside [0, 1): the variables are collinear"
        raise DomainError(msg)
    level = LEVELS.index(min(LEVELS, key=lambda v: abs(v - inputs.significance)))
    trace, maximum = np.asarray(result.lr1), np.asarray(result.lr2)
    trace_critical, max_critical = np.asarray(result.cvt), np.asarray(result.cvm)
    return JohansenOutputs(
        variables=inputs.labels(),
        eigenvalues=_values(eigenvalues, "eigenvalue"),
        trace_statistics=_values(trace, "trace statistic"),
        trace_critical_values=_rows(trace_critical, "critical value"),
        max_eigenvalue_statistics=_values(maximum, "maximum-eigenvalue statistic"),
        max_eigenvalue_critical_values=_rows(max_critical, "critical value"),
        rank_trace=_rank(trace, trace_critical[:, level]),
        rank_max_eigenvalue=_rank(maximum, max_critical[:, level]),
        observations=int(np.asarray(result.r0t).shape[0]),
    )


_CALCULATIONS: Final[dict[str, Callable[[Any, Any], TimeSeriesOutputs]]] = {
    "arima": _arima,
    "var": _var,
    "engle_granger": _engle_granger,
    "johansen": _johansen,
}


# --- the model ---------------------------------------------------------------


def _example_data(count: int, seed: int) -> tuple[tuple[float, ...], ...]:
    """Simulate a random walk, a series cointegrated with it, and a stable pair."""
    shocks = generator(seed).standard_normal((count, 3))
    level, autoregressive, other = 0.0, 0.0, 0.0
    walk, pair, ar1, linked = [], [], [], []
    for first, second, third in shocks:
        level += float(first)
        other = 0.3 * autoregressive + 0.4 * other + float(second)
        autoregressive = 0.6 * autoregressive + float(third)
        walk.append(round(level, 4))
        pair.append(round(0.5 * level + float(second), 4))
        ar1.append(round(autoregressive, 4))
        linked.append(round(other, 4))
    return tuple(walk), tuple(pair), tuple(ar1), tuple(linked)


_LEVEL, _PAIR, _AR1, _LINKED = _example_data(120, 11)

_BOX_JENKINS = Reference(
    key="box2015",
    citation=(
        "Box, G. E. P., Jenkins, G. M., Reinsel, G. C. and Ljung, G. M. (2015). "
        "Time Series Analysis: Forecasting and Control, 5th ed. Wiley."
    ),
    url=(
        "https://www.wiley.com/en-us/Time+Series+Analysis%3A+Forecasting+and+"
        "Control%2C+5th+Edition-p-9781118675021"
    ),
    locator="Chapters 4, 7 and 9: ARIMA models, their estimation and seasonal models",
)
_LUTKEPOHL = Reference(
    key="lutkepohl2005",
    citation=(
        "Lütkepohl, H. (2005). New Introduction to Multiple Time Series Analysis. "
        "Springer."
    ),
    doi="10.1007/978-3-540-27752-1",
    locator=(
        "Sections 3.2 (least squares), 2.3.2 and 2.3.3 (orthogonalized impulse "
        "responses, forecast-error variance decomposition) and 4.3 (lag criteria)"
    ),
)
_SIMS = Reference(
    key="sims1980",
    citation=(
        "Sims, C. A. (1980). Macroeconomics and reality. Econometrica, 48(1), 1-48."
    ),
    doi="10.2307/1912017",
    locator="Section 5: innovation accounting with a triangular orthogonalization",
)
_HANNAN_QUINN = Reference(
    key="hannan1979",
    citation=(
        "Hannan, E. J. and Quinn, B. G. (1979). The determination of the order of "
        "an autoregression. Journal of the Royal Statistical Society: Series B, "
        "41(2), 190-195."
    ),
    doi="10.1111/j.2517-6161.1979.tb01072.x",
    locator="The criterion with penalty 2 k ln ln n",
)
_ENGLE_GRANGER = Reference(
    key="engle1987",
    citation=(
        "Engle, R. F. and Granger, C. W. J. (1987). Co-integration and error "
        "correction: Representation, estimation, and testing. Econometrica, 55(2), "
        "251-276."
    ),
    doi="10.2307/1913236",
    locator="Section 5: the two-step test on the cointegrating regression",
)
_MACKINNON_1994 = Reference(
    key="mackinnon1994",
    citation=(
        "MacKinnon, J. G. (1994). Approximate asymptotic distribution functions "
        "for unit-root and cointegration tests. Journal of Business & Economic "
        "Statistics, 12(2), 167-176."
    ),
    doi="10.1080/07350015.1994.10510005",
    locator="The response surfaces for p-values",
)
_MACKINNON_2010 = Reference(
    key="mackinnon2010",
    citation=(
        "MacKinnon, J. G. (2010). Critical values for cointegration tests. Queen's "
        "Economics Department Working Paper No. 1227."
    ),
    url="https://www.econ.queensu.ca/sites/econ.queensu.ca/files/wpaper/qed_wp_1227.pdf",
    locator="Table 2: response-surface coefficients of the tau critical values",
)
_JOHANSEN = Reference(
    key="johansen1991",
    citation=(
        "Johansen, S. (1991). Estimation and hypothesis testing of cointegration "
        "vectors in Gaussian vector autoregressive models. Econometrica, 59(6), "
        "1551-1580."
    ),
    doi="10.2307/2938278",
    locator="The trace and maximum-eigenvalue likelihood-ratio statistics",
)
_MHM = Reference(
    key="mackinnon1999",
    citation=(
        "MacKinnon, J. G., Haug, A. A. and Michelis, L. (1999). Numerical "
        "distribution functions of likelihood ratio tests for cointegration. "
        "Journal of Applied Econometrics, 14(5), 563-577."
    ),
    doi="10.1002/(SICI)1099-1255(199909/10)14:5<563::AID-JAE530>3.0.CO;2-R",
    locator="The critical values of the trace and maximum-eigenvalue tests",
)
_STATSMODELS = Reference(
    key="seabold2010",
    citation=(
        "Seabold, S. and Perktold, J. (2010). statsmodels: Econometric and "
        "statistical modeling with Python. Proceedings of the 9th Python in "
        "Science Conference, 92-96."
    ),
    doi="10.25080/Majora-92bf1922-011",
    locator=(
        "statsmodels.tsa: ARIMA, VAR, stattools.coint, stattools.adfuller and "
        "vector_ar.vecm.coint_johansen"
    ),
)


@model(
    id="econometrics.time_series",
    version=1,
    title="ARIMA, VAR and cointegration tests",
    summary=(
        "ARIMA and seasonal ARIMA fits and forecasts with intervals, VARs with "
        "lag selection, orthogonalized impulse responses and variance "
        "decompositions, and the Engle-Granger and Johansen cointegration tests, "
        "over statsmodels."
    ),
    formula=(
        (
            r"\phi(L)\Phi(L^s)(1-L)^d(1-L^s)^D y_t = c + \theta(L)\Theta(L^s)"
            r"\varepsilon_t, \quad \varepsilon_t \sim N(0, \sigma^2)"
        ),
        (
            r"y_t = \nu + A_1 y_{t-1} + \dots + A_p y_{t-p} + u_t, \quad "
            r"\Sigma_u = P P', \quad \Theta_h = \Phi_h P"
        ),
        (
            r"\omega_{ij,h} = \frac{\sum_{s<h} (e_i' \Theta_s e_j)^2}"
            r"{\sum_{s<h} e_i' \Phi_s \Sigma_u \Phi_s' e_i}"
        ),
        (
            r"y_t = \alpha + \beta' x_t + e_t, \quad \Delta\hat e_t = \rho\,"
            r"\hat e_{t-1} + \sum_{j=1}^{k} \delta_j \Delta\hat e_{t-j} + v_t"
        ),
        (
            r"\lambda_{\text{trace}}(r) = -T \sum_{i=r+1}^{K}\ln(1-\hat\lambda_i), "
            r"\quad \lambda_{\max}(r) = -T\ln(1 - \hat\lambda_{r+1})"
        ),
    ),
    assumptions=(
        (
            "ARIMA: statsmodels' state-space ARIMA, exact Gaussian maximum "
            "likelihood with stationarity and invertibility enforced; standard "
            "errors from the outer product of gradients (statsmodels' default), "
            "p-values normal; intervals "
            "assume normal errors and ignore parameter uncertainty."
        ),
        (
            "VAR: least squares equation by equation; lag order chosen by AIC, BIC "
            "or Hannan-Quinn over 1 to max_lags on a common sample, then refitted "
            "on all the data. The criteria count every coefficient, m = K^2 p plus "
            "K per deterministic term (Lütkepohl's book counts K^2 p alone: the "
            "same order is chosen). Impulse responses are orthogonalized by the "
            "Cholesky factor of the residual covariance in the order series, "
            "second, ..., sixth: a shock to an earlier variable moves later ones at "
            "once, not the reverse."
        ),
        (
            "Engle-Granger: the cointegrating regression of series on the other "
            "variables and the trend terms by least squares, then an ADF test "
            "without deterministic terms on its residuals; statsmodels' coint "
            "gives MacKinnon's p-value and critical values at T = n - 1."
        ),
        (
            "Johansen: statsmodels' coint_johansen (the LeSage implementation), "
            "the deterministic terms detrending the levels before the reduced-rank "
            "regression; critical values from MacKinnon, Haug and Michelis' "
            "johdist at 0.10, 0.05 and 0.01; the rank is the first null not "
            "rejected at the chosen level. At least one lagged difference is "
            "required: with none, coint_johansen regresses the differences on the "
            "current level rather than the lagged one (issue #156)."
        ),
        (
            "Profiles: default binds 240 months of US CPI inflation "
            "(us.inflation.cpi.yoy) to series and the unemployment rate "
            "(us.unemployment.rate) to second, for every calculation (arima reads "
            "series alone). concepts= rebinds either to any other monthly rate or "
            "ratio series in the catalog."
        ),
    ),
    limitations=(
        (
            "A variable that does not vary, collinear variables (a singular "
            "covariance, an exact cointegrating fit, a degenerate eigenproblem) or "
            "an output that is not finite raise DomainError."
        ),
        (
            "The ARIMA optimizer may stop short of the maximum, or the observed "
            "information may be singular: a warning says so, and standard errors "
            "are then null. A VAR whose lag polynomial has a root on or inside the "
            "unit circle is reported with a warning; its responses do not die out."
        ),
        (
            "BLS published no October 2025 CPI or unemployment rate (the federal "
            "shutdown), and a binding never fills a gap: the default profile's "
            "window cannot span that month, so bind it as of 2025-09-30 or "
            "earlier, or rebind to series without the gap."
        ),
        (
            "Cointegration tests have low power in short samples; the critical "
            "values are asymptotic (Johansen) or response surfaces in the sample "
            "size (Engle-Granger), and neither corrects for lag selection."
        ),
        "Needs the econometrics extra: pip install 'pyeconomics[econometrics]'.",
    ),
    references=(
        _BOX_JENKINS,
        _LUTKEPOHL,
        _SIMS,
        _HANNAN_QUINN,
        _ENGLE_GRANGER,
        _MACKINNON_1994,
        _MACKINNON_2010,
        _JOHANSEN,
        _MHM,
        _STATSMODELS,
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.HEAVY,
    tags=(
        "arima",
        "sarima",
        "var",
        "impulse response",
        "cointegration",
        "engle-granger",
        "johansen",
        "forecast",
    ),
    invariants=(
        Invariant(
            id="var_irf_at_horizon_zero_is_the_cholesky_factor",
            statement=(
                "The orthogonalized impulse responses at horizon zero are the lower "
                "Cholesky factor of the residual covariance."
            ),
        ),
        Invariant(
            id="fevd_rows_sum_to_one",
            statement=(
                "At every horizon, each variable's forecast-error variance shares "
                "sum to one across the shocks."
            ),
        ),
        Invariant(
            id="cointegrated_simulation_rejects_no_cointegration",
            statement=(
                "On a long simulated cointegrated system, both tests reject the "
                "null of no cointegration at the 5% level."
            ),
        ),
        Invariant(
            id="forecast_interval_contains_the_forecast",
            statement="Each ARIMA forecast lies inside its interval.",
        ),
    ),
    examples=(
        Example(
            name="arima_ar1",
            inputs={"calculation": "arima", "series": _AR1, "ar": 1, "horizon": 6},
            note="An AR(1) with coefficient 0.6, simulated for 120 periods.",
        ),
        Example(
            name="var_pair",
            inputs={
                "calculation": "var",
                "series": _AR1,
                "second": _LINKED,
                "max_lags": 3,
                "horizon": 8,
            },
        ),
        Example(
            name="engle_granger_pair",
            inputs={"calculation": "engle_granger", "series": _PAIR, "second": _LEVEL},
            note="The series is half the second plus noise: the two are cointegrated.",
        ),
        Example(
            name="johansen_pair",
            inputs={"calculation": "johansen", "series": _LEVEL, "second": _PAIR},
        ),
    ),
    charts=(
        ChartSpec(
            id="arima_forecast",
            title="ARIMA forecast and interval",
            kind=ChartKind.BAND,
            x="horizons",
            y=("forecast_lower", "forecast_upper", "forecasts"),
            x_label="Periods ahead",
            y_label="Forecast",
            calculation="arima",
        ),
    ),
    bindings=(
        Binding("series", "us.inflation.cpi.yoy", as_of=AsOf.WINDOW, window=_WINDOW),
        Binding("second", "us.unemployment.rate", as_of=AsOf.WINDOW, window=_WINDOW),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
    # A literal: the import allowlist reads it with ast to admit statsmodels.
    extra="econometrics",
)
def time_series(inputs: TimeSeriesInputs) -> TimeSeriesOutputs:
    """Run the calculation with statsmodels, imported here (the econometrics extra)."""
    try:
        from statsmodels.regression.linear_model import OLS  # noqa: PLC0415
        from statsmodels.tsa.api import VAR  # noqa: PLC0415
        from statsmodels.tsa.arima.model import ARIMA  # noqa: PLC0415
        from statsmodels.tsa.stattools import adfuller, coint  # noqa: PLC0415
        from statsmodels.tsa.tsatools import add_trend  # noqa: PLC0415
        from statsmodels.tsa.vector_ar.vecm import coint_johansen  # noqa: PLC0415
    except ImportError as error:
        package = "statsmodels"
        raise MissingOptionalDependencyError(package, extra=EXTRA) from error
    sm = _Statsmodels(
        ARIMA=ARIMA,
        VAR=VAR,
        OLS=OLS,
        add_trend=add_trend,
        adfuller=adfuller,
        coint=coint,
        coint_johansen=coint_johansen,
    )
    return _CALCULATIONS[inputs.calculation](inputs, sm)
