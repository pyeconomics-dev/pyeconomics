# tests/models/portfolio/test_mean_variance.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``portfolio.mean_variance``: its invariants, its errors, and SciPy as an oracle.

The oracle is ``scipy.optimize.minimize`` (SLSQP) minimizing ``w' Sigma w``
subject to ``sum(w) = 1``, a numerical route to the minimum-variance portfolio
that shares nothing with the closed form. SciPy is imported at the top, so a
missing library fails the suite.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import pytest
import scipy.optimize
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.portfolio import mean_variance

if TYPE_CHECKING:
    from numpy.typing import NDArray


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(mean_variance, inputs).outputs


@st.composite
def assets(draw: st.DrawFn, low: int = 2, high: int = 5) -> dict[str, Any]:
    """Draw well-conditioned assets: expected returns and a covariance matrix."""
    size = draw(st.integers(low, high))
    loadings = np.array(
        [draw(st.lists(st.floats(-1, 1), min_size=2, max_size=2)) for _ in range(size)]
    )
    noise = np.array(draw(st.lists(st.floats(0.2, 1.0), min_size=size, max_size=size)))
    raw = loadings @ loadings.T + np.diag(noise)
    scale = np.sqrt(np.diag(raw))
    correlations = raw / np.outer(scale, scale)
    np.fill_diagonal(correlations, 1.0)
    vols = np.array(draw(st.lists(st.floats(0.05, 0.5), min_size=size, max_size=size)))
    mu = draw(st.lists(st.floats(-0.1, 0.3), min_size=size, max_size=size))
    covariance = correlations * np.outer(vols, vols)
    return {"expected_returns": mu, "covariance": covariance.tolist()}


@st.composite
def fully_invested(draw: st.DrawFn, size: int) -> NDArray[np.float64]:
    """Draw weights that sum to one, long or short."""
    raw = np.array(
        draw(st.lists(st.floats(-2, 2), min_size=size, max_size=size)), dtype=np.float64
    )
    total = float(raw.sum())
    if abs(total) < 0.1:
        raw[0] += 1.0
        total = float(raw.sum())
    return raw / total


@pytest.mark.invariant("portfolio.mean_variance", "weights_sum_to_one")
@given(chosen=assets(), gap=st.floats(0.01, 0.2))
def test_optimized_weights_sum_to_one(chosen: dict[str, Any], gap: float) -> None:
    mvp = run(calculation="minimum_variance", **chosen)
    assert math.isclose(sum(mvp.weights), 1.0, abs_tol=1e-9)
    rate = max(mvp.expected_return - gap, -0.99)
    tangency = run(calculation="tangency", risk_free_rate=rate, **chosen)
    assert math.isclose(sum(tangency.weights), 1.0, abs_tol=1e-9)
    if max(chosen["expected_returns"]) - min(chosen["expected_returns"]) > 1e-3:
        frontier = run(calculation="frontier", points=5, **chosen)
        for row in frontier.weights:
            assert math.isclose(sum(row), 1.0, abs_tol=1e-9)


@pytest.mark.invariant(
    "portfolio.mean_variance", "minimum_variance_has_lowest_variance"
)
@given(data=st.data(), chosen=assets())
def test_no_portfolio_has_less_variance(
    data: st.DataObject, chosen: dict[str, Any]
) -> None:
    mvp = run(calculation="minimum_variance", **chosen)
    sigma = np.asarray(chosen["covariance"])
    weights = data.draw(fully_invested(sigma.shape[0]))
    other = float(weights @ sigma @ weights)
    assert other >= mvp.variance * (1 - 1e-9) - 1e-15
    computed = np.asarray(mvp.weights)
    assert math.isclose(float(computed @ sigma @ computed), mvp.variance, rel_tol=1e-9)


@pytest.mark.invariant(
    "portfolio.mean_variance", "frontier_variance_quadratic_in_return"
)
@given(chosen=assets())
def test_frontier_variance_is_a_parabola(chosen: dict[str, Any]) -> None:
    mu = chosen["expected_returns"]
    if max(mu) - min(mu) < 1e-3:
        return
    frontier = run(calculation="frontier", points=7, **chosen)
    m = np.asarray(frontier.target_returns)
    v = np.asarray(frontier.variances)
    # Through three points the parabola is fixed; every point must lie on it.
    coefficients = np.polyfit(m[[0, 3, 6]], v[[0, 3, 6]], 2)
    assert coefficients[0] > 0
    assert np.allclose(np.polyval(coefficients, m), v, rtol=1e-7, atol=1e-12)
    vertex = -coefficients[1] / (2 * coefficients[0])
    assert math.isclose(
        vertex, frontier.minimum_variance_return, rel_tol=1e-6, abs_tol=1e-8
    )
    assert math.isclose(v[0], frontier.minimum_variance_volatility**2, rel_tol=1e-9)
    sigma = np.asarray(chosen["covariance"])
    for target, variance, row in zip(m, v, frontier.weights, strict=True):
        w = np.asarray(row)
        assert math.isclose(
            float(w @ np.asarray(mu)), target, rel_tol=1e-9, abs_tol=1e-12
        )
        assert math.isclose(float(w @ sigma @ w), variance, rel_tol=1e-8)


