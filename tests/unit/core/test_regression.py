# tests/unit/core/test_regression.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Least squares: statsmodels agrees for every covariance type; the edges refuse.

statsmodels is the independent oracle (the test group carries it): its OLS with
``nonrobust``, ``HC1`` and ``HAC`` (Bartlett weights, ``use_correction=False``)
covariances must give the same coefficients, standard errors, t statistics, R²
and residuals as :func:`pyeconomics.core.least_squares`.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
import statsmodels.api as sm
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from pyeconomics.core import (
    Covariance,
    DomainError,
    InputError,
    least_squares,
    newey_west_lags,
)
from pyeconomics.core.regression import COLUMNS_MAX, LAGS_MAX, ROWS_MAX

#: statsmodels' arguments for each of our covariance types.
STATSMODELS: dict[str, dict[str, Any]] = {
    "classical": {},
    "hc1": {"cov_type": "HC1"},
    "newey_west": {"cov_type": "HAC"},
}


@st.composite
def regressions(draw: st.DrawFn) -> tuple[np.ndarray, np.ndarray, bool, int]:
    """A response with autocorrelated, heteroskedastic errors and its design."""
    rows = draw(st.integers(8, 120))
    width = draw(st.integers(1, 4))
    seed = draw(st.integers(0, 2**32 - 1))
    rng = np.random.default_rng(seed)
    scale = draw(st.sampled_from([1e-6, 1.0, 1e6]))
    x = rng.normal(size=(rows, width)) * scale + draw(st.floats(-5.0, 5.0))
    errors = np.zeros(rows)
    for t in range(1, rows):
        errors[t] = 0.5 * errors[t - 1] + rng.normal() * (1.0 + abs(x[t, 0]) / scale)
    beta = rng.normal(size=width)
    y = 2.0 + x @ beta / scale + errors
    constant = draw(st.booleans())
    lags = draw(st.integers(0, min(12, rows - 1)))
    return y, x, constant, lags


@pytest.mark.parametrize("covariance", sorted(STATSMODELS))
@settings(max_examples=60, deadline=None)
@given(drawn=regressions())
def test_statsmodels_agrees_for_each_covariance(
    covariance: str, drawn: tuple[np.ndarray, np.ndarray, bool, int]
) -> None:
    y, x, constant, lags = drawn
    design = sm.add_constant(x, has_constant="add") if constant else x
    # statsmodels' robust errors lose digits on near-collinear designs (4e-5 at a
    # scaled condition number of 1e6, against an exact computation); the exact
    # test below holds those, so the oracle compares well-conditioned ones.
    assume(np.linalg.cond(design / np.max(np.abs(design), axis=0)) < 1e4)
    options = dict(STATSMODELS[covariance])
    if covariance == "newey_west":
        options["cov_kwds"] = {"maxlags": lags, "use_correction": False}
    expected = sm.OLS(y, design).fit(**options)
    fit = least_squares(y, x, constant=constant, covariance=covariance, lags=lags)
    np.testing.assert_allclose(fit.coefficients, expected.params, rtol=1e-8, atol=0)
    np.testing.assert_allclose(fit.standard_errors, expected.bse, rtol=1e-8)
    assert fit.t_statistics is not None
    np.testing.assert_allclose(fit.t_statistics, expected.tvalues, rtol=1e-7)
    np.testing.assert_allclose(fit.residuals, expected.resid, rtol=1e-7, atol=1e-9)
    assert fit.r_squared == pytest.approx(expected.rsquared, rel=1e-8, abs=1e-12)
    assert fit.degrees_of_freedom == int(expected.df_resid)
    assert fit.lags == (lags if covariance == "newey_west" else 0)


def _exact_errors(
    y: list[Fraction], x: list[list[Fraction]], covariance: str, lags: int
) -> list[float]:
    """Standard errors in exact rational arithmetic (no constant), then rooted."""
    n, k = len(y), len(x[0])
    xtx = [[sum(r[i] * r[j] for r in x) for j in range(k)] for i in range(k)]
    det = xtx[0][0] * xtx[1][1] - xtx[0][1] * xtx[1][0]
    inv = [[xtx[1][1] / det, -xtx[0][1] / det], [-xtx[1][0] / det, xtx[0][0] / det]]
    xty = [sum(r[i] * v for r, v in zip(x, y, strict=True)) for i in range(k)]
    beta = [sum(inv[i][j] * xty[j] for j in range(k)) for i in range(k)]
    e = [
        v - sum(b * c for b, c in zip(beta, r, strict=True))
        for r, v in zip(x, y, strict=True)
    ]
    if covariance == "classical":
        s2 = sum(v * v for v in e) / (n - k)
        cov = [[s2 * inv[i][j] for j in range(k)] for i in range(k)]
    else:
        meat = [[Fraction(0)] * k for _ in range(k)]
        for lag in range(lags + 1):
            weight = Fraction(1) if lag == 0 else 1 - Fraction(lag, lags + 1)
            for t in range(lag, n):
                for i in range(k):
                    for j in range(k):
                        term = x[t][i] * e[t] * e[t - lag] * x[t - lag][j]
                        mirror = x[t - lag][i] * e[t - lag] * e[t] * x[t][j]
                        meat[i][j] += Fraction(
                            weight * (term if lag == 0 else term + mirror)
                        )
        cov = [
            [
                sum(
                    inv[i][a] * meat[a][b] * inv[b][j]
                    for a in range(k)
                    for b in range(k)
                )
                for j in range(k)
            ]
            for i in range(k)
        ]
        if covariance == "hc1":
            cov = [[c * Fraction(n, n - k) for c in row] for row in cov]
    return [math.sqrt(cov[i][i]) for i in range(k)]


