# tests/models/asset_pricing/test_factor_model_tests.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``asset_pricing.factor_model_tests``: invariants, errors and two oracles.

The oracles share no code with the model: SciPy's F distribution
(``scipy.stats.f.sf``) for the p-value, and a recomputation that fits every
time-series and cross-sectional regression with statsmodels' OLS, period by
period, and applies Shanken's correction in its own subtractive form,
``(1 + c)(V_FM - Sigma_F*/T) + Sigma_F*/T``, where the model builds it from the
residuals. Both libraries are imported at the top, so a missing one fails.
"""

from __future__ import annotations

import importlib
from typing import Any

import numpy as np
import pandas as pd
import pytest
import scipy.stats
import statsmodels.api as sm
from hypothesis import given, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.asset_pricing import factor_model_tests


def panel(
    periods: int, assets: int, factors: int, seed: int, noise: float = 0.02
) -> dict[str, Any]:
    """Return test-asset and factor returns with a mild pricing error."""
    rng = np.random.default_rng(seed)
    f = rng.normal(0.006, 0.045, size=(periods, factors))
    betas = rng.uniform(0.2, 1.6, size=(assets, factors))
    alphas = rng.normal(0.0, 0.002, size=assets)
    rf = rng.uniform(0.0, 0.004, size=periods)
    r = (
        rf[:, None]
        + alphas
        + f @ betas.T
        + rng.normal(0.0, noise, size=(periods, assets))
    )
    return {"returns": r.tolist(), "factors": f.tolist(), "risk_free": rf.tolist()}


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(factor_model_tests, inputs).outputs


def projected_out(values: np.ndarray, factors: np.ndarray) -> np.ndarray:
    """Return the columns of ``values`` less their fit on a constant and the factors."""
    design = np.column_stack([np.ones(len(factors)), factors])
    fit, *_ = np.linalg.lstsq(design, values, rcond=None)
    remainder: np.ndarray = values - design @ fit
    return remainder


@pytest.mark.invariant(
    "asset_pricing.factor_model_tests", "grs_zero_when_alphas_are_zero"
)
@settings(max_examples=60)
@given(
    periods=st.integers(12, 150),
    assets=st.integers(1, 5),
    factors=st.integers(1, 3),
    seed=st.integers(0, 2**32 - 1),
)
def test_grs_is_zero_when_every_alpha_is(
    periods: int, assets: int, factors: int, seed: int
) -> None:
    rng = np.random.default_rng(seed)
    f = rng.normal(0.0, 0.05, size=(periods, factors))
    betas = rng.uniform(-1.0, 2.0, size=(assets, factors))
    errors = projected_out(rng.normal(0.0, 0.02, size=(periods, assets)), f)
    returns = f @ betas.T + errors
    outputs = run(calculation="grs", returns=returns.tolist(), factors=f.tolist())
    assert outputs.statistic == pytest.approx(0.0, abs=1e-12)
    assert outputs.p_value == pytest.approx(1.0, abs=1e-9)
    np.testing.assert_allclose(outputs.alphas, 0.0, atol=1e-14)


@pytest.mark.invariant(
    "asset_pricing.factor_model_tests", "fama_macbeth_recovers_premia_on_exact_data"
)
@settings(max_examples=60)
@given(
    periods=st.integers(5, 120),
    factors=st.integers(1, 3),
    extra=st.integers(1, 6),
    seed=st.integers(0, 2**32 - 1),
    constant=st.floats(-0.01, 0.01),
)
def test_fama_macbeth_recovers_the_premia_on_exact_data(
    periods: int, factors: int, extra: int, seed: int, constant: float
) -> None:
    rng = np.random.default_rng(seed)
    assets = factors + 1 + extra
    f = rng.normal(0.005, 0.04, size=(periods, factors))
    betas = rng.uniform(0.1, 2.0, size=(assets, factors))
    returns = constant + f @ betas.T
    outputs = run(
        calculation="fama_macbeth", returns=returns.tolist(), factors=f.tolist()
    )
    np.testing.assert_allclose(outputs.premia, f.mean(axis=0), rtol=1e-9, atol=1e-12)
    assert outputs.intercept == pytest.approx(constant, abs=1e-12)
    np.testing.assert_allclose(outputs.betas, betas, rtol=1e-9)


@pytest.mark.invariant(
    "asset_pricing.factor_model_tests", "shanken_correction_never_narrows_errors"
)
@settings(max_examples=80)
@given(
    periods=st.integers(6, 150),
    factors=st.integers(1, 3),
    extra=st.integers(1, 8),
    seed=st.integers(0, 2**32 - 1),
    intercept=st.booleans(),
    noise=st.sampled_from([0.001, 0.02, 0.1]),
)
def test_shanken_never_narrows_the_errors(  # noqa: PLR0913 - the draws
    *, periods: int, factors: int, extra: int, seed: int, intercept: bool, noise: float
) -> None:
    assets = factors + 1 + extra
    data = panel(periods, assets, factors, seed, noise)
    outputs = run(calculation="fama_macbeth", intercept=intercept, **data)
    for corrected, plain in zip(
        outputs.shanken_standard_errors, outputs.premium_standard_errors, strict=True
    ):
        assert corrected >= plain * (1 - 1e-12)
    if intercept:
        assert outputs.shanken_intercept_standard_error >= (
            outputs.intercept_standard_error * (1 - 1e-12)
        )


@pytest.mark.oracle("asset_pricing.factor_model_tests")
@pytest.mark.parametrize(
    ("periods", "assets", "factors"),
    [(30, 4, 1), (120, 10, 3), (61, 25, 3), (240, 6, 5)],
)
@pytest.mark.parametrize("seed", [1, 2])
def test_grs_agrees_with_statsmodels_and_scipy(
    periods: int, assets: int, factors: int, seed: int
) -> None:
    data = panel(periods, assets, factors, seed)
    outputs = run(calculation="grs", **data)
    excess = np.subtract(data["returns"], np.asarray(data["risk_free"])[:, None])
    f = np.asarray(data["factors"])
    design = sm.add_constant(f)
    fits = [sm.OLS(excess[:, i], design).fit() for i in range(assets)]
    alphas = np.array([fit.params[0] for fit in fits])
    residuals = np.column_stack([fit.resid for fit in fits])
    sigma = residuals.T @ residuals / periods
    omega = np.cov(f, rowvar=False, ddof=0).reshape(factors, factors)
    mean = f.mean(axis=0)
    expected = (
        (periods - assets - factors)
        / assets
        * float(alphas @ np.linalg.inv(sigma) @ alphas)
        / (1 + float(mean @ np.linalg.inv(omega) @ mean))
    )
    assert outputs.statistic == pytest.approx(expected, rel=1e-8)
    np.testing.assert_allclose(outputs.alphas, alphas, rtol=1e-8, atol=1e-14)
    tail = scipy.stats.f.sf(outputs.statistic, assets, periods - assets - factors)
    assert outputs.p_value == pytest.approx(tail, rel=1e-10, abs=1e-300)
    assert outputs.denominator_degrees_of_freedom == periods - assets - factors


@pytest.mark.oracle("asset_pricing.factor_model_tests")
@given(
    statistic=st.floats(0.0, 1e4),
    numerator=st.integers(1, 100),
    denominator=st.integers(1, 2_500),
)
def test_the_p_value_is_scipys_f_tail(
    statistic: float, numerator: int, denominator: int
) -> None:
    module = importlib.import_module(
        "pyeconomics.models.asset_pricing.factor_model_tests"
    )
    found = module._p_value(statistic, numerator, denominator)  # noqa: SLF001
    expected = scipy.stats.f.sf(statistic, numerator, denominator)
    assert found == pytest.approx(expected, rel=1e-9, abs=1e-15)


@pytest.mark.oracle("asset_pricing.factor_model_tests")
@pytest.mark.parametrize(
    ("periods", "assets", "factors"), [(24, 6, 1), (120, 25, 3), (60, 12, 5)]
)
@pytest.mark.parametrize("intercept", [True, False])
def test_fama_macbeth_agrees_with_a_statsmodels_recomputation(
    *, periods: int, assets: int, factors: int, intercept: bool
) -> None:
    data = panel(periods, assets, factors, seed=periods + assets)
    outputs = run(calculation="fama_macbeth", intercept=intercept, **data)
    excess = np.subtract(data["returns"], np.asarray(data["risk_free"])[:, None])
    f = np.asarray(data["factors"])
    betas = np.array(
        [
            sm.OLS(excess[:, i], sm.add_constant(f)).fit().params[1:]
            for i in range(assets)
        ]
    )
    design = sm.add_constant(betas) if intercept else betas
    gammas = np.array([sm.OLS(excess[t], design).fit().params for t in range(periods)])
    estimates = gammas.mean(axis=0)
    w = np.cov(gammas, rowvar=False, ddof=0).reshape(len(estimates), -1)
    v_fm = w / periods
    sigma_f = np.cov(f, rowvar=False, ddof=0).reshape(factors, factors)
    first = 1 if intercept else 0
    premia = estimates[first:]
    c = float(premia @ np.linalg.inv(sigma_f) @ premia)
    bordered = np.zeros_like(v_fm)
    bordered[first:, first:] = sigma_f / periods
    v_shanken = (1 + c) * (v_fm - bordered) + bordered
    np.testing.assert_allclose(outputs.betas, betas, rtol=1e-8)
    np.testing.assert_allclose(outputs.premia, premia, rtol=1e-8, atol=1e-14)
    np.testing.assert_allclose(
        outputs.premium_standard_errors, np.sqrt(np.diag(v_fm))[first:], rtol=1e-7
    )
    np.testing.assert_allclose(
        outputs.shanken_standard_errors, np.sqrt(np.diag(v_shanken))[first:], rtol=1e-7
    )
    if intercept:
        assert outputs.intercept == pytest.approx(estimates[0], rel=1e-8, abs=1e-14)
        assert outputs.intercept_standard_error == pytest.approx(
            np.sqrt(v_fm[0, 0]), rel=1e-7
        )
        assert outputs.shanken_intercept_standard_error == pytest.approx(
            np.sqrt(v_shanken[0, 0]), rel=1e-7
        )


def test_without_a_constant_the_intercept_is_none_and_says_so() -> None:
    result = run_model(
        factor_model_tests,
        {"calculation": "fama_macbeth", "intercept": False, **panel(30, 5, 2, 4)},
    )
    assert result.outputs.intercept is None
    assert result.outputs.shanken_intercept_standard_error is None
    assert "no_intercept" in [w.code for w in result.warnings]


def test_a_dataframe_panel_is_accepted() -> None:
    data = panel(40, 4, 2, 6)
    outputs = run(
        calculation="grs",
        returns=pd.DataFrame(data["returns"]),
        factors=np.asarray(data["factors"]),
        risk_free=data["risk_free"],
    )
    assert outputs.observations == 40
    assert outputs.numerator_degrees_of_freedom == 4


@pytest.mark.parametrize(
    ("calculation", "shape", "message"),
    [
        ("grs", (8, 5, 3), "needs more than 8 periods"),
        ("fama_macbeth", (40, 3, 2), "needs more than 3 assets"),
        ("fama_macbeth", (3, 6, 2), "needs more than 3 periods"),
    ],
)
def test_too_small_a_panel_is_refused(
    calculation: str, shape: tuple[int, int, int], message: str
) -> None:
    with pytest.raises(InputError, match=message):
        run(calculation=calculation, **panel(*shape, seed=1))


def test_ragged_and_mismatched_panels_are_refused() -> None:
    data = panel(20, 3, 1, 2)
    ragged = [list(row) for row in data["returns"]]
    ragged[3] = ragged[3][:2]
    with pytest.raises(InputError, match="one value per column"):
        run(calculation="grs", **{**data, "returns": ragged})
    with pytest.raises(InputError, match="factors has 19 periods"):
        run(calculation="grs", **{**data, "factors": data["factors"][:-1]})
    with pytest.raises(InputError, match="risk_free has 19 periods"):
        run(calculation="grs", **{**data, "risk_free": data["risk_free"][:-1]})


def test_an_asset_that_is_a_factor_leaves_no_grs_statistic() -> None:
    data = panel(30, 3, 2, 3)
    for row, factor_row in zip(data["returns"], data["factors"], strict=True):
        row[0] = factor_row[0]
    with pytest.raises(DomainError, match="exact combination of the factors"):
        run(calculation="grs", **{**data, "risk_free": None})


def test_betas_that_never_vary_across_assets_leave_no_premia() -> None:
    rng = np.random.default_rng(5)
    f = rng.normal(0.0, 0.05, size=(30, 1))
    # Every asset is the same portfolio up to noise orthogonal to the factor:
    # identical betas.
    same = np.column_stack([0.8 * f[:, 0]] * 4) + projected_out(
        rng.normal(0.0, 1e-3, size=(30, 4)), f
    )
    with pytest.raises(DomainError, match="betas are collinear"):
        run(calculation="fama_macbeth", returns=same.tolist(), factors=f.tolist())


@pytest.mark.parametrize(
    ("statistic", "numerator", "denominator"),
    [(4.814924630055046e-18, 1, 2), (1e-13, 1, 2500), (1e-300, 25, 92), (50.0, 3, 5)],
)
def test_the_p_value_keeps_its_digits_for_a_tiny_statistic(
    statistic: float, numerator: int, denominator: int
) -> None:
    module = importlib.import_module(
        "pyeconomics.models.asset_pricing.factor_model_tests"
    )
    found = module._p_value(statistic, numerator, denominator)  # noqa: SLF001
    expected = scipy.stats.f.sf(statistic, numerator, denominator)
    assert found == pytest.approx(expected, rel=1e-12, abs=1e-300)


@pytest.mark.parametrize("scale", [1e-100, 1e-160, 1e-200])
def test_the_tests_do_not_depend_on_the_scale_of_the_data(scale: float) -> None:
    data = panel(60, 8, 2, seed=21)
    tiny = {
        "returns": (np.asarray(data["returns"]) * scale).tolist(),
        "factors": (np.asarray(data["factors"]) * scale).tolist(),
    }
    plain = {"returns": data["returns"], "factors": data["factors"]}
    for calculation in ("grs", "fama_macbeth"):
        small = run(calculation=calculation, **tiny)
        base = run(calculation=calculation, **plain)
        if calculation == "grs":
            assert small.statistic == pytest.approx(base.statistic, rel=1e-8)
        else:
            np.testing.assert_allclose(
                np.asarray(small.premium_standard_errors) / scale,
                base.premium_standard_errors,
                rtol=1e-8,
            )
            np.testing.assert_allclose(
                np.asarray(small.shanken_standard_errors) / scale,
                base.shanken_standard_errors,
                rtol=1e-8,
            )
