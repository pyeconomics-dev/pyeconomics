# tests/models/econometrics/test_time_series.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``econometrics.time_series``: invariants, NumPy oracles and a published table.

The oracles are independent of statsmodels: the VAR is least squares equation
by equation with ``numpy.linalg.lstsq``, its impulse responses come from powers
of the companion matrix, the Johansen eigenvalues from SciPy's symmetric-definite
eigenproblem, the Engle-Granger statistic from a NumPy ADF regression, and the
AR(1) likelihood from its exact closed form.

The published table is Lütkepohl's (2005) VAR(2) for West German investment,
income and consumption, recomputed on the ``lutkepohl2`` data statsmodels ships
and compared with the coefficients, standard errors and criteria StataCorp
prints to seven decimals in its reproduction ([TS] var, Example 1). The data are
read from the installed statsmodels at test time and never committed.
"""

from __future__ import annotations

import contextlib
import math
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import pytest
import scipy.linalg
import scipy.stats
import statsmodels
import strategies
from hypothesis import given, reject, settings
from hypothesis import strategies as st

from pyeconomics.core import (
    DomainError,
    InputError,
    MissingOptionalDependencyError,
    ModelWarning,
    run_model,
)
from pyeconomics.core import registry as core_registry
from pyeconomics.models.econometrics import time_series

if TYPE_CHECKING:
    from numpy.typing import NDArray

FIELDS = ("series", "second", "third", "fourth")


def result(**inputs: Any) -> Any:  # noqa: ANN401 - a Result
    return run_model(time_series, inputs)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the outputs
    return result(**inputs).outputs


def stray_warnings(inputs: dict[str, Any]) -> list[str]:
    """Run the model; return every warning that is not a model warning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with contextlib.suppress(DomainError):
            run(**inputs)
    return [
        f"{type(w.message).__name__}: {w.message}"
        for w in caught
        if not isinstance(w.message, ModelWarning)
    ]


def simulate_var(
    count: int, seed: int, coefficients: NDArray[np.float64], scale: float = 1.0
) -> NDArray[np.float64]:
    """Simulate a stable VAR(1) with correlated shocks."""
    rng = np.random.default_rng(seed)
    k = coefficients.shape[0]
    mix = np.tril(rng.uniform(0.2, 1.0, (k, k)))
    shocks = rng.standard_normal((count + 100, k)) @ mix.T
    path = np.zeros((count + 100, k))
    for t in range(1, count + 100):
        path[t] = coefficients @ path[t - 1] + shocks[t]
    return np.asarray(path[100:] * scale, dtype=np.float64)


def variables(data: NDArray[np.float64]) -> dict[str, list[float]]:
    return {
        name: [float(v) for v in data[:, index].tolist()]
        for index, name in enumerate(FIELDS[: data.shape[1]])
    }


def cointegrated(count: int, seed: int, k: int = 2) -> NDArray[np.float64]:
    """K - 1 random walks and one series cointegrated with them."""
    rng = np.random.default_rng(seed)
    walks = np.cumsum(rng.standard_normal((count, k - 1)), axis=0)
    weights = rng.uniform(0.5, 1.5, k - 1)
    noise = np.zeros(count)
    shocks = rng.standard_normal(count)
    for t in range(1, count):
        noise[t] = 0.3 * noise[t - 1] + shocks[t]
    return np.column_stack([walks @ weights + noise, walks])


@st.composite
def stable_vars(draw: st.DrawFn) -> dict[str, Any]:
    """Draw a stable VAR(1), simulate it, and the options of its fit."""
    k = draw(st.integers(2, 4))
    raw = np.asarray(
        draw(st.lists(st.floats(-0.5, 0.5), min_size=k * k, max_size=k * k))
    )
    coefficients = raw.reshape(k, k)
    radius = max(abs(np.linalg.eigvals(coefficients)))
    if radius >= 0.9:
        coefficients = coefficients * 0.85 / radius
    data = simulate_var(
        draw(st.integers(60, 200)),
        draw(st.integers(0, 2**32 - 1)),
        coefficients,
        draw(st.sampled_from([1e-3, 1.0, 100.0])),
    )
    return {
        "calculation": "var",
        **variables(data),
        "lags": draw(st.one_of(st.none(), st.integers(1, 3))),
        "max_lags": draw(st.integers(1, 4)),
        "criterion": draw(st.sampled_from(["aic", "bic", "hqic"])),
        "trend": draw(st.sampled_from(["n", "c", "ct"])),
        "horizon": draw(st.integers(1, 15)),
    }