@pytest.mark.invariant("portfolio.mean_variance", "tangency_maximizes_sharpe")
@given(data=st.data(), chosen=assets(), gap=st.floats(0.01, 0.5))
def test_no_portfolio_beats_the_tangency_sharpe(
    data: st.DataObject, chosen: dict[str, Any], gap: float
) -> None:
    mvp = run(calculation="minimum_variance", **chosen)
    rate = mvp.expected_return - gap
    assume(rate >= -0.99)
    found = run(calculation="tangency", risk_free_rate=rate, **chosen)
    assert math.isclose(
        (found.expected_return - rate) / found.volatility,
        found.capital_market_line_slope,
        rel_tol=1e-9,
    )
    sigma = np.asarray(chosen["covariance"])
    mu = np.asarray(chosen["expected_returns"])
    weights = data.draw(fully_invested(mu.size))
    sharpe = float(weights @ mu - rate) / math.sqrt(float(weights @ sigma @ weights))
    assert sharpe <= found.capital_market_line_slope * (1 + 1e-9) + 1e-12


@pytest.mark.oracle("portfolio.mean_variance")
@settings(max_examples=40)
@given(chosen=assets())
def test_minimum_variance_matches_scipy(chosen: dict[str, Any]) -> None:
    sigma = np.asarray(chosen["covariance"], dtype=np.float64)
    size = sigma.shape[0]

    def variance(w: NDArray[np.float64]) -> float:
        return float(w @ sigma @ w)

    def gradient(w: NDArray[np.float64]) -> NDArray[np.float64]:
        return np.asarray(2 * sigma @ w, dtype=np.float64)

    solved = scipy.optimize.minimize(
        variance,
        np.full(size, 1.0 / size),
        jac=gradient,
        method="SLSQP",
        constraints=scipy.optimize.LinearConstraint(np.ones((1, size)), 1.0, 1.0),
        options={"ftol": 1e-16, "maxiter": 500},
    )
    assert solved.success
    mvp = run(calculation="minimum_variance", **chosen)
    assert np.allclose(mvp.weights, solved.x, atol=1e-5)
    assert math.isclose(mvp.variance, float(solved.fun), rel_tol=1e-8)


# --- inputs and errors ---------------------------------------------------------

TWO = {"expected_returns": [0.1, 0.06]}


def test_volatilities_and_correlations_equal_the_covariance() -> None:
    by_parts = run(
        calculation="minimum_variance",
        volatilities=[0.2, 0.1],
        correlations=[[1, 0.3], [0.3, 1]],
        **TWO,
    )
    whole = run(
        calculation="minimum_variance", covariance=[[0.04, 0.006], [0.006, 0.01]], **TWO
    )
    assert np.allclose(by_parts.weights, whole.weights, rtol=1e-12)


def test_a_matrix_may_be_a_numpy_array_or_a_dataframe() -> None:
    matrix = np.array([[0.04, 0.006], [0.006, 0.01]])
    expected = run(calculation="minimum_variance", covariance=matrix.tolist(), **TWO)
    for given_matrix in (matrix, pd.DataFrame(matrix)):
        found = run(calculation="minimum_variance", covariance=given_matrix, **TWO)
        assert found.weights == expected.weights


def test_an_oversized_matrix_is_refused_before_conversion() -> None:
    with pytest.raises(InputError, match="at most 100 x 100"):
        run(calculation="minimum_variance", covariance=np.eye(101), **TWO)


@pytest.mark.parametrize(
    ("extra", "match"),
    [
        (
            {"covariance": [[0.04, 0.0], [0.0, 0.01]], "volatilities": [0.2, 0.1]},
            "not both",
        ),
        ({}, "give a covariance matrix"),
        ({"volatilities": [0.2]}, "give a covariance matrix"),
        ({"volatilities": [0.2], "correlations": [[1.0]]}, "one volatility per asset"),
        ({"covariance": [[0.04, 0.0]]}, "2 x 2"),
        ({"volatilities": [0.2, 0.1], "correlations": [[1.0, 0.0]]}, "2 x 2"),
    ],
)
def test_the_risk_inputs_must_fit_the_assets(extra: dict[str, Any], match: str) -> None:
    with pytest.raises(InputError, match=match):
        run(calculation="minimum_variance", **TWO, **extra)


def test_weights_must_match_the_assets() -> None:
    with pytest.raises(InputError, match="one weight per asset"):
        run(
            calculation="portfolio",
            weights=[1.0],
            covariance=[[0.04, 0], [0, 0.01]],
            **TWO,
        )


def test_the_frontier_range_must_be_ordered() -> None:
    with pytest.raises(InputError, match="below max_return"):
        run(
            calculation="frontier",
            min_return=0.1,
            max_return=0.05,
            covariance=[[0.04, 0], [0, 0.01]],
            **TWO,
        )