@pytest.mark.parametrize(
    ("covariance", "lags"),
    [("classical", 0), ("hc1", 0), ("newey_west", 0), ("newey_west", 2)],
)
@pytest.mark.parametrize("seed", range(6))
def test_errors_keep_their_digits_on_a_near_collinear_design(
    covariance: str, lags: int, seed: int
) -> None:
    rng = np.random.default_rng(seed)
    x = 0.25 + rng.normal(size=(8, 2)) * 1e-6
    y = rng.normal(size=8) * 2e5 + 4e5
    assert np.linalg.cond(x / np.max(np.abs(x), axis=0)) > 1e4
    exact = _exact_errors(
        [Fraction(v) for v in y],
        [[Fraction(v) for v in row] for row in x],
        covariance,
        lags,
    )
    fit = least_squares(y, x, constant=False, covariance=covariance, lags=lags)
    np.testing.assert_allclose(fit.standard_errors, exact, rtol=1e-8)


def test_the_newey_west_rule_picks_the_lag_when_none_is_given() -> None:
    rng = np.random.default_rng(1)
    x = rng.normal(size=240)
    y = 1.0 + 0.5 * x + rng.normal(size=240)
    fit = least_squares(y, x, covariance="newey_west")
    assert fit.lags == newey_west_lags(240) == 4
    expected = sm.OLS(y, sm.add_constant(x)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 4, "use_correction": False}
    )
    np.testing.assert_allclose(fit.standard_errors, expected.bse, rtol=1e-10)


@pytest.mark.parametrize(
    ("observations", "lags"), [(1, 0), (2, 1), (10, 2), (100, 4), (10_000, 11)]
)
def test_the_newey_west_rule(observations: int, lags: int) -> None:
    assert newey_west_lags(observations) == lags


def test_the_lag_rule_needs_an_observation() -> None:
    with pytest.raises(InputError, match="at least one observation"):
        newey_west_lags(0)


@given(
    intercept=st.floats(-1e3, 1e3),
    slope=st.floats(-1e3, 1e3),
    xs=st.lists(st.integers(-50, 50), min_size=3, max_size=40, unique=True),
)
def test_an_exact_line_is_recovered_and_has_no_t_statistic(
    intercept: float, slope: float, xs: list[int]
) -> None:
    y = [intercept + slope * x for x in xs]
    fit = least_squares(y, [float(x) for x in xs])
    level = max(1.0, abs(intercept), abs(slope) * 50)
    assert fit.coefficients[0] == pytest.approx(intercept, abs=1e-9 * level)
    assert fit.coefficients[1] == pytest.approx(slope, abs=1e-9 * level)
    assert fit.exact
    assert fit.t_statistics is None


@settings(max_examples=50, deadline=None)
@given(drawn=regressions())
def test_residuals_are_orthogonal_to_the_regressors(
    drawn: tuple[np.ndarray, np.ndarray, bool, int],
) -> None:
    y, x, constant, _ = drawn
    design = np.column_stack([np.ones(len(y)), x]) if constant else x
    assume(np.linalg.cond(design / np.max(np.abs(design), axis=0)) < 1e6)
    fit = least_squares(y, x, constant=constant)
    residuals = np.asarray(fit.residuals)
    scale = np.max(np.abs(design), axis=0) * np.max(np.abs(y)) * len(y)
    assert np.all(np.abs(design.T @ residuals) <= 1e-10 * scale)
    np.testing.assert_allclose(
        np.asarray(fit.fitted) + residuals, y, rtol=1e-12, atol=1e-12
    )


def test_r_squared_is_uncentered_without_a_constant() -> None:
    y = np.array([1.0, 2.0, 2.0, 4.0])
    x = np.array([1.0, 2.0, 3.0, 4.0])
    fit = least_squares(y, x, constant=False)
    expected = sm.OLS(y, x).fit()
    assert fit.r_squared == pytest.approx(expected.rsquared, rel=1e-12)


