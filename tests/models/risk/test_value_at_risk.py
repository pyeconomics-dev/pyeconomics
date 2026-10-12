# tests/models/risk/test_value_at_risk.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``risk.value_at_risk``: invariants, warnings and independent oracles.

The oracles are SciPy (the normal distribution's conditional expectation, and
quadrature of the Edgeworth density for the modified ES) and pandas (its
exponentially weighted mean with ``adjust=False`` is the RiskMetrics recursion
seeded with the first squared return). Both are imported at the top, so a
missing one fails the suite.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
import pytest
import scipy.integrate
import scipy.stats
from hypothesis import given, reject
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.risk import value_at_risk
from pyeconomics.models.risk._common import bounded

CONFIDENCE = st.floats(0.5, 0.9999)
VOLATILITY = st.floats(0.0001, 2.0)
MEAN = st.floats(-1.0, 1.0)
HORIZON = st.floats(1.0, 1000.0)
RETURNS = st.lists(st.floats(-1.0, 100.0), min_size=2, max_size=60)
SMALL_RETURNS = st.lists(st.floats(-0.2, 0.2), min_size=1, max_size=60)


def result(**inputs: Any) -> Any:  # noqa: ANN401 - a Result
    return run_model(value_at_risk, inputs)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the outputs
    return result(**inputs).outputs


@st.composite
def calculations(draw: st.DrawFn) -> dict[str, Any]:
    """Draw inputs for any calculation, with a modest Monte Carlo."""
    kind = draw(
        st.sampled_from(
            ["parametric", "cornish_fisher", "historical", "monte_carlo", "ewma"]
        )
    )
    common = {"calculation": kind, "horizon": draw(HORIZON)}
    if kind in {"parametric", "cornish_fisher", "monte_carlo"}:
        common |= {"mean": draw(MEAN), "volatility": draw(VOLATILITY)}
    if kind == "cornish_fisher":
        common |= {
            "skewness": draw(st.floats(-3.0, 3.0)),
            "excess_kurtosis": draw(st.floats(-2.0, 20.0)),
        }
    if kind == "historical":
        common |= {
            "returns": draw(RETURNS),
            "interpolation": draw(
                st.sampled_from(["linear", "lower", "higher", "midpoint", "nearest"])
            ),
        }
    if kind == "monte_carlo":
        common |= {
            "simulations": 10_000,
            "seed": draw(st.integers(0, 2**32)),
            "distribution": draw(st.sampled_from(["normal", "student_t"])),
            "degrees_of_freedom": draw(st.floats(2.5, 50.0)),
        }
    if kind == "ewma":
        common |= {"returns": draw(SMALL_RETURNS), "decay": draw(st.floats(0.5, 0.999))}
    return common


@pytest.mark.invariant("risk.value_at_risk", "es_at_least_var")
@given(inputs=calculations(), confidence=CONFIDENCE)
def test_expected_shortfall_is_at_least_var(
    inputs: dict[str, Any], confidence: float
) -> None:
    try:
        out = run(**inputs, confidence=confidence)
    except DomainError:
        reject()
    assert out.expected_shortfall >= out.value_at_risk


@st.composite
def monotone_calculations(draw: st.DrawFn) -> dict[str, Any]:
    """Draw inputs where VaR must rise with confidence (Cornish-Fisher in domain)."""
    inputs = draw(calculations())
    if inputs["calculation"] == "cornish_fisher":
        inputs |= {
            "skewness": draw(st.floats(-0.2, 0.2)),
            "excess_kurtosis": draw(st.floats(0.0, 1.0)),
        }
    return inputs


@pytest.mark.invariant("risk.value_at_risk", "var_increases_with_confidence")
@given(inputs=monotone_calculations(), first=CONFIDENCE, second=CONFIDENCE)
def test_var_rises_with_confidence(
    inputs: dict[str, Any], first: float, second: float
) -> None:
    low, high = sorted((first, second))
    lower = run(**inputs, confidence=low).value_at_risk
    higher = run(**inputs, confidence=high).value_at_risk
    assert higher >= lower - 1e-12 * max(1.0, abs(lower))


@pytest.mark.invariant("risk.value_at_risk", "parametric_var_scales_with_sqrt_horizon")
@given(volatility=VOLATILITY, confidence=CONFIDENCE, horizon=HORIZON)
def test_parametric_var_scales_with_the_root_of_the_horizon(
    volatility: float, confidence: float, horizon: float
) -> None:
    one = run(calculation="parametric", volatility=volatility, confidence=confidence)
    many = run(
        calculation="parametric",
        volatility=volatility,
        confidence=confidence,
        horizon=horizon,
    )
    assert math.isclose(
        many.value_at_risk, math.sqrt(horizon) * one.value_at_risk, rel_tol=1e-12
    )
    assert math.isclose(
        many.expected_shortfall,
        math.sqrt(horizon) * one.expected_shortfall,
        rel_tol=1e-12,
    )