# --- the oracles, written out -----------------------------------------------------


def var_by_least_squares(
    inputs: dict[str, Any], lags: int
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Each equation by lstsq: coefficients (K x m), standard errors, Sigma_u."""
    data = np.column_stack([inputs[f] for f in FIELDS if f in inputs])
    n = len(data)
    rows = n - lags
    deterministic = {
        "n": [],
        "c": [np.ones(rows)],
        "ct": [np.ones(rows), np.arange(lags + 1, n + 1.0)],
    }
    lagged = [data[lags - lag : n - lag] for lag in range(1, lags + 1)]
    design = np.column_stack([*deterministic[inputs["trend"]], *lagged])
    target = data[lags:]
    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
    residuals = target - design @ coefficients
    sigma = residuals.T @ residuals / (rows - design.shape[1])
    bread = np.linalg.inv(design.T @ design)
    errors = np.sqrt(np.outer(np.diag(bread), np.diag(sigma)))
    return coefficients.T, errors.T, sigma


def companion_responses(
    coefficients: NDArray[np.float64],
    sigma: NDArray[np.float64],
    lags: int,
    k: int,
    horizon: int,
) -> NDArray[np.float64]:
    """Orthogonalized responses Phi_h P from powers of the companion matrix."""
    slopes = coefficients[:, -k * lags :]
    companion = np.zeros((k * lags, k * lags))
    companion[:k] = slopes
    companion[k:, :-k] = np.eye(k * (lags - 1))
    factor = np.linalg.cholesky(sigma)
    power = np.eye(k * lags)
    out = []
    for _ in range(horizon + 1):
        out.append(power[:k, :k] @ factor)
        power = companion @ power
    return np.asarray(out)


def johansen_eigenvalues(
    data: NDArray[np.float64], order: int, lagged: int
) -> NDArray[np.float64]:
    """The reduced-rank regression's eigenvalues: S10 S00^-1 S01 v = l S11 v.

    The deterministic terms follow statsmodels' convention: the levels are
    detrended by a polynomial of the order (none for -1), then the differences
    and the lagged levels are demeaned (when order > -1).
    """

    def detrend(y: NDArray[np.float64], degree: int) -> NDArray[np.float64]:
        if degree < 0:
            return y
        basis = np.vander(np.linspace(-1, 1, len(y)), degree + 1)
        beta, *_ = np.linalg.lstsq(basis, y, rcond=None)
        return np.asarray(y - basis @ beta, dtype=np.float64)

    y = detrend(data, order)
    inner = 0 if order > -1 else -1
    dy = np.diff(y, axis=0)
    t = len(dy) - lagged
    z = (
        np.column_stack([dy[lagged - j : len(dy) - j] for j in range(1, lagged + 1)])
        if lagged
        else np.empty((t, 0))
    )
    d0 = detrend(dy[lagged:], inner)
    z = detrend(z, inner) if lagged else z
    level = detrend(y[lagged : lagged + t], inner)

    def residual(target: NDArray[np.float64]) -> NDArray[np.float64]:
        if z.shape[1] == 0:
            return target
        beta, *_ = np.linalg.lstsq(z, target, rcond=None)
        return np.asarray(target - z @ beta, dtype=np.float64)

    r0, r1 = residual(d0), residual(level)
    s00, s01, s11 = r0.T @ r0 / t, r0.T @ r1 / t, r1.T @ r1 / t
    values = scipy.linalg.eigh(
        s01.T @ np.linalg.solve(s00, s01), s11, eigvals_only=True
    )
    return np.asarray(np.sort(values)[::-1], dtype=np.float64)


# --- invariants -------------------------------------------------------------------


@pytest.mark.invariant(
    "econometrics.time_series", "var_irf_at_horizon_zero_is_the_cholesky_factor"
)
@settings(max_examples=40, deadline=None)
@given(inputs=stable_vars())
def test_the_responses_at_horizon_zero_are_the_cholesky_factor(
    inputs: dict[str, Any],
) -> None:
    out = run(**inputs)
    factor = np.linalg.cholesky(np.asarray(out.residual_covariance))
    assert np.allclose(
        out.impulse_responses[0], factor, rtol=1e-9, atol=1e-12 * np.max(np.abs(factor))
    )


@pytest.mark.invariant("econometrics.time_series", "fevd_rows_sum_to_one")
@settings(max_examples=40, deadline=None)
@given(inputs=stable_vars())
def test_every_variance_decomposition_row_sums_to_one(inputs: dict[str, Any]) -> None:
    out = run(**inputs)
    shares = np.asarray(out.variance_decomposition)
    assert shares.shape == (inputs["horizon"], len(out.variables), len(out.variables))
    assert np.allclose(shares.sum(axis=2), 1.0, rtol=0, atol=1e-12)
    assert np.all(shares >= 0)


@pytest.mark.invariant(
    "econometrics.time_series", "cointegrated_simulation_rejects_no_cointegration"
)
@settings(max_examples=15, deadline=None)
@given(seed=st.integers(0, 2**32 - 1), k=st.integers(2, 3))
def test_a_cointegrated_simulation_rejects_no_cointegration(seed: int, k: int) -> None:
    data = cointegrated(400, seed, k)
    fields = variables(data)
    engle = run(calculation="engle_granger", **fields)
    assert engle.p_value < 0.05
    johansen = run(calculation="johansen", **fields)
    assert johansen.rank_trace >= 1
    assert johansen.rank_max_eigenvalue >= 1
    assert johansen.trace_statistics[0] > johansen.trace_critical_values[0][1]


@pytest.mark.invariant(
    "econometrics.time_series", "forecast_interval_contains_the_forecast"
)
@settings(max_examples=20, deadline=None)
@given(
    seed=st.integers(0, 2**32 - 1),
    ar=st.integers(0, 2),
    ma=st.integers(0, 2),
    differences=st.integers(0, 1),
    alpha=st.floats(0.01, 0.3),
)
def test_each_forecast_lies_inside_its_interval(
    seed: int, ar: int, ma: int, differences: int, alpha: float
) -> None:
    rng = np.random.default_rng(seed)
    series = (
        np.cumsum(rng.standard_normal(80)) if differences else rng.standard_normal(80)
    )
    out = run(
        calculation="arima",
        series=list(series),
        ar=ar,
        ma=ma,
        differences=differences,
        alpha=alpha,
        horizon=8,
    )
    for low, mid, high in zip(
        out.forecast_lower, out.forecasts, out.forecast_upper, strict=True
    ):
        assert low <= mid <= high
    z = scipy.stats.norm.ppf(1 - alpha / 2)
    widths = np.asarray(out.forecast_upper) - np.asarray(out.forecast_lower)
    assert np.allclose(
        widths, 2 * z * np.asarray(out.forecast_standard_errors), rtol=1e-9
    )


# --- oracles ----------------------------------------------------------------------


@pytest.mark.oracle("econometrics.time_series")
@settings(max_examples=40, deadline=None)
@given(inputs=stable_vars())
def test_the_var_matches_equation_by_equation_least_squares(
    inputs: dict[str, Any],
) -> None:
    out = run(**inputs)
    coefficients, errors, sigma = var_by_least_squares(inputs, out.lags)
    assert np.allclose(
        out.coefficients,
        coefficients,
        rtol=1e-7,
        atol=1e-9 * np.max(np.abs(coefficients)),
    )
    assert np.allclose(out.standard_errors, errors, rtol=1e-6, atol=0)
    assert np.allclose(out.residual_covariance, sigma, rtol=1e-7, atol=0)


@pytest.mark.oracle("econometrics.time_series")
@settings(max_examples=40, deadline=None)
@given(inputs=stable_vars())
def test_the_responses_match_the_companion_matrix(inputs: dict[str, Any]) -> None:
    out = run(**inputs)
    k = len(out.variables)
    coefficients, _, sigma = var_by_least_squares(inputs, out.lags)
    responses = companion_responses(coefficients, sigma, out.lags, k, inputs["horizon"])
    scale = np.max(np.abs(responses))
    assert np.allclose(out.impulse_responses, responses, rtol=1e-6, atol=1e-9 * scale)
    # The decomposition: cumulative squared responses over the forecast-error variance.
    squares = np.cumsum(responses**2, axis=0)[: inputs["horizon"]]
    shares = squares / squares.sum(axis=2, keepdims=True)
    assert np.allclose(out.variance_decomposition, shares, rtol=1e-6, atol=1e-9)


@pytest.mark.oracle("econometrics.time_series")
@settings(max_examples=40, deadline=None)
@given(
    seed=st.integers(0, 2**32 - 1),
    k=st.integers(2, 4),
    deterministic=st.sampled_from(["none", "constant", "trend"]),
    lagged=st.integers(1, 3),
    count=st.integers(60, 250),
)
def test_the_johansen_statistics_match_the_eigenvalue_problem(
    seed: int, k: int, deterministic: str, lagged: int, count: int
) -> None:
    data = cointegrated(count, seed, k)
    out = run(
        calculation="johansen",
        **variables(data),
        deterministic=deterministic,
        lagged_differences=lagged,
    )
    order = {"none": -1, "constant": 0, "trend": 1}[deterministic]
    eigenvalues = johansen_eigenvalues(data, order, lagged)
    assert np.allclose(out.eigenvalues, eigenvalues, rtol=1e-7, atol=1e-10)
    t = out.observations
    logs = np.log(1 - eigenvalues)
    trace = [-t * float(np.sum(logs[r:])) for r in range(k)]
    assert np.allclose(out.trace_statistics, trace, rtol=1e-7, atol=1e-8)
    assert np.allclose(out.max_eigenvalue_statistics, -t * logs, rtol=1e-7, atol=1e-8)


@pytest.mark.oracle("econometrics.time_series")
@settings(max_examples=40, deadline=None)
@given(
    seed=st.integers(0, 2**32 - 1),
    trend=st.sampled_from(["c", "ct", "ctt"]),
    k=st.integers(2, 3),
    lags=st.one_of(st.none(), st.integers(0, 4)),
)
def test_the_engle_granger_regressions_match_numpy(
    seed: int, trend: str, k: int, lags: int | None
) -> None:
    data = cointegrated(150, seed, k)
    out = run(
        calculation="engle_granger",
        **variables(data),
        trend=trend,
        max_lags=lags if lags is not None else 4,
        lag_criterion=None if lags is not None else "aic",
    )
    n = len(data)
    time = np.arange(1.0, n + 1)
    terms = {
        "c": [np.ones(n)],
        "ct": [np.ones(n), time],
        "ctt": [np.ones(n), time, time**2],
    }[trend]
    design = np.column_stack([*terms, data[:, 1:]])
    beta, *_ = np.linalg.lstsq(design, data[:, 0], rcond=None)
    assert np.allclose(out.coefficients, beta, rtol=1e-7, atol=1e-9)
    residuals = data[:, 0] - design @ beta
    used = out.lags
    if lags is not None:
        assert used == lags
    change = np.diff(residuals)
    rows = len(change) - used
    regressors = np.column_stack(
        [
            residuals[used:-1],
            *(change[used - j : len(change) - j] for j in range(1, used + 1)),
        ]
    )
    target = change[used:]
    gamma, *_ = np.linalg.lstsq(regressors, target, rcond=None)
    e = target - regressors @ gamma
    variance = e @ e / (rows - regressors.shape[1])
    se = math.sqrt(variance * np.linalg.inv(regressors.T @ regressors)[0, 0])
    assert math.isclose(out.statistic, gamma[0] / se, rel_tol=1e-7)


@pytest.mark.oracle("econometrics.time_series")
@settings(max_examples=25, deadline=None)
@given(seed=st.integers(0, 2**32 - 1), phi=st.floats(-0.9, 0.9), mean=st.floats(-5, 5))
def test_the_ar1_likelihood_and_forecasts_match_their_closed_forms(
    seed: int, phi: float, mean: float
) -> None:
    rng = np.random.default_rng(seed)
    shocks = rng.standard_normal(150)
    y = np.empty(150)
    y[0] = mean + shocks[0] / math.sqrt(1 - phi * phi)
    for t in range(1, 150):
        y[t] = mean + phi * (y[t - 1] - mean) + shocks[t]
    out = run(calculation="arima", series=list(y), ar=1, horizon=5)
    mu, a, s2 = out.parameters
    if not abs(a) < 1:
        reject()
    e = y[1:] - mu - a * (y[:-1] - mu)
    ll = -0.5 * (
        math.log(2 * math.pi * s2 / (1 - a * a)) + (y[0] - mu) ** 2 * (1 - a * a) / s2
    )
    ll += float(np.sum(-0.5 * (np.log(2 * math.pi * s2) + e**2 / s2)))
    assert math.isclose(out.log_likelihood, ll, rel_tol=1e-8)
    expected = [mu + a**h * (y[-1] - mu) for h in range(1, 6)]
    errors = [math.sqrt(s2 * sum(a ** (2 * i) for i in range(h))) for h in range(1, 6)]
    assert np.allclose(out.forecasts, expected, rtol=1e-8, atol=1e-10)
    assert np.allclose(out.forecast_standard_errors, errors, rtol=1e-8)


# --- the published table ----------------------------------------------------------

#: Lutkepohl (2005), section 3.2.3: VAR(2) with intercepts on the log differences
#: of investment, income and consumption, 1960Q4-1978Q4 (73 observations), as
#: StataCorp prints it in [TS] var, Example 1 (lutstats dfk): rows are equations,
#: columns const, L1 (inv, inc, consump), L2 (inv, inc, consump).
LUTKEPOHL_COEFFICIENTS = (
    (-0.0167221, -0.3196318, 0.1459851, 0.9612288, -0.1605508, 0.1146009, 0.9344001),
    (0.0157672, 0.0439309, -0.1527311, 0.2884992, 0.0500302, 0.0191634, -0.0102),
    (0.0129258, -0.002423, 0.2248134, -0.2639695, 0.0338806, 0.3549135, -0.0222264),
)
LUTKEPOHL_ERRORS = (
    (0.0172264, 0.1254564, 0.5456664, 0.6643086, 0.1249066, 0.5345709, 0.6650949),
    (0.0043746, 0.0318592, 0.1385702, 0.168699, 0.0317196, 0.1357525, 0.1688987),
    (0.0035256, 0.0256763, 0.1116778, 0.1359595, 0.0255638, 0.1094069, 0.1361204),
)
#: Lutkepohl's criteria, which count the K^2 p lag coefficients only.
LUTKEPOHL_CRITERIA = {"aic": -24.63163, "hqic": -24.40656, "bic": -24.06686}
LUTKEPOHL_LOG_LIKELIHOOD = 606.307


def lutkepohl_data() -> pd.DataFrame:
    """The e1 data statsmodels ships with its tests (never committed here)."""
    path = (
        Path(statsmodels.__file__).parent
        / "tsa"
        / "tests"
        / "results"
        / "lutkepohl2.dta"
    )
    frame = pd.read_stata(path)
    sample = frame[frame["qtr"] <= pd.Timestamp("1978-10-01")]
    return sample[["dln_inv", "dln_inc", "dln_consump"]].dropna()


def test_lutkepohl_var2_reproduces_the_published_estimates() -> None:
    data = lutkepohl_data()
    out = run(
        calculation="var",
        series=data["dln_inv"].tolist(),
        second=data["dln_inc"].tolist(),
        third=data["dln_consump"].tolist(),
        names=["dln_inv", "dln_inc", "dln_consump"],
        lags=2,
    )
    assert out.observations == 73
    assert np.allclose(out.coefficients, LUTKEPOHL_COEFFICIENTS, rtol=0, atol=5e-8)
    assert np.allclose(out.standard_errors, LUTKEPOHL_ERRORS, rtol=0, atol=5e-8)
    assert math.isclose(out.log_likelihood, LUTKEPOHL_LOG_LIKELIHOOD, abs_tol=5e-4)
    k, n = 3, out.observations
    penalty = {
        "aic": 2 / n,
        "hqic": 2 * math.log(math.log(n)) / n,
        "bic": math.log(n) / n,
    }
    for name, published in LUTKEPOHL_CRITERIA.items():
        # statsmodels also counts the K intercepts.
        assert math.isclose(
            getattr(out, name) - k * penalty[name], published, abs_tol=5e-6
        )


# --- no stray warnings ------------------------------------------------------------


@settings(max_examples=60, deadline=None)
@given(raw=strategies.inputs(time_series))
def test_no_library_warning_escapes_the_model(raw: dict[str, Any]) -> None:
    assert stray_warnings(dict(raw)) == []


# --- inputs, edge cases and documented errors ---------------------------------------


@pytest.mark.parametrize(
    "inputs",
    [
        {"calculation": "var", "series": [1.0, 2.0, 3.0], "second": [1.0, 2.0]},
        {
            "calculation": "var",
            "series": [1.0] * 30,
            "third": [1.0] * 30,
            "second": None,
        },
        {"calculation": "arima", "series": [1.0, 2.0, 4.0, 3.0, 5.0], "seasonal_ar": 1},
        {
            "calculation": "arima",
            "series": [1.0, 2.0, 4.0, 3.0, 5.0, 4.0],
            "differences": 1,
            "trend": "c",
            "ar": 0,
        },
        {"calculation": "arima", "series": [1.0, 2.0, 4.0], "ar": 2},
        {
            "calculation": "johansen",
            "series": [1.0] * 40,
            "second": [2.0] * 40,
            "significance": 0.03,
        },
        {"calculation": "var", "series": [1.0] * 8, "second": [2.0] * 8, "max_lags": 4},
        {
            "calculation": "engle_granger",
            "series": [1.0] * 30,
            "second": [2.0] * 30,
            "names": ["y"],
        },
        {"calculation": "engle_granger", "series": [1.0] * 10, "second": [2.0] * 10},
    ],
)
def test_inconsistent_inputs_are_refused(inputs: dict[str, Any]) -> None:
    with pytest.raises(InputError):
        time_series.validate_inputs(inputs)


def test_every_input_is_bounded() -> None:
    long = {"calculation": "arima", "series": [0.1 * (-1) ** t for t in range(2_001)]}
    with pytest.raises(InputError):
        time_series.validate_inputs(long)
    for options in ({"ar": 5}, {"season": 13, "seasonal_ar": 1}, {"horizon": 121}):
        with pytest.raises(InputError):
            time_series.validate_inputs(
                {
                    "calculation": "arima",
                    "series": [0.1 * (-1) ** t for t in range(100)],
                    **options,
                }
            )
    with pytest.raises(InputError):
        time_series.validate_inputs(
            {
                "calculation": "var",
                "series": [0.1] * 100,
                "second": [0.2] * 100,
                "max_lags": 13,
            }
        )


def test_a_variable_that_does_not_vary_is_a_domain_error() -> None:
    with pytest.raises(DomainError, match="does not vary"):
        run(calculation="arima", series=[2.0] * 30)
    rng = np.random.default_rng(1)
    walk = list(np.cumsum(rng.standard_normal(60)))
    with pytest.raises(DomainError, match="does not vary"):
        run(calculation="var", series=walk, second=[1.0] * 60)


@pytest.mark.parametrize("calculation", ["var", "johansen", "engle_granger"])
def test_collinear_variables_are_a_domain_error(calculation: str) -> None:
    rng = np.random.default_rng(2)
    walk = np.cumsum(rng.standard_normal(80))
    with pytest.raises(DomainError):
        run(calculation=calculation, series=list(walk), second=list(2 * walk))


def test_the_lag_order_is_chosen_from_one_up_with_or_without_a_trend() -> None:
    data = simulate_var(150, 4, np.array([[0.5, 0.1], [0.0, 0.3]]))
    for trend in ("n", "c", "ct"):
        out = run(calculation="var", **variables(data), max_lags=1, trend=trend)
        assert out.lags == 1


def test_an_unstable_var_is_reported() -> None:
    # An explosive pair: each variable grows by 3% a period plus noise.
    data = simulate_var(120, 3, np.array([[1.03, 0.0], [0.0, 1.03]]))
    found = result(calculation="var", **variables(data), lags=1)
    assert not found.outputs.stable
    assert "unstable_var" in {w.code for w in found.warnings}


def test_a_seasonal_lag_may_not_repeat_a_plain_one() -> None:
    series = [0.1 * (-1) ** t + 0.01 * t for t in range(100)]
    for options in (
        {"ar": 2, "season": 2, "seasonal_ar": 1},
        {"ma": 4, "season": 4, "seasonal_ma": 1, "ar": 0},
    ):
        with pytest.raises(InputError, match="repeats a non-seasonal"):
            time_series.validate_inputs(
                {"calculation": "arima", "series": series, **options}
            )
    out = run(calculation="arima", series=series, ar=1, season=2, seasonal_ar=1)
    assert "ar.S.L2" in out.parameter_names


def test_the_default_adf_lags_stay_within_their_bound() -> None:
    data = cointegrated(2000, 7)
    out = run(calculation="engle_granger", **variables(data), lag_criterion=None)
    assert out.lags == 24  # ceil(12 (2000/100)^(1/4)) = 26, capped


def test_long_variable_names_fit_the_term_names() -> None:
    data = simulate_var(80, 6, np.array([[0.4, 0.0], [0.1, 0.2]]))
    names = ["x" * 32, "y" * 32]
    out = run(calculation="var", **variables(data), lags=12, names=names)
    assert out.coefficient_names[-1] == "L12." + "y" * 32


def test_lag_selection_needs_room_for_the_largest_model() -> None:
    rng = np.random.default_rng(8)
    # 27 observations of three variables with a constant: (27 - 3 - 1) // 4 = 5
    # lags can be compared on a common sample, though a VAR(6) alone validates.
    fields = variables(rng.standard_normal((27, 3)))
    with pytest.raises(InputError, match="at most 5 lags can be compared"):
        time_series.validate_inputs({"calculation": "var", **fields, "max_lags": 6})
    time_series.validate_inputs({"calculation": "var", **fields, "lags": 6})
    assert run(calculation="var", **fields, max_lags=5).lags >= 1


def test_a_lagged_variable_constant_over_the_sample_is_a_domain_error() -> None:
    rng = np.random.default_rng(9)
    first = list(rng.standard_normal(40))
    second = [1.0] * 39 + [2.0]
    with pytest.raises(DomainError, match="constant over the fitted sample"):
        run(calculation="var", series=first, second=second, lags=1)


def test_the_names_label_the_variables_and_the_terms() -> None:
    data = simulate_var(80, 5, np.array([[0.4, 0.0], [0.1, 0.2]]))
    out = run(calculation="var", **variables(data), lags=2, names=["gdp", "rate"])
    assert out.variables == ("gdp", "rate")
    assert out.coefficient_names == ("const", "L1.gdp", "L1.rate", "L2.gdp", "L2.rate")


def test_the_arima_chart_is_a_band() -> None:
    found = result(calculation="arima", series=list(np.sin(np.arange(40.0))), horizon=6)
    figure = found.plot()
    assert len(figure.data) >= 2


# --- the econometrics extra ---------------------------------------------------------


@pytest.fixture
def without_statsmodels(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the extra's packages unimportable and their distributions uninstalled.

    arch, the extra's other package, imports statsmodels: both go.
    """
    extra = {"statsmodels", "arch"}
    for name in [m for m in sys.modules if m.split(".")[0] in extra]:
        monkeypatch.setitem(sys.modules, name, None)
    for package in extra:
        monkeypatch.setitem(sys.modules, package, None)
    installed = core_registry._is_installed  # noqa: SLF001

    def missing(distribution: str) -> bool:
        return distribution not in extra and installed(distribution)

    monkeypatch.setattr(core_registry, "_is_installed", missing)


@pytest.mark.usefixtures("without_statsmodels")
def test_without_statsmodels_the_model_names_the_extra() -> None:
    with pytest.raises(MissingOptionalDependencyError) as caught:
        run_model(time_series, time_series.spec.examples[0].inputs)
    assert caught.value.extra == "econometrics"
    assert caught.value.package == "statsmodels"
    assert "pip install 'pyeconomics[econometrics]'" in str(caught.value)


def test_importing_the_package_does_not_import_statsmodels(tmp_path: Path) -> None:
    code = (
        "import sys, pyeconomics.models.econometrics; "
        "print('statsmodels' in sys.modules)"
    )
    found = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
    )
    assert found.stdout.strip() == "False"
