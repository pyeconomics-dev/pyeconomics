# tests/models/portfolio/test_risk_based_allocation.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``portfolio.risk_based_allocation``: invariants, errors and independent oracles.

Two oracles share nothing with the model: SciPy's L-BFGS-B minimizing Maillard,
Roncalli and Teiletche's log-barrier objective for the equal-risk-contribution
weights (the model uses Newton's method), and a transcription of López de
Prado's (2016) Appendix A.3 code (pandas, ``scipy.cluster.hierarchy.linkage`` on
the distance matrix itself, his quasi-diagonalization and recursive bisection)
for hierarchical risk parity.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
import pandas as pd
import pytest
import scipy.cluster.hierarchy as sch
import scipy.optimize
from hypothesis import given, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.portfolio import risk_based_allocation

CALCULATIONS = (
    "inverse_volatility",
    "equal_risk_contribution",
    "hierarchical_risk_parity",
)


@st.composite
def risks(draw: st.DrawFn, low: int = 1, high: int = 10) -> dict[str, Any]:
    """Draw a positive definite covariance matrix."""
    size = draw(st.integers(low, high))
    rng = np.random.default_rng(draw(st.integers(0, 2**32 - 1)))
    loadings = rng.normal(size=(size, 3))
    raw = loadings @ loadings.T + np.diag(rng.uniform(0.1, 1.0, size))
    scale = np.sqrt(np.diag(raw))
    vols = rng.uniform(0.02, 0.6, size)
    return {
        "covariance": (raw / np.outer(scale, scale) * np.outer(vols, vols)).tolist()
    }


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(risk_based_allocation, inputs).outputs


@pytest.mark.invariant("portfolio.risk_based_allocation", "weights_sum_to_one")
@given(chosen=risks(), calculation=st.sampled_from(CALCULATIONS))
def test_the_weights_sum_to_one(chosen: dict[str, Any], calculation: str) -> None:
    outputs = run(calculation=calculation, **chosen)
    assert math.fsum(outputs.weights) == pytest.approx(1.0, abs=1e-12)
    assert math.fsum(outputs.risk_contributions) == pytest.approx(
        outputs.volatility, rel=1e-9
    )


@pytest.mark.invariant("portfolio.risk_based_allocation", "erc_contributions_are_equal")
@given(chosen=risks())
def test_every_risk_contribution_is_equal(chosen: dict[str, Any]) -> None:
    outputs = run(calculation="equal_risk_contribution", **chosen)
    share = outputs.volatility / len(outputs.weights)
    np.testing.assert_allclose(outputs.risk_contributions, share, rtol=1e-10)


@pytest.mark.invariant(
    "portfolio.risk_based_allocation",
    "inverse_volatility_equals_erc_for_uncorrelated_assets",
)
@given(
    vols=st.lists(
        st.one_of(st.floats(0.01, 1.0), st.floats(1e-5, 10.0)), min_size=1, max_size=12
    )
)
def test_uncorrelated_assets_give_inverse_volatility(vols: list[float]) -> None:
    inputs = {"covariance": np.diag(np.square(vols)).tolist()}
    erc = run(calculation="equal_risk_contribution", **inputs)
    inverse = run(calculation="inverse_volatility", **inputs)
    np.testing.assert_allclose(erc.weights, inverse.weights, rtol=1e-10, atol=1e-15)


@pytest.mark.invariant("portfolio.risk_based_allocation", "hrp_weights_are_positive")
@given(chosen=risks(), spread=st.floats(-12.0, 1.0))
def test_every_hrp_weight_is_positive(chosen: dict[str, Any], spread: float) -> None:
    # One asset's volatility scaled by 10^spread: tiny variances must keep a share.
    covariance = np.asarray(chosen["covariance"])
    factor = np.ones(len(covariance))
    factor[0] = 10.0**spread
    chosen = {"covariance": (covariance * np.outer(factor, factor)).tolist()}
    outputs = run(calculation="hierarchical_risk_parity", **chosen)
    assert all(w > 0 for w in outputs.weights)
    assert sorted(outputs.order) == list(range(len(outputs.weights)))


def log_barrier_weights(sigma: np.ndarray) -> np.ndarray:
    """Minimize 1/2 y' Sigma y - (1/N) sum log y by L-BFGS-B, then normalize."""
    size = len(sigma)
    scaled = sigma / np.max(np.abs(sigma))

    def objective(y: np.ndarray) -> tuple[float, np.ndarray]:
        marginal = scaled @ y
        value = 0.5 * float(y @ marginal) - float(np.sum(np.log(y))) / size
        return value, marginal - 1.0 / (size * y)

    start = 1.0 / np.sqrt(np.diag(scaled))
    found = scipy.optimize.minimize(
        objective,
        start / math.sqrt(float(start @ scaled @ start)),
        jac=True,
        method="L-BFGS-B",
        bounds=[(1e-12, None)] * size,
        options={"ftol": 1e-15, "gtol": 1e-12, "maxiter": 10_000},
    )
    return found.x / found.x.sum()