@pytest.mark.invariant("risk.value_at_risk", "cornish_fisher_reduces_to_normal")
@given(mean=MEAN, volatility=VOLATILITY, confidence=CONFIDENCE, horizon=HORIZON)
def test_cornish_fisher_without_shape_is_normal(
    mean: float, volatility: float, confidence: float, horizon: float
) -> None:
    common = {
        "mean": mean,
        "volatility": volatility,
        "confidence": confidence,
        "horizon": horizon,
    }
    normal = run(calculation="parametric", **common)
    modified = run(calculation="cornish_fisher", **common)
    for name in ("value_at_risk", "expected_shortfall", "quantile"):
        assert math.isclose(
            getattr(modified, name),
            getattr(normal, name),
            rel_tol=1e-12,
            abs_tol=1e-12,
        )


@pytest.mark.oracle("risk.value_at_risk")
@given(mean=MEAN, volatility=VOLATILITY, confidence=st.floats(0.5, 0.999))
def test_parametric_matches_scipy_norm(
    mean: float, volatility: float, confidence: float
) -> None:
    out = run(
        calculation="parametric",
        mean=mean,
        volatility=volatility,
        confidence=confidence,
    )
    # Standardized first: SciPy's quadrature loses a narrow normal's mass.
    z = scipy.stats.norm.ppf(1 - confidence)
    tail = scipy.stats.norm.expect(lambda x: x, ub=z, conditional=True)
    quantile, tail_mean = mean + volatility * z, mean + volatility * tail
    assert math.isclose(out.value_at_risk, -quantile, rel_tol=1e-10, abs_tol=1e-12)
    assert math.isclose(out.expected_shortfall, -tail_mean, rel_tol=1e-7, abs_tol=1e-9)


@pytest.mark.oracle("risk.value_at_risk")
@given(
    skewness=st.floats(-1.0, 1.0),
    kurtosis=st.floats(0.0, 4.0),
    confidence=st.floats(0.9, 0.999),
)
def test_modified_es_matches_quadrature_of_the_edgeworth_density(
    skewness: float, kurtosis: float, confidence: float
) -> None:
    found = result(
        calculation="cornish_fisher",
        volatility=1.0,
        skewness=skewness,
        excess_kurtosis=kurtosis,
        confidence=confidence,
    )
    if found.warnings:
        reject()
    g = -found.outputs.quantile

    def density(x: float) -> float:
        he3, he4 = x**3 - 3 * x, x**4 - 6 * x**2 + 3
        he6 = x**6 - 15 * x**4 + 45 * x**2 - 15
        shape = 1 + skewness / 6 * he3 + kurtosis / 24 * he4 + skewness**2 / 72 * he6
        return float(scipy.stats.norm.pdf(x)) * shape

    integral, _ = scipy.integrate.quad(lambda x: x * density(x), -np.inf, g)
    expected = -integral / (1 - confidence)
    assert math.isclose(
        found.outputs.expected_shortfall, expected, rel_tol=1e-8, abs_tol=1e-9
    )


@pytest.mark.oracle("risk.value_at_risk")
@given(returns=SMALL_RETURNS, decay=st.floats(0.5, 0.999), confidence=CONFIDENCE)
def test_ewma_matches_pandas_ewm(
    returns: list[float], decay: float, confidence: float
) -> None:
    out = run(calculation="ewma", returns=returns, decay=decay, confidence=confidence)
    squares = pd.Series(np.square(returns))
    variance = squares.ewm(alpha=1 - decay, adjust=False).mean().iloc[-1]
    assert math.isclose(
        out.volatility_forecast, math.sqrt(variance), rel_tol=1e-9, abs_tol=1e-15
    )
    z = scipy.stats.norm.ppf(confidence)
    assert math.isclose(
        out.value_at_risk, z * math.sqrt(variance), rel_tol=1e-9, abs_tol=1e-15
    )


@pytest.mark.oracle("risk.value_at_risk")
@given(returns=RETURNS, confidence=CONFIDENCE)
def test_historical_matches_pandas_quantile(
    returns: list[float], confidence: float
) -> None:
    out = run(calculation="historical", returns=returns, confidence=confidence)
    series = pd.Series(returns)
    quantile = float(series.quantile(1 - confidence, interpolation="linear"))
    tail = series[series <= quantile]
    assert math.isclose(out.value_at_risk, -quantile, rel_tol=1e-12, abs_tol=1e-15)
    assert math.isclose(
        out.expected_shortfall,
        max(-tail.mean(), -quantile),
        rel_tol=1e-12,
        abs_tol=1e-15,
    )


