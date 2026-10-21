# tests/models/portfolio/test_black_litterman.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``portfolio.black_litterman``: invariants, errors and an independent recomputation.

The oracle is the textbook route the model does not take: Theil's mixed
estimation, ``mu = [(tau Sigma)^-1 + P' Omega^-1 P]^-1 [(tau Sigma)^-1 Pi + P'
Omega^-1 Q]`` and ``M = [(tau Sigma)^-1 + P' Omega^-1 P]^-1`` (He and Litterman,
eqs. 8-9), with the weights from NumPy solves against Sigma and Sigma + M. The
model instead updates the equilibrium by the views' surprise, which also holds
for certain views, and never inverts Sigma for the weights.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.portfolio import black_litterman


@st.composite
def priors(draw: st.DrawFn, low: int = 2, high: int = 7) -> dict[str, Any]:
    """Draw a well-conditioned covariance and market weights."""
    size = draw(st.integers(low, high))
    seed = draw(st.integers(0, 2**32 - 1))
    rng = np.random.default_rng(seed)
    loadings = rng.normal(size=(size, 2))
    raw = loadings @ loadings.T + np.diag(rng.uniform(0.2, 1.0, size))
    scale = np.sqrt(np.diag(raw))
    vols = rng.uniform(0.05, 0.35, size)
    covariance = raw / np.outer(scale, scale) * np.outer(vols, vols)
    weights = rng.dirichlet(np.ones(size))
    return {
        "covariance": covariance.tolist(),
        "market_weights": weights.tolist(),
        "risk_aversion": draw(st.floats(0.5, 6.0)),
        "tau": draw(st.floats(0.01, 1.0)),
    }


@st.composite
def views(draw: st.DrawFn, size: int, *, most: int | None = None) -> dict[str, Any]:
    """Draw linearly independent views on ``size`` assets."""
    count = draw(st.integers(1, most or size))
    seed = draw(st.integers(0, 2**32 - 1))
    rng = np.random.default_rng(seed)
    picks = rng.normal(size=(count, size))
    returns = rng.normal(0.02, 0.05, size=count)
    return {"picks": picks.tolist(), "view_returns": returns.tolist()}


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the model's outputs
    return run_model(black_litterman, inputs).outputs


def mixed_estimation(
    inputs: dict[str, Any], omega: np.ndarray
) -> dict[str, np.ndarray]:
    """He and Litterman's eqs. (8)-(9) by matrix inverses, and the two weights."""
    sigma = np.asarray(inputs["covariance"])
    w = np.asarray(inputs["market_weights"])
    delta, tau = inputs["risk_aversion"], inputs["tau"]
    p = np.asarray(inputs["picks"])
    q = np.asarray(inputs["view_returns"])
    pi = delta * sigma @ w
    prior = np.linalg.inv(tau * sigma)
    precision = prior + p.T @ np.linalg.inv(omega) @ p
    m = np.linalg.inv(precision)
    mu = m @ (prior @ pi + p.T @ np.linalg.inv(omega) @ q)
    return {
        "mu": mu,
        "posterior": sigma + m,
        "weights": np.linalg.solve(delta * sigma, mu),
        "posterior_weights": np.linalg.solve(delta * (sigma + m), mu),
    }


@pytest.mark.invariant("portfolio.black_litterman", "no_views_return_equilibrium")
@given(prior=priors())
def test_no_views_return_the_equilibrium(prior: dict[str, Any]) -> None:
    outputs = run(**prior)
    np.testing.assert_allclose(
        outputs.posterior_returns, outputs.equilibrium_returns, rtol=1e-12, atol=0
    )
    sigma = np.asarray(prior["covariance"])
    np.testing.assert_allclose(
        outputs.posterior_covariance, (1 + prior["tau"]) * sigma, rtol=1e-12, atol=1e-16
    )
    assert outputs.view_variances == ()


@pytest.mark.invariant("portfolio.black_litterman", "certain_view_holds_exactly")
@settings(max_examples=80)
@given(data=st.data(), prior=priors())
def test_a_certain_view_holds_exactly(
    data: st.DataObject, prior: dict[str, Any]
) -> None:
    size = len(prior["market_weights"])
    chosen = data.draw(views(size))
    count = len(chosen["picks"])
    outputs = run(**prior, **chosen, confidence="idzorek", confidences=[1.0] * count)
    held = np.asarray(chosen["picks"]) @ np.asarray(outputs.posterior_returns)
    np.testing.assert_allclose(held, chosen["view_returns"], rtol=1e-9, atol=1e-12)
    assert outputs.view_variances == (0.0,) * count


@pytest.mark.invariant(
    "portfolio.black_litterman", "no_views_weights_equal_market_weights"
)
@given(prior=priors())
def test_no_views_give_the_market_weights(prior: dict[str, Any]) -> None:
    outputs = run(**prior)
    assert outputs.weights == tuple(prior["market_weights"])
    np.testing.assert_allclose(
        outputs.posterior_weights,
        np.asarray(prior["market_weights"]) / (1 + prior["tau"]),
        rtol=1e-9,
        atol=1e-12,
    )


