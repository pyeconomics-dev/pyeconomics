# tests/models/macro/test_okun_law.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``macro.okun_law``: the exact-line invariant, the statsmodels oracle and edges."""

from __future__ import annotations

import itertools
from typing import Any

import numpy as np
import pytest
import statsmodels.api as sm
from hypothesis import given, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.macro import okun_law


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(okun_law, inputs).outputs


@pytest.mark.invariant("macro.okun_law", "exact_linear_data_recovers_coefficient")
@given(
    slope=st.floats(-4.0, -0.5),
    intercept=st.floats(-0.005, 0.005),
    gaps=st.lists(
        st.integers(-30, 30).map(lambda g: g / 1000),
        min_size=3,
        max_size=60,
        unique=True,
    ),
)
def test_the_gap_form_recovers_an_exact_line(
    slope: float, intercept: float, gaps: list[float]
) -> None:
    outputs = run(
        calculation="gap",
        output_gap=[intercept + slope * g for g in gaps],
        unemployment=[0.05 + g for g in gaps],
        natural_unemployment=[0.05] * len(gaps),
    )
    assert outputs.slope == pytest.approx(slope, abs=1e-9)
    assert outputs.intercept == pytest.approx(intercept, abs=1e-11)


@pytest.mark.invariant("macro.okun_law", "exact_linear_data_recovers_coefficient")
@given(
    slope=st.floats(-0.1, -0.02),
    intercept=st.floats(-0.002, 0.004),
    growths=st.lists(
        st.integers(-30, 60).map(lambda g: g / 1000), min_size=3, max_size=15
    ).filter(lambda g: len(set(g)) > 1),
    span=st.integers(1, 4),
)
def test_the_difference_form_recovers_an_exact_line(
    slope: float, intercept: float, growths: list[float], span: int
) -> None:
    unemployment = [0.15] * span
    output = [100.0] * span
    for growth in growths:
        output.append(output[-span] * (1.0 + growth))
        unemployment.append(unemployment[-span] + intercept + slope * growth)
    outputs = run(
        calculation="difference",
        output=output,
        unemployment=unemployment,
        span=span,
    )
    assert outputs.slope == pytest.approx(slope, abs=1e-9)
    assert outputs.intercept == pytest.approx(intercept, abs=1e-11)
    assert outputs.constant_unemployment_growth == pytest.approx(
        -outputs.intercept / outputs.slope
    )
    assert outputs.observations == len(growths)


def test_growth_annualizes_by_compounding() -> None:
    output = [100.0, 101.0, 101.5, 102.5, 102.9, 104.0]
    unemployment = [0.05, 0.049, 0.0495, 0.048, 0.0482, 0.047]
    annual = run(
        calculation="difference",
        output=output,
        unemployment=unemployment,
        periods_per_year=4,
        covariance="classical",
    )
    growth = [(b / a) ** 4 - 1.0 for a, b in itertools.pairwise(output)]
    change = [b - a for a, b in itertools.pairwise(unemployment)]
    expected = sm.OLS(change, sm.add_constant(growth)).fit()
    assert annual.slope == pytest.approx(expected.params[1], rel=1e-10)
    assert annual.intercept == pytest.approx(expected.params[0], rel=1e-9)
    assert annual.constant_unemployment_growth == pytest.approx(
        -expected.params[0] / expected.params[1], rel=1e-9
    )


def test_a_flat_slope_holds_no_growth_constant() -> None:
    result = run_model(
        okun_law,
        {
            "calculation": "difference",
            "output": [100.0, 101.0, 103.0, 104.0, 107.0],
            "unemployment": [0.05, 0.051, 0.052, 0.053, 0.054],
            "covariance": "classical",
        },
    )
    # The change in unemployment never varies: the slope is zero to rounding,
    # and no growth rate holds unemployment constant.
    assert result.outputs.slope == pytest.approx(0.0, abs=1e-15)
    assert result.outputs.constant_unemployment_growth is None
    assert "no_constant_unemployment_growth" in [w.code for w in result.warnings]


