# src/pyeconomics/models/macro/output_gap.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The output gap: ``macro.output_gap``.

How far output is from its trend or potential, as five calculations
discriminated on ``calculation``:

- ``from_potential``: actual over potential output less one, or the log
  difference, from a published potential (CBO's, for the United States);
- ``hp``: the Hodrick-Prescott (1997) filter, the trend :math:`\tau` that
  minimizes :math:`\sum (x_t - \tau_t)^2 + \lambda \sum (\Delta^2 \tau_t)^2`, with
  :math:`\lambda` of 1,600 for quarterly data scaled to other frequencies by Ravn
  and Uhlig's (2002) rule, :math:`1600\,(f/4)^4`;
- ``hamilton``: Hamilton's (2018) regression, :math:`x_{t+h}` on a constant and
  :math:`x_t, \ldots, x_{t-p+1}`, whose residual is the cycle (:math:`h = 8`,
  :math:`p = 4` for quarterly data, two years and one year at any frequency);
- ``baxter_king``: Baxter and King's (1999) symmetric band-pass filter, the ideal
  weights for periods of 6 to 32 quarters truncated at :math:`K = 12` leads and
  lags and shifted to sum to zero;
- ``christiano_fitzgerald``: Christiano and Fitzgerald's (2003) asymmetric
  band-pass filter for a random walk, over the same band, with the series' drift
  removed first.

The filters run on the natural logarithm of the series, :math:`x_t = \ln y_t`;
the trend is reported in the series' units, :math:`e^{\tau_t}`, and the gap in
the stated ``form``: ``ratio`` (:math:`y_t / \text{trend}_t - 1`, CBO's definition
and the one ``macro.policy_rule`` reads) or ``log`` (:math:`\ln y_t - \ln
\text{trend}_t`). The Hamilton and Baxter-King cycles start later than the series
(``start`` says where), and Baxter-King's also ends :math:`K` periods early.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
    ARRAY_INPUT,
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Periods,
    Rate,
    Ratio,
    Reference,
    least_squares,
    model,
    warn,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

__all__ = ["output_gap"]

#: The longest series: 500 years of quarters, or 166 of months. The HP solve is
#: banded and the Christiano-Fitzgerald filter quadratic in the length, so a
#: 2,000-observation series filters in milliseconds.
SERIES_MAX: Final = 2_000
#: Output and potential in a currency's units, positive.
_LEVEL_MAX: Final = 1e15
#: A gap stated as a ratio is at least -1; as a log difference it has no floor.
#: Beyond these the series moves by factors no output series does, and the
#: model raises DomainError rather than report a meaningless gap.
_GAP_MIN: Final = -100.0
_GAP_MAX: Final = 1e6
_TREND_MAX: Final = 1e18
_SMOOTHING_MAX: Final = 1e8
_PERIOD_MAX: Final = 1_000.0
#: The regression takes p + 1 coefficients, at most core's 20.
_LAGS_MAX: Final = 19
_HORIZON_MAX: Final = 100

type Frequency = Literal["annual", "quarterly", "monthly"]
type Form = Literal["ratio", "log"]

#: Observations per year, for the defaults each frequency scales.
_PER_YEAR: Final[dict[str, int]] = {"annual": 1, "quarterly": 4, "monthly": 12}
#: Baxter and King's (1999) recommended band and truncation by frequency: 6 to
#: 32 quarters with K = 12; 2 to 8 years with K = 3; 18 to 96 months, K = 36.
_BAND: Final[dict[str, tuple[float, float, int]]] = {
    "annual": (2.0, 8.0, 3),
    "quarterly": (6.0, 32.0, 12),
    "monthly": (18.0, 96.0, 36),
}

_Level = Annotated[Money, Field(gt=0, le=_LEVEL_MAX)]
_Levels = Annotated[tuple[_Level, ...], ARRAY_INPUT]
_Trend = Annotated[Money, Field(gt=0, le=_TREND_MAX)]
_Gap = Annotated[Rate, Field(ge=_GAP_MIN, le=_GAP_MAX)]


def _ravn_uhlig(frequency: Frequency) -> float:
    """Return the HP smoothing parameter for a frequency: 1,600 (f / 4) ** 4."""
    return 1600.0 * (_PER_YEAR[frequency] / 4) ** 4


# --- inputs ------------------------------------------------------------------


class _Common(ModelInputs):
    """What every calculation shares: how the gap is stated."""

    form: Form = Field(
        "ratio",
        description=(
            "How the gap is stated: 'ratio' is output over trend less one; 'log' "
            "the difference of their logarithms"
        ),
    )


class FromPotentialInputs(_Common):
    """A published potential output: the gap is actual against potential."""

    calculation: Literal["from_potential"] = Field(
        "from_potential", description="The gap from a published potential output"
    )
    actual: _Levels = Field(
        min_length=1,
        max_length=SERIES_MAX,
        description="Real output each period, positive",
    )
    potential: _Levels = Field(
        min_length=1,
        max_length=SERIES_MAX,
        description="Potential output each period, in the units of actual",
    )

    @model_validator(mode="after")
    def _paired(self) -> Self:
        if len(self.actual) != len(self.potential):
            msg = (
                f"actual has {len(self.actual)} periods and potential "
                f"{len(self.potential)}; give one value of each per period"
            )
            raise ValueError(msg)
        return self


class _Filter(_Common):
    """A filter: a series of output and its frequency."""

    series: _Levels = Field(
        min_length=3,
        max_length=SERIES_MAX,
        description="Real output each period, positive; the filter runs on its log",
    )
    frequency: Frequency = Field(
        description="How often the series is observed; it sets the filter's defaults"
    )


class HodrickPrescottInputs(_Filter):
    """The Hodrick-Prescott filter."""

    calculation: Literal["hp"] = Field("hp", description="The Hodrick-Prescott filter")
    smoothing: Ratio | None = Field(
        None,
        gt=0,
        le=_SMOOTHING_MAX,
        description=(
            "Lambda, the penalty on the trend's curvature; left out, 1,600 for "
            "quarterly data, 6.25 annual and 129,600 monthly (Ravn and Uhlig)"
        ),
    )


class HamiltonInputs(_Filter):
    """Hamilton's regression filter."""

    calculation: Literal["hamilton"] = Field(
        "hamilton", description="Hamilton's (2018) regression filter"
    )
    horizon: Count | None = Field(
        None,
        ge=1,
        le=_HORIZON_MAX,
        description="h, periods ahead the regression predicts; left out, two years",
    )
    lags: Count | None = Field(
        None,
        ge=1,
        le=_LAGS_MAX,
        description="p, the most recent values it predicts from; left out, one year",
    )

    @model_validator(mode="after")
    def _long_enough(self) -> Self:
        h, p = _hamilton_settings(self)
        if len(self.series) < 2 * p + h + 1:
            msg = (
                f"the Hamilton regression with h = {h} and p = {p} needs at least "
                f"{2 * p + h + 1} observations, not {len(self.series)}"
            )
            raise ValueError(msg)
        return self


def _low(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(None, ge=2.0, le=_PERIOD_MAX, description=description)


class _BandPass(_Filter):
    """A band-pass filter: the shortest and longest cycles it keeps."""

    low: Periods | None = _low(
        "The shortest cycle kept, in periods; left out, 6 quarters (2 years, 18 months)"
    )
    high: Periods | None = _low(
        "The longest cycle kept, in periods; left out, 32 quarters (8 years, 96 months)"
    )

    @model_validator(mode="after")
    def _ordered_band(self) -> Self:
        low, high, _ = _band(self)
        if not low < high:
            msg = f"the band needs low below high, not {low:g} and {high:g}"
            raise ValueError(msg)
        return self


class BaxterKingInputs(_BandPass):
    """The Baxter-King band-pass filter."""

    calculation: Literal["baxter_king"] = Field(
        "baxter_king", description="The Baxter-King (1999) band-pass filter"
    )
    lead_lag: Count | None = Field(
        None,
        ge=1,
        le=SERIES_MAX // 2,
        description=(
            "K, the leads and lags of the moving average; left out, 12 quarters "
            "(3 years, 36 months)"
        ),
    )

    @model_validator(mode="after")
    def _long_enough(self) -> Self:
        k = _band(self)[2]
        if len(self.series) < 2 * k + 1:
            msg = (
                f"the Baxter-King filter with K = {k} needs at least {2 * k + 1} "
                f"observations, not {len(self.series)}"
            )
            raise ValueError(msg)
        return self


class ChristianoFitzgeraldInputs(_BandPass):
    """The Christiano-Fitzgerald band-pass filter."""

    calculation: Literal["christiano_fitzgerald"] = Field(
        "christiano_fitzgerald",
        description="The Christiano-Fitzgerald (2003) band-pass filter",
    )
    drift: bool = Field(
        default=True,
        description=(
            "Remove the line from the first to the last observation before "
            "filtering (the random walk with drift)"
        ),
    )


OutputGapInputs = Annotated[
    FromPotentialInputs
    | HodrickPrescottInputs
    | HamiltonInputs
    | BaxterKingInputs
    | ChristianoFitzgeraldInputs,
    Field(discriminator="calculation"),
]


def _hamilton_settings(inputs: HamiltonInputs) -> tuple[int, int]:
    per_year = _PER_YEAR[inputs.frequency]
    horizon = 2 * per_year if inputs.horizon is None else inputs.horizon
    lags = per_year if inputs.lags is None else inputs.lags
    return horizon, lags


def _band(inputs: _BandPass) -> tuple[float, float, int]:
    low, high, k = _BAND[inputs.frequency]
    low = low if inputs.low is None else inputs.low
    high = high if inputs.high is None else inputs.high
    lead_lag = getattr(inputs, "lead_lag", None)
    return low, high, k if lead_lag is None else lead_lag


# --- outputs -----------------------------------------------------------------


class _GapOutputs(ModelOutputs):
    trend: Annotated[tuple[_Trend, ...], ARRAY_INPUT] = Field(
        max_length=SERIES_MAX,
        description=(
            "The trend (potential output) in each period the cycle covers, in the "
            "series' units"
        ),
    )
    cycle: Annotated[tuple[_Gap, ...], ARRAY_INPUT] = Field(
        max_length=SERIES_MAX, description="The gap in each period, in the stated form"
    )
    gap: _Gap = Field(description="The gap in the last period the cycle covers")
    start: Count = Field(
        ge=0,
        le=SERIES_MAX,
        description=(
            "The position in the series (from 0) of the first period the trend "
            "and cycle cover"
        ),
    )


class FromPotentialOutputs(_GapOutputs):
    calculation: Literal["from_potential"] = Field(
        "from_potential", description="The gap from a published potential output"
    )


class HodrickPrescottOutputs(_GapOutputs):
    calculation: Literal["hp"] = Field("hp", description="The Hodrick-Prescott filter")
    smoothing: Ratio = Field(
        gt=0, le=_SMOOTHING_MAX, description="The lambda the filter used"
    )


class HamiltonOutputs(_GapOutputs):
    calculation: Literal["hamilton"] = Field(
        "hamilton", description="Hamilton's (2018) regression filter"
    )
    horizon: Count = Field(ge=1, le=_HORIZON_MAX, description="The h it used")
    lags: Count = Field(ge=1, le=_LAGS_MAX, description="The p it used")


class BaxterKingOutputs(_GapOutputs):
    calculation: Literal["baxter_king"] = Field(
        "baxter_king", description="The Baxter-King (1999) band-pass filter"
    )
    low: Periods = Field(ge=2.0, le=_PERIOD_MAX, description="The band's low end")
    high: Periods = Field(ge=2.0, le=_PERIOD_MAX, description="The band's high end")
    lead_lag: Count = Field(ge=1, le=SERIES_MAX // 2, description="The K it used")


class ChristianoFitzgeraldOutputs(_GapOutputs):
    calculation: Literal["christiano_fitzgerald"] = Field(
        "christiano_fitzgerald",
        description="The Christiano-Fitzgerald (2003) band-pass filter",
    )
    low: Periods = Field(ge=2.0, le=_PERIOD_MAX, description="The band's low end")
    high: Periods = Field(ge=2.0, le=_PERIOD_MAX, description="The band's high end")


OutputGapOutputs = Annotated[
    FromPotentialOutputs
    | HodrickPrescottOutputs
    | HamiltonOutputs
    | BaxterKingOutputs
    | ChristianoFitzgeraldOutputs,
    Field(discriminator="calculation"),
]


# --- the arithmetic ------------------------------------------------------------

type _Vector = NDArray[np.float64]


def _gaps(
    log_series: _Vector, log_cycle: _Vector, start: int, form: Form
) -> dict[str, Any]:
    """State the trend and the gap from the log series and its log cycle.

    ``log_cycle`` covers ``log_series[start:start + len(log_cycle)]``.
    """
    covered = log_series[start : start + len(log_cycle)]
    with np.errstate(over="ignore"):
        trend = np.exp(covered - log_cycle)
        cycle = np.expm1(log_cycle) if form == "ratio" else log_cycle
    if not (
        np.all(np.isfinite(trend))
        and np.all(trend > 0)
        and np.all(trend <= _TREND_MAX)
        and np.all(np.isfinite(cycle))
        and np.all(cycle >= _GAP_MIN)
        and np.all(cycle <= _GAP_MAX)
    ):
        msg = (
            "the series moves by factors no output series does: the trend or the "
            f"gap leaves its bounds (a trend up to {_TREND_MAX:g}, a gap from "
            f"{_GAP_MIN:g} to {_GAP_MAX:g})"
        )
        raise DomainError(msg)
    values = tuple(float(v) + 0.0 for v in cycle)
    return {
        "trend": tuple(float(v) for v in trend),
        "cycle": values,
        "gap": values[-1],
        "start": start,
    }


def _logs(levels: tuple[float, ...]) -> _Vector:
    return np.log(np.asarray(levels, dtype=np.float64))


def _from_potential(inputs: FromPotentialInputs) -> FromPotentialOutputs:
    actual, potential = _logs(inputs.actual), _logs(inputs.potential)
    stated = _gaps(actual, actual - potential, 0, inputs.form)
    # The trend is the potential given, exactly, not a round trip through logs.
    stated["trend"] = tuple(inputs.potential)
    if inputs.form == "ratio":
        values = tuple(
            a / p - 1.0 for a, p in zip(inputs.actual, inputs.potential, strict=True)
        )
        # The quotient can round past the bound its log form just met.
        if not all(_GAP_MIN <= v <= _GAP_MAX for v in values):
            msg = f"a gap of actual over potential passes {_GAP_MAX:g}"
            raise DomainError(msg)
        stated |= {"cycle": values, "gap": values[-1]}
    return FromPotentialOutputs.model_validate(stated)


def _penalty_bands(n: int, smoothing: float) -> _Vector:
    """Return I + lambda D'D in symmetric banded upper form (three rows)."""
    second = (1.0, -2.0, 1.0)
    bands = np.zeros((3, n))
    for a in range(3):
        for b in range(a, 3):
            # Row k of D has the second difference at columns k, k+1, k+2:
            # entry (k + a, k + b) of D'D gains second[a] * second[b].
            offset = b - a
            weight = second[a] * second[b]
            bands[2 - offset, offset + a : n - 2 + a + offset] += weight
    bands *= smoothing
    bands[2] += 1.0
    return bands


def _hp_trend(log_series: _Vector, smoothing: float) -> _Vector:
    """Return the Hodrick-Prescott trend: solve (I + lambda D'D) tau = x."""
    from scipy.linalg import solveh_banded  # noqa: PLC0415 - SciPy on first use

    bands = _penalty_bands(len(log_series), smoothing)
    return np.asarray(solveh_banded(bands, log_series), dtype=np.float64)


def _hodrick_prescott(inputs: HodrickPrescottInputs) -> HodrickPrescottOutputs:
    smoothing = (
        _ravn_uhlig(inputs.frequency) if inputs.smoothing is None else inputs.smoothing
    )
    x = _logs(inputs.series)
    cycle = x - _hp_trend(x, smoothing)
    stated = _gaps(x, cycle, 0, inputs.form)
    return HodrickPrescottOutputs.model_validate(stated | {"smoothing": smoothing})


def _hamilton(inputs: HamiltonInputs) -> HamiltonOutputs:
    h, p = _hamilton_settings(inputs)
    x = _logs(inputs.series)
    n = len(x)
    rows = n - p - h + 1
    # Row r predicts x[p + h - 1 + r] from x[p - 1 + r], ..., x[r].
    design = np.column_stack([x[p - j : p - j + rows] for j in range(1, p + 1)])
    target = x[p + h - 1 :]
    fit = least_squares(target, design)
    residuals = np.asarray(fit.residuals, dtype=np.float64)
    stated = _gaps(x, residuals, p + h - 1, inputs.form)
    return HamiltonOutputs.model_validate(stated | {"horizon": h, "lags": p})


def _band_pass_weights(low: float, high: float, lead_lag: int) -> _Vector:
    """Return Baxter and King's 2K + 1 weights for periods ``low`` to ``high``.

    The ideal band-pass weights, truncated at ``lead_lag`` and shifted by their
    mean so they sum to zero.
    """
    shortest, longest = 2 * math.pi / high, 2 * math.pi / low
    j = np.arange(1, lead_lag + 1, dtype=np.float64)
    side = (np.sin(longest * j) - np.sin(shortest * j)) / (math.pi * j)
    weights = np.concatenate([side[::-1], [(longest - shortest) / math.pi], side])
    return weights - weights.mean()


def _baxter_king(inputs: BaxterKingInputs) -> BaxterKingOutputs:
    low, high, k = _band(inputs)
    x = _logs(inputs.series)
    cycle = np.convolve(x, _band_pass_weights(low, high, k), mode="valid")
    stated = _gaps(x, cycle, k, inputs.form)
    warn(
        "end_points_lost",
        f"the Baxter-King filter has no cycle for the first and last {k} periods; "
        "the gap is the one K periods before the series ends",
    )
    return BaxterKingOutputs.model_validate(
        stated | {"low": low, "high": high, "lead_lag": k}
    )


def _cf_cycle(x: _Vector, low: float, high: float, *, drift: bool) -> _Vector:
    """Return the Christiano-Fitzgerald random-walk band-pass cycle of ``x``.

    Each period's weights are the ideal ones, with the weights on the first
    and last observations set so the period's weights sum to zero.
    """
    n = len(x)
    if drift:
        x = x - np.arange(n) * (x[-1] - x[0]) / (n - 1)
    shortest, longest = 2 * math.pi / high, 2 * math.pi / low
    j = np.arange(1, n + 1, dtype=np.float64)
    ideal = np.concatenate(
        [[(longest - shortest) / math.pi], (np.sin(longest * j) - np.sin(shortest * j))]
    )
    ideal[1:] /= math.pi * j
    cumulative = np.concatenate([[0.0], np.cumsum(ideal[1:])])
    cycle = np.empty(n)
    for t in range(n):
        ahead = max(n - t - 2, 0)  # weights on x[t + 1] .. x[n - 2]
        behind = max(t - 1, 0)  # weights on x[t - 1] .. x[1]
        last = -0.5 * ideal[0] - cumulative[ahead]
        first = -ideal[0] - cumulative[ahead] - cumulative[behind] - last
        value = ideal[0] * x[t] + last * x[-1] + first * x[0]
        if ahead:
            value += float(ideal[1 : ahead + 1] @ x[t + 1 : t + 1 + ahead])
        if behind:
            value += float(ideal[1 : behind + 1] @ x[t - 1 : 0 : -1])
        cycle[t] = value
    return cycle


def _christiano_fitzgerald(
    inputs: ChristianoFitzgeraldInputs,
) -> ChristianoFitzgeraldOutputs:
    low, high, _ = _band(inputs)
    x = _logs(inputs.series)
    cycle = _cf_cycle(x, low, high, drift=inputs.drift)
    stated = _gaps(x, cycle, 0, inputs.form)
    return ChristianoFitzgeraldOutputs.model_validate(
        stated | {"low": low, "high": high}
    )


# --- the model -----------------------------------------------------------------

_HP = Reference(
    key="hodrick1997",
    citation=(
        "Hodrick, R. J. and Prescott, E. C. (1997). Postwar U.S. Business Cycles: "
        "An Empirical Investigation. Journal of Money, Credit and Banking, 29(1), "
        "1-16."
    ),
    doi="10.2307/2953682",
    locator="Section 2: the trend that minimizes the penalized sum of squares",
)
_RAVN_UHLIG = Reference(
    key="ravn2002",
    citation=(
        "Ravn, M. O. and Uhlig, H. (2002). On Adjusting the Hodrick-Prescott "
        "Filter for the Frequency of Observations. Review of Economics and "
        "Statistics, 84(2), 371-376."
    ),
    doi="10.1162/003465302317411604",
    locator="Lambda scales with the fourth power of the observation frequency",
)
_HAMILTON = Reference(
    key="hamilton",
    citation=(
        "Hamilton, J. D. (2018). Why You Should Never Use the Hodrick-Prescott "
        "Filter. Review of Economics and Statistics, 100(5), 831-843."
    ),
    doi="10.1162/rest_a_00706",
    locator="Section 4: the regression of y(t+h) on y(t), ..., y(t-p+1)",
)
_BAXTER_KING = Reference(
    key="baxter1999",
    citation=(
        "Baxter, M. and King, R. G. (1999). Measuring Business Cycles: "
        "Approximate Band-Pass Filters for Economic Time Series. Review of "
        "Economics and Statistics, 81(4), 575-593."
    ),
    doi="10.1162/003465399558454",
    locator="The truncated ideal filter with weights summing to zero; K = 12",
)
_CHRISTIANO_FITZGERALD = Reference(
    key="christiano",
    citation=(
        "Christiano, L. J. and Fitzgerald, T. J. (2003). The Band Pass Filter. "
        "International Economic Review, 44(2), 435-465."
    ),
    doi="10.1111/1468-2354.t01-1-00076",
    locator="The random-walk filter with end weights that sum the rest to zero",
)
_CBO = Reference(
    key="cbo_potential",
    citation=(
        "Congressional Budget Office. Budget and Economic Data: Potential GDP and "
        "Underlying Inputs."
    ),
    url="https://www.cbo.gov/data/budget-economic-data",
    locator="Quarterly real GDP, real potential GDP and the output gap",
)
_STATSMODELS = Reference(
    key="seabold2010",
    citation=(
        "Seabold, S. and Perktold, J. (2010). statsmodels: Econometric and "
        "statistical modeling with Python. Proceedings of the 9th Python in "
        "Science Conference, 92-96."
    ),
    doi="10.25080/Majora-92bf1922-011",
    locator="statsmodels.tsa.filters: hpfilter, bkfilter and cffilter (oracles)",
)

_PWT: Final = ("ca", "de", "fr", "gb", "it", "jp")

_BINDINGS: Final = (
    Binding("actual", "us.output.real_gdp", as_of=AsOf.WINDOW, window=120),
    Binding("potential", "us.output.potential_gdp", as_of=AsOf.WINDOW, window=120),
    Binding("series", "us.output.real_gdp", as_of=AsOf.WINDOW, window=120),
    *(
        Binding(
            "series",
            f"pwt.rgdpna.{economy}.annual",
            as_of=AsOf.WINDOW,
            window=40,
            profile=economy,
        )
        for economy in _PWT
    ),
)

#: Real GDP, an invented but plausible path of 24 quarters (billions of chained
#: dollars) with a recession in the middle.
_GDP: Final = (
    19_000.0,
    19_150.0,
    19_310.0,
    19_440.0,
    19_590.0,
    19_700.0,
    19_760.0,
    19_650.0,
    19_420.0,
    19_350.0,
    19_480.0,
    19_660.0,
    19_850.0,
    20_030.0,
    20_190.0,
    20_340.0,
    20_480.0,
    20_610.0,
    20_760.0,
    20_900.0,
    21_050.0,
    21_180.0,
    21_330.0,
    21_470.0,
)


@model(
    id="macro.output_gap",
    version=1,
    title="Output gap",
    summary=(
        "The output gap from a published potential output, or by the "
        "Hodrick-Prescott, Hamilton, Baxter-King and Christiano-Fitzgerald "
        "filters, with the trend, the cycle and the latest gap."
    ),
    formula=(
        (
            r"\text{gap}_t = \frac{y_t}{\bar y_t} - 1 \ \text{(ratio)} "
            r"\quad\text{or}\quad \ln y_t - \ln \bar y_t \ \text{(log)}"
        ),
        (
            r"\tau^{HP} = \arg\min_\tau \sum_t (x_t - \tau_t)^2 + \lambda \sum_t "
            r"(\tau_{t+1} - 2\tau_t + \tau_{t-1})^2, \quad \lambda = 1600 (f/4)^4"
        ),
        (
            r"x_{t+h} = \beta_0 + \beta_1 x_t + \cdots + \beta_p x_{t-p+1} + "
            r"v_{t+h}, \quad \text{cycle}_{t+h} = \hat v_{t+h}"
        ),
        (
            r"c^{BK}_t = \sum_{j=-K}^{K} a_j x_{t-j}, \quad a_j = b_j - "
            r"\frac{1}{2K+1}\sum_{i=-K}^{K} b_i, \quad b_j = \frac{\sin(j\omega_2) - "
            r"\sin(j\omega_1)}{\pi j}"
        ),
    ),
    assumptions=(
        (
            "The filters run on the natural log of output; the trend is reported "
            "in the series' units and the gap as a ratio (CBO's definition, the "
            "default) or a log difference."
        ),
        (
            "Defaults follow the papers and scale with the frequency: lambda 1,600 "
            "quarterly (Ravn and Uhlig: 6.25 annual, 129,600 monthly); Hamilton's "
            "h of two years and p of one; a band of 1.5 to 8 years with K of three "
            "years (two to eight years for annual data). Each can be overridden."
        ),
        (
            "The Christiano-Fitzgerald filter is the asymmetric random-walk form, "
            "on the series less the line from its first to its last value (as "
            "statsmodels' cffilter computes it)."
        ),
        (
            "Profiles: default binds 120 quarters of US real GDP and CBO's real "
            "potential GDP; ca, de, fr, gb, it and jp bind 40 years of the Penn "
            "World Table's real GDP (rgdpna) for a filter, with frequency='annual'."
        ),
    ),
    limitations=(
        (
            "Potential output is not observed: the filters' trends are statistical "
            "and revised as data arrive, and the HP and Christiano-Fitzgerald "
            "trends are least reliable at the ends of the sample (Hamilton 2018)."
        ),
        (
            "Hamilton's cycle starts h + p - 1 periods into the series, and "
            "Baxter-King's starts K periods in and ends K periods early: its gap is "
            "the one K periods before the last observation, and it warns."
        ),
        (
            "A series whose recent values are collinear (an exactly log-linear "
            "one) has no Hamilton regression, and a series that moves by factors "
            "no output series does leaves the trend or gap bounds: both raise "
            "DomainError."
        ),
        (
            "Chain into macro.policy_rule by passing the gap as its output_gap "
            "override; the manifest records it as user-supplied, apart from a "
            "published gap."
        ),
        (
            "In hosted mode, where FRED is refused, the originators serve too "
            "short a history for the default windows (BLS about three years, "
            "CBO's potential and natural rate from 2021), so the bind raises: "
            "supply the series instead."
        ),
    ),
    references=(
        _HP,
        _RAVN_UHLIG,
        _HAMILTON,
        _BAXTER_KING,
        _CHRISTIANO_FITZGERALD,
        _CBO,
        _STATSMODELS,
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    tags=(
        "output gap",
        "potential output",
        "hodrick-prescott",
        "hamilton filter",
        "band-pass filter",
    ),
    invariants=(
        Invariant(
            id="trend_plus_cycle_equals_series",
            statement=(
                "The log trend plus the log gap is the log of the series, so the "
                "trend times one plus the ratio gap is the series."
            ),
        ),
        Invariant(
            id="hp_cycle_zero_for_linear_series",
            statement=(
                "The HP filter leaves no cycle in a series that grows at a constant "
                "rate (linear in logs)."
            ),
        ),
        Invariant(
            id="band_pass_removes_linear_trend",
            statement=(
                "The Baxter-King filter, and the Christiano-Fitzgerald filter with "
                "its drift removed, leave no cycle in a series linear in logs."
            ),
        ),
        Invariant(
            id="gap_zero_when_actual_equals_potential",
            statement="When actual output equals potential, every gap is zero.",
        ),
        Invariant(
            id="hamilton_cycle_has_zero_mean",
            statement=(
                "Hamilton's cycle is a regression residual with a constant, so its "
                "log values sum to zero."
            ),
        ),
    ),
    examples=(
        Example(
            name="hp_quarterly",
            inputs={
                "calculation": "hp",
                "series": list(_GDP),
                "frequency": "quarterly",
            },
            note=(
                "Chain the gap into a policy rule: `gap = pyeconomics.run("
                'pyeconomics.bind("macro.output_gap", calculation="hp", '
                'frequency="quarterly")).outputs.gap`, then `pyeconomics.run('
                'pyeconomics.bind("macro.policy_rule", profile="us_output_gap", '
                'calculation="taylor_1993", output_gap=gap))`. The manifest '
                "records output_gap as user-supplied beside the rule's bound data."
            ),
        ),
        Example(
            name="from_potential",
            inputs={
                "calculation": "from_potential",
                "actual": [23_400.0, 23_520.0],
                "potential": [23_300.0, 23_470.0],
            },
        ),
        Example(
            name="hamilton_quarterly",
            inputs={
                "calculation": "hamilton",
                "series": list(_GDP),
                "frequency": "quarterly",
            },
        ),
        Example(
            name="baxter_king_quarterly",
            inputs={
                "calculation": "baxter_king",
                "series": list(_GDP),
                "frequency": "quarterly",
                "lead_lag": 6,
            },
        ),
        Example(
            name="christiano_fitzgerald_log_gap",
            inputs={
                "calculation": "christiano_fitzgerald",
                "series": list(_GDP),
                "frequency": "quarterly",
                "form": "log",
            },
        ),
    ),
    bindings=_BINDINGS,
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def output_gap(inputs: OutputGapInputs) -> OutputGapOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], OutputGapOutputs]]] = {
    FromPotentialInputs: _from_potential,
    HodrickPrescottInputs: _hodrick_prescott,
    HamiltonInputs: _hamilton,
    BaxterKingInputs: _baxter_king,
    ChristianoFitzgeraldInputs: _christiano_fitzgerald,
}
