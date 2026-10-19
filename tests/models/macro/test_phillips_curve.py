# tests/models/macro/test_phillips_curve.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``macro.phillips_curve``: the exact-line invariant, the statsmodels oracle, edges."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import statsmodels.api as sm
from hypothesis import given, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.macro import phillips_curve


def result(**inputs: Any) -> Any:  # noqa: ANN401 - a Result
    return run_model(phillips_curve, inputs)


def sample(size: int, seed: int) -> dict[str, list[float]]:
    """Quarterly-like data with a negative slope and autocorrelated noise."""
    rng = np.random.default_rng(seed)
    natural = 0.045 + 0.002 * np.sin(np.arange(size) / 9)
    unemployment = np.clip(
        natural + 0.012 * np.cumsum(rng.normal(size=size)) / 4, 0.02, 0.12
    )
    expected = 0.02 + 0.001 * rng.normal(size=size)
    noise = np.zeros(size)
    for t in range(1, size):
        noise[t] = 0.6 * noise[t - 1] + 0.002 * rng.normal()
    inflation = expected + 0.001 - 0.4 * (unemployment - natural) + noise
    return {
        "inflation": inflation.tolist(),
        "expected_inflation": expected.tolist(),
        "unemployment": unemployment.tolist(),
        "natural_unemployment": natural.tolist(),
    }


@pytest.mark.invariant("macro.phillips_curve", "exact_linear_data_recovers_slope")
@given(
    slope=st.floats(-3.0, 3.0),
    intercept=st.floats(-0.01, 0.01),
    gaps=st.lists(
        st.integers(-30, 30).map(lambda g: g / 1000),
        min_size=3,
        max_size=60,
        unique=True,
    ),
)
def test_an_exact_line_returns_its_slope_and_intercept(
    slope: float, intercept: float, gaps: list[float]
) -> None:
    natural = [0.05] * len(gaps)
    unemployment = [0.05 + g for g in gaps]
    expected = [0.02] * len(gaps)
    inflation = [0.02 + intercept + slope * g for g in gaps]
    outputs = result(
        inflation=inflation,
        expected_inflation=expected,
        unemployment=unemployment,
        natural_unemployment=natural,
    ).outputs
    assert outputs.slope == pytest.approx(slope, abs=1e-9)
    assert outputs.intercept == pytest.approx(intercept, abs=1e-11)


@pytest.mark.oracle("macro.phillips_curve")
@pytest.mark.parametrize("covariance", ["classical", "hc1", "newey_west"])
@settings(deadline=None, max_examples=40)
@given(
    size=st.integers(8, 200),
    seed=st.integers(0, 2**32 - 1),
    controls=st.integers(0, 2),
    lags=st.one_of(st.none(), st.integers(0, 6)),
)
def test_statsmodels_ols_agrees(
    covariance: str, size: int, seed: int, controls: int, lags: int | None
) -> None:
    data = sample(size, seed)
    rng = np.random.default_rng(seed + 1)
    shocks = [rng.normal(scale=0.01, size=size).tolist() for _ in range(controls)]
    outputs = result(
        **data,
        supply_shocks=shocks or None,
        covariance=covariance,
        lags=lags,
    ).outputs
    surprise = np.subtract(data["inflation"], data["expected_inflation"])
    gap = np.subtract(data["unemployment"], data["natural_unemployment"])
    design = sm.add_constant(np.column_stack([gap, *shocks]))
    options: dict[str, Any] = {}
    if covariance == "hc1":
        options = {"cov_type": "HC1"}
    elif covariance == "newey_west":
        used = outputs.hac_lags
        options = {
            "cov_type": "HAC",
            "cov_kwds": {"maxlags": used, "use_correction": False},
        }
    expected = sm.OLS(surprise, design).fit(**options)
    assert outputs.slope == pytest.approx(expected.params[1], rel=1e-8)
    assert outputs.intercept == pytest.approx(expected.params[0], rel=1e-8, abs=1e-14)
    assert outputs.slope_standard_error == pytest.approx(expected.bse[1], rel=1e-8)
    assert outputs.intercept_standard_error == pytest.approx(expected.bse[0], rel=1e-8)
    assert outputs.slope_t_statistic == pytest.approx(expected.tvalues[1], rel=1e-7)
    assert outputs.r_squared == pytest.approx(expected.rsquared, rel=1e-8, abs=1e-12)
    assert outputs.observations == size
    np.testing.assert_allclose(
        outputs.control_coefficients, expected.params[2:], rtol=1e-7
    )
    np.testing.assert_allclose(
        outputs.control_standard_errors, expected.bse[2:], rtol=1e-7
    )


def test_newey_west_is_the_default_with_the_rule_of_thumb() -> None:
    outputs = result(**sample(100, 4)).outputs
    assert outputs.hac_lags == 4


def test_an_exact_fit_has_no_t_statistic_and_says_so() -> None:
    gaps = [-0.01, 0.0, 0.01, 0.02]
    run = result(
        inflation=[0.03 - 0.5 * g for g in gaps],
        expected_inflation=[0.03] * 4,
        unemployment=[0.05 + g for g in gaps],
        natural_unemployment=[0.05] * 4,
        covariance="classical",
    )
    assert run.outputs.slope_t_statistic is None
    assert "exact_fit" in [w.code for w in run.warnings]


def test_a_surprise_that_never_varies_has_no_r_squared() -> None:
    run = result(
        inflation=[0.03] * 4,
        expected_inflation=[0.02] * 4,
        unemployment=[0.04, 0.05, 0.06, 0.055],
        natural_unemployment=[0.05] * 4,
    )
    assert run.outputs.r_squared is None
    assert {"no_variation", "exact_fit"} <= {w.code for w in run.warnings}


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"unemployment": [0.05, 0.05, 0.05]}, "unemployment has 3 periods"),
        ({"supply_shocks": [[0.0, 0.1, 0.2]]}, "supply_shocks"),
        ({"lags": 4}, "lags must be below"),
    ],
)
def test_misaligned_inputs_are_refused(changes: dict[str, Any], message: str) -> None:
    data = sample(4, 1) | changes
    with pytest.raises(InputError, match=message):
        result(**data)


def test_controls_need_degrees_of_freedom() -> None:
    data = sample(4, 2)
    shocks = [[0.0, 0.1, 0.2, 0.3], [0.3, 0.1, 0.2, 0.0]]
    with pytest.raises(InputError, match="4 coefficients need more than 4"):
        result(**data, supply_shocks=shocks)


def test_a_gap_that_never_varies_is_not_identified() -> None:
    with pytest.raises(DomainError, match="collinear"):
        result(
            inflation=[0.02, 0.03, 0.025, 0.04],
            expected_inflation=[0.02] * 4,
            unemployment=[0.05] * 4,
            natural_unemployment=[0.045] * 4,
        )
