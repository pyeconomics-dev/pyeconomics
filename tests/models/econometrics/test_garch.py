# tests/models/econometrics/test_garch.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``econometrics.garch``: invariants, SciPy oracles and the arch gap.

The oracles are independent of arch's code: the variance recursions are written
out here from Bollerslev (1986), Glosten, Jagannathan and Runkle (1993) and
Nelson (1991), started from the backcast arch documents, and the likelihood is
SciPy's normal or standardized Student's t density at the model's reported
(decimal) parameters.

arch publishes no wheel for CPython 3.15 yet, so the econometrics extra and the
test group leave it out there (issue #154). On those cells every test that needs
arch asserts instead that the model names the gap: never a skip.

statsmodels and arch reset their own warning filters, so pytest's
warnings-as-errors cannot see a library warning raised inside the model;
:func:`stray_warnings` records them instead.
"""

from __future__ import annotations

import contextlib
import importlib.metadata
import importlib.util
import math
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
import warnings
from collections.abc import Callable
from itertools import pairwise
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest
import scipy.stats
import strategies
from hypothesis import given, reject, settings
from hypothesis import strategies as st

from pyeconomics import registry
from pyeconomics.core import (
    DomainError,
    InputError,
    MissingOptionalDependencyError,
    ModelWarning,
    run_model,
)
from pyeconomics.core import registry as core_registry
from pyeconomics.core.registry import Provider
from pyeconomics.models.econometrics import garch

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from numpy.typing import NDArray

#: The cells the econometrics extra cannot install arch on (the Wheel rule).
GAP = sys.version_info >= (3, 15)
SQRT_2_OVER_PI = math.sqrt(2 / math.pi)


def assert_the_gap() -> None:
    """The model raises naming the extra, arch and the CPython 3.15 gap."""
    with pytest.raises(MissingOptionalDependencyError) as caught:
        run_model(garch, garch.spec.examples[0].inputs)
    assert caught.value.package == "arch"
    assert caught.value.extra == "econometrics"
    assert "CPython 3.15" in str(caught.value)
    assert "#154" in str(caught.value)


def needs_arch[Test: Callable[..., None]](test: Test) -> Test:
    """Run the test where arch installs; where it cannot, assert the gap instead."""
    if not GAP:
        return test

    def gap() -> None:
        assert_the_gap()

    gap.__name__ = test.__name__
    gap.__qualname__ = test.__qualname__
    gap.__doc__ = test.__doc__
    gap.pytestmark = [  # type: ignore[attr-defined]
        mark
        for mark in getattr(test, "pytestmark", [])
        if mark.name in {"invariant", "oracle"}
    ]
    return gap  # type: ignore[return-value]


def result(**inputs: Any) -> Any:  # noqa: ANN401 - a Result
    return run_model(garch, inputs)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the outputs
    return result(**inputs).outputs


def simulate(  # noqa: PLR0913 - a process and its parameters
    count: int,
    seed: int,
    *,
    omega: float = 1e-6,
    alpha: float = 0.08,
    gamma: float = 0.0,
    beta: float = 0.9,
    mu: float = 0.0,
    nu: float | None = None,
) -> list[float]:
    """Simulate a GJR(1, 1, 1) path in decimals (gamma 0 is GARCH(1, 1))."""
    rng = np.random.default_rng(seed)
    draws = (
        rng.standard_t(nu, count + 200) * math.sqrt((nu - 2) / nu)
        if nu is not None
        else rng.standard_normal(count + 200)
    )
    variance = omega / (1 - alpha - gamma / 2 - beta)
    path = []
    for z in draws:
        shock = math.sqrt(variance) * float(z)
        path.append(mu + shock)
        variance = (
            omega + (alpha + gamma * (shock < 0)) * shock * shock + beta * variance
        )
    return path[200:]


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


# --- the oracle: the recursions written out ----------------------------------------


def backcast(residuals: NDArray[np.float64]) -> float:
    """arch's backcast: the 0.94-weighted mean of the first min(75, n) squares."""
    tau = min(75, len(residuals))
    weights = 0.94 ** np.arange(tau)
    return float(np.sum(weights * residuals[:tau] ** 2) / np.sum(weights))


def split(names: Sequence[str], values: Sequence[float]) -> dict[str, Any]:
    """The parameters by family: mu, omega, alpha, gamma, beta (lists) and nu."""
    found: dict[str, Any] = {"mu": 0.0, "alpha": [], "gamma": [], "beta": []}
    for name, value in zip(names, values, strict=True):
        family = name.partition("[")[0]
        if family in {"alpha", "gamma", "beta"}:
            found[family].append(value)
        else:
            found[family] = value
    return found


def fitted_scale(returns: Sequence[float] | NDArray[np.float64]) -> float:
    """The model's scale: percent, then the power of ten arch advises."""
    variance = float(np.var(np.asarray(returns, dtype=np.float64)))
    scale = 100.0
    while not 0.1 <= variance * scale * scale < 1e4:
        scale = scale * 10 if variance * scale * scale < 1 else scale / 10
    return scale


def within_bounds(
    sigma2: NDArray[np.float64], start: NDArray[np.float64], scale: float
) -> bool:
    """Whether a path stays inside the variance bounds arch documents.

    arch clips each conditional variance to [EWMA / 1e6, EWMA x 1e6] (0.94
    smoothing of the residuals), floored at var / 1e8 and capped between
    1 + max e^2 and 1e7 (1 + max e^2), all in its fitted units. A path the
    recursion takes outside them is one arch does not follow.
    """
    if not np.all(np.isfinite(sigma2) & (sigma2 > 0)):
        return False
    e = start * scale
    tau = min(75, len(e))
    weights = 0.94 ** np.arange(tau)
    ewma = np.empty(len(e))
    ewma[0] = float(weights @ e[:tau] ** 2 / weights.sum())
    for t in range(1, len(e)):
        ewma[t] = 0.06 * e[t - 1] ** 2 + 0.94 * ewma[t - 1]
    peak = 1 + float(np.max(e**2))
    lower = np.maximum(ewma / 1e6, float(np.var(e)) / 1e8)
    upper = np.clip(ewma * 1e6, peak, 1e7 * peak)
    scaled = sigma2 * scale * scale
    return bool(np.all((scaled >= lower) & (scaled <= upper)))


def variances(  # noqa: C901 - three processes written out
    calculation: str,
    inputs: dict[str, Any],
    params: dict[str, Any],
    *,
    forecasting: bool = False,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """The conditional variances and residuals of the returns, by the recursion.

    The backcast is of the demeaned returns for the fit and of the returns less
    the estimated mean for the forecasts, as arch has it.
    """
    r = np.asarray(inputs["returns"], dtype=np.float64)
    e = r - params["mu"]
    constant = inputs.get("mean", "constant") == "constant"
    start = e if forecasting else r - (np.mean(r) if constant else 0.0)
    b = backcast(start)
    alpha, gamma, beta = params["alpha"], params["gamma"], params["beta"]
    sigma2 = np.empty(len(r))
    if calculation == "egarch":
        log = np.empty(len(r))
        # A degenerate path underflows: within_bounds then rejects it.
        with np.errstate(all="ignore"):
            for t in range(len(r)):
                value = params["omega"]
                for i, a in enumerate(alpha, start=1):
                    if t - i >= 0:
                        value += a * (
                            abs(e[t - i]) / math.sqrt(sigma2[t - i]) - SQRT_2_OVER_PI
                        )
                for j, g in enumerate(gamma, start=1):
                    if t - j >= 0:
                        value += g * e[t - j] / math.sqrt(sigma2[t - j])
                for k, c in enumerate(beta, start=1):
                    value += c * (log[t - k] if t - k >= 0 else math.log(b))
                log[t] = value
                sigma2[t] = np.exp(value)
        return sigma2, e
    for t in range(len(r)):
        value = params["omega"]
        for i, a in enumerate(alpha, start=1):
            value += a * (e[t - i] ** 2 if t - i >= 0 else b)
        for j, g in enumerate(gamma, start=1):
            negative = e[t - j] ** 2 * (e[t - j] < 0) if t - j >= 0 else b / 2
            value += g * negative
        for k, c in enumerate(beta, start=1):
            value += c * (sigma2[t - k] if t - k >= 0 else b)
        sigma2[t] = value
    return sigma2, e


def log_likelihood(
    e: NDArray[np.float64], sigma2: NDArray[np.float64], nu: float | None
) -> float:
    """SciPy's log density of the standardized errors, less the log scale."""
    sigma = np.sqrt(sigma2)
    if nu is None:
        return float(np.sum(scipy.stats.norm.logpdf(e, scale=sigma)))
    scale = sigma * math.sqrt((nu - 2) / nu)
    return float(np.sum(scipy.stats.t.logpdf(e, nu, scale=scale)))


def forecast(
    params: dict[str, Any], sigma2: NDArray[np.float64], e: NDArray[np.float64], h: int
) -> list[float]:
    """GARCH and GJR variance forecasts: E[e^2 1(e < 0)] = sigma^2 / 2 ahead."""
    alpha, gamma, beta = params["alpha"], params["gamma"], params["beta"]
    past_e2 = list(e**2)
    past_negative = list(e**2 * (e < 0))
    past_s2 = list(sigma2)
    out: list[float] = []
    for step in range(h):
        value = params["omega"]
        for i, a in enumerate(alpha, start=1):
            value += a * (past_e2[step - i] if step - i < 0 else out[step - i])
        for j, g in enumerate(gamma, start=1):
            value += g * (
                past_negative[step - j] if step - j < 0 else out[step - j] / 2
            )
        for k, c in enumerate(beta, start=1):
            value += c * (past_s2[step - k] if step - k < 0 else out[step - k])
        out.append(value)
    return out


# --- strategies -----------------------------------------------------------------


@st.composite
def fits(
    draw: st.DrawFn, *, calculations: Sequence[str] = ("garch", "gjr", "egarch")
) -> dict[str, Any]:
    """Draw a model specification and a simulated path it can fit."""
    calculation = draw(st.sampled_from(calculations))
    inputs: dict[str, Any] = {
        "calculation": calculation,
        "returns": simulate(
            draw(st.integers(300, 600)),
            draw(st.integers(0, 2**32 - 1)),
            alpha=draw(st.floats(0.03, 0.15)),
            gamma=draw(st.sampled_from([0.0, 0.05])),
            beta=draw(st.floats(0.6, 0.8)),
            mu=draw(st.sampled_from([0.0, 0.0004])),
            nu=draw(st.sampled_from([None, 6.0])),
        ),
        "periods_per_year": 252,
        "mean": draw(st.sampled_from(["constant", "zero"])),
        "distribution": draw(st.sampled_from(["normal", "student_t"])),
        "p": draw(st.integers(1, 2)),
        "q": draw(st.integers(1, 2)),
        "horizon": draw(st.integers(1, 30)),
    }
    if calculation != "garch":
        inputs["asymmetric_lags"] = draw(st.integers(1, 2))
    if calculation == "egarch":
        inputs["simulations"] = 200
    return inputs


@st.composite
def fixed_order_one(draw: st.DrawFn) -> dict[str, Any]:
    """Draw a GARCH(1, 1) or GJR(1, 1, 1) at fixed, stationary parameters."""
    gjr = draw(st.booleans())
    alpha = draw(st.floats(0.0, 0.3))
    gamma = draw(st.floats(-alpha, 0.3)) if gjr else 0.0
    beta = draw(st.floats(0.0, 0.95 - alpha - gamma / 2).filter(lambda b: b >= 0))
    omega = draw(st.floats(1e-7, 1e-4))
    values = [omega, alpha, *([gamma] if gjr else []), beta]
    return {
        "calculation": "gjr" if gjr else "garch",
        "returns": simulate(draw(st.integers(100, 300)), draw(st.integers(0, 10**6))),
        "periods_per_year": 252,
        "mean": "zero",
        "horizon": draw(st.integers(2, 60)),
        "fixed_parameters": values,
    }


# --- invariants -------------------------------------------------------------------


@needs_arch
@pytest.mark.invariant(
    "econometrics.garch", "forecast_converges_to_unconditional_variance"
)
@settings(max_examples=40, deadline=None)
@given(inputs=fixed_order_one())
def test_forecasts_close_the_gap_by_the_persistence_each_period(
    inputs: dict[str, Any],
) -> None:
    out = run(**inputs)
    assert out.unconditional_volatility is not None
    bar = out.unconditional_volatility**2
    first = out.variance_forecasts[0]
    for h, value in enumerate(out.variance_forecasts, start=1):
        expected = bar + out.persistence ** (h - 1) * (first - bar)
        assert math.isclose(value, expected, rel_tol=1e-9, abs_tol=1e-18)
    gaps = [abs(v - bar) for v in out.variance_forecasts]
    assert all(
        later <= earlier * (1 + 1e-12) + 1e-18 for earlier, later in pairwise(gaps)
    )


@needs_arch
@pytest.mark.invariant(
    "econometrics.garch", "forecast_converges_to_unconditional_variance"
)
@settings(max_examples=10, deadline=None)
@given(inputs=fits(calculations=("garch", "gjr")))
def test_estimated_forecasts_approach_the_long_run_variance(
    inputs: dict[str, Any],
) -> None:
    inputs = {**inputs, "p": 1, "q": 1, "horizon": 400}
    if inputs["calculation"] == "gjr":
        inputs["asymmetric_lags"] = 1
    out = run(**inputs)
    if out.unconditional_volatility is None:
        assert out.persistence >= 1
        return
    bar = out.unconditional_volatility**2
    first, last = out.variance_forecasts[0], out.variance_forecasts[-1]
    assert (
        abs(last - bar) <= out.persistence**399 * abs(first - bar) * (1 + 1e-6) + 1e-18
    )


@needs_arch
@pytest.mark.invariant("econometrics.garch", "conditional_variance_is_positive")
@settings(max_examples=15, deadline=None)
@given(inputs=fits())
def test_every_variance_is_positive(inputs: dict[str, Any]) -> None:
    try:
        out = run(**inputs)
    except DomainError:
        reject()  # an explosive fit is refused, as documented
    assert out.last_volatility > 0
    assert all(v > 0 for v in out.variance_forecasts)
    assert all(v > 0 for v in out.volatility_forecasts_annualized)


@needs_arch
@pytest.mark.invariant("econometrics.garch", "rescaling_returns_rescales_the_variance")
@settings(max_examples=30, deadline=None)
@given(
    calculation=st.sampled_from(["garch", "gjr", "egarch"]),
    factor=st.sampled_from([0.37, 3.1, 10.0, 0.01]),
    seed=st.integers(0, 10**6),
)
def test_rescaling_the_returns_rescales_mu_and_the_variances(
    calculation: str, factor: float, seed: int
) -> None:
    returns = simulate(200, seed, mu=0.0003)
    values = {
        "garch": [0.0003, 2e-6, 0.08, 0.88],
        "gjr": [0.0003, 2e-6, 0.05, 0.06, 0.88],
        "egarch": [0.0003, -0.3, 0.1, -0.05, 0.97],
    }[calculation]
    base = {
        "calculation": calculation,
        "periods_per_year": 252,
        "horizon": 3,
        "simulations": 300,
    }
    if calculation != "egarch":
        base.pop("simulations")
    scaled = list(values)
    scaled[0] *= factor
    if calculation == "egarch":
        scaled[1] += (1 - values[-1]) * math.log(factor * factor)
    else:
        scaled[1] *= factor * factor
    one = run(**base, returns=returns, fixed_parameters=values)
    two = run(**base, returns=[r * factor for r in returns], fixed_parameters=scaled)
    assert math.isclose(two.parameters[0], one.parameters[0] * factor, rel_tol=1e-9)
    assert np.allclose(two.parameters[2:], one.parameters[2:], rtol=1e-9, atol=0)
    assert math.isclose(two.last_volatility, one.last_volatility * factor, rel_tol=1e-8)
    if calculation != "egarch":
        assert np.allclose(
            np.asarray(two.variance_forecasts),
            np.asarray(one.variance_forecasts) * factor * factor,
            rtol=1e-8,
            atol=0,
        )
    n = len(returns)
    assert math.isclose(
        two.log_likelihood, one.log_likelihood - n * math.log(factor), rel_tol=1e-9
    )


@needs_arch
def test_a_power_of_ten_leaves_the_estimates_unchanged() -> None:
    returns = simulate(500, 3, mu=0.0004)
    for calculation in ("garch", "egarch"):
        base = {"calculation": calculation, "periods_per_year": 252, "horizon": 1}
        one = run(**base, returns=returns)
        # A thousandth of the returns: the model's scale rises by the same
        # power of ten, so arch fits the very same numbers.
        two = run(**base, returns=[r / 1000 for r in returns])
        assert fitted_scale([r / 1000 for r in returns]) == 1000 * fitted_scale(returns)
        assert math.isclose(two.parameters[0], one.parameters[0] / 1000, rel_tol=1e-6)
        assert np.allclose(two.parameters[2:], one.parameters[2:], rtol=1e-6, atol=0)


@needs_arch
def test_persistence_a_hair_below_one_has_no_unconditional_volatility() -> None:
    found = result(
        calculation="garch",
        returns=simulate(150, 4),
        periods_per_year=252,
        mean="zero",
        p=2,
        fixed_parameters=[1e-4, 0.6, 0.3, 0.1],
    )
    assert found.outputs.unconditional_volatility is None
    assert "no_unconditional_variance" in {w.code for w in found.warnings}


# --- oracles ----------------------------------------------------------------------


@needs_arch
@pytest.mark.oracle("econometrics.garch")
@settings(max_examples=25, deadline=None)
@given(inputs=fits())
def test_the_log_likelihood_matches_scipy_at_the_estimates(
    inputs: dict[str, Any],
) -> None:
    try:
        out = run(**inputs)
    except DomainError:
        reject()  # an explosive fit has no likelihood to check
    params = split(out.parameter_names, out.parameters)
    sigma2, e = variances(inputs["calculation"], inputs, params)
    r = np.asarray(inputs["returns"], dtype=np.float64)
    start = r - (np.mean(r) if inputs.get("mean", "constant") == "constant" else 0.0)
    if not within_bounds(sigma2, start, fitted_scale(r)):
        reject()  # arch clips this path; the recursion alone does not
    expected = log_likelihood(e, sigma2, params.get("nu"))
    assert math.isclose(out.log_likelihood, expected, rel_tol=1e-8, abs_tol=1e-6)
    k = len(out.parameters)
    assert math.isclose(out.aic, -2 * expected + 2 * k, rel_tol=1e-8, abs_tol=1e-6)
    n = len(inputs["returns"])
    assert math.isclose(
        out.bic, -2 * expected + k * math.log(n), rel_tol=1e-8, abs_tol=1e-6
    )
    assert math.isclose(out.last_volatility, math.sqrt(sigma2[-1]), rel_tol=1e-8)


@needs_arch
@pytest.mark.oracle("econometrics.garch")
@settings(max_examples=25, deadline=None)
@given(inputs=fits())
def test_the_forecasts_match_the_recursion(inputs: dict[str, Any]) -> None:
    try:
        out = run(**inputs)
    except DomainError:
        reject()  # an explosive fit has no forecast to check
    params = split(out.parameter_names, out.parameters)
    sigma2, e = variances(inputs["calculation"], inputs, params, forecasting=True)
    if not within_bounds(sigma2, e, fitted_scale(inputs["returns"])):
        reject()  # arch clips this path; the recursion alone does not
    if inputs["calculation"] == "egarch":
        log_next = params["omega"]
        with np.errstate(divide="ignore", invalid="ignore"):
            z = e / np.sqrt(sigma2)
        if not np.all(np.isfinite(z)) or np.any(sigma2 <= 0):
            reject()
        for i, a in enumerate(params["alpha"], start=1):
            log_next += a * (abs(z[-i]) - SQRT_2_OVER_PI)
        for j, g in enumerate(params["gamma"], start=1):
            log_next += g * z[-j]
        for k, c in enumerate(params["beta"], start=1):
            log_next += c * math.log(sigma2[-k])
        assert math.isclose(out.variance_forecasts[0], math.exp(log_next), rel_tol=1e-8)
        return
    expected = forecast(params, sigma2, e, inputs["horizon"])
    assert np.allclose(out.variance_forecasts, expected, rtol=1e-8, atol=0)
    periods = inputs["periods_per_year"]
    assert np.allclose(
        out.volatility_forecasts_annualized,
        np.sqrt(periods * np.asarray(expected)),
        rtol=1e-8,
    )
    cumulative = np.cumsum(expected) / np.arange(1, len(expected) + 1)
    assert np.allclose(
        out.term_volatility_annualized, np.sqrt(periods * cumulative), rtol=1e-8
    )


@needs_arch
@pytest.mark.oracle("econometrics.garch")
@settings(max_examples=10, deadline=None)
@given(
    seed=st.integers(0, 10**6), distribution=st.sampled_from(["normal", "student_t"])
)
def test_the_egarch_omega_error_follows_the_delta_method(
    seed: int, distribution: str
) -> None:
    from arch import univariate  # noqa: PLC0415 - the extra, as the model does

    returns = simulate(400, seed)
    out = run(
        calculation="egarch",
        returns=returns,
        periods_per_year=252,
        mean="zero",
        distribution=distribution,
        horizon=1,
    )
    scale = 100.0
    errors = univariate.Normal() if distribution == "normal" else univariate.StudentsT()
    direct = univariate.ZeroMean(
        np.asarray(returns) * scale,
        volatility=univariate.EGARCH(1, 1, 1),
        distribution=errors,
        rescale=False,
    ).fit(disp="off")
    cov = np.asarray(direct.param_cov)
    log_scale = 2 * math.log(scale)
    omega_variance = cov[0, 0] + log_scale**2 * cov[3, 3] + 2 * log_scale * cov[0, 3]
    assert out.standard_errors is not None
    assert math.isclose(out.standard_errors[0], math.sqrt(omega_variance), rel_tol=1e-6)
    expected_omega = direct.params.iloc[0] - (1 - direct.params.iloc[3]) * log_scale
    assert math.isclose(out.parameters[0], expected_omega, rel_tol=1e-9, abs_tol=1e-12)


# --- no stray warnings ------------------------------------------------------------


@needs_arch
@settings(max_examples=30, deadline=None)
@given(raw=strategies.inputs(garch))
def test_no_library_warning_escapes_the_model(raw: dict[str, Any]) -> None:
    assert stray_warnings(dict(raw)) == []


# --- inputs, edge cases and documented errors ---------------------------------------


@needs_arch
def test_returns_that_do_not_vary_are_a_domain_error() -> None:
    with pytest.raises(DomainError, match="barely vary"):
        run(calculation="garch", returns=[0.01] * 120, periods_per_year=252)
    with pytest.raises(DomainError, match="barely vary"):
        run(
            calculation="garch",
            returns=[1e-10 * (-1) ** t for t in range(120)],
            periods_per_year=252,
        )


@needs_arch
def test_fixed_parameters_have_no_standard_errors() -> None:
    found = result(
        calculation="garch",
        returns=simulate(150, 1),
        periods_per_year=252,
        fixed_parameters=[0.0, 1e-6, 0.1, 0.85],
    )
    assert found.outputs.standard_errors is None
    assert found.outputs.t_statistics is None
    assert "fixed_parameters" in {w.code for w in found.warnings}


@needs_arch
def test_egarch_simulated_forecasts_repeat_with_their_seed() -> None:
    inputs = {
        "calculation": "egarch",
        "returns": simulate(300, 5),
        "periods_per_year": 252,
        "horizon": 5,
        "simulations": 200,
        # Fixed, so no optimizer (whose path differs by platform) is involved.
        "fixed_parameters": [0.0, -0.3, 0.1, -0.05, 0.97],
    }
    first, again = run(**inputs, seed=1), run(**inputs, seed=1)
    other = run(**inputs, seed=2)
    assert first.variance_forecasts == again.variance_forecasts
    assert first.variance_forecasts[1:] != other.variance_forecasts[1:]
    assert first.variance_forecasts[0] == other.variance_forecasts[0]


@needs_arch
def test_egarch_reports_no_unconditional_volatility() -> None:
    found = result(
        calculation="egarch",
        returns=simulate(300, 6),
        periods_per_year=12,
        fixed_parameters=[0.0, -0.3, 0.1, -0.05, 0.97],
    )
    assert found.outputs.unconditional_volatility is None
    assert "no_unconditional_variance" in {w.code for w in found.warnings}


@needs_arch
def test_an_integrated_process_has_no_unconditional_volatility() -> None:
    found = result(
        calculation="garch",
        returns=simulate(150, 2),
        periods_per_year=252,
        mean="zero",
        horizon=4,
        fixed_parameters=[1e-6, 0.1, 0.9],
    )
    out = found.outputs
    assert out.persistence == 1.0
    assert out.unconditional_volatility is None
    assert "no_unconditional_variance" in {w.code for w in found.warnings}
    steps = np.diff(out.variance_forecasts)
    assert np.allclose(steps, 1e-6, rtol=1e-6)


@needs_arch
def test_a_student_t_fit_reports_nu_last() -> None:
    out = run(
        calculation="gjr",
        returns=simulate(400, 4, gamma=0.05, beta=0.85, nu=5.0),
        periods_per_year=252,
        distribution="student_t",
    )
    assert out.parameter_names == (
        "mu",
        "omega",
        "alpha[1]",
        "gamma[1]",
        "beta[1]",
        "nu",
    )
    assert 2.05 <= out.parameters[-1] <= 500


@pytest.mark.parametrize(
    ("calculation", "fixed", "match"),
    [
        ("garch", [0.0, 1e-6, 0.1], "must give 4 values"),
        ("garch", [0.0, -1e-6, 0.1, 0.8], "omega must be positive"),
        ("garch", [0.0, 1e-6, -0.1, 0.8], "must not be negative"),
        ("garch", [0.0, 1e-6, 0.3, 0.8], "must not exceed one"),
        ("gjr", [0.0, 1e-6, 0.05, -0.1, 0.8], "alpha \\+ gamma"),
        ("egarch", [0.0, -0.3, 0.1, 0.0, 1.0], "strictly between"),
        ("garch", [20.0, 1e-6, 0.1, 0.8], "mu must lie"),
    ],
)
def test_inconsistent_fixed_parameters_are_refused(
    calculation: str, fixed: list[float], match: str
) -> None:
    inputs: dict[str, Any] = {
        "calculation": calculation,
        "returns": [0.01 * (-1) ** t for t in range(100)],
        "periods_per_year": 252,
        "fixed_parameters": fixed,
    }
    if calculation == "egarch":
        inputs["mean"] = "constant"
    with pytest.raises(InputError, match=match):
        garch.validate_inputs(inputs)


def test_student_t_needs_nu_in_range() -> None:
    inputs = {
        "calculation": "garch",
        "returns": [0.01 * (-1) ** t for t in range(100)],
        "periods_per_year": 252,
        "distribution": "student_t",
        "mean": "zero",
        "fixed_parameters": [1e-6, 0.1, 0.8, 1.5],
    }
    with pytest.raises(InputError, match="nu must lie"):
        garch.validate_inputs(inputs)


def test_every_input_is_bounded() -> None:
    with pytest.raises(InputError):
        garch.validate_inputs(
            {"calculation": "garch", "returns": [0.01] * 10_001, "periods_per_year": 1}
        )
    with pytest.raises(InputError):
        garch.validate_inputs(
            {"calculation": "garch", "returns": [0.01] * 99, "periods_per_year": 1}
        )
    with pytest.raises(InputError):
        garch.validate_inputs(
            {
                "calculation": "garch",
                "returns": [0.01] * 100,
                "periods_per_year": 1,
                "p": 3,
            }
        )
    with pytest.raises(InputError):
        garch.validate_inputs(
            {
                "calculation": "egarch",
                "returns": [0.01] * 100,
                "periods_per_year": 1,
                "simulations": 10_001,
            }
        )


# --- the extra and the CPython 3.15 gap -------------------------------------------


@pytest.fixture
def without_arch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make arch unimportable, as it is where no wheel installs."""
    for name in [m for m in sys.modules if m.split(".")[0] == "arch"]:
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setitem(sys.modules, "arch", None)


@pytest.mark.usefixtures("without_arch")
def test_without_arch_the_model_names_the_extra_and_the_gap() -> None:
    assert_the_gap()


def test_on_a_cell_without_an_arch_wheel_the_model_names_the_gap() -> None:
    """Where the marker leaves arch out (CPython 3.15), the model says so."""
    installed = importlib.util.find_spec("arch") is not None
    assert installed is not GAP
    if GAP:
        assert_the_gap()
    else:
        assert run_model(garch, garch.spec.examples[0].inputs).outputs is not None


def test_the_extra_leaves_arch_out_only_where_the_marker_says() -> None:
    provider = Provider.from_distribution(
        importlib.metadata.distribution("pyeconomics")
    )
    assert provider.installed("econometrics")
    assert provider.excludes("econometrics", "arch") is GAP
    assert ("arch" in provider.extras["econometrics"]) is not GAP
    assert "statsmodels" in provider.extras["econometrics"]


def test_the_registry_validates_with_or_without_the_gap() -> None:
    registration = next(
        r for r in core_registry.installed().registrations if r.model.id == garch.id
    )
    assert registration.provider.declares("econometrics")
    assert garch.spec.extra == "econometrics"
    registry.validate()


def test_importing_the_package_does_not_import_arch(tmp_path: Path) -> None:
    code = "import sys, pyeconomics.models.econometrics; print('arch' in sys.modules)"
    # From an empty directory: the checkout's root must not be on sys.path.
    found = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
    )
    assert found.stdout.strip() == "False"


def test_the_gap_decorator_keeps_only_the_markers() -> None:
    def sample(x: int) -> None:
        raise AssertionError(x)

    # Built by name, so the invariant scan does not take it for a real marker.
    marked = getattr(pytest.mark, "oracle")("econometrics.garch")  # noqa: B009
    sample = pytest.mark.parametrize("x", [1])(marked(sample))
    kept = needs_arch(sample)
    if GAP:
        assert [m.name for m in kept.pytestmark] == ["oracle"]  # type: ignore[attr-defined]
    else:
        assert kept is sample