@pytest.mark.parametrize(
    ("risk", "match"),
    [
        ({"covariance": [[0.04, 0.01], [0.0, 0.01]]}, "not symmetric"),
        ({"covariance": [[0.01, 0.01], [0.01, 0.01]]}, "not positive definite"),
        ({"covariance": [[0.01, 0.02], [0.02, 0.01]]}, "not positive definite"),
        (
            {"volatilities": [0.2, 0.1], "correlations": [[0.9, 0.0], [0.0, 1.0]]},
            "diagonal",
        ),
        (
            {"volatilities": [0.2, 0.1], "correlations": [[1.0, 0.5], [0.4, 1.0]]},
            "not symmetric",
        ),
    ],
)
def test_a_matrix_that_is_not_a_covariance_is_a_domain_error(
    risk: dict[str, Any], match: str
) -> None:
    with pytest.raises(DomainError, match=match):
        run(calculation="minimum_variance", **TWO, **risk)


def test_a_frontier_of_equal_returns_is_one_point() -> None:
    with pytest.raises(DomainError, match="expected returns are equal"):
        run(
            calculation="frontier",
            expected_returns=[0.05, 0.05],
            covariance=[[0.04, 0], [0, 0.01]],
        )


def test_an_empty_frontier_range_is_a_domain_error() -> None:
    with pytest.raises(DomainError, match="is empty"):
        run(
            calculation="frontier",
            min_return=0.5,
            covariance=[[0.04, 0], [0, 0.01]],
            **TWO,
        )


def test_the_default_range_when_the_minimum_variance_return_is_highest() -> None:
    # Highly correlated assets: the minimum-variance portfolio shorts the risky
    # asset with the lower return and earns more than either asset.
    found = run(
        calculation="frontier",
        points=3,
        expected_returns=[0.05, 0.1],
        volatilities=[0.3, 0.1],
        correlations=[[1.0, 0.9], [0.9, 1.0]],
    )
    assert found.minimum_variance_return > 0.1
    assert math.isclose(
        found.target_returns[-1], found.minimum_variance_return + 0.05, rel_tol=1e-12
    )


def test_tangency_needs_a_rate_below_the_minimum_variance_return() -> None:
    with pytest.raises(DomainError, match="not below"):
        run(
            calculation="tangency",
            risk_free_rate=0.5,
            covariance=[[0.04, 0], [0, 0.01]],
            **TWO,
        )


def test_tangency_with_equal_returns_is_the_minimum_variance_portfolio() -> None:
    risk = {"expected_returns": [0.05, 0.05], "covariance": [[0.04, 0.0], [0.0, 0.01]]}
    tangency = run(calculation="tangency", risk_free_rate=0.01, **risk)
    mvp = run(calculation="minimum_variance", **risk)
    assert np.allclose(tangency.weights, mvp.weights, rtol=1e-12)


def test_weights_of_a_near_singular_matrix_out_of_bounds_are_a_domain_error() -> None:
    # Two assets with correlation 1 - 1e-11 and different returns: the
    # tangency portfolio's weights are enormous.
    near = 1 - 1e-11
    with pytest.raises(DomainError, match="outside its bounds"):
        run(
            calculation="tangency",
            risk_free_rate=0.0,
            expected_returns=[0.1, 0.2],
            volatilities=[0.2, 0.2],
            correlations=[[1.0, near], [near, 1.0]],
        )


def test_portfolio_risk_of_weights_that_do_not_sum_to_one() -> None:
    found = run(
        calculation="portfolio",
        weights=[1.0, -1.0],
        covariance=[[0.04, 0.006], [0.006, 0.01]],
        **TWO,
    )
    assert found.weight_sum == 0.0
    assert math.isclose(found.variance, 0.04 + 0.01 - 0.012, rel_tol=1e-12)
    assert math.isclose(found.expected_return, 0.04, rel_tol=1e-12)


@pytest.mark.parametrize(
    "risk",
    [
        {"covariance": [[1e-310, 0.0], [0.0, 1e-310]]},
        {"volatilities": [1e-160, 1e-160], "correlations": [[1.0, 0.0], [0.0, 1.0]]},
        {"covariance": [[1e10 * 1e-8, 0.0], [0.0, 1e2]]},
    ],
)
def test_tiny_or_large_variances_solve_at_any_scale(risk: dict[str, Any]) -> None:
    # Review regression: solving the unscaled matrix overflowed and reported a
    # well-conditioned matrix as close to singular.
    found = run(calculation="minimum_variance", **TWO, **risk)
    assert np.allclose(found.weights, [0.5, 0.5], rtol=1e-12)


def test_a_frontier_of_tiny_but_distinct_returns() -> None:
    found = run(
        calculation="frontier",
        points=3,
        expected_returns=[2e-310, 0.0, 1e-310],
        covariance=[[0.04, 0, 0], [0, 0.04, 0], [0, 0, 0.04]],
    )
    assert math.isclose(found.variances[0], 0.04 / 3, rel_tol=1e-12)