def quarters(size: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Output, unemployment and its natural rate, related by Okun's law."""
    rng = np.random.default_rng(seed)
    natural = np.full(size, 0.045)
    unemployment = np.clip(
        0.045 + np.cumsum(rng.normal(scale=0.002, size=size)), 0.02, 0.15
    )
    gap = -2.0 * (unemployment - natural) + rng.normal(scale=0.003, size=size)
    output = 18_000.0 * np.exp(0.006 * np.arange(size) + gap)
    return output, unemployment, natural


@pytest.mark.oracle("macro.okun_law")
@pytest.mark.parametrize("covariance", ["classical", "hc1", "newey_west"])
@settings(deadline=None, max_examples=40)
@given(
    size=st.integers(12, 240),
    seed=st.integers(0, 2**32 - 1),
    span=st.integers(1, 4),
    lags=st.one_of(st.none(), st.integers(0, 4)),
)
def test_statsmodels_ols_agrees_in_both_forms(
    covariance: str, size: int, seed: int, span: int, lags: int | None
) -> None:
    output, unemployment, natural = quarters(size, seed)
    gap = np.log(output) - np.log(18_000.0 * np.exp(0.006 * np.arange(size)))
    cases = [
        (
            run(
                calculation="gap",
                output_gap=gap.tolist(),
                unemployment=unemployment.tolist(),
                natural_unemployment=natural.tolist(),
                covariance=covariance,
                lags=lags,
            ),
            gap,
            unemployment - natural,
        ),
        (
            run(
                calculation="difference",
                output=output.tolist(),
                unemployment=unemployment.tolist(),
                span=span,
                covariance=covariance,
                lags=lags,
            ),
            unemployment[span:] - unemployment[:-span],
            output[span:] / output[:-span] - 1.0,
        ),
    ]
    for outputs, response, regressor in cases:
        options: dict[str, Any] = {}
        if covariance == "hc1":
            options = {"cov_type": "HC1"}
        elif covariance == "newey_west":
            kwds = {"maxlags": outputs.hac_lags, "use_correction": False}
            options = {"cov_type": "HAC", "cov_kwds": kwds}
        expected = sm.OLS(response, sm.add_constant(regressor)).fit(**options)
        assert outputs.slope == pytest.approx(expected.params[1], rel=1e-8)
        assert outputs.intercept == pytest.approx(
            expected.params[0], rel=1e-7, abs=1e-14
        )
        assert outputs.slope_standard_error == pytest.approx(expected.bse[1], rel=1e-8)
        assert outputs.intercept_standard_error == pytest.approx(
            expected.bse[0], rel=1e-8
        )
        assert outputs.r_squared == pytest.approx(
            expected.rsquared, rel=1e-8, abs=1e-12
        )


@pytest.mark.parametrize(
    ("inputs", "message"),
    [
        (
            {
                "calculation": "gap",
                "output_gap": [0.0, 0.01, -0.01, 0.0],
                "unemployment": [0.05, 0.04, 0.045],
                "natural_unemployment": [0.05] * 4,
            },
            "unemployment has 3 periods",
        ),
        (
            {
                "calculation": "difference",
                "output": [100.0, 101.0, 102.0, 101.5],
                "unemployment": [0.05, 0.05, 0.051, 0.05],
                "span": 2,
            },
            "leaves 2 changes",
        ),
        (
            {
                "calculation": "difference",
                "output": [100.0, 101.0, 102.0, 101.5, 102.0],
                "unemployment": [0.05, 0.05, 0.051, 0.05],
            },
            "unemployment has 4 periods",
        ),
    ],
)
def test_misaligned_inputs_are_refused(inputs: dict[str, Any], message: str) -> None:
    with pytest.raises(InputError, match=message):
        run(**inputs)


def test_output_that_grows_beyond_representation_is_refused() -> None:
    with pytest.raises(DomainError, match="beyond representation"):
        run(
            calculation="difference",
            output=[1e-320, 1e15, 1e14, 1e15],
            unemployment=[0.05, 0.04, 0.045, 0.043],
        )
