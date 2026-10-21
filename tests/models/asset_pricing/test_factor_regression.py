# tests/models/asset_pricing/test_factor_regression.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``asset_pricing.factor_regression``: invariants, errors and statsmodels as an oracle.

The oracle is statsmodels' OLS with the same covariance estimator (``nonrobust``,
``HC1`` or ``HAC`` with Bartlett weights and no small-sample correction), fitted
to the same excess returns and factors. statsmodels is imported at the top, so a
missing library fails the suite.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from hypothesis import given, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.asset_pricing import factor_regression

#: Each calculation's factors, in the order of its coefficients.
SETS = {
    "capm": ("market",),
    "ff3": ("market", "size", "value"),
    "carhart": ("market", "size", "value", "momentum"),
    "ff5": ("market", "size", "value", "profitability", "investment"),
    "ff6": ("market", "size", "value", "profitability", "investment", "momentum"),
}


def sample(calculation: str, size: int, seed: int) -> dict[str, Any]:
    """Return monthly-looking returns, a risk-free rate and factors."""
    rng = np.random.default_rng(seed)
    names = SETS[calculation]
    factors = rng.normal(0.005, 0.04, size=(size, len(names)))
    betas = rng.uniform(-0.5, 1.5, size=len(names))
    risk_free = rng.uniform(0.0, 0.004, size=size)
    noise = rng.normal(0.0, 0.02, size=size)
    returns = risk_free + 0.001 + factors @ betas + noise
    inputs: dict[str, Any] = {
        "calculation": calculation,
        "returns": returns.tolist(),
        "risk_free": risk_free.tolist(),
        "periods_per_year": 12,
        **{name: factors[:, j].tolist() for j, name in enumerate(names)},
    }
    if calculation == "capm":
        inputs["market_premium"] = 0.005
    return inputs


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(factor_regression, inputs).outputs


@pytest.mark.invariant(
    "asset_pricing.factor_regression", "exact_factor_data_recovers_betas"
)
@settings(max_examples=60)
@given(
    calculation=st.sampled_from(sorted(SETS)),
    size=st.integers(8, 120),
    seed=st.integers(0, 2**32 - 1),
    alpha=st.floats(-0.01, 0.01),
)
def test_exact_factor_data_recovers_the_betas(
    calculation: str, size: int, seed: int, alpha: float
) -> None:
    rng = np.random.default_rng(seed)
    names = SETS[calculation]
    factors = rng.normal(0.0, 0.05, size=(size, len(names)))
    betas = rng.uniform(-2.0, 2.0, size=len(names))
    inputs = sample(calculation, size, seed)
    inputs.update({name: factors[:, j].tolist() for j, name in enumerate(names)})
    risk_free = np.asarray(inputs["risk_free"])
    inputs["returns"] = (risk_free + alpha + factors @ betas).tolist()
    result = run_model(factor_regression, inputs)
    outputs = result.outputs
    assert outputs.alpha == pytest.approx(alpha, abs=1e-12)
    for name, beta in zip(names, betas, strict=True):
        assert getattr(outputs, f"{name}_beta") == pytest.approx(beta, abs=1e-10)
    assert outputs.residual_volatility == pytest.approx(0.0, abs=1e-12)
    assert outputs.alpha_t_statistic is None
    assert "exact_fit" in [w.code for w in result.warnings]


@pytest.mark.invariant(
    "asset_pricing.factor_regression", "capm_beta_equals_covariance_over_variance"
)
@given(size=st.integers(3, 200), seed=st.integers(0, 2**32 - 1))
def test_the_capm_beta_is_covariance_over_variance(size: int, seed: int) -> None:
    inputs = sample("capm", size, seed)
    outputs = run(**inputs)
    excess = np.subtract(inputs["returns"], inputs["risk_free"])
    market = np.asarray(inputs["market"])
    covariance = np.cov(excess, market, ddof=1)
    expected = covariance[0, 1] / covariance[1, 1]
    assert outputs.market_beta == pytest.approx(expected, rel=1e-9, abs=1e-12)


@pytest.mark.invariant(
    "asset_pricing.factor_regression", "annualized_alpha_is_alpha_times_periods"
)
@given(
    calculation=st.sampled_from(sorted(SETS)),
    size=st.integers(10, 60),
    seed=st.integers(0, 2**32 - 1),
    periods=st.sampled_from([1, 4, 12, 52, 252, 365]),
)
def test_annualized_alpha_is_alpha_times_the_periods(
    calculation: str, size: int, seed: int, periods: int
) -> None:
    inputs = {**sample(calculation, size, seed), "periods_per_year": periods}
    outputs = run(**inputs)
    assert outputs.alpha_annualized == pytest.approx(outputs.alpha * periods, rel=1e-15)
    assert outputs.residual_volatility_annualized == pytest.approx(
        outputs.residual_volatility * math.sqrt(periods), rel=1e-15
    )


