# tests/unit/core/test_descriptive.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Descriptive statistics: the named estimators, their limits and refusals."""

from __future__ import annotations

import math

import pytest

from pyeconomics.core import (
    DomainError,
    InputError,
    annualized_log_return,
    annualized_return,
    compound_return,
    has_spread,
    log_return,
    max_drawdown,
    sample_mean,
    sample_moments,
    sample_variance,
    semideviation_below_mean,
    semideviation_below_target,
)


def test_numacc1_keeps_its_digits() -> None:
    # NIST StRD NumAcc1: certified mean 10000002 and standard deviation 1.
    data = [10000001.0, 10000003.0, 10000002.0]
    assert sample_mean(data) == 10000002.0
    assert sample_variance(data) == 1.0


def test_the_variance_divides_by_n_minus_ddof() -> None:
    assert sample_variance([1.0, 3.0], ddof=0) == 1.0
    assert sample_variance([1.0, 3.0]) == 2.0


@pytest.mark.parametrize(
    "values",
    [[], [[1.0, 2.0]], [1.0, math.inf]],
    ids=["empty", "two_dimensional", "infinite"],
)
def test_a_bad_series_is_refused(values: list[object]) -> None:
    with pytest.raises(InputError):
        sample_mean(values)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_too_few_values_are_refused() -> None:
    with pytest.raises(InputError, match="at least 2"):
        sample_variance([1.0])
    with pytest.raises(InputError, match="at least 4"):
        sample_moments([1.0, 2.0, 3.0])


def test_the_target_must_be_finite() -> None:
    with pytest.raises(InputError):
        semideviation_below_target([0.1, 0.2], math.nan)


def test_semideviations_of_a_rising_series() -> None:
    assert semideviation_below_target([0.1, 0.2], 0.0) == 0.0
    assert semideviation_below_mean([0.0, 2.0]) == 1.0


def test_moments_of_rounding_noise_are_undefined() -> None:
    # The spread is a few ulps of the values: no shape can be estimated.
    with pytest.raises(DomainError, match="no spread"):
        sample_moments([1.0, 1.0 + 2**-52, 1.0, 1.0])


def test_a_drawdown_needs_positive_values() -> None:
    with pytest.raises(InputError, match="positive"):
        max_drawdown([1.0, 0.0])


def test_a_drawdown_peak_is_the_first_of_a_repeated_maximum() -> None:
    found = max_drawdown([5.0, 10.0, 7.0, 10.0, 4.0])
    assert (found.depth, found.peak, found.trough) == (0.6, 1, 4)


@pytest.mark.parametrize(
    "values",
    [
        [0.0, 0.0, 0.0, 1e-200],
        [0.0, 0.0, 1e-120, 1e-120],
        [0.0, 0.0, 0.0, 2.2250738585072014e-308],
    ],
    ids=["1e-200", "1e-120", "smallest_normal"],
)
def test_moments_of_a_tiny_spread_are_scale_free(values: list[float]) -> None:
    # Review regression: m2**1.5 used to underflow to zero and divide by it.
    shape = sample_moments(values)
    reference = sample_moments([v / max(values) for v in values])
    assert math.isclose(shape.skewness, reference.skewness, rel_tol=1e-12)
    assert math.isclose(shape.excess_kurtosis, reference.excess_kurtosis, rel_tol=1e-12)


def test_returns_compound_geometrically() -> None:
    assert math.isclose(compound_return([0.1, -0.05, 0.2]), 0.254, rel_tol=1e-15)
    assert compound_return([0.5, -1.0, 2.0]) == -1.0
    assert compound_return([100.0] * 200) == math.inf


def test_a_loss_beyond_everything_does_not_compound() -> None:
    with pytest.raises(InputError, match="below -1"):
        compound_return([0.1, -1.5])


def test_annualizing_compounds_to_a_year() -> None:
    assert math.isclose(annualized_return(0.21, 2, 1), 0.1, rel_tol=1e-15)
    assert math.isclose(annualized_return(0.01, 1, 12), 1.01**12 - 1, rel_tol=1e-14)
    assert annualized_return(0.0, 1e-9, 1e5) == 0.0
    assert annualized_return(-1.0, 1, 12) == -1.0
    assert annualized_return(100.0, 1, 1000) == math.inf
    assert annualized_return(-0.999999, 1, 1e5) == -1.0


@pytest.mark.parametrize(
    ("total", "periods", "per_year"),
    [(-1.5, 1, 1), (math.nan, 1, 1), (0.1, 0, 1), (0.1, 1, -12), (0.1, math.inf, 1)],
)
def test_annualizing_refuses_what_has_no_meaning(
    total: float, periods: float, per_year: float
) -> None:
    with pytest.raises(InputError):
        annualized_return(total, periods, per_year)


def test_spread_is_more_than_rounding() -> None:
    assert not has_spread([0.1, 0.1, 0.1])
    assert not has_spread([1.0, 1.0 + 2**-52])
    assert has_spread([0.1, 0.2])
    assert has_spread([0.0, 1e-300])


def test_log_returns_sum_without_rounding_to_a_total_loss() -> None:
    assert math.isclose(log_return([0.1, -0.05, 0.2]), math.log(1.254), rel_tol=1e-15)
    assert log_return([0.1, -1.0]) == -math.inf
    assert math.isclose(log_return([-0.5] * 2000), 2000 * math.log(0.5), rel_tol=1e-15)
    with pytest.raises(InputError, match="below -1"):
        log_return([-2.0])


def test_annualizing_a_log_return() -> None:
    assert math.isclose(
        annualized_log_return(log_return([-0.5] * 100), 100, 1), -0.5, rel_tol=1e-15
    )
    assert annualized_log_return(-math.inf, 3, 12) == -1.0
    assert annualized_log_return(0.0, 1e-9, 1e5) == 0.0
    assert annualized_log_return(1000.0, 1, 12) == math.inf
    for bad in (math.nan, math.inf):
        with pytest.raises(InputError, match="finite or minus infinity"):
            annualized_log_return(bad, 1, 1)