@pytest.mark.oracle("portfolio.risk_based_allocation")
@settings(max_examples=60)
@given(chosen=risks(low=2))
def test_scipy_minimizes_the_same_log_barrier(chosen: dict[str, Any]) -> None:
    outputs = run(calculation="equal_risk_contribution", **chosen)
    expected = log_barrier_weights(np.asarray(chosen["covariance"]))
    np.testing.assert_allclose(outputs.weights, expected, rtol=1e-5, atol=1e-8)


def lopez_de_prado(cov: pd.DataFrame) -> tuple[pd.Series, list[int]]:
    """The paper's Appendix A.3 functions, ported to Python 3 and pandas 2."""
    matrix = cov.to_numpy()
    vols = np.sqrt(np.diag(matrix))
    corr = np.clip(matrix / np.outer(vols, vols), -1.0, 1.0)
    dist = ((1 - corr) / 2.0) ** 0.5
    # As the paper's code does: linkage on the rows of the distance matrix,
    # which SciPy warns looks like an uncondensed distance matrix.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", sch.ClusterWarning)
        link = sch.linkage(dist, "single")
    link = link.astype(int)
    sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
    items = link[-1, 3]
    while sort_ix.max() >= items:
        sort_ix.index = pd.RangeIndex(0, sort_ix.shape[0] * 2, 2)
        clusters = sort_ix[sort_ix >= items]
        i, j = clusters.index, clusters.to_numpy() - items
        sort_ix[i] = link[j, 0]
        sort_ix = pd.concat([sort_ix, pd.Series(link[j, 1], index=i + 1)]).sort_index()
        sort_ix.index = pd.RangeIndex(sort_ix.shape[0])
    order = sort_ix.tolist()
    labels = list(cov.index)
    ordered = [labels[k] for k in order]
    weights = pd.Series(1.0, index=ordered)
    pending = [ordered]
    while pending:
        pending = [
            c[a:b]
            for c in pending
            for a, b in ((0, len(c) // 2), (len(c) // 2, len(c)))
            if len(c) > 1
        ]
        for k in range(0, len(pending), 2):
            left, right = pending[k], pending[k + 1]
            variances = []
            for part in (left, right):
                block = cov.loc[part, part].to_numpy()
                ivp = 1.0 / np.diag(block)
                ivp /= ivp.sum()
                variances.append(float(ivp @ block @ ivp))
            alpha = 1 - variances[0] / (variances[0] + variances[1])
            weights[left] *= alpha
            weights[right] *= 1 - alpha
    return weights.sort_index(), order


@pytest.mark.oracle("portfolio.risk_based_allocation")
@settings(max_examples=60)
@given(chosen=risks(low=2, high=12))
def test_lopez_de_prados_code_agrees(chosen: dict[str, Any]) -> None:
    outputs = run(calculation="hierarchical_risk_parity", **chosen)
    covariance = np.asarray(chosen["covariance"])
    frame = pd.DataFrame(covariance)
    weights, order = lopez_de_prado(frame)
    np.testing.assert_allclose(outputs.weights, weights.to_numpy(), rtol=1e-10)
    assert list(outputs.order) == order


@pytest.mark.oracle("portfolio.risk_based_allocation")
@given(chosen=risks(low=2, high=12))
def test_the_order_is_scipys_leaf_order(chosen: dict[str, Any]) -> None:
    outputs = run(calculation="hierarchical_risk_parity", **chosen)
    covariance = np.asarray(chosen["covariance"])
    vols = np.sqrt(np.diag(covariance))
    corr = np.clip(covariance / np.outer(vols, vols), -1, 1)
    distance = np.sqrt(np.clip((1 - corr) / 2, 0, None))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", sch.ClusterWarning)
        link = sch.linkage(distance, "single")
    assert list(outputs.order) == sch.leaves_list(link).tolist()


def test_inverse_volatility_is_proportional_to_one_over_sigma() -> None:
    outputs = run(
        calculation="inverse_volatility",
        volatilities=[0.1, 0.2, 0.4],
        correlations=[[1.0, 0.3, 0.1], [0.3, 1.0, 0.2], [0.1, 0.2, 1.0]],
    )
    np.testing.assert_allclose(outputs.weights, [4 / 7, 2 / 7, 1 / 7], rtol=1e-12)


def test_a_returns_window_gives_the_sample_covariance() -> None:
    rng = np.random.default_rng(2)
    window = rng.normal(0.01, 0.05, size=(120, 4))
    covariance = np.cov(window, rowvar=False, ddof=1)
    for calculation in CALCULATIONS:
        from_window = run(calculation=calculation, returns=pd.DataFrame(window))
        from_matrix = run(calculation=calculation, covariance=covariance.tolist())
        np.testing.assert_allclose(from_window.weights, from_matrix.weights, rtol=1e-10)


def test_a_duplicated_asset_gives_a_singular_matrix_risk_parity_accepts() -> None:
    rng = np.random.default_rng(4)
    window = rng.normal(0.01, 0.05, size=(60, 4))
    window[:, 3] = window[:, 0]
    outputs = run(calculation="equal_risk_contribution", returns=window.tolist())
    share = outputs.volatility / 4
    np.testing.assert_allclose(outputs.risk_contributions, share, rtol=1e-10)


def test_a_single_asset_takes_all_the_weight() -> None:
    for calculation in CALCULATIONS:
        outputs = run(calculation=calculation, covariance=[[0.04]])
        assert outputs.weights == (1.0,)
        assert outputs.volatility == pytest.approx(0.2)


@pytest.mark.parametrize(
    "calculation", ["equal_risk_contribution", "hierarchical_risk_parity"]
)
def test_a_riskless_long_portfolio_raises_domain_error(calculation: str) -> None:
    with pytest.raises(DomainError, match=r"no (risk|variance)"):
        run(
            calculation=calculation,
            volatilities=[0.1, 0.1],
            correlations=[[1.0, -1.0], [-1.0, 1.0]],
        )


def test_a_matrix_with_a_negative_eigenvalue_raises_domain_error() -> None:
    with pytest.raises(DomainError, match="semidefinite"):
        run(
            calculation="equal_risk_contribution",
            volatilities=[0.1, 0.2, 0.3],
            correlations=[[1.0, 0.9, -0.9], [0.9, 1.0, 0.9], [-0.9, 0.9, 1.0]],
        )


def test_an_asset_without_variance_raises_domain_error() -> None:
    with pytest.raises(DomainError, match="no variance"):
        run(calculation="inverse_volatility", returns=[[0.01, 0.02], [0.01, -0.01]])


@pytest.mark.parametrize(
    ("inputs", "message"),
    [
        ({"volatilities": [0.1, 0.2]}, "volatilities and correlations together"),
        (
            {"covariance": [[0.01, 0.0], [0.0, 0.04]], "volatilities": [0.1, 0.2]},
            "give one of",
        ),
        ({"returns": [[0.01, 0.02], [0.03]]}, "one value per asset"),
        (
            {"covariance": [[0.01, 0.0, 0.0], [0.0, 0.04, 0.0]]},
            r"must be (2 x 2|3 x 3)",
        ),
    ],
)
def test_inconsistent_inputs_are_refused(inputs: dict[str, Any], message: str) -> None:
    with pytest.raises(InputError, match=message):
        run(calculation="inverse_volatility", **inputs)


@pytest.mark.parametrize("small", [1e-4, 1e-8, 1e-12])
def test_hrp_keeps_a_tiny_variance_assets_weight(small: float) -> None:
    outputs = run(
        calculation="hierarchical_risk_parity",
        volatilities=[1.0, small],
        correlations=[[1.0, 0.0], [0.0, 1.0]],
    )
    # Inverse-variance split of two uncorrelated assets.
    expected = small * small / (1 + small * small)
    assert outputs.weights[0] == pytest.approx(expected, rel=1e-12)
    assert outputs.weights[0] > 0


@pytest.mark.parametrize("calculation", CALCULATIONS)
def test_subnormal_variances_neither_overflow_nor_lose_the_weights(
    calculation: str,
) -> None:
    outputs = run(calculation=calculation, covariance=[[1e-310, 0.0], [0.0, 4e-310]])
    expected = (
        [2 / 3, 1 / 3] if calculation != "hierarchical_risk_parity" else [0.8, 0.2]
    )
    np.testing.assert_allclose(outputs.weights, expected, rtol=1e-12)
    assert outputs.volatility > 0


@pytest.mark.parametrize("rho", [-0.999999, -0.99999999])
def test_risk_parity_solves_a_nearly_riskless_pair(rho: float) -> None:
    outputs = run(
        calculation="equal_risk_contribution",
        volatilities=[0.2, 0.2],
        correlations=[[1.0, rho], [rho, 1.0]],
    )
    np.testing.assert_allclose(outputs.weights, [0.5, 0.5], rtol=1e-12)