def test_a_response_that_does_not_vary_has_no_r_squared() -> None:
    fit = least_squares([3.0, 3.0, 3.0, 3.0], [1.0, 2.0, 4.0, 8.0])
    assert fit.r_squared is None
    assert fit.exact
    zero = least_squares([0.0, 0.0, 0.0], [1.0, 2.0, 3.0], constant=False)
    assert zero.r_squared is None


def test_a_negative_zero_fits_as_zero() -> None:
    plus = least_squares([0.0, 1.0, 2.5, 2.0], [0.0, 1.0, 2.0, 3.0])
    minus = least_squares([-0.0, 1.0, 2.5, 2.0], [-0.0, 1.0, 2.0, 3.0])
    assert plus == minus


def test_a_regressor_of_zeros_is_not_identified() -> None:
    with pytest.raises(DomainError, match="zero in every observation"):
        least_squares(
            [1.0, 2.0, 3.0, 5.0], [[0.0, 1.0], [0.0, 2.0], [0.0, 4.0], [0.0, 5.0]]
        )


def test_a_collinear_design_has_no_fit() -> None:
    x = [[1.0, 2.0], [2.0, 4.0], [3.0, 6.0], [4.0, 8.0]]
    with pytest.raises(DomainError, match="collinear"):
        least_squares([1.0, 2.0, 2.0, 5.0], x)
    with pytest.raises(DomainError, match="collinear"):
        least_squares([1.0, 2.0, 3.0], [5.0, 5.0, 5.0])


@pytest.mark.parametrize(
    ("response", "design", "message"),
    [
        ([1.0, 2.0], [[1.0], [2.0], [3.0]], "observations"),
        ([1.0, math.nan, 2.0], [1.0, 2.0, 3.0], "finite"),
        ([1.0, 2.0, 3.0], [1.0, math.inf, 3.0], "finite"),
        ([[1.0], [2.0]], [1.0, 2.0], "vector"),
        ([1.0, 2.0, 3.0], np.ones((3, 1, 1)), "vector"),
        ([1.0, 2.0], [1.0, 2.0], "more than 2 observations"),
    ],
)
def test_a_bad_regression_is_refused(
    response: object, design: object, message: str
) -> None:
    with pytest.raises(InputError, match=message):
        least_squares(response, design)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_the_bounds_hold() -> None:
    with pytest.raises(InputError, match=f"at most {ROWS_MAX}"):
        least_squares(np.ones(ROWS_MAX + 1), np.arange(ROWS_MAX + 1.0))
    with pytest.raises(InputError, match=f"1 to {COLUMNS_MAX}"):
        least_squares(np.ones(30), np.ones((30, COLUMNS_MAX)))
    with pytest.raises(InputError, match="lag"):
        least_squares([1.0, 2.0, 2.5, 4.0], [1.0, 2.0, 3.0, 4.0], lags=4)
    with pytest.raises(InputError, match="lag"):
        least_squares(np.arange(500.0), np.arange(500.0) ** 2, lags=LAGS_MAX + 1)


def test_an_unknown_covariance_is_refused() -> None:
    with pytest.raises(InputError, match="hc3"):
        least_squares([1.0, 2.0, 2.5], [1.0, 2.0, 3.0], covariance="hc3")


@pytest.mark.parametrize("lags", [2.0, True, "2"])
def test_a_lag_must_be_a_whole_number(lags: object) -> None:
    with pytest.raises(InputError, match="whole number"):
        least_squares(
            [1.0, 2.0, 2.5, 4.0, 5.5],
            [1.0, 2.0, 3.0, 4.0, 5.0],
            covariance="newey_west",
            lags=lags,  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        )


def test_the_covariance_is_recorded() -> None:
    fit = least_squares(
        [1.0, 2.0, 2.5, 4.5], [1.0, 2.0, 3.0, 4.0], covariance=Covariance.HC1
    )
    assert fit.covariance is Covariance.HC1
    assert fit.lags == 0
    assert fit.observations == 4


def test_subnormal_data_fits_without_overflow() -> None:
    # Response and regressor both near 1e-310: unit / scales is moderate, so
    # scaling back must not divide a coefficient by a subnormal scale first.
    rng = np.random.default_rng(12)
    x = rng.normal(0.0, 0.05, size=40)
    y = 0.002 + 1.3 * x + rng.normal(0.0, 0.01, size=40)
    plain = least_squares(y, x, covariance="newey_west")
    tiny = least_squares(y * 1e-310, x * 1e-310, covariance="newey_west")
    assert tiny.coefficients[1] == pytest.approx(plain.coefficients[1], rel=1e-6)
    assert tiny.standard_errors[1] == pytest.approx(plain.standard_errors[1], rel=1e-6)


def test_a_coefficient_past_the_floating_point_range_is_refused() -> None:
    # A slope of about 1e316: past the largest float.
    x = [1e-318, -2e-318, 3e-318, -1e-318, 2e-318]
    y = [0.01, -0.02, 0.03, -0.01, 0.025]
    with pytest.raises(DomainError, match="beyond the floating-point range"):
        least_squares(y, x)