@pytest.mark.oracle("asset_pricing.factor_regression")
@pytest.mark.parametrize("calculation", sorted(SETS))
@pytest.mark.parametrize(
    ("covariance", "lags"),
    [("classical", None), ("hc1", None), ("newey_west", None), ("newey_west", 6)],
)
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_statsmodels_ols_agrees(
    calculation: str, covariance: str, lags: int | None, seed: int
) -> None:
    size = 60 + 40 * seed
    inputs = {**sample(calculation, size, seed), "covariance": covariance, "lags": lags}
    outputs = run(**inputs)
    names = SETS[calculation]
    excess = np.asarray(inputs["returns"]) - np.asarray(inputs["risk_free"])
    columns = [np.asarray(inputs[name], dtype=np.float64) for name in names]
    design = sm.add_constant(np.column_stack(columns))
    options: dict[str, Any] = {}
    if covariance == "hc1":
        options = {"cov_type": "HC1"}
    elif covariance == "newey_west":
        options = {
            "cov_type": "HAC",
            "cov_kwds": {"maxlags": outputs.hac_lags, "use_correction": False},
        }
    expected = sm.OLS(excess, design).fit(**options)
    assert outputs.alpha == pytest.approx(expected.params[0], rel=1e-8, abs=1e-14)
    assert outputs.alpha_standard_error == pytest.approx(expected.bse[0], rel=1e-8)
    assert outputs.alpha_t_statistic == pytest.approx(expected.tvalues[0], rel=1e-7)
    for j, name in enumerate(names, start=1):
        assert getattr(outputs, f"{name}_beta") == pytest.approx(
            expected.params[j], rel=1e-8
        )
        assert getattr(outputs, f"{name}_beta_standard_error") == pytest.approx(
            expected.bse[j], rel=1e-8
        )
        assert getattr(outputs, f"{name}_beta_t_statistic") == pytest.approx(
            expected.tvalues[j], rel=1e-7
        )
    assert outputs.r_squared == pytest.approx(expected.rsquared, rel=1e-9)
    assert outputs.residual_volatility == pytest.approx(
        math.sqrt(expected.mse_resid), rel=1e-9
    )
    assert outputs.observations == size
    if lags is not None:
        assert outputs.hac_lags == lags


def test_the_security_market_line_prices_the_beta() -> None:
    inputs = {**sample("capm", 60, 7), "market_premium": 0.006, "risk_free_rate": 0.003}
    outputs = run(**inputs)
    assert outputs.expected_excess_return == pytest.approx(outputs.market_beta * 0.006)
    assert outputs.expected_return == pytest.approx(0.003 + outputs.market_beta * 0.006)


def test_returns_given_as_excess_returns_need_no_risk_free_rate() -> None:
    inputs = sample("ff3", 80, 11)
    excess = np.subtract(inputs["returns"], inputs["risk_free"]).tolist()
    with_rate = run(**inputs)
    without = run(**{**inputs, "returns": excess, "risk_free": None})
    assert without.alpha == pytest.approx(with_rate.alpha, rel=1e-12)
    assert without.value_beta == pytest.approx(with_rate.value_beta, rel=1e-12)


def test_newey_west_is_the_default_with_the_rule_of_thumb() -> None:
    outputs = run(**sample("capm", 100, 4))
    assert outputs.hac_lags == 4


def test_numpy_and_pandas_series_are_accepted() -> None:
    inputs = sample("ff3", 40, 9)
    outputs = run(
        **{
            **inputs,
            "returns": np.asarray(inputs["returns"]),
            "market": pd.Series(inputs["market"]),
        }
    )
    assert outputs.observations == 40


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"size": [0.01, 0.02, 0.0, 0.01]}, "size has 4 periods"),
        ({"risk_free": [0.0] * 5}, "risk_free has 5 periods"),
        ({"lags": 30}, "lags must be below"),
    ],
)
def test_inconsistent_samples_are_refused(change: dict[str, Any], message: str) -> None:
    inputs = {**sample("ff3", 30, 3), **change}
    with pytest.raises(InputError, match=message):
        run(**inputs)


def test_a_sample_no_longer_than_the_coefficients_is_refused() -> None:
    inputs = sample("ff6", 7, 3)
    with pytest.raises(InputError, match="7 coefficients need more than 7 periods"):
        run(**inputs)


def test_collinear_factors_raise_domain_error() -> None:
    inputs = sample("ff3", 50, 5)
    inputs["value"] = list(inputs["size"])
    with pytest.raises(DomainError, match="collinear"):
        run(**inputs)


def test_a_factor_that_never_varies_raises_domain_error() -> None:
    inputs = sample("ff3", 50, 6)
    inputs["size"] = [0.0] * 50
    with pytest.raises(DomainError):
        run(**inputs)


def test_a_flat_excess_return_has_no_r_squared_and_says_so() -> None:
    inputs = sample("capm", 20, 8)
    inputs["returns"] = list(inputs["risk_free"])
    result = run_model(factor_regression, inputs)
    assert result.outputs.r_squared is None
    assert "no_variation" in [w.code for w in result.warnings]


def test_a_near_exact_fit_drops_only_the_unbounded_t_statistic() -> None:
    inputs = sample("capm", 40, 10)
    market = np.asarray(inputs["market"])
    risk_free = np.asarray(inputs["risk_free"])
    # Residuals of 1e-11: past the exact-fit test (1e-12 of the spread), yet
    # small enough that the t statistics pass 1e9.
    wiggle = np.tile([1e-11, -1e-11], 20)
    inputs["returns"] = (risk_free + 0.5 + 2.0 * market + wiggle).tolist()
    result = run_model(factor_regression, inputs)
    assert "near_exact_fit" in [w.code for w in result.warnings]
    assert result.outputs.alpha_t_statistic is None
    assert result.outputs.alpha_standard_error > 0


@pytest.mark.parametrize("scale", [1e-100, 1e-200, 1e-300])
def test_the_residual_volatility_scales_with_the_data(scale: float) -> None:
    inputs = sample("ff3", 60, 13)
    names = ("returns", "risk_free", *SETS["ff3"])
    tiny = {**inputs, **{n: (np.asarray(inputs[n]) * scale).tolist() for n in names}}
    base = run(**inputs)
    small = run(**tiny)
    assert small.residual_volatility / scale == pytest.approx(
        base.residual_volatility, rel=1e-8
    )
    assert small.market_beta == pytest.approx(base.market_beta, rel=1e-8)