@pytest.mark.oracle("portfolio.black_litterman")
@settings(max_examples=60)
@given(data=st.data(), prior=priors(), idzorek=st.booleans())
def test_mixed_estimation_agrees(
    data: st.DataObject, prior: dict[str, Any], *, idzorek: bool
) -> None:
    size = len(prior["market_weights"])
    chosen = data.draw(views(size))
    inputs = {**prior, **chosen}
    p = np.asarray(chosen["picks"])
    base = np.diag(p @ (prior["tau"] * np.asarray(prior["covariance"])) @ p.T)
    if idzorek:
        levels = data.draw(
            st.lists(st.floats(0.05, 0.95), min_size=len(p), max_size=len(p))
        )
        inputs.update(confidence="idzorek", confidences=levels)
        omega = np.diag(base * (1 - np.asarray(levels)) / np.asarray(levels))
    else:
        omega = np.diag(base)
    outputs = run(**inputs)
    expected = mixed_estimation(inputs, omega)
    np.testing.assert_allclose(
        outputs.posterior_returns, expected["mu"], rtol=1e-8, atol=1e-12
    )
    np.testing.assert_allclose(
        outputs.posterior_covariance, expected["posterior"], rtol=1e-8, atol=1e-14
    )
    np.testing.assert_allclose(
        outputs.weights, expected["weights"], rtol=1e-7, atol=1e-10
    )
    np.testing.assert_allclose(
        outputs.posterior_weights, expected["posterior_weights"], rtol=1e-7, atol=1e-10
    )
    np.testing.assert_allclose(outputs.view_variances, np.diag(omega), rtol=1e-12)


@settings(max_examples=40)
@given(data=st.data(), prior=priors(), level=st.floats(0.05, 1.0))
def test_idzorek_confidence_moves_one_view_a_share_of_the_way(
    data: st.DataObject, prior: dict[str, Any], level: float
) -> None:
    size = len(prior["market_weights"])
    chosen = data.draw(views(size, most=1))
    certain = run(**prior, **chosen, confidence="idzorek", confidences=[1.0])
    partial = run(**prior, **chosen, confidence="idzorek", confidences=[level])
    market = np.asarray(prior["market_weights"])
    full_tilt = np.asarray(certain.weights) - market
    np.testing.assert_allclose(
        np.asarray(partial.weights) - market, level * full_tilt, rtol=1e-8, atol=1e-12
    )


def test_a_returns_window_gives_the_sample_covariance() -> None:
    rng = np.random.default_rng(3)
    window = rng.normal(0.01, 0.05, size=(60, 3))
    covariance = np.cov(window, rowvar=False, ddof=1)
    weights = [0.5, 0.3, 0.2]
    from_window = run(returns=window.tolist(), market_weights=weights)
    from_matrix = run(covariance=covariance.tolist(), market_weights=weights)
    np.testing.assert_allclose(
        from_window.equilibrium_returns, from_matrix.equilibrium_returns, rtol=1e-12
    )


def test_a_view_is_the_same_at_any_scale() -> None:
    prior = {
        "volatilities": [0.15, 0.2, 0.25],
        "correlations": [[1.0, 0.4, 0.2], [0.4, 1.0, 0.3], [0.2, 0.3, 1.0]],
        "market_weights": [0.5, 0.3, 0.2],
    }
    one = run(**prior, picks=[[1.0, -1.0, 0.0]], view_returns=[0.01])
    ten = run(**prior, picks=[[10.0, -10.0, 0.0]], view_returns=[0.1])
    np.testing.assert_allclose(one.posterior_returns, ten.posterior_returns, rtol=1e-12)
    np.testing.assert_allclose(one.weights, ten.weights, rtol=1e-12)
    assert ten.view_variances[0] == pytest.approx(100 * one.view_variances[0])


def test_two_certain_views_on_one_portfolio_raise_domain_error() -> None:
    with pytest.raises(DomainError, match="singular"):
        run(
            volatilities=[0.15, 0.2],
            correlations=[[1.0, 0.3], [0.3, 1.0]],
            market_weights=[0.6, 0.4],
            picks=[[1.0, -1.0], [2.0, -2.0]],
            view_returns=[0.01, 0.03],
            confidence="idzorek",
            confidences=[1.0, 1.0],
        )


def test_a_covariance_that_is_not_positive_definite_raises_domain_error() -> None:
    with pytest.raises(DomainError, match="positive definite"):
        run(
            volatilities=[0.15, 0.2],
            correlations=[[1.0, 1.0], [1.0, 1.0]],
            market_weights=[0.6, 0.4],
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"view_returns": [0.01]}, "give picks and view_returns together"),
        (
            {"picks": [[1.0, 0.0]], "view_returns": [0.01, 0.02]},
            "one view return per view",
        ),
        ({"picks": [[1.0, 0.0, 0.0]], "view_returns": [0.01]}, "one weight per asset"),
        ({"picks": [[0.0, 0.0]], "view_returns": [0.01]}, "all zero"),
        (
            {"picks": [[1.0, 0.0]], "view_returns": [0.01], "confidences": [0.5]},
            "confidences go with confidence='idzorek'",
        ),
        (
            {"picks": [[1.0, 0.0]], "view_returns": [0.01], "confidence": "idzorek"},
            "one confidence per view",
        ),
        ({"market_weights": [0.0, 0.0]}, "needs some weight"),
        ({"covariance": [[0.04, 0.0], [0.0, 0.04]]}, "give one of"),
    ],
)
def test_inconsistent_inputs_are_refused(change: dict[str, Any], message: str) -> None:
    inputs = {
        "volatilities": [0.15, 0.2],
        "correlations": [[1.0, 0.3], [0.3, 1.0]],
        "market_weights": [0.6, 0.4],
        **change,
    }
    with pytest.raises(InputError, match=message):
        run(**inputs)