@pytest.mark.parametrize("distribution", ["normal", "student_t"])
def test_monte_carlo_agrees_with_its_distribution(distribution: str) -> None:
    out = run(
        calculation="monte_carlo",
        volatility=0.01,
        distribution=distribution,
        degrees_of_freedom=5,
        simulations=400_000,
        seed=3,
    )
    if distribution == "normal":
        exact = 0.01 * scipy.stats.norm.ppf(0.99)
    else:
        scale = 0.01 * math.sqrt(3 / 5)
        exact = -scipy.stats.t.ppf(0.01, 5) * scale
    assert abs(out.value_at_risk - exact) < 4 * out.value_at_risk_standard_error
    assert out.expected_shortfall_standard_error > 0


def test_monte_carlo_standard_errors_shrink_with_size() -> None:
    small = run(calculation="monte_carlo", volatility=0.01, simulations=10_000)
    large = run(calculation="monte_carlo", volatility=0.01, simulations=1_000_000)
    ratio = small.value_at_risk_standard_error / large.value_at_risk_standard_error
    assert 8 < ratio < 12  # sqrt(100) = 10


def test_the_same_seed_gives_the_same_simulation() -> None:
    first = result(calculation="monte_carlo", volatility=0.02, seed=11)
    second = result(calculation="monte_carlo", volatility=0.02, seed=11)
    other = result(calculation="monte_carlo", volatility=0.02, seed=12)
    assert first.to_json() == second.to_json()
    assert first.outputs.value_at_risk != other.outputs.value_at_risk


def test_amounts_are_the_decimals_times_the_position() -> None:
    out = run(calculation="parametric", volatility=0.01, position_value=2_500_000)
    assert out.value_at_risk_amount == out.value_at_risk * 2_500_000
    assert out.expected_shortfall_amount == out.expected_shortfall * 2_500_000


def test_a_strong_drift_makes_var_a_gain() -> None:
    out = run(calculation="parametric", mean=0.5, volatility=0.01, confidence=0.9)
    assert out.value_at_risk < 0


def test_cornish_fisher_warns_outside_its_domain() -> None:
    found = result(
        calculation="cornish_fisher",
        volatility=0.01,
        skewness=3.0,
        excess_kurtosis=0.0,
        confidence=0.9999,
    )
    codes = {w.code for w in found.warnings}
    assert "outside_expansion_domain" in codes
    assert found.outputs.expected_shortfall >= found.outputs.value_at_risk


def test_cornish_fisher_caps_a_tail_mean_above_its_quantile() -> None:
    found = result(
        calculation="cornish_fisher",
        volatility=0.01,
        skewness=-3.0,
        excess_kurtosis=20.0,
        confidence=0.9999,
    )
    assert "tail_mean_capped" in {w.code for w in found.warnings}
    assert found.outputs.expected_shortfall == found.outputs.value_at_risk


def test_an_output_past_its_bound_raises() -> None:
    assert bounded(1.0, 0.0, 2.0, "loss") == 1.0
    with pytest.raises(DomainError, match="the loss is inf, outside its bounds"):
        bounded(math.inf, 0.0, 2.0, "loss")
    with pytest.raises(DomainError, match="outside its bounds"):
        bounded(3.0, 0.0, 2.0, "loss")


def test_constant_returns_have_no_spread_but_a_var() -> None:
    out = run(calculation="historical", returns=[-0.01] * 5, confidence=0.95)
    assert out.value_at_risk == out.expected_shortfall == 0.01
    assert out.tail_observations == 5


def test_zero_returns_give_zero_ewma_risk() -> None:
    out = run(calculation="ewma", returns=[0.0, 0.0, 0.0])
    assert out.volatility_forecast == out.value_at_risk == 0.0


@pytest.mark.parametrize(
    "inputs",
    [
        {"calculation": "parametric", "volatility": 0.01, "confidence": 0.4},
        {"calculation": "parametric", "volatility": 0.01, "confidence": 1.0},
        {"calculation": "parametric", "volatility": 0.0},
        {"calculation": "historical", "returns": [0.01]},
        {"calculation": "monte_carlo", "volatility": 0.01, "simulations": 100},
        {"calculation": "ewma", "returns": [0.01], "decay": 1.0},
        {"calculation": "parametric", "volatility": 0.01, "horizon": 0.5},
    ],
)
def test_out_of_range_inputs_are_refused(inputs: dict[str, Any]) -> None:
    with pytest.raises(InputError):
        run(**inputs)


def test_monte_carlo_standard_errors_match_the_spread_across_seeds() -> None:
    runs = [
        run(calculation="monte_carlo", volatility=0.01, simulations=10_000, seed=s)
        for s in range(150)
    ]
    for estimate, error in (
        ("value_at_risk", "value_at_risk_standard_error"),
        ("expected_shortfall", "expected_shortfall_standard_error"),
    ):
        spread = float(np.std([getattr(r, estimate) for r in runs], ddof=1))
        reported = float(np.mean([getattr(r, error) for r in runs]))
        assert 0.75 < spread / reported < 1.3
